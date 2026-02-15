from django.contrib.auth.models import User
from django.db import models
import uuid


class Store(models.Model):
    subdomain = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        default='',
        help_text='Пустой поддомен = основной домен',
        verbose_name='Поддомен',
    )
    name = models.CharField(max_length=100, verbose_name='Название магазина')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлен')
    address = models.TextField(blank=True, default='', verbose_name='Адрес')
    phone = models.CharField(max_length=20, blank=True, default='', verbose_name='Телефон')

    class Meta:
        verbose_name = 'Магазин'
        verbose_name_plural = 'Магазины'

    def __str__(self):
        return self.name


class StoreManager(models.Model):
    telegram_id = models.BigIntegerField(unique=True, db_index=True, verbose_name='Telegram ID')
    telegram_username = models.CharField(max_length=100, blank=True, default='', verbose_name='Username')
    full_name = models.CharField(max_length=200, verbose_name='Имя')
    stores = models.ManyToManyField('Store', related_name='managers', verbose_name='Магазины')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')

    class Meta:
        verbose_name = 'Менеджер магазина'
        verbose_name_plural = 'Менеджеры магазинов'

    def __str__(self):
        return f'{self.full_name} ({self.telegram_id})'


class Product(models.Model):
    SHOWCASE_CHANNEL_DELIVERY = 'delivery'
    SHOWCASE_CHANNEL_PICKUP = 'pickup'
    SHOWCASE_CHANNEL_BOTH = 'both'
    SHOWCASE_CHANNEL_CHOICES = [
        (SHOWCASE_CHANNEL_DELIVERY, 'Доставка'),
        (SHOWCASE_CHANNEL_PICKUP, 'Самовывоз'),
        (SHOWCASE_CHANNEL_BOTH, 'И доставка, и самовывоз'),
    ]

    title = models.CharField(max_length=100, verbose_name='Название')
    article = models.CharField(max_length=64, blank=True, default="", verbose_name='Артикул')
    description = models.TextField(blank=True, verbose_name='Описание')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')
    image = models.URLField(max_length=200, blank=True, default='', verbose_name='Изображение (URL)')
    uploaded_image = models.ImageField(
        upload_to='products/',
        null=True,
        blank=True,
        verbose_name='Изображение (файл)',
    )
    is_online_showcase = models.BooleanField(default=False, verbose_name='Показывать в ONLINE витрине')
    showcase_channel = models.CharField(
        max_length=16,
        choices=SHOWCASE_CHANNEL_CHOICES,
        default=SHOWCASE_CHANNEL_BOTH,
        verbose_name='Канал витрины',
    )
    showcase_sort_order = models.PositiveIntegerField(default=0, verbose_name='Порядок в витрине')
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='products', verbose_name='Категория')
    store = models.ForeignKey(
        'Store',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name='Магазин',
    )
    is_published = models.BooleanField(default=True, verbose_name='Опубликован')
    created_by = models.ForeignKey(
        'StoreManager',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_products',
        verbose_name='Добавил менеджер',
    )

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'


class Discount(models.Model):
    code = models.CharField(max_length=20, verbose_name='Код')
    percent = models.PositiveIntegerField(verbose_name='Процент')

    def __str__(self):
        return f"{self.code} ({self.percent})"

    class Meta:
        verbose_name = 'Скидка'
        verbose_name_plural = 'Скидки'


class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name='ID заказа')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders', verbose_name='Пользователь')
    discount = models.ForeignKey('Discount', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Скидка')

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'


class OrderItem(models.Model):
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='items', verbose_name='Заказ')
    product = models.ForeignKey('Product', on_delete=models.CASCADE, verbose_name='Товар')
    qty = models.PositiveIntegerField(verbose_name='Количество')

    def __str__(self):
        return f"{self.product.title} ({self.qty})"

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказа'


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='Название')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'


class Review(models.Model):
    author = models.CharField(max_length=150, verbose_name='Автор')
    company = models.CharField(max_length=200, blank=True, default='', verbose_name='Компания')
    text = models.TextField(verbose_name='Текст отзыва')
    rating = models.PositiveSmallIntegerField(default=5, verbose_name='Оценка')
    image = models.URLField(max_length=300, blank=True, default='', verbose_name='Логотип/изображение (URL)')
    source_url = models.URLField(max_length=300, blank=True, default='', verbose_name='Источник')
    is_published = models.BooleanField(default=True, verbose_name='Опубликован')
    sort_order = models.PositiveIntegerField(default=0, verbose_name='Порядок')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлен')

    def __str__(self):
        if self.company:
            return f'{self.company} - {self.author}'
        return self.author

    class Meta:
        ordering = ('sort_order', '-created_at')
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'


class HeroBanner(models.Model):
    name = models.CharField(max_length=200, verbose_name='Название кампании')
    title = models.CharField(max_length=255, verbose_name='Заголовок')
    caption = models.CharField(max_length=255, blank=True, default='', verbose_name='Подзаголовок')
    button_text = models.CharField(max_length=80, blank=True, default='Перейти в каталог', verbose_name='Текст кнопки')
    button_url = models.CharField(max_length=255, blank=True, default='/store', verbose_name='Ссылка кнопки')
    desktop_image = models.URLField(max_length=500, verbose_name='Изображение desktop (URL)')
    mobile_image = models.URLField(max_length=500, blank=True, default='', verbose_name='Изображение mobile (URL)')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    starts_on = models.DateField(null=True, blank=True, verbose_name='Дата начала')
    ends_on = models.DateField(null=True, blank=True, verbose_name='Дата окончания')
    sort_order = models.PositiveIntegerField(default=0, verbose_name='Приоритет')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлен')

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('sort_order', '-created_at')
        verbose_name = 'Hero-баннер'
        verbose_name_plural = 'Hero-баннеры'
