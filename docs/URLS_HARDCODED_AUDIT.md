# Auditoria de URLs Hardcoded - WallClub Backend

## Objetivo
Centralizar todas as URLs do projeto em variáveis de ambiente para facilitar manutenção e migração de domínios.

---

## Arquivos com URLs Hardcoded

### 1. Settings (Prioridade ALTA)

#### `wallclub/settings/base.py` (7 ocorrências)
- Linha 311: `DEFAULT_FROM_EMAIL = 'noreply@wallclub.com.br'`
- Linha 314: `BASE_URL = os.environ.get('BASE_URL', 'https://wcadmin.wallclub.com.br')`
- Linha 315: `CHECKOUT_BASE_URL = os.environ.get('CHECKOUT_BASE_URL', 'https://checkout.wallclub.com.br')`
- Linha 316: `PORTAL_LOJISTA_URL = os.environ.get('PORTAL_LOJISTA_URL', 'https://wclojista.wallclub.com.br')`
- Linha 317: `PORTAL_VENDAS_URL = os.environ.get('PORTAL_VENDAS_URL', 'https://wcvendas.wallclub.com.br')`
- Linha 318: `MEDIA_BASE_URL = os.environ.get('MEDIA_BASE_URL', 'https://wcapi.wallclub.com.br')`
- Linha 319: `MERCHANT_URL = os.environ.get('MERCHANT_URL', 'wallclub.com.br')`

**Ação:** Atualizar valores default para novos domínios (sem "wc")

#### `wallclub/settings/apis.py` (4 ocorrências)
- Linhas 18-21: Lista de `ALLOWED_HOSTS` hardcoded
```python
ALLOWED_HOSTS = [
    'api.wallclub.com.br',
    'checkout.wallclub.com.br',
    'wcapi.wallclub.com.br',
    'wccheckout.wallclub.com.br',
]
```

**Ação:** Remover e usar variável de ambiente do base.py

#### `wallclub/settings/pos.py` (2 ocorrências)
- Linhas 18-19: Lista de `ALLOWED_HOSTS` hardcoded
```python
ALLOWED_HOSTS = [
    'api.wallclub.com.br',
    'wcapi.wallclub.com.br',
]
```

**Ação:** Remover e usar variável de ambiente do base.py

#### `wallclub/settings/production.py` (1 ocorrência)
- Linha 38: `CSRF_TRUSTED_ORIGINS = ['https://wcapi.wallclub.com.br']`

**Ação:** Remover e usar variável de ambiente do base.py

---

### 2. Middleware (Prioridade MÉDIA)

#### `wallclub/middleware/subdomain_router.py` (1 ocorrência)
- Linha 5: Comentário documentando domínios
```python
"""
Permite que admin.wallclub.com.br, vendas.wallclub.com.br e lojista.wallclub.com.br
respondam cada um em sua raiz (/) sem prefixos.
"""
```

**Ação:** Atualizar documentação apenas (não afeta funcionalidade)

#### `portais/controle_acesso/middleware.py` (1 ocorrência)
- Linha 20: Comentário sobre cookie
```python
'/': 'wallclub_admin_session',  # Admin responde na raiz via wcadmin.wallclub.com.br
```

**Ação:** Atualizar comentário apenas

---

### 3. Views (Prioridade ALTA)

#### `portais/admin/views_ofertas.py` (3 ocorrências)
- Linha 112: `imagem_url = f'https://apidj.wallclub.com.br/media/{caminho}'`
- Linha 181: `'imagem_url': f'https://apidj.wallclub.com.br/media/{nome_final}'`
- Linha 276: `imagem_url = f'https://apidj.wallclub.com.br/media/{caminho}'`

**Ação:** Substituir por `f'{settings.MEDIA_BASE_URL}/media/{caminho}'`

#### `portais/corporativo/views.py` (3 ocorrências)
- Linha 100: URL no template de email
```python
Esta mensagem foi enviada através do site: https://wcinstitucional.wallclub.com.br/contato/
```
- Linha 105: Email de contato
```python
destinatarios = ['atendimento@wallclub.com.br', 'jp.ferreira@wallclub.com.br']
```
- Linha 151: Email de contato
```python
'email': 'atendimento@wallclub.com.br'
```

**Ação:** Criar variáveis de ambiente para emails de contato e URL institucional

---

### 4. Services (Prioridade MÉDIA)

#### `checkout/link_recorrencia_web/services.py` (1 ocorrência)
- Linha 63: `base_url = settings.BASE_URL or 'https://apidj.wallclub.com.br'`

**Ação:** Remover fallback hardcoded, usar apenas `settings.BASE_URL`

---

### 5. URLs (Prioridade BAIXA - Apenas Documentação)

#### `wallclub/urls_admin.py` (1 ocorrência)
- Linha 2: Comentário `URLs para Portal Admin (admin.wallclub.com.br)`

#### `wallclub/urls_vendas.py` (1 ocorrência)
- Linha 2: Comentário `URLs para Portal Vendas (vendas.wallclub.com.br)`

#### `wallclub/urls_lojista.py` (1 ocorrência)
- Linha 2: Comentário `URLs para Portal Lojista (lojista.wallclub.com.br)`

#### `wallclub/urls_corporativo.py` (1 ocorrência)
- Linha 2: Comentário `URLs para Portal Corporativo (corporativo.wallclub.com.br, wallclub.com.br, www.wallclub.com.br)`

**Ação:** Atualizar comentários apenas

---

### 6. Scripts (Prioridade BAIXA - Não afeta produção)

#### `scripts/producao/backup/comparar_django_local_vs_php_prod.py`
- Linha 15: `url = "https://posp2.wallclub.com.br/calcula_desconto_para_teste.php"`

#### `scripts/producao/backup/migracao_param_wall/comparar_desconto_django_prod_vs_php_prod.py`
- Linha 153: `url = "https://posp2.wallclub.com.br/calcula_desconto_parcela_para_teste.php"`

#### `scripts/producao/backup/validar_calculos_producao.py`
- Linha 29: `self.endpoint_php = endpoint_php or "https://wallclub.com.br/apps/calcula_desconto_parcela_para_teste.php"`

**Ação:** Scripts de backup/teste - baixa prioridade

---

## Resumo de Ações

### Prioridade ALTA (Afeta funcionalidade)
1. ✅ `wallclub/settings/base.py` - Atualizar defaults
2. ✅ `wallclub/settings/apis.py` - Remover ALLOWED_HOSTS hardcoded
3. ✅ `wallclub/settings/pos.py` - Remover ALLOWED_HOSTS hardcoded
4. ✅ `wallclub/settings/production.py` - Remover CSRF_TRUSTED_ORIGINS hardcoded
5. ⚠️ `portais/admin/views_ofertas.py` - Usar settings.MEDIA_BASE_URL
6. ⚠️ `portais/corporativo/views.py` - Criar variáveis para emails e URL institucional
7. ⚠️ `checkout/link_recorrencia_web/services.py` - Remover fallback hardcoded

### Prioridade MÉDIA (Documentação/Comentários)
8. `wallclub/middleware/subdomain_router.py` - Atualizar comentário
9. `portais/controle_acesso/middleware.py` - Atualizar comentário

### Prioridade BAIXA (Apenas comentários em URLs)
10. `wallclub/urls_*.py` - Atualizar comentários

### Ignorar (Scripts de backup/teste)
- `scripts/producao/backup/*.py`

---

## Estratégia de Migração de URLs

### URLs de API (Compatibilidade com sistemas externos)

**Situação Atual:**
- POS e APP (sistemas externos) acessam `wcapi.wallclub.com.br`
- Código usa `MEDIA_BASE_URL` que aponta para `wcapi.wallclub.com.br`

**Estratégia:**
1. Manter `WC_API_BASE_URL=https://wcapi.wallclub.com.br` (compatibilidade com POS/APP)
2. Criar `API_BASE_URL=https://api.wallclub.com.br` (para migração futura)
3. Remover `MEDIA_BASE_URL` e consolidar com `WC_API_BASE_URL`

### Arquivos que usam MEDIA_BASE_URL (precisam migrar para WC_API_BASE_URL)

1. **`wallclub/settings/base.py`** (linha 318)
   - Remover: `MEDIA_BASE_URL = os.environ.get('MEDIA_BASE_URL', 'https://wcapi.wallclub.com.br')`
   - Adicionar: `WC_API_BASE_URL = os.environ.get('WC_API_BASE_URL', 'https://wcapi.wallclub.com.br')`
   - Adicionar: `API_BASE_URL = os.environ.get('API_BASE_URL', 'https://api.wallclub.com.br')`

2. **`portais/lojista/views_ofertas.py`** (linhas 99 e 235)
   - Substituir: `settings.MEDIA_BASE_URL` → `settings.WC_API_BASE_URL`

3. **`portais/admin/views_ofertas.py`** (linhas 112, 181, 276)
   - Substituir: `'https://apidj.wallclub.com.br'` → `settings.WC_API_BASE_URL`

---

## Novas Variáveis de Ambiente Necessárias

Adicionar ao `.env.production`:

```bash
# APIs (compatibilidade e migração)
API_BASE_URL=https://api.wallclub.com.br
WC_API_BASE_URL=https://wcapi.wallclub.com.br

# Emails
CONTACT_EMAIL=atendimento@wallclub.com.br
NOREPLY_EMAIL=noreply@wallclub.com.br
ADMIN_EMAIL=jp.ferreira@wallclub.com.br

# URLs Institucionais
INSTITUCIONAL_URL=https://www.wallclub.com.br
```

**Remover:**
```bash
MEDIA_BASE_URL=https://wcapi.wallclub.com.br  # Consolidar com WC_API_BASE_URL
```

---

## Checklist de Validação

- [ ] Atualizar `base.py` com novos defaults
- [ ] Remover ALLOWED_HOSTS de `apis.py` e `pos.py`
- [ ] Remover CSRF_TRUSTED_ORIGINS de `production.py`
- [ ] Atualizar `views_ofertas.py` para usar settings
- [ ] Atualizar `corporativo/views.py` para usar variáveis de ambiente
- [ ] Atualizar `link_recorrencia_web/services.py`
- [ ] Adicionar novas variáveis ao `.env.production`
- [ ] Testar em desenvolvimento
- [ ] Testar em produção
- [ ] Atualizar comentários/documentação
