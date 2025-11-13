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


@shared_task(bind=True, name='pinbank.carga_tef')
def carga_tef_task(self, limite=10000):
    """
    Task para executar carga TEF (transações sem transactiondata)
    
    Args:
        limite: Número máximo de registros a processar
    """
    try:
        logger.info(f"[{datetime.now()}] Iniciando carga TEF - limite: {limite}")
        call_command('carga_tef', f'--limite={limite}')
        logger.info(f"[{datetime.now()}] Carga TEF concluída com sucesso")
        return {'status': 'success', 'limite': limite}
    except Exception as e:
        logger.error(f"[{datetime.now()}] Erro na carga TEF: {str(e)}")
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


@shared_task(bind=True, name='pinbank.cargas_completas')
def cargas_completas_task(self):
    """
    Task que executa todas as cargas sequencialmente
    """
    try:
        logger.info(f"[{datetime.now()}] 🚀 Iniciando cargas completas sequenciais")
        
        # Executar cargas em sequência
        logger.info("📋 Etapa 1/4 - Carga extrato POS")
        carga_extrato_pos_task(periodo='80min')
        
        logger.info("📋 Etapa 2/4 - Carga base gestão")
        carga_base_gestao_task(limite=10000)
        
        logger.info("📋 Etapa 3/4 - Carga TEF")
        carga_tef_task(limite=10000)
        
        logger.info("📋 Etapa 4/4 - Ajustes manuais")
        ajustes_manuais_base_task()
        
        logger.info(f"[{datetime.now()}] 🎉 Todas as cargas executadas com sucesso!")
        return {'status': 'success', 'etapas': 4}
        
    except Exception as e:
        logger.error(f"[{datetime.now()}] ⚠️ Erro nas cargas completas: {str(e)}")
        raise


@shared_task(bind=True, name='pinbank.carga_checkout')
def carga_checkout_task(self):
    """
    Task para executar carga de checkout
    """
    try:
        logger.info(f"[{datetime.now()}] Iniciando carga checkout")
        call_command('carga_checkout')
        logger.info(f"[{datetime.now()}] Carga checkout concluída com sucesso")
        return {'status': 'success'}
    except Exception as e:
        logger.error(f"[{datetime.now()}] Erro na carga checkout: {str(e)}")
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
