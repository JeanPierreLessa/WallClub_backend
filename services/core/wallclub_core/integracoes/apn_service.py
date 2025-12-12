"""
Serviço APN para envio de push notifications iOS
Sistema unificado usando templates
"""
import os
import json
from django.conf import settings
from django.db import connection
from wallclub_core.utilitarios.log_control import registrar_log
from wallclub_core.estr_organizacional.canal import Canal
from wallclub_core.integracoes.messages_template_service import MessagesTemplateService


class APNService:
    """
    Serviço unificado para envio de push notifications via APN (iOS)
    Usa sistema de templates para todas as notificações
    """
    _instances = {}  # Singleton por canal_id

    @classmethod
    def get_instance(cls, canal_id):
        """Retorna instância singleton do APNService para o canal específico"""
        if canal_id not in cls._instances:
            cls._instances[canal_id] = APNService(canal_id)
        return cls._instances[canal_id]

    def __init__(self, canal_id):
        """Inicializa o serviço APN para um canal específico"""
        self.canal_id = canal_id
        self.initialized = False
        self.cert_path = None
        self.key_path = None
        self._initialize_apn()

    def _get_apn_credentials(self):
        """Busca os certificados APN para o canal (do banco ou arquivo local)"""
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT apn_cert_pem, apn_key_pem FROM canal WHERE id = %s",
                    [self.canal_id]
                )
                result = cursor.fetchone()

                if not result:
                    registrar_log('comum.integracoes', f'Canal {self.canal_id} não encontrado', nivel='WARNING')
                    return None, None

                apn_cert_pem = result[0]
                apn_key_pem = result[1]

                # Opção 1: Certificados do banco (produção)
                if apn_cert_pem and apn_key_pem:
                    import tempfile
                    # Criar arquivos temporários com os certificados
                    cert_file = tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False)
                    key_file = tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False)
                    
                    cert_file.write(apn_cert_pem)
                    key_file.write(apn_key_pem)
                    
                    cert_file.close()
                    key_file.close()
                    
                    registrar_log('comum.integracoes', f'✅ Certificados APN carregados do banco para canal {self.canal_id}')
                    return cert_file.name, key_file.name

                registrar_log('comum.integracoes', f'❌ Nenhum certificado APN disponível para canal {self.canal_id}', nivel='WARNING')
                return None, None
                
        except Exception as e:
            registrar_log('comum.integracoes', f'Erro ao buscar certificados APN: {str(e)}', nivel='ERROR')
            return None, None

    def _initialize_apn(self):
        """Inicializa o APN com os certificados do canal"""
        try:
            cert_path, key_path = self._get_apn_credentials()
            if not cert_path or not key_path:
                registrar_log('comum.integracoes', f'Não foi possível inicializar APN para canal {self.canal_id}', nivel='WARNING')
                return False

            self.cert_path = cert_path
            self.key_path = key_path
            self.initialized = True

            registrar_log('comum.integracoes', f'✅ APN inicializado para canal {self.canal_id}')
            return True
        except Exception as e:
            registrar_log('comum.integracoes', f'❌ Erro ao inicializar APN: {str(e)}', nivel='ERROR')
            return False

    def get_token_by_cpf(self, cpf):
        """Busca o token APN do usuário pelo CPF"""
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT firebase_token, id
                    FROM cliente
                    WHERE cpf = %s AND canal_id = %s
                    """,
                    [cpf, self.canal_id]
                )
                result = cursor.fetchone()

                if not result or not result[0]:
                    registrar_log('comum.integracoes', f'Token não encontrado para CPF {cpf}', nivel='WARNING')
                    return None, None

                token = result[0]
                cliente_id = result[1]

                # Verificar se é token APN (< 142 caracteres)
                if len(token) >= 142:
                    registrar_log('comum.integracoes', f'Token encontrado é Firebase, não APN para CPF {cpf}', nivel='WARNING')
                    return None, None

                return token, cliente_id
        except Exception as e:
            registrar_log('comum.integracoes', f'Erro ao buscar token APN: {str(e)}', nivel='ERROR')
            return None, None

    def get_token_by_client_id(self, cliente_id):
        """Busca o token APN do usuário pelo ID do cliente"""
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT firebase_token
                    FROM cliente
                    WHERE id = %s AND canal_id = %s
                    """,
                    [cliente_id, self.canal_id]
                )
                result = cursor.fetchone()

                if not result or not result[0]:
                    registrar_log('comum.integracoes', f'Token não encontrado para cliente {cliente_id}', nivel='WARNING')
                    return None

                token = result[0]

                # Verificar se é token APN (< 142 caracteres)
                if len(token) >= 142:
                    registrar_log('comum.integracoes', f'Token encontrado é Firebase, não APN para cliente {cliente_id}', nivel='WARNING')
                    return None

                return token
        except Exception as e:
            registrar_log('comum.integracoes', f'Erro ao buscar token: {str(e)}', nivel='ERROR')
            return None

    def send_push(self, cpf=None, cliente_id=None, id_template=None, **parametros):
        """
        Método unificado para envio de push notifications via APN

        Args:
            cpf (str, optional): CPF do cliente
            cliente_id (int, optional): ID do cliente
            id_template (str): ID do template de push (ex: 'transacao_aprovada', 'autorizacao_saldo')
            **parametros: Parâmetros para substituir no template

        Returns:
            dict: {'sucesso': bool, 'mensagem': str}
        """
        if not self.initialized:
            return {'sucesso': False, 'mensagem': 'APN não inicializado'}

        try:
            # Buscar token
            if cpf:
                token, cliente_id_found = self.get_token_by_cpf(cpf)
                if not cliente_id:
                    cliente_id = cliente_id_found
            elif cliente_id:
                token = self.get_token_by_client_id(cliente_id)
            else:
                return {'sucesso': False, 'mensagem': 'CPF ou cliente_id obrigatório'}

            if not token:
                return {'sucesso': False, 'mensagem': 'Token não encontrado'}

            # Buscar template
            if not id_template:
                return {'sucesso': False, 'mensagem': 'id_template obrigatório'}

            template_push = MessagesTemplateService.preparar_push(
                canal_id=self.canal_id,
                id_template=id_template,
                **parametros
            )

            if not template_push:
                # Fallback básico
                canal_nome = Canal.get_canal_nome(self.canal_id)
                title = f"{canal_nome} - Notificação"
                body = parametros.get('mensagem', 'Nova notificação')
                tipo_push = parametros.get('tipo', 'notificacao')
                custom_data = parametros
                registrar_log('comum.integracoes', f'Template {id_template} não encontrado, usando fallback', nivel='WARNING')
            else:
                title = template_push['title']
                body = template_push['body']
                tipo_push = template_push.get('tipo_push', 'notificacao')
                template_data = template_push.get('data', {})
                # Merge template data com parametros extras
                custom_data = {**template_data, **parametros}
                registrar_log('comum.integracoes', f'Usando template APN: {id_template} (tipo_push: {tipo_push})')

            # Montar payload APN
            payload = {
                "aps": {
                    "alert": {
                        "title": title,
                        "body": body
                    },
                    "badge": 1,
                    "sound": "default"
                }
            }

            # Adicionar categoria iOS para ações interativas (se for autorização)
            if tipo_push == 'autorizacao_saldo':
                payload["aps"]["category"] = tipo_push

            # Adicionar custom_data ao payload (campos fora de aps)
            for key, value in custom_data.items():
                if key not in payload:
                    payload[key] = str(value)

            # Garantir tipo no payload
            if 'tipo' not in payload:
                payload['tipo'] = tipo_push

            registrar_log('comum.integracoes', f'🔔 [APN PUSH] Enviando: cliente={cliente_id}, tipo={tipo_push}, template={id_template}')

            # Enviar via APN
            success = self._send_apn_notification(token, payload)

            if success:
                registrar_log('comum.integracoes', f'✅ Push APN enviado com sucesso')
                return {'sucesso': True, 'mensagem': 'Push enviado com sucesso'}
            else:
                registrar_log('comum.integracoes', f'❌ Falha ao enviar push APN')
                return {'sucesso': False, 'mensagem': 'Falha no envio APN'}

        except Exception as e:
            registrar_log('comum.integracoes', f'❌ Erro ao enviar push APN: {str(e)}', nivel='ERROR')
            return {'sucesso': False, 'mensagem': str(e)}

    def _send_apn_notification(self, device_token, payload):
        """Envia a notificação APN usando HTTP/2 API moderna"""
        try:
            import httpx

            registrar_log('comum.integracoes', f'=== INICIANDO ENVIO APN ===')
            registrar_log('comum.integracoes', f'Device token: {device_token[:20]}...')

            # Validar certificados
            if not self._validate_certificates():
                registrar_log('comum.integracoes', '❌ Certificados APN inválidos')
                return False

            # Buscar Bundle ID
            canal = Canal.get_canal(self.canal_id)
            bundle_id = canal.bundle_id if canal and canal.bundle_id else 'com.wallclub.app'

            # Payload JSON
            payload_json = json.dumps(payload, separators=(',', ':'))

            registrar_log('comum.integracoes', f'Bundle ID: {bundle_id} (canal {self.canal_id})')
            registrar_log('comum.integracoes', f'Payload: {payload_json}')

            # Tentar produção primeiro, depois sandbox
            endpoints = [
                ('https://api.push.apple.com:443', 'PRODUÇÃO'),
                ('https://api.sandbox.push.apple.com:443', 'SANDBOX')
            ]

            for apn_url, env_name in endpoints:
                try:
                    notification_url = f"{apn_url}/3/device/{device_token}"

                    headers = {
                        'apns-topic': bundle_id,
                        'apns-priority': '10',
                        'apns-expiration': '0',
                        'Content-Type': 'application/json'
                    }

                    registrar_log('comum.integracoes', f'Tentando {env_name}: {notification_url}')

                    with httpx.Client(
                        http2=True,
                        cert=(self.cert_path, self.key_path),
                        timeout=30.0,
                        verify=True
                    ) as client:
                        response = client.post(
                            notification_url,
                            headers=headers,
                            content=payload_json
                        )

                        registrar_log('comum.integracoes', f'Resposta {env_name}: status={response.status_code}')

                    if response.status_code == 200:
                        registrar_log('comum.integracoes', f'✅ Push APN enviado via {env_name}')
                        return True
                    else:
                        # Se BadDeviceToken em produção, tenta sandbox
                        if 'BadDeviceToken' in response.text and env_name == 'PRODUÇÃO':
                            registrar_log('comum.integracoes', f'⚠️ BadDeviceToken em {env_name}, tentando sandbox...')
                            continue
                        else:
                            registrar_log('comum.integracoes', f'❌ Erro APN {env_name}: {response.status_code} - {response.text}', nivel='ERROR')
                            return False

                except Exception as e:
                    registrar_log('comum.integracoes', f'❌ ERRO ao tentar {env_name}: {str(e)}')
                    if env_name == 'PRODUÇÃO':
                        continue
                    else:
                        return False

            registrar_log('comum.integracoes', '❌ Falha em PRODUÇÃO e SANDBOX', nivel='ERROR')
            return False

        except Exception as e:
            registrar_log('comum.integracoes', f'❌ Erro ao enviar APN: {str(e)}', nivel='ERROR')
            return False

    def _validate_certificates(self):
        """Valida se os certificados estão no formato correto"""
        try:
            if not os.path.exists(self.cert_path) or not os.path.exists(self.key_path):
                registrar_log('comum.integracoes', f'Arquivos de certificado não encontrados')
                return False

            # Verificar conteúdo do certificado
            with open(self.cert_path, 'r') as f:
                cert_content = f.read()
                if '-----BEGIN CERTIFICATE-----' not in cert_content:
                    registrar_log('comum.integracoes', f'Formato de certificado inválido: {self.cert_path}')
                    return False

            # Verificar conteúdo da chave
            with open(self.key_path, 'r') as f:
                key_content = f.read()
                if not ('-----BEGIN PRIVATE KEY-----' in key_content or
                       '-----BEGIN RSA PRIVATE KEY-----' in key_content):
                    registrar_log('comum.integracoes', f'Formato de chave privada inválido: {self.key_path}')
                    return False

            return True

        except Exception as e:
            registrar_log('comum.integracoes', f'Erro ao validar certificados: {str(e)}', nivel='ERROR')
            return False
