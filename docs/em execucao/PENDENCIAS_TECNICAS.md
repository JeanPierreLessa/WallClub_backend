# PENDÊNCIAS TÉCNICAS - RISK ENGINE

**Data:** 02/11/2025 21:27  
**Status:** 🔴 BLOQUEADOR EM PRODUÇÃO

---

## 🚨 PROBLEMA ATUAL - ERRO 500 NO /api/antifraude/analyze/

### Contexto
Risk Engine (`wallclub-riskengine-monorepo`) está retornando **500 Internal Server Error** para todas as chamadas do POS ao endpoint `/api/antifraude/analyze/`.

### Sintomas
```
[2025-11-02 21:25:32] [ERROR] Erro HTTP ao chamar antifraude: 500
[2025-11-02 21:25:32] [ERROR] Response text: TypeError at /api/antifraude/analyze/
```

### Causa Raiz
Decorator `@handle_api_errors` (do `wallclub_core`) tenta acessar `LogParametro` model que **NÃO EXISTE** no Risk Engine:

```
Erro ao verificar se log está habilitado para 'api_error': 
Model class wallclub_core.models.LogParametro doesn't declare an explicit 
app_label and isn't in an application in INSTALLED_APPS.
```

### O que NÃO funcionou
1. ❌ Remover `@handle_api_errors` → gera **TypeError** (erro diferente, não resolveu)
2. ❌ Adicionar `wallclub_core` ao INSTALLED_APPS → não é apropriado

### Próximos Passos
1. **Ver TypeError completo:**
   ```bash
   docker logs wallclub-riskengine-monorepo --since "2025-11-02T21:25:00" | grep -A 50 "TypeError"
   ```

2. **Opções de Solução:**
   - **A)** Criar versão simplificada do `@handle_api_errors` sem dependência de `LogParametro`
   - **B)** Fazer o decorator verificar se `LogParametro` existe antes de usar
   - **C)** Usar try/except manual nos endpoints do Risk Engine

---

## 📋 OUTRAS PENDÊNCIAS RESOLVIDAS HOJE

### ✅ OAuth Removido da Rede Interna
- **Problema:** Comunicação interna Docker exigia OAuth (404 no `/oauth/token/`)
- **Solução:** Removido `@require_oauth_token` de todos os endpoints internos
- **Arquivos Alterados:**
  - `services/riskengine/antifraude/views_api.py` (4 decorators removidos)
  - `services/riskengine/antifraude/views.py` (1 decorator removido - dashboard)
  - `services/django/posp2/services_antifraude.py` (removido método OAuth)
  - `services/django/checkout/services_antifraude.py` (removido método OAuth)
  - `services/django/portais/admin/services_antifraude.py` (URL interna)

### ✅ ALLOWED_HOSTS Corrigido
- **Problema:** 400 Bad Request por hostname incorreto
- **Solução:** Adicionado `wallclub-riskengine-monorepo` ao ALLOWED_HOSTS

### ✅ Portal Admin Antifraude
- **Status:** ✅ Funcionando
- **URL:** https://apidj.wallclub.com.br/portal_admin/antifraude/

---

## 🎯 PRIORIDADE IMEDIATA

1. **CRÍTICO:** Resolver TypeError no `/api/antifraude/analyze/`
2. Validar transações POS end-to-end
3. Validar Checkout Web
4. Monitorar logs de produção

---

## 📝 NOTAS TÉCNICAS

### Arquitetura OAuth - Decisão
- **Rede Interna Docker:** SEM OAuth (comunicação direta container-to-container)
- **Rede Externa/Pública:** COM OAuth (quando necessário no futuro)
- **Justificativa:** Rede interna é isolada, OAuth adiciona complexidade desnecessária

### Risk Engine - Limitações
- Não tem `django.contrib.admin` apps do Django principal
- Não tem models do `wallclub_core` (LogParametro, etc)
- Decorators genéricos devem verificar dependências antes de usar
