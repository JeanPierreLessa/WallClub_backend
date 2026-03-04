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
                data_pagamento_inicio = request.POST.get('data_pagamento_inicio')
                data_pagamento_fim = request.POST.get('data_pagamento_fim')
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
                    where_conditions.append("btu.var6 = %s")
                    params.append(lojas_para_consulta[0])
                else:
                    placeholders = ','.join(['%s'] * len(lojas_para_consulta))
                    where_conditions.append(f"btu.var6 IN ({placeholders})")
                    params.extend(lojas_para_consulta)

                # Filtros de data de transação - converter formato se necessário
                if data_inicio:
                    try:
                        # Se data vem no formato YYYY-MM-DD, usar diretamente
                        if '-' in data_inicio and len(data_inicio) == 10:
                            where_conditions.append("btu.data_transacao >= %s")
                            params.append(f"{data_inicio} 00:00:00")
                        else:
                            # Converter DD/MM/YYYY para YYYY-MM-DD
                            data_obj = datetime.strptime(data_inicio, '%d/%m/%Y')
                            data_formatada = data_obj.strftime('%Y-%m-%d')
                            where_conditions.append("btu.data_transacao >= %s")
                            params.append(f"{data_formatada} 00:00:00")
                    except ValueError:
                        where_conditions.append("btu.data_transacao >= %s")
                        params.append(f"{data_inicio} 00:00:00")

                if data_fim:
                    try:
                        # Se data vem no formato YYYY-MM-DD, usar diretamente
                        if '-' in data_fim and len(data_fim) == 10:
                            where_conditions.append("btu.data_transacao <= %s")
                            params.append(f"{data_fim} 23:59:59")
                        else:
                            # Converter DD/MM/YYYY para YYYY-MM-DD
                            data_obj = datetime.strptime(data_fim, '%d/%m/%Y')
                            data_formatada = data_obj.strftime('%Y-%m-%d')
                            where_conditions.append("btu.data_transacao <= %s")
                            params.append(f"{data_formatada} 23:59:59")
                    except ValueError:
                        where_conditions.append("btu.data_transacao <= %s")
                        params.append(f"{data_fim} 23:59:59")

                # Filtros de data de pagamento (var45)
                if data_pagamento_inicio:
                    try:
                        # Converter YYYY-MM-DD para DD/MM/YYYY (formato do var45)
                        if '-' in data_pagamento_inicio and len(data_pagamento_inicio) == 10:
                            data_obj = datetime.strptime(data_pagamento_inicio, '%Y-%m-%d')
                            data_formatada_br = data_obj.strftime('%d/%m/%Y')
                            where_conditions.append("STR_TO_DATE(btu.var45, '%%d/%%m/%%Y') >= STR_TO_DATE(%s, '%%d/%%m/%%Y')")
                            params.append(data_formatada_br)
                    except ValueError:
                        pass

                if data_pagamento_fim:
                    try:
                        # Converter YYYY-MM-DD para DD/MM/YYYY (formato do var45)
                        if '-' in data_pagamento_fim and len(data_pagamento_fim) == 10:
                            data_obj = datetime.strptime(data_pagamento_fim, '%Y-%m-%d')
                            data_formatada_br = data_obj.strftime('%d/%m/%Y')
                            where_conditions.append("STR_TO_DATE(btu.var45, '%%d/%%m/%%Y') <= STR_TO_DATE(%s, '%%d/%%m/%%Y')")
                            params.append(data_formatada_br)
                    except ValueError:
                        pass

                # Filtro de NSU
                if nsu:
                    where_conditions.append("btu.var9 LIKE %s")
                    params.append(f"%{nsu}%")

                # Filtro TEF - se não incluir TEF, filtrar apenas transações não-Credenciadora
                if not incluir_tef:
                    where_conditions.append("btu.tipo_operacao != 'Credenciadora'")

                # Montar WHERE clause
                where_clause = " AND ".join(where_conditions)

                # Paginação
                pagina = int(request.POST.get('pagina', 1))
                por_pagina = 200
                offset = (pagina - 1) * por_pagina

                # Contar total de registros primeiro
                sql_count = f"""
                SELECT COUNT(*)
                FROM base_transacoes_unificadas btu
                WHERE {where_clause}
                """

                with connection.cursor() as cursor:
                    cursor.execute(sql_count, params)
                    total_registros = cursor.fetchone()[0]

                total_paginas = (total_registros + por_pagina - 1) // por_pagina

                # Query sem JOIN - dados direto da base unificada
                sql = f"""
                SELECT
                    DATE_FORMAT(btu.data_transacao, '%%d/%%m/%%Y')     AS `Data`,
                    btu.var43                                          AS `Dt_credito`,
                    btu.var45                                          AS `Dt_pagto`,
                    CASE
                        WHEN TRIM(btu.var70) = '0001-01-01T00:00:00' OR btu.var70 IS NULL OR TRIM(btu.var70) = ''
                            THEN NULL
                        ELSE DATE_FORMAT(STR_TO_DATE(LEFT(btu.var70, 10), '%%Y-%%m-%%d'), '%%d/%%m/%%Y')
                    END                                                AS `Dt_cancelamento`,
                    btu.var5                                           AS `Filial`,
                    CAST(btu.var6 AS UNSIGNED)                         AS `Cod_Estab`,
                    btu.var2                                           AS `Terminal`,
                    btu.var9                                           AS `NSU`,
                    btu.authorization_code                             AS `Autorizacao`,
                    CAST(btu.var13 AS SIGNED)                          AS `Prazo_Total`,
                    CAST(btu.var19 AS DECIMAL(10,2))                   AS `Vl_Bruto`,
                    CAST(btu.var37 AS DECIMAL(10,4))                   AS `Tx_Adm_R`,
                    CAST(btu.var42 AS DECIMAL(10,2))                   AS `Vl_Liq`,
                    CASE
                        WHEN TRIM(btu.var70) = '0001-01-01T00:00:00' OR btu.var70 IS NULL OR TRIM(btu.var70) = ''
                             THEN 0
                        ELSE CAST(btu.var19 AS DECIMAL(10,2))
                    END                                                AS `Vl_Canc`,
                    CAST(btu.var36 AS DECIMAL(10,4))                   AS `Tx_Adm_Perc`,
                    CAST(btu.var44 AS DECIMAL(10,2))                   AS `Vl_Liq_Pago`,
                    CAST(btu.var40 AS DECIMAL(10,4))                   AS `Tx_Antec_Per`,
                    CAST(btu.var41 AS DECIMAL(10,2))                   AS `Custo_Antec`,
                    CAST(btu.var39 AS DECIMAL(10,4))                   AS `Tx_Antec_AM`,
                    btu.var121                                         AS `Status_Pagto`,
                    btu.var8                                           AS `Plano`,
                    btu.var12                                          AS `Bandeira`,
                    btu.var68                                          AS `Status_Trans`,
                    btu.var10                                          AS `NOP`
                FROM base_transacoes_unificadas btu
                WHERE {where_clause}
                ORDER BY btu.data_transacao DESC
                LIMIT {por_pagina} OFFSET {offset}
                """

                # Executar query
                with connection.cursor() as cursor:
                    cursor.execute(sql, params)
                    columns = [col[0] for col in cursor.description]
                    results = []

                    for row in cursor.fetchall():
                        row_dict = dict(zip(columns, row))

                        # Substituir None por string vazia em todos os campos
                        row_dict = {k: ('' if v is None else v) for k, v in row_dict.items()}

                        # Datas já vem formatadas do SQL
                        # Apenas copiar para campos _formatada para compatibilidade com template
                        for campo in ['Data', 'Dt_credito', 'Dt_pagto', 'Dt_cancelamento']:
                            valor = row_dict.get(campo)
                            # Tratar datas inválidas como "-"
                            if not valor or valor in ['00/00/0000', '01/01/0001']:
                                row_dict[f'{campo}_formatada'] = '-'
                            else:
                                row_dict[f'{campo}_formatada'] = valor

                        results.append(row_dict)

                # Renderizar HTML
                html = self._render_conciliacao_html(results, pagina, total_paginas, total_registros)

                return JsonResponse({
                    'success': True,
                    'html': html,
                    'total': total_registros,
                    'pagina': pagina,
                    'total_paginas': total_paginas
                })

            except Exception as e:
                registrar_log('portais.lojista', f"CONCILIACAO - Erro na consulta: {e}", nivel='ERROR')
                return JsonResponse({'error': f'Erro na consulta: {e}'}, status=500)

        # Se não for AJAX, redirecionar para GET
        return redirect('lojista:conciliacao')

    def _render_conciliacao_html(self, conciliacoes, pagina, total_paginas, total_registros):
        """Renderizar HTML da conciliação"""
        if not conciliacoes:
            return '<div class="alert alert-info mt-3">Nenhum registro encontrado com os filtros informados.</div>'

        # Tabela de conciliação com cabeçalho fixo
        html = '''
        <div class="conciliacao-container">
            <!-- Cabeçalho fixo -->
            <div class="conciliacao-header">
                <table class="table table-bordered mb-0">
                    <thead>
                        <tr>
                            <th style="width: 90px;">Data</th>
                            <th style="width: 90px;">Dt Crédito</th>
                            <th style="width: 90px;">Dt Pagto</th>
                            <th style="width: 90px;">Dt Cancel.</th>
                            <th style="width: 80px;">Filial</th>
                            <th style="width: 80px;">Cód.Estab.</th>
                            <th style="width: 100px;">Terminal</th>
                            <th style="width: 100px;">NSU</th>
                            <th style="width: 100px;">Autorização</th>
                            <th style="width: 70px;">Parcela</th>
                            <th style="width: 80px;">Prazo Total</th>
                            <th style="width: 100px;">Vl.Bruto(R$)</th>
                            <th style="width: 100px;">Tx.Adm.(R$)</th>
                            <th style="width: 100px;">Vl.Líq.(R$)</th>
                            <th style="width: 90px;">Vl.Canc</th>
                            <th style="width: 90px;">Tx.Adm(%)</th>
                            <th style="width: 110px;">Vl.Líq.Pago(R$)</th>
                            <th style="width: 100px;">Tx.Antec(% per)</th>
                            <th style="width: 110px;">Custo Antec(R$)</th>
                            <th style="width: 100px;">Tx.Antec(%a.m.)</th>
                            <th style="width: 100px;">Status Pagto</th>
                            <th style="width: 80px;">Plano</th>
                            <th style="width: 100px;">Bandeira</th>
                            <th style="width: 100px;">Status Trans</th>
                            <th style="width: 80px;">NOP</th>
                        </tr>
                    </thead>
                </table>
            </div>
            <!-- Corpo com scroll -->
            <div class="conciliacao-body">
                <table class="table table-striped table-bordered table-hover mb-0">
                    <tbody>
        '''

        for conciliacao in conciliacoes:
            # Função helper para converter valores numéricos com segurança
            def safe_float(valor, default=0):
                if valor is None:
                    return default
                try:
                    return float(valor)
                except (ValueError, TypeError):
                    return default

            html += f'''
            <tr>
                <td style="width: 90px;">{conciliacao.get("Data_formatada", "-")}</td>
                <td style="width: 90px;">{conciliacao.get("Dt_credito_formatada", "-")}</td>
                <td style="width: 90px;">{conciliacao.get("Dt_pagto_formatada", "-")}</td>
                <td style="width: 90px;">{conciliacao.get("Dt_cancelamento_formatada", "-")}</td>
                <td style="width: 80px;">{conciliacao.get("Filial", "-")}</td>
                <td style="width: 80px;">{conciliacao.get("Cod_Estab", "-")}</td>
                <td style="width: 100px;">{conciliacao.get("Terminal", "-")}</td>
                <td style="width: 100px;">{conciliacao.get("NSU", "-")}</td>
                <td style="width: 100px;">{conciliacao.get("Autorizacao", "-")}</td>
                <td style="width: 70px;">{conciliacao.get("Parcela", "-")}</td>
                <td style="width: 80px;">{conciliacao.get("Prazo_Total", "-")}</td>
                <td style="width: 100px;">R$ {safe_float(conciliacao.get("Vl_Bruto")):,.2f}</td>
                <td style="width: 100px;">R$ {safe_float(conciliacao.get("Tx_Adm_R")):,.2f}</td>
                <td style="width: 100px;">R$ {safe_float(conciliacao.get("Vl_Liq")):,.2f}</td>
                <td style="width: 90px;">R$ {safe_float(conciliacao.get("Vl_Canc")):,.2f}</td>
                <td style="width: 90px;">{safe_float(conciliacao.get("Tx_Adm_Perc")):,.2f}%</td>
                <td style="width: 110px;">R$ {safe_float(conciliacao.get("Vl_Liq_Pago")):,.2f}</td>
                <td style="width: 100px;">{safe_float(conciliacao.get("Tx_Antec_Per")):,.2f}%</td>
                <td style="width: 110px;">R$ {safe_float(conciliacao.get("Custo_Antec")):,.2f}</td>
                <td style="width: 100px;">{safe_float(conciliacao.get("Tx_Antec_AM")):,.2f}%</td>
                <td style="width: 100px;">{conciliacao.get("Status_Pagto", "-")}</td>
                <td style="width: 80px;">{conciliacao.get("Plano", "-")}</td>
                <td style="width: 100px;">{conciliacao.get("Bandeira", "-")}</td>
                <td style="width: 100px;">{conciliacao.get("Status_Trans", "-")}</td>
                <td style="width: 80px;">{conciliacao.get("NOP", "-")}</td>
            </tr>
            '''

        html += '</tbody></table></div>'

        # Paginação
        html += '<div class="d-flex justify-content-between align-items-center mt-3 px-3">'
        html += f'<div class="text-muted">Mostrando {len(conciliacoes)} de {total_registros} registros (Página {pagina} de {total_paginas})</div>'
        html += '<nav><ul class="pagination mb-0">'

        # Botão Anterior
        if pagina > 1:
            html += f'<li class="page-item"><a class="page-link" href="#" data-pagina="{pagina-1}">Anterior</a></li>'
        else:
            html += '<li class="page-item disabled"><span class="page-link">Anterior</span></li>'

        # Páginas
        inicio = max(1, pagina - 2)
        fim = min(total_paginas, pagina + 2)

        if inicio > 1:
            html += '<li class="page-item"><a class="page-link" href="#" data-pagina="1">1</a></li>'
            if inicio > 2:
                html += '<li class="page-item disabled"><span class="page-link">...</span></li>'

        for p in range(inicio, fim + 1):
            if p == pagina:
                html += f'<li class="page-item active"><span class="page-link">{p}</span></li>'
            else:
                html += f'<li class="page-item"><a class="page-link" href="#" data-pagina="{p}">{p}</a></li>'

        if fim < total_paginas:
            if fim < total_paginas - 1:
                html += '<li class="page-item disabled"><span class="page-link">...</span></li>'
            html += f'<li class="page-item"><a class="page-link" href="#" data-pagina="{total_paginas}">{total_paginas}</a></li>'

        # Botão Próximo
        if pagina < total_paginas:
            html += f'<li class="page-item"><a class="page-link" href="#" data-pagina="{pagina+1}">Próximo</a></li>'
        else:
            html += '<li class="page-item disabled"><span class="page-link">Próximo</span></li>'

        html += '</ul></nav></div></div>'

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
            where_conditions.append("btu.var6 IN %s")
            params.append(tuple(lojas_query))

            # Filtro TEF - usar mesma lógica da view principal
            if not incluir_tef:
                where_conditions.append("btu.tipo_operacao != 'Credenciadora'")

            # Verificar total de registros primeiro
            sql_count = """
            SELECT COUNT(*)
            FROM base_transacoes_unificadas btu
            """

            # Parâmetros apenas para o count (sem formatos de data)
            params_count = params.copy()

            # Aplicar filtros de data ao count
            where_conditions_count = where_conditions.copy()
            if data_inicio:
                try:
                    if '-' in data_inicio and len(data_inicio) == 10:
                        where_conditions_count.append("btu.data_transacao >= %s")
                        params_count.append(f"{data_inicio} 00:00:00")
                    else:
                        data_obj = datetime.strptime(data_inicio, '%d/%m/%Y')
                        where_conditions_count.append("btu.data_transacao >= %s")
                        params_count.append(f"{data_obj.strftime('%Y-%m-%d')} 00:00:00")
                except ValueError:
                    where_conditions_count.append("btu.data_transacao >= %s")
                    params_count.append(f"{data_inicio} 00:00:00")

            if data_fim:
                try:
                    if '-' in data_fim and len(data_fim) == 10:
                        where_conditions_count.append("btu.data_transacao <= %s")
                        params_count.append(f"{data_fim} 23:59:59")
                    else:
                        data_obj = datetime.strptime(data_fim, '%d/%m/%Y')
                        where_conditions_count.append("btu.data_transacao <= %s")
                        params_count.append(f"{data_obj.strftime('%Y-%m-%d')} 23:59:59")
                except ValueError:
                    where_conditions_count.append("btu.data_transacao <= %s")
                    params_count.append(f"{data_fim} 23:59:59")

            if nsu:
                where_conditions_count.append("btu.var9 LIKE %s")
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

            # Construir SQL sem JOIN
            sql = """
            SELECT DISTINCT
                DATE_FORMAT(btu.data_transacao, '%%d/%%m/%%Y')   AS `Data`,
                STR_TO_DATE(btu.var43, '%%d/%%m/%%Y')       AS `Dt_credito`,
                STR_TO_DATE(btu.var45, '%%d/%%m/%%Y')       AS `Dt_pagto`,
                CASE
                    WHEN TRIM(btu.var70) = '0001-01-01T00:00:00' OR btu.var70 IS NULL OR TRIM(btu.var70) = ''
                        THEN NULL
                    ELSE STR_TO_DATE(LEFT(btu.var70, 10), '%%Y-%%m-%%d')
                END                                              AS `Dt_cancelamento`,
                btu.var5                                         AS `Filial`,
                CAST(btu.var6 AS UNSIGNED)                       AS `Cod_Estab`,
                btu.var2                                         AS `Terminal`,
                btu.var9                                         AS `NSU`,
                btu.authorization_code                           AS `Autorizacao`,
                CAST(btu.var13 AS SIGNED)                        AS `Prazo_Total`,
                CAST(btu.var19 AS DECIMAL(10,2))             AS `Vl_Bruto`,
                CAST(btu.var37 AS DECIMAL(10,2))             AS `Tx_Adm_R`,
                CAST(btu.var42 AS DECIMAL(10,2))             AS `Vl_Liq`,
                CASE
                    WHEN TRIM(btu.var70) = '0001-01-01T00:00:00' OR btu.var70 IS NULL OR TRIM(btu.var70) = ''
                         THEN 0
                    ELSE CAST(btu.var19 AS DECIMAL(10,2))
                END                                          AS `Vl_Canc`,
                CAST(btu.var36 AS DECIMAL(10,4))             AS `Tx_Adm_Perc`,
                CAST(btu.var44 AS DECIMAL(10,2))             AS `Vl_Liq_Pago`,
                CAST(btu.var40 AS DECIMAL(10,4))             AS `Tx_Antec_Per`,
                CAST(btu.var41 AS DECIMAL(10,2))             AS `Custo_Antec`,
                CAST(btu.var39 AS DECIMAL(10,4))             AS `Tx_Antec_AM`,
                btu.var121                                   AS `Status_Pagto`,
                btu.var8                                     AS `Plano`,
                btu.var12                                    AS `Bandeira`,
                btu.var68                                    AS `Status_Trans`,
                btu.var10                                    AS `NOP`
            FROM base_transacoes_unificadas btu
            """

            # Aplicar filtros de data - usar mesma lógica da view principal
            if data_inicio:
                try:
                    # Se data vem no formato YYYY-MM-DD, usar diretamente
                    if '-' in data_inicio and len(data_inicio) == 10:
                        where_conditions.append("btu.data_transacao >= %s")
                        params.append(f"{data_inicio} 00:00:00")
                    else:
                        # Se data vem no formato DD/MM/YYYY, converter
                        data_obj = datetime.strptime(data_inicio, '%d/%m/%Y')
                        data_formatada = data_obj.strftime('%Y-%m-%d')
                        where_conditions.append("btu.data_transacao >= %s")
                        params.append(f"{data_formatada} 00:00:00")
                except ValueError:
                    where_conditions.append("btu.data_transacao >= %s")
                    params.append(f"{data_inicio} 00:00:00")

            if data_fim:
                try:
                    # Se data vem no formato YYYY-MM-DD, usar diretamente
                    if '-' in data_fim and len(data_fim) == 10:
                        where_conditions.append("btu.data_transacao <= %s")
                        params.append(f"{data_fim} 23:59:59")
                    else:
                        # Se data vem no formato DD/MM/YYYY, converter
                        data_obj = datetime.strptime(data_fim, '%d/%m/%Y')
                        data_formatada = data_obj.strftime('%Y-%m-%d')
                        where_conditions.append("btu.data_transacao <= %s")
                        params.append(f"{data_formatada} 23:59:59")
                except ValueError:
                    where_conditions.append("btu.data_transacao <= %s")
                    params.append(f"{data_fim} 23:59:59")

            # Filtro NSU
            if nsu:
                where_conditions.append("btu.var9 LIKE %s")
                params.append(f'%{nsu}%')

            # Finalizar SQL
            if where_conditions:
                sql += f" WHERE {' AND '.join(where_conditions)}"
            sql += " ORDER BY btu.data_transacao DESC"

            # Executar query
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                columns = [col[0] for col in cursor.description]
                results = []

                for row in cursor.fetchall():
                    row_dict = dict(zip(columns, row))
                    # Substituir None por string vazia em todos os campos
                    row_dict = {k: ('' if v is None else v) for k, v in row_dict.items()}
                    results.append(row_dict)

            registrar_log('portais.lojista', f"CONCILIACAO - Exportação {formato} - {len(results)} registros")

            # Preparar dados para exportação
            lojas_incluidas = f"Lojas: {', '.join(map(str, lojas_query))}"
            nome_arquivo = f"conciliacao_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Definir colunas monetárias e percentuais para formatação
            colunas_monetarias = ['Vl.Bruto(R$)', 'Tx.Adm.(R$)', 'Vl.Líq.(R$)', 'Vl.Canc', 'Vl.Líq.Pago(R$)', 'Custo Antec(R$)']
            colunas_percentuais = ['Tx.Adm(%)', 'Tx.Antec(% per)', 'Tx.Antec(%a.m.)']

            # Mapeamento de nomes de colunas SQL para nomes da tela web
            mapeamento_colunas = {
                'Data': 'Data',
                'Dt_credito': 'Dt Crédito',
                'Dt_pagto': 'Dt Pagto',
                'Dt_cancelamento': 'Dt Cancel.',
                'Filial': 'Filial',
                'Cod_Estab': 'Cód.Estab.',
                'Terminal': 'Terminal',
                'NSU': 'NSU',
                'Autorizacao': 'Autorização',
                'Prazo_Total': 'Prazo Total',
                'Vl_Bruto': 'Vl.Bruto(R$)',
                'Tx_Adm_R': 'Tx.Adm.(R$)',
                'Vl_Liq': 'Vl.Líq.(R$)',
                'Vl_Canc': 'Vl.Canc',
                'Tx_Adm_Perc': 'Tx.Adm(%)',
                'Vl_Liq_Pago': 'Vl.Líq.Pago(R$)',
                'Tx_Antec_Per': 'Tx.Antec(% per)',
                'Custo_Antec': 'Custo Antec(R$)',
                'Tx_Antec_AM': 'Tx.Antec(%a.m.)',
                'Status_Pagto': 'Status Pagto',
                'Plano': 'Plano',
                'Bandeira': 'Bandeira',
                'Status_Trans': 'Status Trans',
                'NOP': 'NOP'
            }

            # Renomear colunas nos dados para todos os formatos
            results_renomeados = []
            for row in results:
                row_renomeado = {mapeamento_colunas.get(k, k): v for k, v in row.items()}
                results_renomeados.append(row_renomeado)

            if formato == 'excel':
                # Aplicar mapeamento de nomes de colunas
                cabecalhos_dict = {mapeamento_colunas.get(col, col): mapeamento_colunas.get(col, col) for col in columns}
                return exportar_excel(
                    nome_arquivo=nome_arquivo,
                    dados=results_renomeados,
                    titulo="Conciliação Portal Lojista",
                    cabecalhos=cabecalhos_dict,
                    colunas_monetarias=colunas_monetarias,
                    colunas_percentuais=colunas_percentuais,
                    lojas_incluidas=[lojas_incluidas]
                )
            elif formato == 'csv':
                return exportar_csv(
                    nome_arquivo=nome_arquivo,
                    dados=results_renomeados,
                    colunas_monetarias=colunas_monetarias,
                    colunas_percentuais=colunas_percentuais,
                    lojas_incluidas=[lojas_incluidas]
                )
            elif formato == 'pdf':
                return exportar_pdf(
                    nome_arquivo=nome_arquivo,
                    dados=results_renomeados,
                    titulo="Relatório de Conciliação - Portal Lojista",
                    colunas_monetarias=colunas_monetarias,
                    colunas_percentuais=colunas_percentuais,
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

                    # SQL com LIMIT e OFFSET - sem JOIN
                    sql_lote = """
                    SELECT
                        DATE_FORMAT(btu.data_transacao, '%%d/%%m/%%Y')   AS `Data`,
                        STR_TO_DATE(btu.var43, '%%d/%%m/%%Y')       AS `Dt_credito`,
                        STR_TO_DATE(btu.var45, '%%d/%%m/%%Y')       AS `Dt_pagto`,
                        CASE
                            WHEN TRIM(btu.var70) = '0001-01-01T00:00:00' OR btu.var70 IS NULL OR TRIM(btu.var70) = ''
                                THEN NULL
                            ELSE STR_TO_DATE(LEFT(btu.var70, 10), '%%Y-%%m-%%d')
                        END                                              AS `Dt_cancelamento`,
                        btu.var5                                         AS `Filial`,
                        CAST(btu.var6 AS UNSIGNED)                       AS `Cod_Estab`,
                        btu.var2                                         AS `Terminal`,
                        btu.var9                                         AS `NSU`,
                        btu.authorization_code                           AS `Autorizacao`,
                        CAST(btu.var13 AS SIGNED)                        AS `Prazo_Total`,
                        CAST(btu.var19 AS DECIMAL(10,2))             AS `Vl_Bruto`,
                        CAST(btu.var37 AS DECIMAL(10,2))             AS `Tx_Adm_R`,
                        CAST(btu.var42 AS DECIMAL(10,2))             AS `Vl_Liq`,
                        CASE
                            WHEN TRIM(btu.var70) = '0001-01-01T00:00:00' OR btu.var70 IS NULL OR TRIM(btu.var70) = ''
                                 THEN 0
                            ELSE CAST(btu.var19 AS DECIMAL(10,2))
                        END                                          AS `Vl_Canc`,
                        CAST(btu.var36 AS DECIMAL(10,4))*100         AS `Tx_Adm_Perc`,
                        CAST(btu.var44 AS DECIMAL(10,2))             AS `Vl_Liq_Pago`,
                        CAST(btu.var40 AS DECIMAL(10,4))*100         AS `Tx_Antec_Per`,
                        CAST(btu.var41 AS DECIMAL(10,2))             AS `Custo_Antec`,
                        CAST(btu.var39 AS DECIMAL(10,4))*100         AS `Tx_Antec_AM`,
                        btu.var121                                   AS `Status_Pagto`,
                        btu.var8                                     AS `Plano`,
                        btu.var12                                    AS `Bandeira`,
                        btu.var68                                    AS `Status_Trans`,
                        btu.var10                                    AS `NOP`
                    FROM base_transacoes_unificadas btu
                    """

                    # Montar parâmetros do lote (sem formatos de data)
                    params_lote = params.copy()

                    # Aplicar filtros de data
                    where_conditions_lote = where_conditions.copy()
                    if data_inicio:
                        try:
                            if '-' in data_inicio and len(data_inicio) == 10:
                                where_conditions_lote.append("btu.data_transacao >= %s")
                                params_lote.append(f"{data_inicio} 00:00:00")
                            else:
                                data_obj = datetime.strptime(data_inicio, '%d/%m/%Y')
                                where_conditions_lote.append("btu.data_transacao >= %s")
                                params_lote.append(f"{data_obj.strftime('%Y-%m-%d')} 00:00:00")
                        except ValueError:
                            where_conditions_lote.append("btu.data_transacao >= %s")
                            params_lote.append(f"{data_inicio} 00:00:00")

                    if data_fim:
                        try:
                            if '-' in data_fim and len(data_fim) == 10:
                                where_conditions_lote.append("btu.data_transacao <= %s")
                                params_lote.append(f"{data_fim} 23:59:59")
                            else:
                                data_obj = datetime.strptime(data_fim, '%d/%m/%Y')
                                where_conditions_lote.append("btu.data_transacao <= %s")
                                params_lote.append(f"{data_obj.strftime('%Y-%m-%d')} 23:59:59")
                        except ValueError:
                            where_conditions_lote.append("btu.data_transacao <= %s")
                            params_lote.append(f"{data_fim} 23:59:59")

                    if nsu:
                        where_conditions_lote.append("btu.var9 LIKE %s")
                        params_lote.append(f'%{nsu}%')

                    # Finalizar SQL do lote
                    if where_conditions_lote:
                        sql_lote += f" WHERE {' AND '.join(where_conditions_lote)}"
                    sql_lote += f" ORDER BY btu.data_transacao DESC LIMIT {lote_size} OFFSET {offset}"

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
