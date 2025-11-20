"""
Views do Portal Lojista - Módulo de Recebimentos
"""
import json
from datetime import datetime
from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.views import View
from django.http import JsonResponse, HttpResponse
from django.db import connection
from django.contrib import messages
from datetime import datetime, timedelta, date
import json
import csv
import io
from decimal import Decimal
from django.apps import apps

from .mixins import LojistaAccessMixin, LojistaDataMixin


class LojistaRecebimentosView(LojistaAccessMixin, LojistaDataMixin, TemplateView):
    """View de recebimentos"""
    template_name = 'portais/lojista/recebimentos.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obter lojas acessíveis usando serviço centralizado
        from portais.controle_acesso.models import PortalUsuario
        from portais.controle_acesso.filtros import FiltrosAcessoService
        
        usuario_id = self.request.session.get('lojista_usuario_id')
        try:
            usuario = PortalUsuario.objects.get(id=usuario_id)
            lojas_acessiveis = FiltrosAcessoService.obter_lojas_acessiveis(usuario)
        except PortalUsuario.DoesNotExist:
            lojas_acessiveis = []
        
        context.update({
            'current_page': 'recebimentos',
            'lojas_acessiveis': lojas_acessiveis,
            'mostrar_filtro_loja': len(lojas_acessiveis) > 1
        })
        
        return context
    
    def post(self, request):
        """Processar consulta AJAX de recebimentos - Nova versão com resumo por data"""
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Parâmetros da consulta
            data_inicio = request.POST.get('data_inicio', '')
            data_fim = request.POST.get('data_fim', '')
            loja_selecionada = request.POST.get('loja', '')
            nsu = request.POST.get('nsu', '').strip()
            
            # Validar acesso às lojas usando serviço centralizado
            from portais.controle_acesso.models import PortalUsuario
            from portais.controle_acesso.filtros import FiltrosAcessoService
            from .services_recebimentos import RecebimentoService
            
            usuario_id = request.session.get('lojista_usuario_id')
            try:
                usuario = PortalUsuario.objects.get(id=usuario_id)
                lojas_acessiveis = FiltrosAcessoService.obter_lojas_acessiveis(usuario)
                loja_ids_acesso = [loja['id'] for loja in lojas_acessiveis] if lojas_acessiveis else []
            except PortalUsuario.DoesNotExist:
                loja_ids_acesso = []
            
            # Determinar lojas para consulta
            if loja_selecionada and loja_selecionada != 'todas':
                if int(loja_selecionada) in loja_ids_acesso:
                    lojas_para_consulta = [int(loja_selecionada)]
                else:
                    return JsonResponse({'error': 'Acesso negado à loja selecionada'}, status=403)
            else:
                lojas_para_consulta = loja_ids_acesso
            
            try:
                # Usar RecebimentoService para buscar recebimentos agrupados por data
                recebimentos_por_data = RecebimentoService.obter_recebimentos_por_data(
                    lojas_ids=lojas_para_consulta,
                    data_inicio=data_inicio if data_inicio else None,
                    data_fim=data_fim if data_fim else None,
                    nsu=nsu if nsu else None
                )
                
                # Converter para formato esperado pelo template
                recebimentos_resumo = []
                for data_key, dados in recebimentos_por_data.items():
                    # Calcular valores por tipo (separar repasse, rebate e outros)
                    valor_pago_repasse = 0
                    valor_pago_rebate = 0
                    outros_lancamentos = 0
                    
                    for transacao in dados['transacoes']:
                        if transacao.get('tipo') == 'lancamento_manual':
                            outros_lancamentos += float(transacao['valor'])
                        # Lógica para separar repasse e rebate poderia vir aqui
                        # Por enquanto, soma tudo no valor total
                    
                    recebimentos_resumo.append({
                        'data_recebimento': dados['data_formatada'],
                        'data_recebimento_raw': data_key,
                        'valor_pago_repasse': float(dados['valor_total']) - outros_lancamentos,
                        'valor_pago_rebate': 0,  # Será calculado se necessário
                        'outros_lancamentos': outros_lancamentos
                    })
                
                # Renderizar HTML do resumo
                html = self._render_resumo_recebimentos_html(recebimentos_resumo)
                
                return JsonResponse({
                    'success': True,
                    'html': html,
                    'total': len(recebimentos_resumo)
                })
                
            except Exception as e:
                return JsonResponse({'error': f'Erro na consulta: {str(e)}'}, status=500)
        
        return self.get(request)
    
    def _render_resumo_recebimentos_html(self, recebimentos_resumo):
        """Renderizar HTML do resumo de recebimentos por data"""
        if not recebimentos_resumo:
            return '<div class="alert alert-info mt-3">Nenhum recebimento encontrado com os filtros informados.</div>'
        
        # Calcular totais gerais
        total_repasse = sum(item['valor_pago_repasse'] for item in recebimentos_resumo)
        total_rebate = sum(item['valor_pago_rebate'] for item in recebimentos_resumo)
        total_outros_lancamentos = sum(item['outros_lancamentos'] for item in recebimentos_resumo)
        total_liquido = total_repasse + total_rebate + total_outros_lancamentos
        
        # Cards de totais
        html = '<div class="row mt-3 mb-3">'
        
        cards = [
            ('Total Repasse', total_repasse, 'bg-primary'),
            ('Total Rebate', total_rebate, 'bg-success'),
            ('Total Outros Lançamentos', total_outros_lancamentos, 'bg-warning text-dark'),
            ('Total Líquido', total_liquido, 'bg-info')
        ]
        
        for titulo, valor, classe in cards:
            valor_formatado = f"R$ {valor:,.2f}"
            
            html += f'''
            <div class="col-md-3">
                <div class="card {classe} text-white">
                    <div class="card-body py-2 text-center">
                        <h5 class="card-title" style="font-size: 14px; margin-bottom: 5px;">{titulo}</h5>
                        <h3 class="card-text" style="font-size: 18px; margin-bottom: 0;">{valor_formatado}</h3>
                    </div>
                </div>
            </div>
            '''
        
        html += '</div>'
        
        # Tabela de recebimentos por data
        html += '''
        <div class="table-responsive">
            <table class="table table-striped table-hover">
                <thead class="table-dark">
                    <tr>
                        <th>Data Recebimento</th>
                        <th>Valor Repasse (R$)</th>
                        <th>Valor Rebate (R$)</th>
                        <th>Outros Lançamentos (R$)</th>
                        <th>Total Líquido (R$)</th>
                        <th>Ações</th>
                    </tr>
                </thead>
                <tbody>
        '''
        
        for item in recebimentos_resumo:
            total_item = item['valor_pago_repasse'] + item['valor_pago_rebate'] + item['outros_lancamentos']
            html += f'''
            <tr>
                <td>{item['data_recebimento']}</td>
                <td>R$ {item['valor_pago_repasse']:,.2f}</td>
                <td>R$ {item['valor_pago_rebate']:,.2f}</td>
                <td>R$ {item['outros_lancamentos']:,.2f}</td>
                <td><strong>R$ {total_item:,.2f}</strong></td>
                <td>
                    <a href="/recebimentos/detalhes/?data={item['data_recebimento_raw']}" 
                       class="btn btn-sm btn-outline-primary">
                        <i class="fas fa-eye me-1"></i>Ver Detalhes
                    </a>
                </td>
            </tr>
            '''
        
        html += '</tbody></table></div>'
        
        return html

    def _render_recebimentos_html(self, recebimentos, totais):
        """Renderizar HTML dos recebimentos"""
        # Função auxiliar para conversão segura de float
        def safe_float_convert(value):
            if not value:
                return 0
            if isinstance(value, str):
                value = value.replace('R$', '').replace(' ', '').strip()
                if ',' in value and '.' not in value:
                    value = value.replace(',', '.')
            try:
                return float(value)
            except (ValueError, TypeError):
                return 0
        
        if not recebimentos:
            return '<div class="alert alert-info mt-3">Nenhum recebimento encontrado com os filtros informados.</div>'
        
        # Cards de totais - ESPECÍFICOS PARA RECEBIMENTOS
        html = '<div class="row mt-3 mb-3">'
        
        cards = [
            ('Total Bruto', totais['total_bruto'], 'bg-primary'),
            ('Total Líquido', totais['total_liquido'], 'bg-success'),
            ('Total Créditos', totais['total_creditos'], 'bg-info'),
            ('Total Débitos', totais['total_debitos'], 'bg-warning')
        ]
        
        for titulo, valor, classe in cards:
            html += f'''
            <div class="col-md-3">
                <div class="card {classe} text-white">
                    <div class="card-body py-2 text-center">
                        <h5 class="card-title" style="font-size: 14px; margin-bottom: 5px;">{titulo}</h5>
                        <h3 class="card-text" style="font-size: 18px; margin-bottom: 0;">R$ {valor:,.2f}</h3>
                    </div>
                </div>
            </div>
            '''
        
        html += '</div>'
        
        # Tabela de recebimentos
        html += '''
        <div class="table-responsive">
            <table class="table table-striped table-hover" style="font-size: 0.75rem;">
                <thead class="table-dark">
                    <tr>
                        <th>Loja</th>
                        <th>Data</th>
                        <th>Vl Líq(R$)</th>
                        <th>Tipo</th>
                        <th>Status</th>
                        <th>Vl Bruto(R$)</th>
                        <th>Tx.Antec(R$)</th>
                        <th>Custo Antec(R$)</th>
                        <th>Parcela</th>
                        <th>Prazo Total</th>
                        <th>Plano</th>
                        <th>Bandeira</th>
                        <th>NSU</th>
                        <th>Status Trans.</th>
                    </tr>
                </thead>
                <tbody>
        '''
        
        for recebimento in recebimentos:
            tipo_class = 'text-success' if recebimento.get("Tipo") == 'Crédito' else 'text-danger'
            html += f'''
            <tr>
                <td>{recebimento.get("Loja", "-")}</td>
                <td>{recebimento.get("Data", "-")}</td>
                <td>R$ {safe_float_convert(recebimento.get("Vl Líq(R$)", 0)):,.2f}</td>
                <td><span class="{tipo_class}"><strong>{recebimento.get("Tipo", "-")}</strong></span></td>
                <td>{recebimento.get("Status", "-")}</td>
                <td>R$ {safe_float_convert(recebimento.get("Vl Bruto(R$)", 0)):,.2f}</td>
                <td>R$ {safe_float_convert(recebimento.get("Tx.Antec(R$)", 0)):,.2f}</td>
                <td>R$ {safe_float_convert(recebimento.get("Custo Antec(R$)", 0)):,.2f}</td>
                <td>{recebimento.get("Parcela", "-")}</td>
                <td>{recebimento.get("Prazo Total", "-")}</td>
                <td>{recebimento.get("Plano", "-")}</td>
                <td>{recebimento.get("Bandeira", "-")}</td>
                <td>{recebimento.get("NSU", "-")}</td>
                <td>{recebimento.get("Status Trans.", "-")}</td>
            </tr>
            '''
        
        html += '</tbody></table></div>'
        
        return html


class LojistaRecebimentosDetalhesView(TemplateView):
    """View para mostrar detalhes das transações de uma data específica"""
    template_name = 'portais/lojista/recebimentos_detalhes.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.session.get('lojista_authenticated'):
            return redirect('lojista:login')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Adicionar marca do canal se disponível
        context['marca'] = self.request.session.get('marca_canal', '')
        
        # Obter data do parâmetro GET e converter para formato brasileiro
        data_recebimento = self.request.GET.get('data', '')
        data_formatada_br = data_recebimento
        
        if data_recebimento:
            try:
                from datetime import datetime
                data_obj = datetime.strptime(data_recebimento, '%Y-%m-%d')
                data_formatada_br = data_obj.strftime('%d/%m/%Y')
            except ValueError:
                pass
        
        context['data_recebimento'] = data_formatada_br
        
        # Verificar se deve mostrar filtro de loja usando serviço centralizado
        from portais.controle_acesso.models import PortalUsuario
        from portais.controle_acesso.filtros import FiltrosAcessoService
        
        usuario_id = self.request.session.get('lojista_usuario_id')
        try:
            usuario = PortalUsuario.objects.get(id=usuario_id)
            lojas_acessiveis = FiltrosAcessoService.obter_lojas_acessiveis(usuario)
            context['mostrar_filtro_loja'] = len(lojas_acessiveis) > 1
        except PortalUsuario.DoesNotExist:
            context['mostrar_filtro_loja'] = False
        
        return context
    
    def post(self, request):
        """Processar consulta AJAX das transações de uma data específica"""
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Parâmetros da consulta
            data_recebimento = request.POST.get('data_recebimento', '')
            loja_selecionada = request.POST.get('loja', '')
            nsu = request.POST.get('nsu', '').strip()
            
            if not data_recebimento:
                return JsonResponse({'error': 'Data de recebimento é obrigatória'}, status=400)
            
            # Validar acesso às lojas usando serviço centralizado
            from portais.controle_acesso.models import PortalUsuario
            from portais.controle_acesso.filtros import FiltrosAcessoService
            
            usuario_id = request.session.get('lojista_usuario_id')
            try:
                usuario = PortalUsuario.objects.get(id=usuario_id)
                lojas_acessiveis = FiltrosAcessoService.obter_lojas_acessiveis(usuario)
                loja_ids_acesso = [loja['id'] for loja in lojas_acessiveis] if lojas_acessiveis else []
            except PortalUsuario.DoesNotExist:
                loja_ids_acesso = []
            
            # Determinar lojas para consulta
            if loja_selecionada and loja_selecionada != 'todas':
                if int(loja_selecionada) in loja_ids_acesso:
                    lojas_para_consulta = [int(loja_selecionada)]
                else:
                    return JsonResponse({'error': 'Acesso negado à loja selecionada'}, status=403)
            else:
                lojas_para_consulta = loja_ids_acesso
            
            try:
                # Usar RecebimentoService para buscar transações por data
                from .services_recebimentos import RecebimentoService
                from wallclub_core.utilitarios.log_control import registrar_log
                
                registrar_log('portais.lojista', f"RECEBIMENTOS - Buscando detalhes para data: {data_recebimento}")
                
                # Buscar transações usando o service
                transacoes_list = RecebimentoService.obter_transacoes_por_data(
                    lojas_ids=lojas_para_consulta,
                    data_recebimento=data_recebimento
                )
                
                # Converter para formato esperado pelo template
                results = []
                for transacao in transacoes_list:
                    vl_bruto = float(transacao.get('valor_transacao', 0) or 0)
                    vl_liquido = float(transacao.get('valor_recebimento', 0) or 0)
                    
                    # Determinar tipo (Crédito/Débito)
                    tipo = 'Crédito' if vl_liquido >= 0 else 'Débito'
                    
                    # Buscar nome da loja
                    nome_loja = f"Loja {transacao['loja_id']}"
                    try:
                        from portais.controle_acesso.filtros import FiltrosAcessoService
                        lojas_acessiveis = FiltrosAcessoService.obter_lojas_acessiveis(usuario)
                        for loja_info in lojas_acessiveis:
                            if loja_info.get('id') == transacao['loja_id']:
                                nome_loja = loja_info.get('nome', nome_loja)[:10]
                                break
                    except:
                        pass
                    
                    row_dict = {
                        'Loja': nome_loja,
                        'Data': transacao.get('data_transacao', '-'),
                        'Vl Líq(R$)': vl_liquido,
                        'Tipo': tipo,
                        'Status': '-',
                        'Vl Bruto(R$)': vl_bruto,
                        'Tx.Antec(R$)': 0,
                        'Custo Antec(R$)': 0,
                        'Parcela': transacao.get('parcelas', 0) or 0,
                        'Prazo Total': transacao.get('parcelas', 0) or 0,
                        'Plano': transacao.get('plano', '-') or '-',
                        'Bandeira': transacao.get('bandeira', '-') or '-',
                        'NSU': transacao.get('nsu', '-') or '-',
                        'NOP': '-'
                    }
                    results.append(row_dict)
                
                # Buscar lançamentos manuais usando o service
                lancamentos_list = RecebimentoService.obter_lancamentos_por_data(
                    lojas_ids=lojas_para_consulta,
                    data_lancamento=data_recebimento
                )
                
                lancamentos_manuais = []
                for lancamento in lancamentos_list:
                    # Buscar nome da loja
                    nome_loja = f"Loja {lancamento['loja_id']}"
                    try:
                        from portais.controle_acesso.filtros import FiltrosAcessoService
                        lojas_acessiveis = FiltrosAcessoService.obter_lojas_acessiveis(usuario)
                        for loja_info in lojas_acessiveis:
                            if loja_info.get('id') == lancamento['loja_id']:
                                nome_loja = loja_info.get('nome', nome_loja)[:10]
                                break
                    except:
                        pass
                    
                    lancamentos_manuais.append({
                        'Loja': nome_loja,
                        'Data': lancamento['data_lancamento'].strftime('%d/%m/%Y'),
                        'Tipo': lancamento['tipo_display'],
                        'Valor(R$)': float(lancamento['valor']),
                        'Descrição': lancamento['descricao'],
                        'Status': lancamento['status'],
                        'Usuário': f"ID {lancamento['id']}"
                    })
                
                # Calcular totais específicos para recebimentos detalhados
                def safe_float_convert(value):
                    if not value:
                        return 0
                    if isinstance(value, str):
                        value = value.replace('R$', '').replace(' ', '').strip()
                        if ',' in value and '.' not in value:
                            value = value.replace(',', '.')
                    try:
                        return float(value)
                    except (ValueError, TypeError):
                        return 0
                
                # Totais das transações de venda
                total_bruto = sum(safe_float_convert(row.get('Vl Bruto(R$)', 0)) for row in results)
                total_liquido = sum(safe_float_convert(row.get('Vl Líq(R$)', 0)) for row in results)
                total_creditos = sum(safe_float_convert(row.get('Vl Líq(R$)', 0)) for row in results if row.get('Tipo') == 'Crédito')
                total_debitos = sum(abs(safe_float_convert(row.get('Vl Líq(R$)', 0))) for row in results if row.get('Tipo') == 'Débito')
                
                # Totais dos lançamentos manuais (valor já vem com sinal correto)
                total_lancamentos = sum(safe_float_convert(row.get('Valor(R$)', 0)) for row in lancamentos_manuais)
                total_lancamentos_creditos = sum(safe_float_convert(row.get('Valor(R$)', 0)) for row in lancamentos_manuais if row.get('Tipo') == 'Crédito')
                total_lancamentos_debitos = sum(safe_float_convert(row.get('Valor(R$)', 0)) for row in lancamentos_manuais if row.get('Tipo') == 'Débito')
                
                totais = {
                    'total_bruto': total_bruto,
                    'total_liquido': total_liquido,
                    'total_creditos': total_creditos,
                    'total_debitos': total_debitos,
                    'total_lancamentos': total_lancamentos,
                    'total_lancamentos_creditos': total_lancamentos_creditos,
                    'total_lancamentos_debitos': total_lancamentos_debitos,
                    'total_geral': total_liquido + total_lancamentos
                }
                
                # Renderizar HTML dos detalhes com ambas as listas
                html = self._render_detalhes_recebimentos_html(results, lancamentos_manuais, totais)
                
                return JsonResponse({
                    'success': True,
                    'html': html,
                    'total': len(results)
                })
                
            except Exception as e:
                return JsonResponse({'error': f'Erro na consulta: {str(e)}'}, status=500)
        
        return self.get(request)
    
    def _render_detalhes_recebimentos_html(self, recebimentos, lancamentos_manuais, totais):
        """Renderizar HTML dos detalhes de recebimentos com transações e lançamentos manuais"""
        # Função auxiliar para conversão segura de float
        def safe_float_convert(value):
            if not value:
                return 0
            if isinstance(value, str):
                value = value.replace('R$', '').replace(' ', '').strip()
                if ',' in value and '.' not in value:
                    value = value.replace(',', '.')
            try:
                return float(value)
            except (ValueError, TypeError):
                return 0
        
        # Cards de totais - padronizados com tela de vendas
        html = '<div class="row mt-3 mb-3">'
        
        cards = [
            ('Total Repasse', totais['total_liquido'], 'bg-primary'),
            ('Total Rebate', 0, 'bg-success'),
            ('Total Outros Lançamentos', totais['total_lancamentos'], 'bg-warning text-dark'),
            ('Total Líquido', totais['total_geral'], 'bg-info'),
        ]
        
        for titulo, valor, classe in cards:
            html += f'''
            <div class="col-md-3">
                <div class="card {classe} text-white">
                    <div class="card-body py-2 text-center">
                        <h5 class="card-title" style="font-size: 14px; margin-bottom: 5px;">{titulo}</h5>
                        <h3 class="card-text" style="font-size: 18px; margin-bottom: 0;">R$ {valor:,.2f}</h3>
                    </div>
                </div>
            </div>
            '''
        
        html += '</div>'
        
        # 1. TABELA DE TRANSAÇÕES DE VENDA
        html += '''
        <div class="row mb-4 mt-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
                        <h5 class="mb-0 mt-2">
                            <i class="fas fa-credit-card me-2"></i>
                            Transações de Venda
                            <span class="badge bg-light text-dark ms-2">''' + str(len(recebimentos)) + ''' registros</span>
                        </h5>
                        <div class="btn-group''' + (' d-none' if not recebimentos else '') + '''" id="exportTransacoesGroup">
                            <button type="button" class="btn btn-outline-light btn-sm dropdown-toggle" data-bs-toggle="dropdown" data-bs-auto-close="true">
                                <i class="fas fa-download me-1"></i>
                                Exportar
                            </button>
                            <ul class="dropdown-menu dropdown-menu-end">
                                <li><a class="dropdown-item" href="#" data-formato="excel" data-tipo="transacoes">
                                    <i class="fas fa-file-excel me-2 text-success"></i>Excel
                                </a></li>
                                <li><a class="dropdown-item" href="#" data-formato="csv" data-tipo="transacoes">
                                    <i class="fas fa-file-csv me-2 text-info"></i>CSV
                                </a></li>
                                <li><a class="dropdown-item" href="#" data-formato="pdf" data-tipo="transacoes">
                                    <i class="fas fa-file-pdf me-2 text-danger"></i>PDF
                                </a></li>
                            </ul>
                        </div>
                    </div>
                    <div class="card-body p-0">
        '''
        
        if not recebimentos:
            html += '<div class="alert alert-info m-3">Nenhuma transação de venda encontrada para esta data.</div>'
        else:
            html += '''
                        <div class="table-responsive mt-3">
                            <table class="table table-striped table-hover mb-0 mt-2" style="font-size: 0.75rem;">
                                <thead class="table-dark">
                                    <tr>
                                        <th>Loja</th>
                                        <th>Data</th>
                                        <th>Vl Líq(R$)</th>
                                        <th>Tipo</th>
                                        <th>Status</th>
                                        <th>Vl Bruto(R$)</th>
                                        <th>Tx.Antec(R$)</th>
                                        <th>Custo Antec(R$)</th>
                                        <th>Parcela</th>
                                        <th>Prazo Total</th>
                                        <th>Plano</th>
                                        <th>Bandeira</th>
                                        <th>NSU</th>
                                    </tr>
                                </thead>
                                <tbody>
            '''
            
            for recebimento in recebimentos:
                tipo_class = 'text-success' if recebimento.get("Tipo") == 'Crédito' else 'text-danger'
                html += f'''
                                    <tr>
                                        <td>{recebimento.get("Loja", "-")}</td>
                                        <td>{recebimento.get("Data", "-")}</td>
                                        <td>R$ {safe_float_convert(recebimento.get("Vl Líq(R$)", 0)):,.2f}</td>
                                        <td><span class="{tipo_class}"><strong>{recebimento.get("Tipo", "-")}</strong></span></td>
                                        <td>{recebimento.get("Status", "-")}</td>
                                        <td>R$ {safe_float_convert(recebimento.get("Vl Bruto(R$)", 0)):,.2f}</td>
                                        <td>R$ {safe_float_convert(recebimento.get("Tx.Antec(R$)", 0)):,.2f}</td>
                                        <td>R$ {safe_float_convert(recebimento.get("Custo Antec(R$)", 0)):,.2f}</td>
                                        <td>{recebimento.get("Parcela", "-")}</td>
                                        <td>{recebimento.get("Prazo Total", "-")}</td>
                                        <td>{recebimento.get("Plano", "-")}</td>
                                        <td>{recebimento.get("Bandeira", "-")}</td>
                                        <td>{recebimento.get("NSU", "-")}</td>
                                    </tr>
                '''
        
            html += '''
                                </tbody>
                            </table>
                        </div>'''
        
        html += '''
                    </div>
                </div>
            </div>
        </div>
        '''
        
        # 2. TABELA DE OUTROS LANÇAMENTOS (LANÇAMENTOS MANUAIS)
        html += '''
        <div class="row mb-4">
            <div class="col-12">
                <div class="card">
                    <div class="card-header bg-info text-white d-flex justify-content-between align-items-center">
                        <h5 class="mb-0 mt-2">
                            <i class="fas fa-edit me-2"></i>
                            Outros Lançamentos
                            <span class="badge bg-light text-dark ms-2">''' + str(len(lancamentos_manuais)) + ''' registros</span>
                        </h5>
                        <div class="btn-group''' + (' d-none' if not lancamentos_manuais else '') + '''" id="exportLancamentosGroup">
                            <button type="button" class="btn btn-outline-light btn-sm dropdown-toggle" data-bs-toggle="dropdown" data-bs-auto-close="true">
                                <i class="fas fa-download me-1"></i>
                                Exportar
                            </button>
                            <ul class="dropdown-menu dropdown-menu-end">
                                <li><a class="dropdown-item" href="#" data-formato="excel" data-tipo="lancamentos">
                                    <i class="fas fa-file-excel me-2 text-success"></i>Excel
                                </a></li>
                                <li><a class="dropdown-item" href="#" data-formato="csv" data-tipo="lancamentos">
                                    <i class="fas fa-file-csv me-2 text-info"></i>CSV
                                </a></li>
                                <li><a class="dropdown-item" href="#" data-formato="pdf" data-tipo="lancamentos">
                                    <i class="fas fa-file-pdf me-2 text-danger"></i>PDF
                                </a></li>
                            </ul>
                        </div>
                    </div>
                    <div class="card-body p-0">
        '''
        
        if not lancamentos_manuais:
            html += '<div class="alert alert-info m-3">Nenhum lançamento manual encontrado para esta data.</div>'
        else:
            html += '''
                        <div class="table-responsive mt-3">
                            <table class="table table-striped table-hover mb-0 mt-2" style="font-size: 0.75rem;">
                                <thead class="table-dark">
                                    <tr>
                                        <th>Loja</th>
                                        <th>Data</th>
                                        <th>Tipo</th>
                                        <th>Valor(R$)</th>
                                        <th>Descrição</th>
                                        <th>Status</th>
                                        <th>Usuário</th>
                                    </tr>
                                </thead>
                                <tbody>
            '''
            
            for lancamento in lancamentos_manuais:
                tipo_class = 'text-success' if lancamento.get("Tipo") == 'Crédito' else 'text-danger'
                valor = safe_float_convert(lancamento.get("Valor(R$)", 0))
                html += f'''
                                    <tr>
                                        <td>{lancamento.get("Loja", "-")}</td>
                                        <td>{lancamento.get("Data", "-")}</td>
                                        <td><span class="{tipo_class}"><strong>{lancamento.get("Tipo", "-")}</strong></span></td>
                                        <td>R$ {valor:,.2f}</td>
                                        <td>{lancamento.get("Descrição", "-")}</td>
                                        <td>{lancamento.get("Status", "-")}</td>
                                        <td>{lancamento.get("Usuário", "-")}</td>
                                    </tr>
                '''
            
            html += '''
                                </tbody>
                            </table>
                        </div>'''
        
        html += '''
                    </div>
                </div>
            </div>
        </div>
        '''
        
        return html


class LojistaRecebimentosExportView(View):
    """View para exportação de dados de recebimentos"""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.session.get('lojista_authenticated'):
            return redirect('lojista:login')
        return super().dispatch(request, *args, **kwargs)
    
    def post(self, request):
        from wallclub_core.utilitarios.export_utils import exportar_excel, exportar_csv, exportar_pdf
        from django.http import JsonResponse
        from datetime import datetime
        
        formato = request.POST.get('formato', 'excel')
        
        # Usar EXATAMENTE a mesma lógica da view principal de recebimentos
        data_inicio = request.POST.get('data_inicio', '')
        data_fim = request.POST.get('data_fim', '')
        loja_selecionada = request.POST.get('loja', '')
        nsu = request.POST.get('nsu', '').strip()
        
        # Validar acesso às lojas usando serviço centralizado
        from portais.controle_acesso.models import PortalUsuario
        from portais.controle_acesso.filtros import FiltrosAcessoService
        
        usuario_id = request.session.get('lojista_usuario_id')
        try:
            usuario = PortalUsuario.objects.get(id=usuario_id)
            lojas_acessiveis = FiltrosAcessoService.obter_lojas_acessiveis(usuario)
            loja_ids_acesso = [loja['id'] for loja in lojas_acessiveis] if lojas_acessiveis else []
        except PortalUsuario.DoesNotExist:
            loja_ids_acesso = []
        
        # Determinar lojas para consulta
        if loja_selecionada and loja_selecionada != 'todas':
            if int(loja_selecionada) in loja_ids_acesso:
                lojas_para_consulta = [int(loja_selecionada)]
            else:
                return JsonResponse({'error': 'Acesso negado à loja selecionada'}, status=403)
        else:
            lojas_para_consulta = loja_ids_acesso
        
        try:
            from django.db.models import Sum, Q
            from gestao_financeira.models import LancamentoManual
            
            # Usar RecebimentoService para buscar recebimentos agrupados
            from .services_recebimentos import RecebimentoService
            
            recebimentos_por_data = RecebimentoService.obter_recebimentos_por_data(
                lojas_ids=lojas_para_consulta,
                data_inicio=data_inicio if data_inicio else None,
                data_fim=data_fim if data_fim else None,
                nsu=nsu if nsu else None
            )
            
            # Converter para lista e ordenar
            results = []
            for data_key, dados in recebimentos_por_data.items():
                # Separar valores por tipo
                valor_pago_repasse = 0
                valor_pago_rebate = 0
                outros_lancamentos = 0
                
                for transacao in dados['transacoes']:
                    if transacao.get('tipo') == 'lancamento_manual':
                        outros_lancamentos += float(transacao['valor'])
                
                valor_pago_repasse = float(dados['valor_total']) - outros_lancamentos
                
                total_liquido = valor_pago_repasse + valor_pago_rebate + outros_lancamentos
                results.append({
                    'Data Recebimento': dados['data_formatada'],
                    'Valor Repasse (R$)': valor_pago_repasse,
                    'Valor Rebate (R$)': valor_pago_rebate,
                    'Outros Lançamentos (R$)': outros_lancamentos,
                    'Total Líquido (R$)': total_liquido
                })
            
            # Ordenar por data decrescente
            results.sort(key=lambda x: datetime.strptime(x['Data Recebimento'], '%d/%m/%Y'), reverse=True)
            
            # Coletar nomes únicos das lojas para o rodapé
            lojas_incluidas = [loja['nome'] for loja in lojas_acessiveis if loja['id'] in lojas_para_consulta]
            
            # Definir colunas monetárias para formatação
            colunas_monetarias = ['Valor Repasse (R$)', 'Valor Rebate (R$)', 'Outros Lançamentos (R$)', 'Total Líquido (R$)']
            
            nome_arquivo = f"recebimentos_resumo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            if formato == 'excel':
                return exportar_excel(
                    nome_arquivo=nome_arquivo,
                    dados=results,
                    titulo="Resumo Recebimentos",
                    colunas_monetarias=colunas_monetarias,
                    lojas_incluidas=lojas_incluidas
                )
            elif formato == 'csv':
                return exportar_csv(
                    nome_arquivo=nome_arquivo,
                    dados=results,
                    lojas_incluidas=lojas_incluidas
                )
            elif formato == 'pdf':
                return exportar_pdf(
                    nome_arquivo=nome_arquivo,
                    dados=results,
                    titulo="Resumo de Recebimentos - Portal Lojista",
                    colunas_monetarias=colunas_monetarias,
                    lojas_incluidas=lojas_incluidas
                )
            else:
                return JsonResponse({'error': 'Formato não suportado'}, status=400)
                    
        except Exception as e:
            return JsonResponse({'error': f'Erro na exportação: {str(e)}'}, status=500)


class LojistaRecebimentosDetalhesTransacoesExportView(View):
    """View para exportação de transações de vendas da página de detalhes"""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.session.get('lojista_authenticated'):
            return redirect('lojista:login')
        return super().dispatch(request, *args, **kwargs)
    
    def post(self, request):
        from wallclub_core.utilitarios.export_utils import exportar_excel, exportar_csv, exportar_pdf
        from django.http import JsonResponse
        from datetime import datetime
        
        formato = request.POST.get('formato', 'excel')
        data_recebimento = request.POST.get('data_recebimento', '')
        
        if not data_recebimento:
            return JsonResponse({'error': 'Data de recebimento é obrigatória'}, status=400)
        
        # Validar acesso às lojas usando serviço centralizado
        from portais.controle_acesso.models import PortalUsuario
        from portais.controle_acesso.filtros import FiltrosAcessoService
        
        usuario_id = request.session.get('lojista_usuario_id')
        try:
            usuario = PortalUsuario.objects.get(id=usuario_id)
            lojas_acessiveis = FiltrosAcessoService.obter_lojas_acessiveis(usuario)
            lojas_para_consulta = [loja['id'] for loja in lojas_acessiveis] if lojas_acessiveis else []
        except PortalUsuario.DoesNotExist:
            lojas_para_consulta = []
        
        try:
            # Usar RecebimentoService para buscar transações
            from .services_recebimentos import RecebimentoService
            
            transacoes_list = RecebimentoService.obter_transacoes_por_data(
                lojas_ids=lojas_para_consulta,
                data_recebimento=data_recebimento
            )
            
            results = []
            for transacao in transacoes_list:
                # Processar dados da transação
                valor_bruto = float(transacao.get('valor_transacao', 0) or 0)
                valor_liquido = float(transacao.get('valor_recebimento', 0) or 0)
                valor_rebate = 0
                
                # Formatar data da transação
                data_transacao = transacao.get('data_transacao', '-')
                if data_transacao != '-' and hasattr(data_transacao, 'strftime'):
                    data_transacao = data_transacao.strftime('%d/%m/%Y')
                
                results.append({
                    'NSU': transacao.get('nsu', '-'),
                    'Data Transação': data_transacao,
                    'Valor Bruto (R$)': valor_bruto,
                    'Valor Líquido (R$)': valor_liquido,
                    'Valor Rebate (R$)': valor_rebate,
                    'Plano': transacao.get('plano', '-') or '-',
                    'Bandeira': transacao.get('bandeira', '-') or '-',
                    'Parcelas': transacao.get('parcelas', '-') or '-',
                    'Loja ID': transacao.get('loja_id', '-')
                })
            
            # Coletar nomes únicos das lojas para o rodapé
            lojas_incluidas = [loja['nome'] for loja in lojas_acessiveis if loja['id'] in lojas_para_consulta]
            
            # Definir colunas monetárias para formatação
            colunas_monetarias = ['Valor Bruto (R$)', 'Valor Líquido (R$)', 'Valor Rebate (R$)']
            
            # Verificar se há dados para exportar
            if not results:
                return JsonResponse({'error': 'Nenhuma transação encontrada para a data especificada'}, status=404)
            
            nome_arquivo = f"transacoes_vendas_{data_formatada.replace('/', '')}_{datetime.now().strftime('%H%M%S')}"
            
            if formato == 'excel':
                return exportar_excel(
                    nome_arquivo=nome_arquivo,
                    dados=results,
                    titulo=f"Transações Vendas {data_recebimento}",
                    colunas_monetarias=colunas_monetarias,
                    lojas_incluidas=lojas_incluidas
                )
            elif formato == 'csv':
                return exportar_csv(
                    nome_arquivo=nome_arquivo,
                    dados=results,
                    lojas_incluidas=lojas_incluidas
                )
            elif formato == 'pdf':
                return exportar_pdf(
                    nome_arquivo=nome_arquivo,
                    dados=results,
                    titulo=f"Transações de Vendas - {data_recebimento}",
                    colunas_monetarias=colunas_monetarias,
                    lojas_incluidas=lojas_incluidas
                )
            else:
                return JsonResponse({'error': 'Formato não suportado'}, status=400)
                    
        except Exception as e:
            return JsonResponse({'error': f'Erro na exportação: {str(e)}'}, status=500)


class LojistaRecebimentosDetalhesLancamentosExportView(View):
    """View para exportação de lançamentos manuais da página de detalhes"""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.session.get('lojista_authenticated'):
            return redirect('lojista:login')
        return super().dispatch(request, *args, **kwargs)
    
    def post(self, request):
        from wallclub_core.utilitarios.export_utils import exportar_excel, exportar_csv, exportar_pdf
        from django.http import JsonResponse
        from datetime import datetime
        
        formato = request.POST.get('formato', 'excel')
        data_recebimento = request.POST.get('data_recebimento', '')
        
        if not data_recebimento:
            return JsonResponse({'error': 'Data de recebimento é obrigatória'}, status=400)
        
        # Validar acesso às lojas usando serviço centralizado
        from portais.controle_acesso.models import PortalUsuario
        from portais.controle_acesso.filtros import FiltrosAcessoService
        
        usuario_id = request.session.get('lojista_usuario_id')
        try:
            usuario = PortalUsuario.objects.get(id=usuario_id)
            lojas_acessiveis = FiltrosAcessoService.obter_lojas_acessiveis(usuario)
            loja_ids_acesso = [loja['id'] for loja in lojas_acessiveis] if lojas_acessiveis else []
        except PortalUsuario.DoesNotExist:
            loja_ids_acesso = []
        
        # Determinar lojas para consulta
        loja_selecionada = request.POST.get('loja_selecionada', '')
        if loja_selecionada and loja_selecionada != 'todas':
            if int(loja_selecionada) in loja_ids_acesso:
                lojas_para_consulta = [int(loja_selecionada)]
            else:
                return JsonResponse({'error': 'Acesso negado à loja selecionada'}, status=403)
        else:
            lojas_para_consulta = loja_ids_acesso
        
        try:
            from django.db.models import Q
            from gestao_financeira.models import LancamentoManual
            
            # Converter data para formato datetime - aceitar tanto YYYY-MM-DD quanto DD/MM/YYYY
            try:
                # Tentar formato YYYY-MM-DD primeiro (vem do frontend)
                data_obj = datetime.strptime(data_recebimento, '%Y-%m-%d').date()
            except ValueError:
                # Se falhar, tentar formato DD/MM/YYYY
                data_obj = datetime.strptime(data_recebimento, '%d/%m/%Y').date()
            
            # Buscar lançamentos manuais para a data específica
            filtros = Q(loja_id__in=lojas_para_consulta) & Q(data_lancamento__date=data_obj) & Q(status='processado')
            lancamentos = LancamentoManual.objects.filter(filtros).order_by('-data_lancamento')
            
            results = []
            for lancamento in lancamentos:
                # Processar dados do lançamento
                valor = float(lancamento.valor or 0)
                if lancamento.tipo_lancamento == 'D':
                    valor = -valor
                
                # Buscar nome da loja pelo loja_id
                nome_loja = '-'
                if lancamento.loja_id:
                    loja_encontrada = next((loja for loja in lojas_acessiveis if loja['id'] == lancamento.loja_id), None)
                    if loja_encontrada:
                        nome_loja = loja_encontrada['nome']
                
                results.append({
                    'Data': lancamento.data_lancamento.strftime('%d/%m/%Y %H:%M'),
                    'Tipo': 'Crédito' if lancamento.tipo_lancamento == 'C' else 'Débito',
                    'Valor (R$)': valor,
                    'Descrição': lancamento.descricao or '-',
                    'Status': lancamento.status or '-',
                    'Loja': nome_loja
                })
            
            # Coletar nomes únicos das lojas para o rodapé
            lojas_incluidas = [loja['nome'] for loja in lojas_acessiveis if loja['id'] in lojas_para_consulta]
            
            # Definir colunas monetárias para formatação
            colunas_monetarias = ['Valor (R$)']
            
            nome_arquivo = f"lancamentos_manuais_{data_recebimento.replace('/', '')}_{datetime.now().strftime('%H%M%S')}"
            
            if formato == 'excel':
                return exportar_excel(
                    nome_arquivo=nome_arquivo,
                    dados=results,
                    titulo=f"Lançamentos Manuais {data_recebimento}",
                    colunas_monetarias=colunas_monetarias,
                    lojas_incluidas=lojas_incluidas
                )
            elif formato == 'csv':
                return exportar_csv(
                    nome_arquivo=nome_arquivo,
                    dados=results,
                    lojas_incluidas=lojas_incluidas
                )
            elif formato == 'pdf':
                return exportar_pdf(
                    nome_arquivo=nome_arquivo,
                    dados=results,
                    titulo=f"Lançamentos Manuais - {data_recebimento}",
                    colunas_monetarias=colunas_monetarias,
                    lojas_incluidas=lojas_incluidas
                )
            else:
                return JsonResponse({'error': 'Formato não suportado'}, status=400)
                    
        except Exception as e:
            return JsonResponse({'error': f'Erro na exportação: {str(e)}'}, status=500)
