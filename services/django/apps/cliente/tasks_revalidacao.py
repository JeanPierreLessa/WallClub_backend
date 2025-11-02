"""
Celery tasks para revalidação automática de celular.
Jobs executados periodicamente para enviar lembretes e alertas.
"""
from celery import shared_task
from wallclub_core.utilitarios.log_control import registrar_log
from .services_revalidacao_celular import RevalidacaoCelularService


@shared_task(name='apps.cliente.verificar_celulares_expirar')
def verificar_celulares_expirar():
    """
    Job executado DIARIAMENTE às 09:00.
    Verifica celulares próximos de expirar (7 dias antes) e envia lembretes.
    
    Configuração no Celery Beat:
    'verificar_celulares_expirar': {
        'task': 'apps.cliente.verificar_celulares_expirar',
        'schedule': crontab(hour=9, minute=0),
    }
    """
    try:
        registrar_log('apps.cliente', "Iniciando job de verificação de celulares próximos a expirar")
        
        # Listar clientes com celular expirando em 7 dias
        clientes = RevalidacaoCelularService.listar_clientes_proximos_expirar(dias_antes=7)
        
        registrar_log('apps.cliente', f"Encontrados {len(clientes)} clientes com celular próximo a expirar")
        
        enviados = 0
        erros = 0
        
        for cliente in clientes:
            try:
                # Calcular dias restantes
                dias_restantes = RevalidacaoCelularService.VALIDADE_DIAS - cliente['dias_desde_validacao']
                
                # Enviar lembrete
                sucesso = RevalidacaoCelularService.enviar_lembrete_revalidacao(
                    cliente_id=cliente['id'],
                    canal_id=cliente['canal_id'],
                    dias_restantes=dias_restantes
                )
                
                if sucesso:
                    enviados += 1
                else:
                    erros += 1
                    
            except Exception as e:
                erros += 1
                registrar_log('apps.cliente', 
                    f"Erro ao enviar lembrete para cliente {cliente['id']}: {str(e)}", 
                    nivel='ERROR')
        
        registrar_log('apps.cliente', 
            f"Job concluído: {enviados} lembretes enviados, {erros} erros")
        
        return {
            'sucesso': True,
            'total_clientes': len(clientes),
            'lembretes_enviados': enviados,
            'erros': erros
        }
        
    except Exception as e:
        registrar_log('apps.cliente', 
            f"Erro no job verificar_celulares_expirar: {str(e)}", 
            nivel='ERROR')
        return {
            'sucesso': False,
            'mensagem': str(e)
        }


@shared_task(name='apps.cliente.processar_celulares_expirados')
def processar_celulares_expirados():
    """
    Job executado DIARIAMENTE às 10:00.
    Verifica celulares já expirados e envia alertas críticos.
    
    Configuração no Celery Beat:
    'processar_celulares_expirados': {
        'task': 'apps.cliente.processar_celulares_expirados',
        'schedule': crontab(hour=10, minute=0),
    }
    """
    try:
        registrar_log('apps.cliente', "Iniciando job de processamento de celulares expirados")
        
        # Listar clientes com celular expirado
        clientes = RevalidacaoCelularService.listar_clientes_expirados()
        
        registrar_log('apps.cliente', f"Encontrados {len(clientes)} clientes com celular expirado")
        
        enviados = 0
        erros = 0
        
        for cliente in clientes:
            try:
                # Enviar alerta de expiração
                sucesso = RevalidacaoCelularService.enviar_alerta_expirado(
                    cliente_id=cliente['id'],
                    canal_id=cliente['canal_id']
                )
                
                if sucesso:
                    enviados += 1
                else:
                    erros += 1
                    
            except Exception as e:
                erros += 1
                registrar_log('apps.cliente', 
                    f"Erro ao enviar alerta para cliente {cliente['id']}: {str(e)}", 
                    nivel='ERROR')
        
        registrar_log('apps.cliente', 
            f"Job concluído: {enviados} alertas enviados, {erros} erros")
        
        return {
            'sucesso': True,
            'total_clientes': len(clientes),
            'alertas_enviados': enviados,
            'erros': erros
        }
        
    except Exception as e:
        registrar_log('apps.cliente', 
            f"Erro no job processar_celulares_expirados: {str(e)}", 
            nivel='ERROR')
        return {
            'sucesso': False,
            'mensagem': str(e)
        }
