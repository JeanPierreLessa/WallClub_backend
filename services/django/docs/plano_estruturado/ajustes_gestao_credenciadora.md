# Ajustes Gestão Credenciadora - Variáveis de Cálculo

**Data:** 2025-10-25
**Calculadora:** `CalculadoraBaseCredenciadora`
**Objetivo:** Corrigir variáveis que estavam usando dados de `pagamentos_efetuados` ou parâmetros errados

---

## 📋 Contexto

A calculadora atual foi criada baseada em `CalculadoraBaseGestao` (Wallet), que tem acesso à tabela `pagamentos_efetuados`.

Para **Credenciadora** e **Checkout**, não temos acesso a essa tabela, então precisamos:
1. Usar dados diretos de `pinbankExtratoPOS`
2. Usar parâmetros corretos das tabelas de configuração

---

## 🚨 Erros Identificados e Correções

### 1. **var36** - Taxa de Administração
**Erro Atual:**
```python
# Linha 302
param_12 = ParametrosService.retornar_parametro_loja(info_loja['id'], data_ref, id_plano, 12, wall)
valores[36] = self._format_decimal(self._to_decimal(param_12, 4), 4)
```

**Correção:**
```python
# var36 deve vir diretamente da Pinbank (já vem em %)
# Exemplo: 0.89 significa 0.89%
valores[36] = self._format_decimal(self._to_decimal(dados_linha['ValorTaxaAdm'], 4), 4)
```

**Observação:** `ValorTaxaAdm` já vem no formato percentual (0.89 = 0.89%), armazenar como está.

---

### 2. **var39** - Taxa Mensal
**Erro Atual:**
```python
# Linha 314
param_13 = ParametrosService.retornar_parametro_loja(info_loja['id'], data_ref, id_plano, 13, wall)
valores[39] = self._format_decimal(self._to_decimal(param_13, 4), 4)
```

**Correção:**
```python
# var39 deve vir diretamente da Pinbank (já vem em %)
# Exemplo: 1.99 significa 1.99%
valores[39] = self._format_decimal(self._to_decimal(dados_linha['ValorTaxaMes'], 4), 4)
```

**Observação:** `ValorTaxaMes` já vem no formato percentual, armazenar como está.

---

### 3. **var44** - Valor de Pagamento (Soma de Repasses)
**Erro Atual:**
```python
# Linha 658-662
f44 = dados_linha.get('f44')
if f44 is not None:
    valores[44] = self._format_decimal(self._to_decimal(f44, 2), 2)
else:
    valores[44] = self._format_decimal(0, 2)
```

**Correção:**
```python
# var44 = SOMA de ValorLiquidoRepasse de todas as parcelas
# Precisa adicionar campo agregado na query SQL do service

# Na query do service (services_carga_credenciadora.py):
# ( SELECT SUM(pep2.ValorLiquidoRepasse)
#   FROM wallclub.pinbankExtratoPOS pep2
#   WHERE pep.NsuOperacao = pep2.NsuOperacao
#         AND pep2.DescricaoStatusPagamento in ('Pago','Pago-M')) AS vRepasse

# No cálculo:
vrepasse = self._to_decimal(dados_linha.get('vRepasse') or 0, 2)
valores[44] = self._format_decimal(vrepasse, 2)
```

**Observação:** Na Pinbank, cada parcela vem em uma linha. Precisamos somar todas para ter o valor total pago.

---

### 4. **var45** - Data de Pagamento
**Erro Atual:**
```python
# Linha 665-669
f45 = dados_linha.get('f45')
if f45 is not None:
    valores[45] = str(f45)
else:
    valores[45] = ''
```

**Correção:**
```python
# var45 = DataFuturaPagamento quando status é 'Pago' ou 'Pago-M'
# Converter de formato ISO (2025-10-25T22:19:47.706) para DD/MM/YYYY

descricao_status_pag = dados_linha.get('DescricaoStatusPagamento')
if descricao_status_pag in ('Pago', 'Pago-M'):
    data_futura = dados_linha.get('DataFuturaPagamento')
    if data_futura and str(data_futura) != 'None':
        # Converter de ISO para DD/MM/YYYY
        try:
            if isinstance(data_futura, str):
                data_obj = dt.strptime(data_futura[:10], '%Y-%m-%d')
            else:
                data_obj = data_futura
            valores[45] = data_obj.strftime('%d/%m/%Y')
        except:
            valores[45] = ''
    else:
        valores[45] = ''
else:
    valores[45] = ''
```

**Formato de Entrada:** `2025-10-25T22:19:47.706`
**Formato de Saída:** `25/10/2025`

---

### 5. **var70** - Data de Cancelamento
**Erro Atual:**
```python
# Linha 129
valores[70] = dados_linha['DataCancelamento'] or ''
```

**Correção:**
```python
# var70 só deve ter valor quando DescricaoStatus = 'TRANS. CANCELADA POSTERIOR'
# Converter de formato ISO (2025-10-18T18:55:27.943) para DD/MM/YYYY

descricao_status = dados_linha.get('DescricaoStatus')
if descricao_status == 'TRANS. CANCELADA POSTERIOR':
    data_cancelamento = dados_linha.get('DataCancelamento')
    if data_cancelamento and str(data_cancelamento) not in ['None', '0001-01-01T00:00:00']:
        # Converter de ISO para DD/MM/YYYY
        try:
            if isinstance(data_cancelamento, str):
                # Verificar se não é a data padrão inválida
                if data_cancelamento.startswith('0001-01-01'):
                    valores[70] = ''
                else:
                    data_obj = dt.strptime(data_cancelamento[:10], '%Y-%m-%d')
                    valores[70] = data_obj.strftime('%d/%m/%Y')
            else:
                valores[70] = data_cancelamento.strftime('%d/%m/%Y')
        except:
            valores[70] = ''
    else:
        valores[70] = ''
else:
    valores[70] = ''
```

**Observação:** Pinbank retorna `0001-01-01T00:00:00` quando não há cancelamento, precisamos filtrar isso.

---

### 6. **var89** - Parâmetro Wall 1
**Erro Atual:**
```python
# Linha 95
valores[89] = self._format_decimal(self._to_decimal(dados_linha['ValorTaxaAdm'], 4) / Decimal('100'), 4)
```

**Correção:**
```python
# var89 deve vir de parametros_wall_1 (não de ValorTaxaAdm)
param_wall_1 = ParametrosService.retornar_parametro_uptal(info_loja['id'], data_ref, id_plano, 1, wall)
if param_wall_1 is None:
    param_wall_1 = 0
valores[89] = self._format_decimal(self._to_decimal(param_wall_1, 4), 4)
```

**Nota:** `ValorTaxaAdm` vai para var36, não para var89.

---

### 7. **var92** - Parâmetro Wall 4 (Taxa Mensal)
**Erro Atual:**
```python
# Linha 100
valores[92] = self._format_decimal(self._to_decimal(dados_linha['ValorTaxaMes'], 4) / Decimal('100'), 4)
```

**Correção:**
```python
# var92 = var91 (já calculada na linha 390)
# var91 vem de parametros_wall_4
valores[92] = valores[91]
```

**Nota:** `ValorTaxaMes` vai para var39, não para var92.

---

### 8. **var93** - Parâmetro Wall 5
**Erro Atual:**
```python
# Linha 396
valores[93] = {"0": self._format_decimal(valores[91] * (1 + valores[13]) / 2, 4)}
```

**Correção:**
```python
# var93 deve usar parametros_wall_5 (não var91)
param_wall_5 = ParametrosService.retornar_parametro_uptal(info_loja['id'], data_ref, id_plano, 5, wall)
if param_wall_5 is None:
    param_wall_5 = 0

# var93["0"] = param_wall_5 * (1 + numParcelas) / 2
valores[93] = {"0": self._format_decimal(self._to_decimal(param_wall_5, 4) * (1 + valores[13]) / 2, 4)}
```

**Nota:** O cálculo está correto, mas estava usando o parâmetro errado (wall_4 em vez de wall_5).

---

## 📊 Resumo de Variáveis Afetadas

| Variável | Origem Antiga | Origem Nova | Impacto |
|----------|---------------|-------------|---------|
| var36 | `param_12` | `ValorTaxaAdm` | Alto - afeta var37, var38 |
| var39 | `param_13` | `ValorTaxaMes` | Alto - afeta var40, var41 |
| var44 | `f44` (pagamentos_efetuados) | Soma `ValorLiquidoRepasse` | Alto - afeta var101, var102 |
| var45 | `f45` (pagamentos_efetuados) | `DataFuturaPagamento` + conversão | Médio |
| var70 | Sem validação | Com validação + conversão | Baixo |
| var89 | `ValorTaxaAdm / 100` | `parametros_wall_1` | Alto - afeta var90 |
| var92 | `ValorTaxaMes / 100` | `var91` (parametros_wall_4) | Baixo |
| var93 | Usa `var91` | Usa `parametros_wall_5` | Alto - afeta var94, var95 |

---

## 🔧 Alterações Necessárias no Código

### Arquivo: `calculadora_base_credenciadora.py`

**Localização das mudanças:**
- ✅ Linha 95-97: var89 (parametros_wall_1)
- ✅ Linha 100-102: var92 (usar var91)
- ✅ Linha 129: var70 (adicionar validação)
- ✅ Linha 302: var36 (ValorTaxaAdm)
- ✅ Linha 314: var39 (ValorTaxaMes)
- ✅ Linha 396: var93 (parametros_wall_5)
- ✅ Linha 658-669: var44 e var45 (novas lógicas)

### Arquivo: `services_carga_credenciadora.py`

**Alterações na Query SQL (linha ~35-88):**
```sql
-- Adicionar agregação de ValorLiquidoRepasse
( SELECT SUM(pep2.ValorLiquidoRepasse)
  FROM wallclub.pinbankExtratoPOS pep2
  WHERE pep.NsuOperacao = pep2.NsuOperacao
        AND pep2.DescricaoStatusPagamento in ('Pago','Pago-M')) AS vRepasse
```

---

## ✅ Variáveis que NÃO precisam de ajuste

Estas variáveis já estão corretas e não dependem de `pagamentos_efetuados`:

- ✅ var43 - Já calcula data futura corretamente
- ✅ var69 - Já trata status de pagamento
- ✅ var37 - Mantido como está (pedido do usuário)
- ✅ var38 - Automática (depende de var36 e var16)
- ✅ var40 - Automática (depende de var39)
- ✅ var41 - Automática (depende de var38 e var40)
- ✅ var91 - Já usa parametros_wall_4 corretamente

---

## 🎯 Ordem de Implementação Recomendada

1. **Ajustar Query SQL** (services_carga_credenciadora.py)
   - Adicionar agregação `vRepasse`

2. **Corrigir Parâmetros Wall** (calculadora_base_credenciadora.py)
   - var89 (parametros_wall_1)
   - var92 (copiar var91)
   - var93 (parametros_wall_5)

3. **Corrigir Dados Pinbank Diretos**
   - var36 (ValorTaxaAdm)
   - var39 (ValorTaxaMes)

4. **Implementar Lógicas Novas**
   - var44 (soma vRepasse)
   - var45 (DataFuturaPagamento + conversão)
   - var70 (validação + conversão)

5. **Testar Variáveis Dependentes**
   - var37, var38 (dependem de var36)
   - var40, var41 (dependem de var39)
   - var90 (depende de var89)
   - var94, var95 (dependem de var93)
   - var101, var102 (dependem de var44)

---

## 📝 Notas Importantes

1. **Conversão de Datas:** Pinbank usa formato ISO `YYYY-MM-DDTHH:MM:SS.mmm`, precisamos converter para `DD/MM/YYYY`

2. **Status de Pagamento:**
   - `in ('Pago', 'Pago-M')` = foi pago
   - `'Pendente'` = será pago

3. **Parcelas:** Pinbank retorna cada parcela em uma linha separada. Para var44, precisamos somar todas.

4. **Data Cancelamento:** Pinbank retorna `0001-01-01T00:00:00` quando não há cancelamento, filtrar isso.

5. **Taxas Percentuais:** `ValorTaxaAdm` e `ValorTaxaMes` já vêm em formato percentual (0.89 = 0.89%), não dividir por 100.

---

**Próximo Passo:** Implementar correções na ordem recomendada

---

## 🔍 Validação Completa - Resumo Executivo

### 1. Status de Pagamento
✅ **Correto** - Entendimento validado:
- `in ('Pago', 'Pago-M')` = foi pago
- `'Pendente'` = será pago

---

### 2. Variáveis Diretas

| Variável | Sua Definição | Status Atual | Ação |
|----------|---------------|--------------|------|
| **var44** | Soma de `ValorLiquidoRepasse` | ❌ Vem de `f44` | ⚠️ **AJUSTAR** |
| **var45** | `DataFuturaPagamento` (quando pago) | ❌ Vem de `f45` | ⚠️ **AJUSTAR + converter formato** |

**Conversão de data necessária:** `2025-10-25T22:19:47.706` → `25/10/2025`

---

### 3. Outras Variáveis

| Variável | Sua Definição | Status Atual | Verificação |
|----------|---------------|--------------|-------------|
| **var43** | `DataFuturaPagamento` (quando Pendente) | ✅ Linha 336-338 | ✅ **OK** (já calcula data futura) |
| **var69** | 'Pago' quando `in ('Pago', 'Pago-M')` | ✅ Linha 117-128 | ✅ **OK** |
| **var70** | `DataCancelamento` (verificar DescricaoStatus) | ✅ Linha 129 | ⚠️ **AJUSTAR** (validação + conversão) |
| **var36** | `ValorTaxaAdm` (0.89 = 0.89%) | ❌ Vem de `param_12` (linha 302) | 🚨 **ERRO - CORRIGIR** |
| **var37** | `ValorBruto * var36/100` | ❌ Usa `valores[16] * valores[36]` (linha 305) | ✅ **MANTER COMO ESTÁ** |
| **var39** | `ValorTaxaMes` | ❌ Vem de `param_13` (linha 314) | 🚨 **ERRO - CORRIGIR** |
| **var40** | Cálculo automático com var39 | ✅ Linha 317 | ✅ **OK** (se var39 estiver certa) |
| **var38** | Automática | ✅ Linha 308 | ✅ **OK** (depende de var36) |
| **var41** | Automática | ✅ Linha 320 | ✅ **OK** (depende de var38 e var40) |

---

### 4. Outros Checks - Parâmetros

| Variável | Origem Esperada | Código Atual | Status |
|----------|-----------------|--------------|--------|
| **var89** | `parametros_wall_1` | `ValorTaxaAdm / 100` (linha 95) | 🚨 **ERRO** |
| **var91** | `parametros_wall_4` | `retornar_parametro_uptal(..., 4)` (linha 387-390) | ✅ **CORRETO** |
| **var92** | `parametros_wall_4` | `ValorTaxaMes / 100` (linha 100) | 🚨 **ERRO** |
| **var93** | usa var91

---

## 🚨 Resumo de Erros Encontrados

### Erros Críticos:
1. **var36** - Vem de `param_12`, deveria vir de `ValorTaxaAdm`
2. ~~**var37** - Usa `valores[16]`, deveria usar `ValorBruto`~~ → **MANTER COMO ESTÁ**
3. **var39** - Vem de `param_13`, deveria vir de `ValorTaxaMes`
4. **var89** - Vem de `ValorTaxaAdm`, deveria vir de `parametros_wall_1`
5. **var92** - Vem de `ValorTaxaMes`, deveria vir de `parametros_wall_4`
6. **var93** - Calculado com `var91`, deveria usar `parametros_wall_5`

### Ajustes Necessários:
7. **var44** - Precisa SOMAR todas as parcelas
8. **var45** - Adicionar lógica + conversão de formato
9. **var70** - Adicionar validação `DescricaoStatus` + conversão

---

**Total de Correções:** 8 variáveis (6 erros críticos + 2 ajustes)

---

## ✅ CORREÇÕES APLICADAS - 27/10/2025

**Status:** Concluído e pronto para commit

### Resumo das Alterações

Total de **50+ variáveis ajustadas** com foco em:
- Mudança de `var16` para `var19` como base de cálculos
- Criação de arrays para var93/var94/var103
- Simplificação de fórmulas complexas
- Remoção de cálculos duplicados

---

### Grupo 1: Parâmetros Base (var24-25)
- ✅ var25: `var16 * var24` → `var19 * var24`

### Grupo 2: Taxas Administração (var36-45)
- ✅ var37: `var16 * var36` → `var19 * var36`
- ✅ var38: `var16 - var37` → `var19 - var37`
- ✅ var40: `var39 * (1+var13)/2` → `var41 / var19`
- ✅ var41: `var38 * var40` → `var19 - var37 - var44`
- ✅ var42: `var38 - var41` → `= var44`
- ✅ var43: `data + param_18` → `DataFuturaPagamento` direto

### Grupo 3: Cálculos Wall (var48-96)
- ✅ var49: lógica complexa → `var50 * var19`
- ✅ var50: NOVA → `parametro_loja_23`
- ✅ var51: lógica complexa → `var52 * var19`
- ✅ var52: NOVA → `parametro_loja_25`
- ✅ var53: NOVA → `parametro_loja_27`
- ✅ var54: lógica complexa → `var53 * var19`
- ✅ var88: `var26 * var87` → `var87 * var19`
- ✅ var89: `parametro_uptal_1` → `ValorTaxaAdm` direto
- ✅ var90: NOVA → `var89 * var19`
- ✅ var92: `cópia var91` → `ValorTaxaMes` direto
- ✅ var93: valor único → Array `{"0": var91*(1+var13)/2, "A": var92*(1+var13)/2}`
- ✅ var94: valor único → Array `{"0": var93["0"]*var19, "A": var40}`
- ✅ var95: `var26 - var88 - var94["0"]` → `var19 - var90 - var94["A"]`
- ✅ var96: `data + param_uptal_3` → `var0 + 1 dia útil`

### Grupo 4: Variáveis Finais (var60-104)
- ✅ var60: array → `var19 - (param_12*var19) - (param_14*var19) + var56`
- ✅ var60A: NOVA → `var44`
- ✅ var61: array → `var60 - var33`
- ✅ var61A: NOVA → `var60A - var33`
- ✅ var62, 63, 64: ajustados para var61 direto
- ✅ var98: lógica complexa → `if var69=="Pendente" ? "Não Recebido" : var44`
- ✅ var99: `var98 - var95` → `var95 - var44`
- ✅ var102: condicional → `0` (ZERO fixo)
- ✅ var103: valor único → Array `{"0": var95-var42, "A": var103["0"]}`
- ✅ var104: condicional → `var37` direto

### Remoções de Código Legado
1. ❌ Recalculação de var93["A"] (linha ~811)
2. ❌ Recalculação de var94["A"] (linha ~802)
3. ❌ Cálculo de var94["B"] (linha ~805-807)
4. ❌ Cálculo antigo de var99 (linha ~827-834)
5. ❌ Cálculo duplicado de var90 (linha ~738-742)
6. ❌ Cálculo inicial duplicado de var98 (linha ~746)

### Verificação de Integridade
✅ Não há sobrescritas posteriores  
✅ Arrays têm estrutura correta  
✅ Dependências estão em ordem  
✅ Fórmulas seguem especificação

---

## 🔧 CORREÇÕES TÉCNICAS - 27/10/2025 (Pós-Deploy)

### 1️⃣ Problema: Ordem de Dependências (var40/41/42/44 vs var94)

**Erro:**
```
KeyError: 40
```

**Causa:**
- `var94["A"]` usa `valores[40]` (linha ~435)
- Mas `var40` só era calculada depois (linha ~687)

**Correção:**
- Movido cálculo de `var44`, `var42`, `var41`, `var40` para **antes** de `var94`
- Nova ordem: var44 → var42 → var41 → var40 → var93 → var94

---

### 2️⃣ Problema: Ordem de Dependências (var103/107 vs var95)

**Erro:**
- `var103` tentava usar `valores[95]` que ainda não existia
- `var103` estava na linha ~527, mas `var95` só na linha ~460

**Correção:**
- Movido `var103` e `var107` para **depois** de `var95`
- Nova ordem: var95 → var103 → var107

---

### 3️⃣ Problema: Função Inexistente

**Erro:**
```
ImportError: cannot import name 'proximo_dia_util' from 'comum.utilitarios.funcoes_gerais'
```

**Causa:**
- `var96` usava `proximo_dia_util()` que não existia
- Só havia `proxima_sexta_feira()`

**Correção:**
- Criada função `proximo_dia_util()` em `comum/utilitarios/funcoes_gerais.py`
- Lógica: data + 1 dia, pulando finais de semana

```python
def proximo_dia_util(data_str):
    data_obj = datetime.strptime(data_str, '%d/%m/%Y')
    data_obj += timedelta(days=1)
    while data_obj.weekday() >= 5:  # Pular sábado/domingo
        data_obj += timedelta(days=1)
    return data_obj.strftime('%d/%m/%Y')
```

---

### 4️⃣ Problema: Operação Matemática com String

**Erro:**
```
TypeError: unsupported operand type(s) for -: 'str' and 'decimal.Decimal'
```

**Causa:**
- `valores[98]` pode ser `"Não Recebido"` (string) quando status é "Pendente"
- Linha 800 tentava: `valores[98] - valores[44]` = `"Não Recebido" - 108.9`

**Correção:**
- Adicionada verificação antes de usar `valores[98]` em cálculo

```python
# ANTES:
if valores[102] == "Não Recebido":
    valores[107]["A"] = 0
else:
    valores[107]["A"] = valores[98] - valores[44]  # ERRO se var98 for string!

# DEPOIS:
if valores[102] == "Não Recebido" or valores[98] == "Não Recebido":
    valores[107]["A"] = 0
else:
    valores[107]["A"] = valores[98] - valores[44]  # Seguro
```

---

### ✅ Commits Aplicados

1. `fix: mover cálculo var40/41/42/44 antes de var94`
2. `fix: corrigir ordem de cálculo var103/107 (dependem de var95)`
3. `feat: adicionar função proximo_dia_util para var96`
4. `fix: adicionar verificação var98 string em var107["A"]`

---

### 🚦 Status Final

✅ Ordem de dependências corrigida  
✅ Funções utilitárias criadas  
✅ Validações de tipo adicionadas  
✅ Pronto para testes em produção

---

## 🔧 CORREÇÕES ADICIONAIS - 27/10/2025 20:50

### 5️⃣ Problema: var43 - Data Excedendo VARCHAR(20)

**Erro:**
```
DataError: (1406, "Data too long for column 'var43' at row 1")
```

**Causa:**
- `var43` salvava `DataFuturaPagamento` em formato ISO completo: `2025-10-25T22:19:47.706` (23 caracteres)
- Campo `var43` no banco: `VARCHAR(20)` (limite de 20 caracteres)

**Correção (linhas 362-380):**
```python
# ANTES:
valores[43] = str(data_futura_pag)  # ISO completo = 23 chars

# DEPOIS:
# Converter ISO para DD/MM/YYYY = 10 chars
data_futura_pag = dados_linha.get('DataFuturaPagamento')
if data_futura_pag and str(data_futura_pag) not in ['None', '0001-01-01T00:00:00']:
    try:
        if isinstance(data_futura_pag, str):
            if data_futura_pag.startswith('0001-01-01'):
                valores[43] = ''
            else:
                data_obj = dt.strptime(data_futura_pag[:10], '%Y-%m-%d')
                valores[43] = data_obj.strftime('%d/%m/%Y')  # 25/10/2025
        else:
            valores[43] = data_futura_pag.strftime('%d/%m/%Y')
    except:
        valores[43] = ''
else:
    valores[43] = ''
```

**Resultado:**
- Entrada: `2025-10-25T22:19:47.706`
- Saída: `25/10/2025` (10 caracteres)
- ✅ Cabe em VARCHAR(20)

---

### 6️⃣ Problema: var98 String em Operações Matemáticas

**Erro 1 - Linha 813 (var107):**
```
TypeError: unsupported operand type(s) for -: 'str' and 'decimal.Decimal'
Traceback: valores[107]["A"] = valores[98] - valores[44]
```

**Erro 2 - Linha 952 (var119):**
```python
if valores[98] >= (valores[42] + valores[115]["0"]):  # ERRO: "Não Recebido" >= Decimal
```

**Erro 3 - Linha 1062 (var128):**
```python
valores[128] = valores[98] - valores[42]  # ERRO: "Não Recebido" - Decimal
```

**Causa:**
- `var98` pode ser string `"Não Recebido"` quando `var69 == "Pendente"` (linha 803)
- Tentativas de usar `var98` em operações matemáticas sem validar tipo

**Correção 1 - var107 (linha 810-813):**
```python
# ANTES:
if valores[102] == "Não Recebido":
    valores[107]["A"] = 0
else:
    valores[107]["A"] = valores[98] - valores[44]  # ERRO!

# DEPOIS:
if valores[102] == "Não Recebido" or valores[98] == "Não Recebido":
    valores[107]["A"] = self._format_decimal(0, 2)
else:
    valores[107]["A"] = self._format_decimal(valores[98] - valores[44], 2)
```

**Correção 2 - var119 (linha 952-961):**
```python
# ANTES:
else:
    if valores[98] >= (valores[42] + valores[115]["0"]):  # ERRO!
        ...

# DEPOIS:
else:
    # Verificar se var98 não é string antes de usar em operação matemática
    if valores[98] == "Não Recebido":
        valores[119] = "Pendente"
    elif valores[98] >= (valores[42] + valores[115]["0"]):
        if date_provided1 <= date_provided2:
            valores[119] = "Pagar. Recebido um pouco a menor, mas dentro do prazo"
        else:
            valores[119] = "Pagar. Recebido um pouco a menor e atrasado"
    else:
        valores[119] = "Não Pagar. Valor recebido menor do que o valor a pagar ao EC"
```

**Correção 3 - var128 (linha 1061-1066):**
```python
# ANTES:
if valores[98] == "Não Recebido":
    valores[128] = valores[42]
else:
    valores[128] = valores[98] - valores[42]  # ERRO se var98 for outra string!

# DEPOIS:
# var98 pode ser string "Não Recebido" quando status é Pendente
if valores[98] == "Não Recebido" or isinstance(valores[98], str):
    valores[128] = valores[42]
else:
    valores[128] = self._format_decimal(valores[98] - valores[42], 2)
```

---

### ✅ Commits Aplicados (27/10/2025 20:50)

1. ✅ `fix: converter var43 de ISO para DD/MM/YYYY (cabe em VARCHAR20)`
2. ✅ `fix: validar var98 string antes de operação matemática em var119`
3. ✅ `fix: validar var98 string antes de operação matemática em var128`
4. ✅ `fix: validar var98 string em var107["A"]` (já aplicado anteriormente)

---

### 🎯 Impacto das Correções

**var43:**
- ❌ Antes: 23 caracteres → erro SQL
- ✅ Depois: 10 caracteres → salva com sucesso

**var98 (3 locais corrigidos):**
- ❌ Antes: TypeError em operações matemáticas
- ✅ Depois: Validação de tipo antes de calcular

**Registros Afetados:**
- ID=336415, ID=340190, ID=342104 (exemplo dos logs)
- Todos os registros com `DescricaoStatusPagamento = 'Pendente'`

---

### 🚦 Status Pós-Correções

✅ var43 não excede mais VARCHAR(20)  
✅ var98 validada em todas operações matemáticas  
✅ var107, var119, var128 seguras contra TypeError  
✅ Pronto para reprocessamento dos registros com erro
