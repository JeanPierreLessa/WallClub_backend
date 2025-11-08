"""
Configuração do Celery para WallClub Django.
Processa tasks assíncronas como recorrências, cargas, notificações, etc.
"""

import os
from celery import Celery
from celery.schedules import crontab

# Define o módulo de settings do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wallclub.settings')

# Cria a instância do Celery
app = Celery('wallclub')

# Carrega configurações do Django
app.config_from_object('django.conf:settings', namespace='CELERY')

# Descobre tasks automaticamente em todos os apps instalados
app.autodiscover_tasks()

# Configuração do Celery Beat Schedule
app.conf.beat_schedule = {
    # ============================================
    # RECORRÊNCIAS (Fase 5)
    # ============================================
    
    # Processar recorrências do dia - 08:00 todos os dias
    'processar-recorrencias-diarias': {
        'task': 'portais.vendas.tasks_recorrencia.processar_recorrencias_do_dia',
        'schedule': crontab(hour=8, minute=0),
        'options': {
            'expires': 3600,  # Expira em 1 hora se não executar
        }
    },
    
    # Retentar cobranças falhadas - 10:00 todos os dias
    'retentar-cobrancas-falhadas': {
        'task': 'portais.vendas.tasks_recorrencia.retentar_cobrancas_falhadas',
        'schedule': crontab(hour=10, minute=0),
        'options': {
            'expires': 3600,
        }
    },
    
    # Notificar recorrências em hold - 18:00 todos os dias
    'notificar-recorrencias-hold': {
        'task': 'portais.vendas.tasks_recorrencia.notificar_recorrencias_hold',
        'schedule': crontab(hour=18, minute=0),
        'options': {
            'expires': 3600,
        }
    },
    
    # Limpar recorrências antigas - Domingo 02:00
    'limpar-recorrencias-antigas': {
        'task': 'portais.vendas.tasks_recorrencia.limpar_recorrencias_antigas',
        'schedule': crontab(hour=2, minute=0, day_of_week=0),  # 0 = Domingo
        'options': {
            'expires': 7200,  # Expira em 2 horas
        }
    },
    
    # ============================================
    # REVALIDAÇÃO DE DISPOSITIVOS (Fase 4)
    # ============================================
    
    # Limpar dispositivos expirados - Diariamente às 03:00
    'limpar-dispositivos-expirados': {
        'task': 'apps.cliente.tasks_revalidacao.limpar_dispositivos_expirados',
        'schedule': crontab(hour=3, minute=0),
        'options': {
            'expires': 3600,
        }
    },
    
    # ============================================
    # CARGAS PINBANK (Automáticas)
    # ============================================
    
    # Carga extrato POS - 5x ao dia às 05:13, 09:13, 13:13, 18:13, 22:13
    'carga-extrato-pos': {
        'task': 'pinbank.carga_extrato_pos',
        'schedule': crontab(minute=13, hour='5,9,13,18,22'),  # xx:13 em horários específicos
        'args': ('72h',),  # Período de 72 horas
        'options': {
            'expires': 3600,  # Expira em 1 hora
        }
    },
    
    # Cargas completas - De hora em hora, minuto 5, das 5h às 23h
    'cargas-completas-pinbank': {
        'task': 'pinbank.cargas_completas',
        'schedule': crontab(minute=5, hour='5-23'),  # xx:05 das 5h às 23h
        'options': {
            'expires': 3600,  # Expira em 1 hora
        }
    },
    
    # ============================================
    # CONTA DIGITAL - AUTORIZAÇÕES
    # ============================================
    
    # Expirar autorizações de saldo - 1x ao dia às 01:00
    'expirar-autorizacoes-saldo': {
        'task': 'apps.conta_digital.expirar_autorizacoes_saldo',
        'schedule': crontab(hour=1, minute=0),  # 01:00 todos os dias
        'options': {
            'expires': 3600,  # Expira em 1 hora
        }
    },
}

# Timezone (mesmo do Django)
app.conf.timezone = 'America/Sao_Paulo'

# Beat Scheduler: Verifica schedule a cada 30 minutos (padrão é 1 minuto)
# Reduz carga, já que tasks são diárias/semanais
app.conf.beat_schedule_filename = 'celerybeat-schedule'
app.conf.beat_max_loop_interval = 1800  # 1800 segundos = 30 minutos


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Task de debug para testar Celery."""
    print(f'Request: {self.request!r}')
