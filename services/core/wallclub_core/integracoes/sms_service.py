"""
Serviço de envio de SMS via API LocaPlataforma
"""

import requests
from typing import Dict, Any, Optional
from django.conf import settings
from wallclub_core.utilitarios.log_control import registrar_log


class SMSService:
    """
    Serviço para envio de SMS via API LocaPlataforma
    """
    
    BASE_URL = "https://api.locaplataforma.com.br/servicesms/sendsingle"
    API_KEY = "MDdkM2I4MTE1Y2Q2NGMxMGFkZWE1YzAwY2M0MWNjNDI="
    SHORTCODE = "SHORTCODE_PREMIUM"
    
    @classmethod
    def enviar_sms(cls, telefone: str, mensagem: str, assunto: str) -> Dict[str, Any]:
        """
        Envia SMS via API LocaPlataforma
        
        Args:
            telefone (str): Número do telefone de destino
            mensagem (str): Conteúdo da mensagem SMS
            assunto (str): Assunto da mensagem
            
        Returns:
            Dict[str, Any]: Resposta da API com status, data e message
            
        Exemplo de retorno:
            {
                "status": "success",
                "data": "123",
                "message": null
            }
        """
        
        # Validar telefone antes de construir URL
        if not telefone or not telefone.strip():
            registrar_log('comum.integracoes', "Telefone vazio ou inválido para envio de SMS", nivel='ERROR')
            return {
                "status": "failure",
                "data": None,
                "message": "Telefone vazio ou inválido"
            }
        
        # Construir URL da API com URL encoding
        # Formato correto: /API_KEY/TELEFONE/MENSAGEM/SHORTCODE/ASSUNTO
        from urllib.parse import quote
        telefone_limpo = telefone.strip()
        mensagem_encoded = quote(mensagem, safe='')
        assunto_encoded = quote(assunto, safe='')
        url = f"{cls.BASE_URL}/{cls.API_KEY}/{telefone_limpo}/{mensagem_encoded}/{cls.SHORTCODE}/{assunto_encoded}"
        
        try:
            registrar_log('comum.integracoes', f"Enviando SMS para {telefone} com assunto: {assunto}")
            registrar_log('comum.integracoes', f"URL SMS construída: {url}")
            
            # Fazer requisição para API (com bypass SSL se necessário)
            try:
                response = requests.get(url, timeout=30, verify=True)
                response.raise_for_status()
            except requests.exceptions.SSLError as ssl_error:
                registrar_log('comum.integracoes', f"AVISO: Erro SSL detectado ({ssl_error}). Tentando bypass SSL...")
                registrar_log('comum.integracoes', "AÇÃO NECESSÁRIA: Contatar LocaPlataforma para renovar certificado SSL")
                response = requests.get(url, timeout=30, verify=False)
                response.raise_for_status()
                registrar_log('comum.integracoes', "SMS enviado com bypass SSL - certificado deve ser renovado")
            
            # Parse da resposta JSON
            resultado = response.json()
            
            if resultado.get('status') == 'success':
                registrar_log('comum.integracoes', f"SMS enviado com sucesso. REF_ID: {resultado.get('data')}")
            else:
                registrar_log('comum.integracoes', f"Falha no envio de SMS: {resultado.get('message')}", nivel='ERROR')
                
            return resultado
            
        except requests.exceptions.RequestException as e:
            registrar_log('comum.integracoes', f"Erro na requisição para API de SMS: {str(e)}", nivel='ERROR')
            return {
                "status": "failure",
                "data": None,
                "message": f"Erro na requisição: {str(e)}"
            }
            
        except ValueError as e:
            registrar_log('comum.integracoes', f"Erro ao fazer parse da resposta JSON: {str(e)}", nivel='ERROR')
            return {
                "status": "failure", 
                "data": None,
                "message": f"Erro no parse da resposta: {str(e)}"
            }
            
        except Exception as e:
            registrar_log('comum.integracoes', f"Erro inesperado no envio de SMS: {str(e)}", nivel='ERROR')
            return {
                "status": "failure",
                "data": None,
                "message": f"Erro inesperado: {str(e)}"
            }


def enviar_sms(telefone: str, mensagem: str, assunto: str) -> Dict[str, Any]:
    """
    Função utilitária para envio de SMS
    
    Args:
        telefone (str): Número do telefone de destino
        mensagem (str): Conteúdo da mensagem SMS
        assunto (str): Assunto da mensagem
        
    Returns:
        Dict[str, Any]: Resposta da API
    """
    return SMSService.enviar_sms(telefone, mensagem, assunto)
