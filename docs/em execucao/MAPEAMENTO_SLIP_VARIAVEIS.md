# MAPEAMENTO SLIP → VARIÁVEIS

**Data:** 25/01/2026
**Objetivo:** Mapear cada campo do SLIP para sua variável de origem

---

## 📋 CAMPOS DO SLIP (Cliente Wall)

### **PIX / DÉBITO**

| Campo do SLIP | Valor | Variável Origem | Observação |
|---------------|-------|-----------------|------------|
| **Valor original da loja** | R$ 10,00 | `valores[11]` | Valor bruto da compra |
| **Valor do desconto CLUB** | R$ 0,29 | `valores[15]` (PIX) ou `valores[18]` (DÉBITO) | Desconto/encargo Wall |
| **Cupom PROMO_TESTE** | -R$ 5,00 | `dados['cupom_valor_desconto']` | Informativo (não afeta calculadora) |
| **Saldo utilizado de cashback** | R$ 0,26 | `AutorizacaoService.verificar_autorizacao()` | Buscado via `autorizacao_id` |
| **Cashback concedido** | R$ 0,00 | `dados['cashback_concedido']` | Cashback creditado nesta transação |
| **Valor total pago** | R$ 5,03 | `valores[26]` ajustado | var26 - cupom - cashback |
| **Valor pago à loja à vista** | R$ 10,29 | `valores[16]` | Valor líquido para loja |
| **Valor da parcela** | R$ 5,03 | `vparcela_ajustado` | vdesconto_final / parcelas |
| **Tarifas CLUB** | -- | -- | Não aplicável para PIX/DÉBITO |
| **Encargos** | -- | -- | Não exibido para PIX/DÉBITO |

---

### **PARCELADO (À VISTA / SEM JUROS / COM JUROS)**

| Campo do SLIP | Valor | Variável Origem | Observação |
|---------------|-------|-----------------|------------|
| **Valor original da loja** | R$ 10,00 | `valores[11]` | Valor bruto da compra |
| **Desconto/Encargo** | R$ 0,29 | `parte1` | abs(parcelas × vparcela - valores[11]) |
| **Label do Desconto/Encargo** | Variável | `valores[14]` | Se < 0: "Encargos", se >= 0: "Desconto CLUB" |
| **Cupom PROMO_TESTE** | -R$ 5,00 | `dados['cupom_valor_desconto']` | Informativo (não afeta calculadora) |
| **Saldo utilizado de cashback** | R$ 0,26 | `AutorizacaoService.verificar_autorizacao()` | Buscado via `autorizacao_id` |
| **Cashback concedido** | R$ 0,00 | `dados['cashback_concedido']` | Cashback creditado nesta transação |
| **Valor total pago** | R$ 5,03 | `vdesconto_final` | valores[26] ajustado |
| **Valor pago à loja à vista** | R$ 10,29 | `valores[16]` | Valor líquido para loja |
| **Valor da parcela** | R$ 5,03 | `vparcela_ajustado` | vdesconto_final / parcelas |
| **Tarifas CLUB** | R$ -0,42 | `tarifas` | abs(parcelas × vparcela - valores[16]) - encargos |
| **Encargos pagos a operadora** | R$ 0,42 | `encargos` | abs(valores[88] + valores[94][0]) |

---

## 🔢 VARIÁVEIS CALCULADAS (Intermediárias)

| Variável | Valor | Cálculo | Usado em |
|----------|-------|---------|----------|
| `valores[11]` | R$ 10,00 | Entrada (valor original) | voriginal |
| `valores[14]` | -0,0289 | param_7 (% desconto/encargo Wall) | Decisão label |
| `valores[15]` | R$ 0,00 | valores[11] × valores[14] / 100 | Desconto PIX |
| `valores[16]` | R$ 10,29 | valores[11] × (1 - valores[14]) | pagoavista |
| `valores[17]` | 0,029 | param_10 (% taxa operadora) | Cálculo valores[18] |
| `valores[18]` | R$ 0,29 | valores[11] × valores[17] | Desconto DÉBITO/Parcelado |
| `valores[20]` | R$ 10,29 | valores[19] / valores[13] | vparcela (antes ajuste) |
| `valores[26]` | R$ 10,29 → 5,03 | Calculadora → ajustado (- cupom - cashback) | vdesconto |
| `valores[88]` | R$ 0,22 | Calculadora (encargo componente 1) | encargos |
| `valores[94][0]` | R$ 0,20 | Calculadora (encargo componente 2) | encargos |
| `parte1` | R$ 0,29 | abs(parcelas × vparcela - valores[11]) | desconto/encargo |
| `encargos` | R$ 0,42 | abs(valores[88] + valores[94][0]) | Encargos operadora |
| `tarifas` | R$ -0,42 | abs(parcelas × vparcela - valores[16]) - encargos | Tarifas CLUB |
| `vdesconto_final` | R$ 5,03 | valores[26] ajustado | vdesconto |
| `vparcela_ajustado` | R$ 5,03 | vdesconto_final / parcelas | vparcela |

---

## 📊 CAMPOS SEM WALL CLUB

| Campo do SLIP | Valor | Variável Origem |
|---------------|-------|-----------------|
| **Valor original da loja** | R$ 10,00 | `valores[11]` |
| **Desconto** | -- | -- |
| **Valor total pago** | R$ 10,00 | `valores[11]` |
| **Valor pago à loja** | R$ 10,00 | `valores[11]` |
| **Valor da parcela** | R$ 10,00 | `valores[20]` |
| **Tarifas CLUB** | -- | -- |
| **Encargos** | -- | -- |

---

## 🎯 RESUMO RÁPIDO

**Campos principais:**
- `voriginal` → `valores[11]`
- `desconto` → `parte1` (calculado) ou `valores[15]`/`valores[18]`
- `cupom` → `dados['cupom_valor_desconto']`
- `saldo_usado` → `AutorizacaoService` (via `autorizacao_id`)
- `cashback_concedido` → `dados['cashback_concedido']`
- `vdesconto` → `valores[26]` ajustado
- `pagoavista` → `valores[16]`
- `vparcela` → `vparcela_ajustado`
- `tarifas` → calculado (parcelas × vparcela - valores[16] - encargos)
- `encargos` → `valores[88]` + `valores[94][0]`

---

## 📊 COMPARAÇÃO: SEM vs COM CUPOM+SALDO

### **CENÁRIO 1: SEM CUPOM/SALDO (Hoje - Como está)**

| Item | Valor | Cálculo |
|------|-------|---------|
| **Entrada** | | |
| Valor original loja | R$ 10,00 | - |
| Cupom | R$ 0,00 | - |
| Saldo cashback | R$ 0,00 | - |
| **Calculadora recebe** | R$ 10,00 | valor_original |
| | | |
| **Variáveis Calculadas** | | |
| valores[11] | R$ 10,00 | Entrada |
| valores[14] | -0,0289 | param_7 (% encargo) |
| valores[16] | R$ 10,29 | 10.00 × (1 - (-0.0289)) |
| valores[17] | 0,029 | param_10 (% taxa operadora) |
| valores[18] | R$ 0,29 | 10.00 × 0.029 |
| valores[26] | R$ 10,29 | = valores[16] |
| valores[87] | 0,0214 | param_wall_1 |
| valores[88] | R$ 0,22 | 10.29 × 0.0214 |
| valores[94][0] | R$ 0,20 | 10.29 × valores[93][0] |
| | | |
| **Resultado** | | |
| Valor cobrado cartão | R$ 10,29 | amount / 100 |
| Loja recebe | R$ 10,29 | valores[16] |
| Encargos operadora | R$ 0,42 | 0.22 + 0.20 |
| Cliente paga | R$ 10,29 | valores[26] |

---

### **CENÁRIO 2: COM CUPOM+SALDO (Como está hoje)**

| Item | Valor | Cálculo |
|------|-------|---------|
| **Entrada** | | |
| Valor original loja | R$ 10,00 | - |
| Cupom | R$ 5,00 | - |
| Saldo cashback | R$ 0,26 | - |
| **Calculadora recebe** | R$ 10,00 ❌ | valor_original (ATUAL) |
| | | |
| **Variáveis Calculadas** | | |
| valores[11] | R$ 10,00 | Entrada |
| valores[16] | R$ 10,29 | 10.00 × (1.0289) |
| valores[26] | R$ 10,29 → 5,03 | Ajustado depois (- 5.00 - 0.26) |
| valores[88] | R$ 0,22 | 10.29 × 0.0214 ❌ |
| valores[94][0] | R$ 0,20 | 10.29 × valores[93][0] ❌ |
| | | |
| **Resultado** | | |
| Valor cobrado cartão | R$ 5,03 | amount / 100 |
| Loja recebe | R$ 10,29 | valores[16] |
| Encargos operadora | R$ 0,42 | Sobre 10.29 ❌ ERRADO |
| Cliente paga | R$ 5,03 | valores[26] ajustado |
| | | |
| **❌ PROBLEMA:** | | |
| Encargos calculados sobre | R$ 10,29 | Mas cliente pagou 5.03 |
| Base_unificada com valores | Errados | Todas as taxas sobre 10.29 |

---

### **CENÁRIO 3: COM CUPOM+SALDO (Como deveria ser - PROPOSTO)**

| Item | Valor | Cálculo |
|------|-------|---------|
| **Entrada** | | |
| Valor original loja | R$ 10,00 | Informativo (manter separado) |
| Cupom | R$ 5,00 | - |
| Saldo cashback | R$ 0,26 | - |
| **Calculadora recebe** | R$ 5,03 ✅ | amount / 100 (PROPOSTO) |
| | | |
| **Variáveis Calculadas** | | |
| valores[11] | R$ 5,03 | Entrada (valor cobrado) |
| valores[16] | R$ 5,17 | 5.03 × (1.0289) |
| valores[26] | R$ 5,17 | = valores[16] |
| valores[88] | R$ 0,11 | 5.17 × 0.0214 ✅ |
| valores[94][0] | R$ 0,10 | 5.17 × valores[93][0] ✅ |
| | | |
| **Resultado** | | |
| Valor cobrado cartão | R$ 5,03 | amount / 100 |
| Loja recebe | R$ 5,17 ❓ | valores[16] |
| Encargos operadora | R$ 0,21 | Sobre 5.03 ✅ CORRETO |
| Cliente paga | R$ 5,03 | valores[26] |
| | | |
| **✅ BENEFÍCIO:** | | |
| Encargos calculados sobre | R$ 5,03 | Valor real cobrado |
| Base_unificada com valores | Corretos | Todas as taxas sobre 5.03 |
| | | |
| **❓ DÚVIDA:** | | |
| Valor original loja (10.00) | Como manter? | Novo campo informativo? |
| Loja recebe 5.17 ou 10.29? | Definir | Impacta lógica de negócio |
