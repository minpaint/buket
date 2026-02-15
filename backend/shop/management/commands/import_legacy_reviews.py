from django.core.management.base import BaseCommand

from shop.models import Review


class Command(BaseCommand):
    help = "Import initial reviews from https://buket.by/otzyvy.html"

    def handle(self, *args, **options):
        source = "https://buket.by/otzyvy.html"

        rows = [
            {
                "author": "Пресс-служба",
                "company": "ЗАО Банк ВТБ (Беларусь)",
                "rating": 5,
                "sort_order": 10,
                "text": (
                    "На протяжении долгих лет банк покупает цветочную продукцию в салоне-магазине "
                    "«Планета цветов». Отмечены качественная работа, своевременное изготовление "
                    "флористических работ, свежесть цветов, широкий ассортимент и удобный график."
                ),
                "image": "https://buket.by/images/stories/vtb.jpg",
            },
            {
                "author": "Редакция",
                "company": "РУП «Белорусское телеграфное агентство» (БЕЛТА)",
                "rating": 5,
                "sort_order": 20,
                "text": (
                    "Салон-магазин «Планета цветов» зарекомендовал себя как надежный поставщик. "
                    "Отмечены персональный подбор и заказ цветов, широкий ассортимент, высокий "
                    "уровень обслуживания, свежесть цветов и профессиональный подход к композициям."
                ),
                "image": "https://buket.by/images/belta.jpg",
            },
            {
                "author": "Корпоративный клиент",
                "company": "Постоянный клиент buket.by",
                "rating": 5,
                "sort_order": 30,
                "text": (
                    "Компания много лет заказывает цветочные композиции в «Планете цветов». "
                    "Подчеркиваются разнообразный ассортимент, высокая художественная ценность "
                    "работ, удобная доставка по Минску, оперативность и профессионализм сотрудников."
                ),
                "image": "https://buket.by/images/stories/new.jpg",
            },
            {
                "author": "Администрация",
                "company": "ИООО «ЛУКОИЛ Белоруссия»",
                "rating": 5,
                "sort_order": 40,
                "text": (
                    "Организация на протяжении многих лет заказывает букеты и композиции. "
                    "Отмечены стабильное качество, выполнение срочных заказов в срок, "
                    "свежесть цветов и конструктивное сотрудничество."
                ),
                "image": "https://buket.by/images/stories/lukoil.jpg",
            },
            {
                "author": "Руководство компании",
                "company": "ООО «Росчерк»",
                "rating": 5,
                "sort_order": 50,
                "text": (
                    "Компания выражает благодарность коллективу «Планета цветов» за "
                    "плодотворное сотрудничество, качественные поставки цветочной продукции "
                    "и индивидуальный подход к каждому букету."
                ),
                "image": "https://buket.by/images/stories/roscherk.ru.png",
            },
        ]

        created = 0
        updated = 0
        for row in rows:
            obj, is_created = Review.objects.update_or_create(
                company=row["company"],
                defaults={
                    "author": row["author"],
                    "text": row["text"],
                    "rating": row["rating"],
                    "sort_order": row["sort_order"],
                    "image": row["image"],
                    "source_url": source,
                    "is_published": True,
                },
            )
            if is_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS("Reviews import finished"))
        self.stdout.write(f"Created: {created}")
        self.stdout.write(f"Updated: {updated}")

