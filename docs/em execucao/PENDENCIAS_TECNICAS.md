# PENDÊNCIAS TÉCNICAS - RISK ENGINE

**Data:** 03/11/2025 19:40  
**Status:** ✅ TODAS RESOLVIDAS

---

## ✅ PROBLEMA RESOLVIDO - ERRO 500 NO /api/antifraude/analyze/

### Contexto
Risk Engine retornava **500 Internal Server Error** para todas as chamadas do POS ao endpoint `/api/antifraude/analyze/`.

### Causa Raiz Identificada
**Uso incorreto do decorator `@validate_required_params`:**

```python
# ❌ ERRADO (linha 22 views_api.py)
@validate_required_params(['cpf', 'valor', 'modalidade'])  # Lista

# ✅ CORRETO
@validate_required_params('cpf', 'valor', 'modalidade')    # Args individuais
```

**Erro no decorator:**
```python
# wallclub_core/decorators/api_decorators.py (linha 64)
data = json.loads(request.body)  # ❌ Body já consumido pelo DRF
```

### Solução Implementada

**1. Corrigir decorator para funcionar com DRF:**
```python
# Detectar se é DRF (request.data) ou Django tradicional (request.body)
if hasattr(request, 'data'):
    data = request.data  # DRF já processou
else:
    data = json.loads(request.body)  # Django tradicional
```

**2. Corrigir uso nos endpoints:**
```python
# views_api.py linhas 22 e 243
@validate_required_params('cpf', 'valor', 'modalidade')  # Sem colchetes
@validate_required_params('auth_id')                      # Sem colchetes
```

### Resultado
```
✅ HTTP 200 (era 500)
✅ Score calculado: 10/100
✅ Decisão: APROVADO
✅ Tempo: 297ms
✅ Regras acionadas: MaxMind + Whitelist
```

### Arquivos Modificados
- `services/core/wallclub_core/decorators/api_decorators.py`
- `services/riskengine/antifraude/views_api.py`

---

## ✅ RESOLVIDO - LogParametro (03/11/2025 19:40)

### Situação Anterior
`log_control.py` tentava importar `LogParametro` model (linha 39), mas Risk Engine não tinha `wallclub_core` no `INSTALLED_APPS`.

**Comportamento anterior:**
- ✅ Não bloqueava operação (fallback funcionava)
- ⚠️ Gerava warning nos logs

### Solução Implementada
Adicionado `wallclub_core` ao `INSTALLED_APPS` do Risk Engine:

```python
# services/riskengine/riskengine/settings.py (linha 31)
INSTALLED_APPS = [
    # ...
    # Shared core
    'wallclub_core',
    # ...
]
```

**Resultado:**
- ✅ Import funciona sem warnings
- ✅ LogParametro model acessível
- ✅ Mantém consistência com Django service

---

## 📋 HISTÓRICO - PROBLEMAS RESOLVIDOS HOJE

### ✅ Erro 500 no /api/antifraude/analyze/ (22:00)
- **Causa:** Decorator `@validate_required_params` recebendo lista em vez de args
- **Solução:** Corrigir decorator para DRF + remover colchetes nos decorators
- **Resultado:** HTTP 200, análise funcionando perfeitamente

### ✅ OAuth Removido da Rede Interna
- **Problema:** Comunicação interna Docker exigia OAuth (404 no `/oauth/token/`)
- **Solução:** Removido `@require_oauth_token` de endpoints internos

### ✅ ALLOWED_HOSTS Corrigido
- **Problema:** 400 Bad Request por hostname incorreto
- **Solução:** Adicionado `wallclub-riskengine-monorepo` ao ALLOWED_HOSTS

### ✅ Portal Admin Antifraude
- **URL:** https://apidj.wallclub.com.br/portal_admin/antifraude/

---

## 📝 NOTAS TÉCNICAS

### Decorators DRF vs Django
- **DRF (@api_view):** Usa `request.data` (body já processado)
- **Django tradicional:** Precisa `json.loads(request.body)`
- **Solução:** Detectar com `hasattr(request, 'data')`

### Arquitetura OAuth
- **Rede Interna Docker:** SEM OAuth (comunicação direta)
- **Rede Externa/Pública:** COM OAuth (quando necessário)

### Risk Engine - Considerações
- Não tem `wallclub_core` no `INSTALLED_APPS`
- Import de models do core pode gerar warnings (não bloqueantes)
- Decorators devem ser resilientes a dependências ausentes
