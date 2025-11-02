"""
Middleware para isolamento de sessões por portal
Cada portal usa um cookie de sessão específico
"""
from django.conf import settings
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.sessions import serializers
from django.utils.cache import patch_vary_headers
from django.utils.http import http_date
import time


class PortalSessionMiddleware(SessionMiddleware):
    """
    Middleware customizado para gerenciar sessões separadas por portal
    """
    
    # Mapeamento de URLs para nomes de cookies específicos
    PORTAL_COOKIE_MAPPING = {
        '/portal_admin/': 'wallclub_admin_session',
        '/portal_lojista/': 'wallclub_lojista_session',
        '/portal_corporativo/': 'wallclub_corporativo_session',
        '/portal_vendas/': 'wallclub_vendas_session',
    }
    
    def get_portal_from_path(self, path):
        """Identifica o portal baseado no path da URL"""
        for portal_path, cookie_name in self.PORTAL_COOKIE_MAPPING.items():
            if path.startswith(portal_path):
                return cookie_name
        # Fallback para cookie padrão
        return settings.SESSION_COOKIE_NAME
    
    def process_request(self, request):
        """Processa request definindo cookie específico do portal"""
        # Determinar cookie baseado na URL
        portal_cookie_name = self.get_portal_from_path(request.path)
        
        # Obter session_key do cookie específico do portal
        session_key = request.COOKIES.get(portal_cookie_name)
        request.session = self.SessionStore(session_key)
        
        # Armazenar nome do cookie para uso no response
        request._portal_cookie_name = portal_cookie_name

    def process_response(self, request, response):
        """Processa response usando cookie específico do portal"""
        try:
            accessed = request.session.accessed
            modified = request.session.modified
            empty = request.session.is_empty()
        except AttributeError:
            return response
        
        # Usar nome do cookie específico do portal
        portal_cookie_name = getattr(request, '_portal_cookie_name', settings.SESSION_COOKIE_NAME)
        
        # If the session is empty, don't bother setting the cookie.
        if empty:
            if portal_cookie_name in request.COOKIES:
                response.delete_cookie(
                    portal_cookie_name,
                    path=settings.SESSION_COOKIE_PATH,
                    domain=settings.SESSION_COOKIE_DOMAIN,
                    samesite=settings.SESSION_COOKIE_SAMESITE,
                )
            patch_vary_headers(response, ('Cookie',))
            return response

        if accessed:
            patch_vary_headers(response, ('Cookie',))

        if (modified or settings.SESSION_SAVE_EVERY_REQUEST) and not empty:
            if request.session.get_expire_at_browser_close():
                max_age = None
                expires = None
            else:
                max_age = request.session.get_expiry_age()
                expires_time = time.time() + max_age
                expires = http_date(expires_time)
            
            # Save the session data and refresh the client cookie.
            # Skip session save for 500 responses, refs #3881.
            if response.status_code != 500:
                try:
                    request.session.save()
                except Exception:
                    # If saving fails, don't fail the entire response.
                    pass
                
                response.set_cookie(
                    portal_cookie_name,  # Usar cookie específico do portal
                    request.session.session_key,
                    max_age=max_age,
                    expires=expires,
                    domain=settings.SESSION_COOKIE_DOMAIN,
                    path=settings.SESSION_COOKIE_PATH,
                    secure=settings.SESSION_COOKIE_SECURE or None,
                    httponly=settings.SESSION_COOKIE_HTTPONLY or None,
                    samesite=settings.SESSION_COOKIE_SAMESITE,
                )
        
        return response


class PortalAuthMiddleware:
    """
    Middleware para anexar usuário autenticado do portal ao request
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Anexar usuário do portal ao request se autenticado
        from portais.controle_acesso.services import AutenticacaoService
        
        request.portal_usuario = None
        
        # Verificar se há usuário autenticado na sessão
        usuario = AutenticacaoService.obter_usuario_sessao(request)
        if usuario:
            request.portal_usuario = usuario
        
        response = self.get_response(request)
        return response
