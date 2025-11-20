"""
Serviços de Recebimentos do Portal Lojista
Camada de negócio para consultas e relatórios de recebimentos
"""

from django.db.models import Q, Sum, Count
from datetime import datetime, date
from decimal import Decimal
from wallclub_core.utilitarios.log_control import registrar_log


class RecebimentoService:
    """
    Serviço para gerenciamento de recebimentos do portal lojista.
    Centraliza toda lógica de consultas, agrupamentos e relatórios.
    """
    
    @staticmethod
    def obter_recebimentos_por_data(lojas_ids, data_inicio=None, data_fim=None, nsu=None):
        """
        Busca recebimentos agrupados por data de recebimento.
        
        Args:
            lojas_ids (list): IDs das lojas acessíveis
            data_inicio (str): Data início formato YYYY-MM-DD
            data_fim (str): Data fim formato YYYY-MM-DD
            nsu (str): Filtro opcional por NSU
            
        Returns:
            dict: Recebimentos agrupados por data com totalizadores
        """
        from wallclub_core.database.queries import TransacoesQueries
        from gestao_financeira.models import LancamentoManual
        
        # Com GROUP BY e LIMIT, não precisa mais exigir filtros
        
        # Construir filtros base
        filtros = Q(var6__in=lojas_ids) & Q(var45__isnull=False) & ~Q(var45='')
        
        if nsu:
            filtros &= Q(var9__icontains=nsu)
        
        # Usar SQL direto para agregar - MUITO mais eficiente
        from django.db import connection
        
        recebimentos_por_data = {}
        
        # Montar WHERE clause
        lojas_str = ','.join(map(str, lojas_ids))
        where_clauses = [f"var6 IN ({lojas_str})", "var45 IS NOT NULL", "var45 != ''"]
        
        if nsu:
            where_clauses.append(f"var9 LIKE '%{nsu}%'")
        
        # Adicionar filtros de data direto no SQL
        # Como var45 está em formato DD/MM/YYYY, precisamos converter
        if data_inicio:
            # Converter YYYY-MM-DD para DD/MM/YYYY
            data_ini_obj = datetime.strptime(data_inicio, '%Y-%m-%d')
            data_ini_br = data_ini_obj.strftime('%d/%m/%Y')
            where_clauses.append(f"STR_TO_DATE(var45, '%d/%m/%Y') >= STR_TO_DATE('{data_ini_br}', '%d/%m/%Y')")
        
        if data_fim:
            # Converter YYYY-MM-DD para DD/MM/YYYY
            data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d')
            data_fim_br = data_fim_obj.strftime('%d/%m/%Y')
            where_clauses.append(f"STR_TO_DATE(var45, '%d/%m/%Y') <= STR_TO_DATE('{data_fim_br}', '%d/%m/%Y')")
        
        where_sql = ' AND '.join(where_clauses)
        
        # Query otimizada com GROUP BY
        sql = f"""
        SELECT 
            var45 as data_recebimento,
            COUNT(*) as quantidade,
            SUM(CAST(COALESCE(var44, 0) AS DECIMAL(10,2))) as valor_total
        FROM baseTransacoesGestao
        WHERE {where_sql}
        GROUP BY var45
        ORDER BY STR_TO_DATE(var45, '%d/%m/%Y') DESC
        LIMIT 1000
        """
        
        with connection.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
            
            for row in rows:
                var45, quantidade, valor_total = row
                
                if not var45:
                    continue
                
                try:
                    # Converter data
                    data_recebimento = None
                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%Y%m%d']:
                        try:
                            data_recebimento = datetime.strptime(var45, fmt).date()
                            break
                        except ValueError:
                            continue
                    
                    if not data_recebimento:
                        continue
                    
                    # Filtros já aplicados no SQL
                    data_key = data_recebimento.strftime('%Y-%m-%d')
                    
                    recebimentos_por_data[data_key] = {
                        'data': data_recebimento,
                        'data_formatada': data_recebimento.strftime('%d/%m/%Y'),
                        'valor_total': Decimal(str(valor_total)) if valor_total else Decimal('0.00'),
                        'quantidade': quantidade,
                        'transacoes': []  # Não carregar transações individuais por padrão
                    }
                    
                except Exception as e:
                    registrar_log(
                        'portais.lojista',
                        f'Erro ao processar data {var45}: {str(e)}',
                        nivel='WARNING'
                    )
                    continue
        
        # Buscar lançamentos manuais
        filtros_lancamentos = Q(loja_id__in=lojas_ids) & Q(status='processado')
        
        if data_inicio:
            data_ini_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            filtros_lancamentos &= Q(data_lancamento__date__gte=data_ini_obj)
        
        if data_fim:
            data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d').date()
            filtros_lancamentos &= Q(data_lancamento__date__lte=data_fim_obj)
        
        lancamentos_manuais = LancamentoManual.objects.filter(filtros_lancamentos)
        
        # Adicionar lançamentos manuais aos recebimentos
        for lancamento in lancamentos_manuais:
            data_key = lancamento.data_lancamento.strftime('%Y-%m-%d')
            
            if data_key not in recebimentos_por_data:
                recebimentos_por_data[data_key] = {
                    'data': lancamento.data_lancamento.date(),
                    'data_formatada': lancamento.data_lancamento.strftime('%d/%m/%Y'),
                    'valor_total': Decimal('0.00'),
                    'quantidade': 0,
                    'transacoes': []
                }
            
            # Somar valor (considerar tipo de lançamento)
            valor = Decimal(str(lancamento.valor)) if lancamento.valor else Decimal('0.00')
            if lancamento.tipo_lancamento == 'D':
                valor = -valor
            
            recebimentos_por_data[data_key]['valor_total'] += valor
            recebimentos_por_data[data_key]['quantidade'] += 1
            recebimentos_por_data[data_key]['transacoes'].append({
                'nsu': f'LM-{lancamento.id}',
                'valor': valor,
                'loja_id': lancamento.loja_id,
                'tipo': 'lancamento_manual'
            })
        
        # Ordenar por data (mais recente primeiro)
        recebimentos_ordenados = sorted(
            recebimentos_por_data.items(),
            key=lambda x: x[1]['data'],
            reverse=True
        )
        
        registrar_log(
            'portais.lojista',
            f'Recebimentos agrupados - Lojas: {len(lojas_ids)} - Datas: {len(recebimentos_ordenados)}'
        )
        
        return dict(recebimentos_ordenados)
    
    @staticmethod
    def obter_transacoes_por_data(lojas_ids, data_recebimento):
        """
        Busca todas as transações de uma data específica.
        
        Args:
            lojas_ids (list): IDs das lojas acessíveis
            data_recebimento (str): Data no formato YYYY-MM-DD ou DD/MM/YYYY
            
        Returns:
            list: Lista de transações da data
        """
        from django.apps import apps
        
        # Tentar formatos de data
        data_obj = None
        for fmt in ['%Y-%m-%d', '%d/%m/%Y']:
            try:
                data_obj = datetime.strptime(data_recebimento, fmt).date()
                break
            except ValueError:
                continue
        
        if not data_obj:
            return []
        
        # Formatar data conforme está no banco (DD/MM/YYYY)
        data_formatada = data_obj.strftime('%d/%m/%Y')
        
        # Lazy import do modelo
        BaseTransacoesGestao = apps.get_model('gestao_financeira', 'BaseTransacoesGestao')
        
        # Buscar transações
        filtros = Q(var6__in=lojas_ids) & Q(var45=data_formatada)
        transacoes = BaseTransacoesGestao.objects.filter(filtros).order_by('var9', '-data_transacao')
        
        results = []
        for transacao in transacoes:
            results.append({
                'nsu': transacao.var9,
                'loja_id': int(transacao.var6) if transacao.var6 else None,
                'valor_transacao': transacao.var19,
                'valor_recebimento': transacao.var44,  # var44 é o valor correto
                'data_transacao': transacao.data_transacao,
                'data_recebimento': transacao.var45,
                'bandeira': transacao.var12,
                'parcelas': transacao.var13,
                'plano': transacao.var8,
            })
        
        registrar_log(
            'portais.lojista',
            f'Transações por data - Data: {data_formatada} - Total: {len(results)}'
        )
        
        return results
    
    @staticmethod
    def obter_lancamentos_por_data(lojas_ids, data_lancamento):
        """
        Busca lançamentos manuais de uma data específica.
        
        Args:
            lojas_ids (list): IDs das lojas acessíveis
            data_lancamento (str): Data no formato YYYY-MM-DD ou DD/MM/YYYY
            
        Returns:
            list: Lista de lançamentos da data
        """
        from gestao_financeira.models import LancamentoManual
        
        # Tentar formatos de data
        data_obj = None
        for fmt in ['%Y-%m-%d', '%d/%m/%Y']:
            try:
                data_obj = datetime.strptime(data_lancamento, fmt).date()
                break
            except ValueError:
                continue
        
        if not data_obj:
            return []
        
        # Buscar lançamentos
        filtros = Q(loja_id__in=lojas_ids) & Q(data_lancamento__date=data_obj) & Q(status='processado')
        lancamentos = LancamentoManual.objects.filter(filtros).order_by('-data_lancamento')
        
        results = []
        for lancamento in lancamentos:
            valor = Decimal(str(lancamento.valor)) if lancamento.valor else Decimal('0.00')
            if lancamento.tipo_lancamento == 'D':
                valor = -valor
            
            results.append({
                'id': lancamento.id,
                'loja_id': lancamento.loja_id,
                'tipo_lancamento': lancamento.tipo_lancamento,
                'tipo_display': lancamento.get_tipo_lancamento_display(),
                'valor': valor,
                'descricao': lancamento.descricao,
                'data_lancamento': lancamento.data_lancamento,
                'status': lancamento.status,
            })
        
        registrar_log(
            'portais.lojista',
            f'Lançamentos por data - Data: {data_obj} - Total: {len(results)}'
        )
        
        return results
    
    @staticmethod
    def obter_totalizadores(lojas_ids, data_inicio=None, data_fim=None):
        """
        Calcula totalizadores gerais de recebimentos.
        
        Args:
            lojas_ids (list): IDs das lojas acessíveis
            data_inicio (str): Data início formato YYYY-MM-DD
            data_fim (str): Data fim formato YYYY-MM-DD
            
        Returns:
            dict: Totalizadores (valor_total, quantidade, valor_medio)
        """
        recebimentos = RecebimentoService.obter_recebimentos_por_data(
            lojas_ids, data_inicio, data_fim
        )
        
        valor_total = Decimal('0.00')
        quantidade_total = 0
        
        for data_key, dados in recebimentos.items():
            valor_total += dados['valor_total']
            quantidade_total += dados['quantidade']
        
        valor_medio = valor_total / quantidade_total if quantidade_total > 0 else Decimal('0.00')
        
        return {
            'valor_total': valor_total,
            'quantidade_total': quantidade_total,
            'valor_medio': valor_medio,
            'total_datas': len(recebimentos)
        }
    
    @staticmethod
    def exportar_csv(lojas_ids, data_inicio=None, data_fim=None):
        """
        Gera arquivo CSV com recebimentos para exportação.
        
        Args:
            lojas_ids (list): IDs das lojas acessíveis
            data_inicio (str): Data início formato YYYY-MM-DD
            data_fim (str): Data fim formato YYYY-MM-DD
            
        Returns:
            str: Conteúdo CSV
        """
        import csv
        import io
        
        recebimentos = RecebimentoService.obter_recebimentos_por_data(
            lojas_ids, data_inicio, data_fim
        )
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Cabeçalho
        writer.writerow([
            'Data Recebimento',
            'Quantidade Transações',
            'Valor Total',
            'NSUs'
        ])
        
        # Dados
        for data_key, dados in sorted(recebimentos.items()):
            nsus = ', '.join([t['nsu'] for t in dados['transacoes']])
            writer.writerow([
                dados['data_formatada'],
                dados['quantidade'],
                f"{dados['valor_total']:.2f}",
                nsus
            ])
        
        registrar_log(
            'portais.lojista',
            f'CSV exportado - Lojas: {len(lojas_ids)} - Linhas: {len(recebimentos)}'
        )
        
        return output.getvalue()
