# PLANO DE IMPLEMENTAÇÃO - PARTE 4

## 🔄 FLUXOS DETALHADOS

### Fluxo 1: Checkout Web com Own Financial

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Cliente acessa link de pagamento                        │
│    GET /checkout/{token}                                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Sistema valida token (30min)                            │
│    - Verifica validade                                      │
│    - Identifica loja                                        │
│    - Verifica gateway_ativo da loja                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Cliente preenche dados do cartão                        │
│    - Número, CVV, validade, nome                           │
│    - Validação client-side                                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Backend roteia para gateway apropriado                  │
│    gateway_service = GatewayRouter.get_gateway_service(loja)│
└─────────────────────────────────────────────────────────────┘
                            ↓
        ┌───────────────────┴───────────────────┐
        │                                       │
┌───────▼────────┐                    ┌────────▼────────┐
│ PINBANK        │                    │ OWN FINANCIAL   │
│ (contingência) │                    │ (prioritário)   │
└───────┬────────┘                    └────────┬────────┘
        │                                      │
        │ POST EfetuarTransacao                │ POST /v1/payments
        │                                      │ paymentType=DB
        │                                      │
        ▼                                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Resposta síncrona (1-4s)                                │
│    - Aprovado/Reprovado                                     │
│    - NSU/ID da transação                                    │
│    - Código de autorização                                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. Sistema salva transação                                  │
│    - BaseTransacoesGestao (unificado)                       │
│    - OwnTransaction (se Own)                                │
│    - Marca gateway usado                                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. Exibe resultado ao cliente                              │
│    - Tela de sucesso/erro                                   │
│    - Transparente (não mostra qual gateway)                 │
└─────────────────────────────────────────────────────────────┘
```

---

### Fluxo 2: Link de Recorrência com Own Financial

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Lojista cria link de recorrência                        │
│    - Valor mensal                                           │
│    - Descrição                                              │
│    - Dia de cobrança                                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Sistema gera token (72h)                                │
│    - RecorrenciaToken                                       │
│    - Envia email para cliente                               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Cliente acessa link e preenche cartão                   │
│    - SEM pagamento imediato                                 │
│    - Apenas tokenização                                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Backend chama Own Financial                             │
│    POST /v1/payments                                        │
│    - paymentType=PA (Pre-authorization)                     │
│    - amount=1.00 (simbólico)                                │
│    - createRegistration=true                                │
│    - standingInstruction.mode=INITIAL                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Own retorna registrationId                              │
│    - Token para cobranças futuras                           │
│    - Últimos 4 dígitos do cartão                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. Sistema salva registration                              │
│    - OwnRegistration                                        │
│    - RecorrenciaAgendada.registration_id_own                │
│    - RecorrenciaAgendada.status = 'ativo'                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. (Opcional) Reverter pre-auth de R$ 1,00                │
│    POST /v1/payments/{id}                                   │
│    paymentType=RV (Reversal)                                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 8. Celery Beat agenda cobranças mensais                    │
│    - Task: cobrar_recorrencias_own()                        │
│    - Executa todo dia às 02:00                              │
└─────────────────────────────────────────────────────────────┘
```

---

### Fluxo 3: Cobrança Recorrente Automática

```
┌─────────────────────────────────────────────────────────────┐
│ Celery Beat (02:00 diariamente)                            │
│ Task: cobrar_recorrencias_own()                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 1. Busca recorrências vencidas hoje                        │
│    RecorrenciaAgendada.objects.filter(                      │
│        proxima_cobranca=hoje,                               │
│        status='ativo',                                      │
│        gateway='OWN'                                        │
│    )                                                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Para cada recorrência                                    │
│    - Valida registration_id ativo                           │
│    - Valida valor                                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Chama Own Financial                                      │
│    POST /v1/registrations/{registrationId}/payments         │
│    - paymentType=DB                                         │
│    - amount=valor_recorrencia                               │
│    - standingInstruction.mode=REPEATED                      │
│    - standingInstruction.source=MIT                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
        ┌───────────────────┴───────────────────┐
        │                                       │
┌───────▼────────┐                    ┌────────▼────────┐
│ APROVADO       │                    │ REPROVADO       │
└───────┬────────┘                    └────────┬────────┘
        │                                      │
        ▼                                      ▼
┌─────────────────────┐            ┌─────────────────────┐
│ 4a. Salva transação │            │ 4b. Registra falha  │
│ - BaseTransacoesGestao│          │ - Incrementa tentativas│
│ - Atualiza próxima  │            │ - Notifica lojista  │
│   cobrança (+30 dias)│            │ - Se 3 falhas: pausa│
└─────────────────────┘            └─────────────────────┘
        │                                      │
        ▼                                      ▼
┌─────────────────────┐            ┌─────────────────────┐
│ 5a. Notifica cliente│            │ 5b. Email cliente   │
│ - Email confirmação │            │ - Atualizar cartão  │
│ - Recibo            │            │                     │
└─────────────────────┘            └─────────────────────┘
```

---

### Fluxo 4: Consulta e Carga de Transações

```
┌─────────────────────────────────────────────────────────────┐
│ Celery Beat (02:00 diariamente)                            │
│ Task: carga_transacoes_own()                                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 1. Autenticação OAuth 2.0                                   │
│    POST /agilli/v2/auth                                     │
│    - client_id, client_secret, scope                        │
│    - Recebe access_token (válido 5min)                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Consulta transações do dia anterior                      │
│    POST /agilli/transacoes/v2/buscaTransacoesGerais         │
│    - cnpjCliente                                            │
│    - dataInicial: ontem 00:00                               │
│    - dataFinal: ontem 23:59                                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Processa cada transação                                  │
│    for transacao in response:                               │
│        - Verifica se já existe (identificadorTransacao)     │
│        - Normaliza dados                                    │
│        - Calcula MDR, valores líquidos                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Salva em BaseTransacoesGestao                           │
│    - Formato unificado (Pinbank + Own)                      │
│    - Campo gateway='OWN'                                    │
│    - Processa parcelas                                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Consulta liquidações                                     │
│    GET /agilli/parceiro/v2/consultaLiquidacoes              │
│    - dataPagamentoReal: ontem                               │
│    - Atualiza status de pagamento                           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. Lojista visualiza no portal                             │
│    - Mesma tela (transparente)                              │
│    - Coluna "Gateway" mostra origem                         │
│    - Filtros por gateway                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔐 SEGURANÇA E COMPLIANCE

### PCI-DSS

**Dados de Cartão:**
- ❌ NUNCA armazenar CVV
- ❌ NUNCA armazenar número completo do cartão
- ✅ Armazenar apenas: BIN (6 dígitos) + Last4
- ✅ Usar HTTPS obrigatório
- ✅ Tokenização para recorrência

**Logs:**
- ❌ NUNCA logar dados sensíveis
- ✅ Logar apenas: IDs, timestamps, status
- ✅ Mascarar cartões nos logs

### Autenticação

**OAuth 2.0 (APIs Adquirência):**
- Client credentials grant type
- Token válido por 5 minutos
- Cache de 4 minutos (margem segurança)
- Renovação automática

**Bearer Token (e-SiTef):**
- Access token fixo por loja
- Armazenado em AWS Secrets Manager
- Rotação manual (quando necessário)

### Dados Sensíveis

**AWS Secrets Manager:**
```json
{
  "own/prod/auth": {
    "client_id": "xxxxx",
    "client_secret": "xxxxx",
    "scope": "xxxxx"
  },
  "own/prod/esitef/{loja_id}": {
    "entity_id": "xxxxx",
    "access_token": "xxxxx"
  }
}
```

---

## 📊 MONITORAMENTO E OBSERVABILIDADE

### Métricas Chave

**Transações:**
- Volume por gateway (Pinbank vs Own)
- Taxa de aprovação por gateway
- Tempo médio de resposta
- Taxa de erro/timeout

**Recorrências:**
- Taxa de sucesso cobranças
- Falhas consecutivas
- Cartões expirados

**Consultas:**
- Tempo de carga diária
- Registros processados
- Erros de sincronização

### Logs Estruturados

```python
# Padrão de logs
registrar_log('own.transacao', '💳 Criando pagamento DB: R$ 100.00')
registrar_log('own.transacao', '✅ Pagamento aprovado: 8ac7a4a18d123')
registrar_log('own.transacao', '❌ Pagamento reprovado: 800.100.100')
registrar_log('own.auth', '🔑 Token renovado: client_123')
registrar_log('own.consulta', '🔍 Buscando transações: 2025-11-14')
```

### Alertas

**Críticos:**
- Taxa de erro > 5%
- Timeout > 10%
- Falha autenticação OAuth

**Avisos:**
- Tempo resposta > 5s
- Taxa aprovação < 80%
- Recorrências falhando

---

## 🧪 TESTES

### Testes Unitários

```python
# tests/own/test_transacao_service.py

from django.test import TestCase
from own.services_transacoes import OwnTransacaoService

class OwnTransacaoServiceTest(TestCase):
    
    def setUp(self):
        self.loja = criar_loja_teste()
        self.service = OwnTransacaoService(self.loja)
    
    def test_create_payment_debit_sucesso(self):
        card_data = {
            'number': '4200000000000000',
            'holder': 'TESTE USUARIO',
            'expiry_month': '12',
            'expiry_year': '2025',
            'cvv': '123',
            'brand': 'VISA'
        }
        
        result = self.service.create_payment_debit(card_data, 100.00)
        
        self.assertTrue(result['sucesso'])
        self.assertIn('own_payment_id', result)
    
    def test_refund_payment(self):
        # Criar pagamento
        payment = criar_pagamento_teste()
        
        # Estornar
        result = self.service.refund_payment(payment.own_payment_id, 100.00)
        
        self.assertTrue(result['sucesso'])
```

### Testes de Integração

```python
# tests/own/test_checkout_integration.py

class CheckoutOwnIntegrationTest(TestCase):
    
    def test_fluxo_completo_checkout(self):
        # 1. Criar token checkout
        token = criar_checkout_token_teste()
        
        # 2. Processar pagamento
        response = self.client.post('/checkout/processar/', {
            'token': token.token,
            'numero_cartao': '4200000000000000',
            'cvv': '123',
            # ...
        })
        
        # 3. Verificar resultado
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['sucesso'])
        
        # 4. Verificar salvamento
        transacao = OwnTransaction.objects.filter(
            checkout_token=token
        ).first()
        self.assertIsNotNone(transacao)
```

### Testes E2E (Sandbox)

```bash
# Ambiente de teste Own Financial
export OWN_ENVIRONMENT=TEST
export OWN_ENTITY_ID=test_entity_123
export OWN_ACCESS_TOKEN=test_token_456

# Executar testes
python manage.py test own.tests.e2e
```

---

## 📚 DOCUMENTAÇÃO PARA USUÁRIOS

### Para Lojistas

**Guia: Como Escolher Gateway**

```
1. Novas lojas: Own Financial (padrão)
   - Melhores taxas
   - Mais funcionalidades
   - Processo simplificado

2. Lojas existentes: Podem manter Pinbank
   - Sem necessidade de migração
   - Histórico preservado

3. Trocar de gateway:
   - Solicitar via portal
   - Análise WallClub
   - Processo de credenciamento
   - Período de transição (30 dias)
```

### Para Desenvolvedores

**Guia: Adicionar Novo Gateway**

```python
# 1. Criar service
class NovoGatewayService:
    def processar_pagamento(self, dados):
        # Implementar
        pass

# 2. Adicionar ao roteador
class GatewayRouter:
    GATEWAYS = {
        'PINBANK': PinbankService,
        'OWN': OwnTransacaoService,
        'NOVO': NovoGatewayService  # ← Adicionar aqui
    }
```

---

## ✅ CHECKLIST DE DEPLOY

### Pré-Deploy

- [ ] Credenciais Own em AWS Secrets Manager
- [ ] Configuração de lojas teste
- [ ] Testes em sandbox aprovados
- [ ] Documentação atualizada
- [ ] Rollback plan definido

### Deploy

- [ ] Criar migrations (models Own)
- [ ] Deploy código (containers)
- [ ] Configurar Celery tasks
- [ ] Ativar 3 lojas piloto
- [ ] Monitoramento ativo

### Pós-Deploy

- [ ] Validar transações piloto
- [ ] Validar cargas automáticas
- [ ] Validar recorrências
- [ ] Feedback lojistas
- [ ] Ajustes necessários

---

## 🎯 MÉTRICAS DE SUCESSO

### Técnicas

- Taxa de sucesso transações > 95%
- Tempo médio resposta < 3s
- Zero downtime
- Taxa de erro < 1%

### Negócio

- 50% das novas lojas em Own (3 meses)
- Redução de 20% em custos de gateway
- Satisfação lojistas > 4.5/5

---

**FIM DO DOCUMENTO**

**Próximos Passos:**
1. Validar especificação com stakeholders
2. Obter aprovação técnica
3. Alocar recursos (2 devs full-time)
4. Iniciar Fase 1 (Infraestrutura)

**Contato:**
- Tech Lead: [nome]
- Product Owner: [nome]
- Suporte Own Financial: [contato]
