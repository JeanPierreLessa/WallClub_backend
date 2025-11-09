# Tasks Celery Agendadas

**Data:** 08/11/2025

## Arquitetura

### Worker Unificado
- **Container:** `wallclub-celery-worker`
- **Settings:** `wallclub.settings.celery_worker`
- **Acesso:** Todos os apps (portais, apis, pos, pinbank, conta_digital)
- **Concurrency:** 4 workers
- **Recursos:** 512MB RAM, 0.5 CPU

### Beat Scheduler
- **Container:** `wallclub-celery-beat`
- **Settings:** `wallclub.settings.celery_worker`
- **Schedule File:** `celerybeat-schedule`
- **Max Loop Interval:** 30 minutos

### Monitoramento
- **Flower:** https://flower.wallclub.com.br
- **Logs:** `docker logs wallclub-celery-worker` / `docker logs wallclub-celery-beat`

## Tasks Agendadas

### 1. Carga Extrato POS
**Task:** `pinbank.carga_extrato_pos`  
**Schedule:** 5x ao dia - 05:13, 09:13, 13:13, 18:13, 22:13  
**Período:** 72 horas  
**Timeout:** 1 hora  
**Descrição:** Busca transações POS do Pinbank e atualiza base local

```python
'carga-extrato-pos': {
    'task': 'pinbank.carga_extrato_pos',
    'schedule': crontab(minute=13, hour='5,9,13,18,22'),
    'args': ('72h',),
    'options': {'expires': 3600}
}
```

### 2. Cargas Completas Pinbank
**Task:** `pinbank.cargas_completas`  
**Schedule:** De hora em hora (xx:05) das 5h às 23h  
**Timeout:** 1 hora  
**Descrição:** Executa sequencialmente:
1. Carga extrato POS (80min)
2. Carga base gestão (10.000 registros)
3. Carga TEF (10.000 registros)
4. Ajustes manuais de base

```python
'cargas-completas-pinbank': {
    'task': 'pinbank.cargas_completas',
    'schedule': crontab(minute=5, hour='5-23'),
    'options': {'expires': 3600}
}
```

### 3. Expirar Autorizações de Saldo
**Task:** `apps.conta_digital.expirar_autorizacoes_saldo`  
**Schedule:** 1x ao dia às 01:00  
**Timeout:** 1 hora  
**Descrição:** Expira autorizações pendentes/aprovadas e libera bloqueios de saldo

```python
'expirar-autorizacoes-saldo': {
    'task': 'apps.conta_digital.expirar_autorizacoes_saldo',
    'schedule': crontab(hour=1, minute=0),
    'options': {'expires': 3600}
}
```

### 4. Processar Recorrências Diárias
**Task:** `portais.vendas.tasks_recorrencia.processar_recorrencias_do_dia`  
**Schedule:** 1x ao dia às 08:00  
**Timeout:** 1 hora  
**Descrição:** Processa cobranças recorrentes agendadas para o dia

### 5. Retentar Cobranças Falhadas
**Task:** `portais.vendas.tasks_recorrencia.retentar_cobrancas_falhadas`  
**Schedule:** 1x ao dia às 10:00  
**Timeout:** 1 hora  
**Descrição:** Retenta cobranças que falharam anteriormente

### 6. Notificar Recorrências em Hold
**Task:** `portais.vendas.tasks_recorrencia.notificar_recorrencias_hold`  
**Schedule:** 1x ao dia às 18:00  
**Timeout:** 1 hora  
**Descrição:** Notifica clientes sobre recorrências em espera

### 7. Limpar Recorrências Antigas
**Task:** `portais.vendas.tasks_recorrencia.limpar_recorrencias_antigas`  
**Schedule:** 1x por semana (Domingo às 02:00)  
**Timeout:** 2 horas  
**Descrição:** Remove recorrências antigas do banco

### 8. Limpar Dispositivos Expirados
**Task:** `apps.cliente.tasks_revalidacao.limpar_dispositivos_expirados`  
**Schedule:** 1x ao dia às 03:00  
**Timeout:** 1 hora  
**Descrição:** Remove dispositivos confiáveis expirados (>30 dias)

## Comandos Úteis

### Ver Tasks Agendadas
```bash
# Via Python
docker exec wallclub-celery-beat python -c "
from wallclub.celery import app
for name, config in app.conf.beat_schedule.items():
    print(f'{name}: {config}')
"

# Via Logs
docker logs wallclub-celery-beat --tail 100 | grep "Scheduler:"
```

### Executar Task Manualmente
```bash
# Carga extrato POS
docker exec wallclub-celery-worker celery -A wallclub call pinbank.carga_extrato_pos --args='["72h"]'

# Expirar autorizações
docker exec wallclub-celery-worker celery -A wallclub call apps.conta_digital.expirar_autorizacoes_saldo
```

### Reiniciar Schedule
```bash
# Parar Beat
docker-compose stop wallclub-celery-beat

# Deletar schedule persistente (força reload)
docker exec wallclub-celery-beat rm -f /app/celerybeat-schedule

# Subir novamente
docker-compose up -d wallclub-celery-beat
```

### Monitorar Execuções
```bash
# Logs do worker
docker logs wallclub-celery-worker --tail 100 -f

# Logs do beat
docker logs wallclub-celery-beat --tail 50 -f

# Flower (interface web)
https://flower.wallclub.com.br
```

## Troubleshooting

### Task não está executando
1. Verificar se o Beat está rodando: `docker ps | grep celery-beat`
2. Ver logs do Beat: `docker logs wallclub-celery-beat --tail 50`
3. Verificar se a task está registrada no schedule
4. Deletar `celerybeat-schedule` e reiniciar Beat

### Task falha ao executar
1. Ver logs do worker: `docker logs wallclub-celery-worker --tail 100`
2. Verificar se o app está no `INSTALLED_APPS` do `celery_worker.py`
3. Testar comando manualmente no container apropriado

### Worker não descobre tasks
1. Verificar `INSTALLED_APPS` em `wallclub/settings/celery_worker.py`
2. Reiniciar worker: `docker-compose restart wallclub-celery-worker`
3. Ver tasks registradas: `docker exec wallclub-celery-worker celery -A wallclub inspect registered`
