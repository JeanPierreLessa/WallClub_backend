"""
Service para notificações de segurança aos clientes.
Envia alertas via Push, WhatsApp e Email para eventos críticos de segurança.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from django.core.cache import cache
from wallclub_core.utilitarios.log_control import registrar_log


# Definição dos tipos de alerta e seus canais
TIPOS_ALERTA = {
    'login_novo_dispositivo': {
        'titulo': 'Novo dispositivo detectado',
        'mensagem': 'Detectamos um login na sua conta de um novo dispositivo. Foi você?',
        'prioridade': 'alta',
        'canais': ['whatsapp']
    },
    'troca_senha': {
        'titulo': 'Senha alterada',
        'mensagem': 'Sua senha foi alterada com sucesso.',
        'prioridade': 'alta',
        'canais': ['push', 'whatsapp']
    },
    'alteracao_dados': {
        'titulo': 'Dados atualizados',
        'mensagem': 'Seus dados cadastrais foram alterados.',
        'prioridade': 'media',
        'canais': ['push']
    },
    'alteracao_celular': {
        'titulo': 'Celular atualizado',
        'mensagem': 'Seu número de celular foi atualizado.',
        'prioridade': 'alta',
        'canais': ['whatsapp']  # WhatsApp vai para número ANTIGO
    },
    'alteracao_email': {
        'titulo': 'Email alterado',
        'mensagem': 'Seu endereço de email foi atualizado.',
        'prioridade': 'alta',
        'canais': ['whatsapp']
    },
    'tentativa_falha': {
        'titulo': 'Tentativas de acesso',
        'mensagem': 'Detectamos {tentativas} tentativas de acesso à sua conta.',
        'prioridade': 'alta',
        'canais': ['push', 'whatsapp']
    },
    'bloqueio_conta': {
        'titulo': 'Conta bloqueada',
        'mensagem': 'Sua conta foi temporariamente bloqueada por segurança. Entre em contato.',
        'prioridade': 'critica',
        'canais': ['push', 'whatsapp']
    },
    'dispositivo_removido': {
        'titulo': 'Dispositivo removido',
        'mensagem': 'Um dispositivo foi removido da sua conta.',
        'prioridade': 'alta',
        'canais': ['push', 'whatsapp']
    }
}


class NotificacaoSegurancaService:
    """Service para gerenciar notificações de segurança"""

    @staticmethod
    def enviar_alerta_seguranca(
        tipo_alerta: str,
        cliente_id: int,
        canal_id: int,
        celular: str,
        nome: str = '',
        email: str = '',
        firebase_token: str = '',
        dados_adicionais: Optional[Dict[str, Any]] = None,
        celular_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Método unificado para enviar alertas de segurança.
        
        ATENÇÃO: Este método não busca dados do cliente. O caller deve fornecer todos os dados necessários.
        Isso permite que o CORE seja independente de apps específicos.

        Args:
            tipo_alerta: Tipo do alerta (chave de TIPOS_ALERTA)
            cliente_id: ID do cliente
            canal_id: ID do canal
            celular: Celular do cliente
            nome: Nome do cliente (opcional)
            email: Email do cliente (opcional)
            firebase_token: Token Firebase do cliente (opcional)
            dados_adicionais: Dados extras para personalização (ex: valor, tentativas)
            celular_override: Celular para usar no lugar do cadastrado (ex: celular antigo)

        Returns:
            dict: Resultado do envio com status por canal
        """
        try:
            # Verificar se tipo de alerta existe
            if tipo_alerta not in TIPOS_ALERTA:
                registrar_log('comum.integracoes',
                    f"Tipo de alerta inválido: {tipo_alerta}", nivel='ERROR')
                return {
                    'sucesso': False,
                    'mensagem': 'Tipo de alerta inválido'
                }

            # Obter configuração do alerta
            config_alerta = TIPOS_ALERTA[tipo_alerta]

            # Personalizar mensagem com dados adicionais
            mensagem = config_alerta['mensagem']
            if dados_adicionais:
                mensagem = mensagem.format(**dados_adicionais)

            # Enviar por cada canal configurado
            resultados = {}
            canais = config_alerta['canais']

            if 'push' in canais:
                resultados['push'] = NotificacaoSegurancaService._enviar_push(
                    cliente_id=cliente_id,
                    titulo=config_alerta['titulo'],
                    mensagem=mensagem,
                    tipo_alerta=tipo_alerta,
                    canal_id=canal_id
                )

            # WhatsApp: usar celular_override se fornecido (ex: alteração de celular)
            celular_destino = celular_override if celular_override else celular
            if 'whatsapp' in canais and celular_destino:
                registrar_log('comum.integracoes',
                    f"Tentando enviar WhatsApp: tipo={tipo_alerta}, celular={celular_destino[:6]}..., canal={canal_id}")
                resultados['whatsapp'] = NotificacaoSegurancaService._enviar_whatsapp(
                    celular=celular_destino,
                    canal_id=canal_id,
                    titulo=config_alerta['titulo'],
                    mensagem=mensagem,
                    tipo_alerta=tipo_alerta,
                    dados_adicionais=dados_adicionais
                )
            elif 'whatsapp' in canais and not celular_destino:
                registrar_log('comum.integracoes',
                    f"WhatsApp não enviado: celular não disponível para cliente {cliente_id}", nivel='WARNING')

            # Registrar na auditoria
            NotificacaoSegurancaService._registrar_auditoria(
                cliente_id=cliente_id,
                tipo_alerta=tipo_alerta,
                canais=canais,
                resultados=resultados,
                prioridade=config_alerta['prioridade']
            )

            # Verificar se pelo menos um canal teve sucesso
            algum_sucesso = any(r.get('sucesso', False) for r in resultados.values())

            return {
                'sucesso': algum_sucesso,
                'mensagem': 'Notificação enviada' if algum_sucesso else 'Falha no envio',
                'resultados': resultados
            }

        except Exception as e:
            registrar_log('comum.integracoes',
                f"Erro ao enviar alerta: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Erro interno ao enviar notificação'
            }

    @staticmethod
    def notificar_login_novo_dispositivo(
        cliente_id: int,
        canal_id: int,
        celular: str,
        ip_address: str,
        nome: str = '',
        device_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Notifica login de novo dispositivo"""
        dados = {
            'ip': ip_address,
            'dispositivo': device_name or 'Dispositivo desconhecido'
        }

        # Evitar spam: máximo 1 notificação por hora
        cache_key = f"notif_novo_device_{cliente_id}"
        if cache.get(cache_key):
            return {'sucesso': True, 'mensagem': 'Notificação suprimida (rate limit)'}

        resultado = NotificacaoSegurancaService.enviar_alerta_seguranca(
            tipo_alerta='login_novo_dispositivo',
            cliente_id=cliente_id,
            canal_id=canal_id,
            celular=celular,
            nome=nome,
            dados_adicionais=dados
        )

        # Cache por 1 hora
        if resultado['sucesso']:
            cache.set(cache_key, True, 3600)

        return resultado

    @staticmethod
    def notificar_troca_senha(
        cliente_id: int,
        canal_id: int,
        celular: str,
        nome: str = ''
    ) -> Dict[str, Any]:
        """Notifica troca de senha"""
        return NotificacaoSegurancaService.enviar_alerta_seguranca(
            tipo_alerta='troca_senha',
            cliente_id=cliente_id,
            canal_id=canal_id,
            celular=celular,
            nome=nome
        )

    @staticmethod
    def notificar_alteracao_dados(
        cliente_id: int,
        canal_id: int,
        celular: str,
        campo_alterado: str,
        nome: str = '',
        celular_antigo: Optional[str] = None
    ) -> Dict[str, Any]:
        """Notifica alteração de dados cadastrais"""
        if campo_alterado == 'celular':
            tipo = 'alteracao_celular'
        elif campo_alterado == 'email':
            tipo = 'alteracao_email'
        else:
            tipo = 'alteracao_dados'

        return NotificacaoSegurancaService.enviar_alerta_seguranca(
            tipo_alerta=tipo,
            cliente_id=cliente_id,
            canal_id=canal_id,
            celular=celular,
            nome=nome,
            celular_override=celular_antigo  # WhatsApp vai para número antigo
        )

    @staticmethod
    def notificar_tentativas_falhas(
        cliente_id: int,
        canal_id: int,
        celular: str,
        num_tentativas: int,
        nome: str = ''
    ) -> Dict[str, Any]:
        """Notifica tentativas de login falhadas"""
        if num_tentativas < 3:
            return {'sucesso': True, 'mensagem': 'Número de tentativas abaixo do threshold'}

        return NotificacaoSegurancaService.enviar_alerta_seguranca(
            tipo_alerta='tentativa_falha',
            cliente_id=cliente_id,
            canal_id=canal_id,
            celular=celular,
            nome=nome,
            dados_adicionais={'tentativas': num_tentativas}
        )

    @staticmethod
    def notificar_bloqueio_conta(
        cliente_id: int,
        canal_id: int,
        celular: str,
        nome: str = ''
    ) -> Dict[str, Any]:
        """Notifica bloqueio de conta"""
        return NotificacaoSegurancaService.enviar_alerta_seguranca(
            tipo_alerta='bloqueio_conta',
            cliente_id=cliente_id,
            canal_id=canal_id,
            celular=celular,
            nome=nome
        )

    @staticmethod
    def notificar_dispositivo_removido(
        cliente_id: int,
        canal_id: int,
        celular: str,
        nome: str = '',
        device_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Notifica remoção de dispositivo"""
        dados = {'dispositivo': device_name or 'Dispositivo'}

        return NotificacaoSegurancaService.enviar_alerta_seguranca(
            tipo_alerta='dispositivo_removido',
            cliente_id=cliente_id,
            canal_id=canal_id,
            celular=celular,
            nome=nome,
            dados_adicionais=dados
        )

    @staticmethod
    def _enviar_push(
        cliente_id: int,
        titulo: str,
        mensagem: str,
        tipo_alerta: str,
        canal_id: int
    ) -> Dict[str, Any]:
        """Envia notificação push via NotificationService (detecta automaticamente Firebase/APN)"""
        try:
            from wallclub_core.integracoes.notification_service import NotificationService

            # Usar método unificado com template
            notification_service = NotificationService.get_instance(canal_id)
            resultado = notification_service.send_push(
                cliente_id=cliente_id,
                id_template=f'alerta_{tipo_alerta}',  # Ex: 'alerta_troca_senha', 'alerta_login_suspeito'
                categoria=tipo_alerta,
                timestamp=datetime.now().isoformat()
            )

            if resultado.get('sucesso'):
                registrar_log('comum.integracoes',
                    f"Push enviado: {tipo_alerta} - Cliente: {cliente_id}")

            return resultado

        except Exception as e:
            registrar_log('comum.integracoes',
                f"Erro ao enviar push: {str(e)}", nivel='ERROR')
            return {'sucesso': False, 'mensagem': str(e)}

    @staticmethod
    def _enviar_whatsapp(
        celular: str,
        canal_id: int,
        titulo: str,
        mensagem: str,
        tipo_alerta: str,
        dados_adicionais: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Envia notificação via WhatsApp"""
        try:
            registrar_log('comum.integracoes',
                f"[WhatsApp] Iniciando envio - tipo_alerta={tipo_alerta}, dados={dados_adicionais}")

            from wallclub_core.integracoes.whatsapp_service import WhatsAppService
            from wallclub_core.integracoes.messages_template_service import MessagesTemplateService

            # Buscar template WhatsApp específico para alertas de segurança
            template_id = f'alerta_seguranca_{tipo_alerta}'

            registrar_log('comum.integracoes',
                f"[WhatsApp] Buscando template: {template_id} para canal {canal_id}")

            # Passar dados_adicionais como kwargs para o template
            template_params = dados_adicionais if dados_adicionais else {}

            template = MessagesTemplateService.preparar_whatsapp(
                canal_id=canal_id,
                id_template=template_id,
                **template_params
            )

            registrar_log('comum.integracoes',
                f"[WhatsApp] Template retornado: {template}")

            if not template:
                registrar_log('comum.integracoes',
                    f"[WhatsApp] Template não encontrado: {template_id}, pulando envio", nivel='WARNING')
                return {'sucesso': False, 'mensagem': 'Template não encontrado'}

            registrar_log('comum.integracoes',
                f"[WhatsApp] Parâmetros do template: {template.get('parametros_corpo', [])}")

            # Enviar com template
            resultado = WhatsAppService.envia_whatsapp(
                numero_telefone=celular,
                canal_id=canal_id,
                nome_template=template['nome_template'],
                idioma_template=template['idioma'],
                parametros_corpo=template.get('parametros_corpo', []),
                parametros_botao=template.get('parametros_botao')
            )

            if resultado:
                registrar_log('comum.integracoes',
                    f"WhatsApp enviado: {tipo_alerta} - Celular: {celular[:6]}...")
                return {'sucesso': True, 'mensagem': 'WhatsApp enviado'}
            else:
                return {'sucesso': False, 'mensagem': 'Falha no envio WhatsApp'}

        except Exception as e:
            registrar_log('comum.integracoes',
                f"Erro ao enviar WhatsApp: {str(e)}", nivel='ERROR')
            return {'sucesso': False, 'mensagem': str(e)}


    @staticmethod
    def _registrar_auditoria(
        cliente_id: int,
        tipo_alerta: str,
        canais: List[str],
        resultados: Dict[str, Any],
        prioridade: str
    ) -> None:
        """Registra notificação na auditoria"""
        try:
            from django.db import connection
            from datetime import datetime
            import json

            # Preparar detalhes
            detalhes = {
                'canais_tentados': canais,
                'resultados': {
                    canal: {
                        'sucesso': resultado.get('sucesso', False),
                        'mensagem': resultado.get('mensagem', '')
                    }
                    for canal, resultado in resultados.items()
                },
                'timestamp': datetime.now().isoformat()
            }

            # Status geral
            status = 'enviado' if any(r.get('sucesso', False) for r in resultados.values()) else 'falha'

            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO wallclub.cliente_notificacoes_seguranca
                    (cliente_id, tipo, canais, status, prioridade, detalhes, enviado_em)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """, [
                    cliente_id,
                    tipo_alerta,
                    ','.join(canais),
                    status,
                    prioridade,
                    json.dumps(detalhes)
                ])

            registrar_log('comum.integracoes',
                f"Auditoria registrada: cliente={cliente_id}, tipo={tipo_alerta}, status={status}")

        except Exception as e:
            # Não falhar se auditoria falhar
            registrar_log('comum.integracoes',
                f"Erro ao registrar auditoria: {str(e)}", nivel='ERROR')
