"""
Decorators específicos para endpoints de conta digital.
"""
from functools import wraps
from django.http import JsonResponse
from wallclub_core.utilitarios.log_control import registrar_log


def require_jwt_only(view_func):
    """
    Decorator para validar apenas JWT (sem exigir oauth_validated)
    Específico para endpoints de consulta da conta digital
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            registrar_log("apps.conta_digital", "Tentativa de acesso sem token")
            return JsonResponse({'error': 'Token obrigatório'}, status=401)

        token = auth_header.split(' ')[1]
        
        # Verificar se é JWT de cliente - usando decodificação direta
        import jwt
        from django.conf import settings
        from datetime import datetime
        
        try:
            # Decodificar o token sem verificar na tabela ClienteJWTToken
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            
            # Verificar expiração
            exp = payload.get('exp')
            if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
                registrar_log("apps.conta_digital", "JWT expirado")
                return JsonResponse({'error': 'Token expirado'}, status=401)
            
            # Verificar se tem dados mínimos do cliente
            if not payload.get('cliente_id') or not payload.get('cpf'):
                registrar_log("apps.conta_digital", "JWT sem dados de cliente")
                return JsonResponse({'error': 'Token inválido'}, status=401)
                
            registrar_log("apps.conta_digital", f"JWT válido para cliente {payload.get('cliente_id')}")
            
        except jwt.ExpiredSignatureError:
            registrar_log("apps.conta_digital", "JWT expirado")
            return JsonResponse({'error': 'Token expirado'}, status=401)
        except jwt.InvalidTokenError as e:
            registrar_log("apps.conta_digital", "JWT inválido")
            return JsonResponse({'error': 'Token inválido'}, status=401)
        except Exception as e:
            registrar_log("apps.conta_digital", f"Erro ao validar JWT: {str(e)}", nivel='ERROR')
            return JsonResponse({'error': 'Erro ao validar token'}, status=401)
        
        # Adicionar dados do cliente ao request (compatibilidade com IsAuthenticated)
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
