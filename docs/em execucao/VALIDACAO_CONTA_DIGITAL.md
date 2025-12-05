# VALIDAÇÃO E AUDITORIA - MÓDULO CONTA DIGITAL

**Data:** 05/12/2025  
**Objetivo:** Validar integridade do módulo conta_digital e mapear todos os lançamentos  
**Status:** 🔄 Em execução

---

## 📋 ÍNDICE

1. [Mapeamento de Lançamentos](#mapeamento-de-lançamentos)
2. [Fluxos de Crédito](#fluxos-de-crédito)
3. [Fluxos de Débito](#fluxos-de-débito)
4. [Checklist de Validação](#checklist-de-validação)
5. [Gaps Identificados](#gaps-identificados)
6. [Plano de Ação](#plano-de-ação)

---

## 🔍 MAPEAMENTO DE LANÇAMENTOS

### Visão Geral

O módulo `conta_digital` recebe lançamentos de **3 origens principais**:

```
┌─────────────────────────────────────────────────────────┐
│                    CONTA DIGITAL                        │
│                                                         │
│  ┌─────────────────────────────────────────────────┐  │
│  │  ContaDigital                                   │  │
│  │  - saldo_atual                                  │  │
│  │  - saldo_bloqueado                              │  │
│  │  - cashback_disponivel                          │  │
│  │  - cashback_bloqueado                           │  │
│  └─────────────────────────────────────────────────┘  │
│                        ▲                                │
│                        │                                │
│           ┌────────────┼────────────┐                  │
│           │            │            │                  │
│      ┌────▼───┐   ┌───▼────┐  ┌───▼────┐             │
│      │CASHBACK│   │  POS   │  │ MOBILE │             │
│      │SERVICE │   │SERVICE │  │  APP   │             │
│      └────────┘   └────────┘  └────────┘             │
└─────────────────────────────────────────────────────────┘
```

---

## 💰 FLUXOS DE CRÉDITO

### 1. Cashback Wall (apps/cashback/services.py)

**Origem:** Sistema de cashback centralizado  
**Método:** `CashbackService.aplicar_cashback_wall()`  
**Arquivo:** `apps/cashback/services.py` (linhas 12-98)

**Fluxo:**
```python
CashbackService.aplicar_cashback_wall()
    ↓
ContaDigitalService.creditar(
    tipo_codigo='CASHBACK_WALL',
    referencia_externa=f'WALL:{parametro_wall_id}',
    sistema_origem='CASHBACK'
)
    ↓
MovimentacaoContaDigital criada
    ↓
CashbackUso registrado (histórico)
```

**Características:**
- ✅ Status inicial: `RETIDO` (se periodo_retencao_dias > 0) ou `LIBERADO`
- ✅ Retenção padrão: 30 dias (configurável via settings)
- ✅ Expiração: 90 dias após liberação (configurável)
- ✅ Afeta: `cashback_bloqueado` (se retido) ou `cashback_disponivel`
- ✅ Transação atômica

**Parâmetros:**
```python
parametro_wall_id: int           # ID do ParametrosWall (wall='C')
cliente_id: int
loja_id: int
canal_id: int
transacao_tipo: str              # 'POS' ou 'CHECKOUT'
transacao_id: int
valor_transacao: Decimal
valor_cashback: Decimal
periodo_retencao_dias: int       # Padrão: 30
periodo_expiracao_dias: int      # Padrão: 90
```

**Retorno:**
```python
{
    'cashback_uso_id': int,
    'movimentacao_id': int,
    'status': 'RETIDO' | 'LIBERADO',
    'data_liberacao': str,       # ISO format
    'data_expiracao': str        # ISO format
}
```

---

### 2. Cashback Loja (apps/cashback/services.py)

**Origem:** Regras de cashback customizadas por loja  
**Método:** `CashbackService.aplicar_cashback_loja()`  
**Arquivo:** `apps/cashback/services.py` (linhas 164-250)

**Fluxo:**
```python
CashbackService.aplicar_cashback_loja()
    ↓
ContaDigitalService.creditar(
    tipo_codigo='CASHBACK_LOJA',
    referencia_externa=f'LOJA:{regra_loja_id}',
    sistema_origem='CASHBACK'
)
    ↓
MovimentacaoContaDigital criada
    ↓
CashbackUso registrado
    ↓
RegraCashbackLoja.gasto_mes_atual atualizado
```

**Características:**
- ✅ Status inicial: `RETIDO` ou `LIBERADO` (baseado em regra)
- ✅ Retenção: configurável por regra
- ✅ Expiração: configurável por regra
- ✅ Afeta: `cashback_bloqueado` ou `cashback_disponivel`
- ✅ Atualiza orçamento mensal da regra
- ✅ Transação atômica

**Validações:**
- Valor mínimo da compra
- Forma de pagamento (PIX, DÉBITO, CRÉDITO)
- Dia da semana
- Horário
- Limite uso cliente/dia
- Limite uso cliente/mês
- Orçamento mensal da regra

---

### 3. Integração POS → Sistema Centralizado

**Status:** ✅ **IMPLEMENTADO**

**Implementação Atual:**
- Novos endpoints `/trdata_pinbank/` e `/trdata_own/` usam sistema centralizado
- Service unificado: `TRDataPosService` em `posp2/services_transacao_pos.py`
- Tabela unificada: `transactiondata_pos` (gateway='PINBANK' ou 'OWN')
- ✅ Usa `CashbackService.aplicar_cashback_wall()` e `.aplicar_cashback_loja()`
- ✅ Registra em `cashback_uso` com rastreabilidade completa
- ✅ IDs das regras vêm da simulação (`/simula_parcelas_v2/`)

**Payload POS:**
```json
{
  "cpf": "08733318697",
  "terminal": "PBF923BH70797",
  "valororiginal": "R$100,00",
  "cupom_codigo": "DESC10",
  "cupom_valor_desconto": 10.00,
  "cashback_wall_parametro_id": 124,
  "cashback_wall_valor": 3.00,
  "cashback_loja_regra_id": 12,
  "cashback_loja_valor": 5.00,
  "trdata": "{...}"
}
```

**Arquivos:** 
- `posp2/services_transacao_pos.py` (service unificado)
- `posp2/models.py` (TransactionDataPos)
- `parametros_wallclub/services.py` (CalculadoraDesconto com parametro_id)
- `posp2/services_v2.py` (simulação retorna IDs)

**Novo método (já implementado):**
```python
CashbackService.concessao_cashback(
    cliente_id=cliente.id,
    canal_id=canal_id,
    loja_id=loja_id,
    valor_transacao=valor_transacao,
    valor_cashback=valor_cashback,
    nsu_transacao=nsu,
    cpf=cpf,
    terminal=terminal,
    tipo_cashback='WALL',  # ou 'LOJA'
    parametro_id=parametro_wall_id  # ou regra_loja_id
)
```

**Pendências:**
- [ ] Ajustar chamada em `services_transacao.py` (linha 574-588)
- [ ] Passar `loja_id` e `valor_transacao`
- [ ] Determinar `tipo_cashback` (WALL ou LOJA)
- [ ] Passar `parametro_id` correto

---

### 4. Crédito Manual (apps/conta_digital/views.py)

**Origem:** API Mobile (cliente via app)  
**Método:** `POST /api/v1/conta-digital/creditar/`  
**Arquivo:** `apps/conta_digital/views.py` (linhas 49-104)

**Fluxo:**
```python
@require_jwt_only
def creditar(request):
    ↓
ContaDigitalService.creditar(
    tipo_codigo=request.data['tipo_operacao'],
    referencia_externa=request.data.get('referencia_externa'),
    sistema_origem=request.data.get('sistema_origem')
)
```

**Características:**
- ✅ Autenticação: JWT customizado
- ✅ Tipo operação: configurável (CREDITO, CASHBACK_CREDITO, etc)
- ✅ Validação via serializer
- ✅ Afeta: `saldo_atual` (se não afeta_cashback)

---

## 💸 FLUXOS DE DÉBITO

### 1. Débito Autorizado POS (apps/conta_digital/services_autorizacao.py)

**Origem:** Transação POS com autorização do cliente  
**Método:** `AutorizacaoService.debitar_saldo_autorizado()`  
**Arquivo:** `apps/conta_digital/services_autorizacao.py` (linhas 292-366)

**Fluxo:**
```python
# 1. POS consulta saldo
SaldoService.consultar_saldo_cliente()
    ↓ (API Interna)
POST /api/internal/conta_digital/consultar_saldo/

# 2. POS solicita autorização
SaldoService.solicitar_autorizacao_uso_saldo()
    ↓ (API Interna)
POST /api/internal/conta_digital/autorizar_uso/
    ↓
AutorizacaoService.criar_autorizacao()
    ↓
AutorizacaoUsoSaldo criada (status=PENDENTE)
    ↓
Push notification enviado ao app

# 3. Cliente aprova no app
AutorizacaoService.aprovar_autorizacao()
    ↓
ContaDigital.saldo_bloqueado += valor
    ↓
AutorizacaoUsoSaldo.status = APROVADO

# 4. POS debita após transação aprovada
AutorizacaoService.debitar_saldo_autorizado()
    ↓
ContaDigitalService.debitar(
    tipo_codigo='DEBITO',
    referencia_externa=nsu_transacao,
    sistema_origem='POSP2'
)
    ↓
ContaDigital.saldo_bloqueado -= valor
    ↓
AutorizacaoUsoSaldo.status = CONCLUIDA
```

**Características:**
- ✅ Fluxo em 4 etapas
- ✅ Bloqueio preventivo de saldo
- ✅ Expiração automática (3min pendente + 2min aprovado)
- ✅ Lock pessimista (select_for_update)
- ✅ Validação de token
- ✅ Push notification
- ✅ Transação atômica

**Tempos:**
- Criação → Aprovação: **3 minutos**
- Aprovação → Débito: **2 minutos**
- Total: **5 minutos** máximo

---

### 2. Uso de Cashback (apps/conta_digital/services.py)

**Origem:** Cliente usa cashback para pagamento  
**Método:** `ContaDigitalService.usar_cashback()`  
**Arquivo:** `apps/conta_digital/services.py` (linhas 545-587)

**Fluxo:**
```python
ContaDigitalService.usar_cashback()
    ↓
Validação: cashback_disponivel >= valor
    ↓
ContaDigital.cashback_disponivel -= valor
    ↓
MovimentacaoContaDigital criada (tipo=CASHBACK_DEBITO)
```

**Características:**
- ✅ Afeta: `cashback_disponivel`
- ✅ Validação de saldo
- ✅ Transação atômica
- ⚠️ **Não valida limites diário/mensal**

---

### 3. Expiração de Cashback (apps/cashback/services.py)

**Origem:** Job Celery (automático)  
**Método:** `CashbackService.expirar_cashback()`  
**Arquivo:** `apps/cashback/services.py` (linhas 358-397)

**Fluxo:**
```python
CashbackService.expirar_cashback()
    ↓
ContaDigitalService.debitar(
    tipo_codigo='CASHBACK_EXPIRACAO',
    sistema_origem='CASHBACK'
)
    ↓
CashbackUso.status = EXPIRADO
```

**Características:**
- ✅ Afeta: `cashback_disponivel`
- ✅ Apenas cashback LIBERADO
- ✅ Transação atômica
- ⚠️ **Job Celery não implementado**

---

### 4. Débito Manual (apps/conta_digital/views.py)

**Origem:** API Mobile (cliente via app)  
**Método:** `POST /api/v1/conta-digital/debitar/`  
**Arquivo:** `apps/conta_digital/views.py` (linhas 107-162)

**Fluxo:**
```python
@require_jwt_only
def debitar(request):
    ↓
ContaDigitalService.debitar(
    tipo_codigo=request.data['tipo_codigo'],
    referencia_externa=request.data.get('referencia_externa'),
    sistema_origem=request.data.get('sistema_origem')
)
```

**Características:**
- ✅ Autenticação: JWT customizado
- ✅ Validação de saldo
- ✅ Validação conta ativa/bloqueada

---

## 🔄 FLUXOS DE LIBERAÇÃO E ESTORNO

### 1. Liberação de Cashback Retido

**Origem:** Job Celery (automático) ou Manual  
**Método:** `CashbackService.liberar_cashback()`  
**Arquivo:** `apps/cashback/services.py` (linhas 316-355)

**Fluxo:**
```python
CashbackService.liberar_cashback()
    ↓
ContaDigital.cashback_bloqueado -= valor
ContaDigital.cashback_disponivel += valor
    ↓
CashbackUso.status = LIBERADO
```

**Características:**
- ✅ Apenas cashback RETIDO
- ✅ Lock pessimista
- ✅ Transação atômica
- ⚠️ **Job Celery não implementado**

---

### 2. Estorno de Cashback

**Origem:** Transação estornada  
**Método:** `CashbackService.estornar_cashback()`  
**Arquivo:** `apps/cashback/services.py` (linhas 400-447)

**Fluxo:**
```python
CashbackService.estornar_cashback(transacao_tipo, transacao_id)
    ↓
Busca CashbackUso relacionados
    ↓
Se RETIDO: remove de cashback_bloqueado
Se LIBERADO: debita de cashback_disponivel
    ↓
CashbackUso.status = ESTORNADO
```

**Características:**
- ✅ Suporta RETIDO e LIBERADO
- ✅ Transação atômica
- ✅ Busca por transacao_tipo + transacao_id

---

### 3. Estorno de Movimentação

**Origem:** Manual (admin ou API)  
**Método:** `ContaDigitalService.estornar_movimentacao()`  
**Arquivo:** `apps/conta_digital/services.py` (linhas 409-470)

**Fluxo:**
```python
ContaDigitalService.estornar_movimentacao(movimentacao_id, motivo)
    ↓
Validação: status=PROCESSADA, permite_estorno=True
    ↓
Operação inversa (débito→crédito ou crédito→débito)
    ↓
MovimentacaoContaDigital criada (tipo=ESTORNO)
    ↓
Movimentacao original.status = ESTORNADA
```

**Características:**
- ✅ Operação inversa automática
- ✅ Validação de saldo (estorno de crédito)
- ✅ Link entre movimentações
- ✅ Transação atômica

---

## ✅ CHECKLIST DE VALIDAÇÃO

### 1. Estrutura de Dados

- [ ] **Tabelas criadas:**
  - [ ] `conta_digital`
  - [ ] `conta_digital_tipos_movimentacao`
  - [ ] `conta_digital_movimentacoes`
  - [ ] `conta_digital_cashback_retencoes`
  - [ ] `conta_digital_autorizacao_uso_saldo`
  - [ ] `conta_digital_cashback_param_loja`
  - [ ] `conta_digital_configuracoes`

- [ ] **Índices criados:**
  - [ ] ContaDigital: (cliente_id, canal_id) UNIQUE
  - [ ] ContaDigital: cpf
  - [ ] MovimentacaoContaDigital: (conta_digital, data_movimentacao)
  - [ ] MovimentacaoContaDigital: (referencia_externa, sistema_origem)
  - [ ] AutorizacaoUsoSaldo: autorizacao_id UNIQUE
  - [ ] AutorizacaoUsoSaldo: (cliente_id, status)

### 2. Tipos de Movimentação

- [ ] **Tipos cadastrados:**
  - [ ] `CREDITO` - Crédito normal
  - [ ] `DEBITO` - Débito normal
  - [ ] `CASHBACK_WALL` - Cashback Wall
  - [ ] `CASHBACK_LOJA` - Cashback Loja
  - [ ] `CASHBACK_CREDITO` - Crédito cashback genérico
  - [ ] `CASHBACK_DEBITO` - Uso de cashback
  - [ ] `CASHBACK_EXPIRACAO` - Expiração cashback
  - [ ] `CASHBACK_ESTORNO` - Estorno cashback
  - [ ] `ESTORNO` - Estorno genérico
  - [ ] `BLOQUEIO` - Bloqueio de saldo
  - [ ] `DESBLOQUEIO` - Desbloqueio de saldo
  - [ ] `TRANSFERENCIA` - Transferência
  - [ ] `TAXA` - Taxa
  - [ ] `PIX` - PIX

- [ ] **Configurações corretas:**
  - [ ] `afeta_cashback` configurado corretamente
  - [ ] `periodo_retencao_dias` configurado para cashback
  - [ ] `permite_estorno` configurado
  - [ ] `visivel_extrato` configurado

### 3. Configurações por Canal

- [ ] **ConfiguracaoContaDigital criada para cada canal:**
  - [ ] Canal 1 (principal)
  - [ ] Outros canais ativos

- [ ] **Configurações validadas:**
  - [ ] `limite_diario_padrao`
  - [ ] `limite_mensal_padrao`
  - [ ] `periodo_retencao_cashback_dias` (30)
  - [ ] `auto_criar_conta` (true)

### 4. Integridade de Dados

- [ ] **Contas digitais:**
  - [ ] Todas contas têm cliente_id válido
  - [ ] Todas contas têm canal_id válido
  - [ ] CPF preenchido e válido
  - [ ] Saldos não negativos (ou permitido se configurado)
  - [ ] Limites configurados

- [ ] **Movimentações:**
  - [ ] Todas têm conta_digital válida
  - [ ] Todas têm tipo_movimentacao válido
  - [ ] saldo_anterior e saldo_posterior consistentes
  - [ ] Valores positivos
  - [ ] Status válido

- [ ] **Autorizações:**
  - [ ] Todas têm conta_digital válida
  - [ ] autorizacao_id único
  - [ ] Status válido
  - [ ] Expiradas marcadas corretamente

### 5. Lógica de Negócio

- [ ] **Cashback:**
  - [ ] Retenção funcionando (30 dias)
  - [ ] Liberação automática funcionando
  - [ ] Expiração automática funcionando (90 dias)
  - [ ] Estorno funcionando (RETIDO e LIBERADO)

- [ ] **Autorização POS:**
  - [ ] Criação funcionando
  - [ ] Aprovação bloqueando saldo
  - [ ] Débito liberando bloqueio
  - [ ] Expiração liberando bloqueio
  - [ ] Negação liberando bloqueio

- [ ] **Validações:**
  - [ ] Saldo insuficiente bloqueado
  - [ ] Conta inativa bloqueada
  - [ ] Conta bloqueada não permite movimentação
  - [ ] Limites diário/mensal validados ⚠️ **NÃO IMPLEMENTADO**

### 6. Jobs Celery

- [ ] **Tasks implementadas:**
  - [ ] `liberar_cashback_retido_automatico` ⚠️ **NÃO IMPLEMENTADO**
  - [ ] `expirar_cashback_vencido` ⚠️ **NÃO IMPLEMENTADO**
  - [ ] `expirar_autorizacoes_pendentes` ✅ **IMPLEMENTADO**

- [ ] **Schedule configurado:**
  - [ ] Liberação cashback: diário
  - [ ] Expiração cashback: diário
  - [ ] Expiração autorizações: 1 minuto

### 7. APIs Internas

- [ ] **Endpoints funcionando:**
  - [ ] `POST /api/internal/conta_digital/consultar_saldo/`
  - [ ] `POST /api/internal/conta_digital/autorizar_uso/`
  - [ ] `POST /api/internal/conta_digital/debitar_saldo/`
  - [ ] `POST /api/internal/conta_digital/estornar_saldo/`
  - [ ] `POST /api/internal/conta_digital/calcular_maximo/`

- [ ] **Comunicação entre containers:**
  - [ ] POS → APIs (consulta saldo)
  - [ ] POS → APIs (autorização)
  - [ ] POS → APIs (débito)

### 8. Logs e Auditoria

- [ ] **Logs registrados:**
  - [ ] Créditos
  - [ ] Débitos
  - [ ] Autorizações
  - [ ] Estornos
  - [ ] Erros

- [ ] **Nível correto:**
  - [ ] DEBUG: fluxo normal
  - [ ] INFO: operações concluídas
  - [ ] WARNING: validações negadas
  - [ ] ERROR: exceções

---

## 🚨 GAPS IDENTIFICADOS

### 1. CRÍTICO

#### 1.1. Tipos de Movimentação Não Cadastrados
**Problema:** Tabela `conta_digital_tipos_movimentacao` vazia  
**Impacto:** Nenhum lançamento funciona  
**Ação:** Criar seed obrigatório

#### 1.2. Configurações de Canal Não Criadas
**Problema:** Tabela `conta_digital_configuracoes` vazia  
**Impacto:** Usa valores padrão hardcoded  
**Ação:** Criar configuração para cada canal

#### 1.3. Jobs Celery Não Implementados
**Problema:** Liberação e expiração de cashback não automatizadas  
**Impacto:** Cashback fica retido indefinidamente  
**Ação:** Implementar tasks em `tasks.py`

### 2. ALTO

#### 2.1. Validação de Limites Não Implementada
**Problema:** `limite_diario` e `limite_mensal` não são validados  
**Impacto:** Cliente pode movimentar valores ilimitados  
**Ação:** Implementar validação em `ContaDigitalService`

#### 2.2. Inconsistência de Timezone
**Problema:** Usa `datetime.now()` (naive) em alguns lugares  
**Impacto:** Problemas com horário de verão  
**Ação:** Padronizar uso de `_get_local_now()`

#### 2.3. Cashback POS Não Usa CashbackUso
**Problema:** `posp2/services_conta_digital.py` não registra em `CashbackUso`  
**Impacto:** Histórico incompleto, liberação/expiração não funciona  
**Ação:** Integrar com `CashbackService.aplicar_cashback_wall()`

### 3. MÉDIO

#### 3.1. Estorno de Cashback Permite Saldo Negativo
**Problema:** Se cashback já foi usado, estorno cria saldo negativo  
**Impacto:** Inconsistência contábil  
**Ação:** Validar saldo antes de estornar ou criar regra de negócio

#### 3.2. Falta Dashboard Admin
**Problema:** Não há interface para visualizar movimentações  
**Impacto:** Dificuldade de suporte  
**Ação:** Criar dashboard em `admin.py`

#### 3.3. Falta Relatórios
**Problema:** Não há relatórios de cashback, saldo, etc  
**Impacto:** Dificuldade de análise  
**Ação:** Criar views de relatório

### 4. BAIXO

#### 4.1. Falta Testes Automatizados
**Problema:** Não há testes unitários  
**Impacto:** Risco de regressão  
**Ação:** Criar suite de testes

#### 4.2. Documentação de APIs Incompleta
**Problema:** Falta documentação Swagger/OpenAPI  
**Impacto:** Dificuldade de integração  
**Ação:** Adicionar docstrings e schema

---

## 💳 LANÇAMENTOS DE COMPRAS NA CONTA DIGITAL

### Status: 🔮 **EM PLANEJAMENTO**

**Objetivo:** Registrar compras realizadas pelo cliente na conta digital para controle financeiro completo.

**Cenários a Considerar:**

#### 1. Compra com Saldo da Conta
- Cliente usa saldo disponível para pagar compra no POS
- Já implementado via `AutorizacaoService.debitar_saldo_autorizado()`
- ✅ Funcional

#### 2. Compra com Cashback
- Cliente usa cashback disponível para pagar compra
- Já implementado via `ContaDigitalService.usar_cashback()`
- ✅ Funcional

#### 3. Compra com Cartão (Registro Informativo)
- **NOVO:** Registrar compra feita com cartão como movimentação informativa
- Objetivo: Cliente visualizar histórico completo no extrato
- Não afeta saldo (apenas informativo)

**Proposta de Implementação:**

```python
# Novo tipo de movimentação
COMPRA_CARTAO = {
    'codigo': 'COMPRA_CARTAO',
    'nome': 'Compra com Cartão',
    'debita_saldo': False,
    'afeta_cashback': False,
    'visivel_extrato': True,
    'categoria': 'INFORMATIVO'
}

# Novo método
ContaDigitalService.registrar_compra_informativa(
    cliente_id=cliente_id,
    canal_id=canal_id,
    valor=valor_compra,
    descricao=f'Compra - {nome_loja}',
    referencia_externa=nsu_transacao,
    sistema_origem='POSP2',
    dados_adicionais={
        'forma_pagamento': 'CREDITO',
        'parcelas': 3,
        'bandeira': 'VISA',
        'estabelecimento': nome_loja
    }
)
```

**Benefícios:**
- ✅ Extrato completo (compras + cashback + saldo)
- ✅ Histórico unificado
- ✅ Melhor UX no app
- ✅ Dados para análise de comportamento

**Pendências:**
- [ ] Definir regras de negócio (registrar todas compras ou apenas com CPF?)
- [ ] Definir estrutura de dados adicionais
- [ ] Criar tipo de movimentação COMPRA_CARTAO
- [ ] Implementar método `registrar_compra_informativa()`
- [ ] Ajustar extrato para exibir compras informativas
- [ ] Testar impacto em performance

**Discussão Necessária:**
- Registrar todas compras ou apenas quando cliente tem conta digital?
- Incluir compras anônimas (sem CPF)?
- Limite de retenção de histórico (90 dias? 1 ano?)
- Impacto em volume de dados

---

## 📋 PLANO DE AÇÃO

### Fase 1: CRÍTICO (Imediato)

**1.1. Criar Seed de Tipos de Movimentação**
```bash
python manage.py seed_tipos_movimentacao
```

Arquivo: `apps/conta_digital/management/commands/seed_tipos_movimentacao.py`

Tipos a criar:
- CREDITO (debita_saldo=False, afeta_cashback=False)
- DEBITO (debita_saldo=True, afeta_cashback=False)
- CASHBACK_WALL (debita_saldo=False, afeta_cashback=True, periodo_retencao_dias=30)
- CASHBACK_LOJA (debita_saldo=False, afeta_cashback=True, periodo_retencao_dias=30)
- CASHBACK_CREDITO (debita_saldo=False, afeta_cashback=True)
- CASHBACK_DEBITO (debita_saldo=True, afeta_cashback=True)
- CASHBACK_EXPIRACAO (debita_saldo=True, afeta_cashback=True)
- CASHBACK_ESTORNO (debita_saldo=True, afeta_cashback=True)
- ESTORNO (permite_estorno=False)
- BLOQUEIO (debita_saldo=False, visivel_extrato=False)
- DESBLOQUEIO (debita_saldo=False, visivel_extrato=False)
- TRANSFERENCIA
- TAXA (debita_saldo=True)
- PIX

**1.2. Criar Configurações de Canal**
```bash
python manage.py seed_configuracoes_canal
```

Arquivo: `apps/conta_digital/management/commands/seed_configuracoes_canal.py`

Para cada canal ativo:
- limite_diario_padrao: R$ 5.000,00
- limite_mensal_padrao: R$ 50.000,00
- periodo_retencao_cashback_dias: 30
- auto_criar_conta: True

**1.3. Implementar Jobs Celery**

Arquivo: `apps/conta_digital/tasks.py`

```python
@shared_task
def liberar_cashback_retido_automatico():
    """Libera cashback retido após período de retenção"""
    
@shared_task
def expirar_cashback_vencido():
    """Expira cashback não usado após período de validade"""
```

Adicionar ao `celerybeat-schedule.py`:
```python
'liberar-cashback-retido': {
    'task': 'apps.conta_digital.tasks.liberar_cashback_retido_automatico',
    'schedule': crontab(hour=2, minute=0),  # 02:00 diário
},
'expirar-cashback-vencido': {
    'task': 'apps.conta_digital.tasks.expirar_cashback_vencido',
    'schedule': crontab(hour=3, minute=0),  # 03:00 diário
},
```

### Fase 2: ALTO (Curto Prazo)

**2.1. Implementar Validação de Limites**

Arquivo: `apps/conta_digital/services.py`

Adicionar método:
```python
@staticmethod
def _validar_limites(conta, valor, tipo_operacao):
    """Valida limites diário e mensal"""
    hoje = date.today()
    
    # Limite diário
    total_dia = MovimentacaoContaDigital.objects.filter(
        conta_digital=conta,
        data_movimentacao__date=hoje,
        tipo_movimentacao__debita_saldo=True
    ).aggregate(Sum('valor'))['valor__sum'] or Decimal('0.00')
    
    if total_dia + valor > conta.limite_diario:
        raise ValidationError(f'Limite diário excedido: R$ {conta.limite_diario}')
    
    # Limite mensal
    primeiro_dia_mes = hoje.replace(day=1)
    total_mes = MovimentacaoContaDigital.objects.filter(
        conta_digital=conta,
        data_movimentacao__date__gte=primeiro_dia_mes,
        tipo_movimentacao__debita_saldo=True
    ).aggregate(Sum('valor'))['valor__sum'] or Decimal('0.00')
    
    if total_mes + valor > conta.limite_mensal:
        raise ValidationError(f'Limite mensal excedido: R$ {conta.limite_mensal}')
```

Chamar em `debitar()` e `usar_cashback()`.

**2.2. Padronizar Timezone**

Substituir todos `datetime.now()` por `ContaDigitalService._get_local_now()`.

**2.3. Integrar Cashback POS com CashbackService**

Arquivo: `posp2/services_conta_digital.py`

Modificar `CashbackService.concessao_cashback()` para usar:
```python
from apps.cashback.services import CashbackService as CashbackServiceCentralizado

resultado = CashbackServiceCentralizado.aplicar_cashback_wall(
    parametro_wall_id=parametro_wall_id,  # Buscar do contexto
    cliente_id=cliente_id,
    loja_id=loja_id,
    canal_id=canal_id,
    transacao_tipo='POS',
    transacao_id=transacao_id,
    valor_transacao=valor_transacao,
    valor_cashback=valor_cashback
)
```

### Fase 3: MÉDIO (Médio Prazo)

**3.1. Validar Saldo em Estorno de Cashback**

Arquivo: `apps/cashback/services.py`

Modificar `estornar_cashback()`:
```python
elif cashback.status == 'LIBERADO':
    # Verificar se tem saldo antes de debitar
    conta = ContaDigital.objects.get(
        cliente_id=cashback.cliente_id,
        canal_id=cashback.canal_id
    )
    
    if conta.cashback_disponivel < cashback.valor_cashback:
        # Criar débito parcial ou bloquear estorno?
        registrar_log('apps.cashback',
            f'⚠️ Saldo insuficiente para estorno: disponível={conta.cashback_disponivel}, '
            f'necessário={cashback.valor_cashback}',
            nivel='WARNING')
        # Decidir regra de negócio
```

**3.2. Criar Dashboard Admin**

Arquivo: `apps/conta_digital/admin.py`

Adicionar:
- Lista de contas com saldos
- Filtros por canal, status
- Ações em lote (bloquear, desbloquear)
- Inline de movimentações
- Gráficos de evolução

**3.3. Criar Relatórios**

Arquivo: `portais/admin/views_conta_digital.py`

Relatórios:
- Saldos por canal
- Movimentações por período
- Cashback concedido vs usado
- Autorizações por status
- Top clientes por saldo

### Fase 4: BAIXO (Longo Prazo)

**4.1. Criar Testes Automatizados**

Arquivo: `apps/conta_digital/tests/`

Testes:
- `test_creditar.py`
- `test_debitar.py`
- `test_cashback.py`
- `test_autorizacao.py`
- `test_estorno.py`

**4.2. Documentação de APIs**

Adicionar docstrings completas e schema OpenAPI.

---

## 📊 RESUMO EXECUTIVO

### Lançamentos Mapeados

| Origem | Tipo | Método | Arquivo | Status |
|--------|------|--------|---------|--------|
| Cashback Wall | Crédito | `aplicar_cashback_wall()` | `apps/cashback/services.py` | ✅ OK |
| Cashback Loja | Crédito | `aplicar_cashback_loja()` | `apps/cashback/services.py` | ✅ OK |
| Cashback POS | Crédito | `concessao_cashback()` | `posp2/services_conta_digital.py` | ⚠️ Não usa CashbackUso |
| Débito POS | Débito | `debitar_saldo_autorizado()` | `apps/conta_digital/services_autorizacao.py` | ✅ OK |
| Uso Cashback | Débito | `usar_cashback()` | `apps/conta_digital/services.py` | ⚠️ Sem validação limites |
| Expiração | Débito | `expirar_cashback()` | `apps/cashback/services.py` | ⚠️ Job não implementado |
| Liberação | Interno | `liberar_cashback()` | `apps/cashback/services.py` | ⚠️ Job não implementado |
| Estorno | Ambos | `estornar_movimentacao()` | `apps/conta_digital/services.py` | ✅ OK |

### Gaps Críticos

1. ❌ **Tipos de movimentação não cadastrados** - BLOQUEANTE
2. ❌ **Jobs Celery não implementados** - BLOQUEANTE para cashback
3. ⚠️ **Validação de limites não implementada** - RISCO OPERACIONAL
4. ⚠️ **Cashback POS não integrado** - INCONSISTÊNCIA

### Próximos Passos

1. **Imediato:** Criar seeds (tipos + configurações)
2. **Urgente:** Implementar jobs Celery
3. **Importante:** Validar limites diário/mensal
4. **Desejável:** Integrar cashback POS com sistema centralizado

---

**Responsável:** Equipe Técnica WallClub  
**Revisão:** Pendente  
**Próxima Atualização:** Após execução Fase 1
