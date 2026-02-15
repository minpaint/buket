# Telegram -> Online витрина: текущее решение

## Статус

Документ фиксирует текущее внедрение:
- Django backend расширен под мультимагазины и Telegram-публикацию.
- Добавлен базовый Telegram-бот (aiogram 3) для потока: магазин -> фото -> цена -> название -> публикация.
- Frontend получает фильтр магазина по поддомену при загрузке товаров.

Дата фиксации: 2026-02-14.

## Бизнес-сценарий

Менеджер ТЦ отправляет фото и цену в Telegram-бот.
Бот публикует букет в нужный магазин (поддомен) в разделе online showcase.
Доступ менеджера ограничен его магазинами (через `telegram_id`).

## Реализовано в backend (Django)

### Модели

Файл: `backend/shop/models.py`

Добавлены:
- `Store`
  - `subdomain` (у основного домена пустая строка)
  - `name`
  - `is_active`
  - `address`, `phone`
- `StoreManager`
  - `telegram_id` (unique)
  - `telegram_username`
  - `full_name`
  - `stores` (M2M на `Store`)
  - `is_active`

Расширен `Product`:
- `store` (`FK -> Store`)
- `created_by` (`FK -> StoreManager`)
- `is_published` (bool)
- `image` теперь допускает пустое значение (`blank=True`, `default=''`)

### API и permission

Файлы:
- `backend/shop/views.py`
- `backend/shop/serializers.py`
- `backend/shop/urls.py`

Добавлено:
- `BotTokenPermission` (проверка заголовка `X-Bot-Token`)
- `POST /api/v1/auth/bot-token/`
  - проверяет `telegram_id`
  - возвращает профиль менеджера + доступные магазины
- `POST /api/v1/products/from-bot/`
  - multipart endpoint для публикации товара из бота
  - валидация доступа менеджера к выбранному магазину
  - автоматически:
    - `is_online_showcase=True`
    - `is_published=True`
    - `created_by=StoreManager`
    - синхронизация `image` из `uploaded_image`
- `GET /api/stores/` (read-only)
- фильтрация `ProductViewSet` по query-параметру `store__subdomain`
- для неавторизованных запросов товары ограничены `is_published=True`

### Настройки

Файл: `backend/flowershop_backend/settings.py`

Добавлено:
- `TELEGRAM_BOT_SECRET` из env
- `ALLOWED_HOSTS`: `buket.by`, `.buket.by`

### Миграции

Новые миграции:
- `backend/shop/migrations/0008_store_product_is_published_alter_product_image_and_more.py`
- `backend/shop/migrations/0009_seed_default_stores.py`

Сиды магазинов:
- `""` -> `Основной магазин (buket.by)`
- `dana-mall` -> `Dana Mall`
- `gallery-minsk` -> `Gallery Minsk`
- `minsk-city-mall` -> `Minsk City Mall`

## Реализовано в telegram-bot

Новая директория: `telegram-bot/`

Ключевые файлы:
- `telegram-bot/bot/main.py`
- `telegram-bot/bot/api_client.py`
- `telegram-bot/bot/states.py`
- `telegram-bot/bot/keyboards.py`
- `telegram-bot/bot/config.py`
- `telegram-bot/requirements.txt`
- `telegram-bot/.env.example`

Флоу:
1. `/start` -> проверка доступа
2. `/add` -> выбор магазина
3. загрузка фото
4. ввод цены
5. ввод названия или `/skip`
6. подтверждение -> публикация в Django API

## Изменение frontend

Файл: `frontend/src/services/services.ts`

Добавлено:
- определение subdomain из `window.location.hostname`
- автоматическая подстановка `store__subdomain` в запросы:
  - список товаров
  - товары по категории
  - online showcase

## Настройка перед запуском

### Backend `.env`

Минимум:
- `TELEGRAM_BOT_SECRET=<secret>`

### Bot `.env`

На базе `telegram-bot/.env.example`:
- `BOT_TOKEN=<telegram token>`
- `DJANGO_API_URL=http://127.0.0.1:3002` (или ваш backend URL)
- `BOT_SECRET=<тот же secret, что в backend>`

## Операционные шаги

1. Применить миграции:
   - `python manage.py migrate`
2. В админке создать менеджеров:
   - заполнить `telegram_id`
   - назначить доступные `stores`
3. Запустить backend.
4. Запустить бота:
   - `python -m bot.main` (из `telegram-bot/`)
5. Протестировать `/add`.

## Что еще не доведено до production

- Нет docker-compose для backend + bot + redis.
- Нет webhook-режима (бот работает polling).
- Нет тестов для новых API (bot auth и bot product create).
- Нет rate-limit и расширенного audit/security logging.
- Нет отдельной middleware-логики для subdomain в Next.js (сейчас фильтр определяется в клиентском сервисе).

## Быстрый чек-лист возврата к задаче

Когда вернемся:
1. Добавить автотесты DRF для bot endpoints.
2. Перевести бота на webhook + reverse proxy.
3. Добавить docker-compose и единый запуск.
4. Добавить строгую subdomain-резолюцию на server-side фронта.
5. Ввести мониторинг ошибок и retry-политику в боте.
