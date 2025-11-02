"""
Serviço para integração com Bureau de Crédito.
Consulta dados pessoais e status do CPF.
"""
import requests
import json
from datetime import datetime
from django.conf import settings
from wallclub_core.utilitarios.config_manager import get_config_manager
from wallclub_core.utilitarios.log_control import registrar_log


class BureauService:
    """Serviço para consultas no Bureau de Crédito"""
    
    @staticmethod
    def consulta_bureau(cpf):
        """
        Consulta dados do CPF no Bureau de Crédito.
        
        Args:
            cpf (str): CPF a ser consultado (apenas números)
            
        Returns:
            dict: Dados do cliente ou None se não encontrado
        """
        try:
            # Limpar CPF (apenas números)
            cpf_limpo = ''.join(filter(str.isdigit, cpf))
            if len(cpf_limpo) != 11:
                registrar_log('comum.integracoes', f"CPF inválido para consulta bureau: {cpf}", nivel='WARNING')
                return None
            
            # Buscar configurações do Bureau via ConfigManager
            config_manager = get_config_manager()
            bureau_config = config_manager.get_bureau_config()
            
            # Preparar payload para API
            payload = {
                "Datasets": "basic_data",
                "q": f"doc{{{cpf_limpo}}}",
                "Limit": 1
            }
            
            # Headers da requisição
            headers = {
                'AccessToken': bureau_config['access_token'],
                'TokenId': bureau_config['token_id'],
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            # Fazer requisição para API do Bureau
            response = requests.post(
                bureau_config['url'],
                json=payload,
                headers=headers,
                verify=False,  # SSL verification disabled (como no PHP)
                timeout=30
            )
            
            if response.status_code != 200:
                registrar_log('comum.integracoes', f"Erro na consulta bureau - Status: {response.status_code}", nivel='ERROR')
                return None
            
            # Processar resposta
            resposta_json = response.json()
            
            # Verificar se há resultados
            if not resposta_json.get('Result') or len(resposta_json['Result']) == 0:
                registrar_log('comum.integracoes', f"CPF não encontrado no bureau: {cpf_limpo}", nivel='WARNING')
                return None
            
            # Extrair dados do primeiro resultado
            basic_data = resposta_json['Result'][0].get('BasicData', {})
            tax_status = basic_data.get('TaxIdStatus')
            
            # Verificar se CPF está regular
            if tax_status != "REGULAR":
                registrar_log('comum.integracoes', f"CPF com status irregular no bureau: {cpf_limpo} - Status: {tax_status}", nivel='WARNING')
                return None
            
            # Extrair dados pessoais
            nascimento_raw = basic_data.get('BirthDate', '')
            nascimento_formatado = ''
            
            # Converter data ISO para formato YYYY-MM-DD
            if nascimento_raw:
                try:
                    from datetime import datetime
                    # Parse ISO format (1973-02-09T00:00:00Z) para YYYY-MM-DD
                    dt = datetime.fromisoformat(nascimento_raw.replace('Z', '+00:00'))
                    nascimento_formatado = dt.strftime('%Y-%m-%d')
                except Exception as e:
                    registrar_log('comum.integracoes', f"Erro ao converter data de nascimento: {nascimento_raw} - {str(e)}", nivel='WARNING')
                    nascimento_formatado = nascimento_raw
            
            dados = {
                'nome': basic_data.get('Name', ''),
                'mae': basic_data.get('MotherName', ''),
                'nascimento': nascimento_formatado,
                'signo': basic_data.get('ZodiacSign', '')
            }
            
            registrar_log('comum.integracoes', f"Consulta bureau bem-sucedida: {cpf_limpo}", nivel='INFO')
            return dados
            
        except requests.exceptions.RequestException as e:
            registrar_log('comum.integracoes', f"Erro de conexão na consulta bureau: {str(e)}", nivel='ERROR')
            return None
        except json.JSONDecodeError as e:
            registrar_log('comum.integracoes', f"Erro ao decodificar resposta do bureau: {str(e)}", nivel='ERROR')
            return None
        except Exception as e:
            registrar_log('comum.integracoes', f"Erro inesperado na consulta bureau: {str(e)}", nivel='ERROR')
            return None
