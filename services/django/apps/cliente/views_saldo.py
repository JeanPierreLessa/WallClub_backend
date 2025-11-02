"""
Views para gerenciamento de saldo do cliente via app móvel.
Endpoints para aprovar/negar uso de saldo solicitado pelo POS.
"""
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from wallclub_core.oauth.decorators import require_oauth_apps
from apps.conta_digital.decorators import require_jwt_only
from wallclub_core.utilitarios.log_control import registrar_log


@api_view(['POST'])
@require_jwt_only
def aprovar_uso_saldo(request):
    """
    Cliente aprova uso de saldo solicitado pelo POS.
    """
    try:
        from apps.conta_digital.services_autorizacao import AutorizacaoService
        
        autorizacao_id = request.data.get('autorizacao_id')
        
        if not autorizacao_id:
            return Response({
                'sucesso': False,
                'mensagem': 'Parâmetro obrigatório: autorizacao_id'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        cliente_id = request.user.cliente_id
        
        resultado = AutorizacaoService.aprovar_autorizacao(
            autorizacao_id=autorizacao_id,
            cliente_id=cliente_id
        )
        
        if not resultado['sucesso']:
            return Response({
                'sucesso': False,
                'mensagem': resultado['mensagem']
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'sucesso': True,
            'mensagem': resultado['mensagem'],
            'valor_bloqueado': resultado.get('valor_bloqueado'),
            'expira_em': resultado.get('expira_em')
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        registrar_log('apps.cliente', f"❌ Erro ao aprovar uso de saldo: {str(e)}", nivel='ERROR')
        return Response({
            'sucesso': False,
            'mensagem': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@require_jwt_only
def negar_uso_saldo(request):
    """
    Cliente nega uso de saldo solicitado pelo POS.
    """
    try:
        from apps.conta_digital.services_autorizacao import AutorizacaoService
        
        autorizacao_id = request.data.get('autorizacao_id')
        
        if not autorizacao_id:
            return Response({
                'sucesso': False,
                'mensagem': 'Parâmetro obrigatório: autorizacao_id'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        cliente_id = request.user.cliente_id
        
        resultado = AutorizacaoService.negar_autorizacao(
            autorizacao_id=autorizacao_id,
            cliente_id=cliente_id
        )
        
        if not resultado['sucesso']:
            return Response({
                'sucesso': False,
                'mensagem': resultado['mensagem']
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'sucesso': True,
            'mensagem': resultado['mensagem']
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        registrar_log('apps.cliente', f"❌ Erro ao negar uso de saldo: {str(e)}", nivel='ERROR')
        return Response({
            'sucesso': False,
            'mensagem': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@require_jwt_only
def verificar_autorizacao(request):
    """
    Cliente verifica status de autorização de uso de saldo.
    """
    try:
        from apps.conta_digital.services_autorizacao import AutorizacaoService
        
        autorizacao_id = request.data.get('autorizacao_id')
        
        if not autorizacao_id:
            return Response({
                'sucesso': False,
                'mensagem': 'Parâmetro obrigatório: autorizacao_id'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        resultado = AutorizacaoService.verificar_autorizacao(autorizacao_id)
        
        if not resultado.get('sucesso', True):
            return Response({
                'sucesso': False,
                'mensagem': resultado.get('mensagem', 'Erro desconhecido')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'sucesso': True,
            'status': resultado['status'],
            'valor_bloqueado': resultado.get('valor_bloqueado'),
            'pode_processar': resultado.get('pode_processar')
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        registrar_log('apps.cliente', f"❌ Erro ao verificar autorização: {str(e)}", nivel='ERROR')
        return Response({
            'sucesso': False,
            'mensagem': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
