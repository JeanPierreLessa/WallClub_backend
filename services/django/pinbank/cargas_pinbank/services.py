"""
Serviços para integração com API Pinbank - Arquivo de Re-exportação
Este arquivo mantém compatibilidade com código existente que importa daqui

ARQUITETURA:
- services_carga_extrato_pos.py: CargaExtratoPOSService (busca extrato da API Pinbank)
- services_carga_base_gestao_pos.py: CargaBaseGestaoPOSService (Wallet - transactiondata)
- services_carga_credenciadora.py: CargaCredenciadoraService (terminais não cadastrados)
- services_carga_checkout.py: CargaCheckoutService (checkout_transactions)
"""

# Re-exportar todos os serviços para manter compatibilidade
from .services_carga_extrato_pos import CargaExtratoPOSService
from .services_carga_base_gestao_pos import CargaBaseGestaoPOSService
from .services_carga_credenciadora import CargaCredenciadoraService
from .services_carga_checkout import CargaCheckoutService

# Alias para compatibilidade com código legado
CargaBaseGestaoService = CargaBaseGestaoPOSService

__all__ = [
    'CargaExtratoPOSService',
    'CargaBaseGestaoPOSService',
    'CargaBaseGestaoService',  # Alias legado
    'CargaCredenciadoraService',
    'CargaCheckoutService',
]
