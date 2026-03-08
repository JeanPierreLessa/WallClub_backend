# ROADMAP DE EVOLUÇÃO - INFRAESTRUTURA WALLCLUB

**Versão:** 1.2
**Data:** 31/01/2026
**Base Atual:** R$ 1.500/mês | ~5 transações/dia (Processo 1: POS+App)
**Objetivo:** Evolução incremental baseada em volume e necessidade

**Nota sobre Volumetria:**
- **Processo 1 (transactiondata_pos):** POS + App + Checkout - Sistema core tempo real (~5 trans/dia atual)
- **Processo 2 (base_transacoes_unificadas):** Portais - Consultas/cargas batch (~1.938 trans/dia)
- **Referência para gatilhos:** Processo 1 (impacto crítico na infraestrutura)

---

## 📊 VISÃO GERAL

| Step | Nome | Prazo | Esforço | Custo Total | Δ Custo | Gatilho |
|------|------|-------|---------|-------------|---------|---------|
| **0** | **Atual** | - | - | **R$ 1.500** | - | - |
| **1** | Segurança Crítica | 1 mês | 26h | **R$ 1.500** | R$ 0 | Imediato |
| **2** | Observabilidade | 1 mês | 24h | **R$ 1.600** | +R$ 100 | Após Step 1 |
| **3** | Backup Robusto | 2 semanas | 16h | **R$ 1.650** | +R$ 50 | Após Step 2 |
| **4** | Desacoplamento | 3 meses | 68h | **R$ 1.650** | R$ 0 | >50 trans/dia |
| **5** | BD Gerenciado | 1 mês | 32h | **R$ 2.550** | +R$ 900 | >200 trans/dia |
| **6** | Kubernetes Prep | 2 meses | 60h | **R$ 2.650** | +R$ 100 | >500 trans/dia |
| **7** | Kubernetes Deploy | 2 meses | 80h | **R$ 3.400** | +R$ 750 | Após Step 6 |
| **8** | Auto-scaling | 1 mês | 32h | **R$ 3.600** | +R$ 200 | Após Step 7 |
| **9** | Multi-AZ | 1 mês | 40h | **R$ 5.400** | +R$ 1.800 | >2k trans/dia |
| **10** | Microserviços | 6 meses | 160h | **R$ 6.100** | +R$ 700 | SLA 99.9% |

---

## 🎯 STEP 0: SITUAÇÃO ATUAL

### Infraestrutura
```
├── Servidor EC2 (MySQL + aplicação)
├── Disco local (não gerenciado)
├── Backup manual/script
├── 9 containers Docker Compose
└── Nginx gateway
```

### Custos
- **Total:** R$ 1.500/mês
- **Componentes:** EC2 + storage + rede

### Volume Atual (Jan/2026)
**Processo 1 (Core - transactiondata_pos):**
- Média: ~5 transações/dia
- Pico: ~11 transações/dia (dez/2025)
- Crescimento: +235% (ago→dez 2025)

**Processo 2 (Portais - base_transacoes_unificadas):**
- Média: ~1.938 transações/dia
- Volume alto mas impacto baixo (consultas)

### Riscos Identificados
- 🔴 3 vulnerabilidades críticas de segurança
- 🟠 MySQL em disco local (risco de perda)
- 🟠 Sem monitoramento proativo
- 🟡 Backup não testado regularmente

---

## 🔒 STEP 1: SEGURANÇA CRÍTICA

### Objetivo
Corrigir 3 vulnerabilidades críticas identificadas no documento de arquitetura

### Prazo
**1 mês** (pode ser paralelizado)

### Esforço
**26 horas**

### Ações
```
✅ Remover Endpoint Deprecated (2h)
├── Remover endpoint validar_senha_e_saldo (deprecated)
├── Atualizar documentação de APIs
└── Validar que nenhum cliente usa o endpoint

✅ Rate Limiting Endpoints POS Críticos (4h)
├── Rate limit por terminal em endpoints sensíveis
├── Rate limit por IP: 100 req/min (geral)
├── Auditoria de tentativas falhas
└── Alertas para comportamento suspeito

✅ Gerenciamento Cartões Tokenizados (12h)
├── Interface Portal Vendas: /portal_vendas/cliente/{id}/cartoes/
├── Invalidação automática após 5 tentativas falhas
├── Campos: tentativas_falhas_consecutivas, motivo_invalidacao
└── API REST para invalidação

✅ 2FA App Mobile (8h)
├── Implementar 2FA no login mobile
├── Gatilhos: novo dispositivo, transação >R$ 100
├── Revalidação celular a cada 90 dias
└── Dispositivo confiável (30 dias)
```

### Custos
- **Infraestrutura:** R$ 0 (sem mudança)
- **Total:** **R$ 1.500/mês**

### Entregáveis
- ✅ 3 vulnerabilidades corrigidas
- ✅ Sistema mais seguro
- ✅ Auditoria completa de acessos

### Gatilho para Próximo Step
- Segurança corrigida ✅

---

## 📊 STEP 2: OBSERVABILIDADE BÁSICA ✅ CONCLUÍDO

### Objetivo
Implementar monitoramento proativo com alertas

### Prazo
**1 mês** (Concluído em 01/02/2026)

### Esforço
**24 horas** (Real: 26 horas)

### Ações
```
✅ Health Checks (8h) - CONCLUÍDO
├── ✅ Endpoint /health/ em todos 4 containers Django
├── ✅ /health/live/ - liveness probe
├── ✅ /health/ready/ - readiness probe
├── ✅ /health/startup/ - startup probe
├── ✅ Verificação de dependências (MySQL, Redis)
└── ✅ Endpoint /metrics com métricas Prometheus

✅ Prometheus + Grafana (14h) - CONCLUÍDO
├── ✅ Prometheus configurado e coletando métricas
├── ✅ Grafana com autenticação via Secrets Manager
├── ✅ Dashboard customizado "WallClub - Django Containers"
├── ✅ 10 painéis: requests, latência, CPU, memória, status
├── ✅ Métricas customizadas Django (django-prometheus)
├── ✅ Redis Exporter para métricas do Redis
├── ✅ Node Exporter para métricas do sistema
└── ✅ Refresh automático a cada 10 segundos

✅ Alertas Críticos (4h) - CONCLUÍDO
├── ✅ Alertmanager configurado
├── ✅ Regras de alerta: CPU >80%, Memória >85%, Disco >90%
├── ✅ Alerta Redis memória >90% (corrigido com limite 512mb)
├── ✅ Contact points: Telegram + Email (configuração manual)
└── ✅ Notificações via Grafana (Alertmanager apenas agrupa)
```

### Custos
- **Grafana self-hosted (container):** R$ 0/mês
- **Prometheus storage local:** R$ 0/mês
- **Recursos adicionais (CPU/memória):** ~R$ 0/mês (dentro da capacidade atual)
- **Total:** **R$ 1.500/mês** (R$ 0 de aumento)

**Nota:** Implementação self-hosted economizou R$ 100/mês vs Grafana Cloud

### Entregáveis
- ✅ Dashboards em tempo real (refresh 10s)
- ✅ Alertas proativos configurados
- ✅ Histórico de métricas (15 dias local)
- ✅ 3 URLs de monitoramento:
  - grafana.wallclub.com.br (público com login)
  - prometheus.wallclub.com.br (restrito IP)
  - alertmanager.wallclub.com.br (restrito IP)
- ✅ Dashboard customizado com 10 painéis
- ✅ Métricas de 4 containers Django + Redis + Sistema
- ✅ Health checks em todos os containers

### Gatilho para Próximo Step
- ✅ Monitoramento funcionando e validado (01/02/2026)
- ⏭️ Próximo: Step 3 - Backup Robusto

---

## 💾 STEP 3: BACKUP ROBUSTO

### Objetivo
Backup automático confiável com restore testado

### Prazo
**2 semanas**

### Esforço
**16 horas**

### Ações
```
✅ Backup Automático MySQL (8h)
├── Backup diário para S3 (3h)
├── Backup incremental a cada 6h (2h)
├── Retenção: 7 dias diário, 4 semanas semanal (1h)
└── Criptografia em repouso (2h)

✅ Processo de Restore (4h)
├── Script automatizado de restore
├── Documentação passo-a-passo
├── Teste de restore mensal (agendado)
└── Tempo de restore <30min

✅ Backup de Configurações (4h)
├── Backup de .env e configs
├── Backup de certificados SSL
├── Versionamento no S3
└── Restore de configuração <5min
```

### Custos
- **S3 storage (50GB):** R$ 30/mês
- **S3 requests:** R$ 20/mês
- **Total:** **R$ 1.650/mês** (+R$ 50)

### Entregáveis
- ✅ Backup automático diário
- ✅ Restore testado e documentado
- ✅ RTO <30min, RPO <6h

### Gatilho para Próximo Step
- Volume >50 transações/dia (Processo 1) OU
- Performance começar a degradar

---

## 🔧 STEP 4: DESACOPLAMENTO

### Objetivo
Reduzir acoplamento e preparar para escalabilidade

### Prazo
**3 meses**

### Esforço
**68 horas**

### Ações
```
✅ Sistema Notificações Independente (40h)
├── Serviço dedicado com API REST (16h)
├── Fila Redis/SQS para retry (8h)
├── Suporte WhatsApp, Email, Push (12h)
└── Deploy independente (4h)

✅ NotificationOrchestrator (12h)
├── Orquestrador unificado (6h)
├── Retry policy + backoff (3h)
└── Fallback entre canais (3h)

✅ Substituir Lazy Imports (16h)
├── Identificar 17 arquivos com apps.get_model() (4h)
├── Criar APIs REST correspondentes (8h)
└── Migrar código (4h)
```

### Custos
- **Infraestrutura:** R$ 0 (mesmo servidor)
- **Total:** **R$ 1.650/mês** (sem mudança)

### Entregáveis
- ✅ Primeiro microserviço (Notificações)
- ✅ Acoplamento reduzido
- ✅ Base para escalabilidade

### Gatilho para Próximo Step
- Volume >200 transações/dia (Processo 1) OU
- Performance degradando OU
- MySQL local apresentando problemas

---

## 🗄️ STEP 5: BANCO DE DADOS GERENCIADO

### Objetivo
Migrar MySQL para RDS gerenciado

### Prazo
**1 mês**

### Esforço
**32 horas**

### Ações
```
✅ Preparação (8h)
├── Análise de tamanho e performance (2h)
├── Escolha de instância RDS (2h)
├── Plano de migração detalhado (2h)
└── Plano de rollback (2h)

✅ Setup RDS (8h)
├── Criar RDS MySQL Single-AZ (2h)
├── Configurar security groups (2h)
├── Configurar parameter groups (2h)
└── Configurar backup automático (2h)

✅ Migração (12h)
├── Replicação inicial (mysqldump) (4h)
├── Replicação contínua (DMS ou binlog) (4h)
├── Cutover em janela de manutenção (2h)
└── Validação pós-migração (2h)

✅ Otimização (4h)
├── Ajuste de parâmetros (2h)
└── Monitoramento CloudWatch (2h)
```

### Custos
- **RDS MySQL db.t3.small (Single-AZ):** R$ 350/mês (200-500 trans/dia)
- **ElastiCache Redis t3.micro:** R$ 200/mês
- **Remove:** Parte do custo EC2 (-R$ 0, mantém servidor app)
- **Total:** **R$ 2.200/mês** (+R$ 550)

**Nota:** Instância será upgradada conforme volume cresce (ver tabela de custos)

### Entregáveis
- ✅ MySQL gerenciado pela AWS
- ✅ Backups automáticos (7 dias)
- ✅ Patches automáticos
- ✅ Monitoramento integrado

### Downtime Esperado
- **15-30 minutos** (janela de manutenção)

### Gatilho para Próximo Step
- Volume >500 transações/dia (Processo 1) OU
- Necessidade de escalar horizontalmente OU
- Múltiplos ambientes (staging/prod)

---

## ☸️ STEP 6: PREPARAÇÃO KUBERNETES

### Objetivo
Preparar aplicação para rodar em Kubernetes

### Prazo
**2 meses**

### Esforço
**60 horas**

### Ações
```
✅ Health Checks Avançados (8h)
├── /health/live/ - liveness probe (2h)
├── /health/ready/ - readiness probe (3h)
├── /health/startup/ - startup probe (2h)
└── Testes de cada probe (1h)

✅ Configuração Externalizada (16h)
├── Separar configs sensíveis vs não-sensíveis (4h)
├── Preparar ConfigMaps (4h)
├── Integrar External Secrets Operator (6h)
└── Documentação (2h)

✅ Migrar Arquivos para S3 (12h)
├── Django Storages + boto3 (4h)
├── Migração de arquivos existentes (4h)
├── Testes de upload/download (2h)
└── CloudFront (CDN) opcional (2h)

✅ Testes de Carga (16h)
├── Setup Locust/K6 (4h)
├── Cenários de teste (4h)
├── Execução e análise (6h)
└── Ajustes de performance (2h)

✅ Plano de Rollback (8h)
├── Documentar processo completo (4h)
├── Scripts de rollback (2h)
└── Teste de rollback (2h)
```

### Custos
- **S3 storage (100GB):** R$ 50/mês
- **CloudFront (opcional):** R$ 50/mês
- **Total:** **R$ 2.650/mês** (+R$ 100)

### Entregáveis
- ✅ Aplicação pronta para K8s
- ✅ Configuração externalizada
- ✅ Arquivos em S3
- ✅ Plano de rollback testado

### Gatilho para Próximo Step
- Preparação completa e testada

---

## 🚀 STEP 7: DEPLOY KUBERNETES

### Objetivo
Migrar aplicação para cluster Kubernetes

### Prazo
**2 meses**

### Esforço
**80 horas**

### Ações
```
✅ Setup EKS Cluster (16h)
├── Criar cluster EKS (4h)
├── Configurar node groups (4h)
├── Setup kubectl e helm (2h)
├── Configurar RBAC (4h)
└── Testes básicos (2h)

✅ Deployments + Services (24h)
├── Manifests para 9 containers (12h)
├── Services (ClusterIP/LoadBalancer) (4h)
├── Anti-affinity rules (4h)
└── Resources requests/limits (4h)

✅ Ingress Controller (16h)
├── Instalar Nginx Ingress (4h)
├── Configurar 14 subdomínios (8h)
├── Cert-manager para SSL (4h)
└── Testes de roteamento (2h)

✅ Migração Blue-Green (16h)
├── Deploy em paralelo (4h)
├── Testes de validação (4h)
├── Cutover DNS (2h)
├── Monitoramento 24h (4h)
└── Desligar ambiente antigo (2h)

✅ Documentação (8h)
├── Runbooks operacionais (4h)
└── Procedimentos de deploy (4h)
```

### Custos
- **EKS cluster:** R$ 300/mês
- **Load Balancers (2):** R$ 200/mês
- **NAT Gateway:** R$ 150/mês
- **Nodes EC2 (3x t3.medium):** já coberto
- **RDS upgrade para db.t3.medium:** +R$ 350/mês (500-1k trans/dia)
- **Total:** **R$ 3.750/mês** (+R$ 550)

**Nota:** RDS upgradado de t3.small → t3.medium devido ao volume

### Entregáveis
- ✅ Sistema rodando em Kubernetes
- ✅ Zero downtime em deploys
- ✅ Service discovery nativo
- ✅ SSL automático

### Downtime Esperado
- **0 minutos** (blue-green deployment)

### Gatilho para Próximo Step
- Sistema estável em K8s por 2 semanas

---

## 📈 STEP 8: AUTO-SCALING

### Objetivo
Implementar escalabilidade automática

### Prazo
**1 mês**

### Esforço
**32 horas**

### Ações
```
✅ HPA - Horizontal Pod Autoscaler (12h)
├── HPA para wallclub-apis (min 4, max 15) (3h)
├── HPA para wallclub-portais (min 2, max 8) (3h)
├── HPA para wallclub-pos (min 2, max 10) (3h)
└── Testes de carga e validação (3h)

✅ Redis StatefulSet (12h)
├── Converter para StatefulSet (4h)
├── Persistent volumes (4h)
├── Testes de failover (4h)

✅ Celery Beat Leader Election (4h)
├── Implementar leader election (2h)
└── Testes de singleton (2h)

✅ Monitoramento K8s (4h)
├── Prometheus Operator (2h)
└── Dashboards específicos K8s (2h)
```

### Custos
- **EBS volumes (Redis):** R$ 100/mês
- **Monitoring adicional:** R$ 100/mês
- **RDS upgrade para db.t3.large:** +R$ 400/mês (1k-2k trans/dia)
- **Total:** **R$ 4.350/mês** (+R$ 600)

**Nota:** RDS upgradado de t3.medium → t3.large devido ao volume

### Entregáveis
- ✅ Escalabilidade automática
- ✅ Redis resiliente
- ✅ Celery Beat singleton garantido
- ✅ Monitoramento completo

### Gatilho para Próximo Step
- Volume >2.000 transações/dia (Processo 1) OU
- SLA 99.9% necessário OU
- Operação 24/7 crítica

---

## 🌐 STEP 9: ALTA DISPONIBILIDADE (MULTI-AZ)

### Objetivo
Garantir SLA 99.9% com redundância multi-AZ

### Prazo
**1 mês**

### Esforço
**40 horas**

### Ações
```
✅ RDS Multi-AZ (8h)
├── Upgrade para Multi-AZ (2h)
├── Testes de failover (4h)
└── Validação de performance (2h)

✅ ElastiCache Cluster (12h)
├── Migrar para Cluster Mode (6h)
├── 6 nós (3 masters + 3 replicas) (4h)
└── Testes de failover (2h)

✅ Multi-Região DR (16h)
├── Setup região secundária (8h)
├── Replicação de dados (4h)
└── Runbook de DR (4h)

✅ Chaos Engineering (4h)
├── Testes de falha controlados (2h)
└── Validação de recuperação (2h)
```

### Custos
- **RDS Multi-AZ (db.t3.large):** +R$ 700/mês (dobro Single-AZ)
- **RDS upgrade para db.m5.large:** +R$ 600/mês (>2k trans/dia)
- **ElastiCache Cluster:** +R$ 400/mês (total R$ 600)
- **Multi-região (standby):** R$ 400/mês
- **Total:** **R$ 6.450/mês** (+R$ 2.100)

**Nota:** RDS em Multi-AZ + upgrade para instância otimizada (m5.large)

### Entregáveis
- ✅ SLA 99.95% (AWS garantido)
- ✅ Failover automático <2min
- ✅ Zero downtime em manutenções
- ✅ Disaster recovery testado

### Gatilho para Próximo Step
- Necessidade de microserviços verdadeiros

---

## 🔬 STEP 10: MICROSERVIÇOS ESTRATÉGICOS

### Objetivo
Extrair serviços de baixo acoplamento como microserviços

### Prazo
**6 meses** (incremental)

### Esforço
**160 horas**

### Ações
```
✅ Antifraude Independente (40h)
├── BD próprio PostgreSQL (8h)
├── Migração de dados (8h)
├── APIs REST completas (16h)
└── Deploy independente (8h)

✅ Sistema Ofertas (48h)
├── BD próprio PostgreSQL (8h)
├── Event-driven (Kafka/SQS) (16h)
├── APIs REST (16h)
└── Deploy independente (8h)

✅ Observabilidade Avançada (32h)
├── Distributed tracing (Jaeger) (12h)
├── Log aggregation (ELK) (12h)
└── APM (8h)

✅ Resiliência (24h)
├── Circuit breakers (8h)
├── Rate limiting distribuído (8h)
└── Retry policies (8h)

✅ Autenticação Centralizada (16h)
├── OAuth 2.0 server dedicado (8h)
├── Redis cluster para sessões (4h)
└── Latência <50ms garantida (4h)
```

### Custos
- **PostgreSQL RDS (2 instâncias):** R$ 400/mês
- **Kafka/SQS:** R$ 200/mês
- **Monitoring avançado:** R$ 100/mês
- **RDS MySQL upgrade para db.m5.xlarge:** +R$ 800/mês (>5k trans/dia)
- **Total:** **R$ 7.950/mês** (+R$ 1.500)

**Nota:** RDS MySQL principal upgradado para m5.xlarge (alta performance)

### Entregáveis
- ✅ 3 microserviços independentes
- ✅ Observabilidade completa
- ✅ Resiliência a falhas
- ✅ Deploy independente por serviço

---

## 📊 RESUMO EXECUTIVO

### Progressão de Custos

| Step | Custo Total | Δ Mensal | Δ Acumulado | Volume Alvo (Proc 1) | RDS Instância |
|------|-------------|----------|-------------|----------------------|---------------|
| 0. Atual | R$ 1.500 | - | - | ~5/dia | MySQL local |
| 1. Segurança ✅ | R$ 1.500 | R$ 0 | R$ 0 | ~5/dia | MySQL local |
| 2. Observabilidade ✅ | R$ 1.500 | R$ 0 | R$ 0 | ~5/dia | MySQL local |
| 3. Backup | R$ 1.650 | +R$ 150 | +R$ 150 | ~5/dia | MySQL local |
| 4. Desacoplamento | R$ 1.650 | R$ 0 | +R$ 150 | 50-200/dia | MySQL local |
| 5. BD Gerenciado | R$ 2.550 | +R$ 900 | +R$ 1.050 | 200-500/dia | db.t3.small |
| 6. K8s Prep | R$ 2.650 | +R$ 100 | +R$ 1.150 | 500/dia | db.t3.small |
| 7. K8s Deploy | R$ 3.750 | +R$ 1.450 | +R$ 2.250 | 500-1k/dia | db.t3.medium |
| 8. Auto-scaling | R$ 4.350 | +R$ 600 | +R$ 2.850 | 1k-2k/dia | db.t3.large |
| 9. Multi-AZ | R$ 6.450 | +R$ 2.100 | +R$ 4.950 | >2k/dia | db.m5.large Multi-AZ |
| 10. Microserviços | R$ 7.950 | +R$ 1.500 | +R$ 6.450 | >5k/dia | db.m5.xlarge Multi-AZ |

### Progressão de Esforço

| Fase | Steps | Prazo Total | Esforço Total |
|------|-------|-------------|---------------|
| **Fundação** | 1-3 | 2-3 meses | 66h |
| **Otimização** | 4-5 | 4 meses | 100h |
| **Kubernetes** | 6-8 | 5 meses | 172h |
| **Enterprise** | 9-10 | 7 meses | 200h |
| **TOTAL** | 1-10 | **18 meses** | **538h** |

---

## 🎯 RECOMENDAÇÕES

### Execução Imediata (Steps 1-3)
```
Prazo: 3 meses
Esforço: 66h
Custo: R$ 1.650/mês (+R$ 150)
ROI: ⭐⭐⭐⭐⭐

Foco: Segurança, observabilidade, backup
Benefício: Sistema robusto com custo mínimo
```

### Crescimento Orgânico (Steps 4-5)
```
Prazo: 4 meses
Esforço: 100h
Custo: R$ 2.550/mês (+R$ 900)
ROI: ⭐⭐⭐⭐

Gatilho: Volume >5k transações/dia
Benefício: Primeiro microserviço + BD gerenciado
```

### Escalabilidade (Steps 6-8)
```
Prazo: 5 meses
Esforço: 172h
Custo: R$ 3.600/mês (+R$ 1.050)
ROI: ⭐⭐⭐

Gatilho: Volume >15k transações/dia
Benefício: Kubernetes + auto-scaling
```

### Enterprise (Steps 9-10)
```
Prazo: 7 meses
Esforço: 200h
Custo: R$ 6.100/mês (+R$ 2.500)
ROI: ⭐⭐

Gatilho: Volume >50k transações/dia OU SLA 99.9%
Benefício: Alta disponibilidade + microserviços
```

---

## ⚠️ PONTOS DE ATENÇÃO

### Custos
- Progressão gradual permite ajustar orçamento
- Cada step pode ser pausado/acelerado conforme necessidade
- ROI deve ser avaliado antes de steps caros (7+)

### Riscos
- Steps 1-3: Risco baixo, impacto alto
- Steps 4-6: Risco médio, preparação crítica
- Steps 7-8: Risco médio-alto, requer expertise K8s
- Steps 9-10: Risco alto, apenas se necessário

### Dependências
- Step 5 requer Step 3 (backup testado)
- Step 7 requer Step 6 (preparação completa)
- Step 8 requer Step 7 (K8s estável)
- Step 10 requer Step 9 (infraestrutura robusta)

---

## 📅 CRONOGRAMA SUGERIDO

### Q1 2026 (Jan-Mar) ✅ CONCLUÍDO COM SUCESSO

#### Step 1: Segurança Crítica (31/01/2026) ✅
- ✅ Endpoint deprecated removido
- ✅ Rate Limiting POS implementado (16/01/2026)
- ✅ Gerenciamento de cartões tokenizados
- ✅ Device Fingerprint com similaridade (06/03/2026)

#### Step 2: Observabilidade (01/02/2026) ✅
- ✅ Health checks em 4 containers Django
- ✅ Prometheus + Grafana + Alertmanager
- ✅ Dashboard customizado com 10 painéis
- ✅ Redis Exporter + Node Exporter
- ✅ 3 URLs de monitoramento configuradas
- ✅ Economia de R$ 100/mês (self-hosted vs cloud)

#### Releases Implementadas (Jan-Mar 2026)
- ✅ **v2.2.0 (26/01):** 420 commits - Own Financial, Cupons, Cashback, Base Unificada
- ✅ **v2.2.1 (26/02):** 189 commits - Monitoramento completo, Refatoração URLs, 2FA
- ✅ **v2.2.2 (04/03):** 23 commits - Conciliação, Credenciais Pinbank, Checkout

**Total Q1:** 632 commits, 15+ módulos, 13+ novos endpoints

#### Próximo
- ⏳ Step 3: Backup Robusto (2 semanas, 16h, +R$ 50/mês)

### Q2 2026 (Abr-Jun)
- Step 4: Desacoplamento (se volume >50/dia)

### Q3 2026 (Jul-Set)
- Step 5: BD Gerenciado (se volume >200/dia)

### Q4 2026 (Out-Dez)
- Step 6: K8s Prep (se volume >500/dia)

### 2027
- Steps 7-10 conforme necessidade e volume

---

**Última Atualização:** 08/03/2026
**Próxima Revisão:** Trimestral ou quando atingir gatilhos de volume

**Histórico de Atualizações:**
- 08/03/2026: Otimizações de memória Docker implementadas (workers reduzidos, limites ajustados)
- 06/03/2026: Device Fingerprint com similaridade implementado
- 01/02/2026: Step 2 (Observabilidade) concluído - Sistema de monitoramento completo implementado
- 31/01/2026: Step 1 (Segurança Crítica) concluído
