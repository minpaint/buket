from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0031_showcaseitem_section'),
    ]

    operations = [
        migrations.AddField(
            model_name='herobanner',
            name='is_default',
            field=models.BooleanField(
                default=False,
                help_text='Показывать когда нет активных баннеров',
                verbose_name='Фолбэк',
            ),
        ),
    ]
