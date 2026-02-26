# Sistema de Monitoramento - WallClub

Documentação técnica do sistema de monitoramento e observabilidade.

---

## 📊 Monitorias Implementadas

### 1. Métricas Prometheus

**Containers Django (4):**
- `wallclub-portais` (porta 8005)
- `wallclub-apis` (porta 8007)
- `wallclub-pos` (porta 8006)
- `wallclub-riskengine` (porta 8008)

**Endpoint:** `/metrics`

**Métricas expostas:**
```prometheus
# HELP up Service is up and running
# TYPE up gauge
up 1

# HELP django_db_connection_status Database connection status (1=connected, 0=disconnected)
# TYPE django_db_connection_status gauge
django_db_connection_status 1

# HELP django_info Django application information
# TYPE django_info gauge
django_info{version="4.2.23"} 1
```

**Implementação:** `monitoring/metrics_view.py`

---

### 2. Redis Exporter

**Container:** `wallclub-redis-exporter` (porta 9121)

**Métricas principais:**
- `redis_up` - Status do Redis (1=UP, 0=DOWN)
- `redis_memory_used_bytes` - Memória utilizada
- `redis_memory_max_bytes` - Memória máxima
- `redis_connected_clients` - Clientes conectados
- `redis_commands_processed_total` - Total de comandos processados

**Configuração:** Scraping automático via Prometheus

---

### 3. Node Exporter (Sistema)

**Container:** `wallclub-node-exporter` (porta 9100)

**Métricas principais:**
- `node_filesystem_avail_bytes` - Espaço disponível em disco
- `node_filesystem_size_bytes` - Tamanho total do disco
- `node_cpu_seconds_total` - Uso de CPU
- `node_memory_MemAvailable_bytes` - Memória disponível
- `node_memory_MemTotal_bytes` - Memória total

**Nota:** Monitora o ambiente Docker. Para monitorar servidor de banco, ver seção "Produção" abaixo.

---

### 4. Health Checks

**Endpoints em todos os containers Django:**

| Endpoint | Descrição | Validações |
|----------|-----------|------------|
| `/health/` | Status básico | Aplicação rodando |
| `/health/live/` | Liveness probe | Aplicação viva |
| `/health/ready/` | Readiness probe | DB + Redis |
| `/health/startup/` | Startup probe | DB + Redis + Celery |

**Implementação:** `monitoring/health_checks.py`

---

## 🚨 Alertas Configurados

**Total:** 14 alertas

### Alertas Críticos (severity: critical)

| Alerta | Condição | Tempo | Notificação |
|--------|----------|-------|-------------|
| **ServiceDown** | `up == 0` | 30s | Telegram + Email |
| **RedisDown** | `redis_up == 0` | 1min | Telegram + Email |
| **MySQLDown** | `django_db_connection_status == 0` | 1min | Telegram + Email |
| **DiskSpaceLowCritical** | Disco < 10% | 5min | Telegram + Email |

### Alertas de Warning (severity: warning)

| Alerta | Condição | Tempo | Notificação |
|--------|----------|-------|-------------|
| **HealthCheckFailing** | Health check falha | 5min | Telegram + Email |
| **HighDatabaseLatency** | Latência DB > 1s | 5min | Telegram + Email |
| **RedisMemoryHigh** | Redis memória > 90% | 5min | Telegram + Email |
| **MySQLConnectionsHigh** | MySQL conexões > 80% | 5min | Telegram + Email |
| **CeleryTasksFailing** | Tasks Celery falhando | 5min | Telegram + Email |
| **DiskSpaceLowWarning** | Disco < 20% | 10min | Telegram + Email |
| **HighCPUUsage** | CPU > 80% | 10min | Telegram + Email |
| **HighMemoryUsage** | Memória > 90% | 10min | Telegram + Email |
| **LowAvailability** | Disponibilidade < 95% | 5min | Telegram + Email |

**Configuração:** `monitoring/alerts.yml`

---

## 🔔 Notificações

**Telegram:**
- Bot: `@Wallclub_monitor_bot`
- Formato: Emoji + Severidade + Descrição + Status (firing/resolved)

**Email:**
- Destinatário: `jeanpierre.lessa@gmail.com`
- SMTP: AWS SES (email-smtp.us-east-1.amazonaws.com:587)

**Configuração:** `monitoring/alertmanager.yml`

**Credenciais:** Armazenadas em variáveis de ambiente (`.env`)

---

## 📈 Prometheus

**URL:** http://localhost:9090

**Configuração:** `monitoring/prometheus.yml`

**Scrape Interval:** 30 segundos

**Retenção:** 15 dias (padrão)

**Targets monitorados:**
- 4 containers Django (wallclub-portais, apis, pos, riskengine)
- Redis Exporter
- Node Exporter

**Armazenamento:** Volume Docker `prometheus-data`

---

## 🔧 Comandos Úteis

### Subir Monitoramento

```bash
# Subir Prometheus + Alertmanager + Exporters
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d prometheus alertmanager redis-exporter node-exporter

# Verificar status
docker ps --filter "name=wallclub" --format "table {{.Names}}\t{{.Status}}"
```

### Verificar Métricas

```bash
# Testar endpoint /metrics de um container
curl http://localhost:8005/metrics

# Verificar targets no Prometheus
curl http://localhost:9090/api/v1/targets | jq

# Verificar alertas ativos
curl http://localhost:9090/api/v1/alerts | jq
```

### Logs

```bash
# Prometheus
docker logs wallclub-prometheus --tail 50

# Alertmanager
docker logs wallclub-alertmanager --tail 50

# Exporters
docker logs wallclub-redis-exporter --tail 20
docker logs wallclub-node-exporter --tail 20
```

---

## 🏭 Configuração para Produção

### 1. Node Exporter no Servidor de Banco de Dados

**Instalação no servidor MySQL:**

```bash
# 1. Baixar Node Exporter
cd /tmp
wget https://github.com/prometheus/node_exporter/releases/download/v1.7.0/node_exporter-1.7.0.linux-amd64.tar.gz
tar xvfz node_exporter-1.7.0.linux-amd64.tar.gz
sudo mv node_exporter-1.7.0.linux-amd64/node_exporter /usr/local/bin/

# 2. Criar usuário
sudo useradd --no-create-home --shell /bin/false node_exporter

# 3. Criar serviço systemd
sudo tee /etc/systemd/system/node_exporter.service > /dev/null <<EOF
[Unit]
Description=Node Exporter
After=network.target

[Service]
User=node_exporter
Group=node_exporter
Type=simple
ExecStart=/usr/local/bin/node_exporter

[Install]
WantedBy=multi-user.target
EOF

# 4. Iniciar serviço
sudo systemctl daemon-reload
sudo systemctl start node_exporter
sudo systemctl enable node_exporter

# 5. Verificar
curl http://localhost:9100/metrics
```

**Configurar Prometheus para coletar:**

Adicionar em `monitoring/prometheus.yml`:

```yaml
  - job_name: 'mysql-server'
    static_configs:
      - targets: ['<IP_SERVIDOR_MYSQL>:9100']
        labels:
          service: 'mysql-server'
          instance: 'db-server'
    scrape_interval: 30s
```

**Alertas específicos para servidor de banco:**

Adicionar em `monitoring/alerts.yml`:

```yaml
      - alert: DatabaseServerDiskLow
        expr: (node_filesystem_avail_bytes{instance="db-server",mountpoint="/"} / node_filesystem_size_bytes{instance="db-server",mountpoint="/"}) * 100 < 15
        for: 5m
        labels:
          severity: critical
          team: infra
        annotations:
          summary: "Disco do servidor MySQL crítico"
          description: "Servidor de banco de dados tem menos de 15% de espaço disponível."
```

---

### 2. Configuração de Segurança

**Autenticação no Prometheus:**

```yaml
# prometheus.yml
global:
  scrape_interval: 30s

# Adicionar basic auth
scrape_configs:
  - job_name: 'wallclub-portais'
    basic_auth:
      username: 'prometheus'
      password: '<senha_segura>'
```

**Firewall:**

```bash
# Permitir apenas IP do servidor Prometheus
sudo ufw allow from <IP_PROMETHEUS> to any port 9100
sudo ufw allow from <IP_PROMETHEUS> to any port 9121
```

---

### 3. Credenciais em Produção

**Usar AWS Secrets Manager:**

```python
# Exemplo de integração
import boto3
import json

def get_monitoring_credentials():
    client = boto3.client('secretsmanager', region_name='us-east-1')
    secret = client.get_secret_value(SecretId='wallclub/monitoring/credentials')
    return json.loads(secret['SecretString'])

credentials = get_monitoring_credentials()
TELEGRAM_BOT_TOKEN = credentials['telegram_bot_token']
TELEGRAM_CHAT_ID = credentials['telegram_chat_id']
```

---

## 🚀 Evolução Futura

### 1. Aumentar Retenção de Métricas

**Opção A: Aumentar retenção local (até 90 dias)**

Editar `docker-compose.dev.yml`:

```yaml
prometheus:
  command:
    - '--config.file=/etc/prometheus/prometheus.yml'
    - '--storage.tsdb.path=/prometheus'
    - '--storage.tsdb.retention.time=90d'  # 90 dias
    - '--storage.tsdb.retention.size=50GB'  # Limite de 50GB
```

**Custo:** ~50GB de disco para 90 dias de métricas

---

**Opção B: Armazenamento de longo prazo com Thanos (recomendado para produção)**

**Arquitetura:**
```
Prometheus → Thanos Sidecar → S3 (armazenamento infinito)
                ↓
         Thanos Query ← Grafana
```

**Implementação:**

1. **Adicionar Thanos Sidecar:**

```yaml
# docker-compose.yml
thanos-sidecar:
  image: thanosio/thanos:latest
  command:
    - 'sidecar'
    - '--tsdb.path=/prometheus'
    - '--prometheus.url=http://prometheus:9090'
    - '--objstore.config-file=/etc/thanos/bucket.yml'
  volumes:
    - prometheus-data:/prometheus
    - ./monitoring/thanos-bucket.yml:/etc/thanos/bucket.yml
```

2. **Configurar S3:**

```yaml
# monitoring/thanos-bucket.yml
type: S3
config:
  bucket: "wallclub-metrics"
  endpoint: "s3.us-east-1.amazonaws.com"
  region: "us-east-1"
```

3. **Thanos Query:**

```yaml
thanos-query:
  image: thanosio/thanos:latest
  command:
    - 'query'
    - '--http-address=0.0.0.0:9090'
    - '--store=thanos-sidecar:10901'
  ports:
    - "9090:9090"
```

**Benefícios:**
- ✅ Retenção infinita no S3
- ✅ Custo baixo (~$0.023/GB/mês)
- ✅ Queries rápidas (cache local)
- ✅ Downsampling automático (reduz tamanho)

**Custo estimado:**
- 1 ano de métricas: ~200GB → $4.60/mês
- 3 anos de métricas: ~600GB → $13.80/mês

---

### 2. Monitoramento de S3

**Adicionar CloudWatch Exporter:**

```yaml
cloudwatch-exporter:
  image: prom/cloudwatch-exporter:latest
  volumes:
    - ./monitoring/cloudwatch.yml:/config/cloudwatch.yml
  command:
    - '--config.file=/config/cloudwatch.yml'
  ports:
    - "9106:9106"
```

**Configuração:**

```yaml
# monitoring/cloudwatch.yml
region: us-east-1
metrics:
  - aws_namespace: AWS/S3
    aws_metric_name: BucketSizeBytes
    aws_dimensions: [BucketName]
    aws_statistics: [Average]
```

**Alertas S3:**

```yaml
- alert: S3BucketSizeHigh
  expr: aws_s3_bucket_size_bytes > 100e9  # 100GB
  for: 1h
  labels:
    severity: warning
  annotations:
    summary: "Bucket S3 grande"
    description: "Bucket {{ $labels.bucket_name }} tem mais de 100GB."
```

---

### 3. Métricas Customizadas Django

**Adicionar métricas de negócio:**

```python
# monitoring/metrics_view.py
from django.db import connection

def metrics_view(request):
    # Métricas existentes
    metrics = [
        'up 1',
        f'django_db_connection_status {db_status}',
    ]

    # Adicionar métricas de negócio
    with connection.cursor() as cursor:
        # Total de transações hoje
        cursor.execute("SELECT COUNT(*) FROM transacoes WHERE DATE(created_at) = CURDATE()")
        total_transacoes = cursor.fetchone()[0]
        metrics.append(f'wallclub_transacoes_hoje_total {total_transacoes}')

        # Valor total transacionado hoje
        cursor.execute("SELECT COALESCE(SUM(valor), 0) FROM transacoes WHERE DATE(created_at) = CURDATE()")
        valor_total = cursor.fetchone()[0]
        metrics.append(f'wallclub_valor_transacionado_hoje {valor_total}')

    return HttpResponse('\n'.join(metrics), content_type='text/plain')
```

**Alertas de negócio:**

```yaml
- alert: TransacoesZeroHoje
  expr: wallclub_transacoes_hoje_total == 0 and hour() > 10
  for: 30m
  labels:
    severity: warning
  annotations:
    summary: "Nenhuma transação hoje"
    description: "Não houve transações após 10h da manhã."
```

---

### 4. Dashboards Avançados

**Grafana Cloud (opção gerenciada):**
- Sem necessidade de manter Grafana local
- Dashboards prontos para Prometheus
- Alertas integrados
- Custo: Free até 10k séries métricas

**Dashboards customizados:**
- Transações por hora/dia
- Taxa de aprovação de transações
- Latência P50/P95/P99
- Erros por endpoint
- Uso de recursos por container

---

## 📦 Estrutura de Arquivos

```
monitoring/
├── README.md                           # Esta documentação
├── __init__.py                         # Módulo Python
├── health_checks.py                    # Health checks Django
├── metrics_view.py                     # View /metrics customizada
├── urls.py                             # URLs de monitoramento
├── prometheus.yml                      # Config Prometheus
├── alerts.yml                          # Regras de alertas
├── alertmanager.yml                    # Config Alertmanager
└── grafana/provisioning/               # Configs Grafana (opcional)
    ├── datasources/prometheus.yml
    └── alerting/
        ├── contact-points.yml
        └── notification-policies.yml
```

---

## 📝 Notas Importantes

- **Desenvolvimento:** Grafana desabilitado (não essencial)
- **Produção:** Configurar autenticação em Prometheus/Grafana
- **Credenciais:** Migrar para AWS Secrets Manager
- **Retenção:** 15 dias local, expandir com Thanos se necessário
- **Custos:** S3 para métricas ~$5-15/mês dependendo da retenção

---

**Última Atualização:** 31/01/2026
**Versão:** 2.0
**Status:** Sistema core implementado e funcionando
