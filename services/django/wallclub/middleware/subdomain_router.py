"""
Middleware de Roteamento por Subdomínio

Detecta o subdomínio e gera URLpatterns dinamicamente usando a função helper.
Permite que cada portal responda em sua raiz (/) sem prefixos.
"""
import logging
from wallclub.urls_portais import get_portal_urlpatterns

logger = logging.getLogger(__name__)


class SubdomainRouterMiddleware:
    """
    Middleware que gera URLpatterns dinamicamente baseado no subdomínio.
    Usa a função get_portal_urlpatterns() para evitar duplicação de código.
    """

    def __init__(self, get_response):
        self.get_response = get_response

        # Mapeamento de subdomínio para nome do portal
        self.subdomain_map = {
            'admin': 'admin',
            'vendas': 'vendas',
            'lojista': 'lojista',
            'www': 'corporativo',
        }

    def __call__(self, request):
        # Obter o host da requisição
        host = request.get_host().lower()

        # Remover porta se existir (ex: admin.wallclub.local:8005)
        host = host.split(':')[0]

        # Extrair o subdomínio (primeira parte antes do primeiro ponto)
        subdomain = host.split('.')[0] if '.' in host else host

        # Verificar se é um subdomínio mapeado
        if subdomain in self.subdomain_map:
            portal_name = self.subdomain_map[subdomain]
            logger.info(f"[SUBDOMAIN ROUTER] Roteando {host} para portal '{portal_name}'")

            # Gerar URLpatterns dinamicamente para o portal específico
            request.urlconf = type('DynamicURLConf', (), {
                'urlpatterns': get_portal_urlpatterns(portal_name)
            })
        else:
            # Fallback: usar URLconf padrão (portais com prefixos)
            logger.debug(f"[SUBDOMAIN ROUTER] Subdomínio '{subdomain}' não mapeado, usando URLconf padrão")

        response = self.get_response(request)
        return response
