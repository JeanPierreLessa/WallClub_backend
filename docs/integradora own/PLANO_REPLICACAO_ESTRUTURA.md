# PLANO DE REPLICAÇÃO - ESTRUTURA PINBANK → OWN FINANCIAL

**Versão:** 2.0  
**Data:** 15/11/2025  
**Objetivo:** Replicar toda estrutura do módulo Pinbank para Own Financial  
**Status:** ✅ FASE 1-4 CONCLUÍDAS

---

## 📋 RESUMO EXECUTIVO

### Objetivo
Criar módulo `adquirente_own/` replicando a estrutura completa do `pinbank/`, adaptando para as APIs e especificidades da Own Financial.

### Pontos-Chave
1. ✅ Modificar `BaseTransacoesGestao` para incluir campo `adquirente` (PINBANK/OWN)
2. ✅ Criar novas tabelas: `ownExtratoTransacoes`, `ownLiquidacoes`, `credenciaisExtratoContaOwn`
3. ✅ Replicar services de transações e-commerce
4. ✅ Replicar services de cargas automáticas
5. ✅ Criar roteador de gateways no checkout
6. ✅ Manter convivência pacífica entre Pinbank e Own

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
└── cargas_own/
    ├── models.py                       # OwnExtratoTransacoes, Liquidacoes, Credenciais
    ├── services.py                     # Utilitários
    ├── services_carga_transacoes.py    # Consulta transações API Own
    ├── services_carga_liquidacoes.py   # Consulta liquidações API Own
    ├── tasks.py                        # 4 Celery tasks
    ├── executar_cargas_completas.py    # Orquestrador
    └── management/
        └── commands/
            ├── carga_transacoes_own.py
            ├── carga_liquidacoes_own.py
            └── carga_base_gestao_own.py
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

Credenciais de acesso às APIs Own.

**Campos principais:**
- `client_id`, `client_secret`, `scope` (OAuth 2.0)
- `entity_id`, `access_token` (e-SiTef)
- `environment` (TEST/LIVE)
- `cliente_id` (FK para Loja)

---

## 📦 FASES DE IMPLEMENTAÇÃO

### ✅ FASE 1: Estrutura Base (CONCLUÍDA)
- [x] Criar módulo `adquirente_own/`
- [x] Criar submódulo `cargas_own/`
- [x] Criar models (3 tabelas novas)
- [x] Modificar BaseTransacoesGestao (campo `adquirente`)
- [x] Script SQL criado (`001_criar_tabelas_own.sql`)
- [x] Registrar apps no settings

### ✅ FASE 2: Services Base (CONCLUÍDA)
- [x] `OwnService` (autenticação OAuth 2.0)
- [x] Métodos de requisição autenticada
- [x] Cache de tokens (4 minutos)
- [x] Obtenção de credenciais por loja

### ✅ FASE 3: Transações E-commerce (CONCLUÍDA)
- [x] `TransacoesOwnService` (API OPPWA REST)
- [x] Pagamento débito (DB) - `create_payment_debit()`
- [x] Tokenização (PA + Registration) - `create_payment_with_tokenization()`
- [x] Pagamento recorrente - `create_payment_with_registration()`
- [x] Estorno (RF) - `refund_payment()`
- [x] Consulta status - `consultar_status_pagamento()`

### ✅ FASE 4: Cargas Automáticas (CONCLUÍDA)
- [x] `CargaTransacoesOwnService`
- [x] `CargaLiquidacoesOwnService`
- [x] `OwnCargasUtilService` (utilitários)
- [x] Celery tasks (4 tasks)
  - [x] `carga_transacoes_own_diaria`
  - [x] `carga_liquidacoes_own_diaria`
  - [x] `carga_transacoes_own_periodo`
  - [x] `sincronizar_status_pagamentos_own`
- [x] Management commands (3 commands)
  - [x] `carga_transacoes_own.py`
  - [x] `carga_liquidacoes_own.py`
  - [x] `carga_base_gestao_own.py`
- [x] Orquestrador `executar_cargas_completas.py`
- [x] Popular BaseTransacoesGestao

### ⏳ FASE 5: Roteador de Gateways (PENDENTE)
- [ ] `GatewayRouter` no checkout
- [ ] Campo `gateway_ativo` em Loja
- [ ] Adaptar services de checkout
- [ ] Testes de roteamento

### ⏳ FASE 6: Testes e Homologação (PENDENTE)
- [ ] Executar script SQL no banco
- [ ] Testes unitários
- [ ] Testes de integração
- [ ] Testes em sandbox Own
- [ ] Lojas piloto
- [ ] Documentação de uso

**PROGRESSO: 4/6 fases concluídas (67%)**

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

---

## 📝 PRÓXIMOS PASSOS

1. ✅ ~~Validar este plano com o time técnico~~
2. ✅ ~~Criar branch `integracao_own`~~
3. ✅ ~~Iniciar FASE 1-4 (estrutura base, services, transações, cargas)~~
4. ⏳ **Executar script SQL** no banco de dados
5. ⏳ **Implementar FASE 5** (Roteador de Gateways)
6. ⏳ **Implementar FASE 6** (Testes e Homologação)
7. ⏳ **Configurar credenciais** Own em AWS Secrets Manager
8. ⏳ **Testes em sandbox** Own Financial

---

## ⚠️ PONTOS DE ATENÇÃO

1. **Não quebrar Pinbank**: Toda modificação em código compartilhado deve ser retrocompatível
2. **Campo adquirente**: Garantir que todas queries existentes continuem funcionando
3. **Credenciais**: Usar AWS Secrets Manager (não hardcode)
4. **Logs**: Prefixo `own.*` para facilitar debug
5. **Testes**: Ambiente sandbox Own antes de produção

---

**Documento criado por:** Tech Lead  
**Próxima revisão:** Após validação do time
