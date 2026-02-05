"""
Serviço para carga da Base Transações Unificadas - Checkout OWN
Processa transações de checkout OWN (vendas diretas via portal de vendas)
Usa CalculadoraBaseUnificada (tipo_operacao: Wallet)

Similar ao Pinbank, mas para transações OWN:
- Insere em base_transacoes_unificadas
- 1 linha por transação (não duplica por parcela)
- tipo_operacao = 'Wallet' (não passa por credenciadora)
- adquirente = 'OWN'
"""

from typing import Dict, Any
from django.db import connection, transaction
from wallclub_core.utilitarios.log_control import registrar_log


class CargaBaseUnificadaCheckoutOwnService:
    """
    Serviço para carga da base unificada - Checkout OWN
    Regra: 1 linha por transação (NSU único), não por parcela
    Filtro: gateway = 'OWN' e status = 'APROVADA'
    Tipo: Wallet (vendas diretas)
    Adquirente: OWN
    """

    def __init__(self):
        from parametros_wallclub.calculadora_base_unificada import CalculadoraBaseUnificada
        self.calculadora = CalculadoraBaseUnificada()

    def carregar_valores_primarios(self, limite: int = None, nsu: str = None) -> int:
        """
        Rotina principal de carga de variáveis primárias
        Processa transações OWN de checkout ainda não processadas

        Args:
            limite: Limite de registros
            nsu: NSU específico

        Returns:
            Total de transações processadas
        """
        registrar_log('own.cargas_own', f"🚀 Iniciando carga Base Unificada Checkout OWN")

        limit_clause = f"LIMIT {limite}" if limite else ""
        nsu_clause = f"AND ct.nsu = '{nsu}'" if nsu else ""

        # Query para buscar transações OWN de checkout não processadas
        query = f"""
            SELECT
                ct.id as checkout_transaction_id,
                ct.nsu,
                ct.loja_id,
                ct.valor_transacao_final as valor,
                ct.parcelas,
                ct.processed_at as data_transacao,
                ct.forma_pagamento,
                ct.codigo_autorizacao,
                l.canal_id,
                l.razao_social as loja_nome,
                c.nome as canal_nome
            FROM checkout_transactions ct
            INNER JOIN loja l ON ct.loja_id = l.id
            INNER JOIN canal c ON l.canal_id = c.id
            WHERE ct.gateway = 'OWN'
                AND ct.status = 'APROVADA'
                AND ct.processed_at IS NOT NULL
                AND NOT EXISTS (
                    SELECT 1 FROM base_transacoes_unificadas btu
                    WHERE btu.var9 = ct.nsu
                    AND btu.adquirente = 'OWN'
                    AND btu.tipo_operacao = 'Wallet'
                )
                {nsu_clause}
            ORDER BY ct.processed_at DESC
            {limit_clause}
        """

        total_processadas = 0

        with connection.cursor() as cursor:
            cursor.execute(query)
            transacoes = cursor.fetchall()

            registrar_log('own.cargas_own', f"📊 Encontradas {len(transacoes)} transações OWN checkout para processar")

            for row in transacoes:
                try:
                    with transaction.atomic():
                        checkout_transaction_id = row[0]
                        nsu = row[1]
                        loja_id = row[2]
                        valor = float(row[3])
                        parcelas = row[4] or 1
                        data_transacao = row[5]
                        forma_pagamento = row[6]
                        codigo_autorizacao = row[7]
                        canal_id = row[8]
                        loja_nome = row[9]
                        canal_nome = row[10]

                        # Preparar dados para calculadora
                        dados_transacao = {
                            'var0': data_transacao,  # Data da transação
                            'var1': data_transacao.strftime('%H:%M:%S') if data_transacao else '',  # Hora
                            'var4': canal_id,  # Código Canal
                            'var5': canal_nome,  # Nome Canal
                            'var6': loja_id,  # Código Loja
                            'var8': forma_pagamento,  # Forma de Pagamento
                            'var9': nsu,  # NSU
                            'var11': valor,  # Valor da Venda
                            'var13': parcelas,  # Número de Parcelas
                            'tipo_operacao': 'Wallet',  # Tipo de operação
                            'adquirente': 'OWN'  # Adquirente
                        }

                        # Calcular variáveis
                        resultado = self.calculadora.calcular_variaveis(dados_transacao)

                        if not resultado.get('sucesso'):
                            registrar_log(
                                'own.cargas_own',
                                f"❌ Erro ao calcular variáveis para NSU {nsu}: {resultado.get('mensagem')}",
                                nivel='ERROR'
                            )
                            continue

                        variaveis = resultado.get('variaveis', {})

                        # Inserir na base unificada
                        self._inserir_base_unificada(variaveis)

                        total_processadas += 1

                        if total_processadas % 100 == 0:
                            registrar_log('own.cargas_own', f"✅ Processadas {total_processadas} transações...")

                except Exception as e:
                    registrar_log(
                        'own.cargas_own',
                        f"❌ Erro ao processar transação {nsu}: {str(e)}",
                        nivel='ERROR'
                    )
                    continue

        registrar_log('own.cargas_own', f"✅ Carga concluída: {total_processadas} transações processadas")
        return total_processadas

    def _inserir_base_unificada(self, variaveis: Dict[str, Any]):
        """
        Insere registro na base_transacoes_unificadas

        Args:
            variaveis: Dicionário com todas as variáveis calculadas
        """
        # Preparar campos e valores
        campos = []
        valores = []

        for campo, valor in variaveis.items():
            if valor is not None and valor != '':
                campos.append(campo)
                valores.append(valor)

        if not campos:
            return

        campos_str = ', '.join(campos)
        placeholders = ', '.join(['%s'] * len(valores))

        # Montar SQL de insert com ON DUPLICATE KEY UPDATE
        campos_update = [f'{campo} = VALUES({campo})' for campo in campos if campo not in ['var9', 'tipo_operacao', 'adquirente']]
        update_clause = ', '.join(campos_update)

        sql = f"""
            INSERT INTO base_transacoes_unificadas ({campos_str})
            VALUES ({placeholders})
            ON DUPLICATE KEY UPDATE {update_clause}
        """

        with connection.cursor() as cursor:
            cursor.execute(sql, valores)

    def executar_carga_diaria(self) -> Dict[str, Any]:
        """
        Executa carga diária de transações OWN checkout
        Processa todas as transações pendentes

        Returns:
            Dict com resultado da carga
        """
        try:
            total = self.carregar_valores_primarios()

            return {
                'sucesso': True,
                'total_processadas': total,
                'mensagem': f'Carga concluída: {total} transações processadas'
            }
        except Exception as e:
            registrar_log('own.cargas_own', f"❌ Erro na carga diária: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': str(e)
            }
