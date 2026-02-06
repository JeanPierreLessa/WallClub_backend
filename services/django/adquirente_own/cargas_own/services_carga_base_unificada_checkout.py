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
            # LOG TEMPORÁRIO: Ver query completa
            registrar_log('own.cargas_own', f"🔍 QUERY: {query}")

            cursor.execute(query)
            transacoes = cursor.fetchall()

            registrar_log('own.cargas_own', f"📊 Encontradas {len(transacoes)} transações OWN checkout para processar")

            # LOG TEMPORÁRIO: Ver primeiras transações
            if transacoes:
                registrar_log('own.cargas_own', f"📋 Primeira transação: {transacoes[0]}")

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

                        # Preparar dados para calculadora (compatível com CalculadoraBaseUnificada)
                        dados_transacao = {
                            'id': checkout_transaction_id,
                            'NsuOperacao': str(nsu),
                            'DataTransacao': data_transacao.strftime('%Y-%m-%dT%H:%M:%S') if data_transacao else '',
                            'HoraTransacao': data_transacao.strftime('%H:%M:%S') if data_transacao else '',
                            'ValorTransacao': valor,
                            'ValorBruto': valor,
                            'valor_original': valor,
                            'ValorBrutoParcela': valor / parcelas if parcelas > 0 else valor,
                            'QuantidadeParcelas': parcelas,
                            'NumeroTotalParcelas': parcelas,
                            'FormaPagamento': str(forma_pagamento),
                            'TipoCompra': 'CREDITO' if 'CREDIT' in str(forma_pagamento).upper() else 'DEBITO',
                            'Bandeira': 'VISA',  # Extrair da forma_pagamento se necessário
                            'SerialNumber': '',
                            'idTerminal': '',
                            'nsuAcquirer': str(codigo_autorizacao) if codigo_autorizacao else '',
                            'cpf': '',  # Checkout não tem CPF do cliente
                            'ValorTaxaAdm': 0,
                            'ValorTaxaMes': 0,
                            'DescricaoStatus': 'APROVADA',
                            'ValorSplit': 0,
                            'DataFuturaPagamento': None,
                            'DescricaoStatusPagamento': 'Pendente',
                            'IdStatusPagamento': 1,
                            'DataCancelamento': None,
                            'tipo_operacao': 'Wallet',
                            'adquirente': 'OWN'
                        }

                        info_loja = {
                            'id': loja_id,
                            'nome': loja_nome,
                            'loja': loja_nome,
                            'canal_id': canal_id
                        }

                        info_canal = {
                            'id': canal_id,
                            'nome': canal_nome,
                            'canal': canal_nome
                        }

                        # Calcular variáveis
                        variaveis = self.calculadora.calcular_valores_primarios(
                            dados_linha=dados_transacao,
                            tabela='checkout_transactions',
                            info_loja=info_loja,
                            info_canal=info_canal
                        )

                        # DEBUG: Log do tipo e amostra das variáveis
                        registrar_log('own.cargas_own', f"DEBUG variaveis type: {type(variaveis)}")
                        if variaveis:
                            amostra = {k: v for k, v in list(variaveis.items())[:5]}
                            registrar_log('own.cargas_own', f"DEBUG variaveis amostra: {amostra}")

                        # Inserir na base unificada
                        self._inserir_base_unificada(variaveis)

                        total_processadas += 1

                        if total_processadas % 100 == 0:
                            registrar_log('own.cargas_own', f"✅ Processadas {total_processadas} transações...")

                except Exception as e:
                    import traceback
                    registrar_log(
                        'own.cargas_own',
                        f"❌ Erro ao processar transação {nsu}: {str(e)}\n{traceback.format_exc()}",
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
                # Adicionar prefixo 'var' se for número
                nome_campo = f'var{campo}' if isinstance(campo, int) else str(campo)
                campos.append(nome_campo)
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
