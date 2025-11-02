"""
Views para ofertas - protegidas por JWT Token
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from wallclub_core.oauth.decorators import require_oauth_apps
from apps.conta_digital.decorators import require_jwt_only
from wallclub_core.utilitarios.log_control import registrar_log
from apps.ofertas.services import OfertaService


@api_view(['POST'])
@require_jwt_only
def lista_ofertas(request):
    """
    Lista ofertas vigentes para o cliente

    Autenticação: OAuth + JWT

    Retorna ofertas baseadas na loja, canal e grupo econômico do cliente
    """
    try:
        # Extrair cliente_id do JWT
        cliente_id = request.user.cliente_id

        # Buscar ofertas vigentes
        ofertas = OfertaService.listar_ofertas_vigentes(cliente_id)

        return Response({
            'sucesso': True,
            'mensagem': 'Ofertas consultadas com sucesso',
            'ofertas': ofertas,
            'total': len(ofertas)
        }, status=status.HTTP_200_OK)

    except Exception as e:
        registrar_log('apps.ofertas', f'Erro ao listar ofertas: {str(e)}', nivel='ERROR')
        return Response({
            'sucesso': False,
            'mensagem': 'Erro ao consultar ofertas',
            'ofertas': []
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@require_jwt_only
def detalhes_oferta(request):
    """
    Busca detalhes de uma oferta específica

    Autenticação: OAuth + JWT

    Body:
        oferta_id (int): ID da oferta

    Retorna dados completos da oferta se estiver vigente e acessível ao cliente
    """
    try:
        # Extrair dados
        cliente_id = request.user.cliente_id
        oferta_id = request.data.get('oferta_id')

        # Validar oferta_id
        if not oferta_id:
            return Response({
                'sucesso': False,
                'mensagem': 'oferta_id é obrigatório'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Buscar oferta
        oferta = OfertaService.obter_oferta_cliente(oferta_id, cliente_id)

        if not oferta:
            return Response({
                'sucesso': False,
                'mensagem': 'Oferta não encontrada ou não disponível'
            }, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'sucesso': True,
            'mensagem': 'Oferta consultada com sucesso',
            'oferta': oferta
        }, status=status.HTTP_200_OK)

    except Exception as e:
        registrar_log('apps.ofertas', f'Erro ao buscar oferta: {str(e)}', nivel='ERROR')
        return Response({
            'sucesso': False,
            'mensagem': 'Erro ao consultar oferta'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
