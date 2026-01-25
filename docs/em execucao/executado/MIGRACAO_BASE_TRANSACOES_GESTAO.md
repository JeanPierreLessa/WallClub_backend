# Migração: BaseTransacoesGestao → base_transacoes_unificadas

## Status Atual: ✅ 100% COMPLETO

### ✅ Migrado (inserem em base_transacoes_unificadas)
- **Pinbank Wallet** - `services_carga_base_unificada_pos.py`
- **Pinbank Credenciadora** - `services_carga_base_unificada_credenciadora.py`
- **Pinbank Checkout** - `services_carga_base_unificada_checkout.py`
- **POSP2 (Wallet/TEF)** - `services_transacao.py` → método `_inserir_base_transacoes_unificadas()`
- **Own Financial** - `services_carga_base_unificada_pos.py`
- **Calculadora Base Credenciadora** - Consulta `base_transacoes_unificadas`
- **Gestão Financeira** - Relatórios consultam `base_transacoes_unificadas`

### ✅ Model Removido

#### 1. Own Financial ✅ MIGRADO
**Arquivos:**
- `adquirente_own/cargas_own/services_carga_base_gestao_own.py`

**Ação:**
- ✅ Renomeado classe para `CargaBaseUnificadaOwnService`
- ✅ Migrado `_inserir_valores_base_gestao()` para inserir em `base_transacoes_unificadas`
- ✅ Removidos métodos deprecated
- ⚠️ Pendente: `services_carga_transacoes.py` e `services_carga_liquidacoes.py` (não estão em produção)

#### 2. POSP2 TEF ✅ MIGRADO
**Arquivos:**
- `posp2/services_transacao.py` → método `_inserir_base_transacoes_gestao()`

**Ação:**
- ✅ Removida chamada a `_inserir_base_transacoes_gestao()`
- ✅ Método comentado como DEPRECATED
- ✅ Usa apenas `_inserir_base_transacoes_unificadas()`

#### 3. Gestão Financeira (Consultas) ✅ MIGRADO
**Arquivos:**
- `gestao_financeira/services.py`

**Ação:**
- ✅ Migrado `listar_recebimentos()` para `base_transacoes_unificadas`
- ✅ Migrado `obter_relatorio_financeiro()` para `base_transacoes_unificadas`
- ✅ Substituído ORM por queries SQL diretas

#### 4. Calculadora Base Credenciadora ✅ MIGRADO
**Arquivos:**
- `parametros_wallclub/calculadora_base_credenciadora.py`

**Ação:**
- ✅ Migrado consulta de `BaseTransacoesGestao` para `base_transacoes_unificadas`
- ✅ Preservada lógica de datas (var45)

---

## Plano de Migração

### Fase 1: Own Financial ⏳
1. Criar `services_carga_base_unificada_own.py`
2. Implementar método `carregar_valores_primarios()`
3. Usar `CalculadoraBaseCredenciadora` com `tabela='own'`
4. Criar comando `carga_base_unificada_own.py`
5. Testar com `--limite=10`
6. Atualizar `services_carga_liquidacoes.py` para consultar `base_transacoes_unificadas`

### Fase 2: POSP2 TEF ⏳
1. Verificar se `_inserir_base_transacoes_unificadas()` já está sendo usado
2. Remover chamadas a `_inserir_base_transacoes_gestao()`
3. Testar transações TEF

### Fase 3: Consultas e Relatórios ⏳
1. Migrar `gestao_financeira/services.py`
2. Migrar `calculadora_base_credenciadora.py`
3. Testar relatórios e filtros

### Fase 4: Limpeza Final ⏳
1. Verificar que nenhum código ativo usa `BaseTransacoesGestao`
2. Deprecar model (comentar, não deletar)
3. Adicionar comentário: "DEPRECATED - usar base_transacoes_unificadas"
4. Manter tabela no banco (não dropar)

---

## Comandos de Teste

```bash
# Own Financial
docker exec -it wallclub-pos python manage.py carga_base_unificada_own --limite=10

# Verificar dados
SELECT COUNT(*) FROM base_transacoes_unificadas WHERE tipo_operacao = 'Own';

# POSP2 TEF
# Fazer transação TEF via terminal e verificar inserção

# Consultas
# Testar relatórios no portal admin
```

---

## Notas Importantes

1. **Não deletar tabela `baseTransacoesGestao`** - manter para histórico
2. **Não deletar model** - apenas deprecar
3. **Triggers** - verificar se há triggers que dependem da tabela
4. **Relatórios legados** - podem ainda consultar a tabela antiga
5. **Backup** - garantir backup antes de qualquer alteração

---

## Checklist Final

- [ ] Own Financial migrado
- [ ] POSP2 TEF migrado
- [ ] Consultas migradas
- [ ] Calculadora migrada
- [ ] Testes realizados
- [ ] Model depreciado
- [ ] Documentação atualizada
