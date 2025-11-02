"""
Service para buscar templates de mensagens (PUSH, SMS, WHATSAPP)
"""
import json
from typing import Dict, Any, Optional
from django.core.cache import cache
from wallclub_core.utilitarios.log_control import registrar_log
from .models import TemplateEnvioMsg


class MessagesTemplateService:
    """Service para gerenciar templates de SMS/WhatsApp/PUSH"""
    
    CACHE_TTL = 3600  # 1 hora
    
    @staticmethod
    def buscar_template(canal_id: int, tipo: str, id_template: str) -> Optional[TemplateEnvioMsg]:
        """
        Busca template ativo por canal, tipo e id_template
        
        Args:
            canal_id (int): ID do canal
            tipo (str): 'SMS', 'WHATSAPP' ou 'PUSH'
            id_template (str): ID do template
            
        Returns:
            TemplateEnvioMsg|None: Template encontrado ou None
        """
        cache_key = f"template_{canal_id}_{tipo}_{id_template}"
        template_cache = cache.get(cache_key)
        
        if template_cache is not None:
            return template_cache
        
        try:
            template = TemplateEnvioMsg.objects.get(
                canal_id=canal_id,
                tipo=tipo,
                id_template=id_template,
                ativo=True
            )
            
            cache.set(cache_key, template, MessagesTemplateService.CACHE_TTL)
            return template
            
        except TemplateEnvioMsg.DoesNotExist:
            registrar_log('comum.integracoes', f"Template não encontrado: {tipo}/{id_template} para canal {canal_id}", nivel='WARNING')
            cache.set(cache_key, None, 60)  # Cache negativo por 1 minuto
            return None
    
    @staticmethod
    def preparar_sms(canal_id: int, id_template: str, **params) -> Optional[Dict[str, Any]]:
        """
        Prepara mensagem SMS baseada no template
        
        Args:
            canal_id (int): ID do canal
            id_template (str): ID do template
            **params: Parâmetros para substituir na mensagem
            
        Returns:
            dict|None: {'mensagem': str, 'assunto': str} ou None se template não encontrado
        """
        template = MessagesTemplateService.buscar_template(canal_id, 'SMS', id_template)
        
        if not template:
            return None
        
        # Formatar mensagem com parâmetros (template já inclui nome do canal)
        mensagem = template.formatar_mensagem(**params)
        
        # Assunto dinâmico baseado no id_template
        assuntos_padrao = {
            'senha_acesso': 'envio de senha de acesso',
            'cadastro_otp': 'código de verificação',
            'login_otp': 'código de verificação',
            'baixar_app': 'Convite WallClub',
            'reset_senha': 'recuperação de senha'
        }
        
        assunto_tipo = assuntos_padrao.get(id_template, 'notificação')
        
        # Para baixar_app, usar assunto simples sem prefixo
        if id_template == 'baixar_app':
            assunto = assunto_tipo
        else:
            nome_canal = params.get('nome_canal', 'WallClub')
            assunto = f"{nome_canal} - {assunto_tipo}"
        
        return {
            'mensagem': mensagem,
            'assunto': assunto
        }
    
    @staticmethod
    def preparar_whatsapp(canal_id: int, id_template: str, **params) -> Optional[Dict[str, Any]]:
        """
        Prepara dados para envio WhatsApp baseado no template
        
        Args:
            canal_id (int): ID do canal
            id_template (str): ID do template
            **params: Parâmetros para o template (senha, cpf, etc)
            
        Returns:
            dict|None: {
                'nome_template': str,
                'idioma': str,
                'parametros_corpo': list,
                'parametros_botao': list
            } ou None se template não encontrado
        """
        template = MessagesTemplateService.buscar_template(canal_id, 'WHATSAPP', id_template)
        
        if not template:
            return None
        
        # Extrair parâmetros esperados
        parametros_esperados = template.parametros_esperados or []
        
        # Separar parâmetros: primeiro é corpo, resto são botões
        parametros_corpo = []
        parametros_botao = []
        
        for i, param_nome in enumerate(parametros_esperados):
            valor = params.get(param_nome, '')
            if i == 0:
                parametros_corpo.append(valor)
            else:
                # Ignorar valores vazios para evitar 400 da API (button text não pode ser vazio)
                if valor is not None and str(valor).strip() != '':
                    parametros_botao.append(valor)
        
        return {
            'nome_template': template.mensagem,  # Nome do template NO FACEBOOK (ex: 'envio_senha2')
            'idioma': template.idioma,
            'parametros_corpo': parametros_corpo,
            'parametros_botao': parametros_botao if parametros_botao else None
        }
    
    @staticmethod
    def preparar_push(canal_id: int, id_template: str, **params) -> Optional[Dict[str, Any]]:
        """
        Prepara notificação PUSH baseada no template
        
        Args:
            canal_id (int): ID do canal
            id_template (str): ID do template (ex: 'transacao_aprovada')
            **params: Parâmetros para o template
            
        Returns:
            dict|None: {
                'title': str,
                'body': str,
                'tipo_push': str,  # 'notificacao', 'autorizacao_saldo', 'oferta'
                'data': dict  # dados customizados
            } ou None se template não encontrado
        """
        template = MessagesTemplateService.buscar_template(canal_id, 'PUSH', id_template)
        
        if not template:
            registrar_log('comum.integracoes', f"Template PUSH não encontrado: {id_template} para canal {canal_id}", nivel='WARNING')
            return None
        
        try:
            # Template deve estar no formato JSON: {"title": "...", "body": "..."}
            template_json = json.loads(template.mensagem)
            
            # Formatar title e body com os parâmetros
            title = template_json.get('title', '').format(**params)
            body = template_json.get('body', '').format(**params)
            
            # Extrair tipo_push do template (default: 'notificacao')
            tipo_push = template.tipo_push or 'notificacao'
            
            # Extrair dados customizados dos parâmetros (tudo que não é formatação de texto)
            custom_data = {}
            parametros_esperados = template.parametros_esperados or []
            
            for param_nome in parametros_esperados:
                if param_nome in params:
                    custom_data[param_nome] = str(params[param_nome])
            
            registrar_log('comum.integracoes', f"Template PUSH preparado: {id_template} (tipo: {tipo_push}) - title: {title[:50]}...")
            
            return {
                'title': title,
                'body': body,
                'tipo_push': tipo_push,
                'data': custom_data
            }
            
        except json.JSONDecodeError as e:
            registrar_log('comum.integracoes', f"Erro ao decodificar JSON do template PUSH {id_template}: {str(e)}", nivel='ERROR')
            return None
        except KeyError as e:
            registrar_log('comum.integracoes', f"Parâmetro faltando no template PUSH {id_template}: {str(e)}", nivel='ERROR')
            return None
        except Exception as e:
            registrar_log('comum.integracoes', f"Erro ao preparar template PUSH {id_template}: {str(e)}", nivel='ERROR')
            return None


# Manter compatibilidade com código legado
TemplateService = MessagesTemplateService
