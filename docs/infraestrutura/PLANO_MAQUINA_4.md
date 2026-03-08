# Plano de Implementação - Máquina 4 (Serviços Não-Críticos)

**Data:** 08/03/2026
**Objetivo:** Distribuir serviços em 2 máquinas para reduzir pressão de RAM e isolar serviços críticos

---

## 📊 Situação Atual

### Máquina 1 (python-nginx - 10.0.1.124)
- **Tipo:** t2.medium (3.8GB RAM, 2 vCPU)
- **Uso RAM:** 76% (~2.9GB de 3.8GB)
- **Problema:** Alta pressão de memória, risco de OOM
- **Containers:** 14 ativos

### Distribuição Atual de RAM:
```
wallclub-apis:           353MB  (crítico)
wallclub-celery-worker:  368MB  (crítico)
wallclub-portais:        289MB  (não-crítico)
wallclub-pos:            169MB  (crítico)
wallclub-grafana:        239MB  (não-crítico)
wallclub-riskengine:     202MB  (não-crítico)
wallclub-celery-beat:    114MB  (não-crítico)
wallclub-prometheus:      81MB  (não-crítico)
wallclub-flower:          48MB  (não-crítico)
nginx:                     7MB  (crítico)
redis:                     9MB  (crítico)
node-exporter:            15MB  (crítico)
alertmanager:             13MB  (não-crítico)
redis-exporter:            9MB  (não-crítico)
```

---

## 🎯 Arquitetura Proposta

### MÁQUINA 1 (10.0.1.124) - Serviços Críticos
**Manter:**
```
- wallclub-apis (353MB)          # Checkout + Mobile
- wallclub-pos (169MB)           # Terminal POS
- wallclub-celery-worker (368MB) # Tasks assíncronas
- nginx (7MB)                    # Gateway
- redis (9MB)                    # Cache + Celery broker
- node-exporter (15MB)           # Métricas da máquina
```

**Total:** ~921MB (24% de 3.8GB) ✅

---

### MÁQUINA 4 (10.0.1.125) - Serviços Não-Críticos
**Criar nova:**

**Especificações:**
- **Tipo:** t3.small (2GB RAM, 2 vCPU)
- **Disco:** 20GB gp3
- **Subnet:** subnet-04477cc2fe05f06d0 (10.0.1.0/24 - mesma da app)
- **Security Groups:** sg-089ad6fe45dff742e (django_server)
- **Custo:** ~R$ 250/mês

**Serviços:**
```
- wallclub-portais (289MB)       # Admin + Vendas + Lojista
- wallclub-riskengine (202MB)    # Antifraude
- wallclub-celery-beat (114MB)   # Scheduler Celery
- wallclub-grafana (239MB)       # Dashboards
- wallclub-prometheus (81MB)     # Métricas
- wallclub-alertmanager (13MB)   # Alertas
- wallclub-flower (48MB)         # Monitor Celery
- redis-exporter (9MB)           # Métricas Redis
```

**Total:** ~995MB (50% de 2GB) ✅

---

## 📋 Plano de Implementação (6-8 horas)

### Fase 1: Criar Máquina 4 (1h)

#### 1.1 Criar EC2
```bash
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t3.small \
  --key-name webserver-dev \
  --subnet-id subnet-04477cc2fe05f06d0 \
  --security-group-ids sg-089ad6fe45dff742e \
  --private-ip-address 10.0.1.125 \
  --block-device-mappings '[
    {
      "DeviceName": "/dev/sda1",
      "Ebs": {
        "VolumeSize": 20,
        "VolumeType": "gp3",
        "DeleteOnTermination": true
      }
    }
  ]' \
  --tag-specifications 'ResourceType=instance,Tags=[
    {Key=Name,Value=python-nginx-secundario},
    {Key=Ambiente,Value=producao},
    {Key=Tipo,Value=servicos-nao-criticos}
  ]'
```

#### 1.2 Configurar Sistema Base
```bash
# Conectar via VPN
ssh -i /Users/jeanlessa/wall_projects/aws/webserver-dev.pem ubuntu@10.0.1.125

# Atualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Docker
sudo apt install docker.io docker-compose -y
sudo usermod -aG docker ubuntu

# Instalar utilitários
sudo apt install htop vim git -y
```

---

### Fase 2: Clonar Repositório e Configurar (1h)

```bash
# Clonar código
cd /var/www
sudo git clone https://github.com/seu-repo/WallClub_backend.git
cd WallClub_backend
sudo git checkout release/2.2.3

# Ajustar permissões
sudo chown -R ubuntu:ubuntu /var/www/WallClub_backend

# Copiar .env da Máquina 1
scp ubuntu@10.0.1.124:/var/www/WallClub_backend/services/django/.env \
    /var/www/WallClub_backend/services/django/.env

scp ubuntu@10.0.1.124:/var/www/WallClub_backend/services/riskengine/.env \
    /var/www/WallClub_backend/services/riskengine/.env
```

#### Ajustar .env para apontar para Máquina 1
```bash
# services/django/.env
DB_HOST=10.0.1.107        # MySQL (não muda)
REDIS_HOST=10.0.1.124     # Redis na Máquina 1
CELERY_BROKER_URL=redis://10.0.1.124:6379/0
```

---

### Fase 3: Criar docker-compose-secundario.yml (30min)

```yaml
# /var/www/WallClub_backend/docker-compose-secundario.yml
version: '3.8'

services:
  wallclub-portais:
    build:
      context: .
      dockerfile: Dockerfile.portais
    container_name: wallclub-portais
    restart: unless-stopped
    ports:
      - "8005:8005"
    volumes:
      - ./services/django:/app
      - django_code:/app/code
    environment:
      - DB_HOST=10.0.1.107
      - REDIS_HOST=10.0.1.124
    networks:
      - wallclub-network
    deploy:
      resources:
        limits:
          memory: 350M
        reservations:
          memory: 250M

  wallclub-riskengine:
    build:
      context: .
      dockerfile: Dockerfile.riskengine
    container_name: wallclub-riskengine
    restart: unless-stopped
    ports:
      - "8008:8008"
    volumes:
      - ./services/riskengine:/app
    environment:
      - DB_HOST=10.0.1.107
      - REDIS_HOST=10.0.1.124
    networks:
      - wallclub-network
    deploy:
      resources:
        limits:
          memory: 250M
        reservations:
          memory: 150M

  wallclub-celery-beat:
    build:
      context: .
      dockerfile: Dockerfile.portais
    container_name: wallclub-celery-beat
    restart: unless-stopped
    command: celery -A wallclub beat -l info
    volumes:
      - ./services/django:/app
    environment:
      - DB_HOST=10.0.1.107
      - REDIS_HOST=10.0.1.124
      - CELERY_BROKER_URL=redis://10.0.1.124:6379/0
    networks:
      - wallclub-network
    deploy:
      resources:
        limits:
          memory: 150M
        reservations:
          memory: 100M

  wallclub-grafana:
    image: grafana/grafana:latest
    container_name: wallclub-grafana
    restart: unless-stopped
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
      - GF_SERVER_ROOT_URL=https://monitor.wallclub.com.br
    networks:
      - wallclub-network
    deploy:
      resources:
        limits:
          memory: 300M
        reservations:
          memory: 200M

  wallclub-prometheus:
    image: prom/prometheus:latest
    container_name: wallclub-prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    networks:
      - wallclub-network
    deploy:
      resources:
        limits:
          memory: 150M
        reservations:
          memory: 80M

  wallclub-alertmanager:
    image: prom/alertmanager:latest
    container_name: wallclub-alertmanager
    restart: unless-stopped
    ports:
      - "9093:9093"
    volumes:
      - ./monitoring/alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml
      - alertmanager-data:/alertmanager
    networks:
      - wallclub-network
    deploy:
      resources:
        limits:
          memory: 50M
        reservations:
          memory: 20M

  wallclub-flower:
    build:
      context: .
      dockerfile: Dockerfile.flower
    container_name: wallclub-flower
    restart: unless-stopped
    ports:
      - "5555:5555"
    environment:
      - CELERY_BROKER_URL=redis://10.0.1.124:6379/0
    networks:
      - wallclub-network
    deploy:
      resources:
        limits:
          memory: 80M
        reservations:
          memory: 50M

  wallclub-redis-exporter:
    image: oliver006/redis_exporter:latest
    container_name: wallclub-redis-exporter
    restart: unless-stopped
    ports:
      - "9121:9121"
    environment:
      - REDIS_ADDR=10.0.1.124:6379
    networks:
      - wallclub-network
    deploy:
      resources:
        limits:
          memory: 20M
        reservations:
          memory: 10M

volumes:
  django_code:
  grafana-data:
  prometheus-data:
  alertmanager-data:

networks:
  wallclub-network:
    driver: bridge
```

---

### Fase 4: Ajustar Prometheus para Monitorar Ambas Máquinas (30min)

```yaml
# monitoring/prometheus/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  # Máquina 1 (Críticos)
  - job_name: 'wallclub-apis'
    static_configs:
      - targets: ['10.0.1.124:8007']

  - job_name: 'wallclub-pos'
    static_configs:
      - targets: ['10.0.1.124:8006']

  - job_name: 'node-exporter-maq1'
    static_configs:
      - targets: ['10.0.1.124:9100']

  # Máquina 4 (Não-Críticos)
  - job_name: 'wallclub-portais'
    static_configs:
      - targets: ['10.0.1.125:8005']

  - job_name: 'wallclub-riskengine'
    static_configs:
      - targets: ['10.0.1.125:8008']

  - job_name: 'redis-exporter'
    static_configs:
      - targets: ['10.0.1.125:9121']
```

---

### Fase 5: Migração Gradual (2-3h)

#### 5.1 Subir Serviços na Máquina 4
```bash
# Na Máquina 4
cd /var/www/WallClub_backend
docker-compose -f docker-compose-secundario.yml build
docker-compose -f docker-compose-secundario.yml up -d
```

#### 5.2 Validar Serviços
```bash
# Verificar containers
docker ps

# Verificar logs
docker logs wallclub-portais --tail 50
docker logs wallclub-grafana --tail 50
docker logs wallclub-prometheus --tail 50

# Testar conectividade com MySQL
docker exec wallclub-portais python manage.py check

# Testar conectividade com Redis
docker exec wallclub-portais python -c "import redis; r = redis.Redis(host='10.0.1.124', port=6379); print(r.ping())"
```

#### 5.3 Parar Serviços na Máquina 1
```bash
# Na Máquina 1
docker stop wallclub-portais
docker stop wallclub-riskengine
docker stop wallclub-celery-beat
docker stop wallclub-grafana
docker stop wallclub-prometheus
docker stop wallclub-alertmanager
docker stop wallclub-flower
docker stop wallclub-redis-exporter
```

#### 5.4 Atualizar docker-compose.yml da Máquina 1
```bash
# Comentar/remover serviços migrados
# Manter apenas: apis, pos, celery-worker, nginx, redis, node-exporter
```

---

### Fase 6: Validação Final (1h)

#### 6.1 Testes de Conectividade
```bash
# Da Máquina 4 para Máquina 1
ping 10.0.1.124
telnet 10.0.1.124 6379  # Redis
telnet 10.0.1.107 3306  # MySQL

# Da Máquina 1 para Máquina 4
ping 10.0.1.125
curl http://10.0.1.125:8005/health  # Portais
curl http://10.0.1.125:3000         # Grafana
```

#### 6.2 Testes Funcionais
```bash
# Acessar Portal Lojista
curl -I https://lojista.wallclub.com.br

# Verificar Grafana
curl -I https://monitor.wallclub.com.br

# Verificar Celery Beat está agendando tasks
docker logs wallclub-celery-beat --tail 20
```

#### 6.3 Monitoramento
```bash
# Verificar uso de RAM
# Máquina 1
ssh ubuntu@10.0.1.124 "free -h"

# Máquina 4
ssh ubuntu@10.0.1.125 "free -h"

# Verificar métricas no Prometheus
curl http://10.0.1.125:9090/api/v1/targets
```

---

### Fase 7: Atualizar Load Balancer (30min)

#### 7.1 Adicionar Máquina 4 ao Target Group (se necessário)
```bash
# Se portais precisar ser acessível externamente
aws elbv2 register-targets \
  --target-group-arn arn:aws:elasticloadbalancing:us-east-1:528757796910:targetgroup/python-nginx/xxx \
  --targets Id=i-<INSTANCE_ID_MAQ4>,Port=8005
```

---

## 📊 Resultado Esperado

### Antes (Máquina 1 única):
```
RAM: 2.9GB / 3.8GB (76%)
Containers: 14
Risco: Alto (OOM)
```

### Depois (2 Máquinas):

**Máquina 1 (Críticos):**
```
RAM: 0.9GB / 3.8GB (24%)
Containers: 6
Risco: Baixo
```

**Máquina 4 (Não-Críticos):**
```
RAM: 1.0GB / 2.0GB (50%)
Containers: 8
Risco: Baixo
```

---

## 💰 Impacto Financeiro

| Item | Antes | Depois | Diferença |
|------|-------|--------|-----------|
| Máquina 1 | R$ 400 | R$ 400 | - |
| Máquina 4 | - | R$ 250 | +R$ 250 |
| **Total** | **R$ 400** | **R$ 650** | **+R$ 250** |

**Com economia de ALB deletado:** +R$ 190/mês líquido

---

## ⚠️ Pontos de Atenção

### 1. Latência de Rede
- Comunicação entre máquinas: <1ms (mesma subnet)
- Queries MySQL: +0.5-1ms por query
- **Impacto:** Mínimo para serviços não-críticos

### 2. Celery Beat
- Scheduler roda na Máquina 4
- Workers rodam na Máquina 1
- **Importante:** Garantir conectividade Redis estável

### 3. Grafana
- Precisa acessar Prometheus (mesma máquina)
- Precisa acessar métricas da Máquina 1
- **Configurar:** Datasources apontando para IPs corretos

### 4. Backup
- Máquina 1: Backup completo (tem dados críticos)
- Máquina 4: Apenas código (stateless)

---

## 🔄 Plano de Rollback

Se algo der errado:

```bash
# 1. Parar serviços na Máquina 4
ssh ubuntu@10.0.1.125
cd /var/www/WallClub_backend
docker-compose -f docker-compose-secundario.yml down

# 2. Religar serviços na Máquina 1
ssh ubuntu@10.0.1.124
cd /var/www/WallClub_backend
docker-compose up -d

# 3. Verificar tudo voltou ao normal
docker ps
curl http://localhost:8005/health
```

**Tempo de rollback:** 5-10 minutos

---

## 📅 Cronograma Sugerido

**Melhor horário:** Madrugada (02:00-06:00) ou fim de semana

**Duração total:** 6-8 horas

| Fase | Duração | Horário Sugerido |
|------|---------|------------------|
| 1. Criar Máquina 4 | 1h | 02:00-03:00 |
| 2. Clonar e Configurar | 1h | 03:00-04:00 |
| 3. Docker Compose | 30min | 04:00-04:30 |
| 4. Ajustar Prometheus | 30min | 04:30-05:00 |
| 5. Migração | 2-3h | 05:00-08:00 |
| 6. Validação | 1h | 08:00-09:00 |
| 7. Load Balancer | 30min | 09:00-09:30 |

---

## ✅ Checklist de Execução

### Pré-Migração
- [ ] Backup completo do banco de dados
- [ ] Backup dos .env files
- [ ] Documentar IPs e portas atuais
- [ ] Avisar equipe sobre manutenção

### Durante Migração
- [ ] Criar Máquina 4 na AWS
- [ ] Configurar sistema base
- [ ] Clonar repositório
- [ ] Configurar .env files
- [ ] Criar docker-compose-secundario.yml
- [ ] Build das imagens
- [ ] Subir containers
- [ ] Validar conectividade
- [ ] Parar serviços na Máquina 1
- [ ] Atualizar Prometheus

### Pós-Migração
- [ ] Testar Portal Lojista
- [ ] Testar Grafana
- [ ] Verificar Celery Beat
- [ ] Monitorar RAM de ambas máquinas
- [ ] Verificar logs por 24h
- [ ] Atualizar documentação

---

**Última Atualização:** 08/03/2026
