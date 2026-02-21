# Deploy на hoster.by (Django + Next.js)

Этот проект лучше деплоить на **VPS** (не shared-хостинг), потому что фронт на Next.js требует Node runtime.

## 1. Что нужно заранее

- VPS на hoster.by (Ubuntu 22.04/24.04)
- Домен, направленный на IP сервера (`A` запись)
- SSH доступ

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
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
deactivate
```

Создай `backend/.env` (если используешь env-переменные в settings):

```env
DEBUG=False
ALLOWED_HOSTS=your-domain.by,www.your-domain.by
```

Systemd-сервис `/etc/systemd/system/buket-backend.service`:

```ini
[Unit]
Description=Buket Django Backend
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/buket/backend
Environment="PATH=/var/www/buket/backend/.venv/bin"
ExecStart=/var/www/buket/backend/.venv/bin/gunicorn flowershop_backend.wsgi:application --bind 127.0.0.1:3002 --workers 3
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now buket-backend
sudo systemctl status buket-backend
```

## 5. Frontend (Next.js, порт 3001)

```bash
cd /var/www/buket/frontend
npm ci
```

Создай `frontend/.env.production`:

```env
NEXT_PUBLIC_API_BASE_URL=https://your-domain.by
```

```bash
npm run build
pm2 start npm --name buket-frontend -- start -- -p 3001
pm2 save
pm2 startup
pm2 status
```

## 6. Nginx reverse proxy

Файл `/etc/nginx/sites-available/buket`:

```nginx
server {
    listen 80;
    server_name your-domain.by www.your-domain.by;

    client_max_body_size 20M;

    location /media/ {
        alias /var/www/buket/backend/media/;
    }

    location /static/ {
        alias /var/www/buket/backend/static/;
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

## 7. SSL (Let's Encrypt)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.by -d www.your-domain.by
sudo systemctl status certbot.timer
```

## 8. Обновление проекта (релиз)

```bash
cd /var/www/buket
git pull

cd backend
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
deactivate
sudo systemctl restart buket-backend

cd ../frontend
npm ci
npm run build
pm2 restart buket-frontend
```

## 9. Быстрый health-check

```bash
curl -I https://your-domain.by
curl -I https://your-domain.by/api/hero-banners/current/
```

## 10. Важно для продакшена

- Не держи `DEBUG=True`.
- Установи сильный `SECRET_KEY` через env.
- Для серьезной нагрузки используй PostgreSQL вместо SQLite.
- Делай бэкап `backend/db.sqlite3` и `backend/media/`.
