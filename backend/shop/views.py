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
from .models import Product, Discount, Order, Category, Review, HeroBanner, Store, StoreManager, FlowerTag, ShowcaseItem, Ticker, SiteSettings, GuestOrder, GuestOrderItem
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

    # Витрины по магазинам через ShowcaseItem
    active_stores = Store.objects.filter(is_active=True).order_by("sort_order", "name")
    store_showcases = []
    for store in active_stores:
        items_qs = list(
            ShowcaseItem.objects.filter(store=store, product__is_published=True)
            .select_related('product')
            .order_by("sort_order", "-id")[:8]
        )
        if not items_qs:
            continue
        cards = [
            {
                "id": item.product.id,
                "slug": item.product.slug,
                "title": item.product.title.replace("/", " ").replace("\\", " ").strip(),
                "price": item.product.price,
                "image": product_image_url(item.product),
                "hover_image": normalize_public_url(item.product.image) if item.product.image else product_image_url(item.product),
                "href": f"/store/{item.product.slug}/" if item.product.slug else f"/store/{item.product.id}/",
            }
            for item in items_qs
        ]
        store_showcases.append({
            "store": store,
            "cards": cards,
        })

    # Единая витрина (fallback) — все магазины вместе, если нет разбивки
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
            "store_showcases": store_showcases,
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
    submitted = False
    error = None
    all_stores = Store.objects.filter(is_active=True).order_by('sort_order', 'name')
    if request.method == 'POST':
        author = request.POST.get('author', '').strip()
        text = request.POST.get('text', '').strip()
        rating = request.POST.get('rating', '5')
        company = request.POST.get('company', '').strip()
        store_id = request.POST.get('store', '').strip()
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                raise ValueError
        except (ValueError, TypeError):
            rating = 5
        store_obj = None
        if store_id:
            try:
                store_obj = Store.objects.get(id=int(store_id), is_active=True)
            except (Store.DoesNotExist, ValueError):
                pass
        if author and text:
            Review.objects.create(
                author=author,
                company=company,
                text=text,
                rating=rating,
                store=store_obj,
                is_published=False,
            )
            submitted = True
        else:
            error = 'Пожалуйста, заполните имя и текст отзыва.'
    reviews = Review.objects.filter(is_published=True).select_related('store').order_by("sort_order", "-created_at")
    return render(request, "shop/reviews.html", {"reviews": reviews, "submitted": submitted, "error": error, "all_stores": all_stores})


def site_page(request, slug):
    from shop.models import SitePage
    page = get_object_or_404(SitePage, slug=slug, is_active=True)
    return render(request, "shop/site_page.html", {"page": page})


def contacts_page(request):
    from shop.models import Store
    stores = Store.objects.filter(is_active=True).prefetch_related('phones', 'photos').order_by('sort_order', 'name')
    return render(request, "shop/contacts.html", {"stores": stores})


def robots_txt(request):
    return render(request, "shop/robots.txt", content_type="text/plain; charset=utf-8")


def sitemap_xml(request):
    from django.http import HttpResponse
    categories = Category.objects.filter(parent__isnull=True).prefetch_related('children').order_by('sort_order', 'name')
    flower_tags = FlowerTag.objects.filter(slug__gt='').order_by('sort_order', 'name')
    products = Product.objects.filter(is_published=True, slug__gt='').order_by('-id')
    ctx = {
        'categories': categories,
        'flower_tags': flower_tags,
        'products': products,
    }
    content = render(request, "shop/sitemap.xml", ctx).content
    return HttpResponse(content, content_type="application/xml; charset=utf-8")


def error_404(request, exception=None):
    """Кастомная страница 404."""
    from django.shortcuts import render as _render
    return _render(request, '404.html', status=404)


def error_500(request):
    """Кастомная страница 500."""
    from django.shortcuts import render as _render
    return _render(request, '500.html', status=500)


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
    settings_obj = SiteSettings.get()
    stores = Store.objects.filter(is_active=True).order_by('sort_order', 'name')

    if not cart:
        return render(request, 'shop/cart.html', {
            'items': [], 'total': 0,
            'settings': settings_obj,
            'stores': stores,
        })

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

    import decimal
    delivery_cost = settings_obj.delivery_cost if total < settings_obj.delivery_free_from else decimal.Decimal('0')

    return render(request, 'shop/cart.html', {
        'items': items,
        'total': total,
        'delivery_cost': delivery_cost,
        'order_total': total + delivery_cost,
        'settings': settings_obj,
        'stores': stores,
    })


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


def _send_order_notifications(order_pk, notification_text, order_items_data,
                               subtotal, delivery_cost, total,
                               delivery_type, delivery_address, pretty_datetime,
                               pickup_store_name, pickup_store_address,
                               recipient_name, recipient_phone, comment,
                               payment_type, name, phone, email):
    """
    Отправляет email и Telegram-уведомление о заказе.
    Вызывается в отдельном потоке, чтобы не блокировать ответ покупателю.
    """
    import logging as _logging
    _log = _logging.getLogger(__name__)

    settings_obj = SiteSettings.get()
    order = GuestOrder.objects.filter(pk=order_pk).first()
    if not order:
        return

    # Email
    if settings_obj.notification_email:
        try:
            import smtplib
            import urllib.request as _urlreq
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText as _MIMEText
            from email.mime.image import MIMEImage
            from email.header import Header

            _host = getattr(settings, 'EMAIL_HOST', 'smtp.yandex.ru')
            _port = getattr(settings, 'EMAIL_PORT', 587)
            _user = getattr(settings, 'EMAIL_HOST_USER', '')
            _pwd  = getattr(settings, 'EMAIL_HOST_PASSWORD', '')
            _from = getattr(settings, 'DEFAULT_FROM_EMAIL', _user)
            _to   = settings_obj.notification_email

            pay_label = 'Наличные' if payment_type == 'cash' else 'Картой online'
            html_rows = ''
            inline_images = []
            for idx, item_data in enumerate(order_items_data):
                p = item_data['product']
                article_str = p.article or '—'
                cid = f'img{idx}'
                img_path = None
                img_url_str = None
                if p.uploaded_image:
                    try:
                        img_path = p.uploaded_image.path
                    except Exception:
                        pass
                if not img_path and p.image:
                    img_url_str = p.image if p.image.startswith('http') else None
                img_tag = f'<img src="cid:{cid}" style="width:80px;height:80px;object-fit:cover;border-radius:4px;">'
                html_rows += f'''<tr>
  <td style="padding:8px;border-bottom:1px solid #eee;vertical-align:top;">{img_tag}</td>
  <td style="padding:8px;border-bottom:1px solid #eee;vertical-align:top;">
    <b>{item_data["title"]}</b><br>
    <span style="color:#888;font-size:12px;">Арт.: {article_str}</span>
  </td>
  <td style="padding:8px;border-bottom:1px solid #eee;text-align:center;vertical-align:top;">{item_data["qty"]}</td>
  <td style="padding:8px;border-bottom:1px solid #eee;text-align:right;vertical-align:top;">{item_data["price"] * item_data["qty"]:.2f} BYN</td>
</tr>'''
                inline_images.append({'cid': cid, 'path': img_path, 'url': img_url_str})

            delivery_row = ''
            if delivery_type == 'delivery':
                delivery_row = f'<tr><td colspan="3" style="text-align:right;padding:4px 8px;color:#555;">Доставка:</td><td style="text-align:right;padding:4px 8px;">{delivery_cost:.2f} BYN</td></tr>'

            if delivery_type == 'delivery':
                delivery_info = f'🚚 Доставка по адресу: <b>{delivery_address}</b>'
                if pretty_datetime:
                    delivery_info += f'<br>🕐 {pretty_datetime}'
            else:
                delivery_info = f'🏪 Самовывоз: <b>{pickup_store_name}</b>'
                if pickup_store_address:
                    delivery_info += f'<br><span style="color:#555;font-size:12px;">{pickup_store_address}</span>'

            recipient_info = ''
            if recipient_name or recipient_phone:
                recipient_info = f'<p>💐 Получатель: <b>{recipient_name} {recipient_phone}</b></p>'

            comment_info = f'<p>💬 <i>{comment}</i></p>' if comment else ''

            html_body = f'''<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;color:#333;max-width:600px;margin:0 auto;">
<h2 style="color:#2a5db0;border-bottom:2px solid #c8d8f0;padding-bottom:8px;">🌸 Новый заказ #{order.pk}</h2>
<p>👤 <b>{name}</b> &nbsp;|&nbsp; 📞 {phone}{"&nbsp;|&nbsp;📧 "+email if email else ""}</p>
<p>{delivery_info}</p>
{recipient_info}
<p>💳 Оплата: <b>{pay_label}</b></p>
{comment_info}
<table style="width:100%;border-collapse:collapse;margin-top:12px;">
  <thead>
    <tr style="background:#f0f5ff;">
      <th style="padding:8px;text-align:left;">Фото</th>
      <th style="padding:8px;text-align:left;">Товар</th>
      <th style="padding:8px;text-align:center;">Кол-во</th>
      <th style="padding:8px;text-align:right;">Сумма</th>
    </tr>
  </thead>
  <tbody>{html_rows}</tbody>
  <tfoot>
    <tr><td colspan="3" style="text-align:right;padding:4px 8px;color:#555;">Товары:</td><td style="text-align:right;padding:4px 8px;">{subtotal:.2f} BYN</td></tr>
    {delivery_row}
    <tr style="font-weight:bold;font-size:15px;border-top:2px solid #ccc;">
      <td colspan="3" style="text-align:right;padding:8px;">Итого к оплате:</td>
      <td style="text-align:right;padding:8px;">{total:.2f} BYN</td>
    </tr>
  </tfoot>
</table>
</body></html>'''

            msg = MIMEMultipart('related')
            msg['Subject'] = Header(f'Новый заказ #{order.pk} — {name}', 'utf-8')
            msg['From'] = _from
            msg['To'] = _to
            alt = MIMEMultipart('alternative')
            alt.attach(_MIMEText(notification_text, 'plain', 'utf-8'))
            alt.attach(_MIMEText(html_body, 'html', 'utf-8'))
            msg.attach(alt)

            for img_info in inline_images:
                img_data = None
                if img_info['path']:
                    try:
                        with open(img_info['path'], 'rb') as f:
                            img_data = f.read()
                    except Exception:
                        pass
                if not img_data and img_info['url']:
                    try:
                        with _urlreq.urlopen(img_info['url'], timeout=5) as r:
                            img_data = r.read()
                    except Exception:
                        pass
                if img_data:
                    mime_img = MIMEImage(img_data)
                    mime_img.add_header('Content-ID', f'<{img_info["cid"]}>')
                    mime_img.add_header('Content-Disposition', 'inline')
                    msg.attach(mime_img)

            use_ssl = getattr(settings, 'EMAIL_USE_SSL', False)
            if use_ssl:
                import ssl as _ssl
                with smtplib.SMTP_SSL(_host, _port, context=_ssl.create_default_context()) as srv:
                    if _user: srv.login(_user, _pwd)
                    srv.sendmail(_from, [_to], msg.as_string())
            else:
                with smtplib.SMTP(_host, _port) as srv:
                    srv.ehlo(); srv.starttls(); srv.ehlo()
                    if _user: srv.login(_user, _pwd)
                    srv.sendmail(_from, [_to], msg.as_string())
        except Exception as e:
            _log.error('Email send error for order #%s: %s', order_pk, e)

    # Telegram
    tg_token = settings_obj.telegram_notify_token
    tg_chat = settings_obj.telegram_notify_chat_id
    if tg_token and tg_chat:
        try:
            import urllib.request
            import urllib.parse
            tg_url = f'https://api.telegram.org/bot{tg_token}/sendMessage'
            tg_data = urllib.parse.urlencode({
                'chat_id': tg_chat,
                'text': notification_text,
                'parse_mode': '',
            }).encode()
            req_tg = urllib.request.Request(tg_url, data=tg_data, method='POST')
            urllib.request.urlopen(req_tg, timeout=5)
        except Exception as e:
            _log.error('Telegram send error for order #%s: %s', order_pk, e)


@require_POST
def cart_checkout(request):
    """Оформить заказ: сохранить в БД, отправить email и Telegram."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Ошибка данных'}, status=400)

    name = (data.get('customer_name') or '').strip()
    phone = (data.get('customer_phone') or '').strip()
    email = (data.get('customer_email') or '').strip()
    recipient_name = (data.get('recipient_name') or '').strip()
    recipient_phone = (data.get('recipient_phone') or '').strip()
    delivery_type = (data.get('delivery_type') or 'delivery').strip()
    pickup_store_id = data.get('pickup_store_id') or None
    delivery_address = (data.get('delivery_address') or '').strip()
    delivery_date = (data.get('delivery_date') or '').strip()
    delivery_time = (data.get('delivery_time') or '').strip()

    # Красивый формат даты и времени для уведомлений
    def _fmt_datetime(date_str, time_str):
        """'2025-12-25' + '14:00' → '25 декабря 2025, 14:00'"""
        months_ru = ['января','февраля','марта','апреля','мая','июня',
                     'июля','августа','сентября','октября','ноября','декабря']
        result = ''
        if date_str:
            try:
                from datetime import datetime as _dt
                d = _dt.strptime(date_str, '%Y-%m-%d')
                result = f'{d.day} {months_ru[d.month - 1]} {d.year}'
            except Exception:
                result = date_str
        if time_str:
            result = (result + ', ' + time_str) if result else time_str
        return result

    pretty_datetime = _fmt_datetime(delivery_date, delivery_time)
    payment_type = (data.get('payment_type') or 'cash').strip()
    comment = (data.get('comment') or '').strip()

    if not name or not phone:
        return JsonResponse({'ok': False, 'error': 'Укажите имя и телефон'}, status=400)

    cart = _get_cart(request)
    if not cart:
        return JsonResponse({'ok': False, 'error': 'Корзина пуста'}, status=400)

    # Загружаем товары из БД
    product_ids = [int(k) for k in cart.keys()]
    products_map = {
        p.id: p
        for p in Product.objects.filter(id__in=product_ids, is_published=True)
    }

    import decimal
    settings_obj = SiteSettings.get()

    subtotal = decimal.Decimal('0')
    order_items_data = []
    for pid_str, qty in cart.items():
        pid = int(pid_str)
        product = products_map.get(pid)
        if not product or qty <= 0:
            continue
        price = product.price or decimal.Decimal('0')
        subtotal += price * qty
        order_items_data.append({'product': product, 'title': product.title, 'price': price, 'qty': qty})

    if not order_items_data:
        return JsonResponse({'ok': False, 'error': 'Корзина пуста'}, status=400)

    # Стоимость доставки
    if delivery_type == 'delivery':
        delivery_cost = settings_obj.delivery_cost if subtotal < settings_obj.delivery_free_from else decimal.Decimal('0')
    else:
        delivery_cost = decimal.Decimal('0')

    total = subtotal + delivery_cost

    # Магазин самовывоза
    pickup_store = None
    if delivery_type == 'pickup' and pickup_store_id:
        try:
            pickup_store = Store.objects.get(id=int(pickup_store_id), is_active=True)
        except (Store.DoesNotExist, ValueError):
            pass

    # Сохраняем в БД атомарно — если что-то пойдёт не так, откатится всё
    from django.db import transaction as _transaction
    with _transaction.atomic():
        order = GuestOrder.objects.create(
            customer_name=name,
            customer_phone=phone,
            customer_email=email,
            recipient_name=recipient_name,
            recipient_phone=recipient_phone,
            delivery_type=delivery_type,
            pickup_store=pickup_store,
            delivery_address=delivery_address,
            delivery_date=delivery_date,
            delivery_time=delivery_time,
            payment_type=payment_type,
            subtotal=subtotal,
            delivery_cost=delivery_cost,
            total=total,
            comment=comment,
        )
        for item_data in order_items_data:
            GuestOrderItem.objects.create(
                order=order,
                product=item_data['product'],
                title=item_data['title'],
                price=item_data['price'],
                qty=item_data['qty'],
            )

    # Формируем текст уведомления (plain-text для Telegram)
    lines = [f'🌸 Новый заказ #{order.pk}']
    lines.append(f'👤 {name} / {phone}')
    if email:
        lines.append(f'📧 {email}')
    if delivery_type == 'delivery':
        lines.append(f'🚚 Доставка: {delivery_address}')
        if pretty_datetime:
            lines.append(f'🕐 {pretty_datetime}')
    else:
        store_name = pickup_store.name if pickup_store else 'уточнить'
        lines.append(f'🏪 Самовывоз: {store_name}')
    if recipient_name or recipient_phone:
        lines.append(f'💐 Получатель: {recipient_name} {recipient_phone}'.strip())
    lines.append(f'💳 Оплата: {"Наличные" if payment_type == "cash" else "Картой online"}')
    lines.append('')
    for item_data in order_items_data:
        p = item_data['product']
        article_str = f' [{p.article}]' if p.article else ''
        lines.append(f'• {item_data["title"]}{article_str} × {item_data["qty"]} = {item_data["price"] * item_data["qty"]:.2f} BYN')
    lines.append('')
    lines.append(f'Товары: {subtotal:.2f} BYN')
    if delivery_cost:
        lines.append(f'Доставка: {delivery_cost:.2f} BYN')
    lines.append(f'Итого: {total:.2f} BYN')
    if comment:
        lines.append(f'\n💬 {comment}')
    notification_text = '\n'.join(lines)

    # Уведомления отправляем в фоновом потоке — не блокируем ответ покупателю
    import threading
    _t = threading.Thread(
        target=_send_order_notifications,
        args=(
            order.pk, notification_text, order_items_data,
            subtotal, delivery_cost, total,
            delivery_type, delivery_address, pretty_datetime,
            pickup_store.name if pickup_store else 'уточнить',
            pickup_store.address if pickup_store else '',
            recipient_name, recipient_phone, comment,
            payment_type, name, phone, email,
        ),
        daemon=True,
    )
    _t.start()

    # Сохраняем в сессии для страницы "спасибо"
    request.session['last_order'] = {'id': order.pk, 'name': name, 'phone': phone}

    # Очищаем корзину
    _save_cart(request, {})

    return JsonResponse({'ok': True, 'order_id': order.pk})


# ─── ДАШБОРД ─────────────────────────────────────────────────────────────────

from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout, update_session_auth_hash, authenticate, login as auth_login
from django.contrib import messages
from django.core.files.storage import default_storage
import decimal


def dashboard_login(request):
    if request.user.is_authenticated:
        return redirect('/dashboard/products/')
    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_active:
            has_access = (
                user.is_staff or user.is_superuser or
                (hasattr(user, 'store_manager') and user.store_manager.is_active)
            )
            if has_access:
                auth_login(request, user)
                return redirect(request.GET.get('next', '/dashboard/products/'))
            else:
                error = 'Нет доступа к дашборду'
        else:
            error = 'Неверный логин или пароль'
    return render(request, 'shop/dashboard/login.html', {'error': error})


def _dash_product_image(product, request):
    if product.uploaded_image:
        return product.uploaded_image.url
    if product.image:
        return _normalize_public_url(product.image, request)
    return "/static/hero/today-desktop.svg"


def _get_manager_stores(user):
    """Возвращает queryset магазинов для пользователя.
    Superuser/staff — все магазины (None = без ограничений).
    Менеджер — только его магазины через StoreManager."""
    if user.is_superuser or user.is_staff:
        return None  # без фильтра
    try:
        sm = user.store_manager
        if sm.is_active:
            return sm.stores.filter(is_active=True)
    except StoreManager.DoesNotExist:
        pass
    return Store.objects.none()


@login_required(login_url='/dashboard/login/')
def dashboard_products(request):
    manager_stores = _get_manager_stores(request.user)
    qs = Product.objects.select_related('category').prefetch_related('stores').order_by('-id')
    if manager_stores is not None:
        qs = qs.filter(stores__in=manager_stores).distinct()
    products = []
    for p in qs:
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


@login_required(login_url='/dashboard/login/')
def dashboard_product_form(request, product_id=None):
    product = None
    product_store_ids = []
    manager_stores = _get_manager_stores(request.user)
    if product_id:
        product = get_object_or_404(Product, id=product_id)
        # Менеджер не может редактировать чужие товары
        if manager_stores is not None:
            allowed_ids = set(manager_stores.values_list('id', flat=True))
            product_store_ids_check = set(product.stores.values_list('id', flat=True))
            if not allowed_ids & product_store_ids_check:
                from django.http import HttpResponseForbidden
                return HttpResponseForbidden('Нет доступа к этому товару')
        product_store_ids = list(product.stores.values_list('id', flat=True))

    categories = Category.objects.order_by('sort_order', 'name')
    if manager_stores is not None:
        stores = manager_stores.order_by('name')
    else:
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


@login_required(login_url='/dashboard/login/')
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
    # Категории для быстрого выбора ссылки
    categories = list(
        Category.objects.order_by('sort_order', 'name').values('id', 'name', 'slug', 'parent_id')
    )
    return render(request, 'shop/dashboard/hero.html', {
        'banners': banners,
        'banners_json': _json.dumps(banners_data, ensure_ascii=False),
        'categories_json': _json.dumps(categories, ensure_ascii=False),
        'active': 'hero'
    })


@login_required(login_url='/dashboard/login/')
def dashboard_showcase(request):
    manager_stores = _get_manager_stores(request.user)
    is_admin = manager_stores is None  # суперадмин/staff видит все магазины

    # Полный список магазинов для табов (только для админа)
    all_stores = Store.objects.filter(is_active=True).order_by('sort_order', 'name') if is_admin else None

    # Определяем активный магазин
    selected_store = None
    if is_admin:
        try:
            store_id = int(request.GET.get('store', 0))
        except (ValueError, TypeError):
            store_id = 0
        if store_id:
            selected_store = Store.objects.filter(id=store_id, is_active=True).first()
        # Если не выбран — берём первый
        if not selected_store and all_stores.exists():
            selected_store = all_stores.first()
        stores_qs = Store.objects.filter(id=selected_store.id) if selected_store else Store.objects.none()
    else:
        # Менеджер — только его магазины
        stores_qs = manager_stores
        if stores_qs.exists():
            selected_store = stores_qs.first()

    # Товары в витрине — через ShowcaseItem
    showcase_items_qs = ShowcaseItem.objects.filter(
        store__in=stores_qs
    ).select_related('product', 'store').order_by('sort_order', '-id')

    showcase_products = []
    showcase_product_ids = set()
    for item in showcase_items_qs:
        p = item.product
        showcase_products.append({
            'id': p.id,
            'title': p.title,
            'price': p.price,
            'showcase_sort_order': item.sort_order,
            'image_url': _dash_product_image(p, request),
            'is_online_showcase': True,
            'store_name': item.store.name,
            'showcase_item_id': item.id,
        })
        showcase_product_ids.add(p.id)

    # Все товары для добавления (фильтруем по выбранному магазину)
    all_qs = Product.objects.filter(is_published=True).select_related('category').order_by('-id')
    if stores_qs:
        all_qs = all_qs.filter(stores__in=stores_qs).distinct()

    all_products = []
    for p in all_qs:
        all_products.append({
            'id': p.id,
            'title': p.title,
            'price': p.price,
            'image_url': _dash_product_image(p, request),
            'is_online_showcase': p.id in showcase_product_ids,
        })

    return render(request, 'shop/dashboard/showcase.html', {
        'showcase_products': showcase_products,
        'all_products': all_products,
        'all_stores': all_stores,           # для табов (только у админа)
        'selected_store': selected_store,   # активный магазин
        'active': 'showcase'
    })


@login_required(login_url='/dashboard/login/')
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


@login_required(login_url='/dashboard/login/')
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


@login_required(login_url='/dashboard/login/')
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
    return redirect('/dashboard/login/')


@login_required(login_url='/dashboard/login/')
def dashboard_reviews(request):
    manager_stores = _get_manager_stores(request.user)
    qs = Review.objects.select_related('store').order_by('-created_at')
    if manager_stores is not None:
        qs = qs.filter(store__in=manager_stores)
    reviews_data = []
    for r in qs:
        reviews_data.append({
            'id': r.id,
            'author': r.author,
            'company': r.company,
            'text': r.text[:120] + ('…' if len(r.text) > 120 else ''),
            'rating': r.rating,
            'is_published': r.is_published,
            'store_name': r.store.name if r.store else '—',
            'created_at': r.created_at.strftime('%d.%m.%Y %H:%M'),
        })
    return render(request, 'shop/dashboard/reviews.html', {
        'reviews': reviews_data,
        'active': 'reviews',
    })


# ─── DASHBOARD API (JSON endpoints) ──────────────────────────────────────────

@login_required(login_url='/dashboard/login/')
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


@login_required(login_url='/dashboard/login/')
@require_POST
def dash_api_product_title(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    try:
        data = json.loads(request.body)
        title = str(data.get('title', '')).strip()
        if not title:
            raise ValueError
    except Exception:
        return JsonResponse({'ok': False, 'error': 'Название не может быть пустым'}, status=400)
    product.title = title
    product.save(update_fields=['title'])
    return JsonResponse({'ok': True})


@login_required(login_url='/dashboard/login/')
@require_POST
def dash_api_product_showcase(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    manager_stores = _get_manager_stores(request.user)
    try:
        data = json.loads(request.body)
        value = bool(data.get('value'))
    except Exception:
        return JsonResponse({'ok': False, 'error': 'bad data'}, status=400)

    if manager_stores is not None:
        # Менеджер — добавляем/убираем ShowcaseItem только для его магазинов
        for store in manager_stores:
            if value:
                ShowcaseItem.objects.get_or_create(store=store, product=product)
            else:
                ShowcaseItem.objects.filter(store=store, product=product).delete()
    else:
        # Суперюзер — работаем через ShowcaseItem с учётом store_id из запроса
        try:
            store_id = int(data.get('store_id', 0))
        except (TypeError, ValueError):
            store_id = 0
        if store_id:
            store = Store.objects.filter(id=store_id, is_active=True).first()
            if store:
                if value:
                    ShowcaseItem.objects.get_or_create(store=store, product=product)
                else:
                    ShowcaseItem.objects.filter(store=store, product=product).delete()
        else:
            # Нет store_id — fallback на is_online_showcase
            product.is_online_showcase = value
            product.save(update_fields=['is_online_showcase'])

    return JsonResponse({'ok': True})


@login_required(login_url='/dashboard/login/')
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


@login_required(login_url='/dashboard/login/')
@require_POST
def dash_api_product_delete(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.delete()
    return JsonResponse({'ok': True})


@login_required(login_url='/dashboard/login/')
@require_POST
def dash_api_showcase_order(request):
    try:
        data = json.loads(request.body)
        items = data.get('items', [])
    except Exception:
        return JsonResponse({'ok': False, 'error': 'bad data'}, status=400)
    manager_stores = _get_manager_stores(request.user)
    try:
        store_id = int(data.get('store_id', 0))
    except (TypeError, ValueError):
        store_id = 0
    for item in items:
        if manager_stores is not None:
            ShowcaseItem.objects.filter(
                product_id=item['id'],
                store__in=manager_stores
            ).update(sort_order=item.get('sort', 0))
        else:
            # Суперюзер — через ShowcaseItem с учётом store_id
            if store_id:
                ShowcaseItem.objects.filter(
                    product_id=item['id'],
                    store_id=store_id
                ).update(sort_order=item.get('sort', 0))
            else:
                Product.objects.filter(id=item['id']).update(showcase_sort_order=item.get('sort', 0))
    return JsonResponse({'ok': True})


@login_required(login_url='/dashboard/login/')
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


@login_required(login_url='/dashboard/login/')
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


@login_required(login_url='/dashboard/login/')
@require_POST
def dash_api_banner_delete(request, banner_id):
    banner = get_object_or_404(HeroBanner, id=banner_id)
    banner.delete()
    return JsonResponse({'ok': True})


@login_required(login_url='/dashboard/login/')
def dashboard_ticker(request):
    if not (request.user.is_superuser or request.user.is_staff):
        return redirect('/dashboard/')
    import json as _json
    items = list(Ticker.objects.order_by('sort_order', 'id').values('id', 'text', 'is_active', 'sort_order'))
    return render(request, 'shop/dashboard/ticker.html', {
        'items': items,
        'items_json': _json.dumps(items, ensure_ascii=False),
        'active': 'ticker',
    })


@login_required(login_url='/dashboard/login/')
@require_POST
def dash_api_ticker_save(request):
    """Создать или обновить строки тикера (принимает массив)."""
    if not (request.user.is_superuser or request.user.is_staff):
        return JsonResponse({'ok': False, 'error': 'forbidden'}, status=403)
    try:
        data = json.loads(request.body)
        items = data.get('items', [])
    except Exception:
        return JsonResponse({'ok': False, 'error': 'bad json'}, status=400)

    for item in items:
        item_id = item.get('id')
        text = str(item.get('text', '')).strip()
        if not text:
            continue
        is_active = bool(item.get('is_active', True))
        sort_order = int(item.get('sort_order', 0) or 0)
        if item_id:
            Ticker.objects.filter(id=item_id).update(text=text, is_active=is_active, sort_order=sort_order)
        else:
            Ticker.objects.create(text=text, is_active=is_active, sort_order=sort_order)
    return JsonResponse({'ok': True})


@login_required(login_url='/dashboard/login/')
@require_POST
def dash_api_ticker_delete(request, ticker_id):
    if not (request.user.is_superuser or request.user.is_staff):
        return JsonResponse({'ok': False, 'error': 'forbidden'}, status=403)
    Ticker.objects.filter(id=ticker_id).delete()
    return JsonResponse({'ok': True})


@login_required(login_url='/dashboard/login/')
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


@login_required(login_url='/dashboard/login/')
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


@login_required(login_url='/dashboard/login/')
@require_POST
def dash_api_category_delete(request, cat_id):
    cat = get_object_or_404(Category, id=cat_id)
    cat.delete()
    return JsonResponse({'ok': True})


@login_required(login_url='/dashboard/login/')
@require_POST
def dash_api_review_published(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    manager_stores = _get_manager_stores(request.user)
    if manager_stores is not None:
        if review.store is None or review.store not in manager_stores:
            return JsonResponse({'ok': False, 'error': 'Нет доступа'}, status=403)
    data = json.loads(request.body)
    review.is_published = bool(data.get('value'))
    review.save(update_fields=['is_published', 'updated_at'])
    return JsonResponse({'ok': True, 'is_published': review.is_published})


@login_required(login_url='/dashboard/login/')
@require_POST
def dash_api_review_delete(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    manager_stores = _get_manager_stores(request.user)
    if manager_stores is not None:
        if review.store is None or review.store not in manager_stores:
            return JsonResponse({'ok': False, 'error': 'Нет доступа'}, status=403)
    review.delete()
    return JsonResponse({'ok': True})
