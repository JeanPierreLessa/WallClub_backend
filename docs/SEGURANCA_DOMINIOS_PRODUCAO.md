# SEGURANÇA: DOMÍNIOS E ORIGENS - PRODUÇÃO vs DESENVOLVIMENTO

**Data:** 22/11/2025  
**Prioridade:** 🔴 ALTA - Segurança em Produção  
**Status:** ⚠️ PENDENTE - Requer ajustes antes de produção

---

## 🚨 PROBLEMA IDENTIFICADO

Atualmente temos domínios de desenvolvimento hardcoded em vários lugares do código, o que representa um **risco de segurança em produção**.

**Exemplo:**
```python
allowed_domains = [
    'wallclub.com.br',
    'apidj.wallclub.com.br',
    'localhost',  # ❌ DESENVOLVIMENTO
    '127.0.0.1',  # ❌ DESENVOLVIMENTO
    'checkout.wallclub.local',  # ❌ DESENVOLVIMENTO
]
```

---

## 📋 LOCAIS QUE PRECISAM SER AJUSTADOS

### 1. **CORS Manual - Checkout 2FA** 🔴 CRÍTICO
**Arquivo:** `services/django/checkout/link_pagamento_web/views_2fa.py`  
**Linhas:** 37-43

**Problema:** Domínios de desenvolvimento hardcoded
```python
allowed_domains = [
    'wallclub.com.br',
    'apidj.wallclub.com.br',
    'localhost',  # ❌ DESENVOLVIMENTO
    '127.0.0.1',  # ❌ DESENVOLVIMENTO
    'checkout.wallclub.local',  # ❌ DESENVOLVIMENTO
]
```

**Solução:**
```python
from django.conf import settings

# Domínios permitidos (produção)
allowed_domains = [
    'wallclub.com.br',
    'wccheckout.wallclub.com.br',
    'checkout.wallclub.com.br',
]

# Adicionar domínios de desenvolvimento apenas se DEBUG=True
if settings.DEBUG:
    allowed_domains.extend([
        'localhost',
        '127.0.0.1',
        'checkout.wallclub.local',
        'apidj.wallclub.com.br',
    ])
```

---

### 2. **CSRF_TRUSTED_ORIGINS - Portais** 🔴 CRÍTICO
**Arquivo:** `services/django/wallclub/settings/portais.py`  
**Linhas:** 77-90

**Problema:** HTTP e HTTPS hardcoded juntos
```python
CSRF_TRUSTED_ORIGINS = [
    'http://admin.wallclub.com.br',  # ❌ HTTP em produção
    'http://wcadmin.wallclub.com.br',  # ❌ HTTP em produção
    'https://admin.wallclub.com.br',
    'https://wcadmin.wallclub.com.br',
    # ...
]
```

**Solução:**
```python
# Produção (apenas HTTPS)
CSRF_TRUSTED_ORIGINS = [
    'https://admin.wallclub.com.br',
    'https://wcadmin.wallclub.com.br',
    'https://vendas.wallclub.com.br',
    'https://wcvendas.wallclub.com.br',
    'https://lojista.wallclub.com.br',
    'https://wclojista.wallclub.com.br',
]

# Desenvolvimento (adicionar HTTP)
if DEBUG:
    CSRF_TRUSTED_ORIGINS.extend([
        'http://admin.wallclub.com.br',
        'http://wcadmin.wallclub.com.br',
        'http://localhost:8005',
        'http://127.0.0.1:8005',
    ])
```

---

### 3. **CSRF_TRUSTED_ORIGINS - Production** 🔴 CRÍTICO
**Arquivo:** `services/django/wallclub/settings/production.py`  
**Linhas:** 37-41

**Problema:** IP interno AWS hardcoded
```python
CSRF_TRUSTED_ORIGINS = [
    'https://api.wallclub.com.br',
    'https://apidj.wallclub.com.br',
    'http://ip-10-0-1-46:8000',  # ❌ IP INTERNO AWS
]
```

**Solução:** Remover IP interno
```python
CSRF_TRUSTED_ORIGINS = [
    'https://api.wallclub.com.br',
    'https://apidj.wallclub.com.br',
]
```

---

### 4. **Nginx - server_name** 🟡 MÉDIO
**Arquivo:** `nginx.conf`  
**Linhas:** Múltiplas

**Problema:** Domínios `.local` hardcoded em todos os blocos `server`
```nginx
server_name admin.wallclub.com.br wcadmin.wallclub.com.br admin.wallclub.local;  # ❌
server_name vendas.wallclub.com.br wcvendas.wallclub.com.br vendas.wallclub.local;  # ❌
server_name lojista.wallclub.com.br wclojista.wallclub.com.br lojista.wallclub.local;  # ❌
server_name api.wallclub.com.br wcapi.wallclub.com.br api.wallclub.local;  # ❌
server_name checkout.wallclub.com.br wccheckout.wallclub.com.br checkout.wallclub.local;  # ❌
server_name flower.wallclub.com.br wcflower.wallclub.com.br flower.wallclub.local;  # ❌
```

**Solução:** Usar arquivo nginx diferente para dev/prod ou variáveis de ambiente

---

### 5. **ALLOWED_HOSTS - Portais** 🟡 MÉDIO
**Arquivo:** `services/django/wallclub/settings/portais.py`  
**Linhas:** 17-32

**Problema:** Domínios `.local` hardcoded mesmo em produção
```python
ALLOWED_HOSTS = [
    'admin.wallclub.com.br',
    'vendas.wallclub.com.br',
    # ...
    'admin.wallclub.local',  # ❌ DESENVOLVIMENTO em produção
    'vendas.wallclub.local',  # ❌ DESENVOLVIMENTO em produção
]
```

**Solução:** Mover `.local` para dentro do `if DEBUG:`

---

### 6. **URLs Hardcoded - Services** 🟡 MÉDIO

#### 6.1 Checkout - Email Link Pagamento
**Arquivo:** `checkout/services.py` linha 907
```python
checkout_url = f"https://checkout.wallclub.com.br/api/v1/checkout/?token={token.token}"  # ❌
```

#### 6.2 Portal Vendas - Link Pagamento
**Arquivo:** `portais/vendas/services.py` linha 574
```python
base_url = getattr(settings, 'CHECKOUT_BASE_URL', 'https://checkout.wallclub.com.br')  # ⚠️ Fallback hardcoded
```

#### 6.3 Controle Acesso - Primeiro Acesso
**Arquivo:** `portais/controle_acesso/email_service.py` linhas 53, 56
```python
link_primeiro_acesso = f"https://wclojista.wallclub.com.br/primeiro_acesso/{token}/"  # ❌
link_primeiro_acesso = f"https://wcvendas.wallclub.com.br/primeiro_acesso/{token}/"  # ❌
```

#### 6.4 Controle Acesso - Reset Senha
**Arquivo:** `portais/controle_acesso/email_service.py` linha 112
```python
link_reset = f"https://wclojista.wallclub.com.br/reset-senha/{token}/"  # ❌
```

#### 6.5 Portal Lojista - Upload Ofertas
**Arquivo:** `portais/lojista/views_ofertas.py` linhas 99, 235
```python
imagem_url = f'https://apidj.wallclub.com.br/media/{caminho}'  # ❌
```

#### 6.6 Own Financial - merchant.url
**Arquivo:** `adquirente_own/services_transacoes_pagamento.py` linhas 203, 300, 374
```python
'merchant.url': 'wallclub.com.br',  # ❌ Hardcoded
```

**Solução:** Criar variáveis de ambiente:
- `CHECKOUT_BASE_URL`
- `PORTAL_LOJISTA_URL`
- `PORTAL_VENDAS_URL`
- `MEDIA_BASE_URL`
- `MERCHANT_URL`

---

### 7. **BASE_URL - Settings** 🟡 MÉDIO
**Arquivo:** `wallclub/settings/base.py` linha 306
```python
BASE_URL = 'https://wcadmin.wallclub.com.br'  # ❌ Hardcoded
```

**Solução:** Usar variável de ambiente
```python
BASE_URL = os.environ.get('BASE_URL', 'https://wcadmin.wallclub.com.br')
```

---

### 8. **Email - DEFAULT_FROM_EMAIL** ✅ OK
**Arquivo:** `wallclub/settings/base.py` linha 305
```python
DEFAULT_FROM_EMAIL = 'noreply@wallclub.com.br'  # ✅ OK (email real)
```

---

### 9. **ALLOWED_HOSTS - Settings** ✅ OK

#### Container Portais
**Arquivo:** `wallclub/settings/portais.py` linhas 11-32  
**Status:** ✅ Usa `DEBUG` (mas tem `.local` hardcoded - ver item 5)

#### Container POS
**Arquivo:** `wallclub/settings/pos.py` linhas 11-20  
**Status:** ✅ Usa `DEBUG` corretamente

#### Container APIs
**Arquivo:** `wallclub/settings/apis.py` linhas 11-22  
**Status:** ✅ Usa `DEBUG` corretamente

---

### 10. **CORS_ALLOWED_ORIGINS** ✅ OK

#### Production Settings
**Arquivo:** `wallclub/settings/production.py` linhas 21-22  
**Status:** ✅ Usa variável de ambiente

#### Development Settings
**Arquivo:** `wallclub/settings/development.py` linhas 18-19  
**Status:** ✅ Usa variável de ambiente com fallback

---

## 🎯 PLANO DE AÇÃO

### Prioridade 1 - 🔴 CRÍTICO (Antes de Produção)

1. **Ajustar CORS Manual no Checkout 2FA**
   - Arquivo: `checkout/link_pagamento_web/views_2fa.py` linhas 37-43
   - Usar `settings.DEBUG` para diferenciar ambientes

2. **Ajustar CSRF_TRUSTED_ORIGINS no Portais**
   - Arquivo: `wallclub/settings/portais.py` linhas 77-90
   - Usar `DEBUG` para diferenciar HTTP (dev) de HTTPS (prod)

3. **Remover IP interno do production.py**
   - Arquivo: `wallclub/settings/production.py` linhas 37-41
   - Remover `http://ip-10-0-1-46:8000`

### Prioridade 2 - 🟡 MÉDIO (Antes de Produção)

4. **Ajustar Nginx - server_name**
   - Arquivo: `nginx.conf` (múltiplas linhas)
   - Remover domínios `.local` ou criar nginx.dev.conf separado

5. **Ajustar ALLOWED_HOSTS - Portais**
   - Arquivo: `wallclub/settings/portais.py` linhas 17-32
   - Mover domínios `.local` para dentro do `if DEBUG:`

6. **Ajustar URLs Hardcoded em Services**
   - `checkout/services.py` linha 907
   - `portais/vendas/services.py` linha 574
   - `portais/controle_acesso/email_service.py` linhas 53, 56, 112
   - `portais/lojista/views_ofertas.py` linhas 99, 235
   - `adquirente_own/services_transacoes_pagamento.py` linhas 203, 300, 374

7. **Ajustar BASE_URL - Settings**
   - Arquivo: `wallclub/settings/base.py` linha 306
   - Usar variável de ambiente

### Prioridade 3 - 🟢 MELHORIA (Pós-Produção)

8. **Criar variáveis de ambiente**
   - `CHECKOUT_BASE_URL`
   - `PORTAL_LOJISTA_URL`
   - `PORTAL_VENDAS_URL`
   - `MEDIA_BASE_URL`
   - `MERCHANT_URL`
   - `BASE_URL`

9. **Documentar variáveis de ambiente**
   - Atualizar `README.md` com lista completa
   - Criar `.env.example` com valores de exemplo

---

## 🔒 VARIÁVEIS DE AMBIENTE RECOMENDADAS

### Produção (.env.production)
```bash
DEBUG=False
ALLOWED_HOSTS=admin.wallclub.com.br,api.wallclub.com.br,checkout.wallclub.com.br

CORS_ALLOWED_ORIGINS=https://wallclub.com.br,https://checkout.wallclub.com.br

CSRF_TRUSTED_ORIGINS=https://admin.wallclub.com.br,https://api.wallclub.com.br

# Checkout 2FA (novo)
CHECKOUT_ALLOWED_DOMAINS=wallclub.com.br,checkout.wallclub.com.br
```

### Desenvolvimento (.env.development)
```bash
DEBUG=True
ALLOWED_HOSTS=*

CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

CSRF_TRUSTED_ORIGINS=http://localhost:8005,http://127.0.0.1:8005

# Checkout 2FA (novo)
CHECKOUT_ALLOWED_DOMAINS=localhost,127.0.0.1,checkout.wallclub.local
```

---

## ✅ CHECKLIST PRÉ-PRODUÇÃO

### 🔴 Crítico
- [ ] Ajustar `views_2fa.py` CORS (usar `settings.DEBUG`)
- [ ] Ajustar `portais.py` CSRF_TRUSTED_ORIGINS (separar HTTP/HTTPS)
- [ ] Remover IP interno de `production.py`

### 🟡 Médio
- [ ] Ajustar `nginx.conf` (remover `.local` ou criar arquivo separado)
- [ ] Ajustar `portais.py` ALLOWED_HOSTS (mover `.local` para DEBUG)
- [ ] Ajustar URLs hardcoded em 6 arquivos de services
- [ ] Ajustar `BASE_URL` em `base.py`

### 🟢 Validação
- [ ] Testar em staging com `DEBUG=False`
- [ ] Validar que `localhost` NÃO funciona com `DEBUG=False`
- [ ] Validar que domínios de produção funcionam
- [ ] Validar que domínios `.local` NÃO funcionam em produção

### 📝 Documentação
- [ ] Documentar variáveis de ambiente no README
- [ ] Criar `.env.example` com todas as URLs

---

## 📚 REFERÊNCIAS

- Django ALLOWED_HOSTS: https://docs.djangoproject.com/en/4.2/ref/settings/#allowed-hosts
- Django CSRF_TRUSTED_ORIGINS: https://docs.djangoproject.com/en/4.2/ref/settings/#csrf-trusted-origins
- Django CORS Headers: https://github.com/adamchainz/django-cors-headers

---

**Criado por:** Tech Lead  
**Próxima revisão:** Antes do deploy em produção
