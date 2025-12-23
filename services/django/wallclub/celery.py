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
    # RECORRÊNCIAS (Fase 5) - DESABILITADAS
    # ============================================
    # Tasks de recorrência definidas mas não agendadas:
    # - portais.vendas.tasks_recorrencia.processar_recorrencias_do_dia
    # - portais.vendas.tasks_recorrencia.retentar_cobrancas_falhadas
    # - portais.vendas.tasks_recorrencia.notificar_recorrencias_hold
    # - portais.vendas.tasks_recorrencia.limpar_recorrencias_antigas

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

    # Cargas completas - A cada 30 minutos
    'cargas-completas-pinbank': {
        'task': 'pinbank.cargas_completas',
        'schedule': crontab(minute='*/30'),  # A cada 30 minutos
        'options': {
            'expires': 1800,  # Expira em 30 minutos
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

    # ============================================
    # CASHBACK - LIBERAÇÃO E EXPIRAÇÃO
    # ============================================

    # Liberar cashback retido - 1x ao dia às 02:00
    'liberar-cashback-retido': {
        'task': 'cashback.liberar_cashback_retido',
        'schedule': crontab(hour=2, minute=0),  # 02:00 todos os dias
        'options': {
            'expires': 3600,  # Expira em 1 hora
        }
    },

    # Expirar cashback vencido - 1x ao dia às 03:00
    'expirar-cashback-vencido': {
        'task': 'cashback.expirar_cashback_vencido',
        'schedule': crontab(hour=3, minute=0),  # 03:00 todos os dias
        'options': {
            'expires': 3600,  # Expira em 1 hora
        }
    },

    # Resetar gasto mensal das lojas - 1x ao mês no dia 1 às 04:00
    'resetar-gasto-mensal-lojas': {
        'task': 'cashback.resetar_gasto_mensal_lojas',
        'schedule': crontab(hour=4, minute=0, day_of_month=1),  # 04:00 dia 1 de cada mês
        'options': {
            'expires': 3600,  # Expira em 1 hora
        }
    },

    # ============================================
    # OFERTAS - DISPARO AUTOMÁTICO
    # ============================================

    # Processar ofertas agendadas - A cada 30 minutos
    'processar-ofertas-agendadas': {
        'task': 'apps.ofertas.processar_ofertas_agendadas',
        'schedule': crontab(minute='*/30'),  # A cada 30 minutos
        'options': {
            'expires': 1800,  # Expira em 30 minutos
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
