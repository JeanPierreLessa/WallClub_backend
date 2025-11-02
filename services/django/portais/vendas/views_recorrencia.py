"""
Views de Recorrência - Portal de Vendas
Fase 5 - Unificação Portal Vendas + Recorrência

Gerencia pagamentos recorrentes agendados (cobranças automáticas).
Todas as views usam CheckoutVendasService para lógica de negócio.
"""
from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from wallclub_core.utilitarios.log_control import registrar_log
from django.apps import apps
from portais.vendas.decorators import requer_permissao
from portais.vendas.services import CheckoutVendasService


@requer_permissao('recorrencia')
@require_http_methods(["GET", "POST"])
def recorrencia_agendar(request):
    """
    Tela de agendamento de nova recorrência.
    GET: Exibe formulário
    POST: Processa criação da recorrência
    """
    if request.method == 'POST':
        try:
            # Extrair dados do formulário
            cliente_id = request.POST.get('cliente_id')
            cartao_tokenizado_id = request.POST.get('cartao_tokenizado_id')
            descricao = request.POST.get('descricao', '').strip()
            valor = request.POST.get('valor')
            tipo_periodicidade = request.POST.get('tipo_periodicidade')
            dia_cobranca = request.POST.get('dia_cobranca')
            mes_cobranca_anual = request.POST.get('mes_cobranca_anual')
            dia_cobranca_anual = request.POST.get('dia_cobranca_anual')
            
            # Validações básicas
            if not all([cliente_id, cartao_tokenizado_id, descricao, valor, tipo_periodicidade]):
                messages.error(request, 'Todos os campos são obrigatórios.')
                return render(request, 'vendas/recorrencia/agendar.html')
            
            # Converter tipos
            try:
                cliente_id = int(cliente_id)
                # Se for 'novo_cartao', mantém como string para enviar link
                if cartao_tokenizado_id != 'novo_cartao':
                    cartao_tokenizado_id = int(cartao_tokenizado_id)
                valor = Decimal(valor.replace(',', '.'))
                dia_cobranca = int(dia_cobranca) if dia_cobranca else None
            except (ValueError, TypeError) as e:
                messages.error(request, f'Dados inválidos: {str(e)}')
                return render(request, 'vendas/recorrencia/agendar.html')
            
            # Validar valor mínimo
            if valor <= 0:
                messages.error(request, 'Valor deve ser maior que zero.')
                return render(request, 'vendas/recorrencia/agendar.html')
            
            # Buscar loja do vendedor
            from portais.controle_acesso.models import PortalUsuarioAcesso
            loja_acesso = PortalUsuarioAcesso.objects.filter(
                usuario=request.vendedor,
                portal='vendas',
                entidade_tipo='loja',
                ativo=True
            ).first()
            
            if not loja_acesso:
                messages.error(request, 'Nenhuma loja vinculada ao seu usuário.')
                return render(request, 'vendas/recorrencia/agendar.html')
            
            # Processar via service
            resultado = CheckoutVendasService.criar_recorrencia(
                cliente_id=cliente_id,
                cartao_tokenizado_id=cartao_tokenizado_id,
                descricao=descricao,
                valor=valor,
                tipo_periodicidade=tipo_periodicidade,
                vendedor_id=request.vendedor.id,
                loja_id=loja_acesso.entidade_id,
                dia_cobranca=int(dia_cobranca) if dia_cobranca else None,
                mes_cobranca_anual=int(mes_cobranca_anual) if mes_cobranca_anual else None,
                dia_cobranca_anual=int(dia_cobranca_anual) if dia_cobranca_anual else None
            )
            
            if resultado['sucesso']:
                messages.success(request, resultado['mensagem'])
                return redirect('vendas:recorrencia_listar')
            else:
                messages.error(request, resultado['mensagem'])
                
        except Exception as e:
            registrar_log('portais.vendas.recorrencia', f"Erro ao agendar recorrência: {str(e)}", nivel='ERROR')
            messages.error(request, 'Erro ao agendar recorrência. Tente novamente.')
    
    # GET: Renderizar formulário
    from checkout.models_recorrencia import RecorrenciaAgendada
    from portais.controle_acesso.models import PortalUsuarioAcesso
    
    # Buscar primeira loja do vendedor
    loja_acesso = PortalUsuarioAcesso.objects.filter(
        usuario=request.vendedor,
        portal='vendas',
        entidade_tipo='loja',
        ativo=True
    ).first()
    
    loja_id = loja_acesso.entidade_id if loja_acesso else 1
    
    context = {
        'titulo': 'Agendar Recorrência',
        'tipos_periodicidade': RecorrenciaAgendada.TIPO_PERIODICIDADE_CHOICES,
        'current_page': 'recorrencia_agendar',
        'loja_id': loja_id
    }
    return render(request, 'vendas/recorrencia/agendar.html', context)


@requer_permissao('recorrencia')
@require_http_methods(["GET"])
def recorrencia_listar(request):
    """
    Lista todas as recorrências com filtros.
    """
    try:
        # Extrair filtros
        status = request.GET.get('status')
        cliente_id = request.GET.get('cliente_id')
        loja_id = request.session.get('loja_id')
        
        # DEBUG: Verificar filtros aplicados
        registrar_log(
            'portais.vendas.recorrencia.debug',
            f"FILTROS LISTAGEM: loja_id={loja_id}, status={status}",
            nivel='INFO'
        )
        
        # Buscar recorrências via service (SEM filtrar por vendedor - ver todas da loja)
        recorrencias = CheckoutVendasService.listar_recorrencias(
            loja_id=loja_id,
            vendedor_id=None,  # Não filtrar por vendedor específico
            status=status,
            cliente_id=int(cliente_id) if cliente_id else None
        )
        
        # DEBUG: Quantidade retornada
        registrar_log(
            'portais.vendas.recorrencia.debug',
            f"RECORRÊNCIAS ENCONTRADAS: {len(recorrencias)}",
            nivel='INFO'
        )
        
        # Calcular estatísticas
        total = len(recorrencias)
        ativas = sum(1 for r in recorrencias if 'Ativo' in r['status'])
        pausadas = sum(1 for r in recorrencias if 'Pausado' in r['status'])
        hold = sum(1 for r in recorrencias if 'Hold' in r['status'])
        
        from checkout.models_recorrencia import RecorrenciaAgendada
        context = {
            'titulo': 'Recorrências Agendadas',
            'recorrencias': recorrencias,
            'status_escolhido': status,
            'total': total,
            'ativas': ativas,
            'pausadas': pausadas,
            'hold': hold,
            'status_choices': RecorrenciaAgendada.STATUS_CHOICES,
            'current_page': 'recorrencia_listar'
        }
        
        return render(request, 'vendas/recorrencia/lista.html', context)
        
    except Exception as e:
        registrar_log('portais.vendas.recorrencia', f"Erro ao listar recorrências: {str(e)}", nivel='ERROR')
        messages.error(request, 'Erro ao carregar recorrências.')
        return render(request, 'vendas/recorrencia/lista.html', {'recorrencias': []})


@requer_permissao('recorrencia')
@require_http_methods(["POST"])
def recorrencia_pausar(request, recorrencia_id):
    """
    Pausa uma recorrência ativa.
    """
    try:
        resultado = CheckoutVendasService.pausar_recorrencia(
            recorrencia_id=recorrencia_id,
            vendedor_id=request.portal_usuario.id
        )
        
        if resultado['sucesso']:
            messages.success(request, resultado['mensagem'])
        else:
            messages.error(request, resultado['mensagem'])
            
    except Exception as e:
        registrar_log('portais.vendas.recorrencia', f"Erro ao pausar recorrência: {str(e)}", nivel='ERROR')
        messages.error(request, 'Erro ao pausar recorrência.')
    
    return redirect('vendas:recorrencia_listar')


@requer_permissao('recorrencia')
@require_http_methods(["POST"])
def recorrencia_cancelar(request, recorrencia_id):
    """
    Cancela uma recorrência permanentemente.
    """
    try:
        resultado = CheckoutVendasService.cancelar_recorrencia(
            recorrencia_id=recorrencia_id,
            vendedor_id=request.portal_usuario.id
        )
        
        if resultado['sucesso']:
            messages.success(request, resultado['mensagem'])
        else:
            messages.error(request, resultado['mensagem'])
            
    except Exception as e:
        registrar_log('portais.vendas.recorrencia', f"Erro ao cancelar recorrência: {str(e)}", nivel='ERROR')
        messages.error(request, 'Erro ao cancelar recorrência.')
    
    return redirect('vendas:recorrencia_listar')


@requer_permissao('recorrencia')
@require_http_methods(["GET"])
def recorrencia_relatorio_nao_cobrados(request):
    """
    Relatório de recorrências em HOLD (múltiplas falhas).
    """
    try:
        loja_id = request.session.get('loja_id')
        
        # Buscar recorrências em hold (todas da loja)
        nao_cobrados = CheckoutVendasService.obter_nao_cobrados(
            loja_id=loja_id,
            vendedor_id=None  # Ver todas da loja
        )
        
        # Calcular total não cobrado
        total_valor = sum(item['valor'] for item in nao_cobrados)
        
        context = {
            'titulo': 'Relatório - Não Cobrados',
            'nao_cobrados': nao_cobrados,
            'total_registros': len(nao_cobrados),
            'total_valor': total_valor,
            'current_page': 'recorrencia_nao_cobrados'
        }
        
        return render(request, 'vendas/recorrencia/relatorio_nao_cobrados.html', context)
        
    except Exception as e:
        registrar_log('portais.vendas.recorrencia', f"Erro ao gerar relatório: {str(e)}", nivel='ERROR')
        messages.error(request, 'Erro ao carregar relatório.')
        return render(request, 'vendas/recorrencia/relatorio_nao_cobrados.html', {'nao_cobrados': []})


@requer_permissao('recorrencia')
@require_http_methods(["GET"])
def recorrencia_detalhe(request, recorrencia_id):
    """
    Exibe detalhes completos de uma recorrência + histórico de tentativas.
    """
    try:
        from checkout.models_recorrencia import RecorrenciaAgendada
        from checkout.models import CheckoutTransaction
        
        # Buscar recorrência
        recorrencia = RecorrenciaAgendada.objects.select_related(
            'cliente', 'cartao_tokenizado', 'loja'
        ).get(id=recorrencia_id)
        
        # Validar acesso do vendedor
        if recorrencia.vendedor_id != request.vendedor.id:
            messages.error(request, 'Você não tem permissão para visualizar esta recorrência.')
            return redirect('vendas:recorrencia_listar')
        
        # Buscar histórico de transações executadas
        historico = CheckoutTransaction.objects.filter(
            checkout_recorrencia=recorrencia
        ).order_by('-created_at')[:10]
        
        context = {
            'titulo': f'Recorrência #{recorrencia.id}',
            'recorrencia': recorrencia,
            'historico': historico,
            'current_page': 'recorrencia_detalhe'
        }
        
        return render(request, 'vendas/recorrencia/detalhe.html', context)
        
    except RecorrenciaAgendada.DoesNotExist:
        messages.error(request, 'Recorrência não encontrada.')
        return redirect('vendas:recorrencia_listar')
    except Exception as e:
        registrar_log('portais.vendas.recorrencia', f"Erro ao exibir detalhe: {str(e)}", nivel='ERROR')
        messages.error(request, 'Erro ao carregar detalhes.')
        return redirect('vendas:recorrencia_listar')


@requer_permissao('recorrencia')
@require_http_methods(["POST"])
def recorrencia_reativar(request, recorrencia_id):
    """
    Reativa uma recorrência pausada.
    """
    try:
        from checkout.models_recorrencia import RecorrenciaAgendada
        
        recorrencia = RecorrenciaAgendada.objects.get(id=recorrencia_id)
        
        # Validar acesso
        if recorrencia.vendedor_id != request.vendedor.id:
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'Você não tem permissão para reativar esta recorrência.'
            }, status=403)
        
        # Validar status
        if recorrencia.status != 'pausado':
            return JsonResponse({
                'sucesso': False,
                'mensagem': f'Não é possível reativar recorrência com status: {recorrencia.get_status_display()}'
            })
        
        # Reativar
        recorrencia.status = 'ativo'
        recorrencia.save(update_fields=['status', 'updated_at'])
        
        registrar_log(
            'portais.vendas.recorrencia',
            f"Recorrência reativada: ID={recorrencia_id}, Vendedor={request.vendedor.id}"
        )
        
        messages.success(request, 'Recorrência reativada com sucesso.')
        return redirect('vendas:recorrencia_listar')
        
    except RecorrenciaAgendada.DoesNotExist:
        messages.error(request, 'Recorrência não encontrada.')
        return redirect('vendas:recorrencia_listar')
    except Exception as e:
        registrar_log('portais.vendas.recorrencia', f"Erro ao reativar: {str(e)}", nivel='ERROR')
        messages.error(request, 'Erro ao reativar recorrência.')
        return redirect('vendas:recorrencia_listar')
