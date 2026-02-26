eu# Análise da Arquitetura de Roteamento WallClub

**Data:** 31/01/2026
**Versão:** 1.0
**Status:** Proposta de Refatoração

---

## 1. CENÁRIO ATUAL

### 1.1 Arquitetura de Containers

```
┌─────────────────────────────────────────────────────────────┐
│                    MONOREPO DJANGO                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Container PORTAIS (porta 8005)                             │
│  ├── ROOT_URLCONF: wallclub.urls_portais                    │
│  ├── Middleware: SubdomainRouterMiddleware                  │
│  └── Serve: Admin, Vendas, Lojista, Corporativo            │
│                                                             │
│  Container APIS (porta 8007)                                │
│  ├── ROOT_URLCONF: wallclub.urls_apis                       │
│  └── Serve: Mobile APIs, Checkout APIs                     │
│                                                             │
│  Container POS (porta 8006)                                 │
│  ├── ROOT_URLCONF: wallclub.urls_pos                        │
│  └── Serve: Terminal POS APIs                              │
│                                                             │
│  Container RISKENGINE (porta 8008)                          │
│  ├── ROOT_URLCONF: wallclub.urls (padrão)                   │
│  └── Serve: Antifraude APIs                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Arquivos de URLconf

**Total: 8 arquivos de URLs**

1. `wallclub/urls.py` - URLconf padrão (não usado por nenhum container)
2. `wallclub/urls_portais.py` - Container PORTAIS (com prefixos)
3. `wallclub/urls_admin.py` - Portal Admin (via middleware)
4. `wallclub/urls_vendas.py` - Portal Vendas (via middleware)
5. `wallclub/urls_lojista.py` - Portal Lojista (via middleware)
6. `wallclub/urls_corporativo.py` - Portal Corporativo (via middleware)
7. `wallclub/urls_apis.py` - Container APIS
8. `wallclub/urls_pos.py` - Container POS

### 1.3 Middleware de Roteamento por Subdomínio

**Localização:** `wallclub/middleware/subdomain_router.py`

**Funcionamento:**
- Intercepta TODAS as requisições no container PORTAIS
- Analisa o subdomínio (admin, vendas, lojista, www)
- Altera dinamicamente o `request.urlconf` baseado no subdomínio
- Se subdomínio não mapeado, usa URLconf padrão (urls_portais)

**Mapeamento:**
```python
subdomain_map = {
    'admin': 'wallclub.urls_admin',
    'vendas': 'wallclub.urls_vendas',
    'lojista': 'wallclub.urls_lojista',
    'www': 'wallclub.urls_corporativo',
}
```

**Exceções:**
- `/metrics` - não aplica roteamento
- `/health/` - não aplica roteamento

---

## 2. PROBLEMAS IDENTIFICADOS

### 2.1 Complexidade Excessiva

**Problema:** 8 arquivos de URLs para gerenciar, sendo que 4 deles (admin, vendas, lojista, corporativo) são praticamente idênticos, apenas mudando os namespaces.

**Impacto:**
- Dificulta manutenção
- Aumenta chance de inconsistências
- Complica adição de rotas globais (ex: `/metrics`, `/health/`)

### 2.2 Middleware com Lógica de Roteamento

**Problema:** O middleware `SubdomainRouterMiddleware` está fazendo roteamento dinâmico, o que é uma responsabilidade que deveria estar nas URLs.

**Impacto:**
- Dificulta debug (URLconf muda dinamicamente)
- Adiciona overhead em TODA requisição
- Complica testes
- Dificulta adicionar rotas globais

### 2.3 Inconsistência entre Containers

**Problema:** Cada container tem uma estratégia diferente de roteamento:
- PORTAIS: usa middleware + múltiplos URLconfs
- APIS: usa URLconf único simples
- POS: usa URLconf único simples
- RISKENGINE: usa URLconf padrão

**Impacto:**
- Dificulta entender qual rota está em qual container
- Complica adição de funcionalidades globais (monitoramento, health checks)

### 2.4 URLconf Padrão Não Utilizado

**Problema:** O arquivo `wallclub/urls.py` existe mas não é usado por nenhum container em produção.

**Impacto:**
- Confusão sobre qual é o URLconf "real"
- Código morto que precisa ser mantido

### 2.5 Dificuldade em Adicionar Rotas Globais

**Problema Atual:** Para adicionar `/metrics` em todos os containers, precisamos:
1. Adicionar em `urls_portais.py`
2. Adicionar em `urls_admin.py`
3. Adicionar em `urls_vendas.py`
4. Adicionar em `urls_lojista.py`
5. Adicionar em `urls_corporativo.py`
6. Adicionar em `urls_apis.py`
7. Adicionar em `urls_pos.py`
8. Adicionar exceção no middleware

**Impacto:**
- 8 lugares para manter sincronizados
- Alto risco de esquecimento
- Dificulta evolução

---

## 3. PROPOSTA DE REFATORAÇÃO

### 3.1 Arquitetura Simplificada

**Objetivo:** Reduzir de 8 para 4 arquivos de URLs, eliminar middleware de roteamento.

```
┌─────────────────────────────────────────────────────────────┐
│                    ESTRUTURA PROPOSTA                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. wallclub/urls_base.py (NOVO)                            │
│     └── Rotas globais: /metrics, /health/, /admin/         │
│                                                             │
│  2. wallclub/urls_portais.py (REFATORADO)                   │
│     ├── include urls_base                                  │
│     └── Portais com PREFIXOS:                              │
│         ├── /portal_admin/                                 │
│         ├── /portal_vendas/                                │
│         ├── /portal_lojista/                               │
│         └── /portal_corporativo/                           │
│                                                             │
│  3. wallclub/urls_apis.py (MANTÉM)                          │
│     ├── include urls_base                                  │
│     └── APIs Mobile + Checkout                             │
│                                                             │
│  4. wallclub/urls_pos.py (MANTÉM)                           │
│     ├── include urls_base                                  │
│     └── APIs Terminal POS                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Mudanças Necessárias

#### 3.2.1 Criar `urls_base.py`

```python
# wallclub/urls_base.py
from django.urls import path, include

urlpatterns = [
    # Métricas Prometheus (global)
    path('metrics', include('django_prometheus.urls')),

    # Health Checks (global)
    path('health/', include('monitoring.urls')),

    # Admin Django (global)
    path('admin/', admin.site.urls),
]
```

#### 3.2.2 Refatorar `urls_portais.py`

```python
# wallclub/urls_portais.py
from django.urls import path, include
from .urls_base import urlpatterns as base_patterns

urlpatterns = base_patterns + [
    # Portais com prefixos (sem middleware)
    path('portal_admin/', include('portais.admin.urls', namespace='portais_admin')),
    path('portal_vendas/', include('portais.vendas.urls', namespace='vendas')),
    path('portal_lojista/', include('portais.lojista.urls', namespace='lojista')),
    path('portal_corporativo/', include('portais.corporativo.urls', namespace='portais_corporativo')),
]
```

#### 3.2.3 Remover Middleware

- Deletar `wallclub/middleware/subdomain_router.py`
- Remover do `MIDDLEWARE` em `settings/base.py`

#### 3.2.4 Deletar URLconfs Redundantes

- Deletar `urls_admin.py`
- Deletar `urls_vendas.py`
- Deletar `urls_lojista.py`
- Deletar `urls_corporativo.py`
- Deletar `urls.py` (padrão não usado)

#### 3.2.5 Atualizar URLs dos Portais

**Antes (com subdomínio):**
- `http://admin.wallclub.com.br/` → Portal Admin
- `http://vendas.wallclub.com.br/` → Portal Vendas

**Depois (com prefixo):**
- `http://wallclub.com.br/portal_admin/` → Portal Admin
- `http://wallclub.com.br/portal_vendas/` → Portal Vendas

---

## 4. IMPACTO DA MUDANÇA

### 4.1 Benefícios

✅ **Simplicidade:**
- 8 arquivos → 4 arquivos (50% redução)
- 1 middleware a menos
- Lógica de roteamento explícita (não dinâmica)

✅ **Manutenibilidade:**
- Rotas globais em 1 único lugar (`urls_base.py`)
- Fácil adicionar novas funcionalidades globais
- Debug mais simples (URLconf estático)

✅ **Consistência:**
- Todos os containers seguem o mesmo padrão
- Mesma estrutura de URLs em todos os lugares

✅ **Performance:**
- Remove overhead do middleware em toda requisição
- URLconf resolvido uma vez no startup

### 4.2 Desvantagens

❌ **URLs Mudam:**
- Usuários precisam atualizar bookmarks
- Links salvos ficam quebrados
- Necessário período de transição

❌ **Prefixos nas URLs:**
- URLs ficam mais longas
- `/portal_admin/` em vez de `/`

❌ **Trabalho de Migração:**
- Atualizar todos os links hardcoded no código
- Atualizar configurações de NGINX/proxy reverso
- Atualizar documentação
- Comunicar mudança para usuários

---

## 5. PLANO DE EXECUÇÃO

### Fase 1: Preparação (2-3 horas)
1. Criar `urls_base.py` com rotas globais
2. Refatorar `urls_portais.py` para usar prefixos
3. Atualizar `urls_apis.py` e `urls_pos.py` para incluir `urls_base`
4. Criar testes para validar todas as rotas

### Fase 2: Remoção do Middleware (1 hora)
1. Remover `SubdomainRouterMiddleware` do `MIDDLEWARE`
2. Deletar arquivo `subdomain_router.py`
3. Testar que rotas ainda funcionam

### Fase 3: Limpeza (1 hora)
1. Deletar `urls_admin.py`, `urls_vendas.py`, `urls_lojista.py`, `urls_corporativo.py`
2. Deletar `urls.py` (padrão não usado)
3. Atualizar imports e referências

### Fase 4: Atualização de Links (2-4 horas)
1. Buscar e substituir links hardcoded no código
2. Atualizar templates HTML
3. Atualizar configurações de proxy reverso
4. Atualizar documentação

### Fase 5: Testes (2 horas)
1. Testar todos os portais
2. Testar todas as APIs
3. Testar monitoramento (`/metrics`, `/health/`)
4. Validar em ambiente de desenvolvimento

**Tempo Total Estimado: 8-12 horas**

---

## 6. ALTERNATIVA: MANTER ARQUITETURA ATUAL

Se decidir **NÃO refatorar**, para fazer o monitoramento funcionar:

### Solução Paliativa

1. Adicionar `path('metrics', include('django_prometheus.urls'))` em **TODOS** os 8 arquivos de URLs
2. Manter exceção no middleware para `/metrics`
3. Aceitar a complexidade e overhead

**Tempo: 30 minutos**

**Custo:** Continuar com arquitetura complexa, dificultar futuras evoluções

---

## 7. RECOMENDAÇÃO

**Recomendo REFATORAR** pelos seguintes motivos:

1. **Dívida Técnica:** A arquitetura atual já está complexa demais
2. **Futuro:** Facilita muito adicionar novas funcionalidades globais
3. **Manutenção:** Reduz drasticamente a complexidade
4. **Custo-Benefício:** 8-12 horas de trabalho para resolver problema estrutural

**Momento Ideal:** Agora, antes de adicionar mais funcionalidades que dependem de rotas globais (monitoramento, métricas, etc.)

---

## 8. DECISÃO

**Opção A:** Refatorar agora (8-12 horas) → Arquitetura limpa e sustentável

**Opção B:** Solução paliativa (30 min) → Continuar com complexidade, resolver depois

**Opção C:** Refatorar parcialmente → Criar `urls_base.py` mas manter middleware (meio termo)

---

**Qual opção você prefere?**
