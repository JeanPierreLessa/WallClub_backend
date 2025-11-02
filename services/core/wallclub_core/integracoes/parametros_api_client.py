"""
Cliente para APIs Internas de Parâmetros WallClub
Comunicação entre containers (portais/admin → parametros_wallclub)
"""
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime
from django.conf import settings
from wallclub_core.utilitarios.log_control import registrar_log


class ParametrosAPIClient:
    """
    Cliente para chamadas às APIs internas de parâmetros
    Usado por portais/admin para comunicação com módulo de parâmetros
    """
    
    def __init__(self):
        self.base_url = getattr(settings, 'INTERNAL_API_BASE_URL', 'http://localhost:8000')
        self.timeout = 10
        
    def _make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Dict[str, Any]:
        """
        Faz requisição à API interna
        
        Args:
            method: GET, POST, PUT, DELETE
            endpoint: Caminho do endpoint
            data: Dados para POST/PUT
            params: Query params para GET
            
        Returns:
            Resposta da API
        """
        url = f"{self.base_url}/api/internal/parametros/{endpoint}"
        
        try:
            registrar_log('comum.integracoes.parametros_api', 
                         f"[API INTERNA] {method} {url}", 
                         nivel='INFO')
            
            response = requests.request(
                method=method,
                url=url,
                json=data,
                params=params,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            registrar_log('comum.integracoes.parametros_api',
                         f"[API INTERNA] Timeout ao chamar {url}",
                         nivel='ERROR')
            return {'sucesso': False, 'mensagem': 'Timeout ao consultar parâmetros'}
            
        except requests.exceptions.RequestException as e:
            registrar_log('comum.integracoes.parametros_api',
                         f"[API INTERNA] Erro ao chamar {url}: {str(e)}",
                         nivel='ERROR')
            return {'sucesso': False, 'mensagem': f'Erro ao consultar parâmetros: {str(e)}'}
    
    def buscar_configuracoes_loja(self, loja_id: int, data_referencia: datetime = None) -> Dict[str, Any]:
        """
        Busca configurações de uma loja
        
        Args:
            loja_id: ID da loja
            data_referencia: Data para buscar configurações (default: now)
            
        Returns:
            {'sucesso': True, 'total': int, 'configuracoes': [...]}
        """
        if data_referencia is None:
            data_referencia = datetime.now()
        
        dados = {
            'loja_id': loja_id,
            'data_referencia': data_referencia.isoformat()
        }
        
        return self._make_request('POST', 'configuracoes/loja/', data=dados)
    
    def contar_configuracoes_loja(self, loja_id: int) -> int:
        """
        Conta configurações vigentes de uma loja
        
        Args:
            loja_id: ID da loja
            
        Returns:
            Total de configurações
        """
        response = self._make_request('POST', 'configuracoes/contar/', data={'loja_id': loja_id})
        return response.get('total', 0) if response.get('sucesso') else 0
    
    def obter_ultima_configuracao(self, loja_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtém última configuração de uma loja
        
        Args:
            loja_id: ID da loja
            
        Returns:
            Dados da configuração ou None
        """
        response = self._make_request('POST', 'configuracoes/ultima/', data={'loja_id': loja_id})
        return response.get('configuracao') if response.get('sucesso') else None
    
    def verificar_modalidades_loja(self, loja_id: int) -> Dict[str, Any]:
        """
        Verifica modalidades Wall S/N de uma loja
        
        Args:
            loja_id: ID da loja
            
        Returns:
            {'sucesso': True, 'wall_s': bool, 'wall_n': bool, 'modalidades': [...]}
        """
        return self._make_request('POST', 'loja/modalidades/', data={'loja_id': loja_id})
    
    def listar_planos(self) -> List[Dict[str, Any]]:
        """
        Lista todos os planos
        
        Returns:
            Lista de planos
        """
        response = self._make_request('GET', 'planos/')
        return response.get('planos', []) if response.get('sucesso') else []
    
    def listar_importacoes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Lista últimas importações
        
        Args:
            limit: Número máximo de importações
            
        Returns:
            Lista de importações
        """
        response = self._make_request('GET', 'importacoes/', params={'limit': limit})
        return response.get('importacoes', []) if response.get('sucesso') else []
    
    def obter_importacao(self, importacao_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtém detalhes de uma importação
        
        Args:
            importacao_id: ID da importação
            
        Returns:
            Dados da importação ou None
        """
        response = self._make_request('GET', f'importacoes/{importacao_id}/')
        return response.get('importacao') if response.get('sucesso') else None


# Instância global
parametros_api = ParametrosAPIClient()
