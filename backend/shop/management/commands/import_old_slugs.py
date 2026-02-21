"""
Импортирует slugи для Product из старой БД buketby_nov.sql.
Поле alias_ru-RU -> Product.slug, матчинг по product_ean -> article.
Для товаров без alias генерирует slug из title через python-slugify.
"""
import os
import re
from django.core.management.base import BaseCommand
from shop.models import Product

DEFAULT_SQL = os.path.join(
    os.path.dirname(__file__), '..', '..', '..', '..', 'old', 'buketby_nov.sql'
)


def parse_fields(row_str):
    """Парсит строку VALUES (...) в список значений (тот же парсер что в import_flower_tags_sql)."""
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
                cur.append(ch); cur.append(s[i + 1]); i += 2; continue
            elif ch == "'":
                if i + 1 < L and s[i + 1] == "'":
                    cur.append("'"); i += 2; continue
                in_q = False; cur.append(ch)
            else:
                cur.append(ch)
        else:
            if ch == "'":
                in_q = True; cur.append(ch)
            elif ch == '(' and not in_q:
                dep += 1; cur.append(ch)
            elif ch == ')' and dep > 0 and not in_q:
                dep -= 1; cur.append(ch)
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
    """Итератор по строкам INSERT INTO `table_name`."""
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
                    in_q = True; pos += 1; continue
                if sql[pos] == "'" and in_q:
                    in_q = False; pos += 1; continue
                pos += 1
            if pos >= L or (sql[pos] == ';' and not in_q):
                break
            pos += 1
            depth = 0; in_q2 = False; start = pos
            while pos < L:
                ch = sql[pos]
                if in_q2:
                    if ch == '\\' and pos + 1 < L:
                        pos += 2; continue
                    elif ch == "'":
                        in_q2 = False
                elif ch == "'":
                    in_q2 = True
                elif ch == '(':
                    depth += 1
                elif ch == ')':
                    if depth == 0:
                        yield parse_fields(sql[start:pos])
                        pos += 1
                        break
                    depth -= 1
                pos += 1
        start_pos = val_idx + 1


def get_col_indices(sql, table_name):
    """Возвращает словарь {имя_колонки: индекс} из CREATE TABLE."""
    m = re.search(
        rf'CREATE TABLE `{re.escape(table_name)}`\s*\((.*?)\)\s*ENGINE',
        sql, re.DOTALL | re.IGNORECASE
    )
    if not m:
        return {}
    cols = {}
    for i, line in enumerate(m.group(1).splitlines()):
        line = line.strip()
        cm = re.match(r'`([^`]+)`\s+', line)
        if cm:
            cols[cm.group(1)] = len(cols)
    return cols


def make_unique_slug(base_slug, existing_slugs):
    slug = base_slug
    counter = 2
    while slug in existing_slugs:
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


class Command(BaseCommand):
    help = 'Импортирует slugи Product из старой БД (buketby_nov.sql)'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--sql', default=None)

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        sql_path = os.path.normpath(options['sql'] or DEFAULT_SQL)

        if not os.path.exists(sql_path):
            self.stderr.write(f'SQL файл не найден: {sql_path}')
            return

        self.stdout.write(f'Читаю: {sql_path}')
        with open(sql_path, encoding='utf-8', errors='replace') as f:
            sql = f.read()

        # Индексы колонок
        cols = get_col_indices(sql, 'wzx3q_jshopping_products')
        if not cols:
            self.stderr.write('CREATE TABLE wzx3q_jshopping_products не найдена')
            return

        idx_ean = cols.get('product_ean')
        idx_alias = cols.get('alias_ru-RU')

        if idx_ean is None or idx_alias is None:
            self.stderr.write(f'Не найдены колонки. Доступные: {list(cols.keys())[:15]}')
            return

        self.stdout.write(f'product_ean[{idx_ean}], alias_ru-RU[{idx_alias}]')

        # Строим словарь article -> alias
        article_to_alias = {}
        row_count = 0
        for row in iter_insert_rows(sql, 'wzx3q_jshopping_products'):
            row_count += 1
            if len(row) > max(idx_ean, idx_alias):
                ean = str(row[idx_ean] or '').strip()
                alias = str(row[idx_alias] or '').strip()
                if ean:
                    article_to_alias[ean] = alias

        self.stdout.write(f'Строк: {row_count}, пар артикул->alias: {len(article_to_alias)}')

        # Slugify функция
        try:
            from slugify import slugify as py_slugify
        except ImportError:
            from django.utils.text import slugify as py_slugify

        # Заполняем Product.slug
        existing_slugs = set(Product.objects.exclude(slug='').values_list('slug', flat=True))
        updated = skipped = generated = 0

        for product in Product.objects.all():
            alias = article_to_alias.get(product.article, '').strip()
            if alias:
                base_slug = alias
            else:
                base_slug = py_slugify(product.title)
                generated += 1
            if not base_slug:
                base_slug = f'product-{product.id}'

            # Если slug уже установлен правильно — пропускаем
            if product.slug == base_slug or (product.slug and product.slug.startswith(base_slug)):
                if product.slug not in existing_slugs:
                    existing_slugs.add(product.slug)
                skipped += 1
                continue

            slug = make_unique_slug(base_slug, existing_slugs)
            existing_slugs.add(slug)

            if dry_run:
                self.stdout.write(f'  [dry] #{product.id} art={product.article!r} "{product.title}" -> {slug}')
            else:
                product.slug = slug
                product.save(update_fields=['slug'])
            updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'Готово. Обновлено: {updated}, пропущено: {skipped}, '
            f'из названия: {generated}'
        ))
        if dry_run:
            self.stdout.write('(dry-run)')
