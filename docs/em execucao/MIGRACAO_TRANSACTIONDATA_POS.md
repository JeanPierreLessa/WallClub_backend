# Migração para transactiondata_pos - Tabela Unificada

**Data Início:** 19/12/2025  
**Status:** Em andamento  
**Objetivo:** Unificar transações Pinbank e Own em uma única tabela

---

## 📋 Contexto

### Situação Atual (Antes da Migração)
- `transactiondata` - Transações Pinbank (gateway antigo)
- `transactiondata_own` - Transações Own (gateway novo)
- 2 services separados: `TRDataService` e `TRDataOwnService`

### Situação Alvo (Após Migração)
- `transactiondata_pos` - Tabela unificada (campo `gateway`: PINBANK/OWN)
- 1 service unificado: `TRDataPosService`
- 2 endpoints: `/trdata_pinbank/` e `/trdata_own/`

---

## ✅ Alterações Realizadas (19/12/2025)

### 1. CalculadoraBaseGestao - Parâmetro Opcional `info_loja`

**Arquivo:** `parametros_wallclub/calculadora_base_gestao.py`

**Mudança:**
```python
# ANTES
def calcular_valores_primarios(self, dados_linha, tabela: str):
    info_loja = self.pinbank_service.pega_info_loja(identificador, tabela)

# DEPOIS
def calcular_valores_primarios(self, dados_linha, tabela: str, info_loja=None):
    if info_loja is None:
        info_loja = self.pinbank_service.pega_info_loja(identificador, tabela)
```

**Motivo:**
- Tabelas antigas (`transactiondata`, `transactiondata_own`) continuam usando `PinbankService`
- Tabela nova (`transactiondata_pos`) passa `info_loja` já resolvida
- Evita transação Own acessar código Pinbank

**Retrocompatibilidade:** ✅ SIM - Parâmetro opcional não quebra código existente

---

### 2. TRDataPosService - Passar info_loja para Calculadora

**Arquivo:** `posp2/services_transacao_pos.py`

**Mudança:**
```python
# ANTES
calculadora = CalculadoraBaseGestao()
valores_calculados = calculadora.calcular_valores_primarios(dados_linha, tabela='transactiondata_pos')

# DEPOIS
loja_info = {'id': loja_id, 'loja_id': loja_id, 'canal_id': canal_id}
calculadora = CalculadoraBaseGestao()
valores_calculados = calculadora.calcular_valores_primarios(
    dados_linha, 
    tabela='transactiondata_pos',
    info_loja=loja_info
)
```

**Motivo:**
- `info_loja` já foi resolvida no início do processamento
- Evita buscar novamente via `PinbankService`
- Isola lógica Own de lógica Pinbank

---

### 3. PinbankService - Suporte a transactiondata_pos (REVERTIDO)

**Arquivo:** `pinbank/services.py`

**Mudança Inicial (INCORRETA):**
```python
elif tabela == 'transactiondata_pos':
    return self._buscar_loja_por_nsu(identificador)
```

**Status:** ❌ REVERTIDO - Não deve ser usado para `transactiondata_pos`

**Motivo da Reversão:**
- `transactiondata_pos` não deve usar `PinbankService`
- Info loja já é resolvida antes de chamar calculadora
- Mantém isolamento entre gateways

---

## 🔄 Período de Transição

### Tabelas em Paralelo
Durante a migração, 3 tabelas coexistem:

| Tabela | Service | Status | Gateway |
|--------|---------|--------|---------|
| `transactiondata` | `TRDataService` | ✅ Ativo (legado) | Pinbank |
| `transactiondata_own` | `TRDataOwnService` | ⚠️ Deprecado | Own |
| `transactiondata_pos` | `TRDataPosService` | ✅ Ativo (Own em produção) | Pinbank + Own |

### Estratégia de Migração
1. ✅ Criar `transactiondata_pos` e `TRDataPosService`
2. ✅ Ajustar `CalculadoraBaseGestao` para aceitar `info_loja` opcional
3. ✅ Testar transações Own em `transactiondata_pos` - **Em produção desde 22/12/2025**
4. ⏳ Testar transações Pinbank em `transactiondata_pos`
5. ⏳ Migrar endpoints gradualmente
6. ⏳ Deprecar tabelas antigas após validação completa

---

## 🎯 Próximos Passos

### Imediato
- [ ] Testar transação Own completa (cálculo + slip)
- [ ] Validar campos calculados vs tabela antiga
- [ ] Testar transação Pinbank em `transactiondata_pos`

### Médio Prazo
- [ ] Migrar endpoint `/trdata/` para usar `TRDataPosService`
- [ ] Migrar endpoint `/trdata_own/` para usar `TRDataPosService`
- [ ] Atualizar portais para consultar `transactiondata_pos`

### Longo Prazo - Limpeza de Código
- [ ] Deprecar `TRDataService` (Pinbank legado)
- [ ] Deprecar `TRDataOwnService` (Own legado)
- [ ] Remover tabelas `transactiondata` e `transactiondata_own`
- [ ] **Remover métodos obsoletos do `PinbankService`:**
  - `pega_info_loja()` - Não mais necessário (info_loja passada como parâmetro)
  - `pega_info_canal()` - Não mais necessário (info_canal passada como parâmetro)
  - `_buscar_loja_por_nsu()` - Usado apenas por tabelas antigas
  - `_buscar_loja_por_cnpj()` - Usado apenas por tabelas antigas
  - `_buscar_canal_por_nsu()` - Usado apenas por tabelas antigas
  - `_buscar_canal_por_cnpj()` - Usado apenas por tabelas antigas
- [ ] **Remover parâmetros opcionais da `CalculadoraBaseGestao`:**
  - Tornar `info_loja` e `info_canal` obrigatórios
  - Remover lógica condicional de busca via `PinbankService`

---

## 📊 Mapeamento de Dependências

### 1. Portais (Consultas)

#### Portal Lojista
- **`portais/lojista/views_vendas_operador.py`** (linha 131)
  - Query: `INNER JOIN transactiondata t ON b.var9 = t.nsuPinbank`
  - Busca operador POS das transações
  - **Ação:** Migrar para `transactiondata_pos`

#### Portal Admin
- **Nenhuma referência direta encontrada**
  - Usa `base_transacoes_unificadas` (já unificada)

### 2. Cargas e Processamento

#### Cargas Pinbank
- **`pinbank/cargas_pinbank/services_carga_base_gestao_pos.py`**
  - Query: `INNER JOIN transactiondata t ON pep.NsuOperacao = t.nsuPinbank`
  - Processa transações Wallet (POS) para BaseTransacoesGestao
  - **Ação:** Migrar para `transactiondata_pos WHERE gateway='PINBANK'`

- **`pinbank/cargas_pinbank/services_carga_base_unificada_pos.py`**
  - Query: `INNER JOIN transactiondata t ON pep.NsuOperacao = t.nsuPinbank`
  - Processa transações Wallet (POS) para base_transacoes_unificadas
  - **Ação:** Migrar para `transactiondata_pos WHERE gateway='PINBANK'`

- **`pinbank/cargas_pinbank/services_carga_credenciadora.py`** (linha 87)
  - Query: `pep.NsuOperacao not in (select nsuPinbank from transactiondata)`
  - Filtra transações que NÃO estão na transactiondata (credenciadora)
  - **Ação:** Migrar para `transactiondata_pos WHERE gateway='PINBANK'`

- **`pinbank/cargas_pinbank/services_carga_base_unificada_credenciadora.py`** (linhas 100, 112)
  - Query: `LEFT JOIN transactiondata td ON pep.NsuOperacao = td.nsuPinbank`
  - Filtra transações credenciadora
  - **Ação:** Migrar para `transactiondata_pos WHERE gateway='PINBANK'`

- **`pinbank/cargas_pinbank/services_ajustes_manuais.py`** (linhas 40, 51)
  - INSERT em `transactiondata` de registros faltantes
  - DELETE duplicatas
  - **Ação:** Migrar para `transactiondata_pos`

#### Cargas Own
- **`adquirente_own/cargas_own/services_carga_base_gestao_own.py`** (linha 71)
  - Query: `JOIN transactiondata_own t ON oet.identificadorTransacao = t.txTransactionId`
  - Processa transações Own para BaseTransacoesGestao
  - **Ação:** ✅ **JÁ MIGRADO** - Own usa `transactiondata_pos` desde 22/12/2025

### 3. APIs e Services

#### Cupom
- **`apps/cupom/models.py`** (linha 178)
  - Campo `transacao_id` referencia TransactionData ou CheckoutTransaction
  - **Ação:** Adicionar suporte para `transactiondata_pos`

- **`apps/cupom/services.py`** (linha 140)
  - Comentário menciona TransactionData
  - **Ação:** Atualizar documentação

#### Conta Digital
- **`apps/conta_digital/admin.py`**, **`services.py`**, **`views.py`**
  - Referências genéricas (não queries diretas)
  - **Ação:** Revisar após migração completa

#### Transações
- **`apps/transacoes/services.py`**, **`views.py`**
  - Referências genéricas
  - **Ação:** Revisar após migração completa

### 4. Gestão Financeira

- **Nenhuma referência direta encontrada**
  - Usa `BaseTransacoesGestao` (já unificada)

### 5. Tasks Celery

#### Pinbank
- **`pinbank/cargas_pinbank/tasks.py`**
  - Tasks que chamam os services de carga
  - **Ação:** Nenhuma alteração necessária (services já serão migrados)

#### Own
- **`adquirente_own/cargas_own/tasks.py`**
  - Tasks que chamam os services de carga Own
  - **Ação:** ✅ **JÁ MIGRADO**

#### Outros
- **`apps/ofertas/tasks.py`**, **`apps/cashback/tasks.py`**, **`apps/conta_digital/tasks.py`**
  - Não referenciam transactiondata diretamente
  - **Ação:** Nenhuma

---

## 📋 Checklist de Migração Completa

### Fase 1: Pinbank em Produção ⏳
- [ ] Migrar endpoint `/trdata/` para `TRDataPosService`
- [ ] Testar transações Pinbank em `transactiondata_pos`
- [ ] Validar slip e cálculos

### Fase 2: Cargas e Processamento ⏳
- [ ] Migrar `services_carga_base_gestao_pos.py`
- [ ] Migrar `services_carga_base_unificada_pos.py`
- [ ] Migrar `services_carga_credenciadora.py`
- [ ] Migrar `services_carga_base_unificada_credenciadora.py`
- [ ] Migrar `services_ajustes_manuais.py`

### Fase 3: Portais e Consultas ⏳
- [ ] Migrar `views_vendas_operador.py` (Portal Lojista)
- [ ] Revisar todos os relatórios e exports
- [ ] Atualizar dashboards

### Fase 4: APIs e Integrações ⏳
- [ ] Atualizar `apps/cupom` para suportar `transactiondata_pos`
- [ ] Revisar `apps/conta_digital`
- [ ] Revisar `apps/transacoes`

### Fase 5: Validação Final ⏳
- [ ] Comparar dados: `transactiondata` vs `transactiondata_pos` (Pinbank)
- [ ] Comparar dados: `transactiondata_own` vs `transactiondata_pos` (Own)
- [ ] Validar integridade referencial
- [ ] Testar todos os fluxos end-to-end

### Fase 6: Deprecação ⏳
- [ ] Marcar `transactiondata` como deprecated
- [ ] Marcar `transactiondata_own` como deprecated
- [ ] Remover `TRDataService` (Pinbank legado)
- [ ] Remover `TRDataOwnService` (Own legado)
- [ ] Limpar métodos obsoletos do `PinbankService`
- [ ] Tornar `info_loja` e `info_canal` obrigatórios na calculadora

### Fase 7: Remoção (Futuro) ⏳
- [ ] Backup das tabelas antigas
- [ ] DROP `transactiondata`
- [ ] DROP `transactiondata_own`
- [ ] Remover models Django das tabelas antigas

---

## ⚠️ Pontos de Atenção

### Isolamento de Gateway
- ❌ **NUNCA** transação Own deve acessar `PinbankService`
- ❌ **NUNCA** transação Pinbank deve acessar `OwnService`
- ✅ `CalculadoraBaseGestao` deve ser agnóstica ao gateway

### Retrocompatibilidade
- ✅ Mudanças devem ser retrocompatíveis
- ✅ Tabelas antigas continuam funcionando durante transição
- ✅ Parâmetros opcionais não quebram código existente

### Validação
- ✅ Comparar valores calculados: nova tabela vs antiga
- ✅ Validar slip de impressão
- ✅ Testar ambos gateways (Pinbank + Own)

---

## 📝 Logs de Teste

### Teste 1 - Own (19/12/2025 11:33)
```
[INFO] Processamento Own
[INFO] Terminal=5202172510000286, TxID=251219000004188460, Valor=R$ 10.00
[INFO] Loja encontrada: loja_id=26, canal_id=1
[INFO] ✅ Transação inserida: ID=4, Gateway=OWN
[ERROR] Loja não encontrada para NSU 251219000004188460
```

**Problema:** Calculadora tentou buscar loja via `PinbankService`  
**Solução:** Passar `info_loja` como parâmetro opcional  
**Status:** ✅ Corrigido

---

**Última Atualização:** 22/12/2025 15:41  
**Responsável:** Jean Lessa

---

## 📝 Log de Migração

### 22/12/2025 - Triggers e Migração Histórica
- ✅ Criados triggers `trg_transactiondata_insert_sync` e `trg_transactiondata_update_sync`
- ✅ Triggers configurados com `DECLARE CONTINUE HANDLER FOR SQLEXCEPTION` (fail-safe)
- ✅ Executada migração histórica: `transactiondata` → `transactiondata_pos`
- ✅ Sincronização automática ativa em produção
- 📊 Status: Coexistência ativa - dados novos sincronizam automaticamente via trigger

### 22/12/2025 - Implementações de Migração
- ✅ **Push Notification em `TRDataPosService`**
  - Adicionado método `_enviar_push_notification()` (linhas 794-886)
  - Valida cliente no canal via API interna
  - Envia push via `NotificationService` com template `transacao_aprovada`
  - Não interrompe fluxo em caso de erro (fail-safe)
  
- ✅ **Portal Lojista - `views_vendas_operador.py`**
  - Migrado JOIN de `transactiondata` para `transactiondata_pos` (linha 131)
  - Query agora usa: `INNER JOIN transactiondata_pos t ON b.var9 = t.nsu_gateway AND t.gateway = 'PINBANK'`
  - Mantém compatibilidade com filtros existentes
  
- ✅ **APIs de Cupom**
  - Atualizado `cupom/models.py` - help_text do campo `transacao_id` (linha 178)
  - Atualizado `cupom/services.py` - docstring do método `registrar_uso()` (linha 140)
  - Agora suporta `TransactionDataPos` além das tabelas legadas

---

## 🔄 Script de Migração de Dados

### Migração: `transactiondata` → `transactiondata_pos`

```sql
-- ============================================================
-- MIGRAÇÃO: transactiondata (Pinbank) → transactiondata_pos
-- ============================================================
-- Migra transações Pinbank da tabela legada para a unificada
-- Gateway: PINBANK
-- ============================================================

INSERT INTO transactiondata_pos (
    gateway,
    datahora,
    valor_original,
    celular,
    cpf,
    terminal,
    operador_pos,
    nsu_gateway,
    nsuAcquirer,
    nsuTerminal,
    nsuHost,
    authorizationCode,
    amount,
    originalAmount,
    totalInstallments,
    paymentMethod,
    brand,
    cardNumber,
    cardName,
    hostTimestamp,
    terminalTimestamp,
    modalidade_wall,
    autorizacao_id,
    valor_desconto,
    valor_cashback,
    cashback_concedido,
    created_at,
    updated_at
)
SELECT 
    'PINBANK' AS gateway,
    
    -- Dados básicos
    STR_TO_DATE(
        SUBSTRING_INDEX(REPLACE(t.datahora, 'T', ' '), '.', 1),
        '%Y-%m-%d %H:%i:%s'
    ) AS datahora,
    t.valor_original,
    t.celular,
    t.cpf,
    t.terminal,
    t.operador_pos,
    
    -- Identificadores (nsuPinbank vira nsu_gateway)
    t.nsuPinbank AS nsu_gateway,
    t.nsuAcquirer,
    CAST(t.nsuTerminal AS CHAR) AS nsuTerminal,
    CAST(t.nsuHost AS CHAR) AS nsuHost,
    t.authorizationCode,
    
    -- Valores
    t.amount,
    t.originalAmount,
    COALESCE(t.totalInstallments, 1) AS totalInstallments,
    
    -- Método de pagamento
    t.paymentMethod,
    t.brand,
    t.cardNumber,
    t.cardName,
    
    -- Timestamps
    CAST(t.hostTimestamp AS CHAR) AS hostTimestamp,
    t.terminalTimestamp,
    
    -- Wall Club
    t.modalidade_wall,
    t.autorizacao_id,
    COALESCE(t.valor_desconto, 0) AS valor_desconto,
    COALESCE(t.valor_cashback, 0) AS valor_cashback,
    COALESCE(t.cashback_concedido, 0) AS cashback_concedido,
    
    -- Auditoria
    NOW() AS created_at,
    NOW() AS updated_at
    
FROM transactiondata t
WHERE t.nsuPinbank IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 
      FROM transactiondata_pos tp 
      WHERE tp.gateway = 'PINBANK' 
        AND tp.nsu_gateway = CAST(t.nsuPinbank AS CHAR) COLLATE utf8mb4_unicode_ci
  )
ORDER BY t.id;

-- ============================================================
-- Verificação pós-migração
-- ============================================================

-- 1. Contar registros migrados
SELECT 
    'transactiondata (origem)' AS tabela,
    COUNT(*) AS total
FROM transactiondata
WHERE nsuPinbank IS NOT NULL

UNION ALL

SELECT 
    'transactiondata_pos PINBANK (destino)' AS tabela,
    COUNT(*) AS total
FROM transactiondata_pos
WHERE gateway = 'PINBANK';

-- 2. Verificar registros sem NSU (não migrados)
SELECT COUNT(*) AS sem_nsu
FROM transactiondata
WHERE nsuPinbank IS NULL;

-- 3. Comparar valores (amostra)
SELECT 
    t.id AS id_origem,
    t.nsuPinbank,
    t.valor_original AS valor_origem,
    tp.id AS id_destino,
    tp.valor_original AS valor_destino,
    tp.gateway
FROM transactiondata t
INNER JOIN transactiondata_pos tp 
    ON tp.nsu_gateway = CAST(t.nsuPinbank AS CHAR) COLLATE utf8mb4_unicode_ci
    AND tp.gateway = 'PINBANK'
LIMIT 10;

-- 4. Verificar duplicatas (não deve retornar nada)
SELECT nsu_gateway, COUNT(*) AS duplicatas
FROM transactiondata_pos
WHERE gateway = 'PINBANK'
GROUP BY nsu_gateway
HAVING COUNT(*) > 1;
```

### Migração: `transactiondata_own` → `transactiondata_pos`

```sql
-- ============================================================
-- MIGRAÇÃO: transactiondata_own (Own) → transactiondata_pos
-- ============================================================
-- Migra transações Own da tabela legada para a unificada
-- Gateway: OWN
-- ============================================================

INSERT INTO transactiondata_pos (
    gateway,
    datahora,
    valor_original,
    celular,
    cpf,
    terminal,
    operador_pos,
    nsu_gateway,
    nsuTerminal,
    nsuHost,
    authorizationCode,
    transactionReturn,
    amount,
    originalAmount,
    totalInstallments,
    paymentMethod,
    operationId,
    brand,
    cardNumber,
    cardName,
    hostTimestamp,
    terminalTimestamp,
    sdk,
    customerTicket,
    estabTicket,
    e2ePixId,
    modalidade_wall,
    autorizacao_id,
    valor_desconto,
    valor_cashback,
    cashback_concedido,
    cupom_id,
    cupom_valor_desconto,
    cashback_wall_parametro_id,
    cashback_loja_regra_id,
    created_at,
    updated_at
)
SELECT 
    'OWN' AS gateway,
    
    -- Dados básicos
    t.datahora,
    t.valor_original,
    t.celular,
    t.cpf,
    t.terminal,
    t.operador_pos,
    
    -- Identificadores (txTransactionId vira nsu_gateway)
    t.txTransactionId AS nsu_gateway,
    t.nsuTerminal,
    t.nsuHost,
    t.authorizationCode,
    t.transactionReturn,
    
    -- Valores
    t.amount,
    t.originalAmount,
    COALESCE(t.totalInstallments, 1) AS totalInstallments,
    
    -- Método de pagamento
    t.paymentMethod,
    t.operationId,
    t.brand,
    t.cardNumber,
    t.cardName,
    
    -- Timestamps
    CAST(t.hostTimestamp AS CHAR) AS hostTimestamp,
    t.terminalTimestamp,
    
    -- Específico Own
    t.sdk,
    t.customerTicket,
    t.estabTicket,
    t.e2ePixId,
    
    -- Wall Club (mapeamento Own → Unificado)
    t.modalidade_wall,
    t.autorizacao_uso_saldo_id AS autorizacao_id,
    COALESCE(t.desconto_wall, 0) AS valor_desconto,
    COALESCE(t.cashback_debitado, 0) AS valor_cashback,
    COALESCE(t.cashback_creditado_wall, 0) + COALESCE(t.cashback_creditado_loja, 0) AS cashback_concedido,
    
    -- Cupom
    t.cupom_id,
    t.cupom_valor_desconto,
    
    -- Cashback Centralizado
    t.cashback_wall_parametro_id,
    t.cashback_loja_regra_id,
    
    -- Auditoria
    COALESCE(t.created_at, NOW()) AS created_at,
    COALESCE(t.updated_at, NOW()) AS updated_at
    
FROM transactiondata_own t
WHERE t.txTransactionId IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 
      FROM transactiondata_pos tp 
      WHERE tp.gateway = 'OWN' 
        AND tp.nsu_gateway = t.txTransactionId
  )
ORDER BY t.id;

-- ============================================================
-- Verificação pós-migração
-- ============================================================

-- 1. Contar registros migrados
SELECT 
    'transactiondata_own (origem)' AS tabela,
    COUNT(*) AS total
FROM transactiondata_own
WHERE txTransactionId IS NOT NULL

UNION ALL

SELECT 
    'transactiondata_pos OWN (destino)' AS tabela,
    COUNT(*) AS total
FROM transactiondata_pos
WHERE gateway = 'OWN';

-- 2. Verificar registros sem TxID (não migrados)
SELECT COUNT(*) AS sem_txid
FROM transactiondata_own
WHERE txTransactionId IS NULL;

-- 3. Comparar valores (amostra)
SELECT 
    t.id AS id_origem,
    t.txTransactionId,
    t.valor_original AS valor_origem,
    tp.id AS id_destino,
    tp.valor_original AS valor_destino,
    tp.gateway
FROM transactiondata_own t
INNER JOIN transactiondata_pos tp 
    ON tp.nsu_gateway = t.txTransactionId
    AND tp.gateway = 'OWN'
LIMIT 10;

-- 4. Verificar duplicatas (não deve retornar nada)
SELECT nsu_gateway, COUNT(*) AS duplicatas
FROM transactiondata_pos
WHERE gateway = 'OWN'
GROUP BY nsu_gateway
HAVING COUNT(*) > 1;

-- 5. Verificar totais por gateway
SELECT 
    gateway,
    COUNT(*) AS total,
    MIN(datahora) AS primeira_transacao,
    MAX(datahora) AS ultima_transacao
FROM transactiondata_pos
GROUP BY gateway;
```

### ⚠️ Observações Importantes

1. **Execução Incremental:** Os scripts usam `NOT EXISTS` para evitar duplicatas em execuções múltiplas
2. **NSU como Chave:** 
   - Pinbank: `nsuPinbank` → `nsu_gateway`
   - Own: `txTransactionId` → `nsu_gateway`
3. **Conversão de Tipos:**
   - `datahora` (Pinbank): String → DateTime
   - `nsuTerminal`, `nsuHost`: Integer → String
   - `hostTimestamp`: BigInt → String
4. **Campos Calculados:**
   - `cashback_concedido` (Own): Soma de `cashback_creditado_wall` + `cashback_creditado_loja`
5. **Valores Default:**
   - `totalInstallments`: Default 1 se NULL
   - Campos decimais: COALESCE com 0
6. **Performance:** Executar em horário de baixo tráfego (migração pode ser lenta)

### 📊 Estimativa de Tempo

- **Pinbank:** ~1-2 min por 100k registros
- **Own:** ~1-2 min por 100k registros
- **Recomendação:** Executar em lotes se > 1M registros

---

## 🔔 Trigger de Sincronização Automática

### Trigger: `transactiondata` → `transactiondata_pos` (INSERT)

```sql
-- ============================================================
-- TRIGGER: Sincronização automática transactiondata → transactiondata_pos
-- ============================================================
-- Sempre que inserir em transactiondata, replica para transactiondata_pos
-- Permite coexistência durante migração gradual
-- ============================================================

DELIMITER $$

CREATE TRIGGER trg_transactiondata_insert_sync
AFTER INSERT ON transactiondata
FOR EACH ROW
BEGIN
    DECLARE CONTINUE HANDLER FOR SQLEXCEPTION
    BEGIN
        -- Ignora erros silenciosamente para não travar o INSERT em transactiondata
    END;
    
    -- Inserir na tabela unificada apenas se tiver nsuPinbank
    IF NEW.nsuPinbank IS NOT NULL THEN
        INSERT INTO transactiondata_pos (
            gateway,
            datahora,
            valor_original,
            celular,
            cpf,
            terminal,
            operador_pos,
            nsu_gateway,
            nsuAcquirer,
            nsuTerminal,
            nsuHost,
            authorizationCode,
            amount,
            originalAmount,
            totalInstallments,
            paymentMethod,
            brand,
            cardNumber,
            cardName,
            hostTimestamp,
            terminalTimestamp,
            modalidade_wall,
            autorizacao_id,
            valor_desconto,
            valor_cashback,
            cashback_concedido,
            cupom_id,
            cupom_valor_desconto,
            created_at,
            updated_at
        ) VALUES (
            'PINBANK',
            
            -- Converter datahora (string → datetime)
            STR_TO_DATE(
                SUBSTRING_INDEX(REPLACE(NEW.datahora, 'T', ' '), '.', 1),
                '%Y-%m-%d %H:%i:%s'
            ),
            
            NEW.valor_original,
            NEW.celular,
            NEW.cpf,
            NEW.terminal,
            NEW.operador_pos,
            
            -- Identificadores (converter para string)
            CAST(NEW.nsuPinbank AS CHAR),
            NEW.nsuAcquirer,
            CAST(NEW.nsuTerminal AS CHAR),
            CAST(NEW.nsuHost AS CHAR),
            NEW.authorizationCode,
            
            -- Valores
            NEW.amount,
            NEW.originalAmount,
            COALESCE(NEW.totalInstallments, 1),
            
            -- Método de pagamento
            NEW.paymentMethod,
            NEW.brand,
            NEW.cardNumber,
            NEW.cardName,
            
            -- Timestamps
            CAST(NEW.hostTimestamp AS CHAR),
            NEW.terminalTimestamp,
            
            -- Wall Club
            NEW.modalidade_wall,
            NEW.autorizacao_id,
            COALESCE(NEW.valor_desconto, 0),
            COALESCE(NEW.valor_cashback, 0),
            COALESCE(NEW.cashback_concedido, 0),
            
            -- Cupom
            NEW.cupom_id,
            NEW.cupom_valor_desconto,
            
            -- Auditoria
            NOW(),
            NOW()
        );
    END IF;
END$$

DELIMITER ;
```

### Trigger: `transactiondata` → `transactiondata_pos` (UPDATE)

```sql
-- ============================================================
-- TRIGGER: Sincronização automática transactiondata → transactiondata_pos
-- ============================================================
-- Sempre que atualizar em transactiondata, replica para transactiondata_pos
-- ============================================================

DELIMITER $$

CREATE TRIGGER trg_transactiondata_update_sync
AFTER UPDATE ON transactiondata
FOR EACH ROW
BEGIN
    DECLARE CONTINUE HANDLER FOR SQLEXCEPTION
    BEGIN
        -- Ignora erros silenciosamente para não travar o UPDATE em transactiondata
    END;
    
    -- Atualizar na tabela unificada se existir
    IF NEW.nsuPinbank IS NOT NULL THEN
        UPDATE transactiondata_pos
        SET
            datahora = STR_TO_DATE(
                SUBSTRING_INDEX(REPLACE(NEW.datahora, 'T', ' '), '.', 1),
                '%Y-%m-%d %H:%i:%s'
            ),
            valor_original = NEW.valor_original,
            celular = NEW.celular,
            cpf = NEW.cpf,
            terminal = NEW.terminal,
            operador_pos = NEW.operador_pos,
            nsuAcquirer = NEW.nsuAcquirer,
            nsuTerminal = CAST(NEW.nsuTerminal AS CHAR),
            nsuHost = CAST(NEW.nsuHost AS CHAR),
            authorizationCode = NEW.authorizationCode,
            amount = NEW.amount,
            originalAmount = NEW.originalAmount,
            totalInstallments = COALESCE(NEW.totalInstallments, 1),
            paymentMethod = NEW.paymentMethod,
            brand = NEW.brand,
            cardNumber = NEW.cardNumber,
            cardName = NEW.cardName,
            hostTimestamp = CAST(NEW.hostTimestamp AS CHAR),
            terminalTimestamp = NEW.terminalTimestamp,
            modalidade_wall = NEW.modalidade_wall,
            autorizacao_id = NEW.autorizacao_id,
            valor_desconto = COALESCE(NEW.valor_desconto, 0),
            valor_cashback = COALESCE(NEW.valor_cashback, 0),
            cashback_concedido = COALESCE(NEW.cashback_concedido, 0),
            cupom_id = NEW.cupom_id,
            cupom_valor_desconto = NEW.cupom_valor_desconto,
            updated_at = NOW()
        WHERE gateway = 'PINBANK'
          AND nsu_gateway = CAST(NEW.nsuPinbank AS CHAR) COLLATE utf8mb4_unicode_ci;
    END IF;
END$$

DELIMITER ;
```

### Verificar Triggers Criados

```sql
-- Listar triggers da tabela transactiondata
SHOW TRIGGERS WHERE `Table` = 'transactiondata';

-- Ver definição completa de um trigger
SHOW CREATE TRIGGER trg_transactiondata_insert_sync;
SHOW CREATE TRIGGER trg_transactiondata_update_sync;
```

### Remover Triggers (se necessário)

```sql
DROP TRIGGER IF EXISTS trg_transactiondata_insert_sync;
DROP TRIGGER IF EXISTS trg_transactiondata_update_sync;
```

### ⚠️ Observações Importantes

1. **Performance:** Triggers adicionam overhead em cada INSERT/UPDATE
2. **Fail-Safe:** Triggers usam `DECLARE CONTINUE HANDLER FOR SQLEXCEPTION` - erros na sincronização NÃO travam o processo principal
3. **Validação:** Apenas registros com `nsuPinbank NOT NULL` são sincronizados
4. **Collation:** O UPDATE usa `COLLATE utf8mb4_unicode_ci` para evitar erro de collation mismatch
5. **Conversões:** Mesmas conversões do script de migração (datahora, tipos numéricos → string)
6. **Cupom:** Campos `cupom_id` e `cupom_valor_desconto` incluídos (se existirem na transactiondata)

### 📋 Estratégia de Migração com Triggers

1. ✅ **Criar triggers** (INSERT + UPDATE) - **Concluído em 22/12/2025**
2. ✅ **Migrar dados históricos** (script de migração) - **Concluído em 22/12/2025**
3. ✅ **Novos dados sincronizam automaticamente** via trigger - **Em produção desde 22/12/2025**
4. ⏳ **Adicionar push notification em `TRDataPosService`** - Falta implementar envio de push para cliente
5. ⏳ **Migrar processos de leitura** gradualmente para `transactiondata_pos`
   - Portal Lojista (`views_vendas_operador.py`)
   - APIs de Cupom (`cupom/models.py`, `cupom/services.py`)
6. ⏳ **Virar fluxo de escrita** para `TRDataPosService` (grava direto na nova tabela)
7. ⏳ **Remover triggers** após 100% migrado
8. ⏳ **Deprecar tabela antiga**
