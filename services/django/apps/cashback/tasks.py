from celery import shared_task
from datetime import datetime
from django.utils import timezone
from wallclub_core.utilitarios.log_control import registrar_log


@shared_task(name='cashback.liberar_cashback_retido')
def liberar_cashback_retido():
    """
    Task Celery para liberar cashback que completou período de retenção.
    Roda diariamente.
    """
    from apps.cashback.models import CashbackUso
    from apps.cashback.services import CashbackService
    
    from django.conf import settings
    from datetime import timedelta
    
    agora = timezone.now()
    periodo_retencao = settings.CASHBACK_PERIODO_RETENCAO_DIAS
    data_limite = agora - timedelta(days=periodo_retencao)
    
    # Buscar cashback retido que já completou o período de retenção
    # Critério: aplicado_em + periodo_retencao <= agora
    cashbacks = CashbackUso.objects.filter(
        status='RETIDO',
        aplicado_em__lte=data_limite
    )
    
    total = cashbacks.count()
    liberados = 0
    erros = 0
    
    registrar_log(
        'apps.cashback.tasks',
        f'Iniciando liberação de cashback retido - {total} registros encontrados'
    )
    
    for cashback in cashbacks:
        try:
            CashbackService.liberar_cashback(cashback.id)
            liberados += 1
        except Exception as e:
            erros += 1
            registrar_log(
                'apps.cashback.tasks',
                f'Erro ao liberar cashback {cashback.id}: {str(e)}',
                nivel='ERROR'
            )
    
    registrar_log(
        'apps.cashback.tasks',
        f'Liberação concluída - Total: {total}, Liberados: {liberados}, Erros: {erros}'
    )
    
    return {
        'total': total,
        'liberados': liberados,
        'erros': erros
    }


@shared_task(name='cashback.expirar_cashback_vencido')
def expirar_cashback_vencido():
    """
    Task Celery para expirar cashback que passou do prazo.
    Roda diariamente.
    """
    from apps.cashback.models import CashbackUso
    from apps.cashback.services import CashbackService
    
    agora = timezone.now()
    
    # Buscar cashback liberado que expirou
    cashbacks = CashbackUso.objects.filter(
        status='LIBERADO',
        expira_em__lte=agora
    )
    
    total = cashbacks.count()
    expirados = 0
    erros = 0
    
    registrar_log(
        'apps.cashback.tasks',
        f'Iniciando expiração de cashback vencido - {total} registros encontrados'
    )
    
    for cashback in cashbacks:
        try:
            CashbackService.expirar_cashback(cashback.id)
            expirados += 1
        except Exception as e:
            erros += 1
            registrar_log(
                'apps.cashback.tasks',
                f'Erro ao expirar cashback {cashback.id}: {str(e)}',
                nivel='ERROR'
            )
    
    registrar_log(
        'apps.cashback.tasks',
        f'Expiração concluída - Total: {total}, Expirados: {expirados}, Erros: {erros}'
    )
    
    return {
        'total': total,
        'expirados': expirados,
        'erros': erros
    }


@shared_task(name='cashback.resetar_gasto_mensal_lojas')
def resetar_gasto_mensal_lojas():
    """
    Task Celery para resetar gasto_mes_atual das regras de loja.
    Roda no primeiro dia de cada mês.
    """
    from apps.cashback.models import RegraCashbackLoja
    from decimal import Decimal
    
    regras = RegraCashbackLoja.objects.filter(
        ativo=True,
        orcamento_mensal__isnull=False
    )
    
    total = regras.count()
    
    registrar_log(
        'apps.cashback.tasks',
        f'Resetando gasto mensal de {total} regras de cashback loja'
    )
    
    regras.update(gasto_mes_atual=Decimal('0.00'))
    
    registrar_log(
        'apps.cashback.tasks',
        f'Gasto mensal resetado para {total} regras'
    )
    
    return {
        'total': total
    }
