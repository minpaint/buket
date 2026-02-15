from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from shop.management.commands.import_joomla_catalog import (
    first_by_key,
    int_or_zero,
    iter_table_rows,
    parse_price,
    safe_str,
)
from shop.models import Product


@dataclass
class SyncStats:
    updated: int = 0
    unchanged: int = 0
    mismatched_titles: int = 0
    with_article: int = 0
    with_non_zero_price: int = 0


class Command(BaseCommand):
    help = "Sync Product.article and Product.price from Joomla SQL dump to existing products."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dump",
            default="old/buketby_newbd.sql",
            help="Path to SQL dump file",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print stats without saving updates",
        )

    def handle(self, *args, **options):
        dump_path = Path(options["dump"]).resolve()
        dry_run = bool(options["dry_run"])
        if not dump_path.exists():
            raise CommandError(f"Dump file not found: {dump_path}")

        ru_by_id = {
            int(row["virtuemart_product_id"]): row
            for row in iter_table_rows(dump_path, "wzx3q_virtuemart_products_ru_ru")
        }
        price_by_product = first_by_key(
            iter_table_rows(dump_path, "wzx3q_virtuemart_product_prices"),
            "virtuemart_product_id",
        )

        old_rows: List[Tuple[str, str, object]] = []
        for row in iter_table_rows(dump_path, "wzx3q_virtuemart_products"):
            if int_or_zero(row.get("published")) != 1:
                continue
            product_id = int(row["virtuemart_product_id"])
            ru = ru_by_id.get(product_id, {})
            title = safe_str(ru.get("product_name")).strip() or safe_str(row.get("product_sku")).strip()
            if not title:
                title = f"Product {product_id}"
            title = title[:100]
            article = safe_str(row.get("product_sku")).strip()
            price = parse_price((price_by_product.get(product_id) or {}).get("product_price"))
            old_rows.append((title, article, price))

        db_by_title: Dict[str, List[Product]] = defaultdict(list)
        for p in Product.objects.order_by("id"):
            db_by_title[p.title].append(p)

        old_by_title: Dict[str, List[Tuple[str, object]]] = defaultdict(list)
        for title, article, price in old_rows:
            old_by_title[title].append((article, price))

        stats = SyncStats()
        to_update: List[Product] = []

        for title, old_items in old_by_title.items():
            db_items = db_by_title.get(title, [])
            if len(old_items) != len(db_items):
                stats.mismatched_titles += 1
                continue

            for product, (article, price) in zip(db_items, old_items):
                new_article = article
                new_price = price

                if new_article:
                    stats.with_article += 1
                if new_price and new_price != 0:
                    stats.with_non_zero_price += 1

                if product.article == new_article and product.price == new_price:
                    stats.unchanged += 1
                    continue

                product.article = new_article
                product.price = new_price
                to_update.append(product)
                stats.updated += 1

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run mode: no DB changes applied"))
        else:
            with transaction.atomic():
                Product.objects.bulk_update(to_update, ["article", "price"])

        self.stdout.write(self.style.SUCCESS("Sync finished"))
        self.stdout.write(f"Updated: {stats.updated}")
        self.stdout.write(f"Unchanged: {stats.unchanged}")
        self.stdout.write(f"Mismatched title groups: {stats.mismatched_titles}")
        self.stdout.write(f"Rows with article: {stats.with_article}")
        self.stdout.write(f"Rows with non-zero price: {stats.with_non_zero_price}")
