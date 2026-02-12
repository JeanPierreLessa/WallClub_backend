"""
Serviço para carga da Base Transações Unificadas - Checkout
Processa transações de checkout (vendas diretas via portal de vendas)
Usa CalculadoraBaseUnificada (tipo_operacao: Wallet)

Diferença da base antiga:
- Insere em base_transacoes_unificadas (nova tabela)
- 1 linha por transação (não duplica por parcela)
- Marca registros como processados
- tipo_operacao = 'Wallet' (não passa por credenciadora)
"""

from typing import Dict, Any
from django.db import connection, transaction
from .models import PinbankExtratoPOS
from wallclub_core.utilitarios.log_control import registrar_log


class CargaBaseUnificadaCheckoutService:
    """
    Serviço para carga da base unificada - Checkout
    Regra: 1 linha por transação (NSU único), não por parcela
    Filtro: Apenas transações com processado = 0
    Tipo: Wallet (vendas diretas, sem credenciadora)
    """

    def __init__(self):
        from parametros_wallclub.calculadora_base_unificada import CalculadoraBaseUnificada
        from pinbank.services import PinbankService
        self.calculadora = CalculadoraBaseUnificada()
        self.pinbank_service = PinbankService()

    def carregar_valores_primarios(self, limite: int = None, nsu: str = None, worker_id: int = None) -> int:
        """
        Rotina principal de carga de variáveis primárias
        Processa registros com processado = 0
        Agrupa por NSU (1 linha por transação)

        Args:
            limite: Limite de registros
            nsu: NSU específico
            worker_id: ID do worker (0-9) para processamento paralelo
        """
        registrar_log('pinbank.cargas_pinbank', f"Iniciando carga de valores primários - Base Unificada Checkout (worker_id={worker_id})")

        limit_clause = f"LIMIT {limite}" if limite else ""
        nsu_clause = f"AND pep.NsuOperacao = '{nsu}'" if nsu else ""
        worker_clause = f"AND MOD(CAST(pep.NsuOperacao AS UNSIGNED), 2) = {worker_id}" if worker_id is not None else ""

        registrar_log('pinbank.cargas_pinbank', f"Executando query com limite={limite}, nsu={nsu}, worker_id={worker_id}")

        with connection.cursor() as cursor:
            # Query simplificada - pega apenas 1 registro por NSU (menor id)
            cursor.execute(f"""
                SELECT   pep.id,
                         l.canal_id,
                         pep.codigo_cliente as codigoCliente,
                         cecp.cliente_id as clienteId,
                         cecp.nome as razao_social,
                         cecp.cnpj as cnpj,
                         cc.cpf as cpf,
                         ct.nsu as nsuAcquirer,
                         ct.origem as origem_checkout,
                         pep.idTerminal,
                         pep.SerialNumber,
                         pep.Terminal,
                         pep.Bandeira,
                         pep.TipoCompra,
                         pep.DadosExtra,
                         pep.CpfCnpjComprador,
                         pep.NomeRazaoSocialComprador,
                         pep.NumeroParcela,
                         pep.NumeroTotalParcelas,
                         pep.DataTransacao,
                         pep.DataFuturaPagamento,
                         pep.CodAutorizAdquirente,
                         pep.NsuOperacao,
                         pep.NsuOperacaoLoja,
                         pep.ValorBruto,
                         pep.ValorBrutoParcela,
                         pep.ValorLiquidoRepasse,
                         pep.ValorSplit,
                         pep.IdStatus,
                         pep.DescricaoStatus,
                         pep.IdStatusPagamento,
                         pep.DescricaoStatusPagamento,
                         pep.ValorTaxaAdm,
                         pep.ValorTaxaMes,
                         pep.NumeroCartao,
                         pep.DataCancelamento,
                         pep.Submerchant,
                         pep.ValorBruto as valor_original,
                         ( SELECT  SUM(pep2.ValorLiquidoRepasse)
                           FROM   wallclub.pinbankExtratoPOS pep2
                           WHERE  pep.NsuOperacao = pep2.NsuOperacao
                                  AND pep2.DescricaoStatusPagamento in ('Pago','Pago-M'))   vRepasse,
                         ( SELECT var69
                           FROM   base_transacoes_unificadas btu
                           WHERE  btu.var9 = CAST(pep.NsuOperacao AS CHAR) COLLATE utf8mb4_unicode_ci ) var69_atual
                FROM     wallclub.pinbankExtratoPOS pep
                INNER JOIN wallclub.credenciaisExtratoContaPinbank cecp ON pep.codigo_cliente = cecp.codigo_cliente
                INNER JOIN wallclub.loja l ON l.id = cecp.cliente_id
                INNER JOIN wallclub.checkout_transactions ct ON pep.NsuOperacao = ct.nsu
                INNER JOIN wallclub.checkout_cliente cc ON ct.cliente_id = cc.id
                WHERE    pep.processado = 0
                         AND pep.id IN (
                             SELECT MIN(pep2.id)
                             FROM wallclub.pinbankExtratoPOS pep2
                             INNER JOIN wallclub.credenciaisExtratoContaPinbank cecp2 ON pep2.codigo_cliente = cecp2.codigo_cliente
                             INNER JOIN wallclub.loja l2 ON l2.id = cecp2.cliente_id
                             INNER JOIN wallclub.checkout_transactions ct2 ON pep2.NsuOperacao = ct2.nsu
                             WHERE pep2.processado = 0
                             {worker_clause}
                             GROUP BY pep2.NsuOperacao
                         )
                         {nsu_clause}
                         {worker_clause}
                ORDER BY pep.id
                {limit_clause}
            """)

            registrar_log('pinbank.cargas_pinbank', "Query executada com sucesso")

            colunas = [desc[0] for desc in cursor.description]
            registros_processados = 0

            registrar_log('pinbank.cargas_pinbank', f"Iniciando processamento de registros em lotes de 100")

            # Cache de canais para evitar N+1 queries
            from wallclub_core.estr_organizacional.canal import Canal
            canais_cache = {}
            for canal in Canal.objects.all():
                canais_cache[canal.id] = {
                    'id': canal.id,
                    'codigo_canal': int(canal.canal) if canal.canal and canal.canal.isdigit() else 0,
                    'codigo_cliente': int(canal.codigo_cliente) if canal.codigo_cliente and canal.codigo_cliente.isdigit() else 0,
                    'key_loja': canal.keyvalue or '',
                    'canal': canal.nome or '',  # Nome do canal, não o código
                    'nome': canal.nome or ''
                }
            registrar_log('pinbank.cargas_pinbank', f"Cache de {len(canais_cache)} canais carregado")

            # Processar em lotes de 100 registros
            BATCH_SIZE = 100
            lote_atual = []
            numero_lote = 1

            # Processar linha por linha (streaming)
            while True:
                row = cursor.fetchone()
                if row is None:
                    break

                lote_atual.append(row)

                # Quando completar um lote de 100, processar
                if len(lote_atual) >= BATCH_SIZE:
                    registrar_log('pinbank.cargas_pinbank', f"Processando lote unificado Checkout {numero_lote}: {len(lote_atual)} registros")

                    # Coletar IDs processados para batch update
                    ids_processados = []

                    with transaction.atomic():
                        for row_lote in lote_atual:
                            linha = dict(zip(colunas, row_lote))

                            try:
                                # Montar info_loja
                                info_loja = {
                                    'id': linha.get('clienteId'),
                                    'loja_id': linha.get('clienteId'),
                                    'loja': linha.get('razao_social'),
                                    'cnpj': linha.get('cnpj'),
                                    'canal_id': linha.get('canal_id')
                                }

                                # Usar cache ao invés de query
                                canal_id = linha.get('canal_id')
                                info_canal = canais_cache.get(canal_id)
                                if not info_canal:
                                    registrar_log('pinbank.cargas_pinbank',
                                                f"⚠️ Canal ID {canal_id} não encontrado no cache",
                                                nivel='WARNING')
                                    info_canal = {
                                        'id': canal_id,
                                        'codigo_canal': 0,
                                        'codigo_cliente': 0,
                                        'key_loja': '',
                                        'canal': f'CANAL_{canal_id}',  # Fallback com ID
                                        'nome': f'CANAL_{canal_id}'
                                    }

                                # Calcular valores primários
                                valores = self.calculadora.calcular_valores_primarios(
                                    dados_linha=linha,
                                    tabela='transactiondata_pos',
                                    info_loja=info_loja,
                                    info_canal=info_canal
                                )

                                # Inserir na base unificada
                                sucesso = self._inserir_valores_base_unificada(valores, linha)

                                if sucesso:
                                    ids_processados.append(linha['id'])
                                    registros_processados += 1
                                else:
                                    registrar_log('pinbank.cargas_pinbank',
                                                f"Valores não foram inseridos para NSU={linha['NsuOperacao']}",
                                                nivel='WARNING')

                            except Exception as e:
                                import traceback
                                erro_detalhado = traceback.format_exc()
                                registrar_log('pinbank.cargas_pinbank',
                                            f"Erro crítico (Checkout Unificado): NSU={linha.get('NsuOperacao')}, Erro: {str(e)}",
                                            nivel='ERROR')
                                registrar_log('pinbank.cargas_pinbank', f"Traceback completo: {erro_detalhado}", nivel='ERROR')

                        # Batch update de processado=1
                        if ids_processados:
                            PinbankExtratoPOS.objects.filter(id__in=ids_processados).update(processado=1)

                    registrar_log('pinbank.cargas_pinbank',
                                f"Lote Checkout {numero_lote} commitado com sucesso ({len(ids_processados)} registros processados)")
                    lote_atual = []
                    numero_lote += 1

            # Processar último lote se houver registros restantes
            if lote_atual:
                registrar_log('pinbank.cargas_pinbank', f"Processando último lote unificado Checkout: {len(lote_atual)} registros")

                ids_processados = []

                with transaction.atomic():
                    for row_lote in lote_atual:
                        linha = dict(zip(colunas, row_lote))

                        try:
                            # Montar info_loja
                            info_loja = {
                                'id': linha.get('clienteId'),
                                'loja_id': linha.get('clienteId'),
                                'loja': linha.get('razao_social'),
                                'cnpj': linha.get('cnpj'),
                                'canal_id': linha.get('canal_id')
                            }

                            # Usar cache ao invés de query
                            canal_id = linha.get('canal_id')
                            info_canal = canais_cache.get(canal_id)
                            if not info_canal:
                                registrar_log('pinbank.cargas_pinbank',
                                            f"⚠️ Canal ID {canal_id} não encontrado no cache",
                                            nivel='WARNING')
                                info_canal = {
                                    'id': canal_id,
                                    'codigo_canal': 0,
                                    'codigo_cliente': 0,
                                    'key_loja': '',
                                    'canal': f'CANAL_{canal_id}',
                                    'nome': f'CANAL_{canal_id}'
                                }

                            # Calcular valores primários
                            valores = self.calculadora.calcular_valores_primarios(
                                dados_linha=linha,
                                tabela='transactiondata_pos',
                                info_loja=info_loja,
                                info_canal=info_canal
                            )
                            sucesso = self._inserir_valores_base_unificada(valores, linha)

                            if sucesso:
                                ids_processados.append(linha['id'])
                                registros_processados += 1
                            else:
                                registrar_log('pinbank.cargas_pinbank',
                                            f"Valores não foram inseridos para NSU={linha['NsuOperacao']}",
                                            nivel='WARNING')

                        except Exception as e:
                            import traceback
                            erro_detalhado = traceback.format_exc()
                            registrar_log('pinbank.cargas_pinbank',
                                        f"Erro crítico (Checkout Unificado): NSU={linha.get('NsuOperacao')}, Erro: {str(e)}",
                                        nivel='ERROR')
                            registrar_log('pinbank.cargas_pinbank', f"Traceback completo: {erro_detalhado}", nivel='ERROR')

                    # Batch update
                    if ids_processados:
                        PinbankExtratoPOS.objects.filter(id__in=ids_processados).update(processado=1)

                registrar_log('pinbank.cargas_pinbank',
                            f"Último lote Checkout commitado com sucesso ({len(ids_processados)} registros processados)")

        registrar_log('pinbank.cargas_pinbank',
                    f"Carga de valores primários Checkout Unificado finalizada. Registros processados: {registros_processados}")
        return registros_processados

    def _inserir_valores_base_unificada(self, valores: Dict[int, Any], linha: Dict) -> bool:
        """
        Insere ou atualiza valores na base unificada
        Lógica: Se já existe, verifica mudanças (status, cancelamento, pagamento)
        """
        try:
            nsu = linha.get('NsuOperacao')
            if not nsu:
                return False

            # Preparar dados para inserção/update
            dados_insert = {}

            # Campos fixos
            dados_insert['tipo_operacao'] = 'Wallet'
            dados_insert['adquirente'] = 'PINBANK'

            # Mapear origem do checkout_transactions para origem_transacao
            origem_checkout = linha.get('origem_checkout', 'CHECKOUT')
            if origem_checkout == 'RECORRENCIA':
                dados_insert['origem_transacao'] = 'RECORRENCIA'
            else:
                dados_insert['origem_transacao'] = 'LINK_PAGAMENTO'

            dados_insert['data_transacao'] = linha.get('DataTransacao')

            # Campos varchar (texto)
            varchar_fields = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130}

            # Mapear valores para campos var0-var130
            for i in range(131):
                campo_nome = f'var{i}'
                if i in valores:
                    valor = valores[i]
                    if isinstance(valor, dict):
                        if "0" in valor:
                            dados_insert[campo_nome] = valor["0"]
                        else:
                            dados_insert[campo_nome] = None
                    else:
                        if valor is None or valor == '':
                            dados_insert[campo_nome] = None
                        else:
                            if i in varchar_fields:
                                dados_insert[campo_nome] = str(valor)
                            else:
                                try:
                                    dados_insert[campo_nome] = float(valor)
                                except (ValueError, TypeError):
                                    dados_insert[campo_nome] = None

            with connection.cursor() as cursor:
                # Verificar se já existe e buscar campos críticos
                cursor.execute("""
                    SELECT var69, var70, var44, var45
                    FROM wallclub.base_transacoes_unificadas
                    WHERE var9 = %s AND tipo_operacao = 'Wallet'
                """, [str(nsu)])

                registro_atual = cursor.fetchone()

                if registro_atual:
                    # Registro já existe - verificar se precisa UPDATE
                    var69_atual, var70_atual, var44_atual, var45_atual = registro_atual
                    var69_novo = dados_insert.get('var69')
                    var70_novo = dados_insert.get('var70')
                    var44_novo = dados_insert.get('var44')
                    var45_novo = dados_insert.get('var45')

                    # Verificar mudanças
                    status_mudou = str(var69_atual or '') != str(var69_novo or '')
                    cancelamento_novo = (not var70_atual) and var70_novo
                    pagamento_mudou = (str(var44_atual or '') != str(var44_novo or '')) or (str(var45_atual or '') != str(var45_novo or ''))

                    if status_mudou or cancelamento_novo or pagamento_mudou:
                        # UPDATE completo
                        set_clause = ', '.join([f'`{col}` = %s' for col in dados_insert.keys() if col != 'var9'])
                        valores_update = [v for k, v in dados_insert.items() if k != 'var9']
                        valores_update.append(str(nsu))

                        sql = f"UPDATE wallclub.base_transacoes_unificadas SET {set_clause} WHERE var9 = %s AND tipo_operacao = 'Wallet'"
                        cursor.execute(sql, valores_update)

                        # Auditoria
                        import json
                        motivo = []
                        if status_mudou:
                            motivo.append(f"status: {var69_atual} -> {var69_novo}")
                        if cancelamento_novo:
                            motivo.append(f"cancelamento: {var70_novo}")
                        if pagamento_mudou:
                            motivo.append(f"pagamento: var44={var44_novo}, var45={var45_novo}")

                        cursor.execute("""
                            INSERT INTO auditoria_base_unificada_mudancas
                            (var9, tipo_operacao, colunas_alteradas, qtd_colunas_alteradas)
                            VALUES (%s, 'Wallet', %s, %s)
                        """, [str(nsu), json.dumps(motivo), 1])

                        registrar_log('pinbank.cargas_pinbank', f'✅ Atualizado em base_transacoes_unificadas - NSU: {nsu} - Motivo: {", ".join(motivo)}')
                    else:
                        registrar_log('pinbank.cargas_pinbank', f'NSU {nsu} já existe sem mudanças. Apenas marcando como processado.')

                    # Marcar como processado
                    cursor.execute(
                        "UPDATE wallclub.pinbankExtratoPOS SET processado = 1 WHERE NsuOperacao = %s",
                        [nsu]
                    )
                else:
                    # INSERT novo registro
                    campos = list(dados_insert.keys())
                    valores_lista = list(dados_insert.values())
                    placeholders = ', '.join(['%s'] * len(valores_lista))
                    campos_str = ', '.join(campos)

                    cursor.execute(f"""
                        INSERT INTO base_transacoes_unificadas ({campos_str})
                        VALUES ({placeholders})
                    """, valores_lista)

                    # Marcar como processado
                    cursor.execute(
                        "UPDATE wallclub.pinbankExtratoPOS SET processado = 1 WHERE NsuOperacao = %s",
                        [nsu]
                    )

                    registrar_log('pinbank.cargas_pinbank', f'✅ Inserido em base_transacoes_unificadas - NSU: {nsu}')

            return True

        except Exception as e:
            registrar_log('pinbank.cargas_pinbank',
                        f'❌ Erro ao inserir/atualizar base_transacoes_unificadas: {str(e)}',
                        nivel='ERROR')
            return False
