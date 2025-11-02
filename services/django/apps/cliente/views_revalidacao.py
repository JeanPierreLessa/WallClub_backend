"""
Views para revalidação de celular do cliente.
Endpoints para o App Móvel gerenciar revalidação periódica.
"""
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from wallclub_core.utilitarios.log_control import registrar_log
from .services_revalidacao_celular import RevalidacaoCelularService
from wallclub_core.oauth.decorators import require_oauth_apps
from apps.conta_digital.decorators import require_jwt_only


@api_view(['POST'])
@require_oauth_apps
def verificar_status_celular(request):
    """
    Verifica o status de validade do celular do cliente.
    Usa auth_token para permitir verificação antes do login completo.
    
    POST /api/v1/cliente/celular/status/
    Body: {
        'auth_token': str  # Token temporário do login
    }
    
    Returns:
        200: {
            'valido': bool,
            'dias_restantes': int,
            'precisa_revalidar': bool,
            'ultima_validacao': datetime
        }
    """
    try:
        auth_token = request.data.get('auth_token')
        
        if not auth_token:
            return Response({
                'sucesso': False,
                'mensagem': 'auth_token é obrigatório'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validar auth_token e extrair cliente_id
        from apps.cliente.jwt_cliente import validate_auth_pending_token
        
        payload = validate_auth_pending_token(auth_token)
        if not payload:
            return Response({
                'sucesso': False,
                'mensagem': 'Token de autenticação inválido ou expirado'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        cliente_id = payload.get('cliente_id')
        
        resultado = RevalidacaoCelularService.verificar_validade_celular(cliente_id)
        
        return Response(resultado, status=status.HTTP_200_OK)
        
    except Exception as e:
        registrar_log('apps.cliente', 
            f"Erro ao verificar status celular: {str(e)}", nivel='ERROR')
        return Response({
            'sucesso': False,
            'mensagem': 'Erro ao verificar status do celular'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@require_oauth_apps
def solicitar_codigo_revalidacao(request):
    """
    Solicita código OTP para revalidação de celular.
    Usa auth_token para permitir solicitação antes do login completo.
    
    POST /api/v1/cliente/celular/solicitar-codigo/
    Body: {
        'auth_token': str  # Token temporário do login
    }
    
    Returns:
        200: {'sucesso': True, 'mensagem': 'Código enviado'}
        400: {'sucesso': False, 'mensagem': 'Erro'}
    """
    try:
        auth_token = request.data.get('auth_token')
        
        if not auth_token:
            return Response({
                'sucesso': False,
                'mensagem': 'auth_token é obrigatório'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validar auth_token e extrair dados
        from apps.cliente.jwt_cliente import validate_auth_pending_token
        
        payload = validate_auth_pending_token(auth_token)
        if not payload:
            return Response({
                'sucesso': False,
                'mensagem': 'Token de autenticação inválido ou expirado'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        from apps.cliente.models import Cliente
        cliente_id = payload.get('cliente_id')
        canal_id = payload.get('canal_id')
        
        if not cliente_id or not canal_id:
            return Response({
                'sucesso': False,
                'mensagem': 'Token inválido'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        resultado = RevalidacaoCelularService.solicitar_revalidacao_celular(
            cliente_id=cliente_id,
            canal_id=canal_id
        )
        
        if resultado['sucesso']:
            return Response(resultado, status=status.HTTP_200_OK)
        else:
            return Response(resultado, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        registrar_log('apps.cliente', 
            f"Erro ao solicitar código: {str(e)}", nivel='ERROR')
        return Response({
            'sucesso': False,
            'mensagem': 'Erro ao solicitar código de revalidação'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@require_oauth_apps
def validar_codigo_revalidacao(request):
    """
    Valida código OTP e revalida o celular.
    Usa auth_token para permitir validação antes do login completo.
    
    POST /api/v1/cliente/celular/validar-codigo/
    Body: {
        'auth_token': str,  # Token temporário do login
        'codigo': str
    }
    
    Returns:
        200: {'sucesso': True, 'mensagem': 'Celular revalidado'}
        400: {'sucesso': False, 'mensagem': 'Código inválido'}
    """
    try:
        auth_token = request.data.get('auth_token')
        codigo = request.data.get('codigo')
        
        if not auth_token:
            return Response({
                'sucesso': False,
                'mensagem': 'auth_token é obrigatório'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validar auth_token e extrair cliente_id
        from apps.cliente.jwt_cliente import validate_auth_pending_token
        
        payload = validate_auth_pending_token(auth_token)
        if not payload:
            return Response({
                'sucesso': False,
                'mensagem': 'Token de autenticação inválido ou expirado'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        cliente_id = payload.get('cliente_id')
        
        if not codigo:
            return Response({
                'sucesso': False,
                'mensagem': 'Código é obrigatório'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        resultado = RevalidacaoCelularService.validar_celular(
            cliente_id=cliente_id,
            codigo_otp=codigo
        )
        
        if resultado['sucesso']:
            return Response(resultado, status=status.HTTP_200_OK)
        else:
            return Response(resultado, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        registrar_log('apps.cliente', 
            f"Erro ao validar código: {str(e)}", nivel='ERROR')
        return Response({
            'sucesso': False,
            'mensagem': 'Erro ao validar código'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@require_jwt_only
def verificar_bloqueio_transacao(request):
    """
    Verifica se transação está bloqueada por celular expirado.
    App deve chamar antes de transações.
    
    POST /api/v1/cliente/celular/verificar-bloqueio/
    Body: {
        'origem': 'app'  # sempre 'app' para mobile
    }
    
    Returns:
        200: {
            'bloqueado': bool,
            'mensagem': str,
            'dias_expirado': int (se bloqueado)
        }
    """
    try:
        cliente_id = request.user.cliente_id
        origem = request.data.get('origem', 'app')
        
        resultado = RevalidacaoCelularService.bloquear_por_celular_expirado(
            cliente_id=cliente_id,
            origem=origem
        )
        
        return Response(resultado, status=status.HTTP_200_OK)
        
    except Exception as e:
        registrar_log('apps.cliente', 
            f"Erro ao verificar bloqueio: {str(e)}", nivel='ERROR')
        return Response({
            'bloqueado': False,
            'mensagem': 'Erro ao verificar bloqueio'
        }, status=status.HTTP_200_OK)  # Fail-open
