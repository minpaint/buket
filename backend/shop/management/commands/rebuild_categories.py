# -*- coding: utf-8 -*-
import json
from django.core.management.base import BaseCommand
from shop.models import Category, Product

CATEGORIES_JSON = [
    {
        "name": "Свадебная флористика",
        "children": [
            {"name": "Букет невесты"},
            {"name": "Поздравительные букеты"},
            {"name": "Оформление свадьбы"},
            {"name": "Бутоньерки"},
        ],
    },
    {
        "name": "Букеты на праздники",
        "children": [
            {"name": "День рождения"},
            {"name": "Свадьба"},
            {"name": "День св. Валентина"},
            {"name": "23 февраля"},
            {"name": "8 марта"},
            {"name": "1 сентября"},
            {"name": "День учителя"},
            {"name": "День матери"},
            {"name": "Траурные букеты"},
        ],
    },
    {"name": "Букеты из роз"},
    {
        "name": "Букеты по цветам",
        "children": [
            {"name": "Розы"},
            {"name": "Альстромерия"},
            {"name": "Амариллис (гипеаструм)"},
            {"name": "Антуриум"},
            {"name": "Гвоздика"},
            {"name": "Гербера"},
            {"name": "Гиацинт"},
            {"name": "Гортензия"},
            {"name": "Ирисы"},
            {"name": "Каллы"},
            {"name": "Лилия"},
            {"name": "Мимоза (акация)"},
            {"name": "Орхидея"},
            {"name": "Пионы"},
            {"name": "Подсолнухи"},
            {"name": "Ранункулюс, анемон"},
            {"name": "Стрелиция"},
            {"name": "Тюльпаны"},
            {"name": "Фрезия"},
            {"name": "Хризантема"},
            {"name": "Эустома (лизиантус)"},
        ],
    },
    {
        "name": "Цветочные композиции",
        "children": [
            {"name": "Поздравительные композиции"},
            {"name": "Рождественские и новогодние композиции"},
            {"name": "Композиции для официальных мероприятий"},
            {"name": "Тематические композиции"},
        ],
    },
    {"name": "Цветы в коробках"},
    {"name": "Сердце из роз и других цветов"},
    {"name": "Букеты для мужчин"},
    {"name": "Букеты с фруктами"},
    {
        "name": "Корзины с цветами",
        "children": [
            {"name": "Маленькие"},
            {"name": "Средние"},
            {"name": "Большие"},
        ],
    },
    {"name": "Зимние букеты"},
    {"name": "Горшечные растения"},
    {"name": "Букет из сухоцветов"},
]


class Command(BaseCommand):
    help = "Rebuild categories from JSON hierarchy"

    def handle(self, *args, **options):
        # Clear product category references first
        Product.objects.all().update(category=None)
        self.stdout.write("Cleared all product category references")

        # Delete all existing categories
        old_count = Category.objects.count()
        Category.objects.all().delete()
        self.stdout.write(f"Deleted {old_count} old categories")

        # Create new categories
        created = 0
        for i, cat_data in enumerate(CATEGORIES_JSON):
            parent = Category.objects.create(
                name=cat_data["name"],
                sort_order=i * 10,
            )
            created += 1
            self.stdout.write(f"  + {parent.name}")

            for j, child_data in enumerate(cat_data.get("children", [])):
                child = Category.objects.create(
                    name=child_data["name"],
                    parent=parent,
                    sort_order=j * 10,
                )
                created += 1
                self.stdout.write(f"    +-- {child.name}")

        self.stdout.write(f"\nCreated {created} categories total")
