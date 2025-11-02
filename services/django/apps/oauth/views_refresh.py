# apps/oauth/views_refresh.py
"""
Endpoint para renovação de access token usando refresh token
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
def refresh_token(request):
    """
    Renova access token usando refresh token
    
    Request:
        {
            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        }
    
    Response (200):
        {
            "sucesso": true,
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "expires_at": "2025-10-28T21:18:00Z"
        }
    
    Response (401):
        {
            "sucesso": false,
            "mensagem": "Refresh token inválido ou expirado"
        }
    """
    try:
        refresh_token = request.data.get('refresh_token')
        
        if not refresh_token:
            return Response({
                'sucesso': False,
                'mensagem': 'Refresh token é obrigatório'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validar e renovar token
        from apps.cliente.jwt_cliente import refresh_cliente_access_token
        
        resultado = refresh_cliente_access_token(refresh_token)
        
        if resultado:
            registrar_log('apps.oauth', 
                f"✅ Access token renovado com sucesso")
            
            return Response({
                'sucesso': True,
                'token': resultado['token'],
                'expires_at': resultado['expires_at']
            }, status=status.HTTP_200_OK)
        else:
            registrar_log('apps.oauth', 
                "❌ Refresh token inválido ou expirado", nivel='WARNING')
            
            return Response({
                'sucesso': False,
                'mensagem': 'Refresh token inválido ou expirado. Faça login novamente.'
            }, status=status.HTTP_401_UNAUTHORIZED)
    
    except Exception as e:
        registrar_log('apps.oauth', 
            f"Erro ao renovar token: {str(e)}", nivel='ERROR')
        
        return Response({
            'sucesso': False,
            'mensagem': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
