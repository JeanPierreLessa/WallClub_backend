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
        "canal_id": 1,
        "native_id": "ABC123-DEF456",
        "screen_resolution": "1170x2532",
        "device_model": "iPhone15,2",
        "os_version": "17.2",
        "device_brand": "Apple",
        "timezone": "America/Sao_Paulo",
        "platform": "ios",
        "device_name": "iPhone 14 Pro" (opcional)
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

        # Componentes individuais do fingerprint
        native_id = request.data.get('native_id', '').strip()
        screen_resolution = request.data.get('screen_resolution', '').strip()
        device_model = request.data.get('device_model', '').strip()
        os_version = request.data.get('os_version', '').strip()
        device_brand = request.data.get('device_brand', '').strip()
        timezone = request.data.get('timezone', '').strip()
        platform = request.data.get('platform', '').strip()
        device_name = request.data.get('device_name', '')

        if not cpf or not device_fingerprint or not canal_id:
            return Response({
                'success': False,
                'error': 'CPF, device_fingerprint e canal_id são obrigatórios'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Buscar cliente (filter + first para evitar MultipleObjectsReturned)
        cliente = Cliente.objects.filter(cpf=cpf, canal_id=canal_id, is_active=True).first()

        if not cliente:
            registrar_log('apps.cliente', f"Login biométrico falhou: CPF {cpf} não encontrado ou inativo no canal {canal_id}", nivel='WARNING')
            return Response({
                'success': False,
                'error': 'Cliente não encontrado'
            }, status=status.HTTP_404_NOT_FOUND)

        # Validar dispositivo com análise de similaridade
        dados_dispositivo = {
            'device_fingerprint': device_fingerprint,
            'native_id': native_id,
            'screen_resolution': screen_resolution,
            'device_model': device_model,
            'os_version': os_version,
            'device_brand': device_brand,
            'timezone': timezone,
            'platform': platform,
        }

        resultado = DeviceManagementService.validar_dispositivo_com_similaridade(
            user_id=cliente.id,
            tipo_usuario='cliente',
            dados_dispositivo=dados_dispositivo
        )

        decisao = resultado.get('decisao')

        if decisao == 'block':
            registrar_log('apps.cliente', f"Login biométrico bloqueado: {resultado['motivo']} - CPF {cpf}", nivel='WARNING')
            return Response({
                'success': False,
                'error': resultado['motivo']
            }, status=status.HTTP_403_FORBIDDEN)

        if decisao == 'require_otp':
            registrar_log('apps.cliente', f"Login biométrico requer 2FA: {resultado['motivo']} - CPF {cpf}", nivel='INFO')
            return Response({
                'success': False,
                'require_otp': True,
                'motivo': resultado['motivo'],
                'similaridade': resultado.get('similaridade_max')
            }, status=status.HTTP_403_FORBIDDEN)

        # decisao == 'allow'
        if resultado.get('requer_monitoramento'):
            registrar_log('apps.cliente',
                f"⚠️ Login biométrico permitido com monitoramento (similaridade: {resultado.get('similaridade_max')}) - CPF {cpf}",
                nivel='WARNING')

        # Gerar tokens JWT
        jwt_data = generate_cliente_jwt_token(cliente, request=request)

        registrar_log('apps.cliente', f"Login biométrico bem-sucedido: CPF {cpf}", nivel='INFO')

        return Response({
            'success': True,
            'token': jwt_data['token'],
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
