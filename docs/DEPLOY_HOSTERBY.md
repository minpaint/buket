# Deploy на hoster.by (Django + Telegram Bot + Next.js)

Этот проект лучше деплоить на **VPS** (не shared-хостинг), потому что фронт на Next.js требует Node runtime.

## Архитектура production

```
Nginx (443/80)
  ├── /static/, /media/  →  файлы на диске
  ├── /api/, /admin/, /dashboard/  →  gunicorn :3002 (Django)
  └── /  →  pm2 :3001 (Next.js frontend)

Отдельный systemd-сервис: Telegram Bot (python -m bot.main)
```

**Важно:** в production бот запускается **отдельным systemd-сервисом**, а НЕ внутри Django. В Django нужно установить переменную `BOT_AUTOSTART=false`, иначе бот запустится в каждом gunicorn-воркере и получишь TelegramConflictError.

---

## 1. Что нужно заранее

- VPS на hoster.by (Ubuntu 22.04/24.04)
- Домен, направленный на IP сервера (`A` запись)
- SSH доступ
- Токен бота от @BotFather

## 2. Установка базовых пакетов

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git nginx python3 python3-venv python3-pip
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
sudo npm i -g pm2
```

## 3. Клонирование проекта

```bash
cd /var/www
sudo git clone <YOUR_REPO_URL> buket
sudo chown -R $USER:$USER /var/www/buket
cd /var/www/buket
```

## 4. Backend (Django, порт 3002)

```bash
cd /var/www/buket/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install gunicorn  # если не в requirements.txt
```

Создай `backend/.env`:

```env
SECRET_KEY=сгенерируй-длинный-случайный-ключ-минимум-50-символов
DEBUG=False
ALLOWED_HOSTS=buket.by,www.buket.by
TELEGRAM_BOT_SECRET=buket_secret_2025
BOT_AUTOSTART=false
```

> `BOT_AUTOSTART=false` — **обязательно** в production! Без этого бот запустится в каждом gunicorn-воркере.

Подключи `.env` в `settings.py` — добавь в начало файла:

```python
from pathlib import Path
import os
from dotenv import load_dotenv  # pip install python-dotenv

load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.environ['SECRET_KEY']
DEBUG = os.getenv('DEBUG', 'False') == 'True'
TELEGRAM_BOT_SECRET = os.getenv('TELEGRAM_BOT_SECRET', '')
```

Запусти миграции и сбор статики:

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
deactivate
```

Systemd-сервис Django — `/etc/systemd/system/buket-backend.service`:

```ini
[Unit]
Description=Buket Django Backend
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/buket/backend
EnvironmentFile=/var/www/buket/backend/.env
Environment="PATH=/var/www/buket/backend/.venv/bin"
ExecStart=/var/www/buket/backend/.venv/bin/gunicorn \
    flowershop_backend.wsgi:application \
    --bind 127.0.0.1:3002 \
    --workers 3
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now buket-backend
sudo systemctl status buket-backend
```

## 5. Telegram Bot (отдельный сервис)

```bash
cd /var/www/buket/telegram-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
deactivate
```

Создай `telegram-bot/.env`:

```env
BOT_TOKEN=токен-от-botfather
DJANGO_API_URL=https://buket.by
BOT_SECRET=buket_secret_2025
```

> `DJANGO_API_URL` должен указывать на продакшен-домен (не localhost), потому что бот и Django — отдельные процессы.

Systemd-сервис бота — `/etc/systemd/system/buket-bot.service`:

```ini
[Unit]
Description=Buket Telegram Bot
After=network.target buket-backend.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/buket/telegram-bot
EnvironmentFile=/var/www/buket/telegram-bot/.env
Environment="PATH=/var/www/buket/telegram-bot/.venv/bin"
ExecStart=/var/www/buket/telegram-bot/.venv/bin/python -m bot.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now buket-bot
sudo systemctl status buket-bot
```

Проверить логи бота:

```bash
sudo journalctl -u buket-bot -f
```

## 6. Frontend (Next.js, порт 3001)

```bash
cd /var/www/buket/frontend
npm ci
```

Создай `frontend/.env.production`:

```env
NEXT_PUBLIC_API_BASE_URL=https://buket.by
```

```bash
npm run build
pm2 start npm --name buket-frontend -- start -- -p 3001
pm2 save
pm2 startup
pm2 status
```

## 7. Nginx reverse proxy

Файл `/etc/nginx/sites-available/buket`:

```nginx
server {
    listen 80;
    server_name buket.by www.buket.by;

    client_max_body_size 20M;

    location /media/ {
        alias /var/www/buket/backend/media/;
    }

    location /static/ {
        alias /var/www/buket/backend/staticfiles/;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:3002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /admin/ {
        proxy_pass http://127.0.0.1:3002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /dashboard/ {
        proxy_pass http://127.0.0.1:3002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://127.0.0.1:3001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/buket /etc/nginx/sites-enabled/buket
sudo nginx -t
sudo systemctl reload nginx
```

## 8. SSL (Let's Encrypt)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d buket.by -d www.buket.by
sudo systemctl status certbot.timer
```

## 9. Обновление проекта (релиз)

```bash
cd /var/www/buket
git pull

# Django
cd backend
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
deactivate
sudo systemctl restart buket-backend

# Бот (если менялся код бота)
cd ../telegram-bot
source .venv/bin/activate
pip install -r requirements.txt
deactivate
sudo systemctl restart buket-bot

# Frontend
cd ../frontend
npm ci
npm run build
pm2 restart buket-frontend
```

## 10. Быстрый health-check

```bash
# Django работает
curl -I https://buket.by/api/hero-banners/current/

# Дашборд доступен
curl -I https://buket.by/dashboard/

# Статика отдаётся
curl -I https://buket.by/static/

# Статус сервисов
sudo systemctl status buket-backend buket-bot
pm2 status
```

## 11. Управление ботом

```bash
# Статус
sudo systemctl status buket-bot

# Перезапуск (после изменений в коде бота)
sudo systemctl restart buket-bot

# Логи в реальном времени
sudo journalctl -u buket-bot -f

# Остановить / запустить
sudo systemctl stop buket-bot
sudo systemctl start buket-bot
```

## 12. Важно для продакшена

| Что | Статус | Примечание |
|-----|--------|------------|
| `DEBUG=False` | ⚠️ Обязательно | Иначе Django отдаёт трейсбеки в браузер |
| `SECRET_KEY` из env | ⚠️ Обязательно | Никогда не хранить в коде |
| `BOT_AUTOSTART=false` | ⚠️ Обязательно | Иначе TelegramConflictError в каждом gunicorn-воркере |
| `DJANGO_API_URL=https://buket.by` | ⚠️ Обязательно | Бот должен стучаться на продакшен-домен, не localhost |
| Бэкап `db.sqlite3` | 🔄 Регулярно | `cp backend/db.sqlite3 /backup/db-$(date +%Y%m%d).sqlite3` |
| Бэкап `media/` | 🔄 Регулярно | Все загруженные фото букетов |
| PostgreSQL вместо SQLite | 💡 Рекомендуется | При росте нагрузки SQLite может блокироваться |

## 13. Структура `.env` файлов

**`backend/.env`** — для Django + gunicorn:
```env
SECRET_KEY=<длинный-случайный-ключ>
DEBUG=False
ALLOWED_HOSTS=buket.by,www.buket.by
TELEGRAM_BOT_SECRET=buket_secret_2025
BOT_AUTOSTART=false
```

**`telegram-bot/.env`** — для бота:
```env
BOT_TOKEN=<токен-от-botfather>
DJANGO_API_URL=https://buket.by
BOT_SECRET=buket_secret_2025
```

> `BOT_SECRET` и `TELEGRAM_BOT_SECRET` должны совпадать в обоих файлах — это общий секрет для аутентификации бота в API Django.
