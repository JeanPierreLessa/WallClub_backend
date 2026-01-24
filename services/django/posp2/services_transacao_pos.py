"""
Service unificado para processar transações POS (Pinbank + Own)
Tabela única: transactiondata_pos
Endpoints: /trdata_pinbank/ e /trdata_own/
"""

import json
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any
from django.db import connection, transaction
from wallclub_core.utilitarios.log_control import registrar_log
from parametros_wallclub.calculadora_base_unificada import CalculadoraBaseUnificada
from parametros_wallclub.services import ParametrosService


class TRDataPosService:
    """
    Service unificado para processar transações POS
    Suporta Pinbank e Own na mesma tabela (transactiondata_pos)
    """

    TIPO_COMPRA_MAP = {
        'CREDIT_IN_INSTALLMENTS_WITHOUT_INTEREST': 'PARCELADO SEM JUROS',
        'CREDIT_ONE_INSTALLMENT': 'A VISTA',
        'DEBIT': 'DEBITO',
        'CASH': 'PIX',
        'PIX': 'PIX'
    }

    def __init__(self):
        self.parametros_service = ParametrosService()

    # ========================================
    # ENDPOINTS PÚBLICOS
    # ========================================

    def processar_transacao_pinbank(self, dados_json: str) -> Dict[str, Any]:
        """Endpoint /trdata_pinbank/"""
        registrar_log('posp2', '========================================')
        registrar_log('posp2', f'{datetime.now().strftime("%d/%m/%Y %H:%M:%S")} - Processamento Pinbank')
        registrar_log('posp2', '========================================')
        registrar_log('posp2', f'📥 JSON Entrada: {dados_json}')

        dados_normalizados = self._parse_payload_pinbank(dados_json)
        resultado = self._processar_comum(dados_normalizados)

        registrar_log('posp2', f'📤 JSON Saída: {json.dumps(resultado, ensure_ascii=False)}')
        return resultado

    def processar_transacao_own(self, dados_json: str) -> Dict[str, Any]:
        """Endpoint /trdata_own/"""
        registrar_log('posp2', '========================================')
        registrar_log('posp2', f'{datetime.now().strftime("%d/%m/%Y %H:%M:%S")} - Processamento Own')
        registrar_log('posp2', '========================================')
        registrar_log('posp2', f'📥 JSON Entrada: {dados_json}')

        dados_normalizados = self._parse_payload_own(dados_json)
        resultado = self._processar_comum(dados_normalizados)

        registrar_log('posp2', f'📤 JSON Saída: {json.dumps(resultado, ensure_ascii=False)}')
        return resultado

    # ========================================
    # PARSERS ESPECÍFICOS
    # ========================================

    def _parse_payload_pinbank(self, dados_json: str) -> Dict:
        """Parse específico para Pinbank"""
        try:
            dados = json.loads(dados_json)
            trdata = json.loads(dados.get('trdata', '{}'))

            dados_normalizados = {
                'gateway': 'PINBANK',

                # Dados básicos
                'celular': dados.get('celular', ''),
                'cpf': dados.get('cpf', ''),
                'terminal': dados.get('terminal', ''),
                'operador_pos': dados.get('operador_pos', ''),
                'valor_original': self._converter_valor_monetario(dados.get('valororiginal', '')),

                # Identificadores Pinbank (do trdata nativo)
                'nsu_gateway': str(trdata.get('nsuPinbank', '')),
                'nsuAcquirer': trdata.get('nsuAcquirer', ''),
                'nsuTerminal': str(trdata.get('nsuTerminal', '')),
                'nsuHost': str(trdata.get('nsuHost', '')) if trdata.get('nsuHost') else None,
                'authorizationCode': trdata.get('authorizationCode', ''),
                'transactionReturn': trdata.get('status', ''),

                # Valores (do trdata nativo)
                'amount': int(trdata.get('amount', 0)),
                'originalAmount': int(trdata.get('originalAmount', 0)),
                'totalInstallments': int(trdata.get('totalInstallments', 1)),

                # Método de pagamento (do trdata nativo)
                'paymentMethod': trdata.get('paymentMethod', ''),
                'operationId': None,
                'brand': trdata.get('brand', ''),
                'cardNumber': trdata.get('cardNumber', ''),
                'cardName': trdata.get('cardName', ''),

                # Timestamps (do trdata nativo)
                'hostTimestamp': str(trdata.get('hostTimestamp', '')),
                'terminalTimestamp': int(trdata.get('terminalTimestamp', 0)),

                # Específico Own (NULL)
                'sdk': None,
                'customerTicket': None,
                'estabTicket': None,
                'e2ePixId': None,

                # Wall Club (do payload principal)
                'modalidade_wall': None,
                'autorizacao_id': dados.get('autorizacao_id', ''),
                'valor_desconto': float(dados.get('valor_desconto', 0)),
                'valor_cashback': float(dados.get('valor_cashback', 0)),
                'cashback_concedido': float(dados.get('cashback_concedido', 0)),

                # Cupom (do payload principal - NÃO do trdata)
                'cupom_codigo': dados.get('cupom_codigo', ''),
                'cupom_valor_desconto': Decimal(str(dados.get('cupom_valor_desconto', 0))),

                # Desconto Wall (do payload principal)
                'desconto_wall_parametro_id': dados.get('desconto_wall_parametro_id'),

                # Cashback centralizado (do payload principal - NÃO do trdata)
                'cashback_wall_parametro_id': dados.get('cashback_wall_parametro_id'),
                'cashback_wall_valor': Decimal(str(dados.get('cashback_wall_valor', 0))),
                'cashback_loja_regra_id': dados.get('cashback_loja_regra_id'),
                'cashback_loja_valor': Decimal(str(dados.get('cashback_loja_valor', 0))),
            }

            registrar_log('posp2', f'📥 Pinbank: Terminal={dados_normalizados["terminal"]}, NSU={dados_normalizados["nsu_gateway"]}, Valor=R$ {dados_normalizados["valor_original"]}')

            return dados_normalizados

        except Exception as e:
            registrar_log('posp2', f'Erro ao parsear payload Pinbank: {e}', nivel='ERROR')
            raise

    def _parse_payload_own(self, dados_json: str) -> Dict:
        """Parse específico para Own"""
        try:
            dados = json.loads(dados_json)
            trdata = json.loads(dados.get('trdata', '{}'))

            dados_normalizados = {
                'gateway': 'OWN',

                # Dados básicos
                'celular': dados.get('celular', ''),
                'cpf': dados.get('cpf', ''),
                'terminal': dados.get('terminal', ''),
                'operador_pos': dados.get('operador_pos', ''),
                'valor_original': self._converter_valor_monetario(dados.get('valororiginal', '')),

                # Identificadores Own (do trdata nativo)
                'nsu_gateway': trdata.get('txTransactionId', ''),
                'nsuAcquirer': None,
                'nsuTerminal': trdata.get('nsuTerminal', ''),
                'nsuHost': trdata.get('nsuHost', ''),
                'authorizationCode': trdata.get('authorizationCode', ''),
                'transactionReturn': trdata.get('transactionReturn', ''),

                # Valores (do trdata nativo)
                'amount': int(trdata.get('amount', 0)),
                'originalAmount': int(trdata.get('originalAmount', 0)),
                'totalInstallments': int(trdata.get('totalInstallments', 1)),

                # Método de pagamento (do trdata nativo)
                'paymentMethod': trdata.get('paymentMethod', ''),
                'operationId': int(trdata.get('operationId', 1)),
                'brand': trdata.get('brand', ''),
                'cardNumber': trdata.get('cardNumber', ''),
                'cardName': trdata.get('cardName', ''),

                # Timestamps (do trdata nativo)
                'hostTimestamp': str(trdata.get('hostTimestamp', '')),
                'terminalTimestamp': int(trdata.get('terminalTimestamp', 0)),

                # Específico Own (do trdata nativo)
                'sdk': trdata.get('sdk', 'agilli'),
                'customerTicket': trdata.get('customerTicket', ''),
                'estabTicket': trdata.get('estabTicket', ''),
                'e2ePixId': trdata.get('e2ePixId', ''),

                # Wall Club (do payload principal)
                'modalidade_wall': None,
                'autorizacao_id': dados.get('autorizacao_id', ''),
                'valor_desconto': float(dados.get('valor_desconto', 0)),
                'valor_cashback': float(dados.get('valor_cashback', 0)),
                'cashback_concedido': float(dados.get('cashback_concedido', 0)),

                # Cupom (do payload principal - NÃO do trdata)
                'cupom_codigo': dados.get('cupom_codigo', ''),
                'cupom_valor_desconto': Decimal(str(dados.get('cupom_valor_desconto', 0))),

                # Desconto Wall (do payload principal)
                'desconto_wall_parametro_id': dados.get('desconto_wall_parametro_id'),

                # Cashback centralizado (do payload principal - NÃO do trdata)
                'cashback_wall_parametro_id': dados.get('cashback_wall_parametro_id'),
                'cashback_wall_valor': Decimal(str(dados.get('cashback_wall_valor', 0))),
                'cashback_loja_regra_id': dados.get('cashback_loja_regra_id'),
                'cashback_loja_valor': Decimal(str(dados.get('cashback_loja_valor', 0))),
            }

            registrar_log('posp2', f'📥 Own: Terminal={dados_normalizados["terminal"]}, TxID={dados_normalizados["nsu_gateway"]}, Valor=R$ {dados_normalizados["valor_original"]}')

            return dados_normalizados

        except Exception as e:
            registrar_log('posp2', f'Erro ao parsear payload Own: {e}', nivel='ERROR')
            raise

    # ========================================
    # PROCESSAMENTO COMUM
    # ========================================

    def _processar_comum(self, dados: Dict) -> Dict[str, Any]:
        """Lógica de negócio unificada para Pinbank e Own"""
        try:
            # 1. Validar dados obrigatórios
            if not dados['terminal'] or not dados['valor_original']:
                return {
                    'sucesso': False,
                    'mensagem': 'Campos obrigatórios ausentes'
                }

            # 2. Buscar loja_id, canal_id, nomes e cnpj
            loja_id, canal_id, nome_canal, razao_social, cnpj = self._buscar_loja_canal(dados['terminal'])
            if not loja_id:
                return {
                    'sucesso': False,
                    'mensagem': f'Terminal não encontrado: {dados["terminal"]}'
                }

            # 3. Validar e processar cupom (COMUM)
            cupom_id, cupom_cliente_id = self._validar_cupom(
                dados['cupom_codigo'],
                dados['cupom_valor_desconto'],
                dados['cpf'],
                loja_id
            )

            # 4. Inserir em transactiondata_pos (UNIFICADO)
            transaction_id = self._inserir_transacao_pos(dados, cupom_id)
            registrar_log('posp2', f'✅ Transação inserida: ID={transaction_id}, Gateway={dados["gateway"]}')

            # 5. Registrar uso do cupom (COMUM)
            if cupom_id and cupom_cliente_id:
                self._registrar_uso_cupom(
                    cupom_id, cupom_cliente_id, loja_id,
                    transaction_id, dados['nsu_gateway'],
                    dados['valor_original'], dados['cupom_valor_desconto']
                )

            # 5.5. Debitar saldo de cashback usado (COMUM)
            if dados.get('autorizacao_id') and dados.get('valor_cashback', 0) > 0:
                self._debitar_saldo_cashback(
                    autorizacao_id=dados['autorizacao_id'],
                    nsu_transacao=dados['nsu_gateway'],
                    valor=dados['valor_cashback']
                )

            # 6. Conceder cashback via sistema centralizado (COMUM)
            self._conceder_cashback(
                dados, transaction_id, loja_id, canal_id
            )

            # 7. Calcular valores via CalculadoraBaseGestao e gerar slip
            tipo_compra = self.TIPO_COMPRA_MAP.get(dados['paymentMethod'], dados['paymentMethod'])

            # Usar valor_original (valororiginal da loja) para a calculadora
            # Igual à trdata - cupom e cashback são informativos para o slip
            valor_para_calculo = dados['valor_original']
            registrar_log('posp2', f'💰 Usando valor_original para calculadora: {valor_para_calculo}')

            dados_linha = {
                'id': transaction_id,
                'DataTransacao': datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
                'SerialNumber': dados['terminal'],
                'idTerminal': dados['terminal'],
                'cpf': dados['cpf'],
                'TipoCompra': tipo_compra,
                'NsuOperacao': dados['nsu_gateway'],
                'nsuAcquirer': dados['nsuAcquirer'],
                'valor_original': valor_para_calculo,
                'ValorBruto': valor_para_calculo,
                'ValorBrutoParcela': valor_para_calculo,
                'Bandeira': dados['brand'],
                'NumeroTotalParcelas': dados['totalInstallments'],
                'ValorTaxaAdm': 0,
                'ValorTaxaMes': 0,
                'ValorSplit': 0,
                'DescricaoStatus': 'Processado',
                'DescricaoStatusPagamento': 'Pendente',
                'IdStatusPagamento': 1,
                'DataCancelamento': None,
                'DataFuturaPagamento': None,
                'cupom_codigo': dados.get('cupom_codigo', ''),
                'cupom_valor_desconto': dados.get('cupom_valor_desconto', 0)
            }

            # 7. Calcular valores (passar info_loja e info_canal já resolvidos)
            loja_info = {'id': loja_id, 'loja_id': loja_id, 'loja': razao_social, 'cnpj': cnpj, 'canal_id': canal_id}
            canal_info = {'id': canal_id, 'canal_id': canal_id, 'canal': nome_canal}
            calculadora = CalculadoraBaseUnificada()
            valores_calculados = calculadora.calcular_valores_primarios(
                dados_linha,
                tabela='transactiondata_pos',
                info_loja=loja_info,
                info_canal=canal_info
            )
            registrar_log('posp2', f'✅ Valores calculados: {len(valores_calculados)} campos')
            registrar_log('posp2', f'🔍 [DEBUG] valores[11]={valores_calculados.get(11)}, valores[19]={valores_calculados.get(19)}, valores[26]={valores_calculados.get(26)}')

            # Ajustar var26 para refletir valor efetivamente pago (abater cupom e cashback)
            cupom_desconto = Decimal(str(dados.get('cupom_valor_desconto', 0) or 0))
            cashback_usado = Decimal(str(dados.get('valor_cashback', 0) or 0))
            if 26 in valores_calculados and (cupom_desconto > 0 or cashback_usado > 0):
                var26_original = Decimal(str(valores_calculados[26]))
                var26_ajustado = var26_original - cupom_desconto - cashback_usado
                valores_calculados[26] = var26_ajustado
                registrar_log('posp2', f'💰 var26 ajustado: {var26_original} - cupom({cupom_desconto}) - cashback({cashback_usado}) = {var26_ajustado}')

            # 8. Inserir em base_transacoes_unificadas
            self._inserir_base_transacoes_unificadas(
                dados, valores_calculados, datetime.now(), dados['nsu_gateway']
            )

            # 9. Gerar slip de impressão
            slip = self._gerar_slip_impressao(dados, valores_calculados, loja_info)

            # 10. Enviar push notification para o cliente
            self._enviar_push_notification(
                dados, valores_calculados, loja_info, canal_id,
                datetime.now()
            )

            registrar_log('posp2', 'Processamento concluído com sucesso')

            return {
                'sucesso': True,
                'mensagem': 'Dados processados com sucesso',
                'transaction_id': transaction_id,
                **slip  # Incluir dados do slip no response
            }

        except Exception as e:
            import traceback
            registrar_log('posp2', f'ERRO no processamento: {str(e)}', nivel='ERROR')
            registrar_log('posp2', f'Traceback: {traceback.format_exc()}', nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': f'Erro interno: {e}'
            }

    # ========================================
    # MÉTODOS AUXILIARES
    # ========================================

    def _buscar_loja_canal(self, terminal: str) -> tuple:
        """Busca loja_id, canal_id, nome_canal, razao_social e cnpj pelo terminal"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT l.id, l.canal_id, c.nome, l.razao_social, l.cnpj
                FROM terminais t
                INNER JOIN loja l ON t.loja_id = l.id
                INNER JOIN canal c ON l.canal_id = c.id
                WHERE t.terminal = %s
            """, [terminal])
            row = cursor.fetchone()
            if row:
                registrar_log('posp2', f'Loja encontrada: loja_id={row[0]}, canal_id={row[1]}')
                return row[0], row[1], row[2], row[3], row[4]  # loja_id, canal_id, nome_canal, razao_social, cnpj
            return None, None, None, None, None

    def _validar_cupom(self, cupom_codigo: str, cupom_valor_desconto: Decimal,
                       cpf: str, loja_id: int) -> tuple:
        """Valida cupom e retorna (cupom_id, cliente_id)"""
        if not cupom_codigo or cupom_valor_desconto <= 0:
            return None, None

        try:
            from apps.cupom.models import Cupom

            registrar_log('posp2', f'🎟️ Validando cupom: {cupom_codigo}')

            # Buscar cliente_id pelo CPF
            cupom_cliente_id = None
            if cpf:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT id FROM cliente WHERE cpf = %s", [cpf])
                    result = cursor.fetchone()
                    if result:
                        cupom_cliente_id = result[0]

            if not cupom_cliente_id:
                raise ValueError("CPF do cliente é obrigatório para usar cupom")

            # Validar cupom
            cupom_obj = Cupom.objects.filter(
                codigo__iexact=cupom_codigo,
                loja_id=loja_id,
                ativo=True
            ).first()

            if not cupom_obj:
                raise ValueError(f"Cupom não encontrado ou inativo: {cupom_codigo}")

            registrar_log('posp2', f'✅ Cupom validado: {cupom_codigo}')
            return cupom_obj.id, cupom_cliente_id

        except Exception as e:
            registrar_log('posp2', f'❌ Erro ao validar cupom: {e}', nivel='ERROR')
            raise

    def _registrar_uso_cupom(self, cupom_id: int, cliente_id: int, loja_id: int,
                            transaction_id: int, nsu: str, valor_original: Decimal,
                            valor_desconto: Decimal):
        """Registra uso do cupom"""
        try:
            from apps.cupom.services import CupomService
            from apps.cupom.models import Cupom

            cupom = Cupom.objects.get(id=cupom_id)
            cupom_service = CupomService()
            cupom_service.registrar_uso(
                cupom=cupom,
                cliente_id=cliente_id,
                loja_id=loja_id,
                transacao_tipo='POS',
                transacao_id=transaction_id,
                nsu=nsu,
                valor_original=valor_original,
                valor_desconto=valor_desconto,
                valor_final=valor_original - valor_desconto
            )
            registrar_log('posp2', f'✅ Uso do cupom registrado')
        except Exception as e:
            registrar_log('posp2', f'⚠️ Erro ao registrar uso do cupom: {e}', nivel='WARNING')

    def _debitar_saldo_cashback(self, autorizacao_id: str, nsu_transacao: str, valor: Decimal):
        """Debita saldo de cashback usado na transação"""
        try:
            from apps.conta_digital.services_autorizacao import AutorizacaoService

            registrar_log('posp2', f'💸 Debitando saldo: autorizacao={autorizacao_id[:8]}, NSU={nsu_transacao}, valor=R$ {valor:.2f}')

            resultado = AutorizacaoService.debitar_saldo_autorizado(
                autorizacao_id=autorizacao_id,
                nsu_transacao=nsu_transacao
            )

            if resultado.get('sucesso'):
                registrar_log('posp2', f'✅ Saldo debitado: R$ {resultado.get("valor_debitado")}, movimentacao_id={resultado.get("movimentacao_id")}')
            else:
                registrar_log('posp2', f'❌ Erro ao debitar saldo: {resultado.get("mensagem")}', nivel='ERROR')

        except Exception as e:
            registrar_log('posp2', f'❌ Erro ao debitar saldo cashback: {str(e)}', nivel='ERROR')

    def _conceder_cashback(self, dados: Dict, transaction_id: int, loja_id: int, canal_id: int):
        """Concede cashback Wall e Loja via sistema centralizado"""
        cpf = dados['cpf']
        cashback_wall_valor = dados['cashback_wall_valor']
        cashback_loja_valor = dados['cashback_loja_valor']

        if (cashback_wall_valor <= 0 and cashback_loja_valor <= 0) or not cpf or not loja_id:
            return

        try:
            from apps.cliente.models import Cliente
            cliente = Cliente.objects.get(cpf=cpf, canal_id=canal_id)

            # Cashback Wall
            if cashback_wall_valor > 0 and dados['cashback_wall_parametro_id']:
                from apps.cashback.services import CashbackService
                resultado_wall = CashbackService.aplicar_cashback_wall(
                    parametro_wall_id=dados['cashback_wall_parametro_id'],
                    cliente_id=cliente.id,
                    loja_id=loja_id,
                    canal_id=canal_id,
                    transacao_tipo='POS',
                    transacao_id=transaction_id,
                    valor_transacao=dados['valor_original'],
                    valor_cashback=cashback_wall_valor
                )
                registrar_log('posp2', f'✅ Cashback Wall concedido: {resultado_wall}')

            # Cashback Loja
            if cashback_loja_valor > 0 and dados['cashback_loja_regra_id']:
                from apps.cashback.services import CashbackService
                resultado_loja = CashbackService.aplicar_cashback_loja(
                    regra_loja_id=dados['cashback_loja_regra_id'],
                    cliente_id=cliente.id,
                    loja_id=loja_id,
                    canal_id=canal_id,
                    transacao_tipo='POS',
                    transacao_id=transaction_id,
                    valor_transacao=dados['valor_original'],
                    valor_cashback=cashback_loja_valor
                )
                registrar_log('posp2', f'✅ Cashback Loja concedido: {resultado_loja}')

        except Exception as e:
            registrar_log('posp2', f'❌ Erro ao conceder cashback: {e}', nivel='ERROR')

    def _inserir_transacao_pos(self, dados: Dict, cupom_id: int) -> int:
        """Insere transação na tabela unificada transactiondata_pos"""
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO transactiondata_pos (
                    gateway, datahora, valor_original, celular, cpf, terminal, operador_pos,
                    nsu_gateway, nsuAcquirer, nsuTerminal, nsuHost, authorizationCode, transactionReturn,
                    amount, originalAmount, totalInstallments,
                    paymentMethod, operationId, brand, cardNumber, cardName,
                    hostTimestamp, terminalTimestamp,
                    sdk, customerTicket, estabTicket, e2ePixId,
                    modalidade_wall, autorizacao_id, valor_desconto, valor_cashback, cashback_concedido,
                    cupom_id, cupom_valor_desconto,
                    desconto_wall_parametro_id, cashback_wall_parametro_id, cashback_loja_regra_id
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s,
                    %s, %s, %s
                )
            """, [
                dados['gateway'], datetime.now(), dados['valor_original'],
                dados['celular'] or None, dados['cpf'] or None, dados['terminal'], dados['operador_pos'] or None,
                dados['nsu_gateway'], dados['nsuAcquirer'], dados['nsuTerminal'], dados['nsuHost'],
                dados['authorizationCode'], dados['transactionReturn'],
                dados['amount'], dados['originalAmount'], dados['totalInstallments'],
                dados['paymentMethod'], dados['operationId'], dados['brand'], dados['cardNumber'], dados['cardName'],
                dados['hostTimestamp'], dados['terminalTimestamp'],
                dados['sdk'], dados['customerTicket'], dados['estabTicket'], dados['e2ePixId'],
                dados['modalidade_wall'] or None, dados['autorizacao_id'] or None,
                dados['valor_desconto'], dados['valor_cashback'], dados['cashback_concedido'],
                cupom_id, float(dados['cupom_valor_desconto']) if dados['cupom_valor_desconto'] > 0 else None,
                dados.get('desconto_wall_parametro_id'), dados.get('cashback_wall_parametro_id'), dados.get('cashback_loja_regra_id')
            ])

            return cursor.lastrowid

    def _converter_valor_monetario(self, valor_str: str) -> Decimal:
        """Converte valor monetário de string para Decimal"""
        if not valor_str:
            return Decimal('0.00')

        valor_limpo = str(valor_str).replace('R$', '').replace(' ', '').strip()
        if ',' in valor_limpo and '.' not in valor_limpo:
            valor_limpo = valor_limpo.replace(',', '.')

        return Decimal(valor_limpo).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def _criar_array_base(self, dados: Dict, valores_calculados: Dict, cpf: str, nome: str,
                         cnpj: str, data_formatada: str, hora: str, forma: str,
                         nopwall: str, autwall: str, terminal: str, nsu: str, cet: str) -> Dict:
        """Cria array base comum para todas as respostas"""
        def mascarar_cpf(cpf_str):
            if not cpf_str:
                return cpf_str
            cpf_numeros = ''.join(filter(str.isdigit, cpf_str))
            if len(cpf_numeros) < 11:
                return cpf_str
            return f"*******{cpf_numeros[-3:]}"

        array_base = {
            "cpf": mascarar_cpf(cpf) if cpf else "",
            "nome": nome,
            "estabelecimento": valores_calculados.get(5, ''),
            "cnpj": cnpj,
            "data": f"{data_formatada} {hora}",
            "forma": forma,
            "parcelas": valores_calculados.get(13, 1),
            "nopwall": nopwall,
            "autwall": autwall,
            "terminal": terminal,
            "nsu": nsu
        }

        if cet and cet.strip() and not cet.endswith(': -'):
            array_base["cet"] = cet

        return array_base

    def _gerar_slip_impressao(self, dados: Dict, valores_calculados: Dict, loja_info: Dict) -> Dict:
        """Gera JSON de resposta formatado para impressão do slip"""
        try:
            # Dados básicos
            cpf = dados.get('cpf', '')
            nome = ''

            if cpf:
                try:
                    from wallclub_core.integracoes.api_interna_service import APIInternaService
                    canal_id = loja_info['canal_id']
                    response = APIInternaService.chamar_api_interna(
                        metodo='POST',
                        endpoint='/api/internal/cliente/obter_dados_cliente/',
                        payload={'cpf': cpf, 'canal_id': canal_id},
                        contexto='apis'
                    )
                    dados_cliente = response.get('dados') if response.get('sucesso') else None
                    if dados_cliente and dados_cliente.get('nome'):
                        nome = dados_cliente['nome']
                except Exception as e:
                    registrar_log('posp2', f'Erro ao buscar nome do cliente: {str(e)}')

            wall = 's' if cpf and len(cpf.strip()) > 0 else 'n'
            forma = self.TIPO_COMPRA_MAP.get(dados.get('paymentMethod', ''), dados.get('paymentMethod', ''))

            # Função auxiliar para converter valores
            def safe_float_convert(value):
                if not value:
                    return 0.0
                if isinstance(value, str):
                    value = value.replace('R$', '').replace(' ', '').strip()
                    if ',' in value and '.' not in value:
                        value = value.replace(',', '.')
                    elif ',' in value and '.' in value:
                        if value.rfind(',') > value.rfind('.'):
                            value = value.replace('.', '').replace(',', '.')
                        else:
                            value = value.replace(',', '')
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return 0.0

            def formatar_valor_monetario(valor):
                if valor is None:
                    return "0.00"
                try:
                    return f"{float(valor):.2f}"
                except (ValueError, TypeError):
                    return "0.00"

            valor_original_display = dados.get('valor_original', valores_calculados.get(11, 0))
            terminal = dados.get('terminal', '')
            nsu = dados.get('nsu_gateway', '')
            nopwall = dados.get('nsuAcquirer', '')
            autwall = dados.get('authorizationCode', '')
            cnpj = loja_info.get('cnpj', '')

            # Lógica condicional do PHP
            pixcartao_tipo = "PIX" if dados.get('brand') == 'PIX' else "CARTÃO"

            if valores_calculados.get(12) == "PIX" or pixcartao_tipo == "PIX":
                desconto = safe_float_convert(valores_calculados.get(15, 0))
            else:
                desconto = safe_float_convert(valores_calculados.get(18, 0))

            # Usar valores[26] calculado pela calculadora (já considera cupom)
            parte0 = safe_float_convert(valores_calculados.get(26, 0))
            if not parte0 or parte0 == 0:
                amount_centavos = dados.get('amount', 0)
                if amount_centavos:
                    parte0 = safe_float_convert(amount_centavos) / 100
                else:
                    parte0 = safe_float_convert(valores_calculados.get(11, 0))

            # vparcela e cálculos de tarifas/encargos conforme PHP
            parcelas = int(valores_calculados.get(13, 1))

            # Calcular encargos (PHP linha 432): $encargos = abs($valores[88] + $valores[94]["0"]);
            valores_94 = valores_calculados.get(94, {})
            if isinstance(valores_94, dict):
                valores_94_0 = safe_float_convert(valores_94.get('0', 0))
            else:
                valores_94_0 = 0
            valores_88 = safe_float_convert(valores_calculados.get(88) or 0)
            encargos = abs(valores_88 + valores_94_0)

            vparcela = valores_calculados.get(20, 0)
            if vparcela is None or vparcela == 0:
                vparcela = parte0 / parcelas if parcelas > 0 else parte0

            # correção feita em 13/12/2025 - Problema quando é encargo e nao desconto
            # Calcular parte1 seguindo PHP (linha 445): $parte1 = abs($valores[13] * $vparcela - $valores[11]);
            if parcelas >= 1 and vparcela:
                valor_original = safe_float_convert(valores_calculados.get(11, 0))
                vparcela_float = safe_float_convert(vparcela)
                parte1 = abs(parcelas * vparcela_float - valor_original)
            else:
                parte1 = abs(desconto)

            # Calcular tarifas (PHP linha 439): $tarifas = abs($valores[13] * $vparcela - $valores[16]) - $encargos;
            valor_liquido = safe_float_convert(valores_calculados.get(16, 0))
            vparcela_float = safe_float_convert(vparcela)
            tarifas = round(abs(parcelas * vparcela_float - valor_liquido) - encargos, 2)

            registrar_log('posp2', f'=== CÁLCULO PHP REPLICADO ===')
            registrar_log('posp2', f'encargos = abs({valores_calculados.get(88, 0)} + {valores_94_0}) = {encargos}')
            registrar_log('posp2', f'vparcela = {vparcela} (valores[20] direto)')
            registrar_log('posp2', f'tarifas = abs({valores_calculados.get(13, 1)} * {vparcela} - {valor_liquido}) - {encargos} = {tarifas}')

            registrar_log('posp2', f'=== RESULTADO FINAL ===')
            registrar_log('posp2', f'vparcela = {vparcela}')
            registrar_log('posp2', f'encargos = {encargos}')

            # Buscar saldo usado de cashback via autorizacao_id
            saldo_cashback_usado = 0.0
            autorizacao_id = dados.get('autorizacao_id', '')
            if autorizacao_id:
                try:
                    from apps.conta_digital.services_autorizacao import AutorizacaoService
                    resultado = AutorizacaoService.verificar_autorizacao(autorizacao_id)
                    if resultado.get('sucesso') and resultado.get('status') in ['APROVADO', 'CONCLUIDA']:
                        valor_bloqueado = resultado.get('valor_bloqueado')
                        if valor_bloqueado:
                            saldo_cashback_usado = float(valor_bloqueado)
                            registrar_log('posp2', f'💸 [SALDO] Saldo cashback usado encontrado: R$ {saldo_cashback_usado:.2f}, status={resultado.get("status")}')
                except Exception as e:
                    registrar_log('posp2', f'❌ [SALDO] Erro ao buscar saldo usado: {str(e)}', nivel='ERROR')

            # Extrair cashback_concedido dos dados
            cashback_concedido = safe_float_convert(dados.get('cashback_concedido', 0))
            cupom_desconto = safe_float_convert(dados.get('cupom_valor_desconto', 0))
            registrar_log('posp2', f'💰 [CASHBACK] Cashback concedido: R$ {cashback_concedido:.2f}')

            # var26 já vem ajustado (cupom e cashback já abatidos)
            # vdesconto_final = parte0 (que é var26 ajustado)
            vdesconto_final = parte0

            # vparcela = vdesconto / parcelas
            vparcela_ajustado = vdesconto_final / parcelas if parcelas > 0 else vdesconto_final

            registrar_log('posp2', f'💰 [SLIP] vdesconto_final={vdesconto_final:.2f}, vparcela_ajustado={vparcela_ajustado:.2f}, parcelas={parcelas}')

            # Data e hora
            agora = datetime.now()
            data_formatada = valores_calculados.get(0, agora.strftime('%Y-%m-%d'))
            hora = agora.strftime('%H:%M:%S')

            # CET para parcelado
            cet = ""
            if parcelas > 1:
                from wallclub_core.utilitarios.funcoes_gerais import calcular_cet
                valor_original_cet = float(valores_calculados.get(11, 0))
                cetn = calcular_cet(vparcela, valor_original_cet, parcelas)
                if cetn is None or cetn == "":
                    cet = "CET (Custo Efetivo Total) %am: -"
                else:
                    cet = f"CET (Custo Efetivo Total) %am: {cetn}"

            # Lógica condicional do PHP
            if wall == 's':
                if forma in ["PIX", "DEBITO"]:
                    array = self._criar_array_base(dados, valores_calculados, cpf, nome, cnpj,
                                                  data_formatada, hora, forma, nopwall, autwall, terminal, nsu, cet)
                    array_update = {
                        "voriginal": f"Valor original da loja: R$ {formatar_valor_monetario(valor_original_display)}",
                        "desconto": f"Valor do desconto CLUB: R$ {formatar_valor_monetario(desconto)}",
                    }

                    # Cupom aplicado
                    cupom_codigo = dados.get('cupom_codigo', '')
                    cupom_valor = dados.get('cupom_valor_desconto', 0)
                    if cupom_codigo and cupom_valor:
                        array_update["cupom"] = f"Cupom {cupom_codigo}: -R$ {formatar_valor_monetario(cupom_valor)}"

                    if saldo_cashback_usado > 0:
                        array_update["saldo_usado"] = f"Saldo utilizado de cashback: R$ {formatar_valor_monetario(saldo_cashback_usado)}"

                    if cashback_concedido > 0:
                        array_update["cashback_concedido"] = f"Cashback concedido: R$ {formatar_valor_monetario(cashback_concedido)}"

                    array_update.update({
                        "vdesconto": f"Valor total pago:\nR$ {formatar_valor_monetario(vdesconto_final)}",
                        "pagoavista": f"Valor pago à loja à vista: R$ {formatar_valor_monetario(valores_calculados.get(16, 0))}",
                        "vparcela": f"R$ {formatar_valor_monetario(vparcela_ajustado)}",
                        "tarifas": "Tarifas CLUB: -- ",
                        "encargos": ""
                    })
                    array.update(array_update)

                elif forma in ["PARCELADO SEM JUROS", "A VISTA", "PARCELADO COM JUROS"]:
                    array = self._criar_array_base(dados, valores_calculados, cpf, nome, cnpj,
                                                  data_formatada, hora, forma, nopwall, autwall, terminal, nsu, cet)
                    # Verificar se é encargo ou desconto usando valores[14] (PHP)
                    valores_14 = safe_float_convert(valores_calculados.get(14, 0))
                    registrar_log('posp2', f'🔍 [DECISÃO] valores[14]={valores_14}, parte1={parte1}')
                    if valores_14 < 0:
                        # É ENCARGO (valores[14] negativo)
                        label_desconto = f"Valor total dos encargos: R$ {formatar_valor_monetario(parte1)}"
                        label_vdesconto = f"Valor total pago com encargos:\nR$ {formatar_valor_monetario(vdesconto_final)}"
                        label_encargos = f"Encargos pagos a operadora de cartão: R$ {formatar_valor_monetario(encargos)}"
                    else:
                        # É DESCONTO (valores[14] positivo ou zero)
                        label_desconto = f"Valor do desconto CLUB: R$ {formatar_valor_monetario(parte1)}"
                        label_vdesconto = f"Valor pago com desconto:\nR$ {formatar_valor_monetario(vdesconto_final)}"
                        label_encargos = f"Encargos financeiros: R$ {formatar_valor_monetario(encargos)}"

                    array_update = {
                        "voriginal": f"Valor original da loja: R$ {formatar_valor_monetario(valor_original_display)}",
                        "desconto": label_desconto,
                        "vdesconto": label_vdesconto,
                    }

                    # Cupom aplicado
                    cupom_codigo = dados.get('cupom_codigo', '')
                    cupom_valor = dados.get('cupom_valor_desconto', 0)
                    if cupom_codigo and cupom_valor:
                        array_update["cupom"] = f"Cupom {cupom_codigo}: -R$ {formatar_valor_monetario(cupom_valor)}"

                    if saldo_cashback_usado > 0:
                        array_update["saldo_usado"] = f"Saldo utilizado de cashback: R$ {formatar_valor_monetario(saldo_cashback_usado)}"

                    if cashback_concedido > 0:
                        array_update["cashback_concedido"] = f"Cashback concedido: R$ {formatar_valor_monetario(cashback_concedido)}"

                    array_update.update({
                        "pagoavista": f"Valor pago à loja à vista: R$ {formatar_valor_monetario(valores_calculados.get(16, 0))}",
                        "vparcela": f"R$ {formatar_valor_monetario(vparcela_ajustado)}",
                        "tarifas": f"Tarifas CLUB: R$ {formatar_valor_monetario(tarifas)}",
                        "encargos": label_encargos
                    })
                    array.update(array_update)

            else:  # SEM WALL CLUB
                array = self._criar_array_base(dados, valores_calculados, "", "", cnpj,
                                              data_formatada, hora, forma, nopwall, autwall, terminal, nsu, cet)

                valor_transacao = valores_calculados.get(11, valor_original_display)

                if forma == "DEBITO":
                    array["parcelas"] = 0

                pagoavista_text = "Valor pago à loja a vista" if forma in ["PIX", "DEBITO"] else "Valor pago à loja"
                valor_parcela_individual = valores_calculados.get(20, valor_transacao)

                array.update({
                    "voriginal": f"Valor original da loja: R$ {formatar_valor_monetario(valor_original_display)}",
                    "desconto": "",
                    "vdesconto": f"Valor total pago:\nR$ {formatar_valor_monetario(valor_transacao)}",
                    "pagoavista": f"{pagoavista_text}: R$ {formatar_valor_monetario(valor_transacao)}",
                    "vparcela": f"R$ {formatar_valor_monetario(valor_parcela_individual)}",
                    "tarifas": "Tarifas CLUB: --",
                    "encargos": ""
                })

            return array

        except Exception as e:
            registrar_log('posp2', f'Erro ao gerar slip: {e}', nivel='ERROR')
            import traceback
            registrar_log('posp2', f'Traceback: {traceback.format_exc()}', nivel='ERROR')
            return {}

    def _inserir_base_transacoes_unificadas(self, dados: Dict, valores_calculados: Dict,
                                            data_transacao, nsu: str):
        """
        Insere dados calculados na tabela base_transacoes_unificadas
        Regra: 1 linha por NSU (não duplica parcelas)
        """
        try:
            # Verificar se NSU já existe (evitar duplicação)
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) FROM base_transacoes_unificadas
                    WHERE var9 = %s AND tipo_operacao = 'Wallet'
                """, [str(nsu)])
                existe = cursor.fetchone()[0] > 0

                if existe:
                    registrar_log('posp2', f'⚠️ NSU {nsu} já existe em base_transacoes_unificadas, pulando INSERT')
                    return

            # Preparar dados para inserção
            dados_insert = {
                'tipo_operacao': 'Wallet',
                'adquirente': dados['gateway'],  # PINBANK ou OWN
                'origem_transacao': 'POS',
                'data_transacao': data_transacao,
            }

            # Campos varchar (string)
            varchar_fields = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 43, 45, 57, 59, 65, 66, 68, 69, 70, 71, 96, 97, 98, 99, 100, 102, 119, 120, 121, 122, 123, 126, 129, 130}

            # Mapear var0-var130
            for i in range(131):
                if i in valores_calculados:
                    valor = valores_calculados[i]
                    campo_nome = f'var{i}'

                    if valor is None:
                        dados_insert[campo_nome] = None
                    elif isinstance(valor, dict):
                        valor_final = valor.get('0', str(valor))
                        if i in varchar_fields:
                            dados_insert[campo_nome] = str(valor_final)
                        else:
                            try:
                                dados_insert[campo_nome] = float(valor_final)
                            except (ValueError, TypeError):
                                dados_insert[campo_nome] = None
                    else:
                        if i in varchar_fields:
                            dados_insert[campo_nome] = str(valor)
                        else:
                            try:
                                dados_insert[campo_nome] = float(valor)
                            except (ValueError, TypeError):
                                dados_insert[campo_nome] = None

            # Inserir usando raw SQL
            campos = list(dados_insert.keys())
            valores = list(dados_insert.values())
            placeholders = ', '.join(['%s'] * len(valores))
            campos_str = ', '.join(campos)

            with connection.cursor() as cursor:
                cursor.execute(f"""
                    INSERT INTO base_transacoes_unificadas ({campos_str})
                    VALUES ({placeholders})
                """, valores)

            registrar_log('posp2', f'✅ Inserido em base_transacoes_unificadas - NSU: {nsu}')

        except Exception as e:
            registrar_log('posp2', f'❌ Erro ao inserir em base_transacoes_unificadas: {str(e)}', nivel='ERROR')
            # Não interromper o fluxo

    def _enviar_push_notification(self, dados: Dict, valores_calculados: Dict,
                                   loja_info: Dict, canal_id: int, data_transacao_dt: datetime):
        """Envia push notification para o cliente após processamento da transação"""
        try:
            from wallclub_core.integracoes.notification_service import NotificationService

            # Obter CPF do cliente - garantir formato correto sem pontos e traços
            cpf = dados.get('cpf')
            if not cpf:
                registrar_log('posp2', 'Push não enviado: CPF não encontrado')
                return

            # Remover pontos e traços para garantir formato correto
            cpf = cpf.replace('.', '').replace('-', '')
            registrar_log('posp2', f'CPF formatado para envio de push: {cpf}')

            # Validar que o cliente existe neste canal específico
            try:
                from wallclub_core.integracoes.api_interna_service import APIInternaService

                response = APIInternaService.chamar_api_interna(
                    metodo='POST',
                    endpoint='/api/internal/cliente/consultar_por_cpf/',
                    payload={'cpf': cpf, 'canal_id': canal_id},
                    contexto='apis'
                )

                cliente_canal = response.get('cliente') if response.get('sucesso') else None

                if not cliente_canal or not cliente_canal.get('is_active'):
                    registrar_log('posp2', f'Push não enviado: Cliente {cpf} não encontrado ou inativo no canal {canal_id}')
                    return

                registrar_log('posp2', f'Cliente {cpf} confirmado no canal {canal_id}')

            except Exception as e:
                registrar_log('posp2', f'Erro ao validar cliente: {str(e)}', nivel='WARNING')
                return

            # Calcular valor final para push (usar amount se valores_calculados[26] for None)
            valor_transacao = valores_calculados.get(26)
            if not valor_transacao or valor_transacao == 0:
                # Usar amount (valor cobrado do cartão)
                amount_centavos = dados.get('amount', 0)
                if amount_centavos:
                    valor_transacao = float(amount_centavos) / 100
                else:
                    valor_transacao = float(dados.get('valor_original', 0))

            registrar_log('posp2', f'Valor final para push: {valor_transacao}')

            # Usar loja_info para obter o nome do estabelecimento
            nome_estabelecimento = loja_info.get('loja', 'Estabelecimento')
            registrar_log('posp2', f'Nome do estabelecimento: {nome_estabelecimento}')

            # Preparar dados da transação para notificação
            notification_data = {
                'valor': valor_transacao,
                'tipo_transacao': valores_calculados.get('tipo_transacao', 'Compra'),
                'estabelecimento': nome_estabelecimento,
                'data_hora': data_transacao_dt.strftime('%Y-%m-%d %H:%M:%S'),
                'id': dados.get('nsu_gateway', '0')
            }

            # Inicializar serviço unificado de notificação para o canal
            notification_service = NotificationService.get_instance(canal_id)

            registrar_log('posp2', f'Enviando push notification para CPF {cpf} no canal {canal_id}')

            try:
                # Extrair dados da notificação
                valor_formatado = notification_data.get('valor', '0,00')
                estabelecimento = notification_data.get('estabelecimento', 'Estabelecimento')
                tipo_transacao = notification_data.get('tipo_transacao', 'Transação')

                push_result = notification_service.send_push(
                    cpf=cpf,
                    id_template='transacao_aprovada',
                    tipo_transacao=tipo_transacao,
                    valor=valor_formatado,
                    estabelecimento=estabelecimento,
                    data_hora=notification_data.get('data_hora', ''),
                    transacao_id=notification_data.get('id', '')
                )
                registrar_log('posp2', f'✅ Push notification enviado: {push_result}')
            except Exception as push_error:
                registrar_log('posp2', f'ERRO ao enviar push: {str(push_error)}', nivel='ERROR')
                import traceback
                registrar_log('posp2', f'Traceback: {traceback.format_exc()}', nivel='ERROR')

        except Exception as e:
            # Não interromper o fluxo se houver erro no envio da notificação
            registrar_log('posp2', f'Erro ao enviar push notification: {str(e)}', nivel='WARNING')
