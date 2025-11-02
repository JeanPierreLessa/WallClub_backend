"""Context processors para controle de acesso"""
from .models import PortalUsuario
from .services import ControleAcessoService


def usuario_canal_context(request):
    """
    Context processor que adiciona informações do canal do usuário logado
    para exibição do logo correto no header
    """
    context = {
        'usuario_canal_id': 1,  # Padrão
        'usuario_logo_filename': '1.png'  # Logo padrão
    }
    
    # Verificar se há usuário logado no portal admin
    usuario_id = request.session.get('portal_usuario_id')
    if usuario_id:
        try:
            usuario = PortalUsuario.objects.get(id=usuario_id)
            canal_id = ControleAcessoService.obter_canal_principal_usuario(usuario)
            context.update({
                'usuario_canal_id': canal_id,
                'usuario_logo_filename': f'{canal_id}.png'
            })
        except PortalUsuario.DoesNotExist:
            pass
    
    # Verificar se há usuário logado no portal lojista
    lojista_usuario_id = request.session.get('lojista_usuario_id')
    if lojista_usuario_id:
        try:
            usuario = PortalUsuario.objects.get(id=lojista_usuario_id)
            canal_id = ControleAcessoService.obter_canal_principal_usuario(usuario)
            context.update({
                'usuario_canal_id': canal_id,
                'usuario_logo_filename': f'{canal_id}.png'
            })
        except PortalUsuario.DoesNotExist:
            pass
    
    return context
