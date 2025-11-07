"""
Service para chamadas de API entre containers
Permite que containers se comuniquem via HTTP interno usando OAuth
"""
import requests
from typing import Dict, Any, Optional
from wallclub_core.utilitarios.log_control import registrar_log


class APIInternaService:
    """
    Service para comunicação entre containers via API HTTP interna
    """
    
    # Mapeamento de contextos para URLs base
    CONTAINER_URLS = {
        'apis': 'http://wallclub-apis:8007',
        'pos': 'http://wallclub-pos:8006',
        'portais': 'http://wallclub-portais:8005',
        'riskengine': 'http://wallclub-riskengine:8008',
    }
    
    @classmethod
    def chamar_api_interna(
        cls,
        metodo: str,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
        contexto: str = 'apis',
        timeout: int = 30,
        oauth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Chama API interna de outro container
        
        Args:
            metodo: GET, POST, PUT, DELETE
            endpoint: Caminho do endpoint (ex: /api/v1/cliente/consultar/)
            payload: Dados a enviar (para POST/PUT)
            contexto: Container de destino (apis, pos, portais, riskengine)
            timeout: Timeout em segundos
            oauth_token: Token OAuth (se não fornecido, usa token do ambiente)
        
        Returns:
            Dict com resposta da API
        """
        try:
            # Obter URL base do container
            base_url = cls.CONTAINER_URLS.get(contexto)
            if not base_url:
                registrar_log(
                    'wallclub_core.api_interna',
                    f'Contexto inválido: {contexto}',
                    nivel='ERROR'
                )
                return {
                    'sucesso': False,
                    'mensagem': f'Contexto inválido: {contexto}'
                }
            
            # Montar URL completa
            url = f"{base_url}{endpoint}"
            
            # Headers
            headers = {
                'Content-Type': 'application/json',
            }
            
            # Adicionar token OAuth se fornecido
            if oauth_token:
                headers['Authorization'] = f'Bearer {oauth_token}'
            
            # Fazer requisição
            registrar_log(
                'wallclub_core.api_interna',
                f'Chamando API interna: {metodo} {url}'
            )
            
            if metodo.upper() == 'GET':
                response = requests.get(url, headers=headers, params=payload, timeout=timeout)
            elif metodo.upper() == 'POST':
                response = requests.post(url, headers=headers, json=payload, timeout=timeout)
            elif metodo.upper() == 'PUT':
                response = requests.put(url, headers=headers, json=payload, timeout=timeout)
            elif metodo.upper() == 'DELETE':
                response = requests.delete(url, headers=headers, json=payload, timeout=timeout)
            else:
                return {
                    'sucesso': False,
                    'mensagem': f'Método HTTP inválido: {metodo}'
                }
            
            # Processar resposta
            if response.status_code >= 200 and response.status_code < 300:
                try:
                    return response.json()
                except Exception:
                    return {
                        'sucesso': True,
                        'mensagem': 'Requisição bem-sucedida',
                        'data': response.text
                    }
            else:
                registrar_log(
                    'wallclub_core.api_interna',
                    f'Erro na API interna: {response.status_code} - {response.text}',
                    nivel='ERROR'
                )
                try:
                    error_data = response.json()
                    return {
                        'sucesso': False,
                        'mensagem': error_data.get('mensagem', 'Erro na API'),
                        'status_code': response.status_code,
                        'error': error_data
                    }
                except Exception:
                    return {
                        'sucesso': False,
                        'mensagem': f'Erro HTTP {response.status_code}',
                        'status_code': response.status_code,
                        'error': response.text
                    }
                    
        except requests.exceptions.Timeout:
            registrar_log(
                'wallclub_core.api_interna',
                f'Timeout ao chamar API: {url}',
                nivel='ERROR'
            )
            return {
                'sucesso': False,
                'mensagem': 'Timeout na chamada da API'
            }
        except requests.exceptions.ConnectionError as e:
            registrar_log(
                'wallclub_core.api_interna',
                f'Erro de conexão ao chamar API: {url} - {str(e)}',
                nivel='ERROR'
            )
            return {
                'sucesso': False,
                'mensagem': f'Erro de conexão: {str(e)}'
            }
        except Exception as e:
            registrar_log(
                'wallclub_core.api_interna',
                f'Erro ao chamar API interna: {str(e)}',
                nivel='ERROR'
            )
            return {
                'sucesso': False,
                'mensagem': f'Erro ao chamar API: {str(e)}'
            }
    
    @classmethod
    def obter_token_oauth_container(cls) -> Optional[str]:
        """
        Obtém token OAuth para comunicação entre containers
        Pode ser implementado para buscar de cache ou gerar novo
        """
        # TODO: Implementar cache de token OAuth para containers
        # Por enquanto, retorna None e espera que seja passado manualmente
        return None
