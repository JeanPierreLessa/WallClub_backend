"""
Serviço de Notificações
Orquestra envio de push notifications via Firebase e APN usando sistema de templates
"""
from django.utils import timezone
from django.db import connection
from wallclub_core.utilitarios.log_control import registrar_log
from wallclub_core.integracoes.firebase_service import FirebaseService
from wallclub_core.integracoes.apn_service import APNService


class NotificationService:
    """
    Serviço unificado para gerenciar envio de notificações push
    Detecta automaticamente se usa Firebase ou APN baseado no token
    """
    _instances = {}  # Singleton por canal_id

    @classmethod
    def get_instance(cls, canal_id):
        """Retorna instância singleton do NotificationService para o canal específico"""
        if canal_id not in cls._instances:
            cls._instances[canal_id] = NotificationService(canal_id)
        return cls._instances[canal_id]

    def __init__(self, canal_id):
        """Inicializa o serviço de notificações para um canal específico"""
        self.canal_id = canal_id
        self.firebase_service = FirebaseService.get_instance(canal_id)
        self.apn_service = APNService.get_instance(canal_id)

    def send_push(self, cpf=None, cliente_id=None, id_template=None, **parametros):
        """
        Método unificado para envio de push notifications
        Detecta automaticamente Firebase ou APN baseado no token do cliente
        
        Args:
            cpf (str, optional): CPF do cliente
            cliente_id (int, optional): ID do cliente
            id_template (str): ID do template (ex: 'transacao_aprovada', 'autorizacao_saldo', 'oferta_disponivel')
            **parametros: Parâmetros para o template
            
        Returns:
            dict: {'sucesso': bool, 'mensagem': str, 'provider': str}
        """
        try:
            # Validações
            if not cpf and not cliente_id:
                return {'sucesso': False, 'mensagem': 'CPF ou cliente_id obrigatório'}
            
            if not id_template:
                return {'sucesso': False, 'mensagem': 'id_template obrigatório'}
            
            # Buscar token e determinar tipo
            token, cliente_id_found, token_type = self._get_token_and_type(cpf, cliente_id)
            
            if not token:
                return {'sucesso': False, 'mensagem': 'Token não encontrado'}
            
            if not cliente_id:
                cliente_id = cliente_id_found
            
            # Buscar CPF se não foi fornecido (para registro no banco)
            if not cpf:
                cpf = self._get_cpf_by_cliente_id(cliente_id)
            
            registrar_log('comum.integracoes', f'🔔 [NOTIFICATION SERVICE] Enviando push: cliente={cliente_id}, template={id_template}, provider={token_type}')
            
            # IMPORTANTE: Registrar no banco ANTES de enviar o push
            # Garante persistência mesmo se o envio falhar
            notificacao_id = self._registrar_notificacao(
                cpf=cpf,
                cliente_id=cliente_id,
                id_template=id_template,
                parametros=parametros
            )
            
            if notificacao_id:
                registrar_log('comum.integracoes', f'Notificação registrada no banco (ID: {notificacao_id})')
            
            # Enviar via Firebase ou APN
            if token_type == 'firebase':
                resultado = self.firebase_service.send_push(
                    cliente_id=cliente_id,
                    id_template=id_template,
                    **parametros
                )
            else:  # apn
                resultado = self.apn_service.send_push(
                    cliente_id=cliente_id,
                    id_template=id_template,
                    **parametros
                )
            
            resultado['provider'] = token_type
            resultado['notificacao_id'] = notificacao_id
            return resultado
            
        except Exception as e:
            registrar_log('comum.integracoes', f'Erro ao enviar notificação: {str(e)}', nivel='ERROR')
            return {'sucesso': False, 'mensagem': str(e)}

    def _get_token_and_type(self, cpf, cliente_id):
        """
        Busca token do cliente e determina se é Firebase ou APN
        
        Returns:
            tuple: (token, cliente_id, token_type) ou (None, None, None)
        """
        try:
            with connection.cursor() as cursor:
                if cpf:
                    cursor.execute(
                        """
                        SELECT firebase_token, id 
                        FROM cliente 
                        WHERE cpf = %s AND canal_id = %s
                        """,
                        [cpf, self.canal_id]
                    )
                else:
                    cursor.execute(
                        """
                        SELECT firebase_token, id 
                        FROM cliente 
                        WHERE id = %s AND canal_id = %s
                        """,
                        [cliente_id, self.canal_id]
                    )
                
                result = cursor.fetchone()
                
                if not result or not result[0]:
                    registrar_log('comum.integracoes', f'Token não encontrado')
                    return None, None, None
                
                token = result[0]
                cliente_id_found = result[1]
                
                # Determinar tipo: Firebase >= 142 caracteres, APN < 142
                token_type = 'firebase' if len(token) >= 142 else 'apn'
                
                registrar_log('comum.integracoes', f'Token encontrado: tipo={token_type}, cliente={cliente_id_found}')
                return token, cliente_id_found, token_type
                
        except Exception as e:
            registrar_log('comum.integracoes', f'Erro ao buscar token: {str(e)}', nivel='ERROR')
            return None, None, None

    def _get_cpf_by_cliente_id(self, cliente_id):
        """Busca CPF do cliente pelo ID"""
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT cpf FROM cliente WHERE id = %s AND canal_id = %s",
                    [cliente_id, self.canal_id]
                )
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            registrar_log('comum.integracoes', f'Erro ao buscar CPF: {str(e)}', nivel='ERROR')
            return None

    def _registrar_notificacao(self, cpf, cliente_id, id_template, parametros):
        """
        Registra a notificação na tabela 'notificacoes' ANTES de enviar
        Isso garante que a notificação fique salva mesmo se o push falhar
        
        Args:
            cpf (str): CPF do cliente
            cliente_id (int): ID do cliente
            id_template (str): ID do template usado
            parametros (dict): Parâmetros passados
            
        Returns:
            int: ID da notificação criada ou None
        """
        try:
            # Buscar template para extrair title e body
            from wallclub_core.integracoes.messages_template_service import MessagesTemplateService
            
            template_push = MessagesTemplateService.preparar_push(
                canal_id=self.canal_id,
                id_template=id_template,
                **parametros
            )
            
            if template_push:
                titulo = template_push['title']
                mensagem = template_push['body']
                tipo_push = template_push.get('tipo_push', 'notificacao')
            else:
                # Fallback se template não encontrado
                from wallclub_core.estr_organizacional.canal import Canal
                canal_nome = Canal.get_canal_nome(self.canal_id)
                titulo = f"{canal_nome} - Notificação"
                mensagem = parametros.get('mensagem', 'Nova notificação')
                tipo_push = parametros.get('tipo', 'notificacao')
            
            # Preparar dados adicionais (todos os parâmetros exceto campos já salvos)
            dados_adicionais = {k: v for k, v in parametros.items() if k not in ['titulo', 'mensagem']}
            
            # Converter para JSON válido
            import json
            dados_adicionais_json = None
            if dados_adicionais:
                try:
                    dados_adicionais_json = json.dumps(dados_adicionais, ensure_ascii=False)
                except Exception as e:
                    registrar_log('comum.integracoes', f'Erro ao serializar dados_adicionais: {str(e)}', nivel='ERROR')
            
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO notificacoes 
                    (cpf, canal_id, titulo, mensagem, tipo, data_envio, lida, dados_adicionais)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        cpf,
                        self.canal_id,
                        titulo,
                        mensagem,
                        tipo_push,
                        timezone.now(),
                        False,
                        dados_adicionais_json
                    ]
                )
                
                # Buscar ID da notificação criada
                cursor.execute("SELECT LAST_INSERT_ID()")
                notificacao_id = cursor.fetchone()[0]
                
                registrar_log('comum.integracoes', f'Notificação registrada: ID={notificacao_id}, tipo={tipo_push}')
                return notificacao_id
                
        except Exception as e:
            registrar_log('comum.integracoes', f'Erro ao registrar notificação: {str(e)}', nivel='ERROR')
            return None
