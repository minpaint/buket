from django.contrib import admin
from django.utils.html import format_html
from .models import Product, Discount, Order, OrderItem, Category, Review, HeroBanner, Store, StoreManager

admin.site.site_header = 'Администрирование Buket.by'
admin.site.site_title = 'Buket.by Admin'
admin.site.index_title = 'Панель управления'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('image_preview', 'title', 'article', 'store', 'display_price', 'is_online_showcase', 'showcase_sort_order')
    search_fields = ('title', 'article')
    list_filter = ('is_online_showcase', 'store', 'is_published')
    list_per_page = 50
    readonly_fields = ('image_preview_large',)
    fields = (
        'image_preview_large',
        'title',
        'article',
        'store',
        'price',
        'is_published',
        'is_online_showcase',
        'showcase_sort_order',
        'created_by',
        'category',
        'description',
        'uploaded_image',
        'image',
    )

    def _image_src(self, obj):
        if obj.uploaded_image:
            return obj.uploaded_image.url
        return obj.image

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

    @admin.display(description='Стоимость', ordering='price')
    def display_price(self, obj):
        return f'{obj.price:.2f} BYN'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Keep legacy URL field in sync so the current frontend keeps working.
        if obj.uploaded_image:
            uploaded_url = request.build_absolute_uri(obj.uploaded_image.url)
            if obj.image != uploaded_url:
                obj.image = uploaded_url
                obj.save(update_fields=['image'])


admin.site.register(Discount)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Category)
admin.site.register(Store)
admin.site.register(StoreManager)


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
    search_fields = ('name', 'title', 'caption')
    list_editable = ('is_active', 'sort_order')
    readonly_fields = ('created_at', 'updated_at')
