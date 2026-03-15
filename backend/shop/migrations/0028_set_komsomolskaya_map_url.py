from django.db import migrations

PANORAMA_URL = (
    "https://yandex.ru/map-widget/v1/"
    "?l=stv%2Csta"
    "&ll=27.5612%2C53.9013"
    "&panorama%5Bpoint%5D=27.5612%2C53.9013"
    "&panorama%5Bfull%5D=true"
    "&z=17"
)


def set_map_url(apps, schema_editor):
    Store = apps.get_model("shop", "Store")
    updated = Store.objects.filter(
        address__icontains="Комсомольская"
    ).update(map_embed_url=PANORAMA_URL)
    if not updated:
        # fallback: try Belarusian spelling
        Store.objects.filter(
            address__icontains="Камсамольская"
        ).update(map_embed_url=PANORAMA_URL)


def unset_map_url(apps, schema_editor):
    Store = apps.get_model("shop", "Store")
    Store.objects.filter(map_embed_url=PANORAMA_URL).update(map_embed_url="")


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0027_add_sitepage_seo_description"),
    ]

    operations = [
        migrations.RunPython(set_map_url, unset_map_url),
    ]
