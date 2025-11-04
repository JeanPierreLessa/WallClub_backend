# FASE 6 - SEPARAÇÃO EM MÚLTIPLOS CONTAINERS ✅

**Status:** ✅ FASE 6 CONCLUÍDA EM DEV (6A+6B+6C+6D)  
**Data Início:** 31/10/2025  
**Data Conclusão DEV:** 04/11/2025 00:00  
**Próximo:** Deploy em Produção (04/11/2025)  
**Última Atualização:** 04/11/2025 00:02

---

## 📊 ÍNDICE

1. [Resumo Executivo](#resumo-executivo)
2. [Fase 6A - Limpeza do CORE](#fase-6a---limpeza-do-core)
3. [Fase 6B - Resolver Dependências Cruzadas](#fase-6b---resolver-dependências-cruzadas)
4. [Fase 6C - Extração do CORE](#fase-6c---extração-do-core)
5. [Fase 6D - Separação Física](#fase-6d---separação-física-próxima)
6. [Métricas Finais](#métricas-finais)

---

## 📊 RESUMO EXECUTIVO

### Objetivo:
Separar monolito Django em múltiplos containers independentes + 1 package compartilhado

### Containers Planejados:
1. **Django Main** (8003): APIs mobile, checkout, clientes
2. **Risk Engine** (8004): Antifraude ✅ JÁ EXISTE
3. **wallclub_core**: Package compartilhado ✅ CRIADO

### Status Geral:
- ✅ **Fase 6A:** CORE limpo (0 imports problemáticos)
- ✅ **Fase 6B:** Dependências cruzadas resolvidas (26 APIs REST + 17 lazy imports)
- ✅ **Fase 6C:** Package wallclub_core extraído (113 arquivos migrados)
- ✅ **Fase 6D:** 4 containers independentes funcionando em DEV
- 📅 **Próximo:** Deploy em Produção

---

## ✅ FASE 6A - LIMPEZA DO CORE

**Duração:** 1 semana (Semana 27)  
**Status:** ✅ CONCLUÍDA

### Objetivo:
Remover dependências do CORE para apps específicos

### Arquivos Alterados:

#### 1. `comum/oauth/jwt_utils.py` ✅ CRIADO
Funções JWT genéricas sem dependência de apps:
- `validate_jwt_token()` - Validação genérica
- `validate_cliente_jwt_token()` - Wrapper retrocompatível
- `decode_jwt_token()` - Debug
- `extract_token_from_header()` - Extração

#### 2. `comum/seguranca/services_device.py` ✅ REFATORADO
Removido código que buscava Cliente:
- Métodos de notificação esvaziados
- Caller deve notificar manualmente
- CORE não conhece Cliente

#### 3. `comum/integracoes/notificacao_seguranca_service.py` ✅ REFATORADO
Métodos não buscam mais Cliente. Nova assinatura:
```python
NotificacaoSegurancaService.notificar_troca_senha(
    cliente_id=123,
    canal_id=1,
    celular='11987654321',  # Obrigatório
    nome='João'             # Opcional
)
```

### Callers Atualizados (6 arquivos):
- ✅ `apps/cliente/views_senha.py`
- ✅ `apps/cliente/views.py` (celular e email)
- ✅ `apps/cliente/services_reset_senha.py`
- ✅ `apps/cliente/services.py` (3 chamadas)
- ✅ `apps/cliente/services_2fa_login.py`

### Bug Fix: device_fingerprint
**Problema:** Backend sobrescrevia fingerprint do app com string vazia
**Correção:** Validação adequada antes de recalcular
**Commit:** `4e2fc56` em release/3.1.0

---

## ✅ FASE 6B - RESOLVER DEPENDÊNCIAS CRUZADAS

**Duração:** 3 semanas (Semanas 28-30)  
**Status:** ✅ CONCLUÍDA  
**Data Conclusão:** 01/11/2025 23:28

### Objetivo:
Resolver 103 imports cruzados entre containers

### Estratégias Aplicadas:

| Estratégia | Uso | Quantidade |
|------------|-----|------------|
| 🌐 APIs REST Internas | 70% | 26 endpoints |
| 📊 SQL Direto | 25% | 2 classes (9 métodos) |
| 🔄 Lazy Imports | 5% | 17 arquivos |

### Semana 28: APIs Internas - Conta Digital + Checkout ✅

**APIs Conta Digital (5 endpoints):**
```
POST /api/internal/conta-digital/consultar-saldo/
POST /api/internal/conta-digital/autorizar-uso/
POST /api/internal/conta-digital/debitar-saldo/
POST /api/internal/conta-digital/estornar-saldo/
POST /api/internal/conta-digital/calcular-maximo/
```

**APIs Checkout Recorrências (8 endpoints):**
```
GET  /api/internal/checkout/recorrencias/
POST /api/internal/checkout/recorrencias/criar/
GET  /api/internal/checkout/recorrencias/{id}/
POST /api/internal/checkout/recorrencias/{id}/pausar/
POST /api/internal/checkout/recorrencias/{id}/reativar/
POST /api/internal/checkout/recorrencias/{id}/cobrar/
PUT  /api/internal/checkout/recorrencias/{id}/atualizar/
DEL  /api/internal/checkout/recorrencias/{id}/deletar/
```

### Semana 29: Ofertas + SQL Direto ✅

**APIs Ofertas (6 endpoints):**
```
POST /api/internal/ofertas/listar/
POST /api/internal/ofertas/criar/
POST /api/internal/ofertas/obter/
POST /api/internal/ofertas/atualizar/
POST /api/internal/ofertas/grupos/listar/
POST /api/internal/ofertas/grupos/criar/
```

**SQL Direto - comum/database/queries.py:**
- `TransacoesQueries` (7 métodos)
- `TerminaisQueries` (2 métodos)

### Semana 30: Lazy Imports + Parâmetros ✅

**Lazy Imports (17 arquivos):**
- `portais/admin/` - 6 arquivos
- `portais/lojista/` - 4 arquivos
- `portais/vendas/` - 4 arquivos
- `posp2/` - 2 arquivos
- `checkout/` - 1 arquivo

**APIs Parâmetros (7 endpoints):**
```
POST /api/internal/parametros/configuracoes/loja/
POST /api/internal/parametros/configuracoes/contar/
POST /api/internal/parametros/configuracoes/ultima/
POST /api/internal/parametros/loja/modalidades/
POST /api/internal/parametros/planos/
GET  /api/internal/parametros/importacoes/
GET  /api/internal/parametros/importacoes/{id}/
```

### Resultado Fase 6B:
```
✓ SUCESSO: Containers desacoplados!
- 🟢 0 imports diretos entre containers
- 🟢 26 APIs REST internas funcionando
- 🟢 17 lazy imports implementados
- 🟢 Comunicação: HTTP/REST via APIs internas
```

---

## ✅ FASE 6C - EXTRAÇÃO DO CORE

**Duração:** 2 dias (planejado: 1 semana)  
**Status:** ✅ CONCLUÍDO  
**Data:** 01-02/11/2025

### Objetivo:
Extrair módulo `comum/` para package compartilhado `wallclub_core`

### 1. Criação do Monorepo

**Localização:** `/Users/jeanlessa/wall_projects/WallClub_backend`

**Estrutura:**
```
WallClub_backend/
├── services/
│   ├── django/          # API Principal
│   ├── riskengine/      # Antifraude
│   └── core/            # Package wallclub_core
├── docs/
├── .gitignore
├── README.md
└── docker-compose.yml
```

### 2. Package `wallclub_core`

**Estrutura criada:**
```
wallclub_core/
├── setup.py              # Configuração do package
├── README.md
├── requirements.txt
├── LICENSE               # MIT License
├── MANIFEST.in
├── .gitignore
└── wallclub_core/        # Package principal
    ├── __init__.py
    ├── database/         # Queries SQL (read-only)
    ├── decorators/       # API decorators
    ├── estr_organizacional/  # Canal, Loja, Regional
    ├── integracoes/      # APIs + serviços externos
    ├── middleware/       # Security
    ├── oauth/            # JWT, OAuth 2.0
    ├── seguranca/        # 2FA, Device Management
    ├── services/         # Auditoria
    ├── templatetags/     # Formatação
    └── utilitarios/      # Config Manager, Utils
```

**Versão:** 1.0.0

### 3. Migração de Imports

#### Django Main
- **Arquivos migrados:** 108
- **Padrão:** `from comum.*` → `from wallclub_core.*`

**Distribuição:**
- 27 arquivos em `apps/`
- 30 arquivos em `portais/`
- 14 arquivos em `checkout/`
- 7 arquivos em `pinbank/`
- 6 arquivos em `parametros_wallclub/`
- 5 arquivos em `posp2/`
- 19 outros arquivos

#### Risk Engine
- **Arquivos migrados:** 5
- `antifraude/views.py`
- `antifraude/views_api.py`
- `antifraude/services.py`
- `antifraude/services_cliente_auth.py`
- `riskengine/settings.py`

### 4. Instalação

**Modo desenvolvimento (editable):**
```bash
pip install -e /Users/jeanlessa/wall_projects/WallClub_backend/services/core
```

**requirements.txt:**
```txt
wallclub_core @ file:///../core
```

### 5. Componentes Principais

#### database/
- `queries.py` - Queries SQL diretas (read-only)

#### decorators/
- `api_decorators.py` - Decorators para APIs REST
  - `handle_api_errors`
  - `validate_required_params`
  - `require_cliente_jwt`

#### integracoes/
- APIs Internas: `ofertas_api_client.py`, `parametros_api_client.py`
- Push: `apn_service.py`, `firebase_service.py`
- Comunicação: `email_service.py`, `sms_service.py`, `whatsapp_service.py`
- Notificações: `notification_service.py`, `notificacao_seguranca_service.py`

#### oauth/
- `decorators.py` - Decorators OAuth
- `jwt_utils.py` - JWT customizado
- `models.py` - OAuthClient, OAuthToken
- `services.py` - OAuth 2.0

#### seguranca/
- `services_2fa.py` - 2FA via WhatsApp
- `services_device.py` - Gerenciamento de dispositivos
- `rate_limiter_2fa.py` - Rate limiting
- `validador_cpf.py`

#### utilitarios/
- `config_manager.py` - AWS Secrets Manager
- `export_utils.py` - Excel, PDF
- `log_control.py` - Sistema de logs

### Resultado Fase 6C:
- ✅ Package `wallclub_core` criado e instalado
- ✅ Monorepo unificado (1 git repo)
- ✅ 113 arquivos migrados (comum → wallclub_core)
- ✅ Diretório `comum/` removido
- ✅ Código pronto para Fase 6D

---

## ✅ FASE 6D - SEPARAÇÃO EM 4 CONTAINERS DJANGO

**Duração:** 1 dia  
**Status:** ✅ CONCLUÍDA EM DEV  
**Data:** 03/11/2025  
**Próximo:** Deploy em Produção (04/11/2025)

### Objetivos:

1. **Separar Django em 4 Containers Especializados**
   - Container 1: Portais (Admin, Vendas, Lojista)
   - Container 2: POS (Terminal POS)
   - Container 3: APIs (Mobile + Checkout)
   - Container 4: Risk Engine (Antifraude)

2. **Configurar Nginx Gateway com Subdomínios**
   - 6 subdomínios para acesso externo
   - Roteamento por subdomínio para container correto
   - Rate limiting diferenciado
   - SSL/TLS centralizado

3. **Deploy Independente por Container**
   - Build por serviço
   - Restart seletivo
   - Zero downtime
   - Escalabilidade horizontal

4. **Isolamento e Segurança**
   - Cada container carrega apenas apps necessários
   - POS isolado (sistema crítico)
   - Comunicação interna via rede Docker

### Arquitetura Final:

```
Internet (80/443)
    ↓
[Nginx Gateway]
    ↓
├─→ admin.wallclub.com.br      → wallclub-portais:8000 (portais/)
├─→ vendas.wallclub.com.br     → wallclub-portais:8000 (portais/)
├─→ lojista.wallclub.com.br    → wallclub-portais:8000 (portais/)
│
├─→ apipos.wallclub.com.br     → wallclub-pos:8000 (posp2/)
│
├─→ api.wallclub.com.br        → wallclub-apis:8000 (apps/)
├─→ checkout.wallclub.com.br   → wallclub-apis:8000 (checkout/)
│
└─→ (interno apenas)           → wallclub-riskengine:8000 (antifraude/)

Comunicação Interna (Rede Docker):
    Todos ←→ Redis (wallclub-redis:6379)
    Todos ←→ MySQL (compartilhado)
    APIs/POS → Risk Engine (OAuth interno)
```

### Containers (9 total):

```yaml
1. nginx                          # Gateway - porta 80/443 (ÚNICA externa)
2. wallclub-portais               # Portais Web - porta 8000 (interna)
3. wallclub-pos                   # Terminal POS - porta 8000 (interna)
4. wallclub-apis                  # APIs Mobile - porta 8000 (interna)
5. wallclub-riskengine            # Antifraude - porta 8000 (interna)
6. wallclub-redis                 # Cache/Broker - porta 6379 (interna)
7. wallclub-celery-worker-portais # Tasks portais
8. wallclub-celery-worker-apis    # Tasks APIs
9. wallclub-celery-beat           # Scheduler
```

### Distribuição de Apps por Container:

#### **Container 1: wallclub-portais**
**Módulos:**
- `portais/admin/` - Portal administrativo
- `portais/lojista/` - Portal lojista
- `portais/vendas/` - Portal vendas/checkout interno
- `portais/controle_acesso/` - Autenticação portais
- `sistema_bancario/` - Gestão bancária

**Características:**
- Deploy: Frequente (features admin/lojista)
- Estabilidade: Média
- Usuários: Equipe interna + Lojistas

#### **Container 2: wallclub-pos**
**Módulos:**
- `posp2/` - Terminal POS
- `pinbank/` - Integração Pinbank
- `parametros_wallclub/` - Parâmetros e calculadora

**Características:**
- Deploy: Raro (sistema crítico)
- Estabilidade: ALTA
- Usuários: Terminais físicos em lojas

#### **Container 3: wallclub-apis**
**Módulos:**
- `apps/cliente/` - Autenticação mobile
- `apps/conta_digital/` - Conta digital
- `apps/ofertas/` - Ofertas e simulações
- `apps/transacoes/` - Transações mobile
- `apps/oauth/` - OAuth apps
- `checkout/` - Checkout web público

**Características:**
- Deploy: Médio (features app mobile)
- Estabilidade: Média
- Usuários: Apps mobile + Checkout web

#### **Container 4: wallclub-riskengine**
**Módulos:**
- `antifraude/` - Motor antifraude + MaxMind

**Características:**
- Deploy: Frequente (ajustes regras)
- Estabilidade: Alta (já consolidado)
- Usuários: Interno (chamado por outros containers)

### Segurança por Subdomínio:

| Subdomínio | Autenticação | Rate Limit | Uso |
|------------|--------------|------------|-----|
| `admin.wallclub.com.br` | Django Admin | 5 req/s | Gestão sistema |
| `vendas.wallclub.com.br` | Django Session | 10 req/s | Portal vendas/checkout |
| `lojista.wallclub.com.br` | Django Session | 10 req/s | Portal lojista |
| `api.wallclub.com.br` | OAuth + JWT | 10 req/s | Apps mobile |
| `apipos.wallclub.com.br` | OAuth POSP2 | 50 req/s | Terminais POS |
| `checkout.wallclub.com.br` | Session/Token | 20 req/s | Checkout web |

### Estratégia de Transição (Domínios API):

**Fase 1 - Imediata (Semana 1):**
```nginx
# Todos os domínios API respondem igual (alias no Nginx)
server_name api.wallclub.com.br apipos.wallclub.com.br apidj.wallclub.com.br;
```
- Zero mudança no código Django
- Comunicar novos domínios aos clientes
- Monitorar uso de cada domínio

**Fase 2 - Separação (30-60 dias):**
```nginx
# Separar rate limiting por domínio
api.wallclub.com.br     → 10 req/s (mobile)
apipos.wallclub.com.br  → 50 req/s (POS)
apidj.wallclub.com.br   → deprecado (logs)
```

**Fase 3 - Deprecação (90 dias):**
```nginx
# Redirecionar apidj.wallclub.com.br
location /posp2/ {
    return 301 https://apipos.wallclub.com.br$request_uri;
}
location / {
    return 301 https://api.wallclub.com.br$request_uri;
}
```

### Mudanças nos Nomes:

**Antes:**
- `wallclub-django-monorepo`
- `wallclub-riskengine-monorepo`
- `wallclub-redis-monorepo`
- `wallclub-celery-worker-monorepo`
- `wallclub-celery-beat-monorepo`

**Depois:**
- `wallclub-django`
- `wallclub-riskengine`
- `wallclub-redis`
- `wallclub-celery-worker`
- `wallclub-celery-beat`

### Passo a Passo da Implementação:

#### **Passo 1: Criar Dockerfiles Especializados**

**Dockerfile.portais:**
```dockerfile
FROM python:3.11-slim
# Copia apenas: portais/, sistema_bancario/, wallclub_core
# DJANGO_SETTINGS_MODULE=wallclub.settings.portais
# Porta 8000
```

**Dockerfile.pos:**
```dockerfile
FROM python:3.11-slim
# Copia apenas: posp2/, pinbank/, parametros_wallclub/, wallclub_core
# DJANGO_SETTINGS_MODULE=wallclub.settings.pos
# Porta 8000
```

**Dockerfile.apis:**
```dockerfile
FROM python:3.11-slim
# Copia apenas: apps/, checkout/, conta_digital/, wallclub_core
# DJANGO_SETTINGS_MODULE=wallclub.settings.apis
# Porta 8000
```

---

#### **Passo 2: Criar Settings Específicos**

**wallclub/settings/portais.py:**
```python
from .base import *

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    # ...
    'portais.admin',
    'portais.lojista',
    'portais.vendas',
    'portais.controle_acesso',
    'sistema_bancario',
]

ROOT_URLCONF = 'wallclub.urls_portais'
```

**wallclub/settings/pos.py:**
```python
from .base import *

INSTALLED_APPS = [
    # Mínimo necessário
    'posp2',
    'pinbank',
    'parametros_wallclub',
]

ROOT_URLCONF = 'wallclub.urls_pos'
```

**wallclub/settings/apis.py:**
```python
from .base import *

INSTALLED_APPS = [
    'apps.cliente',
    'apps.conta_digital',
    'apps.ofertas',
    'apps.transacoes',
    'apps.oauth',
    'checkout',
]

ROOT_URLCONF = 'wallclub.urls_apis'
```

---

#### **Passo 3: Criar URLs Específicos**

**wallclub/urls_portais.py:**
```python
urlpatterns = [
    path('portal_admin/', include('portais.admin.urls')),
    path('portal_vendas/', include('portais.vendas.urls')),
    path('portal_lojista/', include('portais.lojista.urls')),
]
```

**wallclub/urls_pos.py:**
```python
urlpatterns = [
    path('api/posp2/', include('posp2.urls')),
]
```

**wallclub/urls_apis.py:**
```python
urlpatterns = [
    path('api/cliente/', include('apps.cliente.urls')),
    path('api/conta-digital/', include('apps.conta_digital.urls')),
    path('checkout/', include('checkout.urls')),
]
```

---

#### **Passo 4: Ajustar docker-compose.yml**

```yaml
services:
  nginx:
    # Gateway único
    
  wallclub-portais:
    build:
      dockerfile: Dockerfile.portais
    container_name: wallclub-portais
    environment:
      - DJANGO_SETTINGS_MODULE=wallclub.settings.portais
    # Porta 8000 interna
    
  wallclub-pos:
    build:
      dockerfile: Dockerfile.pos
    container_name: wallclub-pos
    environment:
      - DJANGO_SETTINGS_MODULE=wallclub.settings.pos
    # Porta 8000 interna
    
  wallclub-apis:
    build:
      dockerfile: Dockerfile.apis
    container_name: wallclub-apis
    environment:
      - DJANGO_SETTINGS_MODULE=wallclub.settings.apis
    # Porta 8000 interna
    
  wallclub-riskengine:
    # Já existe
    # Porta 8000 interna
  container_name: nginx
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./nginx.conf:/etc/nginx/nginx.conf:ro
    - ./services/django/staticfiles:/staticfiles:ro
  depends_on:
    - wallclub-django
    - wallclub-riskengine
  networks:
    - wallclub-network
```

**Arquivo:** `/WallClub_backend/docker-compose.yml`

---

#### **Passo 2: Criar nginx.conf**

**Objetivo:** Configurar roteamento por subdomínio com rate limiting

**Estrutura:**
```nginx
# Rate limiting zones
limit_req_zone $binary_remote_addr zone=admin:10m rate=5r/s;
limit_req_zone $binary_remote_addr zone=portal:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=api_mobile:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=api_pos:10m rate=50r/s;
limit_req_zone $binary_remote_addr zone=checkout:10m rate=20r/s;

# Upstream Django
upstream django_backend {
    server wallclub-django:8000;
}

# Server blocks (6 subdomínios)
server {
    server_name admin.wallclub.com.br;
    limit_req zone=admin burst=10;
    location / {
        proxy_pass http://django_backend/portal_admin/;
    }
}

server {
    server_name vendas.wallclub.com.br;
    limit_req zone=portal burst=20;
    location / {
        proxy_pass http://django_backend/portal_vendas/;
    }
}

server {
    server_name lojista.wallclub.com.br;
    limit_req zone=portal burst=20;
    location / {
        proxy_pass http://django_backend/portal_lojista/;
    }
}

# APIs - Fase 1 (todos respondem igual)
server {
    server_name api.wallclub.com.br apipos.wallclub.com.br apidj.wallclub.com.br;
    limit_req zone=api_mobile burst=20;
    location / {
        proxy_pass http://django_backend;
    }
}

server {
    server_name checkout.wallclub.com.br;
    limit_req zone=checkout burst=40;
    location / {
        proxy_pass http://django_backend/checkout/;
    }
}
```

**Arquivo:** `/WallClub_backend/nginx.conf`

---

#### **Passo 3: Criar Dockerfile.nginx**

**Objetivo:** Container Nginx customizado

```dockerfile
FROM nginx:1.25-alpine

# Copiar configuração
COPY nginx.conf /etc/nginx/nginx.conf

# Criar diretórios
RUN mkdir -p /var/log/nginx /staticfiles

# Expor portas
EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
```

**Arquivo:** `/WallClub_backend/Dockerfile.nginx`

---

#### **Passo 4: Atualizar variáveis de ambiente**

**Django (.env):**
```bash
# Ajustar URLs internas
REDIS_HOST=wallclub-redis
RISK_ENGINE_URL=http://wallclub-riskengine:8000

# Adicionar domínios permitidos
ALLOWED_HOSTS=admin.wallclub.com.br,vendas.wallclub.com.br,lojista.wallclub.com.br,api.wallclub.com.br,apipos.wallclub.com.br,apidj.wallclub.com.br,checkout.wallclub.com.br,localhost
```

**Risk Engine (.env):**
```bash
REDIS_HOST=wallclub-redis
CALLBACK_URL_PRINCIPAL=http://wallclub-django:8000
```

---

#### **Passo 5: Criar script de teste end-to-end**

**Objetivo:** Validar comunicação entre containers

```python
# scripts/teste_containers.py
import requests
import sys

def testar_health_checks():
    """Testa health checks dos containers"""
    testes = [
        ("Django", "http://wallclub-django:8000/health/"),
        ("Risk Engine", "http://wallclub-riskengine:8000/api/antifraude/health/"),
    ]
    
    for nome, url in testes:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✅ {nome}: OK")
            else:
                print(f"❌ {nome}: ERRO {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ {nome}: {str(e)}")
            return False
    
    return True

def testar_comunicacao_interna():
    """Testa Django → Risk Engine via OAuth"""
    # Implementar teste de análise antifraude
    pass

if __name__ == "__main__":
    if not testar_health_checks():
        sys.exit(1)
    print("\n✅ Todos os testes passaram!")
```

**Arquivo:** `/WallClub_backend/scripts/teste_containers.py`

---

#### **Passo 6: Deploy em produção**

**Comandos:**
```bash
# 1. Fazer backup
docker-compose down
docker system prune -a  # Limpar imagens antigas

# 2. Build dos novos containers
docker-compose build

# 3. Subir containers
docker-compose up -d

# 4. Verificar logs
docker logs -f wallclub-django
docker logs -f wallclub-riskengine
docker logs -f nginx

# 5. Testar health checks
docker exec wallclub-django curl http://localhost:8000/health/
docker exec wallclub-riskengine curl http://localhost:8000/api/antifraude/health/

# 6. Configurar DNS (apontar subdomínios para servidor)
# admin.wallclub.com.br    → IP_SERVIDOR
# vendas.wallclub.com.br   → IP_SERVIDOR
# lojista.wallclub.com.br  → IP_SERVIDOR
# api.wallclub.com.br      → IP_SERVIDOR
# apipos.wallclub.com.br   → IP_SERVIDOR
# checkout.wallclub.com.br → IP_SERVIDOR
```

---

### ✅ Checklist de Validação DEV (03/11/2025):

- ✅ 4 Dockerfiles específicos criados (portais, pos, apis, riskengine)
- ✅ 4 settings.py específicos criados
- ✅ 3 URLs específicos criados (urls_portais.py, urls_pos.py, urls_apis.py)
- ✅ docker-compose.yml com 9 containers configurado
- ✅ nginx.conf com 6 subdomínios + rate limiting
- ✅ Containers rodando localmente (wallclub-portais, wallclub-pos, wallclub-apis, wallclub-riskengine)
- ✅ Nginx roteando corretamente por subdomínio
- ✅ APIs internas funcionando (ofertas, parametros, conta_digital)
- ✅ OAuth POS funcionando
- ✅ Portal Admin - ofertas com campos preenchidos
- ✅ Portal Lojista - ofertas funcionando
- ✅ Health checks respondendo

### 🐛 Correções Aplicadas (03/11/2025):

**1. Container POS - 502 Bad Gateway**
- **Problema:** App label `oauth` duplicado no INSTALLED_APPS
- **Arquivo:** `services/django/wallclub/settings/pos.py`
- **Correção:** Removido `'apps.oauth'` (linha 34) - OAuth já vem do `wallclub_core.oauth`
- **Resultado:** OAuth + endpoints POSP2 funcionando

**2. API Grupos - JSON Parse Error**
- **Problema:** `listar_grupos()` não enviava body, causando `json.loads('')` error
- **Arquivo:** `services/core/wallclub_core/integracoes/ofertas_api_client.py`
- **Correção:** Adicionado `data={}` na linha 137
- **Resultado:** API retornando 2 grupos corretamente

**3. Portal Admin - Campos de data vazios**
- **Problema:** API retorna strings ISO, mas template esperava objetos datetime
- **Arquivos:** 
  - `services/django/portais/admin/views_ofertas.py` (linhas 214-223, 36-40)
  - `services/django/portais/admin/templates/portais/admin/ofertas_form.html` (linhas 110, 122)
  - `services/django/portais/admin/templates/portais/admin/ofertas_list.html` (linhas 66-71)
- **Correção:** Formatar strings ISO para `datetime-local` (remover segundos: `[:16]`)
- **Resultado:** Datas aparecendo corretamente na listagem e edição de ofertas

### ⏳ Checklist Produção (04/11/2025):

- [ ] Deploy em servidor de produção
- [ ] DNS configurado (6 subdomínios)
- [ ] SSL/TLS configurado (Certbot)
- [ ] Logs centralizados
- [ ] Monitoramento ativo
- [ ] Backup configurado
- [ ] Validação end-to-end em produção

### Comandos de Deploy:

```bash
# Deploy completo
docker-compose up -d --build

# Deploy apenas Django (sem afetar outros)
docker-compose up -d --build --no-deps wallclub-django

# Deploy apenas Risk Engine
docker-compose up -d --build --no-deps wallclub-riskengine

# Restart sem rebuild
docker-compose restart wallclub-django wallclub-riskengine

# Logs específicos
docker logs -f wallclub-django
docker logs -f wallclub-riskengine
docker logs -f nginx
```

### Benefícios da Arquitetura:

✅ **Deploy Independente** - Atualizar Django sem afetar Risk Engine  
✅ **Segurança em Camadas** - Rate limiting diferenciado por subdomínio  
✅ **Monitoramento Específico** - Logs separados por tipo de acesso  
✅ **Escalabilidade** - Adicionar réplicas de containers específicos  
✅ **Troubleshooting** - Isolar problemas por serviço  
✅ **Zero Downtime** - Deploy rolling por container  
✅ **Transição Suave** - Aliases no Nginx (zero mudança no código)

---

## 📊 MÉTRICAS FINAIS

### Antes (Outubro 2025):
- **Containers:** 2 (web + riskengine)
- **Repositórios:** 3 separados
- **Deploy:** Tudo junto
- **Acoplamento:** Alto (103 imports cruzados)
- **Bugs:** device_fingerprint duplicado

### Depois Fase 6A+6B+6C (Novembro 2025):
- **Containers:** 2 funcionais + 1 package
- **Repositórios:** 1 monorepo unificado
- **CORE:** Limpo (0 imports de apps)
- **Dependências:** Resolvidas (26 APIs + 17 lazy imports)
- **Acoplamento:** 0 imports diretos
- **Package:** wallclub_core instalado
- **Arquivos migrados:** 113
- **Bug:** ✅ Corrigido

### Resultado Fase 6D (03/11/2025):
- ✅ **Containers:** 9 (nginx + 4 django + redis + 3 celery)
- ✅ **Django Separado:** 4 containers (portais, pos, apis, riskengine)
- ✅ **Subdomínios:** 6 (admin, vendas, lojista, api, apipos, checkout)
- ✅ **Deploy:** Independente por container
- ✅ **Comunicação:** APIs REST + OAuth (interna)
- ✅ **Escalabilidade:** Horizontal por container
- ✅ **Manutenção:** Isolada (atualizar portais sem afetar POS)
- ✅ **Gateway:** Nginx centralizado (única porta externa)
- ✅ **Correções aplicadas:** 3 bugs corrigidos (OAuth POS, API grupos, campos data)

---

## 📝 COMMITS PRINCIPAIS

### Fase 6A:
- `b366851` - feat(fase6a): CORE limpo
- `4e2fc56` - fix: device_fingerprint sobrescrito

### Fase 6B:
- `c6f98d5` - INICIO DA FASE 6B
- `7416f3a` - feat(conta-digital): APIs internas
- `286e0f5` - feat(fase6b): APIs ofertas + SQL direto
- `ee0e369` - Lazy imports (17 arquivos)

### Fase 6C:
- Initial commit - Monorepo completo
- feat(core): Package wallclub_core criado
- refactor: Migrar 113 arquivos para wallclub_core

### Fase 6D:
- `03/11/2025` - feat(fase6d): 4 containers independentes
- `03/11/2025` - fix(pos): OAuth duplicado removido
- `03/11/2025` - fix(ofertas): API grupos + campos data
- `03/11/2025` - docs: Fase 6D concluída em DEV

---

**Documentação Completa:** 03/11/2025  
**Responsável:** Jean Lessa  
**Versão:** Consolidada FASE_6 (A+B+C+D em andamento)
