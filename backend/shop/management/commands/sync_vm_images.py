# -*- coding: utf-8 -*-
"""
Sync product images from old VirtueMart data using the vm_combined.txt mapping.
Copies images to media/products/ and creates ProductImage records.
"""
import os
import re
import shutil
from django.core.management.base import BaseCommand
from shop.models import Product, ProductImage


# VirtueMart SKU -> list of image paths (relative to old public_html)
# Parsed from vm_combined.txt
VM_MAPPING = {
    "0001": ["images/product/data/1.jpg", "images/product/data/1_2.jpg", "images/product/data/1_3.jpg"],
    "0002": ["images/product/data/2_2.jpg", "images/product/data/2.jpg", "images/product/data/2_1.jpg"],
    "0003": ["images/product/data/3.jpg", "images/product/data/3_1.jpg", "images/product/data/3_2.jpg"],
    "0004": ["images/product/data/4.jpg", "images/product/data/4_2.jpg", "images/product/data/4_1.jpg"],
    "0005": ["images/product/data/5.jpg", "images/product/data/5_1.jpg", "images/product/data/5_2.jpg"],
    "0006": ["images/product/data/6_1.jpg", "images/product/data/6_2.jpg", "images/product/data/6.jpg"],
    "0007": ["images/product/data/7_2.jpg", "images/product/data/7_1.jpg", "images/product/data/7_3.jpg", "images/product/data/7.jpg"],
    "0008": ["images/product/data/8.jpg", "images/product/data/8_2.jpg", "images/product/data/8_1.jpg"],
    "0009": ["images/product/data/9.jpg", "images/product/data/9_2.jpg", "images/product/data/9_1.jpg"],
    "0010": ["images/product/data/10_2.jpg", "images/product/data/10_1.jpg", "images/product/data/10.jpg"],
    "0011": ["images/product/data/11.jpg", "images/product/data/11_1.jpg", "images/product/data/11_2.jpg"],
    "0012": ["images/product/data/12_2.jpg", "images/product/data/12_1.jpg", "images/product/data/12.jpg"],
    "0013": ["images/product/data/13_2.jpg", "images/product/data/13_1.jpg", "images/product/data/13.jpg"],
    "0014": ["images/product/data/14_2.jpg", "images/product/data/14_1.jpg", "images/product/data/14.jpg"],
    "0015": ["images/product/data/15_2.jpg", "images/product/data/15_1.jpg", "images/product/data/15.jpg"],
    "0016": ["images/product/data/16_2.jpg", "images/product/data/16_1.jpg", "images/product/data/16.jpg"],
    "0017": ["images/product/data/17_1.jpg", "images/product/data/17.jpg", "images/product/data/17_2.jpg"],
    "0018": ["images/product/data/18_1.jpg", "images/product/data/18.jpg", "images/product/data/18_2.jpg"],
    "0019": ["images/product/data/19_1.jpg", "images/product/data/19.jpg", "images/product/data/19_2.jpg"],
    "0020": ["images/product/data/21_1.jpg", "images/product/data/20.jpg", "images/product/data/21_2.jpg"],
    "0021": ["images/product/data/21_13.jpg", "images/product/data/21.jpg", "images/product/data/21_23.jpg"],
    "0022": ["images/product/data/22_1.jpg", "images/product/data/22.jpg", "images/product/data/22_2.jpg"],
    "0023": ["images/product/data/23_1.jpg", "images/product/data/23.jpg", "images/product/data/23_2.jpg"],
    "0024": ["images/product/data/24_2.jpg", "images/product/data/24.jpg", "images/product/data/24_1.jpg"],
    "0025": ["images/product/data/25_2.jpg", "images/product/data/25_1.jpg", "images/product/data/25.jpg"],
    "0026": ["images/product/data/26_2.jpg", "images/product/data/26_1.jpg", "images/product/data/26.jpg"],
    "0027": ["images/product/data/27_1.jpg", "images/product/data/27_2.jpg", "images/product/data/27.jpg"],
    "0028": ["images/product/data/28_1.jpg", "images/product/data/28.jpg", "images/product/data/28_2.jpg"],
    "0029": ["images/product/data/29_2.jpg", "images/product/data/29_1.jpg", "images/product/data/29.jpg"],
    "0030": ["images/product/data/30.jpg"],
    "0031": ["images/product/data/31_1.jpg", "images/product/data/31.jpg", "images/product/data/31_2.jpg"],
    "0032": ["images/product/data/32_1.jpg", "images/product/data/32.jpg"],
    "0033": ["images/product/data/33.jpg"],
    "0034": ["images/product/data/34_1.jpg", "images/product/data/34.jpg", "images/product/data/34_2.jpg"],
    "0035": ["images/product/data/35_1.jpg", "images/product/data/35.jpg"],
    "0036": ["images/product/data/36.jpg"],
    "0037": ["images/product/data/37.jpg"],
    "0038": ["images/product/data/38.jpg", "images/product/data/38_1.jpg"],
    "0039": ["images/product/data/39.jpg"],
    "0040": ["images/product/data/40.jpg"],
    "0041": ["images/product/data/41.jpg"],
    "0042": ["images/product/data/42.jpg"],
    "0043": ["images/product/data/43.jpg"],
    "0044": ["images/product/data/000295.jpg", "images/product/data/000321.jpg", "images/product/data/000155.jpg"],
    "0045": ["images/product/data/0004.jpg", "images/product/data/0005.jpg", "images/product/data/0006.jpg"],
    "0046": ["images/product/data/0008.jpg", "images/product/data/0009.jpg", "images/product/data/0007.jpg"],
    "0047": ["images/product/data/0011.jpg", "images/product/data/0010.jpg", "images/product/data/0012.jpg"],
    "0048": ["images/product/data/0015.jpg", "images/product/data/0014.jpg", "images/product/data/0013.jpg"],
    "0049": ["images/product/data/0017.jpg", "images/product/data/0018.jpg", "images/product/data/0016.jpg"],
    "0050": ["images/product/data/0020.jpg", "images/product/data/0021.jpg", "images/product/data/0019.jpg"],
    "0051": ["images/product/data/0024.jpg", "images/product/data/0023.jpg", "images/product/data/0022.jpg"],
    "0052": ["images/product/data/0027.jpg", "images/product/data/0026.jpg", "images/product/data/0025.jpg"],
    "0053": ["images/product/data/0028.jpg", "images/product/data/0030.jpg", "images/product/data/0029.jpg"],
    "0054": ["images/product/data/0033.jpg", "images/product/data/0032.jpg", "images/product/data/0031.jpg"],
    "0055": ["images/product/data/0034.jpg", "images/product/data/0035.jpg", "images/product/data/0036.jpg"],
    "0056": ["images/product/data/0038.jpg", "images/product/data/0037.jpg", "images/product/data/0039.jpg"],
    "0057": ["images/product/data/0040.jpg", "images/product/data/0042.jpg", "images/product/data/0041.jpg"],
    "0058": ["images/product/data/0045.jpg", "images/product/data/0044.jpg", "images/product/data/0043.jpg"],
    "0059": ["images/product/data/0047.jpg", "images/product/data/0048.jpg", "images/product/data/0046.jpg"],
    "0060": ["images/product/data/0051.jpg", "images/product/data/0050.jpg", "images/product/data/0049.jpg"],
    "0061": ["images/product/data/0052.jpg", "images/product/data/0054.jpg", "images/product/data/0053.jpg"],
    "0062": ["images/product/data/0056.jpg", "images/product/data/0055.jpg", "images/product/data/0057.jpg"],
    "0063": ["images/product/data/0058.jpg", "images/product/data/0059.jpg", "images/product/data/0060.jpg"],
    "0064": ["images/product/data/0063.jpg", "images/product/data/0062.jpg", "images/product/data/0061.jpg"],
    "0065": ["images/product/data/0065.jpg", "images/product/data/0066.jpg", "images/product/data/0064.jpg"],
    "0066": ["images/product/data/0069.jpg", "images/product/data/0068.jpg", "images/product/data/0067.jpg"],
    "0067": ["images/product/data/0071.jpg", "images/product/data/0072.jpg", "images/product/data/0070.jpg"],
    "0068": ["images/product/data/130.jpg"],
    "0069": ["images/product/data/293.jpg"],
    "0070": ["images/product/data/480.jpg"],
    "0071": ["images/product/data/543.jpg"],
    "0072": ["images/product/data/633.jpg"],
    "0073": ["images/product/data/1015.jpg"],
    "0074": ["images/product/data/1250.jpg"],
    "0075": ["images/product/data/1740.jpg"],
    "0076": ["images/product/data/2165.jpg"],
    "0077": ["images/product/data/2692.jpg"],
    "0078": ["images/product/data/4217.jpg"],
    "0079": ["images/product/data/46.jpg"],
    "0080": ["images/product/data/50.jpg"],
    "0081": ["images/product/data/57.jpg"],
    "0082": ["images/product/data/62.jpg"],
    "0083": ["images/product/data/63.jpg"],
    "0084": ["images/product/data/006051.jpg", "images/product/data/006114.jpg", "images/product/data/006272.jpg"],
    "0085": ["images/product/data/006597.jpg", "images/product/data/006317.jpg", "images/product/data/006421.jpg"],
    "0086": ["images/product/data/006760.jpg", "images/product/data/006811.jpg", "images/product/data/006697.jpg"],
    "0087": ["images/product/data/006921.jpg", "images/product/data/007045.jpg", "images/product/data/007191.jpg"],
    "0088": ["images/product/data/0073.jpg", "images/product/data/007279.jpg", "images/product/data/0074.jpg"],
    "0089": ["images/product/data/0075.jpg", "images/product/data/0077.jpg", "images/product/data/0076.jpg"],
    "0090": ["images/product/data/0078.jpg", "images/product/data/0080.jpg", "images/product/data/0079.jpg"],
    "0091": ["images/product/data/0081.jpg", "images/product/data/0083.jpg", "images/product/data/0082.jpg"],
    "0092": ["images/product/data/0085.jpg", "images/product/data/0084.jpg"],
    "0093": ["images/product/data/0086.jpg", "images/product/data/0088.jpg", "images/product/data/0087.jpg"],
    "0094": ["images/product/data/0089.jpg", "images/product/data/0090.jpg", "images/product/data/0091.jpg"],
    "0095": ["images/product/data/0093.jpg", "images/product/data/0092.jpg"],
    "0096": ["images/product/data/009573.jpg", "images/product/data/009626.jpg", "images/product/data/009758.jpg"],
    "0097": ["images/product/data/009469.jpg"],
    "0098": ["images/product/data/0098.jpg", "images/product/data/0099.jpg", "images/product/data/0100.jpg"],
    "0099": ["images/product/data/0101.jpg", "images/product/data/0102.jpg", "images/product/data/0103.jpg"],
    "0100": ["images/product/data/0104.jpg", "images/product/data/0105.jpg", "images/product/data/0106.jpg"],
    "0101": ["images/product/data/0108.jpg", "images/product/data/0109.jpg", "images/product/data/0107.jpg"],
    "0102": ["images/product/data/0111.jpg", "images/product/data/0110.jpg", "images/product/data/0112.jpg"],
    "0103": ["images/product/data/0113.jpg", "images/product/data/0114.jpg", "images/product/data/0115.jpg"],
    "0104": ["images/product/data/0116.jpg", "images/product/data/0117.jpg", "images/product/data/0118.jpg"],
    "200": ["images/product/data/kally.JPG"],
    "105": ["images/product/data/_D308969.jpg"],
    "106": ["images/product/data/_D308984.jpg"],
    "107": ["images/product/data/_D308993.jpg"],
    "108": ["images/product/data/_D308999.jpg"],
    "109": ["images/product/data/_D309004.jpg"],
    "111": ["images/product/data/_D309011.jpg"],
    "112": ["images/product/data/_D309018.jpg"],
    "113": ["images/product/data/_D309026.jpg"],
    "114": ["images/product/data/_D309033.jpg"],
    "115": ["images/product/data/015.png"],
    "116": ["images/product/data/02.png"],
    "117": ["images/product/data/03.png"],
    "118": ["images/product/data/04.png", "images/product/data/09_1.png", "images/product/data/0990.png", "images/product/data/09_2.png"],
    "119": ["images/product/data/06.png", "images/product/data/06_1.png", "images/product/data/06_2.png"],
    "120": ["images/product/data/073.png", "images/product/data/07_131.png"],
    "121": ["images/product/data/07.png", "images/product/data/07_1.png"],
    "122": ["images/product/data/08.png"],
    "123": ["images/product/data/102.png"],
    "124": ["images/product/data/IMG_7349.jpg"],
    "125": ["images/product/data/125_2.jpg", "images/product/data/125_152.jpg"],
    "126": ["images/product/data/126_2.jpg", "images/product/data/126_1.jpg"],
    "127": ["images/product/data/127_2.jpg", "images/product/data/127_1.jpg"],
    "128": ["images/product/data/128_2.jpg", "images/product/data/128_1.jpg"],
    "129": ["images/product/data/129_3.jpg", "images/product/data/129_2.jpg", "images/product/data/129_1.jpg"],
    "130": ["images/product/data/130_2.jpg", "images/product/data/130_1.jpg"],
    "131": ["images/product/data/131_1.jpg", "images/product/data/131_2.jpg"],
    "132": ["images/product/data/132_2.jpg", "images/product/data/132_1.jpg"],
    "133": ["images/product/data/133_2.jpg", "images/product/data/133_1.jpg"],
    "134": ["images/product/data/134_2.jpg", "images/product/data/134_1.jpg"],
    "135": ["images/product/data/135_3.jpg", "images/product/data/135_2.jpg", "images/product/data/135_1.jpg"],
    "0136": ["images/product/data/136_1.jpg", "images/product/data/136_2.jpg"],
    "0137": ["images/product/data/137_2.jpg", "images/product/data/137_1.jpg"],
    "0138": ["images/product/data/138_1.jpg", "images/product/data/138_3.jpg", "images/product/data/138_2.jpg"],
    "0139": ["images/product/data/139_1.jpg", "images/product/data/139_3.jpg", "images/product/data/139_2.jpg"],
    "0140": ["images/product/data/140_1.jpg", "images/product/data/140_2.jpg", "images/product/data/140_3.jpg"],
    "0141": ["images/product/data/141.jpg", "images/product/data/141_2.jpg"],
    "0142": ["images/product/data/142.jpg", "images/product/data/142_225.jpg"],
    "0143": ["images/product/data/143.jpg", "images/product/data/143_2.jpg", "images/product/data/143_3.jpg"],
    "0144": ["images/product/data/144_1.jpg", "images/product/data/144_3.jpg", "images/product/data/144_2.jpg"],
    "0145": ["images/product/data/145_1.jpg", "images/product/data/145_2.jpg", "images/product/data/145_3.jpg"],
    "0146": ["images/product/data/146_1.jpg", "images/product/data/146_2.jpg"],
    "0147": ["images/product/data/147_1.jpg", "images/product/data/147_3.jpg", "images/product/data/147_2.jpg"],
    "0148": ["images/product/data/484.jpg", "images/product/data/512.jpg", "images/product/data/612.jpg"],
    # Special: sku=0147 second product (Композиция-сердце)
    "0147_heart": ["images/product/data/285.jpg", "images/product/data/171.jpg"],
    # sku=0153 (Букет на 14 февраля)
    "0153": ["images/product/data/0153.png"],
    "0154": ["images/product/data/0154.png"],
    "0155": ["images/product/data/015568.png"],
    "0156": ["images/product/data/156.png"],
    "0157": ["images/product/data/0157.png"],
    "0158": ["images/product/data/0158.png"],
    "0159": ["images/product/data/0159.png"],
    "0160": ["images/product/data/016030.png"],
    # res01 - Оформление ресторана
    "res01": ["images/product/data/IMG_912116.jpg", "images/product/data/841.jpg", "images/product/data/IMG_9116.jpg",
              "images/product/data/924.jpg", "images/product/data/552.jpg", "images/product/data/482.jpg",
              "images/product/data/323.jpg", "images/product/data/236.jpg", "images/product/data/123.jpg"],
    # Additional VirtueMart mappings for sku=0096-0099 (these use different file numbering)
    # sku=0100
    "00102": ["images/product/data/0111.jpg", "images/product/data/0110.jpg", "images/product/data/0112.jpg"],
    "00103": ["images/product/data/0113.jpg", "images/product/data/0114.jpg", "images/product/data/0115.jpg"],
    "00105": ["images/product/data/_D308969.jpg"],
    "00106": ["images/product/data/_D308984.jpg"],
    "00107": ["images/product/data/_D308993.jpg"],
    "00110": [],  # Not in VirtueMart
    "00111": ["images/product/data/_D309011.jpg"],
    "00112": ["images/product/data/_D309018.jpg"],
    "00113": ["images/product/data/_D309026.jpg"],
    "00114": ["images/product/data/_D309033.jpg"],
    "00115": ["images/product/data/015.png"],
    "00116": ["images/product/data/02.png"],
    "00117": ["images/product/data/03.png"],
    "00118": ["images/product/data/04.png", "images/product/data/09_1.png", "images/product/data/0990.png", "images/product/data/09_2.png"],
    "00119": ["images/product/data/06.png", "images/product/data/06_1.png", "images/product/data/06_2.png"],
    "00120": ["images/product/data/073.png", "images/product/data/07_131.png"],
    "00121": ["images/product/data/07.png", "images/product/data/07_1.png"],
    "00122": ["images/product/data/08.png"],
    "00123": ["images/product/data/102.png"],
    "00124": ["images/product/data/IMG_7349.jpg"],
    "00125": ["images/product/data/125_2.jpg", "images/product/data/125_152.jpg"],
    "00126": ["images/product/data/126_2.jpg", "images/product/data/126_1.jpg"],
    "00127": ["images/product/data/127_2.jpg", "images/product/data/127_1.jpg"],
    "00128": ["images/product/data/128_2.jpg", "images/product/data/128_1.jpg"],
    "00129": ["images/product/data/129_3.jpg", "images/product/data/129_2.jpg", "images/product/data/129_1.jpg"],
    "00130": ["images/product/data/130_2.jpg", "images/product/data/130_1.jpg"],
    "00131": ["images/product/data/131_1.jpg", "images/product/data/131_2.jpg"],
    "00132": ["images/product/data/132_2.jpg", "images/product/data/132_1.jpg"],
    "00133": ["images/product/data/133_2.jpg", "images/product/data/133_1.jpg"],
    "00134": ["images/product/data/134_2.jpg", "images/product/data/134_1.jpg"],
    "00135": ["images/product/data/135_3.jpg", "images/product/data/135_2.jpg", "images/product/data/135_1.jpg"],
    "00136": ["images/product/data/136_1.jpg", "images/product/data/136_2.jpg"],
    "00137": ["images/product/data/137_2.jpg", "images/product/data/137_1.jpg"],
    "00138": ["images/product/data/138_1.jpg", "images/product/data/138_3.jpg", "images/product/data/138_2.jpg"],
    "00139": ["images/product/data/139_1.jpg", "images/product/data/139_3.jpg", "images/product/data/139_2.jpg"],
    "00140": ["images/product/data/140_1.jpg", "images/product/data/140_2.jpg", "images/product/data/140_3.jpg"],
    "00141": ["images/product/data/141.jpg", "images/product/data/141_2.jpg"],
    "00142": ["images/product/data/142.jpg", "images/product/data/142_225.jpg"],
    "00143": ["images/product/data/143.jpg", "images/product/data/143_2.jpg", "images/product/data/143_3.jpg"],
    "00144": ["images/product/data/144_1.jpg", "images/product/data/144_3.jpg", "images/product/data/144_2.jpg"],
    "00145": ["images/product/data/145_1.jpg", "images/product/data/145_2.jpg", "images/product/data/145_3.jpg"],
    "00146": ["images/product/data/146_1.jpg", "images/product/data/146_2.jpg"],
    "00147": ["images/product/data/147_1.jpg", "images/product/data/147_3.jpg", "images/product/data/147_2.jpg"],
    "00148": ["images/product/data/484.jpg", "images/product/data/512.jpg", "images/product/data/612.jpg"],
    # Additional IDs with AUTO prefix
    "AUTO-0001": [],
}

OLD_BASE = "G:/Мой диск/buket/old/public_html"
MEDIA_DEST = "G:/Мой диск/buket/backend/media/products"


class Command(BaseCommand):
    help = "Sync product images from old VirtueMart data"

    def handle(self, *args, **options):
        os.makedirs(MEDIA_DEST, exist_ok=True)

        # Clear existing ProductImage records
        old_pi = ProductImage.objects.count()
        ProductImage.objects.all().delete()
        self.stdout.write(f"Cleared {old_pi} existing ProductImage records")

        products_updated = 0
        images_copied = 0
        product_images_created = 0
        errors = []

        for product in Product.objects.all().order_by("id"):
            article = product.article.strip()
            if not article:
                continue

            # Find mapping
            img_paths = VM_MAPPING.get(article)
            if img_paths is None:
                # Try normalized (strip leading zeros)
                norm = article.lstrip("0") or "0"
                img_paths = VM_MAPPING.get(norm)

            if not img_paths:
                if article not in VM_MAPPING and article not in ("AUTO-0001",):
                    errors.append(f"  NO MAPPING: {product.id}|{article}|{product.title}")
                continue

            # Copy files and create records
            first_image = True
            for i, rel_path in enumerate(img_paths):
                src = os.path.join(OLD_BASE, rel_path)
                if not os.path.exists(src):
                    errors.append(f"  FILE NOT FOUND: {src} (product {product.id}|{article})")
                    continue

                fname = os.path.basename(rel_path)
                # Prefix with article to avoid collisions
                dest_fname = f"{article}_{fname}"
                dest = os.path.join(MEDIA_DEST, dest_fname)

                if not os.path.exists(dest):
                    shutil.copy2(src, dest)
                    images_copied += 1

                django_path = f"products/{dest_fname}"

                # First image -> uploaded_image (main photo)
                if first_image:
                    product.uploaded_image = django_path
                    product.image = ""
                    product.save(update_fields=["uploaded_image", "image"])
                    products_updated += 1
                    first_image = False

                # All images -> ProductImage
                ProductImage.objects.create(
                    product=product,
                    image=django_path,
                    sort_order=i,
                )
                product_images_created += 1

        self.stdout.write(f"\n=== RESULTS ===")
        self.stdout.write(f"Products updated (main image): {products_updated}")
        self.stdout.write(f"Image files copied: {images_copied}")
        self.stdout.write(f"ProductImage records created: {product_images_created}")

        if errors:
            self.stdout.write(f"\nErrors ({len(errors)}):")
            for e in errors:
                self.stdout.write(e)

        # Report products still without images
        no_img = Product.objects.filter(
            uploaded_image="",
            image="",
        ).count() + Product.objects.filter(
            uploaded_image__isnull=True,
            image="",
        ).count()
        self.stdout.write(f"\nProducts still without any image: {no_img}")
