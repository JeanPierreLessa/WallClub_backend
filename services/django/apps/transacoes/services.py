"""
Services para transações - lógica de negócio
"""
from django.http import JsonResponse
from django.db import connection
from django.conf import settings
from decimal import Decimal
from datetime import datetime
from typing import Dict, Any
from wallclub_core.utilitarios.log_control import registrar_log
from wallclub_core.utilitarios.funcoes_gerais import calcular_cet, proxima_sexta_feira


class TransacaoService:
    """Service para operações de transações"""
    
    @staticmethod
    def consultar_saldo(cliente_id, canal_id):
        """
        Consulta saldo do cliente - MIGRADO DO saldo.php
        
        IMPLEMENTAÇÃO ORIGINAL: sempre retorna 0 (saldo.php apenas faz "echo 0")
        
        Args:
            cliente_id (int): ID do cliente
            canal_id (int): ID do canal
            
        Returns:
            dict: Dados do saldo (sempre zero conforme PHP original)
        """
        try:
            
            # Implementação EXATA do saldo.php: sempre retorna 0
            # Formato JSON padrão conforme solicitado
            return {
                'sucesso': True,
                'saldo': 0.00,
                'mensagem': 'Saldo consultado com sucesso'
            }
                    
        except Exception as e:
            registrar_log('apps.transacoes', f"Erro ao consultar saldo: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Erro interno do servidor'
            }
    
    def verificar_transacao_cancelada(self, nsu):
        """
        Verifica se uma transação foi cancelada
        
        Args:
            nsu: NSU da transação
            
        Returns:
            bool: True se cancelada, False caso contrário
        """
        try:
            from wallclub_core.database.queries import TransacoesQueries
            
            return TransacoesQueries.verificar_transacao_cancelada(nsu)
            
        except Exception as e:
            registrar_log('apps.transacoes', f"Erro ao verificar cancelamento NSU {nsu}: {str(e)}", nivel='ERROR')
            return False
    
    def consultar_extrato(self, id_usuario_app, dt_inicio, dt_fim):
        """
        Consulta extrato - LÓGICA EXATA DO extrato.php
        
        Args:
            id_usuario_app (int): ID do usuário no app (cadastro.id)
            dt_inicio (str): Data início (YYYY-MM-DD HH:MM:SS)
            dt_fim (str): Data fim (YYYY-MM-DD HH:MM:SS)
            
        Returns:
            dict: Dados do extrato formatados igual ao PHP
        """
        try:
            registrar_log('apps.transacoes', 
                         f"Consultando extrato - Usuario: {id_usuario_app}, Período: {dt_inicio} a {dt_fim}")
            
            # Garantir formato correto das datas
            if hasattr(dt_inicio, 'strftime'):
                dt_inicio = dt_inicio.strftime('%Y-%m-%d') + " 00:00:00"
            elif isinstance(dt_inicio, str) and len(dt_inicio) == 10:
                dt_inicio = f"{dt_inicio} 00:00:00"
                
            if hasattr(dt_fim, 'strftime'):
                dt_fim = dt_fim.strftime('%Y-%m-%d')
            elif isinstance(dt_fim, str) and len(dt_fim) == 10:
                dt_fim = f"{dt_fim}"
            
            # Buscar dados do cliente
            from apps.cliente.models import Cliente
            try:
                cliente = Cliente.objects.get(id=id_usuario_app, is_active=True)
                canal_id = cliente.canal_id
                cpf_cliente = cliente.cpf.replace('.', '').replace('-', '')
            except Cliente.DoesNotExist:
                registrar_log('apps.transacoes', f"Cliente não encontrado: {id_usuario_app}", nivel='ERROR')
                return {'erro': 'Cliente não encontrado'}
            
            with connection.cursor() as cursor:
                query = """
                    SELECT DISTINCT
                        btg.data_transacao, btg.var5, td.valor_original,
                        td.amount/100, td.totalInstallments, td.applicationName,
                        td.brand, td.cardNumber, td.nsuPinbank, td.paymentMethod
                    FROM wallclub.baseTransacoesGestao btg
                    INNER JOIN wallclub.canal canal ON btg.var4 = canal.nome
                    INNER JOIN wallclub.transactiondata td ON td.nsuPinbank = btg.var9
                    WHERE btg.var7 = %s AND canal.id = %s
                      AND btg.data_transacao >= %s
                      AND btg.data_transacao < CONCAT(%s, ' 23:59:59')
                    ORDER BY btg.data_transacao DESC
                """
                
                cursor.execute(query, [cpf_cliente, canal_id, dt_inicio, dt_fim])
                
                extrato = []
                for row in cursor.fetchall():
                    data, estab, valoro, valord, parcelas, forma, band, card, nsu, metodo = row
                    
                    # Formatação de forma de pagamento
                    if metodo == 'CREDIT_ONE_INSTALLMENT':
                        forma = "crédito à vista"
                    elif metodo in ['CREDIT_IN_INSTALLMENTS_WITHOUT_INTEREST', 'CREDIT_IN_INSTALLMENTS_WITH_INTEREST']:
                        forma = "crédito"
                    elif metodo == 'DEBIT':
                        forma = "débito"
                    
                    if band == "PIX":
                        forma = ''
                    
                    # Formatação do cartão
                    if card and len(str(card)) > 6:
                        card = f"Cartão final {str(card)[-3:]}"
                    else:
                        card = ""
                    
                    forma = f" {forma}" if forma else ''
                    
                    # Status de cancelamento
                    status = " (CANCELADA)" if self.verificar_transacao_cancelada(nsu) else ""
                    
                    # Descrição formatada
                    if band == "PIX":
                        descricao = f"{estab}\\n\\n{data}\\n\\nPIX{card}{status}"
                    else:
                        descricao = f"{estab}\\n\\n{data}\\n\\n{band}{forma}{card}{status}"
                    
                    extrato.append({
                        'data': str(data),
                        'estabelecimento': str(estab),
                        'valor_original': valoro or Decimal('0.00'),
                        'valor_decimal': valord or Decimal('0.00'),
                        'parcelas': int(parcelas) if parcelas else 1,
                        'forma_pagamento': str(forma).strip(),
                        'bandeira': str(band),
                        'cartao': str(card),
                        'nsu': str(nsu),
                        'metodo': str(metodo),
                        'descricao': descricao,
                        'cancelada': self.verificar_transacao_cancelada(nsu)
                    })
                
                return {
                    'sucesso': True,
                    'mensagem': 'Extrato consultado com sucesso',
                    'extrato': extrato,
                    'total': len(extrato)
                }
                
        except Exception as e:
            registrar_log('apps.transacoes', f"Erro ao consultar extrato: {str(e)}", nivel='ERROR')
            return {'sucesso': False, 'mensagem': 'Erro interno do servidor'}
    
    def gerar_comprovante(self, nsu_pinbank, cliente_id):
        """
        Gera comprovante de transação específica - COMPLETO
        """
        try:
            from apps.cliente.models import Cliente
            
            try:
                cliente = Cliente.objects.get(id=cliente_id)
                cpf_cliente = cliente.cpf
            except Cliente.DoesNotExist:
                return {'sucesso': False, 'mensagem': 'Cliente não encontrado'}
            
            with connection.cursor() as cursor:
                query = """
                    SELECT cli.cpf, cli.nome, td.valor_original, td.datahora,
                           CASE WHEN td.totalInstallments = 0 THEN 1 ELSE td.totalInstallments END,
                           td.authorizationCode, td.nsuAcquirer, td.terminal,
                           CASE WHEN td.brand = 'PIX' THEN 'PIX'
                                WHEN td.paymentMethod = 'CREDIT_ONE_INSTALLMENT' THEN 'A VISTA'
                                WHEN td.paymentMethod = 'CREDIT_IN_INSTALLMENTS_WITHOUT_INTEREST' THEN 'PARCELADO SEM JUROS'
                                WHEN td.paymentMethod = 'CREDIT_IN_INSTALLMENTS_WITH_INTEREST' THEN 'PARCELADO COM JUROS'
                                WHEN td.paymentMethod = 'DEBIT' THEN 'DEBITO' END,
                           loja.cnpj, loja.razao_social, btg.var16, btg.var20, btg.var26,
                           btg.var88, btg.var94, td.valor_cashback
                    FROM wallclub.transactiondata td, wallclub.baseTransacoesGestao btg,
                         wallclub.loja loja, wallclub.cliente cli
                    WHERE td.nsuPinbank = CAST(btg.var9 AS CHAR)
                      AND cli.id = %s
                      AND cli.cpf = td.cpf
                      AND CAST(btg.var6 AS UNSIGNED) = loja.id
                      AND td.nsuPinbank = %s
                      AND td.valor_original > 0
                """
                
                cursor.execute(query, [cliente_id, nsu_pinbank])
                resultado = cursor.fetchone()
                
                if not resultado:
                    return {'sucesso': False, 'mensagem': 'Transação não encontrada'}
                
                # Extrair dados
                (cpf, nome, valores11, datahora_raw, valores13, autwall, nopwall, terminal,
                 forma, cnpj, razao_social, valores16, valores20, valores26, valores88,
                 valores94, valor_cashback) = resultado
                
                # Converter decimais
                valores11 = valores11 or Decimal('0.00')
                valores16 = valores16 or Decimal('0.00')
                valores20 = valores20 or Decimal('0.00')
                valores26 = valores26 or Decimal('0.00')
                valores88 = valores88 or Decimal('0.00')
                valores94 = valores94 or Decimal('0.00')
                valor_cashback = valor_cashback or Decimal('0.00')
                
                # Formatar data
                if isinstance(datahora_raw, str):
                    try:
                        dt = datetime.strptime(datahora_raw, '%Y-%m-%d %H:%M:%S')
                        datahora = dt.strftime('%d/%m/%Y %H:%M:%S')
                    except:
                        datahora = str(datahora_raw)
                else:
                    datahora = datahora_raw.strftime('%d/%m/%Y %H:%M:%S') if datahora_raw else ""
                
                # Cliente WallClub?
                wall = 's' if len(cpf) > 0 else 'n'
                pixcartao = "PIX" if forma == "PIX" else "CARTÃO"
                
                # Cálculos (bug do PHP original mantido: desconto sempre 0)
                desconto = Decimal('0.00')
                encargos = abs(valores88 + valores94)
                
                if valores13 >= 1:
                    vparcela = valores20
                    tarifas = abs(valores13 * vparcela - valores16) - encargos
                    parte0 = abs(valores13 * vparcela)
                    parte1 = abs(valores13 * vparcela - valores11)
                else:
                    vparcela = Decimal('0.00')
                    tarifas = Decimal('0.00')
                    parte0 = valores26
                    parte1 = desconto
                
                valor_pago_cliente = parte0 - valor_cashback
                
                # CET
                cet = ""
                if forma == "PARCELADO COM JUROS" and desconto < 0:
                    cet_valor = calcular_cet(vparcela, valores11, valores13)
                    if cet_valor:
                        cet = f"CET (Custo Efetivo Total) %am: {cet_valor}"
                
                # Montar comprovante
                if wall == 's':
                    if forma in ["PIX", "DEBITO"]:
                        array_comprovante = {
                            "cpf": cpf, "nome": nome, "estabelecimento": razao_social,
                            "cnpj": cnpj, "voriginal": f"R$ {valores11:.2f}",
                            "desconto": f"Desconto CLUB: R$ {desconto:.2f}",
                            "vdesconto": f"R$ {valores26:.2f}",
                            "pagoavista": f"R$ {valores16:.2f}",
                            "data": datahora, "forma": forma, "parcelas": valores13,
                            "vparcela": "", "tarifas": "sem tarifas", "encargos": "",
                            "nopwall": nopwall, "autwall": autwall, "terminal": terminal,
                            "nsu": nsu_pinbank, "cet": cet,
                            "valor_cashback": f"R$ {valor_cashback:.2f}",
                            "valor_pago_cliente": f"R$ {valor_pago_cliente:.2f}"
                        }
                    elif desconto >= 0:
                        array_comprovante = {
                            "cpf": cpf, "nome": nome, "estabelecimento": razao_social,
                            "cnpj": cnpj, "voriginal": f"R$ {valores11:.2f}",
                            "desconto": f"Desconto CLUB: R$ {parte1:.2f}",
                            "vdesconto": f"R$ {parte0:.2f}",
                            "pagoavista": f"R$ {valores16:.2f}",
                            "data": datahora, "forma": forma, "parcelas": valores13,
                            "vparcela": f"R$ {vparcela:.2f}",
                            "tarifas": f"Tarifas CLUB: R$ {tarifas:.2f}",
                            "encargos": f"R$ {encargos:.2f}",
                            "nopwall": nopwall, "autwall": autwall, "terminal": terminal,
                            "nsu": nsu_pinbank, "cet": cet,
                            "valor_cashback": f"R$ {valor_cashback:.2f}",
                            "valor_pago_cliente": f"R$ {valor_pago_cliente:.2f}"
                        }
                    else:
                        array_comprovante = {
                            "cpf": cpf, "nome": nome, "estabelecimento": razao_social,
                            "cnpj": cnpj, "voriginal": f"R$ {valores11:.2f}",
                            "desconto": f"Encargos: R$ {parte1:.2f}",
                            "vdesconto": f"R$ {parte0:.2f}",
                            "pagoavista": f"R$ {valores16:.2f}",
                            "data": datahora, "forma": forma, "parcelas": valores13,
                            "vparcela": f"R$ {vparcela:.2f}",
                            "tarifas": f"R$ {tarifas:.2f}",
                            "encargos": f"R$ {encargos:.2f}",
                            "nopwall": nopwall, "autwall": autwall, "terminal": terminal,
                            "nsu": nsu_pinbank, "cet": cet,
                            "valor_cashback": f"R$ {valor_cashback:.2f}",
                            "valor_pago_cliente": f"R$ {valor_pago_cliente:.2f}"
                        }
                else:
                    array_comprovante = {
                        "cpf": cpf, "nome": nome, "estabelecimento": razao_social,
                        "cnpj": cnpj, "voriginal": f"R$ {valores11:.2f}",
                        "data": datahora, "forma": forma, "parcelas": valores13,
                        "terminal": terminal, "nsu": nsu_pinbank,
                        "valor_cashback": valor_cashback,
                        "valor_pago_cliente": valor_pago_cliente
                    }
                
                return {
                    'sucesso': True,
                    'mensagem': 'Comprovante gerado com sucesso',
                    'comprovante': array_comprovante
                }
                
        except Exception as e:
            registrar_log('apps.transacoes', f"Erro ao gerar comprovante: {str(e)}", nivel='ERROR')
            return {'sucesso': False, 'mensagem': 'Erro interno do servidor'}
    
    @staticmethod
    def checa_transacao_cancelada(nsu):
        """Método estático para compatibilidade"""
        service = TransacaoService()
        return service.verificar_transacao_cancelada(nsu)
    
