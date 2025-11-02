"""
Celery Tasks para Recorrência
Fase 6B - Movido para checkout/

Processa cobranças recorrentes agendadas automaticamente.
Tasks devem rodar no container APP3 (onde models de checkout estão)
"""
from celery import shared_task
from django.db.models import Q
from datetime import datetime, timedelta
from decimal import Decimal
import logging

from checkout.models import CheckoutTransaction
from wallclub_core.utilitarios.log_control import registrar_log

logger = logging.getLogger('checkout.recorrencia')


@shared_task
def processar_recorrencias_do_dia():
    """
    Task periódica (diária às 08:00) que processa cobranças recorrentes agendadas para hoje.
    
    Busca todas recorrências:
    - is_recorrente=True
    - status_recorrencia='ativo'
    - proxima_cobranca = hoje
    
    Processa cada cobrança via CheckoutVendasService.processar_cobranca_agendada()
    """
    logger.info("🔄 Iniciando processamento de recorrências do dia...")
    registrar_log('portais.vendas.recorrencia.task', "Task processar_recorrencias_do_dia iniciada")
    
    try:
        hoje = datetime.now().date()
        
        # Buscar recorrências agendadas para hoje
        from checkout.models_recorrencia import RecorrenciaAgendada
        
        recorrencias = RecorrenciaAgendada.objects.filter(
            status='ativo',
            proxima_cobranca=hoje
        ).select_related('cliente', 'cartao_tokenizado', 'loja')
        
        total = recorrencias.count()
        logger.info(f"📊 Total de recorrências agendadas para hoje: {total}")
        
        if total == 0:
            registrar_log('portais.vendas.recorrencia.task', "Nenhuma recorrência agendada para hoje")
            return {
                'success': True,
                'total': 0,
                'processadas': 0,
                'aprovadas': 0,
                'negadas': 0,
                'erros': 0,
                'timestamp': datetime.now().isoformat()
            }
        
        processadas = 0
        aprovadas = 0
        negadas = 0
        erros = 0
        
        for rec in recorrencias:
            try:
                logger.info(f"💳 Processando recorrência ID={rec.id} - Cliente: {rec.cliente.nome if rec.cliente else 'N/A'}")
                
                # Processar via service (lazy import para evitar circular)
                from portais.vendas.services import CheckoutVendasService
                resultado = CheckoutVendasService.processar_cobranca_agendada(rec.id)
                
                processadas += 1
                
                if resultado['sucesso']:
                    aprovadas += 1
                    logger.info(f"✅ Recorrência ID={rec.id} APROVADA - NSU: {resultado.get('nsu')}")
                else:
                    negadas += 1
                    logger.warning(f"❌ Recorrência ID={rec.id} NEGADA - {resultado['mensagem']}")
                    
                    # Se atingiu limite de tentativas, será marcado como hold automaticamente
                    if resultado.get('tentativas', 0) >= rec.max_tentativas:
                        logger.warning(f"🛑 Recorrência ID={rec.id} atingiu limite de tentativas. Marcando como HOLD.")
                        from portais.vendas.services import CheckoutVendasService
                        CheckoutVendasService.marcar_hold(rec.id)
                    else:
                        # Agendar retry
                        from portais.vendas.services import CheckoutVendasService
                        CheckoutVendasService.retentar_cobranca(rec.id)
                
            except Exception as e:
                erros += 1
                logger.error(f"❌ Erro ao processar recorrência ID={rec.id}: {str(e)}")
                registrar_log(
                    'portais.vendas.recorrencia.task',
                    f"Erro ao processar recorrência ID={rec.id}: {str(e)}",
                    nivel='ERROR'
                )
        
        # Log final
        logger.info(
            f"✅ Processamento concluído | "
            f"Total: {total} | Processadas: {processadas} | "
            f"Aprovadas: {aprovadas} | Negadas: {negadas} | Erros: {erros}"
        )
        
        registrar_log(
            'portais.vendas.recorrencia.task',
            f"Task concluída: {processadas}/{total} processadas, {aprovadas} aprovadas, {negadas} negadas, {erros} erros"
        )
        
        return {
            'success': True,
            'total': total,
            'processadas': processadas,
            'aprovadas': aprovadas,
            'negadas': negadas,
            'erros': erros,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Erro fatal na task processar_recorrencias_do_dia: {str(e)}")
        registrar_log(
            'portais.vendas.recorrencia.task',
            f"Erro fatal: {str(e)}",
            nivel='ERROR'
        )
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def retentar_cobrancas_falhadas():
    """
    Task periódica (diária às 10:00) que retenta cobranças que falharam.
    
    Busca recorrências com:
    - is_recorrente=True
    - status_recorrencia='ativo'
    - tentativas_retry > 0
    - tentativas_retry < max_tentativas
    - proxima_cobranca = hoje (agenda com backoff: D+1, D+3, D+7)
    """
    logger.info("🔁 Iniciando retry de cobranças falhadas...")
    registrar_log('portais.vendas.recorrencia.task', "Task retentar_cobrancas_falhadas iniciada")
    
    try:
        hoje = datetime.now().date()
        
        # Buscar recorrências com falhas agendadas para retry hoje
        from checkout.models_recorrencia import RecorrenciaAgendada
        
        recorrencias_retry = RecorrenciaAgendada.objects.filter(
            status='ativo',
            proxima_cobranca=hoje,
            tentativas_falhas_consecutivas__gt=0,
            tentativas_falhas_consecutivas__lt=3  # Menos que max_tentativas
        ).select_related('cliente', 'cartao_tokenizado', 'loja')
        
        total = recorrencias_retry.count()
        logger.info(f"📊 Total de retries agendados para hoje: {total}")
        
        if total == 0:
            registrar_log('portais.vendas.recorrencia.task', "Nenhum retry agendado para hoje")
            return {
                'success': True,
                'total': 0,
                'processadas': 0,
                'aprovadas': 0,
                'hold': 0,
                'timestamp': datetime.now().isoformat()
            }
        
        processadas = 0
        aprovadas = 0
        hold = 0
        
        for rec in recorrencias_retry:
            try:
                tentativa_atual = rec.tentativas_retry + 1
                logger.info(
                    f"🔄 Retry {tentativa_atual}/{rec.max_tentativas} - "
                    f"Recorrência ID={rec.id} - Cliente: {rec.cliente.nome if rec.cliente else 'N/A'}"
                )
                
                # Processar cobrança (lazy import)
                from portais.vendas.services import CheckoutVendasService
                resultado = CheckoutVendasService.processar_cobranca_agendada(rec.id)
                
                processadas += 1
                
                if resultado['sucesso']:
                    aprovadas += 1
                    logger.info(f"✅ Retry bem-sucedido ID={rec.id} - NSU: {resultado.get('nsu')}")
                else:
                    # Verificar se atingiu limite
                    rec.refresh_from_db()
                    if rec.tentativas_retry >= rec.max_tentativas:
                        hold += 1
                        from portais.vendas.services import CheckoutVendasService
                        CheckoutVendasService.marcar_hold(rec.id)
                        logger.warning(f"🛑 Recorrência ID={rec.id} marcada como HOLD após {rec.tentativas_retry} tentativas")
                    else:
                        # Agendar próximo retry com backoff
                        from portais.vendas.services import CheckoutVendasService
                        CheckoutVendasService.retentar_cobranca(rec.id)
                        logger.info(f"📅 Próximo retry agendado para recorrência ID={rec.id}")
                
            except Exception as e:
                logger.error(f"❌ Erro no retry da recorrência ID={rec.id}: {str(e)}")
                registrar_log(
                    'portais.vendas.recorrencia.task',
                    f"Erro no retry ID={rec.id}: {str(e)}",
                    nivel='ERROR'
                )
        
        # Log final
        logger.info(
            f"✅ Retry concluído | "
            f"Total: {total} | Processadas: {processadas} | "
            f"Aprovadas: {aprovadas} | Hold: {hold}"
        )
        
        registrar_log(
            'portais.vendas.recorrencia.task',
            f"Task retry concluída: {processadas}/{total} processadas, {aprovadas} aprovadas, {hold} em hold"
        )
        
        return {
            'success': True,
            'total': total,
            'processadas': processadas,
            'aprovadas': aprovadas,
            'hold': hold,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Erro fatal na task retentar_cobrancas_falhadas: {str(e)}")
        registrar_log(
            'portais.vendas.recorrencia.task',
            f"Erro fatal no retry: {str(e)}",
            nivel='ERROR'
        )
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def notificar_recorrencias_hold():
    """
    Task periódica (diária às 18:00) que notifica vendedores sobre recorrências em HOLD.
    
    Recorrências em HOLD requerem intervenção manual:
    - Atualizar cartão
    - Contatar cliente
    - Reativar manualmente
    """
    logger.info("📧 Iniciando notificação de recorrências em HOLD...")
    registrar_log('portais.vendas.recorrencia.task', "Task notificar_recorrencias_hold iniciada")
    
    try:
        # Buscar recorrências em hold
        from checkout.models_recorrencia import RecorrenciaAgendada
        
        recorrencias_hold = RecorrenciaAgendada.objects.filter(
            status='hold'
        ).select_related('cliente', 'loja').values(
            'id',
            'vendedor_id',
            'cliente__nome',
            'cliente__cpf',
            'valor_recorrencia',
            'tentativas_falhas_consecutivas',
            'ultima_tentativa_em',
            'loja__nome'
        )
        
        total = len(recorrencias_hold)
        logger.info(f"📊 Total de recorrências em HOLD: {total}")
        
        if total == 0:
            registrar_log('portais.vendas.recorrencia.task', "Nenhuma recorrência em HOLD para notificar")
            return {
                'success': True,
                'total': 0,
                'notificacoes_enviadas': 0,
                'timestamp': datetime.now().isoformat()
            }
        
        # Agrupar por vendedor
        vendedores_notificar = {}
        for rec in recorrencias_hold:
            vendedor_id = rec['vendedor_id']
            if vendedor_id not in vendedores_notificar:
                vendedores_notificar[vendedor_id] = []
            vendedores_notificar[vendedor_id].append(rec)
        
        notificacoes_enviadas = 0
        
        # Enviar notificação por vendedor
        for vendedor_id, recorrencias in vendedores_notificar.items():
            try:
                # TODO: Implementar envio de notificação (email, SMS, push)
                # Por enquanto, apenas registrar log
                
                logger.info(
                    f"📧 Vendedor ID={vendedor_id}: {len(recorrencias)} recorrências em HOLD"
                )
                
                registrar_log(
                    'portais.vendas.recorrencia.notificacao',
                    f"Vendedor ID={vendedor_id} possui {len(recorrencias)} recorrências em HOLD",
                    nivel='WARNING'
                )
                
                # Lista de recorrências para o log
                for rec in recorrencias[:5]:  # Primeiras 5
                    logger.warning(
                        f"  - ID={rec['id']}: {rec['cliente__nome']} | "
                        f"R$ {rec['valor_recorrencia']} | "
                        f"{rec['tentativas_falhas_consecutivas']} tentativas"
                    )
                
                notificacoes_enviadas += 1
                
            except Exception as e:
                logger.error(f"❌ Erro ao notificar vendedor ID={vendedor_id}: {str(e)}")
        
        logger.info(f"✅ Notificações concluídas: {notificacoes_enviadas} vendedores notificados")
        
        registrar_log(
            'portais.vendas.recorrencia.task',
            f"Task notificação concluída: {notificacoes_enviadas} vendedores notificados sobre {total} recorrências em hold"
        )
        
        return {
            'success': True,
            'total': total,
            'notificacoes_enviadas': notificacoes_enviadas,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Erro fatal na task notificar_recorrencias_hold: {str(e)}")
        registrar_log(
            'portais.vendas.recorrencia.task',
            f"Erro fatal na notificação: {str(e)}",
            nivel='ERROR'
        )
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def limpar_recorrencias_antigas():
    """
    Task periódica (semanal) que marca recorrências muito antigas como 'concluido'.
    
    Critério: recorrências ativas sem cobrança há mais de 180 dias.
    """
    logger.info("🧹 Iniciando limpeza de recorrências antigas...")
    
    try:
        limite = datetime.now().date() - timedelta(days=180)
        
        # Buscar recorrências ativas muito antigas
        from checkout.models_recorrencia import RecorrenciaAgendada
        
        recorrencias_antigas = RecorrenciaAgendada.objects.filter(
            status='ativo',
            proxima_cobranca__lt=limite
        )
        
        total = recorrencias_antigas.count()
        
        if total > 0:
            # Marcar como concluído
            recorrencias_antigas.update(status='concluido')
            
            logger.info(f"✅ {total} recorrências antigas marcadas como concluído")
            registrar_log(
                'portais.vendas.recorrencia.task',
                f"Limpeza: {total} recorrências antigas marcadas como concluído"
            )
        else:
            logger.info("✅ Nenhuma recorrência antiga para limpar")
        
        return {
            'success': True,
            'total_limpas': total,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Erro na limpeza de recorrências: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }
