# SETUP CELERY - SISTEMA DE RECORRÊNCIAS
**Data:** 30/10/2025  
**Status:** ✅ CONFIGURADO - Pronto para deploy

---

## 📋 RESUMO

Sistema Celery configurado para processar **4 tasks periódicas** de recorrências automaticamente:

1. **Processar recorrências do dia** - 08:00 diariamente
2. **Retentar cobranças falhadas** - 10:00 diariamente  
3. **Notificar recorrências em hold** - 18:00 diariamente
4. **Limpar recorrências antigas** - Domingo 02:00

---

## 🏗️ ARQUITETURA

```
┌─────────────────────────────────────────────────┐
│  DJANGO WEB (wallclub-prod-release300:8000)     │
│  - Gera tasks de recorrência                    │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│  REDIS (wallclub-redis:6379)                    │
│  - Broker: Fila de tasks                        │
│  - Backend: Resultados                          │
└─────────────────┬───────────────────────────────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
┌─────────────────┐  ┌─────────────────┐
│ CELERY WORKER   │  │ CELERY BEAT     │
│ (Django)        │  │ (Django)        │
│ - Processa      │  │ - Agenda tasks  │
│   tasks         │  │   periódicas    │
│ - Concurrency:2 │  │ - Cron          │
└─────────────────┘  └─────────────────┘
```

---

## 📁 ARQUIVOS CRIADOS/MODIFICADOS

### 1. Criados
```
wallclub/celery.py                          # Configuração Celery + Beat Schedule
scripts/testar_recorrencias_celery.py      # Script de testes
docs/plano_estruturado/CELERY_RECORRENCIAS_SETUP.md  # Esta documentação
```

### 2. Modificados
```
wallclub/__init__.py                        # Import celery_app
wallclub/settings/base.py                   # Configurações Celery (linhas 405-431)
docker-compose.yml                          # Containers celery-worker-django e celery-beat-django
requirements.txt                            # celery==5.3.4
```

---

## ⚙️ CONFIGURAÇÕES

### Celery Settings (`settings/base.py`)

```python
# Broker e Backend
CELERY_BROKER_URL = 'redis://wallclub-redis:6379/0'
CELERY_RESULT_BACKEND = 'redis://wallclub-redis:6379/0'

# Serialização
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

# Timezone
CELERY_TIMEZONE = 'America/Sao_Paulo'
CELERY_ENABLE_UTC = False

# Limites
CELERY_TASK_TIME_LIMIT = 300        # 5 minutos
CELERY_TASK_SOFT_TIME_LIMIT = 240   # 4 minutos (aviso)
```

### Beat Schedule (`wallclub/celery.py`)

```python
app.conf.beat_schedule = {
    'processar-recorrencias-diarias': {
        'task': 'portais.vendas.tasks_recorrencia.processar_recorrencias_do_dia',
        'schedule': crontab(hour=8, minute=0),
    },
    'retentar-cobrancas-falhadas': {
        'task': 'portais.vendas.tasks_recorrencia.retentar_cobrancas_falhadas',
        'schedule': crontab(hour=10, minute=0),
    },
    'notificar-recorrencias-hold': {
        'task': 'portais.vendas.tasks_recorrencia.notificar_recorrencias_hold',
        'schedule': crontab(hour=18, minute=0),
    },
    'limpar-recorrencias-antigas': {
        'task': 'portais.vendas.tasks_recorrencia.limpar_recorrencias_antigas',
        'schedule': crontab(hour=2, minute=0, day_of_week=0),  # Domingo
    },
}
```

---

## 🐳 CONTAINERS DOCKER

### celery-worker-django
- **Função:** Processa tasks de recorrências
- **Comando:** `celery -A wallclub worker --loglevel=info --concurrency=2`
- **Recursos:** 512MB RAM, 0.5 CPU
- **Dependências:** redis, web

### celery-beat-django
- **Função:** Agenda tasks periódicas (cron)
- **Comando:** `celery -A wallclub beat --loglevel=info`
- **Recursos:** 256MB RAM, 0.25 CPU
- **Dependências:** redis, celery-worker-django

---

## 🧪 TESTES

### 1. Teste Manual (Django Shell)

```bash
python manage.py shell

>>> from portais.vendas.tasks_recorrencia import processar_recorrencias_do_dia
>>> resultado = processar_recorrencias_do_dia()
>>> print(resultado)
```

### 2. Script Automatizado

```bash
python scripts/testar_recorrencias_celery.py
```

**Validações do script:**
- ✅ Celery inicializado
- ✅ Tasks registradas (4 tasks de recorrência)
- ✅ Beat Schedule configurado
- ✅ Execução manual de cada task
- ✅ Estatísticas de recorrências

### 3. Verificar Logs

```bash
# Logs do worker
docker logs wallclub-celery-worker-django -f

# Logs do beat
docker logs wallclub-celery-beat-django -f

# Logs Django (tasks)
tail -f logs/debug.log | grep recorrencia
```

---

## 🚀 DEPLOY

### Local (Desenvolvimento)

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Terminal 1: Iniciar worker
celery -A wallclub worker --loglevel=info

# 3. Terminal 2: Iniciar beat
celery -A wallclub beat --loglevel=info
```

### Docker (Produção)

```bash
# 1. Build e restart dos containers
docker-compose build celery-worker-django celery-beat-django
docker-compose up -d celery-worker-django celery-beat-django

# 2. Verificar status
docker ps | grep celery

# 3. Verificar logs
docker logs wallclub-celery-worker-django --tail=50
docker logs wallclub-celery-beat-django --tail=50
```

---

## 📊 MONITORAMENTO

### Verificar Tasks Agendadas

```bash
# Django shell
python manage.py shell

>>> from wallclub.celery import app
>>> inspect = app.control.inspect()

# Tasks ativas
>>> inspect.active()

# Tasks agendadas
>>> inspect.scheduled()

# Tasks registradas
>>> app.tasks.keys()
```

### Métricas de Recorrências

```sql
-- Recorrências por status
SELECT status, COUNT(*) as total 
FROM checkout_recorrencias 
GROUP BY status;

-- Recorrências agendadas para hoje
SELECT COUNT(*) 
FROM checkout_recorrencias 
WHERE status = 'ativo' 
  AND proxima_cobranca = CURDATE();

-- Recorrências em HOLD
SELECT COUNT(*) 
FROM checkout_recorrencias 
WHERE status = 'hold';
```

---

## 🛠️ TROUBLESHOOTING

### Problema: Worker não encontra tasks

**Sintoma:** `KeyError: 'portais.vendas.tasks_recorrencia.processar_recorrencias_do_dia'`

**Solução:**
```bash
# Verificar se tasks estão registradas
python manage.py shell
>>> from wallclub.celery import app
>>> 'portais.vendas.tasks_recorrencia.processar_recorrencias_do_dia' in app.tasks
True  # Deve retornar True

# Reiniciar worker
docker-compose restart celery-worker-django
```

### Problema: Beat não agenda tasks

**Sintoma:** Tasks não executam no horário configurado

**Solução:**
```bash
# Verificar timezone
python manage.py shell
>>> from wallclub.celery import app
>>> app.conf.timezone
'America/Sao_Paulo'

# Verificar beat_schedule
>>> app.conf.beat_schedule
{...}  # Deve mostrar as 4 tasks

# Reiniciar beat
docker-compose restart celery-beat-django
```

### Problema: Redis não acessível

**Sintoma:** `redis.exceptions.ConnectionError`

**Solução:**
```bash
# Verificar Redis
docker ps | grep redis
docker logs wallclub-redis

# Testar conexão
docker exec wallclub-redis redis-cli ping
# Deve retornar: PONG

# Verificar variáveis de ambiente
docker exec wallclub-celery-worker-django env | grep CELERY
```

---

## ✅ CHECKLIST DE VALIDAÇÃO

### Desenvolvimento
- [ ] `pip install celery==5.3.4` executado
- [ ] Worker inicia sem erros
- [ ] Beat inicia sem erros
- [ ] Script de teste executa todas as 4 tasks
- [ ] Logs mostram tasks sendo descobertas

### Produção
- [ ] `docker-compose build` executado
- [ ] Containers celery-worker-django e celery-beat-django rodando
- [ ] `docker ps` mostra 7 containers (web, redis, riskengine, celery-worker x2, celery-beat x2)
- [ ] Logs não mostram erros
- [ ] Tasks registradas no worker
- [ ] Beat Schedule carregado
- [ ] Teste manual via Django shell funciona

---

## 📅 CRONOGRAMA DE EXECUÇÃO

| Task                              | Horário       | Frequência | Objetivo                          |
|-----------------------------------|---------------|------------|-----------------------------------|
| `processar_recorrencias_do_dia`   | 08:00         | Diária     | Processar cobranças agendadas     |
| `retentar_cobrancas_falhadas`     | 10:00         | Diária     | Retry com backoff                 |
| `notificar_recorrencias_hold`     | 18:00         | Diária     | Alertar vendedores                |
| `limpar_recorrencias_antigas`     | 02:00 Domingo | Semanal    | Limpar recorrências >180 dias     |

---

## 🔗 REFERÊNCIAS

- **Tasks:** `portais/vendas/tasks_recorrencia.py` (404 linhas)
- **Services:** `portais/vendas/services.py` - CheckoutVendasService
- **Models:** `checkout/models_recorrencia.py` - RecorrenciaAgendada
- **Doc Fase 5:** `docs/plano_estruturado/ROTEIRO_FASE_5.md`
- **Celery Docs:** https://docs.celeryq.dev/en/stable/

---

**Configuração completa por:** Jean Pierre Lessa  
**Data:** 30/10/2025  
**Status:** ✅ Pronto para produção
