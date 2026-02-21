"""
Django management command для миграции данных из старой VirtueMart базы.

Использование:
    python manage.py migrate_old_data

Опции:
    --categories-only : Только создать категории
    --products-only : Только создать товары
    --images-only : Только создать записи изображений
"""

import re
import os
from django.core.management.base import BaseCommand
from shop.models import Category, Product, ProductImage


class Command(BaseCommand):
    help = 'Миграция данных из старой VirtueMart базы данных'

    def add_arguments(self, parser):
        parser.add_argument(
            '--categories-only',
            action='store_true',
            help='Создать только категории',
        )
        parser.add_argument(
            '--products-only',
            action='store_true',
            help='Создать только товары',
        )
        parser.add_argument(
            '--images-only',
            action='store_true',
            help='Создать только записи изображений',
        )
        parser.add_argument(
            '--sql-file',
            type=str,
            default=None,
            help='Путь к SQL файлу (по умолчанию: old/buketby_newbd.sql)',
        )

    def handle(self, *args, **options):
        # Определяем путь к SQL файлу
        if options['sql_file']:
            sql_file = options['sql_file']
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            sql_file = os.path.join(base_dir, '..', 'old', 'buketby_newbd.sql')

        if not os.path.exists(sql_file):
            self.stdout.write(self.style.ERROR(f'Файл не найден: {sql_file}'))
            return

        self.stdout.write(self.style.SUCCESS(f'Загрузка SQL файла: {sql_file}'))

        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()

        self.stdout.write(self.style.SUCCESS(f'Загружено {len(sql_content)} байт'))

        # Определяем, что нужно мигрировать
        do_categories = options['categories_only'] or not (options['products_only'] or options['images_only'])
        do_products = options['products_only'] or not (options['categories_only'] or options['images_only'])
        do_images = options['images_only'] or not (options['categories_only'] or options['products_only'])

        vm_to_django_categories = {}
        vm_to_django_products = {}

        if do_categories:
            vm_to_django_categories = self.migrate_categories(sql_content)

        if do_products:
            if not vm_to_django_categories:
                # Загружаем существующие категории
                vm_to_django_categories = self.load_existing_categories(sql_content)

            vm_to_django_products = self.migrate_products(sql_content, vm_to_django_categories)

        if do_images:
            if not vm_to_django_products:
                # Загружаем существующие товары
                vm_to_django_products = self.load_existing_products(sql_content)

            self.migrate_images(sql_content, vm_to_django_products)

        # Итоговая статистика
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('[OK] Миграция завершена!'))
        self.stdout.write(self.style.SUCCESS(f'  Категорий в БД: {Category.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'  Товаров в БД: {Product.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'  Изображений в БД: {ProductImage.objects.count()}'))
        self.stdout.write(self.style.SUCCESS('='*60))

    def parse_sql_insert(self, table_name, sql_content):
        """Парсит INSERT INTO запросы из SQL дампа."""
        pattern = rf"INSERT INTO `{table_name}`.*?VALUES\s*(.*?);"
        matches = re.findall(pattern, sql_content, re.DOTALL | re.IGNORECASE)

        all_rows = []
        for match in matches:
            rows_pattern = r"\(([^)]+)\)"
            rows = re.findall(rows_pattern, match)

            for row in rows:
                values = []
                current_value = ''
                in_quotes = False
                escape_next = False

                for char in row + ',':
                    if escape_next:
                        current_value += char
                        escape_next = False
                        continue

                    if char == '\\':
                        escape_next = True
                        current_value += char
                        continue

                    if char == "'" and not escape_next:
                        in_quotes = not in_quotes
                        current_value += char
                        continue

                    if char == ',' and not in_quotes:
                        value = current_value.strip()
                        if value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        if value.upper() == 'NULL' or value == '':
                            value = None
                        else:
                            value = value.replace("\\'", "'").replace("\\\\", "\\")
                        values.append(value)
                        current_value = ''
                    else:
                        current_value += char

                if values:
                    all_rows.append(tuple(values))

        return all_rows

    def migrate_categories(self, sql_content):
        """Мигрирует категории из VirtueMart."""
        self.stdout.write(self.style.WARNING('\n[CATEGORIES] Миграция категорий...'))

        categories_ru = self.parse_sql_insert('wzx3q_virtuemart_categories_ru_ru', sql_content)

        vm_categories = {}
        for row in categories_ru:
            vm_id = int(row[0])
            name = row[1]
            description = row[2] if len(row) > 2 else ''
            vm_categories[vm_id] = {'name': name, 'description': description}

        self.stdout.write(f'  Найдено категорий: {len(vm_categories)}')

        category_relations = self.parse_sql_insert('wzx3q_virtuemart_category_categories', sql_content)

        hierarchy = {}
        for row in category_relations:
            child_id = int(row[0])
            parent_id = int(row[1])
            hierarchy[child_id] = parent_id

        self.stdout.write(f'  Найдено связей: {len(hierarchy)}')

        vm_to_django = {}

        # Создаем категории без parent
        for vm_id, data in vm_categories.items():
            category, created = Category.objects.get_or_create(
                name=data['name'],
                parent=None,
                defaults={'sort_order': 0}
            )
            vm_to_django[vm_id] = category
            if created:
                self.stdout.write(self.style.SUCCESS(f'  + Создана: {data["name"]}'))

        # Устанавливаем parent
        for child_vm_id, parent_vm_id in hierarchy.items():
            if child_vm_id in vm_to_django and parent_vm_id in vm_to_django:
                child_category = vm_to_django[child_vm_id]
                parent_category = vm_to_django[parent_vm_id]

                if child_category.parent != parent_category:
                    child_category.parent = parent_category
                    child_category.save()
                    self.stdout.write(f'  -> {child_category.name} -> {parent_category.name}')

        return vm_to_django

    def load_existing_categories(self, sql_content):
        """Загружает маппинг существующих категорий."""
        categories_ru = self.parse_sql_insert('wzx3q_virtuemart_categories_ru_ru', sql_content)

        vm_to_django = {}
        for row in categories_ru:
            vm_id = int(row[0])
            name = row[1]

            try:
                category = Category.objects.get(name=name)
                vm_to_django[vm_id] = category
            except Category.DoesNotExist:
                pass

        return vm_to_django

    def migrate_products(self, sql_content, vm_to_django_categories):
        """Мигрирует товары из VirtueMart."""
        self.stdout.write(self.style.WARNING('\n[PRODUCTS] Миграция товаров...'))

        products_ru = self.parse_sql_insert('wzx3q_virtuemart_products_ru_ru', sql_content)

        vm_products = {}
        for row in products_ru:
            vm_id = int(row[0])
            name = row[1]
            description = row[3] if len(row) > 3 else ''
            vm_products[vm_id] = {'name': name, 'description': description}

        self.stdout.write(f'  Найдено товаров: {len(vm_products)}')

        products_main = self.parse_sql_insert('wzx3q_virtuemart_products', sql_content)

        for row in products_main:
            vm_id = int(row[0])
            sku = row[3] if len(row) > 3 and row[3] else ''

            if vm_id in vm_products:
                vm_products[vm_id]['sku'] = sku

        product_categories = self.parse_sql_insert('wzx3q_virtuemart_product_categories', sql_content)

        product_to_categories = {}
        for row in product_categories:
            product_id = int(row[1])
            category_id = int(row[2])

            if product_id not in product_to_categories:
                product_to_categories[product_id] = []
            product_to_categories[product_id].append(category_id)

        vm_to_django_products = {}

        for vm_id, data in vm_products.items():
            main_category = None
            all_categories = []

            if vm_id in product_to_categories:
                category_ids = product_to_categories[vm_id]
                for cat_id in category_ids:
                    if cat_id in vm_to_django_categories:
                        cat = vm_to_django_categories[cat_id]
                        all_categories.append(cat)
                        if not main_category:
                            main_category = cat

            article = data.get('sku', f'VM{vm_id}')

            product, created = Product.objects.get_or_create(
                article=article,
                defaults={
                    'title': data['name'][:100],
                    'description': data.get('description', '')[:5000],
                    'price': 0.00,
                    'category': main_category,
                    'is_published': True,
                }
            )

            # Устанавливаем все категории
            if all_categories:
                product.categories.set(all_categories)

            vm_to_django_products[vm_id] = product

            if created:
                cat_names = ', '.join([c.name for c in all_categories]) if all_categories else 'нет'
                self.stdout.write(self.style.SUCCESS(
                    f'  + {data["name"][:40]} [{cat_names}]'
                ))

        return vm_to_django_products

    def load_existing_products(self, sql_content):
        """Загружает маппинг существующих товаров."""
        products_ru = self.parse_sql_insert('wzx3q_virtuemart_products_ru_ru', sql_content)
        products_main = self.parse_sql_insert('wzx3q_virtuemart_products', sql_content)

        vm_skus = {}
        for row in products_main:
            vm_id = int(row[0])
            sku = row[3] if len(row) > 3 and row[3] else f'VM{vm_id}'
            vm_skus[vm_id] = sku

        vm_to_django = {}
        for vm_id, sku in vm_skus.items():
            try:
                product = Product.objects.get(article=sku)
                vm_to_django[vm_id] = product
            except Product.DoesNotExist:
                pass

        return vm_to_django

    def migrate_images(self, sql_content, vm_to_django_products):
        """Мигрирует изображения товаров."""
        self.stdout.write(self.style.WARNING('\n[IMAGES]  Миграция изображений...'))

        medias = self.parse_sql_insert('wzx3q_virtuemart_medias', sql_content)

        vm_medias = {}
        for row in medias:
            media_id = int(row[0])
            file_url = row[8] if len(row) > 8 else ''
            file_type = row[7] if len(row) > 7 else ''

            if file_type == 'product' and file_url:
                vm_medias[media_id] = file_url

        self.stdout.write(f'  Найдено медиафайлов: {len(vm_medias)}')

        product_medias = self.parse_sql_insert('wzx3q_virtuemart_product_medias', sql_content)

        for row in product_medias:
            product_id = int(row[1])
            media_id = int(row[2])
            ordering = int(row[3]) if len(row) > 3 else 0

            if product_id in vm_to_django_products and media_id in vm_medias:
                product = vm_to_django_products[product_id]
                image_url = vm_medias[media_id]

                # Преобразуем путь: images/product/data/1.jpg -> products/1.jpg
                image_path = image_url.replace('images/product/data/', 'products/')

                # Проверяем, существует ли уже такое изображение
                if not ProductImage.objects.filter(product=product, sort_order=ordering).exists():
                    product_image = ProductImage.objects.create(
                        product=product,
                        sort_order=ordering,
                        image=image_path
                    )
                    self.stdout.write(f'  + {product.title[:30]}: {image_path}')
