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
from parametros_wallclub.calculadora_base_gestao import CalculadoraBaseGestao
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

            # 2. Buscar loja_id, canal_id e nomes
            loja_id, canal_id, nome_canal, razao_social = self._buscar_loja_canal(dados['terminal'])
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

            # 6. Conceder cashback via sistema centralizado (COMUM)
            self._conceder_cashback(
                dados, transaction_id, loja_id, canal_id
            )

            # 7. Calcular valores via CalculadoraBaseGestao e gerar slip
            tipo_compra = self.TIPO_COMPRA_MAP.get(dados['paymentMethod'], dados['paymentMethod'])
            
            dados_linha = {
                'id': transaction_id,
                'DataTransacao': datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
                'SerialNumber': dados['terminal'],
                'idTerminal': dados['terminal'],
                'cpf': dados['cpf'],
                'TipoCompra': tipo_compra,
                'NsuOperacao': dados['nsu_gateway'],
                'nsuAcquirer': dados['nsuAcquirer'],
                'valor_original': dados['valor_original'],
                'ValorBruto': dados['valor_original'],
                'ValorBrutoParcela': dados['valor_original'],
                'Bandeira': dados['brand'],
                'NumeroTotalParcelas': dados['totalInstallments'],
                'ValorTaxaAdm': 0,
                'ValorTaxaMes': 0,
                'ValorSplit': 0,
                'DescricaoStatus': 'Processado',
                'DescricaoStatusPagamento': 'Pendente',
                'IdStatusPagamento': 1,
                'DataCancelamento': None,
                'DataFuturaPagamento': None
            }

            # 7. Calcular valores (passar info_loja e info_canal já resolvidos)
            loja_info = {'id': loja_id, 'loja_id': loja_id, 'loja': razao_social, 'canal_id': canal_id}
            canal_info = {'id': canal_id, 'canal_id': canal_id, 'canal': nome_canal}
            calculadora = CalculadoraBaseGestao()
            valores_calculados = calculadora.calcular_valores_primarios(
                dados_linha, 
                tabela='transactiondata_pos',
                info_loja=loja_info,
                info_canal=canal_info
            )
            registrar_log('posp2', f'✅ Valores calculados: {len(valores_calculados)} campos')

            # 8. Gerar slip de impressão
            slip = self._gerar_slip_impressao(dados, valores_calculados, loja_info)

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
        """Busca loja_id, canal_id e nome_canal pelo terminal"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT l.id, l.canal_id, c.nome, l.razao_social
                FROM terminais t
                INNER JOIN loja l ON t.loja_id = l.id
                INNER JOIN canal c ON l.canal_id = c.id
                WHERE t.terminal = %s
            """, [terminal])
            row = cursor.fetchone()
            if row:
                registrar_log('posp2', f'Loja encontrada: loja_id={row[0]}, canal_id={row[1]}')
                return row[0], row[1], row[2], row[3]  # loja_id, canal_id, nome_canal, razao_social
            return None, None, None, None

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

            saldo_cashback_usado = 0.0
            cashback_concedido = safe_float_convert(dados.get('cashback_concedido', 0))
            
            vdesconto_final = parte0 - saldo_cashback_usado
            vparcela_ajustado = vdesconto_final / parcelas if parcelas > 0 else vdesconto_final

            # Data e hora
            agora = datetime.now()
            data_formatada = valores_calculados.get(0, agora.strftime('%Y-%m-%d'))
            hora = agora.strftime('%H:%M:%S')
            
            # CET para parcelado
            cet = ""
            if parcelas > 1:
                from parametros_wallclub.calculadora_base_gestao import calcular_cet
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
