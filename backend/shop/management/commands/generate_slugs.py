"""
Генерирует slugи для Category, FlowerTag и Product (если пустой).
Использует python-slugify для транслитерации кириллицы.
"""
from django.core.management.base import BaseCommand
from shop.models import Category, FlowerTag, Product


def make_unique_slug(base_slug, existing_slugs):
    slug = base_slug
    counter = 2
    while slug in existing_slugs:
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


def get_slugify():
    try:
        from slugify import slugify
        return slugify
    except ImportError:
        from django.utils.text import slugify
        return slugify


class Command(BaseCommand):
    help = 'Генерирует slugи для Category, FlowerTag и Product (пустых)'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Не сохранять, только показать')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        slugify = get_slugify()

        # ── Category ──
        self.stdout.write('=== Category ===')
        existing = set(Category.objects.exclude(slug='').values_list('slug', flat=True))
        updated = 0
        for cat in Category.objects.all():
            if cat.slug:
                continue
            base = slugify(cat.name)
            if not base:
                base = f'category-{cat.id}'
            slug = make_unique_slug(base, existing)
            existing.add(slug)
            if dry_run:
                self.stdout.write(f'  [dry] Category #{cat.id} "{cat.name}" -> {slug}')
            else:
                cat.slug = slug
                cat.save(update_fields=['slug'])
            updated += 1
        self.stdout.write(self.style.SUCCESS(f'Category: обновлено {updated}'))

        # ── FlowerTag ──
        self.stdout.write('=== FlowerTag ===')
        existing = set(FlowerTag.objects.exclude(slug='').values_list('slug', flat=True))
        updated = 0
        for tag in FlowerTag.objects.all():
            if tag.slug:
                continue
            base = slugify(tag.name)
            if not base:
                base = f'flower-{tag.id}'
            slug = make_unique_slug(base, existing)
            existing.add(slug)
            if dry_run:
                self.stdout.write(f'  [dry] FlowerTag #{tag.id} "{tag.name}" -> {slug}')
            else:
                tag.slug = slug
                tag.save(update_fields=['slug'])
            updated += 1
        self.stdout.write(self.style.SUCCESS(f'FlowerTag: обновлено {updated}'))

        # ── Product (только пустые) ──
        self.stdout.write('=== Product (пустые slug) ===')
        existing = set(Product.objects.exclude(slug='').values_list('slug', flat=True))
        updated = 0
        for product in Product.objects.filter(slug=''):
            base = slugify(product.title)
            if not base:
                base = f'product-{product.id}'
            slug = make_unique_slug(base, existing)
            existing.add(slug)
            if dry_run:
                self.stdout.write(f'  [dry] Product #{product.id} "{product.title}" -> {slug}')
            else:
                product.slug = slug
                product.save(update_fields=['slug'])
            updated += 1
        self.stdout.write(self.style.SUCCESS(f'Product: обновлено {updated}'))
