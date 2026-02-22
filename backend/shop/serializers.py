from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.utils.text import slugify
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Product, ProductImage, Discount, OrderItem, Order, Category, Review, HeroBanner, Store, StoreManager, FlowerTag, ShowcaseItem


class FlowerTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlowerTag
        fields = ['id', 'name', 'sort_order']


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'sort_order']


class ProductSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(
        queryset=Category.objects.all(),
        slug_field="name",
        allow_null=True,
        required=False,
    )
    images = ProductImageSerializer(many=True, read_only=True)
    flower_tags = FlowerTagSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = "__all__"


class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ['id', 'subdomain', 'name', 'is_active']


class StoreManagerSerializer(serializers.ModelSerializer):
    stores = StoreSerializer(many=True, read_only=True)

    class Meta:
        model = StoreManager
        fields = ['telegram_id', 'telegram_username', 'full_name', 'is_active', 'stores']


class BotProductCreateSerializer(serializers.ModelSerializer):
    telegram_id = serializers.IntegerField(write_only=True)
    store_id = serializers.PrimaryKeyRelatedField(queryset=Store.objects.filter(is_active=True), write_only=True)

    class Meta:
        model = Product
        fields = ['telegram_id', 'store_id', 'uploaded_image', 'price', 'title', 'description']

    def validate(self, attrs):
        telegram_id = attrs.get('telegram_id')
        store = attrs.get('store_id')
        manager = StoreManager.objects.filter(telegram_id=telegram_id, is_active=True).first()
        if not manager:
            raise serializers.ValidationError({'telegram_id': 'Пользователь не авторизован.'})
        if not manager.stores.filter(id=store.id, is_active=True).exists():
            raise serializers.ValidationError({'store_id': 'Нет доступа к выбранному магазину.'})

        attrs['_manager'] = manager
        return attrs

    def create(self, validated_data):
        validated_data.pop('telegram_id', None)
        store = validated_data.pop('store_id')
        manager = validated_data.pop('_manager')
        validated_data['created_by'] = manager
        validated_data['is_online_showcase'] = True
        validated_data['is_published'] = True

        if not validated_data.get('title'):
            validated_data['title'] = 'Букет'

        # Генерируем уникальный slug из названия
        base_slug = slugify(validated_data['title'], allow_unicode=False) or 'buket'
        slug = base_slug
        counter = 1
        while Product.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        validated_data['slug'] = slug

        product = Product.objects.create(**validated_data)
        product.stores.set([store])
        # Добавляем в витрину магазина через ShowcaseItem
        ShowcaseItem.objects.get_or_create(store=store, product=product)
        return product

class DiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discount
        fields = '__all__'


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['product', 'qty']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    class Meta:
        model = Order
        fields = ['id', 'discount', 'items']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        order = Order.objects.create(**validated_data)
        for item_data in items_data:
            OrderItem.objects.create(order=order, **item_data)
        return order


class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'parent', 'sort_order', 'children']

    def get_children(self, obj):
        children = obj.children.all()
        if children.exists():
            return CategorySerializer(children, many=True).data
        return []


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = '__all__'


class PublicReviewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['author', 'company', 'text', 'rating']

    def validate_author(self, value):
        value = (value or "").strip()
        if len(value) < 2:
            raise serializers.ValidationError("Укажите имя (минимум 2 символа).")
        return value

    def validate_text(self, value):
        value = (value or "").strip()
        if len(value) < 10:
            raise serializers.ValidationError("Текст отзыва слишком короткий.")
        return value

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Оценка должна быть от 1 до 5.")
        return value

    def create(self, validated_data):
        validated_data['is_published'] = False
        validated_data['source_url'] = 'frontend_form'
        validated_data['sort_order'] = 9999
        return Review.objects.create(**validated_data)


class HeroBannerSerializer(serializers.ModelSerializer):
    desktop_image_url = serializers.CharField(read_only=True)
    mobile_image_url = serializers.CharField(read_only=True)

    class Meta:
        model = HeroBanner
        fields = [
            'id',
            'name',
            'title',
            'caption',
            'overview',
            'button_text',
            'button_url',
            'desktop_image',
            'mobile_image',
            'desktop_image_url',
            'mobile_image_url',
            'is_active',
            'starts_on',
            'ends_on',
            'sort_order',
            'created_at',
            'updated_at',
        ]


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all())]
    )
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['username', 'password', 'password2', 'email', 'first_name', 'last_name']
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True}
        }
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({'password': 'Password must match.'})

        return attrs

    def create(self, validated_data):
        user = User.objects.create(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name']
        )

        user.set_password(validated_data['password'])
        user.save()

        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):

    @classmethod
    def get_token(cls, user):
        token = super(MyTokenObtainPairSerializer, cls).get_token(user)

        token['username'] = user.username
        return token
