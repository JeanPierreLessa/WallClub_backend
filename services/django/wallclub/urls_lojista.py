"""
URLs para Portal Lojista (lojista.wallclub.com.br)
Responde na raiz (/) sem prefixo /portal_lojista/
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
import logging

logger = logging.getLogger(__name__)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Portal Lojista na raiz
    path('', include('portais.lojista.urls', namespace='lojista')),
]

# APIs Internas (comunicação entre containers)
try:
    urlpatterns.append(path('api/internal/ofertas/', include('apps.ofertas.urls_internal')))
except Exception as e:
    logger.error(f"Erro ao carregar ofertas.urls_internal: {e}")

try:
    urlpatterns.append(path('api/internal/parametros/', include('parametros_wallclub.urls_internal')))
except Exception as e:
    logger.error(f"Erro ao carregar parametros_wallclub.urls_internal: {e}")

# Servir arquivos estáticos (Whitenoise cuida em produção)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
