"""
Tasks Celery para Conta Digital
"""
from celery import shared_task
from django.core.management import call_command
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='apps.conta_digital.expirar_autorizacoes_saldo')
def expirar_autorizacoes_saldo_task(self):
    """
    Task para expirar autorizações de uso de saldo pendentes/aprovadas
    Executa a cada 1 minuto
    """
    try:
        logger.info(f"[{datetime.now()}] Iniciando expiração de autorizações de saldo")
        call_command('expirar_autorizacoes_saldo')
        logger.info(f"[{datetime.now()}] Expiração de autorizações concluída com sucesso")
        return {'status': 'success'}
    except Exception as e:
        logger.error(f"[{datetime.now()}] Erro ao expirar autorizações: {str(e)}")
        raise
