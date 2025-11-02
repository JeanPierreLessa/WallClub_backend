"""
Serviço para integração com WhatsApp Business API.
Envio de mensagens e templates.
"""
import requests
import json
from django.conf import settings
from wallclub_core.utilitarios.log_control import registrar_log


class WhatsAppService:
    """Serviço para envio de mensagens via WhatsApp Business API"""
    
    @staticmethod
    def obter_configuracao_whatsapp(canal_id):
        """
        Obtém configuração do WhatsApp baseado no canal_id.
        Busca facebook_url e facebook_token da tabela canal.
        
        Args:
            canal_id (int): ID do canal
            
        Returns:
            dict: Configurações do WhatsApp (URL, token) ou None se não encontrado
        """
        try:
            from wallclub_core.estr_organizacional.services import HierarquiaOrganizacionalService
            
            canal = HierarquiaOrganizacionalService.get_canal(canal_id)
            if not canal:
                registrar_log('comum.integracoes', f"Canal {canal_id} não encontrado", nivel='WARNING')
                return None
            
            if not canal.facebook_url or not canal.facebook_token:
                registrar_log('comum.integracoes', f"Configurações WhatsApp incompletas para canal {canal_id}", nivel='WARNING')
                return None
            
            return {
                'url': canal.facebook_url.strip() if canal.facebook_url else None,
                'token': canal.facebook_token.strip() if canal.facebook_token else None,
                'template_senha': 'envio_senha2',  # Template padrão hardcoded
                'template_language': 'pt_BR'       # Idioma padrão hardcoded
            }
            
        except Exception as e:
            registrar_log('comum.integracoes', f"Erro ao buscar configurações WhatsApp: {str(e)}", nivel='ERROR')
            return None
    
    @staticmethod
    def construir_template_whatsapp(template_name, language_code, parametros_body=None, parametros_button=None):
        """
        Constrói estrutura de template WhatsApp de forma dinâmica.
        
        Args:
            template_name (str): Nome do template
            language_code (str): Código do idioma (ex: 'pt_BR')
            parametros_body (list): Lista de parâmetros para o corpo da mensagem
            parametros_button (list): Lista de parâmetros para botões
            
        Returns:
            dict: Estrutura do template formatada para WhatsApp API
        """
        template = {
            "name": template_name,
            "language": {
                "code": language_code
            }
        }
        
        # Adicionar componentes se houver parâmetros
        components = []
        
        # Componente body (corpo da mensagem)
        if parametros_body:
            body_params = []
            for param in parametros_body:
                # Se parâmetro é dict com type, usar diretamente (CURRENCY, DATE_TIME, etc)
                if isinstance(param, dict) and 'type' in param:
                    body_params.append(param)
                else:
                    # Parâmetro texto simples
                    body_params.append({
                        "type": "text",
                        "text": str(param)
                    })
            
            components.append({
                "type": "body",
                "parameters": body_params
            })
        
        # Componente button (botões)
        if parametros_button:
            for i, param in enumerate(parametros_button):
                components.append({
                    "type": "button",
                    "sub_type": "url",
                    "index": str(i),
                    "parameters": [
                        {
                            "type": "text",
                            "text": str(param)
                        }
                    ]
                })
        
        # Adicionar componentes ao template se existirem
        if components:
            template["components"] = components
            
        return template

    @staticmethod
    def envia_whatsapp(numero_telefone, canal_id, nome_template, idioma_template='pt_BR', parametros_corpo=None, parametros_botao=None):
        """
        Envia mensagem via WhatsApp usando template dinâmico.
        
        Args:
            numero_telefone (str): Número do telefone/celular (apenas números)
            canal_id (int): ID do canal
            nome_template (str): Nome do template (ex: 'envio_senha2')
            idioma_template (str): Código do idioma (ex: 'pt_BR')
            parametros_corpo (list): Lista de parâmetros para o corpo da mensagem (conforme template)
            parametros_botao (list): Lista de parâmetros para botões (conforme template)
            
        Returns:
            bool: True se enviado com sucesso, False caso contrário
        """
        try:
            # Obter configuração do WhatsApp baseado no canal_id
            config = WhatsAppService.obter_configuracao_whatsapp(canal_id)
            if not config:
                registrar_log('comum.integracoes', f"Configuração WhatsApp não encontrada para canal {canal_id}", nivel='ERROR')
                return False
            
            # Limpar número do telefone (apenas números)
            telefone_limpo = ''.join(filter(str.isdigit, numero_telefone))
            if len(telefone_limpo) < 10:
                registrar_log('comum.integracoes', f"Número de telefone inválido: {numero_telefone}", nivel='WARNING')
                return False
            
            # Construir template dinâmico usando parâmetros de entrada
            template = WhatsAppService.construir_template_whatsapp(
                template_name=nome_template,
                language_code=idioma_template,
                parametros_body=parametros_corpo,    # Parâmetros dinâmicos para o corpo
                parametros_button=parametros_botao   # Parâmetros dinâmicos para botões
            )
            
            # Preparar payload para WhatsApp API
            payload = {
                "messaging_product": "whatsapp",
                "to": f"55{telefone_limpo}",  # Código do Brasil + número
                "type": "template",
                "template": template
            }
            
            # Headers da requisição
            headers = {
                'Authorization': f'Bearer {config["token"]}',
                'Content-Type': 'application/json'
            }
            
            # Log do payload completo para diagnóstico
            registrar_log('comum.integracoes', f"[DEBUG] WhatsApp Payload: {json.dumps(payload, ensure_ascii=False)}", nivel='DEBUG')
            registrar_log('comum.integracoes', f"[DEBUG] WhatsApp URL: {config['url']}", nivel='DEBUG')
            
            # Fazer requisição para WhatsApp API
            response = requests.post(
                config['url'],
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                registrar_log('comum.integracoes', f"WhatsApp enviado com sucesso para {telefone_limpo}", nivel='INFO')
                registrar_log('comum.integracoes', f"[DEBUG] WhatsApp Response: {response.text}", nivel='DEBUG')
                return True
            else:
                registrar_log('comum.integracoes', f"Erro ao enviar WhatsApp - Status: {response.status_code} - Response: {response.text}", nivel='ERROR')
                return False
                
        except requests.RequestException as e:
            registrar_log('comum.integracoes', f"Erro de conexão ao enviar WhatsApp: {str(e)}", nivel='ERROR')
            return False
        except Exception as e:
            registrar_log('comum.integracoes', f"Erro inesperado ao enviar WhatsApp: {str(e)}", nivel='ERROR')
            return False
    
