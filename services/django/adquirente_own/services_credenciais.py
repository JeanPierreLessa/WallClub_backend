"""
Serviço para gerenciar credenciais Own Financial
Usa variáveis de ambiente (carregadas do AWS Secrets Manager via ConfigManager)
"""

import os
from typing import Dict, Any, Optional
from wallclub_core.utilitarios.log_control import registrar_log


class CredenciaisOwnService:
    """Serviço para obter credenciais Own das variáveis de ambiente"""

    @staticmethod
    def obter_environment() -> str:
        """
        Retorna o environment correto baseado na variável ENVIRONMENT

        Returns:
            'LIVE' para produção, 'TEST' para desenvolvimento
        """
        env = os.getenv('ENVIRONMENT', 'development').lower()
        return 'LIVE' if env == 'production' else 'TEST'

    def __init__(self, environment: str = None):
        """
        Inicializa serviço de credenciais

        Args:
            environment: 'LIVE' ou 'TEST' (None = usa ENVIRONMENT do sistema)
        """
        if environment is None:
            environment = self.obter_environment()
        self.environment = environment

    def obter_credenciais_core(self) -> Optional[Dict[str, Any]]:
        """
        Obtém credenciais core do WallClub das variáveis de ambiente

        As variáveis são carregadas automaticamente do AWS Secrets Manager
        pelo ConfigManager no settings.py

        Returns:
            Dict com credenciais ou None se não encontrado
            {
                'client_id': str,
                'client_secret': str,
                'scope': str,
                'environment': str
            }
        """
        try:
            # Buscar das variáveis de ambiente
            client_id = os.getenv('OWN_CORE_ID')
            client_secret = os.getenv('OWN_SECRET')
            scope = os.getenv('OWN_SCOPE')

            # Validar se todas as credenciais estão presentes
            if not all([client_id, client_secret, scope]):
                registrar_log('adquirente_own', '❌ Credenciais Own não encontradas nas variáveis de ambiente', nivel='ERROR')
                return None

            credenciais = {
                'client_id': client_id,
                'client_secret': client_secret,
                'scope': scope,
                'environment': self.environment
            }

            registrar_log('adquirente_own', f'✅ Credenciais Own obtidas: {client_id[:15]}...')

            return credenciais

        except Exception as e:
            registrar_log('adquirente_own', f'❌ Erro ao buscar credenciais: {str(e)}', nivel='ERROR')
            return None
