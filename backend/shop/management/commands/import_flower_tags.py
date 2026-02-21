"""
Импорт тегов состава букета из bukety_tablica.xlsx.

Структура Excel (строка заголовков в строке 1):
  Колонка 1 (idx 0): ID
  Колонка 2 (idx 1): Артикул
  Колонка 3 (idx 2): Название
  Колонка 4 (idx 3): Описание (состав — цветы через запятую)
  Колонка 5 (idx 4): Цена

Что делает:
  1. Читает Excel-файл
  2. Парсит 4-ю колонку — список цветов через запятую
  3. Создаёт FlowerTag объекты (get_or_create по имени)
  4. Матчит товар по артикулу (колонка 2)
  5. Привязывает теги к товару (product.flower_tags.set)

Запуск:
  python manage.py import_flower_tags
  python manage.py import_flower_tags --dry-run
  python manage.py import_flower_tags --excel path/to/file.xlsx
"""

import os
from django.core.management.base import BaseCommand
from shop.models import Product, FlowerTag


DEFAULT_EXCEL = os.path.join(
    os.path.dirname(__file__), '..', '..', '..', '..', 'scripts', 'bukety_tablica.xlsx'
)


class Command(BaseCommand):
    help = 'Импортирует теги состава (цветы) из Excel-файла и привязывает к товарам'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Только показать что будет сделано, не сохранять',
        )
        parser.add_argument(
            '--excel',
            type=str,
            default=None,
            help=f'Путь к Excel-файлу (по умолчанию: {DEFAULT_EXCEL})',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Очистить все flower_tags у товаров перед импортом',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        clear = options['clear']
        excel_path = os.path.normpath(options['excel'] or DEFAULT_EXCEL)

        if dry_run:
            self.stdout.write(self.style.WARNING('[DRY RUN] Изменения НЕ будут сохранены\n'))

        # --- Загрузка Excel ---
        try:
            import openpyxl
        except ImportError:
            self.stderr.write(self.style.ERROR(
                'Не установлен openpyxl. Выполните: pip install openpyxl'
            ))
            return

        if not os.path.exists(excel_path):
            self.stderr.write(self.style.ERROR(f'Файл не найден: {excel_path}'))
            return

        self.stdout.write(f'Читаю Excel: {excel_path}')
        wb = openpyxl.load_workbook(excel_path)
        ws = wb.active

        # --- Парсинг строк ---
        rows_data = []  # [(article, [tag_name, ...]), ...]
        all_tag_names = set()
        skipped = 0

        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or row[1] is None:
                continue
            article = str(row[1]).strip()
            composition_raw = row[3] if len(row) > 3 else None
            if not composition_raw:
                skipped += 1
                continue

            # Парсим состав: "Букет невесты, Розы, Тюльпаны" → ["Букет невесты", "Розы", "Тюльпаны"]
            tags = [t.strip() for t in str(composition_raw).split(',') if t.strip()]
            if not tags:
                skipped += 1
                continue

            rows_data.append((article, tags))
            all_tag_names.update(tags)

        self.stdout.write(f'  Строк с составом: {len(rows_data)}')
        self.stdout.write(f'  Строк без состава (пропущено): {skipped}')
        self.stdout.write(f'  Уникальных тегов в файле: {len(all_tag_names)}')

        if dry_run:
            self.stdout.write('\nТеги, которые будут созданы:')
            for name in sorted(all_tag_names):
                exists = FlowerTag.objects.filter(name=name).exists()
                status = '(уже есть)' if exists else '(новый)'
                self.stdout.write(f'  {name} {status}')
            self.stdout.write('\nПримеры привязок (первые 10):')
            for article, tags in rows_data[:10]:
                product = Product.objects.filter(article=article).first()
                status = f'-> {product.title[:50]}' if product else '-> ТОВАР НЕ НАЙДЕН'
                self.stdout.write(f'  {article}: {", ".join(tags[:5])} {status}')
            self.stdout.write(self.style.WARNING('\n[DRY RUN] Ничего не сохранено.'))
            return

        # --- Очистка (если запрошена) ---
        if clear:
            self.stdout.write('\nОчистка flower_tags у всех товаров...')
            for p in Product.objects.all():
                p.flower_tags.clear()
            self.stdout.write('  Очищено.')

        # --- Создание тегов ---
        self.stdout.write('\nСоздание тегов...')
        tag_cache = {}  # name -> FlowerTag instance
        created_count = 0
        for name in sorted(all_tag_names):
            tag, created = FlowerTag.objects.get_or_create(name=name)
            tag_cache[name] = tag
            if created:
                created_count += 1

        self.stdout.write(f'  Создано новых тегов: {created_count}')
        self.stdout.write(f'  Всего тегов в БД: {FlowerTag.objects.count()}')

        # --- Привязка к товарам ---
        self.stdout.write('\nПривязка тегов к товарам...')
        matched = 0
        not_found = 0
        not_found_articles = []

        for article, tag_names in rows_data:
            product = Product.objects.filter(article=article).first()
            if not product:
                not_found += 1
                not_found_articles.append(article)
                continue

            tags_to_set = [tag_cache[name] for name in tag_names if name in tag_cache]
            product.flower_tags.set(tags_to_set)
            matched += 1

        self.stdout.write(self.style.SUCCESS(f'  Товаров с тегами: {matched}'))
        if not_found:
            self.stdout.write(self.style.WARNING(f'  Товаров не найдено по артикулу: {not_found}'))
            for art in not_found_articles[:10]:
                self.stdout.write(f'    {art}')
            if len(not_found_articles) > 10:
                self.stdout.write(f'    ... и ещё {len(not_found_articles) - 10}')

        # --- Итог ---
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('ГОТОВО!'))
        self.stdout.write(f'  Тегов (FlowerTag):     {FlowerTag.objects.count()}')
        self.stdout.write(f'  Товаров с тегами:      {Product.objects.filter(flower_tags__isnull=False).distinct().count()}')
        self.stdout.write(f'  Товаров без тегов:     {Product.objects.filter(flower_tags__isnull=True).count()}')

        # Топ тегов
        self.stdout.write('\nТоп тегов по количеству товаров:')
        from django.db.models import Count
        top = (FlowerTag.objects
               .annotate(n=Count('products'))
               .filter(n__gt=0)
               .order_by('-n')[:15])
        for tag in top:
            self.stdout.write(f'  {tag.name}: {tag.n}')
        self.stdout.write('=' * 60)
