# PLANO DE REFATORAÇÃO: BASE TRANSAÇÕES UNIFICADAS

**Objetivo:** Eliminar duplicação de linhas para transações parceladas e melhorar estrutura da base de gestão.

**Status:** Em Planejamento
**Data Início:** 10/12/2024

---

## 📊 PROBLEMA ATUAL

### Duplicação de Linhas
- **Pinbank:** Transação com N parcelas = N linhas no `pinbankExtratoPOS` (diferem por `NumeroParcela`)
- **Base Gestão:** N linhas **idênticas** (exceto `idFilaExtrato` e `id`)
- **Impacto:** Queries complexas com `ROW_NUMBER() OVER (PARTITION BY var9)` ou `COUNT(DISTINCT var9)`

### Nomenclatura Confusa
```sql
-- Campos atuais (nomes ruins):
valor_original    -- Valor efetivamente pago (com desconto)
originalAmount    -- Valor que o cliente pagaria (sem desconto)
amount            -- Igual a originalAmount
```

**Problema:** Nomes levam a conclusões erradas sobre o que cada campo representa.

---

## 🎯 SOLUÇÃO PROPOSTA

### 1. Nova Tabela: `base_transacoes_unificadas`

**Estrutura:**
- **Manter:** Todos os campos `var0` até `var130`
- **Manter:** `id`, `tipo_operacao`, `adquirente`, `data_transacao`, `created_at`, `updated_at`
- **Remover:** `idFilaExtrato`, `banco`
- **Adicionar:** Campos faltantes (ver seção Gaps)

**Regra:** 1 linha por transação (NSU único), não por parcela.

### 2. Controle de Carga Paralelo

**Problema:** `pinbankExtratoPOS.lido` controla processo atual  
**Solução:** Adicionar coluna `processado` para controle paralelo

```sql
-- Pinbank (✅ EXECUTADO em 10/12/2024)
ALTER TABLE pinbankExtratoPOS ADD COLUMN processado TINYINT DEFAULT 0 after Lido;

-- Own (campo já existe e está em uso - não alterar)
-- Campo processado já controla se transação foi processada para base gestão
```

**Benefício:** Validar cargas em paralelo sem impactar processo atual.

**Escopo Inicial:** Focar apenas em **Pinbank** (produção). Own será ajustado depois (não está em produção).

---

## 📋 GAPS IDENTIFICADOS

### Campos Usados via JOIN que NÃO existem como var*

| Campo | Uso Atual | Necessário? | Observação |
|-------|-----------|-------------|------------|
| `card_number` | Extrato (formatar "Cartão final XXX") | ✅ Sim | Gap real |
| `authorization_code` | Comprovante (autwall) | ✅ Sim | Existe em Pinbank e Own |
| `amount` | Extrato (valor_decimal) | ⚠️ Revisar | Igual a `originalAmount` |
| `valor_cashback` | Comprovante | ⚠️ Pendente | Aguardar refatoração cashback/cupom |

### Nomenclatura a Corrigir (transactiondata_pos)

**Proposta de nomes claros:**
```sql
valor_sem_desconto DECIMAL(10,2)  -- originalAmount (valor cheio)
valor_com_desconto DECIMAL(10,2)  -- valor_original (valor pago)
valor_centavos BIGINT              -- amount (em centavos)
```

**Ação:** Verificar payload POS para ajustar nomes na `transactiondata_pos`.

---

## 🔧 ETAPAS DE EXECUÇÃO

### FASE 1: Preparação - Pinbank (1-2 dias)
- [x] 1.1. Criar coluna `processado` em `pinbankExtratoPOS` ✅
- [x] 1.2. Analisar payload POS para nomenclatura correta ✅
- [x] 1.3. Definir estrutura final de `base_transacoes_unificadas` ✅
- [x] 1.4. Criar script SQL de criação da tabela ✅

### FASE 2: Implementação Cargas - Pinbank (3-5 dias)
- [x] 2.1. Criar `services_carga_base_unificada_pos.py` ✅
  - Agrupar por NSU (1 linha por transação)
  - Usar `processado` para controle
  - Popular campos novos (card_number, authorization_code, amount, valor_cashback)
  - Converter strings vazias em NULL
  - Popular `data_transacao` a partir de var0 + var1
- [ ] 2.2. Refatorar `services_carga_checkout.py`
  - Agrupar por NSU
  - Usar `processado` para controle
- [x] 2.3. Criar `services_carga_base_unificada_credenciadora.py` ✅
  - Agrupar por NSU
  - Usar `processado` para controle
  - Filtro DataTransacao >= '2025-10-01'

**Nota:** Own será implementado em fase posterior (não está em produção).

### FASE 3: Validação Paralela - Pinbank (2-3 dias)
- [ ] 3.1. Executar cargas em paralelo (base antiga + nova)
- [ ] 3.2. Criar queries de comparação
- [ ] 3.3. Validar totalizadores (COUNT, SUM)
- [ ] 3.4. Validar queries críticas dos portais

### FASE 4: Refatoração Portais - Pinbank (5-7 dias)
- [ ] 4.1. Portal Admin
  - `views_transacoes.py` - Remover `ROW_NUMBER()`
  - `views_rpr.py` - Remover `ROW_NUMBER()`
  - `services_rpr.py` - Simplificar queries
- [ ] 4.2. Portal Lojista
  - `views_vendas.py` - Remover `ROW_NUMBER()` (6 queries)
  - `views_cancelamentos.py` - Remover `ROW_NUMBER()` (3 queries)
  - `services_recebimentos.py` - Simplificar GROUP BY
- [ ] 4.3. APIs Mobile
  - `apps/transacoes/services.py` - Remover JOINs
  - Usar campos da base unificada

### FASE 5: Migração Gradual (2-3 dias)
- [ ] 5.1. Feature flag para alternar entre bases
- [ ] 5.2. Testes em produção com % de tráfego
- [ ] 5.3. Monitoramento de performance
- [ ] 5.4. Rollback plan

### FASE 6: Finalização (1-2 dias)
- [ ] 6.1. Remover código legado
- [ ] 6.2. Remover `baseTransacoesGestao` (após validação)
- [ ] 6.3. Documentar mudanças
- [ ] 6.4. Atualizar queries de relatórios

---

## 📈 IMPACTOS ESPERADOS

### Performance
- ✅ Elimina `ROW_NUMBER() OVER (PARTITION BY var9)` (16 queries)
- ✅ Elimina `COUNT(DISTINCT var9)` (5 queries)
- ✅ Elimina JOINs com `transactiondata` (4 queries)
- ✅ Redução de ~50% no tamanho da tabela

### Manutenibilidade
- ✅ Queries mais simples e diretas
- ✅ Nomenclatura mais clara
- ✅ Menos risco de erros em agregações

---

## 🚨 RISCOS E MITIGAÇÕES

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Queries legadas quebram | Alto | Manter base antiga em paralelo |
| Perda de dados na migração | Crítico | Validação exaustiva antes de remover base antiga |
| Performance pior que esperada | Médio | Testes de carga antes de migração completa |
| Relatórios externos quebram | Alto | Mapear todos os consumidores da base |

---

## 📝 ARQUIVOS IMPACTADOS

### Crítico (Cargas)
- `pinbank/cargas_pinbank/services_carga_base_gestao_pos.py`
- `pinbank/cargas_pinbank/services_carga_checkout.py`
- `pinbank/cargas_pinbank/services_carga_credenciadora.py`
- `adquirente_own/cargas_own/services_carga_base_gestao_own.py`

### Alto (Portais)
- `portais/admin/views_transacoes.py`
- `portais/admin/views_rpr.py`
- `portais/lojista/views_vendas.py`
- `portais/lojista/views_cancelamentos.py`

### Médio (APIs)
- `apps/transacoes/services.py`
- `posp2/services_transacao.py`

**Total:** 38 arquivos identificados na varredura

---

## 🔍 PRÓXIMOS PASSOS IMEDIATOS

1. **Analisar payload POS** para definir nomenclatura correta
2. **Definir estrutura SQL final** de `base_transacoes_unificadas`
3. **Criar script de migração** de dados históricos (se necessário)
4. **Validar com time** antes de iniciar implementação

---

## 📝 CHANGELOG

### 10/12/2024 - Implementação Inicial

#### ✅ Concluído
1. **Estrutura da tabela `base_transacoes_unificadas`**
   - Criada com todos os campos var0-var130
   - Campos adicionais: card_number, authorization_code, amount, valor_cashback
   - Índices: var9 (NSU), data_transacao, tipo_operacao
   - Alterado var13 de DECIMAL(8,2) para INT (número de parcelas)

2. **Services de carga criados**
   - `services_carga_base_unificada_pos.py` - POS/transactiondata
   - `services_carga_base_unificada_credenciadora.py` - Credenciadora
   - Management commands criados para ambos

3. **Melhorias implementadas**
   - Conversão de strings vazias em NULL
   - População automática de `data_transacao` (var0 + var1)
   - Filtro de transações >= 01/10/2025
   - Processamento em lotes de 100 registros
   - Marca todas as parcelas do NSU como processadas (processado=1)

4. **Parâmetros históricos (em andamento)**
   - Criado `busca_plano_historico()` no ParametrosService
   - CalculadoraBaseGestao atualizada para usar busca_plano_historico
   - CalculadoraBaseCredenciadora atualizada para usar busca_plano_historico
   - **Pendente:** Implementar lógica real de busca de parâmetros vigentes na data da transação

#### ⚠️ Pendente
- Implementar lógica de parâmetros históricos dentro de `busca_plano_historico()`
- Testar carga completa (sem limite)
- Validar dados entre base antiga e nova
- Refatorar services_carga_checkout.py

---

**Última Atualização:** 10/12/2024 13:54
**Responsável:** [A definir]
