# Инструкция по миграции данных

## Обзор

Есть три источника данных:
1. **SQL дамп VirtueMart** (`old/buketby_newbd.sql`) - старая база данных с категориями, товарами и изображениями
2. **Excel таблица** (`bukety_tablica.xlsx`) - актуальные данные о букетах
3. **JSON иерархия категорий** - новая структура категорий

## Структура данных

### Категории (многоуровневая иерархия)

Категории имеют древовидную структуру:
- Родительские категории (например, "Букеты по цветам")
- Дочерние категории (например, "Розы", "Тюльпаны")

**Важно**: Товар может принадлежать к нескольким категориям одновременно (many-to-many).

### Товары

Каждый товар имеет:
- Название (`title`)
- Описание (`description`)
- Цену (`price`)
- Артикул (`article`)
- Основную категорию (`category`) - ForeignKey
- Дополнительные категории (`categories`) - ManyToManyField
- Множество изображений через `ProductImage`

### Изображения

Каждое изображение товара:
- Привязано к товару через ForeignKey
- Имеет порядок отображения (`sort_order`)
- Хранится в `media/products/`

## Скрипты миграции

### 1. `migrate_from_vm.py`

Мигрирует данные из старой базы VirtueMart:
- Категории и их иерархию
- Товары с привязкой к категориям
- Изображения товаров (пути к файлам)

**Использование:**
```bash
cd "G:\Мой диск\buket"
python migrate_from_vm.py
```

**Что делает:**
- Парсит SQL INSERT запросы из дампа
- Создает категории с учетом parent-child связей
- Создает товары и связывает с категориями
- Сохраняет пути к изображениям (файлы нужно скопировать отдельно)

### 2. `migrate_from_excel.py`

Мигрирует данные из Excel таблицы:
- Создает иерархию категорий из JSON
- Загружает товары из Excel
- Связывает товары с несколькими категориями

**Использование:**
```bash
cd "G:\Мой диск\buket"
python migrate_from_excel.py
```

**Требования к Excel:**
- Колонки: `Название`, `Описание`, `Цена`, `Артикул`
- Колонки категорий: `Категория 1`, `Категория 2`, и т.д.

### 3. `parse_sql.py`

Вспомогательный скрипт для анализа SQL дампа и связи товаров с изображениями.

## Пошаговая инструкция миграции

### Шаг 1: Создание миграции БД

```bash
cd "G:\Мой диск\buket\backend"
python manage.py makemigrations
python manage.py migrate
```

### Шаг 2: Создание категорий

Запустите один из скриптов (рекомендуется Excel):

```bash
cd "G:\Мой диск\buket"
python migrate_from_excel.py
```

Это создаст полную иерархию категорий из JSON.

### Шаг 3: Миграция товаров из VirtueMart

```bash
python migrate_from_vm.py
```

Это:
- Загрузит товары из старой базы
- Свяжет их с категориями
- Создаст записи изображений (с путями к старым файлам)

### Шаг 4: Копирование изображений

Изображения находятся в старой базе по путям:
- `images/product/data/*.jpg`

Нужно скопировать их в:
- `backend/media/products/`

Скрипт для копирования (PowerShell):
```powershell
# TODO: Создать скрипт копирования изображений
```

### Шаг 5: Обновление путей к изображениям

После копирования файлов нужно обновить пути в БД:

```python
# Скрипт для обновления путей изображений
from shop.models import ProductImage

for img in ProductImage.objects.all():
    # Преобразовать путь из images/product/data/1.jpg
    # в products/1.jpg
    old_path = img.image.name
    new_path = old_path.replace('images/product/data/', 'products/')
    img.image.name = new_path
    img.save()
```

### Шаг 6: Проверка данных

```bash
cd "G:\Мой диск\buket\backend"
python manage.py shell
```

```python
from shop.models import Category, Product, ProductImage

# Проверяем категории
print(f"Категорий: {Category.objects.count()}")
for cat in Category.objects.filter(parent=None):
    print(f"  {cat.name} ({cat.children.count()} подкатегорий)")

# Проверяем товары
print(f"\nТоваров: {Product.objects.count()}")
print(f"Товаров с категориями: {Product.objects.exclude(category=None).count()}")

# Проверяем изображения
print(f"\nИзображений: {ProductImage.objects.count()}")
print(f"Товаров с изображениями: {Product.objects.filter(images__isnull=False).distinct().count()}")
```

## Модели Django

### Category

```python
class Category(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', null=True, blank=True,
                                on_delete=models.CASCADE,
                                related_name='children')
    sort_order = models.PositiveIntegerField(default=0)
```

### Product

```python
class Product(models.Model):
    title = models.CharField(max_length=100)
    article = models.CharField(max_length=64)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    # Основная категория
    category = models.ForeignKey('Category', null=True, blank=True,
                                   on_delete=models.SET_NULL,
                                   related_name='main_products')

    # Дополнительные категории (many-to-many)
    categories = models.ManyToManyField('Category',
                                         related_name='products',
                                         blank=True)
```

### ProductImage

```python
class ProductImage(models.Model):
    product = models.ForeignKey('Product', on_delete=models.CASCADE,
                                 related_name='images')
    image = models.ImageField(upload_to='products/')
    sort_order = models.PositiveIntegerField(default=0)
```

## Решение проблем

### Проблема: Товары без категорий

Проверьте маппинг категорий в скриптах миграции. Возможно, названия категорий в Excel и JSON не совпадают.

### Проблема: Изображения не отображаются

1. Проверьте, что файлы скопированы в `backend/media/products/`
2. Проверьте права доступа к файлам
3. Проверьте настройки `MEDIA_URL` и `MEDIA_ROOT` в `settings.py`

### Проблема: Дубликаты товаров

Скрипты используют `article` как уникальный идентификатор. Проверьте, что артикулы уникальны.

## Следующие шаги

После успешной миграции:
1. Проверьте данные в Django Admin
2. Настройте отображение товаров на фронтенде
3. Проверьте работу фильтров по категориям
4. Оптимизируйте запросы (select_related, prefetch_related)
