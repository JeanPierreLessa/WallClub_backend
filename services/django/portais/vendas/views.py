"""
Views do Portal de Vendas (Checkout)
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib import messages
from django.db import transaction
from django.db import models
from django.core.cache import cache
from django.apps import apps
from wallclub_core.utilitarios.log_control import registrar_log
from .decorators import requer_checkout_vendedor, vendedor_pode_acessar_loja
from wallclub_core.estr_organizacional.loja import Loja
from wallclub_core.integracoes.messages_template_service import MessagesTemplateService
from wallclub_core.integracoes.whatsapp_service import WhatsAppService
from wallclub_core.integracoes.sms_service import enviar_sms


# ============================================================================
# AUTENTICAÇÃO
# ============================================================================

@require_http_methods(["GET", "POST"])
def login_view(request):
    """Login do portal de vendas"""
    if request.method == 'POST':
        email = request.POST.get('email')
        senha = request.POST.get('senha')
        
        from .services import CheckoutVendasService
        
        resultado = CheckoutVendasService.autenticar_vendedor(email, senha)
        
        if resultado['sucesso']:
            # Criar sessão
            usuario = resultado['usuario']
            request.session['vendas_authenticated'] = True
            request.session['vendedor_id'] = usuario['id']
            request.session['vendedor_nome'] = usuario['nome']
            request.session['vendedor_email'] = usuario['email']
            
            messages.success(request, resultado['mensagem'])
            return redirect('vendas:dashboard')
        else:
            messages.error(request, resultado['mensagem'])
            return render(request, 'vendas/login.html')
    
    # GET - exibir formulário
    return render(request, 'vendas/login.html')


def logout_view(request):
    """Logout do portal"""
    vendedor_nome = request.session.get('vendedor_nome', 'Usuário')
    
    request.session.flush()
    
    registrar_log('portais.vendas', f"Logout: {vendedor_nome}")
    messages.info(request, 'Logout realizado com sucesso')
    
    return redirect('vendas:login')


# ============================================================================
# DASHBOARD
# ============================================================================

@requer_checkout_vendedor
def dashboard(request):
    """Dashboard principal do portal de vendas"""
    from .services import CheckoutVendasService
    
    # Buscar vendedor da sessão
    vendedor = getattr(request, 'vendedor', None)
    if not vendedor and request.session.get('vendedor_id'):
        from portais.controle_acesso.models import PortalUsuario
        try:
            vendedor = PortalUsuario.objects.get(id=request.session.get('vendedor_id'))
        except:
            vendedor = None
    
    # Buscar lojas e estatísticas via service
    lojas = CheckoutVendasService.obter_lojas_vendedor(vendedor.id)
    estatisticas = CheckoutVendasService.obter_estatisticas_dashboard(vendedor.id)
    
    context = {
        'vendedor': vendedor,
        'lojas': lojas,
        **estatisticas
    }
    
    return render(request, 'vendas/dashboard.html', context)


# ============================================================================
# GESTÃO DE CLIENTES
# ============================================================================

@requer_checkout_vendedor
@require_http_methods(["GET", "POST"])
def cliente_form(request):
    """Formulário de cadastro de cliente"""
    from .services import CheckoutVendasService
    
    vendedor = request.vendedor
    lojas = CheckoutVendasService.obter_lojas_vendedor(vendedor.id)
    
    if request.method == 'POST':
        try:
            loja_id = int(request.POST.get('loja_id'))
            tipo_documento = request.POST.get('tipo_documento')
            
            dados = {
                'nome': request.POST.get('nome'),
                'email': request.POST.get('email'),
                'endereco': request.POST.get('endereco'),
                'cep': request.POST.get('cep', '').replace('-', ''),
            }
            
            if tipo_documento == 'cpf':
                dados['cpf'] = request.POST.get('cpf', '').replace('.', '').replace('-', '')
            else:
                dados['cnpj'] = request.POST.get('cnpj', '').replace('.', '').replace('/', '').replace('-', '')
            
            # Verificar se cliente já existe antes de criar
            from checkout.services import ClienteService
            cpf_limpo = dados.get('cpf', '')
            cnpj_limpo = dados.get('cnpj', '')
            
            cliente_existente = ClienteService.buscar_cliente(
                loja_id=loja_id,
                cpf=cpf_limpo if cpf_limpo else None,
                cnpj=cnpj_limpo if cnpj_limpo else None
            )
            
            if cliente_existente:
                messages.info(request, f'Cliente {cliente_existente.nome} já cadastrado. Redirecionando para edição...')
                return redirect('vendas:cliente_editar', cliente_id=cliente_existente.id)
            
            # Cliente não existe, criar novo
            resultado = CheckoutVendasService.criar_cliente_checkout(
                loja_id=loja_id,
                tipo_documento=tipo_documento,
                dados=dados,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            if resultado['sucesso']:
                messages.success(request, resultado['mensagem'])
                return redirect('vendas:cliente_busca')
            else:
                messages.error(request, resultado['mensagem'])
                
        except Exception as e:
            messages.error(request, f'Erro ao cadastrar cliente: {str(e)}')
            registrar_log('portais.vendas', f"Erro ao cadastrar: {str(e)}", nivel='ERROR')
    
    context = {
        'vendedor': vendedor,
        'lojas': lojas,
    }
    
    return render(request, 'vendas/cliente_form.html', context)


@requer_checkout_vendedor
def cliente_busca(request):
    """Busca e listagem de clientes"""
    from .services import CheckoutVendasService
    
    vendedor = request.vendedor
    busca = request.GET.get('q', '').strip()
    clientes = CheckoutVendasService.buscar_clientes(vendedor.id, busca)
    
    context = {
        'vendedor': vendedor,
        'clientes': clientes,
        'busca': busca,
    }
    
    return render(request, 'vendas/cliente_busca.html', context)


@requer_checkout_vendedor
@require_http_methods(["GET", "POST"])
def cliente_editar(request, cliente_id):
    """Editar dados do cliente"""
    from .services import CheckoutVendasService
    CheckoutCliente = apps.get_model('checkout', 'CheckoutCliente')
    
    cliente = get_object_or_404(CheckoutCliente, id=cliente_id)
    
    if request.method == 'POST':
        dados = {
            'email': request.POST.get('email'),
            'endereco': request.POST.get('endereco'),
            'cep': request.POST.get('cep'),
        }
        
        resultado = CheckoutVendasService.atualizar_cliente_checkout(cliente_id, dados)
        
        if resultado['sucesso']:
            messages.success(request, resultado['mensagem'])
            return redirect('vendas:cliente_busca')
        else:
            messages.error(request, resultado['mensagem'])
    
    context = {
        'vendedor': request.vendedor,
        'cliente': cliente,
    }
    
    return render(request, 'vendas/cliente_editar.html', context)


@requer_checkout_vendedor
@require_POST
def cliente_inativar(request, cliente_id):
    """Inativar cliente"""
    from .services import CheckoutVendasService
    
    resultado = CheckoutVendasService.inativar_cliente_checkout(cliente_id)
    
    if resultado['sucesso']:
        messages.success(request, resultado['mensagem'])
    else:
        messages.error(request, resultado['mensagem'])
    
    return redirect('vendas:cliente_busca')


@requer_checkout_vendedor
@require_POST
def cliente_reativar(request, cliente_id):
    """Reativar cliente"""
    from .services import CheckoutVendasService
    
    resultado = CheckoutVendasService.reativar_cliente_checkout(cliente_id)
    
    if resultado['sucesso']:
        messages.success(request, resultado['mensagem'])
    else:
        messages.error(request, resultado['mensagem'])
    
    return redirect('vendas:cliente_busca')


# ============================================================================
# CHECKOUT DIRETO
# ============================================================================

@requer_checkout_vendedor
def checkout_view(request):
    """Interface de checkout direto"""
    from .services import CheckoutVendasService
    
    vendedor = request.vendedor
    lojas = CheckoutVendasService.obter_lojas_vendedor(vendedor.id)
    
    context = {
        'vendedor': vendedor,
        'lojas': lojas,
    }
    
    return render(request, 'vendas/checkout.html', context)


@requer_checkout_vendedor
@require_POST
def checkout_processar(request):
    """Processar pagamento do checkout direto"""
    from .services import CheckoutVendasService
    from decimal import Decimal
    
    try:
        tipo_cartao = request.POST.get('tipo_cartao', '')
        
        # ENVIAR LINK
        if tipo_cartao == 'enviar_link':
            return processar_envio_link(request)
        
        # CARTÃO SALVO
        if tipo_cartao == 'salvo':
            forma_pagamento = request.POST.get('forma_pagamento', '')
            
            if not forma_pagamento.startswith('cartao_'):
                messages.error(request, 'Cartão não selecionado corretamente')
                return redirect('vendas:checkout')
            
            cartao_id = forma_pagamento.replace('cartao_', '')
            parcelas_str = request.POST.get('parcelas', '').strip()
            
            if not parcelas_str:
                messages.error(request, 'Parcelas obrigatórias')
                return redirect('vendas:checkout')
            
            cliente_id = int(request.POST.get('cliente_id'))
            valor_str = request.POST.get('valor', '').replace('.', '').replace(',', '.')
            valor_original = Decimal(valor_str)
            valor_total_str = request.POST.get('valor_total_parcela', '').replace(',', '.')
            valor_final = Decimal(valor_total_str) if valor_total_str else valor_original
            
            resultado = CheckoutVendasService.processar_pagamento_cartao_salvo(
                cliente_id=cliente_id,
                cartao_id=cartao_id,
                valor_original=valor_original,
                valor_final=valor_final,
                parcelas=int(parcelas_str),
                bandeira=request.POST.get('bandeira'),
                descricao=request.POST.get('descricao'),
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                pedido_origem=request.POST.get('pedido_origem'),
                cod_item_origem=request.POST.get('cod_item_origem'),
                vendedor_id=request.vendedor.id
            )
        else:
            messages.error(request, 'Tipo de cartão inválido')
            return redirect('vendas:checkout')
        
        if resultado.get('sucesso'):
            messages.success(request, f"Pagamento aprovado! NSU: {resultado.get('nsu')}")
            return redirect('vendas:checkout_resultado', transacao_id=resultado.get('transacao_id'))
        else:
            messages.error(request, f"Pagamento negado: {resultado.get('mensagem')}")
            return redirect('vendas:checkout')
    except Exception as e:
        messages.error(request, f'Erro: {str(e)}')
        registrar_log('portais.vendas', f"Erro: {str(e)}", nivel='ERROR')
        return redirect('vendas:checkout')


@requer_checkout_vendedor
@require_POST
def processar_envio_link(request):
    """Gera token, cria transação PENDENTE e envia link de pagamento por email"""
    from .services import CheckoutVendasService
    from decimal import Decimal
    
    try:
        cliente_id = int(request.POST.get('cliente_id'))
        loja_id = int(request.POST.get('loja_id'))
        valor_str = request.POST.get('valor', '').replace('.', '').replace(',', '.')
        valor = Decimal(valor_str)
        descricao = request.POST.get('descricao', 'Venda')
        pedido_origem = request.POST.get('pedido_origem')
        cod_item_origem = request.POST.get('cod_item_origem')
        
        resultado = CheckoutVendasService.processar_envio_link_pagamento(
            cliente_id=cliente_id,
            loja_id=loja_id,
            valor=valor,
            descricao=descricao,
            pedido_origem=pedido_origem,
            cod_item_origem=cod_item_origem,
            vendedor_id=request.vendedor.id
        )
        
        if resultado['sucesso']:
            messages.success(request, resultado['mensagem'])
        else:
            messages.error(request, resultado['mensagem'])
        
        return redirect('vendas:checkout')
    except Exception as e:
        messages.error(request, f'Erro: {str(e)}')
        registrar_log('portais.vendas', f"Erro: {str(e)}", nivel='ERROR')
        return redirect('vendas:checkout')


@requer_checkout_vendedor
def checkout_resultado(request, transacao_id):
    """Exibir resultado da transação"""
    CheckoutTransaction = apps.get_model('checkout', 'CheckoutTransaction')
    transacao = get_object_or_404(CheckoutTransaction, id=transacao_id, origem='CHECKOUT')
    
    context = {
        'vendedor': request.vendedor,
        'transacao': transacao,
    }
    
    return render(request, 'vendas/checkout_resultado.html', context)


@requer_checkout_vendedor
def buscar_pedido(request):
    """Buscar pedidos/transações com filtros"""
    from .services import CheckoutVendasService
    from django.core.paginator import Paginator
    CheckoutTransaction = apps.get_model('checkout', 'CheckoutTransaction')
    
    vendedor = request.vendedor
    
    # Buscar transações via service
    transacoes = CheckoutVendasService.buscar_transacoes(
        vendedor_id=vendedor.id,
        cpf=request.GET.get('cpf', '').strip(),
        status=request.GET.get('status', '').strip(),
        data_inicio=request.GET.get('data_inicio', '').strip(),
        data_fim=request.GET.get('data_fim', '').strip()
    )
    
    # Filtros ativos para exibição
    filtros_ativos = {}
    if request.GET.get('cpf'):
        filtros_ativos['cpf'] = request.GET.get('cpf')
    if request.GET.get('status'):
        filtros_ativos['status'] = request.GET.get('status')
    if request.GET.get('data_inicio'):
        filtros_ativos['data_inicio'] = request.GET.get('data_inicio')
    if request.GET.get('data_fim'):
        filtros_ativos['data_fim'] = request.GET.get('data_fim')
    
    # Paginação
    paginator = Paginator(transacoes, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'vendedor': vendedor,
        'page_obj': page_obj,
        'filtros_ativos': filtros_ativos,
        'status_choices': CheckoutTransaction.STATUS_CHOICES,
        'total_resultados': paginator.count,
        'current_page': 'buscar_pedido',
    }
    
    return render(request, 'vendas/buscar_pedido.html', context)


# ============================================================================
# AJAX
# ============================================================================

@requer_checkout_vendedor
def ajax_buscar_cliente(request):
    """AJAX: Buscar cliente por CPF/CNPJ"""
    from .services import CheckoutVendasService
    
    try:
        loja_id = int(request.GET.get('loja_id'))
        documento = request.GET.get('documento', '')
        
        resultado = CheckoutVendasService.buscar_cliente_por_documento(loja_id, documento)
        return JsonResponse(resultado)
    except Exception as e:
        registrar_log('portais.vendas', f"Erro busca cliente: {str(e)}", nivel='ERROR')
        return JsonResponse({'sucesso': False, 'mensagem': str(e)})


@requer_checkout_vendedor
def ajax_calcular_parcelas(request):
    """AJAX: Calcular parcelas usando CheckoutService (com suporte a bandeira)"""
    from .services import CheckoutVendasService
    
    try:
        valor = float(request.GET.get('valor'))
        loja_id = int(request.GET.get('loja_id'))
        bandeira = request.GET.get('bandeira', 'MASTERCARD')
        
        resultado = CheckoutVendasService.simular_parcelas(valor, loja_id, bandeira)
        
        if resultado.get('sucesso'):
            return JsonResponse({
                'sucesso': True,
                'parcelas': resultado.get('parcelas', {}),
                'mensagem': 'Parcelas calculadas com sucesso'
            })
        else:
            return JsonResponse({
                'sucesso': False,
                'mensagem': resultado.get('mensagem', 'Erro ao calcular parcelas')
            })
    except Exception as e:
        registrar_log('portais.vendas', f"Erro calcular parcelas: {str(e)}", nivel='ERROR')
        return JsonResponse({'sucesso': False, 'mensagem': str(e)})


@requer_checkout_vendedor
def ajax_simular_parcelas(request):
    """AJAX: Simular parcelas para o valor informado"""
    from .services import CheckoutVendasService
    
    try:
        valor = float(request.GET.get('valor'))
        loja_id = int(request.GET.get('loja_id'))
        bandeira = request.GET.get('bandeira', 'MASTERCARD')
        
        resultado = CheckoutVendasService.simular_parcelas(valor, loja_id, bandeira)
        return JsonResponse(resultado)
    except Exception as e:
        registrar_log('portais.vendas', f"Erro simular parcelas: {str(e)}", nivel='ERROR')
        return JsonResponse({'sucesso': False, 'mensagem': str(e)})


@requer_checkout_vendedor
@require_http_methods(["POST"])
def ajax_pesquisar_cpf(request):
    """AJAX: Pesquisa CPF no apps/cliente; se não existir, consulta Bureau.
    Retorna nome oficial (não editável) para preencher o formulário de novo cliente.
    """
    from .services import CheckoutVendasService
    
    try:
        import json
        payload = json.loads(request.body.decode('utf-8')) if request.body else {}
        cpf = payload.get('cpf', '')
        loja_id = int(payload.get('loja_id')) if payload.get('loja_id') else None
        
        if not loja_id:
            return JsonResponse({'sucesso': False, 'mensagem': 'Loja não informada'})
        
        resultado = CheckoutVendasService.pesquisar_cpf_bureau(cpf, loja_id)
        return JsonResponse(resultado)
    except Exception as e:
        registrar_log('portais.vendas', f"Erro pesquisar CPF: {str(e)}", nivel='ERROR')
        return JsonResponse({'sucesso': False, 'mensagem': str(e)})
