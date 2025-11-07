"""
Decorators OAuth 2.0 para WallClub.
Validação de tokens OAuth por contexto de uso.
"""
from functools import wraps
from django.http import JsonResponse
from wallclub_core.utilitarios.log_control import registrar_log


def require_oauth_token(view_func):
    """
    Decorator para validar OAuth access_token
    Inclui validação de device fingerprint
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        from .services import OAuthService

        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            registrar_log("comum.oauth", "Tentativa de acesso sem OAuth token", nivel='WARNING')
            return JsonResponse({'error': 'OAuth token obrigatório'}, status=401)

        access_token = auth_header.split(' ')[1]

        token_obj = OAuthService.validate_oauth_token(access_token)
        if not token_obj:
            return JsonResponse({'error': 'Token OAuth inválido ou expirado'}, status=401)

        # Validar device fingerprint se configurado
        if not OAuthService.validate_device_fingerprint(token_obj, request):
            return JsonResponse({
                'error': 'Dispositivo não autorizado',
                'message': 'Este token foi gerado para outro dispositivo'
            }, status=403)

        # Adicionar informações ao request
        request.oauth_client = token_obj.client
        request.oauth_token = token_obj

        return view_func(request, *args, **kwargs)

    return wrapper


def require_oauth_and_jwt(view_func):
    """
    Decorator para validar OAuth + JWT user token
    """
    @require_oauth_token
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user_token = request.headers.get('X-User-Token')
        if not user_token:
            registrar_log("comum.oauth", "Tentativa de acesso sem user token", nivel='WARNING')
            return JsonResponse({'error': 'User token obrigatório'}, status=401)

        # Validar JWT user token usando sistema customizado
        from .jwt_utils import validate_cliente_jwt_token
        payload = validate_cliente_jwt_token(user_token)
        if not payload:
            registrar_log("comum.oauth", "User token inválido", nivel='WARNING')
            return JsonResponse({'error': 'User token inválido'}, status=401)

        request.cliente_data = payload
        request.cliente_id = payload.get('cliente_id')
        return view_func(request, *args, **kwargs)

    return wrapper


def require_oauth_for_context(context):
    """
    Decorator para validar OAuth específico por contexto

    Args:
        context (str): Contexto de uso ('apps', 'posp2', 'checkout')
    """
    def decorator(view_func):
        @require_oauth_token
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            from .services import OAuthService

            # Validar se cliente OAuth tem permissão para este contexto
            client_id = request.oauth_client.client_id
            if not OAuthService.is_context_allowed(client_id, context):
                registrar_log("comum.oauth", f"Cliente {client_id} sem permissão para contexto {context}", nivel='WARNING')
                return JsonResponse({
                    'error': 'Acesso negado',
                    'message': f'Cliente OAuth não autorizado para contexto {context}'
                }, status=403)

            # Adicionar contexto ao request
            request.oauth_context = context

            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator


def require_oauth_apps(view_func):
    """Decorator específico para apps móveis - aceita JWT de clientes logados via OAuth"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        from .services import OAuthService

        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            registrar_log("comum.oauth", "Tentativa de acesso sem token", nivel='WARNING')
            return JsonResponse({'error': 'Token obrigatório'}, status=401)

        token = auth_header.split(' ')[1]

        # Verificar se é OAuth token (começa com wc_at_)
        if token.startswith('wc_at_'):
            # Validar OAuth token
            token_obj = OAuthService.validate_oauth_token(token)
            if not token_obj:
                return JsonResponse({'error': 'Token OAuth inválido ou expirado'}, status=401)

            # Validar contexto apps
            client_id = token_obj.client.client_id
            if not OAuthService.is_context_allowed(client_id, 'apps'):
                registrar_log("comum.oauth", f"Cliente {client_id} sem permissão para contexto apps")
                return JsonResponse({
                    'error': 'Acesso negado',
                    'message': 'Cliente OAuth não autorizado para contexto apps'
                }, status=403)

            # Adicionar informações ao request
            request.oauth_client = token_obj.client
            request.oauth_token = token_obj
            request.oauth_context = 'apps'

        else:
            # Verificar se é JWT de cliente
            from .jwt_utils import validate_cliente_jwt_token
            payload = validate_cliente_jwt_token(token)
            if not payload:
                registrar_log("comum.oauth", "JWT inválido", nivel='WARNING')
                return JsonResponse({'error': 'Token inválido'}, status=401)

            # Verificar se JWT foi gerado via OAuth (campo oauth_validated no payload)
            if not payload.get('oauth_validated'):
                registrar_log("comum.oauth", "JWT não foi gerado via OAuth", nivel='WARNING')
                return JsonResponse({'error': 'Token deve ser gerado via OAuth'}, status=401)

            # Adicionar dados do cliente ao request (compatibilidade com IsAuthenticated)
            from django.contrib.auth.models import AnonymousUser
            class MockUser:
                def __init__(self, payload):
                    self.cliente_id = payload.get('cliente_id')
                    self.cpf = payload.get('cpf')
                    self.nome = payload.get('nome')
                    self.canal_id = payload.get('canal_id')
                    self.is_active = payload.get('is_active', True)
                    self.is_authenticated = True

                def __bool__(self):
                    return True

            request.user = MockUser(payload)
            request.oauth_context = 'apps'

        return view_func(request, *args, **kwargs)

    return wrapper


def require_oauth_posp2(view_func):
    """Decorator específico para POS/POSP2"""
    return require_oauth_for_context('posp2')(view_func)


def require_oauth_checkout(view_func):
    """Decorator específico para checkout web"""
    return require_oauth_for_context('checkout')(view_func)


def require_oauth_internal(view_func):
    """
    Decorator para APIs internas - comunicação entre containers
    Aceita tokens OAuth de qualquer contexto de servidor (posp2, riskengine, etc)
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        from .services import OAuthService
        
        # Extrair token do header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return JsonResponse({
                'error': 'invalid_request',
                'error_description': 'Token OAuth obrigatório'
            }, status=401)
        
        access_token = auth_header.replace('Bearer ', '').strip()
        
        # Validar token OAuth
        validacao = OAuthService.validate_access_token(access_token)
        
        if not validacao['valid']:
            return JsonResponse({
                'error': 'invalid_token',
                'error_description': validacao.get('error', 'Token inválido')
            }, status=401)
        
        # Anexar informações do token na request
        request.oauth_client = validacao.get('client')
        request.oauth_token = validacao.get('token')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def require_oauth_riskengine(view_func):
    """Decorator específico para riskengine - comunicação entre containers"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        from .services import OAuthService

        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            registrar_log("comum.oauth", "RiskEngine: Tentativa de acesso sem token", nivel='WARNING')
            return JsonResponse({'error': 'OAuth token obrigatório'}, status=401)

        access_token = auth_header.split(' ')[1]

        token_obj = OAuthService.validate_oauth_token(access_token)
        if not token_obj:
            return JsonResponse({'error': 'Token OAuth inválido ou expirado'}, status=401)

        # Validar se é cliente riskengine
        client_id = token_obj.client.client_id
        if client_id != 'wallclub-riskengine':
            registrar_log("comum.oauth", f"Cliente {client_id} tentou acessar endpoint do riskengine", nivel='WARNING')
            return JsonResponse({
                'error': 'Acesso negado',
                'message': 'Endpoint exclusivo para wallclub-riskengine'
            }, status=403)

        # Adicionar informações ao request
        request.oauth_client = token_obj.client
        request.oauth_token = token_obj

        return view_func(request, *args, **kwargs)

    return wrapper
