# Deploy на hoster.by по push в GitHub

Эта копия проекта разворачивается как Django-сайт с отдельным Telegram-ботом. В репозиторий добавлены:

- `.github/workflows/deploy-hosterby.yml`
- `scripts/deploy_hosterby.sh`
- `backend/.env.example`

Схема работы такая:

1. Вы пушите код в `main` или `master`.
2. GitHub Actions подключается к серверу `hoster.by` по SSH.
3. Workflow синхронизирует проект в папку на сервере.
4. На сервере запускается `scripts/deploy_hosterby.sh`.
5. Скрипт обновляет backend virtualenv, зависимости, миграции и статику.
6. Если в репозитории есть `telegram-bot/`, скрипт обновляет и его зависимости.
7. В конце выполняется `POST_DEPLOY_COMMAND`, если он указан в `backend/.env`.

## 1. Что нужно на сервере

- VPS на `hoster.by` с SSH-доступом
- установленные `python3`, `python3-venv`, `rsync`, `curl`
- папка проекта, например `/var/www/buket`
- настроенный способ запуска Django:
  - `systemd + gunicorn`, или
  - Passenger/панель с командой перезапуска
- если используется бот: отдельный `systemd`-сервис для `telegram-bot`

## 2. Первый запуск на сервере

Создайте папку проекта:

```bash
mkdir -p /var/www/buket
```

После первого копирования файлов создайте прод-конфиг для Django:

```bash
cp /var/www/buket/backend/.env.example /var/www/buket/backend/.env
```

Минимальный пример `backend/.env`:

```env
SECRET_KEY=your-long-random-secret
DEBUG=False
ALLOWED_HOSTS=buket.by,www.buket.by
CSRF_TRUSTED_ORIGINS=https://buket.by,https://www.buket.by
CORS_ALLOWED_ORIGINS=https://buket.by,https://www.buket.by
TELEGRAM_BOT_SECRET=shared-secret-for-bot
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=False
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
POST_DEPLOY_COMMAND=sudo systemctl restart buket buket-bot
HEALTHCHECK_URL=https://buket.by/
```

Если у вас нет отдельного сервиса для бота, оставьте только:

```env
POST_DEPLOY_COMMAND=sudo systemctl restart buket
```

Для бота на сервере нужен свой `.env`, например `telegram-bot/.env`:

```env
BOT_TOKEN=your-telegram-token
DJANGO_API_URL=https://buket.by
BOT_SECRET=shared-secret-for-bot
```

## 3. GitHub Secrets

В GitHub откройте `Settings -> Secrets and variables -> Actions` и создайте:

- `HOSTER_HOST` - IP или домен сервера
- `HOSTER_USER` - SSH-пользователь
- `HOSTER_SSH_KEY` - приватный SSH-ключ для входа

Опционально:

- `HOSTER_PORT` - SSH-порт, если не `22`
- `HOSTER_DEPLOY_PATH` - путь на сервере, по умолчанию `/var/www/buket`
- `HOSTER_KNOWN_HOSTS` - вывод `ssh-keyscan -H your-host`

Пример:

```bash
ssh-keyscan -H buket.by
```

## 4. Что делает workflow

`.github/workflows/deploy-hosterby.yml`:

- запускается на push в `main` и `master`
- делает `python manage.py check`
- подключается к серверу по SSH
- синхронизирует код через `rsync`
- не затирает:
  - `backend/.env`
  - `backend/.venv`
  - `backend/db.sqlite3`
  - `backend/media/`
  - `backend/staticfiles/`
  - `*.log`
  - `telegram-bot/.env`
  - `telegram-bot/.venv`
- запускает `scripts/deploy_hosterby.sh`

## 5. Что делает серверный скрипт

`scripts/deploy_hosterby.sh`:

- загружает переменные из `backend/.env`
- создает `backend/.venv` при первом запуске
- обновляет backend зависимости
- выполняет:

```bash
python manage.py check
python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

- если есть `telegram-bot/requirements.txt`, обновляет зависимости бота
- затем запускает `POST_DEPLOY_COMMAND`
- затем делает health-check по `HEALTHCHECK_URL`

## 6. Пример systemd для Django

```ini
[Unit]
Description=Buket Django
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/buket/backend
EnvironmentFile=/var/www/buket/backend/.env
ExecStart=/var/www/buket/backend/.venv/bin/gunicorn flowershop_backend.wsgi:application --bind 127.0.0.1:8000 --workers 3
Restart=always

[Install]
WantedBy=multi-user.target
```

После создания сервиса:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now buket
```

## 7. Пример systemd для бота

```ini
[Unit]
Description=Buket Telegram Bot
After=network.target buket.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/buket/telegram-bot
EnvironmentFile=/var/www/buket/telegram-bot/.env
ExecStart=/var/www/buket/telegram-bot/.venv/bin/python -m bot.main
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now buket-bot
```

## 8. Дальше рабочий цикл простой

```bash
git add .
git commit -m "Deploy update"
git push origin main
```

После push GitHub Actions сам выполнит деплой на `hoster.by`.
