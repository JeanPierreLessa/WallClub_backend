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
from gestao_financeira.models import LancamentoManual
from wallclub_core.estr_organizacional.services import HierarquiaOrganizacionalService
from wallclub_core.estr_organizacional.canal import Canal
from wallclub_core.utilitarios.log_control import registrar_log


class RPRService:
    """
    Service para Relatório de Produção e Receita
    Centraliza cálculos, agregações, fórmulas e exportações
    """

    # ==================== QUERIES E BUSCA DE DADOS ====================

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
                SELECT DISTINCT var4 FROM base_transacoes_unificadas
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
        incluir_tef_valor = filtros.get('incluir_tef')
        registrar_log('portais.admin', f"RPR - incluir_tef valor: {incluir_tef_valor}, tipo: {type(incluir_tef_valor)}")
        if not incluir_tef_valor:
            where_conditions.append("tipo_operacao = 'Wallet'")

        where_clause = " AND ".join(where_conditions)

        registrar_log('portais.admin', f"RPR - Filtros aplicados: {filtros}")
        registrar_log('portais.admin', f"RPR - WHERE clause: {where_clause}")
        registrar_log('portais.admin', f"RPR - Params: {params}")

        # Query para contar total (contar NSUs distintos)
        count_sql = f"""
            SELECT COUNT(*)
            FROM base_transacoes_unificadas
            WHERE {where_clause}
        """

        with connection.cursor() as cursor:
            cursor.execute(count_sql, params)
            total = cursor.fetchone()[0]
            registrar_log('portais.admin', f"RPR - Total de registros encontrados: {total}")

        # Query paginada
        offset = (page - 1) * per_page
        sql = f"""
            SELECT *
            FROM base_transacoes_unificadas
            WHERE {where_clause}
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

    # ==================== ESTRUTURA E CÁLCULOS RPR ====================

    @staticmethod
    def obter_estrutura_colunas_rpr():
        """
        Define estrutura completa de colunas RPR
        Esta é a função VALIDADA que está em produção
        """
        return [
            # 1-7: Variáveis base iniciais
            {'tipo': 'variavel', 'campo': 'var9', 'nome': None},
            {'tipo': 'variavel', 'campo': 'var0', 'nome': None},
            {'tipo': 'variavel', 'campo': 'var1', 'nome': None},
            {'tipo': 'variavel', 'campo': 'var68', 'nome': None},
            {'tipo': 'variavel', 'campo': 'var5', 'nome': 'Nome do Estabelecimento'},

            # Modalidade (tipo_operacao movido para depois de var5)
            {'tipo': 'variavel', 'campo': 'tipo_operacao', 'nome': 'Modalidade'},

            {'tipo': 'variavel', 'campo': 'var8', 'nome': None},  # Plano/Produto
            {'tipo': 'variavel', 'campo': 'var12', 'nome': None},  # Bandeira
            {'tipo': 'variavel', 'campo': 'var6', 'nome': None},

            # Continuação variáveis base
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

            # 22: Receita Encargos Cobrados Clientes Finais (R$) - baseado em var86
            {'tipo': 'formula', 'campo': 'var15', 'nome': 'Receita Encargos Cobrados Clientes Finais (R$)', 'formula': '-var86 if var86 < 0 else 0'},

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

            # Nova coluna: Custo ajuste nos Repasses (movida para antes de var98)
            {'tipo': 'formula', 'campo': 'variavel_nova_18', 'nome': 'Custo ajuste nos Repasses (R$)', 'formula': '(var98 - var101) - (variavel_nova_2 + variavel_nova_5) if var101 != 0 else "Não Finalizada"'},

            # Nova coluna: Resultado Operacional Ajustado (Resultado Operacional projetado + Custo ajuste nos Repasses)
            {'tipo': 'formula', 'campo': 'variavel_nova_19', 'nome': 'Resultado Operacional Ajustado (R$)', 'formula': 'variavel_nova_8 + variavel_nova_18 if variavel_nova_18 != "Não Finalizada" else "Não Finalizada"'},

            # 29-30: var98, var101
            {'tipo': 'variavel', 'campo': 'var98', 'nome': None},
            {'tipo': 'variavel', 'campo': 'var101', 'nome': None},

            # 31-33: Fórmulas resultado caixa e operacional
            {'tipo': 'formula', 'campo': 'variavel_nova_9', 'nome': 'Resultado Caixa (Rcebtos - Repasses) R$', 'formula': '0 if var101 == 0 else var98 - var101'},
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

    @staticmethod
    def obter_mapeamento_colunas_rpr_dinamico():
        """Retorna mapeamento específico para tabela RPR baseado na nova estrutura"""
        from .utils.column_mappings import obter_mapeamento_colunas_completo

        mapeamento_completo = obter_mapeamento_colunas_completo()
        estrutura = RPRService.obter_estrutura_colunas_rpr()

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

    @staticmethod
    def obter_colunas_monetarias_rpr_dinamico():
        """Retorna lista de colunas que devem ser formatadas como monetárias no RPR"""
        estrutura = RPRService.obter_estrutura_colunas_rpr()
        colunas_monetarias = []

        for item in estrutura:
            campo = item['campo']
            # Variáveis monetárias conhecidas (exceto campos auxiliares para totalizadores)
            if campo in ['var11', 'var15', 'var26', 'var37', 'var41', 'var90', 'var94_A', 'var98', 'variavel_nova_18', 'variavel_nova_19', 'var101', 'var58', 'var111_A']:
                colunas_monetarias.append(campo)
            # Fórmulas que resultam em valores monetários (R$)
            elif item['tipo'] == 'formula' and 'R$' in item['nome']:
                colunas_monetarias.append(campo)

        return colunas_monetarias

    @staticmethod
    def obter_colunas_percentuais_rpr_dinamico():
        """Retorna lista de colunas que devem ser formatadas como percentuais no RPR"""
        estrutura = RPRService.obter_estrutura_colunas_rpr()
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

    @staticmethod
    def calcular_formula(formula, transacao, variaveis_calculadas):
        """Calcula fórmula com variáveis do banco e calculadas"""
        try:
            from decimal import Decimal
            import re

            formula_processada = formula
            vars_encontradas = re.findall(r'var\d+(?:_A)?|variavel_nova_\d+', formula_processada)

            for var_name in vars_encontradas:
                if var_name in formula_processada:
                    # Se é variável calculada, buscar do cache primeiro
                    if var_name.startswith('variavel_nova_') or var_name in variaveis_calculadas:
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
                            if isinstance(valor, str):
                                valor_num = Decimal(valor.replace(',', '.')) if valor else Decimal('0')
                            elif isinstance(valor, Decimal):
                                valor_num = valor
                            else:
                                valor_num = Decimal(str(valor)) if valor else Decimal('0')
                        except (ValueError, TypeError):
                            valor_num = Decimal('0')

                        formula_processada = formula_processada.replace(var_name, str(valor_num))

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

    @staticmethod
    def calcular_linha_rpr(transacao, estrutura_colunas, para_export=False):
        """Calcula uma linha da tabela RPR com variáveis e fórmulas"""
        linha = {}
        variaveis_calculadas = {}

        # FASE 1: Calcular todas as variáveis na ordem de dependências
        # Primeiro processar variáveis do banco
        for item in estrutura_colunas:
            if item['tipo'] == 'variavel':
                campo = item['campo']
                valor = transacao.get(campo, '') if isinstance(transacao, dict) else getattr(transacao, campo, '')
                if campo == 'var113_A':
                    registrar_log('portais.admin', f"DEBUG FASE1 - var113_A encontrado na transação: valor={valor}, tipo={type(valor)}")
                try:
                    if isinstance(valor, str):
                        variaveis_calculadas[campo] = float(valor.replace(',', '.')) if valor else 0
                    else:
                        variaveis_calculadas[campo] = float(valor) if valor else 0
                except (ValueError, TypeError):
                    variaveis_calculadas[campo] = 0

        # Depois processar fórmulas na ordem correta de dependências
        formulas_ordenadas = [
            'variavel_nova_1', 'variavel_nova_2', 'variavel_nova_3', 'var15', 'variavel_nova_4',
            'variavel_nova_5', 'variavel_nova_6', 'variavel_nova_8', 'variavel_nova_7',
            'variavel_nova_18', 'variavel_nova_19', 'variavel_nova_9', 'variavel_nova_11', 'variavel_nova_10', 'variavel_nova_12',
            'variavel_nova_13', 'variavel_nova_14', 'variavel_nova_15', 'variavel_nova_17', 'variavel_nova_16'
        ]

        for campo_formula in formulas_ordenadas:
            for item in estrutura_colunas:
                if item['tipo'] == 'formula' and item['campo'] == campo_formula:
                    resultado = RPRService.calcular_formula(item['formula'], transacao, variaveis_calculadas)
                    variaveis_calculadas[campo_formula] = resultado
                    break

        # FASE 2: Montar linha na ordem de exibição com formatação
        for item in estrutura_colunas:
            campo = item['campo']

            if item['tipo'] == 'variavel':
                valor = transacao.get(campo, '') if isinstance(transacao, dict) else getattr(transacao, campo, '')

                if not para_export and campo in RPRService.obter_colunas_monetarias_rpr_dinamico():
                    try:
                        if valor and str(valor).strip():
                            valor_float = float(str(valor).replace(',', '.'))
                            linha[campo] = f"R$ {valor_float:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                        else:
                            linha[campo] = 'R$ 0,00'
                    except (ValueError, TypeError):
                        linha[campo] = str(valor) if valor else ''
                elif campo in ['var36', 'var89', 'var39', 'var92', 'var40', 'var93_A']:
                    try:
                        valor_float = float(str(valor).replace(',', '.')) if valor else 0
                        if para_export:
                            linha[campo] = valor_float
                        else:
                            if valor_float != 0:
                                percentual = valor_float * 100
                                linha[campo] = f"{percentual:.2f}%"
                            else:
                                linha[campo] = '0.00%'
                    except (ValueError, TypeError):
                        linha[campo] = 0 if para_export else '0.00%'
                elif not para_export and campo in ['var11'] and isinstance(valor, (int, float)) and valor > 0:
                    linha[campo] = f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                elif campo in ['var113_A', 'var109_A', 'var116_A', 'var118_A']:
                    linha[campo] = valor if valor else 0
                    if campo == 'var113_A':
                        registrar_log('portais.admin', f"DEBUG - Incluindo var113_A na linha: valor={valor}")
                else:
                    linha[campo] = str(valor) if valor else ''

                try:
                    if isinstance(valor, str):
                        variaveis_calculadas[campo] = float(valor.replace(',', '.')) if valor else 0
                    else:
                        variaveis_calculadas[campo] = float(valor) if valor else 0
                except (ValueError, TypeError):
                    variaveis_calculadas[campo] = 0

            elif item['tipo'] == 'formula':
                resultado = variaveis_calculadas.get(campo, 0)

                if campo in ['variavel_nova_1', 'variavel_nova_3', 'variavel_nova_6', 'variavel_nova_7',
                            'variavel_nova_10', 'variavel_nova_12', 'variavel_nova_14', 'variavel_nova_16']:
                    try:
                        valor_float = float(str(resultado).replace(',', '.')) if resultado else 0
                        if para_export:
                            linha[campo] = valor_float
                        else:
                            if valor_float != 0:
                                percentual = valor_float * 100
                                linha[campo] = f"{percentual:.2f}%"
                            else:
                                linha[campo] = '0.00%'
                    except (ValueError, TypeError):
                        linha[campo] = 0 if para_export else '0.00%'
                elif campo == 'var15' or (not para_export and resultado != 0):
                    try:
                        valor_num = float(resultado) if resultado else 0
                        if para_export:
                            linha[campo] = valor_num
                        else:
                            linha[campo] = f"R$ {valor_num:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    except (ValueError, TypeError):
                        linha[campo] = str(resultado) if resultado else ''
                else:
                    linha[campo] = str(resultado) if resultado else ''

        return linha

    # ==================== TOTALIZAÇÃO RPR ====================

    @staticmethod
    def calcular_percentual_totalizador(campo, totais):
        """Calcula percentuais dos totalizadores baseados nos totais agregados"""
        from decimal import Decimal

        if campo == 'var36':  # Valor MDR Wall (pago Loja) - %
            var37_total = totais.get('var37', Decimal('0'))
            var26_total = totais.get('var26', Decimal('0'))
            return (var37_total / var26_total).quantize(Decimal('0.0001')) if var26_total > 0 else Decimal('0')

        elif campo == 'var89':  # MDR Pago Uptal (%)
            var90_total = totais.get('var90', Decimal('0'))
            var26_total = totais.get('var26', Decimal('0'))
            return (var90_total / var26_total).quantize(Decimal('0.0001')) if var26_total > 0 else Decimal('0')

        elif campo == 'variavel_nova_1':  # Resultado MDR (%)
            var37_total = totais.get('var37', Decimal('0'))
            var90_total = totais.get('var90', Decimal('0'))
            var26_total = totais.get('var26', Decimal('0'))
            variavel_nova_2 = var37_total - var90_total
            return (variavel_nova_2 / var26_total).quantize(Decimal('0.0001')) if var26_total > 0 else Decimal('0')

        elif campo == 'variavel_nova_7':  # Resultado Operacional (projetado) %
            var15_total = totais.get('var15', Decimal('0'))
            var41_total = totais.get('var41', Decimal('0'))
            var94_A_total = totais.get('var94_A', Decimal('0'))
            var37_total = totais.get('var37', Decimal('0'))
            var90_total = totais.get('var90', Decimal('0'))
            var11_total = totais.get('var11', Decimal('0'))
            variavel_nova_8 = ((var15_total + var41_total) - var94_A_total) + (var37_total - var90_total)
            return (variavel_nova_8 / var11_total).quantize(Decimal('0.0001')) if var11_total > 0 else Decimal('0')

        elif campo == 'variavel_nova_10':  # Resultado Operacional (antes Cashback e Chargeback) %
            var113_A_total = totais.get('var113_A', Decimal('0'))
            var11_total = totais.get('var11', Decimal('0'))
            return (var113_A_total / var11_total).quantize(Decimal('0.0001')) if var11_total > 0 else Decimal('0')

        elif campo == 'variavel_nova_12':  # Cashback pago à Loja (%)
            var58_total = totais.get('var58', Decimal('0'))
            var11_total = totais.get('var11', Decimal('0'))
            return (var58_total / var11_total).quantize(Decimal('0.0001')) if var11_total > 0 else Decimal('0')

        elif campo == 'variavel_nova_14':  # Resultado Final (pós impostos - sem POS) - Visão Gestão - %
            var116_A_total = totais.get('var116_A', Decimal('0'))
            var11_total = totais.get('var11', Decimal('0'))
            return (var116_A_total / var11_total).quantize(Decimal('0.0001')) if var11_total > 0 else Decimal('0')

        elif campo == 'variavel_nova_16':  # Resultado Final (pós impostos - sem POS) %
            var113_A_total = totais.get('var113_A', Decimal('0'))
            var109_A_total = totais.get('var109_A', Decimal('0'))
            var11_total = totais.get('var11', Decimal('0'))
            variavel_nova_17 = var113_A_total - var109_A_total
            return (variavel_nova_17 / var11_total).quantize(Decimal('0.0001')) if var11_total > 0 else Decimal('0')

        return Decimal('0')

    @staticmethod
    def calcular_media_ponderada_parcelas(totais):
        """Calcula média ponderada de parcelas por volume"""
        from decimal import Decimal

        var11_total = totais.get('var11', Decimal('0'))
        soma_parcelas_ponderada = totais.get('soma_parcelas_ponderada', Decimal('0'))

        if var11_total > 0:
            return (soma_parcelas_ponderada / var11_total).quantize(Decimal('0.01'))
        return Decimal('0.00')

    @staticmethod
    def calcular_totais_de_linhas(linhas, campos_necessarios):
        """Calcula totais de campos específicos a partir de uma lista de linhas"""
        from decimal import Decimal, InvalidOperation

        totais = {}

        for campo in campos_necessarios:
            total = Decimal('0')
            for linha in linhas:
                valor = linha.get(campo, 0)
                if valor and valor != '' and valor != 'Não Finalizada':
                    try:
                        if isinstance(valor, str):
                            valor_limpo = valor.replace('R$', '').replace('%', '').replace('.', '').replace(',', '.').strip()
                            if valor_limpo:
                                total += Decimal(valor_limpo)
                        else:
                            total += Decimal(str(valor))
                    except (ValueError, TypeError, InvalidOperation):
                        pass
            totais[campo] = total

        # Calcular soma ponderada de parcelas se var13 estiver nos campos
        if 'var13' in campos_necessarios and 'var11' in campos_necessarios:
            soma_parcelas_ponderada = Decimal('0')
            for linha in linhas:
                var13 = linha.get('var13', 0)
                var11 = linha.get('var11', 0)
                if var13 and var11:
                    try:
                        parcelas = Decimal(str(var13)) if var13 else Decimal('0')
                        volume = Decimal(str(var11)) if var11 else Decimal('0')
                        soma_parcelas_ponderada += parcelas * volume
                    except (ValueError, TypeError, InvalidOperation):
                        pass
            totais['soma_parcelas_ponderada'] = soma_parcelas_ponderada

        return totais

    @staticmethod
    def calcular_totalizador_rpr(dados, estrutura_colunas, para_tela=False):
        """
        Calcula linha totalizadora do RPR de forma unificada

        Args:
            dados: Lista de linhas já calculadas (com para_export=True)
            estrutura_colunas: Estrutura de colunas RPR
            para_tela: Se True, formata percentuais como string (ex: "2.50%")

        Returns:
            Dict com linha totalizadora
        """
        from decimal import Decimal, InvalidOperation

        linha_totalizadora = {}
        colunas_monetarias = RPRService.obter_colunas_monetarias_rpr_dinamico()
        colunas_percentuais = RPRService.obter_colunas_percentuais_rpr_dinamico()

        for item in estrutura_colunas:
            campo = item['campo']

            if campo == 'var0':
                linha_totalizadora[campo] = "TOTAL"
            elif campo in ['var1', 'var2', 'var3', 'var4', 'var5', 'var6', 'var7', 'var8', 'var9', 'var10', 'var12', 'var43', 'var68', 'tipo_operacao']:
                linha_totalizadora[campo] = ""
            elif campo in ['var39', 'var92', 'var40', 'var93_A', 'variavel_nova_3', 'variavel_nova_6']:
                # Percentuais sem totalização
                linha_totalizadora[campo] = ""
            elif campo == 'var13':
                # Média ponderada de parcelas
                campos_necessarios = ['var11', 'var13']
                totais = RPRService.calcular_totais_de_linhas(dados, campos_necessarios)
                media = RPRService.calcular_media_ponderada_parcelas(totais)
                linha_totalizadora[campo] = float(media) if media > 0 else ""
            elif campo in colunas_percentuais:
                # Calcular percentuais com totalização
                if campo in ['var36', 'var89', 'variavel_nova_1', 'variavel_nova_7', 'variavel_nova_10', 'variavel_nova_12', 'variavel_nova_14', 'variavel_nova_16']:
                    campos_necessarios = ['var11', 'var26', 'var37', 'var90', 'var15', 'var41', 'var94_A', 'var58', 'var113_A', 'var109_A', 'var116_A']
                    totais = RPRService.calcular_totais_de_linhas(dados, campos_necessarios)
                    percentual = RPRService.calcular_percentual_totalizador(campo, totais)

                    # Debug temporário
                    import logging
                    logger = logging.getLogger('portais.admin')
                    if campo in ['variavel_nova_7', 'variavel_nova_10', 'variavel_nova_12', 'variavel_nova_14', 'variavel_nova_16']:
                        logger.info(f"DEBUG TOTALIZADOR {campo}: percentual={percentual}, var11={totais.get('var11')}, var15={totais.get('var15')}, var41={totais.get('var41')}, var94_A={totais.get('var94_A')}, var37={totais.get('var37')}, var90={totais.get('var90')}, var58={totais.get('var58')}, var113_A={totais.get('var113_A')}, var116_A={totais.get('var116_A')}")

                    if para_tela:
                        linha_totalizadora[campo] = f"{float(percentual) * 100:.2f}%"
                    else:
                        linha_totalizadora[campo] = float(percentual)
                else:
                    linha_totalizadora[campo] = ""
            elif campo in colunas_monetarias or item.get('tipo') == 'formula':
                # Somar valores numéricos
                total = Decimal('0')
                for linha in dados:
                    valor = linha.get(campo, 0)
                    if valor and valor != '' and valor != 'Não Finalizada':
                        try:
                            total += Decimal(str(valor))
                        except (ValueError, TypeError, InvalidOperation):
                            pass
                linha_totalizadora[campo] = total
            else:
                # Outros campos - somar se numérico
                total = Decimal('0')
                for linha in dados:
                    valor = linha.get(campo, 0)
                    if valor and valor != '':
                        try:
                            total += Decimal(str(valor))
                        except (ValueError, TypeError, InvalidOperation):
                            pass
                linha_totalizadora[campo] = total if total != 0 else ""

        return linha_totalizadora
