"""
Estrutura Organizacional WallClub
Modelos hierárquicos: Canal → Regional → Vendedor → Grupo Econômico → Loja
"""

# Não importar modelos no __init__.py para evitar problemas de AppRegistryNotReady
# Os modelos devem ser importados diretamente quando necessário

__all__ = [
    'Canal',
    'Regional', 
    'Vendedor',
    'GrupoEconomico',
    'Loja'
]
