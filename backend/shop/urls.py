from django.urls import include, path
from django.views.generic import RedirectView
from rest_framework.routers import DefaultRouter
from .views import (ProductViewSet, OrderViewSet, DiscountViewSet, CategoryViewSet, ReviewViewSet, ReviewSubmitView, RegisterView
                    , api_root, UserProfileViewSet, HeroBannerViewSet, hero_banner_current, StoreViewSet, FlowerTagViewSet,
                    BotProductCreateView, BotAuthView, home_page, store_page, product_page, product_page_by_id,
                    store_page_category, store_page_flower, old_product_redirect,
                    categories_page, reviews_page, site_page,
                    cart_page, cart_add, cart_update, cart_remove, cart_count, cart_checkout, cart_drawer,
                    # Dashboard pages
                    dashboard_products, dashboard_product_form, dashboard_hero, dashboard_showcase,
                    dashboard_categories, dashboard_profile, dashboard_profile_password, dashboard_logout,
                    # Dashboard API
                    dash_api_product_price, dash_api_product_showcase, dash_api_product_published,
                    dash_api_product_delete, dash_api_showcase_order,
                    dash_api_banner_create, dash_api_banner_save, dash_api_banner_delete,
                    dash_api_category_create, dash_api_category_sort, dash_api_category_delete,
                    )



router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'orders', OrderViewSet)
router.register(r'discounts', DiscountViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'reviews', ReviewViewSet)
router.register(r'hero-banners', HeroBannerViewSet, basename='hero-banner')
router.register(r'stores', StoreViewSet, basename='store')
router.register(r'flower-tags', FlowerTagViewSet, basename='flower-tag')

urlpatterns = [
    path('', home_page, name='web_home'),
    path('store/', store_page, name='web_store'),
    # ЧПУ фильтры каталога (до <slug:slug> чтобы не конфликтовали)
    path('store/category/<slug:slug>/', store_page_category, name='web_store_category'),
    path('store/flower/<slug:slug>/', store_page_flower, name='web_store_flower'),
    # Карточка товара по slug
    path('store/<slug:slug>/', product_page, name='web_product'),
    # 301 редирект: старый числовой URL
    path('store/<int:product_id>/old/', product_page_by_id, name='web_product_id'),
    # 301 редирект: старые URL вида /katalog/buket-nevesty.html
    path('katalog/<slug:slug>.html', old_product_redirect, name='old_product_redirect'),
    path('categories/', categories_page, name='web_categories'),
    path('reviews/', reviews_page, name='web_reviews'),
    path('p/<slug:slug>/', site_page, name='web_site_page'),
    path('cart/', cart_page, name='web_cart'),
    path('cart/add/<int:product_id>/', cart_add, name='cart_add'),
    path('cart/update/<int:product_id>/', cart_update, name='cart_update'),
    path('cart/remove/<int:product_id>/', cart_remove, name='cart_remove'),
    path('cart/count/', cart_count, name='cart_count'),
    path('cart/checkout/', cart_checkout, name='cart_checkout'),
    path('cart/drawer/', cart_drawer, name='cart_drawer'),

    # Dashboard pages
    path('dashboard/', RedirectView.as_view(url='/dashboard/products/', permanent=False), name='dash_home'),
    path('dashboard/products/', dashboard_products, name='dash_products'),
    path('dashboard/products/add/', dashboard_product_form, name='dash_product_add'),
    path('dashboard/products/<int:product_id>/', dashboard_product_form, name='dash_product_edit'),
    path('dashboard/hero/', dashboard_hero, name='dash_hero'),
    path('dashboard/showcase/', dashboard_showcase, name='dash_showcase'),
    path('dashboard/categories/', dashboard_categories, name='dash_categories'),
    path('dashboard/profile/', dashboard_profile, name='dash_profile'),
    path('dashboard/profile/password/', dashboard_profile_password, name='dash_profile_password'),
    path('dashboard/logout/', dashboard_logout, name='dash_logout'),

    # Dashboard API
    path('dashboard/api/product/<int:product_id>/price/', dash_api_product_price, name='dash_api_product_price'),
    path('dashboard/api/product/<int:product_id>/showcase/', dash_api_product_showcase, name='dash_api_product_showcase'),
    path('dashboard/api/product/<int:product_id>/published/', dash_api_product_published, name='dash_api_product_published'),
    path('dashboard/api/product/<int:product_id>/delete/', dash_api_product_delete, name='dash_api_product_delete'),
    path('dashboard/api/showcase/order/', dash_api_showcase_order, name='dash_api_showcase_order'),
    path('dashboard/api/banner/create/', dash_api_banner_create, name='dash_api_banner_create'),
    path('dashboard/api/banner/<int:banner_id>/save/', dash_api_banner_save, name='dash_api_banner_save'),
    path('dashboard/api/banner/<int:banner_id>/delete/', dash_api_banner_delete, name='dash_api_banner_delete'),
    path('dashboard/api/category/create/', dash_api_category_create, name='dash_api_category_create'),
    path('dashboard/api/category/<int:cat_id>/sort/', dash_api_category_sort, name='dash_api_category_sort'),
    path('dashboard/api/category/<int:cat_id>/delete/', dash_api_category_delete, name='dash_api_category_delete'),

    path('api/', api_root, name='api-root'),
    path('api/reviews/submit/', ReviewSubmitView.as_view(), name='review-submit'),
    path('api/hero-banners/current/', hero_banner_current, name='hero-banner-current'),
    path('api/', include(router.urls)),
    path('api/v1/products/from-bot/', BotProductCreateView.as_view(), name='bot-product-create'),
    path('api/v1/auth/bot-token/', BotAuthView.as_view(), name='bot-auth'),
    path('api/profile/', UserProfileViewSet.as_view(), name='user_profile'),
    path('register/', RegisterView.as_view(), name='auth_register'),
]
