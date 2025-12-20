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
    Task para executar carga de extrato POS
    
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


@shared_task(bind=True, name='pinbank.carga_base_gestao')
def carga_base_gestao_task(self, limite=10000):
    """
    Task para executar carga base gestão (recálculo de variáveis)
    
    Args:
        limite: Número máximo de registros a processar
    """
    try:
        logger.info(f"[{datetime.now()}] Iniciando carga base gestão - limite: {limite}")
        call_command('carga_base_gestao', f'--limite={limite}')
        logger.info(f"[{datetime.now()}] Carga base gestão concluída com sucesso")
        return {'status': 'success', 'limite': limite}
    except Exception as e:
        logger.error(f"[{datetime.now()}] Erro na carga base gestão: {str(e)}")
        raise



@shared_task(bind=True, name='pinbank.ajustes_manuais_base')
def ajustes_manuais_base_task(self):
    """
    Task para executar ajustes manuais de base
    """
    try:
        logger.info(f"[{datetime.now()}] Iniciando ajustes manuais de base")
        call_command('ajustes_manuais_base')
        logger.info(f"[{datetime.now()}] Ajustes manuais concluídos com sucesso")
        return {'status': 'success'}
    except Exception as e:
        logger.error(f"[{datetime.now()}] Erro nos ajustes manuais: {str(e)}")
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


@shared_task(bind=True, name='pinbank.carga_credenciadora')
def carga_credenciadora_task(self):
    """
    Task para executar carga de credenciadora
    """
    try:
        logger.info(f"[{datetime.now()}] Iniciando carga credenciadora")
        call_command('carga_credenciadora')
        logger.info(f"[{datetime.now()}] Carga credenciadora concluída com sucesso")
        return {'status': 'success'}
    except Exception as e:
        logger.error(f"[{datetime.now()}] Erro na carga credenciadora: {str(e)}")
        raise


@shared_task(bind=True, name='pinbank.migrar_financeiro_pagamentos')
def migrar_financeiro_pagamentos_task(self, limite=1000):
    """
    Task para migrar dados de wclub.financeiro para wallclub.pagamentos_efetuados
    
    Args:
        limite: Número máximo de registros a processar por execução (padrão: 1000)
    """
    try:
        logger.info(f"[{datetime.now()}] Iniciando migração financeiro → pagamentos_efetuados - limite: {limite}")
        call_command('migrar_financeiro_pagamentos', f'--limite={limite}')
        logger.info(f"[{datetime.now()}] Migração financeiro → pagamentos_efetuados concluída com sucesso")
        return {'status': 'success', 'limite': limite}
    except Exception as e:
        logger.error(f"[{datetime.now()}] Erro na migração financeiro → pagamentos_efetuados: {str(e)}")
        raise


@shared_task(bind=True, name='pinbank.carga_base_unificada', soft_time_limit=7200, time_limit=7500)
def carga_base_unificada_task(self):
    """
    Task para executar carga completa da Base Unificada (POS + Credenciadora)
    Processa transações de outubro/2025 em diante
    Limite: 1000 registros por execução
    Timeout: 2 horas
    """
    from django_redis import get_redis_connection
    
    redis_conn = get_redis_connection("default")
    lock_key = "lock:carga_base_unificada"
    lock_timeout = 7200  # 2 horas
    
    # Tentar adquirir lock
    if not redis_conn.set(lock_key, "locked", nx=True, ex=lock_timeout):
        logger.warning(f"[{datetime.now()}] Carga Base Unificada já está em execução. Pulando...")
        return {'status': 'skipped', 'reason': 'already_running'}
    
    try:
        logger.info(f"[{datetime.now()}] Iniciando carga Base Unificada (POS + Credenciadora) - limite 1000")
        call_command('carga_base_unificada', limite=1000)
        logger.info(f"[{datetime.now()}] Carga Base Unificada concluída com sucesso")
        return {'status': 'success'}
    except Exception as e:
        logger.error(f"[{datetime.now()}] Erro na carga Base Unificada: {str(e)}")
        raise
    finally:
        # Liberar lock
        redis_conn.delete(lock_key)
