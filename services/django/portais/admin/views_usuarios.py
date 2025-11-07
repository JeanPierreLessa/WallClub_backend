"""
Views para gestão de usuários no portal administrativo
Versão refatorada usando UsuarioService
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from portais.controle_acesso.decorators import require_admin_access
from portais.controle_acesso.models import PortalUsuario, PortalPermissao, PortalUsuarioAcesso
from portais.controle_acesso.services import ControleAcessoService, UsuarioService
from wallclub_core.utilitarios.log_control import registrar_log


@require_admin_access
def usuarios_list(request):
    """Lista usuários com filtros por canal"""
    usuario_logado = request.portal_usuario
    nivel_usuario = ControleAcessoService.obter_nivel_portal(usuario_logado, 'admin')

    # Tratar ações POST (resetar senha, remover usuário, etc)
    if request.method == 'POST':
        acao = request.POST.get('acao')
        usuario_id = request.POST.get('usuario_id')
        
        if acao == 'resetar_senha' and usuario_id:
            try:
                resultado = UsuarioService.resetar_senha_usuario(
                    usuario_id=usuario_id,
                    portal_destino='admin'
                )
                
                if resultado['sucesso']:
                    messages.success(request, resultado['mensagem'])
                    registrar_log('portais.admin', f'Senha resetada para usuário ID {usuario_id} por {usuario_logado.email}')
                else:
                    messages.error(request, resultado['mensagem'])
                    registrar_log('portais.admin', f'Erro ao resetar senha: {resultado["mensagem"]}', nivel='ERROR')
            except Exception as e:
                messages.error(request, f'Erro ao resetar senha: {str(e)}')
                registrar_log('portais.admin', f'Erro ao resetar senha: {str(e)}', nivel='ERROR')
            
            return redirect('portais_admin:usuarios_list')
        
        elif acao == 'remover_usuario' and usuario_id:
            resultado = UsuarioService.remover_usuario(
                usuario_id=usuario_id,
                usuario_logado_id=usuario_logado.id
            )
            
            if resultado['sucesso']:
                messages.success(request, resultado['mensagem'])
            else:
                messages.error(request, resultado['mensagem'])
            
            return redirect('portais_admin:usuarios_list')

    # GET: Buscar usuários filtrados por nível de acesso
    usuarios = UsuarioService.buscar_usuarios(
        usuario_logado=usuario_logado
    )

    context = {
        'usuarios': usuarios,
        'nivel_usuario': nivel_usuario,
        'is_admin_canal': (nivel_usuario == 'admin_canal'),
        'is_admin_total': (nivel_usuario == 'admin_total'),
    }

    return render(request, 'portais/admin/usuarios_list.html', context)


@require_admin_access
def usuario_form(request, pk=None):
    """Criar ou editar usuário"""
    usuario_logado = request.portal_usuario
    nivel_usuario = ControleAcessoService.obter_nivel_portal(usuario_logado, 'admin')

    usuario = None
    if pk:
        try:
            usuario = PortalUsuario.objects.get(pk=pk)
        except PortalUsuario.DoesNotExist:
            messages.error(request, 'Usuário não encontrado.')
            return redirect('portais_admin:usuarios_list')

    if request.method == 'POST':
        try:
            # Extrair dados do formulário
            nome = request.POST.get('nome', '').strip()
            email = request.POST.get('email', '').strip()
            acessos_selecionados = request.POST.getlist('acessos')

            # Tipos e referências por portal
            tipo_portal = request.POST.get('tipo_portal', '')
            tipo_lojista = request.POST.get('tipo_lojista', '')
            tipo_recorrencia = request.POST.get('tipo_recorrencia', '')
            tipo_vendas = request.POST.get('tipo_vendas', '')

            referencia_portal = request.POST.get('referencia_portal')
            referencia_lojista = request.POST.get('referencia_lojista')
            referencia_recorrencia = request.POST.get('referencia_recorrencia')
            referencia_vendas = request.POST.get('referencia_vendas')
            
            # Capturar recursos permitidos para portal vendas
            recurso_checkout = request.POST.get('recurso_checkout') == '1'
            recurso_recorrencia = request.POST.get('recurso_recorrencia') == '1'

            # Validações básicas
            if not nome or not email:
                messages.error(request, 'Nome e email são obrigatórios')
                return render(request, 'portais/admin/usuario_form.html', {
                    'usuario': usuario, 'nome': nome, 'email': email, 'is_edit': bool(pk)
                })

            # RESTRIÇÃO: admin_superusuario não pode criar usuários admin
            if nivel_usuario == 'admin_superusuario' and 'portal' in acessos_selecionados:
                messages.error(request, 'Você não tem permissão para criar usuários administrativos.')
                return render(request, 'portais/admin/usuario_form.html', {
                    'usuario': usuario, 'nome': nome, 'email': email, 'is_edit': bool(pk)
                })

            # RESTRIÇÃO: admin_canal só pode criar usuários lojistas
            if nivel_usuario == 'admin_canal':
                if 'portal' in acessos_selecionados:
                    messages.error(request, 'Você só pode criar usuários lojistas.')
                    return render(request, 'portais/admin/usuario_form.html', {
                        'usuario': usuario, 'nome': nome, 'email': email, 'is_edit': bool(pk),
                        'is_admin_canal': True
                    })

            if not acessos_selecionados:
                messages.error(request, 'Selecione pelo menos um portal de acesso.')
                return render(request, 'portais/admin/usuario_form.html', {
                    'usuario': usuario, 'nome': nome, 'email': email, 'is_edit': bool(pk)
                })

            # Usar UsuarioService para criar ou atualizar
            if usuario:
                resultado = UsuarioService.atualizar_usuario(
                    usuario_id=usuario.id,
                    nome=nome,
                    email=email,
                    acessos_selecionados=acessos_selecionados,
                    tipo_portal=tipo_portal or None,
                    tipo_lojista=tipo_lojista or None,
                    tipo_recorrencia=tipo_recorrencia or None,
                    tipo_vendas=tipo_vendas or None,
                    referencia_portal=referencia_portal or None,
                    referencia_lojista=referencia_lojista or None,
                    referencia_recorrencia=referencia_recorrencia or None,
                    referencia_vendas=referencia_vendas or None,
                    recurso_checkout=recurso_checkout,
                    recurso_recorrencia=recurso_recorrencia
                )
            else:
                resultado = UsuarioService.criar_usuario(
                    nome=nome,
                    email=email,
                    acessos_selecionados=acessos_selecionados,
                    usuario_criador=usuario_logado,
                    tipo_portal=tipo_portal or None,
                    tipo_lojista=tipo_lojista or None,
                    tipo_recorrencia=tipo_recorrencia or None,
                    tipo_vendas=tipo_vendas or None,
                    referencia_portal=referencia_portal or None,
                    referencia_lojista=referencia_lojista or None,
                    referencia_recorrencia=referencia_recorrencia or None,
                    referencia_vendas=referencia_vendas or None,
                    recurso_checkout=recurso_checkout,
                    recurso_recorrencia=recurso_recorrencia
                )

            if resultado['sucesso']:
                messages.success(request, resultado['mensagem'])
                return redirect('portais_admin:usuarios_list')
            else:
                messages.error(request, resultado.get('mensagem', 'Erro ao processar usuário'))
                return render(request, 'portais/admin/usuario_form.html', {
                    'usuario': usuario, 'nome': nome, 'email': email, 'is_edit': bool(pk)
                })

        except Exception as e:
            registrar_log('portais.admin', f'USUARIOS - Erro ao salvar - Erro: {str(e)}', nivel='ERROR')
            messages.error(request, f'Erro ao salvar usuário: {str(e)}')
            return render(request, 'portais/admin/usuario_form.html', {
                'usuario': usuario,
                'nome': nome if 'nome' in locals() else '',
                'email': email if 'email' in locals() else '',
                'is_edit': bool(pk)
            })

    # GET: Carregar permissões e acessos existentes para edição
    permissoes_atuais = {}
    acessos_atuais = {}
    vendas_recursos = {}

    if usuario:
        permissoes = PortalPermissao.objects.filter(usuario=usuario)
        for permissao in permissoes:
            permissoes_atuais[permissao.portal] = permissao.nivel_acesso
            
            # Carregar recursos_permitidos do portal vendas
            if permissao.portal == 'vendas' and permissao.recursos_permitidos:
                vendas_recursos = permissao.recursos_permitidos

        acessos = PortalUsuarioAcesso.objects.filter(usuario=usuario, ativo=True)
        for acesso in acessos:
            if acesso.portal not in acessos_atuais:
                acessos_atuais[acesso.portal] = {}
            acessos_atuais[acesso.portal][acesso.entidade_tipo] = acesso.entidade_id
    
    # Preparar recursos para o template
    permissoes_atuais['vendas_recursos'] = vendas_recursos

    is_admin_canal = (nivel_usuario == 'admin_canal')
    is_admin_superusuario = (nivel_usuario == 'admin_superusuario')

    context = {
        'usuario': usuario,
        'is_edit': bool(usuario),
        'permissoes_atuais': permissoes_atuais,
        'acessos_atuais': acessos_atuais,
        'is_admin_canal': is_admin_canal,
        'is_admin_superusuario': is_admin_superusuario
    }

    return render(request, 'portais/admin/usuario_form.html', context)


@require_admin_access
def usuario_delete(request, pk):
    """Deletar usuário"""
    usuario_logado = request.portal_usuario

    if request.method == 'POST':
        resultado = UsuarioService.remover_usuario(
            usuario_id=pk,
            usuario_logado_id=usuario_logado.id
        )

        if resultado['sucesso']:
            messages.success(request, resultado['mensagem'])
        else:
            messages.error(request, resultado['mensagem'])

        return redirect('portais_admin:usuarios_list')

    # GET: Mostrar confirmação
    usuario = get_object_or_404(PortalUsuario, id=pk)

    context = {
        'usuario': usuario,
    }

    return render(request, 'portais/admin/usuario_delete.html', context)


@require_admin_access
def primeiro_acesso(request, token):
    """Processar primeiro acesso do usuário"""
    if request.method == 'POST':
        nova_senha = request.POST.get('senha', '').strip()
        confirmar_senha = request.POST.get('confirmar_senha', '').strip()

        if not nova_senha or not confirmar_senha:
            messages.error(request, 'Todos os campos são obrigatórios')
            return render(request, 'portais/admin/primeiro_acesso.html', {'token': token})

        if nova_senha != confirmar_senha:
            messages.error(request, 'As senhas não coincidem')
            return render(request, 'portais/admin/primeiro_acesso.html', {'token': token})

        resultado = UsuarioService.processar_definicao_senha(
            token=token,
            nova_senha=nova_senha
        )

        if resultado['sucesso']:
            messages.success(request, resultado['mensagem'])
            return redirect('portais_admin:login')
        else:
            messages.error(request, resultado['mensagem'])
            return render(request, 'portais/admin/primeiro_acesso.html', {'token': token})

    # GET: Validar token
    resultado = UsuarioService.validar_token_primeiro_acesso(token)

    if not resultado['sucesso']:
        messages.error(request, resultado['mensagem'])
        return redirect('portais_admin:login')

    context = {
        'token': token,
        'usuario': resultado.get('usuario')
    }

    return render(request, 'portais/admin/primeiro_acesso.html', context)
