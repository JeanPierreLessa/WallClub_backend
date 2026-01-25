# Lógica Funcional do Slip de Impressão POS

## 1. Entrada de Dados

- Recebe transação do POS (Pinbank/Own)
- Extrai: CPF, valor, parcelas, forma de pagamento, NSU, terminal

## 2. Identificação do Tipo de Transação

```
wall = 's' se CPF existe, senão 'n'
forma = PIX | DEBITO | PARCELADO SEM JUROS | A VISTA | PARCELADO COM JUROS
```

## 3. Cálculo via CalculadoraBaseGestao

Gera 130+ variáveis, principais:

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `valores[11]` | Valor original | R$ 2.00 |
| `valores[13]` | Número de parcelas | 2 |
| `valores[14]` | Taxa desconto/encargo | -0.0433 (negativo = encargo, positivo = desconto) |
| `valores[16]` | Valor líquido pago à loja | R$ 2.00 |
| `valores[19]` | Valor total com encargo | R$ 2.10 |
| `valores[20]` | Valor da parcela | R$ 1.05 |
| `valores[26]` | Valor final | R$ 2.10 |
| `valores[88]` | Encargos Wall | R$ 0.00 |
| `valores[94][0]` | Encargos adicionais | R$ 0.00 |

## 4. Cálculo de Tarifas e Encargos

```python
# Encargos da operadora
encargos = abs(valores[88] + valores[94][0])

# Tarifas Wall Club
tarifas = abs(parcelas × vparcela - valor_liquido) - encargos

# parte1 (diferença total)
parte1 = abs(parcelas × vparcela - valor_original)
```

**Exemplo:**
- `encargos = abs(0.00 + 0.00) = R$ 0.00`
- `tarifas = abs(2 × 1.05 - 2.00) - 0.00 = R$ 0.10`
- `parte1 = abs(2 × 1.05 - 2.00) = R$ 0.10`

## 5. Decisão de Labels (usando valores[14])

### Se `valores[14] < 0` (ENCARGO)

```json
{
  "desconto": "Valor total dos encargos: R$ 0.10",
  "vdesconto": "Valor total pago com encargos:\nR$ 2.10",
  "encargos": "Encargos pagos a operadora de cartão: R$ 0.00"
}
```

### Se `valores[14] >= 0` (DESCONTO)

```json
{
  "desconto": "Valor do desconto CLUB: R$ 0.10",
  "vdesconto": "Valor pago com desconto:\nR$ 2.10",
  "encargos": "Encargos financeiros: R$ 0.00"
}
```

## 6. Montagem do Slip

### COM WALL CLUB (wall='s')

#### PIX/DEBITO

```json
{
  "voriginal": "Valor original da loja: R$ 2.00",
  "desconto": "Valor do desconto CLUB: R$ 0.10",
  "vdesconto": "Valor total pago:\nR$ 2.10",
  "pagoavista": "Valor pago à loja à vista: R$ 2.00",
  "vparcela": "R$ 1.05",
  "tarifas": "Tarifas CLUB: --",
  "encargos": ""
}
```

#### PARCELADO

```json
{
  "voriginal": "Valor original da loja: R$ 2.00",
  "desconto": "Valor total dos encargos: R$ 0.10",
  "vdesconto": "Valor total pago com encargos:\nR$ 2.10",
  "pagoavista": "Valor pago à loja à vista: R$ 2.00",
  "vparcela": "R$ 1.05",
  "tarifas": "Tarifas CLUB: R$ 0.10",
  "encargos": "Encargos pagos a operadora de cartão: R$ 0.00",
  "cet": "CET (Custo Efetivo Total) %am: 0.03"
}
```

### SEM WALL CLUB (wall='n')

```json
{
  "voriginal": "Valor original da loja: R$ 2.00",
  "vdesconto": "Valor total pago:\nR$ 2.00",
  "pagoavista": "Valor pago à loja: R$ 2.00",
  "vparcela": "R$ 1.00",
  "tarifas": "Tarifas CLUB: --",
  "encargos": ""
}
```

## 7. Campos Comuns

```json
{
  "cpf": "*******807",
  "nome": "JEAN L FERREIRA",
  "estabelecimento": "Loja Special JJP",
  "cnpj": "17653377807",
  "data": "13/12/2025 08:54:23",
  "forma": "PARCELADO SEM JUROS",
  "parcelas": 2,
  "nopwall": "000068947992",
  "autwall": "BY0D2H",
  "terminal": "PBF923BH70663",
  "nsu": 162216058
}
```

## 8. Fluxo Completo

```
1. Recebe transação POS
   ↓
2. Identifica se tem Wall Club (CPF existe?)
   ↓
3. Calcula valores via CalculadoraBaseGestao
   ↓
4. Usa valores[14] para decidir se é encargo ou desconto
   ↓
5. Separa tarifas Wall (linha "tarifas") de encargos operadora (linha "encargos")
   ↓
6. Monta JSON com labels apropriados
   ↓
7. Retorna para impressão no POS
```

## 9. Diferença entre Tarifas e Encargos

| Campo | Descrição | Origem |
|-------|-----------|--------|
| **Tarifas CLUB** | Diferença entre valor pago pelo cliente e valor recebido pela loja, menos encargos | `abs(parcelas × vparcela - valor_liquido) - encargos` |
| **Encargos** | Custos da operadora de cartão ou Wall | `abs(valores[88] + valores[94][0])` |

**Exemplo:**
- Cliente paga: 2 × R$ 1.05 = **R$ 2.10**
- Loja recebe: **R$ 2.00**
- Diferença total: R$ 0.10
  - Tarifas Wall Club: R$ 0.10
  - Encargos operadora: R$ 0.00

## 10. Correções Implementadas (13/12/2025)

### Problema 1: Valor da parcela incorreto
- **Causa:** Arredondamento de `valores[19]` antes de calcular `valores[20]`
- **Solução:** Recalcular `valores[19]` baseado na parcela arredondada
- **Arquivo:** `calculadora_base_gestao.py` linha 236

### Problema 2: Labels incorretos para encargo
- **Causa:** Usando `desconto < 0` em vez de `valores[14] < 0`
- **Solução:** Usar `valores[14]` para decidir labels
- **Arquivos:** `services_transacao.py`, `services_transacao_pos.py`

### Problema 3: Separação de tarifas e encargos
- **Causa:** Tudo sendo exibido como "tarifas"
- **Solução:** Calcular separadamente `tarifas` e `encargos`
- **Fórmulas:**
  - `encargos = abs(valores[88] + valores[94][0])`
  - `tarifas = abs(parcelas × vparcela - valor_liquido) - encargos`
