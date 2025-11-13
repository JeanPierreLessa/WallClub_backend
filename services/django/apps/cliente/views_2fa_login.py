"""
Views para autenticação 2FA no login do App Móvel.
Endpoints para gerenciar segunda camada de autenticação.
"""
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from wallclub_core.utilitarios.log_control import registrar_log
from wallclub_core.seguranca.services_2fa import OTPService
from .services_2fa_login import ClienteAuth2FAService
from wallclub_core.oauth.decorators import require_oauth_apps
from apps.conta_digital.decorators import require_jwt_only


@api_view(['POST'])
@require_oauth_apps
def verificar_necessidade_2fa(request):
    """
    Verifica se 2FA é necessário para o login/transação.
    Usa auth_token para segurança (cliente_id nunca exposto).

    POST /api/v1/cliente/2fa/verificar_necessidade/
    Body: {
        'auth_token': str,  # Token temporário do login
        'device_fingerprint': str,
        'contexto': str  # 'login', 'transacao', 'alteracao_dados'
    }

    Returns:
        200: {
            'necessario': bool,
            'motivo': str,
            'dispositivo_confiavel': bool,
            'token': str (se não precisar 2FA)
        }
    """
    try:
        auth_token = request.data.get('auth_token')
        device_fingerprint = request.data.get('device_fingerprint')
        contexto = request.data.get('contexto', 'login')

        if not auth_token or not device_fingerprint:
            return Response({
                'sucesso': False,
                'mensagem': 'auth_token e device_fingerprint são obrigatórios'
            }, status=status.HTTP_400_BAD_REQUEST)

        resultado = ClienteAuth2FAService.verificar_necessidade_2fa(
            auth_token=auth_token,
            device_fingerprint=device_fingerprint,
            contexto=contexto
        )

        return Response(resultado, status=status.HTTP_200_OK)

    except Exception as e:
        registrar_log('apps.cliente',
            f"Erro ao verificar necessidade 2FA: {str(e)}", nivel='ERROR')
        return Response({
            'necessario': True,  # Fail-secure
            'mensagem': 'Erro ao verificar 2FA'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@require_oauth_apps
def solicitar_codigo_2fa_login(request):
    """
    Solicita código 2FA para login do app.
    Usa auth_token para segurança.

    POST /api/v1/cliente/2fa/solicitar_codigo/
    Body: {
        'auth_token': str,  # Token temporário do login
        'device_fingerprint': str (opcional)
    }

    Returns:
        200: {'sucesso': True, 'mensagem': 'Código enviado'}
        400: {'sucesso': False, 'mensagem': 'Erro'}
    """
    try:
        auth_token = request.data.get('auth_token')
        device_fingerprint = request.data.get('device_fingerprint')  # Não usar default vazio
        # Capturar IP real considerando proxies/load balancers
        from .views import get_client_ip
        ip_address = get_client_ip(request)

        if not auth_token:
            return Response({
                'sucesso': False,
                'mensagem': 'auth_token é obrigatório'
            }, status=status.HTTP_400_BAD_REQUEST)

        resultado = ClienteAuth2FAService.solicitar_2fa_login(
            auth_token=auth_token,
            device_fingerprint=device_fingerprint,
            ip_address=ip_address
        )

        if resultado['sucesso']:
            return Response(resultado, status=status.HTTP_200_OK)
        else:
            return Response(resultado, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        registrar_log('apps.cliente',
            f"Erro ao solicitar 2FA: {str(e)}", nivel='ERROR')
        return Response({
            'sucesso': False,
            'mensagem': 'Erro ao solicitar código 2FA'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@require_oauth_apps
def validar_codigo_2fa_login(request):
    """
    Valida código 2FA e retorna JWT final.
    Usa auth_token para segurança.

    POST /api/v1/cliente/2fa/validar_codigo/
    Body: {
        'auth_token': str,  # Token temporário do login
        'codigo': str,
        'device_fingerprint': str,
        'marcar_confiavel': bool (opcional, default=True)
    }

    Returns:
        200: {
            'sucesso': True,
            'mensagem': '2FA validado',
            'token': str,  # JWT final (30 dias)
            'refresh_token': str,
            'expires_at': str
        }
    """
    try:
        auth_token = request.data.get('auth_token')
        codigo = request.data.get('codigo')
        device_fingerprint = request.data.get('device_fingerprint')
        marcar_confiavel = request.data.get('marcar_confiavel', True)
        nome_dispositivo = request.data.get('nome_dispositivo')  # Opcional
        # Capturar IP real considerando proxies/load balancers
        from .views import get_client_ip
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT')

        if not all([auth_token, codigo, device_fingerprint]):
            return Response({
                'sucesso': False,
                'mensagem': 'Dados obrigatórios: auth_token, codigo, device_fingerprint'
            }, status=status.HTTP_400_BAD_REQUEST)

        resultado = ClienteAuth2FAService.validar_2fa_login(
            auth_token=auth_token,
            codigo_otp=codigo,
            device_fingerprint=device_fingerprint,
            marcar_confiavel=marcar_confiavel,
            ip_address=ip_address,
            user_agent=user_agent,
            nome_dispositivo=nome_dispositivo
        )

        if resultado['sucesso']:
            return Response(resultado, status=status.HTTP_200_OK)
        else:
            return Response(resultado, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        registrar_log('apps.cliente',
            f"Erro ao validar 2FA: {str(e)}", nivel='ERROR')
        return Response({
            'sucesso': False,
            'mensagem': 'Erro ao validar código 2FA'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@require_jwt_only
def verificar_primeira_transacao(request):
    """
    Verifica se é a primeira transação do dia (requer 2FA).

    POST /api/v1/cliente/2fa/verificar-primeira-transacao/

    Returns:
        200: {
            'primeira_transacao': bool,
            'requer_2fa': bool
        }
    """
    try:
        cliente_id = request.cliente.id

        primeira = ClienteAuth2FAService.verificar_primeira_transacao_dia(cliente_id)

        return Response({
            'primeira_transacao': primeira,
            'requer_2fa': primeira,
            'mensagem': 'Primeira transação do dia requer 2FA' if primeira else 'Transação liberada'
        }, status=status.HTTP_200_OK)

    except Exception as e:
        registrar_log('apps.cliente',
            f"Erro ao verificar primeira transação: {str(e)}", nivel='ERROR')
        return Response({
            'primeira_transacao': False,
            'requer_2fa': False,
            'mensagem': 'Erro ao verificar transação'
        }, status=status.HTTP_200_OK)  # Fail-open


@api_view(['POST'])
@require_jwt_only
def registrar_transacao_completa(request):
    """
    Registra que cliente completou transação (para controle de primeira do dia).

    POST /api/v1/cliente/2fa/registrar-transacao/

    Returns:
        200: {'sucesso': True}
    """
    try:
        cliente_id = request.cliente.id

        ClienteAuth2FAService.registrar_transacao_2fa(cliente_id)

        return Response({
            'sucesso': True,
            'mensagem': 'Transação registrada'
        }, status=status.HTTP_200_OK)

    except Exception as e:
        registrar_log('apps.cliente',
            f"Erro ao registrar transação: {str(e)}", nivel='ERROR')
        return Response({
            'sucesso': True,  # Não falhar
            'mensagem': 'Erro ao registrar transação'
        }, status=status.HTTP_200_OK)
