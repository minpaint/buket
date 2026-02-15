from __future__ import annotations

from pathlib import Path
import csv
import re
import shutil

from django.core.management.base import BaseCommand, CommandError

from shop.models import Product
from .import_joomla_catalog import iter_table_rows, int_or_zero, safe_str


def normalize_article(value: str) -> str:
    digits = "".join(ch for ch in (value or "") if ch.isdigit())
    if not digits:
        return ""
    try:
        return str(int(digits))
    except ValueError:
        return digits


def normalize_title(value: str) -> str:
    text = (value or "").strip().lower().replace("ё", "е")
    text = text.replace('"', "").replace("'", "")
    text = re.sub(r"\s+", " ", text)
    return text


class Command(BaseCommand):
    help = "Sync Product.image from old Joomla/VirtueMart media by article and title."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dump",
            default=str(Path("..") / "old" / "buketby_newbd.sql"),
            help="Path to SQL dump file",
        )
        parser.add_argument(
            "--old-root",
            default=str(Path("..") / "old" / "public_html"),
            help="Path to old Joomla public_html directory",
        )
        parser.add_argument(
            "--backend-base-url",
            default="http://127.0.0.1:3002",
            help="Base URL used to build Product.image links",
        )
        parser.add_argument(
            "--only-placeholders",
            action="store_true",
            help="Update only products with no_image placeholder",
        )
        parser.add_argument(
            "--report",
            default="legacy_image_sync_report.csv",
            help="CSV report path (relative to backend dir)",
        )

    def handle(self, *args, **options):
        dump_path = Path(options["dump"]).resolve()
        old_root = Path(options["old_root"]).resolve()
        backend_base_url = options["backend_base_url"].rstrip("/")
        only_placeholders = bool(options["only_placeholders"])
        report_path = Path(options["report"]).resolve()

        if not dump_path.exists():
            raise CommandError(f"Dump file not found: {dump_path}")
        if not old_root.exists():
            raise CommandError(f"Old root not found: {old_root}")

        static_root = Path(__file__).resolve().parents[2] / "static" / "legacy-old"
        static_root.mkdir(parents=True, exist_ok=True)

        self.stdout.write("Loading legacy mapping from SQL dump...")

        products_base = list(iter_table_rows(dump_path, "wzx3q_virtuemart_products"))
        products_ru = {
            int_or_zero(row.get("virtuemart_product_id")): row
            for row in iter_table_rows(dump_path, "wzx3q_virtuemart_products_ru_ru")
        }

        medias = {
            int_or_zero(row.get("virtuemart_media_id")): row
            for row in iter_table_rows(dump_path, "wzx3q_virtuemart_medias")
        }

        media_by_product = {}
        for row in iter_table_rows(dump_path, "wzx3q_virtuemart_product_medias"):
            pid = int_or_zero(row.get("virtuemart_product_id"))
            if pid <= 0 or pid in media_by_product:
                continue
            media_by_product[pid] = row

        by_article_exact = {}
        by_article_norm = {}
        by_title_norm = {}

        for row in products_base:
            if int_or_zero(row.get("published")) != 1:
                continue

            pid = int_or_zero(row.get("virtuemart_product_id"))
            if pid <= 0:
                continue

            media_link = media_by_product.get(pid)
            if not media_link:
                continue
            media_id = int_or_zero(media_link.get("virtuemart_media_id"))
            media_row = medias.get(media_id)
            if not media_row:
                continue

            file_rel = safe_str(media_row.get("file_url")).lstrip("/").replace("\\", "/")
            if not file_rel:
                continue

            sku = safe_str(row.get("product_sku")).strip()
            title = safe_str(products_ru.get(pid, {}).get("product_name")).strip()
            payload = (file_rel, pid, sku, title)

            if sku:
                by_article_exact.setdefault(sku, payload)
                sku_norm = normalize_article(sku)
                if sku_norm:
                    by_article_norm.setdefault(sku_norm, payload)

            if title:
                by_title_norm.setdefault(normalize_title(title), payload)

        self.stdout.write(
            f"Mapping loaded: exact_sku={len(by_article_exact)}, norm_sku={len(by_article_norm)}, title={len(by_title_norm)}"
        )

        qs = Product.objects.all().order_by("id")
        if only_placeholders:
            qs = qs.filter(image__contains="/static/legacy-old/image/no_image.jpg")

        checked = 0
        updated = 0
        copied = 0
        missing_file = 0
        unresolved = 0
        report_rows = []

        for p in qs:
            checked += 1
            art = (p.article or "").strip()
            title_norm = normalize_title(p.title)

            match = None
            reason = ""

            if art and art in by_article_exact:
                match = by_article_exact[art]
                reason = "article_exact"
            if not match and art:
                norm = normalize_article(art)
                if norm and norm in by_article_norm:
                    match = by_article_norm[norm]
                    reason = "article_norm"
            if not match and title_norm and title_norm in by_title_norm:
                match = by_title_norm[title_norm]
                reason = "title_norm"

            if not match:
                unresolved += 1
                report_rows.append(
                    [p.id, p.title, p.article, p.image, "", "", "unresolved"]
                )
                continue

            file_rel, legacy_pid, legacy_sku, legacy_title = match
            src = old_root / file_rel
            dst = static_root / file_rel

            if not src.exists():
                missing_file += 1
                report_rows.append(
                    [p.id, p.title, p.article, p.image, legacy_pid, file_rel, "legacy_file_missing"]
                )
                continue

            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists():
                shutil.copy2(src, dst)
                copied += 1

            new_url = f"{backend_base_url}/static/legacy-old/{file_rel}"
            if p.image != new_url:
                p.image = new_url
                p.save(update_fields=["image"])
                updated += 1
                status = f"updated:{reason}"
            else:
                status = f"already_set:{reason}"

            report_rows.append(
                [p.id, p.title, p.article, p.image, legacy_pid, file_rel, status]
            )

        report_path.parent.mkdir(parents=True, exist_ok=True)
        with report_path.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(
                [
                    "product_id",
                    "product_title",
                    "product_article",
                    "current_image",
                    "legacy_product_id",
                    "legacy_file_rel",
                    "status",
                ]
            )
            w.writerows(report_rows)

        self.stdout.write(self.style.SUCCESS("Legacy image sync finished"))
        self.stdout.write(f"Checked products: {checked}")
        self.stdout.write(f"Updated products: {updated}")
        self.stdout.write(f"Copied files: {copied}")
        self.stdout.write(f"Missing legacy files: {missing_file}")
        self.stdout.write(f"Unresolved products: {unresolved}")
        self.stdout.write(f"Report: {report_path}")

