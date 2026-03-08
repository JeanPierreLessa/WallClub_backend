# MAPA COMPLETO DA INFRAESTRUTURA AWS - WALLCLUB

**Data da Análise:** 08/03/2026
**Região:** us-east-1
**VPC:** vpc-0de4282590e373430 (10.0.0.0/16 - private-vpc)

---

## 📊 VISÃO GERAL

### Instâncias EC2 (4 total)

| Nome | Instance ID | Tipo | IP Privado | IP Público | Status | Função |
|------|-------------|------|------------|------------|--------|--------|
| **python-nginx** | i-0887d8da277afe122 | t2.medium | 10.0.1.124 | - | running | **Aplicação Principal** |
| **mysql-prd** | i-0010bfc2561c63c61 | t2.medium | 10.0.1.107 | - | running | **Banco de Dados** |
| **vpn-server** | i-047962144c571fdbf | t2.medium | 10.0.0.243 | 44.214.49.0 | running | **VPN/Bastion** |
| vpn2 | i-02f8bb9d5a9be9fd1 | t2.medium | 10.0.0.61 | 54.84.47.159 | stopped | VPN Backup (desligada) |

---

## 🏗️ ARQUITETURA DE REDE

### VPC: private-vpc (10.0.0.0/16)

```
┌─────────────────────────────────────────────────────────────────┐
│                    VPC: 10.0.0.0/16 (private-vpc)               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────┐         ┌─────────────────────┐      │
│  │  AZ: us-east-1a     │         │  AZ: us-east-1b     │      │
│  ├─────────────────────┤         ├─────────────────────┤      │
│  │                     │         │                     │      │
│  │ Public Subnet       │         │ Public Subnet       │      │
│  │ 10.0.0.0/24         │         │ 10.0.3.0/24         │      │
│  │ - VPN (10.0.0.243)  │         │                     │      │
│  │                     │         │                     │      │
│  ├─────────────────────┤         ├─────────────────────┤      │
│  │                     │         │                     │      │
│  │ Private Subnet      │         │ Private Subnet      │      │
│  │ 10.0.1.0/24         │         │ 10.0.2.0/24         │      │
│  │ - App (10.0.1.124)  │         │                     │      │
│  │ - MySQL (10.0.1.107)│         │                     │      │
│  │                     │         │                     │      │
│  └─────────────────────┘         └─────────────────────┘      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Subnets

| Subnet ID | CIDR | AZ | Tipo | Recursos |
|-----------|------|----|----|----------|
| subnet-03bb7c28932d7e5ba | 10.0.0.0/24 | us-east-1a | Public | VPN Server |
| subnet-04477cc2fe05f06d0 | 10.0.1.0/24 | us-east-1a | Private | App + MySQL |
| subnet-0edbb2cc519eb6c24 | 10.0.3.0/24 | us-east-1b | Public | - |
| subnet-09305765f7a765011 | 10.0.2.0/24 | us-east-1b | Private | - |

---

## 🔒 SECURITY GROUPS

| Group ID | Nome | Descrição | Uso |
|----------|------|-----------|-----|
| sg-089ad6fe45dff742e | django_server | Servidor novo do Django | **App Principal** |
| sg-07b7717cda1a835e5 | php-mysql-ssh | Allow SSH/http/mysql | **App Principal** |
| sg-0b6470a6b0b89fa7e | mysql-prd | mysql instance | MySQL |
| sg-098369c704033a8f4 | ipsec | ipsec ports | VPN |
| sg-0bc9c8a632c3cb2e5 | ssh-proxy | ssh proxy to server | VPN |
| sg-0b25ec38a73f7d871 | http-https | web balancer | Load Balancer |

---

## ⚖️ LOAD BALANCERS

### Application Load Balancers (3 ativos)

| Nome | DNS | Tipo | Scheme | Target Group | Status |
|------|-----|------|--------|--------------|--------|
| **python-nginx** | python-nginx-1059793183.us-east-1.amazonaws.com | application | internet-facing | python-nginx (HTTP:8005) | ✅ Ativo |
| ~~php-server~~ | ~~php-server-757864010.us-east-1.elb.amazonaws.com~~ | ~~application~~ | ~~internet-facing~~ | ~~prd-php-mysql (HTTP:80)~~ | ❌ **DELETADO (08/03)** |
| monitor | monitor-1125181423.us-east-1.elb.amazonaws.com | application | internet-facing | uptime-kuma (HTTP:80) | ⚠️ Verificar uso |
| mysql-prd | mysql-prd-b539514470b84713.elb.us-east-1.amazonaws.com | network | internet-facing | mysql-prd (TCP:3306) | ✅ Ativo |

### Target Groups

| Nome | Protocol | Port | Target | Health Status |
|------|----------|------|--------|---------------|
| **python-nginx** | HTTP | 8005 | i-0887d8da277afe122 | ✅ healthy |
| prd-php-mysql | HTTP | 80 | - | - |
| uptime-kuma | HTTP | 80 | - | - |
| mysql-prd | TCP | 3306 | i-0010bfc2561c63c61 | - |

---

## 💾 ARMAZENAMENTO

### Instância de Aplicação (python-nginx)

| Recurso | Detalhes |
|---------|----------|
| **Volume EBS** | vol-00e1943a595cb9495 |
| **Tipo** | gp3 (SSD) |
| **Tamanho** | 50GB |
| **Uso** | 28GB (58%) |
| **Disponível** | 21GB |

### Distribuição de Espaço

```
/var/www/WallClub_backend: 344MB (código)
/var/lib/docker: ~15GB (imagens + volumes)
Logs Django: 260MB
Media Django: 13MB
Sistema: ~12GB
```

---

## 🐳 CONTAINERS DOCKER (Aplicação)

### 14 Containers Ativos

| Container | Imagem | Memória | Criticidade |
|-----------|--------|---------|-------------|
| **wallclub-apis** | wallclub_backend-wallclub-apis | 353MB | 🔴 Alta |
| **wallclub-pos** | wallclub_backend-wallclub-pos | 169MB | 🔴 Alta |
| **wallclub-portais** | wallclub_backend-wallclub-portais | 289MB | 🟡 Média |
| **wallclub-riskengine** | wallclub_backend-wallclub-riskengine | 202MB | 🟡 Média |
| **wallclub-celery-worker** | wallclub_backend-wallclub-celery-worker | 368MB | 🔴 Alta |
| **wallclub-celery-beat** | wallclub_backend-wallclub-celery-beat | 114MB | 🟢 Baixa |
| **nginx** | wallclub_backend-nginx | 7MB | 🔴 Alta |
| **wallclub-redis** | redis:7-alpine | 9MB | 🔴 Alta |
| **wallclub-grafana** | grafana/grafana:latest | 239MB | 🟢 Baixa |
| **wallclub-prometheus** | prom/prometheus:latest | 81MB | 🟢 Baixa |
| **wallclub-alertmanager** | prom/alertmanager:latest | 13MB | 🟢 Baixa |
| **wallclub-flower** | wallclub_backend-flower | 48MB | 🟢 Baixa |
| **wallclub-redis-exporter** | oliver006/redis_exporter:latest | 9MB | 🟢 Baixa |
| **wallclub-node-exporter** | prom/node-exporter:latest | 15MB | 🟢 Baixa |

**Total RAM:** ~1.9GB (de 3.8GB disponível = 50% após otimizações)

---

## 🔌 CONECTIVIDADE

### Fluxo de Acesso

```
Internet
    │
    ▼
ALB: python-nginx (python-nginx-1059793183.us-east-1.amazonaws.com)
    │
    ▼
Target Group: python-nginx (HTTP:8005)
    │
    ▼
EC2: python-nginx (10.0.1.124)
    │
    ├─► Nginx Gateway (porta 8005)
    │       │
    │       ├─► wallclub-apis (8007)
    │       ├─► wallclub-pos (8006)
    │       ├─► wallclub-portais (8005)
    │       └─► wallclub-riskengine (8008)
    │
    └─► MySQL (10.0.1.107:3306)
```

### Acesso SSH

```
SSH → VPN Server (44.214.49.0)
         │
         ├─► App (10.0.1.124) via VPN
         └─► MySQL (10.0.1.107) via VPN
```

---

## 💰 CUSTOS ESTIMADOS (Mensal)

| Recurso | Tipo | Quantidade | Custo Unitário | Total |
|---------|------|------------|----------------|-------|
| EC2 t2.medium | App | 1 | ~R$ 400 | R$ 400 |
| EC2 t2.medium | MySQL | 1 | ~R$ 400 | R$ 400 |
| EC2 t2.medium | VPN | 1 | ~R$ 400 | R$ 400 |
| EBS gp3 50GB | Storage | 1 | ~R$ 50 | R$ 50 |
| ALB | Load Balancer | ~~4~~ **3** | ~R$ 60 | ~~R$ 240~~ **R$ 180** |
| Data Transfer | Rede | - | - | ~R$ 100 |
| **TOTAL ANTERIOR** | | | | ~~R$ 1.590/mês~~ |
| **TOTAL ATUAL** | | | | **~R$ 1.530/mês** |
| **ECONOMIA (08/03)** | | | | **-R$ 60/mês** ✅ |

---

## ⚠️ PONTOS DE ATENÇÃO

### Recursos Subutilizados
- ❌ **vpn2** (i-02f8bb9d5a9be9fd1) - Instância parada, pode ser terminada
- ⚠️ **Subnet us-east-1b** - Sem recursos ativos, pode ser removida

### Oportunidades de Otimização
1. 🟢 **Remover vpn2** (economia: ~R$ 400/mês)
2. 🟢 **Consolidar ALBs** - 4 ALBs podem ser reduzidos
3. 🟡 **Limpar imagens Docker antigas** - Liberar ~10GB de disco
4. 🟡 **Implementar backup S3** - Atualmente sem backup automatizado

### Riscos Identificados
- 🔴 **Single Point of Failure:** MySQL em instância única (sem Multi-AZ)
- 🔴 **Sem Backup Automatizado:** Banco de dados sem backup S3
- 🟡 **Aplicação em AZ única:** Sem redundância geográfica

---

## � DESPERDÍCIOS IDENTIFICADOS

### Crítico - Recursos Pagos Sem Uso

#### 1. **Instância vpn2 Parada** (i-02f8bb9d5a9be9fd1)
- **Status:** Stopped desde 29/01/2026
- **Custo:** ~R$ 50-65/mês (volume EBS + IP elástico)
- **Problema:** Instância parada AINDA COBRA pelo volume anexado
- **Ação:** ❌ TERMINAR IMEDIATAMENTE
```bash
aws ec2 terminate-instances --instance-ids i-02f8bb9d5a9be9fd1
```

#### 2. **Load Balancer "prd-php-mysql" Vazio** ✅ DELETADO (08/03/2026)
- **ARN:** arn:aws:elasticloadbalancing:us-east-1:528757796910:loadbalancer/app/php-server/80d1a738c60ec0b4
- **Status:** ~~Rodando desde 12/04/2025~~ → **DELETADO**
- **Economia:** R$ 60/mês
- **Backup:** `docs/infraestrutura/backup_alb_php-server.json`

#### 3. **Load Balancer "monitor" (uptime-kuma)**
- **ARN:** arn:aws:elasticloadbalancing:us-east-1:528757796910:loadbalancer/app/monitor/8a49493f4f22479b
- **Status:** Rodando desde 24/04/2025
- **Custo:** ~R$ 60/mês
- **Problema:** Verificar se ainda está em uso
- **Ação:** ⚠️ VERIFICAR E DELETAR SE NÃO USA
```bash
# Verificar targets primeiro
aws elbv2 describe-target-health --target-group-arn <arn-do-target-group>
# Se não usa, deletar
aws elbv2 delete-load-balancer --load-balancer-arn arn:aws:elasticloadbalancing:us-east-1:528757796910:loadbalancer/app/monitor/8a49493f4f22479b
```

#### 4. **9 Snapshots Antigos (Mai-Nov 2025)**
- **Custo:** ~R$ 0.05/GB/mês × 450GB = ~R$ 22/mês
- **Problema:** Snapshots de AMIs antigas que provavelmente não usa mais
- **Ação:** 🟡 MANTER APENAS OS 2-3 MAIS RECENTES
```bash
# Deletar snapshots antigos (exemplo)
aws ec2 delete-snapshot --snapshot-id snap-06d0a80e88b34bba5
aws ec2 delete-snapshot --snapshot-id snap-0c1fd2a9286e077bf
aws ec2 delete-snapshot --snapshot-id snap-02c69cfee62250143
aws ec2 delete-snapshot --snapshot-id snap-0a4b42ee1cb25be9c
aws ec2 delete-snapshot --snapshot-id snap-09d17b17e52f7556d
aws ec2 delete-snapshot --snapshot-id snap-0134d35e8281b6c0c
aws ec2 delete-snapshot --snapshot-id snap-03663063224f19c57
# Manter: snap-0fee5e0d5cbac3a5d (Nov 2025) e snap-0b1f9d1e6eb25dc57 (mais recente)
```

### Médio - Configurações Subótimas

#### 5. **Imagens Docker Antigas na Aplicação**
- **Problema:** ~15GB de imagens não utilizadas
- **Impacto:** Ocupa espaço em disco (58% usado)
- **Ação:** 🟢 LIMPAR
```bash
ssh -i /Users/jeanlessa/wall_projects/aws/webserver-dev.pem ubuntu@10.0.1.124
docker system prune -a --volumes --force
```

---

## 💰 PLANO DE ECONOMIA IMEDIATA

### Resumo de Economia Possível

| # | Ação | Economia Mensal | Esforço | Status |
|---|------|-----------------|---------|--------|
| 1 | Terminar vpn2 | R$ 50-65 | 2 min | ⏳ Pendente |
| 2 | Deletar ALB "prd-php-mysql" | R$ 60 | 2 min | ✅ **FEITO (08/03)** |
| 3 | Deletar ALB "monitor" (se não usa) | R$ 60 | 2 min | ⏳ Pendente |
| 4 | Limpar 7 snapshots antigos | R$ 15-20 | 5 min | ⏳ Pendente |
| 5 | Limpar imagens Docker | R$ 0 (libera 10GB) | 5 min | ⏳ Pendente |
| **TOTAL POSSÍVEL** | | **R$ 185-205/mês** | **15 min** | |
| **ECONOMIZADO ATÉ AGORA** | | **R$ 60/mês** | | ✅ |

### Script de Limpeza Completo

```bash
# ============================================
# ECONOMIA IMEDIATA - EXECUTAR COM CUIDADO
# ============================================

# 1. Terminar vpn2 (economia: R$ 50-65/mês)
aws ec2 terminate-instances --instance-ids i-02f8bb9d5a9be9fd1

# 2. Deletar ALB sem targets (economia: R$ 60/mês)
aws elbv2 delete-load-balancer \
  --load-balancer-arn arn:aws:elasticloadbalancing:us-east-1:528757796910:loadbalancer/app/php-server/80d1a738c60ec0b4

# 3. Verificar e deletar ALB monitor (economia: R$ 60/mês se não usa)
# ANTES: verificar se está sendo usado
aws elbv2 describe-target-health \
  --target-group-arn $(aws elbv2 describe-target-groups --names uptime-kuma --query 'TargetGroups[0].TargetGroupArn' --output text)
# Se não usa, deletar:
# aws elbv2 delete-load-balancer --load-balancer-arn arn:aws:elasticloadbalancing:us-east-1:528757796910:loadbalancer/app/monitor/8a49493f4f22479b

# 4. Deletar snapshots antigos (economia: R$ 15-20/mês)
aws ec2 delete-snapshot --snapshot-id snap-06d0a80e88b34bba5
aws ec2 delete-snapshot --snapshot-id snap-0c1fd2a9286e077bf
aws ec2 delete-snapshot --snapshot-id snap-02c69cfee62250143
aws ec2 delete-snapshot --snapshot-id snap-0a4b42ee1cb25be9c
aws ec2 delete-snapshot --snapshot-id snap-09d17b17e52f7556d
aws ec2 delete-snapshot --snapshot-id snap-0134d35e8281b6c0c
aws ec2 delete-snapshot --snapshot-id snap-03663063224f19c57

# 5. Limpar Docker (libera 10GB de disco)
ssh -i /Users/jeanlessa/wall_projects/aws/webserver-dev.pem ubuntu@10.0.1.124 \
  "docker system prune -a --volumes --force"
```

### Resultado Esperado

**Economia Total:** R$ 185-205/mês
**Com essa economia, você quase paga a Máquina 4 (R$ 250/mês)!**

**Novo Custo Mensal:**
- Atual: R$ 1.590/mês
- Após limpeza: R$ 1.385-1.405/mês
- Com Máquina 4: R$ 1.635-1.655/mês (+R$ 45-65/mês líquido)

---

---

## 🖥️ PROPOSTA: ADICIONAR MÁQUINA 4

### Opções de Implementação

#### **Opção 1: Começar Pequeno (Recomendado)**
**Máquina 4:** t3.small (2GB RAM) - R$ 250/mês

**Fase 1 - Migrar apenas Monitoramento:**
```
- wallclub-grafana (239MB)
- wallclub-prometheus (81MB)
- wallclub-alertmanager (13MB)
Total: ~330MB (16% de 2GB)
```

**Vantagens:**
- ✅ Baixo risco (monitoramento não é crítico)
- ✅ Testa conectividade entre máquinas
- ✅ Sobra espaço para adicionar mais depois
- ✅ Reduz RAM da Máquina 1: 76% → 67%

**Fase 2 - Adicionar Portais (se funcionar bem):**
```
+ wallclub-portais (289MB)
Total: ~620MB (31% de 2GB)
Reduz RAM da Máquina 1: 67% → 59%
```

**Fase 3 - Adicionar RiskEngine + Celery Beat:**
```
+ wallclub-riskengine (202MB)
+ wallclub-celery-beat (114MB)
+ wallclub-flower (48MB)
+ redis-exporter (9MB)
Total: ~995MB (50% de 2GB)
Reduz RAM da Máquina 1: 59% → 24%
```

---

#### **Opção 2: Migração Completa Imediata**
**Máquina 4:** t3.small (2GB RAM) - R$ 250/mês

**Migrar tudo de uma vez:**
```
- wallclub-portais (289MB)
- wallclub-riskengine (202MB)
- wallclub-celery-beat (114MB)
- wallclub-grafana (239MB)
- wallclub-prometheus (81MB)
- wallclub-alertmanager (13MB)
- wallclub-flower (48MB)
- redis-exporter (9MB)
Total: ~995MB (50% de 2GB)
```

**Resultado:**
- Máquina 1: 76% → 24% RAM ✅
- Máquina 4: 50% RAM ✅

---

#### **Opção 3: Máquina Ainda Menor**
**Máquina 4:** t3.micro (1GB RAM) - R$ 80-100/mês

**Migrar apenas:**
```
- wallclub-grafana (239MB)
- wallclub-prometheus (81MB)
- wallclub-alertmanager (13MB)
- wallclub-flower (48MB)
Total: ~380MB (38% de 1GB)
```

**Vantagens:**
- ✅ Custo muito baixo
- ✅ Suficiente para monitoramento
- ❌ Pouco espaço para crescer

---

### Distribuição Final (Opção 1 - Fase 3)

**MÁQUINA 1 (python-nginx - 10.0.1.124)** - Serviços Críticos
```
- wallclub-apis (353MB)
- wallclub-pos (169MB)
- wallclub-celery-worker (368MB)
- nginx (7MB)
- wallclub-redis (9MB)
- node-exporter (15MB)
Total: ~921MB (24% de 3.8GB)
```

**MÁQUINA 4 (NOVA - 10.0.1.125)** - Serviços Não-Críticos
```
- wallclub-portais (289MB)
- wallclub-riskengine (202MB)
- wallclub-celery-beat (114MB)
- wallclub-grafana (239MB)
- wallclub-prometheus (81MB)
- wallclub-alertmanager (13MB)
- wallclub-flower (48MB)
- redis-exporter (9MB)
Total: ~995MB (50% de 2GB)
```

### Benefícios
- ✅ Reduz pressão de RAM na máquina principal (76% → 24%)
- ✅ Isolamento de serviços críticos vs não-críticos
- ✅ Facilita troubleshooting e manutenção
- ✅ Migração gradual e segura (3 fases)
- ✅ Custo adicional baixo (+R$ 250/mês)
- ✅ Preparação para crescimento futuro

### Plano Detalhado
📄 Ver: `docs/infraestrutura/PLANO_MAQUINA_4.md`

---

**Última Atualização:** 08/03/2026 07:40 BRT
