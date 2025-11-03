# WallClub - Backend Monorepo

Repositório unificado contendo todos os serviços do ecossistema WallClub, criado na **Fase 6C** (Novembro 2025) como parte da evolução arquitetural para containers independentes.

Sistema de gestão financeira e antifraude com múltiplos containers orquestrados.

## 🚨 STATUS ATUAL

**Última Atualização:** 02/11/2025 21:27

### Produção
- ✅ Django Principal (wallclub-django-monorepo:8000)
- ✅ Risk Engine (wallclub-riskengine-monorepo:8004)
- ✅ Portal Admin Antifraude
- ✅ Atividades Suspeitas & Bloqueios
- 🔴 **BLOQUEADOR:** POS → Risk Engine (TypeError em `/api/antifraude/analyze/`)

### Pendências Técnicas
📋 **Ver:** [`docs/em execucao/PENDENCIAS_TECNICAS.md`](docs/em%20execucao/PENDENCIAS_TECNICAS.md)

**Problema Crítico:**
- Decorator `@handle_api_errors` depende de `LogParametro` que não existe no Risk Engine
- Causa TypeError 500 em transações POS
- Solução em andamento: simplificar decorator ou usar try/except manual

## 📋 Navegação Rápida

- [Estrutura](#estrutura)
- [Serviços](#serviços)
- [Desenvolvimento Local](#desenvolvimento-local)
- [Deployment](#deployment)
- [Arquitetura](#arquitetura)
- [Documentação](#documentação)
- [Histórico](#histórico)

## Estrutura

```
WallClub_backend/
├── services/
│   ├── django/          # API Principal (porta 8003)
│   ├── riskengine/      # Engine Antifraude (porta 8004)
│   └── core/            # Package compartilhado (wallclub_core)
├── docs/                # Documentação consolidada
│   ├── architecture/    # Arquitetura e visão integrada
│   ├── development/     # Diretrizes de desenvolvimento
│   ├── services/        # READMEs detalhados por serviço
│   ├── setup/           # Setup local
│   └── deployment/      # Deploy produção
├── docker-compose.yml
├── README.md            # Este arquivo
└── wallclub.code-workspace
```

## Serviços

### 1. Django (services/django/)

**Porta:** 8003  
**Descrição:** API principal do WallClub

**Componentes:**
- **Apps:** Cliente, Conta Digital, Ofertas, Transações, OAuth
- **Checkout:** Link de Pagamento, Recorrência
- **Portais:** Admin, Lojista, Controle de Acesso, Vendas
- **PinBank:** Cargas de extrato, base de gestão, TEF
- **Parâmetros:** Calculadora de descontos, configurações financeiras
- **POSP2:** Terminal virtual, tokenização
- **Sistema Bancário:** Pagamentos, lançamentos

**Stack:**
- Django 4.2.23
- DRF 3.16.1
- MySQL 5.7
- Redis 5.0.1
- Celery 5.3.4

### 2. Risk Engine (services/riskengine/)

**Porta:** 8004  
**Descrição:** Motor de análise antifraude e scoring de risco

**Componentes:**
- **Antifraude:** Análise de transações, scoring, regras
- **APIs:** Endpoints para consulta de risco
- **Integrações:** Bureau (MaxMind minFraud)

**Stack:**
- Django 4.2.11
- DRF 3.14.0
- MySQL 5.7
- Redis 5.0.1
- Celery 5.3.4

### 3. Core (services/core/)

**Descrição:** Package Python compartilhado entre serviços  
**Instalação:** `wallclub_core @ file:///../core`

**Componentes:**

#### database/
- `queries.py` - Queries SQL diretas (read-only)

#### decorators/
- `api_decorators.py` - Decorators para APIs REST

#### estr_organizacional/
- Canal, Loja, Regional, Grupo Econômico, Vendedor
- Services de estrutura organizacional

#### integracoes/
**APIs Internas:**
- `ofertas_api_client.py` - Cliente API Ofertas
- `parametros_api_client.py` - Cliente API Parâmetros

**Serviços Externos:**
- `apn_service.py` - Apple Push Notifications
- `bureau_service.py` - MaxMind minFraud
- `email_service.py` - AWS SES
- `firebase_service.py` - Firebase Cloud Messaging
- `sms_service.py` - Gateway SMS
- `whatsapp_service.py` - WhatsApp Business API

**Notificações:**
- `notification_service.py` - Orquestrador
- `notificacao_seguranca_service.py` - Segurança
- `messages_template_service.py` - Templates

#### middleware/
- `security_middleware.py` - Segurança HTTP
- `security_validation.py` - Validações
- `session_timeout.py` - Timeout de sessão

#### oauth/
- `decorators.py` - Autenticação OAuth
- `jwt_utils.py` - JWT customizado
- `models.py` - OAuthClient, OAuthToken
- `services.py` - OAuth 2.0

#### seguranca/
- `services_2fa.py` - 2FA via WhatsApp
- `services_device.py` - Device Management
- `rate_limiter_2fa.py` - Rate limiting
- `validador_cpf.py` - Validação CPF

#### services/
- `auditoria_service.py` - Logs de auditoria

#### templatetags/
- `formatacao_tags.py` - Tags Django

#### utilitarios/
- `config_manager.py` - AWS Secrets Manager
- `export_utils.py` - Excel, PDF
- `formatacao.py` - Formatação de dados
- `log_control.py` - Controle de logs

## Desenvolvimento Local

### Pré-requisitos
- Python 3.11+
- MySQL 5.7+
- Redis
- Docker & Docker Compose

### Setup

```bash
# Clone o repositório
git clone <url>
cd wallclub

# Django
cd services/django
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py runserver 8003

# Risk Engine
cd services/riskengine
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py runserver 8004
```

### Docker (Produção)

```bash
# Build e iniciar todos os serviços
docker-compose up -d --build

# Verificar logs
docker-compose logs -f web
docker-compose logs -f riskengine

# Parar serviços
docker-compose down
```

### VSCode Workspace

Abrir o workspace multi-folder:
```bash
code wallclub.code-workspace
```

Estrutura:
- WallClub Django (Principal - 8003)
- WallClub Risk Engine (Antifraude - 8004)
- WallClub Core (Package Compartilhado)
- Root (Monorepo)

## Histórico

### Antes do Monorepo (até Nov 2025)

```
wall_projects/
├── wallclub_django/         (repo git 1)
├── wallclub-riskengine/     (repo git 2)
└── wallclub_core/           (sem repo)
```

**Problemas:**
- 3 repositórios separados
- Versionamento fragmentado
- Deploy complexo
- Dependências entre repos difícil de gerenciar

### Após Monorepo (Fase 6C)

```
wall_projects/
├── WallClub_backend/        (repo git único)
│   └── services/
│       ├── django/
│       ├── riskengine/
│       └── core/
├── wallclub_django/         (backup - pode remover)
├── wallclub-riskengine/     (backup - pode remover)
└── wallclub_core/           (backup - pode remover)
```

**Benefícios:**
- ✅ 1 repositório unificado
- ✅ Versionamento coordenado
- ✅ Deploy simplificado
- ✅ Histórico unificado
- ✅ Refatorações cross-service simplificadas

### Migração Realizada (Fase 6C)

**Data:** 01/11/2025

**Ações:**
1. Criado package `wallclub_core` a partir do módulo `comum/`
2. Copiados 52 arquivos Python para `services/core/wallclub_core/`
3. Migrados imports em 113 arquivos:
   - Django: 108 arquivos
   - Risk Engine: 5 arquivos
4. Padrão: `from comum.*` → `from wallclub_core.*`
5. Removido diretório `comum/` de ambos os projetos
6. Atualizado `requirements.txt`:
   ```txt
   wallclub_core @ file:///../core
   ```

**Resultado:**
- ✅ Código compartilhado centralizado
- ✅ Sem duplicação
- ✅ Fácil manutenção
- ✅ Pronto para containers

### Script de Migração

Criado `services/core/migrate_imports.py` para automatizar migrações futuras:

```bash
python3 migrate_imports.py /path/to/project
```

## Deployment

### Deploy Completo
```bash
git pull
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Deploy Seletivo (Django apenas)
```bash
git pull
docker-compose stop web celery-worker celery-beat
docker-compose build web celery-worker celery-beat
docker-compose up -d web celery-worker celery-beat
```

### Deploy Seletivo (Risk Engine apenas)
```bash
git pull
docker-compose stop riskengine
docker-compose build riskengine
docker-compose up -d riskengine
```

### Deploy do wallclub_core

Quando atualizar código do `wallclub_core`:

```bash
git pull
# Rebuild TODOS os containers que usam o core
docker-compose stop web riskengine celery-worker celery-beat
docker-compose build web riskengine celery-worker celery-beat
docker-compose up -d web riskengine celery-worker celery-beat
```

## Docker

### Build do wallclub_core

Durante o `docker-compose build`, cada container:

1. Copia código: `COPY . /app`
2. Instala dependências: `RUN pip install -r requirements.txt`
3. Lê `wallclub_core @ file:///../core`
4. Instala package no `site-packages/`

**Resultado:**
```
Container Django:
  /app/services/django/
  /usr/local/lib/python3.11/site-packages/wallclub_core/

Container Risk Engine:
  /app/services/riskengine/
  /usr/local/lib/python3.11/site-packages/wallclub_core/
```

### Volumes Compartilhados (Opcional)

Para desenvolvimento com hot reload:

```yaml
services:
  web:
    volumes:
      - ./services/core:/app/services/core:ro
    environment:
      - PYTHONPATH=/app/services/core
```

## Arquitetura

### Fase Atual: 6C - Core Extraído
- ✅ wallclub_core como package compartilhado
- ✅ Imports migrados de `comum` para `wallclub_core`
- ✅ Monorepo unificado

### Próximas Fases

#### Fase 6D - Separação Física (Semanas 32-36)

**Objetivos:**
1. Criar 5 containers independentes
2. Configurar Nginx Gateway
3. Implementar deploy isolado por container
4. Configurar volumes compartilhados
5. Testes end-to-end

**Arquitetura Alvo:**
```
Nginx Gateway (80/443)
  ├── Django Main (:8000)
  ├── Risk Engine (:8001)
  └── Static Files

Containers:
  - wallclub_django
  - wallclub_riskengine
  - redis
  - celery_worker
  - celery_beat

Volumes:
  /shared/wallclub_core → Package instalado
  /shared/media → Arquivos de mídia
  /shared/logs → Logs centralizados
```

**Benefícios:**
- Deploy independente
- Escalabilidade por app
- Isolamento de falhas
- Comunicação via APIs REST

## Documentação

### Estrutura Consolidada

A documentação foi reorganizada em uma estrutura única no diretório `/docs`:

```
docs/
├── architecture/              # Arquitetura e Visão Integrada
│   ├── README.md             # Índice e navegação
│   ├── 1. ARQUITETURA_GERAL.md
│   ├── 2. DIRETRIZES_UNIFICADAS.md
│   └── 3. INTEGRACOES.md
├── development/               # Diretrizes de Desenvolvimento
│   ├── django-diretrizes.md
│   └── riskengine-diretrizes.md
├── services/                  # READMEs Detalhados
│   ├── django-readme.md
│   └── riskengine-readme.md
├── setup/                     # Configuração
│   └── local.md              # Setup desenvolvimento local
└── deployment/                # Deploy
    └── producao.md           # Procedimentos de deploy
```

### Guias Principais

**Para Começar:**
- [Setup Local](docs/setup/local.md) - Configuração do ambiente de desenvolvimento
- [Arquitetura Geral](docs/architecture/1.%20ARQUITETURA_GERAL.md) - Visão completa do sistema

**Desenvolvimento:**
- [Diretrizes Django](docs/development/django-diretrizes.md) - Padrões e boas práticas Django
- [Diretrizes Risk Engine](docs/development/riskengine-diretrizes.md) - Padrões antifraude
- [Integrações](docs/architecture/3.%20INTEGRACOES.md) - APIs e serviços externos

**Operações:**
- [Deploy Produção](docs/deployment/producao.md) - Procedimentos de deploy
- [README Django](docs/services/django-readme.md) - Documentação completa do Django
- [README Risk Engine](docs/services/riskengine-readme.md) - Documentação completa do Risk Engine

### Documentação nos Serviços

Cada serviço mantém documentação técnica específica:
- **Django:** `services/django/docs/` - Planos estruturados, fases concluídas
- **Risk Engine:** `services/riskengine/docs/` - Engine antifraude, executados
- **Core:** `services/core/README.md` - Package compartilhado

## Versionamento

**Versão Atual:** 1.0.0 (Monorepo Inicial)

**Changelog:**
- 1.0.0 (01/11/2025): Criação do monorepo, extração do wallclub_core

## Contribuição

### Workflow

1. Criar branch: `git checkout -b feature/nome`
2. Fazer alterações
3. Commit: `git commit -m "feat: descrição"`
4. Push: `git push origin feature/nome`
5. Pull Request

### Padrão de Commits

```
feat: nova funcionalidade
fix: correção de bug
refactor: refatoração
docs: documentação
chore: manutenção
test: testes
```

### Quando Atualizar wallclub_core

Se alterar código em `services/core/`:

1. Testar localmente nos 2 serviços
2. Commitar tudo junto (core + serviços)
3. Deploy coordenado (rebuild todos os containers)

## Licença

Proprietary - WallClub © 2025

---

**Criado em:** 02/11/2025  
**Última atualização:** 02/11/2025  
**Responsável:** Equipe WallClub
