"""
Roteador de Gateway - Decide qual gateway usar (Pinbank ou Own)
Baseado no campo gateway_ativo da loja
"""
from typing import Any
from django.db import connection
from wallclub_core.utilitarios.log_control import registrar_log


class GatewayRouter:
    """Roteador que seleciona o gateway correto baseado na loja"""
    
    GATEWAY_PINBANK = 'PINBANK'
    GATEWAY_OWN = 'OWN'
    
    @staticmethod
    def obter_gateway_loja(loja_id: int) -> str:
        """
        Obtém o gateway ativo da loja
        
        Args:
            loja_id: ID da loja
            
        Returns:
            'PINBANK' ou 'OWN'
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT gateway_ativo
                    FROM loja
                    WHERE id = %s
                """, [loja_id])
                
                row = cursor.fetchone()
                if row and row[0]:
                    gateway = row[0].upper()
                    registrar_log('checkout.gateway', f'Loja {loja_id}: Gateway {gateway}')
                    return gateway
                
                # Default: Pinbank
                registrar_log('checkout.gateway', f'Loja {loja_id}: Gateway padrão (PINBANK)')
                return GatewayRouter.GATEWAY_PINBANK
                
        except Exception as e:
            registrar_log('checkout.gateway', f'Erro ao obter gateway da loja {loja_id}: {e}', nivel='ERROR')
            return GatewayRouter.GATEWAY_PINBANK
    
    @staticmethod
    def obter_service_transacao(loja_id: int) -> Any:
        """
        Retorna o service de transação correto baseado no gateway da loja
        
        Args:
            loja_id: ID da loja
            
        Returns:
            TransacoesPinbankService ou TransacoesOwnService
        """
        gateway = GatewayRouter.obter_gateway_loja(loja_id)
        
        if gateway == GatewayRouter.GATEWAY_OWN:
            from adquirente_own.services_transacoes_pagamento import TransacoesOwnService
            registrar_log('checkout.gateway', f'🟢 Usando Own Financial para loja {loja_id}')
            return TransacoesOwnService(loja_id=loja_id)
        else:
            from pinbank.services_transacoes_pagamento import TransacoesPinbankService
            registrar_log('checkout.gateway', f'🔵 Usando Pinbank para loja {loja_id}')
            return TransacoesPinbankService()
    
    @staticmethod
    def processar_pagamento_debito(
        loja_id: int,
        card_data: dict,
        amount: float,
        parcelas: int = 1
    ) -> dict:
        """
        Processa pagamento débito/crédito usando o gateway correto
        
        Args:
            loja_id: ID da loja
            card_data: Dados do cartão
            amount: Valor
            parcelas: Número de parcelas
            
        Returns:
            Dict padronizado com sucesso, nsu, codigo_autorizacao, mensagem
        """
        service = GatewayRouter.obter_service_transacao(loja_id)
        gateway = GatewayRouter.obter_gateway_loja(loja_id)
        
        if gateway == GatewayRouter.GATEWAY_OWN:
            # Own Financial
            from decimal import Decimal
            resultado = service.create_payment_debit(
                card_data=card_data,
                amount=Decimal(str(amount)),
                parcelas=parcelas,
                loja_id=loja_id
            )
            
            # Padronizar resposta
            return {
                'sucesso': resultado.get('sucesso', False),
                'nsu': resultado.get('nsu', ''),
                'codigo_autorizacao': resultado.get('codigo_autorizacao', ''),
                'mensagem': resultado.get('mensagem', ''),
                'gateway': 'OWN',
                'payment_id': resultado.get('own_payment_id', '')
            }
        else:
            # Pinbank
            resultado = service.efetuar_transacao_encrypted(
                card_data=card_data,
                valor=amount,
                parcelas=parcelas
            )
            
            return {
                'sucesso': resultado.get('sucesso', False),
                'nsu': resultado.get('nsu', ''),
                'codigo_autorizacao': resultado.get('codigo_autorizacao', ''),
                'mensagem': resultado.get('mensagem', ''),
                'gateway': 'PINBANK',
                'payment_id': resultado.get('nsu', '')
            }
    
    @staticmethod
    def processar_estorno(
        loja_id: int,
        payment_id: str,
        amount: float
    ) -> dict:
        """
        Processa estorno usando o gateway correto
        
        Args:
            loja_id: ID da loja
            payment_id: ID do pagamento original
            amount: Valor a estornar
            
        Returns:
            Dict com sucesso, mensagem
        """
        service = GatewayRouter.obter_service_transacao(loja_id)
        gateway = GatewayRouter.obter_gateway_loja(loja_id)
        
        if gateway == GatewayRouter.GATEWAY_OWN:
            from decimal import Decimal
            resultado = service.refund_payment(
                payment_id=payment_id,
                amount=Decimal(str(amount)),
                loja_id=loja_id
            )
        else:
            # Pinbank - implementar quando necessário
            resultado = {
                'sucesso': False,
                'mensagem': 'Estorno Pinbank não implementado via router'
            }
        
        return resultado
