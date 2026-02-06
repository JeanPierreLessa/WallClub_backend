"""
URLs para Container APIS (Mobile + Checkout)
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
import logging

logger = logging.getLogger(__name__)

# Rotas globais (monitoramento)
from monitoring.metrics_view import metrics_view

urlpatterns = [
    # Métricas Prometheus
    path('metrics', metrics_view, name='prometheus-metrics'),

    # Monitoramento e Health Checks
    path('health/', include('monitoring.urls')),

    # Admin Django
    path('admin/', admin.site.urls),

    # APIs Mobile
    path('api/oauth/', include('apps.oauth.urls')),
    path('api/v1/', include('apps.urls')),  # Health check
    path('api/v1/cliente/', include('apps.cliente.urls')),
    path('api/v1/transacoes/', include('apps.transacoes.urls')),
    path('api/v1/conta_digital/', include('apps.conta_digital.urls')),
    path('api/v1/ofertas/', include('apps.ofertas.urls')),
    path('api/v1/cupons/', include('apps.cupom.urls')),  # APIs de cupons

    # API Interna (comunicação entre containers)
    path('api/internal/cliente/', include('apps.cliente.urls_api_interna')),

    # Checkout Web
    path('api/v1/checkout/', include('checkout.link_pagamento_web.urls')),
    path('api/v1/checkout/recorrencia/', include('checkout.link_recorrencia_web.urls')),
]

# APIs Internas (comunicação entre containers)
try:
    urlpatterns.append(path('api/internal/conta_digital/', include('apps.conta_digital.urls_internal')))
except Exception as e:
    logger.error(f"Erro ao carregar conta_digital.urls_internal: {e}")

try:
    urlpatterns.append(path('api/internal/checkout/', include('checkout.urls_internal')))
except Exception as e:
    logger.error(f"Erro ao carregar checkout.urls_internal: {e}")

try:
    urlpatterns.append(path('api/internal/ofertas/', include('apps.ofertas.urls_internal')))
except Exception as e:
    logger.error(f"Erro ao carregar ofertas.urls_internal: {e}")

try:
    urlpatterns.append(path('api/internal/parametros/', include('parametros_wallclub.urls_internal')))
except Exception as e:
    logger.error(f"Erro ao carregar parametros_wallclub.urls_internal: {e}")

# Servir arquivos estáticos
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
