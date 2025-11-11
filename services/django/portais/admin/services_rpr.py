"""
Service para Relatório de Produção e Receita (RPR)
Centraliza toda a lógica de negócio do relatório RPR
"""

from django.db import connection
from django.db.models import Q, Sum
from datetime import datetime, date
from decimal import Decimal
import decimal
import re
import csv
import tempfile
import threading
import os
from typing import Dict, List, Any, Optional, Tuple

from wallclub_core.database.queries import TransacoesQueries
from sistema_bancario.models import LancamentoManual
from wallclub_core.estr_organizacional.services import HierarquiaOrganizacionalService
from wallclub_core.estr_organizacional.canal import Canal
from wallclub_core.utilitarios.log_control import registrar_log


class RPRService:
    """
    Service para Relatório de Produção e Receita
    Centraliza cálculos, agregações, fórmulas e exportações
    """
    
    # ==================== ESTRUTURA DE COLUNAS ====================
    
    @staticmethod
    def obter_estrutura_colunas() -> List[Dict[str, Any]]:
        """
        Define estrutura completa de colunas RPR (46 colunas)
        
        Returns:
            Lista de dicts com tipo, campo, nome e fórmula
        """
        return [
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
            
            # 14-15: Fórmulas MDR
            {'tipo': 'formula', 'campo': 'variavel_nova_1', 'nome': 'Resultado MDR (%)', 'formula': 'var36 - var89'},
            {'tipo': 'formula', 'campo': 'variavel_nova_2', 'nome': 'Resultado MDR (R$)', 'formula': 'var37 - var90'},
            
            # 16-20: Variáveis intermediárias
            {'tipo': 'variavel', 'campo': 'var39', 'nome': None},
            {'tipo': 'variavel', 'campo': 'var92', 'nome': None},
            {'tipo': 'variavel', 'campo': 'var40', 'nome': None},
            {'tipo': 'variavel', 'campo': 'var93_A', 'nome': None},
            {'tipo': 'variavel', 'campo': 'var41', 'nome': None},
            
            # 21-28: Fórmulas antecipação
            {'tipo': 'formula', 'campo': 'variavel_nova_3', 'nome': 'Encargos Cobrados Clientes Finais (%)', 'formula': 'abs(var14)'},
            {'tipo': 'variavel', 'campo': 'var15', 'nome': None},
            {'tipo': 'formula', 'campo': 'variavel_nova_4', 'nome': 'Receita Total Antec. + Encargos (Total - R$)', 'formula': 'var15 + var41'},
            {'tipo': 'variavel', 'campo': 'var94_A', 'nome': None},
            {'tipo': 'formula', 'campo': 'variavel_nova_6', 'nome': 'Resultado Antecipação & Parcelamento (%)', 'formula': 'variavel_nova_5 / var11 if var11 != 0 else 0'},
            {'tipo': 'formula', 'campo': 'variavel_nova_5', 'nome': 'Resultado Antecipação & Parcelamento (R$)', 'formula': 'variavel_nova_4 - var94_A'},
            {'tipo': 'formula', 'campo': 'variavel_nova_7', 'nome': 'Resultado Operacional (projetado) %', 'formula': 'variavel_nova_8 / var11 if var11 != 0 else 0'},
            {'tipo': 'formula', 'campo': 'variavel_nova_8', 'nome': 'Resultado Operacional (projetado) R$', 'formula': 'variavel_nova_5 + variavel_nova_2'},
            
            # 29-36: Fórmulas resultado final
            {'tipo': 'variavel', 'campo': 'var98', 'nome': None},
            {'tipo': 'variavel', 'campo': 'var101', 'nome': None},
            {'tipo': 'formula', 'campo': 'variavel_nova_9', 'nome': 'Resultado Caixa (Rcebtos - Repasses) R$', 'formula': '"Não Finalizada" if var101 == 0 else var98 - var101'},
            {'tipo': 'formula', 'campo': 'variavel_nova_11', 'nome': 'Resultado Operacional (antes Cashback e Chargeback) R$', 'formula': '"Não Finalizada" if var101 == 0 else var113_A'},
            {'tipo': 'formula', 'campo': 'variavel_nova_10', 'nome': 'Resultado Operacional (antes Cashback e Chargeback) %', 'formula': '"Não Finalizada" if var101 == 0 else variavel_nova_11 / var11 if var11 != 0 else 0'},
            {'tipo': 'formula', 'campo': 'variavel_nova_12', 'nome': 'Cashback pago à Loja (%)', 'formula': 'var58 / var11 if var11 != 0 else 0'},
            {'tipo': 'variavel', 'campo': 'var58', 'nome': None},
            {'tipo': 'variavel', 'campo': 'var111_A', 'nome': None},
            
            # 37-46: Fórmulas impostos e resultado
            {'tipo': 'formula', 'campo': 'variavel_nova_13', 'nome': 'Impostos Diretos pagos (R$)', 'formula': '"Não Finalizada" if var101 == 0 else var109_A'},
            {'tipo': 'formula', 'campo': 'variavel_nova_14', 'nome': 'Resultado Final (pós impostos - sem POS) - Visão Gestão - %', 'formula': '"Não Finalizada" if var101 == 0 else var118_A'},
            {'tipo': 'formula', 'campo': 'variavel_nova_15', 'nome': 'Resultado Final (pós impostos - sem POS) - Visão Gestão - R$', 'formula': '"Não Finalizada" if var101 == 0 else var116_A'},
            {'tipo': 'formula', 'campo': 'variavel_nova_16', 'nome': 'Resultado Final (pós impostos - sem POS) %', 'formula': '"Não Finalizada" if var101 == 0 else variavel_nova_17 / var26 if var26 != 0 else 0'},
            {'tipo': 'formula', 'campo': 'variavel_nova_17', 'nome': 'Resultado Final (pós impostos - sem POS) R$', 'formula': '"Não Finalizada" if var101 == 0 else variavel_nova_11 - variavel_nova_13'},
            {'tipo': 'variavel', 'campo': 'var10', 'nome': None},
            {'tipo': 'variavel', 'campo': 'var8', 'nome': None},
            {'tipo': 'variavel', 'campo': 'var12', 'nome': None},
            {'tipo': 'variavel', 'campo': 'var13', 'nome': None},
            {'tipo': 'variavel', 'campo': 'var43', 'nome': None},
        ]
    
    @staticmethod
    def obter_mapeamento_colunas() -> Dict[str, str]:
        """Retorna mapeamento campo -> nome de exibição"""
        from .utils.column_mappings import obter_mapeamento_colunas_completo
        
        mapeamento_completo = obter_mapeamento_colunas_completo()
        estrutura = RPRService.obter_estrutura_colunas()
        
        mapeamento = {}
        for item in estrutura:
            if item['tipo'] == 'variavel':
                if item['campo'] in mapeamento_completo:
                    mapeamento[item['campo']] = mapeamento_completo[item['campo']]
            elif item['tipo'] == 'formula':
                mapeamento[item['campo']] = item['nome']
        
        return mapeamento
    
    @staticmethod
    def obter_colunas_monetarias() -> List[str]:
        """Retorna colunas monetárias (R$)"""
        estrutura = RPRService.obter_estrutura_colunas()
        colunas = []
        
        for item in estrutura:
            campo = item['campo']
            if campo in ['var11', 'var15', 'var26', 'var37', 'var41', 'var90', 'var94_A', 
                        'var98', 'var101', 'var58', 'var111_A', 'var109_A', 'var113_A', 
                        'var116_A', 'var118_A']:
                colunas.append(campo)
            elif item['tipo'] == 'formula' and item.get('nome') and 'R$' in item['nome']:
                colunas.append(campo)
        
        return colunas
    
    @staticmethod
    def obter_colunas_percentuais() -> List[str]:
        """Retorna colunas percentuais (%)"""
        estrutura = RPRService.obter_estrutura_colunas()
        colunas = []
        
        for item in estrutura:
            campo = item['campo']
            if campo in ['var36', 'var89', 'var39', 'var92', 'var40', 'var93_A']:
                colunas.append(campo)
            elif item['tipo'] == 'formula' and item.get('nome') and '%' in item['nome']:
                colunas.append(campo)
        
        return colunas
    
    # ==================== CÁLCULO ====================
    
    @staticmethod
    def calcular_formula(formula: str, transacao, variaveis_calculadas: Dict[str, float]) -> float:
        """Calcula fórmula com variáveis do banco e calculadas"""
        try:
            formula_processada = formula
            vars_encontradas = re.findall(r'var\d+(?:_A)?|variavel_nova_\d+', formula_processada)
            
            for var_name in vars_encontradas:
                if var_name.startswith('variavel_nova_'):
                    if var_name in variaveis_calculadas:
                        valor_num = Decimal(str(variaveis_calculadas[var_name]))
                        formula_processada = formula_processada.replace(var_name, str(valor_num))
                elif var_name.startswith('var'):
                    valor = getattr(transacao, var_name, 0)
                    try:
                        if isinstance(valor, str):
                            valor_num = Decimal(valor.replace(',', '.')) if valor else Decimal('0')
                        else:
                            valor_num = Decimal(str(valor)) if valor else Decimal('0')
                    except:
                        valor_num = Decimal('0')
                    formula_processada = formula_processada.replace(var_name, str(valor_num))
            
            if 'abs(' in formula_processada:
                abs_matches = re.findall(r'abs\(([^)]+)\)', formula_processada)
                for match in abs_matches:
                    try:
                        valor_abs = abs(Decimal(match))
                        formula_processada = formula_processada.replace(f'abs({match})', str(valor_abs))
                    except:
                        pass
            
            if 'if' in formula_processada and 'else' in formula_processada:
                conditional_match = re.match(r'(.+?)\s+if\s+(.+?)\s+else\s+(.+)', formula_processada)
                if conditional_match:
                    expr_true, condition, expr_false = conditional_match.groups()
                    try:
                        formula_processada = expr_true.strip() if eval(condition) else expr_false.strip()
                    except:
                        formula_processada = '0'
            
            resultado = eval(formula_processada, {"__builtins__": {}, "Decimal": Decimal})
            return float(resultado) if isinstance(resultado, (int, float, Decimal)) else resultado
        except:
            return 0
    
    @staticmethod
    def calcular_linha(transacao, para_export: bool = False) -> Dict[str, Any]:
        """Calcula linha RPR completa com variáveis e fórmulas"""
        estrutura = RPRService.obter_estrutura_colunas()
        variaveis_calculadas = {}
        
        # Log inicial da transação
        var9 = transacao.get('var9', '') if isinstance(transacao, dict) else getattr(transacao, 'var9', '')
        registrar_log('portais.admin', f"RPR - Calculando linha para NSU: {var9}")
        
        # Calcular variáveis do banco
        for item in estrutura:
            if item['tipo'] == 'variavel':
                valor = transacao.get(item['campo'], '') if isinstance(transacao, dict) else getattr(transacao, item['campo'], '')
                try:
                    variaveis_calculadas[item['campo']] = float(str(valor).replace(',', '.')) if valor else 0
                except:
                    variaveis_calculadas[item['campo']] = 0
        
        # Log de variáveis chave
        registrar_log('portais.admin', 
            f"RPR - Vars chave NSU {var9}: var11={variaveis_calculadas.get('var11')}, "
            f"var26={variaveis_calculadas.get('var26')}, var37={variaveis_calculadas.get('var37')}")
        
        # Calcular fórmulas em ordem
        formulas_ordem = [
            'variavel_nova_1', 'variavel_nova_2', 'variavel_nova_3', 'variavel_nova_4',
            'variavel_nova_5', 'variavel_nova_6', 'variavel_nova_8', 'variavel_nova_7',
            'variavel_nova_9', 'variavel_nova_11', 'variavel_nova_10', 'variavel_nova_12',
            'variavel_nova_13', 'variavel_nova_14', 'variavel_nova_15', 'variavel_nova_17',
            'variavel_nova_16'
        ]
        
        for campo_formula in formulas_ordem:
            for item in estrutura:
                if item['tipo'] == 'formula' and item['campo'] == campo_formula:
                    variaveis_calculadas[campo_formula] = RPRService.calcular_formula(
                        item['formula'], transacao, variaveis_calculadas
                    )
                    break
        
        # Montar linha com formatação
        linha = {}
        monetarias = RPRService.obter_colunas_monetarias()
        percentuais = RPRService.obter_colunas_percentuais()
        
        for item in estrutura:
            campo = item['campo']
            
            if item['tipo'] == 'variavel':
                valor = transacao.get(campo, '') if isinstance(transacao, dict) else getattr(transacao, campo, '')
                if not para_export:
                    if campo in monetarias:
                        try:
                            v = float(str(valor).replace(',', '.')) if valor else 0
                            linha[campo] = f"R$ {v:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                        except:
                            linha[campo] = 'R$ 0,00'
                    elif campo in percentuais:
                        try:
                            v = float(str(valor).replace(',', '.')) if valor else 0
                            linha[campo] = f"{v * 100:.2f}%" if v != 0 else '0.00%'
                        except:
                            linha[campo] = '0.00%'
                    else:
                        linha[campo] = str(valor) if valor else ''
                else:
                    linha[campo] = valor
            else:
                resultado = variaveis_calculadas.get(campo, 0)
                if not para_export:
                    if campo in percentuais:
                        try:
                            v = float(str(resultado)) if resultado else 0
                            linha[campo] = f"{v * 100:.2f}%" if v != 0 else '0.00%'
                        except:
                            linha[campo] = '0.00%'
                    elif resultado != 0:
                        try:
                            linha[campo] = f"R$ {float(resultado):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                        except:
                            linha[campo] = str(resultado)
                    else:
                        linha[campo] = ''
                else:
                    linha[campo] = resultado
        
        return linha
    
    @staticmethod
    def calcular_totalizadora(queryset) -> Dict[str, Any]:
        """Calcula linha totalizadora do RPR"""
        estrutura = RPRService.obter_estrutura_colunas()
        percentuais = RPRService.obter_colunas_percentuais()
        totais = {}
        
        for transacao in queryset:
            linha = RPRService.calcular_linha(transacao, para_export=True)
            for campo, valor in linha.items():
                if campo in percentuais:
                    continue
                if campo not in totais:
                    totais[campo] = Decimal('0.00')
                try:
                    if isinstance(valor, (int, float, Decimal)):
                        totais[campo] += Decimal(str(valor))
                except:
                    pass
        
        linha_total = {}
        for item in estrutura:
            campo = item['campo']
            if campo == 'var0':
                linha_total[campo] = "TOTAL"
            elif campo in ['var1', 'var2', 'var3', 'var4', 'var5', 'var6', 'var7', 'var8', 'var9', 'var10', 'var12']:
                linha_total[campo] = ""
            elif campo in percentuais:
                linha_total[campo] = ""
            else:
                linha_total[campo] = totais.get(campo, Decimal('0.00'))
        
        return linha_total
    
    @staticmethod
    def gerar_relatorio_metricas(filtros: Dict, canais_usuario: Optional[List[int]] = None) -> Dict:
        """Gera métricas consolidadas do RPR com SQL otimizado"""
        where_conditions = ["var68 = 'TRANS. APROVADO'"]
        params = []
        
        if filtros.get('data_inicial'):
            where_conditions.append("data_transacao >= %s")
            params.append(f"{filtros['data_inicial']} 00:00:00")
        
        if filtros.get('data_final'):
            where_conditions.append("data_transacao <= %s")
            params.append(f"{filtros['data_final']} 23:59:59")
        
        if canais_usuario:
            nomes = []
            for cid in canais_usuario:
                try:
                    c = HierarquiaOrganizacionalService.get_canal(cid)
                    if c and c.nome:
                        nomes.append(c.nome)
                except:
                    continue
            if nomes:
                where_conditions.append(f"var4 IN ({','.join(['%s'] * len(nomes))})")
                params.extend(nomes)
        elif filtros.get('canal'):
            where_conditions.append("var4 = %s")
            params.append(filtros['canal'])
        
        if filtros.get('loja'):
            where_conditions.append("var6 = %s")
            params.append(filtros['loja'])
        
        if not filtros.get('incluir_tef'):
            where_conditions.append("(var130 != 'TEF' OR var130 IS NULL)")
        
        where_clause = " AND ".join(where_conditions)
        
        sql = f"""
            SELECT 
                COUNT(DISTINCT var9) as qtde_nsus,
                SUM(CAST(var11 AS DECIMAL(15,2))) as volume_total,
                SUM(CAST(var37 AS DECIMAL(15,2))) as receita_mdr,
                SUM(CAST(var90 AS DECIMAL(15,2))) as custo_mdr,
                SUM(CAST(var41 AS DECIMAL(15,2))) as receita_var41,
                SUM(CAST(var109_A AS DECIMAL(15,2))) as impostos,
                SUM(CASE WHEN var101 IS NOT NULL AND CAST(var101 AS DECIMAL(15,2)) != 0 
                         THEN CAST(var116_A AS DECIMAL(15,2)) ELSE 0 END) as resultado
            FROM (
                SELECT *, ROW_NUMBER() OVER (PARTITION BY var9 ORDER BY id DESC) as rn
                FROM baseTransacoesGestao
                WHERE {where_clause}
            ) t WHERE rn = 1
        """
        
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            resultado = cursor.fetchone()
        
        registrar_log('portais.admin', f"RPR - Métricas geradas - Filtros: {filtros}")
        
        return {
            'qtde_transacoes': resultado[0] or 0,
            'volume_total': Decimal(str(resultado[1] or 0)),
            'receita_mdr': Decimal(str(resultado[2] or 0)),
            'custo_mdr': Decimal(str(resultado[3] or 0)),
            'receita_antecipacao': Decimal(str(resultado[4] or 0)),
            'impostos_total': Decimal(str(resultado[5] or 0)),
            'resultado_financeiro': Decimal(str(resultado[6] or 0))
        }
    
    @staticmethod
    def buscar_canais_disponiveis(canais_usuario: Optional[List[int]] = None) -> List[str]:
        """
        Busca lista de canais disponíveis para o usuário
        
        Args:
            canais_usuario: Lista de IDs de canais (se admin_canal)
            
        Returns:
            Lista de nomes de canais disponíveis
        """
        if canais_usuario:
            # Usuário admin_canal - apenas seus canais
            nomes_canais = []
            for canal_id in canais_usuario:
                try:
                    canal = HierarquiaOrganizacionalService.get_canal(canal_id)
                    if canal and canal.nome:
                        nomes_canais.append(canal.nome)
                except Canal.DoesNotExist:
                    continue
            return nomes_canais
        else:
            # Usuário admin_total - todos os canais
            sql = """
                SELECT DISTINCT var4 FROM baseTransacoesGestao 
                WHERE var68 = 'TRANS. APROVADO' AND var4 IS NOT NULL AND var4 != ''
                ORDER BY var4
            """
            with connection.cursor() as cursor:
                cursor.execute(sql)
                canais = [row[0] for row in cursor.fetchall()]
            return canais
    
    @staticmethod
    def buscar_transacoes_rpr(filtros: Dict, canais_usuario: Optional[List[int]] = None, 
                              page: int = 1, per_page: int = 50) -> Tuple[List, int]:
        """
        Busca transações RPR com filtros e paginação
        
        Args:
            filtros: Dict com data_inicial, data_final, canal, loja, nsu, incluir_tef
            canais_usuario: Lista de IDs de canais (se admin_canal)
            page: Página atual
            per_page: Registros por página
            
        Returns:
            Tupla (lista_transacoes, total_registros)
        """
        where_conditions = ["var68 = 'TRANS. APROVADO'"]
        params = []
        
        # Filtro por canal do usuário
        if canais_usuario:
            nomes_canais = []
            for canal_id in canais_usuario:
                try:
                    canal = HierarquiaOrganizacionalService.get_canal(canal_id)
                    if canal and canal.nome:
                        nomes_canais.append(canal.nome)
                except:
                    continue
            if nomes_canais:
                placeholders = ','.join(['%s'] * len(nomes_canais))
                where_conditions.append(f"var4 IN ({placeholders})")
                params.extend(nomes_canais)
        
        # Filtros de data
        if filtros.get('data_inicial'):
            where_conditions.append("data_transacao >= %s")
            params.append(f"{filtros['data_inicial']} 00:00:00")
        
        if filtros.get('data_final'):
            where_conditions.append("data_transacao <= %s")
            params.append(f"{filtros['data_final']} 23:59:59")
        
        # Filtros específicos
        if filtros.get('canal'):
            where_conditions.append("var4 = %s")
            params.append(filtros['canal'])
        
        if filtros.get('loja'):
            where_conditions.append("var6 = %s")
            params.append(filtros['loja'])
        
        if filtros.get('nsu'):
            where_conditions.append("var9 = %s")
            params.append(filtros['nsu'])
        
        # Filtro tipo_operacao (Credenciadora/Wallet)
        if not filtros.get('incluir_tef'):
            where_conditions.append("tipo_operacao = 'Wallet'")
        
        where_clause = " AND ".join(where_conditions)
        
        registrar_log('portais.admin', f"RPR - Filtros aplicados: {filtros}")
        registrar_log('portais.admin', f"RPR - WHERE clause: {where_clause}")
        registrar_log('portais.admin', f"RPR - Params: {params}")
        
        # Query para contar total
        count_sql = f"""
            SELECT COUNT(*) FROM (
                SELECT var9, ROW_NUMBER() OVER (PARTITION BY var9 ORDER BY id DESC) as rn
                FROM baseTransacoesGestao
                WHERE {where_clause}
            ) t WHERE rn = 1
        """
        
        with connection.cursor() as cursor:
            cursor.execute(count_sql, params)
            total = cursor.fetchone()[0]
            registrar_log('portais.admin', f"RPR - Total de registros encontrados: {total}")
        
        # Query paginada
        offset = (page - 1) * per_page
        sql = f"""
            SELECT * FROM (
                SELECT *, ROW_NUMBER() OVER (PARTITION BY var9 ORDER BY id DESC) as rn
                FROM baseTransacoesGestao
                WHERE {where_clause}
            ) t WHERE rn = 1
            ORDER BY id DESC
            LIMIT %s OFFSET %s
        """
        
        params_paginados = params + [per_page, offset]
        
        # Executar query SQL direta
        with connection.cursor() as cursor:
            cursor.execute(sql, params_paginados)
            columns = [col[0] for col in cursor.description]
            transacoes_list = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        registrar_log('portais.admin', f"RPR - Busca transações - Page: {page}, Filtros: {filtros}")
        registrar_log('portais.admin', f"RPR - Registros retornados: {len(transacoes_list)}")
        
        # Log de amostra dos dados (primeira transação se existir)
        if transacoes_list:
            primeira = transacoes_list[0]
            registrar_log('portais.admin', 
                f"RPR - Amostra dados: var0={primeira.get('var0')}, var9={primeira.get('var9')}, "
                f"var11={primeira.get('var11')}, var26={primeira.get('var26')}, "
                f"data_transacao={primeira.get('data_transacao')}")
        else:
            registrar_log('portais.admin', "RPR - ATENÇÃO: Query retornou lista vazia!", nivel='WARNING')
        
        return transacoes_list, total
