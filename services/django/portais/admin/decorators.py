"""
Decorators para controle de acesso no portal administrativo.
"""

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse


def admin_required(view_func):
    """
    Decorator que verifica se o usuário tem acesso administrativo.
    Redireciona para login se não autenticado ou sem permissão.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Verificar se há sessão ativa
        if not request.session.get('portal_usuario_id'):
            messages.error(request, 'Acesso negado. Faça login para continuar.')
            return redirect('portais_admin:login')
        
        # Verificar se usuário tem permissão ao portal admin
        usuario_id = request.session.get('portal_usuario_id')
        try:
            from portais.controle_acesso.models import PortalUsuario
            from portais.controle_acesso.services import ControleAcessoService
            
            usuario = PortalUsuario.objects.get(id=usuario_id, ativo=True)
            nivel_acesso = ControleAcessoService.obter_nivel_portal(usuario, 'admin')
            
            if nivel_acesso == 'negado':
                messages.error(request, 'Acesso negado. Permissões insuficientes.')
                return redirect('portais_admin:dashboard')
        except PortalUsuario.DoesNotExist:
            messages.error(request, 'Sessão inválida. Faça login novamente.')
            return redirect('portais_admin:login')
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view


def admin_total_required(view_func):
    """
    Decorator que verifica se o usuário é admin total (não admin_canal).
    Para funcionalidades mais sensíveis.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Verificar se há sessão ativa
        if not request.session.get('portal_usuario_id'):
            messages.error(request, 'Acesso negado. Faça login para continuar.')
            return redirect('portais_admin:login')
        
        # Verificar se o usuário é admin total
        usuario_id = request.session.get('portal_usuario_id')
        try:
            from portais.controle_acesso.models import PortalUsuario
            from portais.controle_acesso.services import ControleAcessoService
            
            usuario = PortalUsuario.objects.get(id=usuario_id, ativo=True)
            nivel_acesso = ControleAcessoService.obter_nivel_portal(usuario, 'admin')
            
            if nivel_acesso != 'admin_total':
                messages.error(request, 'Acesso negado. Apenas administradores totais podem acessar esta funcionalidade.')
                return redirect('portais_admin:dashboard')
        except PortalUsuario.DoesNotExist:
            messages.error(request, 'Sessão inválida. Faça login novamente.')
            return redirect('portais_admin:login')
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view


def login_required_admin(view_func):
    """
    Decorator simples que apenas verifica se há login ativo.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.session.get('portal_usuario_id'):
            messages.error(request, 'Sessão expirada. Faça login novamente.')
            return redirect('portais_admin:login')
        
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view
