# Руководство по миграции данных

## Обзор проблемы

У вас есть старый сайт на VirtueMart с букетами, и вам нужно перенести данные в новый Django сайт. Основные сложности:

1. **Множественные категории** - один букет может принадлежать к нескольким категориям
2. **Иерархия категорий** - категории имеют parent-child структуру
3. **Много изображений** - у каждого товара может быть несколько изображений

## Текущая структура данных

### Старая база VirtueMart (SQL)

- `wzx3q_virtuemart_categories` - категории
- `wzx3q_virtuemart_categories_ru_ru` - названия категорий на русском
- `wzx3q_virtuemart_category_categories` - иерархия категорий (parent-child)
- `wzx3q_virtuemart_products` - товары
- `wzx3q_virtuemart_products_ru_ru` - описания товаров на русском
- `wzx3q_virtuemart_product_categories` - связь товары-категории (many-to-many)
- `wzx3q_virtuemart_medias` - медиафайлы (изображения)
- `wzx3q_virtuemart_product_medias` - связь товары-изображения

### Новая Django структура

```python
class Category(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', null=True, blank=True,
                                related_name='children')
    sort_order = models.PositiveIntegerField(default=0)

class Product(models.Model):
    title = models.CharField(max_length=100)
    article = models.CharField(max_length=64)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    # Основная категория
    category = models.ForeignKey('Category', null=True, blank=True,
                                   related_name='main_products')

    # Все категории (many-to-many)
    categories = models.ManyToManyField('Category',
                                         related_name='products',
                                         blank=True)

class ProductImage(models.Model):
    product = models.ForeignKey('Product', related_name='images')
    image = models.ImageField(upload_to='products/')
    sort_order = models.PositiveIntegerField(default=0)
```

## Пошаговая миграция

### Шаг 1: Создание миграции для новых полей

```bash
cd "G:\Мой диск\buket\backend"
python manage.py makemigrations
python manage.py migrate
```

Это создаст поле `categories` (ManyToManyField) в модели Product.

### Шаг 2: Создание категорий

У вас есть два варианта:

#### Вариант A: Из JSON иерархии (рекомендуется)

Используйте команду для создания чистой структуры категорий:

```bash
python manage.py create_categories
```

Это создаст категории по вашей новой структуре из JSON.

Если хотите пересоздать категории:

```bash
python manage.py create_categories --clear
```

#### Вариант B: Из старой базы VirtueMart

Если хотите сохранить старую структуру:

```bash
python manage.py migrate_old_data --categories-only
```

### Шаг 3: Миграция товаров

```bash
python manage.py migrate_old_data --products-only
```

Это:
- Загрузит все товары из старой базы
- Свяжет каждый товар с несколькими категориями (many-to-many)
- Установит основную категорию (первую из списка)

### Шаг 4: Миграция изображений

```bash
python manage.py migrate_old_data --images-only
```

Это создаст записи ProductImage с путями к изображениям.

**Важно**: На этом этапе создаются только записи в БД, сами файлы изображений нужно скопировать отдельно!

### Шаг 5: Копирование файлов изображений

Изображения в старой базе находятся по путям типа:
```
images/product/data/1.jpg
images/product/data/1_2.jpg
images/product/data/2.jpg
```

Их нужно скопировать в:
```
backend/media/products/
```

#### Скрипт для копирования (PowerShell):

```powershell
# TODO: Укажите путь к старым изображениям
$sourceDir = "путь\к\старому\сайту\images\product\data"
$targetDir = "G:\Мой диск\buket\backend\media\products"

# Создаем целевую директорию
New-Item -ItemType Directory -Force -Path $targetDir

# Копируем все изображения
Get-ChildItem -Path $sourceDir -Filter *.jpg | ForEach-Object {
    Copy-Item $_.FullName -Destination $targetDir
}

Get-ChildItem -Path $sourceDir -Filter *.png | ForEach-Object {
    Copy-Item $_.FullName -Destination $targetDir
}
```

#### Или через Python:

```python
import os
import shutil
from pathlib import Path

source_dir = Path("путь/к/старому/сайту/images/product/data")
target_dir = Path("G:/Мой диск/buket/backend/media/products")

target_dir.mkdir(parents=True, exist_ok=True)

for img in source_dir.glob("*.*"):
    if img.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
        shutil.copy2(img, target_dir / img.name)
        print(f"Скопировано: {img.name}")
```

### Шаг 6: Проверка данных

```bash
python manage.py shell
```

```python
from shop.models import Category, Product, ProductImage

# Статистика
print(f"Категорий: {Category.objects.count()}")
print(f"  - Родительских: {Category.objects.filter(parent=None).count()}")
print(f"  - Дочерних: {Category.objects.exclude(parent=None).count()}")

print(f"\nТоваров: {Product.objects.count()}")
print(f"  - С основной категорией: {Product.objects.exclude(category=None).count()}")

# Проверим товары с множественными категориями
for p in Product.objects.all()[:5]:
    cats = p.categories.all()
    print(f"{p.title}: {cats.count()} категорий - {[c.name for c in cats]}")

print(f"\nИзображений: {ProductImage.objects.count()}")
print(f"Товаров с изображениями: {Product.objects.filter(images__isnull=False).distinct().count()}")

# Проверим иерархию категорий
for parent in Category.objects.filter(parent=None)[:5]:
    print(f"\n{parent.name}:")
    for child in parent.children.all():
        print(f"  - {child.name}")
```

## Полезные команды

### Полная миграция (все за раз)

```bash
python manage.py migrate_old_data
```

### Только категории

```bash
python manage.py migrate_old_data --categories-only
```

### Только товары

```bash
python manage.py migrate_old_data --products-only
```

### Только изображения

```bash
python manage.py migrate_old_data --images-only
```

### С кастомным путем к SQL

```bash
python manage.py migrate_old_data --sql-file="путь/к/файлу.sql"
```

## Ручная настройка категорий для товаров

Если нужно вручную добавить товар в несколько категорий:

```python
from shop.models import Category, Product

product = Product.objects.get(article='VM2056')

# Получаем категории
cat1 = Category.objects.get(name='Букеты из роз')
cat2 = Category.objects.get(name='Розы')
cat3 = Category.objects.get(name='День рождения')

# Добавляем категории
product.categories.set([cat1, cat2, cat3])

# Устанавливаем основную категорию
product.category = cat1
product.save()

# Или добавляем одну категорию
product.categories.add(cat3)
```

## Частые проблемы и решения

### Проблема: Товары не появляются в нужных категориях

**Решение**: Проверьте маппинг старых VM категорий на новые Django категории. Возможно, названия не совпадают.

```python
# Посмотреть товары без категорий
Product.objects.filter(category=None)

# Посмотреть товары без дополнительных категорий
Product.objects.filter(categories__isnull=True)
```

### Проблема: Изображения не отображаются

**Решение**:
1. Проверьте, что файлы скопированы в `backend/media/products/`
2. Проверьте настройки в `settings.py`:

```python
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

3. В `urls.py` добавьте:

```python
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # ... ваши URL
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

### Проблема: Дубликаты товаров

**Решение**: Скрипт использует `article` как уникальный ключ. Проверьте дубликаты:

```python
from django.db.models import Count

# Найти дубликаты артикулов
duplicates = Product.objects.values('article').annotate(
    count=Count('id')
).filter(count__gt=1)

for dup in duplicates:
    print(f"Артикул {dup['article']}: {dup['count']} товаров")
    products = Product.objects.filter(article=dup['article'])
    for p in products:
        print(f"  - {p.id}: {p.title}")
```

## Дополнительная настройка

### Обновление цен

Цены в миграции устанавливаются в 0. Если в SQL есть таблица с ценами, добавьте её парсинг в скрипт или обновите вручную.

### Установка приоритета категорий

Можно установить порядок сортировки категорий:

```python
for i, cat in enumerate(Category.objects.filter(parent=None).order_by('name')):
    cat.sort_order = i
    cat.save()
```

### Оптимизация запросов

При выборке товаров с категориями используйте:

```python
# Вместо
products = Product.objects.all()
for p in products:
    print(p.category.name)  # N+1 запрос!

# Используйте
products = Product.objects.select_related('category').prefetch_related('categories')
for p in products:
    print(p.category.name)  # Один запрос!
```

## Следующие шаги

1. ✅ Миграция категорий
2. ✅ Миграция товаров
3. ✅ Миграция изображений
4. ⬜ Копирование файлов изображений
5. ⬜ Проверка данных в Django Admin
6. ⬜ Настройка фронтенда для отображения товаров
7. ⬜ Настройка фильтров по категориям
8. ⬜ Тестирование функционала каталога
