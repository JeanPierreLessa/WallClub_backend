from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q, Count
from datetime import date
from posp2.models import TerminalOperador, TerminalOperadorPos, TerminalOperadorLog, Terminal
from portais.controle_acesso.models import PortalUsuario
from portais.controle_acesso.filtros import FiltrosAcessoService


def listar_operadores(request):
    """
    Tela 1: Lista operadores da loja (respeitando hierarquia)
    """
    # Verificar autenticação
    if not request.session.get('lojista_authenticated'):
        return redirect('lojista:login')
    
    # Obter lojas acessíveis ao usuário
    usuario_id = request.session.get('lojista_usuario_id')
    try:
        usuario = PortalUsuario.objects.get(id=usuario_id)
        lojas_acessiveis = FiltrosAcessoService.obter_lojas_acessiveis(usuario)
        lojas_ids = [loja['id'] for loja in lojas_acessiveis]
    except PortalUsuario.DoesNotExist:
        messages.error(request, 'Usuário não encontrado')
        return redirect('lojista:home')
    
    # Filtros
    busca = request.GET.get('busca', '')
    status = request.GET.get('status', 'todos')  # todos, ativos, inativos
    
    operadores = TerminalOperador.objects.filter(loja_id__in=lojas_ids)
    
    if busca:
        operadores = operadores.filter(
            Q(operador__icontains=busca) |
            Q(nome__icontains=busca) |
            Q(cpf__icontains=busca)
        )
    
    # Anotar quantidade de vínculos ativos
    operadores = operadores.annotate(
        total_vinculos_ativos=Count(
            'vinculos',
            filter=Q(vinculos__ativo=True)
        )
    )
    
    if status == 'ativos':
        operadores = operadores.filter(total_vinculos_ativos__gt=0)
    elif status == 'inativos':
        operadores = operadores.filter(total_vinculos_ativos=0)
    
    operadores = operadores.order_by('nome')
    
    context = {
        'operadores': operadores,
        'busca': busca,
        'status': status,
        'current_page': 'operadores',
    }
    
    return render(request, 'portais/lojista/operadores/listar.html', context)


def criar_operador(request):
    """
    Cria novo operador (respeitando hierarquia)
    """
    # Verificar autenticação
    if not request.session.get('lojista_authenticated'):
        return redirect('lojista:login')
    
    if request.method == 'POST':
        # Obter lojas acessíveis
        usuario_id = request.session.get('lojista_usuario_id')
        try:
            usuario = PortalUsuario.objects.get(id=usuario_id)
            lojas_acessiveis = FiltrosAcessoService.obter_lojas_acessiveis(usuario)
            lojas_ids = [loja['id'] for loja in lojas_acessiveis]
        except PortalUsuario.DoesNotExist:
            messages.error(request, 'Usuário não encontrado')
            return redirect('lojista:home')
        
        # Validar loja selecionada
        loja_id = request.POST.get('loja_id')
        if not loja_id or int(loja_id) not in lojas_ids:
            messages.error(request, 'Loja não permitida')
            return redirect('lojista:criar_operador')
        
        # Validar campos obrigatórios
        operador = request.POST.get('operador', '').strip()
        nome = request.POST.get('nome', '').strip()
        cpf = request.POST.get('cpf', '').replace('.', '').replace('-', '')
        
        if not operador or not nome or not cpf:
            messages.error(request, 'Preencha todos os campos obrigatórios')
            return redirect('lojista:criar_operador')
        
        # Verificar se operador já existe
        if TerminalOperador.objects.filter(operador=operador).exists():
            messages.error(request, f'Código de operador {operador} já existe')
            return redirect('lojista:criar_operador')
        
        # Verificar se CPF já existe na loja
        if TerminalOperador.objects.filter(loja_id=loja_id, cpf=cpf).exists():
            messages.error(request, f'CPF {cpf} já cadastrado nesta loja')
            return redirect('lojista:criar_operador')
        
        # Criar operador
        novo_operador = TerminalOperador.objects.create(
            loja_id=loja_id,
            operador=operador,
            nome=nome,
            cpf=cpf,
            identificacao_loja=request.POST.get('identificacao_loja', ''),
            matricula=request.POST.get('matricula', ''),
            telefone=request.POST.get('telefone', ''),
            email=request.POST.get('email', ''),
            endereco_loja=request.POST.get('endereco_loja', ''),
        )
        
        messages.success(request, f'Operador {novo_operador.nome} criado com sucesso')
        return redirect('lojista:listar_operadores')
    
    # GET - listar lojas disponíveis
    usuario_id = request.session.get('lojista_usuario_id')
    try:
        usuario = PortalUsuario.objects.get(id=usuario_id)
        lojas_acessiveis = FiltrosAcessoService.obter_lojas_acessiveis(usuario)
    except PortalUsuario.DoesNotExist:
        lojas_acessiveis = []
    
    context = {
        'lojas_acessiveis': lojas_acessiveis,
        'current_page': 'operadores',
    }
    
    return render(request, 'portais/lojista/operadores/criar.html', context)


def editar_operador(request, operador_id):
    """
    Edita dados do operador (respeitando hierarquia)
    """
    # Verificar autenticação
    if not request.session.get('lojista_authenticated'):
        return redirect('lojista:login')
    
    # Verificar acesso
    usuario_id = request.session.get('lojista_usuario_id')
    try:
        usuario = PortalUsuario.objects.get(id=usuario_id)
        lojas_acessiveis = FiltrosAcessoService.obter_lojas_acessiveis(usuario)
        lojas_ids = [loja['id'] for loja in lojas_acessiveis]
    except PortalUsuario.DoesNotExist:
        messages.error(request, 'Usuário não encontrado')
        return redirect('lojista:home')
    
    operador = get_object_or_404(TerminalOperador, id=operador_id, loja_id__in=lojas_ids)
    
    if request.method == 'POST':
        operador.nome = request.POST.get('nome', '').strip()
        operador.identificacao_loja = request.POST.get('identificacao_loja', '')
        operador.matricula = request.POST.get('matricula', '')
        operador.telefone = request.POST.get('telefone', '')
        operador.email = request.POST.get('email', '')
        operador.endereco_loja = request.POST.get('endereco_loja', '')
        operador.save()
        
        messages.success(request, f'Operador {operador.nome} atualizado com sucesso')
        return redirect('lojista:listar_operadores')
    
    context = {
        'operador': operador,
        'current_page': 'operadores',
    }
    
    return render(request, 'portais/lojista/operadores/editar.html', context)


def visualizar_operador(request, operador_id):
    """
    Visualiza detalhes e histórico de vínculos do operador (respeitando hierarquia)
    """
    # Verificar autenticação
    if not request.session.get('lojista_authenticated'):
        return redirect('lojista:login')
    
    # Verificar acesso
    usuario_id = request.session.get('lojista_usuario_id')
    try:
        usuario = PortalUsuario.objects.get(id=usuario_id)
        lojas_acessiveis = FiltrosAcessoService.obter_lojas_acessiveis(usuario)
        lojas_ids = [loja['id'] for loja in lojas_acessiveis]
    except PortalUsuario.DoesNotExist:
        messages.error(request, 'Usuário não encontrado')
        return redirect('lojista:home')
    
    operador = get_object_or_404(TerminalOperador, id=operador_id, loja_id__in=lojas_ids)
    
    vinculos_ativos = operador.vinculos_ativos()
    vinculos_inativos = operador.vinculos_inativos()
    
    context = {
        'operador': operador,
        'vinculos_ativos': vinculos_ativos,
        'vinculos_inativos': vinculos_inativos,
        'current_page': 'operadores',
    }
    
    return render(request, 'portais/lojista/operadores/visualizar.html', context)


def listar_vinculos(request):
    """
    Tela 2: Lista terminais e seus operadores vinculados (respeitando hierarquia)
    """
    # Verificar autenticação
    if not request.session.get('lojista_authenticated'):
        return redirect('lojista:login')
    
    # Obter lojas acessíveis
    usuario_id = request.session.get('lojista_usuario_id')
    try:
        usuario = PortalUsuario.objects.get(id=usuario_id)
        lojas_acessiveis = FiltrosAcessoService.obter_lojas_acessiveis(usuario)
        lojas_ids = [loja['id'] for loja in lojas_acessiveis]
    except PortalUsuario.DoesNotExist:
        messages.error(request, 'Usuário não encontrado')
        return redirect('lojista:home')
    
    terminais = Terminal.objects.filter(loja_id__in=lojas_ids).prefetch_related(
        'operadores_vinculados__operador'
    ).order_by('terminal')
    
    # Para cada terminal, separar vínculos ativos e inativos
    terminais_data = []
    for terminal in terminais:
        vinculos_ativos = terminal.operadores_vinculados.filter(
            ativo=True
        ).select_related('operador')
        
        terminais_data.append({
            'terminal': terminal,
            'vinculos_ativos': vinculos_ativos,
        })
    
    # Operadores disponíveis para vincular
    operadores_disponiveis = TerminalOperador.objects.filter(loja_id__in=lojas_ids).order_by('nome')
    
    context = {
        'terminais_data': terminais_data,
        'operadores_disponiveis': operadores_disponiveis,
        'current_page': 'operadores',
    }
    
    return render(request, 'portais/lojista/operadores/vinculos.html', context)


def criar_vinculo(request):
    """
    Cria novo vínculo operador-terminal (respeitando hierarquia)
    """
    # Verificar autenticação
    if not request.session.get('lojista_authenticated'):
        return redirect('lojista:login')
    
    if request.method == 'POST':
        # Verificar acesso
        usuario_id = request.session.get('lojista_usuario_id')
        try:
            usuario = PortalUsuario.objects.get(id=usuario_id)
            lojas_acessiveis = FiltrosAcessoService.obter_lojas_acessiveis(usuario)
            lojas_ids = [loja['id'] for loja in lojas_acessiveis]
        except PortalUsuario.DoesNotExist:
            messages.error(request, 'Usuário não encontrado')
            return redirect('lojista:home')
        
        terminal_id = request.POST.get('terminal_id')
        operador_id = request.POST.get('operador_id')
        
        if not terminal_id or not operador_id:
            messages.error(request, 'Preencha todos os campos obrigatórios')
            return redirect('lojista:listar_vinculos')
        
        terminal = get_object_or_404(Terminal, id=terminal_id, loja_id__in=lojas_ids)
        operador = get_object_or_404(TerminalOperador, id=operador_id, loja_id__in=lojas_ids)
        
        # Verificar se já existe vínculo
        vinculo_existente = TerminalOperadorPos.objects.filter(
            terminal=terminal,
            operador=operador
        ).first()
        
        if vinculo_existente:
            if vinculo_existente.ativo:
                messages.error(request, f'Operador {operador.nome} já está vinculado ao terminal {terminal.terminal}')
            else:
                # Reativar vínculo existente
                vinculo_existente.ativar(usuario=request.user)
                messages.success(request, f'Vínculo reativado: {operador.nome} → Terminal {terminal.terminal}')
            return redirect('lojista:listar_vinculos')
        
        # Criar novo vínculo
        vinculo = TerminalOperadorPos.objects.create(
            terminal=terminal,
            operador=operador,
            ativo=True
        )
        
        # Log gerado automaticamente pelo método create (ativo=True por padrão)
        TerminalOperadorLog.objects.create(
            vinculo=vinculo,
            acao='ATIVADO',
            usuario_id=request.user.id,
            motivo='Vínculo criado via portal'
        )
        
        messages.success(request, f'Operador {operador.nome} vinculado ao terminal {terminal.terminal}')
        return redirect('lojista:listar_vinculos')
    
    return redirect('lojista:listar_vinculos')


def desativar_vinculo(request, vinculo_id):
    """
    Desativa vínculo (respeitando hierarquia)
    """
    # Verificar autenticação
    if not request.session.get('lojista_authenticated'):
        return redirect('lojista:login')
    
    # Verificar acesso
    usuario_id = request.session.get('lojista_usuario_id')
    try:
        usuario = PortalUsuario.objects.get(id=usuario_id)
        lojas_acessiveis = FiltrosAcessoService.obter_lojas_acessiveis(usuario)
        lojas_ids = [loja['id'] for loja in lojas_acessiveis]
    except PortalUsuario.DoesNotExist:
        messages.error(request, 'Usuário não encontrado')
        return redirect('lojista:home')
    
    vinculo = get_object_or_404(TerminalOperadorPos, id=vinculo_id, terminal__loja_id__in=lojas_ids)
    
    if request.method == 'POST':
        motivo = request.POST.get('motivo', '')
        vinculo.desativar(usuario=request.user, motivo=motivo)
        
        messages.success(request, f'Vínculo desativado: {vinculo.operador.nome} → Terminal {vinculo.terminal.terminal}')
        return redirect('lojista:listar_vinculos')
    
    context = {
        'vinculo': vinculo,
        'current_page': 'operadores',
    }
    
    return render(request, 'portais/lojista/operadores/desativar_vinculo.html', context)


def ativar_vinculo(request, vinculo_id):
    """
    Ativa vínculo (respeitando hierarquia)
    """
    # Verificar autenticação
    if not request.session.get('lojista_authenticated'):
        return redirect('lojista:login')
    
    # Verificar acesso
    usuario_id = request.session.get('lojista_usuario_id')
    try:
        usuario = PortalUsuario.objects.get(id=usuario_id)
        lojas_acessiveis = FiltrosAcessoService.obter_lojas_acessiveis(usuario)
        lojas_ids = [loja['id'] for loja in lojas_acessiveis]
    except PortalUsuario.DoesNotExist:
        messages.error(request, 'Usuário não encontrado')
        return redirect('lojista:home')
    
    vinculo = get_object_or_404(TerminalOperadorPos, id=vinculo_id, terminal__loja_id__in=lojas_ids)
    
    if request.method == 'POST':
        motivo = request.POST.get('motivo', '')
        vinculo.ativar(usuario=request.user, motivo=motivo)
        
        messages.success(request, f'Vínculo ativado: {vinculo.operador.nome} → Terminal {vinculo.terminal.terminal}')
        return redirect('lojista:listar_vinculos')
    
    return redirect('lojista:listar_vinculos')


def visualizar_log_vinculo(request, vinculo_id):
    """
    Visualiza log de ativações/desativações do vínculo (respeitando hierarquia)
    """
    # Verificar autenticação
    if not request.session.get('lojista_authenticated'):
        return redirect('lojista:login')
    
    # Verificar acesso
    usuario_id = request.session.get('lojista_usuario_id')
    try:
        usuario = PortalUsuario.objects.get(id=usuario_id)
        lojas_acessiveis = FiltrosAcessoService.obter_lojas_acessiveis(usuario)
        lojas_ids = [loja['id'] for loja in lojas_acessiveis]
    except PortalUsuario.DoesNotExist:
        messages.error(request, 'Usuário não encontrado')
        return redirect('lojista:home')
    
    vinculo = get_object_or_404(TerminalOperadorPos, id=vinculo_id, terminal__loja_id__in=lojas_ids)
    logs = vinculo.logs.all().order_by('-created_at')
    
    context = {
        'vinculo': vinculo,
        'logs': logs,
        'current_page': 'operadores',
    }
    
    return render(request, 'portais/lojista/operadores/log_vinculo.html', context)
