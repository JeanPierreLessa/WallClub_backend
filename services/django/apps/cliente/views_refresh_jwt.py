# apps/cliente/views_refresh_jwt.py
"""
Endpoint para renovação de JWT token do cliente
Data: 27/10/2025
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from wallclub_core.oauth.decorators import require_oauth_apps
from wallclub_core.utilitarios.log_control import registrar_log


@api_view(['POST'])
@permission_classes([AllowAny])
@require_oauth_apps
def refresh_jwt_token(request):
    """
    Renova access token JWT do cliente usando refresh token
    Implementa sliding window de 30 dias + revalidação forçada a cada 90 dias

    Request:
        {
            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "device_fingerprint": "abc123..." (opcional mas recomendado)
        }

    Response (200):
        {
            "sucesso": true,
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "expires_at": "2025-10-28T21:30:00Z"
        }

    Response (401 - Requer 2FA):
        {
            "sucesso": false,
            "requer_2fa": true,
            "motivo": "dispositivo_expirado_inatividade",
            "mensagem": "Dispositivo inativo há mais de 30 dias. Revalidação necessária."
        }

    Response (401 - Token inválido):
        {
            "sucesso": false,
            "mensagem": "Refresh token inválido ou expirado"
        }
    """
    try:
        refresh_token = request.data.get('refresh_token')
        device_fingerprint = request.data.get('device_fingerprint')

        if not refresh_token:
            return Response({
                'sucesso': False,
                'mensagem': 'Refresh token é obrigatório'
            }, status=status.HTTP_400_BAD_REQUEST)

        if not device_fingerprint:
            return Response({
                'sucesso': False,
                'mensagem': 'Device fingerprint é obrigatório para validação de segurança'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validar e renovar token (com validação de dispositivo)
        from apps.cliente.jwt_cliente import refresh_cliente_access_token

        resultado = refresh_cliente_access_token(refresh_token, device_fingerprint)

        if resultado:
            # Verificar se requer 2FA
            if resultado.get('requer_2fa'):
                registrar_log('apps.cliente',
                    f"🔒 Refresh bloqueado - requer 2FA: {resultado.get('motivo')}",
                    nivel='INFO')

                return Response({
                    'sucesso': False,
                    'requer_2fa': True,
                    'motivo': resultado.get('motivo'),
                    'mensagem': resultado.get('mensagem'),
                    'dias_desde_revalidacao': resultado.get('dias_desde_revalidacao')
                }, status=status.HTTP_401_UNAUTHORIZED)

            # Token renovado com sucesso
            registrar_log('apps.cliente',
                "✅ JWT access token renovado com sucesso")

            return Response({
                'sucesso': True,
                'token': resultado['token'],
                'expires_at': resultado['expires_at']
            }, status=status.HTTP_200_OK)
        else:
            registrar_log('apps.cliente',
                "❌ Refresh token inválido ou expirado", nivel='WARNING')

            return Response({
                'sucesso': False,
                'mensagem': 'Refresh token inválido ou expirado. Faça login novamente.',
                'codigo': 'token_expired'
            }, status=status.HTTP_401_UNAUTHORIZED)

    except Exception as e:
        registrar_log('apps.cliente',
            f"Erro ao renovar JWT token: {str(e)}", nivel='ERROR')

        return Response({
            'sucesso': False,
            'mensagem': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
