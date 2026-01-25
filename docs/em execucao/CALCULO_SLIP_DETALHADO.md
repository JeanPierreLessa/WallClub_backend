# CÁLCULO DETALHADO DO SLIP - TRANSAÇÃO POS

**Data:** 24/01/2026
**Transação:** NSU 2119526 - Terminal PB59237K70569
**Arquivo:** `services/django/posp2/services_transacao_pos.py`

---

## 📥 DADOS DE ENTRADA (POS → Backend)

### Valores Recebidos do POS
```python
valor_original = 10.00          # Valor da compra na loja
cupom_codigo = "PROMO_TESTE"    # Cupom aplicado
cupom_valor_desconto = 5.00     # Desconto do cupom
valor_cashback = 0.26           # Cashback usado pelo cliente
autorizacao_id = "29009707..."  # ID da autorização de uso de cashback
amount = 503                    # Valor cobrado em centavos (5.03)
originalAmount = 503            # Valor original cobrado
paymentMethod = "CREDIT_ONE_INSTALLMENT"
totalInstallments = 1
brand = "VISA"
```

---

## 🧮 ETAPA 1: CALCULADORA BASE (Linha 310-316)

### Entrada para Calculadora
```python
valor_para_calculo = dados['valor_original']  # 10.00
# NÃO abate cupom nem cashback - calculadora trabalha com valor bruto
```

### Saída da Calculadora (valores_calculados)
```python
valores[0]  = "2026-01-24"           # Data da transação
valores[11] = 10.00                  # Valor original da loja
valores[12] = "A VISTA"              # Tipo de compra
valores[13] = 1                      # Número de parcelas
valores[14] = -0.0289                # Desconto/Encargo Wall (negativo = encargo)
valores[15] = 0.00                   # Desconto PIX (não aplicável)
valores[16] = 10.29                  # Valor líquido para loja
valores[18] = 0.29                   # Encargo cartão
valores[19] = 10.29                  # Valor com desconto/encargo
valores[20] = 10.29                  # Valor da parcela
valores[26] = 10.29                  # Valor a pagar (antes do ajuste)
valores[88] = 0.22                   # Encargo componente 1
valores[94][0] = 0.20                # Encargo componente 2
```

**Cálculo valores[16] (Valor líquido para loja):**
```
valores[16] = valores[11] + encargos_wall
valores[16] = 10.00 + 0.29 = 10.29
```

**Cálculo valores[20] (Valor da parcela):**
```
valores[20] = valores[16] / valores[13]
valores[20] = 10.29 / 1 = 10.29
```

---

## 💰 ETAPA 2: AJUSTE VAR26 (Linha 320-327)

### Abater Cupom e Cashback
```python
var26_original = valores_calculados[26]  # 10.29
cupom_desconto = 5.00
cashback_usado = 0.26

var26_ajustado = var26_original - cupom_desconto - cashback_usado
var26_ajustado = 10.29 - 5.00 - 0.26
var26_ajustado = 5.03  # ✅ Valor efetivamente pago pelo cliente

valores_calculados[26] = 5.03  # Atualiza var26
```

**Log gerado:**
```
💰 var26 ajustado: 10.29 - cupom(5.00) - cashback(0.26) = 5.03
```

---

## 🧾 ETAPA 3: GERAÇÃO DO SLIP (Linha 596-850)

### 3.1. Valor Original Display (Linha 648)
```python
valor_original_display = dados.get('valor_original', valores_calculados.get(11, 0))
valor_original_display = 10.00  # Valor da loja (sem encargos)
```

### 3.2. Desconto/Encargo (Linha 658-661)
```python
pixcartao_tipo = "CARTÃO"  # brand = "VISA"

if valores_calculados.get(12) == "PIX" or pixcartao_tipo == "PIX":
    desconto = valores_calculados.get(15, 0)  # Desconto PIX
else:
    desconto = valores_calculados.get(18, 0)  # Encargo cartão

desconto = 0.29  # Encargo do cartão
```

### 3.3. Parte0 - Valor Base (Linha 664-670)
```python
parte0 = valores_calculados.get(26, 0)  # Usa var26 ajustado
parte0 = 5.03  # ✅ Valor efetivamente pago
```

### 3.4. Parcelas (Linha 673)
```python
parcelas = int(valores_calculados.get(13, 1))
parcelas = 1  # À vista
```

### 3.5. Encargos (Linha 675-682)
```python
# Replicando PHP: $encargos = abs($valores[88] + $valores[94]["0"]);
valores_94 = valores_calculados.get(94, {})  # {'0': 0.20}
valores_94_0 = 0.20
valores_88 = 0.22

encargos = abs(valores_88 + valores_94_0)
encargos = abs(0.22 + 0.20)
encargos = 0.42  # ✅ Encargos pagos à operadora
```

**Log gerado:**
```
encargos = abs(0.22 + 0.2) = 0.42000000000000004
```

### 3.6. Vparcela (Linha 684-686)
```python
vparcela = valores_calculados.get(20, 0)
vparcela = 10.29  # Valor da parcela (da calculadora, antes do ajuste)
```

**Log gerado:**
```
vparcela = 10.29 (valores[20] direto)
```

### 3.7. Parte1 - Diferença (Linha 689-695)
```python
# Replicando PHP: $parte1 = abs($valores[13] * $vparcela - $valores[11]);
valor_original = valores_calculados.get(11, 0)  # 10.00
vparcela_float = 10.29
parcelas = 1

parte1 = abs(parcelas * vparcela_float - valor_original)
parte1 = abs(1 * 10.29 - 10.00)
parte1 = abs(10.29 - 10.00)
parte1 = 0.29  # ✅ Diferença (encargo)
```

**Log gerado:**
```
🔍 [DECISÃO] valores[14]=-0.0289, parte1=0.28999999999999915
```

### 3.8. Tarifas (Linha 697-700)
```python
# Replicando PHP: $tarifas = abs($valores[13] * $vparcela - $valores[16]) - $encargos;
valor_liquido = valores_calculados.get(16, 0)  # 10.29
vparcela_float = 10.29
parcelas = 1
encargos = 0.42

tarifas = abs(parcelas * vparcela_float - valor_liquido) - encargos
tarifas = abs(1 * 10.29 - 10.29) - 0.42
tarifas = abs(10.29 - 10.29) - 0.42
tarifas = abs(0) - 0.42
tarifas = -0.42  # ✅ Tarifa Wall (negativa = crédito para loja)
```

**Log gerado:**
```
tarifas = abs(1 * 10.29 - 10.29) - 0.42000000000000004 = -0.42
```

### 3.9. Saldo Cashback Usado (Linha 711-724)
```python
autorizacao_id = "29009707-17cd-4919-9140-73198d1682dc"

# Busca via AutorizacaoService
resultado = AutorizacaoService.verificar_autorizacao(autorizacao_id)
# resultado = {
#     'sucesso': True,
#     'status': 'CONCLUIDA',
#     'valor_bloqueado': 0.26
# }

saldo_cashback_usado = float(resultado.get('valor_bloqueado'))
saldo_cashback_usado = 0.26  # ✅ Valor debitado do cashback
```

**Log gerado:**
```
💸 [SALDO] Saldo cashback usado encontrado: R$ 0.26, status=CONCLUIDA
```

### 3.10. Cashback Concedido (Linha 727-729)
```python
cashback_concedido = dados.get('cashback_concedido', 0)
cashback_concedido = 0.00  # Nenhum cashback concedido nesta transação
```

**Log gerado:**
```
💰 [CASHBACK] Cashback concedido: R$ 0.00
```

### 3.11. Valores Finais (Linha 731-738)
```python
# var26 já vem ajustado (cupom e cashback já abatidos)
vdesconto_final = parte0
vdesconto_final = 5.03  # ✅ Valor total pago pelo cliente

vparcela_ajustado = vdesconto_final / parcelas
vparcela_ajustado = 5.03 / 1
vparcela_ajustado = 5.03  # ✅ Valor da parcela ajustado
```

**Log gerado:**
```
💰 [SLIP] vdesconto_final=5.03, vparcela_ajustado=5.03, parcelas=1
```

---

## 📋 ETAPA 4: DECISÃO ENCARGO vs DESCONTO (Linha 791-802)

### Verificação valores[14]
```python
valores_14 = valores_calculados.get(14, 0)
valores_14 = -0.0289  # ❌ NEGATIVO = ENCARGO

if valores_14 < 0:
    # É ENCARGO (cliente paga mais que o valor original)
    label_desconto = f"Valor total dos encargos: R$ {parte1}"
    label_desconto = "Valor total dos encargos: R$ 0.29"

    label_vdesconto = f"Valor total pago com encargos:\nR$ {vdesconto_final}"
    label_vdesconto = "Valor total pago com encargos:\nR$ 5.03"

    label_encargos = f"Encargos pagos a operadora de cartão: R$ {encargos}"
    label_encargos = "Encargos pagos a operadora de cartão: R$ 0.42"
else:
    # É DESCONTO (cliente paga menos que o valor original)
    label_desconto = f"Valor do desconto CLUB: R$ {parte1}"
    label_vdesconto = f"Valor pago com desconto:\nR$ {vdesconto_final}"
    label_encargos = f"Encargos financeiros: R$ {encargos}"
```

**Resultado:** Labels de ENCARGO (valores[14] < 0)

---

## 📄 ETAPA 5: JSON FINAL DO SLIP (Linha 804-828)

### Montagem do Array
```python
array_update = {
    "voriginal": f"Valor original da loja: R$ {valor_original_display}",
    "voriginal": "Valor original da loja: R$ 10.00",

    "desconto": label_desconto,
    "desconto": "Valor total dos encargos: R$ 0.29",

    "cupom": f"Cupom {cupom_codigo}: -R$ {cupom_valor}",
    "cupom": "Cupom PROMO_TESTE: -R$ 5.00",

    "saldo_usado": f"Saldo utilizado de cashback: R$ {saldo_cashback_usado}",
    "saldo_usado": "Saldo utilizado de cashback: R$ 0.26",

    "vdesconto": label_vdesconto,
    "vdesconto": "Valor total pago com encargos:\nR$ 5.03",

    "pagoavista": f"Valor pago à loja à vista: R$ {valores_calculados.get(16, 0)}",
    "pagoavista": "Valor pago à loja à vista: R$ 10.29",

    "vparcela": f"R$ {vparcela_ajustado}",
    "vparcela": "R$ 5.03",

    "tarifas": f"Tarifas CLUB: R$ {tarifas}",
    "tarifas": "Tarifas CLUB: R$ -0.42",

    "encargos": label_encargos
    "encargos": "Encargos pagos a operadora de cartão: R$ 0.42"
}
```

---

## 📊 RESUMO FINAL - TODAS AS VARIÁVEIS

| Variável | Valor | Origem | Cálculo |
|----------|-------|--------|---------|
| **valor_original** | R$ 10,00 | POS | Valor informado pela loja |
| **cupom_valor_desconto** | R$ 5,00 | POS | Cupom PROMO_TESTE aplicado |
| **valor_cashback** | R$ 0,26 | POS | Cashback usado pelo cliente |
| **valores[11]** | R$ 10,00 | Calculadora | Valor original (entrada) |
| **valores[14]** | -0,0289 | Calculadora | Desconto/Encargo Wall (negativo = encargo) |
| **valores[16]** | R$ 10,29 | Calculadora | 10.00 + 0.29 (valor líquido para loja) |
| **valores[18]** | R$ 0,29 | Calculadora | Encargo do cartão |
| **valores[20]** | R$ 10,29 | Calculadora | 10.29 / 1 (valor da parcela) |
| **valores[26]** | R$ 10,29 → **5,03** | Calculadora + Ajuste | 10.29 - 5.00 - 0.26 |
| **valores[88]** | R$ 0,22 | Calculadora | Encargo componente 1 |
| **valores[94][0]** | R$ 0,20 | Calculadora | Encargo componente 2 |
| **encargos** | R$ 0,42 | SLIP | abs(0.22 + 0.20) |
| **parte1** | R$ 0,29 | SLIP | abs(1 × 10.29 - 10.00) |
| **tarifas** | R$ -0,42 | SLIP | abs(1 × 10.29 - 10.29) - 0.42 |
| **saldo_cashback_usado** | R$ 0,26 | Autorização | Buscado via autorizacao_id |
| **vdesconto_final** | R$ 5,03 | SLIP | valores[26] ajustado |
| **vparcela_ajustado** | R$ 5,03 | SLIP | 5.03 / 1 |

---

## 🎯 FLUXO LÓGICO COMPLETO

```
1. POS envia: valor_original=10.00, cupom=5.00, cashback=0.26
   ↓
2. Calculadora processa: 10.00 → gera valores[11..130]
   - valores[16] = 10.29 (loja recebe)
   - valores[26] = 10.29 (cliente paga - antes do ajuste)
   ↓
3. Ajuste var26: 10.29 - 5.00 - 0.26 = 5.03
   ↓
4. SLIP calcula:
   - encargos = 0.42 (operadora)
   - tarifas = -0.42 (Wall)
   - parte1 = 0.29 (diferença)
   ↓
5. SLIP monta JSON:
   - voriginal = 10.00 (loja)
   - desconto = 0.29 (encargo)
   - cupom = 5.00 (informativo)
   - saldo_usado = 0.26 (informativo)
   - vdesconto = 5.03 (cliente paga)
   - pagoavista = 10.29 (loja recebe)
   - vparcela = 5.03 (parcela)
   - tarifas = -0.42 (Wall)
   - encargos = 0.42 (operadora)
```

---

## ✅ VALIDAÇÃO

**Conferência matemática:**
```
Cliente paga:     R$ 5,03
Cupom usado:    + R$ 5,00
Cashback usado: + R$ 0,26
                ─────────
Total:            R$ 10,29 ✅ (= valores[16] = loja recebe)

Loja recebe:      R$ 10,29
Valor original:   R$ 10,00
Encargo:        + R$ 0,29
                ─────────
Total:            R$ 10,29 ✅
```

**Todos os valores conferem!** 🎉
