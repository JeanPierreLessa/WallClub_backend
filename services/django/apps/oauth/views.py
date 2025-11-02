"""
Views para endpoints OAuth 2.0
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from datetime import datetime, timedelta
from wallclub_core.oauth.models import OAuthClient, OAuthToken
from wallclub_core.oauth.services import OAuthService
from wallclub_core.utilitarios.log_control import registrar_log


@api_view(['POST'])
@permission_classes([AllowAny])
def token_request(request):
    """
    OAuth 2.0 Token Endpoint
    POST /api/oauth/token/
    """
    client_id = request.data.get('client_id')
    client_secret = request.data.get('client_secret')
    grant_type = request.data.get('grant_type')
    
    if not all([client_id, client_secret, grant_type]):
        return Response({
            'error': 'invalid_request',
            'error_description': 'client_id, client_secret e grant_type são obrigatórios'
        }, status=400)
    
    if grant_type != 'client_credentials':
        return Response({
            'error': 'unsupported_grant_type',
            'error_description': 'Apenas client_credentials é suportado'
        }, status=400)
    
    try:
        # Validar cliente OAuth
        client = OAuthClient.objects.get(
            client_id=client_id,
            client_secret=client_secret,
            is_active=True
        )
        
        # Device fingerprint: apenas para clientes mobile/web
        # Clientes server-to-server (POS, internos) não precisam
        device_fingerprint = None
        if not OAuthService.is_server_based_client(client.client_id):
            device_fingerprint = OAuthService.extract_device_fingerprint(request)
        
        # Criar novo token
        token = OAuthService.create_oauth_token(
            client=client,
            device_fingerprint=device_fingerprint
        )
        
        if device_fingerprint:
            registrar_log(
                "apps.oauth", 
                f"Token criado para {client.name} - Device: {device_fingerprint[:8]}..."
            )
        else:
            registrar_log(
                "apps.oauth", 
                f"Token criado para {client.name} (sem device binding)"
            )
        
        return Response({
            'access_token': token.access_token,
            'refresh_token': token.refresh_token,
            'token_type': 'Bearer',
            'expires_in': 86400  # 24 horas
        })
        
    except OAuthClient.DoesNotExist:
        registrar_log("apps.oauth", f"Cliente OAuth inválido: {client_id}", nivel='ERROR')
        return Response({
            'error': 'invalid_client',
            'error_description': 'Cliente OAuth inválido'
        }, status=401)


@api_view(['POST'])
@permission_classes([AllowAny])
def token_refresh(request):
    """
    OAuth 2.0 Token Refresh Endpoint
    POST /api/oauth/refresh/
    """
    refresh_token = request.data.get('refresh_token')
    
    if not refresh_token:
        return Response({
            'error': 'invalid_request',
            'error_description': 'refresh_token é obrigatório'
        }, status=400)
    
    # Usar OAuthService para renovar token
    result = OAuthService.refresh_token(refresh_token)
    
    if result['success']:
        return Response({
            'access_token': result['access_token'],
            'token_type': 'Bearer',
            'expires_in': result['expires_in']
        })
    else:
        return Response({
            'error': result['error'],
            'error_description': result['error_description']
        }, status=401)


@api_view(['POST'])
@permission_classes([AllowAny])
def token_revoke(request):
    """
    OAuth 2.0 Token Revoke Endpoint
    POST /api/oauth/revoke/
    """
    access_token = request.data.get('token')
    
    if not access_token:
        return Response({
            'error': 'invalid_request',
            'error_description': 'token é obrigatório'
        }, status=400)
    
    # Usar OAuthService para revogar token
    revoked = OAuthService.revoke_token(access_token)
    
    if revoked:
        return Response({
            'message': 'Token revogado com sucesso'
        }, status=200)
    else:
        return Response({
            'error': 'invalid_token',
            'error_description': 'Token não encontrado ou já revogado'
        }, status=404)
