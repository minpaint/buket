from django.core.management.base import BaseCommand

from shop.models import HeroBanner


class Command(BaseCommand):
    help = "Create or update demo hero campaigns for the homepage."

    def handle(self, *args, **options):
        base_url = "http://127.0.0.1:3001"
        campaigns = [
            {
                "name": "Сегодня в наличии",
                "title": "Сегодня в наличии",
                "caption": "ONLINE витрина - собранные сегодня букеты прямо из холодильника",
                "button_text": "Смотреть витрину",
                "button_url": "/#today-showcase",
                "desktop_image": "https://images.pexels.com/photos/931177/pexels-photo-931177.jpeg?auto=compress&cs=tinysrgb&w=1920&h=980&fit=crop",
                "mobile_image": "https://images.pexels.com/photos/931177/pexels-photo-931177.jpeg?auto=compress&cs=tinysrgb&w=900&h=1200&fit=crop",
                "is_active": True,
                "starts_on": None,
                "ends_on": None,
                "sort_order": 40,
            },
            {
                "name": "14 февраля",
                "title": "14 февраля",
                "caption": "Коллекция ко Дню святого Валентина",
                "button_text": "Выбрать букет",
                "button_url": "/#today-showcase",
                "desktop_image": f"{base_url}/hero/valentine-desktop.jpg",
                "mobile_image": f"{base_url}/hero/valentine-mobile.jpg",
                "is_active": True,
                "starts_on": None,
                "ends_on": None,
                "sort_order": 10,
            },
            {
                "name": "23 февраля",
                "title": "23 февраля",
                "caption": "Сдержанные и стильные букеты к 23 февраля",
                "button_text": "Смотреть подборку",
                "button_url": "/#today-showcase",
                "desktop_image": f"{base_url}/hero/feb23-desktop.jpg",
                "mobile_image": f"{base_url}/hero/feb23-mobile.jpg",
                "is_active": True,
                "starts_on": None,
                "ends_on": None,
                "sort_order": 20,
            },
            {
                "name": "8 марта",
                "title": "8 марта",
                "caption": "Праздничные композиции к Международному женскому дню",
                "button_text": "Открыть витрину",
                "button_url": "/#today-showcase",
                "desktop_image": f"{base_url}/hero/march8-desktop.jpg",
                "mobile_image": f"{base_url}/hero/march8-mobile.jpg",
                "is_active": True,
                "starts_on": None,
                "ends_on": None,
                "sort_order": 30,
            },
        ]

        created = 0
        updated = 0
        for campaign in campaigns:
            _, was_created = HeroBanner.objects.update_or_create(
                name=campaign["name"], defaults=campaign
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Hero campaigns seeded: created={created}, updated={updated}, total={len(campaigns)}"
            )
        )
