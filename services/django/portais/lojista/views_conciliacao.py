"""
Views para conciliação no portal lojista.
"""

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
from wallclub_core.utilitarios.log_control import registrar_log


class LojistaConciliacaoView(LojistaAccessMixin, LojistaDataMixin, TemplateView):
    """View para página de conciliação do lojista"""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.session.get('lojista_authenticated'):
            return redirect('lojista:login')
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request):
        """Renderizar página de conciliação"""
        # Obter lojas acessíveis usando serviço centralizado
        from portais.controle_acesso.models import PortalUsuario
        from portais.controle_acesso.filtros import FiltrosAcessoService
        
        usuario_id = request.session.get('lojista_usuario_id')
        try:
            usuario = PortalUsuario.objects.get(id=usuario_id)
            lojas_acessiveis = FiltrosAcessoService.obter_lojas_acessiveis(usuario)
        except PortalUsuario.DoesNotExist:
            lojas_acessiveis = []
        
        context = {
            'current_page': 'conciliacao',
            'lojas_acessiveis': lojas_acessiveis,
            'mostrar_filtro_loja': len(lojas_acessiveis) > 1
        }
        
        return render(request, 'portais/lojista/conciliacao.html', context)
    
    def post(self, request):
        """Processar consulta de conciliação via AJAX"""
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            try:
                # Capturar parâmetros
                data_inicio = request.POST.get('data_inicio')
                data_fim = request.POST.get('data_fim')
                loja_selecionada = request.POST.get('loja')
                nsu = request.POST.get('nsu', '').strip()
                incluir_tef = request.POST.get('incluir_tef') == 'on'
                
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
                
                # Determinar quais lojas consultar
                # Lógica simplificada - permitir acesso a todas as lojas disponíveis
                # if tipo_usuario in ['vendedor', 'lojista']:
                #     lojas_para_consulta = [ids_lojas[0]] if ids_lojas else []
                # else:
                if True:
                    # Usuários com acesso múltiplo
                    if loja_selecionada and loja_selecionada != 'todas' and int(loja_selecionada) in loja_ids_acesso:
                        lojas_para_consulta = [int(loja_selecionada)]
                    else:
                        lojas_para_consulta = loja_ids_acesso
                
                if not lojas_para_consulta:
                    return JsonResponse({'error': 'Acesso negado'}, status=403)
                
                # Construir query com JOIN
                where_conditions = []
                params = []
                
                # Filtro de loja
                if len(lojas_para_consulta) == 1:
                    where_conditions.append("btg.var6 = %s")
                    params.append(lojas_para_consulta[0])
                else:
                    placeholders = ','.join(['%s'] * len(lojas_para_consulta))
                    where_conditions.append(f"btg.var6 IN ({placeholders})")
                    params.extend(lojas_para_consulta)
                
                # Filtros de data - converter formato se necessário
                if data_inicio:
                    try:
                        # Se data vem no formato YYYY-MM-DD, usar diretamente
                        if '-' in data_inicio and len(data_inicio) == 10:
                            where_conditions.append("btg.data_transacao >= %s")
                            params.append(f"{data_inicio} 00:00:00")
                        else:
                            # Converter DD/MM/YYYY para YYYY-MM-DD
                            data_obj = datetime.strptime(data_inicio, '%d/%m/%Y')
                            data_formatada = data_obj.strftime('%Y-%m-%d')
                            where_conditions.append("btg.data_transacao >= %s")
                            params.append(f"{data_formatada} 00:00:00")
                    except ValueError:
                        where_conditions.append("btg.data_transacao >= %s")
                        params.append(f"{data_inicio} 00:00:00")
                
                if data_fim:
                    try:
                        # Se data vem no formato YYYY-MM-DD, usar diretamente
                        if '-' in data_fim and len(data_fim) == 10:
                            where_conditions.append("btg.data_transacao <= %s")
                            params.append(f"{data_fim} 23:59:59")
                        else:
                            # Converter DD/MM/YYYY para YYYY-MM-DD
                            data_obj = datetime.strptime(data_fim, '%d/%m/%Y')
                            data_formatada = data_obj.strftime('%Y-%m-%d')
                            where_conditions.append("btg.data_transacao <= %s")
                            params.append(f"{data_formatada} 23:59:59")
                    except ValueError:
                        where_conditions.append("btg.data_transacao <= %s")
                        params.append(f"{data_fim} 23:59:59")
                
                # Filtro de NSU
                if nsu:
                    where_conditions.append("pep.NsuOperacao LIKE %s")
                    params.append(f"%{nsu}%")
                
                # Filtro TEF - se não incluir TEF, filtrar apenas transações não-TEF
                if not incluir_tef:
                    where_conditions.append("(btg.var130 != 'TEF' OR btg.var130 IS NULL)")
                
                # Montar WHERE clause
                where_clause = " AND ".join(where_conditions)
                
                # Query completa com JOIN e deduplicação
                sql = f"""
                SELECT 
                    DATE_FORMAT(t.data_transacao, '%%d/%%m/%%Y')       AS `Data`,
                    t.var43                                            AS `Dt_credito`,
                    t.var45                                            AS `Dt_pagto`,
                    CASE 
                        WHEN t.var70 = '0001-01-01T00:00:00' OR t.var70 IS NULL
                            THEN NULL
                        ELSE DATE_FORMAT(STR_TO_DATE(LEFT(t.var70, 10), '%%Y-%%m-%%d'), '%%d/%%m/%%Y')
                    END                                                AS `Dt_cancelamento`,
                    t.var5                                             AS `Filial`,
                    CAST(t.var6 AS UNSIGNED)                           AS `Cod_Estab`,
                    t.var2                                             AS `Terminal`,
                    t.NsuOperacao                                      AS `NSU`,
                    t.CodAutorizAdquirente                             AS `Autorizacao`,
                    CAST(t.NumeroParcela AS UNSIGNED)                  AS `Parcela`,
                    CAST(t.var13 AS UNSIGNED)                          AS `Prazo_Total`,
                    CAST(t.var19 AS DECIMAL(10,2))                     AS `Vl_Bruto`,
                    CAST(t.var37 AS DECIMAL(10,2))                     AS `Tx_Adm_R`,
                    CAST(t.var42 AS DECIMAL(10,2))                     AS `Vl_Liq`,
                    CASE 
                        WHEN t.var70 = '0001-01-01T00:00:00' OR t.var70 IS NULL
                             THEN 0
                        ELSE CAST(t.ValorBruto AS DECIMAL(10,2))
                    END                                                AS `Vl_Canc`, 
                    CAST(t.var36 AS DECIMAL(10,2))*100                 AS `Tx_Adm_Perc`,
                    CAST(t.var44 AS DECIMAL(10,2))                     AS `Vl_Liq_Pago`,
                    CAST(t.var40 AS DECIMAL(10,2))*100                 AS `Tx_Antec_Per`,
                    CAST(t.var41 AS DECIMAL(10,2))                     AS `Custo_Antec`,
                    CAST(t.var39 AS DECIMAL(10,2))*100                 AS `Tx_Antec_AM`,
                    t.var121                                           AS `Status_Pagto`,
                    t.var8                                             AS `Plano`,
                    t.var12                                            AS `Bandeira`,
                    t.var68                                            AS `Status_Trans`,
                    t.var10                                            AS `NOP`
                FROM (
                    SELECT 
                        btg.*,
                        pep.NsuOperacao,
                        pep.CodAutorizAdquirente,
                        pep.NumeroParcela,
                        pep.ValorBruto,
                        ROW_NUMBER() OVER (PARTITION BY btg.var9, pep.NumeroParcela ORDER BY btg.id DESC) as rn
                    FROM baseTransacoesGestao btg
                    INNER JOIN pinbankExtratoPOS pep ON btg.idFilaExtrato = pep.id
                    WHERE {where_clause}
                ) t
                WHERE t.rn = 1
                ORDER BY t.data_transacao DESC
                LIMIT 5000
                """
                
                # Executar query
                with connection.cursor() as cursor:
                    cursor.execute(sql, params)
                    columns = [col[0] for col in cursor.description]
                    results = []
                    
                    for row in cursor.fetchall():
                        row_dict = dict(zip(columns, row))
                        
                        # Datas já vem formatadas do SQL
                        # Apenas copiar para campos _formatada para compatibilidade com template
                        for campo in ['Data', 'Dt_credito', 'Dt_pagto', 'Dt_cancelamento']:
                            row_dict[f'{campo}_formatada'] = row_dict.get(campo) or '-'
                        
                        results.append(row_dict)
                
                # Renderizar HTML
                html = self._render_conciliacao_html(results)
                
                # Contar registros únicos
                total_registros = len(results)
                
                return JsonResponse({
                    'success': True,
                    'html': html,
                    'total': total_registros
                })
                    
            except Exception as e:
                registrar_log('portais.lojista', f"CONCILIACAO - Erro na consulta: {e}", nivel='ERROR')
                return JsonResponse({'error': f'Erro na consulta: {e}'}, status=500)
        
        # Se não for AJAX, redirecionar para GET
        return redirect('lojista:conciliacao')
    
    def _render_conciliacao_html(self, conciliacoes):
        """Renderizar HTML da conciliação"""
        if not conciliacoes:
            return '<div class="alert alert-info mt-3">Nenhum registro encontrado com os filtros informados.</div>'
        
        # Tabela de conciliação
        html = '''
        <div class="table-responsive">
            <table class="table table-striped table-hover" style="font-size: 0.70rem;">
                <thead class="table-dark">
                    <tr>
                        <th>Data</th>
                        <th>Dt Crédito</th>
                        <th>Dt Pagto</th>
                        <th>Dt Cancel.</th>
                        <th>Filial</th>
                        <th>Cód.Estab.</th>
                        <th>Terminal</th>
                        <th>NSU</th>
                        <th>Autorização</th>
                        <th>Parcela</th>
                        <th>Prazo Total</th>
                        <th>Vl.Bruto(R$)</th>
                        <th>Tx.Adm.(R$)</th>
                        <th>Vl.Líq.(R$)</th>
                        <th>Vl.Canc</th>
                        <th>Tx.Adm(%)</th>
                        <th>Vl.Líq.Pago(R$)</th>
                        <th>Tx.Antec(% per)</th>
                        <th>Custo Antec(R$)</th>
                        <th>Tx.Antec(%a.m.)</th>
                        <th>Status Pagto</th>
                        <th>Plano</th>
                        <th>Bandeira</th>
                        <th>Status Trans</th>
                        <th>NOP</th>
                    </tr>
                </thead>
                <tbody>
        '''
        
        for conciliacao in conciliacoes:
            html += f'''
            <tr>
                <td>{conciliacao.get("Data_formatada", "-")}</td>
                <td>{conciliacao.get("Dt_credito_formatada", "-")}</td>
                <td>{conciliacao.get("Dt_pagto_formatada", "-")}</td>
                <td>{conciliacao.get("Dt_cancelamento_formatada", "-")}</td>
                <td>{conciliacao.get("Filial", "-")}</td>
                <td>{conciliacao.get("Cod_Estab", "-")}</td>
                <td>{conciliacao.get("Terminal", "-")}</td>
                <td>{conciliacao.get("NSU", "-")}</td>
                <td>{conciliacao.get("Autorizacao", "-")}</td>
                <td>{conciliacao.get("Parcela", "-")}</td>
                <td>{conciliacao.get("Prazo_Total", "-")}</td>
                <td>R$ {float(conciliacao.get("Vl_Bruto", 0)):,.2f}</td>
                <td>R$ {float(conciliacao.get("Tx_Adm_R", 0)):,.2f}</td>
                <td>R$ {float(conciliacao.get("Vl_Liq", 0)):,.2f}</td>
                <td>R$ {float(conciliacao.get("Vl_Canc", 0)):,.2f}</td>
                <td>{float(conciliacao.get("Tx_Adm_Perc", 0)):,.2f}%</td>
                <td>R$ {float(conciliacao.get("Vl_Liq_Pago", 0)):,.2f}</td>
                <td>{float(conciliacao.get("Tx_Antec_Per", 0)):,.2f}%</td>
                <td>R$ {float(conciliacao.get("Custo_Antec", 0)):,.2f}</td>
                <td>{float(conciliacao.get("Tx_Antec_AM", 0)):,.2f}%</td>
                <td>{conciliacao.get("Status_Pagto", "-")}</td>
                <td>{conciliacao.get("Plano", "-")}</td>
                <td>{conciliacao.get("Bandeira", "-")}</td>
                <td>{conciliacao.get("Status_Trans", "-")}</td>
                <td>{conciliacao.get("NOP", "-")}</td>
            </tr>
            '''
        
        html += '</tbody></table></div>'
        
        return html


class LojistaConciliacaoExportView(View):
    """View para exportação de dados de conciliação"""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.session.get('lojista_authenticated'):
            return redirect('lojista:login')
        return super().dispatch(request, *args, **kwargs)
    
    def post(self, request):
        from wallclub_core.utilitarios.export_utils import exportar_excel, exportar_csv, exportar_pdf
        from django.db import connection
        from django.http import JsonResponse
        from datetime import datetime
        
        try:
            # Obter lojas acessíveis usando serviço centralizado
            from portais.controle_acesso.models import PortalUsuario
            from portais.controle_acesso.filtros import FiltrosAcessoService
            
            usuario_id = request.session.get('lojista_usuario_id')
            try:
                usuario = PortalUsuario.objects.get(id=usuario_id)
                lojas_acessiveis = FiltrosAcessoService.obter_lojas_acessiveis(usuario)
                loja_ids = [loja['id'] for loja in lojas_acessiveis] if lojas_acessiveis else []
            except PortalUsuario.DoesNotExist:
                loja_ids = []
            
            # Determinar quais lojas consultar
            # Lógica simplificada - usar todas as lojas disponíveis
            lojas_para_consulta = loja_ids
            
            if not lojas_para_consulta:
                return JsonResponse({'error': 'Acesso negado'}, status=403)
            
            # Capturar parâmetros
            data_inicio = request.POST.get('data_inicio')
            data_fim = request.POST.get('data_fim')
            nsu = request.POST.get('nsu', '').strip()
            loja_selecionada = request.POST.get('loja', 'todas')
            formato = request.POST.get('export_format', 'excel')
            
            # Determinar lojas para a query
            if loja_selecionada != 'todas' and int(loja_selecionada) in lojas_para_consulta:
                lojas_query = [int(loja_selecionada)]
            else:
                lojas_query = lojas_para_consulta
            
            # Capturar parâmetros (incluindo incluir_tef)
            incluir_tef = request.POST.get('incluir_tef') == 'on'
            
            # Construir WHERE conditions
            where_conditions = []
            params = []
            
            # Filtro de loja
            where_conditions.append("btg.var6 IN %s")
            params.append(tuple(lojas_query))
            
            # Filtro TEF - usar mesma lógica da view principal
            if not incluir_tef:
                where_conditions.append("(btg.var130 != 'TEF' OR btg.var130 IS NULL)")
            
            # Verificar total de registros primeiro
            sql_count = """
            SELECT COUNT(DISTINCT btg.id)
            FROM baseTransacoesGestao btg
            INNER JOIN pinbankExtratoPOS pep ON btg.idFilaExtrato = pep.id
            """
            
            # Parâmetros apenas para o count (sem formatos de data)
            params_count = params.copy()
            
            # Aplicar filtros de data ao count
            where_conditions_count = where_conditions.copy()
            if data_inicio:
                try:
                    if '-' in data_inicio and len(data_inicio) == 10:
                        where_conditions_count.append("btg.data_transacao >= %s")
                        params_count.append(f"{data_inicio} 00:00:00")
                    else:
                        data_obj = datetime.strptime(data_inicio, '%d/%m/%Y')
                        where_conditions_count.append("btg.data_transacao >= %s")
                        params_count.append(f"{data_obj.strftime('%Y-%m-%d')} 00:00:00")
                except ValueError:
                    where_conditions_count.append("btg.data_transacao >= %s")
                    params_count.append(f"{data_inicio} 00:00:00")
            
            if data_fim:
                try:
                    if '-' in data_fim and len(data_fim) == 10:
                        where_conditions_count.append("btg.data_transacao <= %s")
                        params_count.append(f"{data_fim} 23:59:59")
                    else:
                        data_obj = datetime.strptime(data_fim, '%d/%m/%Y')
                        where_conditions_count.append("btg.data_transacao <= %s")
                        params_count.append(f"{data_obj.strftime('%Y-%m-%d')} 23:59:59")
                except ValueError:
                    where_conditions_count.append("btg.data_transacao <= %s")
                    params_count.append(f"{data_fim} 23:59:59")
            
            if nsu:
                where_conditions_count.append("pep.NsuOperacao LIKE %s")
                params_count.append(f'%{nsu}%')
            
            # Executar count
            if where_conditions_count:
                sql_count += f" WHERE {' AND '.join(where_conditions_count)}"
            
            with connection.cursor() as cursor:
                cursor.execute(sql_count, params_count)
                total_registros = cursor.fetchone()[0]
            
            registrar_log('portais.lojista', f"CONCILIACAO - Export {formato} - Total registros: {total_registros}")
            
            # Se mais de 5000 registros, processar em background e enviar por email
            if total_registros > 5000:
                return self._processar_export_grande(request, where_conditions, params, total_registros, formato, lojas_query, data_inicio, data_fim, nsu, incluir_tef)
            
            # Construir SQL (usar mesma estrutura da view principal)
            sql = """
            SELECT DISTINCT
                btg.data_transacao                           AS `Data`,
                STR_TO_DATE(btg.var43, '%%d/%%m/%%Y')       AS `Dt_credito`,
                STR_TO_DATE(btg.var45, '%%d/%%m/%%Y')       AS `Dt_pagto`,
                CASE 
                    WHEN btg.var70 = '0001-01-01T00:00:00'
                        OR btg.var70 IS NULL
                        THEN NULL
                    ELSE STR_TO_DATE(LEFT(btg.var70, 10), '%%Y-%%m-%%d')
                END                                          AS `Dt_cancelamento`,
                btg.var5                                     AS `Filial`,
                CAST(btg.var6 AS DECIMAL(3,0))              AS `Cod_Estab`,
                btg.var2                                     AS `Terminal`,
                pep.NsuOperacao                              AS `NSU`,
                pep.CodAutorizAdquirente                     AS `Autorizacao`,
                CAST(pep.NumeroParcela AS DECIMAL(3,0))      AS `Parcela`,
                CAST(btg.var13 AS DECIMAL(3,0))              AS `Prazo_Total`,
                CAST(btg.var19 AS DECIMAL(10,2))             AS `Vl_Bruto`,
                CAST(btg.var37 AS DECIMAL(10,2))             AS `Tx_Adm_R`,
                CAST(btg.var42 AS DECIMAL(10,2))             AS `Vl_Liq`,
                CASE 
                    WHEN btg.var70 = '0001-01-01T00:00:00' 
                         OR btg.var70 IS NULL 
                         THEN 0
                    ELSE CAST(pep.ValorBruto AS DECIMAL(10,2))
                END                                          AS `Vl_Canc`, 
                CAST(btg.var36 AS DECIMAL(10,2))*100         AS `Tx_Adm_Perc`,
                CAST(btg.var44 AS DECIMAL(10,2))             AS `Vl_Liq_Pago`,
                CAST(btg.var40 AS DECIMAL(10,2))*100         AS `Tx_Antec_Per`,
                CAST(btg.var41 AS DECIMAL(10,2))             AS `Custo_Antec`,
                CAST(btg.var39 AS DECIMAL(10,2))*100         AS `Tx_Antec_AM`,
                btg.var121                                   AS `Status_Pagto`,
                btg.var8                                     AS `Plano`,
                btg.var12                                    AS `Bandeira`,
                btg.var68                                    AS `Status_Trans`,
                btg.var10                                    AS `NOP`
            FROM baseTransacoesGestao btg
            INNER JOIN pinbankExtratoPOS pep ON btg.idFilaExtrato = pep.id
            """
            
            # Aplicar filtros de data - usar mesma lógica da view principal
            if data_inicio:
                try:
                    # Se data vem no formato YYYY-MM-DD, usar diretamente
                    if '-' in data_inicio and len(data_inicio) == 10:
                        where_conditions.append("btg.data_transacao >= %s")
                        params.append(f"{data_inicio} 00:00:00")
                    else:
                        # Converter DD/MM/YYYY para YYYY-MM-DD
                        data_obj = datetime.strptime(data_inicio, '%d/%m/%Y')
                        data_formatada = data_obj.strftime('%Y-%m-%d')
                        where_conditions.append("btg.data_transacao >= %s")
                        params.append(f"{data_formatada} 00:00:00")
                except ValueError:
                    where_conditions.append("btg.data_transacao >= %s")
                    params.append(f"{data_inicio} 00:00:00")
            
            if data_fim:
                try:
                    # Se data vem no formato YYYY-MM-DD, usar diretamente
                    if '-' in data_fim and len(data_fim) == 10:
                        where_conditions.append("btg.data_transacao <= %s")
                        params.append(f"{data_fim} 23:59:59")
                    else:
                        # Converter DD/MM/YYYY para YYYY-MM-DD
                        data_obj = datetime.strptime(data_fim, '%d/%m/%Y')
                        data_formatada = data_obj.strftime('%Y-%m-%d')
                        where_conditions.append("btg.data_transacao <= %s")
                        params.append(f"{data_formatada} 23:59:59")
                except ValueError:
                    where_conditions.append("btg.data_transacao <= %s")
                    params.append(f"{data_fim} 23:59:59")
            
            # Filtro NSU
            if nsu:
                where_conditions.append("pep.NsuOperacao LIKE %s")
                params.append(f'%{nsu}%')
            
            # Finalizar SQL
            if where_conditions:
                sql += f" WHERE {' AND '.join(where_conditions)}"
            sql += " ORDER BY btg.data_transacao DESC"
            
            # Executar query
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                columns = [col[0] for col in cursor.description]
                results = []
                
                for row in cursor.fetchall():
                    row_dict = dict(zip(columns, row))
                    results.append(row_dict)
            
            registrar_log('portais.lojista', f"CONCILIACAO - Exportação {formato} - {len(results)} registros")
            
            # Preparar dados para exportação
            lojas_incluidas = f"Lojas: {', '.join(map(str, lojas_query))}"
            nome_arquivo = f"conciliacao_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            if formato == 'excel':
                # Converter lista de colunas para dict de cabeçalhos
                cabecalhos_dict = {col: col for col in columns}
                return exportar_excel(
                    nome_arquivo=nome_arquivo,
                    dados=results,
                    titulo="Conciliação Portal Lojista",
                    cabecalhos=cabecalhos_dict,
                    lojas_incluidas=[lojas_incluidas]
                )
            elif formato == 'csv':
                return exportar_csv(
                    nome_arquivo=nome_arquivo,
                    dados=results,
                    lojas_incluidas=[lojas_incluidas]
                )
            elif formato == 'pdf':
                return exportar_pdf(
                    nome_arquivo=nome_arquivo,
                    dados=results,
                    titulo="Relatório de Conciliação - Portal Lojista",
                    lojas_incluidas=[lojas_incluidas]
                )
            else:
                return JsonResponse({'error': 'Formato não suportado'}, status=400)
                
        except Exception as e:
            return JsonResponse({'error': f'Erro na exportação: {str(e)}'}, status=500)
    
    def _processar_export_grande(self, request, where_conditions, params, total_registros, formato, lojas_query, data_inicio, data_fim, nsu, incluir_tef):
        """Processar export grande em background com envio por email"""
        import threading
        
        # Processar em background
        thread = threading.Thread(
            target=self._executar_export_background,
            args=(request, where_conditions, params, total_registros, formato, lojas_query, data_inicio, data_fim, nsu, incluir_tef)
        )
        thread.start()
        
        return JsonResponse({
            'success': True,
            'message': f'Export iniciado em background. Arquivo CSV com {total_registros:,} registros será enviado por email.'
        })
    
    def _executar_export_background(self, request, where_conditions, params, total_registros, formato, lojas_query, data_inicio, data_fim, nsu, incluir_tef):
        """Executar export em background e enviar por email"""
        try:
            from django.conf import settings
            from wallclub_core.integracoes.email_service import EmailService
            import tempfile
            import os
            from datetime import datetime
            
            registrar_log('portais.lojista', f"CONCILIACAO - Export grande iniciado - {total_registros} registros")
            
            # Criar arquivo temporário
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as temp_file:
                temp_path = temp_file.name
                
                # Cabeçalho CSV
                colunas_csv = [
                    'Data', 'Dt_credito', 'Dt_pagto', 'Dt_cancelamento', 'Filial', 'Cod_Estab',
                    'Terminal', 'NSU', 'Autorizacao', 'Parcela', 'Prazo_Total', 'Vl_Bruto',
                    'Tx_Adm_R', 'Vl_Liq', 'Vl_Canc', 'Tx_Adm_Perc', 'Vl_Liq_Pago',
                    'Tx_Antec_Per', 'Custo_Antec', 'Tx_Antec_AM', 'Status_Pagto',
                    'Plano', 'Bandeira', 'Status_Trans', 'NOP'
                ]
                temp_file.write(';'.join(colunas_csv) + '\n')
                
                # Processar em lotes de 1000
                lote_size = 1000
                total_lotes = (total_registros + lote_size - 1) // lote_size
                
                for lote in range(total_lotes):
                    offset = lote * lote_size
                    registrar_log('portais.lojista', f"CONCILIACAO - Processando lote {lote + 1}/{total_lotes}")
                    
                    # SQL com LIMIT e OFFSET
                    sql_lote = """
                    SELECT DISTINCT
                        btg.data_transacao                           AS `Data`,
                        STR_TO_DATE(btg.var43, '%%d/%%m/%%Y')       AS `Dt_credito`,
                        STR_TO_DATE(btg.var45, '%%d/%%m/%%Y')       AS `Dt_pagto`,
                        CASE 
                            WHEN btg.var70 = '0001-01-01T00:00:00'
                                OR btg.var70 IS NULL
                                THEN NULL
                            ELSE STR_TO_DATE(LEFT(btg.var70, 10), '%%Y-%%m-%%d')
                        END                                          AS `Dt_cancelamento`,
                        btg.var5                                     AS `Filial`,
                        CAST(btg.var6 AS DECIMAL(3,0))              AS `Cod_Estab`,
                        btg.var2                                     AS `Terminal`,
                        pep.NsuOperacao                              AS `NSU`,
                        pep.CodAutorizAdquirente                     AS `Autorizacao`,
                        CAST(pep.NumeroParcela AS DECIMAL(3,0))      AS `Parcela`,
                        CAST(btg.var13 AS DECIMAL(3,0))              AS `Prazo_Total`,
                        CAST(btg.var19 AS DECIMAL(10,2))             AS `Vl_Bruto`,
                        CAST(btg.var37 AS DECIMAL(10,2))             AS `Tx_Adm_R`,
                        CAST(btg.var42 AS DECIMAL(10,2))             AS `Vl_Liq`,
                        CASE 
                            WHEN btg.var70 = '0001-01-01T00:00:00' 
                                 OR btg.var70 IS NULL 
                                 THEN 0
                            ELSE CAST(pep.ValorBruto AS DECIMAL(10,2))
                        END                                          AS `Vl_Canc`, 
                        CAST(btg.var36 AS DECIMAL(10,2))*100         AS `Tx_Adm_Perc`,
                        CAST(btg.var44 AS DECIMAL(10,2))             AS `Vl_Liq_Pago`,
                        CAST(btg.var40 AS DECIMAL(10,2))*100         AS `Tx_Antec_Per`,
                        CAST(btg.var41 AS DECIMAL(10,2))             AS `Custo_Antec`,
                        CAST(btg.var39 AS DECIMAL(10,2))*100         AS `Tx_Antec_AM`,
                        btg.var121                                   AS `Status_Pagto`,
                        btg.var8                                     AS `Plano`,
                        btg.var12                                    AS `Bandeira`,
                        btg.var68                                    AS `Status_Trans`,
                        btg.var10                                    AS `NOP`
                    FROM baseTransacoesGestao btg
                    INNER JOIN pinbankExtratoPOS pep ON btg.idFilaExtrato = pep.id
                    """
                    
                    # Montar parâmetros do lote (sem formatos de data)
                    params_lote = params.copy()
                    
                    # Aplicar filtros de data
                    where_conditions_lote = where_conditions.copy()
                    if data_inicio:
                        try:
                            if '-' in data_inicio and len(data_inicio) == 10:
                                where_conditions_lote.append("btg.data_transacao >= %s")
                                params_lote.append(f"{data_inicio} 00:00:00")
                            else:
                                data_obj = datetime.strptime(data_inicio, '%d/%m/%Y')
                                where_conditions_lote.append("btg.data_transacao >= %s")
                                params_lote.append(f"{data_obj.strftime('%Y-%m-%d')} 00:00:00")
                        except ValueError:
                            where_conditions_lote.append("btg.data_transacao >= %s")
                            params_lote.append(f"{data_inicio} 00:00:00")
                    
                    if data_fim:
                        try:
                            if '-' in data_fim and len(data_fim) == 10:
                                where_conditions_lote.append("btg.data_transacao <= %s")
                                params_lote.append(f"{data_fim} 23:59:59")
                            else:
                                data_obj = datetime.strptime(data_fim, '%d/%m/%Y')
                                where_conditions_lote.append("btg.data_transacao <= %s")
                                params_lote.append(f"{data_obj.strftime('%Y-%m-%d')} 23:59:59")
                        except ValueError:
                            where_conditions_lote.append("btg.data_transacao <= %s")
                            params_lote.append(f"{data_fim} 23:59:59")
                    
                    if nsu:
                        where_conditions_lote.append("pep.NsuOperacao LIKE %s")
                        params_lote.append(f'%{nsu}%')
                    
                    # Finalizar SQL do lote
                    if where_conditions_lote:
                        sql_lote += f" WHERE {' AND '.join(where_conditions_lote)}"
                    sql_lote += f" ORDER BY btg.data_transacao DESC LIMIT {lote_size} OFFSET {offset}"
                    
                    # Executar query do lote
                    with connection.cursor() as cursor:
                        cursor.execute(sql_lote, params_lote)
                        
                        for row in cursor.fetchall():
                            # Formatar valores para CSV
                            linha_csv = []
                            for valor in row:
                                if valor is None:
                                    linha_csv.append('')
                                elif isinstance(valor, datetime):
                                    linha_csv.append(valor.strftime('%d/%m/%Y'))
                                else:
                                    linha_csv.append(str(valor))
                            
                            temp_file.write(';'.join(linha_csv) + '\n')
            
            # Enviar por email
            usuario_email = request.session.get('lojista_usuario_email', '')
            if not usuario_email:
                registrar_log('portais.lojista', f"CONCILIACAO - ERRO: Email não encontrado na sessão", nivel='ERROR')
                return
            
            nome_arquivo = f"conciliacao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            lojas_texto = f"Lojas: {', '.join(map(str, lojas_query))}"
            
            # Criar email
            assunto = f"Relatório de Conciliação - {total_registros:,} registros"
            corpo = f"""
Olá,

Segue em anexo o relatório de conciliação solicitado.

Detalhes:
- Total de registros: {total_registros:,}
- {lojas_texto}
- Período: {data_inicio or 'Sem filtro'} até {data_fim or 'Sem filtro'}
- TEF incluído: {'Sim' if incluir_tef else 'Não'}
- Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}

Atenciosamente,
Sistema WallClub
            """
            
            # Ler arquivo para anexo
            with open(temp_path, 'rb') as arquivo:
                conteudo_csv = arquivo.read()
            
            # Enviar usando EmailService
            resultado = EmailService.enviar_email(
                destinatarios=[usuario_email],
                assunto=assunto,
                mensagem_texto=corpo,
                anexos=[{
                    'nome': nome_arquivo,
                    'conteudo': conteudo_csv,
                    'tipo': 'text/csv'
                }],
                fail_silently=True
            )
            
            # Remover arquivo temporário
            os.unlink(temp_path)
            
            if resultado['sucesso']:
                registrar_log('portais.lojista', f"CONCILIACAO - Export grande concluído e enviado para {usuario_email}")
            else:
                registrar_log('portais.lojista', f"CONCILIACAO - Erro ao enviar email: {resultado['mensagem']}", nivel='ERROR')
            
        except Exception as e:
            registrar_log('portais.lojista', f"CONCILIACAO - ERRO no export grande: {str(e)}", nivel='ERROR')
