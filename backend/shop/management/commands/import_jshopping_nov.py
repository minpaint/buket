from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
import shutil
from typing import Dict, Iterable, List, Optional, Tuple

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from shop.management.commands.import_joomla_catalog import int_or_zero, iter_table_rows, parse_price, safe_str
from shop.models import Category, Product, ProductImage, Store


@dataclass
class ImportStats:
    categories_created: int = 0
    products_created: int = 0
    product_images_created: int = 0
    image_files_copied: int = 0
    images_missing: int = 0
    products_without_image: int = 0


def normalize_name(name: str) -> str:
    return " ".join((name or "").strip().split())


def choose_category_name(row: Dict[str, object]) -> str:
    candidates = [
        safe_str(row.get("name_ru-RU")),
        safe_str(row.get("name_en-GB")),
        safe_str(row.get("alias_ru-RU")),
        safe_str(row.get("alias_en-GB")),
    ]
    for c in candidates:
        c = normalize_name(c)
        if c:
            return c[:100]
    return ""


def choose_product_title(row: Dict[str, object], product_id: int) -> str:
    candidates = [
        safe_str(row.get("name_ru-RU")),
        safe_str(row.get("name_en-GB")),
        safe_str(row.get("alias_ru-RU")),
        safe_str(row.get("alias_en-GB")),
    ]
    for c in candidates:
        c = normalize_name(c)
        if c:
            return c[:100]
    return f"Product {product_id}"


def choose_product_description(row: Dict[str, object]) -> str:
    candidates = [
        safe_str(row.get("description_ru-RU")),
        safe_str(row.get("short_description_ru-RU")),
        safe_str(row.get("description_en-GB")),
        safe_str(row.get("short_description_en-GB")),
    ]
    for c in candidates:
        c = c.strip()
        if c:
            return c
    return ""


def choose_article(row: Dict[str, object], product_id: int) -> str:
    candidates = [
        safe_str(row.get("product_ean")).strip(),
        safe_str(row.get("manufacturer_code")).strip(),
        safe_str(row.get("extra_field_1")).strip(),
    ]
    for c in candidates:
        if c:
            return c[:64]
    return f"JS{product_id}"


def build_product_category_map(rows: Iterable[Dict[str, object]]) -> Dict[int, List[Tuple[int, int]]]:
    by_product: Dict[int, List[Tuple[int, int]]] = defaultdict(list)
    for row in rows:
        product_id = int_or_zero(row.get("product_id"))
        category_id = int_or_zero(row.get("category_id"))
        ordering = int_or_zero(row.get("product_ordering"))
        if product_id > 0 and category_id > 0:
            by_product[product_id].append((ordering, category_id))

    for product_id in by_product:
        by_product[product_id].sort(key=lambda x: (x[0], x[1]))
    return by_product


def build_product_images_map(rows: Iterable[Dict[str, object]]) -> Dict[int, List[Tuple[int, str]]]:
    by_product: Dict[int, List[Tuple[int, str]]] = defaultdict(list)
    for row in rows:
        product_id = int_or_zero(row.get("product_id"))
        image_name = safe_str(row.get("image_name")).strip()
        ordering = int_or_zero(row.get("ordering"))
        if product_id > 0 and image_name:
            by_product[product_id].append((ordering, image_name))

    for product_id in by_product:
        by_product[product_id].sort(key=lambda x: (x[0], x[1]))
    return by_product


def build_image_index(old_root: Path) -> Dict[str, List[Path]]:
    candidate_dirs = [
        old_root / "components" / "com_jshopping" / "files" / "img_products",
        old_root / "images" / "product" / "data",
        old_root / "image" / "data",
    ]
    index: Dict[str, List[Path]] = defaultdict(list)

    for directory in candidate_dirs:
        if not directory.exists():
            continue
        for p in directory.rglob("*"):
            if not p.is_file():
                continue
            key = p.name.lower()
            index[key].append(p)
            if key.startswith("full_"):
                index[key[5:]].append(p)
            if key.startswith("thumb_"):
                index[key[6:]].append(p)
    return index


def resolve_legacy_image(image_name: str, image_index: Dict[str, List[Path]]) -> Optional[Path]:
    key = image_name.strip().lower()
    if not key:
        return None
    candidates = image_index.get(key, [])
    if not candidates:
        return None
    preferred = sorted(
        candidates,
        key=lambda p: (
            0 if "img_products" in p.as_posix() else 1,
            0 if p.name.lower().startswith("full_") else 1,
            len(p.as_posix()),
        ),
    )
    return preferred[0]


def unique_dest_name(existing: set, base_name: str) -> str:
    if base_name not in existing:
        existing.add(base_name)
        return base_name

    stem = Path(base_name).stem
    suffix = Path(base_name).suffix
    idx = 2
    while True:
        candidate = f"{stem}_{idx}{suffix}"
        if candidate not in existing:
            existing.add(candidate)
            return candidate
        idx += 1


def create_unique_category(name: str, parent: Optional[Category], sort_order: int) -> Category:
    base = name[:100]
    candidate = base
    idx = 2
    while Category.objects.filter(name=candidate, parent=parent).exists():
        suffix = f" ({idx})"
        candidate = f"{base[: 100 - len(suffix)]}{suffix}"
        idx += 1
    return Category.objects.create(
        name=candidate,
        parent=parent,
        sort_order=max(0, sort_order),
    )


class Command(BaseCommand):
    help = "Full import from JShopping (buketby_nov.sql): categories -> products -> prices -> images."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dump",
            default="old/buketby_nov.sql",
            help="Path to SQL dump file.",
        )
        parser.add_argument(
            "--old-root",
            default="old/public_html",
            help="Path to old Joomla public_html directory.",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing ProductImage, Product and Category records before import.",
        )
        parser.add_argument(
            "--assign-active-stores",
            action="store_true",
            help="Assign all imported products to all active stores.",
        )
        parser.add_argument(
            "--backend-base-url",
            default="http://127.0.0.1:3002",
            help="Base URL for Product.image fallback link.",
        )

    def handle(self, *args, **options):
        dump_path = Path(options["dump"]).resolve()
        old_root = Path(options["old_root"]).resolve()
        clear_existing = bool(options["clear"])
        assign_stores = bool(options["assign_active_stores"])
        backend_base_url = safe_str(options["backend_base_url"]).rstrip("/")

        if not dump_path.exists():
            raise CommandError(f"Dump file not found: {dump_path}")
        if not old_root.exists():
            raise CommandError(f"Old root directory not found: {old_root}")

        media_products_dir = Path(settings.MEDIA_ROOT) / "products"
        media_products_dir.mkdir(parents=True, exist_ok=True)
        fallback_url = f"{backend_base_url}/static/legacy-old/image/no_image.jpg"

        self.stdout.write("Loading JShopping tables from SQL dump...")
        category_rows = list(iter_table_rows(dump_path, "wzx3q_jshopping_categories"))
        product_rows = list(iter_table_rows(dump_path, "wzx3q_jshopping_products"))
        product_row_by_legacy_id = {int_or_zero(r.get("product_id")): r for r in product_rows}
        product_to_cat_rows = list(iter_table_rows(dump_path, "wzx3q_jshopping_products_to_categories"))
        product_image_rows = list(iter_table_rows(dump_path, "wzx3q_jshopping_products_images"))

        product_categories = build_product_category_map(product_to_cat_rows)
        product_images = build_product_images_map(product_image_rows)
        image_index = build_image_index(old_root)

        stats = ImportStats()
        used_dest_names: set = set()

        with transaction.atomic():
            if clear_existing:
                ProductImage.objects.all().delete()
                Product.objects.all().delete()
                Category.objects.all().delete()

            category_by_legacy_id: Dict[int, Category] = {}

            # First pass: root categories
            roots = [
                row for row in category_rows
                if int_or_zero(row.get("category_parent_id")) in (0, -1)
                and int_or_zero(row.get("category_publish")) == 1
            ]
            roots.sort(key=lambda r: (int_or_zero(r.get("ordering")), int_or_zero(r.get("category_id"))))

            for row in roots:
                legacy_id = int_or_zero(row.get("category_id"))
                name = choose_category_name(row)
                if legacy_id <= 0 or not name:
                    continue
                category = create_unique_category(name, None, int_or_zero(row.get("ordering")))
                category_by_legacy_id[legacy_id] = category
                stats.categories_created += 1

            # Remaining categories until all possible parents are resolved
            unresolved = [
                row for row in category_rows
                if int_or_zero(row.get("category_publish")) == 1
                and int_or_zero(row.get("category_id")) not in category_by_legacy_id
            ]
            prev_unresolved_count = -1
            while unresolved and prev_unresolved_count != len(unresolved):
                prev_unresolved_count = len(unresolved)
                next_round = []
                for row in unresolved:
                    legacy_id = int_or_zero(row.get("category_id"))
                    parent_legacy_id = int_or_zero(row.get("category_parent_id"))
                    name = choose_category_name(row)
                    if legacy_id <= 0 or not name:
                        continue
                    parent = category_by_legacy_id.get(parent_legacy_id)
                    if parent_legacy_id not in (0, -1) and parent is None:
                        next_round.append(row)
                        continue

                    category = create_unique_category(name, parent, int_or_zero(row.get("ordering")))
                    category_by_legacy_id[legacy_id] = category
                    stats.categories_created += 1
                unresolved = next_round

            if unresolved:
                self.stdout.write(self.style.WARNING(f"Unresolved categories skipped: {len(unresolved)}"))

            products_by_legacy_id: Dict[int, Product] = {}

            for row in product_rows:
                product_id = int_or_zero(row.get("product_id"))
                is_published = int_or_zero(row.get("product_publish")) == 1
                if product_id <= 0 or not is_published:
                    continue

                title = choose_product_title(row, product_id)
                description = choose_product_description(row)
                price = parse_price(row.get("product_price"))
                if price < Decimal("0.00"):
                    price = Decimal("0.00")
                article = choose_article(row, product_id)

                cat_refs = product_categories.get(product_id, [])
                cat_list = [category_by_legacy_id[cid] for _, cid in cat_refs if cid in category_by_legacy_id]
                main_category = cat_list[0] if cat_list else None

                product = Product.objects.create(
                    title=title,
                    article=article,
                    description=description,
                    price=price,
                    category=main_category,
                    image=fallback_url,
                    is_published=True,
                )
                if cat_list:
                    # Preserve order, remove duplicates by id.
                    deduped = list(dict.fromkeys(cat_list))
                    product.categories.set(deduped)

                products_by_legacy_id[product_id] = product
                stats.products_created += 1

            for product_id, product in products_by_legacy_id.items():
                raw_images = product_images.get(product_id, [])
                if not raw_images:
                    main_fallback = safe_str((product_row_by_legacy_id.get(product_id) or {}).get("image")).strip()
                    if main_fallback:
                        raw_images = [(0, main_fallback)]

                created_any_for_product = False
                for sort_order, image_name in raw_images:
                    legacy_path = resolve_legacy_image(image_name, image_index)
                    if legacy_path is None:
                        stats.images_missing += 1
                        continue

                    suffix = Path(legacy_path.name).suffix
                    clean_article = "".join(ch for ch in (product.article or "") if ch.isalnum() or ch in ("-", "_"))
                    clean_article = clean_article or f"p{product.id}"
                    base_dest = f"{clean_article}_{int(sort_order):02d}{suffix}"
                    dest_name = unique_dest_name(used_dest_names, base_dest)
                    dest_path = media_products_dir / dest_name

                    if not dest_path.exists():
                        shutil.copy2(legacy_path, dest_path)
                        stats.image_files_copied += 1

                    rel_media_path = f"products/{dest_name}"
                    ProductImage.objects.create(
                        product=product,
                        image=rel_media_path,
                        sort_order=max(0, int(sort_order)),
                    )
                    stats.product_images_created += 1

                    if not product.uploaded_image:
                        product.uploaded_image = rel_media_path
                        product.image = f"{backend_base_url}/media/{rel_media_path}"
                        product.save(update_fields=["uploaded_image", "image"])
                    created_any_for_product = True

                if not created_any_for_product and not product.uploaded_image:
                    stats.products_without_image += 1

            if assign_stores:
                active_stores = list(Store.objects.filter(is_active=True))
                if active_stores:
                    for p in products_by_legacy_id.values():
                        p.stores.set(active_stores)

        self.stdout.write(self.style.SUCCESS("JShopping import completed."))
        self.stdout.write(f"Categories created: {stats.categories_created}")
        self.stdout.write(f"Products created: {stats.products_created}")
        self.stdout.write(f"ProductImage created: {stats.product_images_created}")
        self.stdout.write(f"Image files copied: {stats.image_files_copied}")
        self.stdout.write(f"Missing legacy images: {stats.images_missing}")
        self.stdout.write(f"Products without images: {stats.products_without_image}")
