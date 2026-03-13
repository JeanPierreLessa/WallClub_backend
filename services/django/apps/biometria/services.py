"""
Service para integração com Veriff (verificação de identidade)
"""
import hmac
import hashlib
import requests
from django.utils import timezone
from wallclub_core.utilitarios.config_manager import get_config_manager
from wallclub_core.utilitarios.log_control import registrar_log


class VeriffService:
    """Service para criar sessões e processar webhooks Veriff"""

    @staticmethod
    def _get_veriff_config():
        """Busca configurações Veriff do secret principal no AWS Secrets Manager"""
        import json
        config = get_config_manager()
        secret_string = config.get_secret(config._get_secret_name())
        if not secret_string:
            raise Exception('Não foi possível carregar secrets do AWS')
        return json.loads(secret_string)

    @staticmethod
    def criar_sessao(cliente):
        """
        Cria sessão no Veriff para o cliente.
        Retorna sessionUrl + sessionId.
        """
        secrets = VeriffService._get_veriff_config()
        api_key = secrets.get('VERIFF_API_KEY')
        base_url = secrets.get('VERIFF_BASE_URL', 'https://stationapi.veriff.com')
        webhook_url = secrets.get('VERIFF_WEBHOOK_URL', '')

        partes_nome = cliente.nome.split(' ', 1) if cliente.nome else ['Cliente', 'WallClub']
        first_name = partes_nome[0]
        last_name = partes_nome[1] if len(partes_nome) > 1 else ''

        payload = {
            'verification': {
                'callback': webhook_url,
                'person': {
                    'firstName': first_name,
                    'lastName': last_name,
                },
                'vendorData': str(cliente.id),
            }
        }

        registrar_log(
            'biometria',
            f'[VERIFF] Criando sessão para cliente {cliente.id}',
            nivel='INFO'
        )

        response = requests.post(
            f'{base_url}/v1/sessions',
            headers={
                'X-AUTH-CLIENT': api_key,
                'Content-Type': 'application/json',
            },
            json=payload,
            timeout=15,
        )

        data = response.json()

        if data.get('status') != 'success' or not data.get('verification', {}).get('url'):
            registrar_log(
                'biometria',
                f'[VERIFF] Erro ao criar sessão para cliente {cliente.id}: {data}',
                nivel='ERROR'
            )
            raise Exception(data.get('message', 'Erro ao criar sessão Veriff'))

        verification = data['verification']

        from apps.biometria.models import VeriffSession
        VeriffSession.objects.create(
            cliente=cliente,
            canal_id=cliente.canal_id,
            session_id=verification['id'],
            session_url=verification['url'],
            status='created',
            vendor_data=str(cliente.id),
        )

        registrar_log(
            'biometria',
            f'[VERIFF] Sessão criada para cliente {cliente.id}: {verification["id"]}',
            nivel='INFO'
        )

        return {
            'sessionUrl': verification['url'],
            'sessionId': verification['id'],
        }

    @staticmethod
    def processar_webhook(payload):
        """
        Processa webhook recebido do Veriff.
        Atualiza status da sessão no banco.
        """
        verification = payload.get('verification', {})
        session_id = verification.get('id')
        status = verification.get('status')
        reason = verification.get('reason')

        if not session_id:
            registrar_log('biometria', '[VERIFF] Webhook sem session_id', nivel='ERROR')
            return False

        from apps.biometria.models import VeriffSession
        try:
            sessao = VeriffSession.objects.get(session_id=session_id)
        except VeriffSession.DoesNotExist:
            registrar_log(
                'biometria',
                f'[VERIFF] Sessão não encontrada: {session_id}',
                nivel='ERROR'
            )
            return False

        sessao.status = status
        sessao.veriff_reason = reason
        sessao.decision_time = timezone.now()
        sessao.save()

        registrar_log(
            'biometria',
            f'[VERIFF] Webhook processado - sessão {session_id}: {status}',
            nivel='INFO'
        )

        if status == 'approved':
            registrar_log(
                'biometria',
                f'[VERIFF] Cliente {sessao.cliente_id} APROVADO na verificação',
                nivel='INFO'
            )

        return True

    @staticmethod
    def validar_hmac(payload_bytes, signature):
        """
        Valida assinatura HMAC-SHA256 do webhook Veriff.
        """
        secrets = VeriffService._get_veriff_config()
        shared_secret = secrets.get('VERIFF_SHARED_SECRET')

        expected = hmac.new(
            shared_secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected.lower(), signature.lower())

    @staticmethod
    def consultar_status(session_id, cliente_id):
        """
        Consulta status de uma sessão Veriff no banco local.
        """
        from apps.biometria.models import VeriffSession
        try:
            sessao = VeriffSession.objects.get(
                session_id=session_id,
                cliente_id=cliente_id,
            )
        except VeriffSession.DoesNotExist:
            return None

        MENSAGENS = {
            'created': 'Verificação ainda não iniciada',
            'submitted': 'Verificação em processamento',
            'approved': 'Identidade verificada com sucesso',
            'declined': 'Verificação não aprovada',
            'resubmission_requested': 'É necessário refazer a verificação',
            'expired': 'Sessão expirada, inicie novamente',
            'abandoned': 'Verificação abandonada',
        }

        return {
            'status': sessao.status,
            'mensagem': MENSAGENS.get(sessao.status, 'Status desconhecido'),
        }
