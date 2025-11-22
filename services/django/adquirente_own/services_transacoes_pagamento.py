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
    
    def __init__(self, loja_id: int = None, environment: str = 'TEST'):
        """
        Inicializa o serviço de transações Own
        
        Args:
            loja_id: ID da loja
            environment: 'TEST' ou 'LIVE'
        """
        self.loja_id = loja_id
        self.own_service = OwnService(environment=environment)
    
    def _obter_credenciais_loja(self, loja_id: int = None) -> Optional[Dict[str, Any]]:
        """Obtém credenciais Own da loja"""
        id_loja = loja_id or self.loja_id
        
        if not id_loja:
            raise ValueError("loja_id não fornecido")
        
        credenciais = self.own_service.obter_credenciais_loja(id_loja)
        
        if not credenciais:
            raise ValueError(f"Credenciais Own não encontradas para loja {id_loja}")
        
        # Se não tem entity_id/access_token específicos, usa client_id e gera token OAuth
        if not credenciais.get('entity_id') or not credenciais.get('access_token'):
            registrar_log('own.transacao', '🔑 Gerando access_token via OAuth para OPPWA')
            
            # Gerar token OAuth
            token_data = self.own_service.obter_token_oauth(
                client_id=credenciais['client_id'],
                client_secret=credenciais['client_secret'],
                scope=credenciais['scope']
            )
            
            if not token_data.get('access_token'):
                raise ValueError("Falha ao obter access_token OAuth")
            
            # Usar client_id como entity_id e token OAuth como access_token
            credenciais['entity_id'] = credenciais['client_id']
            credenciais['access_token'] = token_data['access_token']
        
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
            method: GET, POST ou DELETE
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
            registrar_log('own.transacao', f'📦 Payload: {data}')
            
            if method.upper() == 'POST':
                response = requests.post(url, data=data, headers=headers, timeout=60)
            elif method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=data, timeout=60)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=headers, params=data, timeout=60)
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
            # Tentar capturar resposta de erro
            try:
                if hasattr(e, 'response') and e.response is not None:
                    error_body = e.response.text
                    registrar_log('own.transacao', f'📄 Resposta erro: {error_body}', nivel='ERROR')
            except:
                pass
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
        
        # Normalizar ano para 4 dígitos (OPPWA exige formato YYYY)
        expiry_year = card_data['expiry_year']
        if len(str(expiry_year)) == 2:
            expiry_year = f'20{expiry_year}'
        
        # Normalizar bandeira (MASTERCARD -> MASTER)
        brand = card_data['brand'].upper()
        if brand == 'MASTERCARD':
            brand = 'MASTER'
        
        data = {
            'entityId': credenciais['entity_id'],
            'amount': f'{amount:.2f}',
            'currency': 'BRL',
            'paymentBrand': brand,
            'paymentType': 'DB',
            'card.number': card_data['number'],
            'card.holder': card_data['holder'],
            'card.expiryMonth': card_data['expiry_month'],
            'card.expiryYear': expiry_year,
            'card.cvv': card_data['cvv'],
            'transactionCategory': 'EC',
            'standingInstruction.type': 'INSTALLMENT' if parcelas > 1 else 'UNSCHEDULED',
            'merchant.mcc': '5462',
            'merchant.name': 'WallClub Channel Teste',
            'merchant.street': 'Av Paulista 1000',
            'merchant.city': 'Sao Paulo',
            'merchant.state': 'SP',
            'merchant.countryCode': '076',
            'merchant.url': settings.MERCHANT_URL,
            'merchant.postcode': '01310100',
            'merchant.phone': '1133334444',
            'merchant.customerContactPhone': '1133334444',
            'customParameters[PAYMENT_METHOD]': 'CREDIT',
        }
        
        # Parcelamento (se aplicável)
        if parcelas > 1:
            data['standingInstruction.numberOfInstallments'] = str(parcelas)
        
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
        
        # Normalizar ano para 4 dígitos (OPPWA exige formato YYYY)
        expiry_year = card_data['expiry_year']
        if len(str(expiry_year)) == 2:
            expiry_year = f'20{expiry_year}'
        
        # Normalizar bandeira (MASTERCARD -> MASTER)
        brand = card_data['brand'].upper()
        if brand == 'MASTERCARD':
            brand = 'MASTER'
        
        data = {
            'entityId': credenciais['entity_id'],
            'amount': f'{amount:.2f}',
            'currency': 'BRL',
            'paymentBrand': brand,
            'paymentType': 'PA',
            'card.number': card_data['number'],
            'card.holder': card_data['holder'],
            'card.expiryMonth': card_data['expiry_month'],
            'card.expiryYear': expiry_year,
            'card.cvv': card_data['cvv'],
            'createRegistration': 'true',
            'transactionCategory': 'EC',
            'standingInstruction.mode': 'INITIAL',
            'standingInstruction.type': 'UNSCHEDULED',
            'standingInstruction.source': 'CIT',
            'merchant.mcc': '5462',
            'merchant.name': 'WallClub Channel Teste',
            'merchant.street': 'Av Paulista 1000',
            'merchant.city': 'Sao Paulo',
            'merchant.state': 'SP',
            'merchant.countryCode': '076',
            'merchant.url': settings.MERCHANT_URL,
            'merchant.postcode': '01310100',
            'merchant.phone': '1133334444',
            'merchant.customerContactPhone': '1133334444',
            'customParameters[PAYMENT_METHOD]': 'CREDIT'
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
        parcelas: int = 1,
        loja_id: int = None
    ) -> Dict[str, Any]:
        """
        Pagamento com token existente (recorrência)
        Payment Type: DB com registrationId
        
        Args:
            registration_id: ID do token de recorrência
            amount: Valor da transação
            parcelas: Número de parcelas (padrão: 1)
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
            'transactionCategory': 'EC',
            'standingInstruction.mode': 'REPEATED',
            'standingInstruction.type': 'INSTALLMENT' if parcelas > 1 else 'UNSCHEDULED',
            'standingInstruction.source': 'MIT',
            'merchant.mcc': '5462',
            'merchant.name': 'WallClub Channel Teste',
            'merchant.street': 'Av Paulista 1000',
            'merchant.city': 'Sao Paulo',
            'merchant.state': 'SP',
            'merchant.countryCode': '076',
            'merchant.url': settings.MERCHANT_URL,
            'merchant.postcode': '01310100',
            'merchant.phone': '1133334444',
            'merchant.customerContactPhone': '1133334444',
            'customParameters[PAYMENT_METHOD]': 'CREDIT',
        }
        
        # Parcelamento (se aplicável)
        if parcelas > 1:
            data['standingInstruction.numberOfInstallments'] = str(parcelas)
        
        registrar_log('own.transacao', f'🔁 Pagamento recorrente: R$ {amount:.2f} ({parcelas}x)')
        
        # Pagamento com token usa endpoint diferente
        response = self._fazer_requisicao_oppwa(
            method='POST',
            endpoint=f'/v1/registrations/{registration_id}/payments',
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
    
    # ========================================================================
    # MÉTODOS DE GERENCIAMENTO DE REGISTRATION TOKENS
    # ========================================================================
    
    def delete_registration(
        self,
        registration_id: str,
        loja_id: int = None
    ) -> Dict[str, Any]:
        """
        Exclui (deregistra) um token de cartão
        
        Args:
            registration_id: ID do token de registro
            loja_id: ID da loja (opcional)
            
        Returns:
            Dict com sucesso e mensagem
        """
        credenciais = self._obter_credenciais_loja(loja_id)
        
        registrar_log('own.transacao', f'🗑️ Excluindo registration: {registration_id}')
        
        response = self._fazer_requisicao_oppwa(
            method='DELETE',
            endpoint=f'/v1/registrations/{registration_id}',
            entity_id=credenciais['entity_id'],
            access_token=credenciais['access_token'],
            environment=credenciais['environment'],
            data={'entityId': credenciais['entity_id']}
        )
        
        result_code = response.get('result', {}).get('code', '')
        
        if result_code in self.SUCCESS_CODES:
            registrar_log('own.transacao', f'✅ Registration excluído: {registration_id}')
            return {
                'sucesso': True,
                'mensagem': 'Token excluído com sucesso'
            }
        else:
            return {
                'sucesso': False,
                'mensagem': response.get('result', {}).get('description', 'Erro ao excluir token')
            }
    
    def get_registration_details(
        self,
        registration_id: str,
        loja_id: int = None
    ) -> Dict[str, Any]:
        """
        Consulta detalhes de um token de registro
        
        Args:
            registration_id: ID do token de registro
            loja_id: ID da loja (opcional)
            
        Returns:
            Dict com dados do token
        """
        credenciais = self._obter_credenciais_loja(loja_id)
        
        registrar_log('own.transacao', f'🔍 Consultando registration: {registration_id}')
        
        response = self._fazer_requisicao_oppwa(
            method='GET',
            endpoint=f'/v1/registrations/{registration_id}',
            entity_id=credenciais['entity_id'],
            access_token=credenciais['access_token'],
            environment=credenciais['environment'],
            data={'entityId': credenciais['entity_id']}
        )
        
        result_code = response.get('result', {}).get('code', '')
        
        if result_code in self.SUCCESS_CODES or response.get('id'):
            return {
                'sucesso': True,
                'registration_id': response.get('id'),
                'card_bin': response.get('card', {}).get('bin'),
                'card_last4': response.get('card', {}).get('last4Digits'),
                'card_holder': response.get('card', {}).get('holder'),
                'card_brand': response.get('paymentBrand'),
                'card_expiry_month': response.get('card', {}).get('expiryMonth'),
                'card_expiry_year': response.get('card', {}).get('expiryYear')
            }
        else:
            return {
                'sucesso': False,
                'mensagem': response.get('result', {}).get('description', 'Token não encontrado')
            }
    
    def list_registrations(
        self,
        shopper_id: str = None,
        loja_id: int = None
    ) -> Dict[str, Any]:
        """
        Lista tokens de registro
        
        Args:
            shopper_id: ID do comprador (opcional, filtra por comprador)
            loja_id: ID da loja (opcional)
            
        Returns:
            Dict com lista de tokens
        """
        credenciais = self._obter_credenciais_loja(loja_id)
        
        registrar_log('own.transacao', f'📋 Listando registrations (shopper: {shopper_id})')
        
        data = {'entityId': credenciais['entity_id']}
        if shopper_id:
            data['merchantTransactionId'] = shopper_id
        
        response = self._fazer_requisicao_oppwa(
            method='GET',
            endpoint='/v1/registrations',
            entity_id=credenciais['entity_id'],
            access_token=credenciais['access_token'],
            environment=credenciais['environment'],
            data=data
        )
        
        # A resposta pode vir como lista ou objeto com 'registrations'
        registrations = response.get('registrations', [])
        if not registrations and isinstance(response, list):
            registrations = response
        
        tokens = []
        for reg in registrations:
            tokens.append({
                'registration_id': reg.get('id'),
                'card_bin': reg.get('card', {}).get('bin'),
                'card_last4': reg.get('card', {}).get('last4Digits'),
                'card_holder': reg.get('card', {}).get('holder'),
                'card_brand': reg.get('paymentBrand'),
                'card_expiry_month': reg.get('card', {}).get('expiryMonth'),
                'card_expiry_year': reg.get('card', {}).get('expiryYear')
            })
        
        return {
            'sucesso': True,
            'total': len(tokens),
            'tokens': tokens
        }
    
    # ========================================================================
    # MÉTODOS ADAPTER - COMPATIBILIDADE COM INTERFACE PINBANK
    # ========================================================================
    
    def efetuar_transacao_cartao(self, dados_transacao: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adapter: Compatibilidade com interface Pinbank
        Converte chamada Pinbank para Own (create_payment_debit)
        
        Args:
            dados_transacao: Dict com dados no formato Pinbank
                - numero_cartao
                - data_validade (MM/YYYY)
                - codigo_seguranca
                - nome_impresso
                - valor
                - quantidade_parcelas
                - forma_pagamento (1=vista, 2=parcelado)
                
        Returns:
            Dict com sucesso, nsu, codigo_autorizacao, mensagem, dados
        """
        # Converter dados Pinbank → Own
        card_data = {
            'number': dados_transacao['numero_cartao'],
            'holder': dados_transacao['nome_impresso'],
            'expiry_month': dados_transacao['data_validade'].split('/')[0],
            'expiry_year': dados_transacao['data_validade'].split('/')[1],
            'cvv': dados_transacao['codigo_seguranca'],
            'brand': dados_transacao.get('bandeira', 'VISA').upper()
        }
        
        amount = Decimal(str(dados_transacao['valor']))
        parcelas = int(dados_transacao.get('quantidade_parcelas', 1))
        
        # Chamar método Own
        resultado = self.create_payment_debit(
            card_data=card_data,
            amount=amount,
            parcelas=parcelas,
            loja_id=self.loja_id
        )
        
        # Converter resposta Own → Pinbank
        if resultado.get('sucesso'):
            return {
                'sucesso': True,
                'nsu': resultado.get('nsu'),
                'codigo_autorizacao': resultado.get('codigo_autorizacao'),
                'mensagem': resultado.get('mensagem'),
                'dados': {
                    'nsu': resultado.get('nsu'),
                    'codigo_autorizacao': resultado.get('codigo_autorizacao'),
                    'payment_id': resultado.get('own_payment_id'),
                    'card_bin': resultado.get('card_bin'),
                    'card_last4': resultado.get('card_last4')
                }
            }
        else:
            return {
                'sucesso': False,
                'mensagem': resultado.get('mensagem'),
                'codigo_erro': resultado.get('codigo_erro')
            }
    
    def incluir_cartao_tokenizado(self, dados_cartao: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adapter: Compatibilidade com interface Pinbank
        Converte chamada Pinbank para Own (create_payment_with_tokenization)
        
        IMPORTANTE: Own tokeniza JUNTO com pré-autorização de R$ 1,00
        
        Args:
            dados_cartao: Dict com dados no formato Pinbank
                - numero_cartao
                - data_validade (MM/YYYY)
                - codigo_seguranca
                - nome_impresso
                - cpf_comprador
                
        Returns:
            Dict com sucesso, cartao_id (registration_id), mensagem
        """
        # Converter dados Pinbank → Own
        card_data = {
            'number': dados_cartao['numero_cartao'],
            'holder': dados_cartao['nome_impresso'],
            'expiry_month': dados_cartao['data_validade'].split('/')[0],
            'expiry_year': dados_cartao['data_validade'].split('/')[1],
            'cvv': dados_cartao['codigo_seguranca'],
            'brand': dados_cartao.get('bandeira', 'VISA').upper()
        }
        
        # Own: Pré-autorização R$ 1,00 + tokenização
        resultado = self.create_payment_with_tokenization(
            card_data=card_data,
            amount=Decimal('1.00'),
            loja_id=self.loja_id
        )
        
        # Converter resposta Own → Pinbank
        if resultado.get('sucesso'):
            return {
                'sucesso': True,
                'cartao_id': resultado.get('registration_id'),  # Pinbank espera 'cartao_id'
                'mensagem': 'Cartão tokenizado com sucesso',
                'card_last4': resultado.get('card_last4'),
                'card_brand': resultado.get('card_brand'),
                'payment_id': resultado.get('own_payment_id')  # ID da pré-auth (para estornar depois)
            }
        else:
            return {
                'sucesso': False,
                'mensagem': resultado.get('mensagem')
            }
    
    def excluir_cartao_tokenizado(self, cartao_id: str) -> Dict[str, Any]:
        """
        Adapter: Compatibilidade com interface Pinbank
        Converte chamada Pinbank para Own (delete_registration)
        
        Args:
            cartao_id: ID do token (registration_id)
            
        Returns:
            Dict com sucesso e mensagem
        """
        return self.delete_registration(
            registration_id=cartao_id,
            loja_id=self.loja_id
        )
    
    def consulta_dados_cartao_tokenizado(self, cartao_id: str) -> Dict[str, Any]:
        """
        Adapter: Compatibilidade com interface Pinbank
        Converte chamada Pinbank para Own (get_registration_details)
        
        Args:
            cartao_id: ID do token (registration_id)
            
        Returns:
            Dict com dados do cartão
        """
        resultado = self.get_registration_details(
            registration_id=cartao_id,
            loja_id=self.loja_id
        )
        
        # Converter resposta Own → Pinbank
        if resultado.get('sucesso'):
            return {
                'sucesso': True,
                'cartao_id': resultado.get('registration_id'),
                'numero_truncado': f"{resultado.get('card_bin')}******{resultado.get('card_last4')}",
                'bandeira': resultado.get('card_brand'),
                'nome_impresso': resultado.get('card_holder'),
                'validade': f"{resultado.get('card_expiry_month')}/{resultado.get('card_expiry_year')}"
            }
        else:
            return resultado
    
    def consultar_cartoes(self, status_cartao: str = "Todos", numero_truncado: str = "") -> Dict[str, Any]:
        """
        Adapter: Compatibilidade com interface Pinbank
        Converte chamada Pinbank para Own (list_registrations)
        
        Args:
            status_cartao: Filtro de status (ignorado na Own)
            numero_truncado: Filtro por número (ignorado na Own)
            
        Returns:
            Dict com lista de cartões
        """
        resultado = self.list_registrations(loja_id=self.loja_id)
        
        if resultado.get('sucesso'):
            # Converter formato Own → Pinbank
            cartoes = []
            for token in resultado.get('tokens', []):
                cartoes.append({
                    'cartao_id': token.get('registration_id'),
                    'numero_truncado': f"{token.get('card_bin')}******{token.get('card_last4')}",
                    'bandeira': token.get('card_brand'),
                    'nome_impresso': token.get('card_holder'),
                    'validade': f"{token.get('card_expiry_month')}/{token.get('card_expiry_year')}",
                    'status': 'Ativo'
                })
            
            return {
                'sucesso': True,
                'total': len(cartoes),
                'cartoes': cartoes
            }
        else:
            return resultado
    
    def cancelar_transacao(self, nsu_operacao: str, valor: Decimal) -> Dict[str, Any]:
        """
        Adapter: Compatibilidade com interface Pinbank
        Converte chamada Pinbank para Own (refund_payment)
        
        Args:
            nsu_operacao: NSU/Payment ID da transação
            valor: Valor a estornar
            
        Returns:
            Dict com sucesso e mensagem
        """
        resultado = self.refund_payment(
            payment_id=nsu_operacao,
            amount=valor,
            loja_id=self.loja_id
        )
        
        # Converter resposta Own → Pinbank
        if resultado.get('sucesso'):
            return {
                'sucesso': True,
                'mensagem': 'Transação cancelada com sucesso',
                'nsu_cancelamento': resultado.get('refund_id')
            }
        else:
            return resultado
