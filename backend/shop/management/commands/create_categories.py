"""
Django management command для создания иерархии категорий.

Использование:
    python manage.py create_categories
"""

from django.core.management.base import BaseCommand
from shop.models import Category


CATEGORIES_HIERARCHY = [
    {
        "name": "Свадебная флористика",
        "count": 10,
        "children": [
            {"name": "Букет невесты", "count": 19},
            {"name": "Поздравительные букеты", "count": 42},
            {"name": "Оформление свадьбы", "count": 3},
            {"name": "Бутоньерки", "count": 4}
        ]
    },
    {
        "name": "Букеты на праздники",
        "count": 11,
        "children": [
            {"name": "День рождения", "count": 60},
            {"name": "Свадьба", "count": 36},
            {"name": "День св. Валентина", "count": 47},
            {"name": "23 февраля", "count": 10},
            {"name": "8 марта", "count": 46},
            {"name": "1 сентября", "count": 17},
            {"name": "День учителя", "count": 35},
            {"name": "День матери", "count": 37},
            {"name": "Траурные букеты", "count": 1}
        ]
    },
    {
        "name": "Букеты из роз",
        "count": 28
    },
    {
        "name": "Букеты по цветам",
        "count": 16,
        "children": [
            {"name": "Розы", "count": 57},
            {"name": "Альстромерия", "count": 25},
            {"name": "Амариллис (гипеаструм)", "count": 2},
            {"name": "Антуриум", "count": 2},
            {"name": "Гвоздика", "count": 8},
            {"name": "Гербера", "count": 14},
            {"name": "Гиацинт", "count": 2},
            {"name": "Гортензия", "count": 6},
            {"name": "Ирисы", "count": 1},
            {"name": "Каллы", "count": 4},
            {"name": "Лилия", "count": 3},
            {"name": "Мимоза (акация)", "count": 2},
            {"name": "Орхидея", "count": 25},
            {"name": "Пионы", "count": 3},
            {"name": "Подсолнухи", "count": 2},
            {"name": "Ранункулюс, анемон", "count": 9},
            {"name": "Стрелиция", "count": 2},
            {"name": "Тюльпаны", "count": 8},
            {"name": "Фрезия", "count": 7},
            {"name": "Хризантема", "count": 11},
            {"name": "Эустома (лизиантус)", "count": 16}
        ]
    },
    {
        "name": "Цветочные композиции",
        "count": 5,
        "children": [
            {"name": "Поздравительные композиции", "count": 21},
            {"name": "Рождественские и новогодние композиции", "count": 0},
            {"name": "Композиции для официальных мероприятий", "count": 3},
            {"name": "Тематические композиции", "count": 2}
        ]
    },
    {
        "name": "Цветы в коробках",
        "count": 20
    },
    {
        "name": "Сердце из роз и других цветов",
        "count": 5
    },
    {
        "name": "Букеты для мужчин",
        "count": 10
    },
    {
        "name": "Букеты с фруктами",
        "count": 2
    },
    {
        "name": "Корзины с цветами",
        "count": 6,
        "children": [
            {"name": "Маленькие", "count": 1},
            {"name": "Средние", "count": 4},
            {"name": "Большие", "count": 6}
        ]
    },
    {
        "name": "Зимние букеты",
        "count": 4
    },
    {
        "name": "Горшечные растения",
        "count": 0
    },
    {
        "name": "Букет из сухоцветов",
        "count": None
    }
]


class Command(BaseCommand):
    help = 'Создает иерархию категорий из предопределенной структуры'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Удалить все существующие категории перед созданием',
        )

    def handle(self, *args, **options):
        if options['clear']:
            count = Category.objects.count()
            Category.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Удалено категорий: {count}'))

        self.stdout.write(self.style.SUCCESS('\nСоздание категорий...'))

        categories_map = {}
        sort_order = 0

        for cat_data in CATEGORIES_HIERARCHY:
            parent_name = cat_data['name']

            parent, created = Category.objects.get_or_create(
                name=parent_name,
                parent=None,
                defaults={'sort_order': sort_order}
            )
            categories_map[parent_name] = parent
            sort_order += 1

            if created:
                self.stdout.write(self.style.SUCCESS(f'  + {parent_name}'))
            else:
                self.stdout.write(f'  - {parent_name} (уже существует)')

            if 'children' in cat_data:
                child_order = 0
                for child_data in cat_data['children']:
                    child_name = child_data['name']

                    child, created = Category.objects.get_or_create(
                        name=child_name,
                        parent=parent,
                        defaults={'sort_order': child_order}
                    )
                    categories_map[child_name] = child
                    child_order += 1

                    if created:
                        self.stdout.write(self.style.SUCCESS(f'    + {child_name}'))
                    else:
                        self.stdout.write(f'    - {child_name} (уже существует)')

        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS(f'Создано категорий: {len(categories_map)}'))
        self.stdout.write(self.style.SUCCESS(f'Всего в БД: {Category.objects.count()}'))
        self.stdout.write(self.style.SUCCESS('='*60))
