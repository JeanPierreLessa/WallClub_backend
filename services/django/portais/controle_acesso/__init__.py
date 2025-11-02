"""
Módulo de Controle de Acesso para Portais
Sistema centralizado de permissões e controle de acesso
"""

from .controle_acesso import (
    MatrizControleAcesso,
    TipoUsuario,
    NivelAcesso,
    PermissaoFuncionalidade,
    require_funcionalidade,
    require_secao_permitida
)

__all__ = [
    'MatrizControleAcesso',
    'TipoUsuario', 
    'NivelAcesso',
    'PermissaoFuncionalidade',
    'require_funcionalidade',
    'require_secao_permitida'
]
