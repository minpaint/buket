"""
Импорт тегов состава букета из buketby_nov.sql (JShopping).

Источник данных — три таблицы:
  wzx3q_jshopping_products       : product_id, product_ean (артикул)
  wzx3q_jshopping_attr           : attr_id, name_ru-RU (название цветка)
  wzx3q_jshopping_products_attr2 : product_id, attr_id, addcount (количество — игнорируем)

Что делает:
  1. Читает SQL-файл
  2. Парсит таблицу attr -> dict {attr_id: flower_name}
  3. Парсит таблицу products -> dict {product_id: article}
  4. Парсит таблицу products_attr2 -> dict {product_id: [attr_id, ...]}
  5. Собирает: article -> [flower_name, ...]
  6. Создаёт/обновляет FlowerTag объекты (get_or_create)
  7. Привязывает теги к Product по артикулу (add — не заменяет, а дополняет)

Флаги:
  --dry-run   : только показать, не сохранять
  --replace   : заменить (set) теги вместо добавления (add)
  --sql       : путь к SQL-файлу (по умолчанию: old/buketby_nov.sql)

Запуск:
  python manage.py import_flower_tags_sql
  python manage.py import_flower_tags_sql --dry-run
  python manage.py import_flower_tags_sql --replace
"""

import os
import re
from django.core.management.base import BaseCommand
from shop.models import Product, FlowerTag


DEFAULT_SQL = os.path.join(
    os.path.dirname(__file__), '..', '..', '..', '..', 'old', 'buketby_nov.sql'
)


def parse_fields(row_str):
    """Парсит одну строку VALUES (...) в список значений."""
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
            elif ch == '(' and not in_q:
                dep += 1
                cur.append(ch)
            elif ch == ')' and dep > 0 and not in_q:
                dep -= 1
                cur.append(ch)
            elif ch == ',' and dep == 0 and not in_q:
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
    """Итератор по строкам INSERT INTO `table_name` VALUES (...)."""
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
            pos += 1
            if row_str.strip():
                yield parse_fields(row_str)
            while pos < L and sql[pos] in ' \t\r\n,':
                pos += 1
            if pos < L and sql[pos] == ';':
                break

        start_pos = pos + 1


def extract_attrs(sql):
    """
    Парсит wzx3q_jshopping_attr.
    Структура: attr_id, attr_ordering, attr_type, independent, allcats, cats,
               group, name_en-GB, description_en-GB, name_ru-RU, description_ru-RU
    Возвращает dict: attr_id (int) -> flower_name (str)
    """
    attrs = {}
    for fields in iter_insert_rows(sql, 'wzx3q_jshopping_attr'):
        if len(fields) >= 10:
            try:
                attr_id = int(fields[0])
                name_ru = (fields[9] or '').strip()
                if name_ru:
                    attrs[attr_id] = name_ru
            except (ValueError, TypeError):
                pass
    return attrs


def extract_products(sql):
    """
    Парсит wzx3q_jshopping_products — берём product_id и product_ean (артикул).
    Структура: product_id (0), parent_id (1), product_ean (2), ...
    Возвращает dict: product_id (int) -> article (str)
    """
    products = {}
    for fields in iter_insert_rows(sql, 'wzx3q_jshopping_products'):
        if len(fields) >= 3:
            try:
                product_id = int(fields[0])
                article = (fields[2] or '').strip()
                if article:
                    products[product_id] = article
            except (ValueError, TypeError):
                pass
    return products


def extract_product_attrs(sql):
    """
    Парсит wzx3q_jshopping_products_attr2.
    Структура: id (0), product_id (1), attr_id (2), attr_value_id (3),
               price_mod (4), addprice (5), addcount (6)
    Возвращает dict: product_id (int) -> set of attr_id (int)
    """
    result = {}
    for fields in iter_insert_rows(sql, 'wzx3q_jshopping_products_attr2'):
        if len(fields) >= 3:
            try:
                product_id = int(fields[1])
                attr_id = int(fields[2])
                if product_id not in result:
                    result[product_id] = set()
                result[product_id].add(attr_id)
            except (ValueError, TypeError):
                pass
    return result


class Command(BaseCommand):
    help = 'Импортирует теги состава (цветы) из buketby_nov.sql (JShopping) и добавляет к товарам'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Только показать что будет сделано, не сохранять',
        )
        parser.add_argument(
            '--replace',
            action='store_true',
            help='Заменить (set) теги у товаров вместо добавления (add)',
        )
        parser.add_argument(
            '--sql',
            type=str,
            default=None,
            help='Путь к SQL-файлу (по умолчанию: old/buketby_nov.sql)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        replace = options['replace']
        sql_path = os.path.normpath(options['sql'] or DEFAULT_SQL)

        if dry_run:
            self.stdout.write(self.style.WARNING('[DRY RUN] Изменения НЕ будут сохранены\n'))

        if not os.path.exists(sql_path):
            self.stderr.write(self.style.ERROR(f'Файл не найден: {sql_path}'))
            return

        # --- Загрузка SQL ---
        self.stdout.write(f'Читаю SQL: {sql_path}')
        with open(sql_path, 'r', encoding='utf-8', errors='replace') as f:
            sql = f.read()
        self.stdout.write(f'  Загружено байт: {len(sql):,}')

        # --- Парсинг ---
        self.stdout.write('\nПарсинг таблиц...')

        attrs = extract_attrs(sql)
        self.stdout.write(f'  Цветков в словаре (jshopping_attr): {len(attrs)}')

        products = extract_products(sql)
        self.stdout.write(f'  Товаров в SQL (jshopping_products): {len(products)}')

        product_attrs = extract_product_attrs(sql)
        self.stdout.write(f'  Товаров с составом (jshopping_products_attr2): {len(product_attrs)}')

        # --- Сборка: article -> [flower_name, ...] ---
        # product_id -> article -> [flower_names]
        article_to_flowers = {}
        unknown_attrs = set()

        for product_id, attr_ids in product_attrs.items():
            article = products.get(product_id)
            if not article:
                continue
            flower_names = []
            for attr_id in sorted(attr_ids):
                name = attrs.get(attr_id)
                if name:
                    flower_names.append(name)
                else:
                    unknown_attrs.add(attr_id)
            if flower_names:
                if article not in article_to_flowers:
                    article_to_flowers[article] = []
                article_to_flowers[article].extend(flower_names)

        all_flower_names = set()
        for names in article_to_flowers.values():
            all_flower_names.update(names)

        self.stdout.write(f'\n  Артикулов с составом из SQL: {len(article_to_flowers)}')
        self.stdout.write(f'  Уникальных цветков: {len(all_flower_names)}')
        if unknown_attrs:
            self.stdout.write(self.style.WARNING(
                f'  Неизвестных attr_id (нет в словаре): {len(unknown_attrs)}'
            ))

        if dry_run:
            self.stdout.write('\nЦветки из SQL словаря:')
            for name in sorted(all_flower_names):
                exists = FlowerTag.objects.filter(name=name).exists()
                status = '(уже есть)' if exists else '(НОВЫЙ)'
                self.stdout.write(f'  {name} {status}')

            self.stdout.write('\nПримеры привязок (первые 10):')
            for article, names in list(article_to_flowers.items())[:10]:
                product = Product.objects.filter(article=article).first()
                p_title = product.title[:45] if product else 'ТОВАР НЕ НАЙДЕН'
                self.stdout.write(f'  {article}: {", ".join(names[:6])}')
                self.stdout.write(f'    -> {p_title}')
            self.stdout.write(self.style.WARNING('\n[DRY RUN] Ничего не сохранено.'))
            return

        # --- Создание тегов ---
        self.stdout.write('\nСоздание/поиск FlowerTag...')
        tag_cache = {}
        created_count = 0
        for name in sorted(all_flower_names):
            tag, created = FlowerTag.objects.get_or_create(name=name)
            tag_cache[name] = tag
            if created:
                created_count += 1
        self.stdout.write(f'  Создано новых тегов: {created_count}')
        self.stdout.write(f'  Всего FlowerTag в БД: {FlowerTag.objects.count()}')

        # --- Привязка к товарам ---
        self.stdout.write('\nПривязка тегов к товарам...')
        matched = 0
        not_found = []

        for article, flower_names in article_to_flowers.items():
            product = Product.objects.filter(article=article).first()
            if not product:
                not_found.append(article)
                continue

            tags_to_add = [tag_cache[n] for n in flower_names if n in tag_cache]
            if replace:
                product.flower_tags.set(tags_to_add)
            else:
                product.flower_tags.add(*tags_to_add)
            matched += 1

        self.stdout.write(self.style.SUCCESS(f'  Товаров обновлено: {matched}'))
        if not_found:
            self.stdout.write(self.style.WARNING(
                f'  Артикулов из SQL не найдено в БД: {len(not_found)}'
            ))
            for art in not_found[:10]:
                self.stdout.write(f'    {art}')
            if len(not_found) > 10:
                self.stdout.write(f'    ... и ещё {len(not_found) - 10}')

        # --- Итог ---
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('ГОТОВО!'))
        self.stdout.write(f'  FlowerTag всего:       {FlowerTag.objects.count()}')
        self.stdout.write(f'  Товаров с тегами:      {Product.objects.filter(flower_tags__isnull=False).distinct().count()}')
        self.stdout.write(f'  Товаров без тегов:     {Product.objects.filter(flower_tags__isnull=True).count()}')

        self.stdout.write('\nТоп тегов по количеству товаров:')
        from django.db.models import Count
        top = (FlowerTag.objects
               .annotate(n=Count('products'))
               .filter(n__gt=0)
               .order_by('-n')[:20])
        for tag in top:
            self.stdout.write(f'  {tag.name}: {tag.n}')
        self.stdout.write('=' * 60)
