"""
URLs para Container POS (Terminal POS)
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
import logging

logger = logging.getLogger(__name__)

urlpatterns = [
    # Métricas Prometheus
    path('', include('django_prometheus.urls')),

    # Monitoramento e Health Checks
    path('health/', include('monitoring.urls')),

    # Admin Django
    path('admin/', admin.site.urls),

    # OAuth (necessário para autenticação POS)
    path('api/oauth/', include('apps.oauth.urls')),

    # APIs POS
    path('api/v1/posp2/', include('posp2.urls')),
    path('api/v1/cupons/', include('apps.cupom.urls')),  # APIs de cupons

    # Webhooks Own Financial
    path('', include('adquirente_own.urls_webhook')),
]

# APIs Internas (comunicação entre containers)
try:
    urlpatterns.append(path('api/internal/parametros/', include('parametros_wallclub.urls_internal')))
except Exception as e:
    logger.error(f"Erro ao carregar parametros_wallclub.urls_internal: {e}")

# Servir arquivos estáticos
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
