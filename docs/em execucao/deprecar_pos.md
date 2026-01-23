# Depreciação de Endpoints POS

Documento para rastrear endpoints e funcionalidades POS que serão depreciados.

## Status

- 🟡 **Planejado**: Depreciação planejada, ainda não iniciada
- 🟠 **Em Progresso**: Migração em andamento
- 🔴 **Depreciado**: Endpoint marcado como deprecated, mas ainda funcional
- ⚫ **Removido**: Endpoint completamente removido

---

## Endpoints a Depreciar

### 1. `/api/v1/posp2/transaction_sync_service/` 🟡

**Status**: Planejado
**Motivo**: Grava em tabela antiga `posp2_transactions` que não está integrada ao fluxo principal
**Substituído por**: `/api/v1/posp2/transactiondata_pos_backsync/`
**Data Planejada**: A definir

**Diferenças**:
- **Antigo**: Grava em `posp2_transactions` (tabela isolada)
- **Novo**: Grava em `transactiondata_pos_backsync` (integrado com `transactiondata_pos`)

**Ações Necessárias**:
- [ ] Atualizar app Android para usar novo endpoint
- [ ] Testar novo endpoint em produção
- [ ] Marcar endpoint antigo como deprecated
- [ ] Remover endpoint antigo após período de transição

---

### 2. `/api/v1/posp2/trdata/` 🟡

**Status**: Planejado
**Motivo**: Endpoint genérico legado, substituído por endpoints específicos por gateway
**Substituído por**:
- `/api/v1/posp2/trdata_pinbank/` (Pinbank)
- `/api/v1/posp2/trdata_own/` (Own)

**Data Planejada**: A definir

**Diferenças**:
- **Antigo**: Usa `TRDataService` (legado), não tem suporte completo a cupons e cashback centralizado
- **Novo**: Usa `TRDataPosService` (unificado), suporte completo a cupons, cashback, antifraude

**Problemas Identificados no Antigo**:
- Erro: `cannot access local variable 'nsu_pinbank' where it is not associated with a value`
- Não tem integração com antifraude
- Não tem suporte completo a cupons
- Não tem cashback centralizado

**Ações Necessárias**:
- [ ] Identificar quais apps/clientes ainda usam `/trdata/`
- [ ] Migrar todos para endpoints específicos
- [ ] Marcar endpoint antigo como deprecated
- [ ] Remover endpoint antigo após período de transição

---

## Tabelas a Depreciar

### 1. `posp2_transactions` 🟡

**Status**: Planejado
**Motivo**: Tabela isolada, não integrada ao fluxo principal de transações
**Substituída por**: `transactiondata_pos_backsync`

**Ações Necessárias**:
- [ ] Migrar dados históricos se necessário
- [ ] Atualizar apps para usar nova tabela
- [ ] Remover tabela após período de transição

---

### 2. `transactiondata` (legado Pinbank) 🟠

**Status**: Em Progresso
**Motivo**: Tabela legada Pinbank, substituída por `transactiondata_pos` (unificada)
**Substituída por**: `transactiondata_pos`

**Status Atual**:
- Trigger ativo sincronizando com `transactiondata_pos`
- Ainda recebe dados do endpoint `/trdata/` (legado)

**Ações Necessárias**:
- [ ] Depreciar endpoint `/trdata/`
- [ ] Validar que todos os dados estão em `transactiondata_pos`
- [ ] Remover trigger de sincronização
- [ ] Remover tabela após validação completa

---

## Cronograma de Depreciação

### Fase 1: Criação de Substitutos ✅
- [x] Criar endpoint `transactiondata_pos_backsync`
- [x] Criar tabela `transactiondata_pos_backsync`
- [x] Criar service `TransactionDataPosBacksyncService`

### Fase 2: Testes e Validação (Próxima)
- [ ] Testar novo endpoint em dev
- [ ] Testar novo endpoint em produção
- [ ] Validar idempotência
- [ ] Validar performance

### Fase 3: Migração de Clientes
- [ ] Atualizar app Android Pinbank
- [ ] Atualizar app Android Own
- [ ] Monitorar uso dos endpoints antigos

### Fase 4: Marcação como Deprecated
- [ ] Adicionar warning nos endpoints antigos
- [ ] Atualizar documentação
- [ ] Notificar desenvolvedores

### Fase 5: Período de Transição
- [ ] Manter endpoints antigos funcionais por 3 meses
- [ ] Monitorar logs de uso
- [ ] Alertar clientes que ainda usam endpoints antigos

### Fase 6: Remoção Final
- [ ] Remover endpoints antigos
- [ ] Remover tabelas antigas
- [ ] Atualizar documentação final

---

## Notas

- Sempre manter período de transição de pelo menos 3 meses
- Monitorar logs para identificar uso de endpoints antigos
- Comunicar mudanças com antecedência aos desenvolvedores
- Manter backward compatibility durante período de transição

---

**Última Atualização**: 23/01/2026
**Responsável**: Equipe Backend
