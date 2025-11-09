from django.shortcuts import render
from django.http import JsonResponse
from portais.controle_acesso.decorators import require_admin_access
from datetime import datetime, timedelta
import redis
from django.conf import settings
import json

@require_admin_access
def celery_dashboard(request):
    """Dashboard de monitoramento do Celery"""
    
    # Conectar ao Redis para buscar informações
    try:
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=0,
            decode_responses=True
        )
        redis_client.ping()  # Testar conexão
    except Exception as e:
        return render(request, 'portais/admin/celery_dashboard.html', {
            'erro': f'Erro ao conectar ao Redis: {str(e)}',
            'tasks_agendadas': [],
            'workers': [],
            'tasks_ativas': [],
            'estatisticas': {},
            'agora': datetime.now()
        })
    
    # 1. Tasks Agendadas (hardcoded - baseado no celery.py)
    tasks_agendadas = [
        {
            'nome': 'carga-extrato-pos',
            'task': 'pinbank.carga_extrato_pos',
            'schedule': 'Crontab: 5x ao dia (05:13, 09:13, 13:13, 18:13, 22:13)',
            'args': ('72h',),
            'proxima_execucao': None
        },
        {
            'nome': 'cargas-completas-pinbank',
            'task': 'pinbank.cargas_completas',
            'schedule': 'Crontab: De hora em hora (xx:05) das 5h às 23h',
            'args': (),
            'proxima_execucao': None
        },
        {
            'nome': 'expirar-autorizacoes-saldo',
            'task': 'apps.conta_digital.expirar_autorizacoes_saldo',
            'schedule': 'Crontab: 1x ao dia às 01:00',
            'args': (),
            'proxima_execucao': None
        },
    ]
    
    # 2. Workers Ativos (simplificado - sem inspect)
    workers_info = [
        {
            'nome': 'wallclub-celery-worker@container',
            'pool': 'prefork',
            'max_concurrency': 4,
            'total_tasks': 'N/A',
            'queues': ['celery']
        }
    ]
    
    # 3. Tasks Ativas (não disponível sem Celery inspect)
    tasks_ativas = []
    
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
    
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=0,
        decode_responses=True
    )
    
    try:
        task_data = redis_client.get(f'celery-task-meta-{task_id}')
        if task_data:
            task_info = json.loads(task_data)
            task_info['task_id'] = task_id
        else:
            task_info = {
                'task_id': task_id,
                'status': 'NOT_FOUND',
                'mensagem': 'Task não encontrada no Redis'
            }
    except Exception as e:
        task_info = {
            'task_id': task_id,
            'status': 'ERROR',
            'mensagem': str(e)
        }
    
    return JsonResponse(task_info)
