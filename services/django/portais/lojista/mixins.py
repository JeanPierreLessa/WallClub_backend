"""
Mixins para controle de acesso no portal lojista
"""
from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse
from portais.controle_acesso.filtros import FiltrosAcessoService
from portais.controle_acesso.models import PortalUsuario


class LojistaAuthMixin:
    """Mixin para verificar autenticação no portal lojista"""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.session.get('lojista_authenticated'):
            # Se for requisição AJAX, retornar JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
               request.content_type == 'application/json':
                return JsonResponse({
                    'sucesso': False,
                    'mensagem': 'Sessão expirada. Faça login novamente.'
                }, status=401)
            return redirect('lojista:login')
        return super().dispatch(request, *args, **kwargs)


class LojistaAccessMixin(LojistaAuthMixin):
    """Mixin para controle de acesso a lojas específicas"""
    
    def dispatch(self, request, *args, **kwargs):
        # Primeiro verificar autenticação
        auth_response = super().dispatch(request, *args, **kwargs)
        if hasattr(auth_response, 'status_code') and auth_response.status_code == 302:
            return auth_response
        
        # Verificar acesso à loja se loja_id for fornecido
        loja_id = request.GET.get('loja_id') or request.POST.get('loja_id')
        if loja_id:
            usuario_id = request.session.get('lojista_usuario_id')
            try:
                usuario = PortalUsuario.objects.get(id=usuario_id)
                
                # Usar serviço centralizado
                if not FiltrosAcessoService.usuario_pode_acessar_loja(usuario, int(loja_id)):
                    # Limpar mensagens anteriores para evitar acúmulo
                    storage = messages.get_messages(request)
                    for message in storage:
                        pass  # Consome mensagens antigas
                    
                    # Redirecionar silenciosamente sem mensagem de erro
                    return redirect('lojista:home')
            except (PortalUsuario.DoesNotExist, ValueError):
                return redirect('lojista:login')
        
        return super().dispatch(request, *args, **kwargs)


class LojistaDataMixin:
    """Mixin para fornecer dados comuns do lojista"""
    
    def get_lojas_acessiveis(self):
        """Retorna lojas acessíveis ao usuário logado"""
        usuario_id = self.request.session.get('lojista_usuario_id')
        if usuario_id:
            try:
                usuario = PortalUsuario.objects.get(id=usuario_id)
                return FiltrosAcessoService.obter_lojas_acessiveis(usuario)
            except PortalUsuario.DoesNotExist:
                return []
        return []
    
    def get_lojas_ids(self):
        """Retorna lista de IDs das lojas acessíveis"""
        lojas = self.get_lojas_acessiveis()
        return [loja['id'] for loja in lojas]
    
    def get_where_clause_lojas(self, campo_loja='loja_id'):
        """Retorna WHERE clause SQL para filtrar por lojas acessíveis"""
        lojas_ids = self.get_lojas_ids()
        if lojas_ids:
            ids_str = ','.join(map(str, lojas_ids))
            return f"AND {campo_loja} IN ({ids_str})"
        return "AND 1=0"  # Nenhuma loja acessível
