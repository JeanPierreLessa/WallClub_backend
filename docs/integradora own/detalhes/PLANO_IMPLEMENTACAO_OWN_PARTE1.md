# PLANO DE IMPLEMENTAÇÃO - INTEGRAÇÃO OWN FINANCIAL

**Versão:** 1.1  
**Data:** 20/11/2025  
**Responsável:** Tech Lead WallClub  
**Status:** Em Implementação - Com Bloqueadores

---

## 📋 ÍNDICE

1. [Visão Geral](#visão-geral)
2. [Arquitetura da Solução](#arquitetura-da-solução)
3. [Mapeamento Pinbank vs Own](#mapeamento-pinbank-vs-own)
4. [Especificação Técnica](#especificação-técnica)
5. [Estrutura de Código](#estrutura-de-código)
6. [Cronograma de Implementação](#cronograma-de-implementação)

---

## 🎯 VISÃO GERAL

### Contexto

Integração da **Own Financial** como gateway de pagamento **prioritário** no WallClub, mantendo Pinbank como contingência.

### Tecnologia Escolhida

**e-SiTef (Carat) - API REST**
- Plataforma: OPPWA (Open Payment Platform)
- Hosts:
  - Test: `https://eu-test.oppwa.com/`
  - Live: `https://eu-prod.oppwa.com/`
- Autenticação: Bearer Token (OAuth 2.0)
- Formato: JSON
- Protocolo: HTTPS

### Estratégia de Adoção

```
┌─────────────────────────────────────────┐
│  NOVAS LOJAS → Own Financial (padrão)  │
│  LOJAS EXISTENTES → Pinbank (mantém)   │
└─────────────────────────────────────────┘
```

**Benefícios:**
- ✅ Sem migração forçada (zero risco)
- ✅ Convivência pacífica
- ✅ Troca sob demanda (processo controlado)

---

## 🏗️ ARQUITETURA DA SOLUÇÃO

### Componentes Atuais (Pinbank)

```
WallClub Django
├── pinbank/
│   ├── services_transacoes_pagamento.py
│   ├── services_tokenizacao.py
│   └── cargas_pinbank/
│       ├── services_carga_credenciadora.py
│       └── services_carga_checkout.py
├── checkout/
│   ├── link_pagamento_web/
│   │   ├── services.py
│   │   ├── services_2fa.py
│   │   └── models.py
│   └── link_recorrencia_web/
│       ├── services.py
│       └── models.py
└── parametros_wallclub/
    └── calculadora_base_credenciadora.py
```

### Novos Componentes (Own Financial)

```
WallClub Django
├── own/  ← NOVO MÓDULO
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py
│   ├── services_autenticacao.py
│   ├── services_transacoes.py
│   ├── services_tokenizacao.py
│   ├── services_consultas.py
│   ├── services_credenciamento.py
│   └── cargas_own/
│       ├── services_carga_transacoes.py
│       └── services_carga_liquidacoes.py
├── checkout/
│   ├── services_gateway_router.py  ← NOVO (roteador)
│   └── link_pagamento_web/
│       └── services_own.py  ← NOVO
└── portais/
    └── admin/
        └── views_credenciamento_own.py  ← NOVO
```

### Roteador de Gateways

```python
# checkout/services_gateway_router.py

class GatewayRouter:
    """
    Roteia transações para gateway apropriado
    baseado na configuração da loja
    """
    
    @staticmethod
    def get_gateway_service(loja):
        """
        Retorna service apropriado (Pinbank ou Own)
        """
        if loja.gateway_ativo == 'OWN':
            from own.services_transacoes import OwnTransacaoService
            return OwnTransacaoService()
        else:
            from pinbank.services_transacoes_pagamento import PinbankService
            return PinbankService()
```

---

## 📊 MAPEAMENTO PINBANK VS OWN

### 1. Checkout Web (Link de Pagamento)

#### Pinbank Atual

```python
# checkout/link_pagamento_web/services.py

def processar_pagamento_pinbank(checkout_token):
    # 1. Validar token (30min)
    # 2. Coletar dados cartão
    # 3. Chamar Pinbank API
    response = pinbank_service.efetuar_transacao_encrypted(
        numero_cartao=cartao_encrypted,
        cvv=cvv_encrypted,
        validade=validade,
        valor=valor,
        parcelas=parcelas
    )
    # 4. Processar resposta síncrona
    if response['aprovado']:
        salvar_transacao()
```

#### Own Financial Equivalente

```python
# checkout/link_pagamento_web/services_own.py

def processar_pagamento_own(checkout_token):
    # 1. Validar token (30min)
    # 2. Coletar dados cartão
    # 3. Chamar e-SiTef API
    
    # SYNCHRONOUS DEBIT PAYMENT
    response = own_service.create_payment(
        payment_type='DB',  # Debit (captura imediata)
        amount=valor,
        currency='BRL',
        card_number=numero_cartao,
        card_cvv=cvv,
        card_expiry_month=mes,
        card_expiry_year=ano,
        card_holder=nome_titular
    )
    
    # 4. Processar resposta síncrona
    if response['result']['code'] in ['000.000.000', '000.100.110']:
        salvar_transacao(
            own_payment_id=response['id'],
            nsu=response['id']
        )
```

**Endpoint:** `POST https://eu-prod.oppwa.com/v1/payments`

**Payload:**
```json
{
  "entityId": "{ENTITY_ID}",
  "amount": "100.00",
  "currency": "BRL",
  "paymentBrand": "VISA",
  "paymentType": "DB",
  "card.number": "4200000000000000",
  "card.holder": "NOME TITULAR",
  "card.expiryMonth": "12",
  "card.expiryYear": "2025",
  "card.cvv": "123"
}
```

**Response:**
```json
{
  "id": "8ac7a4a18d1234567890abcdef",
  "paymentType": "DB",
  "paymentBrand": "VISA",
  "amount": "100.00",
  "currency": "BRL",
  "descriptor": "1234.5678.9012",
  "result": {
    "code": "000.000.000",
    "description": "Transaction succeeded"
  },
  "card": {
    "bin": "420000",
    "last4Digits": "0000",
    "holder": "NOME TITULAR",
    "expiryMonth": "12",
    "expiryYear": "2025"
  },
  "timestamp": "2025-11-14 12:30:00+0000"
}
```

---

### 2. Link de Recorrência (Tokenização)

#### Pinbank Atual

```python
# checkout/link_recorrencia_web/services.py

def tokenizar_cartao_pinbank(recorrencia_token):
    # 1. Validar token (72h)
    # 2. Coletar dados cartão
    # 3. Tokenizar via Pinbank
    response = pinbank_service.incluir_cartao_encrypted(
        numero_cartao=cartao_encrypted,
        cvv=cvv_encrypted,
        validade=validade,
        nome_titular=nome
    )
    # 4. Salvar token
    if response['sucesso']:
        salvar_token(
            token_pinbank=response['token_cartao'],
            ultimos_digitos=response['ultimos_4_digitos']
        )
```

#### Own Financial Equivalente

```python
# checkout/link_recorrencia_web/services_own.py

def tokenizar_cartao_own(recorrencia_token):
    # 1. Validar token (72h)
    # 2. Coletar dados cartão
    
    # OPÇÃO 1: Tokenização durante pagamento inicial
    response = own_service.create_payment(
        payment_type='PA',  # Pre-authorization
        amount='1.00',  # Valor simbólico
        currency='BRL',
        card_number=numero_cartao,
        card_cvv=cvv,
        card_expiry_month=mes,
        card_expiry_year=ano,
        card_holder=nome_titular,
        create_registration=True,  # ← TOKENIZAR
        standingInstruction_mode='INITIAL',
        standingInstruction_type='UNSCHEDULED',
        standingInstruction_source='CIT'
    )
    
    # 3. Salvar registration token
    if response['result']['code'] in ['000.000.000', '000.100.110']:
        salvar_token(
            registration_id=response['registrationId'],
            own_payment_id=response['id'],
            ultimos_digitos=response['card']['last4Digits']
        )
        
        # 4. Reverter pre-auth (opcional)
        own_service.reverse_payment(response['id'])
```

**Endpoint:** `POST https://eu-prod.oppwa.com/v1/payments`

**Payload (com tokenização):**
```json
{
  "entityId": "{ENTITY_ID}",
  "amount": "1.00",
  "currency": "BRL",
  "paymentBrand": "VISA",
  "paymentType": "PA",
  "card.number": "4200000000000000",
  "card.holder": "NOME TITULAR",
  "card.expiryMonth": "12",
  "card.expiryYear": "2025",
  "card.cvv": "123",
  "createRegistration": "true",
  "standingInstruction.mode": "INITIAL",
  "standingInstruction.type": "UNSCHEDULED",
  "standingInstruction.source": "CIT"
}
```

**Response:**
```json
{
  "id": "8ac7a4a18d1234567890abcdef",
  "registrationId": "8ac7a4a18d9876543210fedcba",
  "paymentType": "PA",
  "amount": "1.00",
  "result": {
    "code": "000.000.000",
    "description": "Transaction succeeded"
  },
  "card": {
    "last4Digits": "0000"
  }
}
```

---

### 3. Cobranças Recorrentes

#### Pinbank Atual

```python
# checkout/tasks_recorrencia.py (Celery)

def cobrar_recorrencia_pinbank(recorrencia_id):
    recorrencia = RecorrenciaAgendada.objects.get(id=recorrencia_id)
    
    # Usar token salvo
    response = pinbank_service.efetuar_transacao_cartao_id_encrypted(
        token_cartao=recorrencia.token_pinbank,
        valor=recorrencia.valor,
        parcelas=1
    )
    
    if response['aprovado']:
        registrar_cobranca_sucesso()
```

#### Own Financial Equivalente

```python
# checkout/tasks_recorrencia.py (Celery)

def cobrar_recorrencia_own(recorrencia_id):
    recorrencia = RecorrenciaAgendada.objects.get(id=recorrencia_id)
    
    # REBILL usando registration token
    response = own_service.create_payment_with_token(
        registration_id=recorrencia.registration_id_own,
        payment_type='DB',
        amount=recorrencia.valor,
        currency='BRL',
        standingInstruction_mode='REPEATED',
        standingInstruction_type='UNSCHEDULED',
        standingInstruction_source='MIT',
        standingInstruction_initialTransactionId=recorrencia.initial_transaction_id
    )
    
    if response['result']['code'] in ['000.000.000', '000.100.110']:
        registrar_cobranca_sucesso(
            own_payment_id=response['id']
        )
```

**Endpoint:** `POST https://eu-prod.oppwa.com/v1/registrations/{registrationId}/payments`

**Payload:**
```json
{
  "entityId": "{ENTITY_ID}",
  "amount": "100.00",
  "currency": "BRL",
  "paymentType": "DB",
  "standingInstruction.mode": "REPEATED",
  "standingInstruction.type": "UNSCHEDULED",
  "standingInstruction.source": "MIT",
  "standingInstruction.initialTransactionId": "8ac7a4a18d1234567890abcdef"
}
```

---

## 🔴 BLOQUEADORES IDENTIFICADOS

### 1. CalculadoraBaseGestao Hardcoded para Pinbank

**Arquivo:** `parametros_wallclub/calculadora_base_gestao.py`

**Problema:**
A classe `CalculadoraBaseGestao` está hardcoded para buscar dados exclusivamente da tabela `transactiondata` (Pinbank). Não há suporte para processar transações da tabela `transactiondata_own`.

**Impacto no POS Own:**
- Endpoint `/trdata_own/` funciona mas retorna valores zerados
- Calculadora falha com erro: `Loja não encontrada para NSU {nsu}`
- JSON de resposta retorna:
  - `vparcela`: R$ 0.00
  - `tarifas`: R$ 0.00  
  - `encargos`: R$ 0.00
  - `vdesconto`: R$ 0.00
  - `pagoavista`: R$ 0.00

**Causa raiz:**
```python
# calculadora_base_gestao.py (linha ~50)
def calcular_valores_primarios(self, dados_linha):
    # Busca hardcoded na tabela transactiondata
    cursor.execute("""
        SELECT ... FROM transactiondata t
        INNER JOIN terminais term ON t.terminal = term.terminal
        WHERE t.NsuOperacao = %s  -- Campo nsuPinbank
    """, [dados_linha['NsuOperacao']])
```

**Soluções possíveis:**

**Opção A - Refatorar Calculadora (RECOMENDADO):**
```python
def calcular_valores_primarios(self, dados_linha, tabela='transactiondata'):
    if tabela == 'transactiondata_own':
        # Query para Own
        cursor.execute("""
            SELECT ... FROM transactiondata_own t
            INNER JOIN terminais term ON t.terminal = term.terminal
            WHERE t.txTransactionId = %s
        """, [dados_linha['txTransactionId']])
    else:
        # Query original Pinbank
        cursor.execute("""
            SELECT ... FROM transactiondata t
            ...
        """)
```

**Opção B - Calcular Manualmente (TEMPORÁRIO):**
- Implementar cálculos diretamente no `TRDataOwnService`
- Não usar `CalculadoraBaseGestao`
- Manter paridade com lógica Pinbank

**Decisão:** Fazer outros ajustes primeiro, depois resolver calculadora

**Referências:**
- `docs/integradora own/API_TRDATA_OWN.md` (seção Problemas Conhecidos)
- `services/django/posp2/services_transacao_own.py` (linha ~186)

---

Continua na PARTE 2...
