"""
Проверяет наличие файлов изображений товаров.
"""

import os
from django.core.management.base import BaseCommand
from django.conf import settings
from shop.models import Product, ProductImage


class Command(BaseCommand):
    help = 'Проверяет наличие файлов изображений товаров'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\nПроверка изображений товаров...\n'))

        total_images = ProductImage.objects.count()
        products_with_images = Product.objects.filter(images__isnull=False).distinct().count()

        self.stdout.write(f'Всего товаров: {Product.objects.count()}')
        self.stdout.write(f'Товаров с изображениями: {products_with_images}')
        self.stdout.write(f'Всего записей изображений: {total_images}')

        # Проверяем наличие файлов
        missing_files = []
        existing_files = 0

        self.stdout.write('\nПроверка наличия файлов...')

        for img in ProductImage.objects.all():
            file_path = os.path.join(settings.MEDIA_ROOT, img.image.name)
            if os.path.exists(file_path):
                existing_files += 1
            else:
                missing_files.append(img.image.name)

        self.stdout.write(self.style.SUCCESS(f'\nСуществующих файлов: {existing_files}'))

        if missing_files:
            self.stdout.write(self.style.WARNING(f'Отсутствующих файлов: {len(missing_files)}'))

            if len(missing_files) <= 20:
                self.stdout.write('\nОтсутствующие файлы:')
                for f in missing_files:
                    self.stdout.write(f'  - {f}')
            else:
                self.stdout.write('\nПервые 20 отсутствующих файлов:')
                for f in missing_files[:20]:
                    self.stdout.write(f'  - {f}')
        else:
            self.stdout.write(self.style.SUCCESS('Все файлы найдены!'))

        # Примеры товаров с изображениями
        self.stdout.write('\n' + '='*60)
        self.stdout.write('Примеры товаров с изображениями:\n')

        for p in Product.objects.filter(images__isnull=False).distinct()[:5]:
            self.stdout.write(self.style.SUCCESS(f'\n{p.title[:50]}:'))
            for img in p.images.all()[:3]:
                file_path = os.path.join(settings.MEDIA_ROOT, img.image.name)
                exists = os.path.exists(file_path)
                status = '[OK]' if exists else '[MISSING]'
                self.stdout.write(f'  {status} {img.image.name}')

        self.stdout.write('\n' + '='*60)
