# Changelog - 08/11/2025

## Celery - Unificação e Tasks Agendadas

### ✅ Worker Celery Unificado
- **Implementado:** Worker único com acesso a todos os apps
- **Removido:** `wallclub-celery-worker-portais` e `wallclub-celery-worker-apis`
- **Criado:** `wallclub-celery-worker` (unificado)
- **Settings:** Novo arquivo `wallclub/settings/celery_worker.py`
- **Benefícios:**
  - Simplificação da arquitetura (9 containers vs 10)
  - Todas as tasks registradas automaticamente
  - Menos memória consumida (512MB vs 768MB)
  - Mais fácil de gerenciar

### ✅ Tasks Agendadas Implementadas

#### 1. Carga Extrato POS
- **Task:** `pinbank.carga_extrato_pos`
- **Schedule:** 5x ao dia (05:13, 09:13, 13:13, 18:13, 22:13)
- **Período:** 72 horas
- **Arquivo:** `pinbank/cargas_pinbank/tasks.py`

#### 2. Cargas Completas Pinbank
- **Task:** `pinbank.cargas_completas`
- **Schedule:** De hora em hora (xx:05) das 5h às 23h
- **Executa:** Extrato POS + Base Gestão + TEF + Ajustes Manuais
- **Arquivo:** `pinbank/cargas_pinbank/tasks.py`

#### 3. Expirar Autorizações de Saldo
- **Task:** `apps.conta_digital.expirar_autorizacoes_saldo`
- **Schedule:** 1x ao dia às 01:00
- **Descrição:** Expira autorizações pendentes e libera bloqueios
- **Arquivo:** `apps/conta_digital/tasks.py` (novo)

### ✅ Correções de Dependências

#### 1. App estr_organizacional
- **Problema:** `ModuleNotFoundError: No module named 'comum'`
- **Arquivo:** `wallclub_core/estr_organizacional/apps.py`
- **Correção:** Alterado `name = 'comum.estr_organizacional'` para `name = 'wallclub_core.estr_organizacional'`

#### 2. Model Loja não encontrado
- **Problema:** `Cannot import 'wallclub_core.Loja'`
- **Solução:** Adicionado `wallclub_core.estr_organizacional` ao `INSTALLED_APPS`
- **Arquivos:**
  - `wallclub/settings/apis.py`
  - `wallclub/settings/celery_worker.py`

## Commits Realizados
1. `refactor: unificar workers do Celery em um único container com acesso a todas as tasks`
2. `chore: ajusta intervalo de cargas completas Pinbank para 5 minutos em ambiente de teste`
3. `feat: implementa task celery para expiração automática de autorizações de saldo`
4. `fix: atualiza nome do app estr_organizacional para novo namespace wallclub_core`
5. `feat: adiciona carga automática de extrato POS e ajusta expiração de autorizações de saldo`

## Arquivos Criados
- `services/django/wallclub/settings/celery_worker.py`
- `services/django/apps/conta_digital/tasks.py`
- `docs/em execucao/CELERY_TASKS_AGENDADAS.md`

## Arquivos Modificados
- `docker-compose.yml` (worker unificado)
- `services/django/wallclub/celery.py` (3 novas tasks)
- `services/django/wallclub/settings/apis.py`
- `services/core/wallclub_core/estr_organizacional/apps.py`
- `README.md` (atualização de containers)

## Deploy
- **Branch:** `v2.0.0`
- **Containers atualizados:** 
  - `wallclub-celery-worker` (novo)
  - `wallclub-celery-beat`
  - `wallclub-apis`
- **Containers removidos:**
  - `wallclub-celery-worker-portais`
  - `wallclub-celery-worker-apis`
- **Servidor:** Produção (10.0.1.124)

## Monitoramento
- **Flower:** https://flower.wallclub.com.br
- **Logs Beat:** `docker logs wallclub-celery-beat --tail 50`
- **Logs Worker:** `docker logs wallclub-celery-worker --tail 100`
- **Documentação:** `docs/em execucao/CELERY_TASKS_AGENDADAS.md`
