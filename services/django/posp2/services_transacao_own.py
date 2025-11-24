"""
Service para processar transações POS via SDK Ágilli (Own Financial)
Estrutura específica e otimizada para transações Own
"""

import json
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional
from django.db import connection
from wallclub_core.utilitarios.log_control import registrar_log
from parametros_wallclub.calculadora_base_gestao import CalculadoraBaseGestao
from parametros_wallclub.services import ParametrosService


class TRDataOwnService:
    """
    Service para processar dados de transações Own/Ágilli
    Endpoint: /trdata_own/
    Replicando EXATAMENTE a lógica do TRDataService (Pinbank)
    """

    # Mapeamento centralizado de PaymentMethod para TipoCompra (IGUAL AO PINBANK)
    TIPO_COMPRA_MAP = {
        'CREDIT_IN_INSTALLMENTS_WITHOUT_INTEREST': 'PARCELADO SEM JUROS',
        'CREDIT_ONE_INSTALLMENT': 'A VISTA',
        'DEBIT': 'DEBITO',
        'CASH': 'PIX'
    }

    def __init__(self):
        self.parametros_service = ParametrosService()

    def processar_dados_transacao(self, dados_json: str) -> Dict[str, Any]:
        """
        Processa dados de transação Own e gera informações para comprovante

        Args:
            dados_json: JSON bruto com todos os dados da requisição
        """
        try:
            registrar_log('posp2', '========================================')
            registrar_log('posp2', f'{datetime.now().strftime("%d/%m/%Y %H:%M:%S")} - Processamento Transação Own')
            registrar_log('posp2', '========================================')
            registrar_log('posp2', f'JSON Recebido: {dados_json}')

            # Parse do JSON recebido
            try:
                dados = json.loads(dados_json)
            except json.JSONDecodeError as e:
                registrar_log('posp2', f'Erro ao decodificar JSON: {e}', nivel='ERROR')
                return {
                    'sucesso': False,
                    'mensagem': f'Erro ao decodificar JSON: {e}'
                }

            # 1. Extrair parâmetros do JSON
            celular = dados.get('celular', '')
            cpf = dados.get('cpf', '')
            trdata = dados.get('trdata', '')
            terminal = dados.get('terminal', '')
            valororiginal = dados.get('valororiginal', '')
            operador_pos = dados.get('operador_pos', '')

            # Extrair valores Wall Club (podem vir do POS ou serão calculados)
            valor_desconto_pos = dados.get('valor_desconto', 0)
            valor_cashback_pos = dados.get('valor_cashback', 0)
            cashback_concedido_pos = dados.get('cashback_concedido', 0)
            autorizacao_id = dados.get('autorizacao_id', '')
            modalidade_wall = dados.get('modalidade_wall', '')
            
            # Flag para indicar se é Wall Club
            wall_club = 'S' if cpf and cpf.strip() else 'N'
            
            # Extrair cupom (opcional)
            cupom_codigo = dados.get('cupom_codigo', '')

            registrar_log('posp2', f'📥 Recebido request /trdata_own/ - Terminal: {terminal}, CPF: {cpf}, Valor: {valororiginal}')

            # 2. Validar dados obrigatórios
            if not trdata or not terminal or not valororiginal:
                return {
                    'sucesso': False,
                    'mensagem': 'Campos obrigatórios ausentes: trdata, terminal ou valororiginal'
                }

            # 3. Parse do JSON trdata
            try:
                dados_trdata = json.loads(trdata)
                registrar_log('posp2', f'TrData decodificado - Campos: {", ".join(dados_trdata.keys())}')
            except json.JSONDecodeError as e:
                registrar_log('posp2', f'Erro ao decodificar trdata: {e}', nivel='ERROR')
                return {
                    'sucesso': False,
                    'mensagem': f'Erro ao decodificar trdata: {e}'
                }

            # 4. Validar SDK
            sdk = dados_trdata.get('sdk', '')
            if sdk != 'agilli':
                registrar_log('posp2', f'⚠️ SDK inválido: {sdk} (esperado: agilli)', nivel='WARNING')

            # 5. Extrair campos específicos Own
            tx_transaction_id = dados_trdata.get('txTransactionId', '')
            if not tx_transaction_id:
                return {
                    'sucesso': False,
                    'mensagem': 'Campo txTransactionId ausente no trdata'
                }

            # Verificar duplicidade
            if self._transacao_existe(tx_transaction_id):
                registrar_log('posp2', f'⚠️ Transação duplicada: {tx_transaction_id}', nivel='WARNING')
                return {
                    'sucesso': False,
                    'mensagem': f'Transação já processada: {tx_transaction_id}'
                }

            # 6. Converter valor original (usar amount em centavos, não valororiginal)
            amount_centavos = int(dados_trdata.get('amount', 0))
            valor_original = amount_centavos / 100.0  # Converter centavos para reais
            
            # 6.0. Buscar loja_id para cálculo de desconto
            loja_id = None
            canal_id = None
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT l.id, l.canal_id
                    FROM terminais t
                    INNER JOIN loja l ON t.loja_id = l.id
                    WHERE t.terminal = %s
                """, [terminal])
                loja_row = cursor.fetchone()
                if loja_row:
                    loja_id = loja_row[0]
                    canal_id = loja_row[1]
            
            # 6.0.1. Calcular desconto Wall Club (se CPF informado e valor_desconto não veio do POS)
            if wall_club == 'S' and loja_id and valor_desconto_pos == 0:
                try:
                    from parametros_wallclub.services import CalculadoraDesconto
                    
                    calculadora_desconto = CalculadoraDesconto()
                    
                    # Mapear paymentMethod para forma
                    payment_method = dados_trdata.get('paymentMethod', '')
                    parcelas = int(dados_trdata.get('totalInstallments', 1))
                    
                    # Mapear para formato esperado pela calculadora
                    forma_map = {
                        'CREDIT_ONE_INSTALLMENT': 'credito',
                        'CREDIT_IN_INSTALLMENTS_WITHOUT_INTEREST': 'credito',
                        'DEBIT': 'debito',
                        'PIX': 'pix',
                        'VOUCHER': 'voucher'
                    }
                    forma = forma_map.get(payment_method, 'credito')
                    
                    data_atual = datetime.now().strftime('%Y-%m-%d')
                    
                    registrar_log('posp2', f'🧮 Calculando desconto: valor={valor_original}, forma={forma}, parcelas={parcelas}, loja_id={loja_id}')
                    
                    # calcular_desconto retorna o valor FINAL (com desconto aplicado), não o desconto
                    valor_final = calculadora_desconto.calcular_desconto(
                        valor_original=Decimal(str(valor_original)),
                        data=data_atual,
                        forma=forma,
                        parcelas=parcelas,
                        id_loja=loja_id,
                        wall='S'
                    )
                    
                    if valor_final and valor_final < Decimal(str(valor_original)):
                        # Desconto = valor_original - valor_final
                        valor_desconto_pos = float(Decimal(str(valor_original)) - valor_final)
                        registrar_log('posp2', f'✅ Desconto calculado: R$ {valor_desconto_pos:.2f} (valor_final={float(valor_final):.2f})')
                        
                        # Calcular cashback sobre valor COM desconto (valor_final)
                        valor_final_cashback = calculadora_desconto.calcular_desconto(
                            valor_original=valor_final,
                            data=data_atual,
                            forma=forma,
                            parcelas=parcelas,
                            id_loja=loja_id,
                            wall='C'
                        )
                        
                        if valor_final_cashback and valor_final_cashback < valor_final:
                            # Cashback = valor_final - valor_final_cashback
                            cashback_concedido_pos = float(valor_final - valor_final_cashback)
                            registrar_log('posp2', f'✅ Cashback calculado: R$ {cashback_concedido_pos:.2f}')
                    
                except Exception as e:
                    registrar_log('posp2', f'⚠️ Erro ao calcular desconto: {e}', nivel='WARNING')
            
            # 6.1. Aplicar cupom (opcional)
            cupom_obj = None
            cupom_id = None
            cupom_valor_desconto = Decimal('0.00')
            
            if cupom_codigo:
                try:
                    from apps.cupom.services import CupomService
                    from apps.cliente.models import Cliente
                    
                    registrar_log('posp2', f'🎟️ Validando cupom: {cupom_codigo}')
                    
                    # Buscar loja_id e cliente_id
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            SELECT l.id, l.canal_id
                            FROM terminais t
                            INNER JOIN loja l ON t.loja_id = l.id
                            WHERE t.terminal = %s
                        """, [terminal])
                        loja_row = cursor.fetchone()
                        
                        if not loja_row:
                            raise ValueError(f"Terminal {terminal} não encontrado")
                        
                        loja_id = loja_row[0]
                        canal_id = loja_row[1]
                    
                    # Buscar cliente_id pelo CPF
                    cliente_id = None
                    if cpf:
                        try:
                            cliente = Cliente.objects.get(cpf=cpf, canal_id=canal_id)
                            cliente_id = cliente.id
                        except Cliente.DoesNotExist:
                            registrar_log('posp2', f'⚠️ Cliente não encontrado: CPF={cpf}', nivel='WARNING')
                    
                    if not cliente_id:
                        raise ValueError("CPF do cliente é obrigatório para usar cupom")
                    
                    # Validar cupom
                    cupom_service = CupomService()
                    cupom_obj = cupom_service.validar_cupom(
                        codigo=cupom_codigo,
                        loja_id=loja_id,
                        cliente_id=cliente_id,
                        valor_transacao=Decimal(str(valor_original))
                    )
                    
                    # Calcular desconto
                    cupom_valor_desconto = cupom_service.calcular_desconto(
                        cupom_obj, 
                        Decimal(str(valor_original))
                    )
                    cupom_id = cupom_obj.id
                    
                    registrar_log('posp2', f'✅ Cupom validado: {cupom_codigo}, desconto: R$ {cupom_valor_desconto}')
                    
                except Exception as e:
                    registrar_log('posp2', f'❌ Erro ao validar cupom: {e}', nivel='ERROR')
                    return {
                        'sucesso': False,
                        'mensagem': f'Erro ao validar cupom: {str(e)}'
                    }

            # 7. Preparar dados para inserção
            dados_para_inserir = {
                'datahora': datetime.now(),
                'valor_original': valor_original,
                'celular': celular or None,
                'cpf': cpf or None,
                'terminal': terminal,
                'operador_pos': operador_pos or None,

                # Identificadores Own
                'txTransactionId': tx_transaction_id,
                'nsuTerminal': dados_trdata.get('nsuTerminal', ''),
                'nsuHost': dados_trdata.get('nsuHost', ''),
                'authorizationCode': dados_trdata.get('authorizationCode', ''),
                'transactionReturn': dados_trdata.get('transactionReturn', ''),

                # Valores
                'amount': int(dados_trdata.get('amount', 0)),
                'originalAmount': int(dados_trdata.get('originalAmount', 0)),
                'totalInstallments': int(dados_trdata.get('totalInstallments', 1)),

                # Método de pagamento
                'operationId': int(dados_trdata.get('operationId', 1)),
                'paymentMethod': dados_trdata.get('paymentMethod', ''),

                # Cartão
                'brand': dados_trdata.get('brand', ''),
                'cardNumber': dados_trdata.get('cardNumber', ''),
                'cardName': dados_trdata.get('cardName', ''),

                # Comprovantes Ágilli
                'customerTicket': dados_trdata.get('customerTicket', ''),
                'estabTicket': dados_trdata.get('estabTicket', ''),
                'e2ePixId': dados_trdata.get('e2ePixId', ''),

                # Timestamps
                'terminalTimestamp': int(dados_trdata.get('terminalTimestamp', 0)),
                'hostTimestamp': int(dados_trdata.get('hostTimestamp', 0)),

                # Status
                'status': dados_trdata.get('status', 'APPROVED'),
                'capturedTransaction': 1,

                # Estabelecimento
                'cnpj': dados_trdata.get('cnpj', ''),

                # SDK
                'sdk': sdk or 'agilli',

                # Wall Club
                'valor_desconto': self._converter_valor_monetario(valor_desconto_pos),
                'valor_cashback': self._converter_valor_monetario(valor_cashback_pos),
                'cashback_concedido': self._converter_valor_monetario(cashback_concedido_pos),
                'autorizacao_id': autorizacao_id or None,
                'saldo_usado': 0,
                'modalidade_wall': modalidade_wall or None,
                
                # Cupom
                'cupom_id': cupom_id,
                'cupom_valor_desconto': float(cupom_valor_desconto) if cupom_valor_desconto else None,
            }

            # 8. Inserir na base
            transaction_id = self._inserir_transacao(dados_para_inserir)

            if not transaction_id:
                return {
                    'sucesso': False,
                    'mensagem': 'Erro ao inserir transação no banco'
                }

            registrar_log('posp2', f'✅ Transação Own inserida: ID={transaction_id}, TxID={tx_transaction_id}')
            
            # 8.1. Registrar uso do cupom (se aplicado)
            if cupom_obj and cupom_id:
                try:
                    from apps.cupom.services import CupomService
                    
                    cupom_service = CupomService()
                    cupom_service.registrar_uso(
                        cupom=cupom_obj,
                        cliente_id=cliente_id,
                        loja_id=loja_id,
                        transacao_tipo='POS',
                        transacao_id=transaction_id,
                        valor_original=Decimal(str(valor_original)),
                        valor_desconto=cupom_valor_desconto,
                        valor_final=Decimal(str(valor_original)) - cupom_valor_desconto,
                        nsu=dados_trdata.get('nsuHost', ''),
                        ip_address=None
                    )
                    
                    registrar_log('posp2', f'✅ Uso do cupom registrado: {cupom_codigo}')
                    
                except Exception as e:
                    registrar_log('posp2', f'⚠️ Erro ao registrar uso do cupom: {e}', nivel='WARNING')

            # 9. BUSCAR DADOS DA TRANSAÇÃO INSERIDA PARA CALCULADORA
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT t.id, t.datahora, t.terminal, t.cpf, t.paymentMethod, t.nsuHost,
                           t.txTransactionId, t.valor_original, t.brand, t.totalInstallments,
                           l.id as loja_id, l.canal_id, l.cnpj
                    FROM transactiondata_own t
                    INNER JOIN terminais term ON t.terminal = term.terminal
                    INNER JOIN loja l ON term.loja_id = l.id
                    WHERE t.id = %s
                """, [transaction_id])

                row = cursor.fetchone()
                if not row:
                    registrar_log('posp2', 'Erro: transação não encontrada após inserção', nivel='ERROR')
                    valores_calculados = {}
                else:
                    registrar_log('posp2', f'🔍 Row retornado: {len(row)} campos')
                    registrar_log('posp2', f'🔍 CNPJ da loja (row[12]): {row[12] if len(row) > 12 else "ÍNDICE INVÁLIDO"}')
                    
                    # Preparar dados_linha para calculadora
                    dados_linha = {
                        'id': row[0],
                        'DataTransacao': row[1].strftime('%Y-%m-%dT%H:%M:%S'),
                        'SerialNumber': row[2],
                        'idTerminal': row[2],
                        'cpf': row[3] or '',
                        'TipoCompra': self.TIPO_COMPRA_MAP.get(row[4], row[4]),
                        'NsuOperacao': row[5],
                        'nsuAcquirer': row[6],
                        'valor_original': Decimal(str(row[7])),
                        'ValorBruto': Decimal(str(row[7])),
                        'ValorBrutoParcela': Decimal(str(row[7])),
                        'Bandeira': row[8],
                        'NumeroTotalParcelas': row[9],
                        'ValorTaxaAdm': 0,
                        'ValorTaxaMes': 0,
                        'ValorSplit': 0,
                        'DescricaoStatus': 'Processado',
                        'DescricaoStatusPagamento': 'Pendente',
                        'IdStatusPagamento': 1,
                        'DataCancelamento': None,
                        'DataFuturaPagamento': None,
                        'loja_id': row[10],
                        'canal_id': row[11],
                        'cnpjCpfParceiro': row[12] if len(row) > 12 else None  # Nome esperado pela calculadora
                    }
                    
                    registrar_log('posp2', f'🔍 dados_linha[cnpjCpfParceiro]: {dados_linha.get("cnpjCpfParceiro")}')

                    # Calcular valores
                    calculadora = CalculadoraBaseGestao()
                    try:
                        valores_calculados = calculadora.calcular_valores_primarios(dados_linha, tabela='transactiondata_own')
                        registrar_log('posp2', f'Calculadora executada - {len(valores_calculados)} valores')
                    except Exception as e:
                        registrar_log('posp2', f'ERRO na calculadora: {e}', nivel='ERROR')
                        valores_calculados = {}

            # 10. Buscar informações da loja
            info_loja = self._buscar_info_loja(terminal)

            # 11. Buscar nome do cliente
            nome_cliente = self._buscar_nome_cliente(cpf) if cpf else ''

            # 12. Gerar slip de impressão
            json_resposta = self._gerar_slip_impressao(
                dados_trdata,
                info_loja,
                cpf,
                nome_cliente,
                valores_calculados,
                valor_original,
                valor_desconto_pos,
                valor_cashback_pos,
                cashback_concedido_pos,
                autorizacao_id
            )

            # 12. Retornar dados completos para comprovante
            resposta_final = {
                'sucesso': True,
                'mensagem': 'Dados processados com sucesso',
                **json_resposta
            }

            registrar_log('posp2', f'JSON de Resposta: {json.dumps(resposta_final, ensure_ascii=False)}')

            return resposta_final

        except Exception as e:
            import traceback
            erro_completo = traceback.format_exc()
            registrar_log('posp2', f'❌ ERRO CRÍTICO ao processar transação: {e}', nivel='ERROR')
            registrar_log('posp2', f'Traceback completo:\n{erro_completo}', nivel='ERROR')
            print(f"[ERRO TRDataOwnService] {e}")
            print(erro_completo)
            return {
                'sucesso': False,
                'mensagem': f'Erro ao processar transação: {e}'
            }

    def _transacao_existe(self, tx_transaction_id: str) -> bool:
        """Verifica se transação já existe na base"""
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM transactiondata_own WHERE txTransactionId = %s",
                [tx_transaction_id]
            )
            count = cursor.fetchone()[0]
            return count > 0

    def _inserir_transacao(self, dados: Dict[str, Any]) -> Optional[int]:
        """Insere transação na base e retorna o ID"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO transactiondata_own (
                        datahora, valor_original, celular, cpf, terminal, operador_pos,
                        txTransactionId, nsuTerminal, nsuHost, authorizationCode, transactionReturn,
                        amount, originalAmount, totalInstallments,
                        operationId, paymentMethod,
                        brand, cardNumber, cardName,
                        customerTicket, estabTicket, e2ePixId,
                        terminalTimestamp, hostTimestamp,
                        status, capturedTransaction,
                        cnpj, sdk,
                        valor_desconto, valor_cashback, cashback_concedido, autorizacao_id,
                        saldo_usado, modalidade_wall,
                        cupom_id, cupom_valor_desconto
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s,
                        %s, %s,
                        %s, %s,
                        %s, %s, %s, %s,
                        %s, %s,
                        %s, %s
                    )
                """, [
                    dados['datahora'], dados['valor_original'], dados['celular'], dados['cpf'],
                    dados['terminal'], dados['operador_pos'],
                    dados['txTransactionId'], dados['nsuTerminal'], dados['nsuHost'],
                    dados['authorizationCode'], dados['transactionReturn'],
                    dados['amount'], dados['originalAmount'], dados['totalInstallments'],
                    dados['operationId'], dados['paymentMethod'],
                    dados['brand'], dados['cardNumber'], dados['cardName'],
                    dados['customerTicket'], dados['estabTicket'], dados['e2ePixId'],
                    dados['terminalTimestamp'], dados['hostTimestamp'],
                    dados['status'], dados['capturedTransaction'],
                    dados['cnpj'], dados['sdk'],
                    dados['valor_desconto'], dados['valor_cashback'], dados['cashback_concedido'],
                    dados['autorizacao_id'], dados['saldo_usado'], dados['modalidade_wall'],
                    dados['cupom_id'], dados['cupom_valor_desconto']
                ])

                return cursor.lastrowid

        except Exception as e:
            registrar_log('posp2', f'Erro ao inserir transação: {e}', nivel='ERROR')
            return None

    def _buscar_info_loja(self, terminal: str) -> Dict[str, Any]:
        """Busca informações da loja pelo terminal"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT l.id, l.razao_social, l.cnpj
                    FROM terminais t
                    INNER JOIN loja l ON t.loja_id = l.id
                    WHERE t.terminal = %s
                """, [terminal])

                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'nome_fantasia': row[1],
                        'cnpj': row[2]
                    }
        except Exception as e:
            registrar_log('posp2', f'Erro ao buscar loja: {e}', nivel='ERROR')

        return {
            'id': None,
            'nome_fantasia': '',
            'cnpj': ''
        }

    def _buscar_nome_cliente(self, cpf: str) -> str:
        """Busca nome do cliente pelo CPF"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT nome
                    FROM cliente
                    WHERE cpf = %s
                    LIMIT 1
                """, [cpf])

                row = cursor.fetchone()
                if row:
                    return row[0] or ''
        except Exception as e:
            registrar_log('posp2', f'Erro ao buscar nome cliente: {e}', nivel='ERROR')

        return ''

    def _converter_valor_monetario(self, valor) -> float:
        """Converte valor monetário para float"""
        if isinstance(valor, str):
            # Remover formatação monetária brasileira
            valor = valor.replace('R$', '').replace(' ', '').strip()

            # Tratar formato brasileiro: R$17,00 -> 17.00
            if ',' in valor and '.' not in valor:
                valor = valor.replace(',', '.')
            elif ',' in valor and '.' in valor:
                # Formato com milhares: 1.234,56 -> 1234.56
                if valor.rfind(',') > valor.rfind('.'):
                    valor = valor.replace('.', '').replace(',', '.')
                else:
                    valor = valor.replace(',', '')

            return float(valor) if valor else 0.0

        return float(valor) if valor else 0.0

    def _gerar_slip_impressao(self, dados: Dict[str, Any], info_loja: Dict[str, Any],
                              cpf: str, nome: str, valores_calculados: Dict,
                              valor_original: float, valor_desconto: float,
                              valor_cashback: float, cashback_concedido: float,
                              autorizacao_id: str) -> Dict[str, Any]:
        """Gera JSON de resposta formatado EXATAMENTE como Pinbank"""

        def formatar_valor_monetario(valor):
            """Formatar valor monetário com 2 decimais"""
            if valor is None:
                return "0.00"
            try:
                return f"{float(valor):.2f}"
            except (ValueError, TypeError):
                return "0.00"

        def mascarar_cpf(cpf_str):
            """Mascara CPF mostrando apenas últimos 3 dígitos"""
            if not cpf_str:
                return ""
            cpf_numeros = ''.join(filter(str.isdigit, cpf_str))
            if len(cpf_numeros) < 11:
                return cpf_str
            return f"*******{cpf_numeros[-3:]}"

        # Extrair dados da transação
        parcelas = int(valores_calculados.get(13, 1))  # Usar valores_calculados[13]
        payment_method = dados.get('paymentMethod', '')
        
        # Mapear forma de pagamento
        forma_map = {
            'CREDIT_ONE_INSTALLMENT': 'A VISTA',
            'CREDIT_IN_INSTALLMENTS_WITHOUT_INTEREST': 'PARCELADO SEM JUROS',
            'DEBIT': 'DEBITO',
            'PIX': 'PIX',
            'VOUCHER': 'VOUCHER'
        }
        forma = forma_map.get(payment_method, payment_method)

        # === DEBUG valores_calculados ===
        registrar_log('posp2', f'🔍 valores_calculados recebidos: {len(valores_calculados)} campos')
        registrar_log('posp2', f'🔍 valores_calculados[11] (valor_original): {valores_calculados.get(11)}')
        registrar_log('posp2', f'🔍 valores_calculados[13] (parcelas): {valores_calculados.get(13)}')
        registrar_log('posp2', f'🔍 valores_calculados[15] (desconto PIX): {valores_calculados.get(15)}')
        registrar_log('posp2', f'🔍 valores_calculados[18] (desconto): {valores_calculados.get(18)}')
        registrar_log('posp2', f'🔍 valores_calculados[16] (valor_liquido): {valores_calculados.get(16)}')
        registrar_log('posp2', f'🔍 valores_calculados[20] (vparcela): {valores_calculados.get(20)}')
        registrar_log('posp2', f'🔍 valores_calculados[26] (valor_final): {valores_calculados.get(26)}')
        registrar_log('posp2', f'🔍 valores_calculados[88] (encargos1): {valores_calculados.get(88)}')
        registrar_log('posp2', f'🔍 valores_calculados[94] (encargos2): {valores_calculados.get(94)}')
        
        # === REPLICAR LÓGICA PINBANK ===
        # Lógica condicional do PHP: PIX usa valores[15], outros usam valores[18]
        if forma == 'PIX':
            desconto = abs(float(valores_calculados.get(15, 0)))
        else:
            desconto = abs(float(valores_calculados.get(18, 0)))
        
        # Valores conforme PHP
        parte0 = float(valores_calculados.get(26, 0))  # valor final
        parte1 = desconto  # valor absoluto do desconto
        
        # === CÁLCULO TARIFAS/ENCARGOS SEGUINDO PHP ===
        valores_94 = valores_calculados.get(94, {})
        if isinstance(valores_94, dict):
            valores_94_0 = valores_94.get('0', 0)
        else:
            valores_94_0 = 0
        encargos = abs((valores_calculados.get(88) or 0) + valores_94_0)
        
        # vparcela
        vparcela = valores_calculados.get(20, 0)
        if vparcela is None or vparcela == 0:
            vparcela = valores_calculados.get(11, 0)  # valor original como parcela única
        
        # tarifas = abs(parcelas * vparcela - valor_liquido) - encargos
        valor_liquido = valores_calculados.get(16, 0)
        tarifas = round(abs(parcelas * vparcela - valor_liquido) - encargos, 2)
        
        # Buscar saldo usado de cashback via autorizacao_id
        saldo_cashback_usado = 0.0
        if autorizacao_id:
            try:
                from apps.conta_digital.services_autorizacao import AutorizacaoService
                resultado = AutorizacaoService.verificar_autorizacao(autorizacao_id)
                if resultado.get('sucesso') and resultado.get('status') in ['APROVADO', 'CONCLUIDA']:
                    valor_bloqueado = resultado.get('valor_bloqueado')
                    if valor_bloqueado:
                        saldo_cashback_usado = float(valor_bloqueado)
            except Exception as e:
                registrar_log('posp2', f'❌ [SALDO] Erro ao buscar saldo usado: {str(e)}', nivel='ERROR')
        
        # AJUSTAR vdesconto e vparcela considerando saldo usado
        vdesconto_final = parte0 - saldo_cashback_usado
        vparcela_ajustado = vdesconto_final / parcelas if parcelas > 0 else vdesconto_final
        
        # Valor original para display
        valor_original_display = valores_calculados.get(11, 0)

        # Array base
        array = {
            "cpf": mascarar_cpf(cpf) if cpf else "",
            "nome": nome if nome else "",
            "estabelecimento": info_loja.get('nome_fantasia', ''),
            "cnpj": info_loja.get('cnpj', ''),
            "data": datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            "forma": forma,
            "parcelas": parcelas,
            "nopwall": dados.get('txTransactionId', ''),
            "autwall": dados.get('authorizationCode', ''),
            "terminal": dados.get('terminal', ''),
            "nsu": dados.get('nsuHost', '')
        }

        # Lógica condicional EXATA do Pinbank
        if cpf and cpf.strip():  # COM WALL CLUB
            if forma in ["PIX", "DEBITO"]:
                array["voriginal"] = f"Valor original da loja: R$ {formatar_valor_monetario(valor_original_display)}"
                array["desconto"] = f"Valor do desconto CLUB: R$ {formatar_valor_monetario(desconto)}"
                
                if saldo_cashback_usado > 0:
                    array["saldo_usado"] = f"Saldo utilizado de cashback: R$ {formatar_valor_monetario(saldo_cashback_usado)}"
                
                if cashback_concedido > 0:
                    array["cashback_concedido"] = f"Cashback concedido: R$ {formatar_valor_monetario(cashback_concedido)}"
                
                array["vdesconto"] = f"Valor total pago:\nR$ {formatar_valor_monetario(vdesconto_final)}"
                array["pagoavista"] = f"Valor pago à loja à vista: R$ {formatar_valor_monetario(valores_calculados.get(16, 0))}"
                array["vparcela"] = f"R$ {formatar_valor_monetario(vparcela_ajustado)}"
                array["tarifas"] = "Tarifas CLUB: -- "
                array["encargos"] = ""
            
            elif forma in ["PARCELADO SEM JUROS", "A VISTA", "PARCELADO COM JUROS"] and desconto >= 0:
                array["voriginal"] = f"Valor original da loja: R$ {formatar_valor_monetario(valor_original_display)}"
                array["desconto"] = f"Valor do desconto CLUB: R$ {formatar_valor_monetario(parte1)}"
                
                if saldo_cashback_usado > 0:
                    array["saldo_usado"] = f"Saldo utilizado de cashback: R$ {formatar_valor_monetario(saldo_cashback_usado)}"
                
                if cashback_concedido > 0:
                    array["cashback_concedido"] = f"Cashback concedido: R$ {formatar_valor_monetario(cashback_concedido)}"
                
                array["vdesconto"] = f"Valor pago com desconto:\nR$ {formatar_valor_monetario(vdesconto_final)}"
                array["pagoavista"] = f"Valor pago à loja à vista: R$ {formatar_valor_monetario(valores_calculados.get(16, 0))}"
                array["vparcela"] = f"R$ {formatar_valor_monetario(vparcela_ajustado)}"
                array["tarifas"] = f"Tarifas CLUB: R$ {formatar_valor_monetario(tarifas)}"
                array["encargos"] = f"Encargos financeiros: R$ {formatar_valor_monetario(encargos)}"
        else:
            # Sem Wall Club
            array["voriginal"] = f"Valor original da loja: R$ {formatar_valor_monetario(valor_original_display)}"
            array["vdesconto"] = f"Valor total pago:\nR$ {formatar_valor_monetario(valor_original_display)}"
            array["pagoavista"] = f"Valor pago à loja à vista: R$ {formatar_valor_monetario(valor_original_display)}"
            array["vparcela"] = f"R$ {formatar_valor_monetario(vparcela)}"
            array["tarifas"] = ""
            array["encargos"] = ""

        return array
