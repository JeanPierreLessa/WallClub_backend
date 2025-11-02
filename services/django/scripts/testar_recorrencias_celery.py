"""
Script de teste para validar tasks de recorrência do Celery.
Fase 5 - Sistema de Recorrência

Uso:
    python manage.py shell < scripts/testar_recorrencias_celery.py
    
    OU dentro do Django shell:
    >>> exec(open('scripts/testar_recorrencias_celery.py').read())
"""

import os
import sys
import django
from pathlib import Path

# Adicionar diretório raiz do projeto ao sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wallclub.settings')
django.setup()

from datetime import datetime, timedelta
from decimal import Decimal
from portais.vendas.tasks_recorrencia import (
    processar_recorrencias_do_dia,
    retentar_cobrancas_falhadas,
    notificar_recorrencias_hold,
    limpar_recorrencias_antigas
)
from checkout.models_recorrencia import RecorrenciaAgendada

print("=" * 80)
print("TESTE DE TASKS DE RECORRÊNCIA - CELERY")
print("=" * 80)
print()

# ============================================
# 1. Testar descoberta de tasks
# ============================================
print("1. Verificar se Celery descobre as tasks...")
try:
    from wallclub.celery import app as celery_app
    
    # Listar tasks registradas
    tasks = sorted(celery_app.tasks.keys())
    recorrencia_tasks = [t for t in tasks if 'recorrencia' in t]
    
    print(f"✅ Celery inicializado com sucesso")
    print(f"📋 Total de tasks registradas: {len(tasks)}")
    print(f"📋 Tasks de recorrência encontradas: {len(recorrencia_tasks)}")
    
    for task in recorrencia_tasks:
        print(f"  - {task}")
    
except Exception as e:
    print(f"❌ Erro ao verificar Celery: {e}")

print()

# ============================================
# 2. Verificar Beat Schedule
# ============================================
print("2. Verificar configuração do Celery Beat...")
try:
    from wallclub.celery import app as celery_app
    
    beat_schedule = celery_app.conf.beat_schedule
    print(f"✅ Beat Schedule configurado com {len(beat_schedule)} tasks periódicas:")
    
    for name, config in beat_schedule.items():
        if 'recorrencia' in name:
            task_name = config['task']
            schedule = config['schedule']
            print(f"  - {name}")
            print(f"    Task: {task_name}")
            print(f"    Schedule: {schedule}")
    
except Exception as e:
    print(f"❌ Erro ao verificar Beat Schedule: {e}")

print()

# ============================================
# 3. Testar execução manual das tasks
# ============================================
print("3. Testar execução manual das tasks...")
print()

# Task 1: Processar recorrências do dia
print("3.1. Testando: processar_recorrencias_do_dia()")
try:
    hoje = datetime.now().date()
    total_hoje = RecorrenciaAgendada.objects.filter(
        status='ativo',
        proxima_cobranca=hoje
    ).count()
    
    print(f"📊 Recorrências agendadas para hoje: {total_hoje}")
    
    resultado = processar_recorrencias_do_dia()
    
    if resultado.get('success'):
        print(f"✅ Task executada com sucesso")
        print(f"   Processadas: {resultado.get('processadas', 0)}")
        print(f"   Aprovadas: {resultado.get('aprovadas', 0)}")
        print(f"   Negadas: {resultado.get('negadas', 0)}")
        print(f"   Erros: {resultado.get('erros', 0)}")
    else:
        print(f"❌ Task falhou: {resultado.get('error')}")
        
except Exception as e:
    print(f"❌ Erro ao executar task: {e}")

print()

# Task 2: Retentar cobranças falhadas
print("3.2. Testando: retentar_cobrancas_falhadas()")
try:
    hoje = datetime.now().date()
    total_retry = RecorrenciaAgendada.objects.filter(
        status='ativo',
        proxima_cobranca=hoje,
        tentativas_falhas_consecutivas__gt=0,
        tentativas_falhas_consecutivas__lt=3
    ).count()
    
    print(f"📊 Recorrências agendadas para retry hoje: {total_retry}")
    
    resultado = retentar_cobrancas_falhadas()
    
    if resultado.get('success'):
        print(f"✅ Task executada com sucesso")
        print(f"   Processadas: {resultado.get('processadas', 0)}")
        print(f"   Aprovadas: {resultado.get('aprovadas', 0)}")
        print(f"   Hold: {resultado.get('hold', 0)}")
    else:
        print(f"❌ Task falhou: {resultado.get('error')}")
        
except Exception as e:
    print(f"❌ Erro ao executar task: {e}")

print()

# Task 3: Notificar recorrências em hold
print("3.3. Testando: notificar_recorrencias_hold()")
try:
    total_hold = RecorrenciaAgendada.objects.filter(status='hold').count()
    
    print(f"📊 Recorrências em HOLD: {total_hold}")
    
    resultado = notificar_recorrencias_hold()
    
    if resultado.get('success'):
        print(f"✅ Task executada com sucesso")
        print(f"   Total em hold: {resultado.get('total', 0)}")
        print(f"   Notificações enviadas: {resultado.get('notificacoes_enviadas', 0)}")
    else:
        print(f"❌ Task falhou: {resultado.get('error')}")
        
except Exception as e:
    print(f"❌ Erro ao executar task: {e}")

print()

# Task 4: Limpar recorrências antigas
print("3.4. Testando: limpar_recorrencias_antigas()")
try:
    limite = datetime.now().date() - timedelta(days=180)
    total_antigas = RecorrenciaAgendada.objects.filter(
        status='ativo',
        proxima_cobranca__lt=limite
    ).count()
    
    print(f"📊 Recorrências antigas (>180 dias): {total_antigas}")
    
    resultado = limpar_recorrencias_antigas()
    
    if resultado.get('success'):
        print(f"✅ Task executada com sucesso")
        print(f"   Total limpas: {resultado.get('total_limpas', 0)}")
    else:
        print(f"❌ Task falhou: {resultado.get('error')}")
        
except Exception as e:
    print(f"❌ Erro ao executar task: {e}")

print()

# ============================================
# 4. Estatísticas gerais
# ============================================
print("4. Estatísticas de Recorrências")
print("-" * 80)
try:
    stats = {
        'total': RecorrenciaAgendada.objects.count(),
        'ativo': RecorrenciaAgendada.objects.filter(status='ativo').count(),
        'pausado': RecorrenciaAgendada.objects.filter(status='pausado').count(),
        'cancelado': RecorrenciaAgendada.objects.filter(status='cancelado').count(),
        'hold': RecorrenciaAgendada.objects.filter(status='hold').count(),
        'pendente': RecorrenciaAgendada.objects.filter(status='pendente').count(),
        'concluido': RecorrenciaAgendada.objects.filter(status='concluido').count(),
    }
    
    print(f"📊 Total de recorrências: {stats['total']}")
    print(f"   - Ativo: {stats['ativo']}")
    print(f"   - Pausado: {stats['pausado']}")
    print(f"   - Cancelado: {stats['cancelado']}")
    print(f"   - Hold: {stats['hold']}")
    print(f"   - Pendente: {stats['pendente']}")
    print(f"   - Concluído: {stats['concluido']}")
    
except Exception as e:
    print(f"❌ Erro ao buscar estatísticas: {e}")

print()
print("=" * 80)
print("TESTE CONCLUÍDO")
print("=" * 80)
print()
print("📝 PRÓXIMOS PASSOS:")
print("1. Instalar celery: pip install celery==5.3.4")
print("2. Iniciar worker: celery -A wallclub worker --loglevel=info")
print("3. Iniciar beat: celery -A wallclub beat --loglevel=info")
print("4. Ou usar docker-compose: docker-compose up celery-worker-django celery-beat-django")
print()
