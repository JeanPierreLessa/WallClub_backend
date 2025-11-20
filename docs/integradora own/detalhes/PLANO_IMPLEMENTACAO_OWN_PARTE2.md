# PLANO DE IMPLEMENTAÇÃO - PARTE 2

## 📊 MAPEAMENTO PINBANK VS OWN (Continuação)

### 4. Cancelamento/Estorno

#### Pinbank Atual

```python
# pinbank/services_transacoes_pagamento.py

def cancelar_transacao_pinbank(transacao_id):
    transacao = Transacao.objects.get(id=transacao_id)
    
    response = pinbank_service.cancelar_transacao(
        nsu=transacao.nsu_pinbank,
        valor=transacao.valor
    )
    
    if response['sucesso']:
        transacao.status = 'CANCELADA'
        transacao.save()
```

#### Own Financial Equivalente

```python
# own/services_transacoes.py

def cancelar_transacao_own(transacao_id):
    transacao = Transacao.objects.get(id=transacao_id)
    
    # REFUND (total ou parcial)
    response = own_service.refund_payment(
        payment_id=transacao.own_payment_id,
        amount=transacao.valor,
        currency='BRL'
    )
    
    if response['result']['code'] in ['000.000.000', '000.100.110']:
        transacao.status = 'ESTORNADA'
        transacao.own_refund_id = response['id']
        transacao.save()
```

**Endpoint:** `POST https://eu-prod.oppwa.com/v1/payments/{id}`

**Payload:**
```json
{
  "entityId": "{ENTITY_ID}",
  "amount": "100.00",
  "currency": "BRL",
  "paymentType": "RF"
}
```

---

### 5. Consulta de Transações

#### Pinbank Atual

```python
# pinbank/cargas_pinbank/services_carga_checkout.py

def consultar_transacoes_pinbank(data_inicio, data_fim):
    # API Pinbank retorna transações do período
    response = pinbank_api.consultar_transacoes(
        data_inicio=data_inicio,
        data_fim=data_fim
    )
    
    for transacao in response['transacoes']:
        salvar_em_base_gestao(transacao)
```

#### Own Financial Equivalente

```python
# own/cargas_own/services_carga_transacoes.py

def consultar_transacoes_own(data_inicio, data_fim, cnpj_cliente):
    # API Own - Consulta Transações Gerais
    response = own_api.buscar_transacoes_gerais(
        cnpjCliente=cnpj_cliente,
        dataInicial=data_inicio.strftime('%Y-%m-%d %H:%M'),
        dataFinal=data_fim.strftime('%Y-%m-%d %H:%M')
    )
    
    for transacao in response:
        salvar_em_base_gestao_own(transacao)
```

**Endpoint:** `POST https://acquirer.own.financial/agilli/transacoes/v2/buscaTransacoesGerais`

**Payload:**
```json
{
  "cnpjCliente": "00000000000000",
  "docParceiro": "11111111111111",
  "dataInicial": "2025-01-08 00:00",
  "dataFinal": "2025-01-08 23:59"
}
```

**Response:**
```json
[
  {
    "cnpjCpfCliente": "00000000000000",
    "cnpjCpfParceiro": "11111111111111",
    "identificadorTransacao": "241228001856006195",
    "data": "2024-12-28T11:07:34",
    "numeroSerieEquipamento": "6C514723",
    "valor": 3200,
    "quantidadeParcelas": 2,
    "mdr": 173.12,
    "valorAntecipacaoTotal": 3026.88,
    "statusTransacao": "VENDA LIQUIDADA",
    "bandeira": "MASTERCARD",
    "modalidade": "CREDITO PARC 2 a 6",
    "codigoAutorizacao": "097939",
    "numeroCartao": "52343107****9237",
    "parcelas": [...]
  }
]
```

---

### 6. Consulta de Liquidações

#### Pinbank Atual

```python
# Pinbank não tem endpoint específico de liquidações
# Usa mesma consulta de transações
```

#### Own Financial Equivalente

```python
# own/cargas_own/services_carga_liquidacoes.py

def consultar_liquidacoes_own(data_pagamento, cnpj_cliente):
    # API Own - Consulta Liquidações
    response = own_api.consultar_liquidacoes(
        dataPagamentoReal=data_pagamento.strftime('%Y-%m-%d'),
        cnpjCliente=cnpj_cliente
    )
    
    for liquidacao in response:
        atualizar_status_pagamento(liquidacao)
```

**Endpoint:** `GET https://acquirer.own.financial/agilli/parceiro/v2/consultaLiquidacoes`

**Params:**
```
?dataPagamentoReal=2024-11-25&cnpjCliente=00000000000000
```

**Response:**
```json
[
  {
    "lancamentoId": 878021667,
    "statusPagamento": "Pago",
    "dataPagamentoPrevista": "25/11/2024",
    "numeroParcela": 5,
    "valor": 75.41,
    "dataPagamentoReal": "25/11/2024",
    "antecipada": "N",
    "identificadorTransacao": "250108001860537457",
    "bandeira": "ELO",
    "modalidade": "CREDITO PARC 7 A 12",
    "nsuTransacao": "423936371",
    "numeroTitulo": "37525960"
  }
]
```

---

## 🔧 ESPECIFICAÇÃO TÉCNICA

### Models (Django)

```python
# own/models.py

from django.db import models
from decimal import Decimal

class OwnConfiguration(models.Model):
    """Configuração de acesso à API Own"""
    loja = models.ForeignKey('estr_organizacional.Loja', on_delete=models.CASCADE)
    entity_id = models.CharField(max_length=100)
    access_token = models.CharField(max_length=500)
    environment = models.CharField(
        max_length=10,
        choices=[('TEST', 'Test'), ('LIVE', 'Live')],
        default='TEST'
    )
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'own_configuration'
        verbose_name = 'Configuração Own'


class OwnTransaction(models.Model):
    """Registro de transações Own"""
    loja = models.ForeignKey('estr_organizacional.Loja', on_delete=models.CASCADE)
    checkout_token = models.ForeignKey(
        'link_pagamento_web.CheckoutToken',
        null=True,
        on_delete=models.SET_NULL
    )
    
    # IDs Own
    own_payment_id = models.CharField(max_length=100, unique=True)
    registration_id = models.CharField(max_length=100, null=True, blank=True)
    
    # Dados da transação
    payment_type = models.CharField(max_length=10)  # DB, PA, RF, RV, RB
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='BRL')
    payment_brand = models.CharField(max_length=50)  # VISA, MASTER, ELO
    
    # Resultado
    result_code = models.CharField(max_length=20)
    result_description = models.TextField()
    
    # Dados do cartão (mascarados)
    card_bin = models.CharField(max_length=6, null=True)
    card_last4 = models.CharField(max_length=4, null=True)
    card_holder = models.CharField(max_length=100, null=True)
    
    # Timestamps
    transaction_timestamp = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'own_transaction'
        indexes = [
            models.Index(fields=['own_payment_id']),
            models.Index(fields=['loja', 'created_at']),
        ]


class OwnRegistration(models.Model):
    """Tokens de cartão para recorrência"""
    loja = models.ForeignKey('estr_organizacional.Loja', on_delete=models.CASCADE)
    cliente = models.ForeignKey('cliente.Cliente', null=True, on_delete=models.SET_NULL)
    
    registration_id = models.CharField(max_length=100, unique=True)
    initial_transaction_id = models.CharField(max_length=100)
    
    # Dados mascarados
    card_bin = models.CharField(max_length=6)
    card_last4 = models.CharField(max_length=4)
    card_brand = models.CharField(max_length=50)
    card_holder = models.CharField(max_length=100)
    
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'own_registration'


class OwnCredenciamento(models.Model):
    """Processo de credenciamento via API Own"""
    loja = models.ForeignKey('estr_organizacional.Loja', on_delete=models.CASCADE)
    
    # Protocolo Own
    protocolo_core = models.CharField(max_length=50, unique=True)
    numero_contrato = models.CharField(max_length=50, null=True, blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('PENDENTE', 'Pendente Envio'),
            ('EM_ANALISE', 'Em Análise'),
            ('APROVADO', 'Aprovado'),
            ('REPROVADO', 'Reprovado'),
        ],
        default='PENDENTE'
    )
    motivo_reprovacao = models.TextField(null=True, blank=True)
    
    # Dados cadastrais (JSON)
    dados_cadastrais = models.JSONField()
    documentos = models.JSONField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    enviado_em = models.DateTimeField(null=True, blank=True)
    respondido_em = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'own_credenciamento'
```

---

### Services - Autenticação

```python
# own/services_autenticacao.py

import requests
from datetime import datetime, timedelta
from django.core.cache import cache
from wallclub_core.utilitarios.log_control import registrar_log

class OwnAuthService:
    """Service de autenticação OAuth 2.0 com Own Financial"""
    
    AUTH_URL_TEST = 'https://acquirer-qa.own.financial/agilli/v2/auth'
    AUTH_URL_LIVE = 'https://acquirer.own.financial/agilli/v2/auth'
    
    def __init__(self, environment='LIVE'):
        self.environment = environment
        self.auth_url = self.AUTH_URL_LIVE if environment == 'LIVE' else self.AUTH_URL_TEST
    
    def get_access_token(self, client_id, client_secret, scope):
        """
        Obtém access token via OAuth 2.0
        Cache de 4 minutos (token válido por 5min)
        """
        cache_key = f'own_token_{client_id}'
        token = cache.get(cache_key)
        
        if token:
            registrar_log('own.auth', f'✅ Token em cache: {client_id}')
            return token
        
        try:
            payload = {
                'client_id': client_id,
                'client_secret': client_secret,
                'scope': scope,
                'grant_type': 'client_credentials'
            }
            
            response = requests.post(
                self.auth_url,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            access_token = data['access_token']
            expires_in = data['expires_in']  # 300 segundos
            
            # Cache por 4 minutos (margem de segurança)
            cache.set(cache_key, access_token, timeout=expires_in - 60)
            
            registrar_log('own.auth', f'✅ Novo token obtido: {client_id}')
            return access_token
            
        except requests.exceptions.RequestException as e:
            registrar_log('own.auth', f'❌ Erro autenticação: {str(e)}', level='ERROR')
            raise Exception(f'Falha na autenticação Own: {str(e)}')
```

---

### Services - Transações e-SiTef

```python
# own/services_transacoes.py

import requests
from decimal import Decimal
from datetime import datetime
from .services_autenticacao import OwnAuthService
from .models import OwnTransaction, OwnConfiguration
from wallclub_core.utilitarios.log_control import registrar_log

class OwnTransacaoService:
    """Service de transações e-SiTef (Carat)"""
    
    BASE_URL_TEST = 'https://eu-test.oppwa.com'
    BASE_URL_LIVE = 'https://eu-prod.oppwa.com'
    
    # Result codes de sucesso
    SUCCESS_CODES = [
        '000.000.000',  # Transaction succeeded
        '000.100.110',  # Request successfully processed
    ]
    
    def __init__(self, loja):
        self.loja = loja
        self.config = OwnConfiguration.objects.get(loja=loja, ativo=True)
        self.base_url = (
            self.BASE_URL_LIVE if self.config.environment == 'LIVE' 
            else self.BASE_URL_TEST
        )
        self.entity_id = self.config.entity_id
        self.access_token = self.config.access_token
    
    def _make_request(self, method, endpoint, data=None):
        """Requisição HTTP com autenticação"""
        url = f'{self.base_url}{endpoint}'
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        try:
            if method == 'POST':
                response = requests.post(url, data=data, headers=headers, timeout=30)
            elif method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            else:
                raise ValueError(f'Método não suportado: {method}')
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            registrar_log('own.transacao', f'⏱️ Timeout na requisição: {url}', level='WARNING')
            raise Exception('Timeout na comunicação com Own Financial')
        except requests.exceptions.RequestException as e:
            registrar_log('own.transacao', f'❌ Erro HTTP: {str(e)}', level='ERROR')
            raise Exception(f'Erro na comunicação: {str(e)}')
    
    def create_payment_debit(self, card_data, amount, parcelas=1):
        """
        Pagamento débito (captura imediata)
        Equivalente ao checkout web atual
        """
        data = {
            'entityId': self.entity_id,
            'amount': f'{amount:.2f}',
            'currency': 'BRL',
            'paymentBrand': card_data['brand'].upper(),
            'paymentType': 'DB',  # Debit
            'card.number': card_data['number'],
            'card.holder': card_data['holder'],
            'card.expiryMonth': card_data['expiry_month'],
            'card.expiryYear': card_data['expiry_year'],
            'card.cvv': card_data['cvv'],
        }
        
        # Parcelamento (se aplicável)
        if parcelas > 1:
            data['installments'] = str(parcelas)
        
        registrar_log('own.transacao', f'💳 Criando pagamento DB: R$ {amount:.2f}')
        
        response = self._make_request('POST', '/v1/payments', data)
        
        # Salvar transação
        transaction = OwnTransaction.objects.create(
            loja=self.loja,
            own_payment_id=response['id'],
            payment_type='DB',
            amount=amount,
            currency='BRL',
            payment_brand=response.get('paymentBrand', ''),
            result_code=response['result']['code'],
            result_description=response['result']['description'],
            card_bin=response.get('card', {}).get('bin'),
            card_last4=response.get('card', {}).get('last4Digits'),
            card_holder=response.get('card', {}).get('holder'),
            transaction_timestamp=datetime.now()
        )
        
        # Verificar sucesso
        if response['result']['code'] in self.SUCCESS_CODES:
            registrar_log('own.transacao', f'✅ Pagamento aprovado: {response["id"]}')
            return {
                'sucesso': True,
                'own_payment_id': response['id'],
                'nsu': response['id'],
                'codigo_autorizacao': response.get('descriptor', ''),
                'mensagem': response['result']['description']
            }
        else:
            registrar_log('own.transacao', f'❌ Pagamento reprovado: {response["result"]["code"]}')
            return {
                'sucesso': False,
                'codigo_erro': response['result']['code'],
                'mensagem': response['result']['description']
            }
    
    def create_payment_with_tokenization(self, card_data, amount):
        """
        Pagamento com tokenização (para recorrência)
        Pre-authorization + createRegistration
        """
        data = {
            'entityId': self.entity_id,
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
        
        registrar_log('own.transacao', f'🔐 Criando PA com tokenização: R$ {amount:.2f}')
        
        response = self._make_request('POST', '/v1/payments', data)
        
        if response['result']['code'] in self.SUCCESS_CODES:
            return {
                'sucesso': True,
                'own_payment_id': response['id'],
                'registration_id': response.get('registrationId'),
                'card_last4': response.get('card', {}).get('last4Digits')
            }
        else:
            return {
                'sucesso': False,
                'mensagem': response['result']['description']
            }
    
    def refund_payment(self, payment_id, amount):
        """Estorno total ou parcial"""
        data = {
            'entityId': self.entity_id,
            'amount': f'{amount:.2f}',
            'currency': 'BRL',
            'paymentType': 'RF'  # Refund
        }
        
        registrar_log('own.transacao', f'↩️ Estornando: {payment_id} - R$ {amount:.2f}')
        
        response = self._make_request('POST', f'/v1/payments/{payment_id}', data)
        
        if response['result']['code'] in self.SUCCESS_CODES:
            registrar_log('own.transacao', f'✅ Estorno aprovado: {response["id"]}')
            return {
                'sucesso': True,
                'refund_id': response['id']
            }
        else:
            return {
                'sucesso': False,
                'mensagem': response['result']['description']
            }
```

Continua na PARTE 3...
