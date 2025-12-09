"""
Celery tasks para ofertas
"""
from celery import shared_task
from datetime import datetime
from django.db import transaction

from apps.ofertas.models import Oferta
from apps.ofertas.services import OfertaService
from wallclub_core.utilitarios.log_control import registrar_log


@shared_task(name='apps.ofertas.processar_ofertas_agendadas')
def processar_ofertas_agendadas():
    """
    Task agendada para processar ofertas com disparo automático
    
    Busca ofertas com:
    - data_agendamento_disparo <= agora
    - disparada = False
    - ativo = True
    
    Executa disparo automático e marca como disparada
    
    Execução: A cada 5 minutos via Celery Beat
    """
    try:
        agora = datetime.now()
        
        # Buscar ofertas pendentes de disparo
        ofertas_pendentes = Oferta.objects.filter(
            data_agendamento_disparo__lte=agora,
            disparada=False,
            ativo=True
        ).select_for_update()
        
        total_processadas = 0
        total_sucesso = 0
        total_falhas = 0
        
        registrar_log('apps.ofertas.tasks', f'Processando ofertas agendadas: {ofertas_pendentes.count()} encontradas')
        
        for oferta in ofertas_pendentes:
            try:
                with transaction.atomic():
                    # Disparar push via service (usuario_disparador_id=None para automático)
                    sucesso, mensagem, disparo_id = OfertaService.disparar_push(
                        oferta_id=oferta.id,
                        usuario_disparador_id=None
                    )
                    
                    if sucesso:
                        # Marcar como disparada
                        oferta.disparada = True
                        oferta.save()
                        
                        total_sucesso += 1
                        registrar_log(
                            'apps.ofertas.tasks',
                            f'✅ Oferta {oferta.id} disparada automaticamente (disparo_id={disparo_id})'
                        )
                    else:
                        total_falhas += 1
                        registrar_log(
                            'apps.ofertas.tasks',
                            f'❌ Falha ao disparar oferta {oferta.id}: {mensagem}',
                            nivel='ERROR'
                        )
                    
                    total_processadas += 1
                    
            except Exception as e:
                total_falhas += 1
                registrar_log(
                    'apps.ofertas.tasks',
                    f'❌ Erro ao processar oferta {oferta.id}: {str(e)}',
                    nivel='ERROR'
                )
        
        # Log final
        if total_processadas > 0:
            registrar_log(
                'apps.ofertas.tasks',
                f'Processamento concluído: {total_processadas} ofertas ({total_sucesso} sucesso, {total_falhas} falhas)'
            )
        
        return {
            'sucesso': True,
            'total_processadas': total_processadas,
            'total_sucesso': total_sucesso,
            'total_falhas': total_falhas
        }
        
    except Exception as e:
        registrar_log('apps.ofertas.tasks', f'Erro crítico no processamento de ofertas: {str(e)}', nivel='ERROR')
        return {
            'sucesso': False,
            'erro': str(e)
        }
