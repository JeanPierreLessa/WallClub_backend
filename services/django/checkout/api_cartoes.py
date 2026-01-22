"""
API REST para gerenciamento de cartões tokenizados
Usado pelo Portal Vendas para invalidar cartões comprometidos
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

from .models import CheckoutCartaoTokenizado, CheckoutCliente
from .services import CartaoTokenizadoService
from wallclub_core.utilitarios.log_control import registrar_log


@csrf_exempt
@require_http_methods(["GET"])
def listar_cartoes_cliente(request, cpf):
    """
    GET /api/v1/checkout/cartoes/{cpf}/
    Lista cartões tokenizados de um cliente (todos, incluindo inválidos)

    Usado pelo Portal Vendas para visualizar histórico de cartões
    """
    try:
        # Buscar cliente por CPF
        cliente = CheckoutCliente.objects.filter(cpf=cpf).first()

        if not cliente:
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'Cliente não encontrado'
            }, status=404)

        # Listar todos os cartões (incluindo inválidos)
        cartoes = CheckoutCartaoTokenizado.objects.filter(
            cliente=cliente
        ).order_by('-created_at')

        cartoes_data = []
        for cartao in cartoes:
            cartoes_data.append({
                'id': cartao.id,
                'cartao_mascarado': cartao.cartao_mascarado,
                'bandeira': cartao.bandeira,
                'validade': cartao.validade,
                'apelido': cartao.apelido,
                'valido': cartao.valido,
                'tentativas_falhas_consecutivas': cartao.tentativas_falhas_consecutivas,
                'ultima_falha_em': cartao.ultima_falha_em.isoformat() if cartao.ultima_falha_em else None,
                'motivo_invalidacao': cartao.motivo_invalidacao,
                'invalidado_em': cartao.invalidado_em.isoformat() if cartao.invalidado_em else None,
                'created_at': cartao.created_at.isoformat(),
            })

        return JsonResponse({
            'sucesso': True,
            'dados': {
                'cliente': {
                    'id': cliente.id,
                    'nome': cliente.nome,
                    'cpf': cliente.cpf,
                    'email': cliente.email,
                },
                'cartoes': cartoes_data,
                'total': len(cartoes_data),
                'ativos': sum(1 for c in cartoes_data if c['valido']),
                'invalidados': sum(1 for c in cartoes_data if not c['valido']),
            }
        })

    except Exception as e:
        registrar_log('checkout', f'Erro ao listar cartões: {str(e)}', nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': 'Erro ao listar cartões'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def invalidar_cartao(request, cartao_id):
    """
    POST /api/v1/checkout/cartoes/{cartao_id}/invalidar/
    Invalida um cartão tokenizado

    Payload:
    {
        "motivo": "Cartão comprometido - fraude detectada",
        "usuario_id": 123  // ID do usuário do portal que invalidou
    }

    Response:
    {
        "sucesso": true,
        "mensagem": "Cartão invalidado com sucesso"
    }
    """
    try:
        data = json.loads(request.body)
        motivo = data.get('motivo', 'Invalidação manual')
        usuario_id = data.get('usuario_id')

        # Validar que cartão existe
        try:
            cartao = CheckoutCartaoTokenizado.objects.get(id=cartao_id)
        except CheckoutCartaoTokenizado.DoesNotExist:
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'Cartão não encontrado'
            }, status=404)

        # Verificar se já está inválido
        if not cartao.valido:
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'Cartão já está invalidado',
                'dados': {
                    'invalidado_em': cartao.invalidado_em.isoformat() if cartao.invalidado_em else None,
                    'motivo_invalidacao': cartao.motivo_invalidacao
                }
            }, status=400)

        # Invalidar cartão
        CartaoTokenizadoService.invalidar_cartao(
            cartao_id=cartao_id,
            motivo=motivo,
            usuario_id=usuario_id
        )

        registrar_log('checkout',
                     f'Cartão {cartao_id} invalidado - Motivo: {motivo} - Usuário: {usuario_id}',
                     nivel='INFO')

        return JsonResponse({
            'sucesso': True,
            'mensagem': 'Cartão invalidado com sucesso',
            'dados': {
                'cartao_id': cartao_id,
                'motivo': motivo,
                'invalidado_em': 'now'
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'sucesso': False,
            'mensagem': 'JSON inválido'
        }, status=400)
    except Exception as e:
        registrar_log('checkout', f'Erro ao invalidar cartão: {str(e)}', nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': 'Erro ao invalidar cartão'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def reativar_cartao(request, cartao_id):
    """
    POST /api/v1/checkout/cartoes/{cartao_id}/reativar/
    Reativa um cartão previamente invalidado

    Payload:
    {
        "usuario_id": 123  // ID do usuário do portal que reativou
    }
    """
    try:
        data = json.loads(request.body)
        usuario_id = data.get('usuario_id')

        # Validar que cartão existe
        try:
            cartao = CheckoutCartaoTokenizado.objects.get(id=cartao_id)
        except CheckoutCartaoTokenizado.DoesNotExist:
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'Cartão não encontrado'
            }, status=404)

        # Verificar se já está ativo
        if cartao.valido:
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'Cartão já está ativo'
            }, status=400)

        # Reativar cartão
        from django.utils import timezone
        cartao.valido = True
        cartao.tentativas_falhas_consecutivas = 0
        cartao.motivo_invalidacao = None
        cartao.invalidado_por = None
        cartao.invalidado_em = None
        cartao.save()

        registrar_log('checkout',
                     f'Cartão {cartao_id} reativado - Usuário: {usuario_id}',
                     nivel='INFO')

        return JsonResponse({
            'sucesso': True,
            'mensagem': 'Cartão reativado com sucesso',
            'dados': {
                'cartao_id': cartao_id
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'sucesso': False,
            'mensagem': 'JSON inválido'
        }, status=400)
    except Exception as e:
        registrar_log('checkout', f'Erro ao reativar cartão: {str(e)}', nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': 'Erro ao reativar cartão'
        }, status=500)
