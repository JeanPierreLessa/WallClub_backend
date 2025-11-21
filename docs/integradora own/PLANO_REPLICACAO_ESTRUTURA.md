# PLANO DE REPLICAÇÃO - ESTRUTURA PINBANK → OWN FINANCIAL

**Versão:** 2.3  
**Data:** 21/11/2025  
**Objetivo:** Replicar toda estrutura do módulo Pinbank para Own Financial  
**Status:** ✅ FASE 1-5 CONCLUÍDAS | ⚠️ FASE 3 E-COMMERCE PENDENTE (Credenciais OPPWA)

---

## 📋 RESUMO EXECUTIVO

### Objetivo
Criar módulo `adquirente_own/` replicando a estrutura completa do `pinbank/`, adaptando para as APIs e especificidades da Own Financial.

### Pontos-Chave
1. ✅ Modificar `BaseTransacoesGestao` para incluir campo `adquirente` (PINBANK/OWN)
2. ✅ Criar novas tabelas: `ownExtratoTransacoes`, `ownLiquidacoes`, `credenciaisExtratoContaOwn`
3. ✅ Replicar services de transações e-commerce
4. ✅ Replicar services de cargas automáticas
5. ✅ **Implementar webhooks Own** (tempo real + double-check diário)
6. ✅ Criar roteador de gateways no checkout
7. ✅ Manter convivência pacífica entre Pinbank e Own

---

## 🏗️ ESTRUTURA ATUAL vs NOVA

### Pinbank (Atual)
```
pinbank/
├── models.py                           # BaseTransacoesGestao
├── services.py                         # PinbankService
├── services_transacoes_pagamento.py   # TransacoesPinbankService
└── cargas_pinbank/
    ├── models.py                       # PinbankExtratoPOS, Credenciais
    ├── services_carga_checkout.py
    ├── services_carga_credenciadora.py
    ├── services_carga_extrato_pos.py
    └── tasks.py
```

### Own (Implementada) ✅
```
adquirente_own/
├── models.py                           # (vazio - models em cargas_own)
├── services.py                         # OwnService (OAuth 2.0)
├── services_transacoes_pagamento.py   # TransacoesOwnService (API OPPWA)
├── views_webhook.py                    # Webhooks Own (tempo real)
├── urls_webhook.py                     # URLs dos webhooks
└── cargas_own/
    ├── models.py                       # OwnExtratoTransacoes, Liquidacoes, Credenciais
    ├── services.py                     # Utilitários
    ├── services_carga_transacoes.py    # Consulta transações API Own
    ├── services_carga_liquidacoes.py   # Consulta liquidações API Own
    ├── tasks.py                        # 4 Celery tasks (double-check)
    ├── executar_cargas_completas.py    # Orquestrador
    └── management/
        └── commands/
            ├── carga_transacoes_own.py
            ├── carga_liquidacoes_own.py
            └── carga_base_gestao_own.py

posp2/
├── models.py                           # TransactionData (Pinbank), TransactionDataOwn (Own)
├── services_transacao.py               # TRDataService (Pinbank)
├── services_transacao_own.py           # TRDataOwnService (Own) ✅ NOVO
├── views.py                            # Endpoints /trdata/ e /trdata_own/
└── urls.py                             # Rotas POS
```

---

## 🗄️ MODIFICAÇÕES BASE DE DADOS

### 1. BaseTransacoesGestao (MODIFICAR EXISTENTE)

```sql
ALTER TABLE baseTransacoesGestao 
ADD COLUMN adquirente VARCHAR(20) DEFAULT 'PINBANK' AFTER tipo_operacao;

CREATE INDEX idx_adquirente ON baseTransacoesGestao(adquirente);
```

**Model Django (pinbank/models.py):**
```python
class BaseTransacoesGestao(models.Model):
    # ... campos existentes ...
    adquirente = models.CharField(
        max_length=20,
        choices=[('PINBANK', 'Pinbank'), ('OWN', 'Own Financial')],
        default='PINBANK',
        db_index=True
    )
```

### 2. ownExtratoTransacoes (CRIAR NOVA)

Armazena transações consultadas da API Own.

**Campos principais:**
- `identificadorTransacao` (UNIQUE)
- `cnpjCpfCliente`, `cnpjCpfParceiro`
- `valor`, `quantidadeParcelas`, `mdr`
- `statusTransacao`, `bandeira`, `modalidade`
- `parcelaId`, `numeroParcela`, `valorParcela`
- `dataPagamentoReal`, `antecipado`

### 3. ownLiquidacoes (CRIAR NOVA)

Armazena liquidações consultadas da API Own.

**Campos principais:**
- `lancamentoId` (UNIQUE)
- `identificadorTransacao`
- `dataPagamentoReal`, `valor`
- `statusPagamento`, `antecipada`

### 4. credenciaisExtratoContaOwn (CRIAR NOVA)

Credenciais OAuth 2.0 do cliente White Label (WallClub).

**Campos principais:**
- `cnpj_white_label` (UNIQUE) - CNPJ do cliente White Label
- `client_id`, `client_secret`, `scope` (OAuth 2.0)
- `entity_id`, `access_token` (e-SiTef)
- `environment` (TEST/LIVE)

**Observação:** As credenciais são únicas por cliente White Label (WallClub). As lojas individuais são identificadas via `docParceiro` nas consultas às APIs.

### 5. transactiondata_own (CRIAR NOVA) ✅

Tabela específica para transações POS via SDK Ágilli (Own Financial).

**Campos principais:**
- `id` (PRIMARY KEY)
- `txTransactionId` (UNIQUE) - ID único da transação Own
- `datahora`, `valor_original`, `celular`, `cpf`, `terminal`
- `nsuTerminal`, `nsuHost`, `authorizationCode`, `transactionReturn`
- `amount`, `originalAmount`, `totalInstallments`
- `operationId`, `paymentMethod`, `brand`, `cardNumber`, `cardName`
- `customerTicket`, `estabTicket`, `e2ePixId` (comprovantes Ágilli)
- `terminalTimestamp`, `hostTimestamp`, `status`, `capturedTransaction`
- `cnpj`, `sdk` (sempre "agilli")
- `valor_desconto`, `valor_cashback`, `cashback_concedido`, `autorizacao_id`, `saldo_usado`, `modalidade_wall`

**Endpoint:** `POST /posp2/trdata_own/`

---

## 📦 FASES DE IMPLEMENTAÇÃO

### ✅ FASE 1: Estrutura Base (CONCLUÍDA)
- [x] Criar módulo `adquirente_own/`
- [x] Criar submódulo `cargas_own/`
- [x] Criar models (5 tabelas novas: ownExtratoTransacoes, ownLiquidacoes, credenciaisExtratoContaOwn, transactiondata_own, TransactionDataOwn)
- [x] Modificar BaseTransacoesGestao (campo `adquirente`)
- [x] Script SQL criado (`001_criar_tabelas_own.sql`, `criar_transactiondata_own.sql`)
- [x] Registrar apps no settings
- [x] Criar endpoint `/posp2/trdata_own/` para transações POS Own

### ✅ FASE 2: Services Base (CONCLUÍDA)
- [x] `OwnService` (autenticação OAuth 2.0)
- [x] Métodos de requisição autenticada
- [x] Cache de tokens (4 minutos)
- [x] Obtenção de credenciais por loja

### ⚠️ FASE 3: Transações E-commerce e POS (EM ANDAMENTO)

#### ✅ E-commerce - API OPPWA (Registration Tokens)
- [x] `TransacoesOwnService` - Métodos básicos implementados:
  - [x] `create_payment_debit()` - Pagamento débito/crédito (DB)
  - [x] `create_payment_with_tokenization()` - Tokenização inicial (PA + createRegistration)
  - [x] `create_payment_with_registration()` - Pagamento com token existente
  - [x] `refund_payment()` - Estorno (RF)
  - [x] `consultar_status_pagamento()` - Consulta status

- [ ] **Métodos de gerenciamento de tokens (PENDENTE):**
  - [ ] `delete_registration()` - Excluir token (Deregistration)
  - [ ] `get_registration_details()` - Consultar dados do token
  - [ ] `list_registrations()` - Listar tokens do cliente
  - [ ] `update_registration()` - Atualizar token (se disponível)

- [ ] **Métodos adapter para compatibilidade Pinbank (PENDENTE):**
  - [ ] `efetuar_transacao_cartao()` - Adapter para `create_payment_debit()`
  - [ ] `incluir_cartao_tokenizado()` - Adapter para `create_payment_with_tokenization()`
  - [ ] `excluir_cartao_tokenizado()` - Adapter para `delete_registration()`
  - [ ] `consulta_dados_cartao_tokenizado()` - Adapter para `get_registration_details()`
  - [ ] `consultar_cartoes()` - Adapter para `list_registrations()`
  - [ ] `cancelar_transacao()` - Adapter para `refund_payment()`

**Documentação:** https://own-financial.docs.oppwa.com/tutorials/tokenization

#### ✅ POS - SDK Ágilli (CONCLUÍDO)
- [x] `TRDataOwnService` - Processamento POS completo:
  - [x] Endpoint `/trdata_own/` funcionando
  - [x] Validação de duplicidade por `txTransactionId`
  - [x] Geração de slip de impressão formatado (próprio, independente da Pinbank)
  - [x] Suporte a Wall Club (desconto, cashback, saldo usado)
  - [x] Captura de comprovantes Ágilli (customerTicket, estabTicket, e2ePixId)
  - [x] Busca de loja por terminal ou CNPJ
  - [x] Busca de nome do cliente por CPF
  - [x] Cálculo de valores próprio (não depende da CalculadoraBaseGestao)

### ✅ FASE 4: Cargas Automáticas (CONCLUÍDA)
- [x] `CargaTransacoesOwnService`
- [x] `CargaLiquidacoesOwnService`
- [x] `OwnCargasUtilService` (utilitários)
- [x] Celery tasks (4 tasks) - **Ajustadas para double-check**
  - [x] `carga_transacoes_own_diaria` (double-check às 02:00)
  - [x] `carga_liquidacoes_own_diaria` (double-check às 02:30)
  - [x] `carga_transacoes_own_periodo`
  - [x] `sincronizar_status_pagamentos_own`
- [x] Management commands (3 commands)
  - [x] `carga_transacoes_own.py`
  - [x] `carga_liquidacoes_own.py`
  - [x] `carga_base_gestao_own.py`
- [x] Orquestrador `executar_cargas_completas.py`
- [x] Popular BaseTransacoesGestao

### ✅ FASE 4.5: Webhooks Tempo Real (CONCLUÍDA)
- [x] `views_webhook.py` - 3 endpoints webhook
  - [x] `/webhook/transacao/` - Recebe vendas em tempo real
  - [x] `/webhook/liquidacao/` - Recebe liquidações em tempo real
  - [x] `/webhook/cadastro/` - Recebe status de credenciamento
- [x] `urls_webhook.py` - Roteamento dos webhooks
- [x] Validação de payloads e detecção de duplicatas
- [x] Parse de datas nos formatos Own
- [x] Logs detalhados e transações atômicas
- [x] Tasks Celery ajustadas para double-check diário

### ✅ FASE 5: Roteador de Gateways e Integração Checkout (CONCLUÍDA)

#### ✅ Infraestrutura Base
- [x] Campo `gateway_ativo` adicionado na tabela `loja` (VARCHAR(20), valores: 'PINBANK' ou 'OWN')
- [x] `GatewayRouter` criado (`checkout/services_gateway_router.py`)
  - [x] `obter_gateway_loja()` - Consulta gateway ativo da loja
  - [x] `obter_service_transacao()` - Retorna service correto (Pinbank ou Own)
  - [x] `processar_pagamento_debito()` - Processa pagamento unificado
  - [x] `processar_estorno()` - Processa estorno unificado

#### ✅ TransacoesOwnService - E-commerce Completo
- [x] **Métodos de Pagamento**
  - [x] `create_payment_debit()` - Pagamento débito/crédito
  - [x] `create_payment_with_tokenization()` - PA + tokenização
  - [x] `create_payment_with_registration()` - Pagamento com token
  - [x] `refund_payment()` - Estorno
- [x] **Gerenciamento de Tokens**
  - [x] `delete_registration()` - Excluir token
  - [x] `get_registration_details()` - Consultar token
  - [x] `list_registrations()` - Listar tokens
- [x] **Métodos Adapter (Compatibilidade Pinbank)**
  - [x] `efetuar_transacao_cartao()` → `create_payment_debit()`
  - [x] `incluir_cartao_tokenizado()` → `create_payment_with_tokenization()`
  - [x] `excluir_cartao_tokenizado()` → `delete_registration()`
  - [x] `consulta_dados_cartao_tokenizado()` → `get_registration_details()`
  - [x] `consultar_cartoes()` → `list_registrations()`
  - [x] `cancelar_transacao()` → `refund_payment()`

#### ✅ Adaptação dos Checkouts
- [x] **Link Pagamento Web** (`checkout/link_pagamento_web/services.py`)
  - [x] Substituir `TransacoesPinbankService` por `GatewayRouter`
  - [x] Adaptar `processar_checkout_link_pagamento()` para usar roteador
  - [x] Logs identificam gateway ativo (Pinbank/Own)
  - [x] Tokenização unificada

- [x] **Link Recorrência Web** (`checkout/link_recorrencia_web/services.py`)
  - [x] Substituir `TransacoesPinbankService` por `GatewayRouter`
  - [x] Adaptar `processar_cadastro_cartao()` para usar roteador
  - [x] Fluxo de pré-autorização R$ 1,00 compatível com Own
  - [x] Estorno unificado

#### ⚠️ Testes (BLOQUEADO - Aguardando Credenciais OPPWA)
- [x] Script de teste criado (`teste_own_ecommerce.py`)
- [ ] Aguardando credenciais OPPWA da Own:
  - [ ] `entity_id` - ID da entidade OPPWA
  - [ ] `access_token` - Bearer token fixo da API OPPWA
- [ ] Testes de integração com ambos gateways
- [ ] Validação em sandbox

### ✅ FASE 6: Testes e Homologação (CONCLUÍDA)
- [x] Executar script SQL no banco
- [ ] Testes unitários
- [ ] Testes de integração
- [x] **Testes em sandbox Own** ✅
  - [x] Autenticação OAuth 2.0 funcionando
  - [x] Consulta dados cadastrais - 71 registros retornados (endpoint `/indicadores/v2/cadastrais`)
  - [x] Consulta transações - 9 transações retornadas (endpoint `/transacoes/v2/buscaTransacoesGerais`)
  - [x] Script `teste_own_cadastrais.py` criado e validado
  - [x] Script `teste_own_transacoes.py` criado e validado
  - [x] Arquivos JSON gerados com dados reais
- [x] **Teste de cargas automáticas** ✅
  - [x] Comando `carga_transacoes_own` funcionando
  - [x] 9 transações carregadas com sucesso
  - [x] Dados salvos em `OwnExtratoTransacoes` (8 registros)
  - [x] Dados processados para `BaseTransacoesGestao` (8 registros com adquirente='OWN')
  - [x] Credenciais cadastradas em `credenciaisExtratoContaOwn`
- [ ] Lojas piloto
- [ ] Documentação de uso

**PROGRESSO: 5.5/6 fases concluídas (92%)**
- FASE 1: ✅ 100%
- FASE 2: ✅ 100%
- FASE 3: ⚠️ 95% (E-commerce: 90% - aguardando credenciais OPPWA | POS: 100%)
- FASE 4: ✅ 100%
- FASE 4.5: ✅ 100%
- FASE 5: ✅ 100% (roteador + checkout integrados)
- FASE 6: ⚠️ 50% (testes sandbox OK, aguardando credenciais OPPWA para testes e-commerce)

---

## 🔑 DIFERENÇAS PRINCIPAIS: PINBANK vs OWN

### Autenticação

#### APIs de Adquirência (Consultas/Extrato)
| Aspecto | Pinbank | Own |
|---------|---------|-----|
| Método | Username/Password | OAuth 2.0 (client credentials) |
| Token | Bearer fixo | Access token (5min) |
| Cache | Não | Sim (4min) |
| Endpoint Auth | N/A | `POST /agilli/v2/auth` |

#### APIs E-commerce (Pagamentos)
| Aspecto | Pinbank | Own (OPPWA) |
|---------|---------|-------------|
| Método | Username/Password | Bearer token fixo |
| Token | Fixo | Fixo (fornecido pela Own) |
| Cache | Não | Não (token não expira) |
| Credenciais | Username/Password | `entity_id` + `access_token` |

### Transações E-commerce
| Aspecto | Pinbank | Own (OPPWA) |
|---------|---------|-------------|
| API | Proprietária | OPPWA (API REST) |
| Autenticação | Username/Password | Bearer token fixo |
| Base URL | Pinbank proprietária | `https://eu-test.oppwa.com` (teste)<br>`https://eu-prod.oppwa.com` (prod) |
| Criptografia | AES custom | HTTPS nativo |
| Payload | JSON | x-www-form-urlencoded |
| Endpoint Pagamento | `/Transacoes/EfetuarTransacao` | `/v1/payments` |
| Endpoint Tokenização | Integrado | `/v1/payments` (createRegistration=true) |
| Endpoint Tokens | N/A | `/v1/registrations` |
| Payment Types | Proprietários | DB (débito), PA (pré-auth), RF (refund), RV (reversal), RB (rebill) |
| Credenciais | Username/Password | `entity_id` + `access_token` (Bearer fixo) |

### Consultas
| Aspecto | Pinbank | Own |
|---------|---------|-----|
| Transações | Via extrato POS | API `/transacoes/v2/buscaTransacoesGerais` |
| Liquidações | Não tem endpoint específico | API `/parceiro/v2/consultaLiquidacoes` |
| Antecipação | Não disponível | Dados detalhados |
| Webhooks | Não disponível | ✅ Tempo real (transações, liquidações, cadastro) |
| Frequência | Polling 30min | Webhook (tempo real) + Double-check diário |

---

## 📝 PRÓXIMOS PASSOS

### ✅ Concluído
1. ✅ Validar este plano com o time técnico
2. ✅ Criar branch `integracao_own`
3. ✅ Iniciar FASE 1-4 (estrutura base, services, transações, cargas)
4. ✅ Implementar webhooks Own (tempo real)
5. ✅ Testes em sandbox Own Financial
6. ✅ Executar script SQL no banco de dados
7. ✅ Testar cargas automáticas com dados reais do sandbox
8. ✅ Adicionar campo `gateway_ativo` na tabela `loja`
9. ✅ Criar `GatewayRouter` básico

### ⏳ Pendente (Aguardando Credenciais OPPWA)
10. **Solicitar credenciais OPPWA à Own Financial:**
    - [ ] `entity_id` - ID da entidade OPPWA
    - [ ] `access_token` - Bearer token fixo da API OPPWA
    - [ ] Cartões de teste para ambiente sandbox
    - [ ] Documentação específica da Own (se houver diferenças da OPPWA padrão)

### Pendente (FASE 5)
11. **Integrar GatewayRouter com Checkout:**
    - [ ] Adaptar `link_pagamento_web/services.py`
    - [ ] Adaptar `link_recorrencia_web/services.py`
    - [ ] Testar fluxos completos com Own

12. **Infraestrutura:**
    - [ ] Incluir URLs dos webhooks no `urls.py` principal
    - [ ] Cadastrar URLs dos webhooks no suporte Own
    - [ ] Configurar credenciais Own em AWS Secrets Manager

13. **Testes:**
    - [ ] Testes unitários (TransacoesOwnService, GatewayRouter)
    - [ ] Testes de integração (checkout completo)
    - [ ] Lojas piloto em produção

---

## ⚠️ PONTOS DE ATENÇÃO

1. **Não quebrar Pinbank**: Toda modificação em código compartilhado deve ser retrocompatível
2. **Campo adquirente**: Garantir que todas queries existentes continuem funcionando
3. **Credenciais White Label**: As credenciais OAuth são únicas por cliente White Label (WallClub), não por loja
4. **Campo cnpj_white_label**: Usar `cnpj_white_label` (não `cnpj`) ao buscar credenciais
5. **Environment correto**: Inicializar `OwnService(environment=credencial.environment)` para usar URL correta (TEST/LIVE)
6. **Credenciais**: Usar AWS Secrets Manager (não hardcode)
7. **Logs**: Prefixo `own.*` para facilitar debug
8. **Testes**: Ambiente sandbox Own antes de produção
9. **Webhooks**: URLs devem ser públicas e retornar status 200/204
10. **Double-check**: Tasks Celery diárias alertam se encontrarem transações perdidas
11. **Apps no settings**: Registrar `adquirente_own` e `adquirente_own.cargas_own` em todos os settings necessários
12. **Rebuild Docker**: Após mudanças no código, fazer rebuild da imagem Docker

---

**Documento criado por:** Tech Lead  
**Próxima revisão:** Após validação do time
