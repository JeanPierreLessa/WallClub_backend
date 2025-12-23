"""
Tasks Celery para cargas automáticas do Pinbank
"""
from celery import shared_task
from django.core.management import call_command
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='pinbank.carga_extrato_pos')
def carga_extrato_pos_task(self, periodo='80min'):
    """
    Task para executar carga de extrato POS (busca transações da API Pinbank)

    Args:
        periodo: Período para buscar transações (ex: '80min', '2h', '1d')
    """
    try:
        logger.info(f"[{datetime.now()}] Iniciando carga extrato POS - período: {periodo}")
        call_command('carga_extrato_pos', periodo)
        logger.info(f"[{datetime.now()}] Carga extrato POS concluída com sucesso")
        return {'status': 'success', 'periodo': periodo}
    except Exception as e:
        logger.error(f"[{datetime.now()}] Erro na carga extrato POS: {str(e)}")
        raise


@shared_task(bind=True, name='pinbank.cargas_completas', soft_time_limit=1800, time_limit=2400)
def cargas_completas_task(self):
    """
    Task que executa o script executar_cargas_completas.py
    """
    import subprocess
    import sys

    try:
        logger.info(f"[{datetime.now()}] 🚀 Executando script de cargas completas")

        # Executar script Python
        result = subprocess.run(
            [sys.executable, '/app/pinbank/cargas_pinbank/executar_cargas_completas.py'],
            capture_output=True,
            text=True,
            cwd='/app'
        )

        if result.returncode == 0:
            logger.info(f"[{datetime.now()}] 🎉 Script executado com sucesso")
            logger.info(result.stdout)
            return {'status': 'success', 'output': result.stdout}
        else:
            logger.error(f"[{datetime.now()}] ❌ Erro ao executar script")
            logger.error(result.stderr)
            raise Exception(f"Script falhou: {result.stderr}")

    except Exception as e:
        logger.error(f"[{datetime.now()}] ⚠️ Erro nas cargas completas: {str(e)}")
        raise
