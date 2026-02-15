from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
import shutil
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from shop.models import Category, Product


@dataclass
class ImportStats:
    categories_created: int = 0
    products_created: int = 0
    images_copied: int = 0
    images_missing: int = 0


class Command(BaseCommand):
    help = "Import categories and products from Joomla/VirtueMart SQL dump."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dump",
            default=r"G:\Мой диск\buket\old\buketby_newbd.sql",
            help="Path to SQL dump file",
        )
        parser.add_argument(
            "--old-root",
            default=r"G:\Мой диск\buket\old\public_html",
            help="Path to old Joomla public_html directory",
        )
        parser.add_argument(
            "--backend-base-url",
            default="http://127.0.0.1:3002",
            help="Base URL used to build Product.image links",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing Category/Product records before import",
        )

    def handle(self, *args, **options):
        dump_path = Path(options["dump"]).resolve()
        old_root = Path(options["old_root"]).resolve()
        backend_base_url = options["backend_base_url"].rstrip("/")
        clear_existing = options["clear"]

        if not dump_path.exists():
            raise CommandError(f"Dump file not found: {dump_path}")
        if not old_root.exists():
            raise CommandError(f"Old root not found: {old_root}")

        # Store files inside app static so runserver serves them immediately via /static/.
        static_root = Path(__file__).resolve().parents[2] / "static" / "legacy-old"
        static_root.mkdir(parents=True, exist_ok=True)

        fallback_rel = Path("image/no_image.jpg")
        fallback_src = old_root / fallback_rel
        fallback_dst = static_root / fallback_rel
        if fallback_src.exists():
            fallback_dst.parent.mkdir(parents=True, exist_ok=True)
            if not fallback_dst.exists():
                shutil.copy2(fallback_src, fallback_dst)
        fallback_url = f"{backend_base_url}/static/legacy-old/{fallback_rel.as_posix()}"

        self.stdout.write("Loading tables from SQL dump...")

        categories_base = list(iter_table_rows(dump_path, "wzx3q_virtuemart_categories"))
        categories_ru = {
            int(row["virtuemart_category_id"]): safe_str(row.get("category_name"))
            for row in iter_table_rows(dump_path, "wzx3q_virtuemart_categories_ru_ru")
        }
        products_base = list(iter_table_rows(dump_path, "wzx3q_virtuemart_products"))
        products_ru = {
            int(row["virtuemart_product_id"]): row
            for row in iter_table_rows(dump_path, "wzx3q_virtuemart_products_ru_ru")
        }

        price_by_product = first_by_key(
            iter_table_rows(dump_path, "wzx3q_virtuemart_product_prices"),
            "virtuemart_product_id",
        )
        category_by_product = first_by_key(
            iter_table_rows(dump_path, "wzx3q_virtuemart_product_categories"),
            "virtuemart_product_id",
        )
        media_by_product = first_by_key(
            iter_table_rows(dump_path, "wzx3q_virtuemart_product_medias"),
            "virtuemart_product_id",
        )
        media_rows = {
            int(row["virtuemart_media_id"]): row
            for row in iter_table_rows(dump_path, "wzx3q_virtuemart_medias")
        }

        stats = ImportStats()

        with transaction.atomic():
            if clear_existing:
                Product.objects.all().delete()
                Category.objects.all().delete()

            category_id_map: Dict[int, Category] = {}
            used_category_names = set(Category.objects.values_list("name", flat=True))

            for row in categories_base:
                if int_or_zero(row.get("published")) != 1:
                    continue
                old_id = int(row["virtuemart_category_id"])
                name = categories_ru.get(old_id, "").strip()
                if not name:
                    continue

                unique_name = make_unique_name(name, used_category_names, max_len=100)
                category = Category.objects.create(name=unique_name)
                used_category_names.add(unique_name)
                category_id_map[old_id] = category
                stats.categories_created += 1

            for row in products_base:
                if int_or_zero(row.get("published")) != 1:
                    continue
                product_id = int(row["virtuemart_product_id"])
                ru = products_ru.get(product_id, {})

                title = safe_str(ru.get("product_name")).strip() or safe_str(row.get("product_sku")).strip()
                if not title:
                    title = f"Product {product_id}"
                title = title[:100]

                description = (safe_str(ru.get("product_desc")).strip() or safe_str(ru.get("product_s_desc")).strip())

                price_row = price_by_product.get(product_id)
                price = parse_price(price_row.get("product_price") if price_row else None)

                category = None
                product_cat_row = category_by_product.get(product_id)
                if product_cat_row:
                    old_cat_id = int_or_zero(product_cat_row.get("virtuemart_category_id"))
                    category = category_id_map.get(old_cat_id)

                image_url = fallback_url
                product_media_row = media_by_product.get(product_id)
                if product_media_row:
                    media_id = int_or_zero(product_media_row.get("virtuemart_media_id"))
                    media = media_rows.get(media_id)
                    media_rel = safe_str(media.get("file_url")) if media else ""
                    media_rel = media_rel.lstrip("/").replace("\\", "/")
                    if media_rel:
                        src_file = old_root / media_rel
                        dst_file = static_root / media_rel
                        if src_file.exists():
                            dst_file.parent.mkdir(parents=True, exist_ok=True)
                            if not dst_file.exists():
                                shutil.copy2(src_file, dst_file)
                                stats.images_copied += 1
                            image_url = f"{backend_base_url}/static/legacy-old/{media_rel}"
                        else:
                            stats.images_missing += 1

                Product.objects.create(
                    title=title,
                    description=description,
                    price=price,
                    image=image_url,
                    category=category,
                )
                stats.products_created += 1

        self.stdout.write(self.style.SUCCESS("Import finished"))
        self.stdout.write(f"Categories imported: {stats.categories_created}")
        self.stdout.write(f"Products imported: {stats.products_created}")
        self.stdout.write(f"Images copied: {stats.images_copied}")
        self.stdout.write(f"Images missing: {stats.images_missing}")


def iter_table_rows(sql_path: Path, table_name: str) -> Iterator[Dict[str, object]]:
    prefix = f"INSERT INTO `{table_name}`"
    buffer: List[str] = []
    collecting = False

    with sql_path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if not collecting:
                if line.startswith(prefix):
                    collecting = True
                    buffer = [line]
                    if line.rstrip().endswith(";"):
                        yield from parse_insert_statement("".join(buffer))
                        collecting = False
                        buffer = []
            else:
                buffer.append(line)
                if line.rstrip().endswith(";"):
                    yield from parse_insert_statement("".join(buffer))
                    collecting = False
                    buffer = []


def parse_insert_statement(statement: str) -> Iterator[Dict[str, object]]:
    match = re.match(
        r"INSERT INTO `[^`]+` \((?P<cols>.+?)\) VALUES\s*(?P<values>.+);\s*$",
        statement,
        flags=re.S,
    )
    if not match:
        return

    cols = re.findall(r"`([^`]+)`", match.group("cols"))
    values_blob = match.group("values").strip()

    for row_blob in split_rows(values_blob):
        raw_values = split_fields(row_blob[1:-1])
        parsed_values = [parse_sql_value(v.strip()) for v in raw_values]
        if len(parsed_values) != len(cols):
            continue
        yield dict(zip(cols, parsed_values))


def split_rows(values_blob: str) -> List[str]:
    rows: List[str] = []
    in_quote = False
    escape = False
    depth = 0
    start = -1

    for i, ch in enumerate(values_blob):
        if in_quote:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == "'":
                in_quote = False
            continue

        if ch == "'":
            in_quote = True
            continue
        if ch == "(":
            depth += 1
            if depth == 1:
                start = i
            continue
        if ch == ")":
            depth -= 1
            if depth == 0 and start >= 0:
                rows.append(values_blob[start : i + 1])
            continue

    return rows


def split_fields(row_blob: str) -> List[str]:
    fields: List[str] = []
    in_quote = False
    escape = False
    token: List[str] = []

    for ch in row_blob:
        if in_quote:
            token.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == "'":
                in_quote = False
            continue

        if ch == "'":
            in_quote = True
            token.append(ch)
            continue
        if ch == ",":
            fields.append("".join(token))
            token = []
            continue
        token.append(ch)

    fields.append("".join(token))
    return fields


def parse_sql_value(token: str) -> object:
    upper = token.upper()
    if upper == "NULL":
        return None

    if token.startswith("'") and token.endswith("'"):
        value = token[1:-1]
        value = value.replace("\\\\", "\\")
        value = value.replace("\\'", "'")
        value = value.replace("\\r", "\r")
        value = value.replace("\\n", "\n")
        value = value.replace("\\t", "\t")
        return value

    if re.fullmatch(r"-?\d+", token):
        try:
            return int(token)
        except ValueError:
            return token

    if re.fullmatch(r"-?\d+\.\d+", token):
        try:
            return Decimal(token)
        except InvalidOperation:
            return token

    return token


def first_by_key(rows: Iterable[Dict[str, object]], key_name: str) -> Dict[int, Dict[str, object]]:
    result: Dict[int, Dict[str, object]] = {}
    for row in rows:
        key = int_or_zero(row.get(key_name))
        if key and key not in result:
            result[key] = row
    return result


def int_or_zero(value: object) -> int:
    try:
        return int(value) if value is not None else 0
    except (TypeError, ValueError):
        return 0


def safe_str(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def parse_price(value: object) -> Decimal:
    if value in (None, ""):
        return Decimal("0.00")
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return Decimal("0.00")


def make_unique_name(name: str, used: set, max_len: int = 100) -> str:
    base = name.strip()[:max_len]
    if base not in used:
        return base

    idx = 2
    while True:
        suffix = f" ({idx})"
        candidate = f"{base[: max_len - len(suffix)]}{suffix}"
        if candidate not in used:
            return candidate
        idx += 1
