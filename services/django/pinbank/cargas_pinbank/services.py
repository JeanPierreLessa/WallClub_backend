"""
Serviços para integração com API Pinbank - Arquivo de Re-exportação
Este arquivo mantém compatibilidade com código existente que importa daqui

ARQUITETURA ATUAL (base_transacoes_unificadas):
- services_carga_extrato_pos.py: CargaExtratoPOSService (busca extrato da API Pinbank)
- services_carga_base_unificada_pos.py: CargaBaseUnificadaPOSService (Wallet)
- services_carga_base_unificada_credenciadora.py: CargaBaseUnificadaCredenciadoraService
- services_carga_base_unificada_checkout.py: CargaBaseUnificadaCheckoutService

DEPRECATED (movidos para backup/):
- services_carga_base_gestao_pos.py (baseTransacoesGestao)
- services_carga_credenciadora.py (baseTransacoesGestao)
- services_carga_checkout.py (baseTransacoesGestao)
"""

# Re-exportar serviços ativos
from .services_carga_extrato_pos import CargaExtratoPOSService
from .services_carga_base_unificada_pos import CargaBaseUnificadaPOSService
from .services_carga_base_unificada_credenciadora import CargaBaseUnificadaCredenciadoraService
from .services_carga_base_unificada_checkout import CargaBaseUnificadaCheckoutService

__all__ = [
    'CargaExtratoPOSService',
    'CargaBaseUnificadaPOSService',
    'CargaBaseUnificadaCredenciadoraService',
    'CargaBaseUnificadaCheckoutService',
]
