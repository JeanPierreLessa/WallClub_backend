"""
Serviço para carga da Base Unificada POS (Wallet)
Processa transações da tabela transactiondata_pos (Wallet)
Insere em base_transacoes_unificadas (1 linha por NSU, sem duplicação de parcelas)
Filtro: Apenas transações de outubro/2025 em diante
MIGRADO: 22/12/2025 - Consulta transactiondata_pos ao invés de transactiondata
"""

from typing import Dict, Any
from django.db import connection, transaction
from .models import PinbankExtratoPOS
from wallclub_core.utilitarios.log_control import registrar_log


class CargaBaseUnificadaPOSService:
    """
    Serviço para carga da base unificada POS (Wallet)
    Regra: 1 linha por transação (NSU único), não por parcela
    Filtro: Apenas transações >= 2025-10-01
    """

    def __init__(self):
        from parametros_wallclub.calculadora_base_unificada import CalculadoraBaseUnificada
        self.calculadora = CalculadoraBaseUnificada()

    def carregar_valores_primarios(self, limite: int = None, nsu: str = None, worker_id: int = None) -> int:
        """
        Rotina principal de carga de variáveis primárias
        Processa registros com processado = 0 e data >= 2025-10-01
        Agrupa por NSU (1 linha por transação)

        Args:
            limite: Limite de registros
            nsu: NSU específico
            worker_id: ID do worker (0-9) para processamento paralelo
        """
        registrar_log('pinbank.cargas_pinbank', f"Iniciando carga de valores primários - Base Unificada (worker_id={worker_id})")

        limit_clause = f"LIMIT {limite}" if limite else ""
        nsu_clause = f"AND pep.NsuOperacao = '{nsu}'" if nsu else ""
        worker_clause = f"AND MOD(CAST(pep.NsuOperacao AS UNSIGNED), 2) = {worker_id}" if worker_id is not None else ""

        registrar_log('pinbank.cargas_pinbank', f"Executando query com limite={limite}, nsu={nsu}, worker_id={worker_id}")

        # Debug: contar registros antes da query
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*)
                FROM wallclub.pinbankExtratoPOS pep
                INNER JOIN wallclub.transactiondata_pos t ON pep.NsuOperacao = t.nsu_gateway AND t.gateway = 'PINBANK'
                WHERE pep.processado = 0
            """)
            total_antes = cursor.fetchone()[0]
            registrar_log('pinbank.cargas_pinbank', f"DEBUG: {total_antes} registros com processado=0 e transactiondata_pos")

        with connection.cursor() as cursor:
            # Cache de canais e lojas
            from wallclub_core.estr_organizacional.canal import Canal
            from wallclub_core.estr_organizacional.loja import Loja

            canais_cache = {}
            for canal in Canal.objects.all():
                canais_cache[canal.id] = {
                    'id': canal.id,
                    'codigo_canal': int(canal.canal) if canal.canal and canal.canal.isdigit() else 0,
                    'codigo_cliente': int(canal.codigo_cliente) if canal.codigo_cliente and canal.codigo_cliente.isdigit() else 0,
                    'key_loja': canal.keyvalue or '',
                    'canal': canal.nome or '',
                    'nome': canal.nome or ''
                }

            lojas_cache = {}
            for loja in Loja.objects.all():
                lojas_cache[loja.id] = {
                    'id': loja.id,
                    'loja_id': loja.id,
                    'loja': loja.razao_social or '',
                    'cnpj': loja.cnpj or '',
                    'canal_id': loja.canal_id
                }

            registrar_log('pinbank.cargas_pinbank', f"Cache carregado: {len(canais_cache)} canais, {len(lojas_cache)} lojas")

            # Query simplificada - pega apenas 1 registro por NSU (menor id)
            cursor.execute(f"""
                SELECT   pep.id,
                         pep.codigo_cliente,
                         l.id as loja_id,
                         l.canal_id,
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
                         t.cpf,
                         t.nsuAcquirer,
                         t.valor_original,
                         t.cardNumber,
                         t.authorizationCode,
                         t.amount,
                         t.valor_cashback,
                         ( SELECT  SUM(pep2.ValorLiquidoRepasse)
                           FROM   wallclub.pinbankExtratoPOS pep2
                           WHERE  pep.NsuOperacao = pep2.NsuOperacao
                                  AND pep2.DescricaoStatusPagamento in ('Pago','Pago-M'))   vRepasse,
                         pe.var44 f44,
                         pe.var45 f45,
                         pe.var58 f58,
                         pe.var59 f59,
                         pe.var66 f66,
                         pe.var71 f71,
                         pe.var100 f100,
                         pe.var111 f111,
                         pe.var112 f112
                FROM     wallclub.pinbankExtratoPOS pep
                INNER JOIN wallclub.transactiondata_pos t ON pep.NsuOperacao = t.nsu_gateway AND t.gateway = 'PINBANK'
                INNER JOIN wallclub.terminais term ON pep.SerialNumber = term.terminal
                         AND pep.DataTransacao >= term.inicio
                         AND (term.fim IS NULL OR pep.DataTransacao < term.fim)
                INNER JOIN wallclub.loja l ON l.id = term.loja_id
                LEFT JOIN wallclub.pagamentos_efetuados pe ON pe.nsu = t.nsu_gateway
                WHERE    pep.processado = 0
                         AND pep.id IN (
                             SELECT MIN(pep2.id)
                             FROM wallclub.pinbankExtratoPOS pep2
                             INNER JOIN wallclub.transactiondata_pos t2 ON pep2.NsuOperacao = t2.nsu_gateway AND t2.gateway = 'PINBANK'
                             INNER JOIN wallclub.terminais term2 ON pep2.SerialNumber = term2.terminal
                                  AND pep2.DataTransacao >= term2.inicio
                                  AND (term2.fim IS NULL OR pep2.DataTransacao < term2.fim)
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
                    registrar_log('pinbank.cargas_pinbank', f"Processando lote unificado {numero_lote}: {len(lote_atual)} registros")

                    with transaction.atomic():
                        for row_lote in lote_atual:
                            linha = dict(zip(colunas, row_lote))

                            try:
                                # Montar info_loja e info_canal
                                loja_id = linha.get('loja_id')
                                canal_id = linha.get('canal_id')

                                info_loja = lojas_cache.get(loja_id)
                                if not info_loja:
                                    registrar_log('pinbank.cargas_pinbank',
                                                f"⚠️ Loja ID {loja_id} não encontrada no cache - NSU {linha.get('NsuOperacao')}",
                                                nivel='WARNING')
                                    continue

                                info_canal = canais_cache.get(canal_id)
                                if not info_canal:
                                    registrar_log('pinbank.cargas_pinbank',
                                                f"⚠️ Canal ID {canal_id} não encontrado no cache - NSU {linha.get('NsuOperacao')}",
                                                nivel='WARNING')
                                    continue

                                # Calcular valores primários
                                valores = self.calculadora.calcular_valores_primarios(
                                    dados_linha=linha,
                                    tabela='transactiondata_pos',
                                    info_loja=info_loja,
                                    info_canal=info_canal
                                )

                                # Inserir na base unificada (já marca como processado internamente)
                                sucesso = self._inserir_valores_base_unificada(valores, linha)

                                if sucesso:
                                    registros_processados += 1

                            except Exception as e:
                                import traceback
                                erro_detalhado = traceback.format_exc()
                                registrar_log('pinbank.cargas_pinbank',
                                            f"Erro crítico (Base Unificada): NSU={linha.get('NsuOperacao')}, Erro: {str(e)}",
                                            nivel='ERROR')
                                registrar_log('pinbank.cargas_pinbank', f"Traceback: {erro_detalhado}", nivel='ERROR')

                    registrar_log('pinbank.cargas_pinbank',
                                f"Lote unificado {numero_lote} commitado ({len(lote_atual)} registros)")
                    lote_atual = []
                    numero_lote += 1

            # Processar último lote se houver registros restantes
            if lote_atual:
                registrar_log('pinbank.cargas_pinbank', f"Processando último lote unificado: {len(lote_atual)} registros")

                with transaction.atomic():
                    for row_lote in lote_atual:
                        linha = dict(zip(colunas, row_lote))

                        try:
                            # Montar info_loja e info_canal
                            loja_id = linha.get('loja_id')
                            canal_id = linha.get('canal_id')

                            info_loja = lojas_cache.get(loja_id)
                            if not info_loja:
                                registrar_log('pinbank.cargas_pinbank',
                                            f"⚠️ Loja ID {loja_id} não encontrada no cache",
                                            nivel='WARNING')
                                continue

                            info_canal = canais_cache.get(canal_id)
                            if not info_canal:
                                registrar_log('pinbank.cargas_pinbank',
                                            f"⚠️ Canal ID {canal_id} não encontrado no cache",
                                            nivel='WARNING')
                                continue

                            valores = self.calculadora.calcular_valores_primarios(
                                dados_linha=linha,
                                tabela='transactiondata_pos',
                                info_loja=info_loja,
                                info_canal=info_canal
                            )
                            sucesso = self._inserir_valores_base_unificada(valores, linha)

                            if sucesso:
                                registros_processados += 1
                            else:
                                registrar_log('pinbank.cargas_pinbank',
                                            f"Valores não foram inseridos para NSU={linha['NsuOperacao']}",
                                            nivel='ERROR')

                        except Exception as e:
                            import traceback
                            erro_detalhado = traceback.format_exc()
                            registrar_log('pinbank.cargas_pinbank',
                                        f"Erro crítico (Base Unificada): NSU={linha.get('NsuOperacao')}, Erro: {str(e)}",
                                        nivel='ERROR')
                            registrar_log('pinbank.cargas_pinbank', f"Traceback: {erro_detalhado}", nivel='ERROR')

                registrar_log('pinbank.cargas_pinbank', f"Último lote unificado commitado ({len(lote_atual)} registros)")

            registrar_log('pinbank.cargas_pinbank',
                        f"✅ Processamento Base Unificada concluído: {registros_processados} transações processadas")
            return registros_processados

    def _inserir_valores_base_unificada(self, valores: Dict[str, Any], linha: Dict[str, Any]) -> bool:
        """
        Insere valores na base_transacoes_unificadas
        Popula campos novos: card_number, authorization_code, amount, valor_cashback
        Marca registro como processado no mesmo cursor para garantir consistência
        """
        try:
            # Preparar campos para inserção
            campos = self._preparar_campos_insercao(valores, linha)

            # Inserir via SQL direto e marcar como processado no mesmo cursor
            with connection.cursor() as cursor:
                self._inserir_registro_sql(cursor, campos)
                # Marcar TODOS os registros com o mesmo NSU como processados
                nsu = linha.get('NsuOperacao')
                cursor.execute(
                    "UPDATE wallclub.pinbankExtratoPOS SET processado = 1 WHERE NsuOperacao = %s",
                    [nsu]
                )

            return True

        except Exception as e:
            import traceback
            erro_detalhado = traceback.format_exc()
            registrar_log('pinbank.cargas_pinbank',
                        f"Erro ao inserir na base unificada: {str(e)}",
                        nivel='ERROR')
            return False

    def _preparar_campos_insercao(self, valores: Dict[str, Any], linha: Dict[str, Any]) -> Dict[str, Any]:
        """Prepara campos para inserção na base_transacoes_unificadas"""
        from datetime import datetime

        campos = {
            'tipo_operacao': 'Wallet',
            'adquirente': 'PINBANK',
            'origem_transacao': 'POS',
            'data_transacao': None
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

        # Adicionar campos novos (gaps identificados)
        campos['card_number'] = linha.get('cardNumber')
        campos['authorization_code'] = linha.get('authorizationCode')
        campos['amount'] = linha.get('amount')
        campos['valor_cashback'] = linha.get('valor_cashback', 0)

        # Timestamp
        campos['created_at'] = datetime.now()

        return campos

    def _inserir_registro_sql(self, cursor, campos: Dict[str, Any]):
        """Insere ou atualiza registro - só UPDATE se status ou pagamento mudou"""
        nsu = campos.get('var9')

        # Buscar var69 (status), var70 (cancelamento), var44 (valor pago) e var45 (data pagamento)
        cursor.execute("""
            SELECT var69, var70, var44, var45
            FROM wallclub.base_transacoes_unificadas
            WHERE var9 = %s AND tipo_operacao = 'Wallet'
        """, [nsu])

        registro_atual = cursor.fetchone()

        # Verificar estrutura da tabela
        cursor.execute("DESCRIBE wallclub.base_transacoes_unificadas")
        colunas_tabela = [row[0] for row in cursor.fetchall()]

        # Filtrar apenas campos que existem na tabela
        campos_validos = {k: v for k, v in campos.items() if k in colunas_tabela}

        if registro_atual:
            var69_atual, var70_atual, var44_atual, var45_atual = registro_atual
            var69_novo = campos.get('var69')
            var70_novo = campos.get('var70')
            var44_novo = campos.get('var44')
            var45_novo = campos.get('var45')

            # Só recalcular se:
            # 1. Status pagamento mudou
            # 2. Data cancelamento foi preenchida
            # 3. Valor ou data de pagamento mudou (novo pagamento em pagamentos_efetuados)
            status_mudou = str(var69_atual or '') != str(var69_novo or '')
            cancelamento_novo = (not var70_atual) and var70_novo
            pagamento_mudou = (str(var44_atual or '') != str(var44_novo or '')) or (str(var45_atual or '') != str(var45_novo or ''))

            if status_mudou or cancelamento_novo or pagamento_mudou:
                # UPDATE completo
                set_clause = ', '.join([f'`{col}` = %s' for col in campos_validos.keys() if col != 'var9'])
                valores = [v for k, v in campos_validos.items() if k != 'var9']
                valores.append(nsu)

                sql = f"UPDATE wallclub.base_transacoes_unificadas SET {set_clause} WHERE var9 = %s AND tipo_operacao = 'Wallet'"
                cursor.execute(sql, valores)

                # Registrar auditoria
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
                """, [nsu, json.dumps(motivo), 1])
        else:
            # INSERT
            colunas = ', '.join([f'`{col}`' for col in campos_validos.keys()])
            placeholders = ', '.join(['%s'] * len(campos_validos))
            valores = list(campos_validos.values())

            sql = f"INSERT INTO wallclub.base_transacoes_unificadas ({colunas}) VALUES ({placeholders})"
            cursor.execute(sql, valores)
            registrar_log('pinbank.cargas_pinbank', f"✅ Registro inserido na base unificada - NSU: {nsu}")
