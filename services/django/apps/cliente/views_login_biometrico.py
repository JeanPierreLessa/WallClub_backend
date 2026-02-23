"""
View para login biométrico (device fingerprint + CPF)
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from apps.cliente.models import Cliente
from apps.cliente.jwt_cliente import generate_cliente_jwt_token
from wallclub_core.oauth.decorators import require_oauth_apps
from wallclub_core.seguranca.services_device import DeviceManagementService
from wallclub_core.utilitarios.log_control import registrar_log


@api_view(['POST'])
@permission_classes([AllowAny])
@require_oauth_apps
def login_biometrico(request):
    """
    Autentica cliente usando device fingerprint + CPF

    Payload esperado:
    {
        "cpf": "12345678901",
        "device_fingerprint": "hash_do_dispositivo",
        "canal_id": 1
    }

    Retorna:
    {
        "success": true,
        "auth_token": "jwt_token",
        "refresh_token": "refresh_token",
        "cliente": {...}
    }
    """
    try:
        cpf = request.data.get('cpf', '').strip()
        device_fingerprint = request.data.get('device_fingerprint', '').strip()
        canal_id = request.data.get('canal_id')

        if not cpf or not device_fingerprint or not canal_id:
            return Response({
                'success': False,
                'error': 'CPF, device_fingerprint e canal_id são obrigatórios'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Buscar cliente (filter + first para evitar MultipleObjectsReturned)
        cliente = Cliente.objects.filter(cpf=cpf, is_active=True).first()

        if not cliente:
            registrar_log('apps.cliente', f"Login biométrico falhou: CPF {cpf} não encontrado ou inativo", nivel='WARNING')
            return Response({
                'success': False,
                'error': 'Cliente não encontrado'
            }, status=status.HTTP_404_NOT_FOUND)

        # Verificar se dispositivo está cadastrado e confiável
        dispositivo_confiavel = DeviceManagementService.verificar_dispositivo_confiavel(
            cliente_id=cliente.id,
            device_fingerprint=device_fingerprint
        )

        if not dispositivo_confiavel:
            registrar_log('apps.cliente', f"Login biométrico falhou: Device fingerprint não confiável para CPF {cpf}", nivel='WARNING')
            return Response({
                'success': False,
                'error': 'Dispositivo não autorizado para login biométrico'
            }, status=status.HTTP_403_FORBIDDEN)

        # Registrar acesso do dispositivo
        DeviceManagementService.registrar_acesso_dispositivo(
            cliente_id=cliente.id,
            device_fingerprint=device_fingerprint
        )

        # Gerar tokens JWT
        jwt_data = generate_cliente_jwt_token(cliente, request=request)

        registrar_log('apps.cliente', f"Login biométrico bem-sucedido: CPF {cpf}", nivel='INFO')

        return Response({
            'success': True,
            'auth_token': jwt_data['auth_token'],
            'refresh_token': jwt_data['refresh_token'],
            'cliente': {
                'id': cliente.id,
                'cpf': cliente.cpf,
                'nome': cliente.nome,
                'email': cliente.email,
                'celular': cliente.celular
            }
        })

    except Exception as e:
        registrar_log('apps.cliente', f"Erro no login biométrico: {str(e)}", nivel='ERROR')
        return Response({
            'success': False,
            'error': 'Erro interno no servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
