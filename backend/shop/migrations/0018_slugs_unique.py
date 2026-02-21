"""
Добавляет unique constraint на slug поля Product и FlowerTag.
Выполняется после заполнения данных командами import_old_slugs и generate_slugs.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0017_slugs'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='slug',
            field=models.SlugField(
                blank=True, default='', max_length=120, unique=True,
                verbose_name='Slug (ЧПУ)',
                help_text='Заполняется автоматически из названия или старой БД',
            ),
        ),
        migrations.AlterField(
            model_name='flowertag',
            name='slug',
            field=models.SlugField(
                blank=True, default='', max_length=120, unique=True,
                verbose_name='Slug (ЧПУ)',
            ),
        ),
    ]
