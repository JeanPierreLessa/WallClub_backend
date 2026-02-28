"""
URLs para Container PORTAIS (Admin + Vendas + Lojista + Corporativo)
Suporta roteamento por subdomínio via middleware ou acesso direto com prefixos.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
import logging

logger = logging.getLogger(__name__)


def get_portal_urlpatterns(portal_name=None):
    """
    Gera URLpatterns dinamicamente baseado no portal.

    Args:
        portal_name: Nome do portal ('admin', 'vendas', 'lojista', 'corporativo')
                    Se None, retorna URLconf padrão com todos os portais usando prefixos.

    Returns:
        Lista de URLpatterns configurados para o portal específico ou padrão.
    """
    # Rotas globais (disponíveis em todos os portais)
    base_patterns = [
        # Métricas Prometheus
        path('', include('django_prometheus.urls')),

        # Monitoramento e Health Checks
        path('', include('monitoring.urls')),

        # Admin Django
        path('admin/', admin.site.urls),
    ]

    # Mapeamento de portais
    portal_map = {
        'admin': {
            'urls': 'portais.admin.urls',
            'namespace': 'portais_admin',
            'extra_routes': [
                path('api/own/', include('adquirente_own.urls_cadastro')),
            ]
        },
        'vendas': {
            'urls': 'portais.vendas.urls',
            'namespace': 'vendas',
            'extra_routes': []
        },
        'lojista': {
            'urls': 'portais.lojista.urls',
            'namespace': 'lojista',
            'extra_routes': []
        },
        'corporativo': {
            'urls': 'portais.corporativo.urls',
            'namespace': 'portais_corporativo',
            'extra_routes': []
        },
    }

    # Se portal específico, retorna URLconf para aquele portal na raiz
    if portal_name and portal_name in portal_map:
        config = portal_map[portal_name]
        portal_patterns = base_patterns + [
            path('', include(config['urls'], namespace=config['namespace'])),
        ] + config['extra_routes']

        return portal_patterns

    # Fallback: URLconf padrão com todos os portais usando prefixos
    from apps.cupom.api_views import validar_cupom_checkout

    default_patterns = base_patterns + [
        # Portais com prefixos
        path('portal_admin/', include('portais.admin.urls', namespace='portais_admin')),
        path('portal_vendas/', include('portais.vendas.urls', namespace='vendas')),
        path('portal_lojista/', include('portais.lojista.urls', namespace='lojista')),
        path('portal_lojista/<str:marca>/', include('portais.lojista.urls', namespace='lojista_marca')),
        path('portal_corporativo/', include('portais.corporativo.urls', namespace='portais_corporativo')),

        # APIs Own Financial (para portal admin)
        path('api/own/', include('adquirente_own.urls_cadastro')),

        # APIs internas (chamadas entre containers)
        path('api/cupom/validar/', validar_cupom_checkout, name='validar_cupom_interno'),
    ]

    return default_patterns


# URLpatterns padrão (usado quando não há roteamento por subdomínio)
urlpatterns = get_portal_urlpatterns()

# APIs Internas (comunicação entre containers)
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
