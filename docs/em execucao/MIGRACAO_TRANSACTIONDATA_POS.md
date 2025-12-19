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
| `transactiondata_own` | `TRDataOwnService` | ✅ Ativo (legado) | Own |
| `transactiondata_pos` | `TRDataPosService` | 🚧 Em testes | Pinbank + Own |

### Estratégia de Migração
1. ✅ Criar `transactiondata_pos` e `TRDataPosService`
2. ✅ Ajustar `CalculadoraBaseGestao` para aceitar `info_loja` opcional
3. 🚧 Testar transações Own em `transactiondata_pos`
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

### Longo Prazo
- [ ] Deprecar `TRDataService` (Pinbank legado)
- [ ] Deprecar `TRDataOwnService` (Own legado)
- [ ] Remover tabelas `transactiondata` e `transactiondata_own`

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

**Última Atualização:** 19/12/2025 11:40  
**Responsável:** Jean Lessa
