# REFATORAÇÃO E MIGRAÇÃO PARA MÚLTIPLOS CONTAINERS

**Versão:** 1.0  
**Data Início:** 15/10/2025  
**Data Conclusão Fase 6D:** 07/11/2025  
**Status:** ✅ Fase 6 (A+B+C+D) CONCLUÍDA em DEV  
**Próximo:** Deploy em Produção

---

## 📋 ÍNDICE

1. [Visão Executiva](#visão-executiva)
2. [Histórico Completo - Fases 0 a 6](#histórico-completo)
3. [Arquitetura Final](#arquitetura-final)
4. [Alterações Técnicas Detalhadas](#alterações-técnicas-detalhadas)
5. [Sistema de Comunicação Entre Containers](#sistema-de-comunicação)
6. [Melhorias Implementadas](#melhorias-implementadas)
7. [Métricas e Resultados](#métricas-e-resultados)
8. [Guia de Deploy](#guia-de-deploy)

---

## 🎯 VISÃO EXECUTIVA

### Objetivo Alcançado

Transformar monolito Django em **4 containers especializados** com deploy independente, comunicação via APIs REST internas, e arquitetura preparada para escalabilidade horizontal.

### Duração Total

**29 semanas** (15/10/2025 - 07/11/2025)
- Fases 0-5: 26 semanas (preparação + segurança + antifraude + services + 2FA + recorrência)
- Fase 6 (A+B+C+D): 3 semanas (CORE limpo + dependências + monorepo + containers)

### Containers Finais

```
┌──────────────────────────────────────────────────────────┐
│  NGINX Gateway (porta 80/443)                            │
│  ├─ admin.wallclub.com.br       → portais:8005          │
│  ├─ vendas.wallclub.com.br      → portais:8005          │
│  ├─ lojista.wallclub.com.br     → portais:8005          │
│  ├─ wcapi.wallclub.com.br (UNIFICADO)                   │
│  │   ├─ /api/oauth/*            → apis:8007             │
│  │   ├─ /api/v1/posp2/*         → pos:8006              │
│  │   ├─ /api/internal/*         → apis:8007             │
│  │   └─ /api/v1/*               → apis:8007             │
│  └─ checkout.wallclub.com.br    → apis:8007             │
└──────────────────────────────────────────────────────────┘
         │         │         │         │
    ┌────┴────┬────┴────┬────┴────┬────┴────┐
    │         │         │         │         │
┌───┴────┐┌──┴────┐┌───┴────┐┌───┴────┐┌──┴────┐
│Portais ││ POS   ││ APIs   ││ Risk   ││ Redis │
│:8005   ││ :8006 ││ :8007  ││ :8008  ││ :6379 │
└───┬────┘└───┬───┘└───┬────┘└───┬────┘└───────┘
    │         │   ▲    │         │
    │         │   │    │         │
    │         └───┼────┘         │
    │      API    │              │
    │    Interna  │              │
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

**Total:** 9 containers em produção

---

## 📚 HISTÓRICO COMPLETO

### FASE 0: PREPARAÇÃO (Semanas 1-2) ✅

**Objetivo:** Preparar ambiente e validar APIs existentes

**Entregas:**
- ✅ BigDataCorp já integrado (substitui Serpro CPF)
- ✅ SMS/WhatsApp OTP já funcionando
- ✅ Redis configurado (172.18.0.2:6379)
- ✅ Branch `feature/multi-app-security` criada
- ✅ Economia de R$ 450/mês (APIs já contratadas)

**Data:** 15/10/2025

---

### FASE 1: SEGURANÇA CRÍTICA BÁSICA (Semanas 3-6) ✅

**Objetivo:** Mitigar riscos imediatos no monolito

#### Semana 3: Middleware e Rate Limiting
- ✅ `APISecurityMiddleware` implementado
- ✅ `RateLimiter` com Redis
- ✅ Headers de segurança (X-Frame-Options, HSTS)
- ✅ Validação Content-Type e payload

**Arquivos:**
- `comum/middleware/security_middleware.py` (235 linhas)

#### Semana 4: Auditoria e OAuth
- ✅ Tabela `cliente_auditoria_validacao_senha`
- ✅ `AuditoriaService` - registrar tentativas login
- ✅ Bloqueio automático: 5 falhas / 15 min
- ✅ `OAuthService` expandido (254 linhas)
- ✅ Campo `device_fingerprint` em OAuthToken
- ✅ Endpoint `/api/oauth/revoke/`

**Arquivos:**
- `apps/cliente/services_security.py` (280 linhas)
- `comum/oauth/services.py` (254 linhas)
- `scripts/producao/criar_tabela_auditoria.sql`

#### Semanas 5-6: Validação CPF e Decorators
- ✅ `ValidadorCPFService` - mod-11 + blacklist + cache
- ✅ Decorators `@handle_api_errors` + `@validate_required_params`
- ✅ 13 endpoints POSP2 refatorados
- ✅ ~90 linhas removidas

**Arquivos:**
- `comum/seguranca/validador_cpf.py` (227 linhas)
- `posp2/views.py` - 13 endpoints com decorators

**Resultado:** Sistema seguro e auditável para operação

---

### FASE 2: ANTIFRAUDE E ANÁLISE DE RISCO (Semanas 7-14) ✅

**Objetivo:** Criar container separado com sistema antifraude completo

#### Semana 7: Container Risk Engine
- ✅ Novo projeto Django `wallclub-riskengine`
- ✅ Dockerfile + docker-compose
- ✅ Models: `TransacaoRisco`, `DecisaoAntifraude`, `RegraAntifraude`
- ✅ Portal Admin - revisão manual
- ✅ Deploy produção: `/var/www/wallclub_django_risk_engine`

**Repositório:** https://github.com/JeanPierreLessa/wallclub_django_risk_engine

#### Semana 8: Coleta de Dados
- ✅ `ColetaDadosService` - normalizar POS/App/Web
- ✅ Extração BIN de cartões
- ✅ Detecção automática de origem

**Arquivos:**
- `antifraude/services_coleta.py` (330 linhas)

#### Semana 9: Integração MaxMind
- ✅ `MaxMindService` - consulta score (com fallback)
- ✅ Cache Redis (1 hora)
- ✅ Migração credenciais para AWS Secrets Manager
- ✅ Score real validado em produção

**Arquivos:**
- `antifraude/services_maxmind.py` (280 linhas)

#### Semanas 10-11: Engine de Decisão
- ✅ 5 regras parametrizadas
- ✅ Blacklist/Whitelist
- ✅ Ajuste score com MaxMind + regras internas
- ✅ Decisão: aprovar/negar/revisar

#### Semana 12: Listas e Painel
- ✅ Django Admin customizado
- ✅ Whitelist automática (10+ transações aprovadas/30 dias)
- ✅ Dashboard completo integrado ao Portal Admin
- ✅ Métricas: transações, decisões, scores, performance

#### Semana 13: 3DS e API
- ✅ `Auth3DSService` (casca implementada)
- ✅ API `POST /api/antifraude/analyze/`
- ✅ API `GET /api/antifraude/decision/<id>/`
- ✅ API `GET /api/antifraude/health/`

#### Semana 14: Integração POSP2 + Checkout Web
- ✅ POSP2 intercepta antes Pinbank (linha ~333)
- ✅ Checkout Web integrado (linha ~540)
- ✅ Fail-open implementado
- ✅ Latência média: 180-460ms

**Resultado:** Container antifraude operacional em produção

**Custo:** R$ 70-120/mês (MaxMind)

---

### FASE 3: SERVICES E REFATORAÇÃO (Semanas 15-19) ✅

**Objetivo:** Separar lógica de negócio das views

#### 10+ Services Criados (4.370+ linhas)

1. **HierarquiaOrganizacionalService** (519 linhas)
2. **CheckoutVendasService** (592 linhas)
3. **UsuarioService** (410 linhas) + **ControleAcessoService** (1.057 linhas)
4. **TerminaisService** (332 linhas)
5. **PagamentoService** (545 linhas)
6. **RecorrenciaService** (319 linhas)
7. **OfertaService** (505 linhas)
8. **RPRService** (384 linhas)
9. **OAuthService** (270 linhas)
10. **AuditoriaService** (570 linhas)

#### 8 Views Otimizadas com SQL Direto

- Portal Lojista: Recebimentos, Vendas, Cancelamentos, Conciliação, Dashboard
- Portal Admin: Dashboard, RPR, Base Transações

**Ganho de Performance:** 70-80% redução tempo resposta

**Resultado:** Zero manipulação direta de models nas views críticas

---

### FASE 4: AUTENTICAÇÃO 2FA E DEVICE TRACKING (Semanas 20-23) ✅

**Objetivo:** Segunda camada de autenticação em pontos críticos

#### Semana 20: Infraestrutura Base
- ✅ Models: `AutenticacaoOTP`, `DispositivoConfiavel`
- ✅ `OTPService` base
- ✅ Rate limiting: 3 tent/código, 5 códigos/hora

#### Semana 21: 2FA Checkout Web
- ✅ Cliente autogerencia telefone
- ✅ 2FA SEMPRE obrigatório
- ✅ Integração WhatsApp com template CURRENCY
- ✅ Limite progressivo: R$100 → R$200 → R$500

**Status:** ⏸️ Aguardando autorização Pinbank

#### Semana 22: Device Management
- ✅ `DeviceManagementService` completo
- ✅ Limite: Cliente 1 device, Vendedor 2, Admin sem limite
- ✅ Portal Admin - gestão dispositivos
- ✅ Documentação mobile completa

#### Semana 23: Sistema Segurança Multi-Portal
- ✅ Models: `BloqueioSeguranca`, `AtividadeSuspeita`
- ✅ 6 Detectores automáticos
- ✅ Middleware validação login
- ✅ Portal Admin - telas segurança

**Resultado:** Sistema 2FA completo + device tracking + bloqueios centralizados

---

### FASE 5: SISTEMA DE RECORRÊNCIA (Semanas 24-26) ✅

**Objetivo:** Sistema completo de cobranças recorrentes automáticas

#### Implementações
- ✅ Model `RecorrenciaAgendada` completo
- ✅ `CheckoutVendasService` expandido (592 linhas)
- ✅ 4 Celery Tasks agendadas (Beat configurado)
- ✅ Portal Vendas (7 views + 4 templates)
- ✅ Fluxo tokenização separado (`link_recorrencia_web`)
- ✅ Permissões granulares checkout vs recorrência

**Celery Tasks:**
1. `processar_recorrencias_do_dia` - Diariamente 08:00
2. `retentar_cobrancas_falhadas` - Diariamente 10:00
3. `notificar_recorrencias_hold` - Diariamente 18:00
4. `limpar_recorrencias_antigas` - Domingo 02:00

**Resultado:** Sistema recorrência operacional com automação completa

---

### FASE 6A: CORE LIMPO (Semana 27) ✅

**Objetivo:** Remover dependências do CORE para apps

**Entregas:**
- ✅ 0 imports de apps no `wallclub_core`
- ✅ Bug device_fingerprint corrigido
- ✅ `comum/oauth/jwt_utils.py` criado
- ✅ `comum/seguranca/services_device.py` refatorado
- ✅ 6 callers atualizados

**Commits:**
- `b366851` - feat(fase6a): CORE limpo
- `4e2fc56` - fix: device_fingerprint sobrescrito

---

### FASE 6B: RESOLVER DEPENDÊNCIAS (Semana 28) ✅

**Objetivo:** Resolver 103 imports cruzados entre containers

**Estratégias:**
- 🌐 APIs REST Internas: 70% (26 endpoints)
- 📊 SQL Direto: 25% (2 classes, 9 métodos)
- 🔄 Lazy Imports: 5% (17 arquivos)

#### APIs Internas Criadas (26 endpoints)

**Conta Digital (5):**
- consultar-saldo, autorizar-uso, debitar-saldo, estornar-saldo, calcular-maximo

**Checkout Recorrências (8):**
- listar, criar, obter, pausar, reativar, cobrar, atualizar, deletar

**Ofertas (6):**
- listar, criar, obter, atualizar, grupos/listar, grupos/criar

**Parâmetros (7):**
- configuracoes/loja, configuracoes/contar, configuracoes/ultima, loja/modalidades, planos, importacoes

**Resultado:** 0 imports diretos entre containers

---

### FASE 6C: MONOREPO UNIFICADO (Semana 29) ✅

**Objetivo:** Unificar 3 repositórios em 1 monorepo

**Entregas:**
- ✅ Package `wallclub_core` criado
- ✅ 113 arquivos migrados (`comum/` → `wallclub_core/`)
- ✅ Diretório `comum/` removido
- ✅ 1 repositório git unificado

**Estrutura Final:**
```
WallClub_backend/
├── services/
│   ├── django/          # Django Main
│   ├── riskengine/      # Antifraude
│   └── core/            # wallclub_core (package)
├── docs/
├── .gitignore
├── README.md
└── docker-compose.yml
```

**Instalação:**
```bash
pip install -e /path/to/services/core
```

---

### FASE 6D: SEPARAÇÃO EM 4 CONTAINERS (Semanas 30-32) ✅

**Objetivo:** Separar Django em 4 containers especializados

#### Alterações 07/11/2025

**1. DNS Unificado**
- ❌ Removido: `wcapipos.wallclub.com.br`
- ✅ Unificado: `wcapi.wallclub.com.br`
- ✅ Roteamento por path no Nginx

**2. API Interna Cliente (6 endpoints)**
- `POST /api/internal/cliente/consultar_por_cpf/`
- `POST /api/internal/cliente/cadastrar/`
- `POST /api/internal/cliente/obter_cliente_id/`
- `POST /api/internal/cliente/atualizar_celular/`
- `POST /api/internal/cliente/obter_dados_cliente/`
- `POST /api/internal/cliente/verificar_cadastro/`

**3. Service Helper**
- `wallclub_core/integracoes/api_interna_service.py`
- Classe `APIInternaService`
- Mapeamento automático de containers

**4. Decorator OAuth Interno**
- `@require_oauth_internal` criado
- Autenticação entre containers

**5. Container POS Atualizado**
- ❌ Removidos imports diretos de `apps.cliente`
- ✅ Usa API Interna HTTP
- ✅ 3 arquivos refatorados (services.py, services_transacao.py, services_conta_digital.py)

**Arquivos Criados (07/11):**
- `apps/cliente/views_api_interna.py`
- `apps/cliente/urls_api_interna.py`
- `wallclub_core/integracoes/api_interna_service.py`
- `wallclub_core/oauth/decorators.py` (decorator `@require_oauth_internal`)

**Arquivos Modificados (07/11):**
- `nginx.conf` - DNS unificado
- `wallclub/urls_apis.py` - Rotas API interna
- `posp2/services.py` - 3 métodos usando API interna
- `posp2/services_transacao.py` - 4 imports substituídos
- `posp2/services_conta_digital.py` - 1 import substituído

**Resultado:** 4 containers independentes + 32 APIs internas + DNS unificado

---

## 🏗️ ARQUITETURA FINAL

### Containers (9 total)

1. **nginx** - Gateway (porta 80/443)
2. **wallclub-portais** - Admin + Vendas + Lojista (porta 8005)
3. **wallclub-pos** - Terminal POS (porta 8006)
4. **wallclub-apis** - APIs Mobile + Checkout (porta 8007)
5. **wallclub-riskengine** - Antifraude (porta 8008)
6. **wallclub-redis** - Cache/Broker (porta 6379)
7. **wallclub-celery-worker-portais** - Tasks portais
8. **wallclub-celery-worker-apis** - Tasks APIs
9. **wallclub-celery-beat** - Scheduler

### Distribuição de Apps

**Container 1: Portais (8005)**
- `portais/admin/`, `portais/lojista/`, `portais/vendas/`
- `portais/controle_acesso/`, `sistema_bancario/`
- Deploy: Frequente (features admin/lojista)

**Container 2: POS (8006)**
- `posp2/`, `pinbank/`, `parametros_wallclub/`
- ⚠️ NÃO importa `apps.cliente` diretamente
- ✅ Usa API Interna HTTP
- Deploy: Raro (sistema crítico)

**Container 3: APIs (8007)**
- `apps/cliente/`, `apps/conta_digital/`, `apps/ofertas/`
- `apps/transacoes/`, `apps/oauth/`, `checkout/`
- API Interna: 32 endpoints (6 Cliente + 26 outros)
- Deploy: Médio (features app mobile)

**Container 4: Risk Engine (8008)**
- `antifraude/`
- Deploy: Frequente (ajustes regras)

### Comunicação Entre Containers

**API Interna HTTP (32 endpoints):**
- Autenticação: `@require_oauth_internal`
- Timeout: 30s padrão
- Service helper: `APIInternaService`
- Sem rate limiting entre containers

**Exemplo:**
```python
from wallclub_core.integracoes.api_interna_service import APIInternaService

response = APIInternaService.chamar_api_interna(
    metodo='POST',
    endpoint='/api/internal/cliente/consultar_por_cpf/',
    payload={'cpf': '12345678900', 'canal_id': 1},
    contexto='apis'
)
```

---

## 📊 MÉTRICAS E RESULTADOS

### Código
- **Services criados:** 10+ (4.370+ linhas)
- **Linhas eliminadas:** ~160 (decorators + refatoração)
- **Queries diretas eliminadas:** 33
- **Métodos novos:** 24
- **Arquivos migrados:** 113 (comum → wallclub_core)

### Performance
- **Redução tempo resposta:** 70-80% (SQL otimizado)
- **Latência antifraude:** 180-460ms
- **Cache:** Redis implementado

### Segurança
- **Tentativas login auditadas:** 100%
- **Transações analisadas:** 100%
- **Detectores automáticos:** 6
- **Tipos de alertas:** 9

### Arquitetura
- **Containers:** 9 (4 Django + 5 auxiliares)
- **APIs internas:** 32
- **Deploy:** Independente por container
- **Escalabilidade:** Horizontal

---

## 🚀 GUIA DE DEPLOY

### Comandos

```bash
cd /var/www/WallClub_backend

# Pull do código
git pull origin v2.0.0

# Rebuild containers afetados
docker-compose up -d --build wallclub-nginx wallclub-pos wallclub-apis

# Verificar logs
docker logs wallclub-pos --tail 50
docker logs wallclub-apis --tail 50
docker logs nginx --tail 50
```

### Validação

```bash
# 1. Testar OAuth unificado
curl -X POST https://wcapi.wallclub.com.br/api/oauth/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "posp2",
    "client_secret": "...",
    "grant_type": "client_credentials"
  }'

# 2. Testar endpoint POS (deve usar API interna)
curl -X POST https://wcapi.wallclub.com.br/api/v1/posp2/valida_cpf/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "cpf": "17653377807",
    "terminal": "PBF923BH70663"
  }'
```

**Resultado esperado:** Sem erro `No installed app with label 'cliente'`

---

## 📝 DOCUMENTAÇÃO ATUALIZADA

- ✅ `docs/architecture/1. ARQUITETURA_GERAL.md`
- ✅ `docs/architecture/2. DIRETRIZES_UNIFICADAS.md`
- ✅ `docs/architecture/3. INTEGRACOES.md`
- ✅ `docs/README.md`
- ✅ `services/django/docs/TESTES_POSP2_ENDPOINTS.txt`

---

**Responsável:** Jean Lessa  
**Data Conclusão Fase 6D:** 07/11/2025  
**Próximo Passo:** Deploy em Produção
