"""
Serviço para processamento de cargas TEF
ATENÇÃO: Este serviço será descontinuado futuramente
"""

from typing import Dict, Any
from datetime import datetime
from django.db import connection, transaction
from wallclub_core.utilitarios.log_control import registrar_log


class CargaTEFService:
    """Serviço para processamento de cargas TEF - SERÁ DESCONTINUADO"""

    def __init__(self):
        pass

    def buscar_transacoes_tef(self, limite=100, nsu=None):
        """
        Busca transações TEF do Pinbank para processamento

        Args:
            limite: Número máximo de transações para processar (padrão: 100)

        Returns:
            Lista de transações TEF do Pinbank
        """
        try:
            registrar_log('pinbank.cargas_pinbank', f"INÍCIO buscar_transacoes_tef - limite: {limite}" + (f" - NSU: {nsu}" if nsu else ""), nivel='INFO')

            # Filtro por NSU se especificado
            nsu_clause = f"AND pep.NsuOperacao = '{nsu}'" if nsu else ""

            # Query TEF com JOINs corretos para buscar dados reais
            query = f"""
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
                         0 as valor_original
                FROM     wallclub.pinbankExtratoPOS pep,
                         wallclub.credenciaisExtratoContaPinbank cecp,
                         wallclub.loja l
                WHERE    pep.codigo_cliente = cecp.codigo_cliente
                         and l.id = cecp.cliente_id
                         and pep.lido = 0
                         and pep.NsuOperacao not in ( select nsuPinbank from transactiondata)
                         and serialnumber not in ( select terminal from terminais )
                         {nsu_clause}
                ORDER BY pep.id
                LIMIT %s
            """

            with connection.cursor() as cursor:
                registrar_log('pinbank.cargas_pinbank', "Executando query para buscar transações TEF...", nivel='INFO')
                cursor.execute(query, [limite])
                columns = [col[0] for col in cursor.description]
                transacoes = []
                registrar_log('pinbank.cargas_pinbank', "Query executada, processando resultados...", nivel='INFO')

                # Processar linha por linha (streaming) sem carregar tudo em memória
                transacoes = []
                contador = 0
                while True:
                    row = cursor.fetchone()
                    if row is None:
                        break

                    transacao = dict(zip(columns, row))
                    transacoes.append(transacao)
                    contador += 1

                    if contador <= 5:  # Log apenas as primeiras 5 para não poluir
                        registrar_log('pinbank.cargas_pinbank', f"Transação {contador}: ID={transacao.get('id')}, NSU={transacao.get('NsuOperacao')}, DataTransacao={transacao.get('DataTransacao')}", nivel='INFO')
                        registrar_log('pinbank.cargas_pinbank', f"DEBUG - Todas as chaves da query: {list(transacao.keys())}", nivel='DEBUG')

                registrar_log('pinbank.cargas_pinbank', f"Streaming processou {len(transacoes)} linhas", nivel='INFO')

                registrar_log('pinbank.cargas_pinbank', f"FIM buscar_transacoes_tef - Encontradas {len(transacoes)} transações TEF do Pinbank", nivel='INFO')
            return transacoes

        except Exception as e:
            registrar_log('pinbank.cargas_pinbank', f"Erro ao buscar transações TEF: {str(e)}", nivel='ERROR')
            return []

    def processar_carga_tef(self, limite: int = None, nsu: str = None) -> Dict[str, Any]:
        """
        Processa carga completa de transações TEF
        Integra busca + cálculo + inserção na base de gestão

        Args:
            limite: Número máximo de transações para processar (padrão: 100)

        Returns:
            Dict com resultado do processamento
        """
        try:
            registrar_log('pinbank.cargas_pinbank', f"INÍCIO processar_carga_tef - limite: {limite}", nivel='INFO')
            from parametros_wallclub.calculadora_tef import CalculadoraTEF
            registrar_log('pinbank.cargas_pinbank', "CalculadoraTEF importada com sucesso", nivel='INFO')

            # Buscar transações TEF
            registrar_log('pinbank.cargas_pinbank', "Iniciando busca de transações TEF...", nivel='INFO')
            transacoes_tef = self.buscar_transacoes_tef(limite, nsu)
            registrar_log('pinbank.cargas_pinbank', f"Busca concluída - {len(transacoes_tef)} transações encontradas", nivel='INFO')

            if not transacoes_tef:
                registrar_log('pinbank.cargas_pinbank', "NENHUMA transação TEF encontrada - finalizando", nivel='INFO')
                return {
                    'sucesso': True,
                    'mensagem': 'Nenhuma transação TEF encontrada para o período',
                    'processadas': 0
                }

            # Inicializar calculadora TEF
            registrar_log('pinbank.cargas_pinbank', "Inicializando CalculadoraTEF...", nivel='INFO')
            calculadora = CalculadoraTEF()
            registrar_log('pinbank.cargas_pinbank', "CalculadoraTEF inicializada com sucesso", nivel='INFO')

            # Processar e inserir em streaming (transação por transação)
            registrar_log('pinbank.cargas_pinbank', f"Iniciando processamento STREAMING de {len(transacoes_tef)} transações TEF...", nivel='INFO')
            registros_inseridos = self._processar_inserir_streaming_tef(calculadora, transacoes_tef)
            registrar_log('pinbank.cargas_pinbank', f"Processamento STREAMING concluído - {registros_inseridos} registros inseridos", nivel='INFO')

            resultado = {
                'sucesso': True,
                'mensagem': f'Carga TEF processada com sucesso',
                'encontradas': len(transacoes_tef),
                'processadas': registros_inseridos,
                'inseridas': registros_inseridos
            }

            registrar_log('pinbank.cargas_pinbank', f"FIM processar_carga_tef - Carga TEF concluída: {resultado}", nivel='INFO')
            return resultado

        except Exception as e:
            registrar_log('pinbank.cargas_pinbank', f"Erro no processamento da carga TEF: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': f'Erro no processamento: {str(e)}',
                'processadas': 0
            }

    def _processar_inserir_streaming_tef(self, calculadora, transacoes_tef):
        """
        Processa e insere transações TEF uma por vez (streaming)
        Evita carregar tudo em memória antes de começar a inserir

        Args:
            calculadora: Instância da CalculadoraTEF
            transacoes_tef: Lista de transações para processar

        Returns:
            Número de registros inseridos
        """
        try:
            from pinbank.models import BaseTransacoesGestao

            registros_inseridos = 0
            total_transacoes = len(transacoes_tef)

            registrar_log('pinbank.cargas_pinbank', f"Iniciando processamento STREAMING de {total_transacoes} transações TEF")

            # Processar em lotes de 100 para commits
            BATCH_SIZE = 100
            lote_atual = []

            for i, transacao_tef in enumerate(transacoes_tef):
                try:
                    # Preservar DataTransacao original antes do processamento
                    data_transacao_original = transacao_tef.get('DataTransacao')

                    # Processar transação individual
                    transacao_processada = calculadora.calcular_valores_tef(transacao_tef)

                    # Restaurar DataTransacao original (caso tenha sido perdido)
                    if data_transacao_original and 'DataTransacao' not in transacao_processada:
                        transacao_processada['DataTransacao'] = data_transacao_original

                    # Adicionar ao lote atual
                    lote_atual.append(transacao_processada)

                    # Quando completar lote de 100, inserir no banco
                    if len(lote_atual) >= BATCH_SIZE or i == total_transacoes - 1:
                        numero_lote = (i // BATCH_SIZE) + 1
                        registrar_log('pinbank.cargas_pinbank', f"🔄 Inserindo lote TEF {numero_lote}: {len(lote_atual)} registros")

                        with transaction.atomic():
                            with connection.cursor() as cursor:
                                for transacao in lote_atual:
                                    # Preparar campos para inserção
                                    campos = {
                                        'idFilaExtrato': transacao.get('id'),
                                        'banco': 'PIN-TEF',
                                        'tipo_operacao': 'Credenciadora'
                                    }

                                    # Mapear todos os valores calculados (var0 até var130)
                                    for j in range(131):
                                        campo = f'var{j}'
                                        if campo in transacao:
                                            campos[campo] = transacao[campo]

                                    # Popular data_transacao, var0 e var1
                                    try:
                                        data_transacao_str = transacao.get('DataTransacao') or transacao.get('datatransacao')

                                        if data_transacao_str and str(data_transacao_str).strip():
                                            data_str = str(data_transacao_str).strip()

                                            # Tentar diferentes formatos de data
                                            dt = None
                                            formatos = [
                                                '%Y-%m-%dT%H:%M:%S.%f',  # Com milissegundos: 2025-03-18T08:39:51.242
                                                '%Y-%m-%dT%H:%M:%S',     # Sem milissegundos: 2025-03-18T08:39:51
                                                '%Y-%m-%d %H:%M:%S'      # Formato alternativo
                                            ]

                                            for formato in formatos:
                                                try:
                                                    dt = datetime.strptime(data_str, formato)
                                                    break
                                                except ValueError:
                                                    continue

                                            if dt:
                                                campos['data_transacao'] = dt
                                                campos['var0'] = dt.strftime('%d/%m/%Y')
                                                campos['var1'] = dt.strftime('%H:%M:%S')
                                            else:
                                                registrar_log('pinbank.cargas_pinbank', f"Formato de DataTransacao não reconhecido: {data_str}")
                                                campos['data_transacao'] = None
                                                campos['var0'] = ''
                                                campos['var1'] = ''
                                        else:
                                            campos['data_transacao'] = None
                                            campos['var0'] = ''
                                            campos['var1'] = ''

                                    except Exception as e:
                                        registrar_log('pinbank.cargas_pinbank', f"Erro ao processar DataTransacao TEF: {str(e)}", nivel='ERROR')
                                        campos['data_transacao'] = None
                                        campos['var0'] = ''
                                        campos['var1'] = ''

                                    # Adicionar created_at
                                    import os
                                    os.environ['TZ'] = 'America/Sao_Paulo'
                                    campos['created_at'] = datetime.now()

                                    # Inserir usando SQL direto
                                    self._inserir_registro_tef_sql(cursor, campos)

                                    # Marcar como lido na pinbankExtratoPOS
                                    cursor.execute(
                                        "UPDATE wallclub.pinbankExtratoPOS SET lido = 1 WHERE id = %s",
                                        [transacao.get('id')]
                                    )

                                    registros_inseridos += 1

                        # Commit manual forçado
                        connection.commit()
                        registrar_log('pinbank.cargas_pinbank', f"✅ COMMIT - Lote TEF {numero_lote} inserido ({len(lote_atual)} registros)")

                        # Limpar lote atual
                        lote_atual = []

                except Exception as e:
                    registrar_log('pinbank.cargas_pinbank', f"ERRO ao processar transação TEF {i+1}: {str(e)}", nivel='ERROR')
                    continue  # Pular transação com erro

            registrar_log('pinbank.cargas_pinbank', f"STREAMING TEF finalizado - {registros_inseridos} registros inseridos")
            return registros_inseridos

        except Exception as e:
            registrar_log('pinbank.cargas_pinbank', f"ERRO no processamento STREAMING TEF: {str(e)}", nivel='ERROR')
            return 0

    def _inserir_registro_tef_sql(self, cursor, campos):
        """
        Insere registro TEF na base de gestão usando SQL direto

        Args:
            cursor: Cursor do banco de dados
            campos: Dicionário com campos e valores para inserir
        """
        try:
            # Verificar estrutura da tabela
            cursor.execute("DESCRIBE wallclub.baseTransacoesGestao")
            colunas_tabela = [row[0] for row in cursor.fetchall()]

            # Filtrar apenas campos que existem na tabela
            campos_validos = {}
            for campo, valor in campos.items():
                if campo in colunas_tabela:
                    campos_validos[campo] = valor

            # Adicionar campos faltando com valores padrão
            campos_faltando = set(colunas_tabela) - set(campos_validos.keys()) - {'id'}  # Excluir id auto_increment
            for campo_faltando in campos_faltando:
                if campo_faltando.endswith('_A') or campo_faltando.endswith('_B'):
                    campos_validos[campo_faltando] = 0.0
                elif campo_faltando == 'updated_at':
                    # updated_at deve ser NULL na criação inicial - usar datetime atual
                    campos_validos[campo_faltando] = datetime.now()
                elif campo_faltando.startswith('var') and campo_faltando[3:].isdigit():
                    # Campos var* (var0, var1, var101, etc.) são decimais - usar 0.0
                    campos_validos[campo_faltando] = 0.0
                else:
                    campos_validos[campo_faltando] = ''

            # Ordenar campos para garantir consistência
            campos_ordenados = sorted(campos_validos.keys())
            valores_ordenados = [campos_validos[campo] for campo in campos_ordenados]

            # Construir SQL de INSERT com ON DUPLICATE KEY UPDATE
            campos_sql = ', '.join(campos_ordenados)
            placeholders = ', '.join(['%s'] * len(campos_ordenados))

            # Construir UPDATE clause (excluir created_at e id)
            update_clauses = []
            for campo in campos_ordenados:
                if campo not in ['created_at', 'id']:  # Preservar created_at original
                    update_clauses.append(f"{campo} = VALUES({campo})")

            # Adicionar updated_at = NOW() no UPDATE
            update_clauses.append("updated_at = NOW()")

            sql = f"""
                INSERT INTO wallclub.baseTransacoesGestao ({campos_sql})
                VALUES ({placeholders})
                ON DUPLICATE KEY UPDATE
                {', '.join(update_clauses)}
            """

            cursor.execute(sql, valores_ordenados)
            registrar_log('pinbank.cargas_pinbank', "Registro TEF inserido com sucesso", nivel='INFO')

        except Exception as e:
            registrar_log('pinbank.cargas_pinbank', f"Erro ao inserir registro TEF via SQL: {str(e)}", nivel='ERROR')
            raise

    def _marcar_transacao_como_lida(self, transacao_id: int):
        """
        Marca transação como lida (lido = 1) na pinbankExtratoPOS

        Args:
            transacao_id: ID da transação na pinbankExtratoPOS
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE wallclub.pinbankExtratoPOS SET lido = 1 WHERE id = %s",
                    [transacao_id]
                )
                registrar_log('pinbank.cargas_pinbank', f"Transação TEF {transacao_id} marcada como lida", nivel='INFO')

        except Exception as e:
            registrar_log('pinbank.cargas_pinbank', f"Erro ao marcar transação {transacao_id} como lida: {str(e)}", nivel='ERROR')
