"""
Views para transacoes - protegidas por JWT Token
"""
from datetime import datetime
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from wallclub_core.utilitarios.log_control import registrar_log
from wallclub_core.oauth.decorators import require_oauth_apps
from apps.conta_digital.decorators import require_jwt_only
from .services import TransacaoService

from .serializers import (
    ExtratoRequestSerializer, 
    SaldoResponseSerializer,
    ExtratoResponseSerializer,
    ComprovanteResponseSerializer
)
# Removido comum.autenticacao - app deve ser independente


@api_view(['POST'])
@require_jwt_only
def saldo(request):
    """
    Endpoint para consulta de saldo - MIGRADO DO saldo.php
    
    Headers obrigatórios:
    - X-API-Key: <api_key>
    - Authorization: Bearer <jwt_token>
    """
    try:
        # Dados extraídos do JWT customizado
        cliente_id = request.user.cliente_id
        canal_id = getattr(request.user, 'canal_id', 1)  # Canal do token JWT
        
        
        # Consultar saldo via service (retorna 0 igual ao PHP)
        resultado = TransacaoService.consultar_saldo(cliente_id, canal_id)
        
        
        # Retorno no formato JSON padrão
        return Response(resultado, status=status.HTTP_200_OK)
            
    except Exception as e:
        registrar_log('apps.transacoes', f"Erro ao consultar saldo: {str(e)}", nivel='ERROR')
        return Response({
            'sucesso': False,
            'saldo': 0.00,
            'mensagem': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@require_jwt_only
def extrato(request):
    """
    Endpoint para consulta de extrato - MIGRADO DO extrato.php
    
    Headers obrigatórios:
    - X-API-Key: <api_key>
    - Authorization: Bearer <jwt_token>
    """
    try:
        # Dados extraídos do JWT customizado
        cliente_id = request.user.cliente_id
        
        
        # Parâmetros opcionais (se não informados, usa período padrão)
        serializer = ExtratoRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'sucesso': False,
                'mensagem': 'Dados inválidos',
                'erros': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        dt_inicio = serializer.validated_data.get('data_inicio')
        dt_fim = serializer.validated_data.get('data_fim')
        
        
        # Chamar service com lógica EXATA do PHP usando cliente_id correto
        service = TransacaoService()
        resultado = service.consultar_extrato(
            cliente_id, dt_inicio, dt_fim
        )
        
        
        # Retorno padronizado (sempre JSON com sucesso/mensagem)
        return Response(resultado, status=status.HTTP_200_OK)
            
    except Exception as e:
        registrar_log('apps.transacoes', f"Erro ao consultar extrato: {str(e)}", nivel='ERROR')
        return Response({
            'sucesso': False,
            'mensagem': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@require_jwt_only
def comprovante(request):
    """
    Endpoint para geração de comprovante - FUNCIONANDO!
    
    Headers obrigatórios:
    - X-API-Key: <api_key>
    - Authorization: Bearer <jwt_token>
    """
    try:
        # Dados extraídos do JWT customizado
        cliente_id = request.user.cliente_id
        
        # Validar parâmetro obrigatório
        nsu_pinbank = request.data.get('nsu_pinbank')
        if not nsu_pinbank:
            return Response({
                'sucesso': False,
                'mensagem': 'NSU Pinbank é obrigatório'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        
        # Gerar comprovante via service
        service = TransacaoService()
        resultado = service.gerar_comprovante(nsu_pinbank, cliente_id)
        
        
        return Response(resultado, status=status.HTTP_200_OK)
        
    except Exception as e:
        registrar_log('apps.transacoes', f"Erro ao gerar comprovante: {str(e)}", nivel='ERROR')
        return Response({
            'sucesso': False,
            'mensagem': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
