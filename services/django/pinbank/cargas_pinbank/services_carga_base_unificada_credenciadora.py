"""
Serviço para carga da Base Transações Unificadas - Credenciadora
Processa transações de terminais credenciadora (sem cadastro no sistema)
Usa CalculadoraBaseCredenciadora

Diferença da base antiga:
- Insere em base_transacoes_unificadas (nova tabela)
- 1 linha por transação (não duplica por parcela)
- Marca registros como processados
"""

from typing import Dict, Any
from django.db import connection, transaction
from .models import PinbankExtratoPOS
from wallclub_core.utilitarios.log_control import registrar_log


class CargaBaseUnificadaCredenciadoraService:
    """
    Serviço para carga da base unificada - Credenciadora
    Regra: 1 linha por transação (NSU único), não por parcela
    Filtro: Apenas transações com lido = 0
    """

    def __init__(self):
        from parametros_wallclub.calculadora_base_credenciadora import CalculadoraBaseCredenciadora
        from pinbank.services import PinbankService
        self.calculadora = CalculadoraBaseCredenciadora()
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
        registrar_log('pinbank.cargas_pinbank', f"Iniciando carga de valores primários - Base Unificada Credenciadora (worker_id={worker_id})")

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
                         '' as cpf,
                         '' as nsuAcquirer,
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
                         0 as valor_original,
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
                LEFT JOIN transactiondata td ON pep.NsuOperacao = td.nsuPinbank
                LEFT JOIN checkout_transactions ct ON pep.NsuOperacaoLoja = ct.nsu
                LEFT JOIN terminais t ON pep.serialnumber = t.terminal
                WHERE    pep.processado = 0
                         AND td.nsuPinbank IS NULL
                         AND ct.nsu IS NULL
                         AND t.terminal IS NULL
                         AND pep.id IN (
                             SELECT MIN(pep2.id)
                             FROM wallclub.pinbankExtratoPOS pep2
                             INNER JOIN wallclub.credenciaisExtratoContaPinbank cecp2 ON pep2.codigo_cliente = cecp2.codigo_cliente
                             INNER JOIN wallclub.loja l2 ON l2.id = cecp2.cliente_id
                             LEFT JOIN transactiondata td2 ON pep2.NsuOperacao = td2.nsuPinbank
                             LEFT JOIN checkout_transactions ct2 ON pep2.NsuOperacaoLoja = ct2.nsu
                             LEFT JOIN terminais t2 ON pep2.serialnumber = t2.terminal
                             WHERE pep2.processado = 0
                             AND td2.nsuPinbank IS NULL
                             AND ct2.nsu IS NULL
                             AND t2.terminal IS NULL
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
                    'canal': canal.canal or '',
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
                    import time
                    inicio_lote = time.time()
                    registrar_log('pinbank.cargas_pinbank', f"Processando lote unificado Credenciadora {numero_lote}: {len(lote_atual)} registros")

                    # Coletar IDs processados para batch update
                    ids_processados = []

                    with transaction.atomic():
                        for idx, row_lote in enumerate(lote_atual):
                            linha = dict(zip(colunas, row_lote))

                            try:
                                import time
                                inicio_registro = time.time()

                                # Montar info_loja e info_canal
                                linha['info_loja'] = {
                                    'id': linha.get('clienteId'),
                                    'loja_id': linha.get('clienteId'),
                                    'loja': linha.get('razao_social'),
                                    'cnpj': linha.get('cnpj'),
                                    'canal_id': linha.get('canal_id')
                                }
                                # Usar cache ao invés de query
                                canal_id = linha.get('canal_id')
                                linha['info_canal'] = canais_cache.get(canal_id, {
                                    'id': canal_id,
                                    'codigo_canal': 0,
                                    'codigo_cliente': 0,
                                    'key_loja': '',
                                    'canal': '',
                                    'nome': ''
                                })

                                tempo_setup = time.time() - inicio_registro

                                # Verificar se precisa inserir/atualizar
                                var69_atual = linha.get('var69_atual')
                                descricao_status = linha.get('DescricaoStatusPagamento')
                                # Normalizar Pago-M para Pago
                                descricao_status_normalizado = 'Pago' if descricao_status == 'Pago-M' else descricao_status

                                # Caso 1: var69_atual = NULL → registro novo → INSERT
                                # Caso 2: var69_atual = DescricaoStatusPagamento → sem mudança → apenas marca processado
                                # Caso 3: var69_atual ≠ DescricaoStatusPagamento → status mudou → INSERT/UPDATE

                                if var69_atual is None:
                                    # Registro novo - inserir
                                    registrar_log('pinbank.cargas_pinbank',
                                        f"NSU {linha['NsuOperacao']}: NOVO (var69=NULL, status={descricao_status_normalizado}) → INSERT")

                                    inicio_calculo = time.time()
                                    valores = self.calculadora.calcular_valores_primarios(linha, tabela='credenciadora')
                                    tempo_calculo = time.time() - inicio_calculo

                                    inicio_insert = time.time()
                                    sucesso = self._inserir_valores_base_unificada(valores, linha)
                                    tempo_insert = time.time() - inicio_insert

                                    if sucesso:
                                        ids_processados.append(linha['id'])
                                        registros_processados += 1
                                    else:
                                        registrar_log('pinbank.cargas_pinbank',
                                                    f"Valores não foram inseridos para NSU={linha['NsuOperacao']}",
                                                    nivel='ERROR')
                                elif var69_atual == descricao_status_normalizado:
                                    # Status não mudou - apenas marca como processado
                                    registrar_log('pinbank.cargas_pinbank',
                                        f"NSU {linha['NsuOperacao']}: SEM MUDANÇA (var69={var69_atual}, status={descricao_status_normalizado}) → SKIP")

                                    ids_processados.append(linha['id'])
                                    registros_processados += 1
                                else:
                                    # Status mudou - atualizar
                                    registrar_log('pinbank.cargas_pinbank',
                                        f"NSU {linha['NsuOperacao']}: MUDANÇA (var69={var69_atual} → status={descricao_status_normalizado}) → UPDATE")

                                    inicio_calculo = time.time()
                                    valores = self.calculadora.calcular_valores_primarios(linha, tabela='credenciadora')
                                    tempo_calculo = time.time() - inicio_calculo

                                    inicio_insert = time.time()
                                    sucesso = self._inserir_ou_atualizar_valores(valores, linha)
                                    tempo_insert = time.time() - inicio_insert

                                    if sucesso:
                                        ids_processados.append(linha['id'])
                                        registros_processados += 1
                                    else:
                                        registrar_log('pinbank.cargas_pinbank',
                                                    f"Valores não foram atualizados para NSU={linha['NsuOperacao']}",
                                                    nivel='ERROR')

                                tempo_total_registro = time.time() - inicio_registro

                                if tempo_total_registro > 1:
                                    registrar_log('pinbank.cargas_pinbank',
                                        f"⚠️ NSU {linha['NsuOperacao']} demorou {tempo_total_registro:.2f}s",
                                        nivel='WARNING')

                            except Exception as e:
                                import traceback
                                erro_detalhado = traceback.format_exc()
                                registrar_log('pinbank.cargas_pinbank',
                                            f"Erro crítico (Base Unificada Credenciadora): NSU={linha.get('NsuOperacao')}, Erro: {str(e)}",
                                            nivel='ERROR')
                                registrar_log('pinbank.cargas_pinbank', f"Traceback: {erro_detalhado}", nivel='ERROR')

                        # Batch update: marcar apenas os IDs específicos processados (dentro da transação)
                        if ids_processados:
                            PinbankExtratoPOS.objects.filter(
                                id__in=ids_processados
                            ).update(processado=1)
                            registrar_log('pinbank.cargas_pinbank', f"✅ {len(ids_processados)} registros marcados como processados")

                    tempo_total_lote = time.time() - inicio_lote
                    registrar_log('pinbank.cargas_pinbank', f"✅ Lote {numero_lote} concluído em {tempo_total_lote:.2f}s ({registros_processados} registros)")
                    lote_atual = []
                    numero_lote += 1

            # Processar último lote se houver registros restantes
            if lote_atual:
                registrar_log('pinbank.cargas_pinbank', f"Processando último lote unificado Credenciadora: {len(lote_atual)} registros")

                ids_processados = []

                with transaction.atomic():
                    for row_lote in lote_atual:
                        linha = dict(zip(colunas, row_lote))

                        try:
                            # Montar info_loja e info_canal
                            linha['info_loja'] = {
                                'id': linha.get('clienteId'),
                                'loja_id': linha.get('clienteId'),
                                'loja': linha.get('razao_social'),
                                'cnpj': linha.get('cnpj'),
                                'canal_id': linha.get('canal_id')
                            }
                            # Usar cache ao invés de query
                            canal_id = linha.get('canal_id')
                            linha['info_canal'] = canais_cache.get(canal_id, {
                                'id': canal_id,
                                'codigo_canal': 0,
                                'codigo_cliente': 0,
                                'key_loja': '',
                                'canal': '',
                                'nome': ''
                            })

                            # Verificar se precisa inserir/atualizar
                            var69_atual = linha.get('var69_atual')
                            descricao_status = linha.get('DescricaoStatusPagamento')
                            descricao_status_normalizado = 'Pago' if descricao_status == 'Pago-M' else descricao_status

                            if var69_atual is None:
                                registrar_log('pinbank.cargas_pinbank',
                                    f"NSU {linha['NsuOperacao']}: NOVO (var69=NULL, status={descricao_status_normalizado}) → INSERT")

                                valores = self.calculadora.calcular_valores_primarios(linha, tabela='credenciadora')
                                sucesso = self._inserir_valores_base_unificada(valores, linha)

                                if sucesso:
                                    ids_processados.append(linha['id'])
                                    registros_processados += 1
                                else:
                                    registrar_log('pinbank.cargas_pinbank',
                                                f"Valores não foram inseridos para NSU={linha['NsuOperacao']}",
                                                nivel='ERROR')
                            elif var69_atual == descricao_status_normalizado:
                                registrar_log('pinbank.cargas_pinbank',
                                    f"NSU {linha['NsuOperacao']}: SEM MUDANÇA (var69={var69_atual}, status={descricao_status_normalizado}) → SKIP")

                                ids_processados.append(linha['id'])
                                registros_processados += 1
                            else:
                                registrar_log('pinbank.cargas_pinbank',
                                    f"NSU {linha['NsuOperacao']}: MUDANÇA (var69={var69_atual} → status={descricao_status_normalizado}) → UPDATE")

                                valores = self.calculadora.calcular_valores_primarios(linha, tabela='credenciadora')
                                sucesso = self._inserir_ou_atualizar_valores(valores, linha)

                                if sucesso:
                                    ids_processados.append(linha['id'])
                                    registros_processados += 1
                                else:
                                    registrar_log('pinbank.cargas_pinbank',
                                                f"Valores não foram atualizados para NSU={linha['NsuOperacao']}",
                                                nivel='ERROR')

                        except Exception as e:
                            import traceback
                            erro_detalhado = traceback.format_exc()
                            registrar_log('pinbank.cargas_pinbank',
                                        f"Erro crítico (Base Unificada Credenciadora): NSU={linha.get('NsuOperacao')}, Erro: {str(e)}",
                                        nivel='ERROR')
                            registrar_log('pinbank.cargas_pinbank', f"Traceback: {erro_detalhado}", nivel='ERROR')

                    # Batch update do último lote (dentro da transação)
                    if ids_processados:
                        PinbankExtratoPOS.objects.filter(
                            id__in=ids_processados
                        ).update(processado=1)
                        registrar_log('pinbank.cargas_pinbank', f"✅ {len(ids_processados)} registros do último lote marcados como processados")

                registrar_log('pinbank.cargas_pinbank', f"Último lote unificado Credenciadora commitado ({len(lote_atual)} registros)")

            registrar_log('pinbank.cargas_pinbank',
                        f"✅ Processamento Base Unificada Credenciadora concluído: {registros_processados} transações processadas")
            return registros_processados

    def atualizar_cancelamentos(self) -> int:
        """
        Atualiza transações que foram canceladas posteriormente
        Compara var68 (status transação) com DescricaoStatus do extrato
        """
        registrar_log('pinbank.cargas_pinbank', "Iniciando atualização de cancelamentos")

        with connection.cursor() as cursor:
            # Buscar transações canceladas que ainda não foram atualizadas
            cursor.execute("""
                SELECT
                    pep.NsuOperacao
                FROM base_transacoes_unificadas btu
                INNER JOIN wallclub.pinbankExtratoPOS pep ON btu.var9 = CAST(pep.NsuOperacao AS CHAR) COLLATE utf8mb4_unicode_ci
                WHERE pep.DataCancelamento != '0001-01-01T00:00:00'
                  AND pep.DescricaoStatus != btu.var68
                  AND btu.tipo_operacao = 'Credenciadora'
                  AND btu.adquirente = 'PINBANK'
            """)

            cancelamentos = cursor.fetchall()
            total = len(cancelamentos)

            if total == 0:
                registrar_log('pinbank.cargas_pinbank', "Nenhum cancelamento pendente de atualização")
                return 0

            registrar_log('pinbank.cargas_pinbank', f"Encontrados {total} cancelamentos para atualizar")

            # Marcar como processado=0 para forçar reprocessamento
            nsus_cancelados = [row[0] for row in cancelamentos]
            PinbankExtratoPOS.objects.filter(NsuOperacao__in=nsus_cancelados).update(processado=0)
            registrar_log('pinbank.cargas_pinbank', 
                        f"✅ {len(nsus_cancelados)} NSUs marcados como processado=0 para reprocessamento")

            atualizados = 0
            for row in cancelamentos:
                nsu = row[0]

                try:
                    # Buscar dados completos do extrato para recalcular
                    cursor.execute("""
                        SELECT
                            pep.id,
                            l.canal_id,
                            pep.codigo_cliente as codigoCliente,
                            cecp.cliente_id as clienteId,
                            cecp.nome as razao_social,
                            cecp.cnpj as cnpj,
                            '' as cpf,
                            '' as nsuAcquirer,
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
                            0 as valor_original,
                            (SELECT SUM(pep2.ValorLiquidoRepasse)
                             FROM wallclub.pinbankExtratoPOS pep2
                             WHERE pep.NsuOperacao = pep2.NsuOperacao
                               AND pep2.DescricaoStatusPagamento in ('Pago','Pago-M')) as vRepasse
                        FROM wallclub.pinbankExtratoPOS pep
                        INNER JOIN wallclub.credenciaisExtratoContaPinbank cecp ON pep.codigo_cliente = cecp.codigo_cliente
                        INNER JOIN wallclub.loja l ON l.id = cecp.cliente_id
                        WHERE pep.NsuOperacao = %s
                        LIMIT 1
                    """, [nsu])

                    linha_dados = cursor.fetchone()
                    if not linha_dados:
                        registrar_log('pinbank.cargas_pinbank',
                                    f"NSU {nsu}: Não encontrado no extrato",
                                    nivel='WARNING')
                        continue

                    # Converter para dict
                    colunas = [
                        'id', 'canal_id', 'codigoCliente', 'clienteId', 'razao_social', 'cnpj', 'cpf',
                        'nsuAcquirer', 'idTerminal', 'SerialNumber', 'Terminal', 'Bandeira', 'TipoCompra',
                        'DadosExtra', 'CpfCnpjComprador', 'NomeRazaoSocialComprador', 'NumeroParcela',
                        'NumeroTotalParcelas', 'DataTransacao', 'DataFuturaPagamento', 'CodAutorizAdquirente',
                        'NsuOperacao', 'NsuOperacaoLoja', 'ValorBruto', 'ValorBrutoParcela', 'ValorLiquidoRepasse',
                        'ValorSplit', 'IdStatus', 'DescricaoStatus', 'IdStatusPagamento', 'DescricaoStatusPagamento',
                        'ValorTaxaAdm', 'ValorTaxaMes', 'NumeroCartao', 'DataCancelamento', 'Submerchant',
                        'valor_original', 'vRepasse'
                    ]
                    linha = dict(zip(colunas, linha_dados))

                    # Montar info_loja e info_canal
                    linha['info_loja'] = {
                        'id': linha.get('clienteId'),
                        'loja': linha.get('razao_social')
                    }
                    linha['info_canal'] = {
                        'id': linha.get('canal_id')
                    }

                    # Recalcular todos os valores
                    valores = self.calculadora.calcular_valores_primarios(linha, tabela='credenciadora')

                    # Atualizar usando INSERT ON DUPLICATE KEY UPDATE
                    sucesso = self._inserir_ou_atualizar_valores(valores, linha)

                    if sucesso:
                        atualizados += 1
                        registrar_log('pinbank.cargas_pinbank',
                                    f"NSU {nsu}: Recalculado com sucesso")
                    else:
                        registrar_log('pinbank.cargas_pinbank',
                                    f"NSU {nsu}: Falha ao recalcular",
                                    nivel='ERROR')

                except Exception as e:
                    registrar_log('pinbank.cargas_pinbank',
                                f"Erro ao recalcular cancelamento NSU {nsu}: {str(e)}",
                                nivel='ERROR')

            registrar_log('pinbank.cargas_pinbank',
                        f"✅ Cancelamentos atualizados: {atualizados}/{total}")
            return atualizados

    def _inserir_valores_base_unificada(self, valores: Dict[str, Any], linha: Dict[str, Any]) -> bool:
        """
        Insere valores na base_transacoes_unificadas
        """
        try:
            # Preparar campos para inserção
            campos = self._preparar_campos_insercao(valores, linha)

            # Inserir via SQL direto
            with connection.cursor() as cursor:
                self._inserir_registro_sql(cursor, campos)

            return True

        except Exception as e:
            import traceback
            erro_detalhado = traceback.format_exc()
            registrar_log('pinbank.cargas_pinbank',
                        f"Erro ao inserir na base unificada: {str(e)}",
                        nivel='ERROR')
            return False

    def _inserir_ou_atualizar_valores(self, valores: Dict[str, Any], linha: Dict[str, Any]) -> bool:
        """
        Insere ou atualiza valores na base_transacoes_unificadas usando INSERT ON DUPLICATE KEY UPDATE
        """
        try:
            # Preparar campos para inserção
            campos = self._preparar_campos_insercao(valores, linha)

            # Inserir/atualizar via SQL direto
            with connection.cursor() as cursor:
                self._inserir_ou_atualizar_registro_sql(cursor, campos)

            return True

        except Exception as e:
            import traceback
            erro_detalhado = traceback.format_exc()
            registrar_log('pinbank.cargas_pinbank',
                        f"Erro ao inserir/atualizar na base unificada: {str(e)}",
                        nivel='ERROR')
            return False

    def _preparar_campos_insercao(self, valores: Dict[str, Any], linha: Dict[str, Any]) -> Dict[str, Any]:
        """Prepara campos para inserção na base_transacoes_unificadas"""
        from datetime import datetime

        campos = {
            'tipo_operacao': 'Credenciadora',
            'adquirente': 'PINBANK'
        }

        # Adicionar todas as variáveis calculadas
        for key, value in valores.items():
            if isinstance(key, int) or key in ['canal_id', 'id_fila_extrato']:
                if key == 'id_fila_extrato':
                    continue  # Não usar mais idFilaExtrato
                elif key == 'canal_id':
                    continue  # Não precisa
                else:
                    campo_nome = f'var{key}'
                    # Extrair valor correto se for um dicionário (arrays do PHP)
                    if isinstance(value, dict):
                        # Mapear chave "0" para campo principal (prioridade)
                        if "0" in value:
                            val = value["0"]
                            campos[campo_nome] = None if (isinstance(val, str) and val.strip() == '') else val
                        else:
                            campos[campo_nome] = None

                        # Mapear chaves adicionais para campos específicos
                        if "A" in value:
                            val_a = value["A"]
                            campos[f'{campo_nome}_A'] = None if (isinstance(val_a, str) and val_a.strip() == '') else val_a
                        if "B" in value:
                            val_b = value["B"]
                            campos[f'{campo_nome}_B'] = None if (isinstance(val_b, str) and val_b.strip() == '') else val_b
                    else:
                        # Converter string vazia em None
                        campos[campo_nome] = None if (isinstance(value, str) and value.strip() == '') else value

        # Processar data_transacao a partir de var0 (data) e var1 (hora)
        if 0 in valores and 1 in valores:
            try:
                data_str = valores[0]  # var0 = data no formato dd/mm/yyyy
                hora_str = valores[1]  # var1 = hora no formato HH:MM:SS

                if data_str and hora_str:
                    # Converter data de dd/mm/yyyy para yyyy-mm-dd
                    data_parts = data_str.split('/')
                    if len(data_parts) == 3:
                        data_formatada = f"{data_parts[2]}-{data_parts[1]}-{data_parts[0]}"
                        datetime_str = f"{data_formatada} {hora_str}"
                        campos['data_transacao'] = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
            except:
                campos['data_transacao'] = None

        # Adicionar campos novos (não existem para Credenciadora, deixar NULL)
        campos['card_number'] = None
        campos['authorization_code'] = None
        campos['amount'] = None
        campos['valor_cashback'] = None

        # Timestamp
        campos['created_at'] = datetime.now()

        return campos

    def _inserir_registro_sql(self, cursor, campos: Dict[str, Any]):
        """Insere registro usando INSERT IGNORE (não atualiza duplicatas)"""
        nsu = campos.get('var9')

        # Filtrar apenas campos válidos
        campos_validos = {k: v for k, v in campos.items() if k not in ['id']}

        # Ordenar campos
        campos_ordenados = sorted(campos_validos.keys())
        valores_ordenados = [campos_validos[campo] for campo in campos_ordenados]

        # Converter datetime para string
        valores_finais = []
        for valor in valores_ordenados:
            if hasattr(valor, 'strftime'):
                valores_finais.append(valor.strftime('%Y-%m-%d %H:%M:%S'))
            else:
                valores_finais.append(valor)

        # INSERT IGNORE: insere apenas se não existir (ignora duplicatas)
        placeholders = ', '.join(['%s'] * len(campos_ordenados))
        sql_insert = f"INSERT IGNORE INTO base_transacoes_unificadas ({', '.join(campos_ordenados)}) VALUES ({placeholders})"
        cursor.execute(sql_insert, valores_finais)

    def _inserir_ou_atualizar_registro_sql(self, cursor, campos: Dict[str, Any]):
        """Insere ou atualiza registro usando INSERT ON DUPLICATE KEY UPDATE"""
        nsu = campos.get('var9')

        # Filtrar apenas campos válidos
        campos_validos = {k: v for k, v in campos.items() if k not in ['id']}

        # Ordenar campos
        campos_ordenados = sorted(campos_validos.keys())
        valores_ordenados = [campos_validos[campo] for campo in campos_ordenados]

        # Converter datetime para string
        valores_finais = []
        for valor in valores_ordenados:
            if hasattr(valor, 'strftime'):
                valores_finais.append(valor.strftime('%Y-%m-%d %H:%M:%S'))
            else:
                valores_finais.append(valor)

        # INSERT ON DUPLICATE KEY UPDATE
        placeholders = ', '.join(['%s'] * len(campos_ordenados))
        update_clause = ', '.join([f'{campo} = VALUES({campo})' for campo in campos_ordenados if campo not in ['var9', 'tipo_operacao']])

        sql_insert = f"""
            INSERT INTO base_transacoes_unificadas ({', '.join(campos_ordenados)})
            VALUES ({placeholders})
            ON DUPLICATE KEY UPDATE {update_clause}
        """
        cursor.execute(sql_insert, valores_finais)
