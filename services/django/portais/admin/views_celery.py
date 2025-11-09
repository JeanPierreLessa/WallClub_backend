from django.shortcuts import render
from django.http import JsonResponse
from portais.controle_acesso.decorators import require_admin_access
from wallclub.celery import app as celery_app
from celery import current_app
from datetime import datetime, timedelta
import redis
from django.conf import settings
from celery.result import AsyncResult
import json

@require_admin_access
def celery_dashboard(request):
    """Dashboard de monitoramento do Celery"""
    
    # Conectar ao Redis para buscar informações
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=0,
        decode_responses=True
    )
    
    # 1. Tasks Agendadas (do Beat Schedule)
    beat_schedule = celery_app.conf.beat_schedule
    tasks_agendadas = []
    
    for task_name, config in beat_schedule.items():
        schedule = config.get('schedule')
        task = config.get('task')
        args = config.get('args', ())
        
        # Calcular próxima execução
        if hasattr(schedule, 'remaining_estimate'):
            try:
                remaining = schedule.remaining_estimate(datetime.now())
                proxima_execucao = datetime.now() + remaining
            except:
                proxima_execucao = None
        else:
            proxima_execucao = None
        
        # Formatar schedule para exibição
        if hasattr(schedule, 'minute') and hasattr(schedule, 'hour'):
            # Crontab
            schedule_str = f"Crontab: min={schedule.minute}, hour={schedule.hour}"
        elif hasattr(schedule, 'run_every'):
            # Interval
            schedule_str = f"A cada {schedule.run_every}"
        else:
            schedule_str = str(schedule)
        
        tasks_agendadas.append({
            'nome': task_name,
            'task': task,
            'schedule': schedule_str,
            'args': args,
            'proxima_execucao': proxima_execucao
        })
    
    # 2. Workers Ativos
    inspect = celery_app.control.inspect()
    workers_info = []
    
    try:
        stats = inspect.stats()
        active_queues = inspect.active_queues()
        
        if stats:
            for worker_name, worker_stats in stats.items():
                worker_info = {
                    'nome': worker_name,
                    'pool': worker_stats.get('pool', {}).get('implementation', 'N/A'),
                    'max_concurrency': worker_stats.get('pool', {}).get('max-concurrency', 'N/A'),
                    'total_tasks': worker_stats.get('total', {}).get('tasks', 0),
                    'queues': []
                }
                
                # Adicionar filas
                if active_queues and worker_name in active_queues:
                    worker_info['queues'] = [q['name'] for q in active_queues[worker_name]]
                
                workers_info.append(worker_info)
    except Exception as e:
        workers_info = [{'erro': str(e)}]
    
    # 3. Tasks Ativas (em execução agora)
    tasks_ativas = []
    try:
        active = inspect.active()
        if active:
            for worker_name, tasks in active.items():
                for task in tasks:
                    tasks_ativas.append({
                        'worker': worker_name,
                        'nome': task.get('name', 'N/A'),
                        'id': task.get('id', 'N/A'),
                        'args': task.get('args', ''),
                        'tempo_inicio': task.get('time_start', None)
                    })
    except Exception as e:
        pass
    
    # 4. Estatísticas do Redis (filas)
    try:
        # Tamanho da fila principal
        queue_size = redis_client.llen('celery')
        
        # Contar tasks por estado (aproximado via Redis)
        keys_pattern = 'celery-task-meta-*'
        task_keys = redis_client.keys(keys_pattern)
        
        estados = {'SUCCESS': 0, 'FAILURE': 0, 'PENDING': 0, 'RETRY': 0}
        for key in task_keys[:100]:  # Limitar a 100 para performance
            try:
                task_data = redis_client.get(key)
                if task_data:
                    task_info = json.loads(task_data)
                    status = task_info.get('status', 'UNKNOWN')
                    if status in estados:
                        estados[status] += 1
            except:
                pass
        
        estatisticas = {
            'fila_pendente': queue_size,
            'tasks_sucesso': estados['SUCCESS'],
            'tasks_falha': estados['FAILURE'],
            'tasks_retry': estados['RETRY']
        }
    except Exception as e:
        estatisticas = {'erro': str(e)}
    
    context = {
        'tasks_agendadas': sorted(tasks_agendadas, key=lambda x: x['nome']),
        'workers': workers_info,
        'tasks_ativas': tasks_ativas,
        'estatisticas': estatisticas,
        'agora': datetime.now()
    }
    
    return render(request, 'portais/admin/celery_dashboard.html', context)


@require_admin_access
def celery_task_history(request):
    """Histórico de execuções de tasks (últimas 24h)"""
    
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=0,
        decode_responses=True
    )
    
    # Buscar tasks recentes do Redis
    task_keys = redis_client.keys('celery-task-meta-*')
    tasks_history = []
    
    for key in task_keys[:200]:  # Limitar a 200 tasks
        try:
            task_data = redis_client.get(key)
            if task_data:
                task_info = json.loads(task_data)
                task_id = key.replace('celery-task-meta-', '')
                
                tasks_history.append({
                    'task_id': task_id,
                    'status': task_info.get('status', 'UNKNOWN'),
                    'result': task_info.get('result'),
                    'traceback': task_info.get('traceback'),
                    'task_name': task_info.get('task_name', 'N/A'),
                    'date_done': task_info.get('date_done')
                })
        except:
            pass
    
    # Ordenar por data (mais recentes primeiro)
    tasks_history.sort(key=lambda x: x.get('date_done', ''), reverse=True)
    
    context = {
        'tasks_history': tasks_history[:50],  # Mostrar apenas 50 mais recentes
        'total': len(tasks_history)
    }
    
    return render(request, 'portais/admin/celery_history.html', context)


@require_admin_access
def celery_task_detail(request, task_id):
    """Detalhes de uma task específica"""
    
    result = AsyncResult(task_id, app=celery_app)
    
    task_info = {
        'task_id': task_id,
        'status': result.status,
        'result': result.result,
        'traceback': result.traceback,
        'successful': result.successful(),
        'failed': result.failed(),
        'ready': result.ready(),
        'info': result.info
    }
    
    return JsonResponse(task_info)
