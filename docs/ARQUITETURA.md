# ARQUITETURA - WALLCLUB ECOSYSTEM

**Versão:** 5.6  
**Data:** 08/12/2025  
**Status:** 4 containers independentes, 32 APIs internas, Fases 1-7 (95% - Own Financial), Sistema Cashback Centralizado + Compras Informativas + Transactiondata_pos unificada em produção

---

## 📋 ÍNDICE

### Arquitetura
1. [Sobre o Projeto](#sobre-o-projeto)
2. [Arquitetura de Containers](#arquitetura-de-containers)
3. [Status da Migração](#status-da-migração)
4. [Funcionalidades Principais](#funcionalidades-principais)
5. [Risk Engine](#risk-engine)
6. [Estrutura de Diretórios](#estrutura-de-diretórios)
7. [Deploy](#deploy)

### Integrações
8. [APIs Internas - Overview](#apis-internas---overview)
9. [Cliente APIs](#cliente-apis)
10. [Conta Digital APIs](#conta-digital-apis)
11. [Checkout Recorrências APIs](#checkout-recorrências-apis)
12. [Ofertas APIs](#ofertas-apis)
13. [Parâmetros APIs](#parâmetros-apis)
14. [Integrações Externas](#integrações-externas)

**Outros Documentos:**
- [DIRETRIZES.md](DIRETRIZES.md) - Regras de desenvolvimento e padrões de código
- [README.md](../README.md) - Visão geral do projeto

---

## 📋 SOBRE O PROJETO

### WallClub Django (Projeto Principal)

**Sistema fintech** migrado PHP→Django, operacional desde 16/10/2025.

**Responsabilidades:**
- APIs REST móveis (JWT customizado - 18 cenários testados)
- Terminais POS (OAuth 2.0)
- Checkout Web (links + recorrências) - **Roteador multi-gateway (Pinbank/Own)**
- 4 Portais Web (Admin, Lojista, Vendas, Corporativo)
- Cargas automáticas (Pinbank + Own Financial)
  - Pinbank: Extrato POS, Base Gestão, Credenciadora
  - Own: Transações, Liquidações (Webhooks + Double-check diário)
- Parâmetros financeiros (3.840 configurações - 100% validado vs PHP)
- Conta digital (saldo, cashback, autorizações)
- Portal Corporativo público (institucional, sem autenticação)

**Stack:**
- Django 4.2.23 + DRF 3.16.1
- MySQL 8.0 (wallclub + wclub legado)
- Redis 7 (cache + OAuth)
- Gunicorn 21.2.0 (3 workers)
- AWS Secrets Manager

### WallClub Risk Engine (Container Isolado)

**Sistema antifraude** em tempo real desde 16/10/2025.

**Responsabilidades:**
- Análise risco (score 0-100)
- 5 regras antifraude configuráveis
- MaxMind minFraud integration
- 3D Secure 2.0 support
- Portal revisão manual
- 6 detectores automáticos (Celery)

**Stack:**
- Django 4.2.11 (isolado)
- Redis DB 1 (cache separado)
- Celery (worker + beat)
- OAuth 2.0 inter-containers

**Integrações:**
- ✅ POSP2 (Terminal POS)
- ✅ Checkout Web (22/10/2025)
- ✅ Portal Admin
- ✅ Sistema Segurança Multi-Portal (23/10/2025)

---

## 🐳 ARQUITETURA DE CONTAINERS

### Status Atual: 4 Containers Independentes em Produção ✅

**Fases 1-6 Concluídas (05/11/2025):**
- ✅ **Fase 1:** Segurança Básica (Rate limiting, OAuth, Auditoria, CPF)
- ✅ **Fase 2:** Antifraude (MaxMind, 5 regras, Dashboard, POSP2/Checkout integrados)
- ✅ **Fase 3:** Services (22 services criados, 25 queries eliminadas)
- ✅ **Fase 4:** 2FA + Device Management (Checkout 2FA, Login Simplificado, Bypass Apple/Google)
- ✅ **Fase 5:** Unificação Portais (Sistema Multi-Portal, Recorrências, RPR)
- ✅ **Fase 6A:** CORE Limpo (0 imports de apps)
- ✅ **Fase 6B:** Dependências Resolvidas (26 APIs REST + 17 lazy imports)
- ✅ **Fase 6C:** Monorepo + wallclub_core (113 arquivos migrados)
- ✅ **Fase 6D:** 4 Containers Independentes (9 containers totais com Celery)

### 9 Containers em Produção

```
Internet (80/443)
    ↓
┌──────────────────────────────────────────────────────────┐
│  NGINX Gateway (porta 8005)                              │
│  ├─ admin.wallclub.com.br       → portais:8005          │
│  ├─ vendas.wallclub.com.br      → portais:8005          │
│  ├─ lojista.wallclub.com.br     → portais:8005          │
│  ├─ corporativo.wallclub.com.br → portais:8005          │
│  ├─ wallclub.com.br             → portais:8005          │
│  ├─ www.wallclub.com.br         → portais:8005          │
│  ├─ api.wallclub.com.br (UNIFICADO)                     │
│  │   ├─ /api/oauth/*            → apis:8007             │
│  │   ├─ /api/v1/posp2/*         → pos:8006              │
│  │   ├─ /api/internal/*         → apis:8007             │
│  │   └─ /api/v1/*               → apis:8007             │
│  ├─ checkout.wallclub.com.br    → apis:8007             │
│  └─ flower.wallclub.com.br      → flower:5555           │
└──────────────────────────────────────────────────────────┘
         │         │         │         │         │
    ┌────┴────┬────┴────┬────┴────┬────┴────┬────┴────┐
    │         │         │         │         │         │
┌───┴────┐┌──┴────┐┌───┴────┐┌───┴────┐┌──┴────┐┌──┴────┐
│Portais ││ POS   ││ APIs   ││ Risk   ││ Redis ││Flower │
│:8005   ││ :8006 ││ :8007  ││ :8008  ││ :6379 ││ :5555 │
└───┬────┘└───┬───┘└───┬────┘└───┬────┘└───┬───┘└───────┘
    │         │   ▲    │         │         │
    │         │   │    │         │         │ (monitoring)
    │         └───┼────┘         │         │
    │             │              │         │
    └─────────────┴──────────────┴─────────┘
           APIs REST Internas
        (26 endpoints OAuth 2.0)      │
    └─────────────┴──────────────┘
              │
      ┌───────┴────────┐
      │                │
┌─────▼──────┐  ┌──────▼─────┐
│Celery      │  │Celery      │
│Worker      │  │Beat        │
│(Portais+   │  │(Scheduler) │
│ APIs)      │  │            │
└────────────┘  └────────────┘
```

**IMPORTANTE:** DNS `wcapipos.wallclub.com.br` foi **REMOVIDO** em 07/11/2025. Agora todo tráfego de API usa `wcapi.wallclub.com.br` com roteamento por path no Nginx.

### Container 1: Portais (wallclub-portais)

**Porta:** 8005 (interna)
**Recursos:** 3 workers, 1GB RAM, 1.0 CPU

**Módulos:**
- `portais/admin/` - Portal administrativo
- `portais/lojista/` - Portal lojista
- `portais/vendas/` - Portal vendas/checkout interno
- `portais/controle_acesso/` - Sistema Multi-Portal
- `sistema_bancario/` - Gestão bancária

**Settings:** `wallclub.settings.portais`
**URLs:** `wallclub.urls_portais`
**Deploy:** Frequente (features admin/lojista)

### Container 2: POS (wallclub-pos)

**Porta:** 8006 (interna)
**Recursos:** 2 workers, 512MB RAM, 0.5 CPU

**Funcionalidades:**
- `posp2/` - Terminal POS (OAuth 2.0)
  - `/trdata_pinbank/` - Endpoint transações Pinbank 
  - `/trdata_own/` - Endpoint transações Own/Ágilli 
  - Tabela: `transactiondata_pos` (gateway: PINBANK/OWN)
  - Service: `TRDataPosService` (parser específico por gateway)
- `pinbank/` - Integração Pinbank + Cargas
- `adquirente_own/` - Integração Own Financial 
  - OAuth 2.0 (token cache 4min)
  - API OPPWA E-commerce (timeout 60s)
  - API QA com problemas de performance (timeout >60s)
- `parametros_wallclub/` - Parâmetros financeiros (3.840 configs)

**Comunicação:**
- ⚠️ **NÃO importa** `apps.cliente` diretamente
- ✅ Usa **API Interna HTTP** para acessar dados de clientes (container APIs)
- ✅ Endpoints: `/api/internal/cliente/*` (autenticados via OAuth)

**Settings:** `wallclub.settings.pos`
**URLs:** `wallclub.urls_pos`
**Deploy:** Raro (sistema crítico)

### Container 3: APIs Mobile (wallclub-apis)

**Porta:** 8007 (interna)
**Recursos:** 4 workers, 1GB RAM, 1.0 CPU

**Módulos:**
- `apps/cliente/` - JWT Customizado (18 cenários testados)
- `apps/conta_digital/` - Saldo, Cashback, Autorizações
- `apps/ofertas/` - Sistema de Ofertas Push
- `apps/transacoes/` - Transações mobile
- `apps/oauth/` - OAuth 2.0 Token Endpoint (centralizado)
- `checkout/` - Checkout Web + 2FA WhatsApp + Link de Pagamento
  - ✅ `CheckoutTransaction` criada pelo portal de vendas (status PENDENTE)
  - ✅ `LinkPagamentoTransactionService` - Gerencia transações de link
  - ✅ Validação OTP integrada com processamento de pagamento

**API Interna (comunicação entre containers):**
- `/api/internal/cliente/` - 6 endpoints para consulta de clientes
  - `consultar_por_cpf/` - Buscar cliente por CPF e canal
  - `cadastrar/` - Cadastrar novo cliente (com bureau)
  - `obter_cliente_id/` - Obter ID do cliente
  - `atualizar_celular/` - Atualizar celular
  - `obter_dados_cliente/` - Dados completos
  - `verificar_cadastro/` - Verificar se existe cadastro

**Settings:** `wallclub.settings.apis`
**URLs:** `wallclub.urls_apis`
**Deploy:** Médio (features app mobile)

### Container 2: Redis (wallclub-redis)

**Porta:** 6379

**Databases:**
- DB 0: Django (tokens OAuth, sessões, rate limiting)
- DB 1: Risk Engine (MaxMind scores, regras)

**TTLs:**
- OAuth: 1h
- MaxMind: 1h
- Rate limit: 15min/1h/24h
- OTP: 5min

### Container 4: Risk Engine (wallclub-riskengine)

**Porta:** 8008 (interna)
**Acesso:** Interno (chamado por outros containers), 512MB RAM, 0.5 CPU

**Funcionalidades:**
- Análise risco <200ms
- 9 regras antifraude (5 básicas + 4 autenticação)
- MaxMind minFraud (score 0-100, cache 1h)
- Sistema Segurança Multi-Portal (6 detectores)
- Portal revisão manual
- Blacklist/Whitelist automática

**Thresholds:**
- 0-59: APROVADO ✅
- 60-79: REVISAR ⚠️
- 80-100: REPROVADO 🚫

**Integrações:**
- ✅ POSP2 (intercepta antes Pinbank)
- ✅ Checkout Web (7 campos antifraude)
- ✅ Portal Admin (dashboard + revisão)
- ✅ Sistema Segurança (validate-login, bloqueios)

### Container 4: Celery Worker

**Recursos:** 4 workers, 256MB RAM

**Tasks:**
- detectar_atividades_suspeitas (5min)
- bloquear_automatico_critico (10min)
- Exportações grandes
- Notificações massa

### Container 5: Celery Beat

**Recursos:** 128MB RAM

**Schedule:**
- 5min: detectar_atividades_suspeitas
- 10min: bloquear_automatico_critico

### Container 6: Flower (wallclub-flower)

**Porta:** 5555 (interna)
**Acesso:** flower.wallclub.com.br (via Nginx)
**Recursos:** 256MB RAM, 0.25 CPU

**Funcionalidades:**
- Monitoramento Celery em tempo real
- Dashboard de workers (portais + apis)
- Histórico de tasks (sucesso/falha)
- Estatísticas de performance
- Controle de workers (restart, shutdown)
- Visualização de filas Redis
- Gráficos de throughput

**Autenticação:**
- HTTP Basic Auth
- Credenciais via AWS Secrets Manager
- Variáveis: `FLOWER_USER` e `FLOWER_PASSWD`

**Métricas Disponíveis:**
- Tasks ativas/pendentes/concluídas
- Tempo médio de execução
- Taxa de sucesso/falha
- Workers online/offline
- Uso de memória por worker

### Deploy Unificado

```bash
cd /var/www/wallclub_django

# Todos containers
docker-compose up -d --build

# Seletivo (mantém Redis)
docker-compose up -d --build --no-deps web riskengine

# Status
docker-compose ps

# Logs
docker-compose logs -f web
docker-compose logs -f riskengine
```

**Repositório:**
- Monorepo: `/var/www/wallclub`
  - Django: `services/django/`
  - Risk Engine: `services/riskengine/`
  - Core: `services/core/` (package compartilhado)

---

### Arquitetura Futura: 5 Containers Independentes (Fase 6D)

**Status:** Código pronto, aguardando extração do CORE

```
┌────────────────────────────────┐
│  NGINX Gateway (80/443)        │
│  Roteamento por path           │
└───────────┬────────────────────┘
            │
    ┌───────┼────────┬────────┬────────┐
    │       │        │        │        │
┌───▼──┐ ┌─▼───┐ ┌──▼──┐ ┌───▼──┐ ┌──▼──┐
│APP1  │ │APP2 │ │APP3 │ │APP4  │ │Redis│
│8001  │ │8002 │ │8003 │ │8004  │ │6379 │
│Portal│ │POS  │ │APIs │ │Risk  │ │     │
└──────┘ └─────┘ └─────┘ └──────┘ └─────┘
   │        │       │        │
   └────────┴───────┴────────┘
            │
    ┌───────┴───────┐
    │               │
┌───▼──────┐ ┌─────▼────┐
│wallclub  │ │  MySQL   │
│  -core   │ │ (shared) │
│ (package)│ │          │
└──────────┘ └──────────┘
```

**APP1 - wallclub-portais (8001):**
- Portais: admin, lojista, vendas, corporativo
- Controle de acesso
- Sistema bancário
- **Deploy:** Frequente
- **Auth:** Sessão Django

**APP2 - wallclub-pos (8002):**
- POSP2 (terminais)
- Pinbank (cargas)
- Parâmetros financeiros
- **Deploy:** Raro (crítico)
- **Auth:** OAuth 2.0

**APP3 - wallclub-apis (8003):**
- APIs Mobile (JWT)
- Checkout Web
- Cliente/Conta Digital
- Ofertas
- **Deploy:** Médio
- **Auth:** JWT customizado

**APP4 - wallclub-riskengine (8004):** ✅ Já existe
- Antifraude
- MaxMind
- Portal revisão

**CORE - wallclub-core (package):**
- comum/* (49 arquivos)
- Compartilhado entre todos
- Instalado via pip

**Comunicação Inter-Containers:**
- 26 APIs REST internas (OAuth 2.0)
- SQL direto (read-only queries)
- Lazy imports (apps.get_model)

---

## ✅ STATUS DA MIGRAÇÃO

### Marcos Históricos

**Fase 0: Preparação (Ago-Set/2025)**
- ✅ 3.840 parâmetros migrados
- ✅ 100% validação Django vs PHP (168/168)
- ✅ Calculadoras com fidelidade total

**Fase 1: APIs (Set/2025)**
- ✅ APIs Mobile + JWT
- ✅ OAuth 2.0 completo
- ✅ Deploy AWS (16/10)

**Fase 2: Antifraude (Out/2025)**
- ✅ Risk Engine (16/10)
- ✅ POSP2 integrado
- ✅ Checkout integrado (22/10)
- ✅ MaxMind + fallback

**Fase 3: Refatoração (Out/2025)**
- ✅ 22 services criados
- ✅ 25 queries eliminadas
- ✅ Sistema bancário refatorado

**Fase 4: Autenticação Enterprise (Out/2025)**
- ✅ JWT Customizado (28/10) - 18 cenários
- ✅ 2FA Checkout (18/10)
- ✅ Device Management (18/10)
- ✅ Segurança Multi-Portal (23/10)
- ✅ Login Simplificado Fintech (25/10)
- ✅ **Correção crítica tokens revogados (26/10)**

**Fase 5: Portal Vendas (Out/2025)**
- ✅ Unificação portais (24/10)
- ✅ Checkout + recorrências
- ⏳ Celery Beat (tasks prontas)

**Fase 6: Separação em Múltiplos Containers (Out-Nov/2025)**
- ✅ **6A - CORE Limpo (30/10):** 0 imports de apps, pronto para extração
- ✅ **6B - Dependências Cruzadas (01/11):** 103 imports resolvidos
  - 26 APIs REST internas (OAuth 2.0)
  - 17 arquivos com lazy imports
  - 2 classes SQL direto (9 métodos)
  - Fix crítico RPR (dict vs getattr)
- ✅ **6C - Monorepo Unificado (02/11):** wallclub_core extraído + monorepo criado
  - Package wallclub_core (52 arquivos)
  - 113 arquivos migrados (108 Django + 5 Risk Engine)
  - Estrutura: wallclub/services/{django,riskengine,core}
  - Diretório comum/ removido
- ⏳ **6D - Separação Física:** 5 containers independentes

### Taxa de Sucesso

- Cálculos Financeiros: **100%** (168/168)
- APIs Mobile: **100%** funcional
- Antifraude: **<200ms** latência
- Deploy: **Zero downtime**

**Detalhes completos:** Ver [Django README linhas 403-444](../2.%20README.md#status-da-migração)

---

## 🎯 FUNCIONALIDADES PRINCIPAIS

### 1. Sistema JWT Customizado ⭐

**Status:** 18 cenários testados (28/10/2025)

**Endpoints:**
- Cadastro: iniciar, validar_otp, finalizar
- Login: rate limiting 5/15min, 10/1h, 20/24h
- Reset senha: solicitar, validar, trocar
- 2FA: verificar, solicitar, validar
- Dispositivos: listar, revogar
- Refresh: renovar access_token

**Tabelas:**
- cliente_jwt_tokens (auditoria completa)
- otp_autenticacao (códigos 5min)
- otp_dispositivo_confiavel (30 dias)
- cliente_autenticacao (tentativas)
- cliente_bloqueios (histórico)
- cliente_senhas_historico

**Correção Crítica 26/10:**
- Tokens revogados continuavam funcionando
- Agora: validação obrigatória is_active + revoked_at
- Novo login revoga tokens anteriores

**Arquivos:** `apps/cliente/jwt_cliente.py`, `views_2fa_login.py`, `services_2fa_login.py`

**Documentação:** [TESTE_CURL_USUARIO.md](../TESTE_CURL_USUARIO.md)

### 2. Sistema de Cashback Centralizado ⭐

**Status:** Implementado (02/12/2025)

**Tipos:**
- **Cashback Wall:** Concedido pela WallClub (custo WallClub)
- **Cashback Loja:** Concedido pela loja (custo loja)

**Tabelas:**
- `cashback_regra_loja` - Regras customizadas por loja
- `cashback_uso` - Histórico unificado (Wall + Loja)
- `transactiondata_own` - Campos renomeados (desconto_wall, cashback_creditado_wall, cashback_creditado_loja)

**Fluxo:**
1. Simulação V2: `/api/v1/posp2/simula_parcelas_v2/` retorna cashback Wall + Loja
2. Transação: POS envia valores para `/api/v1/posp2/trdata_own/`
3. Aplicação: `CashbackService` credita na conta digital (RETIDO → LIBERADO → EXPIRADO)
4. Jobs Celery: Liberação (30 dias) e expiração (90 dias)

**Portal Lojista:**
- CRUD regras cashback (`/cashback/`)
- Configuração: valor, condições, limites, orçamento
- Relatórios de uso

### 3. Sistema de Ofertas Push

**Segmentação:**
- todos_canal (todos ativos)
- grupo_customizado (VIP, Novos, etc)

**Push:**
- Firebase: `{"tipo": "oferta", "oferta_id": "X"}`
- APN: fallback produção→sandbox
- Templates dinâmicos (BD)

**APIs:**
- `/ofertas/lista_ofertas/` - Com segmentação
- `/ofertas/detalhes_oferta/` - Valida acesso

**Portais:**
- Admin: CRUD + grupos + disparo
- Lojista: CRUD filtrado por canal

### 3. Autorização Uso Saldo (Wall Cashback)

**Fluxo:**
1. POS consulta saldo (CPF + senha) → auth_token 15min
2. POS solicita autorização → push app cliente
3. Cliente aprova/nega no app (180s)
4. POS verifica status (polling)
5. Débito automático após INSERT transactiondata

**Movimentações:**
- CRÉDITO Cashback: cashback_bloqueado (30 dias)
- DÉBITO Uso Saldo: cashback_disponivel (lock pessimista)

**Formato:** `{"sucesso": bool, "mensagem": str}`

**Arquivos:** `posp2/services_conta_digital.py`, `apps/cliente/views_saldo.py`

### 4. Cargas Pinbank

**Extrato POS:**
- Periodicidades: 30min, 72h, 60d, ano
- Command: `carga_extrato_pos`
- Lock: execução única

**Base Gestão:**
- 130+ variáveis (var0-var130)
- Streaming: 100 registros/lote
- Command: `carga_base_gestao`
- Service: CalculadoraBaseGestao (1178 linhas)

**Ajustes Manuais:**
- Inserções faltantes: transactiondata
- Remoções duplicatas: baseTransacoesGestao
- SQL direto com auditoria

### 5. Sistema Checkout

**Web (Link Pagamento):**
- Token único 30min
- Antifraude integrado
- 2FA WhatsApp (OTP 6 dígitos)
- Limite progressivo R$100→200→500

**Portal Vendas:**
- CRUD clientes
- Tokenização cartões
- 3 formas pagamento
- Pulldown unificado

**Recorrências:**
- Models: RecorrenciaAgendada
- Link tokenização separado
- Celery tasks prontas
- ⏳ Ativação Celery Beat

**Antifraude (7 campos novos):**
- score_risco (0-100)
- decisao_antifraude
- motivo_bloqueio
- antifraude_response
- revisado_por/em
- observacao_revisao

**Status novos:**
- BLOQUEADA_ANTIFRAUDE
- PENDENTE_REVISAO

### 6. Parâmetros Financeiros

**Estrutura:**
- 3.840 configurações ativas
- 133 planos (PIX, DÉBITO, CRÉDITO, PARCELADO)
- Granularidade: (loja, plano, vigência)

**CalculadoraDesconto:**
- 100% validado (168/168 vs PHP)
- Formas: PIX, DÉBITO, À VISTA, PARCELADO 2-12x
- Integração: ParametrosService

**Mapeamento:**
- 1-30: parametro_loja_X
- 31-36: parametro_uptal_X
- 37-40: parametro_wall_X

---

## 🛡️ RISK ENGINE

### Visão Geral

**Container:** wallclub-riskengine:8004
**Latência:** <200ms média

**Score:**
```
MaxMind (0-100) + Regras (+pontos) = Score Final
0-59: APROVADO ✅
60-79: REVISAR ⚠️
80-100: REPROVADO 🚫
```

### 5 Regras Antifraude

| Nome | Pontos | Lógica |
|------|--------|--------|
| Velocidade | +80 | >3 tx em 10min |
| Valor | +70 | >média × 3 |
| Device | +50 | Fingerprint novo |
| Horário | +40 | 00h-05h |
| IP | +90 | >5 CPFs no IP/24h |

### Integrações

**POSP2:**
- Arquivo: `posp2/services_antifraude.py` (374 linhas)
- Intercepta antes do Pinbank (linha ~333)
- Dados: CPF, valor, modalidade, BIN, terminal

**Checkout Web:**
- Arquivo: `checkout/services_antifraude.py` (268 linhas)
- Intercepta linhas 117-183
- Dados: CPF, valor, cartão, IP, device_fingerprint
- Decisões: APROVADO/REPROVADO/REVISAR

**Portal Admin:**
- Dashboard: `/admin/antifraude/`
- Pendentes: `/admin/antifraude/pendentes/`
- Histórico: `/admin/antifraude/historico/`

### Segurança Multi-Portal (23/10)

**Middleware:**
- Valida IP/CPF antes login
- Fail-open (erro não bloqueia)
- Arquivo: `comum/middleware/security_validation.py`

**6 Detectores (Celery 5min):**
1. Login Múltiplo (3+ IPs)
2. Tentativas Falhas (5+ em 5min)
3. IP Novo
4. Horário Suspeito (02:00-05:00)
5. Velocidade Transação (10+ em 5min)
6. Localização Anômala (MaxMind)

**Telas:**
- Atividades Suspeitas: `/admin/seguranca/atividades/`
- Bloqueios: `/admin/seguranca/bloqueios/`

### APIs REST

**OAuth 2.0:**
```bash
curl -X POST http://localhost:8004/oauth/token/ \
  -d "grant_type=client_credentials" \
  -d "client_id=wallclub_django_internal" \
  -d "client_secret=..."
```

**Endpoints:**
- `POST /api/antifraude/analyze/` - Análise completa
- `GET /api/antifraude/decision/<id>/` - Consulta decisão
- `POST /api/antifraude/validate-3ds/` - Valida 3DS
- `GET /api/antifraude/health/` - Health check
- `POST /api/antifraude/validate-login/` - Valida IP/CPF
- `GET /api/antifraude/suspicious/` - Atividades suspeitas
- `POST /api/antifraude/block/` - Cria bloqueio
- `GET /api/antifraude/blocks/` - Lista bloqueios

**Detalhes completos:** [Risk Engine README](../../wallclub-riskengine/docs/README.md)

---

## 📁 ESTRUTURA DE DIRETÓRIOS

### Django Principal

```
wallclub_django/
├── apps/                       # APIs Mobile
│   ├── cliente/               # JWT Customizado (18 cenários)
│   │   ├── jwt_cliente.py
│   │   ├── views_2fa_login.py
│   │   ├── views_dispositivos.py
│   │   └── views_senha.py
│   ├── conta_digital/         # Conta digital + cashback
│   └── ofertas/               # Sistema ofertas push
├── parametros_wallclub/        # Sistema parâmetros (3.840)
│   ├── models.py
│   └── services.py            # CalculadoraDesconto
├── posp2/                      # Terminal POS (OAuth)
│   ├── models.py              # TransactionData, TransactionDataOwn
│   ├── services_transacao.py  # TRDataService (Pinbank)
│   ├── services_transacao_own.py # TRDataOwnService (Own) ✅ NOVO
│   └── services_conta_digital.py # Autorização saldo
├── pinbank/cargas_pinbank/     # Cargas automáticas Pinbank
│   ├── services.py            # Extrato POS
│   └── services_ajustes_manuais.py
├── adquirente_own/             # Integração Own Financial ✅ NOVO
│   ├── services.py            # OwnService (OAuth 2.0)
│   ├── services_transacoes_pagamento.py # E-commerce OPPWA
│   ├── views_webhook.py       # Webhooks tempo real
│   └── cargas_own/            # Cargas automáticas Own
│       ├── models.py          # OwnExtratoTransacoes, Liquidacoes
│       ├── services_carga_transacoes.py
│       └── services_carga_liquidacoes.py
├── portais/                    # 4 Portais web
│   ├── controle_acesso/       # Multi-portal
│   ├── admin/                 # 45+ templates
│   ├── lojista/
│   └── vendas/                # Checkout + recorrências
├── checkout/                   # Checkout core
│   ├── models.py              # + 7 campos antifraude
│   ├── services_antifraude.py # 268 linhas
│   ├── link_pagamento_web/
│   └── link_recorrencia_web/
├── sistema_bancario/           # Camada serviços
│   └── services.py            # PagamentoService
└── comum/                      # Compartilhado
    ├── oauth/                 # OAuth 2.0
    ├── integracoes/           # WhatsApp, SMS, Push
    ├── middleware/            # SecurityValidation
    ├── seguranca/             # 2FA, Devices
    └── estr_organizacional/   # Canal, Loja, Regional
```

### Risk Engine

```
wallclub-riskengine/
├── antifraude/
│   ├── models.py              # TransacaoRisco, Regras
│   ├── services.py            # 5 regras antifraude
│   ├── views_api.py           # REST APIs
│   ├── views_revisao.py       # Portal admin
│   ├── views_seguranca.py     # APIs segurança
│   ├── tasks.py               # 6 detectores Celery
│   └── notifications.py       # Email + Slack
├── comum/oauth/               # OAuth independente
├── docs/
│   ├── README.md             # Este documento
│   └── engine_antifraude.md  # Guia completo
└── scripts/
    ├── seed_regras_antifraude.py
    └── testar_maxmind_producao.py
```

---

## 🚀 DEPLOY

### Desenvolvimento Local

```bash
# Django
cd wallclub_django
docker-compose up --build

# Acesso
http://localhost:8005  # Portais (admin, vendas, lojista)
http://localhost:8007/api/v1/  # APIs Mobile
http://localhost:8006  # POS
```

### Produção (5 Containers)

**Servidor:** AWS EC2 ubuntu@ip-10-0-1-46
**Configuração:** AWS Secrets Manager + IAM Role
**Proxy:** Nginx + Gunicorn

**Comandos:**
```bash
cd /var/www/wallclub_django

# Deploy completo
docker-compose down
docker-compose up -d --build

# Deploy seletivo
docker-compose up -d --build --no-deps web riskengine

# Status
docker-compose ps

# Logs
docker logs wallclub-prod-release300 --tail 100
docker logs wallclub-riskengine --tail 100
```

**Health Checks:**
```bash
# APIs Mobile
curl http://localhost:8007/api/v1/health/

# Risk Engine
curl http://localhost:8008/api/antifraude/health/
```

### Recursos por Container

| Container | CPU | RAM | Porta | Workers |
|-----------|-----|-----|-------|---------|
| Portais | 1.0 | 1GB | 8005 | 3 |
| POS | 0.5 | 512MB | 8006 | 2 |
| APIs | 1.0 | 1GB | 8007 | 4 |
| Risk Engine | 0.5 | 512MB | 8008 | 3 |
| Redis | 0.25 | 256MB | 6379 | - |
| Celery Worker | 0.5 | 512MB | - | 4 |
| Celery Beat | 0.25 | 128MB | - | - |

---

## 🔗 INTEGRAÇÕES EXTERNAS

### Pinbank

**Transações:**
- Cartão direto: EfetuarTransacaoEncrypted
- Cartão tokenizado: EfetuarTransacaoCartaoIdEncrypted
- Tokenização: IncluirCartaoEncrypted

**Cargas:**
- Extrato POS (30min, 72h, 60d, ano)
- Base Gestão (130+ variáveis)
- Credenciadora + Checkout

**Arquivos:** `pinbank/services_transacoes_pagamento.py`, `pinbank/cargas_pinbank/services.py`

### MaxMind minFraud

**Cache:** 1h (Redis)
**Fallback:** Score neutro 50
**Timeout:** 3s
**Custo:** R$ 50-75/mês

**Arquivo:** `antifraude/services_maxmind.py`

### WhatsApp Business

**Templates dinâmicos:**
- 2fa_login_app (AUTHENTICATION)
- senha_acesso (AUTHENTICATION)
- baixar_app (UTILITY)

**Categorias:**
- AUTHENTICATION: sempre entrega
- UTILITY: funcional
- MARKETING: requer opt-in

**Arquivo:** `comum/integracoes/whatsapp_service.py`

### Firebase + APN

**Firebase:** Android push
**APN:** iOS (fallback produção→sandbox)
**Bundle ID:** Dinâmico da tabela canal

**Arquivos:** `comum/integracoes/firebase_service.py`, `comum/integracoes/apn_service.py`

### AWS Secrets Manager

**Secrets:**
- `wall/prod/db` - Credenciais BD + MaxMind
- OAuth clients separados (admin, pos, internal)

**Configuração:** IAM Role no EC2

---

## 📊 PADRÕES TÉCNICOS

### Banco de Dados

**Collation obrigatória:** utf8mb4_unicode_ci

```sql
-- Template CREATE
CREATE TABLE nome (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    campo VARCHAR(255) COLLATE utf8mb4_unicode_ci
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Converter existente
ALTER TABLE nome CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

**Timezone:** USE_TZ=False + TZ=America/Sao_Paulo

**Valores monetários:** SEMPRE Decimal (nunca float)

### APIs REST

**Autenticação:**
- Mobile: JWT customizado (Bearer token)
- POS: OAuth 2.0 client_credentials
- Checkout: OAuth 2.0 + sessão temporária

**Método:** SEMPRE POST (nunca GET/PUT/DELETE)

**Formato resposta:**
```json
{"sucesso": bool, "mensagem": str, ...}
```
NUNCA: `success`, `error`, `data`

### Logs

**Níveis:**
- DEBUG: validações OK, fluxo normal
- INFO: operações concluídas
- WARNING: validações negadas, anomalias
- ERROR: exceções críticas

**Categoria:** `comum.modulo` ou `apps.modulo`

### Nomenclatura

- Variáveis/funções: snake_case
- Classes: PascalCase
- Arquivos: snake_case.py
- Templates: snake_case.html

---

## 📚 DOCUMENTAÇÃO COMPLEMENTAR

### Documentos Principais

- **[Django README (1117 linhas)](../2.%20README.md)** - Sistema completo detalhado
- **[Risk Engine README (839 linhas)](../../wallclub-riskengine/docs/README.md)** - Antifraude completo
- **[DIRETRIZES (3428 linhas)](../1.%20DIRETRIZES.md)** - Padrões obrigatórios
- **[Risk Engine DIRETRIZES](../../wallclub-riskengine/docs/DIRETRIZES.md)** - Padrões antifraude

### Documentos Técnicos

- `docs/TESTE_CURL_USUARIO.md` - Testes JWT (18 cenários)
- `docs/engine_antifraude.md` - Motor antifraude
- `docs/mudancas_login_app.md` - Sistema autenticação
- `docs/fluxo_login_revalidacao.md` - Login simplificado
- `docs/4. sistema_checkout_completo.md` - Checkout detalhado
- `docs/0. deploy_simplificado.md` - Setup Docker

### Scripts

- `scripts/producao/` - Migração, validação, comparação Django vs PHP
- `scripts/seed_regras_antifraude.py` - Seed regras Risk Engine
- `scripts/testar_maxmind_producao.py` - Teste MaxMind
- `curls_teste/checkout.txt` - Exemplos API

---

## 🔄 FASE 6B - APIS REST INTERNAS (Em andamento)

### Status: 71% Completo (5/7 dias)

**Branch:** `multiplos_containers`
**Período:** 28/10 - 08/11/2025
**Objetivo:** Resolver dependências cruzadas via APIs REST

### Implementado:

#### 1. Middleware APIs Internas ✅
- Path `/api/internal/*` sem rate limiting
- Diferenciação automática interno vs externo
- Arquivo: `comum/middleware/security_middleware.py`

#### 2. APIs Conta Digital (5 endpoints) ✅
**Base:** `/api/internal/conta_digital/`

- `POST /consultar_saldo/` - Consulta saldo por CPF
- `POST /calcular_maximo/` - Calcula valor máximo permitido
- `POST /autorizar_uso/` - Cria autorização e bloqueia saldo
- `POST /debitar_saldo/` - Debita após transação aprovada
- `POST /estornar_saldo/` - Estorna transação cancelada

**Usado por:** posp2 (fluxo POS completo)

#### 3. APIs Checkout Recorrências (8 endpoints) ✅
**Base:** `/api/internal/checkout/`

- CRUD completo de recorrências
- Pausar/reativar/cobrar manualmente
- Usado por portais Admin/Lojista

#### 4. Tasks Celery Movidas ✅
- `portais/vendas/tasks_recorrencia.py` → `checkout/tasks_recorrencia.py`
- Lazy imports para evitar dependências circulares
- Logger correto: `checkout.recorrencia`

### Commits Realizados:
- `c6f98d5` - Middleware ajustado
- `7416f3a` - 5 endpoints conta-digital
- `b9fae11` - Refatorar posp2 (usar APIs)
- `62ca51e` - Mover tasks recorrência
- `05c0b39` - 8 endpoints checkout
- `9439f64` - Fix consultar_saldo
- `63f4f07` - Fix calcular_maximo
- `3ec67df` - Fix autorizar_uso
- `bd2091a` - URLs underscore
- `6d1f13f` - Base path underscore

### Pendente (Dia 6-7):
- 8 endpoints checkout clientes/links
- Testes end-to-end completos

### Arquitetura Atual:
```
APP (Monolito)
├── posp2/                    → Chama APIs via HTTP
│   └── services_conta_digital.py (requests.post)
├── apps/conta_digital/       → Prove APIs
│   ├── views_internal_api.py (5 endpoints)
│   └── urls_internal.py
├── checkout/                 → Prove APIs
│   ├── views_internal_api.py (8 endpoints)
│   ├── urls_internal.py
│   └── tasks_recorrencia.py (Celery)
└── comum/middleware/
    └── security_middleware.py (diferencia interno/externo)
```

**Próxima Fase 6C:** Extrair CORE em package compartilhado

---

## 📞 SUPORTE

**Responsável:** Jean Lessa + Claude AI
**Repositório Django:** `/var/www/wallclub_django`
**Repositório Risk Engine:** `/var/www/wallclub_django_risk_engine`
**Ambiente:** AWS EC2 + Docker + MySQL + Redis
**Status:** ✅ 100% operacional em produção

---

**Última atualização:** 14/11/2025

---

## 🌐 APIS INTERNAS - OVERVIEW

**Status:** Fase 6B concluída (01/11/2025) - Operacional em produção  
**Total:** 32 endpoints REST  
**Propósito:** Comunicação entre 4 containers Django independentes

**Containers:**
- wallclub-portais (Admin, Vendas, Lojista)
- wallclub-pos (Terminal POS)
- wallclub-apis (Mobile + Checkout)
- wallclub-riskengine (Antifraude)

### Características

**Autenticação:** ❌ Sem autenticação (isolamento de rede Docker)  
**Rate Limiting:** Desabilitado (containers confiáveis)  
**Timeout:** 30s (padrão), configurável por endpoint  
**Base URL:** `http://wallclub-apis:8007/api/internal/` (rede Docker interna)  
**Segurança:** Rede interna Docker (não exposta publicamente)

**Helper Service:** `wallclub_core.integracoes.api_interna_service.APIInternaService`

### Distribuição

| Módulo | Endpoints | Finalidade |
|---------|-----------|------------|
| **Cliente** ⭐ | 6 | Consulta, cadastro, atualização |
| Conta Digital | 5 | Saldo, autorização, débito |
| Checkout Recorrências | 8 | CRUD + controle recorrências |
| Ofertas | 6 | CRUD ofertas + grupos |
| Parâmetros | 7 | Configurações lojas |

### Exemplo de Uso

```python
from wallclub_core.integracoes.api_interna_service import APIInternaService

# Container POS consultando cliente no container APIs
response = APIInternaService.chamar_api_interna(
    metodo='POST',
    endpoint='/api/internal/cliente/consultar_por_cpf/',
    payload={'cpf': '12345678900', 'canal_id': 1},
    contexto='apis',
    timeout=10
)

if response.get('sucesso'):
    cliente = response['cliente']
    print(f"Cliente: {cliente['nome']}")
```

---

## 👤 CLIENTE APIS (Fase 6B)

**Base:** `/api/internal/cliente/`  
**Arquivo:** `apps/cliente/views_api_interna.py`  
**Container:** wallclub-apis  
**Criado:** 07/11/2025

### Endpoints Disponíveis

1. `POST /consultar_por_cpf/` - Buscar cliente por CPF e canal_id
2. `POST /cadastrar/` - Cadastrar novo cliente (inclui consulta bureau)
3. `POST /obter_cliente_id/` - Obter ID do cliente
4. `POST /atualizar_celular/` - Atualizar número de celular
5. `POST /obter_dados_cliente/` - Obter dados completos do cliente
6. `POST /verificar_cadastro/` - Verificar se cliente existe no canal

**Autenticação:** ❌ Sem autenticação (rede interna)  
**Usado por:** POSP2 (Terminal POS)

### 1. Consultar por CPF

```bash
POST /api/internal/cliente/consultar_por_cpf/
Authorization: Bearer {oauth_token}
Content-Type: application/json

{
  "cpf": "12345678900",
  "canal_id": 1
}
```

**Resposta:**
```json
{
  "sucesso": true,
  "cliente": {
    "id": 123,
    "cpf": "12345678900",
    "nome": "João Silva",
    "celular": "11999999999",
    "email": "joao@example.com",
    "firebase_token": "abc123...",
    "is_active": true,
    "canal_id": 1
  }
}
```

### 2. Cadastrar Cliente

```bash
POST /api/internal/cliente/cadastrar/
Authorization: Bearer {oauth_token}

{
  "cpf": "12345678900",
  "celular": "11999999999",
  "canal_id": 1
}
```

**Observações:**
- Realiza consulta ao bureau automaticamente
- Retorna erro se CPF bloqueado
- Gera senha temporária e envia WhatsApp

### 3. Verificar Cadastro

```bash
POST /api/internal/cliente/verificar_cadastro/

{
  "cpf": "12345678900",
  "canal_id": 1
}
```

**Resposta:**
```json
{
  "sucesso": true,
  "tem_cadastro": true
}
```

**Caso de Uso:** Container POS precisa verificar se cliente existe antes de processar transação.

---

## 💳 CONTA DIGITAL APIS (Fase 6B)

**Base:** `/api/internal/conta-digital/`  
**Arquivo:** `apps/conta_digital/views_internal_api.py`  
**Container:** wallclub-apis

### Endpoints Disponíveis

1. `POST /consultar-saldo/` - Consulta saldo disponível + bloqueado
2. `POST /autorizar-uso/` - Autorização uso saldo (push app cliente)
3. `POST /debitar-saldo/` - Débito com lock pessimista
4. `POST /estornar-saldo/` - Estorno de débito
5. `POST /calcular-maximo/` - Cálculo valor máximo disponível

**Autenticação:** OAuth 2.0 interno  
**Usado por:** POSP2 (Terminal POS)

---

## 🔁 CHECKOUT RECORRENCIAS APIS (Fase 5)

**Base:** `/api/internal/checkout/recorrencias/`  
**Arquivo:** `checkout/views_internal_api.py`  
**Container:** wallclub-apis

### Endpoints Disponíveis

1. `GET /` - Listar recorrências (filtros: status, cliente, loja)
2. `POST /criar/` - Criar nova recorrência agendada
3. `GET /{id}/` - Obter detalhes de recorrência
4. `POST /{id}/pausar/` - Pausar cobranças (status=pausado)
5. `POST /{id}/reativar/` - Reativar cobranças (status=ativo)
6. `POST /{id}/cobrar/` - Executar cobrança manual
7. `PUT /{id}/atualizar/` - Atualizar dados (valor, dia_cobranca)
8. `DELETE /{id}/deletar/` - Cancelar recorrência (status=cancelado)

**Autenticação:** OAuth 2.0 interno  
**Usado por:** Portal Vendas, Celery Beat (cobranças automáticas)  
**Celery Task:** `processar_recorrencias_do_dia()` - executa diariamente às 08:00

---

## 🎁 OFERTAS APIS (Fase 3 + 6B)

**Base:** `/api/internal/ofertas/`  
**Arquivo:** `apps/ofertas/views_internal_api.py`  
**Container:** wallclub-apis

### Endpoints Disponíveis

1. `POST /listar/` - Lista ofertas (filtros: canal, ativo, vigência)
2. `POST /criar/` - Cria nova oferta + upload imagem
3. `POST /obter/` - Obtém detalhes de oferta
4. `POST /atualizar/` - Atualiza oferta existente
5. `POST /grupos/listar/` - Lista grupos de segmentação
6. `POST /grupos/criar/` - Cria novo grupo customizado

**Autenticação:** OAuth 2.0 interno  
**Usado por:** Portal Admin, Portal Lojista  
**Features:** Push notifications (Firebase + APN), segmentação dinâmica

---

## ⚙️ PARAMETROS APIS (Fase 0 + 6B)

**Base:** `/api/internal/parametros/`  
**Arquivo:** `parametros_wallclub/views_internal_api.py`  
**Container:** wallclub-pos

### Endpoints Disponíveis

1. `POST /configuracoes/loja/` - Busca configurações financeiras por loja
2. `POST /configuracoes/contar/` - Conta total de configurações
3. `POST /configuracoes/ultima/` - Obtém última configuração ativa
4. `POST /loja/modalidades/` - Lista modalidades disponíveis (PIX, DÉBITO, etc)
5. `POST /planos/` - Lista planos de parcelamento
6. `GET /importacoes/` - Lista importações de parâmetros PHP→Django
7. `GET /importacoes/{id}/` - Detalhes de importação específica

**Autenticação:** OAuth 2.0 interno  
**Usado por:** POSP2, Portal Admin, Portal Lojista  
**Total:** 3.840 configurações validadas 100% vs PHP

---

## 💳 PINBANK (Gateway de Pagamentos)

### Visão Geral

**Gateway de pagamentos** para transações cartão crédito/débito, tokenização e cargas automáticas.

**Ambiente:** Produção  
**Autenticação:** Basic Auth (credenciais AWS Secrets Manager)  
**Timeout:** 30s transações, 60s cargas  
**Container:** wallclub-pos (POSP2) + wallclub-apis (Checkout)

**Integrado com:**
- ✅ POSP2 (Terminal POS)
- ✅ Checkout Web (Link Pagamento + Recorrências)
- ✅ Portal Vendas
- ✅ Risk Engine (análise antes de processar)  

### APIs de Transação

#### 1. EfetuarTransacaoEncrypted

**Uso:** Pagamento com dados cartão direto (sem token)

**Endpoint:** `POST /PinPagSeguroController/EfetuarTransacaoEncrypted`

**Request:**
```json
{
  "CodigoCliente": 1234,
  "NumeroCartao": "5111111111111111",
  "NomeTitular": "JOSE SILVA",
  "MesValidade": "12",
  "AnoValidade": "28",
  "CVV": "123",
  "TipoTransacao": "CREDITO",
  "ValorTransacao": 110.50,
  "NumeroParcelas": 1,
  "UrlRetorno": "https://wcadmin.wallclub.com.br/callback/",
  "terminal": "12345678"
}
```

**Response:**
```json
{
  "Status": true,
  "NSU": "148456789",
  "CodigoAutorizacao": "ABC123",
  "Mensagem": "Transacao aprovada"
}
```

**Arquivo:** `pinbank/services_transacoes_pagamento.py`

#### 2. EfetuarTransacaoCartaoIdEncrypted

**Uso:** Pagamento com cartão tokenizado

**Diferenças:**
- Usa `CartaoId` em vez de dados completos
- Mais seguro (PCI-DSS compliant)
- Mais rápido (sem digitação)

**Request:**
```json
{
  "CodigoCliente": 1234,
  "CartaoId": "550e8400-e29b-41d4-a716-446655440000",
  "CVV": "123",
  "TipoTransacao": "CREDITO",
  "ValorTransacao": 110.50,
  "NumeroParcelas": 1
}
```

**Arquivo:** `pinbank/services_transacoes_pagamento.py`

#### 3. CapturarTransacaoEncrypted (Fase 5)

**Uso:** Captura de transações pré-autorizadas (recorrências)

**Endpoint:** `POST /Transacoes/CapturarTransacaoEncrypted`  
**Data Implementação:** 03/11/2025

**Fluxo:**
1. Efetuar transação com `TransacaoPreAutorizada=true` (reserva valor)
2. Capturar transação com NSU (efetiva cobrança)

**Request:**
```json
{
  "CodigoCanal": 47,
  "CodigoCliente": 3510,
  "KeyLoja": "11384322623341877660",
  "Valor": 1000,
  "NsuOperacao": "136586937"
}
```

**Response:**
```json
{
  "ResultCode": 0,
  "Message": "Success",
  "Data": {
    "CodigoAutorizacaoCaptura": "343163"
  }
}
```

**Arquivo:** `pinbank/services_transacoes_pagamento.py` (método `capturar_transacao`)  
**Usado por:** Celery task `processar_recorrencias_do_dia()`

#### 4. CancelarTransacaoEncrypted

**Uso:** Estorno de transações (pré-autorizadas ou normais)

**Endpoint:** `POST /Transacoes/CancelarTransacaoEncrypted`

**Request:**
```json
{
  "CodigoCanal": 47,
  "CodigoCliente": 3510,
  "KeyLoja": "11384322623341877660",
  "Valor": 500,
  "NsuOperacao": "136586940"
}
```

**Response:**
```json
{
  "ResultCode": 0,
  "Message": "Success",
  "Data": {
    "CodigoAutorizacaoCancelamento": "775169"
  }
}
```

**Arquivo:** `pinbank/services_transacoes_pagamento.py` (método `cancelar_transacao`)

#### 5. IncluirCartaoEncrypted

**Uso:** Tokenização de cartões para pagamentos futuros

**Request:**
```json
{
  "CodigoCliente": 1234,
  "CPF": "12345678900",
  "NumeroCartao": "5111111111111111",
  "NomeTitular": "JOSE SILVA",
  "MesValidade": "12",
  "AnoValidade": "28",
  "TipoCartao": "CREDITO"
}
```

**Response:**
```json
{
  "Status": true,
  "CartaoId": "550e8400-e29b-41d4-a716-446655440000",
  "UltimosDigitos": "1111",
  "Bandeira": "MASTERCARD"
}
```

**Arquivo:** `checkout/link_pagamento_web/services.py`, `portais/vendas/services_checkout.py`

### Cargas Automáticas (Fase 0 + 3)

#### 1. Extrato POS

**Periodicidades:**
- **30min:** Últimas 30 minutos (cron)
- **72h:** Últimas 72 horas (manual)
- **60d:** Últimos 60 dias (manual)
- **ano:** Ano corrente (manual)

**Command:** `python manage.py carga_extrato_pos`  
**Container:** wallclub-pos

**Tabelas:**
- `pinbank_extrato_pos` (staging)
- `transactiondata` (transações finais)

**Lock:** Impede execução paralela

**Erro:** `baseTransacoesGestaoErroCarga`

**Arquivo:** `pinbank/cargas_pinbank/services.py` (CargaExtratoPOSService)

#### 2. Base Gestão

**Variáveis:** 130+ (var0-var130)  
**Streaming:** 100 registros/lote (otimização memória)  
**Command:** `python manage.py carga_base_gestao`  
**Tabela:** `baseTransacoesGestao`  
**Container:** wallclub-pos

**Calculadora:** Compartilhada com Credenciadora (1178 linhas)  
**Arquivo:** `parametros_wallclub/calculadora_base_gestao.py`

**Refatoração (21/11/2025):**
- ✅ Parâmetro `tabela` obrigatório (suporta Pinbank e Own)
- ✅ Busca de loja: NSU (Pinbank) ou CNPJ (Own)
- ✅ Busca de canal: NSU (Pinbank) ou CNPJ (Own)

**Status:**
- 85 variáveis implementadas
- 46 variáveis faltantes documentadas (var93-130)

**Arquivo:** `parametros_wallclub/calculadora_base_gestao.py` (compartilhado)

#### 3. Carga Credenciadora

**Fonte:** Arquivo credenciadora

**Normalização:** 
- `tipo_operacao` padronizado
- `codigoCliente` camelCase
- `info_loja`/`info_canal` montados localmente

**Command:** `python manage.py carga_credenciadora`

**Bug corrigido (25/10):** Último lote <100 registros

**Arquivo:** `pinbank/cargas_pinbank/services_carga_credenciadora.py`

#### 4. Celery Beat - Agendamento Automático

**Tasks Agendadas:**
- `carga-extrato-pos` - 5x/dia (05:13, 09:13, 13:13, 18:13, 22:13)
- `cargas-completas-pinbank` - De hora em hora (xx:05, 5h-23h)
- `migrar-financeiro-pagamentos` - De hora em hora (xx:15, 24h)
- `expirar-autorizacoes-saldo` - Diariamente às 01:00

**Script de Cargas Completas:**
Executa sequencialmente via `executar_cargas_completas.py`:
1. Carga extrato POS (80min)
2. Carga base gestão (--limite=10000)
3. Carga credenciadora
4. Ajustes manuais base

**Arquivo:** `wallclub/celery.py`  
**Documentação:** `docs/CELERY_SCHEDULE.md`

### Ajustes Manuais

**Service:** `AjustesManuaisService`

**Operações:**
- Inserções faltantes: `transactiondata` via cruzamento
- Remoções duplicatas: `baseTransacoesGestao` sem `idFilaExtrato`

**Método:** Queries SQL diretas com auditoria

**Arquivo:** `pinbank/cargas_pinbank/services_ajustes_manuais.py`

### Tratamento de Erros

**Timeout:**
```python
try:
    response = requests.post(url, json=payload, timeout=30)
except requests.Timeout:
    return {'sucesso': False, 'mensagem': 'Timeout Pinbank'}
```

**Respostas Inválidas:**
```python
if not response_data.get('Status'):
    mensagem = response_data.get('Mensagem', 'Erro desconhecido')
    return {'sucesso': False, 'mensagem': mensagem}
```

---

## 🌍 MAXMIND MINFRAUD (Fase 2)

### Visão Geral

**Serviço:** Análise de risco score 0-100  
**Status:** Operacional desde 17/10/2025  
**Container:** wallclub-riskengine

**Cache:** Redis 1h (chave: `maxmind:{cpf}:{valor}:{ip}`)  
**Timeout:** 3s  
**Fallback:** Score neutro 50 (fail-safe)  
**Custo:** R$ 70-120/mês (validado em produção)

**Hit Rate Cache:** >90% (reduz 90% das chamadas API)

### Configuração

**Credenciais:** AWS Secrets Manager (`wall/prod/db`)  
**Migração:** 17/10/2025 - Removido do .env

```json
{
  "MAXMIND_ACCOUNT_ID": "123456",
  "MAXMIND_LICENSE_KEY": "abc123..."
}
```

**Validação Produção:**
```bash
docker exec wallclub-riskengine python scripts/testar_maxmind_producao.py
# Score: 1/100, fonte: maxmind, tempo: 92ms ✅
```

**Settings:**
```python
MAXMIND_ACCOUNT_ID = secrets.get('MAXMIND_ACCOUNT_ID')
MAXMIND_LICENSE_KEY = secrets.get('MAXMIND_LICENSE_KEY')
```

### Uso

**Arquivo:** `antifraude/services_maxmind.py` (Risk Engine)

**Método:**
```python
from antifraude.services_maxmind import MaxMindService

score = MaxMindService.get_score(
    cpf='12345678900',
    ip='192.168.1.100',
    valor=150.00,
    email='cliente@email.com'
)
# score = 0-100 (ou 50 se falha)
```

### Cache Redis

**TTL:** 3600s (1 hora)

**Reduz:** 90% das chamadas API

**Exemplo:**
```python
cache_key = f"maxmind:{cpf}:{valor}:{ip}"
cached_score = redis.get(cache_key)

if cached_score:
    return int(cached_score)

# Chamar API MaxMind
score = api_call()
redis.setex(cache_key, 3600, score)
```

### Fallback Automático

**Score neutro 50 quando:**
- Credenciais não configuradas
- Timeout (>3s)
- Erro HTTP (4xx, 5xx)
- Exceção inesperada

**Princípio:** Sistema NUNCA bloqueia por falha técnica

**Log:**
```python
logger.warning(f"⚠️ MaxMind indisponível, usando score neutro 50")
```

### Teste em Produção

**Script:** `scripts/testar_maxmind_producao.py`

```bash
docker exec wallclub-riskengine python scripts/testar_maxmind_producao.py
```

**Valida:**
- Credenciais corretas
- Resposta API 200
- Score entre 0-100
- Cache funcionando

---

## 💬 WHATSAPP BUSINESS

### Visão Geral

**Plataforma:** Meta Business API

**Autenticação:** Bearer token (AWS Secrets)

**Templates:** Dinâmicos do banco (`templates_envio_msg`)

**Categorias:**
- AUTHENTICATION: sempre entrega
- UTILITY: funcional
- MARKETING: requer opt-in

### Templates Ativos

| Template | Categoria | Parâmetros | Uso |
|----------|-----------|------------|-----|
| 2fa_login_app | AUTHENTICATION | código | Login 2FA |
| senha_acesso | AUTHENTICATION | código | Reset senha |
| baixar_app | UTILITY | nome, link | Onboarding |
| autorizacao_saldo | UTILITY | valor, loja | Autorização cashback |

### Estrutura Template

**Banco de dados:**
```sql
CREATE TABLE templates_envio_msg (
  id BIGINT PRIMARY KEY,
  meio VARCHAR(50),  -- 'whatsapp'
  tipo VARCHAR(50),  -- 'authentication', 'utility'
  nome_template VARCHAR(100),
  template_id VARCHAR(100),
  parametros JSON,  -- ["{{1}}", "{{2}}"]
  corpo_template TEXT
);
```

### Envio de Mensagem

**Arquivo:** `comum/integracoes/whatsapp_service.py`

**Método:**
```python
from comum.integracoes.whatsapp_service import WhatsAppService

resultado = WhatsAppService.enviar_template(
    telefone='5511999887766',
    template_name='2fa_login_app',
    parametros=['123456']  # Código OTP
)

if resultado['sucesso']:
    message_id = resultado['message_id']
```

**Request API:**
```json
{
  "messaging_product": "whatsapp",
  "to": "5511999887766",
  "type": "template",
  "template": {
    "name": "2fa_login_app",
    "language": {
      "code": "pt_BR"
    },
    "components": [
      {
        "type": "body",
        "parameters": [
          {"type": "text", "text": "123456"}
        ]
      }
    ]
  }
}
```

### Tratamento de Erros

**Timeout:**
```python
try:
    response = requests.post(url, json=payload, timeout=10)
except requests.Timeout:
    logger.error("⏱️ Timeout WhatsApp")
    return {'sucesso': False, 'mensagem': 'Timeout'}
```

**Erro API:**
```python
if response.status_code != 200:
    error = response.json().get('error', {})
    logger.error(f"❌ WhatsApp error: {error}")
    return {'sucesso': False, 'mensagem': error.get('message')}
```

**Fail-safe:** OTP sempre retorna sucesso (não bloqueia fluxo)

---

## 📱 SMS

### Visão Geral

**Provedor:** Gateway SMS customizado

**Formato URL:**
```
/TELEFONE/MENSAGEM/SHORTCODE/ASSUNTO
```

**Encoding:** `quote(mensagem, safe=':/')`

### URL Encoding Correto (24/10/2025)

❌ **ERRADO:** Codifica tudo
```python
mensagem_encoded = quote(mensagem, safe='')
# Resultado: https:%2F%2Ftinyurl.com%2Fabc
```

✅ **CORRETO:** Preserva URLs
```python
mensagem_encoded = quote(mensagem, safe=':/')
# Resultado: https://tinyurl.com/abc
```

**Motivo:** URLs em mensagens SMS devem permanecer clicáveis

### Envio

**Arquivo:** `comum/integracoes/sms_service.py`

**Método:**
```python
from comum.integracoes.sms_service import SMSService

resultado = SMSService.enviar_sms(
    telefone='5511999887766',
    mensagem='Seu código é: 1234. Link: https://app.wallclub.com.br/auth',
    shortcode='WALLCLUB',
    assunto='Autenticacao'
)
```

**URL Final:**
```
https://api-sms.com/5511999887766/Seu%20c%C3%B3digo%20%C3%A9%3A%201234.%20Link%3A%20https://app.wallclub.com.br/auth/WALLCLUB/Autenticacao
```

### Rate Limiting

**Por telefone:**
- 3 SMS/5min
- 5 SMS/1h
- 10 SMS/24h

**Redis:**
```python
key = f"sms_rate:{telefone}"
count = redis.incr(key)
if count == 1:
    redis.expire(key, 300)  # 5min
```

---

## 🔔 FIREBASE CLOUD MESSAGING

### Visão Geral

**Plataforma:** Firebase (Android push)

**Autenticação:** Service Account JSON (AWS Secrets)

**Payload:**
```json
{
  "message": {
    "token": "device_token_here",
    "notification": {
      "title": "Título",
      "body": "Mensagem"
    },
    "data": {
      "tipo": "oferta",
      "oferta_id": "123"
    }
  }
}
```

### Configuração

**Service Account:** AWS Secrets Manager

```json
{
  "type": "service_account",
  "project_id": "wallclub-app",
  "private_key_id": "...",
  "private_key": "...",
  "client_email": "firebase-adminsdk@wallclub-app.iam.gserviceaccount.com"
}
```

### Envio

**Arquivo:** `comum/integracoes/firebase_service.py`

**Método:**
```python
from comum.integracoes.firebase_service import FirebaseService

resultado = FirebaseService.send_push(
    token='device_token',
    title='Nova oferta!',
    body='Desconto de 20% em todos produtos',
    custom_data={
        'tipo': 'oferta',
        'oferta_id': '123'
    }
)
```

### Custom Data

**Uso no app:**
```kotlin
// Android - Receber custom data
remoteMessage.data.forEach { (key, value) ->
    when(key) {
        "tipo" -> handleTipo(value)
        "oferta_id" -> openOferta(value)
    }
}
```

### Tratamento

**Token inválido:**
```python
if 'INVALID_ARGUMENT' in error_message:
    # Remover token do banco
    DispositivoConfiavel.objects.filter(
        push_token=token
    ).delete()
```

---

## 🍎 APPLE PUSH NOTIFICATIONS

### Visão Geral

**Plataforma:** APNs (iOS push)

**Autenticação:** Token JWT + Team ID + Key ID

**Certificados:** `.p8` file (AWS Secrets)

### Configuração

**Bundle IDs:** Dinâmicos da tabela `canal`

```sql
SELECT bundle_id FROM canal WHERE id = 1;
-- br.com.wallclub.app
```

**Settings:**
```python
APN_TEAM_ID = secrets.get('APN_TEAM_ID')
APN_KEY_ID = secrets.get('APN_KEY_ID')
APN_AUTH_KEY = secrets.get('APN_AUTH_KEY')  # .p8 content
```

### Fallback Automático (24/10/2025)

**Problema:** Certificado produção pode falhar

**Solução:** Tentar sandbox automaticamente

```python
try:
    # Tentar produção
    client = APNsClient(credentials, use_sandbox=False)
    client.send_notification(token, payload)
except Exception:
    # Fallback sandbox
    client = APNsClient(credentials, use_sandbox=True)
    client.send_notification(token, payload)
```

### Envio

**Arquivo:** `comum/integracoes/apn_service.py`

**Método:**
```python
from comum.integracoes.apn_service import APNService

resultado = APNService.send_push(
    token='device_token_hex',
    title='Nova oferta!',
    body='Desconto de 20% em todos produtos',
    badge=1,
    sound='default',
    custom_data={
        'tipo': 'oferta',
        'oferta_id': '123'
    },
    bundle_id='br.com.wallclub.app'
)
```

### Payload

**Estrutura:**
```json
{
  "aps": {
    "alert": {
      "title": "Nova oferta!",
      "body": "Desconto de 20%"
    },
    "badge": 1,
    "sound": "default",
    "category": "oferta"
  },
  "tipo": "oferta",
  "oferta_id": "123"
}
```

### Category Dinâmica (24/10/2025)

❌ **ERRADO:** Hardcode
```python
payload["aps"]["category"] = "AUTORIZACAO_SALDO"
```

✅ **CORRETO:** Dinâmico do template
```python
template = TemplateEnvioMsg.objects.get(nome='autorizacao_saldo')
payload["aps"]["category"] = template.tipo_push
```

---

## 🔐 AWS SECRETS MANAGER

### Visão Geral

**Serviço:** Armazenamento seguro de credenciais

**Autenticação:** IAM Role no EC2 (sem access keys)

**Região:** us-east-1

### Secrets Ativos

**1. wall/prod/db**
```json
{
  "DB_NAME": "wallclub",
  "DB_USER": "root",
  "DB_PASSWORD": "...",
  "DB_HOST": "mysql",
  "DB_PORT": "3306",
  "MAXMIND_ACCOUNT_ID": "123456",
  "MAXMIND_LICENSE_KEY": "..."
}
```

**2. wall/prod/oauth/admin**
```json
{
  "CLIENT_ID": "wallclub_admin_portal",
  "CLIENT_SECRET": "..."
}
```

**3. wall/prod/oauth/pos**
```json
{
  "CLIENT_ID": "wallclub_pos_terminal",
  "CLIENT_SECRET": "..."
}
```

**4. wall/prod/integrations**
```json
{
  "WHATSAPP_TOKEN": "...",
  "FIREBASE_SERVICE_ACCOUNT": {...},
  "APN_TEAM_ID": "...",
  "APN_KEY_ID": "...",
  "APN_AUTH_KEY": "..."
}
```

### Uso no Django

**Arquivo:** `wallclub/settings/base.py`

```python
import boto3
import json

def get_secret(secret_name):
    client = boto3.client('secretsmanager', region_name='us-east-1')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

# Database
db_secrets = get_secret('wall/prod/db')
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': db_secrets['DB_NAME'],
        'USER': db_secrets['DB_USER'],
        'PASSWORD': db_secrets['DB_PASSWORD'],
        'HOST': db_secrets['DB_HOST'],
        'PORT': db_secrets['DB_PORT'],
    }
}

# MaxMind
MAXMIND_ACCOUNT_ID = db_secrets.get('MAXMIND_ACCOUNT_ID')
MAXMIND_LICENSE_KEY = db_secrets.get('MAXMIND_LICENSE_KEY')
```

### IAM Role

**Policy:** `AWSSecretsManagerReadWrite`

**Attached to:** EC2 instance

**Benefício:** Sem credenciais hardcoded

---

## 🔧 TROUBLESHOOTING

### Pinbank

**Timeout frequente:**
```bash
# Verificar conectividade
curl -X POST https://api.pinbank.com.br/health -m 5

# Aumentar timeout
PINBANK_TIMEOUT=60  # Em settings
```

**NSU duplicado:**
```sql
-- Verificar duplicatas
SELECT nsu, COUNT(*) 
FROM transactiondata 
GROUP BY nsu 
HAVING COUNT(*) > 1;
```

### MaxMind

**Score sempre 50:**
```bash
# Testar credenciais
docker exec wallclub-riskengine python scripts/testar_maxmind_producao.py

# Verificar cache
docker exec wallclub-redis redis-cli
> KEYS maxmind:*
> GET maxmind:12345678900:100.00:192.168.1.1
```

**Custo alto:**
```bash
# Ver hit rate cache
docker exec wallclub-redis redis-cli INFO stats | grep keyspace_hits
```

### WhatsApp

**Template rejeitado:**
- Verificar categoria correta (AUTHENTICATION vs UTILITY)
- Templates MARKETING precisam opt-in prévio
- Parâmetros devem corresponder ao template

**Mensagem não entrega:**
```bash
# Verificar logs
docker logs wallclub-prod-release300 | grep whatsapp

# Status do número
curl -X GET "https://graph.facebook.com/v18.0/PHONE_NUMBER_ID" \
  -H "Authorization: Bearer TOKEN"
```

### Firebase

**Token inválido:**
```sql
-- Limpar tokens antigos
UPDATE otp_dispositivo_confiavel 
SET push_token = NULL 
WHERE last_used < NOW() - INTERVAL 90 DAY;
```

**Service account inválido:**
```bash
# Validar JSON
cat firebase_service_account.json | jq .

# Testar credenciais
python -c "import firebase_admin; firebase_admin.initialize_app()"
```

### APN

**Certificado produção falha:**
- Fallback sandbox automático ativo (24/10)
- Verificar bundle ID correto do canal
- Certificado `.p8` válido por 1 ano

**Token hex inválido:**
```python
# Token deve ser 64 caracteres hex
assert len(token) == 64
assert all(c in '0123456789abcdef' for c in token.lower())
```

---

## 📊 MONITORAMENTO

### Métricas Importantes

**Pinbank:**
- Taxa de sucesso transações: >95%
- Tempo médio resposta: <2s
- Cargas concluídas: 4/4 diárias

**MaxMind:**
- Hit rate cache: >90%
- Latência média: <300ms
- Fallback rate: <5%

**Push Notifications:**
- Taxa de entrega: >80%
- Tokens inválidos: <10%
- Tempo envio: <1s

### Logs Úteis

```bash
# Todas integrações
docker logs wallclub-prod-release300 | grep -E "pinbank|maxmind|whatsapp|firebase|apn"

# Erros específicos
docker logs wallclub-prod-release300 | grep ERROR | grep -i pinbank

# Rate de sucesso
docker logs wallclub-prod-release300 | grep "✅" | wc -l
```

---

---

## 🛡️ RISK ENGINE - AUTENTICAÇÃO CLIENTE

### Visão Geral

**Serviço:** Análise de comportamento de autenticação para score antifraude

**Score:** 0-50 pontos (somado ao score total)

**Endpoint:** Django WallClub (OAuth exclusivo Risk Engine)

**Timeout:** 2s

**Fallback:** Score 0 (não penaliza cliente em caso de erro)

**Data:** 30/10/2025

### Configuração

**Autenticação:** OAuth 2.0 exclusivo (`@require_oauth_riskengine`)

**Credenciais:** AWS Secrets Manager

```json
{
  "RISK_ENGINE_INTERNAL_CLIENT_ID": "wallclub_django_internal",
  "RISK_ENGINE_INTERNAL_CLIENT_SECRET": "..."
}
```

**URL Base:** `http://wallclub-portais:8005`

### Endpoint

**Método:** `GET /cliente/api/v1/autenticacao/analise/<cpf>/`

**Autenticação:** Bearer token OAuth 2.0

**Arquivo Django:** `apps/cliente/views_autenticacao_analise.py`

**Service:** `apps/cliente/services_autenticacao_analise.py`

**Arquivo Risk Engine:** `antifraude/services_cliente_auth.py`

### Request

```bash
curl -X GET "http://wallclub-portais:8005/cliente/api/v1/autenticacao/analise/12345678900/" \
  -H "Authorization: Bearer <oauth_token>"
```

### Response

**Sucesso (200):**
```json
{
  "cpf": "12345678900",
  "status_atual": {
    "conta_bloqueada": false,
    "tentativas_login_falhas": 2,
    "ultima_tentativa_falha": "2025-10-30T10:30:00"
  },
  "historico_24h": {
    "total_tentativas": 5,
    "tentativas_falhas": 2,
    "taxa_falha": 0.40,
    "ips_distintos": 2,
    "devices_distintos": 1
  },
  "dispositivos": {
    "total_conhecidos": 3,
    "confiaveis": 2,
    "novos_ultimos_7_dias": 1
  },
  "bloqueios_historico": {
    "total_30_dias": 0,
    "bloqueio_recente_7_dias": false,
    "ultimo_bloqueio": null
  },
  "flags_risco": {
    "conta_bloqueada": false,
    "bloqueio_recente": false,
    "multiplos_bloqueios": false,
    "alta_taxa_falha": true,
    "multiplas_tentativas_falhas": false,
    "multiplos_ips": false,
    "multiplos_devices": false,
    "todos_devices_novos": false,
    "sem_device_confiavel": false
  },
  "score_autenticacao": 15,
  "timestamp": "2025-10-30T10:45:00"
}
```

**Erro (404):**
```json
{
  "erro": "Cliente não encontrado",
  "cpf": "12345678900"
}
```

### Dados Retornados

#### Status Atual
- `conta_bloqueada`: Se cliente está bloqueado atualmente
- `tentativas_login_falhas`: Total de tentativas falhas registradas
- `ultima_tentativa_falha`: Timestamp da última falha

#### Histórico 24h
- `total_tentativas`: Total de tentativas de login
- `tentativas_falhas`: Tentativas que falharam
- `taxa_falha`: Percentual de falha (0.0 a 1.0)
- `ips_distintos`: Quantidade de IPs diferentes
- `devices_distintos`: Quantidade de dispositivos diferentes

#### Dispositivos
- `total_conhecidos`: Total de devices já usados
- `confiaveis`: Devices com 10+ logins bem-sucedidos
- `novos_ultimos_7_dias`: Devices cadastrados recentemente

#### Bloqueios Histórico
- `total_30_dias`: Bloqueios nos últimos 30 dias
- `bloqueio_recente_7_dias`: Teve bloqueio na última semana
- `ultimo_bloqueio`: Data do último bloqueio

### Flags de Risco (9 flags)

| Flag | Descrição | Pontuação |
|------|-----------|----------|
| `conta_bloqueada` | Conta atualmente bloqueada | +30 |
| `bloqueio_recente` | Bloqueio nos últimos 7 dias | +20 |
| `multiplos_bloqueios` | 2+ bloqueios em 30 dias | +15 |
| `alta_taxa_falha` | Taxa de falha ≥30% | +15 |
| `multiplas_tentativas_falhas` | 5+ falhas em 24h | +10 |
| `multiplos_ips` | 3+ IPs distintos em 24h | +10 |
| `multiplos_devices` | 2+ devices distintos em 24h | +10 |
| `todos_devices_novos` | Todos devices <7 dias | +10 |
| `sem_device_confiavel` | Nenhum device com 10+ logins | +5 |

### Score de Autenticação (0-50)

**Cálculo:** Soma dos pontos das flags ativadas (máximo 50)

**Exemplos:**

1. **Cliente Normal (Score 0):**
   - Sem bloqueios
   - Taxa falha <30%
   - Device confiável
   - Score: 0 pontos

2. **Cliente Suspeito (Score 25):**
   - Alta taxa falha: +15
   - Múltiplos IPs: +10
   - Score: 25 pontos

3. **Cliente Crítico (Score 50):**
   - Conta bloqueada: +30
   - Bloqueio recente: +20
   - Score: 50 pontos (máximo)

### Integração AnaliseRiscoService

**Arquivo:** `antifraude/services.py`

**Fluxo:**
```python
# 1. Consultar endpoint Django
score_auth = ClienteAutenticacaoService.obter_score_autenticacao(cpf)

# 2. Somar ao score total
score_total += score_auth  # 0-50 pontos

# 3. Aplicar regras de autenticação
if score_auth >= 30:
    regras_acionadas.append('Cliente com Bloqueio Recente')
```

**Configurações Centralizadas:**
```python
# Tabela: antifraude_configuracao
AUTH_MAX_TENTATIVAS_FALHAS_24H = 5
AUTH_TAXA_FALHA_SUSPEITA = 0.3
AUTH_DIAS_ULTIMO_BLOQUEIO = 7
AUTH_MAX_BLOQUEIOS_30_DIAS = 2
AUTH_MAX_IPS_DISTINTOS_24H = 3
AUTH_MAX_DEVICES_DISTINTOS_24H = 2
CONSULTA_AUTH_TIMEOUT_SEGUNDOS = 2
```

### 4 Regras Novas Criadas

**1. Dispositivo Novo - Alto Valor** (Peso 7)
```python
{
  "nome": "Dispositivo Novo - Alto Valor",
  "parametros": {
    "device_age_days": 7,
    "valor_minimo": 500.0
  },
  "peso": 7,
  "acao": "REVISAR"
}
```

**2. IP Novo + Histórico de Bloqueios** (Peso 8)
```python
{
  "nome": "IP Novo + Histórico de Bloqueios",
  "parametros": {
    "ip_age_days": 3,
    "bloqueios_ultimos_30_dias": 2
  },
  "peso": 8,
  "acao": "REVISAR"
}
```

**3. Múltiplas Tentativas Falhas Recentes** (Peso 6)
```python
{
  "nome": "Múltiplas Tentativas Falhas Recentes",
  "parametros": {
    "tentativas_falhas_24h": 5,
    "taxa_falha_minima": 0.3
  },
  "peso": 6,
  "acao": "REVISAR"
}
```

**4. Cliente com Bloqueio Recente** (Peso 9)
```python
{
  "nome": "Cliente com Bloqueio Recente",
  "parametros": {
    "dias_desde_ultimo_bloqueio": 7
  },
  "peso": 9,
  "acao": "REVISAR"
}
```

### Tratamento de Erros

**Timeout:**
```python
try:
    response = requests.get(url, timeout=2)
except requests.Timeout:
    logger.warning("⏱️ Timeout consulta autenticação")
    return {'score_autenticacao': 0}  # Não penaliza
```

**Cliente não encontrado:**
```python
if response.status_code == 404:
    logger.info(f"ℹ️ Cliente {cpf} não encontrado")
    return {'score_autenticacao': 0}  # Não penaliza
```

**Erro interno:**
```python
if response.status_code >= 500:
    logger.error(f"❌ Erro servidor: {response.status_code}")
    return {'score_autenticacao': 0}  # Fail-safe
```

**Princípio:** Sistema NUNCA penaliza cliente por falha técnica

### Tabelas Consultadas

**Django WallClub:**
- `cliente` - Dados básicos e status bloqueio
- `cliente_autenticacao` - Tentativas de login (24h)
- `cliente_bloqueios` - Histórico de bloqueios (30 dias)
- `otp_dispositivo_confiavel` - Dispositivos conhecidos

**Índices Importantes:**
```sql
-- Performance crítica
CREATE INDEX idx_cliente_autenticacao_cpf_data 
  ON cliente_autenticacao(cpf, data_tentativa);

CREATE INDEX idx_cliente_bloqueios_cpf_data 
  ON cliente_bloqueios(cpf, data_bloqueio);

CREATE INDEX idx_dispositivo_user_ativo 
  ON otp_dispositivo_confiavel(user_id, ativo, created_at);
```

### Cache

**Não utiliza cache** (dados precisam ser em tempo real)

**Motivo:** Comportamento de autenticação muda rapidamente

### Teste em Produção

**Script manual:**
```bash
# 1. Obter token OAuth
TOKEN=$(curl -X POST http://wallclub-riskengine:8004/oauth/token/ \
  -d "grant_type=client_credentials" \
  -d "client_id=wallclub_django_internal" \
  -d "client_secret=SECRET" \
  | jq -r '.access_token')

# 2. Consultar análise
curl -X GET "http://wallclub-prod-release300:8003/cliente/api/v1/autenticacao/analise/12345678900/" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

**Valida:**
- Autenticação OAuth funcionando
- Response 200 com estrutura correta
- Flags calculadas adequadamente
- Score entre 0-50

---

## 🔗 APIs REST INTERNAS (Fase 6B)

### Visão Geral

**Comunicação entre containers** para preparação da separação física.

**Ambiente:** Produção  
**Autenticação:** Sem rate limiting (middleware interno)  
**Base URL:** `http://127.0.0.1:8005` (mesmo container portais)  
**Status:** 🟢 Operacional (13 endpoints)

### APIs Conta Digital

**Base Path:** `/api/internal/conta_digital/`

#### 1. Consultar Saldo

**Endpoint:** `POST /api/internal/conta_digital/consultar_saldo/`

**Request:**
```json
{
  "cpf": "12345678900",
  "canal_id": 1
}
```

**Response:**
```json
{
  "sucesso": true,
  "tem_saldo": true,
  "saldo_disponivel": "150.50",
  "saldo_bloqueado": "0.00",
  "valor_maximo_permitido": "150.50"
}
```

**Usado por:** posp2 (validação POS)

#### 2. Calcular Máximo Permitido

**Endpoint:** `POST /api/internal/conta_digital/calcular_maximo/`

**Request:**
```json
{
  "cpf": "12345678900",
  "canal_id": 1,
  "loja_id": 1,
  "valor_transacao": "200.00"
}
```

**Response:**
```json
{
  "sucesso": true,
  "valor_maximo_permitido": "10.00",
  "percentual_permitido": "5.00"
}
```

**Usado por:** posp2 (cálculo cashback)

#### 3. Autorizar Uso

**Endpoint:** `POST /api/internal/conta_digital/autorizar_uso/`

**Request:**
```json
{
  "cpf": "12345678900",
  "canal_id": 1,
  "valor": "50.00",
  "loja_id": 1,
  "terminal_id": "PB59237K70569"
}
```

**Response:**
```json
{
  "sucesso": true,
  "autorizacao_id": "AUTH123456",
  "status": "APROVADO",
  "valor_bloqueado": "50.00"
}
```

**Usado por:** posp2 (autorização de uso de saldo)

#### 4. Debitar Saldo

**Endpoint:** `POST /api/internal/conta_digital/debitar_saldo/`

**Usado após:** Transação aprovada

#### 5. Estornar Saldo

**Endpoint:** `POST /api/internal/conta_digital/estornar_saldo/`

**Usado após:** Transação cancelada/estornada

### APIs Checkout Recorrências

**Base Path:** `/api/internal/checkout/`

**Endpoints (8 total):**
- `GET /recorrencias/` - Listar com filtros
- `POST /recorrencias/criar/` - Criar nova
- `GET /recorrencias/{id}/` - Obter detalhes
- `POST /recorrencias/{id}/pausar/` - Pausar cobranças
- `POST /recorrencias/{id}/reativar/` - Reativar
- `POST /recorrencias/{id}/cobrar/` - Cobrar manualmente
- `PUT /recorrencias/{id}/atualizar/` - Atualizar dados
- `DELETE /recorrencias/{id}/deletar/` - Cancelar

**Usado por:** Portais Admin/Lojista (gestão de recorrências)

### Middleware Diferenciado

**Path `/api/internal/*`:**
- ❌ Sem rate limiting
- ❌ Sem autenticação OAuth (por enquanto)
- ✅ Timeout 5-10s
- ✅ Logs detalhados

**Arquivo:** `comum/middleware/security_middleware.py`

### Próximos Passos (Fase 6D)

Quando containers forem separados fisicamente:
1. Alterar `INTERNAL_API_BASE_URL` nos .env
2. Adicionar autenticação OAuth Client Credentials
3. Configurar rede Docker interna
4. Adicionar health checks

**URLs finais:**
- APP2 (POS): `http://wallclub-pos:8002`
- APP3 (APIs): `http://wallclub-apis:8003`

---

## 📧 AWS SES - EMAIL SERVICE

**Status:** ✅ Operacional (06/11/2025)  
**Implementação:** `wallclub_core.integracoes.email_service`  
**Configuração:** AWS Secrets Manager via ConfigManager

### Visão Geral

Sistema centralizado de envio de emails transacionais usando AWS SES (Simple Email Service).

**Características:**
- Templates HTML centralizados em `/templates/emails/`
- Credenciais gerenciadas via AWS Secrets Manager
- Suporte a anexos
- Fallback para texto puro
- Logs detalhados de envio

### Configuração

**Credenciais (AWS Secrets Manager):**
```json
{
  "MAILSERVER_URL": "email-smtp.us-east-1.amazonaws.com",
  "MAILSERVER_USERNAME": "AKIAXXXXXXXXXXXXXXXX",
  "MAILSERVER_PASSWD": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```

**Django Settings:**
```python
# wallclub/settings/base.py
from wallclub_core.utilitarios.config_manager import get_config_manager
_email_config = get_config_manager().get_email_config()

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = _email_config.get('host', 'email-smtp.us-east-1.amazonaws.com')
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = _email_config.get('user')
EMAIL_HOST_PASSWORD = _email_config.get('password')
DEFAULT_FROM_EMAIL = 'noreply@wallclub.com.br'
```

### Uso

**Email Simples:**
```python
from wallclub_core.integracoes.email_service import EmailService

resultado = EmailService.enviar_email_simples(
    destinatario='usuario@example.com',
    assunto='Bem-vindo ao WallClub',
    mensagem='Sua conta foi criada com sucesso!'
)
```

**Email com Template:**
```python
resultado = EmailService.enviar_email(
    destinatarios=['usuario@example.com'],
    assunto='Reset de Senha',
    template_html='emails/autenticacao/reset_senha.html',
    template_context={
        'usuario': usuario,
        'link_reset': 'https://...',
        'validade_horas': 24
    }
)
```

### Templates Disponíveis

**Autenticação:**
- `emails/autenticacao/primeiro_acesso.html` - Primeiro acesso com senha temporária
- `emails/autenticacao/reset_senha.html` - Reset de senha
- `emails/autenticacao/senha_alterada.html` - Confirmação de alteração

**Checkout:**
- `checkout/emails/link_pagamento.html` - Link de pagamento

**Base:**
- `emails/base.html` - Template base com estilos

### Email Service (Portais)

**Implementação:** `portais/controle_acesso/email_service.py`

**Métodos:**
- `enviar_email_primeiro_acesso()` - Email de boas-vindas
- `enviar_email_reset_senha()` - Solicitação de reset
- `enviar_email_senha_alterada()` - Confirmação de alteração

**Contexto Automático:**
- `canal_nome` - Nome do canal (Admin, Vendas, Lojista)
- `canal_logo_url` - URL do logo do canal
- `support_email` - Email de suporte

### Monitoramento

**Logs:**
```bash
# Ver logs de email
docker logs wallclub-portais | grep -i "email\|smtp"

# Logs detalhados
tail -f /var/www/WallClub_backend/services/django/logs/portais.controle_acesso.log
```

**Métricas AWS SES:**
- Sending Statistics (Console AWS)
- Bounce Rate
- Complaint Rate
- Delivery Rate

### Troubleshooting

**Email não chega:**
1. Verificar se AWS SES está em produção (não sandbox)
2. Verificar se domínio `noreply@wallclub.com.br` está verificado
3. Verificar logs: `docker logs wallclub-portais --tail 100 | grep email`

**Erro de autenticação:**
1. Verificar credenciais no AWS Secrets Manager
2. Testar: `docker exec -it wallclub-portais python scripts/test_email.py`

**Template não encontrado:**
1. Verificar `TEMPLATES['DIRS']` em `settings/base.py`
2. Confirmar que template existe em `/templates/emails/`

### Testes

**Script de teste:**
```bash
docker exec -it wallclub-portais python scripts/test_email.py
```

**Testes incluídos:**
- ✅ Configurações AWS SES
- ✅ Templates disponíveis
- ✅ Email simples
- ✅ Email com template HTML
- ✅ Email de reset de senha

---

## 🏦 INTEGRAÇÃO OWN FINANCIAL

**Status:** ⚠️ 92% Concluído (Aguardando credenciais OPPWA e-commerce)  
**Data:** 21/11/2025  
**Documentação Completa:** [PLANO_REPLICACAO_ESTRUTURA.md](integradora%20own/PLANO_REPLICACAO_ESTRUTURA.md)

### Visão Geral

Integração completa com Own Financial replicando estrutura Pinbank, suportando:
- **APIs Adquirência** (OAuth 2.0) - Consultas transações/liquidações ✅
- **Webhooks Tempo Real** - Transações, liquidações, cadastro ✅
- **API OPPWA E-commerce** - Pagamentos e tokenização ⏳
- **Roteador Multi-Gateway** - Convivência Pinbank + Own ✅

### Componentes Implementados

#### 1. Módulo `adquirente_own/`
```
adquirente_own/
├── services.py                         # OwnService (OAuth 2.0)
├── services_transacoes_pagamento.py   # TransacoesOwnService (OPPWA)
├── views_webhook.py                    # 3 webhooks tempo real
├── urls_webhook.py                     # Rotas webhooks
└── cargas_own/
    ├── models.py                       # OwnExtratoTransacoes, Liquidacoes
    ├── services_carga_transacoes.py    # Carga API transações
    ├── services_carga_liquidacoes.py   # Carga API liquidações
    ├── tasks.py                        # 4 Celery tasks (double-check)
    └── management/commands/            # 3 comandos Django
```

#### 2. Roteador Multi-Gateway
- **Arquivo:** `checkout/services_gateway_router.py`
- **Função:** Roteia pagamentos entre Pinbank e Own baseado em `loja.gateway_ativo`
- **Métodos:**
  - `obter_gateway_loja()` - Consulta gateway ativo
  - `obter_service_transacao()` - Retorna service correto
  - `processar_pagamento_debito()` - Pagamento unificado
  - `processar_estorno()` - Estorno unificado

#### 3. TransacoesOwnService - E-commerce
**Métodos de Pagamento:**
- `create_payment_debit()` - Débito/crédito
- `create_payment_with_tokenization()` - PA + token
- `create_payment_with_registration()` - Pagamento com token
- `refund_payment()` - Estorno

**Gerenciamento de Tokens:**
- `delete_registration()` - Excluir token
- `get_registration_details()` - Consultar token
- `list_registrations()` - Listar tokens

**Métodos Adapter (Compatibilidade Pinbank):**
- Interface 100% compatível com `TransacoesPinbankService`
- Checkouts funcionam com ambos gateways sem modificação

#### 4. Webhooks Tempo Real
**Endpoints:**
- `POST /webhook/transacao/` - Vendas em tempo real
- `POST /webhook/liquidacao/` - Liquidações em tempo real
- `POST /webhook/cadastro/` - Status credenciamento

**Características:**
- Validação de payloads
- Detecção de duplicatas
- Transações atômicas
- Logs detalhados

#### 5. Cargas Automáticas
**Celery Tasks (Double-check diário):**
- `carga_transacoes_own_diaria` - 02:00
- `carga_liquidacoes_own_diaria` - 02:30
- `carga_transacoes_own_periodo` - Sob demanda
- `sincronizar_status_pagamentos_own` - Sincronização

### Diferenças Pinbank vs Own

#### Autenticação
| Sistema | Pinbank | Own Adquirência | Own E-commerce |
|---------|---------|-----------------|----------------|
| Método | Username/Password | OAuth 2.0 | Bearer fixo |
| Token | Fixo | 5min (cache 4min) | Fixo |
| Endpoint | N/A | `/agilli/v2/auth` | N/A |

#### APIs
| Funcionalidade | Pinbank | Own |
|----------------|---------|-----|
| Consulta Transações | Extrato POS | `/transacoes/v2/buscaTransacoesGerais` |
| Consulta Liquidações | N/A | `/parceiro/v2/consultaLiquidacoes` |
| Pagamentos E-commerce | API proprietária | OPPWA REST (`/v1/payments`) |
| Webhooks | ❌ | ✅ Tempo real |
| Frequência Cargas | 30min | Webhook + Double-check diário |

### Status Atual

**✅ Concluído (92%):**
- Estrutura base e models
- APIs Adquirência (OAuth 2.0)
- Webhooks tempo real
- Cargas automáticas
- Roteador multi-gateway
- Checkouts adaptados
- POS TRData Own

**⏳ Pendente (8%):**
- Credenciais OPPWA da Own:
  - `entity_id` - ID entidade OPPWA
  - `access_token` - Bearer token fixo
- Testes e-commerce em sandbox
- Validação completa

### Próximos Passos

1. **Solicitar à Own Financial:**
   - Credenciais OPPWA (`entity_id` + `access_token`)
   - Cartões de teste ambiente sandbox
   - Documentação específica (se houver)

2. **Após receber credenciais:**
   - Executar `teste_own_ecommerce.py`
   - Validar 8 cenários de teste
   - Testes integração checkout

3. **Produção:**
   - Lojas piloto
   - Monitoramento
   - Documentação uso

---

---

## 🔒 SEGURANÇA E DOMÍNIOS

### Domínios de Produção

**Portais (HTTPS apenas):**
- `wcadmin.wallclub.com.br` - Portal Admin
- `wcvendas.wallclub.com.br` - Portal Vendas
- `wclojista.wallclub.com.br` - Portal Lojista
- `wcinstitucional.wallclub.com.br` - Portal Institucional

**APIs e Checkout:**
- `wcapi.wallclub.com.br` - API Unificada (Mobile + POS)
- `checkout.wallclub.com.br` - Checkout Web + 2FA

**Monitoramento:**
- `flower.wallclub.com.br` - Flower (Celery)

### Configurações de Segurança

**CORS e CSRF:**
- Middleware `django-cors-headers` configurado
- `CORS_ALLOWED_ORIGINS` via variável de ambiente
- `CSRF_TRUSTED_ORIGINS` separado por ambiente (HTTP dev / HTTPS prod)
- Validação CORS manual removida (usa middleware)

**Variáveis de Ambiente (.env.production):**
```bash
# URLs base
BASE_URL=https://wcadmin.wallclub.com.br
CHECKOUT_BASE_URL=https://checkout.wallclub.com.br
PORTAL_LOJISTA_URL=https://wclojista.wallclub.com.br
PORTAL_VENDAS_URL=https://wcvendas.wallclub.com.br
MEDIA_BASE_URL=https://wcapi.wallclub.com.br
MERCHANT_URL=wallclub.com.br

# Segurança
ALLOWED_HOSTS=wcapi.wallclub.com.br,wcadmin.wallclub.com.br,...
CORS_ALLOWED_ORIGINS=https://wallclub.com.br,https://wcadmin.wallclub.com.br,...
```

**Desenvolvimento vs Produção:**
- Domínios `.local` apenas em `DEBUG=True`
- HTTP apenas em desenvolvimento
- HTTPS obrigatório em produção
- Nginx não usado em desenvolvimento (acesso direto às portas)

### Arquivos Ajustados (22/11/2025)

1. ✅ `views_2fa.py` - CORS manual removido (usa middleware)
2. ✅ `portais.py` - CSRF_TRUSTED_ORIGINS separado por DEBUG
3. ✅ `production.py` - IP interno AWS removido
4. ✅ `nginx.conf` - Domínios `.local` removidos
5. ✅ `portais.py` - ALLOWED_HOSTS limpo
6. ✅ `checkout/services.py` - URL via settings
7. ✅ `portais/vendas/services.py` - URL via settings
8. ✅ `portais/controle_acesso/email_service.py` - URLs via settings
9. ✅ `portais/lojista/views_ofertas.py` - URL via settings
10. ✅ `adquirente_own/services_transacoes_pagamento.py` - URL via settings
11. ✅ `base.py` - 6 variáveis de URL adicionadas

---

**Última atualização:** 01/12/2025  
**Manutenção:** Jean Lessa + Claude AI

---

## 🎁 SISTEMA DE OFERTAS E CASHBACK

### Status Atual (08/12/2025)

**Ofertas:** ✅ Implementado
- 5 tabelas criadas (ofertas, grupos, disparos, envios)
- Portal Lojista com menu ativo
- Escopo: loja específica ou grupo econômico
- Segmentação: todos do canal ou grupo customizado
- Push notifications via Firebase/APN
- Histórico de disparos com métricas

**Cashback:** ✅ Em produção
- Sistema centralizado (Wall + Loja)
- Regras de concessão validadas
- Contabilização separada por tipo
- Portal Lojista com CRUD completo
- Integração com conta digital completa
- Compras informativas (tipo COMPRA_CARTAO)

### Pendências

**Ofertas:**
- Testes em produção
- Validação de disparos em massa
- Métricas de conversão

**Conta Digital:**
- Integrar compras informativas no POS Pinbank
- Integrar compras informativas no Checkout Web

---

## 📊 PORTAL LOJISTA - NOVAS FUNCIONALIDADES

### Vendas por Operador (08/12/2025)

**Localização:** `/vendas/` → Botão "Pesquisar venda por operador"

**Funcionalidades:**
- Relatório agrupado por operador POS
- Filtros: data inicial/final, loja, NSU
- Métricas: qtde vendas, valor total, ticket médio
- Totalizador geral

**Query:**
```sql
SELECT nome_operador, SUM(valor), COUNT(*)
FROM baseTransacoesGestao + transactiondata + terminais_operadores
GROUP BY nome_operador
```

**Status:** ✅ Implementado e funcional
