"""
View para login biométrico (device fingerprint + CPF)
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from apps.cliente.models import Cliente
from apps.cliente.jwt_cliente import generate_cliente_jwt_token
from wallclub_core.oauth.decorators import require_oauth_apps
from wallclub_core.seguranca.services_device import DeviceManagementService
from wallclub_core.utilitarios.log_control import registrar_log
import json


@csrf_exempt
@require_http_methods(["POST"])
@require_oauth_apps
def login_biometrico(request):
    """
    Autentica cliente usando device fingerprint + CPF

    Payload esperado:
    {
        "cpf": "12345678901",
        "device_fingerprint": "hash_do_dispositivo"
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
        data = json.loads(request.body)
        cpf = data.get('cpf', '').strip()
        device_fingerprint = data.get('device_fingerprint', '').strip()

        if not cpf or not device_fingerprint:
            return JsonResponse({
                'success': False,
                'error': 'CPF e device_fingerprint são obrigatórios'
            }, status=400)

        # Buscar cliente
        try:
            cliente = Cliente.objects.get(cpf=cpf)
        except Cliente.DoesNotExist:
            registrar_log('apps.cliente', f"Login biométrico falhou: CPF {cpf} não encontrado", nivel='WARNING')
            return JsonResponse({
                'success': False,
                'error': 'Cliente não encontrado'
            }, status=404)

        # Verificar se cliente está ativo
        if not cliente.ativo:
            registrar_log('apps.cliente', f"Login biométrico falhou: Cliente {cpf} inativo", nivel='WARNING')
            return JsonResponse({
                'success': False,
                'error': 'Cliente inativo'
            }, status=403)

        # Verificar se dispositivo está cadastrado e confiável
        dispositivo_confiavel = DeviceManagementService.verificar_dispositivo_confiavel(
            cliente_id=cliente.id,
            device_fingerprint=device_fingerprint
        )

        if not dispositivo_confiavel:
            registrar_log('apps.cliente', f"Login biométrico falhou: Device fingerprint não confiável para CPF {cpf}", nivel='WARNING')
            return JsonResponse({
                'success': False,
                'error': 'Dispositivo não autorizado para login biométrico'
            }, status=403)

        # Registrar acesso do dispositivo
        DeviceManagementService.registrar_acesso_dispositivo(
            cliente_id=cliente.id,
            device_fingerprint=device_fingerprint
        )

        # Gerar tokens JWT
        jwt_data = generate_cliente_jwt_token(cliente, request=request)

        registrar_log('apps.cliente', f"Login biométrico bem-sucedido: CPF {cpf}", nivel='INFO')

        return JsonResponse({
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

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'JSON inválido'
        }, status=400)
    except Exception as e:
        registrar_log('apps.cliente', f"Erro no login biométrico: {str(e)}", nivel='ERROR')
        return JsonResponse({
            'success': False,
            'error': 'Erro interno no servidor'
        }, status=500)
