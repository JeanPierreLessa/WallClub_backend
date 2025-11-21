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

    # Cargas completas - De hora em hora, minuto 5, das 5h às 23h
    'cargas-completas-pinbank': {
        'task': 'pinbank.cargas_completas',
        'schedule': crontab(minute=5, hour='5-23'),  # xx:05 das 5h às 23h
        'options': {
            'expires': 3600,  # Expira em 1 hora
        }
    },

    # Migração financeiro → pagamentos_efetuados - De hora em hora, minuto 15
    'migrar-financeiro-pagamentos': {
        'task': 'pinbank.migrar_financeiro_pagamentos',
        'schedule': crontab(minute=15),  # xx:15 de hora em hora (24h)
        'kwargs': {'limite': 1000},  # Processar 1000 registros por vez
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
