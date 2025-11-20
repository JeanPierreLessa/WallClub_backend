"""
Views para gerenciamento de transações no portal administrativo.
"""

from datetime import datetime, date, timedelta
from django.utils import timezone
from decimal import Decimal
from django.shortcuts import render
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.db import connection

from wallclub_core.database.queries import TransacoesQueries
from wallclub_core.estr_organizacional.loja import Loja
from wallclub_core.utilitarios.log_control import registrar_log
from ..controle_acesso.decorators import require_admin_access
from portais.controle_acesso.controle_acesso import require_funcionalidade, require_acesso_padronizado, require_secao_permitida
from portais.controle_acesso.filtros import FiltrosAcessoService
from .utils.column_mappings import obter_mapeamento_colunas_completo, obter_colunas_monetarias_gestao_financeira
from wallclub_core.utilitarios.export_utils import exportar_excel, exportar_csv
from sistema_bancario.models import PagamentoEfetuado
from django.apps import apps

@require_acesso_padronizado('base_transacoes_gestao')
def base_transacoes_gestao(request):
    """View para base de transações de gestão com filtros completos"""
    usuario = request.portal_usuario
    
    # View carregada
    
    # Filtros
    incluir_tef_raw = request.GET.get('incluir_tef')
    incluir_tef_bool = incluir_tef_raw == '1'
    # Filtros padrão - mês corrente inteiro
    hoje = date.today()
    primeiro_dia_mes = hoje.replace(day=1)
    
    # Calcular último dia do mês
    if hoje.month == 12:
        ultimo_dia_mes = hoje.replace(year=hoje.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        ultimo_dia_mes = hoje.replace(month=hoje.month + 1, day=1) - timedelta(days=1)
    
    filtros = {
        'data_inicial': request.GET.get('data_inicial', primeiro_dia_mes.strftime('%Y-%m-%d')),
        'data_final': request.GET.get('data_final', ultimo_dia_mes.strftime('%Y-%m-%d')),
        'canal': request.GET.get('canal', ''),
        'loja_id': request.GET.get('loja_id', ''),
        'nsu_filtro': request.GET.get('nsu_filtro', ''),
        'incluir_tef': incluir_tef_bool
    }
    
    # Construir WHERE clause para SQL direto
    from portais.controle_acesso.services import ControleAcessoService
    
    where_conditions = ["var68 = 'TRANS. APROVADO'"]
    params = []
    
    # Filtros de data
    if filtros['data_inicial']:
        where_conditions.append("data_transacao >= %s")
        params.append(f"{filtros['data_inicial']} 00:00:00")
    
    if filtros['data_final']:
        where_conditions.append("data_transacao <= %s")
        params.append(f"{filtros['data_final']} 23:59:59")
    
    # Filtros de acesso baseados em vínculos do usuário
    canais_usuario = ControleAcessoService.obter_canais_usuario(usuario)
    valores_var4_permitidos = []
    
    if canais_usuario:
        mapeamento_canais = {1: 'WALL 1', 6: 'ACLUB'}
        valores_var4_permitidos = [mapeamento_canais[cid] for cid in canais_usuario if cid in mapeamento_canais]
        
        if valores_var4_permitidos:
            placeholders = ','.join(['%s'] * len(valores_var4_permitidos))
            where_conditions.append(f"var4 IN ({placeholders})")
            params.extend(valores_var4_permitidos)
        else:
            # Sem dados - usuário sem canais mapeados
            where_conditions.append("1 = 0")
    
    # Filtro de canal do formulário
    if filtros['canal']:
        where_conditions.append("var4 = %s")
        params.append(filtros['canal'])
    
    # Filtro de NSU
    if filtros['nsu_filtro']:
        where_conditions.append("var9 LIKE %s")
        params.append(f"%{filtros['nsu_filtro']}%")
    
    # Filtro tipo_operacao (Credenciadora/Wallet)
    if not filtros['incluir_tef']:
        where_conditions.append("tipo_operacao = 'Wallet'")
    
    where_clause = " AND ".join(where_conditions)
    
    # Paginação
    page_number = int(request.GET.get('page', 1))
    per_page = 50
    offset = (page_number - 1) * per_page
    
    # Query SQL com ROW_NUMBER e paginação
    sql_dados = f"""
        SELECT * FROM (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY var9 ORDER BY id DESC) as rn
            FROM baseTransacoesGestao
            WHERE {where_clause}
        ) t 
        WHERE rn = 1
        ORDER BY data_transacao DESC
        LIMIT %s OFFSET %s
    """
    
    # Query para total
    sql_count = f"""
        SELECT COUNT(DISTINCT var9)
        FROM baseTransacoesGestao
        WHERE {where_clause}
    """
    
    # Executar queries
    with connection.cursor() as cursor:
        # Total de registros
        cursor.execute(sql_count, params)
        total_registros = cursor.fetchone()[0]
        
        # Dados paginados
        cursor.execute(sql_dados, params + [per_page, offset])
        columns = [col[0] for col in cursor.description]
        transacoes_data = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    # Criar objeto de paginação manual
    from django.core.paginator import Paginator, Page
    import math
    num_pages = math.ceil(total_registros / per_page) if total_registros > 0 else 1
    
    class SimplePage:
        def __init__(self, object_list, number, paginator):
            self.object_list = object_list
            self.number = number
            self.paginator = paginator
        
        def __iter__(self):
            return iter(self.object_list)
        
        def has_previous(self):
            return self.number > 1
        
        def has_next(self):
            return self.number < self.paginator.num_pages
        
        def previous_page_number(self):
            return self.number - 1
        
        def next_page_number(self):
            return self.number + 1
    
    class SimplePaginator:
        def __init__(self, count, per_page, num_pages):
            self.count = count
            self.per_page = per_page
            self.num_pages = num_pages
    
    paginator = SimplePaginator(total_registros, per_page, num_pages)
    transacoes = SimplePage(transacoes_data, page_number, paginator)
    
    # Carregar canais e lojas usando SQL direto
    from wallclub_core.estr_organizacional.services import HierarquiaOrganizacionalService
    with connection.cursor() as cursor:
        cursor.execute("SELECT DISTINCT var4 FROM baseTransacoesGestao ORDER BY var4")
        canais = [row[0] for row in cursor.fetchall()]
    lojas = [{'id': loja.id, 'nome': loja.razao_social} for loja in HierarquiaOrganizacionalService.listar_todas_lojas()]
    
    # Obter mapeamento de cabeçalhos
    cabecalhos = obter_mapeamento_colunas_completo()
    # Remover data_transacao da tela (manter apenas no CSV)
    cabecalhos_tela = {k: v for k, v in cabecalhos.items() if k != 'data_transacao'}
    colunas_monetarias = obter_colunas_monetarias_gestao_financeira()
    
    # Calcular totais no SQL
    totais = {}
    if transacoes_data:
        sum_fields = ', '.join([f"SUM(CAST({col} AS DECIMAL(15,2))) as {col}" for col in colunas_monetarias])
        sql_totais = f"""
            SELECT {sum_fields}
            FROM (
                SELECT *,
                       ROW_NUMBER() OVER (PARTITION BY var9 ORDER BY id DESC) as rn
                FROM baseTransacoesGestao
                WHERE {where_clause}
            ) t WHERE rn = 1
        """
        
        with connection.cursor() as cursor:
            cursor.execute(sql_totais, params)
            row = cursor.fetchone()
            for idx, coluna in enumerate(colunas_monetarias):
                totais[coluna] = float(row[idx] or 0)
    
    context = {
        'transacoes': transacoes,
        'filtros': filtros,
        'canais': canais,
        'lojas': lojas,
        'total_registros': total_registros,
        'cabecalhos': cabecalhos_tela,
        'colunas_monetarias': colunas_monetarias,
        'totais': totais,
    }
    
    return render(request, 'portais/admin/base_transacoes_gestao.html', context)

@require_secao_permitida('gestao_admin')
def exportar_transacoes_excel(request):
    """Exportar transações para Excel usando SQL direto"""
    try:
        # Import do modelo
        from gestao_financeira.models import BaseTransacoesGestao
        
        # Aplicar os mesmos filtros da view principal
        filtros = {
            'data_inicial': request.GET.get('data_inicial', date.today().replace(day=1).strftime('%Y-%m-%d')),
            'data_final': request.GET.get('data_final', date.today().strftime('%Y-%m-%d')),
            'loja_id': request.GET.get('loja_id', ''),
            'nsu_filtro': request.GET.get('nsu_filtro', ''),
            'incluir_tef': request.GET.get('incluir_tef') == '1'
        }
        
        # Construir queryset (mesmo código da view principal)
        queryset = BaseTransacoesGestao.objects.filter(var68='TRANS. APROVADO')
        
        if filtros['data_inicial']:
            # Converter para datetime timezone-aware
            # Usar datetime naive
            data_inicial_dt = datetime.strptime(filtros['data_inicial'], '%Y-%m-%d').replace(hour=0, minute=0, second=0)
            queryset = queryset.extra(
                where=["STR_TO_DATE(var0, '%%d/%%m/%%Y') >= %s"],
                params=[data_inicial_dt.date()]
            )
        
        if filtros['data_final']:
            # Converter para datetime timezone-aware
            # Usar datetime naive
            data_final_dt = datetime.strptime(filtros['data_final'], '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            queryset = queryset.extra(
                where=["STR_TO_DATE(var0, '%%d/%%m/%%Y') <= %s"],
                params=[data_final_dt.date()]
            )
        
        # Filtro de loja - removido para admin (deve ver todas as transações)
        
        if filtros['nsu_filtro']:
            queryset = queryset.filter(var9__icontains=filtros['nsu_filtro'])
        
        # Filtro tipo_operacao
        if not filtros['incluir_tef']:
            queryset = queryset.filter(tipo_operacao='Wallet')
        
        # Ordenação por data
        queryset = queryset.extra(
            select={'data_transacao': "STR_TO_DATE(var0, '%%d/%%m/%%Y')"},
            order_by=['-data_transacao']
        )
        
        # Subquery para pegar apenas o ID mais recente de cada NSU (evita duplicatas)
        from django.db.models import Max
        ids_unicos = queryset.values('var9').annotate(max_id=Max('id')).values_list('max_id', flat=True)
        queryset = BaseTransacoesGestao.objects.filter(id__in=ids_unicos).extra(
            select={'data_transacao': "STR_TO_DATE(var0, '%%d/%%m/%%Y')"},
            order_by=['-data_transacao']
        )
        
        # Verificar quantidade de registros
        total_registros = queryset.count()
        LIMITE_DIRETO = 5000
        
        registrar_log('portais.admin', f"TRANSACOES - Export Excel - {total_registros} registros - Limite: {LIMITE_DIRETO}")
        
        if total_registros > LIMITE_DIRETO:
            # Muitos registros - processar em background e enviar por email
            registrar_log('portais.admin', f"TRANSACOES - Background Excel - {total_registros} > {LIMITE_DIRETO}")
            return _processar_export_background(request, queryset, 'excel', total_registros)
        
        # Log para poucos registros
        registrar_log('portais.admin', f"TRANSACOES - Direto Excel - {total_registros} <= {LIMITE_DIRETO}")
        
        # Poucos registros - processar diretamente
        dados = []
        for transacao in queryset:
            item = {}
            # Adicionar tipo_operacao como primeira coluna
            if hasattr(transacao, 'tipo_operacao'):
                item['tipo_operacao'] = getattr(transacao, 'tipo_operacao')
            
            # Adicionar var0 até var130 com variantes _A e _B na ordem correta
            for i in range(131):  # var0 até var130
                campo = f'var{i}'
                if hasattr(transacao, campo):
                    item[campo] = getattr(transacao, campo)
                
                # Adicionar variante _A logo após se existir
                campo_a = f'var{i}_A'
                if hasattr(transacao, campo_a):
                    item[campo_a] = getattr(transacao, campo_a)
                
                # Adicionar variante _B logo após se existir
                campo_b = f'var{i}_B'
                if hasattr(transacao, campo_b):
                    item[campo_b] = getattr(transacao, campo_b)
            
            dados.append(item)
        
        cabecalhos = obter_mapeamento_colunas_completo()
        colunas_monetarias = obter_colunas_monetarias_gestao_financeira()
        
        nome_arquivo = f"transacoes_gestao_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        titulo = "Transacoes Gestao"
        
        registrar_log('portais.admin', f"TRANSACOES - Excel concluído - {len(dados)} registros")
        
        return exportar_excel(nome_arquivo, dados, cabecalhos, titulo, colunas_monetarias)
        
    except Exception as e:
        registrar_log('portais.admin', f"TRANSACOES - Erro Excel: {e}", nivel='ERROR')
        
        # Retornar JsonResponse de erro para evitar HTML
        from django.http import JsonResponse
        response = JsonResponse({
            'status': 'erro',
            'message': f'Erro ao processar export: {str(e)}',
            'error': True
        })
        response['Content-Type'] = 'application/json'
        response.status_code = 500
        return response

@require_secao_permitida('gestao_admin')
def exportar_transacoes_csv(request):
    """Exportar transações para CSV com proteção contra timeout"""
    # Import do modelo
    from gestao_financeira.models import BaseTransacoesGestao
    
    # Aplicar os mesmos filtros da view principal
    filtros = {
        'data_inicial': request.GET.get('data_inicial', date.today().replace(day=1).strftime('%Y-%m-%d')),
        'data_final': request.GET.get('data_final', date.today().strftime('%Y-%m-%d')),
        'loja_id': request.GET.get('loja_id', ''),
        'nsu_filtro': request.GET.get('nsu_filtro', ''),
        'incluir_tef': request.GET.get('incluir_tef') == '1'
    }
    
    # Construir queryset (mesmo código da view principal)
    queryset = BaseTransacoesGestao.objects.filter(var68='TRANS. APROVADO')
    
    if filtros['data_inicial']:
        # Converter para datetime timezone-aware
        data_inicial_dt = timezone.make_aware(
            datetime.strptime(filtros['data_inicial'], '%Y-%m-%d').replace(hour=0, minute=0, second=0)
        )
        queryset = queryset.extra(
            where=["STR_TO_DATE(var0, '%%d/%%m/%%Y') >= %s"],
            params=[data_inicial_dt.date()]
        )
    
    if filtros['data_final']:
        # Converter para datetime timezone-aware
        data_final_dt = timezone.make_aware(
            datetime.strptime(filtros['data_final'], '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        )
        queryset = queryset.extra(
            where=["STR_TO_DATE(var0, '%%d/%%m/%%Y') <= %s"],
            params=[data_final_dt.date()]
        )
    
    # Filtro de loja - removido para admin (deve ver todas as transações)
    
    if filtros['nsu_filtro']:
        queryset = queryset.filter(var9__icontains=filtros['nsu_filtro'])
    
    # Filtro tipo_operacao
    if not filtros['incluir_tef']:
        queryset = queryset.filter(tipo_operacao='Wallet')
    
    # Ordenação por data
    queryset = queryset.extra(
        select={'data_transacao': "STR_TO_DATE(var0, '%%d/%%m/%%Y')"},
        order_by=['-data_transacao']
    )
    
    # Subquery para pegar apenas o ID mais recente de cada NSU (evita duplicatas)
    from django.db.models import Max
    ids_unicos = queryset.values('var9').annotate(max_id=Max('id')).values_list('max_id', flat=True)
    queryset = BaseTransacoesGestao.objects.filter(id__in=ids_unicos).extra(
        select={'data_transacao': "STR_TO_DATE(var0, '%%d/%%m/%%Y')"},
        order_by=['-data_transacao']
    )
    
    # Verificar quantidade de registros
    total_registros = queryset.count()
    LIMITE_DIRETO = 5000
    
    registrar_log('portais.admin', f"TRANSACOES - Export CSV - {total_registros} registros - Limite: {LIMITE_DIRETO}")
    
    if total_registros > LIMITE_DIRETO:
        # Muitos registros - processar em background e enviar por email
        registrar_log('portais.admin', f"TRANSACOES - Background CSV - {total_registros} > {LIMITE_DIRETO}")
        return _processar_export_background(request, queryset, 'csv', total_registros)
    
    # Log para poucos registros
    registrar_log('portais.admin', f"TRANSACOES - Direto CSV - {total_registros} <= {LIMITE_DIRETO}")
    
    # Poucos registros - processar diretamente
    dados = []
    for transacao in queryset:
        item = {}
        # Adicionar tipo_operacao como primeira coluna
        if hasattr(transacao, 'tipo_operacao'):
            item['tipo_operacao'] = getattr(transacao, 'tipo_operacao')
        
        # Adicionar var0 até var130 com variantes _A e _B na ordem correta
        for i in range(131):  # var0 até var130
            campo = f'var{i}'
            if hasattr(transacao, campo):
                item[campo] = getattr(transacao, campo)
            
            # Adicionar variante _A logo após se existir
            campo_a = f'var{i}_A'
            if hasattr(transacao, campo_a):
                item[campo_a] = getattr(transacao, campo_a)
            
            # Adicionar variante _B logo após se existir
            campo_b = f'var{i}_B'
            if hasattr(transacao, campo_b):
                item[campo_b] = getattr(transacao, campo_b)
        
        # Adicionar data_transacao se existir
        if hasattr(transacao, 'data_transacao'):
            item['data_transacao'] = transacao.data_transacao
        
        dados.append(item)
    
    cabecalhos = obter_mapeamento_colunas_completo()
    colunas_monetarias = obter_colunas_monetarias_gestao_financeira()
    
    nome_arquivo = f"transacoes_gestao_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    registrar_log('portais.admin', f"TRANSACOES - CSV concluído - {len(dados)} registros")
    
    return exportar_csv(nome_arquivo, dados, cabecalhos, colunas_monetarias)


def _processar_export_background(request, queryset, formato, total_registros):
    """Processa export em background e envia por email - ÚNICA rotina para Excel e CSV"""
    from django.http import JsonResponse
    from django.conf import settings
    from wallclub_core.integracoes.email_service import EmailService
    import threading
    import tempfile
    import os
    
    # Capturar dados do usuário ANTES da thread (contexto da requisição)
    # O sistema usa PortalUsuario, não Django User
    portal_usuario = getattr(request, 'portal_usuario', None)
    if portal_usuario:
        usuario_email = portal_usuario.email
        usuario_nome = portal_usuario.nome or 'Usuário'
    else:
        usuario_email = None
        usuario_nome = 'Usuário'
    
    def processar_e_enviar():
        try:
            registrar_log('portais.admin', f"TRANSACOES - Thread iniciada")
            
            # Sempre usar CSV para exports em background para otimizar memória
            import csv
            import tempfile
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
                arquivo_path = temp_file.name
            
            registrar_log('portais.admin', f"TRANSACOES - Batches 1000 registros")
            
            # Processar em batches para evitar estouro de memória
            batch_size = 1000
            total_processados = 0
            
            # Usar exatamente a mesma estrutura da tela e do export direto
            cabecalhos = obter_mapeamento_colunas_completo()
            colunas_monetarias = obter_colunas_monetarias_gestao_financeira()
            
            # Função para remover acentos
            def remover_acentos(texto):
                import unicodedata
                if not texto:
                    return texto
                
                # Normalizar e remover acentos
                texto_normalizado = unicodedata.normalize('NFD', str(texto))
                texto_sem_acentos = ''.join(c for c in texto_normalizado if unicodedata.category(c) != 'Mn')
                
                # Substituições específicas
                substituicoes = {
                    'ç': 'c', 'Ç': 'C',
                    'ñ': 'n', 'Ñ': 'N'
                }
                
                for original, substituto in substituicoes.items():
                    texto_sem_acentos = texto_sem_acentos.replace(original, substituto)
                
                return texto_sem_acentos
            
            with open(arquivo_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile, delimiter=';')
                
                # Headers - usar os mesmos da tela (sem acentos)
                headers_sem_acentos = [remover_acentos(header) for header in cabecalhos.values()]
                writer.writerow(headers_sem_acentos)
                
                for start in range(0, total_registros, batch_size):
                    batch = queryset[start:start + batch_size]
                    
                    for transacao in batch:
                        # Montar item exatamente como na tela
                        item = {}
                        # Adicionar tipo_operacao como primeira coluna
                        if hasattr(transacao, 'tipo_operacao'):
                            item['tipo_operacao'] = getattr(transacao, 'tipo_operacao')
                        
                        # Adicionar var0 até var130 com variantes _A e _B na ordem correta
                        for i in range(131):  # var0 até var130
                            campo = f'var{i}'
                            if hasattr(transacao, campo):
                                item[campo] = getattr(transacao, campo)
                            
                            # Adicionar variante _A logo após se existir
                            campo_a = f'var{i}_A'
                            if hasattr(transacao, campo_a):
                                item[campo_a] = getattr(transacao, campo_a)
                            
                            # Adicionar variante _B logo após se existir
                            campo_b = f'var{i}_B'
                            if hasattr(transacao, campo_b):
                                item[campo_b] = getattr(transacao, campo_b)
                        
                        # Adicionar data_transacao se existir
                        if hasattr(transacao, 'data_transacao'):
                            item['data_transacao'] = transacao.data_transacao
                        
                        # Escrever linha usando a mesma ordem dos cabeçalhos
                        linha = []
                        for var_name in cabecalhos.keys():
                            valor = item.get(var_name, '')
                            
                            # Formatação especial para campos monetários
                            if var_name in colunas_monetarias and valor:
                                try:
                                    valor_float = float(valor)
                                    valor = f"{valor_float:.2f}".replace('.', ',')
                                except:
                                    valor = str(valor) if valor else ''
                            # Formatação especial para data
                            elif var_name == 'data_transacao' and valor:
                                try:
                                    valor = valor.strftime('%d/%m/%Y') if hasattr(valor, 'strftime') else str(valor)
                                except:
                                    valor = str(valor)
                            else:
                                valor = str(valor) if valor else ''
                            
                            # Remover acentos de todos os valores
                            valor = remover_acentos(valor)
                            linha.append(valor)
                        
                        writer.writerow(linha)
                    
                    total_processados += len(batch)
                    registrar_log('portais.admin', f"TRANSACOES - Processados {total_processados}/{total_registros}")
            
            # Enviar por email usando EmailService
            nome_arquivo = f"transacoes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            mensagem = f'''Olá {usuario_nome},

Seu export de transações foi processado com sucesso!

Detalhes:
- Total de registros: {total_registros:,}
- Formato: CSV (otimizado para grande volume de dados)
- Data/hora: {datetime.now().strftime('%d/%m/%Y às %H:%M')}

O arquivo está anexado a este email.

Atenciosamente,
Sistema WallClub'''
            
            # Ler arquivo para anexo
            with open(arquivo_path, 'rb') as f:
                conteudo_csv = f.read()
            
            resultado = EmailService.enviar_email(
                destinatarios=[usuario_email],
                assunto=f'Export de Transações - {total_registros:,} registros',
                mensagem_texto=mensagem,
                anexos=[{
                    'nome': nome_arquivo,
                    'conteudo': conteudo_csv,
                    'tipo': 'text/csv'
                }],
                fail_silently=True
            )
            
            if resultado['sucesso']:
                registrar_log('portais.admin', f"TRANSACOES - Email enviado {usuario_email} - {total_registros} registros")
            else:
                registrar_log('portais.admin', f"TRANSACOES - Erro ao enviar email: {resultado['mensagem']}", nivel='ERROR')
            
            # Limpar arquivo temporário
            try:
                os.unlink(arquivo_path)
            except:
                pass
                
        except Exception as e:
            registrar_log('portais.admin', f"TRANSACOES - Erro background: {e}", nivel='ERROR')
            
            # Enviar email de erro usando EmailService
            if usuario_email:
                try:
                    EmailService.enviar_email_simples(
                        destinatario=usuario_email,
                        assunto='Erro no Export de Transações',
                        mensagem=f'Ocorreu um erro ao processar seu export: {str(e)}',
                        fail_silently=True
                    )
                except:
                    pass
            
    # Log antes de iniciar thread
    registrar_log('portais.admin', f"TRANSACOES - Thread start {total_registros} registros - {usuario_email}")
    
    # Iniciar processamento em background
    thread = threading.Thread(target=processar_e_enviar)
    thread.daemon = True
    thread.start()
    
    registrar_log('portais.admin', f"TRANSACOES - Thread success")
    
    # Retornar resposta imediata com content-type explícito
    response = JsonResponse({
        'status': 'processando',
        'message': f'Export de {total_registros:,} registros iniciado em formato CSV (otimizado para grande volume). Você receberá o arquivo por email quando estiver pronto.',
        'total_registros': total_registros,
        'email': usuario_email
    })
    response['Content-Type'] = 'application/json'
    return response


# Funções movidas para utils/column_mappings.py para unificação
