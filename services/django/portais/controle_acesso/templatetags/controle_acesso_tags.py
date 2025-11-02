"""
Template tags para controle de acesso
Permite verificar permissões diretamente nos templates
"""

from django import template
from portais.controle_acesso import MatrizControleAcesso

register = template.Library()


@register.simple_tag(takes_context=True)
def tem_acesso(context, funcionalidade):
    """
    Verifica se usuário logado tem acesso a uma funcionalidade
    
    Uso no template:
    {% tem_acesso 'usuarios_create' as pode_criar_usuario %}
    {% if pode_criar_usuario %}
        <button>Criar Usuário</button>
    {% endif %}
    """
    from ..services import ControleAcessoService
    from ..controle_acesso import MatrizControleAcesso
    
    request = context.get('request')
    if not request or not hasattr(request, 'portal_usuario'):
        return False
    
    usuario = request.portal_usuario
    portal = getattr(request, 'portal_atual', 'admin')
    
    # Obter nível do usuário e verificar acesso à funcionalidade
    nivel_usuario = ControleAcessoService.obter_nivel_portal(usuario, portal)
    return MatrizControleAcesso.usuario_tem_acesso(nivel_usuario, funcionalidade)


@register.simple_tag(takes_context=True)
def nivel_usuario(context):
    """
    Retorna o nível de acesso do usuário logado
    
    Uso no template:
    {% nivel_usuario as nivel %}
    {% if nivel == 'admin_canal' %}
        <div class="admin-canal-panel">...</div>
    {% endif %}
    """
    from ..services import ControleAcessoService
    
    request = context.get('request')
    if not request or not hasattr(request, 'portal_usuario'):
        return 'negado'
    
    usuario = request.portal_usuario
    portal = getattr(request, 'portal_atual', 'admin')
    
    return ControleAcessoService.obter_nivel_portal(usuario, portal)


@register.inclusion_tag('portais/controle_acesso/templates/botoes_acesso.html', takes_context=True)
def botoes_funcionalidade(context, funcionalidades):
    """
    Renderiza botões baseado nas permissões do usuário
    
    Uso no template:
    {% botoes_funcionalidade 'usuarios,transacoes,parametros' %}
    """
    from ..services import ControleAcessoService
    
    request = context.get('request')
    botoes_permitidos = []
    
    if request and hasattr(request, 'portal_usuario'):
        usuario = request.portal_usuario
        portal = getattr(request, 'portal_atual', 'admin')
        lista_funcionalidades = funcionalidades.split(',')
        
        for func in lista_funcionalidades:
            func = func.strip()
            if ControleAcessoService.usuario_pode_acessar_secao(usuario, portal, func):
                botoes_permitidos.append(func)
    
    return {
        'botoes_permitidos': botoes_permitidos,
        'request': request
    }


@register.simple_tag(takes_context=True)
def tem_secao_permitida(context, secao):
    """
    Verifica se usuário tem acesso a uma seção específica
    
    Uso no template:
    {% tem_secao_permitida 'pagamentos' as pode_pagamentos %}
    {% if pode_pagamentos %}
        <li>Link Pagamentos</li>
    {% endif %}
    """
    from ..services import ControleAcessoService
    
    request = context.get('request')
    if not request or not hasattr(request, 'portal_usuario'):
        return False
    
    usuario = request.portal_usuario
    portal = getattr(request, 'portal_atual', 'admin')
    
    # Obter nível do usuário
    nivel_usuario = ControleAcessoService.obter_nivel_portal(usuario, portal)
    
    # Verificar se seção está permitida para este nível
    from ..services import ControleAcessoService
    secoes_permitidas = ControleAcessoService.SECOES_POR_NIVEL.get(nivel_usuario, [])
    
    return secao in secoes_permitidas


@register.filter
def pode_acessar(usuario, funcionalidade):
    """
    Filter para verificar acesso de um usuário específico
    
    Uso no template:
    {% if usuario|pode_acessar:'usuarios_edit' %}
        <a href="...">Editar</a>
    {% endif %}
    """
    if not usuario:
        return False
    
    # Assume portal 'admin' como padrão para este filtro
    permissoes = usuario.permissoes.filter(portal='admin')
    if not permissoes.exists():
        return False
    
    # Se tem permissão admin, libera todas as funcionalidades
    if permissoes.filter(nivel_acesso='admin').exists():
        return True
    
    # Verifica se funcionalidade está nos recursos permitidos
    for permissao in permissoes:
        if permissao.recursos_permitidos and funcionalidade in permissao.recursos_permitidos:
            return True
    
    return False


@register.filter
def nivel_portal(usuario, portal):
    """
    Filter para obter nível do usuário no portal
    
    Uso no template:
    {% if request.portal_usuario|nivel_portal:'admin' == 'admin_total' %}
        <a href="...">Novo Canal</a>
    {% endif %}
    """
    if not usuario:
        return 'negado'
    
    from ..services import ControleAcessoService
    return ControleAcessoService.obter_nivel_portal(usuario, portal)


@register.simple_tag(takes_context=True)
def tem_permissao_recurso(context, recurso):
    """
    Verifica se usuário tem permissão para um recurso específico (checkout, recorrencia, etc)
    Busca em recursos_permitidos do PortalPermissao
    
    Uso no template:
    {% tem_permissao_recurso 'recorrencia' as pode_recorrencia %}
    {% if pode_recorrencia %}
        <li>Links de recorrência...</li>
    {% endif %}
    """
    request = context.get('request')
    if not request:
        return False
    
    # Portal vendas usa sessão
    vendedor_id = request.session.get('vendedor_id')
    if not vendedor_id:
        return False
    
    try:
        from ..models import PortalUsuario, PortalPermissao
        usuario = PortalUsuario.objects.get(id=vendedor_id)
        
        # Buscar permissões do portal vendas
        permissoes = PortalPermissao.objects.filter(
            usuario=usuario,
            portal='vendas'
        )
        
        for permissao in permissoes:
            recursos = permissao.recursos_permitidos or {}
            if recursos.get(recurso) is True:
                return True
        
        return False
    except:
        return False
