"""
Views para gestão de terminais POS no portal administrativo
Versão refatorada usando TerminaisService
"""
from django.shortcuts import render, redirect
from django.contrib import messages
from datetime import datetime
from portais.controle_acesso.decorators import require_admin_access
from portais.controle_acesso.services import ControleAcessoService
from .services_terminais import TerminaisService, MODELOS_POS_OWN


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
                # Desativar na Own antes de encerrar localmente
                resultado_own = TerminaisService.desativar_equipamento_own(
                    terminal_id=int(terminal_id),
                    usuario=usuario_nome
                )
                if not resultado_own['sucesso']:
                    messages.warning(request, resultado_own['mensagem'])

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

        # Dados Own
        own_cadastrar = request.POST.get('own_cadastrar') == '1'
        own_modelo = request.POST.get('own_modelo', '').strip()
        own_contrato = request.POST.get('own_contrato', '').strip()

        try:
            inicio_date = datetime.strptime(inicio_str, '%Y-%m-%d').date() if inicio_str else None
            fim_date = datetime.strptime(fim_str, '%Y-%m-%d').date() if fim_str else None

            # Validar campos Own se checkbox marcado
            if own_cadastrar:
                if not own_modelo:
                    messages.error(request, 'Para cadastrar na Own, selecione o modelo do equipamento.')
                    # Re-render com dados preenchidos
                    nivel_usuario = ControleAcessoService.obter_nivel_portal(usuario_logado, 'admin')
                    canais_usuario = ControleAcessoService.obter_canais_usuario(usuario_logado) if nivel_usuario == 'admin_canal' else None
                    context = {
                        'lojas': TerminaisService.obter_lojas_para_select(canais_usuario=canais_usuario),
                        'lojas_own': TerminaisService.obter_lojas_own_para_select(),
                        'modelos_pos_own': MODELOS_POS_OWN,
                    }
                    return render(request, 'portais/admin/terminal_form.html', context)

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

                # Cadastrar na Own se solicitado
                if own_cadastrar and terminal:
                    terminal_obj = resultado.get('terminal')
                    resultado_own = TerminaisService.configurar_equipamento_own(
                        terminal_id=terminal_obj.id,
                        numero_serie=terminal,
                        modelo=own_modelo,
                        numero_contrato=own_contrato,
                        usuario=usuario_nome
                    )
                    if resultado_own['sucesso']:
                        messages.success(request, resultado_own['mensagem'])
                    else:
                        messages.warning(request, resultado_own['mensagem'])

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
        'lojas_own': TerminaisService.obter_lojas_own_para_select(),
        'modelos_pos_own': MODELOS_POS_OWN,
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


@require_admin_access
def terminais_historico(request):
    """Lista histórico de terminais inativos (somente leitura)"""
    usuario_logado = request.portal_usuario
    
    # Filtro por canal se necessário
    nivel_usuario = ControleAcessoService.obter_nivel_portal(usuario_logado, 'admin')
    
    if nivel_usuario == 'admin_canal':
        canais_usuario = ControleAcessoService.obter_canais_usuario(usuario_logado)
        canal_filter = f"AND c.id IN ({','.join(map(str, canais_usuario))})" if canais_usuario else "AND 1=0"
    else:
        canal_filter = ""
    
    # Query para buscar terminais inativos
    from django.db import connection
    query = f"""
        SELECT 
            t.id,
            t.loja_id,
            t.terminal,
            t.idterminal,
            t.endereco,
            t.contato,
            t.inicio,
            t.fim,
            l.razao_social as loja_nome,
            c.nome as canal_nome
        FROM terminais t
        LEFT JOIN loja l ON t.loja_id = l.id
        LEFT JOIN canal c ON l.canal_id = c.id
        WHERE t.fim IS NOT NULL AND t.fim <= NOW() {canal_filter}
        ORDER BY t.fim DESC, t.id DESC
    """
    
    with connection.cursor() as cursor:
        cursor.execute(query)
        terminais_inativos = cursor.fetchall()
    
    terminais = [{
        'id': t[0],
        'loja_id': t[1],
        'terminal': t[2],
        'idterminal': t[3],
        'endereco': t[4],
        'contato': t[5],
        'inicio': t[6],
        'fim': t[7],
        'loja_nome': t[8],
        'canal_nome': t[9]
    } for t in terminais_inativos]
    
    context = {
        'terminais': terminais,
    }
    
    return render(request, 'portais/admin/terminais_historico.html', context)
