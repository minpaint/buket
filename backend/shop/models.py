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
    phone = models.CharField(max_length=20, blank=True, default='', verbose_name='Телефон (устар.)')
    description = models.TextField(blank=True, default='', verbose_name='Описание / как добраться')
    working_hours = models.CharField(max_length=200, blank=True, default='', verbose_name='Режим работы')
    map_embed_url = models.TextField(
        blank=True, default='',
        verbose_name='Код карты (iframe src)',
        help_text='Вставьте src="" из iframe Яндекс/Google карт',
    )
    sort_order = models.PositiveSmallIntegerField(default=0, verbose_name='Порядок')

    class Meta:
        verbose_name = 'Магазин'
        verbose_name_plural = 'Магазины'
        ordering = ('sort_order', 'name')

    def __str__(self):
        return self.name


class StorePhone(models.Model):
    EMOJI_CHOICES = [
        ('📞', '📞 Телефон'),
        ('📱', '📱 Мобильный'),
        ('💬', '💬 WhatsApp/Viber'),
        ('✉️', '✉️ Email'),
        ('🕐', '🕐 Доп. время'),
        ('', 'Без эмоджи'),
    ]
    store = models.ForeignKey('Store', on_delete=models.CASCADE, related_name='phones', verbose_name='Магазин')
    emoji = models.CharField(max_length=10, blank=True, default='📞', choices=EMOJI_CHOICES, verbose_name='Эмоджи')
    label = models.CharField(max_length=50, blank=True, default='', verbose_name='Подпись (напр. «Заказы»)')
    number = models.CharField(max_length=50, verbose_name='Номер / контакт')
    sort_order = models.PositiveSmallIntegerField(default=0, verbose_name='Порядок')

    class Meta:
        verbose_name = 'Телефон магазина'
        verbose_name_plural = 'Телефоны магазина'
        ordering = ('sort_order',)

    def __str__(self):
        return f'{self.store.name}: {self.number}'


class StorePhoto(models.Model):
    store = models.ForeignKey('Store', on_delete=models.CASCADE, related_name='photos', verbose_name='Магазин')
    image = models.ImageField(upload_to='stores/', verbose_name='Фото интерьера')
    caption = models.CharField(max_length=200, blank=True, default='', verbose_name='Подпись')
    sort_order = models.PositiveSmallIntegerField(default=0, verbose_name='Порядок')

    class Meta:
        verbose_name = 'Фото магазина'
        verbose_name_plural = 'Фото магазина'
        ordering = ('sort_order',)

    def __str__(self):
        return f'{self.store.name} — фото {self.sort_order}'


class StoreManager(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='store_manager',
        verbose_name='Пользователь (дашборд)',
    )
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
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Цена')
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
                                    related_name='main_products', verbose_name='Основная категория')
    categories = models.ManyToManyField('Category', related_name='products', blank=True,
                                          verbose_name='Категории')
    flower_tags = models.ManyToManyField(
        'FlowerTag',
        related_name='products',
        blank=True,
        verbose_name='Состав (цветы)',
    )
    stores = models.ManyToManyField(
        'Store',
        related_name='products_m2m',
        blank=True,
        verbose_name='Магазины',
    )
    slug = models.SlugField(
        max_length=120, unique=True, blank=True, default='',
        verbose_name='Slug (ЧПУ)',
        help_text='Заполняется автоматически из названия или старой БД',
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


class ProductImage(models.Model):
    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name='Товар',
    )
    image = models.ImageField(
        upload_to='products/',
        verbose_name='Изображение',
    )
    sort_order = models.PositiveIntegerField(default=0, verbose_name='Порядок')

    def __str__(self):
        return f'{self.product.title} - фото {self.sort_order}'

    class Meta:
        verbose_name = 'Фото товара'
        verbose_name_plural = 'Фото товаров'
        ordering = ('sort_order',)


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


class FlowerTag(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='Название цветка')
    slug = models.SlugField(max_length=120, unique=True, blank=True, default='', verbose_name='Slug (ЧПУ)')
    sort_order = models.PositiveIntegerField(default=0, verbose_name='Порядок')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Тег (цветок)'
        verbose_name_plural = 'Теги (цветы)'
        ordering = ('sort_order', 'name')


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название')
    slug = models.SlugField(max_length=120, blank=True, default='', verbose_name='Slug (ЧПУ)')
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='Родительская категория',
    )
    sort_order = models.PositiveIntegerField(default=0, verbose_name='Порядок')

    def __str__(self):
        if self.parent:
            return f'{self.parent.name} → {self.name}'
        return self.name

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ('sort_order', 'name')
        unique_together = ('name', 'parent')


class Review(models.Model):
    author = models.CharField(max_length=150, verbose_name='Автор')
    company = models.CharField(max_length=200, blank=True, default='', verbose_name='Компания')
    text = models.TextField(verbose_name='Текст отзыва')
    rating = models.PositiveSmallIntegerField(default=5, verbose_name='Оценка')
    image = models.URLField(max_length=300, blank=True, default='', verbose_name='Логотип/изображение (URL)')
    source_url = models.URLField(max_length=300, blank=True, default='', verbose_name='Источник')
    store = models.ForeignKey(
        'Store',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviews',
        verbose_name='Магазин',
    )
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
    overview = models.TextField(blank=True, default='', verbose_name='Обзор')
    button_text = models.CharField(max_length=80, blank=True, default='Перейти в каталог', verbose_name='Текст кнопки')
    button_url = models.CharField(max_length=255, blank=True, default='/store', verbose_name='Ссылка кнопки')
    desktop_image = models.ImageField(upload_to='hero_banners/', verbose_name='Изображение desktop')
    mobile_image = models.ImageField(upload_to='hero_banners/', blank=True, null=True, verbose_name='Изображение mobile')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    starts_on = models.DateField(null=True, blank=True, verbose_name='Дата начала')
    ends_on = models.DateField(null=True, blank=True, verbose_name='Дата окончания')
    sort_order = models.PositiveIntegerField(default=0, verbose_name='Приоритет')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлен')

    def __str__(self):
        return self.name

    @staticmethod
    def _media_or_legacy_url(field_file):
        if not field_file:
            return ''
        raw_value = str(field_file)
        if raw_value.startswith(('http://', 'https://', '/')):
            return raw_value
        try:
            return field_file.url
        except Exception:
            return raw_value

    @property
    def desktop_image_url(self):
        return self._media_or_legacy_url(self.desktop_image)

    @property
    def mobile_image_url(self):
        if self.mobile_image:
            return self._media_or_legacy_url(self.mobile_image)
        return self.desktop_image_url

    class Meta:
        ordering = ('sort_order', '-created_at')
        verbose_name = 'Hero-баннер'
        verbose_name_plural = 'Hero-баннеры'


class SitePage(models.Model):
    slug = models.SlugField(max_length=60, unique=True, verbose_name='URL (slug)')
    title = models.CharField(max_length=200, verbose_name='Заголовок')
    content = models.TextField(verbose_name='Содержимое (HTML)')
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    sort_order = models.PositiveSmallIntegerField(default=0, verbose_name='Порядок в меню')

    class Meta:
        ordering = ('sort_order', 'title')
        verbose_name = 'Страница сайта'
        verbose_name_plural = 'Страницы сайта'

    def __str__(self):
        return self.title


class Ticker(models.Model):
    """Бегущая строка на сайте."""
    text = models.TextField(verbose_name='Текст строки')
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    sort_order = models.PositiveSmallIntegerField(default=0, verbose_name='Порядок')

    class Meta:
        ordering = ('sort_order',)
        verbose_name = 'Бегущая строка'
        verbose_name_plural = 'Бегущая строка'

    def __str__(self):
        return self.text[:60]


class ShowcaseItem(models.Model):
    """Товар в витрине конкретного магазина (независимо от is_online_showcase)."""
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='showcase_items',
        verbose_name='Магазин',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='showcase_items',
        verbose_name='Товар',
    )
    sort_order = models.PositiveIntegerField(default=0, verbose_name='Порядок')

    class Meta:
        unique_together = ('store', 'product')
        ordering = ('sort_order', '-id')
        verbose_name = 'Товар в витрине'
        verbose_name_plural = 'Товары в витринах'

    def __str__(self):
        return f'{self.store.name} — {self.product.title}'
