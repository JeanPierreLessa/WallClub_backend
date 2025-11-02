"""
Sistema de Controle de Acesso Centralizado
Matriz de permissões por página/funcionalidade vs tipo de usuário
"""

from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass
from functools import wraps


class TipoUsuario(Enum):
    ADMIN = 'admin'
    ADMIN_CANAL = 'admin_canal'
    CANAL_ADMIN = 'canal_admin'
    CANAL_LEITURA = 'canal_leitura'
    LOJISTA = 'lojista'
    CANAL = 'canal'
    REGIONAL = 'regional'
    CORPORATIVO = 'corporativo'
    GRUPO_ECONOMICO = 'grupo_economico'


class NivelAcesso(Enum):
    NEGADO = 'negado'
    LEITURA = 'leitura'
    ESCRITA = 'escrita'
    ADMIN = 'admin'
    ADMIN_TOTAL = 'admin_total'


@dataclass
class PermissaoFuncionalidade:
    """Define permissão para uma funcionalidade específica"""
    nome: str
    descricao: str
    nivel_minimo: NivelAcesso
    requer_canal: bool = False  # Se true, filtra por canal do usuário


class MatrizControleAcesso:
    """
    Matriz centralizada de controle de acesso
    Define permissões por página/funcionalidade vs tipo de usuário
    """
    
    # Matriz de níveis de acesso por tipo de usuário
    NIVEIS_USUARIO = {
        TipoUsuario.ADMIN: NivelAcesso.ADMIN_TOTAL,
        TipoUsuario.ADMIN_CANAL: NivelAcesso.ADMIN,
        TipoUsuario.CANAL_ADMIN: NivelAcesso.ESCRITA,
        TipoUsuario.CANAL_LEITURA: NivelAcesso.LEITURA,
        TipoUsuario.LOJISTA: NivelAcesso.ESCRITA,
        TipoUsuario.CANAL: NivelAcesso.ESCRITA,
        TipoUsuario.REGIONAL: NivelAcesso.ESCRITA,
        TipoUsuario.CORPORATIVO: NivelAcesso.LEITURA,
        TipoUsuario.GRUPO_ECONOMICO: NivelAcesso.LEITURA,
    }
    
    # Funcionalidades do sistema
    FUNCIONALIDADES = {
        # Dashboard
        'dashboard_view': PermissaoFuncionalidade(
            'dashboard_view', 'Visualizar Dashboard', NivelAcesso.LEITURA, requer_canal=True
        ),
        
        # Usuários
        'usuarios_list': PermissaoFuncionalidade(
            'usuarios_list', 'Listar Usuários', NivelAcesso.LEITURA
        ),
        'usuarios_create': PermissaoFuncionalidade(
            'usuarios_create', 'Criar Usuários', NivelAcesso.ESCRITA
        ),
        'usuarios_edit': PermissaoFuncionalidade(
            'usuarios_edit', 'Editar Usuários', NivelAcesso.ESCRITA
        ),
        'usuarios_delete': PermissaoFuncionalidade(
            'usuarios_delete', 'Excluir Usuários', NivelAcesso.ADMIN
        ),
        'usuarios_manage_portals': PermissaoFuncionalidade(
            'usuarios_manage_portals', 'Gerenciar Portais de Usuários', NivelAcesso.ADMIN
        ),
        
        # Parâmetros - Apenas admin_total
        'parametros_list': PermissaoFuncionalidade(
            'parametros_list', 'Listar Parâmetros', NivelAcesso.ADMIN_TOTAL
        ),
        'parametros_view': PermissaoFuncionalidade(
            'parametros_view', 'Visualizar Parâmetros', NivelAcesso.ADMIN_TOTAL
        ),
        'parametros_copy': PermissaoFuncionalidade(
            'parametros_copy', 'Copiar Parâmetros', NivelAcesso.ADMIN_TOTAL
        ),
        'parametros_edit': PermissaoFuncionalidade(
            'parametros_edit', 'Editar Parâmetros', NivelAcesso.ADMIN_TOTAL
        ),
        # Gestão Financeira - Admin total tem acesso
        'base_transacoes_gestao': PermissaoFuncionalidade(
            'base_transacoes_gestao', 'Visualizar Base Transações Gestão', NivelAcesso.ADMIN, requer_canal=False
        ),
        
        # RPR (Relatório Produção Receita)
        'rpr_view': PermissaoFuncionalidade(
            'rpr_view', 'Visualizar RPR', NivelAcesso.LEITURA, requer_canal=True
        ),
        'rpr_export': PermissaoFuncionalidade(
            'rpr_export', 'Exportar RPR', NivelAcesso.LEITURA, requer_canal=True
        ),
        'rpr_manual_transactions': PermissaoFuncionalidade(
            'rpr_manual_transactions', 'Ver Lançamentos Manuais', NivelAcesso.LEITURA, requer_canal=True
        ),
        
        # Hierarquia
        'hierarquia_list': PermissaoFuncionalidade(
            'hierarquia_list', 'Listar Hierarquia', NivelAcesso.LEITURA, requer_canal=True
        ),
        'hierarquia_create': PermissaoFuncionalidade(
            'hierarquia_create', 'Criar Hierarquia', NivelAcesso.ESCRITA, requer_canal=True
        ),
        'hierarquia_edit': PermissaoFuncionalidade(
            'hierarquia_edit', 'Editar Hierarquia', NivelAcesso.ESCRITA, requer_canal=True
        ),
        'hierarquia_delete': PermissaoFuncionalidade(
            'hierarquia_delete', 'Excluir Hierarquia', NivelAcesso.ADMIN
        ),
        
        # Terminais
        'terminais_list': PermissaoFuncionalidade(
            'terminais_list', 'Listar Terminais', NivelAcesso.LEITURA, requer_canal=True
        ),
        'terminais_create': PermissaoFuncionalidade(
            'terminais_create', 'Criar Terminais', NivelAcesso.ESCRITA, requer_canal=True
        ),
        'terminais_edit': PermissaoFuncionalidade(
            'terminais_edit', 'Editar Terminais', NivelAcesso.ESCRITA, requer_canal=True
        ),
        'terminais_delete': PermissaoFuncionalidade(
            'terminais_delete', 'Excluir Terminais', NivelAcesso.ADMIN
        ),
        
        # Pagamentos
        'pagamentos_list': PermissaoFuncionalidade(
            'pagamentos_list', 'Listar Pagamentos', NivelAcesso.LEITURA, requer_canal=True
        ),
        'pagamentos_create': PermissaoFuncionalidade(
            'pagamentos_create', 'Criar Pagamentos', NivelAcesso.ESCRITA, requer_canal=True
        ),
        'pagamentos_edit': PermissaoFuncionalidade(
            'pagamentos_edit', 'Editar Pagamentos', NivelAcesso.ESCRITA, requer_canal=True
        ),
        'pagamentos_delete': PermissaoFuncionalidade(
            'pagamentos_delete', 'Excluir Pagamentos', NivelAcesso.ADMIN
        ),
    }
    
    @classmethod
    def usuario_tem_acesso(cls, nivel_ou_tipo_usuario: str, funcionalidade: str) -> bool:
        """
        Verifica se usuário tem acesso à funcionalidade
        
        Args:
            nivel_ou_tipo_usuario: Nível de acesso (admin_total, admin_canal) ou tipo do usuário
            funcionalidade: Nome da funcionalidade
            
        Returns:
            bool: True se tem acesso, False caso contrário
        """
        if funcionalidade not in cls.FUNCIONALIDADES:
            return False
            
        funcionalidade_obj = cls.FUNCIONALIDADES[funcionalidade]
        
        # Mapear string para constante NivelAcesso
        mapeamento_niveis = {
            'admin_total': NivelAcesso.ADMIN_TOTAL,
            'admin': NivelAcesso.ADMIN,
            'escrita': NivelAcesso.ESCRITA,
            'leitura': NivelAcesso.LEITURA,
            'negado': NivelAcesso.NEGADO
        }
        
        # Determinar o nível do usuário
        if nivel_ou_tipo_usuario in mapeamento_niveis:
            nivel_usuario = mapeamento_niveis[nivel_ou_tipo_usuario]
        else:
            # Se é um tipo de usuário, mapear para nível
            try:
                tipo_enum = TipoUsuario(nivel_ou_tipo_usuario)
                nivel_usuario = cls.NIVEIS_USUARIO.get(tipo_enum, NivelAcesso.NEGADO)
            except ValueError:
                return False
        
        # Verificar se o nível do usuário é suficiente
        niveis_hierarquia = [NivelAcesso.NEGADO, NivelAcesso.LEITURA, NivelAcesso.ESCRITA, NivelAcesso.ADMIN, NivelAcesso.ADMIN_TOTAL]
        
        try:
            nivel_minimo_idx = niveis_hierarquia.index(funcionalidade_obj.nivel_minimo)
            nivel_usuario_idx = niveis_hierarquia.index(nivel_usuario)
            return nivel_usuario_idx >= nivel_minimo_idx
        except ValueError:
            return False
    
    @classmethod
    def obter_funcionalidades_usuario(cls, tipo_usuario: str) -> List[str]:
        """
        Retorna lista de funcionalidades que o usuário tem acesso
        
        Args:
            tipo_usuario: Tipo do usuário
            
        Returns:
            List[str]: Lista de funcionalidades acessíveis
        """
        funcionalidades_acessiveis = []
        
        for nome_func in cls.FUNCIONALIDADES.keys():
            if cls.usuario_tem_acesso(tipo_usuario, nome_func):
                funcionalidades_acessiveis.append(nome_func)
                
        return funcionalidades_acessiveis
    
    @classmethod
    def obter_nivel_usuario(cls, tipo_usuario: str) -> NivelAcesso:
        """
        Retorna o nível de acesso do tipo de usuário
        
        Args:
            tipo_usuario: Tipo do usuário
            
        Returns:
            NivelAcesso: Nível de acesso do usuário
        """
        try:
            tipo_enum = TipoUsuario(tipo_usuario)
            return cls.NIVEIS_USUARIO.get(tipo_enum, NivelAcesso.NEGADO)
        except ValueError:
            return NivelAcesso.NEGADO
    
    @classmethod
    def funcionalidade_requer_canal(cls, funcionalidade: str) -> bool:
        """
        Verifica se funcionalidade requer filtro por canal
        
        Args:
            funcionalidade: Nome da funcionalidade
            
        Returns:
            bool: True se requer canal, False caso contrário
        """
        if funcionalidade not in cls.FUNCIONALIDADES:
            return False
            
        return cls.FUNCIONALIDADES[funcionalidade].requer_canal


# Decorator para controle de acesso baseado na nova estrutura (Opção 2)
def require_funcionalidade(funcionalidade: str, portal: str = 'admin', nivel_minimo: str = 'leitura'):
    """
    Decorator que verifica acesso baseado na nova estrutura de permissões
    
    Args:
        funcionalidade: Nome da funcionalidade
        portal: Portal necessário ('admin', 'lojista', 'corporativo')
        nivel_minimo: Nível mínimo necessário ('leitura', 'escrita', 'admin')
    """
    def decorator(view_func):
        from functools import wraps
        from django.shortcuts import redirect
        from django.contrib import messages
        from .services import ControleAcessoService
        
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            from .services import AutenticacaoService
            
            # Obter usuário da sessão
            usuario = AutenticacaoService.obter_usuario_sessao(request)
            
            if not usuario:
                messages.error(request, 'Você precisa fazer login para acessar esta página.')
                return redirect('/portal_admin/login/')
            
            # Verificar acesso ao portal
            if not usuario.pode_acessar_portal(portal):
                messages.error(request, f'Você não tem acesso ao portal {portal}.')
                return redirect('/portal_admin/dashboard/')
            
            # Verificar se tem permissão para a funcionalidade
            # Para usuários admin, permitir acesso a todas as funcionalidades
            permissoes = usuario.permissoes.filter(portal=portal)
            if not permissoes.exists():
                messages.error(request, 'Você não tem permissão para acessar este recurso.')
                return redirect('/portal_admin/dashboard/')
            
            # Se tem permissão admin no portal, liberar acesso
            tem_admin = permissoes.filter(nivel_acesso='admin').exists()
            if not tem_admin and nivel_minimo == 'admin':
                messages.error(request, 'Você não tem permissão administrativa para este recurso.')
                return redirect('/portal_admin/dashboard/')
            
            # Adicionar informações de controle ao request
            request.portal_usuario = usuario
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def require_secao_permitida(secao):
    """
    Decorator para bloquear acesso a seções não permitidas para o nível do usuário
    
    Args:
        secao: Nome da seção (ex: 'pagamentos', 'gestao_admin')
    
    Usage:
        @require_secao_permitida('pagamentos')
        def pagamentos_list(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            from django.contrib import messages
            from django.shortcuts import redirect
            from .services import AutenticacaoService
            from .services import ControleAcessoService
            
            # Obter usuário da sessão
            usuario = AutenticacaoService.obter_usuario_sessao(request)
            
            if not usuario:
                messages.error(request, 'Você precisa fazer login para acessar esta página.')
                return redirect('/portal_admin/login/')
            
            # Obter nível do usuário no portal admin
            nivel_usuario = ControleAcessoService.obter_nivel_portal(usuario, 'admin')
            
            # Verificar se seção está permitida para este nível
            secoes_permitidas = ControleAcessoService.SECOES_POR_NIVEL.get(nivel_usuario, [])
            
            if secao not in secoes_permitidas:
                messages.error(request, 'A tela que você tentou acessar não está disponível pro seu perfil.')
                return redirect('portais_admin:dashboard')
            
            # Adicionar informações de controle ao request
            request.portal_usuario = usuario
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def require_acesso_padronizado(funcionalidade: str):
    """
    Decorator padronizado que redireciona para dashboard com mensagem padrão
    quando usuário não tem acesso
    
    Args:
        funcionalidade: Nome da funcionalidade a verificar
    
    Usage:
        @require_acesso_padronizado('pagamentos_list')
        def pagamentos_list(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            from django.contrib import messages
            from django.shortcuts import redirect
            from .services import AutenticacaoService
            from .services import ControleAcessoService
            
            # Obter usuário da sessão
            usuario = AutenticacaoService.obter_usuario_sessao(request)
            
            if not usuario:
                messages.error(request, 'Você precisa fazer login para acessar esta página.')
                return redirect('/portal_admin/login/')
            
            # Obter nível do usuário no portal admin
            nivel_usuario = ControleAcessoService.obter_nivel_portal(usuario, 'admin')
            
            # Verificar acesso direto por nível para funcionalidades específicas
            if funcionalidade == 'base_transacoes_gestao':
                if nivel_usuario not in ['admin_total', 'admin_superusuario']:
                    messages.error(request, 'A tela que você tentou acessar não está disponível pro seu perfil.')
                    return redirect('portais_admin:dashboard')
            elif funcionalidade in ['rpr_view', 'rpr_export']:
                if nivel_usuario not in ['admin_total', 'admin_superusuario', 'admin_canal']:
                    messages.error(request, 'A tela que você tentou acessar não está disponível pro seu perfil.')
                    return redirect('portais_admin:dashboard')
            elif funcionalidade in ['parametros_list', 'parametros_view', 'parametros_copy', 'parametros_edit']:
                if nivel_usuario not in ['admin_total']:
                    messages.error(request, 'A tela que você tentou acessar não está disponível pro seu perfil.')
                    return redirect('portais_admin:dashboard')
            else:
                # Para outras funcionalidades, usar matriz de controle
                if not MatrizControleAcesso.usuario_tem_acesso(nivel_usuario, funcionalidade):
                    messages.error(request, 'A tela que você tentou acessar não está disponível pro seu perfil.')
                    return redirect('portais_admin:dashboard')
            
            # Para funcionalidades que requerem canal, verificar se tem vínculos
            # Exceção: admin_total tem acesso global mesmo sem vínculos específicos
            if MatrizControleAcesso.funcionalidade_requer_canal(funcionalidade):
                if nivel_usuario != 'admin_total':
                    vinculos = ControleAcessoService.obter_vinculos_usuario(usuario, portal='admin')
                    if not vinculos:
                        messages.error(request, 'A tela que você tentou acessar não está disponível pro seu perfil.')
                        return redirect('portais_admin:dashboard')
            
            # Adicionar informações de controle ao request
            request.portal_usuario = usuario
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator
