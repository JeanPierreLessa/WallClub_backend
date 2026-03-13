"""
Views para integração Veriff (verificação de identidade)
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from apps.conta_digital.decorators import require_jwt_only
from wallclub_core.utilitarios.log_control import registrar_log
from .services import VeriffService


@api_view(['POST'])
@permission_classes([AllowAny])
@require_jwt_only
def criar_sessao_veriff(request):
    """
    POST /api/v1/cliente/veriff/criar_sessao/
    Cria sessão Veriff para o cliente autenticado.
    """
    try:
        from apps.cliente.models import Cliente
        cliente = Cliente.objects.get(id=request.user.cliente_id)

        resultado = VeriffService.criar_sessao(cliente)

        return Response({
            'sucesso': True,
            'dados': resultado,
        }, status=status.HTTP_200_OK)

    except Cliente.DoesNotExist:
        return Response({
            'sucesso': False,
            'erro': 'cliente_nao_encontrado',
            'mensagem': 'Cliente não encontrado',
        }, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        registrar_log('biometria', f'[VERIFF] Erro ao criar sessão: {str(e)}', nivel='ERROR')
        return Response({
            'sucesso': False,
            'erro': 'erro_criar_sessao',
            'mensagem': str(e),
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def webhook_veriff(request):
    """
    POST /api/v1/cliente/veriff/webhook/
    Recebe decisão do Veriff via webhook.
    Valida assinatura HMAC antes de processar.
    """
    signature = request.headers.get('X-HMAC-SIGNATURE', '')
    if not signature:
        registrar_log('biometria', '[VERIFF] Webhook sem assinatura HMAC', nivel='WARNING')
        return Response({'erro': 'assinatura_ausente'}, status=status.HTTP_401_UNAUTHORIZED)

    if not VeriffService.validar_hmac(request.body, signature):
        registrar_log('biometria', '[VERIFF] Webhook com assinatura HMAC inválida', nivel='WARNING')
        return Response({'erro': 'assinatura_invalida'}, status=status.HTTP_401_UNAUTHORIZED)

    sucesso = VeriffService.processar_webhook(request.data)

    if sucesso:
        return Response({'sucesso': True}, status=status.HTTP_200_OK)
    else:
        return Response({'sucesso': False}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
@require_jwt_only
def status_veriff(request, session_id):
    """
    GET /api/v1/cliente/veriff/status/{session_id}/
    Consulta status da verificação.
    """
    resultado = VeriffService.consultar_status(session_id, request.user.cliente_id)

    if resultado is None:
        return Response({
            'sucesso': False,
            'erro': 'sessao_nao_encontrada',
            'mensagem': 'Sessão não encontrada',
        }, status=status.HTTP_404_NOT_FOUND)

    return Response({
        'sucesso': True,
        'dados': resultado,
    }, status=status.HTTP_200_OK)
