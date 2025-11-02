"""
Decorators para controle de acesso ao portal de vendas
"""
from functools import wraps
from django.shortcuts import redirect
from django.http import HttpResponseForbidden
from wallclub_core.utilitarios.log_control import registrar_log


def requer_checkout_vendedor(view_func):
    """
    Decorator para restringir acesso apenas a usuários com perfil checkout_vendedor
    
    Verifica:
    - Usuário autenticado
    - Perfil = checkout_vendedor
    - Sessão ativa
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Verificar autenticação
        if not request.session.get('vendas_authenticated'):
            registrar_log('portais.vendas', f"Tentativa de acesso não autenticado: {request.path}")
            return redirect('vendas:login')
        
        # Verificar perfil
        vendedor_id = request.session.get('vendedor_id')
        if not vendedor_id:
            registrar_log('portais.vendas', f"Sessão sem vendedor_id: {request.path}", nivel='WARNING')
            return redirect('vendas:login')
        
        # Buscar usuário e validar permissão
        from portais.controle_acesso.models import PortalUsuario, PortalUsuarioAcesso
        try:
            usuario = PortalUsuario.objects.prefetch_related('permissoes', 'acessos').get(id=vendedor_id)
            
            # Validar permissão para portal vendas
            if not usuario.permissoes.filter(portal='vendas').exists():
                registrar_log('portais.vendas', f"Acesso negado - sem permissão vendas", nivel='WARNING')
                return HttpResponseForbidden('Acesso negado. Apenas vendedores de checkout.')
            
            # Validar se operador tem vínculo com pelo menos uma loja
            permissao_vendas = usuario.permissoes.filter(portal='vendas').first()
            if permissao_vendas and permissao_vendas.nivel_acesso == 'operador':
                tem_loja = PortalUsuarioAcesso.objects.filter(
                    usuario=usuario,
                    portal='vendas',
                    entidade_tipo='loja',
                    ativo=True
                ).exists()
                
                if not tem_loja:
                    registrar_log(
                        'portais.vendas',
                        f"Acesso negado - operador sem loja vinculada: {usuario.email}",
                        nivel='WARNING'
                    )
                    return HttpResponseForbidden('Acesso negado. Nenhuma loja vinculada ao seu usuário.')
            
            # Adicionar usuário ao request para uso nas views
            request.vendedor = usuario
            
        except PortalUsuario.DoesNotExist:
            registrar_log('portais.vendas', f"Vendedor não encontrado: {vendedor_id}", nivel='ERROR')
            return redirect('vendas:login')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def vendedor_pode_acessar_loja(view_func):
    """
    Decorator adicional para validar se vendedor tem acesso à loja específica
    Usado em views que recebem loja_id como parâmetro
    """
    @wraps(view_func)
    def wrapper(request, loja_id=None, *args, **kwargs):
        if not loja_id:
            return view_func(request, *args, **kwargs)
        
        # Validar se vendedor tem acesso a esta loja
        vendedor = getattr(request, 'vendedor', None)
        if not vendedor:
            return HttpResponseForbidden('Vendedor não identificado')
        
        # Buscar lojas vinculadas ao vendedor
        from portais.controle_acesso.models import PortalUsuarioAcesso
        tem_acesso = PortalUsuarioAcesso.objects.filter(
            usuario=vendedor,
            entidade_tipo='loja',
            entidade_id=loja_id,
            ativo=True
        ).exists()
        
        if not tem_acesso:
            registrar_log('portais.vendas', f"Vendedor {vendedor.id} sem acesso à loja {loja_id}", nivel='WARNING')
            return HttpResponseForbidden('Você não tem acesso a esta loja')
        
        return view_func(request, loja_id=loja_id, *args, **kwargs)
    
    return wrapper


def requer_permissao(recurso):
    """
    Decorator para validar permissões granulares de recursos específicos
    
    Args:
        recurso: Nome do recurso a validar (ex: 'recorrencia', 'relatorios', 'configuracoes')
    
    Verifica:
    - Usuário autenticado (via requer_checkout_vendedor)
    - recursos_permitidos no PortalPermissao contém o recurso solicitado
    
    Exemplo de uso:
        @requer_permissao('recorrencia')
        def minha_view(request):
            ...
    """
    def decorator(view_func):
        @requer_checkout_vendedor  # Garante autenticação primeiro
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            registrar_log('portais.vendas', f"[DEBUG] Validando permissão para recurso: {recurso}", nivel='INFO')
            
            # Buscar permissão do vendedor
            vendedor = getattr(request, 'vendedor', None)
            if not vendedor:
                registrar_log('portais.vendas', f"Vendedor não identificado para recurso: {recurso}", nivel='ERROR')
                return HttpResponseForbidden('Vendedor não identificado')
            
            registrar_log('portais.vendas', f"[DEBUG] Vendedor encontrado: {vendedor.id} - {vendedor.email}", nivel='INFO')
            
            # Buscar permissão do portal vendas
            from portais.controle_acesso.models import PortalPermissao
            try:
                permissao = PortalPermissao.objects.get(
                    usuario=vendedor,
                    portal='vendas'
                )
                
                registrar_log('portais.vendas', f"[DEBUG] Permissão encontrada - recursos: {permissao.recursos_permitidos}", nivel='INFO')
                
                # Verificar recursos_permitidos
                recursos = permissao.recursos_permitidos or {}
                
                # Se recursos_permitidos estiver vazio, liberar acesso (permissão total)
                if not recursos:
                    registrar_log('portais.vendas', f"[DEBUG] Recursos vazio - acesso liberado", nivel='INFO')
                    return view_func(request, *args, **kwargs)
                
                # Verificar se recurso específico está permitido
                if not recursos.get(recurso, False):
                    registrar_log(
                        'portais.vendas',
                        f"Acesso negado - vendedor {vendedor.id} sem permissão para recurso: {recurso}",
                        nivel='WARNING'
                    )
                    return HttpResponseForbidden(
                        f'Acesso negado. Você não tem permissão para acessar: {recurso}'
                    )
                
                # Recurso permitido, executar view
                registrar_log('portais.vendas', f"[DEBUG] Acesso permitido ao recurso: {recurso}", nivel='INFO')
                return view_func(request, *args, **kwargs)
                
            except PortalPermissao.DoesNotExist:
                registrar_log('portais.vendas', f"Permissão não encontrada para vendedor: {vendedor.id}", nivel='ERROR')
                return HttpResponseForbidden('Permissão não configurada para este usuário')
        
        return wrapper
    return decorator
