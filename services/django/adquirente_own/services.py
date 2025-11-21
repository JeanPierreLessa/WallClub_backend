"""
Serviços base para integração com Own Financial
Autenticação OAuth 2.0 e utilitários
"""

import requests
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from wallclub_core.utilitarios.log_control import registrar_log


class OwnService:
    """Serviço base para operações com Own Financial"""
    
    # URLs APIs Adquirência (OAuth 2.0)
    AUTH_URL_TEST = 'https://acquirer-qa.own.financial/agilli/v2/auth'
    AUTH_URL_LIVE = 'https://acquirer.own.financial/agilli/v2/auth'
    BASE_URL_TEST = 'https://acquirer-qa.own.financial/agilli'
    BASE_URL_LIVE = 'https://acquirer.own.financial/agilli'
    
    # URLs e-SiTef (Transações)
    ESITEF_URL_TEST = 'https://eu-test.oppwa.com'
    ESITEF_URL_LIVE = 'https://eu-prod.oppwa.com'
    
    def __init__(self, environment: str = 'LIVE'):
        """
        Inicializa o serviço Own
        
        Args:
            environment: 'TEST' ou 'LIVE'
        """
        self.environment = environment
        self.auth_url = self.AUTH_URL_LIVE if environment == 'LIVE' else self.AUTH_URL_TEST
        self.base_url = self.BASE_URL_LIVE if environment == 'LIVE' else self.BASE_URL_TEST
        self.esitef_url = self.ESITEF_URL_LIVE if environment == 'LIVE' else self.ESITEF_URL_TEST
        self.timeout = getattr(settings, 'OWN_TIMEOUT', 30)
    
    def obter_token_oauth(self, client_id: str, client_secret: str, scope: str) -> Dict[str, Any]:
        """
        Obtém access token via OAuth 2.0
        Token válido por 5 minutos (300s)
        Cache por 4 minutos (margem de segurança)
        
        Args:
            client_id: Client ID da aplicação
            client_secret: Client Secret da aplicação
            scope: Escopo solicitado
            
        Returns:
            Dict com access_token, token_type, expires_in
        """
        cache_key = f'own_oauth_token_{client_id}'
        token_cached = cache.get(cache_key)
        
        if token_cached:
            registrar_log('own.auth', f'✅ Token OAuth em cache: {client_id[:10]}...')
            return token_cached
        
        try:
            payload = {
                'client_id': client_id,
                'client_secret': client_secret,
                'scope': scope,
                'grant_type': 'client_credentials'
            }
            
            registrar_log('own.auth', f'🔑 Solicitando novo token OAuth: {client_id[:10]}...')
            
            response = requests.post(
                self.auth_url,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Cache por 4 minutos (margem de segurança - token válido por 5min)
            cache.set(cache_key, data, timeout=240)
            
            registrar_log('own.auth', f'✅ Token OAuth obtido: expires_in={data.get("expires_in")}s')
            
            return data
            
        except requests.exceptions.Timeout:
            registrar_log('own.auth', f'⏱️ Timeout ao obter token OAuth', nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Timeout na autenticação'
            }
        except requests.exceptions.RequestException as e:
            registrar_log('own.auth', f'❌ Erro ao obter token OAuth: {str(e)}', nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': f'Erro de autenticação: {str(e)}'
            }
    
    def fazer_requisicao_autenticada(
        self,
        method: str,
        endpoint: str,
        client_id: str,
        client_secret: str,
        scope: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Faz requisição autenticada às APIs Adquirência
        
        Args:
            method: Método HTTP (GET, POST)
            endpoint: Endpoint da API (ex: '/transacoes/v2/buscaTransacoesGerais')
            client_id: Client ID
            client_secret: Client Secret
            scope: Escopo
            data: Dados para POST (JSON)
            params: Query parameters para GET
            
        Returns:
            Dict com sucesso, dados ou mensagem de erro
        """
        try:
            # Obter token
            token_data = self.obter_token_oauth(client_id, client_secret, scope)
            
            if not token_data.get('access_token'):
                return {
                    'sucesso': False,
                    'mensagem': 'Falha na autenticação'
                }
            
            # Preparar headers
            headers = {
                'Authorization': f'Bearer {token_data["access_token"]}',
                'Content-Type': 'application/json'
            }
            
            # Fazer requisição
            url = f'{self.base_url}{endpoint}'
            
            registrar_log('own.api', f'📡 {method} {endpoint}')
            
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=self.timeout)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=self.timeout)
            else:
                raise ValueError(f'Método HTTP não suportado: {method}')
            
            response.raise_for_status()
            
            registrar_log('own.api', f'✅ Resposta recebida: status={response.status_code}')
            
            return {
                'sucesso': True,
                'dados': response.json(),
                'status_code': response.status_code
            }
            
        except requests.exceptions.Timeout:
            registrar_log('own.api', f'⏱️ Timeout na requisição: {endpoint}', nivel='WARNING')
            return {
                'sucesso': False,
                'mensagem': 'Timeout na comunicação com Own Financial'
            }
        except requests.exceptions.HTTPError as e:
            registrar_log('own.api', f'❌ Erro HTTP {e.response.status_code}: {endpoint}', nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': f'Erro HTTP {e.response.status_code}',
                'status_code': e.response.status_code
            }
        except requests.exceptions.RequestException as e:
            registrar_log('own.api', f'❌ Erro na requisição: {str(e)}', nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': f'Erro na comunicação: {str(e)}'
            }
    
    def obter_credenciais_white_label(self, environment: str = 'LIVE') -> Optional[Dict[str, Any]]:
        """
        Obtém credenciais Own do cliente White Label (WallClub)
        
        Args:
            environment: 'LIVE' ou 'TEST'
            
        Returns:
            Dict com credenciais ou None
        """
        from adquirente_own.cargas_own.models import CredenciaisExtratoContaOwn
        
        try:
            credencial = CredenciaisExtratoContaOwn.objects.filter(
                environment=environment,
                ativo=True
            ).first()
            
            if not credencial:
                registrar_log('own.credenciais', f'❌ Credenciais não encontradas para ambiente {environment}', nivel='ERROR')
                return None
            
            return {
                'client_id': credencial.client_id,
                'client_secret': credencial.client_secret,
                'scope': credencial.scope,
                'entity_id': credencial.entity_id,
                'access_token': credencial.access_token,
                'environment': credencial.environment,
                'cnpj_white_label': credencial.cnpj_white_label
            }
            
        except Exception as e:
            registrar_log('own.credenciais', f'❌ Erro ao buscar credenciais: {str(e)}', nivel='ERROR')
            return None
    
    def obter_credenciais_loja(self, loja_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtém credenciais Own para uma loja específica
        
        Args:
            loja_id: ID da loja
            
        Returns:
            Dict com credenciais ou None
        """
        # Por enquanto, todas as lojas usam as mesmas credenciais White Label
        # No futuro, pode-se implementar credenciais por loja
        return self.obter_credenciais_white_label(self.environment)
