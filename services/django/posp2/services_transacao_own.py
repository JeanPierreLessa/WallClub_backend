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


class TRDataOwnService:
    """
    Service para processar dados de transações Own/Ágilli
    Endpoint: /trdata_own/
    """
    
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
            
            # Extrair valores Wall Club
            valor_desconto_pos = dados.get('valor_desconto', 0)
            valor_cashback_pos = dados.get('valor_cashback', 0)
            cashback_concedido_pos = dados.get('cashback_concedido', 0)
            autorizacao_id = dados.get('autorizacao_id', '')
            modalidade_wall = dados.get('modalidade_wall', '')
            
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
            
            # 6. Converter valor original
            valor_original = self._converter_valor_monetario(valororiginal)
            
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
            }
            
            # 8. Inserir na base
            transaction_id = self._inserir_transacao(dados_para_inserir)
            
            if not transaction_id:
                return {
                    'sucesso': False,
                    'mensagem': 'Erro ao inserir transação no banco'
                }
            
            registrar_log('posp2', f'✅ Transação Own inserida: ID={transaction_id}, TxID={tx_transaction_id}')
            
            # 9. Buscar informações da loja
            info_loja = self._buscar_info_loja(terminal)
            
            # 10. Buscar nome do cliente (se CPF informado)
            nome = ''
            if cpf:
                nome = self._buscar_nome_cliente(cpf)
            
            # 11. Gerar JSON de resposta para impressão do slip
            json_resposta = self._gerar_slip_impressao(dados_para_inserir, info_loja, cpf, nome)
            
            # 11. Retornar dados completos para comprovante
            return {
                'sucesso': True,
                'mensagem': 'Dados processados com sucesso',
                **json_resposta
            }
            
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
                        saldo_usado, modalidade_wall
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
                    dados['autorizacao_id'], dados['saldo_usado'], dados['modalidade_wall']
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
                    FROM terminal t
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
                              cpf: str, nome: str) -> Dict[str, Any]:
        """Gera JSON de resposta formatado para impressão do slip"""
        
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
        
        # Valores básicos
        valor_original = float(dados['valor_original'])
        valor_desconto = float(dados.get('valor_desconto', 0))
        valor_cashback = float(dados.get('valor_cashback', 0))
        cashback_concedido = float(dados.get('cashback_concedido', 0))
        saldo_usado = float(dados.get('saldo_usado', 0))
        parcelas = dados['totalInstallments']
        
        # Valor final após descontos
        valor_final = valor_original - valor_desconto - saldo_usado
        valor_parcela = valor_final / parcelas if parcelas > 0 else valor_final
        
        # Data e hora
        data_hora = dados['datahora'].strftime('%Y-%m-%d %H:%M:%S')
        
        # Mapear operationId para forma de pagamento
        operation_id = dados['operationId']
        payment_method = dados['paymentMethod']
        
        forma_map = {
            'CREDIT_ONE_INSTALLMENT': 'A VISTA',
            'CREDIT_IN_INSTALLMENTS_WITHOUT_INTEREST': 'PARCELADO SEM JUROS',
            'DEBIT': 'DEBITO',
            'PIX': 'PIX',
            'VOUCHER': 'VOUCHER',
            'PARCELAMENTO_INTELIGENTE': 'PARCELAMENTO INTELIGENTE'
        }
        forma = forma_map.get(payment_method, payment_method)
        
        # Array base
        array = {
            "cpf": mascarar_cpf(cpf) if cpf else "",
            "nome": nome if nome else "",
            "estabelecimento": info_loja.get('nome_fantasia', ''),
            "cnpj": dados['cnpj'],
            "data": data_hora,
            "forma": forma,
            "parcelas": parcelas,
            "nopwall": dados['txTransactionId'],  # ID da transação Own
            "autwall": dados['authorizationCode'],
            "terminal": dados['terminal'],
            "nsu": dados['nsuHost']
        }
        
        # Se tem CPF (Wall Club)
        if cpf and cpf.strip():
            array["voriginal"] = f"Valor original da loja: R$ {formatar_valor_monetario(valor_original)}"
            
            if valor_desconto > 0:
                array["desconto"] = f"Valor do desconto CLUB: R$ {formatar_valor_monetario(valor_desconto)}"
            
            if saldo_usado > 0:
                array["saldo_usado"] = f"Saldo utilizado de cashback: R$ {formatar_valor_monetario(saldo_usado)}"
            
            if cashback_concedido > 0:
                array["cashback_concedido"] = f"Cashback concedido: R$ {formatar_valor_monetario(cashback_concedido)}"
            
            array["vdesconto"] = f"Valor total pago:\nR$ {formatar_valor_monetario(valor_final)}"
            array["pagoavista"] = f"Valor pago à loja à vista: R$ {formatar_valor_monetario(valor_final)}"
            array["vparcela"] = f"R$ {formatar_valor_monetario(valor_parcela)}"
            array["tarifas"] = "Tarifas CLUB: -- "
            array["encargos"] = ""
        else:
            # Venda normal sem Wall Club
            array["voriginal"] = f"Valor da transação: R$ {formatar_valor_monetario(valor_original)}"
            array["pagoavista"] = f"Valor pago à loja: R$ {formatar_valor_monetario(valor_original)}"
            array["vparcela"] = f"R$ {formatar_valor_monetario(valor_original / parcelas if parcelas > 0 else valor_original)}"
        
        return array
