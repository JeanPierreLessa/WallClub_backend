"""
URL configuration for wallclub project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
import logging
# SimpleJWT removido - usando JWT customizado

logger = logging.getLogger(__name__)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Portais (nova estrutura modular)
    path('portal_admin/', include('portais.admin.urls')),  # Portal administrativo
    path('portal_lojista/', include('portais.lojista.urls', namespace='lojista')),  # Portal lojista padrão (wallclub)
    path('portal_lojista/<str:marca>/', include('portais.lojista.urls', namespace='lojista_marca')),  # Portal lojista por marca
    path('portal_corporativo/', include('portais.corporativo.urls')),  # Portal corporativo
    path('portal_vendas/', include('portais.vendas.urls')),  # Portal de vendas (checkout)
    
    
    # APIs Externas
    path('api/oauth/', include('apps.oauth.urls')),  # OAuth 2.0 endpoints - PRECISA SER CRIADO
    path('api/v1/', include('apps.urls')),  # Health check e outras rotas gerais
    path('api/v1/cliente/', include('apps.cliente.urls')),  # Endpoints de cliente
    path('api/v1/transacoes/', include('apps.transacoes.urls')),  # Endpoints de transações
    # path('api/v1/carteira/', include('apps.carteira.urls')),  # Removido - usando conta_digital
    path('api/v1/conta_digital/', include('apps.conta_digital.urls')),  # Endpoints de conta digital
    path('api/v1/ofertas/', include('apps.ofertas.urls')),  # Endpoints de ofertas
    path('api/v1/checkout/', include('checkout.link_pagamento_web.urls')),  # Link de pagamento web
    path('api/v1/checkout/recorrencia/', include('checkout.link_recorrencia_web.urls')),  # Cadastro de cartão para recorrência
    path('api/v1/posp2/', include('posp2.urls')),  # Endpoints POSP2
    
    # Webhooks Own Financial
    path('', include('adquirente_own.urls_webhook')),  # Webhooks Own
]

# APIs Internas (comunicação entre containers - sem rate limiting)
# Carregar com try/except para garantir que erros não quebrem toda aplicação
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

# Servir arquivos estáticos em desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
