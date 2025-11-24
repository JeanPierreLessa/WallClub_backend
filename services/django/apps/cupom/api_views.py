"""
API Views para cupons
"""
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from decimal import Decimal
import json
from .models import Cupom
from .serializers import CupomAtivoSerializer, CupomValidarSerializer, CupomValidarResponseSerializer
from .services import CupomService
from wallclub_core.utilitarios.log_control import registrar_log
from apps.cliente.jwt_cliente import ClienteJWTAuthentication
from wallclub_core.oauth.decorators import require_oauth_posp2


@api_view(['GET'])
@authentication_classes([ClienteJWTAuthentication])
@permission_classes([IsAuthenticated])
def cupons_ativos(request):
    """
    GET /api/cupons/ativos/
    Lista cupons ativos disponíveis para o cliente autenticado
    Autenticação: JWT (App Mobile) - extrai cliente_id do token
    
    Retorna cupons de TODAS as lojas que o cliente pode usar:
    - Cupons genéricos ativos e vigentes
    - Cupons individuais vinculados ao cliente
    """
    # Cliente ID vem do JWT (request.user.cliente_id)
    cliente_id = request.user.cliente_id
    
    try:
        # Buscar cupons ativos e vigentes de TODAS as lojas
        agora = timezone.now()
        cupons = Cupom.objects.filter(
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
            
            # Se for cupom individual, verificar se é para este cliente
            if cupom.tipo_cupom == 'INDIVIDUAL' and cupom.cliente_id:
                if cliente_id != cupom.cliente_id:
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


@csrf_exempt
@require_http_methods(["POST"])
@require_oauth_posp2
def verificar_cupons_disponiveis(request):
    """
    POST /api/v1/cupons/verificar_disponiveis/
    Verifica se existem cupons ativos para uma loja
    Autenticação: OAuth Token (POS)
    
    Payload:
    {
        "loja_id": 26
    }
    
    Response:
    {
        "tem_cupons": true,
        "quantidade": 5
    }
    """
    try:
        data = json.loads(request.body)
        loja_id = data.get('loja_id')
        
        if not loja_id:
            return JsonResponse({
                'tem_cupons': False,
                'quantidade': 0,
                'mensagem': 'loja_id é obrigatório'
            }, status=400)
        
        # Buscar cupons ativos e vigentes da loja
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
            cupons_disponiveis.append(cupom)
        
        quantidade = len(cupons_disponiveis)
        
        return JsonResponse({
            'tem_cupons': quantidade > 0,
            'quantidade': quantidade
        })
        
    except Exception as e:
        registrar_log('apps.cupom', f'Erro ao verificar cupons disponíveis: {e}', nivel='ERROR')
        return JsonResponse({
            'tem_cupons': False,
            'quantidade': 0,
            'mensagem': 'Erro ao verificar cupons'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@require_oauth_posp2
def validar_cupom(request):
    """
    POST /api/v1/cupons/validar/
    Valida cupom e retorna valor do desconto
    Autenticação: OAuth Token (POS)
    
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
    try:
        data = json.loads(request.body)
        
        codigo = data.get('codigo')
        loja_id = data.get('loja_id')
        cliente_id = data.get('cliente_id')
        valor_transacao = Decimal(str(data.get('valor_transacao', 0)))
        
        if not all([codigo, loja_id, cliente_id, valor_transacao]):
            return JsonResponse({
                'valido': False,
                'mensagem': 'Dados inválidos: codigo, loja_id, cliente_id e valor_transacao são obrigatórios'
            }, status=400)
        
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
        
        return JsonResponse(response_data)
        
    except ValueError as e:
        # Erro de validação do cupom
        return JsonResponse({
            'valido': False,
            'cupom_id': None,
            'valor_desconto': None,
            'valor_final': None,
            'mensagem': str(e)
        })
        
    except Exception as e:
        registrar_log('apps.cupom', f'Erro ao validar cupom: {e}', nivel='ERROR')
        return JsonResponse({
            'valido': False,
            'mensagem': 'Erro ao validar cupom'
        }, status=500)
