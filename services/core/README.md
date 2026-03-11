# WallClub Core


Monorepo unificado do ecossistema WallClub - 4 containers Django independentes + Sistema de Monitoramento completo.


## 🏗️ Arquitetura

### Containers Django
- **wallclub-portais** - Portal Admin + Vendas + Lojista
- **wallclub-apis** - APIs Mobile + Checkout Web
- **wallclub-pos** - Terminal POS
- **wallclub-riskengine** - Sistema Antifraude

### Infraestrutura
- **Redis** - Cache + Message Broker
- **Celery Worker + Beat** - Tarefas assíncronas
- **Nginx** - Reverse Proxy + SSL

### Monitoramento
- **Prometheus** - Coleta de métricas
- **Alertmanager** - Gerenciamento de alertas + Notificações Telegram
- **Grafana** - Dashboards e visualizações
- **Node Exporter** - Métricas do sistema operacional
- **Redis Exporter** - Métricas do Redis

### wallclub_core (Package Compartilhado)
- **database/**: Queries SQL diretas (read-only)
- **decorators/**: Decorators para APIs
- **estr_organizacional/**: Canal, Loja, Regional, Grupo Econômico, Vendedor
- **integracoes/**: Clientes para APIs internas e serviços externos
- **middleware/**: Security, Session Timeout
- **oauth/**: JWT, OAuth 2.0, Decorators de autenticação
- **seguranca/**: 2FA, Device Management, Rate Limiter, Validador CPF
- **services/**: Auditoria
- **templatetags/**: Tags de formatação
- **utilitarios/**: Config Manager, Export Utils, Formatação

## Instalação Local

```bash
pip install -e /path/to/wallclub_core
```

## Instalação em Containers

No `requirements.txt` do container:

```
wallclub_core @ file:///shared/wallclub_core
```

## Versão

**1.0.0** - Extração inicial do módulo `comum/`


## 📊 Sistema de Monitoramento



### Alertas Configurados (14 regras)

**Críticos (30min repeat):**
- ServiceDown - Serviço não responde por 30s
- RedisDown - Redis offline por 1min
- MySQLDown - MySQL offline por 1min
- DiskSpaceLowCritical - Disco <10%

**Warning (1h repeat):**
- HealthCheckFailing - Health check falhando por 5min
- HighDatabaseLatency - Latência DB >1s por 5min
- RedisMemoryHigh - Redis usando >90% da memória
- MySQLConnectionsHigh - MySQL usando >80% das conexões
- CeleryTasksFailing - Tarefas Celery falhando por 5min
- DiskSpaceLowWarning - Disco <20%
- HighCPUUsage - CPU >80% por 10min
- HighMemoryUsage - Memória >90% por 10min
- LowAvailability - Disponibilidade <95% na última hora

### Notificações
- **Telegram:** @Wallclub_monitor_bot
- **Alertmanager:** Gerenciamento inteligente com grouping e rate limiting
- **Resolved:** Notificação automática quando alerta é resolvido

### Dashboards Grafana
- Métricas de sistema (CPU, RAM, Disco, Rede)
- Métricas de aplicação (Requisições, Latência, Erros)
- Métricas de Redis (Memória, Conexões, Hit Rate)
- Métricas customizadas Django

## 🛠️ Tecnologias

- **Backend:** Python 3.11, Django 4.2
- **Cache/Broker:** Redis 7
- **Queue:** Celery
- **Proxy:** Nginx 1.25
- **Monitoramento:** Prometheus, Alertmanager, Grafana
- **Notificações:** Telegram Bot API
- **Secrets:** AWS Secrets Manager
- **Container:** Docker + Docker Compose
