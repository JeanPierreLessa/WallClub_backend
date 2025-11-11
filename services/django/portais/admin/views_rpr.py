"""
Views para Relatório de Produção e Receita (RPR)
"""

from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.db import connection
from datetime import datetime, date
from decimal import Decimal
import decimal
import json
from ..controle_acesso.decorators import require_admin_access
from portais.controle_acesso.controle_acesso import require_funcionalidade, require_acesso_padronizado
from wallclub_core.database.queries import TransacoesQueries
from wallclub_core.estr_organizacional.loja import Loja
from wallclub_core.estr_organizacional.canal import Canal
from wallclub_core.estr_organizacional.services import HierarquiaOrganizacionalService
from sistema_bancario.models import LancamentoManual
from .utils.column_mappings import (
    obter_mapeamento_colunas_rpr, 
    obter_colunas_monetarias_rpr
)
from wallclub_core.utilitarios.export_utils import exportar_csv
from wallclub_core.utilitarios.log_control import registrar_log


def obter_nomes_canais_por_ids(canal_ids):
    """
    Função auxiliar para obter nomes de canais a partir de IDs usando método centralizado
    """
    from wallclub_core.estr_organizacional.canal import Canal
    
    nomes_canais = []
    for canal_id in canal_ids:
        canal_nome = Canal.get_canal_nome(canal_id)
        if canal_nome and canal_nome != f"Canal {canal_id}":
            nomes_canais.append(canal_nome)
    
    return nomes_canais


def obter_estrutura_colunas_rpr():
    """
    ESTRUTURA COMPLETA DE COLUNAS RPR:
    ==================================
    
    tipo_operacao
    var9
    var0
    var1
    var68
    var5
    var6
    var4
    var11
    var26
    var36 
    var37 
    var89 
    var90
    (formula) var36 - var89 nome_coluna: "Resultado MDR (%)"  #variavel_nova_1
    (formula) var37 - var90 nome_coluna: "Resultado MDR (R$)" #variavel_nova_2
    var39 
    var92 
    var40
    var93_A
    var41
    (formula) volta o modulo de var14 (valor absoluto) nome_coluna: "Encargos Cobrados Clientes Finais (%)"  #variavel_nova_3
    var15
    (formula) var15 + var41 nome_coluna: "Receita Total Antec. + Encargos (Total - R$)" #variavel_nova_4
    var94_A
    (formula) variavel_nova_5 / var11 nome_coluna: "Resultado Antecipação & Parcelamento (%)" #variavel_nova_6
    (formula) variavel_nova_4 - var94_A nome_coluna: "Resultado Antecipação & Parcelamento (R$)" #variavel_nova_5
    (formula) se var11<>0 entao variavel_nova_8/ var11 nome_coluna: "Resultado Operacional (projetado) %" #variavel_nova_7
    (formula) variavel_nova_5 + variavel_nova_2 nome_coluna: "Resultado Operacional (projetado) R$" #variavel_nova_8 
    var98
    var101
    (formula) Se var101=0 mostra "Não Finalizada", senao  var98-var101  nome_coluna: "Resultado Caixa (Rcebtos - Repasses) R$" #variavel_nova_9
    (formula) Se var101=0 mostra "Não Finalizada", senao #variavel_nova_11/var11 nome_coluna: "Resultado Operacional (antes Cashback e Chargeback) %" #variavel_nova_10
    (formula) se var101=0 mostra "Não Finalizada", senao var113_A nome_coluna: "Resultado Operacional (antes Cashback e Chargeback) R$" #variavel_nova_11
    (formula) var58/var11 nome_coluna: "Cashback pago à Loja (%)" #variavel_nova_12
    var58
    var111_A
    (formula) Se var101=0 mostra "Não Finalizada", senao var109_A nome_coluna: "Impostos Diretos pagos (R$)" #variavel_nova_13
    (formula) Se var101=0 mostra "Não Finalizada", senao var118_A nome_coluna: "Resultado Final (pós impostos - sem POS) - Visão Gestão - %" #variavel_nova_14
    (formula) Se var101=0 mostra "Não Finalizada", senao var116_A nome_coluna: "Resultado Final (pós impostos - sem POS) - Visão Gestão - R$" #variavel_nova_15
    (formula) Se var101=0 mostra "Não Finalizada", senao #variavel_nova_17/var26 nome_coluna: "Resultado Final (pós impostos - sem POS) %" #variavel_nova_16
    (formula) Se var101=0 mostra "Não Finalizada", senao #variavel_nova_11-#variavel_nova_13 nome_coluna: "Resultado Final (pós impostos - sem POS) R$" #variavel_nova_17
    var10
    var8
    var12
    var13
    var43
    """
    return [
        # 0: Tipo de transação
        {'tipo': 'variavel', 'campo': 'tipo_operacao', 'nome': None},
        
        # 1-13: Variáveis base
        {'tipo': 'variavel', 'campo': 'var9', 'nome': None},
        {'tipo': 'variavel', 'campo': 'var0', 'nome': None},
        {'tipo': 'variavel', 'campo': 'var1', 'nome': None},
        {'tipo': 'variavel', 'campo': 'var68', 'nome': None},
        {'tipo': 'variavel', 'campo': 'var5', 'nome': None},
        {'tipo': 'variavel', 'campo': 'var6', 'nome': None},
        {'tipo': 'variavel', 'campo': 'var4', 'nome': None},
        {'tipo': 'variavel', 'campo': 'var11', 'nome': None},
        {'tipo': 'variavel', 'campo': 'var26', 'nome': None},
        {'tipo': 'variavel', 'campo': 'var36', 'nome': None},
        {'tipo': 'variavel', 'campo': 'var37', 'nome': None},
        {'tipo': 'variavel', 'campo': 'var89', 'nome': None},
        {'tipo': 'variavel', 'campo': 'var90', 'nome': None},
        
        # 14-15: Primeiras fórmulas MDR
        {'tipo': 'formula', 'campo': 'variavel_nova_1', 'nome': 'Resultado MDR (%)', 'formula': 'var36 - var89'},
        {'tipo': 'formula', 'campo': 'variavel_nova_2', 'nome': 'Resultado MDR (R$)', 'formula': 'var37 - var90'},
        
        # 16-20: Mais variáveis
        {'tipo': 'variavel', 'campo': 'var39', 'nome': None},
        {'tipo': 'variavel', 'campo': 'var92', 'nome': None},
        {'tipo': 'variavel', 'campo': 'var40', 'nome': None},
        {'tipo': 'variavel', 'campo': 'var93_A', 'nome': None},
        {'tipo': 'variavel', 'campo': 'var41', 'nome': None},
        
        # 21: Fórmula encargos
        {'tipo': 'formula', 'campo': 'variavel_nova_3', 'nome': 'Encargos Cobrados Clientes Finais (%)', 'formula': 'abs(var14)'},
        
        # 22: var15
        {'tipo': 'variavel', 'campo': 'var15', 'nome': None},
        
        # 23: Fórmula receita total
        {'tipo': 'formula', 'campo': 'variavel_nova_4', 'nome': 'Receita Total Antec. + Encargos (Total - R$)', 'formula': 'var15 + var41'},
        
        # 24: var94_A
        {'tipo': 'variavel', 'campo': 'var94_A', 'nome': None},
        
        # 25: Fórmula antecipação percentual (exibição)
        {'tipo': 'formula', 'campo': 'variavel_nova_6', 'nome': 'Resultado Antecipação & Parcelamento (%)', 'formula': 'variavel_nova_5 / var11 if var11 != 0 else 0'},
        
        # 26: Fórmula antecipação monetária (cálculo)
        {'tipo': 'formula', 'campo': 'variavel_nova_5', 'nome': 'Resultado Antecipação & Parcelamento (R$)', 'formula': 'variavel_nova_4 - var94_A'},
        
        # 27: Fórmula operacional percentual (exibição)
        {'tipo': 'formula', 'campo': 'variavel_nova_7', 'nome': 'Resultado Operacional (projetado) %', 'formula': 'variavel_nova_8 / var11 if var11 != 0 else 0'},
        
        # 28: Fórmula operacional monetária (cálculo)
        {'tipo': 'formula', 'campo': 'variavel_nova_8', 'nome': 'Resultado Operacional (projetado) R$', 'formula': 'variavel_nova_5 + variavel_nova_2'},
        
        # 29-30: var98, var101
        {'tipo': 'variavel', 'campo': 'var98', 'nome': None},
        {'tipo': 'variavel', 'campo': 'var101', 'nome': None},
        
        # 31-33: Fórmulas resultado caixa e operacional
        {'tipo': 'formula', 'campo': 'variavel_nova_9', 'nome': 'Resultado Caixa (Rcebtos - Repasses) R$', 'formula': '"Não Finalizada" if var101 == 0 else var98 - var101'},
        {'tipo': 'formula', 'campo': 'variavel_nova_11', 'nome': 'Resultado Operacional (antes Cashback e Chargeback) R$', 'formula': '"Não Finalizada" if var101 == 0 else var113_A'},
        {'tipo': 'formula', 'campo': 'variavel_nova_10', 'nome': 'Resultado Operacional (antes Cashback e Chargeback) %', 'formula': '"Não Finalizada" if var101 == 0 else variavel_nova_11 / var11 if var11 != 0 else 0'},
        
        # 34: Fórmula cashback
        {'tipo': 'formula', 'campo': 'variavel_nova_12', 'nome': 'Cashback pago à Loja (%)', 'formula': 'var58 / var11 if var11 != 0 else 0'},
        
        # 35-36: var58, var111_A
        {'tipo': 'variavel', 'campo': 'var58', 'nome': None},
        {'tipo': 'variavel', 'campo': 'var111_A', 'nome': None},
        
        # 37-41: Fórmulas resultado final
        {'tipo': 'formula', 'campo': 'variavel_nova_13', 'nome': 'Impostos Diretos pagos (R$)', 'formula': '"Não Finalizada" if var101 == 0 else var109_A'},
        {'tipo': 'formula', 'campo': 'variavel_nova_14', 'nome': 'Resultado Final (pós impostos - sem POS) - Visão Gestão - %', 'formula': '"Não Finalizada" if var101 == 0 else var118_A'},
        {'tipo': 'formula', 'campo': 'variavel_nova_15', 'nome': 'Resultado Final (pós impostos - sem POS) - Visão Gestão - R$', 'formula': '"Não Finalizada" if var101 == 0 else var116_A'},
        {'tipo': 'formula', 'campo': 'variavel_nova_16', 'nome': 'Resultado Final (pós impostos - sem POS) %', 'formula': '"Não Finalizada" if var101 == 0 else variavel_nova_17 / var26 if var26 != 0 else 0'},
        {'tipo': 'formula', 'campo': 'variavel_nova_17', 'nome': 'Resultado Final (pós impostos - sem POS) R$', 'formula': '"Não Finalizada" if var101 == 0 else variavel_nova_11 - variavel_nova_13'},
        
        # 42-46: Variáveis finais
        {'tipo': 'variavel', 'campo': 'var10', 'nome': None},
        {'tipo': 'variavel', 'campo': 'var8', 'nome': None},
        {'tipo': 'variavel', 'campo': 'var12', 'nome': None},
        {'tipo': 'variavel', 'campo': 'var13', 'nome': None},
        {'tipo': 'variavel', 'campo': 'var43', 'nome': None},
    ]


def obter_mapeamento_colunas_rpr_dinamico():
    """Retorna mapeamento específico para tabela RPR baseado na nova estrutura"""
    from .utils.column_mappings import obter_mapeamento_colunas_completo
    
    mapeamento_completo = obter_mapeamento_colunas_completo()
    estrutura = obter_estrutura_colunas_rpr()
    
    mapeamento = {}
    for item in estrutura:
        if item['tipo'] == 'variavel':
            # Usar mapeamento existente
            if item['campo'] in mapeamento_completo:
                mapeamento[item['campo']] = mapeamento_completo[item['campo']]
        elif item['tipo'] == 'formula':
            # Usar nome personalizado da fórmula
            mapeamento[item['campo']] = item['nome']
    
    return mapeamento


def obter_colunas_monetarias_rpr_dinamico():
    """Retorna lista de colunas que devem ser formatadas como monetárias no RPR"""
    estrutura = obter_estrutura_colunas_rpr()
    colunas_monetarias = []
    
    for item in estrutura:
        campo = item['campo']
        # Variáveis monetárias conhecidas
        if campo in ['var11', 'var15', 'var26', 'var37', 'var41', 'var90', 'var94_A', 'var98', 'var101', 'var58', 'var111_A', 'var109_A', 'var113_A', 'var116_A', 'var118_A']:
            colunas_monetarias.append(campo)
        # Fórmulas que resultam em valores monetários (R$)
        elif item['tipo'] == 'formula' and 'R$' in item['nome']:
            colunas_monetarias.append(campo)
    
    return colunas_monetarias


def obter_colunas_percentuais_rpr_dinamico():
    """Retorna lista de colunas que devem ser formatadas como percentuais no RPR"""
    estrutura = obter_estrutura_colunas_rpr()
    colunas_percentuais = []
    
    for item in estrutura:
        campo = item['campo']
        # Variáveis percentuais conhecidas
        if campo in ['var36', 'var89', 'var39', 'var92', 'var40', 'var93_A']:
            colunas_percentuais.append(campo)
        # Fórmulas que resultam em percentuais (%)
        elif item['tipo'] == 'formula' and '%' in item['nome']:
            colunas_percentuais.append(campo)
    
    return colunas_percentuais


@require_acesso_padronizado('rpr_view')
def relatorio_producao_receita(request):
    """View para Relatório de Produção e Receita (RPR)"""
    
    # Validar acesso à loja se especificada
    loja_param = request.GET.get('loja', '')
    if loja_param:
        from portais.controle_acesso.filtros import FiltrosAcessoService
        from django.contrib import messages
        from django.shortcuts import redirect
        
        try:
            FiltrosAcessoService.validar_acesso_loja_ou_403(request.portal_usuario, int(loja_param))
        except:
            messages.error(request, 'A tela que você tentou acessar não está disponível pro seu perfil.')
            return redirect('portais_admin:dashboard')
    
    # Filtros padrão - mês corrente inteiro
    hoje = date.today()
    primeiro_dia_mes = hoje.replace(day=1)
    
    filtros = {
        'data_inicial': request.GET.get('data_inicial', primeiro_dia_mes.strftime('%Y-%m-%d')),
        'data_final': request.GET.get('data_final', hoje.strftime('%Y-%m-%d')),
        'canal': request.GET.get('canal', ''),
        'loja': request.GET.get('loja', ''),
        'incluir_tef': request.GET.get('incluir_tef') == '1',
    }
    
    # Construir WHERE clause para SQL direto
    from portais.controle_acesso.services import ControleAcessoService
    
    where_conditions = ["var68 = 'TRANS. APROVADO'"]
    params = []
    
    # Filtro de data
    if filtros['data_inicial']:
        where_conditions.append("data_transacao >= %s")
        params.append(f"{filtros['data_inicial']} 00:00:00")
    
    if filtros['data_final']:
        where_conditions.append("data_transacao <= %s")
        params.append(f"{filtros['data_final']} 23:59:59")
    
    # Filtro de canal
    canais_usuario = ControleAcessoService.obter_canais_usuario(request.portal_usuario)
    
    if canais_usuario:
        nomes_canais = []
        for canal_id in canais_usuario:
            try:
                canal = HierarquiaOrganizacionalService.get_canal(canal_id)
                if canal and canal.nome:
                    nomes_canais.append(canal.nome)
            except Exception:
                continue
        
        if nomes_canais:
            placeholders = ','.join(['%s'] * len(nomes_canais))
            where_conditions.append(f"var4 IN ({placeholders})")
            params.extend(nomes_canais)
    elif filtros['canal']:
        where_conditions.append("var4 = %s")
        params.append(filtros['canal'])
    
    # Filtro de loja
    if filtros['loja']:
        where_conditions.append("var6 = %s")
        params.append(filtros['loja'])
    
    # Filtro tipo_operacao (Credenciadora/Wallet)
    if not filtros['incluir_tef']:
        where_conditions.append("tipo_operacao = 'Wallet'")
    
    where_clause = " AND ".join(where_conditions)
    
    # Query SQL consolidada com todas as agregações
    sql = f"""
        SELECT 
            COUNT(DISTINCT var9) as qtde_nsus_distintos,
            SUM(CAST(var11 AS DECIMAL(15,2))) as volume_total,
            SUM(CAST(var23 AS DECIMAL(15,2))) as receita_var23,
            SUM(CAST(var21 AS DECIMAL(15,2))) as receita_var21,
            SUM(CAST(var14 AS DECIMAL(15,2))) as custo_mdr_total,
            SUM(CAST(var37 AS DECIMAL(15,2))) as receita_mdr_total,
            SUM(CAST(var90 AS DECIMAL(15,2))) as custo_mdr_direto,
            SUM(CAST(var94_A AS DECIMAL(15,2))) as custo_antecipacao_direto,
            SUM(CAST(var41 AS DECIMAL(15,2))) as receita_var41,
            SUM(CASE WHEN CAST(var14 AS DECIMAL(15,2)) < 0 AND var15 IS NOT NULL 
                     THEN ABS(CAST(var15 AS DECIMAL(15,2))) * 100 
                     ELSE 0 END) as receita_var14_var15,
            SUM(CAST(var109_A AS DECIMAL(15,2))) as impostos_total,
            SUM(CASE WHEN var101 IS NOT NULL AND CAST(var101 AS DECIMAL(15,2)) != 0 
                     THEN CAST(var116_A AS DECIMAL(15,2)) 
                     ELSE 0 END) as resultado_financeiro
        FROM (
            SELECT *,
                   ROW_NUMBER() OVER (PARTITION BY var9 ORDER BY id DESC) as rn
            FROM baseTransacoesGestao
            WHERE {where_clause}
        ) t WHERE rn = 1
    """
    
    registrar_log('portais.admin', f"RPR - Relatório gerado - Filtros: {filtros}")
    
    # Executar query consolidada
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        resultado = cursor.fetchone()
    
    # Extrair resultados
    qtde_nsus_distintos = resultado[0] or 0
    total_transacoes = qtde_nsus_distintos
    
    volume_total = Decimal(str(resultado[1] or 0))
    receita_var23 = Decimal(str(resultado[2] or 0))
    receita_var21 = Decimal(str(resultado[3] or 0))
    custo_mdr_total_raw = Decimal(str(resultado[4] or 0))
    receita_mdr_total = Decimal(str(resultado[5] or 0))
    custo_mdr_direto = Decimal(str(resultado[6] or 0))
    custo_antecipacao_direto = Decimal(str(resultado[7] or 0))
    receita_var41 = Decimal(str(resultado[8] or 0))
    receita_var14_var15 = Decimal(str(resultado[9] or 0))
    impostos_total = Decimal(str(resultado[10] or 0))
    resultado_financeiro = Decimal(str(resultado[11] or 0))
    
    # Cálculos derivados
    receita_antecipacao_parcelamentos = receita_var41 + receita_var14_var15
    receita_outras_tarifas = Decimal('0.00')
    receita_financeira_total = receita_mdr_total + receita_antecipacao_parcelamentos + receita_outras_tarifas
    
    custo_mdr_total = custo_mdr_direto
    custo_antecipacao_total = custo_antecipacao_direto
    custos_pos_equip = Decimal('0.00')
    custo_direto_total = custo_mdr_total + custo_antecipacao_total + custos_pos_equip + impostos_total
    
    receita_antecipacao = receita_var23 + receita_var21
    
    # Manter compatibilidade com código legado
    metricas = {
        'volume_total': volume_total,
        'receita_var23': receita_var23,
        'receita_var21': receita_var21,
        'custo_mdr_total': custo_mdr_total_raw,
        'receita_mdr_total': receita_mdr_total,
        'custo_mdr_direto': custo_mdr_direto,
        'custo_antecipacao_direto': custo_antecipacao_direto
    }
    
    # Calcular ticket médio
    volume_total = metricas['volume_total'] or Decimal('0.00')
    ticket_medio = Decimal('0.00')
    if qtde_nsus_distintos > 0 and volume_total > 0:
        ticket_medio = volume_total / qtde_nsus_distintos
    
    # Calcular percentual de comissão usando nova tabela canal_comissao
    percentual_comissao = Decimal('0.00')
    
    def obter_comissao_vigente_canal(canal_nome, data_referencia):
        """Busca comissão vigente do canal na data de referência"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT cc.comissao
                FROM canal_comissao cc
                JOIN canal c ON cc.canal_id = c.id
                WHERE c.nome = %s 
                AND cc.vigencia_inicio <= %s
                AND (cc.vigencia_fim IS NULL OR cc.vigencia_fim >= %s)
                ORDER BY cc.vigencia_inicio DESC
                LIMIT 1
            """, [canal_nome, data_referencia, data_referencia])
            
            result = cursor.fetchone()
            return Decimal(str(result[0])) if result else Decimal('0.00')
    
    # Data de referência para buscar comissão (usar data final do filtro ou hoje)
    data_referencia = filtros.get('data_final') or date.today().strftime('%Y-%m-%d')
    
    if filtros['canal']:
        # Filtro por canal específico - buscar comissão vigente
        percentual_comissao = obter_comissao_vigente_canal(filtros['canal'], data_referencia)
    else:
        # Sem filtro de canal - calcular média ponderada por volume via SQL
        sql_volume_canal = f"""
            SELECT 
                var4 as canal_nome,
                SUM(CAST(var26 AS DECIMAL(15,2))) as volume_canal
            FROM (
                SELECT var4, var26,
                       ROW_NUMBER() OVER (PARTITION BY var9 ORDER BY id DESC) as rn
                FROM baseTransacoesGestao
                WHERE {where_clause}
            ) t 
            WHERE rn = 1 AND var4 IS NOT NULL
            GROUP BY var4
        """
        
        volume_por_canal = {}
        with connection.cursor() as cursor:
            cursor.execute(sql_volume_canal, params)
            for row in cursor.fetchall():
                canal_nome = row[0]
                volume = Decimal(str(row[1] or 0))
                if canal_nome and volume > 0:
                    volume_por_canal[canal_nome] = volume
        
        # Calcular comissão média ponderada usando nova tabela
        volume_total_canais = sum(volume_por_canal.values())
        comissao_ponderada = Decimal('0.00')
        
        if volume_total_canais > 0:
            for canal_nome, volume in volume_por_canal.items():
                comissao_canal = obter_comissao_vigente_canal(canal_nome, data_referencia)
                if comissao_canal > 0:
                    peso = volume / volume_total_canais
                    comissao_ponderada += comissao_canal * peso
            
            percentual_comissao = comissao_ponderada
    
    # Calcular lançamentos manuais com filtros aplicados
    lancamentos_manuais_queryset = LancamentoManual.objects.filter(
        status='processado',
        tipo_lancamento='D'  # Apenas débitos
    )
    
    # Aplicar filtros de data
    if filtros['data_inicial']:
        data_inicial = datetime.strptime(filtros['data_inicial'], '%Y-%m-%d').date()
        lancamentos_manuais_queryset = lancamentos_manuais_queryset.filter(
            data_lancamento__date__gte=data_inicial
        )
    
    if filtros['data_final']:
        data_final = datetime.strptime(filtros['data_final'], '%Y-%m-%d').date()
        lancamentos_manuais_queryset = lancamentos_manuais_queryset.filter(
            data_lancamento__date__lte=data_final
        )
    
    # Aplicar filtro de loja
    if filtros['loja']:
        lancamentos_manuais_queryset = lancamentos_manuais_queryset.filter(
            loja_id=filtros['loja']
        )
    
    # Calcular total de lançamentos manuais
    total_lancamentos_manuais = lancamentos_manuais_queryset.aggregate(
        total=Sum('valor')
    )['total'] or Decimal('0.00')
    
    # Calcular comissão líquida
    comissao_total_pagar = resultado_financeiro * percentual_comissao
    comissao_liquida_pagar = comissao_total_pagar - total_lancamentos_manuais
    
    # Preparar dados para o template
    dados_metricas = {
        'volume_total': volume_total,
        'qtde_nsus_distintos': qtde_nsus_distintos,
        'ticket_medio': ticket_medio,
        'receita_antecipacao': receita_antecipacao,
        'total_transacoes': total_transacoes,
        
        # Receita Financeira Total
        'receita_mdr_total': receita_mdr_total,
        'receita_antecipacao_parcelamentos': receita_antecipacao_parcelamentos,
        'receita_outras_tarifas': receita_outras_tarifas,
        'receita_financeira_total': receita_financeira_total,
        
        # Custo Direto Total
        'custo_mdr_total': custo_mdr_total,
        'custo_antecipacao_total': custo_antecipacao_total,
        'custos_pos_equip': custos_pos_equip,
        'impostos_total': impostos_total,
        'custo_direto_total': custo_direto_total,
        
        # Resultado Financeiro
        'resultado_financeiro': resultado_financeiro,
        'percentual_comissao': percentual_comissao * 100,  # Converter 0.2 para 20%
        'comissao_total_pagar': comissao_total_pagar,
        'total_lancamentos_manuais': total_lancamentos_manuais,
        'comissao_liquida_pagar': comissao_liquida_pagar,
    }
    
    # Buscar opções para filtros - filtrar por vínculos do usuário
    from portais.controle_acesso.services import ControleAcessoService
    from portais.controle_acesso.filtros import FiltrosAcessoService
    from .services_rpr import RPRService
    
    canais_usuario = ControleAcessoService.obter_canais_usuario(request.portal_usuario)
    
    # Usar service para buscar canais
    canais = RPRService.buscar_canais_disponiveis(canais_usuario)
    
    # Buscar lojas acessíveis
    lojas_acessiveis = FiltrosAcessoService.obter_lojas_acessiveis(request.portal_usuario)
    lojas = lojas_acessiveis
    
    context = {
        'filtros': filtros,
        'dados_metricas': dados_metricas,
        'canais': canais,
        'lojas': lojas,
    }
    
    return render(request, 'portais/admin/relatorio_producao_receita.html', context)


@require_funcionalidade('rpr_view')
def tabela_rpr_ajax(request):
    """View AJAX para tabela RPR com paginação e filtros"""
    
    # Parâmetros de paginação
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 50))
    
    # Filtros
    filtros = {
        'data_inicial': request.GET.get('data_inicial', ''),
        'data_final': request.GET.get('data_final', ''),
        'canal': request.GET.get('canal', ''),
        'loja': request.GET.get('loja', ''),
        'nsu': request.GET.get('nsu', ''),
        'incluir_tef': request.GET.get('incluir_tef') == '1',
    }
    
    # Buscar canais do usuário
    from portais.controle_acesso.services import ControleAcessoService
    from .services_rpr import RPRService
    
    canais_usuario = ControleAcessoService.obter_canais_usuario(request.portal_usuario)
    
    registrar_log('portais.admin', f"RPR AJAX - Filtros recebidos: {filtros}")
    registrar_log('portais.admin', f"RPR AJAX - Canais usuário: {canais_usuario}")
    registrar_log('portais.admin', f"RPR AJAX - Page: {page}, Per page: {per_page}")
    
    # Usar service para buscar transações
    transacoes_list, total = RPRService.buscar_transacoes_rpr(
        filtros=filtros,
        canais_usuario=canais_usuario,
        page=page,
        per_page=per_page
    )
    
    registrar_log('portais.admin', f"RPR AJAX - Transações retornadas: {len(transacoes_list)}, Total: {total}")
    
    # Calcular totalizadora e linhas
    estrutura_colunas = obter_estrutura_colunas_rpr()
    
    # Para totalizadora, buscar todas as transações (sem paginação)
    todas_transacoes, _ = RPRService.buscar_transacoes_rpr(
        filtros=filtros,
        canais_usuario=canais_usuario,
        page=1,
        per_page=999999  # Buscar todas para totalizar
    )
    linha_totalizadora = calcular_linha_totalizadora_rpr(todas_transacoes, estrutura_colunas)
    
    # Preparar dados para a tabela
    dados_tabela = []
    for transacao in transacoes_list:
        linha = calcular_linha_rpr(transacao, estrutura_colunas)
        dados_tabela.append(linha)
    
    # Calcular paginação
    import math
    total_paginas = math.ceil(total / per_page) if total > 0 else 1
    
    # Mapeamento de colunas
    mapeamento_colunas = obter_mapeamento_colunas_rpr_dinamico()
    
    # Resposta JSON
    response_data = {
        'dados': dados_tabela,
        'linha_totalizadora': linha_totalizadora,
        'paginacao': {
            'pagina_atual': page,
            'total_paginas': total_paginas,
            'total_registros': total,
            'tem_proxima': page < total_paginas,
            'tem_anterior': page > 1,
            'registros_por_pagina': per_page
        },
        'colunas': mapeamento_colunas,
        'campos_monetarios': obter_colunas_monetarias_rpr_dinamico()
    }
    
    registrar_log('portais.admin', f"RPR - Tabela página {page} - Filtros: {filtros}")
    
    return JsonResponse(response_data)


def calcular_linha_totalizadora_rpr(queryset, estrutura_colunas):
    """Calcula linha totalizadora com somas de todas as transações"""
    
    # Inicializar totais
    totais = {}
    
    # Processar todas as transações para calcular totais
    for transacao in queryset:
        # Calcular linha individual SEM formatação para obter valores numéricos
        linha_individual = calcular_linha_rpr(transacao, estrutura_colunas, para_export=True)
        
        # Somar valores numéricos
        for campo, valor in linha_individual.items():
            if campo not in totais:
                totais[campo] = Decimal('0.00')
            
            # Identificar colunas percentuais que NÃO devem ser somadas
            colunas_percentuais = [
                'var36', 'var89', 'var39', 'var92', 'var40', 'var93_A',  # Variáveis percentuais do banco
                'variavel_nova_1', 'variavel_nova_3', 'variavel_nova_6', 'variavel_nova_7',  # Fórmulas percentuais
                'variavel_nova_10', 'variavel_nova_12', 'variavel_nova_14', 'variavel_nova_16'
            ]
            
            # Pular colunas percentuais
            if campo in colunas_percentuais:
                continue
            
            # Converter e somar valores (apenas colunas não percentuais)
            try:
                if isinstance(valor, (int, float, Decimal)):
                    totais[campo] += Decimal(str(valor))
                elif isinstance(valor, str):
                    # Tentar extrair número de strings formatadas como "R$ 100,00"
                    # NÃO processar strings com % (já filtradas acima)
                    if '%' not in valor:
                        valor_limpo = valor.replace('R$', '').replace('.', '').replace(',', '.').strip()
                        if valor_limpo and valor_limpo != 'Não Finalizada' and valor_limpo != '':
                            try:
                                totais[campo] += Decimal(valor_limpo)
                            except (ValueError, decimal.InvalidOperation):
                                # Se não conseguir converter, trata como zero (não soma nada)
                                pass
            except (ValueError, TypeError, decimal.InvalidOperation):
                pass
    
    # Criar linha totalizadora
    linha_totalizadora = {}
    for item in estrutura_colunas:
        campo = item['campo']
        
        if campo == 'var0':  # Data - mostrar "TOTAL"
            linha_totalizadora[campo] = "TOTAL"
        elif campo in ['var1', 'var2', 'var3', 'var4', 'var5', 'var6', 'var7', 'var8', 'var9', 'var10', 'var12']:
            # Campos de texto - deixar vazio
            linha_totalizadora[campo] = ""
        elif campo in ['var36', 'var89', 'var39', 'var92', 'var40', 'var93_A', 
                       'variavel_nova_1', 'variavel_nova_3', 'variavel_nova_6', 'variavel_nova_7',
                       'variavel_nova_10', 'variavel_nova_12', 'variavel_nova_14', 'variavel_nova_16']:
            # Campos percentuais - deixar vazio (não somar)
            linha_totalizadora[campo] = ""
        else:
            # Campos numéricos - usar total calculado
            linha_totalizadora[campo] = totais.get(campo, Decimal('0.00'))
    
    return linha_totalizadora


def _obter_queryset_rpr(request):
    """Auxiliar para construir queryset RPR com filtros"""
    from portais.controle_acesso.services import ControleAcessoService
    from .services_rpr import RPRService
    
    usuario_logado = getattr(request, 'portal_usuario', None)
    if usuario_logado:
        nivel_usuario = ControleAcessoService.obter_nivel_portal(usuario_logado, 'admin')
        if nivel_usuario == 'admin_canal':
            canais_usuario = ControleAcessoService.obter_canais_usuario(usuario_logado)
        else:
            canais_usuario = None
    else:
        canais_usuario = None
    
    # Aplicar mesmos filtros da tabela
    filtros = {
        'data_inicial': request.GET.get('data_inicial', ''),
        'data_final': request.GET.get('data_final', ''),
        'canal': request.GET.get('canal', ''),
        'loja': request.GET.get('loja', ''),
        'nsu': request.GET.get('nsu', ''),
        'incluir_tef': request.GET.get('incluir_tef') == '1',
    }
    
    # Usar service para buscar transações (sem paginação para export)
    transacoes_list, _ = RPRService.buscar_transacoes_rpr(
        filtros=filtros,
        canais_usuario=canais_usuario,
        page=1,
        per_page=999999  # Buscar todas para exportação
    )
    
    return transacoes_list


@require_funcionalidade('rpr_export')
def exportar_rpr_excel(request):
    """Exportar dados RPR para Excel - direto ou por email se >5000 registros"""
    try:
        # Obter transações com filtros aplicados
        transacoes = _obter_queryset_rpr(request)
        total_registros = len(transacoes)
        
        registrar_log('portais.admin', f"RPR Excel - Total registros: {total_registros}")
        
        # Se mais de 5000 registros, enviar por email
        if total_registros > 5000:
            return _exportar_rpr_csv_email(request, transacoes, total_registros)
        
        # Export direto para menos de 5000 registros
        dados = []
        estrutura_colunas = obter_estrutura_colunas_rpr()
        
        for transacao in transacoes:
            linha = calcular_linha_rpr(transacao, estrutura_colunas, para_export=True)
            dados.append(linha)
        
        # Usar utilitário comum para exportar
        nome_arquivo = f"rpr_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        titulo = "Relatório de Produção e Receita"
        colunas_rpr = obter_mapeamento_colunas_rpr_dinamico()
        colunas_monetarias = obter_colunas_monetarias_rpr_dinamico()
        colunas_percentuais = obter_colunas_percentuais_rpr_dinamico()
        
        # Import direto da função
        from wallclub_core.utilitarios.export_utils import exportar_excel
        return exportar_excel(nome_arquivo, dados, colunas_rpr, titulo, colunas_monetarias, colunas_percentuais)
        
    except Exception as e:
        return JsonResponse({'erro': f'Erro ao exportar Excel: {str(e)}'}, status=500)


@require_funcionalidade('rpr_export')
def exportar_rpr_csv(request):
    """Exportar dados RPR para CSV - direto ou por email se >5000 registros"""
    try:
        # Obter transações com filtros aplicados
        transacoes = _obter_queryset_rpr(request)
        total_registros = len(transacoes)
        
        registrar_log('portais.admin', f"RPR CSV - Total registros: {total_registros}")
        
        # Se mais de 5000 registros, enviar por email
        if total_registros > 5000:
            return _exportar_rpr_csv_email(request, transacoes, total_registros)
        
        # Export direto para menos de 5000 registros
        dados = []
        estrutura_colunas = obter_estrutura_colunas_rpr()
        
        for transacao in transacoes:
            linha = calcular_linha_rpr(transacao, estrutura_colunas, para_export=True)
            dados.append(linha)
        
        # Usar utilitário comum para exportar
        nome_arquivo = f"rpr_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        colunas_rpr = obter_mapeamento_colunas_rpr_dinamico()
        
        return exportar_csv(nome_arquivo, dados, colunas_rpr)
        
    except Exception as e:
        return JsonResponse({'erro': f'Erro ao exportar CSV: {str(e)}'}, status=500)


def _exportar_rpr_csv_email(request, queryset, total_registros):
    """Exportar RPR CSV por email em background (>5000 registros)"""
    from django.http import JsonResponse
    import threading
    import tempfile
    import os
    
    # Capturar dados do usuário ANTES da thread
    portal_usuario = getattr(request, 'portal_usuario', None)
    if portal_usuario:
        usuario_email = portal_usuario.email
        usuario_nome = portal_usuario.nome or 'Usuário'
    else:
        usuario_email = None
        usuario_nome = 'Usuário'
    
    def processar_e_enviar():
        try:
            registrar_log('portais.admin', f"RPR CSV - Thread iniciada")
            
            import csv
            import tempfile
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as temp_file:
                arquivo_path = temp_file.name
            
            registrar_log('portais.admin', f"RPR CSV - Processando em batches de 1000")
            
            # Processar em batches
            batch_size = 1000
            total_processados = 0
            
            # Estrutura e mapeamento
            estrutura_colunas = obter_estrutura_colunas_rpr()
            colunas_rpr = obter_mapeamento_colunas_rpr_dinamico()
            
            # Função para remover acentos (mesma do gestão admin)
            def remover_acentos(texto):
                import unicodedata
                if not texto:
                    return texto
                
                texto_normalizado = unicodedata.normalize('NFD', str(texto))
                texto_sem_acentos = ''.join(c for c in texto_normalizado if unicodedata.category(c) != 'Mn')
                
                substituicoes = {
                    'ç': 'c', 'Ç': 'C',
                    'ñ': 'n', 'Ñ': 'N'
                }
                
                for original, substituto in substituicoes.items():
                    texto_sem_acentos = texto_sem_acentos.replace(original, substituto)
                
                return texto_sem_acentos
            
            with open(arquivo_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile, delimiter=';')
                
                # Headers (sem acentos)
                headers_sem_acentos = [remover_acentos(header) for header in colunas_rpr.values()]
                writer.writerow(headers_sem_acentos)
                
                for start in range(0, total_registros, batch_size):
                    batch = queryset[start:start + batch_size]
                    
                    for transacao in batch:
                        # Calcular linha RPR
                        linha_individual = calcular_linha_rpr(transacao, estrutura_colunas, para_export=True)
                        
                        # Escrever linha usando mesma ordem dos cabeçalhos
                        linha = []
                        for campo in colunas_rpr.keys():
                            valor = linha_individual.get(campo, '')
                            
                            # Formatação para campos monetários
                            if campo in obter_colunas_monetarias_rpr_dinamico() and valor:
                                try:
                                    if isinstance(valor, (int, float)):
                                        valor = f"{valor:.2f}".replace('.', ',')
                                    elif isinstance(valor, str) and valor != 'Não Finalizada':
                                        valor_float = float(str(valor).replace(',', '.'))
                                        valor = f"{valor_float:.2f}".replace('.', ',')
                                    else:
                                        valor = str(valor) if valor else ''
                                except:
                                    valor = str(valor) if valor else ''
                            else:
                                valor = str(valor) if valor else ''
                            
                            # Remover acentos de todos os valores
                            valor = remover_acentos(valor)
                            linha.append(valor)
                        
                        writer.writerow(linha)
                    
                    total_processados += len(batch)
                    registrar_log('portais.admin', f"RPR CSV - Processados {total_processados}/{total_registros}")
            
            # Enviar por email
            nome_arquivo = f"rpr_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            if usuario_email:
                from wallclub_core.utilitarios.email_utils import enviar_arquivo_por_email
                
                assunto = f"Exportação RPR - {total_registros} registros"
                corpo = f"""
                Olá {usuario_nome},
                
                Sua exportação do Relatório de Produção e Receita foi concluída com sucesso.
                
                Total de registros: {total_registros:,}
                Arquivo: {nome_arquivo}
                
                O arquivo está anexado a este email.
                
                Atenciosamente,
                Sistema WallClub
                """
                
                enviar_arquivo_por_email(
                    destinatario=usuario_email,
                    assunto=assunto,
                    corpo=corpo,
                    arquivo_path=arquivo_path,
                    nome_arquivo=nome_arquivo
                )
                
                registrar_log('portais.admin', f"RPR CSV - Email enviado para {usuario_email}")
            else:
                registrar_log('portais.admin', f"RPR CSV - Email não enviado (usuário sem email)")
            
            # Limpar arquivo temporário
            try:
                os.unlink(arquivo_path)
            except:
                pass
                
        except Exception as e:
            registrar_log('portais.admin', f"RPR CSV - Erro na thread: {str(e)}", nivel='ERROR')
    
    # Iniciar thread
    thread = threading.Thread(target=processar_e_enviar)
    thread.daemon = True
    thread.start()
    
    return JsonResponse({
        'sucesso': True,
        'mensagem': f'Exportação iniciada! O arquivo com {total_registros:,} registros será enviado por email.',
        'total_registros': total_registros
    })


def calcular_linha_rpr(transacao, estrutura_colunas, para_export=False):
    """Calcula uma linha da tabela RPR com variáveis e fórmulas"""
    linha = {}
    variaveis_calculadas = {}  # Cache para variáveis novas
    
    # FASE 1: Calcular todas as variáveis na ordem de dependências
    # Primeiro processar variáveis do banco
    for item in estrutura_colunas:
        if item['tipo'] == 'variavel':
            campo = item['campo']
            # Transação vem como dict da query SQL
            valor = transacao.get(campo, '') if isinstance(transacao, dict) else getattr(transacao, campo, '')
            # Armazenar no cache para cálculos
            try:
                if isinstance(valor, str):
                    variaveis_calculadas[campo] = float(valor.replace(',', '.')) if valor else 0
                else:
                    variaveis_calculadas[campo] = float(valor) if valor else 0
            except (ValueError, TypeError):
                variaveis_calculadas[campo] = 0
    
    # Depois processar fórmulas na ordem correta de dependências
    formulas_ordenadas = [
        'variavel_nova_1', 'variavel_nova_2', 'variavel_nova_3', 'variavel_nova_4',
        'variavel_nova_5', 'variavel_nova_6', 'variavel_nova_8', 'variavel_nova_7',
        'variavel_nova_9', 'variavel_nova_11', 'variavel_nova_10', 'variavel_nova_12',
        'variavel_nova_13', 'variavel_nova_14', 'variavel_nova_15', 'variavel_nova_17', 'variavel_nova_16'
    ]
    
    for campo_formula in formulas_ordenadas:
        for item in estrutura_colunas:
            if item['tipo'] == 'formula' and item['campo'] == campo_formula:
                resultado = calcular_formula(item['formula'], transacao, variaveis_calculadas)
                variaveis_calculadas[campo_formula] = resultado
                break
    
    # FASE 2: Montar linha na ordem de exibição com formatação
    for item in estrutura_colunas:
        campo = item['campo']
        
        if item['tipo'] == 'variavel':
            # Variável conhecida do banco
            valor = transacao.get(campo, '') if isinstance(transacao, dict) else getattr(transacao, campo, '')
            
            # Formatação para exibição
            if not para_export and campo in obter_colunas_monetarias_rpr():
                try:
                    if valor and str(valor).strip():
                        valor_float = float(str(valor).replace(',', '.'))
                        linha[campo] = f"R$ {valor_float:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    else:
                        linha[campo] = 'R$ 0,00'
                except (ValueError, TypeError):
                    linha[campo] = str(valor) if valor else ''
            elif not para_export and campo in ['var36', 'var89', 'var39', 'var92', 'var40', 'var93_A']:
                # Variáveis que devem ser formatadas como percentual
                try:
                    valor_float = float(str(valor).replace(',', '.')) if valor else 0
                    if valor_float != 0:
                        percentual = valor_float * 100
                        linha[campo] = f"{percentual:.2f}%"
                    else:
                        linha[campo] = '0.00%'
                except (ValueError, TypeError):
                    linha[campo] = '0.00%'
            elif not para_export and campo in ['var11'] and isinstance(valor, (int, float)) and valor > 0:
                # var11 deve ser formatado como monetário
                linha[campo] = f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            else:
                linha[campo] = str(valor) if valor else ''
                
            # Guardar valor numérico para cálculos
            try:
                if isinstance(valor, str):
                    variaveis_calculadas[campo] = float(valor.replace(',', '.')) if valor else 0
                else:
                    variaveis_calculadas[campo] = float(valor) if valor else 0
            except (ValueError, TypeError):
                variaveis_calculadas[campo] = 0
                
        elif item['tipo'] == 'formula':
            # Variável calculada - usar valor já calculado na FASE 1
            resultado = variaveis_calculadas.get(campo, 0)
            
            # Formatação para exibição
            if not para_export and campo in ['variavel_nova_1', 'variavel_nova_3', 'variavel_nova_6', 'variavel_nova_7', 
                                           'variavel_nova_10', 'variavel_nova_12', 'variavel_nova_14', 'variavel_nova_16']:
                # Variáveis que devem ser formatadas como percentual
                try:
                    valor_float = float(str(resultado).replace(',', '.')) if resultado else 0
                    if valor_float != 0:
                        percentual = valor_float * 100
                        linha[campo] = f"{percentual:.2f}%"
                    else:
                        linha[campo] = '0.00%'
                except (ValueError, TypeError):
                    linha[campo] = '0.00%'
            elif not para_export and resultado != 0:
                # Outras fórmulas monetárias
                try:
                    valor_num = float(resultado) if resultado else 0
                    linha[campo] = f"R$ {valor_num:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                except (ValueError, TypeError):
                    linha[campo] = str(resultado) if resultado else ''
            else:
                linha[campo] = str(resultado) if resultado else ''
                
    
    return linha


def calcular_formula(formula, transacao, variaveis_calculadas):
    try:
        from decimal import Decimal
        import re
        
        
        # Substituir variáveis do banco de dados
        formula_processada = formula
        
        # Buscar todas as variáveis na fórmula (incluindo variavel_nova_X)
        import re
        vars_encontradas = re.findall(r'var\d+(?:_A)?|variavel_nova_\d+', formula_processada)
        
        for var_name in vars_encontradas:
            if var_name in formula_processada:
                # Se é variável calculada, buscar do cache primeiro
                if var_name.startswith('variavel_nova_'):
                    if var_name in variaveis_calculadas:
                        valor_calculado = variaveis_calculadas[var_name]
                        try:
                            valor_num = Decimal(str(valor_calculado))
                        except:
                            valor_num = Decimal('0')
                        formula_processada = formula_processada.replace(var_name, str(valor_num))
                        
                
                # Se é variável do banco, buscar do objeto transacao
                elif var_name.startswith('var'):
                    valor = transacao.get(var_name, 0) if isinstance(transacao, dict) else getattr(transacao, var_name, 0)
                    
                    try:
                        from decimal import Decimal
                        if isinstance(valor, str):
                            valor_num = Decimal(valor.replace(',', '.')) if valor else Decimal('0')
                        elif isinstance(valor, Decimal):
                            valor_num = valor
                        else:
                            valor_num = Decimal(str(valor)) if valor else Decimal('0')
                    except (ValueError, TypeError):
                        valor_num = Decimal('0')
                    
                    formula_processada = formula_processada.replace(var_name, str(valor_num))
                    
        
        # Substituir variáveis calculadas (remover seção duplicada - já processado acima)
        
        # Processar função abs()
        if 'abs(' in formula_processada:
            abs_matches = re.findall(r'abs\(([^)]+)\)', formula_processada)
            for match in abs_matches:
                try:
                    valor_abs = abs(Decimal(match))
                    formula_processada = formula_processada.replace(f'abs({match})', str(valor_abs))
                except:
                    formula_processada = formula_processada.replace(f'abs({match})', '0')
        
        # Processar condicionais simples
        if 'if' in formula_processada and 'else' in formula_processada:
            conditional_match = re.match(r'(.+?)\s+if\s+(.+?)\s+else\s+(.+)', formula_processada)
            if conditional_match:
                expr_true, condition, expr_false = conditional_match.groups()
                
                try:
                    if eval(condition):
                        formula_processada = expr_true.strip()
                    else:
                        formula_processada = expr_false.strip()
                except:
                    formula_processada = '0'
        
        # Avaliar expressão final
        try:
            # Usar eval com contexto Decimal para manter precisão
            from decimal import Decimal
            resultado = eval(formula_processada, {"__builtins__": {}, "Decimal": Decimal})
            
            
            # Converter para float apenas no final se necessário
            if isinstance(resultado, Decimal):
                return float(resultado)
            return float(resultado) if isinstance(resultado, (int, float)) else resultado
        except Exception as e:
            return 0
            
    except Exception:
        return 0
