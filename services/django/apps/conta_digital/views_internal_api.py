"""
APIs Internas de Conta Digital
Comunicação entre containers (POS → Conta Digital)
Sem rate limiting (middleware interno)
"""
import json
from decimal import Decimal
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from wallclub_core.utilitarios.log_control import registrar_log


@csrf_exempt
@require_http_methods(["POST"])
def consultar_saldo(request):
    """
    Consulta saldo disponível do cliente

    POST /api/internal/conta-digital/consultar-saldo/
    Body: {
        "cpf": "12345678900",
        "canal_id": 1
    }

    Response: {
        "sucesso": true,
        "tem_saldo": true,
        "saldo_disponivel": "150.50",
        "saldo_bloqueado": "0.00",
        "valor_maximo_permitido": "150.50"
    }
    """
    try:
        data = json.loads(request.body)
        cpf = data.get('cpf')
        canal_id = data.get('canal_id')

        if not cpf or not canal_id:
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'CPF e canal_id são obrigatórios'
            }, status=400)

        # Buscar cliente pelo CPF
        from apps.cliente.models import Cliente
        try:
            cliente = Cliente.objects.get(cpf=cpf, canal_id=canal_id)
        except Cliente.DoesNotExist:
            return JsonResponse({
                'sucesso': True,
                'tem_saldo': False,
                'saldo_disponivel': '0.00',
                'saldo_bloqueado': '0.00',
                'valor_maximo_permitido': '0.00'
            })

        # Obter saldo da conta digital
        from .services import ContaDigitalService

        try:
            saldo_info = ContaDigitalService.obter_saldo(cliente.id, canal_id)
            saldo_disponivel = saldo_info['saldo_disponivel']
            saldo_bloqueado = saldo_info['saldo_bloqueado']
        except Exception:
            # Cliente sem conta digital
            return JsonResponse({
                'sucesso': True,
                'tem_saldo': False,
                'saldo_disponivel': '0.00',
                'saldo_bloqueado': '0.00',
                'valor_maximo_permitido': '0.00'
            })

        registrar_log('apps.conta_digital',
                     f"Consulta saldo - CPF: {cpf[:3]}***, Disponível: R$ {saldo_disponivel}")

        return JsonResponse({
            'sucesso': True,
            'tem_saldo': saldo_disponivel > 0,
            'saldo_disponivel': str(saldo_disponivel),
            'saldo_bloqueado': str(saldo_bloqueado),
            'valor_maximo_permitido': str(saldo_disponivel)
        })

    except Exception as e:
        registrar_log('apps.conta_digital',
                     f"Erro ao consultar saldo: {str(e)}",
                     nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro ao consultar saldo: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def autorizar_uso(request):
    """
    Autoriza uso de saldo (bloqueia valor)

    POST /api/internal/conta-digital/autorizar-uso/
    Body: {
        "cpf": "12345678900",
        "canal_id": 1,
        "valor": "50.00",
        "loja_id": 1,
        "terminal_id": 123
    }

    Response: {
        "sucesso": true,
        "autorizacao_id": "AUTH123456",
        "status": "APROVADO",
        "valor_bloqueado": "50.00"
    }
    """
    try:
        data = json.loads(request.body)
        cpf = data.get('cpf')
        canal_id = data.get('canal_id')
        valor = Decimal(str(data.get('valor', 0)))
        loja_id = data.get('loja_id')
        terminal_id = data.get('terminal_id')

        if not all([cpf, canal_id, valor, loja_id]):
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'CPF, canal_id, valor e loja_id são obrigatórios'
            }, status=400)

        # Buscar cliente pelo CPF
        from apps.cliente.models import Cliente
        try:
            cliente = Cliente.objects.get(cpf=cpf, canal_id=canal_id)
        except Cliente.DoesNotExist:
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'Cliente não encontrado'
            }, status=404)

        # Criar autorização via service (método correto)
        from .services_autorizacao import AutorizacaoService

        resultado = AutorizacaoService.criar_autorizacao(
            cliente_id=cliente.id,
            canal_id=canal_id,
            valor=valor,
            terminal=str(terminal_id) if terminal_id else 'API',
            ip_address=None
        )

        registrar_log('apps.conta_digital',
                     f"Autorização - CPF: {cpf[:3]}***, Valor: R$ {valor}, "
                     f"Status: {resultado.get('status')}")

        return JsonResponse(resultado)

    except Exception as e:
        registrar_log('apps.conta_digital',
                     f"Erro ao autorizar uso: {str(e)}",
                     nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro ao autorizar uso: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def debitar_saldo(request):
    """
    Debita saldo após transação aprovada

    POST /api/internal/conta-digital/debitar-saldo/
    Body: {
        "autorizacao_id": "AUTH123456",
        "nsu_transacao": "148482386"
    }

    Response: {
        "sucesso": true,
        "mensagem": "Saldo debitado com sucesso",
        "movimentacao_id": 456
    }
    """
    try:
        data = json.loads(request.body)
        autorizacao_id = data.get('autorizacao_id')
        nsu_transacao = data.get('nsu_transacao')

        if not autorizacao_id or not nsu_transacao:
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'autorizacao_id e nsu_transacao são obrigatórios'
            }, status=400)

        # Debitar saldo via service
        from .services_autorizacao import AutorizacaoService

        resultado = AutorizacaoService.debitar_saldo_autorizado(
            autorizacao_id=autorizacao_id,
            nsu_transacao=str(nsu_transacao)
        )

        registrar_log('apps.conta_digital',
                     f"Débito - Autorização: {autorizacao_id[:8]}, NSU: {nsu_transacao}, "
                     f"Sucesso: {resultado.get('sucesso')}")

        return JsonResponse(resultado)

    except Exception as e:
        registrar_log('apps.conta_digital',
                     f"Erro ao debitar saldo: {str(e)}",
                     nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro ao debitar saldo: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def estornar_saldo(request):
    """
    Estorna saldo se transação foi negada

    POST /api/internal/conta-digital/estornar-saldo/
    Body: {
        "autorizacao_id": "AUTH123456",
        "motivo": "Transação negada"
    }

    Response: {
        "sucesso": true,
        "mensagem": "Saldo estornado com sucesso"
    }
    """
    try:
        data = json.loads(request.body)
        autorizacao_id = data.get('autorizacao_id')
        motivo = data.get('motivo', 'Estorno')

        if not autorizacao_id:
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'autorizacao_id é obrigatório'
            }, status=400)

        # Estornar saldo via service
        from .services_autorizacao import AutorizacaoService

        resultado = AutorizacaoService.estornar_autorizacao(
            autorizacao_id=autorizacao_id,
            motivo=motivo
        )

        registrar_log('apps.conta_digital',
                     f"Estorno - Autorização: {autorizacao_id[:8]}, "
                     f"Sucesso: {resultado.get('sucesso')}")

        return JsonResponse(resultado)

    except Exception as e:
        registrar_log('apps.conta_digital',
                     f"Erro ao estornar saldo: {str(e)}",
                     nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro ao estornar saldo: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def calcular_maximo(request):
    """
    Calcula valor máximo permitido para uso

    POST /api/internal/conta-digital/calcular-maximo/
    Body: {
        "cpf": "12345678900",
        "canal_id": 1,
        "loja_id": 1,
        "valor_transacao": "200.00"
    }

    Response: {
        "sucesso": true,
        "valor_maximo_permitido": "150.50",
        "percentual_permitido": "100.00"
    }
    """
    try:
        data = json.loads(request.body)
        cpf = data.get('cpf')
        canal_id = data.get('canal_id')
        loja_id = data.get('loja_id')
        valor_transacao = Decimal(str(data.get('valor_transacao', 0)))

        if not all([cpf, canal_id, loja_id]):
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'CPF, canal_id e loja_id são obrigatórios'
            }, status=400)

        # Buscar cliente pelo CPF
        from apps.cliente.models import Cliente
        try:
            cliente = Cliente.objects.get(cpf=cpf, canal_id=canal_id)
        except Cliente.DoesNotExist:
            return JsonResponse({
                'sucesso': True,
                'valor_maximo_permitido': '0.00',
                'percentual_permitido': '0.00'
            })

        # Obter saldo disponível
        from .services import ContaDigitalService

        try:
            saldo_info = ContaDigitalService.obter_saldo(cliente.id, canal_id)
            saldo_disponivel = saldo_info['saldo_disponivel']
        except Exception:
            return JsonResponse({
                'sucesso': True,
                'valor_maximo_permitido': '0.00',
                'percentual_permitido': '0.00'
            })

        # Calcular valor máximo via service (método correto)
        from .services_autorizacao import CashbackService

        resultado = CashbackService.calcular_valor_utilizacao_maximo(
            valor_compra=valor_transacao,
            saldo_disponivel=saldo_disponivel,
            loja_id=loja_id,
            processo_venda='POS'
        )

        # Resultado do método retorna 'valor_permitido', não 'valor_maximo_permitido'
        if resultado.get('sucesso'):
            valor_permitido = resultado.get('valor_permitido', 0)
            registrar_log('apps.conta_digital',
                         f"Cálculo máximo - CPF: {cpf[:3]}***, "
                         f"Máximo: R$ {valor_permitido}")

            return JsonResponse({
                'sucesso': True,
                'valor_maximo_permitido': str(valor_permitido),
                'percentual_permitido': str(resultado.get('percentual_aplicado', 0))
            })
        else:
            return JsonResponse(resultado)

    except Exception as e:
        registrar_log('apps.conta_digital',
                     f"Erro ao calcular máximo: {str(e)}",
                     nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro ao calcular máximo: {str(e)}'
        }, status=500)
