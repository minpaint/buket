"""
Полный правильный реимпорт из VirtueMart SQL дампа.

Что делает:
1. Читает все категории VM с их ID и названиями
2. Читает иерархию категорий VM
3. Читает все товары VM (ru_ru)
4. Читает привязки товар->категории VM
5. Читает изображения VM
6. Очищает существующие товары и изображения (категории оставляет)
7. Создаёт товары с правильными привязками к категориям

Маппинг старых VM-категорий на новые Django-категории делается по названию.
Если названия не совпадают — выводит список несовпадений.
"""

import re
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from shop.models import Category, Product, ProductImage, Store


SQL_FILE = os.path.join(
    os.path.dirname(__file__), '..', '..', '..', '..', 'old', 'buketby_newbd.sql'
)

EXCEL_FILE = os.path.join(
    os.path.dirname(__file__), '..', '..', '..', '..', 'bukety_tablica.xlsx'
)

# Ручной маппинг: старое название VM -> новое название Django
# Добавьте сюда если что-то не совпадёт по названию
CATEGORY_NAME_MAP = {
    # Старые VM названия -> Новые Django названия
    'Цветы на свадьбу':             'Свадебная флористика',
    'Свадебная флористика':         'Свадебная флористика',
    'Букеты невесты':               'Букет невесты',
    'Букет невесты':                'Букет невесты',
    'Бутоньерки для жениха':        'Бутоньерки',
    'Бутоньерки':                   'Бутоньерки',
    'Букеты для детей':             'Поздравительные букеты',
    'Поздравительные букеты':       'Поздравительные букеты',
    'Оформление свадьбы':           'Оформление свадьбы',
    'Букеты на праздники':          'Букеты на праздники',
    'Букеты на День рождения':      'День рождения',
    'День рождения':                'День рождения',
    'Свадьба':                      'Свадьба',
    'Букеты на Св. Валентина':      'День св. Валентина',
    'Букеты на св. Валентина':      'День св. Валентина',
    'День св. Валентина':           'День св. Валентина',
    'Букеты на 23 февраля':         '23 февраля',
    '23 февраля':                   '23 февраля',
    'Букеты на 8 марта':            '8 марта',
    '8 марта':                      '8 марта',
    '1 сентября':                   '1 сентября',
    'День учителя':                 'День учителя',
    'День матери':                  'День матери',
    'Траурные букеты':              'Траурные букеты',
    'Букеты на проф.праздник':      'Букеты на праздники',
    'Букеты на проф. праздник':     'Букеты на праздники',
    'Букеты из роз':                'Букеты из роз',
    'Букеты по цветам':             'Букеты по цветам',
    'Розы':                         'Розы',
    'Тюльпаны':                     'Тюльпаны',
    'Лилии':                        'Лилия',
    'Лилия':                        'Лилия',
    'Хризантемы':                   'Хризантема',
    'Хризантема':                   'Хризантема',
    'Герберы':                      'Гербера',
    'Гербера':                      'Гербера',
    'Гвоздики':                     'Гвоздика',
    'Гвоздика':                     'Гвоздика',
    'Ирисы':                        'Ирисы',
    'Орхидеи':                      'Орхидея',
    'Орхидея':                      'Орхидея',
    'Мимозы':                       'Мимоза (акация)',
    'Мимоза (акация)':              'Мимоза (акация)',
    'Альстромерия':                 'Альстромерия',
    'Амариллис (гипеаструм)':       'Амариллис (гипеаструм)',
    'Антуриум':                     'Антуриум',
    'Гиацинт':                      'Гиацинт',
    'Гортензия':                    'Гортензия',
    'Каллы':                        'Каллы',
    'Пионы':                        'Пионы',
    'Подсолнухи':                   'Подсолнухи',
    'Ранункулюс, анемон':           'Ранункулюс, анемон',
    'Стрелиция':                    'Стрелиция',
    'Фрезия':                       'Фрезия',
    'Фрезии':                       'Фрезия',
    'Эустома (лизиантус)':          'Эустома (лизиантус)',
    'Цветочные композиции':         'Цветочные композиции',
    'Поздравительные композиции':   'Поздравительные композиции',
    'Рождественские и новогодние композиции': 'Рождественские и новогодние композиции',
    'Новогодние композиции':        'Рождественские и новогодние композиции',
    'Композиции для официальных мероприятий': 'Композиции для официальных мероприятий',
    'Тематические композиции':      'Тематические композиции',
    'Цветы в коробках':             'Цветы в коробках',
    'Сердце из роз и других цветов':'Сердце из роз и других цветов',
    'Букеты для мужчин':            'Букеты для мужчин',
    'Букеты с фруктами':            'Букеты с фруктами',
    'Корзины с цветами':            'Корзины с цветами',
    'Маленькие':                    'Маленькие',
    'Средние':                      'Средние',
    'Большие':                      'Большие',
    'Зимние букеты':                'Зимние букеты',
    'Горшечные растения':           'Горшечные растения',
    'Букет из сухоцветов':          'Букет из сухоцветов',
    # Старые категории без аналога — игнорируем (скидки и т.п.)
    # 'Скидка 20%': None,
    # 'Скидка 10%': None,
    # 'Для всех': None,
}


def read_sql():
    path = os.path.normpath(SQL_FILE)
    # Файл в utf-8, errors='replace' на случай битых байт
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()


def parse_fields(row_str):
    """
    Универсальный парсер одной строки SQL VALUES: 'val1', 'val2', 123, NULL, ...
    Возвращает список значений (строки или None).
    Корректно обрабатывает строки с HTML, переносами строк, экранированными символами.
    """
    fields = []
    cur = []
    in_q = False
    dep = 0
    i = 0
    s = row_str + ','
    L = len(s)
    while i < L:
        ch = s[i]
        if in_q:
            if ch == '\\' and i + 1 < L:
                cur.append(ch)
                cur.append(s[i + 1])
                i += 2
                continue
            elif ch == "'":
                if i + 1 < L and s[i + 1] == "'":
                    cur.append("'")
                    i += 2
                    continue
                in_q = False
                cur.append(ch)
            else:
                cur.append(ch)
        else:
            if ch == "'":
                in_q = True
                cur.append(ch)
            elif ch == '(':
                dep += 1
                cur.append(ch)
            elif ch == ')' and dep > 0:
                dep -= 1
                cur.append(ch)
            elif ch == ',' and dep == 0:
                val = ''.join(cur).strip()
                if val.startswith("'") and val.endswith("'"):
                    val = val[1:-1].replace("\\'", "'").replace('\\\\', '\\')
                elif val.upper() == 'NULL':
                    val = None
                fields.append(val)
                cur = []
            else:
                cur.append(ch)
        i += 1
    return fields


def iter_insert_rows(sql, table_name):
    """
    Генератор: для каждой строки из INSERT INTO `table_name` ... VALUES (...), (...);
    Корректно обрабатывает значения со знаком ';' внутри строковых литералов.
    """
    search_str = f'INSERT INTO `{table_name}`'
    start_pos = 0
    L = len(sql)
    while True:
        idx = sql.find(search_str, start_pos)
        if idx < 0:
            break
        val_idx = sql.find('VALUES', idx)
        if val_idx < 0:
            break
        val_idx += len('VALUES')
        while val_idx < L and sql[val_idx] in ' \t\r\n':
            val_idx += 1

        pos = val_idx
        in_q = False
        while pos < L:
            # Ищем '(' начало строки значений
            while pos < L:
                if not in_q and sql[pos] == ';':
                    break
                if not in_q and sql[pos] == '(':
                    break
                if sql[pos] == "'" and not in_q:
                    in_q = True
                    pos += 1
                    continue
                if sql[pos] == "'" and in_q:
                    in_q = False
                    pos += 1
                    continue
                pos += 1
            if pos >= L or (sql[pos] == ';' and not in_q):
                break
            pos += 1  # пропускаем '('

            # Собираем содержимое строки значений
            depth = 0
            in_q2 = False
            start = pos
            while pos < L:
                ch = sql[pos]
                if in_q2:
                    if ch == '\\' and pos + 1 < L:
                        pos += 2
                        continue
                    elif ch == "'":
                        in_q2 = False
                elif ch == "'":
                    in_q2 = True
                elif ch == '(':
                    depth += 1
                elif ch == ')':
                    if depth == 0:
                        break
                    depth -= 1
                pos += 1
            row_str = sql[start:pos]
            pos += 1  # пропускаем ')'
            if row_str.strip():
                yield parse_fields(row_str)
            # Пропускаем пробелы и запятую до следующей строки
            while pos < L and sql[pos] in ' \t\r\n,':
                pos += 1
            if pos < L and sql[pos] == ';':
                break

        start_pos = pos + 1


def extract_vm_categories(sql):
    """Возвращает dict: vm_cat_id -> category_name"""
    cats = {}
    # Структура: virtuemart_category_id, category_name, category_description, ...
    for fields in iter_insert_rows(sql, 'wzx3q_virtuemart_categories_ru_ru'):
        if len(fields) >= 2:
            try:
                vm_id = int(fields[0])
                name = fields[1] or ''
                if name:
                    cats[vm_id] = name
            except (ValueError, TypeError):
                pass
    return cats


def extract_vm_product_categories(sql):
    """Возвращает dict: vm_product_id -> [vm_cat_id, ...]  отсортировано по ordering"""
    result = {}
    # Структура: id, virtuemart_product_id, virtuemart_category_id, ordering
    for fields in iter_insert_rows(sql, 'wzx3q_virtuemart_product_categories'):
        if len(fields) >= 4:
            try:
                pid = int(fields[1])
                cid = int(fields[2])
                ordering = int(fields[3]) if fields[3] is not None else 0
                if pid not in result:
                    result[pid] = []
                result[pid].append((ordering, cid))
            except (ValueError, TypeError):
                pass
    for pid in result:
        result[pid].sort()
        result[pid] = [cid for _, cid in result[pid]]
    return result


def extract_vm_products(sql):
    """
    Парсит wzx3q_virtuemart_products_ru_ru.
    Структура: virtuemart_product_id, product_s_desc, product_desc, product_name, ...
    Возвращает dict: vm_product_id -> {name, description}
    """
    products = {}
    for fields in iter_insert_rows(sql, 'wzx3q_virtuemart_products_ru_ru'):
        if len(fields) >= 4:
            try:
                vm_id = int(fields[0])
                short_desc = fields[1] or ''
                full_desc = fields[2] or ''
                name = fields[3] or ''
                name = name.strip()
                if name:
                    products[vm_id] = {
                        'name': name,
                        'description': short_desc.strip(),
                    }
            except (ValueError, TypeError):
                pass
    return products


def extract_vm_products_main(sql):
    """
    Парсит wzx3q_virtuemart_products: берём product_sku.
    Структура: virtuemart_product_id, virtuemart_vendor_id, product_parent_id, product_sku, ...
    Возвращает dict: vm_product_id -> {sku}
    """
    result = {}
    for fields in iter_insert_rows(sql, 'wzx3q_virtuemart_products'):
        if len(fields) >= 4:
            try:
                vm_id = int(fields[0])
                sku = fields[3] or ''
                result[vm_id] = {'sku': sku.strip()}
            except (ValueError, TypeError):
                pass
    return result


def extract_vm_prices(sql):
    """
    Парсит цены из wzx3q_virtuemart_product_prices.
    Структура: virtuemart_product_price_id, virtuemart_product_id, virtuemart_shoppergroup_id, product_price, ...
    Возвращает dict: vm_product_id -> price
    """
    prices = {}
    for fields in iter_insert_rows(sql, 'wzx3q_virtuemart_product_prices'):
        if len(fields) >= 4:
            try:
                pid = int(fields[1])
                price_str = fields[3] or '0'
                price = float(price_str)
                if pid not in prices:
                    prices[pid] = price
            except (ValueError, TypeError):
                pass
    return prices


def load_excel_prices():
    """
    Читает цены из Excel-файла bukety_tablica.xlsx.
    Структура: ID, Артикул, Название, Описание, Цена (напр. '2.70 BYN')
    Возвращает dict: article -> price (float)
    """
    try:
        import openpyxl
    except ImportError:
        return {}
    path = os.path.normpath(EXCEL_FILE)
    if not os.path.exists(path):
        return {}
    wb = openpyxl.load_workbook(path)
    ws = wb.active
    prices = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or row[1] is None:
            continue
        article = str(row[1]).strip()
        price_raw = row[4] if len(row) > 4 else None
        if price_raw is None:
            continue
        # Формат: '2.70 BYN' или просто '2.70' или число
        price_str = str(price_raw).replace('BYN', '').replace(',', '.').strip()
        try:
            price = float(price_str)
            prices[article] = price
        except (ValueError, TypeError):
            pass
    return prices


def extract_vm_medias(sql):
    """
    Структура: virtuemart_media_id, virtuemart_vendor_id, file_title, file_description,
               file_meta, file_class, file_mimetype, file_type, file_url, file_url_thumb, ...
    Возвращает dict: vm_media_id -> file_url (только type='product')
    """
    medias = {}
    for fields in iter_insert_rows(sql, 'wzx3q_virtuemart_medias'):
        if len(fields) >= 9:
            try:
                media_id = int(fields[0])
                file_type = fields[7] or ''
                file_url = fields[8] or ''
                if file_type == 'product' and file_url:
                    medias[media_id] = file_url
            except (ValueError, TypeError):
                pass
    return medias


def extract_vm_product_medias(sql):
    """
    Структура: id, virtuemart_product_id, virtuemart_media_id, ordering
    Возвращает dict: vm_product_id -> [(ordering, media_id), ...]  отсортировано
    """
    result = {}
    for fields in iter_insert_rows(sql, 'wzx3q_virtuemart_product_medias'):
        if len(fields) >= 4:
            try:
                pid = int(fields[1])
                mid = int(fields[2])
                ordering = int(fields[3]) if fields[3] is not None else 0
                if pid not in result:
                    result[pid] = []
                result[pid].append((ordering, mid))
            except (ValueError, TypeError):
                pass
    for pid in result:
        result[pid].sort()
    return result


class Command(BaseCommand):
    help = 'Полный реимпорт товаров из VirtueMart с правильными категориями и изображениями'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Только показать что будет сделано, не сохранять')

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        self.stdout.write('Загрузка SQL дампа...')
        sql = read_sql()
        self.stdout.write(f'  Загружено {len(sql):,} байт')

        # --- Парсинг ---
        self.stdout.write('\nПарсинг данных...')

        vm_cats = extract_vm_categories(sql)
        self.stdout.write(f'  VM категорий: {len(vm_cats)}')

        vm_prod_cats = extract_vm_product_categories(sql)
        self.stdout.write(f'  VM привязок товар->категория: {sum(len(v) for v in vm_prod_cats.values())}')

        vm_products_ru = extract_vm_products(sql)
        self.stdout.write(f'  VM товаров (ru): {len(vm_products_ru)}')

        vm_products_main = extract_vm_products_main(sql)
        self.stdout.write(f'  VM товаров (main): {len(vm_products_main)}')

        vm_prices = extract_vm_prices(sql)
        self.stdout.write(f'  VM цен (из SQL): {len(vm_prices)}')

        excel_prices = load_excel_prices()
        self.stdout.write(f'  Цен из Excel: {len(excel_prices)}')

        vm_medias = extract_vm_medias(sql)
        self.stdout.write(f'  VM медиафайлов (product): {len(vm_medias)}')

        vm_prod_medias = extract_vm_product_medias(sql)
        self.stdout.write(f'  VM привязок товар->медиа: {len(vm_prod_medias)}')

        # --- Строим маппинг VM cat_id -> Django Category по названиям ---
        self.stdout.write('\nСтроим маппинг категорий...')
        vm_to_django_cat = {}
        unmapped_vm_cats = []
        for vm_cat_id, vm_cat_name in vm_cats.items():
            mapped_name = CATEGORY_NAME_MAP.get(vm_cat_name, vm_cat_name)
            if mapped_name is None:
                continue
            cat = Category.objects.filter(name=mapped_name).first()
            if cat:
                vm_to_django_cat[vm_cat_id] = cat
            else:
                unmapped_vm_cats.append((vm_cat_id, vm_cat_name, mapped_name))

        self.stdout.write(f'  Маппингов категорий построено: {len(vm_to_django_cat)}')
        if unmapped_vm_cats:
            self.stdout.write(self.style.WARNING(f'  Не сматчено VM категорий: {len(unmapped_vm_cats)}'))
            for vm_cat_id, vm_cat_name, mapped_name in unmapped_vm_cats[:20]:
                self.stdout.write(f'    VM {vm_cat_id}: "{vm_cat_name}" -> "{mapped_name}" (не найдена)')

        if dry_run:
            self.stdout.write(self.style.WARNING('\n[DRY RUN] Ничего не сохранено.'))
            return

        # --- Очистка старых товаров и изображений ---
        self.stdout.write('\nОчистка старых данных...')
        old_images = ProductImage.objects.count()
        old_products = Product.objects.count()
        ProductImage.objects.all().delete()
        Product.objects.all().delete()
        self.stdout.write(f'  Удалено: {old_products} товаров, {old_images} изображений')

        # --- Создание товаров ---
        self.stdout.write('\nСоздание товаров...')
        vm_to_django_product = {}
        created = 0
        skipped = 0
        without_categories = 0

        for vm_id, data in vm_products_ru.items():
            name = data['name'].strip()
            if not name:
                skipped += 1
                continue

            main_info = vm_products_main.get(vm_id, {})
            sku = main_info.get('sku', '') or f'VM{vm_id}'
            # Сначала ищем цену из Excel по артикулу, потом из VM SQL
            price = excel_prices.get(sku, vm_prices.get(vm_id, 0))

            # Категории
            vm_cat_ids = vm_prod_cats.get(vm_id, [])
            django_cat_list = []
            for cid in vm_cat_ids:
                if cid in vm_to_django_cat:
                    django_cat_list.append(vm_to_django_cat[cid])

            main_cat = django_cat_list[0] if django_cat_list else None

            product = Product(
                title=name[:100],
                article=sku[:64],
                description=data.get('description', '')[:5000],
                price=price,
                category=main_cat,
                is_published=True,
            )
            product.save()

            if django_cat_list:
                product.categories.set(django_cat_list)
            else:
                without_categories += 1

            vm_to_django_product[vm_id] = product
            created += 1

        self.stdout.write(self.style.SUCCESS(f'  Создано товаров: {created}'))
        if skipped:
            self.stdout.write(self.style.WARNING(f'  Пропущено (нет названия): {skipped}'))
        self.stdout.write(f'  Товаров без категорий (как в источнике): {without_categories}')

        # --- Создание изображений ---
        self.stdout.write('\nСоздание изображений...')
        img_created = 0
        img_missing = 0

        for vm_prod_id, media_list in vm_prod_medias.items():
            if vm_prod_id not in vm_to_django_product:
                continue
            product = vm_to_django_product[vm_prod_id]

            for ordering, media_id in media_list:
                if media_id not in vm_medias:
                    continue
                old_url = vm_medias[media_id]
                # Преобразуем путь: images/product/data/1.jpg -> products/1.jpg
                filename = os.path.basename(old_url)
                new_path = f'products/{filename}'

                # Проверяем что файл есть
                full_path = os.path.join(settings.MEDIA_ROOT, new_path)
                if not os.path.exists(full_path):
                    img_missing += 1
                    continue

                ProductImage.objects.create(
                    product=product,
                    image=new_path,
                    sort_order=ordering,
                )
                img_created += 1

        self.stdout.write(self.style.SUCCESS(f'  Создано изображений: {img_created}'))
        if img_missing:
            self.stdout.write(self.style.WARNING(f'  Файлов не найдено: {img_missing}'))

        # --- Назначаем товары во все активные магазины ---
        active_stores = list(Store.objects.filter(is_active=True))
        if active_stores:
            for p in Product.objects.all():
                p.stores.set(active_stores)
            self.stdout.write(f'  Назначено магазинов (M2M) всем товарам: {len(active_stores)}')
        else:
            self.stdout.write(self.style.WARNING('  Активные магазины не найдены, M2M stores не назначены'))

        # --- Итог ---
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('ГОТОВО!'))
        self.stdout.write(f'  Категорий:    {Category.objects.count()}')
        self.stdout.write(f'  Товаров:      {Product.objects.count()}')
        self.stdout.write(f'  Изображений:  {ProductImage.objects.count()}')

        # Статистика по категориям
        self.stdout.write('\nТоваров по категориям:')
        from django.db.models import Count
        top = (Category.objects
               .annotate(n=Count('products'))
               .filter(n__gt=0)
               .order_by('-n')[:15])
        for cat in top:
            self.stdout.write(f'  {cat.name}: {cat.n}')
        self.stdout.write('=' * 60)
