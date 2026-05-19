from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0030_telegrambotsession'),
    ]

    operations = [
        migrations.AddField(
            model_name='showcaseitem',
            name='section',
            field=models.CharField(
                blank=True,
                choices=[('', 'Основная витрина'), ('plants', 'Комнатные растения')],
                default='',
                max_length=40,
                verbose_name='Секция',
            ),
        ),
        migrations.AlterUniqueTogether(
            name='showcaseitem',
            unique_together={('store', 'product', 'section')},
        ),
    ]
