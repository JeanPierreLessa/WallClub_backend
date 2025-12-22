"""
Views do Portal Lojista - Relatório de Vendas por Operador
"""
from django.shortcuts import render
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.db import connection
from datetime import datetime

from wallclub_core.utilitarios.log_control import registrar_log
from .mixins import LojistaAccessMixin, LojistaDataMixin


class LojistaVendasOperadorView(LojistaAccessMixin, LojistaDataMixin, TemplateView):
    """View de vendas agrupadas por operador"""
    template_name = 'portais/lojista/vendas_operador.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Obter lojas acessíveis
        from portais.controle_acesso.models import PortalUsuario
        from portais.controle_acesso.filtros import FiltrosAcessoService

        usuario_id = self.request.session.get('lojista_usuario_id')
        try:
            usuario = PortalUsuario.objects.get(id=usuario_id)
            lojas_acessiveis = FiltrosAcessoService.obter_lojas_acessiveis(usuario)
        except PortalUsuario.DoesNotExist:
            lojas_acessiveis = []

        # Pegar filtros da URL
        context.update({
            'current_page': 'vendas',
            'lojas_acessiveis': lojas_acessiveis,
            'mostrar_filtro_loja': len(lojas_acessiveis) > 1,
            'data_inicio': self.request.GET.get('data_inicio', ''),
            'data_fim': self.request.GET.get('data_fim', ''),
            'nsu': self.request.GET.get('nsu', ''),
            'loja_selecionada': self.request.GET.get('loja', 'todas')
        })

        return context

    def _obter_lojas_acesso(self, request):
        """Obter lojas acessíveis usando serviço centralizado"""
        from portais.controle_acesso.models import PortalUsuario
        from portais.controle_acesso.filtros import FiltrosAcessoService

        usuario_id = request.session.get('lojista_usuario_id')
        if not usuario_id:
            return []

        try:
            usuario = PortalUsuario.objects.get(id=usuario_id)
            return FiltrosAcessoService.obter_lojas_acessiveis(usuario)
        except PortalUsuario.DoesNotExist:
            return []

    def post(self, request):
        """Buscar vendas agrupadas por operador"""
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            data_inicio = request.POST.get('data_inicio')
            data_fim = request.POST.get('data_fim')
            loja_selecionada = request.POST.get('loja')
            nsu = request.POST.get('nsu', '').strip()

            # Obter lojas acessíveis
            lojas_acesso = self._obter_lojas_acesso(request)
            if not lojas_acesso:
                return JsonResponse({'error': 'Nenhuma loja acessível'}, status=403)

            # Determinar lojas para consulta
            if loja_selecionada and loja_selecionada != 'todas':
                lojas_ids_acesso = [loja['id'] for loja in lojas_acesso]
                if int(loja_selecionada) not in lojas_ids_acesso:
                    return JsonResponse({'error': 'Loja não acessível'}, status=403)
                lojas_para_consulta = [int(loja_selecionada)]
            else:
                lojas_para_consulta = [loja['id'] for loja in lojas_acesso]

            try:
                # Construir WHERE clause
                where_conditions = []
                params = []

                # Filtro de data (obrigatório)
                if not data_inicio or not data_fim:
                    return JsonResponse({'error': 'Datas inicial e final são obrigatórias'}, status=400)

                where_conditions.append("data_transacao >= %s")
                params.append(f"{data_inicio} 00:00:00")

                where_conditions.append("data_transacao < %s")
                # Adicionar 1 dia à data final para incluir todo o dia
                from datetime import datetime, timedelta
                data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d')
                data_fim_inclusiva = (data_fim_obj + timedelta(days=1)).strftime('%Y-%m-%d')
                params.append(f"{data_fim_inclusiva} 00:00:00")

                # Filtro de loja
                if len(lojas_para_consulta) == 1:
                    where_conditions.append("b.var6 = %s")
                    params.append(lojas_para_consulta[0])
                else:
                    placeholders = ','.join(['%s'] * len(lojas_para_consulta))
                    where_conditions.append(f"b.var6 IN ({placeholders})")
                    params.extend(lojas_para_consulta)

                # Filtro de NSU (opcional)
                if nsu:
                    where_conditions.append("b.var9 LIKE %s")
                    params.append(f"%{nsu}%")

                where_clause = " AND ".join(where_conditions)

                # Query agrupada por operador (MIGRADO para transactiondata_pos)
                sql = f"""
                    SELECT
                        x.nome AS nome_operador,
                        SUM(x.var11) AS valor_total,
                        COUNT(1) AS qtde_vendas
                    FROM (
                        SELECT DISTINCT
                            b.var9,
                            b.var6,
                            b.var11,
                            t.operador_pos,
                            teops.nome
                        FROM base_transacoes_unificadas b
                        INNER JOIN transactiondata_pos t ON b.var9 = t.nsu_gateway AND t.gateway = 'PINBANK'
                        LEFT JOIN terminais_operadores_pos tepos ON t.operador_pos = tepos.id
                        LEFT JOIN terminais_operadores teops ON tepos.operador = teops.operador
                        WHERE {where_clause}
                    ) x
                    WHERE x.nome IS NOT NULL
                    GROUP BY x.nome
                    ORDER BY valor_total DESC
                """

                registrar_log('portais.lojista', f"VENDAS OPERADOR - Query: {sql}")
                registrar_log('portais.lojista', f"VENDAS OPERADOR - Params: {params}")

                results = []
                with connection.cursor() as cursor:
                    cursor.execute(sql, params)
                    rows = cursor.fetchall()

                    for row in rows:
                        nome_operador, valor_total, qtde_vendas = row
                        results.append({
                            'nome_operador': nome_operador or 'Sem nome',
                            'valor_total': float(valor_total or 0),
                            'qtde_vendas': int(qtde_vendas or 0)
                        })

                registrar_log('portais.lojista', f"VENDAS OPERADOR - {len(results)} operadores encontrados")

                # Renderizar HTML
                html = self._render_operadores_html(results)

                return JsonResponse({
                    'success': True,
                    'html': html,
                    'total': len(results)
                })

            except Exception as e:
                registrar_log('portais.lojista', f"VENDAS OPERADOR - Erro: {str(e)}", nivel='ERROR')
                return JsonResponse({'error': f'Erro na consulta: {str(e)}'}, status=500)

        # Se não for AJAX, renderizar template
        return self.get(request)

    def _render_operadores_html(self, operadores):
        """Renderizar HTML dos operadores"""
        if not operadores:
            return '<div class="alert alert-info mt-3">Nenhum operador encontrado com os filtros informados.</div>'

        # Calcular totais
        total_valor = sum(op['valor_total'] for op in operadores)
        total_vendas = sum(op['qtde_vendas'] for op in operadores)

        # Cards de totais
        html = '<div class="row mt-3 mb-3">'
        html += f'''
        <div class="col-md-4">
            <div class="card bg-primary text-white">
                <div class="card-body py-2 text-center">
                    <h5 class="card-title" style="font-size: 14px; margin-bottom: 5px;">Total de Operadores</h5>
                    <h3 class="card-text" style="font-size: 18px; margin-bottom: 0;">{len(operadores)}</h3>
                </div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card bg-success text-white">
                <div class="card-body py-2 text-center">
                    <h5 class="card-title" style="font-size: 14px; margin-bottom: 5px;">Total de Vendas</h5>
                    <h3 class="card-text" style="font-size: 18px; margin-bottom: 0;">{total_vendas}</h3>
                </div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card bg-info text-white">
                <div class="card-body py-2 text-center">
                    <h5 class="card-title" style="font-size: 14px; margin-bottom: 5px;">Valor Total</h5>
                    <h3 class="card-text" style="font-size: 18px; margin-bottom: 0;">R$ {total_valor:,.2f}</h3>
                </div>
            </div>
        </div>
        '''
        html += '</div>'

        # Tabela de operadores
        html += '''
        <div class="table-responsive">
            <table class="table table-striped table-hover">
                <thead class="table-dark">
                    <tr>
                        <th>Operador</th>
                        <th class="text-end">Qtde Vendas</th>
                        <th class="text-end">Valor Total (R$)</th>
                        <th class="text-end">Ticket Médio (R$)</th>
                    </tr>
                </thead>
                <tbody>
        '''

        for op in operadores:
            ticket_medio = op['valor_total'] / op['qtde_vendas'] if op['qtde_vendas'] > 0 else 0
            html += f'''
            <tr>
                <td><strong>{op["nome_operador"]}</strong></td>
                <td class="text-end">{op["qtde_vendas"]}</td>
                <td class="text-end">R$ {op["valor_total"]:,.2f}</td>
                <td class="text-end">R$ {ticket_medio:,.2f}</td>
            </tr>
            '''

        html += '</tbody>'

        # Linha de totalizador
        ticket_medio_geral = total_valor / total_vendas if total_vendas > 0 else 0
        html += f'''
        <tfoot class="table-secondary">
            <tr>
                <th>TOTAL</th>
                <th class="text-end">{total_vendas}</th>
                <th class="text-end">R$ {total_valor:,.2f}</th>
                <th class="text-end">R$ {ticket_medio_geral:,.2f}</th>
            </tr>
        </tfoot>
        '''

        html += '</table></div>'

        return html
