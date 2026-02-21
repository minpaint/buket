from django.contrib.auth.models import User
from django.conf import settings
from django.db.models import Prefetch, Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import RetrieveUpdateAPIView, CreateAPIView
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from django.utils import timezone
from django.utils.text import slugify
from django.shortcuts import get_object_or_404, render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from urllib.parse import quote, urlsplit
import json
from datetime import date
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import Product, Discount, Order, Category, Review, HeroBanner, Store, StoreManager, FlowerTag
from .serializers import (ProductSerializer, DiscountSerializer, OrderSerializer, CategorySerializer
, TokenObtainPairSerializer, RegisterSerializer, UserSerializer, ReviewSerializer, PublicReviewCreateSerializer,
HeroBannerSerializer, StoreSerializer, StoreManagerSerializer, BotProductCreateSerializer, FlowerTagSerializer)


class BotTokenPermission(IsAuthenticatedOrReadOnly):
    def has_permission(self, request, view):
        token = request.headers.get('X-Bot-Token', '')
        expected = getattr(settings, 'TELEGRAM_BOT_SECRET', '')
        return bool(token and expected and token == expected)


def home_page(request):
    def normalize_public_url(raw_url):
        if not raw_url:
            return ""
        if raw_url.startswith("/"):
            return raw_url
        parsed = urlsplit(raw_url)
        if parsed.scheme and parsed.netloc and parsed.path:
            return parsed.path
        return raw_url

    def product_image_url(product):
        if product.uploaded_image:
            return product.uploaded_image.url
        if product.image:
            return normalize_public_url(product.image)
        return "/static/legacy-old/image/no_image.jpg"

    today = timezone.localdate()
    hero_banners = HeroBanner.objects.filter(is_active=True).order_by("sort_order", "-created_at")
    active_banners = []
    for banner in hero_banners:
        starts_ok = banner.starts_on is None or banner.starts_on <= today
        ends_ok = banner.ends_on is None or banner.ends_on >= today
        if starts_ok and ends_ok:
            active_banners.append(banner)

    showcase_products = list(
        Product.objects.filter(is_online_showcase=True, is_published=True)
        .select_related("category")
        .prefetch_related("stores")
        .order_by("showcase_sort_order", "-id")[:24]
    )

    categories = Category.objects.filter(parent__isnull=True).prefetch_related(
        Prefetch(
            "products",
            queryset=Product.objects.filter(is_published=True).order_by("-id"),
        )
    ).order_by("sort_order", "name")

    category_cards = []
    for category in categories:
        products = list(category.products.all())
        if not products:
            continue
        primary = products[0]
        secondary = products[1] if len(products) > 1 else products[0]
        category_cards.append(
            {
                "id": category.id,
                "name": category.name,
                "slug": category.slug,
                "image": product_image_url(primary),
                "hover_image": product_image_url(secondary),
                "href": f"/store/category/{category.slug}/" if category.slug else f"/store/?category={quote(category.name)}",
            }
        )

    showcase_cards = [
        {
            "id": p.id,
            "slug": p.slug,
            "title": p.title.replace("/", " ").replace("\\", " ").strip(),
            "price": p.price,
            "image": product_image_url(p),
            "hover_image": normalize_public_url(p.image) if p.image else product_image_url(p),
            "href": f"/store/{p.slug}/" if p.slug else f"/store/{p.id}/",
        }
        for p in showcase_products
    ]

    reviews = Review.objects.filter(is_published=True).order_by("sort_order", "-created_at")[:6]
    stores = Store.objects.filter(is_active=True).order_by("name")
    return render(
        request,
        "shop/home.html",
        {
            "active_banners": active_banners,
            "category_cards": category_cards,
            "showcase_cards": showcase_cards,
            "reviews": reviews,
            "stores": stores,
        },
    )


def store_page(request):
    def normalize_public_url(raw_url):
        if not raw_url:
            return ""
        if raw_url.startswith("/"):
            return raw_url
        parsed = urlsplit(raw_url)
        if parsed.scheme and parsed.netloc and parsed.path:
            return parsed.path
        return raw_url

    # 301 редиректы с query-param URLs на ЧПУ
    category_name = (request.GET.get("category") or "").strip()
    flower_tag_name = (request.GET.get("flower_tag") or "").strip()
    if category_name:
        cat = Category.objects.filter(name=category_name).first()
        if cat and cat.slug:
            url = f'/store/category/{cat.slug}/'
            if flower_tag_name:
                tag = FlowerTag.objects.filter(name=flower_tag_name).first()
                if tag and tag.slug:
                    url = f'/store/category/{cat.slug}/?flower_tag_slug={tag.slug}'
            return redirect(url, permanent=True)
    if flower_tag_name:
        tag = FlowerTag.objects.filter(name=flower_tag_name).first()
        if tag and tag.slug:
            return redirect(f'/store/flower/{tag.slug}/', permanent=True)

    categories = Category.objects.filter(parent__isnull=True).prefetch_related("children").order_by("sort_order", "name")
    flower_tags = FlowerTag.objects.order_by("sort_order", "name")
    products_qs = Product.objects.filter(is_published=True).select_related("category").prefetch_related("stores", "categories").order_by("-id")
    products = _build_product_list(products_qs, normalize_public_url)

    return render(request, "shop/store.html", {
        "products": products,
        "categories": categories,
        "selected_category": "",
        "selected_category_slug": "",
        "flower_tags": flower_tags,
        "selected_flower_tag": "",
        "selected_flower_slug": "",
    })


def _build_product_list(products_qs, normalize_fn):
    products = []
    for p in products_qs:
        if p.uploaded_image:
            image_url = p.uploaded_image.url
        elif p.image:
            image_url = normalize_fn(p.image)
        else:
            image_url = "/static/hero/today-desktop.svg"
        products.append({
            "id": p.id,
            "slug": p.slug,
            "title": p.title.replace("/", " ").replace("\\", " ").strip(),
            "price": p.price,
            "image_url": image_url,
        })
    return products


def store_page_category(request, slug):
    def normalize_public_url(raw_url):
        if not raw_url:
            return ""
        if raw_url.startswith("/"):
            return raw_url
        parsed = urlsplit(raw_url)
        if parsed.scheme and parsed.netloc and parsed.path:
            return parsed.path
        return raw_url

    cat = get_object_or_404(Category, slug=slug)
    # Собираем ID: сама категория + все дочерние
    child_ids = list(cat.children.values_list("id", flat=True))
    cat_ids = [cat.id] + child_ids

    products_qs = Product.objects.filter(is_published=True)\
        .select_related("category").prefetch_related("stores", "categories")\
        .filter(Q(category__id__in=cat_ids) | Q(categories__id__in=cat_ids))\
        .distinct().order_by("-id")

    # Дополнительный фильтр по цветку (комбинированный)
    flower_slug = (request.GET.get("flower_tag_slug") or "").strip()
    selected_flower_tag = ""
    selected_flower_slug = ""
    if flower_slug:
        tag = FlowerTag.objects.filter(slug=flower_slug).first()
        if tag:
            products_qs = products_qs.filter(flower_tags=tag).distinct()
            selected_flower_tag = tag.name
            selected_flower_slug = tag.slug

    categories = Category.objects.filter(parent__isnull=True).prefetch_related("children").order_by("sort_order", "name")
    flower_tags = FlowerTag.objects.order_by("sort_order", "name")
    products = _build_product_list(products_qs, normalize_public_url)

    return render(request, "shop/store.html", {
        "products": products,
        "categories": categories,
        "selected_category": cat.name,
        "selected_category_slug": slug,
        "flower_tags": flower_tags,
        "selected_flower_tag": selected_flower_tag,
        "selected_flower_slug": selected_flower_slug,
    })


def store_page_flower(request, slug):
    def normalize_public_url(raw_url):
        if not raw_url:
            return ""
        if raw_url.startswith("/"):
            return raw_url
        parsed = urlsplit(raw_url)
        if parsed.scheme and parsed.netloc and parsed.path:
            return parsed.path
        return raw_url

    tag = get_object_or_404(FlowerTag, slug=slug)
    products_qs = Product.objects.filter(is_published=True)\
        .select_related("category").prefetch_related("stores", "categories")\
        .filter(flower_tags=tag).distinct().order_by("-id")

    categories = Category.objects.filter(parent__isnull=True).prefetch_related("children").order_by("sort_order", "name")
    flower_tags = FlowerTag.objects.order_by("sort_order", "name")
    products = _build_product_list(products_qs, normalize_public_url)

    return render(request, "shop/store.html", {
        "products": products,
        "categories": categories,
        "selected_category": "",
        "selected_category_slug": "",
        "flower_tags": flower_tags,
        "selected_flower_tag": tag.name,
        "selected_flower_slug": slug,
    })


def product_page(request, slug):
    def normalize_public_url(raw_url):
        if not raw_url:
            return ""
        if raw_url.startswith("/"):
            return raw_url
        parsed = urlsplit(raw_url)
        if parsed.scheme and parsed.netloc and parsed.path:
            return parsed.path
        return raw_url

    product = get_object_or_404(
        Product.objects.select_related("category").prefetch_related("stores", "flower_tags"),
        slug=slug,
        is_published=True,
    )
    if product.uploaded_image:
        image_url = product.uploaded_image.url
    elif product.image:
        image_url = normalize_public_url(product.image)
    else:
        image_url = "/static/hero/today-desktop.svg"
    return render(request, "shop/product.html", {"product": product, "image_url": image_url})


def product_page_by_id(request, product_id):
    """301 редирект со старого /store/<id>/ на /store/<slug>/"""
    product = get_object_or_404(Product, id=product_id, is_published=True)
    return redirect(f'/store/{product.slug}/', permanent=True)


def old_product_redirect(request, slug):
    """301 редирект со старого /katalog/<slug>.html на /store/<slug>/"""
    product = get_object_or_404(Product, slug=slug, is_published=True)
    return redirect(f'/store/{product.slug}/', permanent=True)


def categories_page(request):
    categories = Category.objects.prefetch_related("products").order_by("name")
    return render(request, "shop/categories.html", {"categories": categories})


def reviews_page(request):
    reviews = Review.objects.filter(is_published=True).order_by("sort_order", "-created_at")
    return render(request, "shop/reviews.html", {"reviews": reviews})


def site_page(request, slug):
    from shop.models import SitePage
    page = get_object_or_404(SitePage, slug=slug, is_active=True)
    return render(request, "shop/site_page.html", {"page": page})


def contacts_page(request):
    from shop.models import Store
    stores = Store.objects.filter(is_active=True).prefetch_related('phones', 'photos').order_by('sort_order', 'name')
    return render(request, "shop/contacts.html", {"stores": stores})


@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request, format=None):
    return Response({
        'products': reverse('product-list', request=request, format=format),
        'orders': reverse('order-list', request=request, format=format),
        'discounts': reverse('discount-list', request=request, format=format),
        'categories': reverse('category-list', request=request, format=format),
        'reviews': reverse('review-list', request=request, format=format),
        'hero_banners': reverse('hero-banner-list', request=request, format=format),
        'hero_banner_current': reverse('hero-banner-current', request=request, format=format),
        'review_submit': reverse('review-submit', request=request, format=format),
        'register': reverse('auth_register', request=request, format=format),
        'login': reverse('token_obtain_pair', request=request, format=format),
    })


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = Product.objects.all().select_related("category").prefetch_related("stores", "flower_tags")
        category = self.request.query_params.get("category")
        online_showcase = self.request.query_params.get("online_showcase")
        store_subdomain = self.request.query_params.get("store__subdomain")
        flower_tag = self.request.query_params.get("flower_tag")

        if category:
            queryset = queryset.filter(category__name=category)
        if store_subdomain is not None:
            queryset = queryset.filter(stores__subdomain=store_subdomain)
        if flower_tag:
            queryset = queryset.filter(flower_tags__name=flower_tag)

        showcase_enabled = bool(online_showcase and online_showcase.lower() in ("1", "true", "yes"))
        if showcase_enabled:
            queryset = queryset.filter(is_online_showcase=True)
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(is_published=True)

        if showcase_enabled:
            queryset = queryset.order_by('showcase_sort_order', '-id')
        return queryset.distinct()

    def perform_create(self, serializer):
        instance = serializer.save()
        if instance.uploaded_image and not instance.image:
            instance.image = self.request.build_absolute_uri(instance.uploaded_image.url)
            instance.save(update_fields=['image'])


class StoreViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Store.objects.filter(is_active=True)
    serializer_class = StoreSerializer
    permission_classes = [AllowAny]


class FlowerTagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FlowerTag.objects.all()
    serializer_class = FlowerTagSerializer
    permission_classes = [AllowAny]


class BotProductCreateView(CreateAPIView):
    serializer_class = BotProductCreateSerializer
    permission_classes = [BotTokenPermission]
    parser_classes = (MultiPartParser, FormParser)

    def perform_create(self, serializer):
        instance = serializer.save()
        if instance.uploaded_image:
            instance.image = self.request.build_absolute_uri(instance.uploaded_image.url)
            if not instance.article:
                first_store = instance.stores.order_by('id').first()
                store_slug = first_store.subdomain if first_store else 'main'
                instance.article = slugify(f"{store_slug}-{instance.id}")[:64]
            instance.save(update_fields=['image', 'article'])


class BotAuthView(APIView):
    permission_classes = [BotTokenPermission]

    def post(self, request):
        telegram_id = request.data.get('telegram_id')
        if not telegram_id:
            return Response({'detail': 'telegram_id is required'}, status=400)

        manager = StoreManager.objects.filter(telegram_id=telegram_id, is_active=True).first()
        if not manager:
            return Response({'detail': 'Unauthorized'}, status=403)
        data = StoreManagerSerializer(manager).data
        return Response(data, status=200)


class DiscountViewSet(viewsets.ModelViewSet):
    queryset = Discount.objects.all()
    serializer_class = DiscountSerializer


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = Review.objects.all()
        if self.request.user.is_authenticated:
            return queryset
        return queryset.filter(is_published=True)


class ReviewSubmitView(CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = PublicReviewCreateSerializer


class HeroBannerViewSet(viewsets.ModelViewSet):
    queryset = HeroBanner.objects.all()
    serializer_class = HeroBannerSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    parser_classes = (MultiPartParser, FormParser)


@api_view(['GET'])
@permission_classes([AllowAny])
def hero_banner_current(request):
    today = timezone.localdate()
    banners = HeroBanner.objects.filter(is_active=True).order_by('sort_order', '-created_at')

    current = None
    for banner in banners:
        starts_ok = banner.starts_on is None or banner.starts_on <= today
        ends_ok = banner.ends_on is None or banner.ends_on >= today
        if starts_ok and ends_ok:
            current = banner
            break

    if current is None:
        return Response({}, status=200)

    serializer = HeroBannerSerializer(current)
    return Response(serializer.data, status=200)


# SIGN_UP AND LOGIN
class RegisterView(CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer


class TokenObtainPairViewSet(TokenObtainPairView):
    permission_classes = (AllowAny,)
    serializer_class = TokenObtainPairSerializer


class UserProfileViewSet(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


# ─── КОРЗИНА (сессии, гостевая) ───────────────────────────────────────────────

def _get_cart(request):
    """Вернуть корзину из сессии: {str(product_id): qty}"""
    return request.session.get('cart', {})


def _save_cart(request, cart):
    request.session['cart'] = cart
    request.session.modified = True


def _normalize_public_url(raw_url, request=None):
    if not raw_url:
        return ""
    if raw_url.startswith("/"):
        return raw_url
    parsed = urlsplit(raw_url)
    if parsed.scheme and parsed.netloc and parsed.path:
        # Берём только путь — работает на любом домене/порту
        return parsed.path
    return raw_url


def _product_image_url(product, request):
    if product.uploaded_image:
        return product.uploaded_image.url
    if product.image:
        return _normalize_public_url(product.image, request)
    return "/static/hero/today-desktop.svg"


def cart_page(request):
    """Страница корзины."""
    cart = _get_cart(request)
    if not cart:
        return render(request, 'shop/cart.html', {'items': [], 'total': 0})

    product_ids = [int(k) for k in cart.keys()]
    products = Product.objects.filter(id__in=product_ids, is_published=True).select_related('category')

    items = []
    total = 0
    for product in products:
        qty = cart.get(str(product.id), 0)
        if qty <= 0:
            continue
        price = product.price or 0
        line_total = price * qty
        total += line_total
        items.append({
            'id': product.id,
            'title': product.title,
            'price': price,
            'image_url': _product_image_url(product, request),
            'qty': qty,
            'line_total': line_total,
        })

    return render(request, 'shop/cart.html', {'items': items, 'total': total})


@require_POST
def cart_add(request, product_id):
    """Добавить товар в корзину или увеличить количество."""
    product = get_object_or_404(Product, id=product_id, is_published=True)
    cart = _get_cart(request)
    key = str(product_id)
    cart[key] = min(cart.get(key, 0) + 1, 99)
    _save_cart(request, cart)
    return JsonResponse({'ok': True, 'qty': cart[key], 'cart_count': sum(cart.values())})


@require_POST
def cart_update(request, product_id):
    """Установить конкретное количество товара."""
    try:
        data = json.loads(request.body)
        qty = int(data.get('qty', 1))
    except (ValueError, json.JSONDecodeError):
        return JsonResponse({'ok': False, 'error': 'invalid qty'}, status=400)

    cart = _get_cart(request)
    key = str(product_id)
    if qty <= 0:
        cart.pop(key, None)
    else:
        cart[key] = min(qty, 99)
    _save_cart(request, cart)
    return JsonResponse({'ok': True, 'qty': cart.get(key, 0), 'cart_count': sum(cart.values())})


@require_POST
def cart_remove(request, product_id):
    """Удалить товар из корзины."""
    cart = _get_cart(request)
    cart.pop(str(product_id), None)
    _save_cart(request, cart)
    return JsonResponse({'ok': True, 'cart_count': sum(cart.values())})


def cart_count(request):
    """Вернуть общее кол-во позиций в корзине (для бейджа в хедере)."""
    cart = _get_cart(request)
    return JsonResponse({'cart_count': sum(cart.values())})


def cart_drawer(request):
    """Вернуть данные корзины для мини-корзины (drawer) в формате JSON."""
    cart = _get_cart(request)
    if not cart:
        return JsonResponse({'items': [], 'cart_count': 0})

    product_ids = [int(k) for k in cart.keys()]
    products = Product.objects.filter(id__in=product_ids, is_published=True).select_related('category')

    items = []
    for product in products:
        qty = cart.get(str(product.id), 0)
        if qty <= 0:
            continue
        items.append({
            'id': product.id,
            'title': product.title,
            'price': float(product.price) if product.price is not None else None,
            'image_url': _product_image_url(product, request),
            'qty': qty,
        })

    return JsonResponse({'items': items, 'cart_count': sum(cart.values())})


@require_POST
def cart_checkout(request):
    """Оформить заказ: сохранить контакт в сессии, очистить корзину."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Ошибка данных'}, status=400)

    name = (data.get('name') or '').strip()
    phone = (data.get('phone') or '').strip()
    comment = (data.get('comment') or '').strip()

    if not name or not phone:
        return JsonResponse({'ok': False, 'error': 'Укажите имя и телефон'}, status=400)

    cart = _get_cart(request)
    if not cart:
        return JsonResponse({'ok': False, 'error': 'Корзина пуста'}, status=400)

    # Сохраняем заказ в сессии
    request.session['last_order'] = {
        'name': name,
        'phone': phone,
        'comment': comment,
        'items': cart,
    }

    # Очищаем корзину
    _save_cart(request, {})

    return JsonResponse({'ok': True})


# ─── ДАШБОРД ─────────────────────────────────────────────────────────────────

from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib import messages
from django.core.files.storage import default_storage
import decimal


def _dash_product_image(product, request):
    if product.uploaded_image:
        return product.uploaded_image.url
    if product.image:
        return _normalize_public_url(product.image, request)
    return "/static/hero/today-desktop.svg"


@login_required(login_url='/admin/login/')
def dashboard_products(request):
    products_qs = Product.objects.select_related('category').prefetch_related('stores').order_by('-id')
    products = []
    for p in products_qs:
        products.append({
            'id': p.id,
            'title': p.title,
            'article': p.article or '',
            'price': p.price,
            'category_name': p.category.name if p.category else '',
            'is_published': p.is_published,
            'is_online_showcase': p.is_online_showcase,
            'image_url': _dash_product_image(p, request),
        })
    return render(request, 'shop/dashboard/products.html', {'products': products, 'active': 'products'})


@login_required(login_url='/admin/login/')
def dashboard_product_form(request, product_id=None):
    product = None
    product_store_ids = []
    if product_id:
        product = get_object_or_404(Product, id=product_id)
        product_store_ids = list(product.stores.values_list('id', flat=True))

    categories = Category.objects.order_by('sort_order', 'name')
    stores = Store.objects.filter(is_active=True).order_by('name')

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if not title:
            messages.error(request, 'Название обязательно')
            return render(request, 'shop/dashboard/product_form.html', {
                'product': product, 'categories': categories, 'stores': stores,
                'product_store_ids': product_store_ids, 'active': 'products'
            })

        price_raw = request.POST.get('price', '0')
        try:
            price = decimal.Decimal(price_raw)
        except Exception:
            price = decimal.Decimal('0')

        cat_id = request.POST.get('category') or None
        category = None
        if cat_id:
            try:
                category = Category.objects.get(id=int(cat_id))
            except (Category.DoesNotExist, ValueError):
                pass

        data = {
            'title': title,
            'price': price,
            'article': request.POST.get('article', '').strip(),
            'description': request.POST.get('description', '').strip(),
            'image': request.POST.get('image', '').strip(),
            'is_published': 'is_published' in request.POST,
            'is_online_showcase': 'is_online_showcase' in request.POST,
            'showcase_sort_order': int(request.POST.get('showcase_sort_order', 0) or 0),
            'category': category,
        }

        if product_id:
            for k, v in data.items():
                setattr(product, k, v)
            if request.FILES.get('uploaded_image'):
                product.uploaded_image = request.FILES['uploaded_image']
            product.save()
            store_ids = [int(x) for x in request.POST.getlist('stores') if x]
            product.stores.set(Store.objects.filter(id__in=store_ids))
            messages.success(request, 'Товар сохранён')
            return render(request, 'shop/dashboard/product_form.html', {
                'product': product, 'categories': categories, 'stores': stores,
                'product_store_ids': list(product.stores.values_list('id', flat=True)),
                'active': 'products'
            })
        else:
            product = Product(**data)
            if request.FILES.get('uploaded_image'):
                product.uploaded_image = request.FILES['uploaded_image']
            product.save()
            store_ids = [int(x) for x in request.POST.getlist('stores') if x]
            product.stores.set(Store.objects.filter(id__in=store_ids))
            messages.success(request, 'Товар добавлен')
            from django.shortcuts import redirect
            return redirect(f'/dashboard/products/{product.id}/')

    return render(request, 'shop/dashboard/product_form.html', {
        'product': product, 'categories': categories, 'stores': stores,
        'product_store_ids': product_store_ids, 'active': 'products'
    })


@login_required(login_url='/admin/login/')
def dashboard_hero(request):
    from django.core import serializers as dj_serializers
    import json as _json
    banners = HeroBanner.objects.order_by('sort_order', '-created_at')
    banners_data = []
    for b in banners:
        banners_data.append({
            'id': b.id,
            'name': b.name,
            'title': b.title or '',
            'caption': b.caption or '',
            'overview': b.overview or '',
            'button_text': b.button_text or '',
            'button_url': b.button_url or '',
            'desktop_image': b.desktop_image_url,
            'mobile_image': b.mobile_image_url,
            'starts_on': b.starts_on.isoformat() if b.starts_on else '',
            'ends_on': b.ends_on.isoformat() if b.ends_on else '',
            'sort_order': b.sort_order,
            'is_active': b.is_active,
        })
    return render(request, 'shop/dashboard/hero.html', {
        'banners': banners,
        'banners_json': _json.dumps(banners_data, ensure_ascii=False),
        'active': 'hero'
    })


@login_required(login_url='/admin/login/')
def dashboard_showcase(request):
    showcase_qs = Product.objects.filter(is_online_showcase=True, is_published=True).order_by('showcase_sort_order', '-id')
    all_qs = Product.objects.filter(is_published=True).select_related('category').order_by('-id')

    showcase_products = []
    for p in showcase_qs:
        showcase_products.append({
            'id': p.id,
            'title': p.title,
            'price': p.price,
            'showcase_sort_order': p.showcase_sort_order,
            'image_url': _dash_product_image(p, request),
            'is_online_showcase': p.is_online_showcase,
        })

    all_products = []
    for p in all_qs:
        all_products.append({
            'id': p.id,
            'title': p.title,
            'price': p.price,
            'image_url': _dash_product_image(p, request),
            'is_online_showcase': p.is_online_showcase,
        })

    return render(request, 'shop/dashboard/showcase.html', {
        'showcase_products': showcase_products,
        'all_products': all_products,
        'active': 'showcase'
    })


@login_required(login_url='/admin/login/')
def dashboard_categories(request):
    categories = Category.objects.prefetch_related('products').select_related('parent').order_by('sort_order', 'name')
    cats_data = []
    for cat in categories:
        cats_data.append({
            'id': cat.id,
            'name': cat.name,
            'parent': cat.parent,
            'sort_order': cat.sort_order,
            'products_count': cat.products.count(),
        })
    root_categories = Category.objects.filter(parent__isnull=True).order_by('sort_order', 'name')
    return render(request, 'shop/dashboard/categories.html', {
        'categories': cats_data,
        'root_categories': root_categories,
        'active': 'categories'
    })


@login_required(login_url='/admin/login/')
def dashboard_profile(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', '').strip()
        user.last_name = request.POST.get('last_name', '').strip()
        user.email = request.POST.get('email', '').strip()
        username = request.POST.get('username', '').strip()
        if username:
            user.username = username
        user.save()
        messages.success(request, 'Профиль обновлён')
    return render(request, 'shop/dashboard/profile.html', {'active': 'profile'})


@login_required(login_url='/admin/login/')
def dashboard_profile_password(request):
    if request.method == 'POST':
        old = request.POST.get('old_password', '')
        new = request.POST.get('new_password', '')
        confirm = request.POST.get('confirm_password', '')
        if new != confirm:
            messages.error(request, 'Пароли не совпадают')
        elif not request.user.check_password(old):
            messages.error(request, 'Неверный текущий пароль')
        else:
            request.user.set_password(new)
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Пароль изменён')
    from django.shortcuts import redirect
    return redirect('/dashboard/profile/')


def dashboard_logout(request):
    if request.method == 'POST':
        logout(request)
    from django.shortcuts import redirect
    return redirect('/admin/login/')


# ─── DASHBOARD API (JSON endpoints) ──────────────────────────────────────────

@login_required(login_url='/admin/login/')
@require_POST
def dash_api_product_price(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    try:
        data = json.loads(request.body)
        price = decimal.Decimal(str(data['price']))
        if price < 0:
            raise ValueError
    except Exception:
        return JsonResponse({'ok': False, 'error': 'Неверная цена'}, status=400)
    product.price = price
    product.save(update_fields=['price'])
    return JsonResponse({'ok': True})


@login_required(login_url='/admin/login/')
@require_POST
def dash_api_product_showcase(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    try:
        data = json.loads(request.body)
        value = bool(data.get('value'))
    except Exception:
        return JsonResponse({'ok': False, 'error': 'bad data'}, status=400)
    product.is_online_showcase = value
    product.save(update_fields=['is_online_showcase'])
    return JsonResponse({'ok': True})


@login_required(login_url='/admin/login/')
@require_POST
def dash_api_product_published(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    try:
        data = json.loads(request.body)
        value = bool(data.get('value'))
    except Exception:
        return JsonResponse({'ok': False, 'error': 'bad data'}, status=400)
    product.is_published = value
    product.save(update_fields=['is_published'])
    return JsonResponse({'ok': True})


@login_required(login_url='/admin/login/')
@require_POST
def dash_api_product_delete(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.delete()
    return JsonResponse({'ok': True})


@login_required(login_url='/admin/login/')
@require_POST
def dash_api_showcase_order(request):
    try:
        data = json.loads(request.body)
        items = data.get('items', [])
    except Exception:
        return JsonResponse({'ok': False, 'error': 'bad data'}, status=400)
    for item in items:
        Product.objects.filter(id=item['id']).update(showcase_sort_order=item.get('sort', 0))
    return JsonResponse({'ok': True})


@login_required(login_url='/admin/login/')
@require_POST
def dash_api_banner_create(request):
    data = request.POST if request.POST else None
    if data is None:
        try:
            data = json.loads(request.body)
        except Exception:
            return JsonResponse({'ok': False, 'error': 'bad data'}, status=400)

    if not data.get('name'):
        return JsonResponse({'ok': False, 'error': 'Название обязательно'}, status=400)

    desktop_image = request.FILES.get('desktop_image')
    mobile_image = request.FILES.get('mobile_image')
    if not desktop_image and not data.get('desktop_image'):
        return JsonResponse({'ok': False, 'error': 'Загрузите desktop изображение'}, status=400)

    is_active_value = str(data.get('is_active', True)).lower() in ('1', 'true', 'yes', 'on')
    try:
        sort_order_value = int(data.get('sort_order', 0))
    except Exception:
        sort_order_value = 0

    banner = HeroBanner(
        name=data['name'],
        title=data.get('title', ''),
        caption=data.get('caption', ''),
        overview=data.get('overview', ''),
        button_text=data.get('button_text', ''),
        button_url=data.get('button_url', ''),
        desktop_image=data.get('desktop_image', ''),
        sort_order=sort_order_value,
        is_active=is_active_value,
    )
    if mobile_image:
        banner.mobile_image = mobile_image
    elif data.get('mobile_image'):
        banner.mobile_image = data.get('mobile_image')
    if desktop_image:
        banner.desktop_image = desktop_image

    if data.get('starts_on'):
        try:
            banner.starts_on = date.fromisoformat(data['starts_on'])
        except Exception:
            pass
    if data.get('ends_on'):
        try:
            banner.ends_on = date.fromisoformat(data['ends_on'])
        except Exception:
            pass
    banner.save()
    return JsonResponse({'ok': True, 'id': banner.id})


@login_required(login_url='/admin/login/')
@require_POST
def dash_api_banner_save(request, banner_id):
    banner = get_object_or_404(HeroBanner, id=banner_id)
    data = request.POST if request.POST else None
    if data is None:
        try:
            data = json.loads(request.body)
        except Exception:
            return JsonResponse({'ok': False, 'error': 'bad data'}, status=400)

    if not data.get('name'):
        return JsonResponse({'ok': False, 'error': 'Название обязательно'}, status=400)

    is_active_value = str(data.get('is_active', True)).lower() in ('1', 'true', 'yes', 'on')
    try:
        sort_order_value = int(data.get('sort_order', 0))
    except Exception:
        sort_order_value = 0

    banner.name = data['name']
    banner.title = data.get('title', '')
    banner.caption = data.get('caption', '')
    banner.overview = data.get('overview', '')
    banner.button_text = data.get('button_text', '')
    banner.button_url = data.get('button_url', '')

    desktop_image = request.FILES.get('desktop_image')
    mobile_image = request.FILES.get('mobile_image')
    if desktop_image:
        banner.desktop_image = desktop_image
    elif data.get('desktop_image'):
        banner.desktop_image = data.get('desktop_image')
    if mobile_image:
        banner.mobile_image = mobile_image
    elif data.get('mobile_image'):
        banner.mobile_image = data.get('mobile_image')

    banner.sort_order = sort_order_value
    banner.is_active = is_active_value
    banner.starts_on = None
    banner.ends_on = None
    if data.get('starts_on'):
        try:
            banner.starts_on = date.fromisoformat(data['starts_on'])
        except Exception:
            pass
    if data.get('ends_on'):
        try:
            banner.ends_on = date.fromisoformat(data['ends_on'])
        except Exception:
            pass
    banner.save()
    return JsonResponse({'ok': True})


@login_required(login_url='/admin/login/')
@require_POST
def dash_api_banner_delete(request, banner_id):
    banner = get_object_or_404(HeroBanner, id=banner_id)
    banner.delete()
    return JsonResponse({'ok': True})


@login_required(login_url='/admin/login/')
@require_POST
def dash_api_category_create(request):
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'ok': False, 'error': 'bad json'}, status=400)
    name = (data.get('name') or '').strip()
    if not name:
        return JsonResponse({'ok': False, 'error': 'Название обязательно'}, status=400)
    parent = None
    if data.get('parent'):
        try:
            parent = Category.objects.get(id=int(data['parent']))
        except (Category.DoesNotExist, ValueError):
            pass
    cat = Category(name=name, parent=parent, sort_order=data.get('sort_order', 0))
    try:
        cat.save()
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)
    return JsonResponse({'ok': True, 'id': cat.id})


@login_required(login_url='/admin/login/')
@require_POST
def dash_api_category_sort(request, cat_id):
    cat = get_object_or_404(Category, id=cat_id)
    try:
        data = json.loads(request.body)
        cat.sort_order = int(data.get('sort_order', 0))
        cat.save(update_fields=['sort_order'])
    except Exception:
        return JsonResponse({'ok': False}, status=400)
    return JsonResponse({'ok': True})


@login_required(login_url='/admin/login/')
@require_POST
def dash_api_category_delete(request, cat_id):
    cat = get_object_or_404(Category, id=cat_id)
    cat.delete()
    return JsonResponse({'ok': True})
