# PLANO DE REPLICAÇÃO - ESTRUTURA PINBANK → OWN FINANCIAL

**Versão:** 1.0  
**Data:** 15/11/2025  
**Objetivo:** Replicar toda estrutura do módulo Pinbank para Own Financial  
**Status:** Planejamento

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

### Own (Nova)
```
adquirente_own/
├── models.py                           # (vazio ou específico Own)
├── services.py                         # OwnService (OAuth 2.0)
├── services_transacoes_pagamento.py   # TransacoesOwnService (e-SiTef)
└── cargas_own/
    ├── models.py                       # OwnExtratoTransacoes, Liquidacoes, Credenciais
    ├── services_carga_transacoes.py    # Consulta transações API Own
    ├── services_carga_liquidacoes.py   # Consulta liquidações API Own
    └── tasks.py
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

### FASE 1: Estrutura Base (3 dias)
- [ ] Criar módulo `adquirente_own/`
- [ ] Criar submódulo `cargas_own/`
- [ ] Criar models (3 tabelas novas)
- [ ] Modificar BaseTransacoesGestao
- [ ] Executar migrations
- [ ] Registrar apps no settings

### FASE 2: Services Base (5 dias)
- [ ] `OwnService` (autenticação OAuth 2.0)
- [ ] Métodos de requisição autenticada
- [ ] Cache de tokens
- [ ] Testes de conectividade

### FASE 3: Transações E-commerce (7 dias)
- [ ] `TransacoesOwnService` (e-SiTef API)
- [ ] Pagamento débito (DB)
- [ ] Tokenização (PA + Registration)
- [ ] Estorno (RF)
- [ ] Integração com checkout

### FASE 4: Cargas Automáticas (7 dias)
- [ ] `CargaTransacoesOwnService`
- [ ] `CargaLiquidacoesOwnService`
- [ ] Celery tasks
- [ ] Management commands
- [ ] Popular BaseTransacoesGestao

### FASE 5: Roteador de Gateways (3 dias)
- [ ] `GatewayRouter` no checkout
- [ ] Campo `gateway_ativo` em Loja
- [ ] Adaptar services de checkout
- [ ] Testes de roteamento

### FASE 6: Testes e Homologação (5 dias)
- [ ] Testes unitários
- [ ] Testes de integração
- [ ] Testes em sandbox Own
- [ ] Lojas piloto
- [ ] Documentação

**TOTAL: ~30 dias (6 semanas)**

---

## 🔑 DIFERENÇAS PRINCIPAIS: PINBANK vs OWN

### Autenticação
| Aspecto | Pinbank | Own |
|---------|---------|-----|
| Método | Username/Password | OAuth 2.0 (client credentials) |
| Token | Bearer fixo | Access token (5min) |
| Cache | Não | Sim (4min) |

### Transações E-commerce
| Aspecto | Pinbank | Own (e-SiTef) |
|---------|---------|---------------|
| API | Proprietária | OPPWA (Carat) |
| Criptografia | AES custom | HTTPS nativo |
| Payload | JSON | x-www-form-urlencoded |
| Endpoint | `/Transacoes/EfetuarTransacao` | `/v1/payments` |

### Consultas
| Aspecto | Pinbank | Own |
|---------|---------|-----|
| Transações | Via extrato POS | API `/transacoes/v2/buscaTransacoesGerais` |
| Liquidações | Não tem endpoint específico | API `/parceiro/v2/consultaLiquidacoes` |
| Antecipação | Não disponível | Dados detalhados |

---

## 📝 PRÓXIMOS PASSOS

1. **Validar este plano** com o time técnico
2. **Criar branch** `feature/adquirente-own`
3. **Iniciar FASE 1** (estrutura base)
4. **Documentar decisões** técnicas durante implementação
5. **Manter Pinbank intacto** (zero risco para produção)

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
