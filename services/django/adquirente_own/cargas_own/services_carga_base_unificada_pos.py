"""
Serviço para carga da Base Transações Unificadas - Own Financial
Processa transações das tabelas ownExtratoTransacoes e transactiondata_own
Usa CalculadoraBaseCredenciadora

MIGRADO: 23/12/2025 - Insere em base_transacoes_unificadas
"""

from typing import Dict, Any
from datetime import datetime
from django.db import connection, transaction
from adquirente_own.cargas_own.models import OwnExtratoTransacoes
from wallclub_core.utilitarios.log_control import registrar_log


class CargaBaseUnificadaOwnService:
    """
    Serviço para carga da base unificada - Own Financial
    Regra: 1 linha por transação (NSU único), não por parcela
    Filtro: Apenas transações com lido = 0
    """

    def __init__(self):
        from parametros_wallclub.calculadora_base_unificada import CalculadoraBaseUnificada
        self.calculadora = CalculadoraBaseUnificada()

    def carregar_valores_primarios(self, limite: int = None, identificador: str = None) -> int:
        """
        Rotina principal de carga de variáveis primárias
        Processa registros com lido = 0
        """
        registrar_log('adquirente_own.cargas_own', "Iniciando carga de valores primários Own")

        # Query principal - busca registros não lidos
        limit_clause = f"LIMIT {limite}" if limite else ""
        identificador_clause = f"AND oet.identificadorTransacao = '{identificador}'" if identificador else ""

        with connection.cursor() as cursor:
            # Cache de canais
            from wallclub_core.estr_organizacional.canal import Canal
            
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
            
            registrar_log('adquirente_own.cargas_own', f"Cache carregado: {len(canais_cache)} canais")
            
            cursor.execute(f"""
                SELECT   oet.id,
                         oet.cnpjCpfParceiro,
                         oet.identificadorTransacao,
                         oet.numeroSerieEquipamento,
                         oet.bandeira,
                         oet.modalidade,
                         oet.data,
                         oet.dataPagamentoReal,
                         oet.codigoAutorizacao,
                         oet.numeroCartao,
                         oet.numeroParcela,
                         oet.quantidadeParcelas,
                         oet.valor,
                         oet.valorParcela,
                         oet.mdrParcela,
                         oet.statusTransacao,
                         oet.statusPagamento,
                         t.cpf,
                         t.txTransactionId,
                         t.valor_original,
                         t.terminal,
                         t.nsuHost,
                         t.totalInstallments,
                         t.valor_desconto,
                         t.valor_cashback,
                         t.cashback_concedido,
                         t.saldo_usado,
                         t.modalidade_wall,
                         t.autorizacao_id,
                         l.id as loja_id,
                         l.razao_social,
                         l.cnpj,
                         l.canal_id,
                         term.id as terminal_id
                FROM     wallclub.ownExtratoTransacoes oet
                 JOIN wallclub.transactiondata_own t ON oet.identificadorTransacao = t.txTransactionId
                 JOIN wallclub.loja l ON oet.cnpjCpfParceiro = l.cnpj
                 JOIN wallclub.terminais term ON t.terminal = term.terminal
                WHERE    oet.lido = 0
                         {identificador_clause}
                ORDER BY oet.id
                {limit_clause}
            """)

            colunas = [desc[0] for desc in cursor.description]
            registros_processados = 0

            # Processar em lotes de 100 registros SEM carregar tudo em memória
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
                    registrar_log('adquirente_own.cargas_own', f"Processando lote {numero_lote}: {len(lote_atual)} registros")

                    with transaction.atomic():
                        for row_lote in lote_atual:
                            linha = dict(zip(colunas, row_lote))

                            try:
                                # Montar info_loja e info_canal
                                loja_id = linha.get('loja_id')
                                canal_id = linha.get('canal_id')
                                
                                info_loja = {
                                    'id': loja_id,
                                    'loja_id': loja_id,
                                    'loja': linha.get('razao_social'),
                                    'cnpj': linha.get('cnpj'),
                                    'canal_id': canal_id
                                }
                                
                                info_canal = canais_cache.get(canal_id)
                                if not info_canal:
                                    registrar_log('adquirente_own.cargas_own', 
                                                f"⚠️ Canal ID {canal_id} não encontrado no cache", 
                                                nivel='WARNING')
                                    continue
                                
                                # Calcular valores primários
                                valores = self.calculadora.calcular_valores_primarios(
                                    dados_linha=linha,
                                    tipo_operacao='Wallet',
                                    info_loja=info_loja,
                                    info_canal=info_canal
                                )

                                # Inserir na base de gestão
                                sucesso = self._inserir_valores_base_gestao(valores, linha)

                                if sucesso:
                                    # Marcar como lido
                                    OwnExtratoTransacoes.objects.filter(id=linha['id']).update(lido=True)
                                    registros_processados += 1
                                else:
                                    registrar_log('adquirente_own.cargas_own', f"Valores primários não foram atualizados para ID={linha['id']}", nivel='ERROR')

                            except Exception as e:
                                import traceback
                                erro_detalhado = traceback.format_exc()
                                registrar_log('adquirente_own.cargas_own', f"Erro crítico (CargaBaseGestaoOwn): ID={linha['id']}, Erro: {str(e)}", nivel='ERROR')
                                registrar_log('adquirente_own.cargas_own', f"Traceback completo: {erro_detalhado}", nivel='ERROR')

                                # Registrar erro
                                BaseTransacoesGestaoErroCarga.objects.create(
                                    idFilaExtrato=linha['id'],
                                    mensagem=str(e)
                                )

                    registrar_log('adquirente_own.cargas_own', f"Lote {numero_lote} commitado com sucesso ({len(lote_atual)} registros processados)")
                    lote_atual = []
                    numero_lote += 1

            # Processar último lote se houver registros restantes
            if lote_atual:
                registrar_log('adquirente_own.cargas_own', f"Processando último lote {numero_lote}: {len(lote_atual)} registros")

                with transaction.atomic():
                    for row_lote in lote_atual:
                        linha = dict(zip(colunas, row_lote))

                        try:
                            # Preservar campos originais importantes antes dos cálculos
                            campos_originais = {
                                'data': linha.get('data'),
                                'dataPagamentoReal': linha.get('dataPagamentoReal'),
                                'identificadorTransacao': linha.get('identificadorTransacao'),
                                'id': linha.get('id')
                            }

                            # Montar info_loja e info_canal
                            loja_id = linha.get('loja_id')
                            canal_id = linha.get('canal_id')
                            
                            info_loja = {
                                'id': loja_id,
                                'loja_id': loja_id,
                                'loja': linha.get('razao_social'),
                                'cnpj': linha.get('cnpj'),
                                'canal_id': canal_id
                            }
                            
                            info_canal = canais_cache.get(canal_id)
                            if not info_canal:
                                registrar_log('adquirente_own.cargas_own', 
                                            f"⚠️ Canal ID {canal_id} não encontrado no cache", 
                                            nivel='WARNING')
                                continue
                            
                            # Calcular valores primários
                            valores = self.calculadora.calcular_valores_primarios(
                                dados_linha=linha,
                                tipo_operacao='Wallet',
                                info_loja=info_loja,
                                info_canal=info_canal
                            )

                            # Inserir na base de gestão
                            sucesso = self._inserir_valores_base_gestao(valores, linha)

                            if sucesso:
                                # Marcar como lido
                                OwnExtratoTransacoes.objects.filter(id=linha['id']).update(lido=True)
                                registros_processados += 1
                            else:
                                registrar_log('adquirente_own.cargas_own', f"Valores primários não foram atualizados para ID={linha['id']}")

                        except Exception as e:
                            import traceback
                            erro_detalhado = traceback.format_exc()
                            registrar_log('adquirente_own.cargas_own', f"Erro crítico (CargaBaseGestaoOwn): ID={linha['id']}, Erro: {str(e)}", nivel='ERROR')
                            registrar_log('adquirente_own.cargas_own', f"Traceback completo: {erro_detalhado}", nivel='ERROR')

                            # Registrar erro
                            BaseTransacoesGestaoErroCarga.objects.create(
                                idFilaExtrato=linha['id'],
                                mensagem=str(e)
                            )

                registrar_log('adquirente_own.cargas_own', f"Último lote {numero_lote} commitado com sucesso ({len(lote_atual)} registros processados)")

        registrar_log('adquirente_own.cargas_own', f"Carga de valores primários Own finalizada. Registros processados: {registros_processados}")
        return registros_processados

    def _inserir_valores_base_gestao(self, valores: Dict[int, Any], linha: Dict[str, Any]) -> bool:
        """
        Insere valores na base_transacoes_unificadas
        MIGRADO: Não insere mais em baseTransacoesGestao
        """
        try:
            # NSU da transação Own
            nsu = linha.get('identificadorTransacao')
            if not nsu:
                registrar_log('adquirente_own.cargas_own', 'NSU não encontrado, pulando inserção', nivel='WARNING')
                return False

            # Verificar se NSU já existe (evitar duplicação)
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) FROM base_transacoes_unificadas
                    WHERE var9 = %s AND adquirente = 'OWN'
                """, [str(nsu)])
                existe = cursor.fetchone()[0] > 0

                if existe:
                    registrar_log('adquirente_own.cargas_own', f'⚠️ NSU {nsu} já existe em base_transacoes_unificadas, pulando INSERT')
                    return True

            # Preparar dados para inserção
            dados_insert = {
                'banco': 'OWN',
                'adquirente': 'OWN',
                'tipo_operacao': 'Wallet',
                'origem_transacao': 'POS',
                'data_transacao': linha.get('data') or datetime.now()
            }

            # Mapear var0-var130
            for i in range(131):
                if i in valores:
                    valor = valores[i]
                    campo_nome = f'var{i}'
                    
                    # Extrair valor correto se for dict
                    if isinstance(valor, dict):
                        if "0" in valor:
                            dados_insert[campo_nome] = valor["0"]
                        else:
                            dados_insert[campo_nome] = None
                    else:
                        dados_insert[campo_nome] = valor

            # Inserir em base_transacoes_unificadas
            with connection.cursor() as cursor:
                campos = list(dados_insert.keys())
                valores_insert = list(dados_insert.values())
                placeholders = ', '.join(['%s'] * len(valores_insert))
                campos_sql = ', '.join(campos)

                sql = f"INSERT INTO base_transacoes_unificadas ({campos_sql}) VALUES ({placeholders})"
                cursor.execute(sql, valores_insert)
                
                registrar_log('adquirente_own.cargas_own', f'✅ base_transacoes_unificadas inserida - NSU: {nsu}')

            return True

        except Exception as e:
            import traceback
            erro_completo = traceback.format_exc()
            registrar_log('adquirente_own.cargas_own', f"Erro ao inserir valores na base unificada: {str(e)}", nivel='ERROR')
            registrar_log('adquirente_own.cargas_own', f"Traceback completo: {erro_completo}", nivel='ERROR')
            return False


    def _mapear_tipo_compra(self, modalidade: str) -> str:
        """
        Mapeia modalidade Own para TipoCompra Pinbank
        
        Own: "DEBITO", "CREDITO", "CREDITO PARC 2 a 6", "CREDITO PARC 7 A 12", etc
        Pinbank: "DEBITO", "A VISTA", "PARCELADO SEM JUROS", etc
        """
        if not modalidade:
            return 'A VISTA'  # Default: crédito à vista
        
        modalidade_upper = modalidade.upper()
        
        if 'DEBITO' in modalidade_upper or 'DÉBITO' in modalidade_upper:
            return 'DEBITO'
        elif 'PARC' in modalidade_upper or 'PARCELADO' in modalidade_upper:
            return 'PARCELADO SEM JUROS'  # Own não diferencia com/sem juros
        else:
            return 'A VISTA'  # Crédito à vista
