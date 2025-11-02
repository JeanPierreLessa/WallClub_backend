"""
Views do Portal Lojista - Módulo de Vendas
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

from wallclub_core.utilitarios.log_control import registrar_log
from .mixins import LojistaAccessMixin, LojistaDataMixin


class LojistaVendasView(LojistaAccessMixin, LojistaDataMixin, TemplateView):
    """View de vendas"""
    template_name = 'portais/lojista/vendas.html'
    
    
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
            'current_page': 'vendas',
            'lojas_acessiveis': lojas_acessiveis
        })
        
        # Sempre mostrar filtro de loja se há múltiplas lojas acessíveis
        # Admin com permissão lojista também deve ver o filtro
        context['mostrar_filtro_loja'] = len(lojas_acessiveis) > 1
        
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
        """Buscar vendas com filtros - retorna HTML renderizado para AJAX"""
        # Verificar se é requisição AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            data_inicio = request.POST.get('data_inicio')
            data_fim = request.POST.get('data_fim')
            loja_selecionada = request.POST.get('loja')
            nsu = request.POST.get('nsu', '').strip()
            cliente_id = request.POST.get('cliente_id')
            incluir_tef = request.POST.get('incluir_tef') == 'on'
            pagina = int(request.POST.get('pagina', 1))
            por_pagina = 50  # Registros por página
            
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
                # Inicializar vendas_queryset
                vendas_queryset = []
                
                # Usar Django ORM
                from django.db.models import Q
                
                # Construir filtros Django
                filtros = Q(var6__in=lojas_para_consulta) & Q(var68='TRANS. APROVADO')
                
                # Filtros adicionais
                if nsu:
                    filtros &= Q(var9__icontains=nsu)
                
                if cliente_id:
                    filtros &= Q(var6=cliente_id)
                
                # Filtro TEF (excluir por padrão)
                if not incluir_tef:
                    filtros &= ~Q(var130='TEF')
                
                # Aplicar filtros de data usando data_transacao
                if data_inicio:
                    filtros &= Q(data_transacao__gte=f"{data_inicio} 00:00:00")
                
                if data_fim:
                    filtros &= Q(data_transacao__lte=f"{data_fim} 23:59:59")
                
                # Aplicar deduplicação usando ROW_NUMBER (mesma lógica do dashboard admin)
                from django.db import connection
                
                # Construir WHERE clause para SQL raw
                where_conditions = []
                params = []
                
                # Filtro de loja - corrigir sintaxe SQL
                if len(lojas_para_consulta) == 1:
                    where_conditions.append("var6 = %s")
                    params.append(lojas_para_consulta[0])
                else:
                    placeholders = ','.join(['%s'] * len(lojas_para_consulta))
                    where_conditions.append(f"var6 IN ({placeholders})")
                    params.extend(lojas_para_consulta)
                
                # Filtro var68 = 'TRANS. APROVADO'
                where_conditions.append("var68 = %s")
                params.append('TRANS. APROVADO')
                
                # Filtro de data
                if data_inicio:
                    where_conditions.append("data_transacao >= %s")
                    params.append(f"{data_inicio} 00:00:00")
                
                if data_fim:
                    where_conditions.append("data_transacao <= %s")
                    params.append(f"{data_fim} 23:59:59")
                
                # Filtro de NSU
                if nsu:
                    where_conditions.append("var9 LIKE %s")
                    params.append(f"%{nsu}%")
                
                # Filtro TEF (excluir por padrão)
                if not incluir_tef:
                    where_conditions.append("(var130 != %s OR var130 IS NULL)")
                    params.append('TEF')
                
                where_clause = " AND ".join(where_conditions)
                
                # Cache habilitado
                import hashlib
                import json
                from django.core.cache import cache
                
                # Gerar chave de cache baseada nos filtros e página
                cache_key_data = {
                    'lojas': lojas_para_consulta,
                    'data_inicio': data_inicio,
                    'data_fim': data_fim,
                    'nsu': nsu,
                    'cliente_id': cliente_id,
                    'incluir_tef': incluir_tef,
                    'pagina': pagina
                }
                cache_key = 'lojista_vendas_' + hashlib.md5(
                    json.dumps(cache_key_data, sort_keys=True).encode()
                ).hexdigest()
                
                # Cache reabilitado com debug
                cached_result = cache.get(cache_key)
                if cached_result:
                    registrar_log('portais.lojista', f"VENDAS DEBUG - Cache data keys: {list(cached_result.keys())}")
                    registrar_log('portais.lojista', f"VENDAS DEBUG - Cache data type: {type(cached_result)}")
                    
                    results = cached_result.get('results', [])
                    totais = cached_result.get('totais', {})
                    total_registros = cached_result.get('total_registros', 0)
                    
                    registrar_log('portais.lojista', f"VENDAS - Cache HIT - {total_registros} registros")
                    registrar_log('portais.lojista', f"VENDAS DEBUG - Cache results count: {len(results)}")
                    registrar_log('portais.lojista', f"VENDAS DEBUG - Cache results type: {type(results)}")
                    
                    if len(results) == 0 and total_registros > 0:
                        registrar_log('portais.lojista', f"VENDAS DEBUG - PROBLEMA: Cache tem total_registros={total_registros} mas results vazio")
                        registrar_log('portais.lojista', f"VENDAS DEBUG - Cached result completo: {cached_result}")
                        # Forçar cache miss para reprocessar
                        cached_result = None
                    else:
                        # Cache válido - calcular paginação e retornar
                        total_paginas = (total_registros + por_pagina - 1) // por_pagina
                        tem_proxima = pagina < total_paginas
                        tem_anterior = pagina > 1
                        
                        html = self._render_vendas_html(results, totais, {
                            'pagina_atual': pagina,
                            'total_paginas': total_paginas,
                            'total_registros': total_registros,
                            'tem_proxima': tem_proxima,
                            'tem_anterior': tem_anterior,
                            'registros_exibidos': len(results)
                        })
                        
                        return JsonResponse({
                            'success': True,
                            'html': html,
                            'total': total_registros,
                            'pagina_atual': pagina,
                            'total_paginas': total_paginas,
                            'tem_proxima': tem_proxima,
                            'tem_anterior': tem_anterior
                        })
                
                if not cached_result:
                    # Calcular offset para paginação
                    offset = (pagina - 1) * por_pagina
                    
                    # Query otimizada - selecionar apenas campos necessários
                    sql = f"""
                        SELECT 
                            data_transacao,
                            var6 as loja_id,
                            var9 as nsu,
                            var10 as nop,
                            var13 as parcelas,
                            var19 as vl_bruto,
                            var37 as taxa_adm,
                            var41 as custo_antec,
                            var42 as vl_liq_previsto,
                            var44 as vl_liq_pago,
                            var68 as status
                        FROM (
                            SELECT *,
                                   ROW_NUMBER() OVER (PARTITION BY var9 ORDER BY id DESC) as rn
                            FROM baseTransacoesGestao 
                            WHERE {where_clause}
                        ) t WHERE rn = 1
                        ORDER BY data_transacao DESC
                        LIMIT {por_pagina} OFFSET {offset}
                    """
                
                    # Criar mapa de lojas para lookup rápido
                    lojas_map = {int(loja['id']): loja['nome'] for loja in lojas_acesso}
                    
                    # Executar query e processar resultados
                    results = []
                    with connection.cursor() as cursor:
                        cursor.execute(sql, params)
                        rows = cursor.fetchall()
                        
                        for row in rows:
                            data_transacao, loja_id, nsu, nop, parcelas, vl_bruto, taxa_adm, custo_antec, vl_liq_previsto, vl_liq_pago, status = row
                            
                            # Data e hora formatadas
                            data_formatada = data_transacao.strftime('%d/%m/%Y') if data_transacao else '-'
                            hora_formatada = data_transacao.strftime('%H:%M:%S') if data_transacao else '-'
                            
                            # Buscar nome da loja no mapa
                            nome_loja = lojas_map.get(int(loja_id), f'Loja {loja_id}')
                            
                            # Criar dicionário com dados da venda
                            results.append({
                                'Data': data_formatada,
                                'Hora': hora_formatada,
                                'Loja': nome_loja,
                                'Vl. Bruto(R$)': float(vl_bruto or 0),
                                'Vl. Líq. Previsto(R$)': float(vl_liq_previsto or 0),
                                'Vl. Líq. Pago(R$)': float(vl_liq_pago or 0),
                                'Núm. Parcelas': int(parcelas or 0),
                                'Taxa Adm(R$)': float(taxa_adm or 0),
                                'Custo Antec(R$)': float(custo_antec or 0),
                                'Status Trans.': status or '-',
                                'NSU': nsu or '-',
                                'NOP': nop or '-'
                            })
                
                # Calcular totais REAIS (de todos os registros filtrados, não apenas da página)
                sql_totais = f"""
                    SELECT 
                        SUM(CAST(var19 AS DECIMAL(15,2))) as total_bruto,
                        SUM(CAST(var42 AS DECIMAL(15,2))) as total_liquido,
                        SUM(CAST(var37 AS DECIMAL(15,2))) as total_taxa_adm,
                        SUM(CAST(var44 AS DECIMAL(15,2))) as total_pago
                    FROM (
                        SELECT var19, var42, var37, var44,
                               ROW_NUMBER() OVER (PARTITION BY var9 ORDER BY id DESC) as rn
                        FROM baseTransacoesGestao 
                        WHERE {where_clause}
                    ) t WHERE rn = 1
                """
                
                with connection.cursor() as cursor:
                    cursor.execute(sql_totais, params)
                    totais_row = cursor.fetchone()
                    
                totais = {
                    'total_bruto': float(totais_row[0] or 0),
                    'total_liquido': float(totais_row[1] or 0),
                    'total_taxa_adm': float(totais_row[2] or 0),
                    'total_pago': float(totais_row[3] or 0)
                }
                
                # Query de contagem para paginação
                sql_count = f"""
                    SELECT COUNT(*) FROM (
                        SELECT var9,
                               ROW_NUMBER() OVER (PARTITION BY var9 ORDER BY id DESC) as rn
                        FROM baseTransacoesGestao 
                        WHERE {where_clause}
                    ) t WHERE rn = 1
                """
                
                with connection.cursor() as cursor:
                    cursor.execute(sql_count, params)
                    total_registros = cursor.fetchone()[0]
                
                # Salvar no cache por 5 minutos
                cache_data = {
                    'results': results,
                    'totais': totais,
                    'total_registros': total_registros
                }
                registrar_log('portais.lojista', f"VENDAS DEBUG - Salvando no cache: {len(results)} results, total: {total_registros}")
                cache.set(cache_key, cache_data, 300)
                registrar_log('portais.lojista', f"VENDAS - Cache MISS - {total_registros} registros salvos no cache")
                
                # Calcular informações de paginação
                total_paginas = (total_registros + por_pagina - 1) // por_pagina
                tem_proxima = pagina < total_paginas
                tem_anterior = pagina > 1
                
                # Debug: log dos resultados
                registrar_log('portais.lojista', f"VENDAS DEBUG - Results count: {len(results)}")
                registrar_log('portais.lojista', f"VENDAS DEBUG - Total registros: {total_registros}")
                
                # Renderizar HTML com paginação
                html = self._render_vendas_html(results, totais, {
                    'pagina_atual': pagina,
                    'total_paginas': total_paginas,
                    'total_registros': total_registros,
                    'tem_proxima': tem_proxima,
                    'tem_anterior': tem_anterior,
                    'registros_exibidos': len(results)
                })
                
                return JsonResponse({
                    'success': True,
                    'html': html,
                    'total': total_registros,
                    'pagina_atual': pagina,
                    'total_paginas': total_paginas,
                    'tem_proxima': tem_proxima,
                    'tem_anterior': tem_anterior
                })
                    
            except Exception as e:
                return JsonResponse({'error': f'Erro na consulta: {e}'}, status=500)
        
        # Se não for AJAX, redirecionar para GET
        return redirect('lojista:vendas')
    
    def _render_vendas_html(self, vendas, totais, paginacao=None):
        """Renderizar HTML das vendas"""
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
            return '<div class="alert alert-info mt-3">Nenhuma venda encontrada com os filtros informados.</div>'
        
        # Cards de totais
        total_registros_exibidos = len(vendas)
        info_paginacao = paginacao or {}
        
        html = ''
        html += '<div class="row mt-3 mb-3">'
        
        cards = [
            ('Total Bruto', totais['total_bruto'], 'bg-primary'),
            ('Total Líquido', totais['total_liquido'], 'bg-success'),
            ('Total Taxa Adm', totais['total_taxa_adm'], 'bg-warning text-dark'),
            ('Total Pago', totais['total_pago'], 'bg-info')
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
        
        # Informações de paginação
        if info_paginacao:
            html += f'''
            <div class="row mt-3 mb-3">
                <div class="col-md-6">
                    <p class="text-muted mb-0">
                        Exibindo {info_paginacao.get('registros_exibidos', 0)} de {info_paginacao.get('total_registros', 0)} registros
                        (Página {info_paginacao.get('pagina_atual', 1)} de {info_paginacao.get('total_paginas', 1)})
                    </p>
                </div>
                <div class="col-md-6 text-end">
                    <div class="btn-group" role="group">
                        <button type="button" class="btn btn-outline-primary btn-sm" 
                                onclick="navegarPagina({info_paginacao.get('pagina_atual', 1) - 1})" 
                                {'disabled' if not info_paginacao.get('tem_anterior', False) else ''}>
                            <i class="fas fa-chevron-left"></i> Anterior
                        </button>
                        <button type="button" class="btn btn-outline-primary btn-sm" 
                                onclick="navegarPagina({info_paginacao.get('pagina_atual', 1) + 1})" 
                                {'disabled' if not info_paginacao.get('tem_proxima', False) else ''}>
                            Próxima <i class="fas fa-chevron-right"></i>
                        </button>
                    </div>
                </div>
            </div>
            '''
        
        # Tabela de vendas
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
        
        # Controles de paginação no final
        if info_paginacao and info_paginacao.get('total_paginas', 1) > 1:
            pagina_atual = info_paginacao.get('pagina_atual', 1)
            total_paginas = info_paginacao.get('total_paginas', 1)
            
            html += '''
            <div class="row mt-3">
                <div class="col-12">
                    <nav aria-label="Navegação de páginas">
                        <ul class="pagination justify-content-center mb-0">
            '''
            
            # Botão Anterior
            if info_paginacao.get('tem_anterior', False):
                html += f'''
                <li class="page-item">
                    <a class="page-link" href="#" onclick="navegarPagina({pagina_atual - 1}); return false;">
                        <i class="fas fa-chevron-left"></i> Anterior
                    </a>
                </li>
                '''
            else:
                html += '''
                <li class="page-item disabled">
                    <span class="page-link"><i class="fas fa-chevron-left"></i> Anterior</span>
                </li>
                '''
            
            # Números das páginas (mostrar até 5 páginas)
            inicio = max(1, pagina_atual - 2)
            fim = min(total_paginas, pagina_atual + 2)
            
            for i in range(inicio, fim + 1):
                if i == pagina_atual:
                    html += f'''
                    <li class="page-item active">
                        <span class="page-link">{i}</span>
                    </li>
                    '''
                else:
                    html += f'''
                    <li class="page-item">
                        <a class="page-link" href="#" onclick="navegarPagina({i}); return false;">{i}</a>
                    </li>
                    '''
            
            # Botão Próxima
            if info_paginacao.get('tem_proxima', False):
                html += f'''
                <li class="page-item">
                    <a class="page-link" href="#" onclick="navegarPagina({pagina_atual + 1}); return false;">
                        Próxima <i class="fas fa-chevron-right"></i>
                    </a>
                </li>
                '''
            else:
                html += '''
                <li class="page-item disabled">
                    <span class="page-link">Próxima <i class="fas fa-chevron-right"></i></span>
                </li>
                '''
            
            html += '''
                        </ul>
                    </nav>
                </div>
            </div>
            '''
        
        return html


class LojistaVendasExportView(LojistaAccessMixin, LojistaDataMixin, View):
    """View para exportação de dados de vendas"""
    
    def post(self, request):
        from wallclub_core.utilitarios.export_utils import exportar_excel, exportar_csv, exportar_pdf
        from django.db import connection
        from django.http import JsonResponse
        from datetime import datetime
        import threading
        
        formato = request.POST.get('formato', 'excel')
        
        # Reutilizar a mesma lógica de filtros da view principal
        nsu = request.POST.get('nsu', '').strip()
        data_inicial = request.POST.get('data_inicio', '')
        data_final = request.POST.get('data_fim', '')
        loja_id = request.POST.get('loja', '')
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
        
        # Determinar filtro de loja (tipo_usuario removido - usar lógica simplificada)
        if loja_id and loja_id != 'todas' and int(loja_id) in loja_ids_acesso:
            lojas_filtro = [int(loja_id)]
        else:
            lojas_filtro = loja_ids_acesso
        
        if not lojas_filtro:
            return JsonResponse({'error': 'Acesso negado'}, status=403)
        
        # Usar Django ORM para exportação
        from django.db.models import Q
        
        # Construir filtros Django
        filtros = Q(var6__in=lojas_filtro) & Q(var68='TRANS. APROVADO')
        
        if nsu:
            filtros &= Q(var9__icontains=nsu)
        
        if data_inicial:
            filtros &= Q(data_transacao__gte=f"{data_inicial} 00:00:00")
        
        if data_final:
            filtros &= Q(data_transacao__lte=f"{data_final} 23:59:59")
        
        try:
            # Usar mesma lógica ROW_NUMBER do dashboard admin
            from django.db import connection
            
            # Construir WHERE clause
            where_conditions = []
            params = []
            
            # Filtro de loja
            where_conditions.append("var6 IN %s")
            params.append(tuple(lojas_filtro))
            
            # Filtro var68 = 'TRANS. APROVADO'
            where_conditions.append("var68 = 'TRANS. APROVADO'")
            
            # Filtro de data
            if data_inicial:
                where_conditions.append("data_transacao >= %s")
                params.append(f"{data_inicial} 00:00:00")
            
            if data_final:
                where_conditions.append("data_transacao <= %s")
                params.append(f"{data_final} 23:59:59")
            
            # Filtro de NSU
            if nsu:
                where_conditions.append("var9 LIKE %s")
                params.append(f"%{nsu}%")
            
            # Filtro TEF (excluir por padrão)
            if not incluir_tef:
                where_conditions.append("var130 != 'TEF'")
            
            where_clause = " AND ".join(where_conditions)
            
            # Contar total de registros primeiro
            sql_count = f"""
                SELECT COUNT(*) FROM (
                    SELECT var9,
                           ROW_NUMBER() OVER (PARTITION BY var9 ORDER BY id DESC) as rn
                    FROM baseTransacoesGestao 
                    WHERE {where_clause}
                ) t WHERE rn = 1
            """
            
            with connection.cursor() as cursor:
                cursor.execute(sql_count, params)
                total_registros = cursor.fetchone()[0]
            
            registrar_log('portais.lojista', f"EXPORT VENDAS - Total de registros: {total_registros}")
            
            # Se mais de 5000 registros, processar em background e enviar por email
            if total_registros > 5000:
                # Processar em background
                thread = threading.Thread(
                    target=self._processar_export_grande,
                    args=(request, where_clause, params, total_registros)
                )
                thread.start()
                
                return JsonResponse({
                    'success': True,
                    'message': f'Export iniciado em background. Arquivo CSV com {total_registros:,} registros será enviado por email.'
                })
            
            # Query com ROW_NUMBER para deduplicação (mesma lógica do dashboard)
            sql = f"""
                SELECT * FROM (
                    SELECT *,
                           ROW_NUMBER() OVER (PARTITION BY var9 ORDER BY id DESC) as rn
                    FROM baseTransacoesGestao 
                    WHERE {where_clause}
                ) t WHERE rn = 1
                ORDER BY data_transacao DESC
            """
            
            # Query SQL direta - não precisa de modelo
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                columns = [col[0] for col in cursor.description]
                vendas_queryset = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
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
            
            nome_arquivo = f"vendas_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            if formato == 'excel':
                return exportar_excel(
                    nome_arquivo=nome_arquivo,
                    dados=results,
                    titulo="Vendas Portal Lojista",  # Máximo 30 caracteres
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
                    titulo="Relatório de Vendas - Portal Lojista",
                    colunas_monetarias=colunas_monetarias,
                    lojas_incluidas=lojas_incluidas
                )
            else:
                return JsonResponse({'error': 'Formato não suportado'}, status=400)
                    
        except Exception as e:
            registrar_log('portais.lojista', f"ERRO EXPORT VENDAS: {str(e)}", nivel='ERROR')
            return JsonResponse({'error': f'Erro na exportação: {str(e)}'}, status=500)
    
    def _processar_export_grande(self, request, where_clause, params, total_registros):
        """Processar export grande em background com envio por email"""
        try:
            from django.conf import settings
            from wallclub_core.integracoes.email_service import EmailService
            import tempfile
            import os
            from datetime import datetime
            
            registrar_log('portais.lojista', f"EXPORT GRANDE - Iniciando processamento de {total_registros} registros")
            
            # Criar arquivo temporário
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as temp_file:
                temp_path = temp_file.name
                
                # Cabeçalho CSV
                colunas = [
                    'Loja', 'Data', 'Hora', 'Vl Bruto(R$)', 'Vl Liq Previsto(R$)', 'Vl Liq Pago(R$)',
                    'Status Pgto', 'Data Pgto', 'Plano', 'Núm. Parcelas', 'Taxa Adm(R$)', 'Custo Antec(R$)',
                    'Status Trans.', 'NSU', 'NOP'
                ]
                temp_file.write(';'.join(colunas) + '\n')
                
                # Processar em lotes de 1000
                lote_size = 1000
                total_lotes = (total_registros + lote_size - 1) // lote_size
                
                for lote in range(total_lotes):
                    offset = lote * lote_size
                    registrar_log('portais.lojista', f"EXPORT GRANDE - Processando lote {lote + 1}/{total_lotes}")
                    
                    sql_lote = f"""
                        SELECT * FROM (
                            SELECT *,
                                   ROW_NUMBER() OVER (PARTITION BY var9 ORDER BY id DESC) as rn
                            FROM baseTransacoesGestao 
                            WHERE {where_clause}
                        ) t WHERE rn = 1
                        ORDER BY data_transacao DESC
                        LIMIT {lote_size} OFFSET {offset}
                    """
                    
                    # Query SQL direta - não precisa de modelo
                    with connection.cursor() as cursor:
                        cursor.execute(sql_lote, params)
                        columns = [col[0] for col in cursor.description]
                        vendas_lote = [dict(zip(columns, row)) for row in cursor.fetchall()]
                    
                    for venda in vendas_lote:
                        # Processar dados (mesma lógica da view principal)
                        vl_bruto = float(venda.var19 or 0)
                        vl_liq_previsto = float(venda.var42 or 0)
                        vl_liq_pago = float(venda.var44 or 0)
                        taxa_adm = float(venda.var37 or 0)
                        custo_antec = float(venda.var41 or 0)
                        num_parcelas = int(venda.var13 or 0)
                        
                        data_formatada = venda.data_transacao.strftime('%d/%m/%Y') if venda.data_transacao else '-'
                        hora_formatada = venda.data_transacao.strftime('%H:%M:%S') if venda.data_transacao else '-'
                        data_pgto = venda.var45 if venda.var45 else venda.var43
                        nome_loja = (venda.var5 or '-')[:10] if venda.var5 else '-'
                        
                        # Escrever linha CSV
                        linha = [
                            nome_loja, data_formatada, hora_formatada,
                            f"{vl_bruto:.2f}".replace('.', ','),
                            f"{vl_liq_previsto:.2f}".replace('.', ','),
                            f"{vl_liq_pago:.2f}".replace('.', ','),
                            venda.var121 or '-', data_pgto or '-', venda.var8 or '-',
                            str(num_parcelas),
                            f"{taxa_adm:.2f}".replace('.', ','),
                            f"{custo_antec:.2f}".replace('.', ','),
                            venda.var68 or '-', venda.var9 or '-', venda.var10 or '-'
                        ]
                        temp_file.write(';'.join(linha) + '\n')
            
            # Enviar por email
            usuario_email = request.session.get('lojista_usuario_email', '')
            if usuario_email:
                nome_arquivo = f"vendas_lojista_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                
                # Ler arquivo para anexo
                with open(temp_path, 'rb') as arquivo:
                    conteudo_csv = arquivo.read()
                
                # Enviar usando EmailService
                resultado = EmailService.enviar_email(
                    destinatarios=[usuario_email],
                    assunto=f'Export de Vendas - {total_registros:,} registros',
                    mensagem_texto=f'Segue em anexo o arquivo CSV com {total_registros:,} registros de vendas.\n\nArquivo gerado em: {datetime.now().strftime("%d/%m/%Y às %H:%M:%S")}',
                    anexos=[{
                        'nome': nome_arquivo,
                        'conteudo': conteudo_csv,
                        'tipo': 'text/csv'
                    }],
                    fail_silently=True
                )
                
                if resultado['sucesso']:
                    registrar_log('portais.lojista', f"EXPORT GRANDE - Email enviado para {usuario_email}")
                else:
                    registrar_log('portais.lojista', f"EXPORT GRANDE - Erro ao enviar email: {resultado['mensagem']}", nivel='ERROR')
            
            # Limpar arquivo temporário
            os.unlink(temp_path)
            registrar_log('portais.lojista', f"EXPORT GRANDE - Concluído com sucesso")
            
        except Exception as e:
            registrar_log('portais.lojista', f"ERRO EXPORT GRANDE: {str(e)}", nivel='ERROR')
