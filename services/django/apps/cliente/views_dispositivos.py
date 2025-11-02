"""
Views para gestão de dispositivos do cliente no app móvel.
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from wallclub_core.oauth.decorators import require_oauth_apps
from apps.conta_digital.decorators import require_jwt_only
from wallclub_core.seguranca.services_device import DeviceManagementService
from wallclub_core.utilitarios.log_control import registrar_log


@api_view(['POST'])
@require_jwt_only
def meus_dispositivos(request):
    """
    Lista dispositivos confiáveis do cliente logado.
    
    Headers:
        - Authorization: Bearer <jwt_token>
    
    Returns:
        {
            "sucesso": bool,
            "dispositivos": [
                {
                    "id": int,
                    "nome_dispositivo": str,
                    "ultimo_acesso": str (ISO),
                    "ativo": bool,
                    "confiavel": bool,
                    "dias_desde_acesso": int,
                    "criado_em": str (ISO),
                    "ip_address": str
                }
            ],
            "total": int
        }
    """
    try:
        # Extrair cliente_id do JWT
        cliente_id = request.user.cliente_id
        
        # Listar dispositivos
        dispositivos = DeviceManagementService.listar_dispositivos(
            user_id=cliente_id,
            tipo_usuario='cliente'
        )
        
        return Response({
            'sucesso': True,
            'dispositivos': dispositivos,
            'total': len(dispositivos)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        registrar_log('apps.cliente',
            f"Erro ao listar dispositivos: {str(e)}", nivel='ERROR')
        return Response({
            'sucesso': False,
            'mensagem': 'Erro ao listar dispositivos'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@require_jwt_only
def revogar_meu_dispositivo(request):
    """
    Revoga dispositivo confiável do cliente logado.
    
    Payload:
        {
            "device_fingerprint": str
        }
    
    Headers:
        - Authorization: Bearer <jwt_token>
    
    Returns:
        {
            "sucesso": bool,
            "mensagem": str
        }
    """
    try:
        # Extrair cliente_id do JWT
        cliente_id = request.user.cliente_id
        
        # Validar payload
        device_fingerprint = request.data.get('device_fingerprint')
        if not device_fingerprint:
            return Response({
                'sucesso': False,
                'mensagem': 'device_fingerprint é obrigatório'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Revogar dispositivo
        resultado = DeviceManagementService.revogar_dispositivo(
            user_id=cliente_id,
            tipo_usuario='cliente',
            device_fingerprint=device_fingerprint
        )
        
        if resultado['sucesso']:
            registrar_log('apps.cliente',
                f"Dispositivo revogado pelo cliente: cliente_id={cliente_id}")
            
            return Response({
                'sucesso': True,
                'mensagem': 'Dispositivo removido com sucesso'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'sucesso': False,
                'mensagem': resultado['mensagem']
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        registrar_log('apps.cliente',
            f"Erro ao revogar dispositivo: {str(e)}", nivel='ERROR')
        return Response({
            'sucesso': False,
            'mensagem': 'Erro ao processar solicitação'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


