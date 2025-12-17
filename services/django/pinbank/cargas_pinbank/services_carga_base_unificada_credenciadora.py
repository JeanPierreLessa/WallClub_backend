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

    def carregar_valores_primarios(self, limite: int = None, nsu: str = None) -> int:
        """
        Rotina principal de carga de variáveis primárias
        Processa registros com processado = 0
        Agrupa por NSU (1 linha por transação)
        """
        registrar_log('pinbank.cargas_pinbank', "Iniciando carga de valores primários - Base Unificada Credenciadora")

        limit_clause = f"LIMIT {limite}" if limite else ""
        nsu_clause = f"AND pep.NsuOperacao = '{nsu}'" if nsu else ""

        registrar_log('pinbank.cargas_pinbank', f"Executando query com limite={limite}, nsu={nsu}")

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
                                  AND pep2.DescricaoStatusPagamento in ('Pago','Pago-M'))   vRepasse
                FROM     wallclub.pinbankExtratoPOS pep,
                         wallclub.credenciaisExtratoContaPinbank cecp,
                         wallclub.loja l
                WHERE    pep.codigo_cliente = cecp.codigo_cliente
                         and l.id = cecp.cliente_id
                         and pep.processado = 0
                         and pep.DataTransacao >= '2025-10-01'
                         and pep.NsuOperacao not in ( select nsuPinbank from transactiondata)
                         and pep.NsuOperacaoLoja not in ( select nsu from checkout_transactions where nsu is not null )
                         and serialnumber not in ( select terminal from terminais )
                         AND pep.id IN (
                             SELECT MIN(pep2.id)
                             FROM wallclub.pinbankExtratoPOS pep2,
                                  wallclub.credenciaisExtratoContaPinbank cecp2,
                                  wallclub.loja l2
                             WHERE pep2.codigo_cliente = cecp2.codigo_cliente
                             AND l2.id = cecp2.cliente_id
                             AND pep2.processado = 0
                             AND pep2.DataTransacao >= '2025-10-01'
                             AND pep2.NsuOperacao NOT IN (SELECT nsuPinbank FROM transactiondata)
                             AND pep2.NsuOperacaoLoja NOT IN (SELECT nsu FROM checkout_transactions WHERE nsu IS NOT NULL)
                             AND pep2.serialnumber NOT IN (SELECT terminal FROM terminais)
                             GROUP BY pep2.NsuOperacao
                         )
                         {nsu_clause}
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
                    registrar_log('pinbank.cargas_pinbank', f"Processando lote unificado Credenciadora {numero_lote}: {len(lote_atual)} registros")

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
                                linha['info_canal'] = self.pinbank_service.pega_info_canal_por_id(linha.get('canal_id'))

                                # Calcular valores primários
                                valores = self.calculadora.calcular_valores_primarios(linha, tabela='credenciadora')

                                # Inserir na base unificada
                                sucesso = self._inserir_valores_base_unificada(valores, linha)

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
                                registrar_log('pinbank.cargas_pinbank',
                                            f"Erro crítico (Base Unificada Credenciadora): NSU={linha.get('NsuOperacao')}, Erro: {str(e)}",
                                            nivel='ERROR')
                                registrar_log('pinbank.cargas_pinbank', f"Traceback: {erro_detalhado}", nivel='ERROR')

                    registrar_log('pinbank.cargas_pinbank',
                                f"Lote unificado Credenciadora {numero_lote} commitado ({len(lote_atual)} registros)")
                    lote_atual = []
                    numero_lote += 1

            # Processar último lote se houver registros restantes
            if lote_atual:
                registrar_log('pinbank.cargas_pinbank', f"Processando último lote unificado Credenciadora: {len(lote_atual)} registros")

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
                            linha['info_canal'] = self.pinbank_service.pega_info_canal_por_id(linha.get('canal_id'))

                            valores = self.calculadora.calcular_valores_primarios(linha, tabela='credenciadora')
                            sucesso = self._inserir_valores_base_unificada(valores, linha)

                            if sucesso:
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
                            registrar_log('pinbank.cargas_pinbank',
                                        f"Erro crítico (Base Unificada Credenciadora): NSU={linha.get('NsuOperacao')}, Erro: {str(e)}",
                                        nivel='ERROR')
                            registrar_log('pinbank.cargas_pinbank', f"Traceback: {erro_detalhado}", nivel='ERROR')

                registrar_log('pinbank.cargas_pinbank', f"Último lote unificado Credenciadora commitado ({len(lote_atual)} registros)")

            registrar_log('pinbank.cargas_pinbank',
                        f"✅ Processamento Base Unificada Credenciadora concluído: {registros_processados} transações processadas")
            return registros_processados

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
        """Insere novo registro usando SQL direto (apenas se NSU não existir)"""
        nsu = campos.get('var9')
        
        # Verificar se NSU já existe na base unificada
        cursor.execute("""
            SELECT COUNT(*) 
            FROM base_transacoes_unificadas 
            WHERE var9 = %s AND tipo_operacao = 'Credenciadora'
        """, [nsu])
        
        existe = cursor.fetchone()[0] > 0
        
        if existe:
            registrar_log('pinbank.cargas_pinbank', f"⚠️ NSU {nsu} já existe na base unificada (Credenciadora) - pulando inserção")
            return
        
        # Filtrar apenas campos válidos
        campos_validos = {k: v for k, v in campos.items() if k not in ['id']}

        # Ordenar campos
        campos_ordenados = sorted(campos_validos.keys())
        valores_ordenados = [campos_validos[campo] for campo in campos_ordenados]

        # Construir SQL
        campos_sql = ', '.join(campos_ordenados)
        placeholders = ', '.join(['%s'] * len(campos_ordenados))

        sql = f"""
            INSERT INTO base_transacoes_unificadas ({campos_sql})
            VALUES ({placeholders})
        """

        # Converter datetime para string
        valores_finais = []
        for valor in valores_ordenados:
            if hasattr(valor, 'strftime'):
                valores_finais.append(valor.strftime('%Y-%m-%d %H:%M:%S'))
            else:
                valores_finais.append(valor)

        cursor.execute(sql, valores_finais)
        registrar_log('pinbank.cargas_pinbank', f"✅ Registro inserido na base unificada (Credenciadora) - NSU: {nsu}")
