"""
Cliente para APIs Internas de Ofertas
Comunicação entre containers (portais/admin → apps/ofertas)
"""
import requests
from typing import Dict, Any, List, Optional
from django.conf import settings
from wallclub_core.utilitarios.log_control import registrar_log


class OfertasAPIClient:
    """
    Cliente para chamadas às APIs internas de ofertas
    Usado por portais/admin para comunicação com container de ofertas
    """
    
    def __init__(self):
        self.base_url = getattr(settings, 'INTERNAL_API_BASE_URL', 'http://localhost:8000')
        self.timeout = 10
        
    def _make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Dict[str, Any]:
        """
        Faz requisição à API interna
        
        Args:
            method: GET, POST, PUT, DELETE
            endpoint: Caminho do endpoint (ex: 'listar/')
            data: Dados para POST/PUT
            params: Query params para GET
            
        Returns:
            Resposta da API
        """
        url = f"{self.base_url}/api/internal/ofertas/{endpoint}"
        
        try:
            registrar_log('comum.integracoes.ofertas_api', 
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
            registrar_log('comum.integracoes.ofertas_api',
                         f"[API INTERNA] Timeout ao chamar {url}",
                         nivel='ERROR')
            return {'sucesso': False, 'mensagem': 'Timeout ao consultar ofertas'}
            
        except requests.exceptions.RequestException as e:
            registrar_log('comum.integracoes.ofertas_api',
                         f"[API INTERNA] Erro ao chamar {url}: {str(e)}",
                         nivel='ERROR')
            return {'sucesso': False, 'mensagem': f'Erro ao consultar ofertas: {str(e)}'}
    
    def listar_ofertas(self, canal_id: Optional[int] = None, ativo: Optional[bool] = None) -> Dict[str, Any]:
        """
        Lista ofertas
        
        Args:
            canal_id: Filtrar por canal (opcional)
            ativo: Filtrar por status ativo (opcional)
            
        Returns:
            {'sucesso': True, 'total': int, 'ofertas': [...]}
        """
        dados = {}
        if canal_id is not None:
            dados['canal_id'] = canal_id
        if ativo is not None:
            dados['ativo'] = ativo
            
        return self._make_request('POST', 'listar/', data=dados)
    
    def criar_oferta(self, dados: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cria nova oferta
        
        Args:
            dados: {
                'canal_id': int,
                'titulo': str,
                'descricao': str,
                'texto_push': str,
                'vigencia_inicio': str (ISO format),
                'vigencia_fim': str (ISO format),
                'tipo_segmentacao': str,
                'grupo_id': int (opcional)
            }
            
        Returns:
            {'sucesso': True, 'oferta_id': int}
        """
        return self._make_request('POST', 'criar/', data=dados)
    
    def obter_oferta(self, oferta_id: int) -> Dict[str, Any]:
        """
        Obtém detalhes de uma oferta
        
        Args:
            oferta_id: ID da oferta
            
        Returns:
            {'sucesso': True, 'oferta': {...}}
        """
        return self._make_request('POST', 'obter/', data={'oferta_id': oferta_id})
    
    def atualizar_oferta(self, oferta_id: int, dados: Dict[str, Any]) -> Dict[str, Any]:
        """
        Atualiza oferta existente
        
        Args:
            oferta_id: ID da oferta
            dados: Campos a atualizar
            
        Returns:
            {'sucesso': True, 'mensagem': str}
        """
        dados['oferta_id'] = oferta_id
        return self._make_request('POST', 'atualizar/', data=dados)
    
    def listar_grupos(self) -> Dict[str, Any]:
        """
        Lista grupos de segmentação
        
        Returns:
            {'sucesso': True, 'total': int, 'grupos': [...]}
        """
        return self._make_request('POST', 'grupos/listar/', data={})
    
    def criar_grupo(self, dados: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cria novo grupo de segmentação
        
        Args:
            dados: {
                'nome': str,
                'descricao': str,
                'canal_id': int
            }
            
        Returns:
            {'sucesso': True, 'grupo_id': int}
        """
        return self._make_request('POST', 'grupos/criar/', data=dados)


# Instância global
ofertas_api = OfertasAPIClient()
