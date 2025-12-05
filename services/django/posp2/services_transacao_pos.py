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
        
        dados_normalizados = self._parse_payload_pinbank(dados_json)
        return self._processar_comum(dados_normalizados)

    def processar_transacao_own(self, dados_json: str) -> Dict[str, Any]:
        """Endpoint /trdata_own/"""
        registrar_log('posp2', '========================================')
        registrar_log('posp2', f'{datetime.now().strftime("%d/%m/%Y %H:%M:%S")} - Processamento Own')
        registrar_log('posp2', '========================================')
        
        dados_normalizados = self._parse_payload_own(dados_json)
        return self._processar_comum(dados_normalizados)

    # ========================================
    # PARSERS ESPECÍFICOS
    # ========================================

    def _parse_payload_pinbank(self, dados_json: str) -> Dict:
        """Parse específico para Pinbank"""
        try:
            dados = json.loads(dados_json)
            trdata = json.loads(dados.get('trdata', '{}'))
            
            # Extrair cashback
            cashback_wall_data = trdata.get('cashback_wall', {})
            cashback_loja_data = trdata.get('cashback_loja', {})
            
            dados_normalizados = {
                'gateway': 'PINBANK',
                
                # Dados básicos
                'celular': dados.get('celular', ''),
                'cpf': dados.get('cpf', ''),
                'terminal': dados.get('terminal', ''),
                'operador_pos': dados.get('operador_pos', ''),
                'valor_original': self._converter_valor_monetario(dados.get('valororiginal', '')),
                
                # Identificadores Pinbank
                'nsu_gateway': trdata.get('nsuPinbank', ''),
                'nsuAcquirer': trdata.get('nsuAcquirer', ''),
                'nsuTerminal': trdata.get('nsuTerminal', ''),
                'nsuHost': None,
                'authorizationCode': trdata.get('authorizationCode', ''),
                'transactionReturn': trdata.get('transactionReturn', ''),
                
                # Valores
                'amount': int(trdata.get('amount', 0)),
                'originalAmount': int(trdata.get('originalAmount', 0)),
                'totalInstallments': int(trdata.get('totalInstallments', 1)),
                
                # Método de pagamento
                'paymentMethod': trdata.get('paymentMethod', ''),
                'operationId': None,
                'brand': trdata.get('brand', ''),
                'cardNumber': trdata.get('cardNumber', ''),
                'cardName': trdata.get('cardName', ''),
                
                # Timestamps
                'hostTimestamp': str(trdata.get('hostTimestamp', '')),
                'terminalTimestamp': int(trdata.get('terminalTimestamp', 0)),
                
                # Específico Own (NULL)
                'sdk': None,
                'customerTicket': None,
                'estabTicket': None,
                'e2ePixId': None,
                
                # Wall Club
                'modalidade_wall': dados.get('modalidade_wall', ''),
                'autorizacao_id': dados.get('autorizacao_id', ''),
                'valor_desconto': float(dados.get('valor_desconto', 0)),
                'valor_cashback': float(dados.get('valor_cashback', 0)),
                'cashback_concedido': float(dados.get('cashback_concedido', 0)),
                
                # Cupom
                'cupom_codigo': trdata.get('cupom_codigo', ''),
                'cupom_valor_desconto': Decimal(str(trdata.get('cupom_valor_desconto', 0))),
                
                # Cashback centralizado
                'cashback_wall_parametro_id': cashback_wall_data.get('parametro_id') if cashback_wall_data else None,
                'cashback_wall_valor': Decimal(str(cashback_wall_data.get('valor', 0))) if cashback_wall_data else Decimal('0'),
                'cashback_loja_regra_id': cashback_loja_data.get('regra_id') if cashback_loja_data else None,
                'cashback_loja_valor': Decimal(str(cashback_loja_data.get('valor', 0))) if cashback_loja_data else Decimal('0'),
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
            
            # Extrair cashback
            cashback_wall_data = trdata.get('cashback_wall', {})
            cashback_loja_data = trdata.get('cashback_loja', {})
            
            dados_normalizados = {
                'gateway': 'OWN',
                
                # Dados básicos
                'celular': dados.get('celular', ''),
                'cpf': dados.get('cpf', ''),
                'terminal': dados.get('terminal', ''),
                'operador_pos': dados.get('operador_pos', ''),
                'valor_original': self._converter_valor_monetario(dados.get('valororiginal', '')),
                
                # Identificadores Own
                'nsu_gateway': trdata.get('txTransactionId', ''),
                'nsuAcquirer': None,
                'nsuTerminal': trdata.get('nsuTerminal', ''),
                'nsuHost': trdata.get('nsuHost', ''),
                'authorizationCode': trdata.get('authorizationCode', ''),
                'transactionReturn': trdata.get('transactionReturn', ''),
                
                # Valores
                'amount': int(trdata.get('amount', 0)),
                'originalAmount': int(trdata.get('originalAmount', 0)),
                'totalInstallments': int(trdata.get('totalInstallments', 1)),
                
                # Método de pagamento
                'paymentMethod': trdata.get('paymentMethod', ''),
                'operationId': int(trdata.get('operationId', 1)),
                'brand': trdata.get('brand', ''),
                'cardNumber': trdata.get('cardNumber', ''),
                'cardName': trdata.get('cardName', ''),
                
                # Timestamps
                'hostTimestamp': str(trdata.get('hostTimestamp', '')),
                'terminalTimestamp': int(trdata.get('terminalTimestamp', 0)),
                
                # Específico Own
                'sdk': trdata.get('sdk', 'agilli'),
                'customerTicket': trdata.get('customerTicket', ''),
                'estabTicket': trdata.get('estabTicket', ''),
                'e2ePixId': trdata.get('e2ePixId', ''),
                
                # Wall Club
                'modalidade_wall': dados.get('modalidade_wall', ''),
                'autorizacao_id': dados.get('autorizacao_id', ''),
                'valor_desconto': float(dados.get('valor_desconto', 0)),
                'valor_cashback': float(dados.get('valor_cashback', 0)),
                'cashback_concedido': float(dados.get('cashback_concedido', 0)),
                
                # Cupom
                'cupom_codigo': trdata.get('cupom_codigo', ''),
                'cupom_valor_desconto': Decimal(str(trdata.get('cupom_valor_desconto', 0))),
                
                # Cashback centralizado
                'cashback_wall_parametro_id': cashback_wall_data.get('parametro_id') if cashback_wall_data else None,
                'cashback_wall_valor': Decimal(str(cashback_wall_data.get('valor', 0))) if cashback_wall_data else Decimal('0'),
                'cashback_loja_regra_id': cashback_loja_data.get('regra_id') if cashback_loja_data else None,
                'cashback_loja_valor': Decimal(str(cashback_loja_data.get('valor', 0))) if cashback_loja_data else Decimal('0'),
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
            
            # 2. Buscar loja_id e canal_id
            loja_id, canal_id = self._buscar_loja_canal(dados['terminal'])
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
            
            # 7. Calcular valores via CalculadoraBaseGestao (COMUM)
            # TODO: Implementar quando necessário
            
            registrar_log('posp2', 'Processamento concluído com sucesso')
            
            return {
                'sucesso': True,
                'mensagem': 'Dados processados com sucesso',
                'transaction_id': transaction_id
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
        """Busca loja_id e canal_id pelo terminal"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT l.id, l.canal_id
                FROM terminais t
                INNER JOIN loja l ON t.loja_id = l.id
                WHERE t.terminal = %s
            """, [terminal])
            row = cursor.fetchone()
            if row:
                registrar_log('posp2', f'Loja encontrada: loja_id={row[0]}, canal_id={row[1]}')
                return row[0], row[1]
            return None, None

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
                    cashback_wall_parametro_id, cashback_loja_regra_id
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s,
                    %s, %s
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
                dados['cashback_wall_parametro_id'], dados['cashback_loja_regra_id']
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
