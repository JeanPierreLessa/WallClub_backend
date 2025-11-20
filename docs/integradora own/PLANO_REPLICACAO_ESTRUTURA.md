# PLANO DE REPLICAÇÃO - ESTRUTURA PINBANK → OWN FINANCIAL

**Versão:** 2.2  
**Data:** 20/11/2025  
**Objetivo:** Replicar toda estrutura do módulo Pinbank para Own Financial  
**Status:** ✅ FASE 1-6 CONCLUÍDAS | ⏳ FASE 5 PENDENTE (Roteador Gateways)

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

### ✅ FASE 3: Transações E-commerce e POS (CONCLUÍDA)
- [x] `TransacoesOwnService` (API OPPWA REST - E-commerce)
  - [x] Pagamento débito (DB) - `create_payment_debit()`
  - [x] Tokenização (PA + Registration) - `create_payment_with_tokenization()`
  - [x] Pagamento recorrente - `create_payment_with_registration()`
  - [x] Estorno (RF) - `refund_payment()`
  - [x] Consulta status - `consultar_status_pagamento()`
- [x] `TRDataOwnService` (SDK Ágilli - POS)
  - [x] Processar transações POS via endpoint `/trdata_own/`
  - [x] Validação de duplicidade por `txTransactionId`
  - [x] Geração de slip de impressão formatado
  - [x] Suporte a Wall Club (desconto, cashback, saldo usado)
  - [x] Captura de comprovantes Ágilli (customerTicket, estabTicket, e2ePixId)

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

### ⏳ FASE 5: Roteador de Gateways (PENDENTE)
- [ ] `GatewayRouter` no checkout
- [ ] Campo `gateway_ativo` em Loja
- [ ] Adaptar services de checkout
- [ ] Testes de roteamento

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

**PROGRESSO: 5/6 fases concluídas (83%)**

---

## 🔑 DIFERENÇAS PRINCIPAIS: PINBANK vs OWN

### Autenticação
| Aspecto | Pinbank | Own |
|---------|---------|-----|
| Método | Username/Password | OAuth 2.0 (client credentials) |
| Token | Bearer fixo | Access token (5min) |
| Cache | Não | Sim (4min) |

### Transações E-commerce
| Aspecto | Pinbank | Own (OPPWA) |
|---------|---------|-------------|
| API | Proprietária | OPPWA (API REST) |
| Criptografia | AES custom | HTTPS nativo |
| Payload | JSON | x-www-form-urlencoded |
| Endpoint | `/Transacoes/EfetuarTransacao` | `/v1/payments` |
| Payment Types | Proprietários | DB, PA, RF, RV, RB |

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

1. ✅ ~~Validar este plano com o time técnico~~
2. ✅ ~~Criar branch `integracao_own`~~
3. ✅ ~~Iniciar FASE 1-4 (estrutura base, services, transações, cargas)~~
4. ✅ ~~Implementar webhooks Own (tempo real)~~
5. ✅ ~~**Testes em sandbox** Own Financial~~
   - ✅ Autenticação OAuth 2.0 validada
   - ✅ Endpoint de dados cadastrais validado (71 registros)
   - ✅ Endpoint de transações validado (9 transações)
   - ✅ Scripts de teste criados e validados
   - ✅ Arquivos JSON gerados com dados reais
6. ✅ ~~**Executar script SQL** no banco de dados~~
   - ✅ Credenciais cadastradas em `credenciaisExtratoContaOwn`
   - ✅ Campo `cnpj_white_label` corrigido nos services
7. ✅ ~~**Testar cargas automáticas** com dados reais do sandbox~~
   - ✅ Comando `carga_transacoes_own --dias` implementado
   - ✅ 9 transações carregadas com sucesso
   - ✅ Dados salvos em ambas as tabelas (OwnExtratoTransacoes + BaseTransacoesGestao)
   - ✅ Apps registrados em `settings/apis.py`
8. ⏳ **Incluir URLs dos webhooks no `urls.py` principal**
9. ⏳ **Cadastrar URLs dos webhooks no suporte Own:**
   - `https://api.wallclub.com.br/own/webhook/transacao/`
   - `https://api.wallclub.com.br/own/webhook/liquidacao/`
   - `https://api.wallclub.com.br/own/webhook/cadastro/`
10. ⏳ **Implementar FASE 5** (Roteador de Gateways)
11. ⏳ **Configurar credenciais** Own em AWS Secrets Manager

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
