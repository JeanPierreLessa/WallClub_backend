"""
Views para gestão de terminais POS no portal administrativo
Versão refatorada usando TerminaisService
"""
from django.shortcuts import render, redirect
from django.contrib import messages
from datetime import datetime
from portais.controle_acesso.decorators import require_admin_access
from portais.controle_acesso.services import ControleAcessoService
from .services_terminais import TerminaisService


@require_admin_access
def terminais_list(request):
    """Lista terminais POS com ações inline"""
    usuario_logado = request.portal_usuario
    
    # Processar ações POST (edição inline e encerramento)
    if request.method == 'POST':
        acao = request.POST.get('acao')
        usuario_nome = request.session.get('portal_usuario_nome', 'N/A')
        
        if acao == 'editar_datas':
            terminal_id = request.POST.get('terminal_id')
            inicio_str = request.POST.get('inicio', '').strip()
            fim_str = request.POST.get('fim', '').strip()
            
            if terminal_id:
                try:
                    inicio_date = datetime.strptime(inicio_str, '%Y-%m-%d').date() if inicio_str else None
                    fim_date = datetime.strptime(fim_str, '%Y-%m-%d').date() if fim_str else None
                    limpar_fim = (fim_str == '')
                    
                    resultado = TerminaisService.atualizar_datas_terminal(
                        terminal_id=int(terminal_id),
                        inicio=inicio_date,
                        fim=fim_date,
                        limpar_fim=limpar_fim,
                        usuario_editor=usuario_nome
                    )
                    
                    if resultado['sucesso']:
                        messages.success(request, resultado['mensagem'])
                    else:
                        messages.error(request, resultado['mensagem'])
                        
                except ValueError as e:
                    messages.error(request, f'Erro no formato de data: {str(e)}')
        
        elif acao == 'encerrar_agora':
            terminal_id = request.POST.get('terminal_id')
            if terminal_id:
                resultado = TerminaisService.encerrar_terminal(
                    terminal_id=int(terminal_id),
                    usuario_editor=usuario_nome
                )
                
                if resultado['sucesso']:
                    messages.success(request, resultado['mensagem'])
                else:
                    messages.error(request, resultado['mensagem'])
        
        return redirect('portais_admin:terminais_list')
    
    # GET: Listar terminais com filtro por canal
    nivel_usuario = ControleAcessoService.obter_nivel_portal(usuario_logado, 'admin')
    
    if nivel_usuario == 'admin_canal':
        canais_usuario = ControleAcessoService.obter_canais_usuario(usuario_logado)
    else:
        canais_usuario = None
    
    terminais = TerminaisService.listar_terminais(canais_usuario=canais_usuario)
    
    context = {
        'terminais': terminais,
    }
    
    return render(request, 'portais/admin/terminais_list.html', context)


@require_admin_access
def terminal_novo(request):
    """Cadastro de novo terminal"""
    usuario_logado = request.portal_usuario
    usuario_nome = request.session.get('portal_usuario_nome', 'N/A')
    
    if request.method == 'POST':
        loja_id = request.POST.get('loja_id', '').strip()
        terminal = request.POST.get('terminal', '').strip()
        idterminal = request.POST.get('idterminal', '').strip()
        endereco = request.POST.get('endereco', '').strip()
        contato = request.POST.get('contato', '').strip()
        inicio_str = request.POST.get('inicio', '').strip()
        fim_str = request.POST.get('fim', '').strip()
        
        try:
            inicio_date = datetime.strptime(inicio_str, '%Y-%m-%d').date() if inicio_str else None
            fim_date = datetime.strptime(fim_str, '%Y-%m-%d').date() if fim_str else None
            
            resultado = TerminaisService.criar_terminal(
                loja_id=int(loja_id) if loja_id else None,
                terminal=terminal,
                idterminal=idterminal,
                endereco=endereco,
                contato=contato,
                inicio=inicio_date,
                fim=fim_date,
                usuario_criador=usuario_nome
            )
            
            if resultado['sucesso']:
                messages.success(request, resultado['mensagem'])
                return redirect('portais_admin:terminais_list')
            else:
                messages.error(request, resultado['mensagem'])
                
        except ValueError as e:
            messages.error(request, f'Erro no formato de data: {str(e)}')
    
    # GET: Buscar lojas para o select - filtrar por canal se admin_canal
    nivel_usuario = ControleAcessoService.obter_nivel_portal(usuario_logado, 'admin')
    
    if nivel_usuario == 'admin_canal':
        canais_usuario = ControleAcessoService.obter_canais_usuario(usuario_logado)
    else:
        canais_usuario = None
    
    lojas = TerminaisService.obter_lojas_para_select(canais_usuario=canais_usuario)
    
    context = {
        'lojas': lojas,
    }
    
    return render(request, 'portais/admin/terminal_form.html', context)


@require_admin_access
def terminal_delete(request, pk):
    """Deletar terminal"""
    usuario_nome = request.session.get('portal_usuario_nome', 'N/A')
    
    if request.method == 'POST':
        resultado = TerminaisService.remover_terminal(
            terminal_id=pk,
            usuario_removedor=usuario_nome
        )
        
        if resultado['sucesso']:
            messages.success(request, resultado['mensagem'])
        else:
            messages.error(request, resultado['mensagem'])
    
    return redirect('portais_admin:terminais_list')
