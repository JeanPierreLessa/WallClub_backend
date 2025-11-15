"""
Celery tasks para cargas automáticas Own Financial
"""

from celery import shared_task
from datetime import datetime, timedelta
from wallclub_core.utilitarios.log_control import registrar_log


@shared_task(name='adquirente_own.carga_transacoes_diaria')
def carga_transacoes_own_diaria():
    """
    Carga diária de transações Own Financial
    Executa às 02:00 (após carga Pinbank)
    """
    from adquirente_own.cargas_own.services_carga_transacoes import CargaTransacoesOwnService
    
    registrar_log('own.tasks', '🚀 Iniciando task: carga_transacoes_own_diaria')
    
    try:
        service = CargaTransacoesOwnService()
        resultado = service.executar_carga_diaria()
        
        registrar_log('own.tasks', f'✅ Task concluída: {resultado}')
        
        return {
            'sucesso': True,
            'total_transacoes': resultado.get('total_transacoes', 0),
            'total_processadas': resultado.get('total_processadas', 0),
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        registrar_log('own.tasks', f'❌ Erro na task: {str(e)}', nivel='ERROR')
        return {
            'sucesso': False,
            'erro': str(e),
            'timestamp': datetime.now().isoformat()
        }


@shared_task(name='adquirente_own.carga_liquidacoes_diaria')
def carga_liquidacoes_own_diaria():
    """
    Carga diária de liquidações Own Financial
    Executa às 02:30 (após carga de transações)
    """
    from adquirente_own.cargas_own.services_carga_liquidacoes import CargaLiquidacoesOwnService
    
    registrar_log('own.tasks', '🚀 Iniciando task: carga_liquidacoes_own_diaria')
    
    try:
        service = CargaLiquidacoesOwnService()
        resultado = service.executar_carga_diaria()
        
        registrar_log('own.tasks', f'✅ Task concluída: {resultado}')
        
        return {
            'sucesso': True,
            'total_liquidacoes': resultado.get('total_liquidacoes', 0),
            'total_processadas': resultado.get('total_processadas', 0),
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        registrar_log('own.tasks', f'❌ Erro na task: {str(e)}', nivel='ERROR')
        return {
            'sucesso': False,
            'erro': str(e),
            'timestamp': datetime.now().isoformat()
        }


@shared_task(name='adquirente_own.carga_transacoes_periodo')
def carga_transacoes_own_periodo(cnpj_cliente: str, data_inicial: str, data_final: str):
    """
    Carga de transações por período específico
    
    Args:
        cnpj_cliente: CNPJ do cliente
        data_inicial: Data inicial (formato: YYYY-MM-DD)
        data_final: Data final (formato: YYYY-MM-DD)
    """
    from adquirente_own.cargas_own.services_carga_transacoes import CargaTransacoesOwnService
    
    registrar_log('own.tasks', f'🚀 Carga período: {data_inicial} a {data_final}')
    
    try:
        service = CargaTransacoesOwnService()
        
        # Converter strings para datetime
        dt_inicial = datetime.strptime(data_inicial, '%Y-%m-%d')
        dt_final = datetime.strptime(data_final, '%Y-%m-%d')
        
        # Buscar transações
        result = service.buscar_transacoes_gerais(
            cnpj_cliente=cnpj_cliente,
            data_inicial=dt_inicial,
            data_final=dt_final
        )
        
        if not result.get('sucesso'):
            return {
                'sucesso': False,
                'mensagem': result.get('mensagem')
            }
        
        # Processar transações
        total_processadas = 0
        for transacao_data in result.get('transacoes', []):
            transacao_obj = service.salvar_transacao(transacao_data)
            if not transacao_obj.processado:
                service.processar_para_base_gestao(transacao_obj)
                total_processadas += 1
        
        registrar_log('own.tasks', f'✅ Período processado: {total_processadas} transações')
        
        return {
            'sucesso': True,
            'total_transacoes': result.get('total', 0),
            'total_processadas': total_processadas
        }
        
    except Exception as e:
        registrar_log('own.tasks', f'❌ Erro: {str(e)}', nivel='ERROR')
        return {
            'sucesso': False,
            'erro': str(e)
        }


@shared_task(name='adquirente_own.sincronizar_status_pagamentos')
def sincronizar_status_pagamentos_own():
    """
    Sincroniza status de pagamentos pendentes
    Executa a cada 6 horas
    """
    from adquirente_own.cargas_own.models import OwnExtratoTransacoes
    from adquirente_own.cargas_own.services_carga_liquidacoes import CargaLiquidacoesOwnService
    
    registrar_log('own.tasks', '🚀 Sincronizando status de pagamentos')
    
    try:
        service = CargaLiquidacoesOwnService()
        
        # Buscar transações com pagamento pendente (últimos 30 dias)
        data_limite = datetime.now() - timedelta(days=30)
        
        transacoes_pendentes = OwnExtratoTransacoes.objects.filter(
            data__gte=data_limite,
            statusPagamento__isnull=True
        ).values_list('cnpjCpfCliente', flat=True).distinct()
        
        total_sincronizadas = 0
        
        for cnpj in transacoes_pendentes:
            # Consultar liquidações dos últimos 7 dias
            for dias_atras in range(7):
                data_consulta = datetime.now() - timedelta(days=dias_atras)
                
                result = service.consultar_liquidacoes(
                    cnpj_cliente=cnpj,
                    data_pagamento_real=data_consulta
                )
                
                if result.get('sucesso'):
                    for liquidacao_data in result.get('liquidacoes', []):
                        liquidacao_obj = service.salvar_liquidacao(liquidacao_data)
                        if service.atualizar_status_transacao(liquidacao_obj):
                            total_sincronizadas += 1
        
        registrar_log('own.tasks', f'✅ Sincronização concluída: {total_sincronizadas} atualizações')
        
        return {
            'sucesso': True,
            'total_sincronizadas': total_sincronizadas
        }
        
    except Exception as e:
        registrar_log('own.tasks', f'❌ Erro: {str(e)}', nivel='ERROR')
        return {
            'sucesso': False,
            'erro': str(e)
        }
