from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse
from .services import AutenticacaoService, PermissaoService


def require_portal_login(portal):
    """
    Decorator que exige login para portal específico
    
    Args:
        portal: Portal necessário ('admin', 'lojista', 'corporativo')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            usuario = AutenticacaoService.obter_usuario_sessao(request)
            
            if not usuario:
                messages.error(request, 'Você precisa fazer login para acessar esta página.')
                return redirect(f'/portal_{portal}/')
            
            if not usuario.pode_acessar_portal(portal):
                messages.error(request, f'Você não tem permissão para acessar o portal {portal}.')
                return redirect('portais_admin:login')
            
            # Adiciona usuário ao request para uso nas views
            request.portal_usuario = usuario
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def require_portal_permission(portal, recurso=None, nivel='leitura'):
    """
    Decorator que exige permissão específica no portal
    
    Args:
        portal: Portal necessário
        recurso: Recurso específico (opcional)
        nivel: Nível mínimo necessário ('leitura', 'escrita', 'admin')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            usuario = AutenticacaoService.obter_usuario_sessao(request)
            
            if not usuario:
                messages.error(request, 'Você precisa fazer login.')
                return redirect(f'/portal_{portal}/')
            
            if not PermissaoService.usuario_tem_permissao(usuario, portal, recurso, nivel):
                messages.error(request, 'Você não tem permissão para acessar este recurso.')
                return redirect(f'/portal_{portal}/dashboard/')
            
            request.portal_usuario = usuario
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def require_admin_access(view_func):
    """Decorator específico para portal administrativo"""
    return require_portal_login('admin')(view_func)


def require_lojista_access(view_func):
    """Decorator específico para portal lojista"""
    return require_portal_login('lojista')(view_func)


def require_corporativo_access(view_func):
    """Decorator específico para portal corporativo"""
    return require_portal_login('corporativo')(view_func)


def api_require_portal_permission(portal, recurso=None, nivel='leitura'):
    """
    Decorator para APIs que exige permissão específica
    Retorna JSON em caso de erro
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            usuario = AutenticacaoService.obter_usuario_sessao(request)
            
            if not usuario:
                return JsonResponse({
                    'sucesso': False,
                    'mensagem': 'Autenticação necessária'
                }, status=401)
            
            if not PermissaoService.usuario_tem_permissao(usuario, portal, recurso, nivel):
                return JsonResponse({
                    'sucesso': False,
                    'mensagem': 'Permissão insuficiente'
                }, status=403)
            
            request.portal_usuario = usuario
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def requer_permissao(recurso):
    """
    Decorator genérico que exige permissão específica para recurso.
    Usado para controlar acesso a funcionalidades como 'recorrencia'.
    
    Uso:
        @requer_permissao('recorrencia')
        def minha_view(request):
            ...
    
    Args:
        recurso: Nome do recurso (ex: 'recorrencia', 'relatorios', 'parametros')
    
    Validação:
        - Verifica se usuário está logado
        - Verifica se tem permissão para o recurso no portal atual
        - Retorna 403 (HTML) ou JSON conforme tipo de requisição
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            usuario = AutenticacaoService.obter_usuario_sessao(request)
            
            # Verificar se está logado
            if not usuario:
                if request.content_type == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'sucesso': False,
                        'mensagem': 'Autenticação necessária'
                    }, status=401)
                messages.error(request, 'Você precisa fazer login.')
                return redirect('/portal_vendas/')
            
            # Verificar se tem permissão para o recurso
            # Buscar permissões do usuário e verificar recursos_permitidos
            tem_permissao = False
            for permissao in usuario.permissoes.all():
                recursos = permissao.recursos_permitidos or {}
                if recursos.get(recurso) is True:
                    tem_permissao = True
                    break
            
            if not tem_permissao:
                if request.content_type == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'sucesso': False,
                        'mensagem': f'Você não tem permissão para acessar {recurso}'
                    }, status=403)
                messages.error(request, f'Você não tem permissão para acessar {recurso}.')
                return redirect('/portal_vendas/dashboard/')
            
            request.portal_usuario = usuario
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator
