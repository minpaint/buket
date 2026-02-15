from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import (ProductViewSet, OrderViewSet, DiscountViewSet, CategoryViewSet, ReviewViewSet, ReviewSubmitView, RegisterView
                    , api_root, UserProfileViewSet, HeroBannerViewSet, hero_banner_current, StoreViewSet,
                    BotProductCreateView, BotAuthView)



router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'orders', OrderViewSet)
router.register(r'discounts', DiscountViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'reviews', ReviewViewSet)
router.register(r'hero-banners', HeroBannerViewSet, basename='hero-banner')
router.register(r'stores', StoreViewSet, basename='store')

urlpatterns = [
    path('', api_root),
    path('api/reviews/submit/', ReviewSubmitView.as_view(), name='review-submit'),
    path('api/hero-banners/current/', hero_banner_current, name='hero-banner-current'),
    path('api/', include(router.urls)),
    path('api/v1/products/from-bot/', BotProductCreateView.as_view(), name='bot-product-create'),
    path('api/v1/auth/bot-token/', BotAuthView.as_view(), name='bot-auth'),
    path('api/profile/', UserProfileViewSet.as_view(), name='user_profile'),
    path('register/', RegisterView.as_view(), name='auth_register'),
]
