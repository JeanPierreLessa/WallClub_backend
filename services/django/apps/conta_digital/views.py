"""
Views/APIs para o sistema de conta digital.
"""
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from wallclub_core.oauth.decorators import require_oauth_apps
from apps.conta_digital.decorators import require_jwt_only
from apps.cliente.jwt_cliente import ClienteJWTAuthentication
from rest_framework.decorators import authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import permission_classes
from wallclub_core.utilitarios.log_control import registrar_log
from .services import ContaDigitalService
from .serializers import (
    SaldoSerializer, CreditarSerializer, DebitarSerializer,
    BloquearSaldoSerializer, DesbloquearSaldoSerializer,
    EstornarSerializer, ExtratoFiltroSerializer,
    MovimentacaoResponseSerializer, ExtratoSerializer
)


@api_view(['POST'])
@require_jwt_only
def saldo(request):
    """
    Consulta saldo da conta digital do cliente.
    """
    try:
        cliente_id = request.user.cliente_id
        canal_id = getattr(request.user, 'canal_id', 1)
        
        saldo_info = ContaDigitalService.obter_saldo(cliente_id, canal_id)
        serializer = SaldoSerializer(saldo_info)
        
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        registrar_log('apps.conta_digital', f"Erro ao consultar saldo: {str(e)}", nivel='ERROR')
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@require_jwt_only
def creditar(request):
    """
    Credita valor na conta digital do cliente.
    """
    try:
        serializer = CreditarSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        cliente_id = request.user.cliente_id
        canal_id = getattr(request.user, 'canal_id', 1)
        
        movimentacao = ContaDigitalService.creditar(
            cliente_id=cliente_id,
            canal_id=canal_id,
            valor=serializer.validated_data['valor'],
            descricao=serializer.validated_data['descricao'],
            tipo_codigo=serializer.validated_data['tipo_operacao'],
            referencia_externa=serializer.validated_data.get('referencia_externa'),
            sistema_origem=serializer.validated_data.get('sistema_origem')
        )
        
        response_data = {
            'id': movimentacao.id,
            'tipo': movimentacao.tipo_movimentacao.nome,
            'valor': movimentacao.valor,
            'descricao': movimentacao.descricao,
            'saldo_anterior': movimentacao.saldo_anterior,
            'saldo_posterior': movimentacao.saldo_posterior,
            'status': movimentacao.status,
            'data_movimentacao': movimentacao.data_movimentacao,
            'referencia_externa': movimentacao.referencia_externa,
            'sistema_origem': movimentacao.sistema_origem
        }
        
        return Response({
            'success': True,
            'data': response_data
        }, status=status.HTTP_201_CREATED)
        
    except ValidationError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        registrar_log('apps.conta_digital', f"Erro ao creditar: {str(e)}", nivel='ERROR')
        return Response({
            'success': False,
            'error': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@require_jwt_only
def debitar(request):
    """
    Debita valor da conta digital do cliente.
    """
    try:
        serializer = DebitarSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        cliente_id = request.user.cliente_id
        canal_id = getattr(request.user, 'canal_id', 1)
        
        movimentacao = ContaDigitalService.debitar(
            cliente_id=cliente_id,
            canal_id=canal_id,
            valor=serializer.validated_data['valor'],
            descricao=serializer.validated_data['descricao'],
            tipo_codigo=serializer.validated_data['tipo_codigo'],
            referencia_externa=serializer.validated_data.get('referencia_externa'),
            sistema_origem=serializer.validated_data.get('sistema_origem')
        )
        
        response_data = {
            'id': movimentacao.id,
            'tipo': movimentacao.tipo_movimentacao.nome,
            'valor': movimentacao.valor,
            'descricao': movimentacao.descricao,
            'saldo_anterior': movimentacao.saldo_anterior,
            'saldo_posterior': movimentacao.saldo_posterior,
            'status': movimentacao.status,
            'data_movimentacao': movimentacao.data_movimentacao,
            'referencia_externa': movimentacao.referencia_externa,
            'sistema_origem': movimentacao.sistema_origem
        }
        
        return Response({
            'success': True,
            'data': response_data
        }, status=status.HTTP_201_CREATED)
        
    except ValidationError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        registrar_log('apps.conta_digital', f"Erro ao debitar: {str(e)}", nivel='ERROR')
        return Response({
            'success': False,
            'error': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@require_jwt_only
def extrato(request):
    """
    Obtém extrato de movimentações da conta digital.
    """
    try:
        # Usar dados do POST para filtros
        filtro_data = {
            'data_inicio': request.data.get('data_inicio'),
            'data_fim': request.data.get('data_fim'),
            'tipo_movimentacao': request.data.get('tipo_movimentacao'),
            'limite': int(request.data.get('limite', 50))
        }
        
        # Remover valores None
        filtro_data = {k: v for k, v in filtro_data.items() if v is not None}
        
        filtro_serializer = ExtratoFiltroSerializer(data=filtro_data)
        if not filtro_serializer.is_valid():
            return Response({
                'success': False,
                'errors': filtro_serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        cliente_id = request.user.cliente_id
        canal_id = getattr(request.user, 'canal_id', 1)
        
        extrato_data = ContaDigitalService.obter_extrato(
            cliente_id=cliente_id,
            canal_id=canal_id,
            **filtro_serializer.validated_data
        )
        
        serializer = ExtratoSerializer(extrato_data)
        
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        registrar_log('apps.conta_digital', f"Erro ao obter extrato: {str(e)}", nivel='ERROR')
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@require_jwt_only
def bloquear_saldo(request):
    """
    Bloqueia saldo da conta digital.
    """
    try:
        serializer = BloquearSaldoSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        cliente_id = request.user.cliente_id
        canal_id = getattr(request.user, 'canal_id', 1)
        
        movimentacao = ContaDigitalService.bloquear_saldo(
            cliente_id=cliente_id,
            canal_id=canal_id,
            valor=serializer.validated_data['valor'],
            motivo=serializer.validated_data['motivo']
        )
        
        response_data = {
            'id': movimentacao.id,
            'tipo': movimentacao.tipo_movimentacao.nome,
            'valor': movimentacao.valor,
            'descricao': movimentacao.descricao,
            'status': movimentacao.status,
            'data_movimentacao': movimentacao.data_movimentacao
        }
        
        return Response({
            'success': True,
            'data': response_data
        }, status=status.HTTP_201_CREATED)
        
    except ValidationError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        registrar_log('apps.conta_digital', f"Erro ao bloquear saldo: {str(e)}", nivel='ERROR')
        return Response({
            'success': False,
            'error': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@require_jwt_only
def desbloquear_saldo(request):
    """
    Desbloqueia saldo da conta digital.
    """
    try:
        serializer = DesbloquearSaldoSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        cliente_id = request.user.cliente_id
        canal_id = getattr(request.user, 'canal_id', 1)
        
        movimentacao = ContaDigitalService.desbloquear_saldo(
            cliente_id=cliente_id,
            canal_id=canal_id,
            valor=serializer.validated_data['valor'],
            motivo=serializer.validated_data['motivo']
        )
        
        response_data = {
            'id': movimentacao.id,
            'tipo': movimentacao.tipo_movimentacao.nome,
            'valor': movimentacao.valor,
            'descricao': movimentacao.descricao,
            'status': movimentacao.status,
            'data_movimentacao': movimentacao.data_movimentacao
        }
        
        return Response({
            'success': True,
            'data': response_data
        }, status=status.HTTP_201_CREATED)
        
    except ValidationError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        registrar_log('apps.conta_digital', f"Erro ao desbloquear saldo: {str(e)}", nivel='ERROR')
        return Response({
            'success': False,
            'error': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@require_jwt_only
def estornar(request):
    """
    Estorna uma movimentação da conta digital.
    """
    try:
        serializer = EstornarSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        movimentacao_estorno = ContaDigitalService.estornar_movimentacao(
            movimentacao_id=serializer.validated_data['movimentacao_id'],
            motivo=serializer.validated_data['motivo']
        )
        
        response_data = {
            'id': movimentacao_estorno.id,
            'tipo': movimentacao_estorno.tipo_movimentacao.nome,
            'valor': movimentacao_estorno.valor,
            'descricao': movimentacao_estorno.descricao,
            'saldo_anterior': movimentacao_estorno.saldo_anterior,
            'saldo_posterior': movimentacao_estorno.saldo_posterior,
            'status': movimentacao_estorno.status,
            'data_movimentacao': movimentacao_estorno.data_movimentacao,
            'movimentacao_original': serializer.validated_data['movimentacao_id']
        }
        
        return Response({
            'success': True,
            'data': response_data
        }, status=status.HTTP_201_CREATED)
        
    except ValidationError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        registrar_log('apps.conta_digital', f"Erro ao estornar: {str(e)}", nivel='ERROR')
        return Response({
            'success': False,
            'error': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
