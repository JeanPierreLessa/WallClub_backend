# ROTEIRO DE TESTES - FLUXO TRANSACIONAL COMPLETO

**Versão:** 1.0
**Data:** 07/12/2025
**Objetivo:** Validar integração completa de Cupom + Cashback + Conta Digital
**Status:** 🔄 Pronto para execução

---

## 📋 ÍNDICE

1. [Visão Geral](#visão-geral)
2. [Pré-requisitos](#pré-requisitos)
3. [Cenários de Teste - POS](#cenários-de-teste---pos)
4. [Cenários de Teste - Checkout Web](#cenários-de-teste---checkout-web)
5. [Validações de Integridade](#validações-de-integridade)
6. [Queries de Validação](#queries-de-validação)
7. [Checklist Final](#checklist-final)
8. [Gaps Identificados](#gaps-identificados)

---

## 🎯 VISÃO GERAL

### Fluxo Completo a Validar

```
TRANSAÇÃO
    ↓
1. Desconto Pinbank/Own (calculadora)
2. Desconto Wall (calculadora)
3. Cupom (se informado) ← ÚLTIMO desconto
    ↓
= Valor Final
    ↓
4. Antifraude (analisa valor final)
5. Gateway (processa valor final)
    ↓
6. Cashback Wall (sobre valor final)
7. Cashback Loja (sobre valor final)
    ↓
8. Movimentações na Conta Digital:
   - Se usou saldo: DÉBITO
   - Se usou cashback: DÉBITO cashback_disponivel
   - Cashback concedido: CRÉDITO cashback_bloqueado
```

### Sistemas Envolvidos

| Sistema | Responsabilidade | Status |
|---------|------------------|--------|
| **Cupom** | Validar e aplicar desconto | ✅ Implementado (POS Own) |
| **Cashback** | Calcular e conceder (Wall + Loja) | ✅ Implementado (POS) |
| **Conta Digital** | Registrar movimentações | ✅ Implementado |
| **Autorização POS** | Uso de saldo da conta | ✅ Implementado |

---

## 🔧 PRÉ-REQUISITOS

### 1. Dados de Teste

**Cliente:**
```sql
-- Criar cliente de teste
INSERT INTO cliente (cpf, nome, celular, email, canal_id, ativo)
VALUES ('12345678900', 'Cliente Teste', '11999999999', 'teste@wall.com', 1, 1);

-- Criar conta digital
INSERT INTO conta_digital (cliente_id, canal_id, cpf, saldo_atual, cashback_disponivel, cashback_bloqueado, ativo)
VALUES (
    (SELECT id FROM cliente WHERE cpf = '12345678900'),
    1,
    '12345678900',
    500.00,  -- R$ 500 de saldo
    50.00,   -- R$ 50 de cashback disponível
    0.00,
    1
);
```

**Loja:**
```sql
-- Usar loja existente ou criar
SELECT id, razao_social FROM loja WHERE ativo = 1 LIMIT 1;
```

**Terminal POS:**
```sql
-- Verificar terminal ativo
SELECT serial, loja_id FROM posp2_terminal WHERE ativo = 1 LIMIT 1;
```

### 2. Cupom de Teste

```sql
-- Criar cupom genérico
INSERT INTO cupom (
    codigo, loja_id, tipo_cupom, tipo_desconto, valor_desconto,
    valor_minimo_compra, limite_uso_total, data_inicio, data_fim, ativo
)
VALUES (
    'TESTE10',
    (SELECT id FROM loja WHERE ativo = 1 LIMIT 1),
    'GENERICO',
    'FIXO',
    10.00,
    50.00,  -- Mínimo R$ 50
    100,    -- 100 usos
    NOW(),
    DATE_ADD(NOW(), INTERVAL 30 DAY),
    1
);
```

### 3. Regra Cashback Loja

```sql
-- Criar regra cashback loja
INSERT INTO cashback_regra_loja (
    loja_id, nome, descricao, ativo, prioridade,
    tipo_concessao, valor_concessao,
    valor_minimo_compra, vigencia_inicio, vigencia_fim
)
VALUES (
    (SELECT id FROM loja WHERE ativo = 1 LIMIT 1),
    'Cashback Teste 5%',
    'Regra de teste',
    1,
    10,
    'PERCENTUAL',
    5.00,  -- 5%
    0.00,
    NOW(),
    DATE_ADD(NOW(), INTERVAL 30 DAY)
);
```

### 4. Verificar Configurações

```sql
-- Tipos de movimentação cadastrados
SELECT codigo, nome, debita_saldo, afeta_cashback
FROM conta_digital_tipos_movimentacao;

-- Deve ter pelo menos:
-- CASHBACK_WALL, CASHBACK_LOJA, DEBITO, CASHBACK_DEBITO

-- Configurações de canal
SELECT * FROM conta_digital_configuracoes WHERE canal_id = 1;

-- Parâmetros Wall com cashback
SELECT id, wall, percentual_desconto
FROM parametros_wallclub
WHERE wall = 'C' AND ativo = 1
LIMIT 1;
```

---

## 🧪 CENÁRIOS DE TESTE - POS

### Cenário 1: Transação Simples (sem cupom, com cashback)

**Objetivo:** Validar concessão de cashback Wall + Loja

**Payload:**
```json
{
  "cpf": "12345678900",
  "terminal": "PBF923BH70797",
  "valororiginal": "100.00",
  "modalidade": "PIX",
  "trdata": "{...}"
}
```

**Validações:**

1. **Simulação (`/simula_parcelas_v2/`):**
```bash
curl -X POST http://localhost:8006/api/v1/posp2/simula_parcelas_v2/ \
  -H "Content-Type: application/json" \
  -d '{
    "valor": 100.00,
    "terminal": "PBF923BH70797",
    "wall": "s",
    "cliente_id": 123
  }'
```

Espera-se:
```json
{
  "sucesso": true,
  "dados": {
    "parcelas": {
      "PIX": {
        "valor_original": "100.00",
        "valor_total": "85.00",
        "desconto_wall": "15.00",
        "cashback_wall": {"valor": "0.00"},
        "cashback_loja": {
          "aplicavel": true,
          "valor": "4.25",
          "regra_id": 1
        },
        "cashback_total": "4.25"
      }
    }
  }
}
```

2. **Transação (`/trdata_own/`):**
```bash
# Processar transação com IDs da simulação
```

3. **Validar Banco:**
```sql
-- 1. Transação criada
SELECT * FROM transactiondata_own
WHERE cpf = '12345678900'
ORDER BY created_at DESC LIMIT 1;

-- Verificar:
-- cashback_creditado_wall = 0.00
-- cashback_creditado_loja = 4.25

-- 2. Cashback registrado
SELECT * FROM cashback_uso
WHERE cliente_id = (SELECT id FROM cliente WHERE cpf = '12345678900')
ORDER BY aplicado_em DESC LIMIT 2;

-- Deve ter 2 registros:
-- tipo_origem = 'LOJA', valor_cashback = 4.25, status = 'RETIDO'

-- 3. Movimentações na conta
SELECT m.*, t.codigo as tipo
FROM conta_digital_movimentacoes m
JOIN conta_digital_tipos_movimentacao t ON m.tipo_movimentacao_id = t.id
WHERE conta_digital_id = (
    SELECT id FROM conta_digital WHERE cpf = '12345678900'
)
ORDER BY data_movimentacao DESC LIMIT 2;

-- Deve ter:
-- CASHBACK_LOJA: +4.25 (afeta cashback_bloqueado)

-- 4. Saldo da conta
SELECT cashback_bloqueado, cashback_disponivel
FROM conta_digital
WHERE cpf = '12345678900';

-- cashback_bloqueado deve ter aumentado 4.25
```

---

### Cenário 2: Transação com Cupom

**Objetivo:** Validar aplicação de cupom + cashback

**Payload:**
```json
{
  "cpf": "12345678900",
  "terminal": "PBF923BH70797",
  "valororiginal": "100.00",
  "modalidade": "PIX",
  "cupom_codigo": "TESTE10",
  "cupom_valor_desconto": 10.00,
  "trdata": "{...}"
}
```

**Validações:**

1. **Transação criada:**
```sql
SELECT * FROM transactiondata_own
WHERE cpf = '12345678900'
ORDER BY created_at DESC LIMIT 1;

-- Verificar:
-- cupom_id = (ID do cupom TESTE10)
-- cupom_valor_desconto = 10.00
-- cashback calculado sobre valor APÓS cupom
```

2. **Cupom usado:**
```sql
SELECT * FROM cupom_uso
WHERE cupom_id = (SELECT id FROM cupom WHERE codigo = 'TESTE10')
ORDER BY usado_em DESC LIMIT 1;

-- Verificar:
-- cliente_id correto
-- valor_desconto_aplicado = 10.00
-- transacao_tipo = 'POS'
-- estornado = 0
```

3. **Cupom contador atualizado:**
```sql
SELECT quantidade_usada FROM cupom WHERE codigo = 'TESTE10';
-- Deve ter incrementado +1
```

4. **Cashback sobre valor com desconto:**
```sql
-- Se valor original = 100, desconto wall = 15, cupom = 10
-- Valor final = 75
-- Cashback loja 5% = 3.75

SELECT valor_cashback FROM cashback_uso
WHERE tipo_origem = 'LOJA'
AND cliente_id = (SELECT id FROM cliente WHERE cpf = '12345678900')
ORDER BY aplicado_em DESC LIMIT 1;

-- Deve ser 3.75 (5% de 75)
```

---

### Cenário 3: Uso de Saldo da Conta

**Objetivo:** Validar débito de saldo via autorização

**Fluxo:**

1. **Consultar saldo:**
```bash
curl -X POST http://localhost:8006/api/v1/posp2/consultar_saldo/ \
  -H "Authorization: Bearer {oauth_token}" \
  -d '{
    "cpf": "12345678900",
    "senha": "1234"
  }'
```

2. **Solicitar autorização:**
```bash
curl -X POST http://localhost:8006/api/v1/posp2/solicitar_autorizacao/ \
  -d '{
    "cpf": "12345678900",
    "valor": 50.00,
    "terminal": "PBF923BH70797"
  }'
```

3. **Cliente aprova no app** (simular via API interna)

4. **Processar transação com autorização:**
```json
{
  "cpf": "12345678900",
  "terminal": "PBF923BH70797",
  "valororiginal": "50.00",
  "autorizacao_id": "AUTH123456",
  "trdata": "{...}"
}
```

**Validações:**

```sql
-- 1. Autorização concluída
SELECT * FROM conta_digital_autorizacao_uso_saldo
WHERE autorizacao_id = 'AUTH123456';

-- status = 'CONCLUIDA'

-- 2. Saldo debitado
SELECT m.*, t.codigo
FROM conta_digital_movimentacoes m
JOIN conta_digital_tipos_movimentacao t ON m.tipo_movimentacao_id = t.id
WHERE conta_digital_id = (SELECT id FROM conta_digital WHERE cpf = '12345678900')
AND t.codigo = 'DEBITO'
ORDER BY data_movimentacao DESC LIMIT 1;

-- valor = 50.00
-- referencia_externa = NSU da transação

-- 3. Saldo atualizado
SELECT saldo_atual, saldo_bloqueado
FROM conta_digital
WHERE cpf = '12345678900';

-- saldo_atual deve ter diminuído 50.00
-- saldo_bloqueado deve ter voltado a 0
```

---

### Cenário 4: Uso de Cashback

**Objetivo:** Validar débito de cashback disponível

**Pré-condição:** Cliente tem cashback_disponivel > 0

**Payload:**
```json
{
  "cpf": "12345678900",
  "terminal": "PBF923BH70797",
  "valororiginal": "100.00",
  "usar_cashback": true,
  "valor_cashback_usado": 20.00,
  "trdata": "{...}"
}
```

**Validações:**

```sql
-- 1. Cashback debitado
SELECT m.*, t.codigo
FROM conta_digital_movimentacoes m
JOIN conta_digital_tipos_movimentacao t ON m.tipo_movimentacao_id = t.id
WHERE conta_digital_id = (SELECT id FROM conta_digital WHERE cpf = '12345678900')
AND t.codigo = 'CASHBACK_DEBITO'
ORDER BY data_movimentacao DESC LIMIT 1;

-- valor = 20.00

-- 2. Saldo cashback atualizado
SELECT cashback_disponivel
FROM conta_digital
WHERE cpf = '12345678900';

-- Deve ter diminuído 20.00

-- 3. Novo cashback concedido sobre valor líquido
-- Se valor original = 100, cashback usado = 20
-- Valor pago pelo cliente = 80
-- Cashback 5% = 4.00 (sobre 80, não sobre 100)
```

---

### Cenário 5: Estorno de Transação

**Objetivo:** Validar estorno de cupom e cashback

**Fluxo:**

1. **Processar transação normal** (Cenário 2)
2. **Estornar transação**

**Validações:**

```sql
-- 1. Cupom marcado como estornado
SELECT estornado FROM cupom_uso
WHERE transacao_id = {transaction_id}
AND transacao_tipo = 'POS';

-- estornado = 1

-- 2. Cupom NÃO retorna (quantidade_usada não decrementa)
SELECT quantidade_usada FROM cupom WHERE codigo = 'TESTE10';
-- Mantém o valor (prevenção fraude)

-- 3. Cashback estornado
SELECT status FROM cashback_uso
WHERE transacao_tipo = 'POS'
AND transacao_id = {transaction_id};

-- status = 'ESTORNADO'

-- 4. Saldo cashback ajustado
-- Se cashback estava RETIDO: remove de cashback_bloqueado
-- Se cashback estava LIBERADO: debita de cashback_disponivel
```

---

## 🌐 CENÁRIOS DE TESTE - CHECKOUT WEB

### Cenário 6: Checkout Simples (sem cupom)

**Objetivo:** Validar fluxo checkout básico

**Status:** ⚠️ **Cupom não implementado no Checkout**

**Fluxo:**

1. Portal Vendas cria `CheckoutTransaction` (status PENDENTE)
2. Cliente acessa link de pagamento
3. Cliente valida OTP WhatsApp
4. Cliente preenche dados do cartão
5. Sistema processa pagamento

**Validações:**

```sql
-- 1. Transação criada
SELECT * FROM checkoutTransaction
WHERE cpf = '12345678900'
ORDER BY created_at DESC LIMIT 1;

-- 2. Cashback concedido (se aplicável)
SELECT * FROM cashback_uso
WHERE transacao_tipo = 'CHECKOUT'
AND transacao_id = {checkout_id};

-- 3. Movimentações na conta
SELECT * FROM conta_digital_movimentacoes
WHERE referencia_externa LIKE '%CHECKOUT%'
ORDER BY data_movimentacao DESC;
```

---

### Cenário 7: Checkout com Cupom

**Status:** ❌ **NÃO IMPLEMENTADO**

**Pendências:**
- Adicionar campos `cupom_id` e `cupom_valor_desconto` em `CheckoutTransaction`
- Integrar `CupomService` no `LinkPagamentoTransactionService`
- Adicionar campo cupom no formulário HTML
- Validação AJAX do cupom

---

## ✅ VALIDAÇÕES DE INTEGRIDADE

### 1. Estrutura de Dados

```sql
-- Verificar tabelas existem
SHOW TABLES LIKE 'cupom%';
SHOW TABLES LIKE 'cashback%';
SHOW TABLES LIKE 'conta_digital%';

-- Verificar índices
SHOW INDEX FROM cupom;
SHOW INDEX FROM cashback_uso;
SHOW INDEX FROM conta_digital_movimentacoes;
```

### 2. Tipos de Movimentação Cadastrados

```sql
SELECT codigo, nome, debita_saldo, afeta_cashback, visivel_extrato
FROM conta_digital_tipos_movimentacao
ORDER BY codigo;

-- Obrigatórios:
-- CREDITO, DEBITO
-- CASHBACK_WALL, CASHBACK_LOJA
-- CASHBACK_CREDITO, CASHBACK_DEBITO
-- CASHBACK_EXPIRACAO, CASHBACK_ESTORNO
-- ESTORNO, BLOQUEIO, DESBLOQUEIO
```

### 3. Configurações de Canal

```sql
SELECT
    canal_id,
    limite_diario_padrao,
    limite_mensal_padrao,
    periodo_retencao_cashback_dias,
    auto_criar_conta
FROM conta_digital_configuracoes;

-- Deve ter configuração para cada canal ativo
```

### 4. Consistência de Saldos

```sql
-- Verificar saldos não negativos (se não permitido)
SELECT id, cpf, saldo_atual, cashback_disponivel, cashback_bloqueado
FROM conta_digital
WHERE saldo_atual < 0 OR cashback_disponivel < 0 OR cashback_bloqueado < 0;

-- Não deve retornar nada (ou apenas contas com permite_saldo_negativo=1)
```

### 5. Movimentações Órfãs

```sql
-- Movimentações sem conta digital
SELECT m.id, m.conta_digital_id
FROM conta_digital_movimentacoes m
LEFT JOIN conta_digital c ON m.conta_digital_id = c.id
WHERE c.id IS NULL;

-- Não deve retornar nada

-- Movimentações sem tipo
SELECT m.id, m.tipo_movimentacao_id
FROM conta_digital_movimentacoes m
LEFT JOIN conta_digital_tipos_movimentacao t ON m.tipo_movimentacao_id = t.id
WHERE t.id IS NULL;

-- Não deve retornar nada
```

### 6. Cashback Retido vs Saldo Bloqueado

```sql
-- Total cashback retido deve bater com saldo bloqueado
SELECT
    c.cpf,
    c.cashback_bloqueado as saldo_bloqueado,
    COALESCE(SUM(cu.valor_cashback), 0) as total_retido
FROM conta_digital c
LEFT JOIN cashback_uso cu ON cu.cliente_id = c.cliente_id
    AND cu.canal_id = c.canal_id
    AND cu.status = 'RETIDO'
GROUP BY c.id, c.cpf, c.cashback_bloqueado
HAVING ABS(c.cashback_bloqueado - total_retido) > 0.01;

-- Não deve retornar nada (ou diferença < R$ 0,01)
```

### 7. Cupons Usados vs Contador

```sql
-- Quantidade usada deve bater com registros
SELECT
    c.codigo,
    c.quantidade_usada as contador,
    COUNT(cu.id) as usos_registrados
FROM cupom c
LEFT JOIN cupom_uso cu ON cu.cupom_id = c.id
GROUP BY c.id, c.codigo, c.quantidade_usada
HAVING c.quantidade_usada != COUNT(cu.id);

-- Não deve retornar nada
```

---

## 📊 QUERIES DE VALIDAÇÃO

### Query 1: Resumo Conta Digital por Cliente

```sql
SELECT
    c.cpf,
    c.nome,
    cd.saldo_atual,
    cd.cashback_disponivel,
    cd.cashback_bloqueado,
    cd.limite_diario,
    cd.limite_mensal,
    cd.ativo,
    cd.bloqueado
FROM cliente c
JOIN conta_digital cd ON cd.cliente_id = c.id
WHERE c.cpf = '12345678900';
```

### Query 2: Histórico de Movimentações

```sql
SELECT
    m.data_movimentacao,
    t.codigo as tipo,
    t.nome as tipo_nome,
    m.valor,
    m.saldo_anterior,
    m.saldo_posterior,
    m.descricao,
    m.referencia_externa,
    m.sistema_origem,
    m.status
FROM conta_digital_movimentacoes m
JOIN conta_digital_tipos_movimentacao t ON m.tipo_movimentacao_id = t.id
WHERE m.conta_digital_id = (
    SELECT id FROM conta_digital WHERE cpf = '12345678900'
)
ORDER BY m.data_movimentacao DESC
LIMIT 20;
```

### Query 3: Cashback Concedido (Wall + Loja)

```sql
SELECT
    cu.aplicado_em,
    cu.tipo_origem,
    cu.valor_transacao,
    cu.valor_cashback,
    cu.status,
    cu.liberado_em,
    cu.expira_em,
    l.razao_social as loja,
    CASE cu.transacao_tipo
        WHEN 'POS' THEN CONCAT('POS-', cu.transacao_id)
        WHEN 'CHECKOUT' THEN CONCAT('CHECKOUT-', cu.transacao_id)
    END as transacao
FROM cashback_uso cu
JOIN loja l ON l.id = cu.loja_id
WHERE cu.cliente_id = (SELECT id FROM cliente WHERE cpf = '12345678900')
ORDER BY cu.aplicado_em DESC
LIMIT 20;
```

### Query 4: Cupons Usados

```sql
SELECT
    cu.usado_em,
    c.codigo as cupom,
    c.tipo_desconto,
    c.valor_desconto,
    cu.valor_transacao_original,
    cu.valor_desconto_aplicado,
    cu.valor_transacao_final,
    cu.estornado,
    l.razao_social as loja,
    cu.nsu
FROM cupom_uso cu
JOIN cupom c ON c.id = cu.cupom_id
JOIN loja l ON l.id = cu.loja_id
WHERE cu.cliente_id = (SELECT id FROM cliente WHERE cpf = '12345678900')
ORDER BY cu.usado_em DESC;
```

### Query 5: Autorizações de Uso de Saldo

```sql
SELECT
    a.autorizacao_id,
    a.valor,
    a.status,
    a.criado_em,
    a.aprovado_em,
    a.expirado_em,
    a.concluido_em,
    a.terminal,
    a.ip_address
FROM conta_digital_autorizacao_uso_saldo a
WHERE a.cliente_id = (SELECT id FROM cliente WHERE cpf = '12345678900')
ORDER BY a.criado_em DESC
LIMIT 10;
```

### Query 6: Transações POS do Cliente

```sql
-- Own
SELECT
    t.created_at,
    t.nsu,
    t.valor_original,
    t.valor_liquido,
    t.desconto_wall,
    t.cupom_valor_desconto,
    t.cashback_creditado_wall,
    t.cashback_creditado_loja,
    t.cashback_debitado,
    t.saldo_debitado,
    t.status,
    l.razao_social as loja
FROM transactiondata_own t
JOIN loja l ON l.id = t.loja_id
WHERE t.cpf = '12345678900'
ORDER BY t.created_at DESC
LIMIT 10;

-- Pinbank (se implementado)
SELECT
    t.created_at,
    t.nsu,
    t.valor_original,
    t.valor_liquido,
    t.status,
    l.razao_social as loja
FROM transactiondata t
JOIN loja l ON l.id = t.loja_id
WHERE t.cpf = '12345678900'
ORDER BY t.created_at DESC
LIMIT 10;
```

### Query 7: Dashboard Resumo

```sql
SELECT
    -- Conta Digital
    (SELECT COUNT(*) FROM conta_digital WHERE ativo = 1) as contas_ativas,
    (SELECT SUM(saldo_atual) FROM conta_digital WHERE ativo = 1) as saldo_total,
    (SELECT SUM(cashback_disponivel) FROM conta_digital WHERE ativo = 1) as cashback_disponivel_total,
    (SELECT SUM(cashback_bloqueado) FROM conta_digital WHERE ativo = 1) as cashback_bloqueado_total,

    -- Cashback
    (SELECT COUNT(*) FROM cashback_uso WHERE status = 'RETIDO') as cashback_retido_qtd,
    (SELECT SUM(valor_cashback) FROM cashback_uso WHERE status = 'RETIDO') as cashback_retido_valor,
    (SELECT COUNT(*) FROM cashback_uso WHERE status = 'LIBERADO') as cashback_liberado_qtd,
    (SELECT SUM(valor_cashback) FROM cashback_uso WHERE status = 'LIBERADO') as cashback_liberado_valor,

    -- Cupons
    (SELECT COUNT(*) FROM cupom WHERE ativo = 1) as cupons_ativos,
    (SELECT COUNT(*) FROM cupom_uso WHERE DATE(usado_em) = CURDATE()) as cupons_usados_hoje,
    (SELECT SUM(valor_desconto_aplicado) FROM cupom_uso WHERE DATE(usado_em) = CURDATE()) as desconto_cupons_hoje,

    -- Movimentações
    (SELECT COUNT(*) FROM conta_digital_movimentacoes WHERE DATE(data_movimentacao) = CURDATE()) as movimentacoes_hoje;
```

---

## ✅ CHECKLIST FINAL

### Estrutura Base

- [X] Tabelas criadas (cupom, cashback_*, conta_digital_*)
- [X] Índices criados
- [X] Tipos de movimentação cadastrados (14 tipos)
- [X] Configurações de canal criadas
- [X] Foreign keys configuradas

### Funcionalidades - POS

- [X] Simulação retorna cashback Wall + Loja
- [X] Transação aplica cupom corretamente
- [X] Cashback Wall creditado e registrado
- [X] Cashback Loja creditado e registrado
- [ ] Cupom usado e contador incrementado
- [ ] Saldo debitado quando usa autorização
- [ ] Cashback debitado quando usa cashback
- [ ] Movimentações criadas corretamente

### Funcionalidades - Checkout

- [ ] Transação básica funciona
- [ ] Cashback concedido (se aplicável)
- [ ] ❌ Cupom não implementado

### Validações

- [ ] Saldos não negativos (ou permitido)
- [ ] Cashback retido = saldo bloqueado
- [ ] Cupons usados = contador
- [ ] Movimentações sem órfãs
- [ ] Tipos de movimentação corretos

### Jobs Celery

- [ ] ❌ Liberação cashback não implementada
- [ ] ❌ Expiração cashback não implementada
- [ ] ✅ Expiração autorizações implementada

### Estornos

- [ ] Cupom marcado como estornado
- [ ] Cupom NÃO retorna (contador mantém)
- [ ] Cashback estornado corretamente
- [ ] Saldo ajustado

---

## 🚨 GAPS IDENTIFICADOS

### CRÍTICO

1. **Jobs Celery não implementados**
   - Liberação automática de cashback retido
   - Expiração automática de cashback vencido
   - **Impacto:** Cashback fica retido indefinidamente
   - **Ação:** Implementar tasks em `apps/cashback/tasks.py`

2. **Tipos de movimentação não cadastrados**
   - Tabela `conta_digital_tipos_movimentacao` pode estar vazia
   - **Impacto:** Nenhum lançamento funciona
   - **Ação:** Executar seed obrigatório

3. **Configurações de canal não criadas**
   - Tabela `conta_digital_configuracoes` pode estar vazia
   - **Impacto:** Usa valores padrão hardcoded
   - **Ação:** Criar configuração para cada canal

### ALTO

4. **Validação de limites não implementada**
   - `limite_diario` e `limite_mensal` não são validados
   - **Impacto:** Cliente pode movimentar valores ilimitados
   - **Ação:** Implementar validação em `ContaDigitalService`

5. **Cupom não implementado no Checkout Web**
   - Apenas POS Own tem cupom
   - **Impacto:** Checkout não pode usar cupons
   - **Ação:** Integrar `CupomService` no checkout

6. **Cashback POS legado não usa CashbackUso**
   - `posp2/services_conta_digital.py` não registra em `cashback_uso`
   - **Impacto:** Histórico incompleto, liberação/expiração não funciona
   - **Ação:** Migrar para `CashbackService.aplicar_cashback_wall()`

### MÉDIO

7. **Estorno de cashback pode gerar saldo negativo**
   - Se cashback já foi usado, estorno cria saldo negativo
   - **Impacto:** Inconsistência contábil
   - **Ação:** Validar saldo antes de estornar

8. **Falta dashboard admin**
   - Não há interface para visualizar movimentações
   - **Impacto:** Dificuldade de suporte
   - **Ação:** Criar dashboard em `admin.py`

9. **Registro de compras não implementado**
   - Compras não aparecem no extrato da conta digital
   - **Impacto:** Cliente não vê histórico completo
   - **Ação:** Implementar tipo `COMPRA_CARTAO` informativo

### BAIXO

10. **Falta testes automatizados**
    - Não há testes unitários
    - **Impacto:** Risco de regressão
    - **Ação:** Criar suite de testes

11. **Documentação de APIs incompleta**
    - Falta documentação Swagger/OpenAPI
    - **Impacto:** Dificuldade de integração
    - **Ação:** Adicionar docstrings e schema

---

## 📋 PLANO DE AÇÃO

### Fase 1: CRÍTICO (Imediato)

1. **Criar seed de tipos de movimentação**
   ```bash
   python manage.py seed_tipos_movimentacao
   ```

2. **Criar configurações de canal**
   ```bash
   python manage.py seed_configuracoes_canal
   ```

3. **Implementar jobs Celery**
   - `liberar_cashback_retido_automatico()` - diário 02:00
   - `expirar_cashback_vencido()` - diário 03:00

### Fase 2: ALTO (Curto Prazo)

4. **Implementar validação de limites**
   - Método `_validar_limites()` em `ContaDigitalService`
   - Chamar em `debitar()` e `usar_cashback()`

5. **Integrar cupom no Checkout Web**
   - Adicionar campos em `CheckoutTransaction`
   - Integrar `CupomService` no fluxo
   - Adicionar campo no formulário HTML

6. **Migrar cashback POS legado**
   - Usar `CashbackService.aplicar_cashback_wall()` em vez de código legado

### Fase 3: MÉDIO (Médio Prazo)

7. **Validar saldo em estorno de cashback**
8. **Criar dashboard admin**
9. **Implementar registro de compras informativas**

### Fase 4: BAIXO (Longo Prazo)

10. **Criar testes automatizados**
11. **Documentação de APIs**

---

## 📝 OBSERVAÇÕES

### Ordem de Execução dos Testes

1. Executar **Pré-requisitos** primeiro
2. Testar **Cenários POS** (1 a 5) em ordem
3. Testar **Cenários Checkout** (6 a 7)
4. Executar **Validações de Integridade**
5. Executar **Queries de Validação**
6. Preencher **Checklist Final**

### Ambiente de Teste

- **Desenvolvimento:** `docker-compose -f docker-compose.yml -f docker-compose.dev.yml up`
- **Produção:** Criar dados de teste em ambiente isolado

### Logs

Monitorar logs durante testes:
```bash
docker logs wallclub-apis --tail 100 -f
docker logs wallclub-pos --tail 100 -f
```

### Rollback

Se encontrar problemas críticos:
1. Anotar o gap identificado
2. Não prosseguir com testes dependentes
3. Reportar para correção imediata

---

**Responsável:** Equipe Técnica WallClub
**Próxima Atualização:** Após execução dos testes
**Status:** 🔄 Aguardando execução
