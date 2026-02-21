# Быстрый старт миграции

## 1. Применить миграцию БД

```bash
cd "G:\Мой диск\buket\backend"
python manage.py migrate
```

## 2. Создать категории

```bash
python manage.py create_categories
```

Результат:
- Создаст ~60 категорий с иерархией
- Свадебная флористика → Букет невесты, и т.д.
- Букеты по цветам → Розы, Тюльпаны, и т.д.

## 3. Мигрировать товары из старой базы

```bash
python manage.py migrate_old_data --products-only
```

Результат:
- Загрузит ~160 товаров из VirtueMart
- Свяжет каждый товар с несколькими категориями
- Установит артикулы и описания

## 4. Добавить изображения

```bash
python manage.py migrate_old_data --images-only
```

Результат:
- Создаст записи для ~1600 изображений
- Установит правильный порядок отображения

## 5. Скопировать файлы изображений

**Важно**: Файлы нужно скопировать вручную!

Из:
```
<старый_сайт>/images/product/data/*.jpg
```

В:
```
G:\Мой диск\buket\backend\media\products\
```

## 6. Проверить результат

```bash
python manage.py shell
```

```python
from shop.models import Category, Product, ProductImage

print(f"Категорий: {Category.objects.count()}")
print(f"Товаров: {Product.objects.count()}")
print(f"Изображений: {ProductImage.objects.count()}")

# Пример товара с категориями
p = Product.objects.first()
print(f"\n{p.title}")
print(f"Категории: {[c.name for c in p.categories.all()]}")
```

## Полная миграция одной командой

```bash
python manage.py create_categories
python manage.py migrate_old_data
```

## Что делать, если что-то пошло не так

### Пересоздать категории

```bash
python manage.py create_categories --clear
```

### Удалить все товары

```python
from shop.models import Product
Product.objects.all().delete()
```

### Удалить все изображения

```python
from shop.models import ProductImage
ProductImage.objects.all().delete()
```

## Дальнейшая работа

- Зайдите в Django Admin: http://localhost:8000/admin
- Проверьте категории и товары
- Настройте фронтенд для отображения каталога
- Добавьте фильтры по категориям
