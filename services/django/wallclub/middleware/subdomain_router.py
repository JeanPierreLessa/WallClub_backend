"""
Middleware de Roteamento por Subdomínio

Detecta o subdomínio e roteia para o URLconf correto dentro do container portais.
Permite que admin.wallclub.com.br, vendas.wallclub.com.br e lojista.wallclub.com.br
respondam cada um em sua raiz (/) sem prefixos.
"""
import logging

logger = logging.getLogger(__name__)


class SubdomainRouterMiddleware:
    """
    Middleware que altera o ROOT_URLCONF baseado no subdomínio.
    Deve ser colocado no início da lista de middlewares.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Mapeamento de subdomínio para URLconf
        self.subdomain_map = {
            # Portal Admin
            'admin': 'wallclub.urls_admin',
            'wcadmin': 'wallclub.urls_admin',
            
            # Portal Vendas
            'vendas': 'wallclub.urls_vendas',
            'wcvendas': 'wallclub.urls_vendas',
            
            # Portal Lojista
            'lojista': 'wallclub.urls_lojista',
            'wclojista': 'wallclub.urls_lojista',
            
            # Portal Corporativo (se existir)
            'corporativo': 'wallclub.urls_corporativo',
            'wccorporativo': 'wallclub.urls_corporativo',
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
            urlconf = self.subdomain_map[subdomain]
            logger.debug(f"Roteando {host} (subdomínio: {subdomain}) para {urlconf}")
            request.urlconf = urlconf
        else:
            # Fallback: usar o URLconf padrão (portais com prefixos)
            logger.debug(f"Subdomínio '{subdomain}' não mapeado, usando URLconf padrão")
        
        response = self.get_response(request)
        return response
