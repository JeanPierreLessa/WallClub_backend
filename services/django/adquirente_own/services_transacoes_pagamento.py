"""
Serviço para processamento de transações via API Own Financial (OPPWA)
Baseado na documentação: https://own-financial.docs.oppwa.com/integrations/server-to-server
"""

import requests
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime
from django.conf import settings
from adquirente_own.services import OwnService
from wallclub_core.utilitarios.log_control import registrar_log


class TransacoesOwnService:
    """Serviço para processamento de transações via API Own Financial (OPPWA)"""
    
    # URLs base OPPWA
    BASE_URL_TEST = 'https://eu-test.oppwa.com'
    BASE_URL_LIVE = 'https://eu-prod.oppwa.com'
    
    # Result codes de sucesso
    SUCCESS_CODES = [
        '000.000.000',  # Transaction succeeded
        '000.100.110',  # Request successfully processed
        '000.100.111',  # Request successfully processed (please review manually)
        '000.100.112',  # Request successfully processed (please review manually)
    ]
    
    def __init__(self, loja_id: int = None):
        """
        Inicializa o serviço de transações Own
        
        Args:
            loja_id: ID da loja
        """
        self.loja_id = loja_id
        self.own_service = OwnService()
    
    def _obter_credenciais_loja(self, loja_id: int = None) -> Optional[Dict[str, Any]]:
        """Obtém credenciais Own da loja"""
        id_loja = loja_id or self.loja_id
        
        if not id_loja:
            raise ValueError("loja_id não fornecido")
        
        credenciais = self.own_service.obter_credenciais_loja(id_loja)
        
        if not credenciais:
            raise ValueError(f"Credenciais Own não encontradas para loja {id_loja}")
        
        return credenciais
    
    def _get_base_url(self, environment: str) -> str:
        """Retorna URL base conforme ambiente"""
        return self.BASE_URL_LIVE if environment == 'LIVE' else self.BASE_URL_TEST
    
    def _fazer_requisicao_oppwa(
        self,
        method: str,
        endpoint: str,
        entity_id: str,
        access_token: str,
        environment: str,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Faz requisição à API OPPWA
        
        Args:
            method: GET ou POST
            endpoint: Endpoint da API (ex: '/v1/payments')
            entity_id: Entity ID da loja
            access_token: Bearer token
            environment: TEST ou LIVE
            data: Dados do formulário (application/x-www-form-urlencoded)
            
        Returns:
            Dict com resposta da API
        """
        base_url = self._get_base_url(environment)
        url = f'{base_url}{endpoint}'
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        try:
            registrar_log('own.transacao', f'📡 {method} {endpoint}')
            
            if method.upper() == 'POST':
                response = requests.post(url, data=data, headers=headers, timeout=30)
            elif method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=data, timeout=30)
            else:
                raise ValueError(f'Método não suportado: {method}')
            
            response.raise_for_status()
            result = response.json()
            
            registrar_log('own.transacao', f'✅ Resposta: {result.get("result", {}).get("code")}')
            
            return result
            
        except requests.exceptions.Timeout:
            registrar_log('own.transacao', f'⏱️ Timeout: {endpoint}', nivel='WARNING')
            return {
                'result': {
                    'code': 'TIMEOUT',
                    'description': 'Timeout na comunicação com Own Financial'
                }
            }
        except requests.exceptions.RequestException as e:
            registrar_log('own.transacao', f'❌ Erro HTTP: {str(e)}', nivel='ERROR')
            return {
                'result': {
                    'code': 'ERROR',
                    'description': f'Erro na comunicação: {str(e)}'
                }
            }
    
    def create_payment_debit(
        self,
        card_data: Dict[str, str],
        amount: Decimal,
        parcelas: int = 1,
        loja_id: int = None
    ) -> Dict[str, Any]:
        """
        Pagamento débito/crédito (captura imediata)
        Payment Type: DB (Debit)
        
        Args:
            card_data: Dados do cartão (number, holder, expiry_month, expiry_year, cvv, brand)
            amount: Valor da transação
            parcelas: Número de parcelas (padrão: 1)
            loja_id: ID da loja (opcional)
            
        Returns:
            Dict com sucesso, own_payment_id, nsu, codigo_autorizacao, mensagem
        """
        credenciais = self._obter_credenciais_loja(loja_id)
        
        data = {
            'entityId': credenciais['entity_id'],
            'amount': f'{amount:.2f}',
            'currency': 'BRL',
            'paymentBrand': card_data['brand'].upper(),
            'paymentType': 'DB',  # Debit (captura imediata)
            'card.number': card_data['number'],
            'card.holder': card_data['holder'],
            'card.expiryMonth': card_data['expiry_month'],
            'card.expiryYear': card_data['expiry_year'],
            'card.cvv': card_data['cvv'],
        }
        
        # Parcelamento (se aplicável)
        if parcelas > 1:
            data['installments'] = str(parcelas)
        
        registrar_log('own.transacao', f'💳 Pagamento DB: R$ {amount:.2f} ({parcelas}x)')
        
        response = self._fazer_requisicao_oppwa(
            method='POST',
            endpoint='/v1/payments',
            entity_id=credenciais['entity_id'],
            access_token=credenciais['access_token'],
            environment=credenciais['environment'],
            data=data
        )
        
        # Verificar sucesso
        result_code = response.get('result', {}).get('code', '')
        
        if result_code in self.SUCCESS_CODES:
            registrar_log('own.transacao', f'✅ Pagamento aprovado: {response.get("id")}')
            return {
                'sucesso': True,
                'own_payment_id': response.get('id'),
                'nsu': response.get('id'),
                'codigo_autorizacao': response.get('descriptor', ''),
                'mensagem': response.get('result', {}).get('description', ''),
                'card_bin': response.get('card', {}).get('bin'),
                'card_last4': response.get('card', {}).get('last4Digits'),
                'payment_brand': response.get('paymentBrand', '')
            }
        else:
            registrar_log('own.transacao', f'❌ Pagamento reprovado: {result_code}', nivel='WARNING')
            return {
                'sucesso': False,
                'codigo_erro': result_code,
                'mensagem': response.get('result', {}).get('description', 'Erro desconhecido')
            }
    
    def create_payment_with_tokenization(
        self,
        card_data: Dict[str, str],
        amount: Decimal,
        loja_id: int = None
    ) -> Dict[str, Any]:
        """
        Pagamento com tokenização (para recorrência)
        Payment Type: PA (Pre-authorization) + createRegistration
        
        Args:
            card_data: Dados do cartão
            amount: Valor da transação
            loja_id: ID da loja (opcional)
            
        Returns:
            Dict com sucesso, own_payment_id, registration_id, card_last4
        """
        credenciais = self._obter_credenciais_loja(loja_id)
        
        data = {
            'entityId': credenciais['entity_id'],
            'amount': f'{amount:.2f}',
            'currency': 'BRL',
            'paymentBrand': card_data['brand'].upper(),
            'paymentType': 'PA',  # Pre-authorization
            'card.number': card_data['number'],
            'card.holder': card_data['holder'],
            'card.expiryMonth': card_data['expiry_month'],
            'card.expiryYear': card_data['expiry_year'],
            'card.cvv': card_data['cvv'],
            'createRegistration': 'true',
            'standingInstruction.mode': 'INITIAL',
            'standingInstruction.type': 'UNSCHEDULED',
            'standingInstruction.source': 'CIT'
        }
        
        registrar_log('own.transacao', f'🔐 PA com tokenização: R$ {amount:.2f}')
        
        response = self._fazer_requisicao_oppwa(
            method='POST',
            endpoint='/v1/payments',
            entity_id=credenciais['entity_id'],
            access_token=credenciais['access_token'],
            environment=credenciais['environment'],
            data=data
        )
        
        result_code = response.get('result', {}).get('code', '')
        
        if result_code in self.SUCCESS_CODES:
            registrar_log('own.transacao', f'✅ Tokenização aprovada: {response.get("registrationId")}')
            return {
                'sucesso': True,
                'own_payment_id': response.get('id'),
                'registration_id': response.get('registrationId'),
                'card_last4': response.get('card', {}).get('last4Digits'),
                'card_bin': response.get('card', {}).get('bin'),
                'card_brand': response.get('paymentBrand', ''),
                'card_holder': response.get('card', {}).get('holder')
            }
        else:
            return {
                'sucesso': False,
                'mensagem': response.get('result', {}).get('description', 'Erro na tokenização')
            }
    
    def create_payment_with_registration(
        self,
        registration_id: str,
        amount: Decimal,
        loja_id: int = None
    ) -> Dict[str, Any]:
        """
        Pagamento usando token de recorrência
        Payment Type: DB com registrationId
        
        Args:
            registration_id: ID do token de recorrência
            amount: Valor da transação
            loja_id: ID da loja (opcional)
            
        Returns:
            Dict com sucesso, own_payment_id, mensagem
        """
        credenciais = self._obter_credenciais_loja(loja_id)
        
        data = {
            'entityId': credenciais['entity_id'],
            'amount': f'{amount:.2f}',
            'currency': 'BRL',
            'paymentType': 'DB',
            'registrationId': registration_id,
            'standingInstruction.mode': 'REPEATED',
            'standingInstruction.type': 'UNSCHEDULED',
            'standingInstruction.source': 'MIT'
        }
        
        registrar_log('own.transacao', f'🔁 Pagamento recorrente: R$ {amount:.2f}')
        
        response = self._fazer_requisicao_oppwa(
            method='POST',
            endpoint='/v1/payments',
            entity_id=credenciais['entity_id'],
            access_token=credenciais['access_token'],
            environment=credenciais['environment'],
            data=data
        )
        
        result_code = response.get('result', {}).get('code', '')
        
        if result_code in self.SUCCESS_CODES:
            registrar_log('own.transacao', f'✅ Recorrência aprovada: {response.get("id")}')
            return {
                'sucesso': True,
                'own_payment_id': response.get('id'),
                'nsu': response.get('id'),
                'mensagem': response.get('result', {}).get('description', '')
            }
        else:
            return {
                'sucesso': False,
                'mensagem': response.get('result', {}).get('description', 'Erro na recorrência')
            }
    
    def refund_payment(
        self,
        payment_id: str,
        amount: Decimal,
        loja_id: int = None
    ) -> Dict[str, Any]:
        """
        Estorno total ou parcial
        Payment Type: RF (Refund)
        
        Args:
            payment_id: ID do pagamento original
            amount: Valor a estornar
            loja_id: ID da loja (opcional)
            
        Returns:
            Dict com sucesso, refund_id, mensagem
        """
        credenciais = self._obter_credenciais_loja(loja_id)
        
        data = {
            'entityId': credenciais['entity_id'],
            'amount': f'{amount:.2f}',
            'currency': 'BRL',
            'paymentType': 'RF'  # Refund
        }
        
        registrar_log('own.transacao', f'↩️ Estorno: {payment_id} - R$ {amount:.2f}')
        
        response = self._fazer_requisicao_oppwa(
            method='POST',
            endpoint=f'/v1/payments/{payment_id}',
            entity_id=credenciais['entity_id'],
            access_token=credenciais['access_token'],
            environment=credenciais['environment'],
            data=data
        )
        
        result_code = response.get('result', {}).get('code', '')
        
        if result_code in self.SUCCESS_CODES:
            registrar_log('own.transacao', f'✅ Estorno aprovado: {response.get("id")}')
            return {
                'sucesso': True,
                'refund_id': response.get('id'),
                'mensagem': response.get('result', {}).get('description', '')
            }
        else:
            return {
                'sucesso': False,
                'mensagem': response.get('result', {}).get('description', 'Erro no estorno')
            }
    
    def consultar_status_pagamento(
        self,
        payment_id: str,
        loja_id: int = None
    ) -> Dict[str, Any]:
        """
        Consulta status de um pagamento
        
        Args:
            payment_id: ID do pagamento
            loja_id: ID da loja (opcional)
            
        Returns:
            Dict com dados do pagamento
        """
        credenciais = self._obter_credenciais_loja(loja_id)
        
        registrar_log('own.transacao', f'🔍 Consultando: {payment_id}')
        
        response = self._fazer_requisicao_oppwa(
            method='GET',
            endpoint=f'/v1/payments/{payment_id}',
            entity_id=credenciais['entity_id'],
            access_token=credenciais['access_token'],
            environment=credenciais['environment'],
            data={'entityId': credenciais['entity_id']}
        )
        
        return {
            'sucesso': True,
            'payment_id': response.get('id'),
            'result_code': response.get('result', {}).get('code'),
            'result_description': response.get('result', {}).get('description'),
            'amount': response.get('amount'),
            'currency': response.get('currency'),
            'payment_type': response.get('paymentType'),
            'payment_brand': response.get('paymentBrand'),
            'timestamp': response.get('timestamp')
        }
