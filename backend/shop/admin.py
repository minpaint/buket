from django.contrib import admin
from django.utils.html import format_html
from .models import Product, ProductImage, Discount, Order, OrderItem, Category, Review, HeroBanner, Store, StoreManager, StorePhone, StorePhoto, FlowerTag, SitePage

admin.site.site_header = 'Администрирование Buket.by'
admin.site.site_title = 'Buket.by Admin'
admin.site.index_title = 'Панель управления'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'image_preview',
        'title',
        'slug',
        'article',
        'flower_tags_display',
        'categories_display',
        'stores_display',
        'display_price',
        'is_online_showcase',
        'showcase_sort_order',
    )
    search_fields = ('title', 'article', 'slug')
    list_filter = ('is_online_showcase', 'stores', 'is_published')
    list_per_page = 50
    readonly_fields = ('slug', 'image_preview_large', 'all_images_preview')
    fields = (
        'all_images_preview',
        'image_preview_large',
        'uploaded_image',
        'image',
        'title',
        'slug',
        'article',
        'stores',
        'price',
        'is_published',
        'is_online_showcase',
        'showcase_sort_order',
        'created_by',
        'category',
        'categories',
        'flower_tags',
        'description',
    )
    inlines = []

    def _image_src(self, obj):
        if obj.uploaded_image:
            return obj.uploaded_image.url
        if obj.image:
            return obj.image
        first_image = obj.images.order_by('sort_order', 'id').first()
        if first_image and first_image.image:
            return first_image.image.url
        return ''

    @admin.display(description='Превью')
    def image_preview(self, obj):
        src = self._image_src(obj)
        if not src:
            return 'Нет фото'
        return format_html(
            '<img src="{}" alt="{}" style="width:56px;height:56px;object-fit:cover;border-radius:6px;border:1px solid #ddd;" />',
            src,
            obj.title,
        )

    @admin.display(description='Текущее изображение')
    def image_preview_large(self, obj):
        if not obj or not obj.pk:
            return 'Сохраните товар, чтобы увидеть превью'
        src = self._image_src(obj)
        if not src:
            return 'Нет фото'
        return format_html(
            '<img src="{}" alt="{}" style="width:180px;height:180px;object-fit:cover;border-radius:8px;border:1px solid #ddd;" />',
            src,
            obj.title,
        )

    @admin.display(description='Все изображения товара')
    def all_images_preview(self, obj):
        if not obj or not obj.pk:
            return 'Сохраните товар, затем добавьте фото в блоке ниже'

        images = list(obj.images.order_by('sort_order', 'id'))
        if not images:
            src = self._image_src(obj)
            if src:
                return format_html(
                    '<img src="{}" alt="{}" style="width:88px;height:88px;object-fit:cover;'
                    'border-radius:8px;border:1px solid #ddd;margin-right:8px;" />',
                    src,
                    obj.title,
                )
            return 'Нет фото. Добавьте фото в блоке "Фото товара" ниже.'

        html = []
        for img in images:
            html.append(
                format_html(
                    '<img src="{}" alt="{}" style="width:88px;height:88px;object-fit:cover;'
                    'border-radius:8px;border:1px solid #ddd;margin-right:8px;margin-bottom:8px;" />',
                    img.image.url,
                    obj.title,
                )
            )
        return format_html(''.join(html))

    @admin.display(description='Стоимость', ordering='price')
    def display_price(self, obj):
        return f'{obj.price:.2f} BYN'

    @admin.display(description='Категории (M2M)')
    def categories_display(self, obj):
        names = list(obj.categories.values_list('name', flat=True))
        return ', '.join(names) if names else '—'

    @admin.display(description='Магазины (M2M)')
    def stores_display(self, obj):
        names = list(obj.stores.values_list('name', flat=True))
        return ', '.join(names) if names else '—'

    @admin.display(description='Состав (цветы)')
    def flower_tags_display(self, obj):
        names = list(obj.flower_tags.values_list('name', flat=True))
        return ', '.join(names) if names else '—'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('categories', 'stores', 'flower_tags')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Keep legacy URL field in sync so the current frontend keeps working.
        if obj.uploaded_image:
            uploaded_url = request.build_absolute_uri(obj.uploaded_image.url)
            if obj.image != uploaded_url:
                obj.image = uploaded_url
                obj.save(update_fields=['image'])


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3
    fields = ('image', 'sort_order')


# Re-register ProductAdmin with inline
ProductAdmin.inlines = [ProductImageInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'parent', 'sort_order')
    list_filter = ('parent',)
    list_editable = ('sort_order',)
    search_fields = ('name', 'slug')
    readonly_fields = ('slug',)


admin.site.register(Discount)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(StoreManager)


class StorePhoneInline(admin.TabularInline):
    model = StorePhone
    extra = 2
    fields = ('emoji', 'label', 'number', 'sort_order')


class StorePhotoInline(admin.TabularInline):
    model = StorePhoto
    extra = 2
    fields = ('image', 'caption', 'sort_order')
    readonly_fields = ('photo_preview',)

    def photo_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width:80px;height:80px;object-fit:cover;border-radius:6px;" />',
                obj.image.url,
            )
        return '—'
    photo_preview.short_description = 'Превью'


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'working_hours', 'is_active', 'sort_order')
    list_editable = ('is_active', 'sort_order')
    search_fields = ('name', 'address')
    fields = (
        'name', 'subdomain', 'is_active', 'sort_order',
        'address', 'working_hours', 'description',
        'map_embed_url',
    )
    inlines = [StorePhoneInline, StorePhotoInline]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('author', 'company', 'rating', 'is_published', 'sort_order', 'updated_at')
    list_filter = ('is_published', 'rating')
    search_fields = ('author', 'company', 'text')
    list_editable = ('is_published', 'sort_order')
    readonly_fields = ('created_at', 'updated_at')
    actions = ('publish_reviews', 'unpublish_reviews')

    @admin.action(description='Опубликовать выбранные отзывы')
    def publish_reviews(self, request, queryset):
        queryset.update(is_published=True)

    @admin.action(description='Снять с публикации выбранные отзывы')
    def unpublish_reviews(self, request, queryset):
        queryset.update(is_published=False)


@admin.register(HeroBanner)
class HeroBannerAdmin(admin.ModelAdmin):
    list_display = ('name', 'title', 'is_active', 'starts_on', 'ends_on', 'sort_order', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'title', 'caption', 'overview')
    list_editable = ('is_active', 'sort_order')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(FlowerTag)
class FlowerTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'sort_order', 'product_count')
    list_editable = ('sort_order',)
    search_fields = ('name', 'slug')
    ordering = ('sort_order', 'name')
    readonly_fields = ('slug',)

    @admin.display(description='Товаров')
    def product_count(self, obj):
        return obj.products.count()


@admin.register(SitePage)
class SitePageAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'is_active', 'sort_order')
    list_editable = ('is_active', 'sort_order')
    prepopulated_fields = {'slug': ('title',)}
    fields = ('title', 'slug', 'content', 'is_active', 'sort_order')
