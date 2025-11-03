"""
Decorators para APIs REST
Tratamento padronizado de erros e validações
"""
import json
import functools
from django.http import JsonResponse
from wallclub_core.utilitarios.log_control import registrar_log


def handle_api_errors(view_func):
    """
    Decorator para tratamento padrão de erros em endpoints de API.
    
    Captura:
    - JSONDecodeError: Retorna 400 Bad Request
    - Exception genérica: Retorna 500 Internal Server Error + log
    
    Uso:
        @csrf_exempt
        @require_http_methods(["POST"])
        @require_oauth_posp2
        @handle_api_errors
        def meu_endpoint(request):
            data = json.loads(request.body)
            # ... lógica ...
    """
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except json.JSONDecodeError:
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'JSON inválido'
            }, status=400)
        except Exception as e:
            registrar_log(
                'api_error', 
                f'❌ Erro em {view_func.__name__}: {str(e)}', 
                nivel='ERROR'
            )
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'Erro interno'
            }, status=500)
    
    return wrapper


def validate_required_params(*required_params):
    """
    Decorator para validar parâmetros obrigatórios no request body.
    Funciona com DRF (@api_view) e views Django tradicionais.
    
    Uso:
        @api_view(['POST'])
        @validate_required_params('cpf', 'senha', 'terminal')
        def validar_senha(request):
            data = request.data  # DRF já processou
            # cpf, senha e terminal já foram validados
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Detectar se é DRF (request.data) ou Django tradicional (request.body)
            if hasattr(request, 'data'):
                # DRF - dados já processados
                data = request.data
            else:
                # Django tradicional - precisa fazer parse
                try:
                    data = json.loads(request.body)
                except json.JSONDecodeError:
                    return JsonResponse({
                        'sucesso': False,
                        'mensagem': 'JSON inválido'
                    }, status=400)
            
            # Verifica parâmetros obrigatórios
            missing = [param for param in required_params if not data.get(param)]
            
            if missing:
                return JsonResponse({
                    'sucesso': False,
                    'mensagem': f'Parâmetros obrigatórios: {", ".join(required_params)}',
                    'faltando': missing
                }, status=400)
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def require_cliente_jwt(view_func):
    """
    Decorator para validar JWT de cliente e adicionar request.cliente.
    
    Verifica o header X-Cliente-Token e valida o JWT customizado.
    Adiciona o objeto Cliente completo em request.cliente.
    
    Uso:
        @api_view(['POST'])
        @require_oauth_apps
        @require_cliente_jwt
        def minha_view(request):
            cliente = request.cliente
            # ...
    """
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        from wallclub_core.oauth.jwt_utils import validate_cliente_jwt_token
        from apps.cliente.models import Cliente
        
        # Obter token do header
        cliente_token = request.headers.get('X-Cliente-Token')
        if not cliente_token:
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'Token de cliente obrigatório (X-Cliente-Token)'
            }, status=401)
        
        # Validar JWT
        payload = validate_cliente_jwt_token(cliente_token)
        if not payload:
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'Token de cliente inválido ou expirado'
            }, status=401)
        
        # Buscar cliente no banco
        try:
            cliente = Cliente.objects.get(
                id=payload.get('cliente_id'),
                cpf=payload.get('cpf'),
                is_active=True
            )
        except Cliente.DoesNotExist:
            registrar_log(
                'api_decorators',
                f"Cliente não encontrado ou inativo: cliente_id={payload.get('cliente_id')}",
                nivel='WARNING'
            )
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'Cliente não encontrado'
            }, status=404)
        
        # Adicionar cliente ao request
        request.cliente = cliente
        request.cliente_jwt_payload = payload
        
        return view_func(request, *args, **kwargs)
    
    return wrapper
