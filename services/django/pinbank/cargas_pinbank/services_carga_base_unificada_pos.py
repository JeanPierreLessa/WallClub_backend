"""
Serviço para carga da Base Unificada POS (Wallet)
Processa transações da tabela transactiondata (Wallet)
Insere em base_transacoes_unificadas (1 linha por NSU, sem duplicação de parcelas)
Filtro: Apenas transações de outubro/2025 em diante
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
        from parametros_wallclub.calculadora_base_gestao import CalculadoraBaseGestao
        self.calculadora = CalculadoraBaseGestao()

    def carregar_valores_primarios(self, limite: int = None, nsu: str = None) -> int:
        """
        Rotina principal de carga de variáveis primárias
        Processa registros com processado = 0 e data >= 2025-10-01
        Agrupa por NSU (1 linha por transação)
        """
        print(f"[DEBUG] Iniciando carga de valores primários - Base Unificada")
        registrar_log('pinbank.cargas_pinbank', "Iniciando carga de valores primários - Base Unificada")

        limit_clause = f"LIMIT {limite}" if limite else ""
        nsu_clause = f"AND pep.NsuOperacao = '{nsu}'" if nsu else ""
        
        print(f"[DEBUG] Executando query com limite={limite}, nsu={nsu}")
        registrar_log('pinbank.cargas_pinbank', f"Executando query com limite={limite}, nsu={nsu}")

        with connection.cursor() as cursor:
            # Query simplificada - pega apenas 1 registro por NSU (menor id)
            cursor.execute(f"""
                SELECT   pep.id,
                         pep.codigo_cliente,
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
                INNER JOIN wallclub.transactiondata t ON pep.NsuOperacao = t.nsuPinbank
                LEFT JOIN wallclub.pagamentos_efetuados pe ON pe.nsu = t.nsuPinbank
                WHERE    pep.processado = 0
                         AND pep.DataTransacao >= '2025-10-01'
                         AND pep.id IN (
                             SELECT MIN(pep2.id)
                             FROM wallclub.pinbankExtratoPOS pep2
                             WHERE pep2.processado = 0
                             AND pep2.DataTransacao >= '2025-10-01'
                             GROUP BY pep2.NsuOperacao
                         )
                         {nsu_clause}
                ORDER BY pep.id
                {limit_clause}
            """)

            print(f"[DEBUG] Query executada com sucesso")
            registrar_log('pinbank.cargas_pinbank', "Query executada com sucesso")
            
            colunas = [desc[0] for desc in cursor.description]
            registros_processados = 0
            
            print(f"[DEBUG] Iniciando processamento de registros em lotes de 100")
            registrar_log('pinbank.cargas_pinbank', f"Iniciando processamento de registros em lotes de 100")

            # Processar em lotes de 100 registros
            BATCH_SIZE = 100
            lote_atual = []
            numero_lote = 1

            # Processar linha por linha (streaming)
            while True:
                row = cursor.fetchone()
                if row is None:
                    print(f"[DEBUG] Fim do cursor - nenhum registro encontrado")
                    break

                print(f"[DEBUG] Registro encontrado: {row[0] if row else 'None'}")
                lote_atual.append(row)

                # Quando completar um lote de 100, processar
                if len(lote_atual) >= BATCH_SIZE:
                    registrar_log('pinbank.cargas_pinbank', f"Processando lote unificado {numero_lote}: {len(lote_atual)} registros")

                    with transaction.atomic():
                        for row_lote in lote_atual:
                            linha = dict(zip(colunas, row_lote))

                            try:
                                print(f"[DEBUG] Processando NSU: {linha.get('NsuOperacao')}")
                                # Calcular valores primários
                                valores = self.calculadora.calcular_valores_primarios(linha, tabela='transactiondata')
                                print(f"[DEBUG] Valores calculados com sucesso")

                                # Inserir na base unificada
                                sucesso = self._inserir_valores_base_unificada(valores, linha)
                                print(f"[DEBUG] Inserção retornou: {sucesso}")

                                if sucesso:
                                    # Marcar TODAS as parcelas do NSU como processadas
                                    PinbankExtratoPOS.objects.filter(
                                        NsuOperacao=linha['NsuOperacao']
                                    ).update(processado=1)
                                    registros_processados += 1
                                else:
                                    registrar_log('pinbank.cargas_pinbank',
                                                f"Valores não foram inseridos para NSU={linha['NsuOperacao']}",
                                                nivel='ERROR')

                            except Exception as e:
                                import traceback
                                erro_detalhado = traceback.format_exc()
                                print(f"[DEBUG] ERRO: {str(e)}")
                                print(f"[DEBUG] Traceback: {erro_detalhado}")
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
                print(f"[DEBUG] Processando último lote: {len(lote_atual)} registros")
                registrar_log('pinbank.cargas_pinbank', f"Processando último lote unificado: {len(lote_atual)} registros")

                with transaction.atomic():
                    for row_lote in lote_atual:
                        linha = dict(zip(colunas, row_lote))

                        try:
                            print(f"[DEBUG] Último lote - Processando NSU: {linha.get('NsuOperacao')}")
                            valores = self.calculadora.calcular_valores_primarios(linha, tabela='transactiondata')
                            print(f"[DEBUG] Último lote - Valores calculados")
                            sucesso = self._inserir_valores_base_unificada(valores, linha)
                            print(f"[DEBUG] Último lote - Inserção retornou: {sucesso}")

                            if sucesso:
                                PinbankExtratoPOS.objects.filter(
                                    NsuOperacao=linha['NsuOperacao']
                                ).update(processado=1)
                                registros_processados += 1
                                print(f"[DEBUG] Último lote - Registro processado com sucesso")
                            else:
                                print(f"[DEBUG] Último lote - Inserção falhou")
                                registrar_log('pinbank.cargas_pinbank',
                                            f"Valores não foram inseridos para NSU={linha['NsuOperacao']}",
                                            nivel='ERROR')

                        except Exception as e:
                            import traceback
                            erro_detalhado = traceback.format_exc()
                            print(f"[DEBUG] Último lote - ERRO: {str(e)}")
                            print(f"[DEBUG] Último lote - Traceback: {erro_detalhado}")
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
        """
        try:
            # Preparar campos para inserção
            campos = self._preparar_campos_insercao(valores, linha)

            # Inserir via SQL direto
            with connection.cursor() as cursor:
                self._inserir_registro_sql(cursor, campos)

            return True

        except Exception as e:
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
                    campos[f'var{key}'] = value

        # Processar data_transacao
        if 'DataTransacao' in linha and linha['DataTransacao']:
            try:
                if isinstance(linha['DataTransacao'], str):
                    campos['data_transacao'] = datetime.strptime(linha['DataTransacao'], '%Y-%m-%d %H:%M:%S')
                else:
                    campos['data_transacao'] = linha['DataTransacao']
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
        """Insere novo registro usando SQL direto"""
        # Verificar estrutura da tabela
        cursor.execute("DESCRIBE wallclub.base_transacoes_unificadas")
        colunas_tabela = [row[0] for row in cursor.fetchall()]

        # Filtrar apenas campos que existem na tabela
        campos_validos = {k: v for k, v in campos.items() if k in colunas_tabela}

        # Construir INSERT
        colunas = ', '.join([f'`{col}`' for col in campos_validos.keys()])
        placeholders = ', '.join(['%s'] * len(campos_validos))
        valores = list(campos_validos.values())

        sql = f"INSERT INTO wallclub.base_transacoes_unificadas ({colunas}) VALUES ({placeholders})"

        cursor.execute(sql, valores)
        registrar_log('pinbank.cargas_pinbank', f"✅ Registro inserido na base unificada - NSU: {campos.get('var9')}")
