"""
Views do Portal Lojista - Módulo de Cancelamentos
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

from .mixins import LojistaAccessMixin, LojistaDataMixin
from django.apps import apps


class LojistaCancelamentosView(LojistaAccessMixin, LojistaDataMixin, TemplateView):
    """View de cancelamentos"""
    template_name = 'portais/lojista/cancelamentos.html'
    
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
            'current_page': 'cancelamentos',
            'lojas_acessiveis': lojas_acessiveis,
            'mostrar_filtro_loja': len(lojas_acessiveis) > 1
        })
        
        return context
    
    def post(self, request):
        """Processar consulta AJAX de cancelamentos"""
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Parâmetros da consulta
            nsu = request.POST.get('nsu', '').strip()
            data_inicio = request.POST.get('data_inicio', '')
            data_fim = request.POST.get('data_fim', '')
            loja_selecionada = request.POST.get('loja', '')
            
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
                # Construir WHERE clause para SQL
                where_conditions = []
                params = []
                
                # Filtro de lojas
                if len(lojas_para_consulta) == 1:
                    where_conditions.append("var6 = %s")
                    params.append(lojas_para_consulta[0])
                else:
                    placeholders = ','.join(['%s'] * len(lojas_para_consulta))
                    where_conditions.append(f"var6 IN ({placeholders})")
                    params.extend(lojas_para_consulta)
                
                # CANCELAMENTOS: var68 != 'TRANS. APROVADO'
                where_conditions.append("var68 != %s")
                params.append('TRANS. APROVADO')
                
                # Filtro de NSU
                if nsu:
                    where_conditions.append("var9 LIKE %s")
                    params.append(f"%{nsu}%")
                
                # Filtros de data
                if data_inicio:
                    where_conditions.append("data_transacao >= %s")
                    params.append(f"{data_inicio} 00:00:00")
                
                if data_fim:
                    where_conditions.append("data_transacao <= %s")
                    params.append(f"{data_fim} 23:59:59")
                
                where_clause = " AND ".join(where_conditions)
                
                # Query otimizada com ROW_NUMBER
                sql = f"""
                    SELECT 
                        data_transacao,
                        var5 as nome_loja,
                        var6 as loja_id,
                        var8 as plano,
                        var9 as nsu,
                        var10 as nop,
                        var13 as parcelas,
                        var19 as vl_bruto,
                        var37 as taxa_adm,
                        var41 as custo_antec,
                        var42 as vl_liq_previsto,
                        var43,
                        var44 as vl_liq_pago,
                        var45,
                        var68 as status,
                        var121 as status_pgto
                    FROM (
                        SELECT *,
                               ROW_NUMBER() OVER (PARTITION BY var9 ORDER BY id DESC) as rn
                        FROM baseTransacoesGestao
                        WHERE {where_clause}
                    ) t WHERE rn = 1
                    ORDER BY data_transacao DESC
                    LIMIT 1000
                """
                
                # Executar query e processar
                results = []
                with connection.cursor() as cursor:
                    cursor.execute(sql, params)
                    rows = cursor.fetchall()
                    
                    for row in rows:
                        data_transacao, nome_loja, loja_id, plano, nsu, nop, parcelas, vl_bruto, taxa_adm, custo_antec, vl_liq_previsto, var43, vl_liq_pago, var45, status, status_pgto = row
                        
                        # Data e hora formatadas
                        data_formatada = data_transacao.strftime('%d/%m/%Y') if data_transacao else '-'
                        hora_formatada = data_transacao.strftime('%H:%M:%S') if data_transacao else '-'
                        
                        # Data pagamento
                        data_pgto = var45 if var45 else var43
                        
                        # Valor líquido pago (se zero, usar previsto)
                        vl_liq_pago_final = float(vl_liq_pago or 0) if vl_liq_pago and float(vl_liq_pago) != 0 else float(vl_liq_previsto or 0)
                        
                        results.append({
                            'Loja': (nome_loja or '-')[:10],
                            'Data': data_formatada,
                            'Hora': hora_formatada,
                            'Vl Bruto(R$)': float(vl_bruto or 0),
                            'Vl Liq Previsto(R$)': float(vl_liq_previsto or 0),
                            'Vl Liq Pago(R$)': vl_liq_pago_final,
                            'Status Pgto': status_pgto or '-',
                            'Data Pgto': data_pgto or '-',
                            'Plano': plano or '-',
                            'Núm. Parcelas': int(parcelas or 0),
                            'Taxa Adm(R$)': float(taxa_adm or 0),
                            'Custo Antec(R$)': float(custo_antec or 0),
                            'Status Trans.': status or '-',
                            'NSU': nsu or '-',
                            'NOP': nop or '-'
                        })
                
                # Calcular total diretamente no SQL
                sql_total = f"""
                    SELECT SUM(CAST(var19 AS DECIMAL(15,2))) as total_cancelado
                    FROM (
                        SELECT var19,
                               ROW_NUMBER() OVER (PARTITION BY var9 ORDER BY id DESC) as rn
                        FROM baseTransacoesGestao
                        WHERE {where_clause}
                    ) t WHERE rn = 1
                """
                
                with connection.cursor() as cursor:
                    cursor.execute(sql_total, params)
                    total_row = cursor.fetchone()
                
                totais = {
                    'total_cancelado': float(total_row[0] or 0)
                }
                
                # Renderizar HTML
                html = self._render_cancelamentos_html(results, totais)
                
                return JsonResponse({
                    'success': True,
                    'html': html,
                    'total': len(results)
                })
                
            except Exception as e:
                return JsonResponse({'error': f'Erro na consulta: {str(e)}'}, status=500)
        
        return self.get(request)
    
    def _render_cancelamentos_html(self, vendas, totais):
        """Renderizar HTML dos cancelamentos"""
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
        
        if not vendas:
            return '<div class="alert alert-info mt-3">Nenhum cancelamento encontrado com os filtros informados.</div>'
        
        # Cards de totais - APENAS TOTAL CANCELADO
        html = '<div class="row mt-3 mb-3">'
        
        cards = [
            ('Total Cancelado', totais['total_cancelado'], 'bg-danger')
        ]
        
        for titulo, valor, classe in cards:
            html += f'''
            <div class="col-md-6 offset-md-3">
                <div class="card {classe} text-white">
                    <div class="card-body py-2 text-center">
                        <h5 class="card-title" style="font-size: 14px; margin-bottom: 5px;">{titulo}</h5>
                        <h3 class="card-text" style="font-size: 18px; margin-bottom: 0;">R$ {valor:,.2f}</h3>
                    </div>
                </div>
            </div>
            '''
        
        html += '</div>'
        
        # Tabela de cancelamentos
        html += '''
        <div class="table-responsive">
            <table class="table table-striped table-hover" style="font-size: 0.75rem;">
                <thead class="table-dark">
                    <tr>
                        <th>Loja</th>
                        <th>Data</th>
                        <th>Hora</th>
                        <th>Vl Bruto(R$)</th>
                        <th>Vl Liq Previsto(R$)</th>
                        <th>Vl Liq Pago(R$)</th>
                        <th>Status Pgto</th>
                        <th>Data Pgto</th>
                        <th>Plano</th>
                        <th>Núm. Parcelas</th>
                        <th>Taxa Adm(R$)</th>
                        <th>NSU</th>
                        <th>Status Trans.</th>
                    </tr>
                </thead>
                <tbody>
        '''
        
        for venda in vendas:
            html += f'''
            <tr>
                <td>{venda.get("Loja", "-")}</td>
                <td>{venda.get("Data", "-")}</td>
                <td>{venda.get("Hora", "-")}</td>
                <td>R$ {safe_float_convert(venda.get("Vl Bruto(R$)", 0)):,.2f}</td>
                <td>R$ {safe_float_convert(venda.get("Vl Liq Previsto(R$)", 0)):,.2f}</td>
                <td>R$ {safe_float_convert(venda.get("Vl Liq Pago(R$)", 0)):,.2f}</td>
                <td>{venda.get("Status Pgto", "-")}</td>
                <td>{venda.get("Data Pgto", "-")}</td>
                <td>{venda.get("Plano", "-")}</td>
                <td>{venda.get("Núm. Parcelas", "-")}</td>
                <td>R$ {safe_float_convert(venda.get("Taxa Adm(R$)", 0)):,.2f}</td>
                <td>{venda.get("NSU", "-")}</td>
                <td>{venda.get("Status Trans.", "-")}</td>
            </tr>
            '''
        
        html += '</tbody></table></div>'
        
        return html


class LojistaCancelamentosExportView(View):
    """View para exportação de dados de cancelamentos"""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.session.get('lojista_authenticated'):
            return redirect('lojista:login')
        return super().dispatch(request, *args, **kwargs)
    
    def post(self, request):
        from wallclub_core.utilitarios.export_utils import exportar_excel, exportar_csv, exportar_pdf
        from django.db import connection
        from django.http import JsonResponse
        from datetime import datetime
        
        formato = request.POST.get('formato', 'excel')
        
        # Reutilizar a mesma lógica de filtros da view principal
        nsu = request.POST.get('nsu', '').strip()
        data_inicial = request.POST.get('data_inicio', '')
        data_final = request.POST.get('data_fim', '')
        loja_id = request.POST.get('loja', '')

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

        # Determinar filtro de loja (lógica simplificada)
        if loja_id and loja_id != 'todas' and int(loja_id) in loja_ids_acesso:
            lojas_filtro = [int(loja_id)]
        else:
            lojas_filtro = loja_ids_acesso

        if not lojas_filtro:
            return JsonResponse({'error': 'Acesso negado'}, status=403)

        # Usar Django ORM para exportação
        from django.db.models import Q

        
        # Construir filtros Django - CANCELAMENTOS: var68 != 'TRANS. APROVADO'
        filtros = Q(var6__in=lojas_filtro) & ~Q(var68='TRANS. APROVADO')
        
        if nsu:
            filtros &= Q(var9__icontains=nsu)
        
        if data_inicial:
            filtros &= Q(data_transacao__gte=f"{data_inicial} 00:00:00")
        
        if data_final:
            filtros &= Q(data_transacao__lte=f"{data_final} 23:59:59")
        
        try:
            # Aplicar deduplicação igual ao admin (NOT EXISTS mais eficiente)
            # Usar SQL direto sem modelo
            from wallclub_core.database.queries import TransacoesQueries
            # Query já está sendo construída via SQL raw abaixo
            from gestao_financeira.models import BaseTransacoesGestao
            vendas_queryset = BaseTransacoesGestao.objects.filter(filtros).extra(
                select={'data_transacao': "STR_TO_DATE(var0, '%%d/%%m/%%Y')"},
                where=["""
                    NOT EXISTS (
                        SELECT 1 FROM baseTransacoesGestao b2 
                        WHERE b2.var9 = baseTransacoesGestao.var9 
                        AND b2.id > baseTransacoesGestao.id
                    )
                """],
                order_by=['-data_transacao']
            )
            
            results = []
            for venda in vendas_queryset:
                # Processar dados
                vl_bruto = float(venda.var19 or 0)
                vl_liq_previsto = float(venda.var42 or 0)
                vl_liq_pago = float(venda.var44 or 0) if venda.var44 and float(venda.var44) != 0 else vl_liq_previsto
                taxa_adm = float(venda.var37 or 0)
                custo_antec = float(venda.var41 or 0)
                num_parcelas = int(venda.var13 or 0)
                
                # Data e hora formatadas
                data_formatada = venda.data_transacao.strftime('%d/%m/%Y') if venda.data_transacao else '-'
                hora_formatada = venda.data_transacao.strftime('%H:%M:%S') if venda.data_transacao else '-'
                
                # Data pagamento
                data_pgto = venda.var45 if venda.var45 else venda.var43
                
                # Truncar nome da loja em 10 caracteres
                nome_loja = (venda.var5 or '-')[:10] if venda.var5 else '-'
                
                row_dict = {
                    'Loja': nome_loja,
                    'Data': data_formatada,
                    'Hora': hora_formatada,
                    'Vl Bruto(R$)': vl_bruto,
                    'Vl Liq Previsto(R$)': vl_liq_previsto,
                    'Vl Liq Pago(R$)': vl_liq_pago,
                    'Status Pgto': venda.var121 or '-',
                    'Data Pgto': data_pgto or '-',
                    'Plano': venda.var8 or '-',
                    'Núm. Parcelas': num_parcelas,
                    'Taxa Adm(R$)': taxa_adm,
                    'Custo Antec(R$)': custo_antec,
                    'Status Trans.': venda.var68 or '-',
                    'NSU': venda.var9 or '-',
                    'NOP': venda.var10 or '-'
                }
                results.append(row_dict)
            
            # Coletar nomes únicos das lojas para o rodapé
            lojas_incluidas = list(set([item['Loja'] for item in results if item['Loja'] != '-']))
            lojas_incluidas.sort()  # Ordenar alfabeticamente
            
            # Definir colunas monetárias para formatação
            colunas_monetarias = ['Vl Bruto(R$)', 'Vl Liq Previsto(R$)', 'Vl Liq Pago(R$)', 'Taxa Adm(R$)', 'Custo Antec(R$)']
            
            nome_arquivo = f"cancelamentos_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            if formato == 'excel':
                return exportar_excel(
                    nome_arquivo=nome_arquivo,
                    dados=results,
                    titulo="Cancelamentos Portal Lojista",  # Máximo 30 caracteres
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
                    titulo="Relatório de Cancelamentos - Portal Lojista",
                    colunas_monetarias=colunas_monetarias,
                    lojas_incluidas=lojas_incluidas
                )
            else:
                return JsonResponse({'error': 'Formato não suportado'}, status=400)
                    
        except Exception as e:
            return JsonResponse({'error': f'Erro na exportação: {str(e)}'}, status=500)
