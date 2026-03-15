from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from rest_framework.permissions import IsAdminUser
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Swagger/ReDoc — в продакшне доступен только администраторам
schema_view = get_schema_view(
    openapi.Info(
        title="Buket.by API",
        default_version='v1',
        description="Buket.by API Documentation",
        contact=openapi.Contact(email="ohrana-truda.by@yandex.by"),
    ),
    public=False,
    permission_classes=(IsAdminUser,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('', include("shop.urls")),
]

# Swagger/ReDoc только в DEBUG (или для залогиненных админов)
if settings.DEBUG:
    urlpatterns += [
        path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
        path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    ]

# Медиафайлы через Django только в DEBUG — в продакшне отдаёт Nginx/whitenoise
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Кастомные страницы ошибок (работают только при DEBUG=False)
handler404 = 'shop.views.error_404'
handler500 = 'shop.views.error_500'
