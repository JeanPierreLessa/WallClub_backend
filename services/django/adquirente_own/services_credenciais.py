"""
Serviço para gerenciar credenciais Own Financial
Usa variáveis de ambiente (carregadas do AWS Secrets Manager via ConfigManager)
"""

import os
from typing import Dict, Any, Optional
from wallclub_core.utilitarios.log_control import registrar_log


class CredenciaisOwnService:
    """Serviço para obter credenciais Own das variáveis de ambiente"""

    def __init__(self, environment: str = 'LIVE'):
        """
        Inicializa serviço de credenciais

        Args:
            environment: 'LIVE' ou 'TEST' (não usado, mantido para compatibilidade)
        """
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
                registrar_log('own.credenciais', '❌ Credenciais Own não encontradas nas variáveis de ambiente', nivel='ERROR')
                return None

            credenciais = {
                'client_id': client_id,
                'client_secret': client_secret,
                'scope': scope,
                'environment': self.environment
            }

            registrar_log('own.credenciais', f'✅ Credenciais Own obtidas: {client_id[:15]}...')

            return credenciais

        except Exception as e:
            registrar_log('own.credenciais', f'❌ Erro ao buscar credenciais: {str(e)}', nivel='ERROR')
            return None
