"""
Serviço Firebase para envio de push notifications
Sistema unificado usando templates
"""
import json
import os
from firebase_admin import messaging, credentials, initialize_app
from django.conf import settings
from django.db import connection
from wallclub_core.utilitarios.log_control import registrar_log
from wallclub_core.estr_organizacional.canal import Canal
from wallclub_core.integracoes.messages_template_service import MessagesTemplateService


class FirebaseService:
    """
    Serviço unificado para envio de push notifications via Firebase
    Usa sistema de templates para todas as notificações
    """
    _instances = {}  # Singleton por canal_id

    @classmethod
    def get_instance(cls, canal_id):
        """Retorna instância singleton do FirebaseService para o canal específico"""
        if canal_id not in cls._instances:
            cls._instances[canal_id] = FirebaseService(canal_id)
        return cls._instances[canal_id]

    def __init__(self, canal_id):
        """Inicializa o serviço Firebase para um canal específico"""
        self.canal_id = canal_id
        self.app = None
        self.initialized = False
        self._initialize_firebase()

    def _get_firebase_credentials(self):
        """Busca as credenciais Firebase para o canal (do banco ou arquivo local)"""
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT firebase_credentials_json, json_firebase FROM canal WHERE id = %s",
                    [self.canal_id]
                )
                result = cursor.fetchone()
                
                if not result:
                    registrar_log('comum.integracoes', f'Canal {self.canal_id} não encontrado')
                    return None
                
                firebase_credentials_json = result[0]
                json_firebase_filename = result[1]
                
                # Opção 1: Credenciais JSON do banco (produção)
                if firebase_credentials_json:
                    try:
                        credentials_dict = json.loads(firebase_credentials_json)
                        registrar_log('comum.integracoes', f'✅ Credenciais Firebase carregadas do banco para canal {self.canal_id}')
                        return credentials_dict
                    except json.JSONDecodeError as e:
                        registrar_log('comum.integracoes', f'Erro ao decodificar JSON do banco: {str(e)}', nivel='ERROR')
                
                # Opção 2: Arquivo local (desenvolvimento)
                if json_firebase_filename:
                    import wallclub_core
                    package_dir = os.path.dirname(wallclub_core.__file__)
                    config_path = os.path.join(package_dir, 'integracoes', 'firebase_configs', json_firebase_filename)
                    
                    if os.path.exists(config_path):
                        registrar_log('comum.integracoes', f'✅ Arquivo Firebase encontrado (dev): {config_path}')
                        return config_path
                
                registrar_log('comum.integracoes', f'❌ Nenhuma credencial Firebase disponível para canal {self.canal_id}', nivel='ERROR')
                return None
                
        except Exception as e:
            registrar_log('comum.integracoes', f'Erro ao buscar credenciais Firebase: {str(e)}', nivel='ERROR')
            return None

    def _initialize_firebase(self):
        """Inicializa o Firebase Admin SDK com as credenciais do canal"""
        try:
            firebase_config = self._get_firebase_credentials()
            if not firebase_config:
                registrar_log('comum.integracoes', f'Não foi possível inicializar Firebase para canal {self.canal_id}')
                return False
            
            # Aceita dict (JSON do banco) ou string (caminho do arquivo)
            if isinstance(firebase_config, dict):
                cred = credentials.Certificate(firebase_config)
            else:
                cred = credentials.Certificate(firebase_config)
            
            self.app = initialize_app(cred, name=f'canal_{self.canal_id}')
            self.initialized = True
            
            registrar_log('comum.integracoes', f'✅ Firebase inicializado para canal {self.canal_id}')
            return True
        except ValueError as e:
            if 'already exists' in str(e):
                import firebase_admin
                self.app = firebase_admin.get_app(f'canal_{self.canal_id}')
                self.initialized = True
                registrar_log('comum.integracoes', f'✅ Firebase já inicializado para canal {self.canal_id}')
                return True
            else:
                registrar_log('comum.integracoes', f'❌ Erro ao inicializar Firebase: {str(e)}', nivel='ERROR')
                return False
        except Exception as e:
            registrar_log('comum.integracoes', f'❌ Erro ao inicializar Firebase: {str(e)}', nivel='ERROR')
            return False

    def get_token_by_cpf(self, cpf):
        """Busca o token Firebase do usuário pelo CPF"""
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
                    registrar_log('comum.integracoes', f'Token Firebase não encontrado para CPF {cpf}')
                    return None, None
                
                token = result[0]
                cliente_id = result[1]
                
                # Verificar se é token Firebase (>= 142 caracteres)
                if len(token) < 142:
                    registrar_log('comum.integracoes', f'Token encontrado é APN, não Firebase para CPF {cpf}')
                    return None, None
                
                return token, cliente_id
        except Exception as e:
            registrar_log('comum.integracoes', f'Erro ao buscar token: {str(e)}', nivel='ERROR')
            return None, None

    def get_token_by_client_id(self, cliente_id):
        """Busca o token Firebase do usuário pelo ID do cliente"""
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
                    registrar_log('comum.integracoes', f'Token Firebase não encontrado para cliente {cliente_id}')
                    return None
                
                token = result[0]
                
                # Verificar se é token Firebase (>= 142 caracteres)
                if len(token) < 142:
                    registrar_log('comum.integracoes', f'Token encontrado é APN, não Firebase para cliente {cliente_id}')
                    return None
                
                return token
        except Exception as e:
            registrar_log('comum.integracoes', f'Erro ao buscar token: {str(e)}', nivel='ERROR')
            return None

    def send_push(self, cpf=None, cliente_id=None, id_template=None, **parametros):
        """
        Método unificado para envio de push notifications via Firebase
        
        Args:
            cpf (str, optional): CPF do cliente
            cliente_id (int, optional): ID do cliente
            id_template (str): ID do template de push (ex: 'transacao_aprovada', 'autorizacao_saldo')
            **parametros: Parâmetros para substituir no template
            
        Returns:
            dict: {'sucesso': bool, 'mensagem': str}
        """
        if not self.initialized:
            return {'sucesso': False, 'mensagem': 'Firebase não inicializado'}
        
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
                registrar_log('comum.integracoes', f'Usando template: {id_template} (tipo_push: {tipo_push})')
            
            # Garantir que 'tipo' está no custom_data
            if 'tipo' not in custom_data:
                custom_data['tipo'] = tipo_push
            
            # Adicionar title e body no data para app processar
            custom_data['title'] = title
            custom_data['body'] = body
            
            # Converter todos os valores para string (Firebase exige)
            data_dict = {k: str(v) for k, v in custom_data.items() if v is not None}
            
            # Enviar apenas data (sem notification) para o app processar em foreground/background
            message = messaging.Message(
                data=data_dict,
                token=token,
            )
            
            # Log completo do payload antes de enviar
            payload_completo = {
                'data': data_dict,
                'token': f'{token[:20]}...{token[-20:]}',  # Token parcial por segurança
                'cliente_id': cliente_id,
                'template': id_template,
                'tipo_push': tipo_push
            }
            registrar_log('comum.integracoes', f'🔔 [FIREBASE PUSH] Payload completo: {json.dumps(payload_completo, indent=2, ensure_ascii=False)}')
            
            # Enviar via Firebase
            response = messaging.send(message, app=self.app)
            
            registrar_log('comum.integracoes', f'✅ Push Firebase enviado com sucesso. Response: {response}')
            return {'sucesso': True, 'mensagem': 'Push enviado com sucesso'}
            
        except Exception as e:
            registrar_log('comum.integracoes', f'❌ Erro ao enviar push Firebase: {str(e)}', nivel='ERROR')
            return {'sucesso': False, 'mensagem': str(e)}
