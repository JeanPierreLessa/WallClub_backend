# Cashback e Desconto - WallClub

**Versão:** 1.0
**Data:** 06/03/2026
**Objetivo:** Documentar os sistemas de cashback e desconto do WallClub

---

## 📊 Visão Geral

O WallClub possui dois sistemas independentes que beneficiam o cliente:

1. **Desconto Wall:** Redução no valor da compra (aplicado na hora)
2. **Cashback:** Crédito futuro na conta digital (aplicado após a compra)

---

## 💰 Sistema de Cashback

### Conceito

Cashback é um **crédito futuro** concedido ao cliente após uma compra aprovada. O valor fica disponível na conta digital para uso em compras futuras.

### Tipos de Cashback

#### 1. Cashback Wall
- **Origem:** Configurado em `parametros_wallclub`
- **Quem paga:** WallClub
- **Tabela:** `parametros_wallclub` (campos `parametro_uptal_5`, `parametro_uptal_6`)
- **Regra:** Percentual fixo sobre o valor da transação

#### 2. Cashback Loja
- **Origem:** Configurado pela própria loja
- **Quem paga:** Loja
- **Tabela:** `cashback_regra_loja`
- **Regras:** Flexíveis (fixo, percentual, condições, vigência)

### Fluxo de Concessão

```
Compra Aprovada (POS/Checkout)
  ↓
Calcular cashback (Wall + Loja)
  ↓
Creditar na conta digital
  ↓
Status: PENDENTE (se houver período de carência)
  ↓
Status: DISPONIVEL (após liberação)
```

### Tabelas Envolvidas

#### `cashback_regra_loja` (Concessão Loja)
Define quanto cashback a loja dá ao cliente.

**Campos principais:**
- `tipo_concessao`: 'FIXO' ou 'PERCENTUAL'
- `valor_concessao`: Valor ou percentual a conceder
- `valor_minimo_compra`: Compra mínima para ganhar cashback
- `valor_maximo_cashback`: Limite máximo por transação
- `vigencia_inicio` / `vigencia_fim`: Período de validade
- `formas_pagamento`: Filtro por forma de pagamento
- `ativo`: Se a regra está ativa

**Exemplo:**
```sql
-- Loja dá 5% de cashback em compras acima de R$ 10
tipo_concessao = 'PERCENTUAL'
valor_concessao = 5.00
valor_minimo_compra = 10.00
```

#### `conta_digital_cashback_param_loja` (Uso)
Define quanto cashback o cliente pode **usar** como pagamento.

**Campos principais:**
- `loja_id`: ID da loja
- `processo_venda`: 'POS' ou 'ECOMMERCE'
- `percentual_utilizacao`: **% máximo da compra que pode ser pago com cashback**
- `percentual_concessao`: (não usado para uso)

**Exemplo:**
```sql
-- Cliente pode usar até 5% do valor da compra em cashback
loja_id = 26
processo_venda = 'POS'
percentual_utilizacao = 5.00
```

**Cálculo:**
- Compra: R$ 10,00
- Cashback disponível: R$ 25,48
- Percentual permitido: 5%
- **Pode usar:** R$ 0,50 (5% de R$ 10,00)

#### `cashback_uso` (Registro de Uso)
Registra cada concessão de cashback ao cliente.

**Campos principais:**
- `cliente_id`: ID do cliente
- `loja_id`: Loja que concedeu
- `canal_id`: Canal
- `tipo`: 'WALL' ou 'LOJA'
- `valor`: Valor do cashback
- `status`: 'PENDENTE', 'DISPONIVEL', 'USADO', 'EXPIRADO'
- `data_liberacao`: Quando fica disponível para uso
- `data_expiracao`: Validade do cashback
- `transacao_tipo`: 'POS', 'CHECKOUT', 'MANUAL'
- `transacao_id`: NSU ou ID da transação origem
- `parametro_wall_id`: Se cashback Wall
- `regra_loja_id`: Se cashback Loja

### Regras de Uso

1. **Limite por transação:** Definido em `percentual_utilizacao` da tabela `conta_digital_cashback_param_loja`
2. **Saldo disponível:** Apenas cashback com `status = 'DISPONIVEL'`
3. **Autorização:** Cliente deve aprovar uso via app (push notification)
4. **Validade:** Token de autorização expira em 5 minutos
5. **Segurança:** Token HMAC-SHA256 valida valor, CPF e terminal

### Fluxo de Uso (POS)

```
1. POS: consultar_saldo_cashback
   ↓
2. API calcula valor_maximo_permitido
   ↓
3. API gera validation_token (5 min)
   ↓
4. POS: solicitar_autorizacao_saldo
   ↓
5. Push notification para cliente
   ↓
6. Cliente aprova no app
   ↓
7. POS: verificar_autorizacao (polling)
   ↓
8. POS: debitar_saldo_transacao
   ↓
9. Movimentação na conta digital
```

---

## 🎁 Sistema de Desconto Wall

### Conceito

Desconto Wall é uma **redução imediata** no valor da compra, aplicada no momento da transação. O cliente paga menos na hora.

### Origem

- **Tabela:** `parametros_wallclub`
- **Campo:** `parametro_loja_31` (desconto Wall em R$)
- **Quem paga:** WallClub

### Aplicação

O desconto é aplicado automaticamente nas calculadoras:
- `CalculadoraBaseUnificada` (POS)
- `CalculadoraBaseCredenciadora` (Credenciadora)
- `CalculadoraCheckout` (Checkout Web)

**Exemplo de cálculo:**
```python
# var42 = var26 - var37 - var41 - parametro_loja_31
valor_final = valor_bruto - taxas - encargos - desconto_wall
```

### Diferença: Desconto vs Cashback

| Característica | Desconto Wall | Cashback |
|----------------|---------------|----------|
| **Quando aplica** | Na hora (reduz valor a pagar) | Depois (crédito futuro) |
| **Impacto imediato** | Sim (cliente paga menos) | Não (cliente paga valor cheio) |
| **Uso futuro** | Não | Sim (em próximas compras) |
| **Tabela** | `parametros_wallclub` | `cashback_regra_loja` + `cashback_uso` |
| **Campo** | `parametro_loja_31` | `valor_concessao` |
| **Tipo** | Sempre em R$ fixo | Fixo ou Percentual |
| **Quem paga** | WallClub | WallClub ou Loja |

---

## 🔄 Combinação: Desconto + Cashback

Uma transação pode ter **ambos** aplicados:

**Exemplo:**
- Valor original: R$ 100,00
- Desconto Wall: R$ 5,00 (`parametro_loja_31`)
- **Cliente paga:** R$ 95,00
- Cashback Wall: 2% de R$ 100,00 = R$ 2,00
- Cashback Loja: 3% de R$ 100,00 = R$ 3,00
- **Cliente recebe:** R$ 5,00 de cashback (disponível em 30 dias)

**Benefício total:** R$ 10,00 (R$ 5 imediato + R$ 5 futuro)

---

## 📋 Tabelas de Referência

### Concessão de Cashback

| Tabela | Tipo | Campos Principais |
|--------|------|-------------------|
| `parametros_wallclub` | Cashback Wall | `parametro_uptal_5`, `parametro_uptal_6` |
| `cashback_regra_loja` | Cashback Loja | `tipo_concessao`, `valor_concessao`, `ativo` |

### Uso de Cashback

| Tabela | Propósito | Campos Principais |
|--------|-----------|-------------------|
| `conta_digital_cashback_param_loja` | Limite de uso | `percentual_utilizacao`, `processo_venda` |
| `cashback_uso` | Registro de concessão | `valor`, `status`, `data_liberacao` |
| `conta_digital_autorizacao` | Autorização de uso | `valor`, `status`, `validation_token` |

### Desconto

| Tabela | Campo | Descrição |
|--------|-------|-----------|
| `parametros_wallclub` | `parametro_loja_31` | Desconto Wall em R$ |

---

## 🔍 Queries Úteis

### Verificar configuração de cashback de uma loja

```sql
-- Concessão (quanto dar)
SELECT * FROM cashback_regra_loja
WHERE loja_id = 26 AND ativo = 1;

-- Uso (quanto pode usar)
SELECT * FROM conta_digital_cashback_param_loja
WHERE loja_id = 26 AND processo_venda = 'POS';

-- Desconto Wall
SELECT parametro_loja_31 FROM parametros_wallclub
WHERE loja_id = 26 AND wall = 's'
ORDER BY data_referencia DESC LIMIT 1;
```

### Verificar cashback de um cliente

```sql
SELECT
    cu.id,
    cu.tipo,
    cu.valor,
    cu.status,
    cu.data_liberacao,
    cu.data_expiracao,
    cu.transacao_tipo,
    cu.transacao_id
FROM cashback_uso cu
JOIN apps_cliente c ON cu.cliente_id = c.id
WHERE c.cpf = '17653377807'
  AND cu.status = 'DISPONIVEL'
ORDER BY cu.created_at DESC;
```

### Verificar saldo total de cashback

```sql
SELECT
    c.cpf,
    c.nome,
    SUM(CASE WHEN cu.status = 'DISPONIVEL' THEN cu.valor ELSE 0 END) AS cashback_disponivel,
    SUM(CASE WHEN cu.status = 'PENDENTE' THEN cu.valor ELSE 0 END) AS cashback_pendente,
    SUM(CASE WHEN cu.status = 'USADO' THEN cu.valor ELSE 0 END) AS cashback_usado
FROM apps_cliente c
LEFT JOIN cashback_uso cu ON c.id = cu.cliente_id
WHERE c.cpf = '17653377807'
GROUP BY c.id, c.cpf, c.nome;
```

---

## ⚠️ Pontos de Atenção

### Cashback

1. **Configuração obrigatória:** Loja precisa ter registro em `conta_digital_cashback_param_loja` para permitir uso
2. **Percentual de uso:** Limite é sobre o **valor da compra**, não sobre o saldo disponível
3. **Autorização:** Uso de cashback sempre requer aprovação do cliente via app
4. **Expiração:** Token de validação expira em 5 minutos
5. **Status:** Apenas cashback com `status = 'DISPONIVEL'` pode ser usado

### Desconto

1. **Valor fixo:** Desconto Wall é sempre em R$ (não percentual)
2. **Configuração:** Definido em `parametros_wallclub.parametro_loja_31`
3. **Aplicação:** Automática nas calculadoras (não requer ação do cliente)
4. **Impacto:** Reduz valor final da transação (afeta repasse, comissão, etc)

---

## 📝 Próximos Passos

- [ ] Documentar contabilização de cashback
- [ ] Documentar contabilização de desconto
- [ ] Documentar impacto no fluxo financeiro (RPR, repasses)
- [ ] Documentar regras de expiração e estorno

---

**Mantido por:** Equipe WallClub
**Última atualização:** 06/03/2026
