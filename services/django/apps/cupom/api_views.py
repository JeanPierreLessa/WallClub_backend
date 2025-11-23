"""
API Views para cupons
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from decimal import Decimal
from .models import Cupom
from .serializers import CupomAtivoSerializer, CupomValidarSerializer, CupomValidarResponseSerializer
from .services import CupomService
from wallclub_core.utilitarios.log_control import registrar_log


class CuponsAtivosAPIView(APIView):
    """
    GET /api/cupons/ativos/
    Lista cupons ativos disponíveis para o cliente
    Autenticação: JWT (App Mobile)
    
    Query params:
    - loja_id: ID da loja (obrigatório)
    - cliente_id: ID do cliente (opcional, para filtrar cupons individuais)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        loja_id = request.query_params.get('loja_id')
        cliente_id = request.query_params.get('cliente_id')
        
        if not loja_id:
            return Response({
                'erro': 'loja_id é obrigatório'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Buscar cupons ativos e vigentes
            agora = timezone.now()
            cupons = Cupom.objects.filter(
                loja_id=loja_id,
                ativo=True,
                data_inicio__lte=agora,
                data_fim__gte=agora
            )
            
            # Filtrar cupons que ainda têm usos disponíveis
            cupons_disponiveis = []
            for cupom in cupons:
                # Verificar limite global
                if cupom.limite_uso_total and cupom.quantidade_usada >= cupom.limite_uso_total:
                    continue
                
                # Se for cupom individual e tiver cliente_id, verificar se é para este cliente
                if cupom.tipo_cupom == 'INDIVIDUAL' and cupom.cliente_id:
                    if not cliente_id or int(cliente_id) != cupom.cliente_id:
                        continue
                
                cupons_disponiveis.append(cupom)
            
            serializer = CupomAtivoSerializer(cupons_disponiveis, many=True)
            
            return Response({
                'cupons': serializer.data,
                'total': len(cupons_disponiveis)
            })
            
        except Exception as e:
            registrar_log('apps.cupom', f'Erro ao listar cupons ativos: {e}', nivel='ERROR')
            return Response({
                'erro': 'Erro ao buscar cupons'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CupomValidarAPIView(APIView):
    """
    POST /api/cupom/validar/
    Valida cupom e retorna valor do desconto
    Autenticação: OAuth Token (POS) ou JWT (Checkout Web)
    
    Payload:
    {
        "codigo": "PROMO10",
        "loja_id": 26,
        "cliente_id": 123,
        "valor_transacao": 100.00
    }
    
    Response:
    {
        "valido": true,
        "cupom_id": 1,
        "valor_desconto": 10.00,
        "valor_final": 90.00,
        "mensagem": "Cupom aplicado com sucesso"
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = CupomValidarSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'valido': False,
                'mensagem': 'Dados inválidos',
                'erros': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        dados = serializer.validated_data
        codigo = dados['codigo']
        loja_id = dados['loja_id']
        cliente_id = dados['cliente_id']
        valor_transacao = dados['valor_transacao']
        
        try:
            cupom_service = CupomService()
            
            # Validar cupom
            cupom = cupom_service.validar_cupom(
                codigo=codigo,
                loja_id=loja_id,
                cliente_id=cliente_id,
                valor_transacao=valor_transacao
            )
            
            # Calcular desconto
            valor_desconto = cupom_service.calcular_desconto(cupom, valor_transacao)
            valor_final = valor_transacao - valor_desconto
            
            response_data = {
                'valido': True,
                'cupom_id': cupom.id,
                'valor_desconto': float(valor_desconto),
                'valor_final': float(valor_final),
                'mensagem': 'Cupom aplicado com sucesso'
            }
            
            registrar_log(
                'apps.cupom',
                f'Cupom validado: {codigo} - Cliente {cliente_id} - Desconto R$ {valor_desconto}'
            )
            
            return Response(response_data)
            
        except ValueError as e:
            # Erro de validação do cupom
            return Response({
                'valido': False,
                'cupom_id': None,
                'valor_desconto': None,
                'valor_final': None,
                'mensagem': str(e)
            }, status=status.HTTP_200_OK)  # 200 pois é uma resposta válida
            
        except Exception as e:
            registrar_log('apps.cupom', f'Erro ao validar cupom: {e}', nivel='ERROR')
            return Response({
                'valido': False,
                'mensagem': 'Erro ao validar cupom'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
