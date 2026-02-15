from django.contrib.auth.models import User
from django.conf import settings
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
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import Product, Discount, Order, Category, Review, HeroBanner, Store, StoreManager
from .serializers import (ProductSerializer, DiscountSerializer, OrderSerializer, CategorySerializer
, TokenObtainPairSerializer, RegisterSerializer, UserSerializer, ReviewSerializer, PublicReviewCreateSerializer,
HeroBannerSerializer, StoreSerializer, StoreManagerSerializer, BotProductCreateSerializer)


class BotTokenPermission(IsAuthenticatedOrReadOnly):
    def has_permission(self, request, view):
        token = request.headers.get('X-Bot-Token', '')
        expected = getattr(settings, 'TELEGRAM_BOT_SECRET', '')
        return bool(token and expected and token == expected)


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
        queryset = Product.objects.all()
        category = self.request.query_params.get("category")
        online_showcase = self.request.query_params.get("online_showcase")
        store_subdomain = self.request.query_params.get("store__subdomain")

        if category:
            queryset = queryset.filter(category__name=category)
        if store_subdomain is not None:
            queryset = queryset.filter(store__subdomain=store_subdomain)

        showcase_enabled = bool(online_showcase and online_showcase.lower() in ("1", "true", "yes"))
        if showcase_enabled:
            queryset = queryset.filter(is_online_showcase=True)
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(is_published=True)

        if showcase_enabled:
            queryset = queryset.order_by('showcase_sort_order', '-id')
        return queryset

    def perform_create(self, serializer):
        instance = serializer.save()
        if instance.uploaded_image and not instance.image:
            instance.image = self.request.build_absolute_uri(instance.uploaded_image.url)
            instance.save(update_fields=['image'])


class StoreViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Store.objects.filter(is_active=True)
    serializer_class = StoreSerializer
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
                store_slug = instance.store.subdomain if instance.store else 'main'
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
