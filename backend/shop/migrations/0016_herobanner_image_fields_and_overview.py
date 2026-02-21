from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0015_flowertag_product_flower_tags'),
    ]

    operations = [
        migrations.AddField(
            model_name='herobanner',
            name='overview',
            field=models.TextField(blank=True, default='', verbose_name='Обзор'),
        ),
        migrations.AlterField(
            model_name='herobanner',
            name='desktop_image',
            field=models.ImageField(upload_to='hero_banners/', verbose_name='Изображение desktop'),
        ),
        migrations.AlterField(
            model_name='herobanner',
            name='mobile_image',
            field=models.ImageField(blank=True, null=True, upload_to='hero_banners/', verbose_name='Изображение mobile'),
        ),
    ]
