antes# WallClub - Backend Monorepo

Repositório unificado contendo todos os serviços do ecossistema WallClub, criado na **Fase 6C** (Novembro 2025) e finalizado na **Fase 6D** (05/11/2025) com 4 containers Django independentes.

Sistema fintech completo com gestão financeira, antifraude, portais web e APIs mobile.

## 🚨 STATUS ATUAL

**Última Atualização:** 31/01/2026

### Produção - 9 Containers Orquestrados
- ✅ **Nginx Gateway** (porta 8005) - 14 subdomínios
  - Incluindo checkout.wallclub.com.br e flower.wallclub.com.br
- ✅ **wallclub-portais** (Admin + Vendas + Lojista + Institucional)
  - ✅ **Arquitetura de URLs Refatorada (31/01):** 3 arquivos (antes 8), função helper dinâmica, zero duplicação
  - ✅ Portal Vendas: Sistema de primeiro acesso implementado
  - ✅ Portal Vendas: Filtro por portal corrigido (14/12/2025)
  - ✅ Portal Lojista: Sistema de Ofertas ativo (menu visível)
  - ✅ Portal Lojista: Sistema de Cashback Loja (CRUD completo)
  - ✅ Portal Admin: Gestão de Terminais com histórico (20/12/2025)
  - ✅ Portal Admin: RPR - Refinamento completo de métricas (03/02/2026)
    - Coluna "Custo ajuste nos Repasses" reposicionada e renomeada
    - Nova coluna "Resultado Operacional Ajustado" (Resultado Operacional + Custo ajuste)
    - Box "Resultado Financeiro" recalculado (Receita Financeira - Custo Direto)
    - "Custos POS/Equip" movido para box Resultado Financeiro
    - Percentual de comissão dinâmico (tabela canal_comissao) em tela e exports
  - ⚠️ Portal Admin: Dashboard Celery (`/celery/`) - tasks agendadas não aparecem (em investigação)
- ✅ **wallclub-pos** (Terminal POS + Pinbank)
  - ✅ Sistema de Cupom: Validação e aplicação de descontos
  - ✅ Slip: Correções completas (13/12/2025)
    - Valor da parcela: recalcula valores[19] após arredondar valores[20]
    - Labels: usa valores[14] para decidir encargo vs desconto
    - Separação: tarifas Wall vs encargos operadora
- ✅ **wallclub-apis** (Mobile + Checkout Web)
  - ✅ Checkout: Domínio dedicado checkout.wallclub.com.br
  - ✅ Checkout: Sistema de Cupom integrado (validação interna)
  - ✅ **Checkout: Campos estruturados (03/02/2026)**
    - CheckoutCliente e CheckoutToken com endereço estruturado
    - Campos: `logradouro`, `numero`, `complemento`, `bairro`, `cidade`, `estado`, `cep`, `data_nascimento`, `email`
    - Portal de Vendas: Formulários de cadastro/edição atualizados
    - Integração ViaCEP para preenchimento automático
  - ✅ POSP2 V2: Simulação com cashback Wall + Loja integrado
  - ✅ Checkout 2FA: Integração com Risk Engine completa
  - ✅ Correções 14/12/2025:
    - Fix: validar-otp com múltiplos clientes (filtro por loja_id)
    - Fix: loja_id passado para PinbankService (2 métodos)
    - Fix: Portal Vendas filtra apenas lojas do portal (5 queries)
- ✅ **wallclub-riskengine** (Antifraude + MaxMind)
- ✅ **wallclub-redis** (Cache + Broker)
- ✅ **wallclub-celery-worker** (Unificado - acesso a todos os apps)
- ✅ **wallclub-celery-beat** (Scheduler - 4 tasks agendadas)
- ✅ **wallclub-flower** (Monitoramento Celery) - flower.wallclub.com.br

### Integrações Externas
- ✅ **AWS SES** - Email transacional (ConfigManager)
- ✅ **AWS Secrets Manager** - Credenciais centralizadas
- ✅ **MaxMind minFraud** - Score antifraude
- ✅ **Pinbank** - Gateway de pagamento (Credenciadora)
- ✅ **Own Financial** - Gateway de pagamento (Adquirência + E-commerce) ⭐ **COMPLETO (06/02/2026)**
  - ✅ APIs Adquirência (OAuth 2.0) - Produção funcionando
  - ✅ Webhooks tempo real (transações, liquidações, cadastro) - endpoints implementados e testados
  - ✅ API OPPWA E-commerce - Integração completa e validada
  - ✅ **Ambiente Centralizado (05/02):** `CredenciaisOwnService.obter_environment()` usado em todos os 7 services
  - ✅ API de consulta de tokens e-commerce por contrato documentada
  - ✅ Documentação oficial OPPWA referenciada: https://docs.payments-own.financial/reference/parameters
  - ✅ Portal de Vendas com GatewayRouter (seleção dinâmica Pinbank/Own)
  - ✅ Tokenização, pagamento com token, pagamento direto, estorno e exclusão
  - ✅ **Payload Otimizado (03/02):** Campos estruturados de cliente e endereço
    - Merchant: `taxId` (CNPJ), `id` (razão social), `postcode` (CEP)
    - Customer: `birthDate`, `email`, `phone`, `identificationDocType: TAXSTATEMENT`
    - Billing/Shipping: `city`, `state`, `postcode`, `country`
  - ✅ Transação aprovada com payload completo (NSU: 8ac7a4a19c22cdec019c2357e13915e2)
  - ✅ **Rotinas de Carga (05/02):**
    - `carga_transacoes_own` - Busca transações POS via API `/buscaTransacoesGerais` (não retorna e-commerce)
    - `carga_liquidacoes_own` - Busca liquidações via API `/consultaLiquidacoes`
    - `carga_base_unificada_checkout_own` - Processa checkout_transactions (gateway='OWN') para base_transacoes_unificadas
    - Suporte a busca por NSU específico (`--nsu`) e período (`--data-inicial`, `--data-final`)
  - ✅ **E-commerce e Webhooks (06/02):**
    - Webhook testado: `https://wcapi.wallclub.com.br/webhook/own/transacao/` ✅ funcional
    - Campos novos em `checkout_transactions`: `card_bin`, `card_last4`, `payment_brand_response`, `result_code`, `tx_transaction_id`
    - Renomeações: `pinbank_response` → `gateway_response`, `erro_pinbank` → `erro_gateway`
    - **Limitação:** API `/buscaTransacoesGerais` NÃO retorna transações e-commerce (apenas POS físico)
    - **Identificadores:** `merchantTransactionId` e `id` (OPPWA) não funcionam como `identificadorTransacao`
    - **Webhook obrigatório:** Único meio de obter `identificadorTransacao` para transações e-commerce
  - ⏳ **Pendente:** Configuração do webhook de e-commerce com a OWN (aguardando suporte)
- ✅ **WhatsApp Business API** - 2FA e notificações
- ✅ **Firebase/APN** - Push notifications

### Sistema de Monitoramento ⭐ **NOVO (31/01/2026)**
- ✅ **Prometheus** (porta 9090) - Coleta de métricas (retenção 15 dias)
- ✅ **Alertmanager** (porta 9093) - Gerenciamento de alertas
- ✅ **Node Exporter** (porta 9100) - Métricas de sistema (CPU, memória, disco)
- ✅ **Redis Exporter** (porta 9121) - Métricas do Redis
- ✅ **14 Alertas Configurados:**
  - Críticos: ServiceDown (30s), RedisDown (1min), MySQLDown (1min), DiskSpaceLowCritical (<10%)
  - Warnings: HighCPU (>80%), HighMemory (>90%), LowAvailability (<95%), e mais
- ✅ **Notificações:**
  - Telegram: @Wallclub_monitor_bot
  - Email: AWS SES
- ✅ **Métricas Customizadas:** `/metrics` em todos os 4 containers Django
- ✅ **Health Checks:** `/health/`, `/health/live/`, `/health/ready/`, `/health/startup/`
- 📖 **Documentação:** `monitoring/README.md`

### Fases Concluídas
- ✅ **Fase 1:** Segurança Básica (Rate limiting, OAuth, Auditoria)
- ✅ **Fase 2:** Antifraude (MaxMind, 9 regras, Dashboard)
- ✅ **Fase 3:** Services (22 services, 25 queries eliminadas)
- ✅ **Fase 4:** 2FA + Device Management (Checkout 2FA, Login Simplificado)
- ✅ **Fase 5:** Unificação Portais (Sistema Multi-Portal, Recorrências)
- ✅ **Fase 6A:** CORE Limpo (0 imports de apps)
- ✅ **Fase 6B:** Dependências Resolvidas (26 APIs REST internas)
- ✅ **Fase 6C:** Monorepo + wallclub_core (113 arquivos migrados)
- ✅ **Fase 6D:** 4 Containers Independentes (Deploy em produção)
- ⚠️ **Fase 7:** Integração Own Financial (95% - API QA com problemas de performance)
- ✅ **Refatoração Base Transações (16/12/2025):**
  - ✅ Criada `base_transacoes_unificadas` (1 linha por NSU)
  - ✅ Migrados todos os portais (Admin, Lojista) e APIs Mobile
  - ✅ Eliminadas 16+ queries com `ROW_NUMBER()`
  - ✅ Processo de carga com UPDATE automático
  - ⚠️ Pendente: Revisão completa e desativação de `baseTransacoesGestao`
- ✅ **Migração Terminais DATETIME (20/12/2025):**
  - ✅ Campos `inicio`/`fim`: INT (Unix timestamp) → DATETIME
  - ✅ View `wallclub.terminais` → Tabela real com índices
  - ✅ Model Django atualizado com propriedades `ativo`, `inicio_date`, `fim_date`
  - ✅ Queries SQL atualizadas (Pinbank cargas, services, portais)
  - ✅ Portal Admin: Página de histórico (terminais inativos)
  - ✅ Template filters compatíveis com DATETIME e timestamp
- ✅ **Migração Pinbank para transactiondata_pos (23/12/2025):**
  - ✅ Endpoint `/trdata/` (Pinbank) grava em `transactiondata_pos`
  - ✅ Tabela unificada com campos Pinbank + Own
  - ✅ `PinbankService` suporta `transactiondata_pos` (busca loja/canal)
  - ✅ Calculadora usa tabela unificada
  - ✅ Migração histórica: `transactiondata` → `transactiondata_pos`
  - ⏳ Trigger de sincronização ativo (período de transição)
- ✅ **Abstração Calculadoras Base (24/12/2025):**
  - ✅ `CalculadoraBaseUnificada`: Wallet (Checkout + POS Pinbank/Own)
  - ✅ `CalculadoraBaseCredenciadora`: TEF (Credenciadora)
  - ✅ Parâmetros obrigatórios: `info_loja` e `info_canal` (sem busca interna)
  - ✅ Todas as cargas migradas (Checkout, Credenciadora, POS Pinbank, POS Own)
  - ✅ Campo `origem_transacao`: LINK_PAGAMENTO, RECORRENCIA, TEF, POS
  - ✅ Campo `tipo_operacao`: Wallet, Credenciadora
  - ✅ Deprecados: `CalculadoraBaseGestao`, `calculadora_tef.py`
- ✅ **Sistema Backsync POS (23/01/2026):**
  - ✅ Novo endpoint: `/api/v1/posp2/transactiondata_pos_backsync/`
  - ✅ Tabela: `transactiondata_pos_backsync` (sincronização offline)
  - ✅ Service: `TransactionDataPosBacksyncService` (idempotência)
  - ✅ Substitui: `/api/v1/posp2/transaction_sync_service/` (deprecated)
  - 🔴 **Depreciações Planejadas:**
    - `/api/v1/posp2/transaction_sync_service/` → `transactiondata_pos_backsync`
    - `/api/v1/posp2/trdata/` → `trdata_pinbank` e `trdata_own`
    - Tabela `posp2_transactions` → `transactiondata_pos_backsync`
  - 📄 Documentação: `docs/em execucao/deprecar_pos.md`

## 📋 Navegação Rápida

- [Estrutura](#estrutura)
- [Serviços](#serviços)
- [Variáveis de Ambiente](#variáveis-de-ambiente)
- [Desenvolvimento Local](#desenvolvimento-local)
- [Deployment](#deployment)
- [Arquitetura](#arquitetura)
- [Documentação](#documentação)
- [Histórico](#histórico)

## Estrutura

```
WallClub_backend/
├── services/
│   ├── django/          # 4 containers Django (portais, pos, apis, riskengine)
│   │   ├── apps/         # APIs Mobile (cliente, conta_digital, ofertas, transacoes)
│   │   ├── checkout/     # Checkout Web + Recorrências
│   │   ├── portais/      # Admin + Lojista + Vendas + Corporativo + Controle Acesso
│   │   ├── posp2/        # Terminal POS
│   │   ├── pinbank/      # Integração Pinbank + Cargas
│   │   └── parametros_wallclub/  # Parâmetros financeiros
│   ├── riskengine/      # Engine Antifraude (porta 8005)
│   └── core/            # Package compartilhado (wallclub_core)
├── docs/                # Documentação consolidada (Fases 1-6)
│   ├── architecture/    # Arquitetura e visão integrada
│   ├── development/     # Diretrizes de desenvolvimento
│   ├── em execucao/     # Fases concluídas (1-6)
│   └── deployment/      # Deploy produção
├── docker-compose.yml   # 10 containers orquestrados
├── nginx.conf           # Gateway com 14 subdomínios
├── Dockerfile.portais   # Container portais
├── Dockerfile.pos       # Container POS
├── Dockerfile.apis      # Container APIs
├── Dockerfile.riskengine # Container Risk Engine
├── Dockerfile.nginx     # Container Nginx
├── README.md            # Este arquivo
└── wallclub.code-workspace
```

## Serviços

### 1. Container Portais (wallclub-portais)

**Porta:** 8005 (interna)
**Subdomínios:**
- wcadmin.wallclub.com.br (responde na raiz `/`)
- wcvendas.wallclub.com.br
- wclojista.wallclub.com.br
- wcinstitucional.wallclub.com.br

**Módulos:**
- **portais/admin/** - Portal administrativo
  - Dashboard Celery (`/celery/`) - Monitoramento de tasks agendadas e workers
  - Dashboard Antifraude - Revisão manual de transações
- **portais/lojista/** - Portal lojista
- **portais/vendas/** - Portal vendas/checkout interno
- **portais/corporativo/** - Portal institucional público
- **portais/controle_acesso/** - Sistema Multi-Portal (3 tabelas) + Email Service
- **sistema_bancario/** - Gestão bancária

**Email Service:**
- Templates centralizados em `/templates/emails/`
- Integração AWS SES via ConfigManager
- Suporte a HTML + anexos

**Settings:** `wallclub.settings.portais`

## Variáveis de Ambiente

### Produção (.env.production)

**URLs Base:**
```bash
BASE_URL=https://wcadmin.wallclub.com.br
CHECKOUT_BASE_URL=https://checkout.wallclub.com.br
PORTAL_LOJISTA_URL=https://wclojista.wallclub.com.br
PORTAL_VENDAS_URL=https://wcvendas.wallclub.com.br
MEDIA_BASE_URL=https://wcapi.wallclub.com.br
MERCHANT_URL=https://wallclub.com.br  # URL do estabelecimento (obrigatória para Own Financial)
```

**Segurança:**
```bash
DEBUG=False
ALLOWED_HOSTS=wcapi.wallclub.com.br,wcadmin.wallclub.com.br,wclojista.wallclub.com.br,wcvendas.wallclub.com.br,wcinstitucional.wallclub.com.br,checkout.wallclub.com.br
CORS_ALLOWED_ORIGINS=https://wallclub.com.br,https://wcadmin.wallclub.com.br,https://wclojista.wallclub.com.br,https://wcvendas.wallclub.com.br,https://wcinstitucional.wallclub.com.br,https://checkout.wallclub.com.br
```

**Observações:**
- Domínios `.local` apenas em desenvolvimento (`DEBUG=True`)
- HTTP apenas em desenvolvimento
- HTTPS obrigatório em produção
- CORS validado via middleware (não manual)

### 2. Container POS (wallclub-pos)

**Porta:** 8006 (interna)
**Subdomínio:** wcapipos.wallclub.com.br (REMOVIDO - agora usa wcapi.wallclub.com.br)

**Módulos:**
- **posp2/** - Terminal POS (OAuth 2.0)
  - `/trdata/` - Endpoint transações Pinbank
  - `/trdata_own/` - Endpoint transações Own/Ágilli ✅ NOVO
  - Models: TransactionData (Pinbank), TransactionDataOwn (Own)
- **pinbank/** - Integração Pinbank + Cargas automáticas
- **adquirente_own/** - Integração Own Financial ✅ NOVO
  - E-commerce (API OPPWA)
  - Webhooks tempo real
  - Cargas automáticas (transações + liquidações)
- **parametros_wallclub/** - Sistema de parâmetros financeiros (3.840 configurações)

**Settings:** `wallclub.settings.pos`

### 3. Container APIs Mobile (wallclub-apis)

**Porta:** 8007 (interna)
**Subdomínios:**
- api.wallclub.com.br / wcapi.wallclub.com.br
- checkout.wallclub.com.br / wccheckout.wallclub.com.br

**Módulos:**
- **apps/cliente/** - JWT Customizado (18 cenários testados)
- **apps/conta_digital/** - Saldo, Cashback, Autorizações
- **apps/ofertas/** - Sistema de Ofertas Push (✅ Implementado 01/12/2025)
  - 5 tabelas (ofertas, grupos, disparos, envios)
  - Escopo: loja ou grupo econômico
  - Segmentação: todos do canal ou grupo customizado
  - Portal Lojista com CRUD completo
- **apps/transacoes/** - Transações mobile
- **checkout/** - Checkout Web + 2FA WhatsApp + Recorrências
  - Integração com Risk Engine para análise de risco
  - Rate limiting por telefone/IP
  - Validação progressiva de limites

**Settings:** `wallclub.settings.apis`

### 4. Container Risk Engine (wallclub-riskengine)

**Porta:** 8008 (interna)
**Acesso:** Interno (chamado por outros containers via API REST)

**Módulos:**
- **antifraude/** - Motor antifraude (9 regras)
- **MaxMind minFraud** - Score 0-100 (cache 1h, hit rate >90%)
- **Sistema Segurança Multi-Portal** - 6 detectores Celery
- **Portal Revisão Manual** - Dashboard + Blacklist/Whitelist

**Settings:** `riskengine.settings`

**Stack Comum:**
- Django 4.2.23
- DRF 3.16.1
- MySQL 8.0 (compartilhado)
- Redis 7 (compartilhado)
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
- `email_service.py` - AWS SES (credenciais via ConfigManager)
- `firebase_service.py` - Firebase Cloud Messaging
- `sms_service.py` - Gateway SMS
- `whatsapp_service.py` - WhatsApp Business API

**Configuração:**
- `config_manager.py` - AWS Secrets Manager + Parameter Store
  - Banco de dados (MySQL)
  - Email (AWS SES)
  - Pinbank
  - Bureau (MaxMind)
  - Risk Engine OAuth

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

### Setup Docker (Recomendado)

```bash
# Clone o repositório
git clone <url>
cd WallClub_backend

# Desenvolvimento (sem nginx, celery, flower)
docker exec wallclub-redis redis-cli FLUSHALL  # Limpar cache
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# Verificar status
docker ps

# Logs
docker logs wallclub-portais --tail 50
docker logs wallclub-apis --tail 50
```

**Acessos locais:**
- Admin: http://localhost:8005/portal_admin/
- Lojista: http://localhost:8005/portal_lojista/
- Vendas: http://localhost:8005/portal_vendas/
- APIs: http://localhost:8007/api/v1/
- Checkout: http://localhost:8007/api/v1/checkout/

**Arquivo `.env` (desenvolvimento):**
```bash
# services/django/.env
DEBUG=True
MERCHANT_URL=https://wallclub.com.br
CHECKOUT_BASE_URL=http://localhost:8007
# ... outras variáveis
```

### Docker (Produção)

```bash
# Build e iniciar todos os serviços
docker-compose up -d --build

# Verificar logs
docker-compose logs -f wallclub-portais
docker-compose logs -f wallclub-riskengine

# Parar serviços
docker-compose down
```

## Arquitetura
### VSCode Workspace

Abrir o workspace multi-folder:
```bash
code wallclub.code-workspace
```

Estrutura:
- WallClub Portais (Admin/Vendas/Lojista - 8005)
- WallClub POS (Terminal POS - 8006)
- WallClub APIs (Mobile/Checkout - 8007)
- WallClub Risk Engine (Antifraude - 8008)
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

### Deploy Completo (Todos os Containers)
```bash
cd /var/www/WallClub_backend
git pull origin main
docker-compose down
docker-compose up -d --build
docker ps  # Verificar status
```

**Nota:** `collectstatic` é executado automaticamente via `docker-entrypoint.sh`

### Deploy Seletivo - Portais
```bash
git pull origin main
docker-compose up -d --build --no-deps wallclub-portais wallclub-celery-worker-portais
```

### Deploy Seletivo - POS (Crítico)
```bash
git pull origin main
docker-compose up -d --build --no-deps wallclub-pos
```

### Deploy Seletivo - APIs Mobile
```bash
git pull origin main
docker-compose up -d --build --no-deps wallclub-apis wallclub-celery-worker-apis
```

### Deploy Seletivo - Risk Engine
```bash
git pull origin main
docker-compose up -d --build --no-deps wallclub-riskengine
```

### Deploy Seletivo - Nginx (Configuração)
```bash
git pull origin main
docker-compose up -d --build --no-deps nginx
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

### Fase Atual: 6D - 4 Containers Independentes ✅

**Concluído em:** 05/11/2025

**Arquitetura Implementada:**
```
Internet (80/443)
    ↓
Nginx Gateway (porta 8005)
  ├─ admin.wallclub.com.br / wcadmin.wallclub.com.br           → wallclub-portais:8005
  ├─ vendas.wallclub.com.br / wcvendas.wallclub.com.br         → wallclub-portais:8005
  ├─ lojista.wallclub.com.br / wclojista.wallclub.com.br       → wallclub-portais:8005
  ├─ institucional.wallclub.com.br / wcinstitucional.wallclub.com.br → wallclub-portais:8005
  ├─ api.wallclub.com.br / wcapi.wallclub.com.br               → wallclub-apis:8007
  ├─ apipos.wallclub.com.br / wcapipos.wallclub.com.br         → wallclub-pos:8006
  └─ checkout.wallclub.com.br / wccheckout.wallclub.com.br     → wallclub-apis:8007
    ↓
9 Containers:
  1. nginx (gateway)
  2. wallclub-portais (Admin + Vendas + Lojista)
  3. wallclub-pos (Terminal POS)
  4. wallclub-apis (Mobile + Checkout)
  5. wallclub-riskengine (Antifraude)
  6. wallclub-redis (Cache + Broker)
  7. wallclub-celery-worker-portais
  8. wallclub-celery-worker-apis
  9. wallclub-celery-beat (Scheduler)
```

**Benefícios Alcançados:**
- ✅ Deploy independente por container
- ✅ Escalabilidade horizontal
- ✅ Isolamento de falhas
- ✅ Comunicação via 26 APIs REST internas
- ✅ Rate limiting diferenciado por subdomínio
- ✅ Zero downtime em deploys seletivos

### Próximas Evoluções

- Monitoramento (Prometheus + Grafana)
- CI/CD automatizado
- Testes end-to-end automatizados
- Kubernetes (migração futura)

## 📚 Documentação

**Documentação Técnica Principal:**
- **[ARQUITETURA.md](docs/ARQUITETURA.md)** - Como o sistema funciona (containers, integrações, fluxos)
- **[DIRETRIZES.md](docs/DIRETRIZES.md)** - Como desenvolver (regras, padrões, boas práticas)

**Guias Específicos:**
- [Setup Local](docs/setup/local.md) - Configuração do ambiente de desenvolvimento
- [Deploy Produção](docs/deployment/producao.md) - Procedimentos de deploy
- [Histórico de Fases](docs/em%20execucao/) - Documentação das fases concluídas (1-6)

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
**Última atualização:** 03/02/2026
**Responsável:** Equipe WallClub

### Atualizações Recentes (03/02/2026)
- **Portal Admin - RPR - Refinamento Completo de Métricas**
  - **Tabela Analítica:**
    - Coluna "Custo ajuste nos Repasses (R$)" reposicionada (antes de var98)
    - Nova coluna "Resultado Operacional Ajustado (R$)" = Resultado Operacional + Custo ajuste nos Repasses
  - **Box "Custo Direto Total":**
    - Linha renomeada: "Custo ajuste nos Repasses"
    - Sinal invertido para exibição (valor positivo)
    - "Custos POS/Equip" removido deste box
    - Cálculo: `custo_mdr + custo_antecipacao + impostos - ajuste_repasses + lancamentos_manuais`
  - **Box "Resultado Financeiro":**
    - Totalizador = `Receita Financeira Total - Custo Direto Total`
    - Comissão Total a Pagar = `Totalizador × Percentual Comissão`
    - "Custos POS/Equip" movido para este box
    - Nova linha: "Resultado após Custos de POS's" = `Totalizador - Custos POS/Equip`
    - Comissão Total Líquida = `Resultado após Custos POS × Percentual Comissão`
  - **Percentual de Comissão:**
    - Cálculo dinâmico usando tabela `canal_comissao`
    - Média ponderada por volume quando sem filtro de canal
    - Sincronizado entre tela e exports (antes era hardcoded 15% no export))
  - JavaScript: Removido truncamento de cabeçalhos (antes limitava a 15 caracteres)

- **Own Financial E-commerce - Correções de Ambiente e Payload**
  - Ambiente dinâmico: `ENVIRONMENT=production` → `LIVE`, `development` → `TEST`
  - Correção do campo `paymentMethod`: movido de `customParameters` para campo direto

### Atualizações Anteriores (24/01/2026)
- **Portal Admin - RPR - Nova Métrica "Ajuste pagos de repasses"**
  - Fórmula: `Resultado Caixa (var98 - var101) - (Resultado MDR + Resultado Antecipação)`
  - Exibida no box "Custo Direto Total" e como nova coluna na tabela RPR
  - Valor arredondado para 2 casas decimais com `.quantize(Decimal('0.01'))`
  - Coluna posicionada após "(98) Valor Recebido Uptal"

- **Portal Admin - Tabelas RPR e Gestão Admin - UX Melhorada**
  - Largura mínima de colunas aumentada de 150px para 200px
  - Largura máxima de células aumentada de 250px para 350px
  - Truncamento de texto removido (sem `text-overflow: ellipsis`)
  - Alinhamento à direita para todas as células (valores monetários e percentuais)
  - JavaScript: Removido truncamento de cabeçalhos (antes limitava a 15 caracteres)

- **Own Financial E-commerce - Correções de Ambiente e Payload**
  - Ambiente dinâmico: `ENVIRONMENT=production` → `LIVE`, `development` → `TEST`
  - Correção do campo `paymentMethod`: movido de `customParameters` para campo direto
  - API de consulta de tokens por contrato documentada: `GET /agilli/ecommerce/token?numeroContrato=XXX`
  - Documentação oficial OPPWA adicionada ao `PLANO_REPLICACAO_ESTRUTURA.md`
  - Links: API Reference, Server-to-Server Guide, Tokenization, Result Codes, Webhooks

### Atualizações Anteriores (24/01/2026)
- ✅ **Conta Digital - Débito de Cashback Corrigido**
  - Método `debitar()` agora verifica `tipo_movimentacao.afeta_cashback`
  - Débito de cashback usa `cashback_disponivel` (antes usava `saldo_atual` incorretamente)
  - Método `estornar_movimentacao()` também verifica `afeta_cashback`
  - `AutorizacaoService.debitar_saldo_autorizado()` usa `tipo_codigo='CASHBACK_DEBITO'`
  - Fluxo POS com uso de saldo de cashback funcionando 100%
  - Validação de saldo correta: verifica `cashback_disponivel` para cashback, `saldo_atual` para dinheiro

### Atualizações Anteriores (08/12/2025)
- ✅ **Transactiondata_pos - Tabela Unificada Pinbank + Own**
  - Campo `gateway` (PINBANK/OWN) para identificar origem
  - Campo `desconto_wall_parametro_id` para rastrear regra de desconto aplicada
  - Campos `cashback_wall_parametro_id` e `cashback_loja_regra_id` já existentes
  - Endpoints: `/trdata_pinbank/` e `/trdata_own/`
  - Service: `TRDataPosService` (parser específico por gateway)
- ✅ **Sistema Cashback Centralizado - Funcionando**
  - Corrigido erro `ParametrosWall.plano` (não existe - usar `id_plano`)
  - Import `timezone` corrigido em todos os métodos de `CashbackService`
  - Corrigido `timezone.timedelta` para `timedelta` em `ContaDigitalService`
  - Tipo movimentação: `CASHBACK_CREDITO` (unificado para Wall e Loja)
  - Integração completa com Conta Digital
  - Cashback Wall e Loja sendo creditados corretamente
- ❌ **Conta Digital - Movimentações Informativas REMOVIDAS**
  - Decisão: Conta digital deve ter apenas movimentações que afetam saldo/cashback
  - Histórico de compras consultado diretamente de `transactiondata_pos` e `checkout_transaction`
  - Tipos removidos: `COMPRA_CARTAO`, `COMPRA_PIX`, `COMPRA_DEBITO`
  - Método `_registrar_compra_informativa()` removido
- ⏳ **API Extrato Consolidado - PENDENTE**
  - Endpoint futuro: `/api/v1/conta_digital/extrato_completo/`
  - Consolidará: movimentações conta + transações POS + checkout
  - Ordenação cronológica unificada
  - Permite filtros por tipo, período, etc
- ✅ **Portal Lojista - Vendas por Operador**
  - Botão "Pesquisar venda por operador" na página de vendas
  - Relatório agrupado por operador POS
  - Métricas: qtde vendas, valor total, ticket médio
  - Totalizador geral
  - URL: `/vendas/operador/`

### Atualizações Anteriores (01/12/2025)
- ✅ **Sistema de Ofertas** - Implementação completa
  - 5 tabelas criadas (ofertas, grupos_segmentacao, grupos_clientes, disparos, envios)
  - Campo `loja_id` e `grupo_economico_id` para escopo
  - Portal Lojista: menu ativo, CRUD completo, disparo de push
  - Segmentação: todos do canal ou grupo customizado
  - Filtros: lojista vê ofertas próprias + ofertas globais (admin)
  - Push notifications via Firebase/APN
  - Histórico de disparos com métricas (total enviados, falhas, taxa sucesso)
- ✅ **Sistema de Cashback** - Em produção
  - Sistema centralizado (Wall + Loja)
  - Contabilização separada por tipo
  - Portal Lojista com CRUD completo

### Atualizações Anteriores (22/11/2025)
- ✅ **Segurança e Domínios** - Ajustes para produção
  - 11 arquivos ajustados (views, settings, services)
  - CORS manual removido (usa middleware)
  - URLs hardcoded substituídas por variáveis de ambiente
  - 6 variáveis de URL adicionadas ao base.py
  - Domínios `.local` apenas em DEBUG=True
  - HTTPS obrigatório em produção
  - Documentação em `docs/SEGURANCA_DOMINIOS_PRODUCAO.md`

### Atualizações Anteriores (20/11/2025)
- ✅ **Integração Own Financial** - Gateway de adquirência em QA/Sandbox
  - OAuth 2.0 com token cache (5min validade, 4min cache)
  - APIs de consulta: transações, liquidações, dados cadastrais
  - Cargas automáticas com comando `carga_transacoes_own --dias N`
  - Webhooks tempo real (transações, liquidações, cadastro)
  - Tabelas: `OwnExtratoTransacoes`, `OwnLiquidacoes`, `credenciaisExtratoContaOwn`
  - Campo `adquirente` em `BaseTransacoesGestao` (PINBANK/OWN)
  - 9 transações carregadas com sucesso no teste
  - Documentação em `docs/integradora own/PLANO_REPLICACAO_ESTRUTURA.md`

### Atualizações Anteriores (14/11/2025)
- ✅ **Upload de Pagamentos via CSV** - Sistema completo de importação em lote
  - Validação em 2 fases (tudo ou nada)
  - Tabela editável com validação de NSU duplicado em tempo real
  - Processamento automático de valores decimais (formato BR e US)
  - Integração automática com PinbankExtratoPOS (marca Lido=0 para reprocessamento)
  - Salvamento em lote com transação atômica
  - Documentação completa em `docs/em execucao/UPLOAD_PAGAMENTOS_CSV.md`

### Atualizações Anteriores (10/11/2025)
- ✅ **Gestão Admin:** Filtro por tipo de transação (Wallet/Credenciadora)
  - Campo `tipo_operacao` adicionado como primeira coluna (tabela + exports)
  - Checkbox "Incluir transações Credenciadora" no RPR e Gestão Admin
  - App `pinbank` adicionado ao INSTALLED_APPS do container portais
- ✅ **Exports Excel:** Removidas linhas inúteis (título + linha em branco)
  - Headers começam direto na linha 1
- ✅ **RPR:** JavaScript alinhado com filtros padrão do servidor
  - Tabela AJAX usa mesmos filtros que métricas (mês corrente)

### Atualizações Anteriores (07/11/2025)
- ✅ Portal Admin sem prefixo `/portal_admin/` (responde na raiz via wcadmin.wallclub.com.br)
- ✅ SubdomainRouterMiddleware ativo (roteamento por domínio)
- ✅ Sistema de logs unificado (processo único por módulo)
- ✅ Email Service centralizado com AWS SES
- ✅ ConfigManager integrado ao email (busca credenciais do Secrets Manager)
- ✅ Templates de email unificados em `/templates/emails/`

---

## 📊 Estatísticas do Projeto

- **Containers:** 9 (4 Django + Redis + 2 Celery + Beat + Nginx)
- **APIs Internas:** 26 endpoints REST
- **Regras Antifraude:** 9 (5 básicas + 4 autenticação)
- **Parâmetros Financeiros:** 3.840 configurações
- **Cenários JWT Testados:** 18
- **Services Criados:** 22
- **Queries SQL Eliminadas:** 25
- **Arquivos Migrados (Fase 6C):** 113

---

## 📚 Documentação Adicional

### Documentação Técnica
- **[ARQUITETURA.md](docs/ARQUITETURA.md)** - Estrutura técnica detalhada do sistema
- **[DIRETRIZES.md](docs/DIRETRIZES.md)** - Regras e padrões de desenvolvimento
- **[PENDENCIAS_SEGURANCA.md](docs/PENDENCIAS_SEGURANCA.md)** - Pendências e melhorias de segurança

### Risk Engine (Antifraude)
- **[Motor Antifraude](docs/riskengine/engine_antifraude.md)** - Documentação completa do sistema antifraude
- **[Integração Autenticação](docs/riskengine/integracao_autenticacao_fraude.md)** - Integração com sistema de autenticação

### Deploy e Setup
- **[Setup Local](docs/setup/local.md)** - Configuração ambiente de desenvolvimento
- **[Deploy Produção](docs/deployment/producao.md)** - Procedimentos de deploy
- **[Arquivos Estáticos](docs/deployment/arquivos-estaticos.md)** - Gestão de assets

### Roadmaps e Evoluções
- **[Roadmap Infraestrutura](docs/em%20execucao/ROADMAP_EVOLUCAO_INFRAESTRUTURA.md)** - Plano de evolução da infraestrutura
- **[Cenário Evolução Arquitetura](docs/em%20execucao/cenario_evolucao_arquitetura_JAN2026.md)** - Análise arquitetural e melhorias
