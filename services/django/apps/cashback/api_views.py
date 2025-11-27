"""
APIs REST para cashback
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from wallclub_core.decorators.api_decorators import handle_api_errors, validate_required_params
from wallclub_core.utilitarios.log_control import registrar_log
from decimal import Decimal
import json
from datetime import datetime
from .services import CashbackService


@csrf_exempt
@require_http_methods(["POST"])
@handle_api_errors
@validate_required_params('loja_id', 'cliente_id', 'valor_transacao', 'forma_pagamento')
def simular_cashback(request):
    """
    Simula cashback Loja para uma transação.
    
    POST /api/v1/cashback/simular/
    Body: {
        "loja_id": 123,
        "cliente_id": 456,
        "canal_id": 1,
        "valor_transacao": 100.00,
        "forma_pagamento": "PIX"  // PIX, DEBITO, CREDITO
    }
    
    Response: {
        "sucesso": true,
        "cashback_loja": {
            "valor": 5.00,
            "regra_id": 10,
            "regra_nome": "Cashback Terça-feira",
            "tipo_desconto": "PERCENTUAL",
            "valor_desconto": 5.00
        }
    }
    """
    try:
        data = json.loads(request.body)
        
        loja_id = int(data['loja_id'])
        cliente_id = int(data['cliente_id'])
        canal_id = int(data.get('canal_id', 1))
        valor_transacao = Decimal(str(data['valor_transacao']))
        forma_pagamento = data['forma_pagamento'].upper()
        
        registrar_log(
            'cashback.api',
            f'Simulando cashback loja - Loja: {loja_id}, Cliente: {cliente_id}, '
            f'Valor: R$ {valor_transacao}, Forma: {forma_pagamento}'
        )
        
        # Simular cashback loja
        resultado = CashbackService.simular_cashback_loja(
            loja_id=loja_id,
            cliente_id=cliente_id,
            canal_id=canal_id,
            valor_transacao=valor_transacao,
            forma_pagamento=forma_pagamento
        )
        
        if resultado:
            registrar_log(
                'cashback.api',
                f'Cashback loja simulado: R$ {resultado["valor"]} - Regra: {resultado["regra_nome"]}'
            )
            
            return JsonResponse({
                'sucesso': True,
                'cashback_loja': resultado
            })
        else:
            registrar_log('cashback.api', 'Nenhuma regra de cashback loja aplicável')
            
            return JsonResponse({
                'sucesso': True,
                'cashback_loja': None
            })
            
    except Exception as e:
        registrar_log('cashback.api', f'Erro ao simular cashback: {str(e)}', nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro ao simular cashback: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@handle_api_errors
@validate_required_params('tipo', 'cliente_id', 'loja_id', 'transacao_id', 'transacao_tipo', 'valor_transacao', 'valor_cashback')
def aplicar_cashback(request):
    """
    Aplica cashback após transação aprovada (chamada interna).
    
    POST /api/v1/cashback/aplicar/
    Body: {
        "tipo": "WALL" ou "LOJA",
        "cliente_id": 456,
        "loja_id": 123,
        "canal_id": 1,
        "transacao_id": 789,
        "transacao_tipo": "POS",  // POS ou CHECKOUT
        "valor_transacao": 100.00,
        "valor_cashback": 5.00,
        "parametro_wall_id": 10,  // obrigatório se tipo=WALL
        "regra_loja_id": 20  // obrigatório se tipo=LOJA
    }
    
    Response: {
        "sucesso": true,
        "cashback_uso_id": 123,
        "movimentacao_id": 456,
        "status": "RETIDO" ou "LIBERADO",
        "data_liberacao": "2025-12-26T20:00:00",
        "data_expiracao": "2026-03-26T20:00:00"
    }
    """
    try:
        data = json.loads(request.body)
        
        tipo = data['tipo'].upper()
        cliente_id = int(data['cliente_id'])
        loja_id = int(data['loja_id'])
        canal_id = int(data.get('canal_id', 1))
        transacao_id = int(data['transacao_id'])
        transacao_tipo = data['transacao_tipo'].upper()
        valor_transacao = Decimal(str(data['valor_transacao']))
        valor_cashback = Decimal(str(data['valor_cashback']))
        
        registrar_log(
            'cashback.api',
            f'Aplicando cashback {tipo} - Cliente: {cliente_id}, Loja: {loja_id}, '
            f'Transação: {transacao_tipo}#{transacao_id}, Valor: R$ {valor_cashback}'
        )
        
        if tipo == 'WALL':
            parametro_wall_id = int(data['parametro_wall_id'])
            
            resultado = CashbackService.aplicar_cashback_wall(
                parametro_wall_id=parametro_wall_id,
                cliente_id=cliente_id,
                loja_id=loja_id,
                canal_id=canal_id,
                transacao_tipo=transacao_tipo,
                transacao_id=transacao_id,
                valor_transacao=valor_transacao,
                valor_cashback=valor_cashback
            )
            
        elif tipo == 'LOJA':
            regra_loja_id = int(data['regra_loja_id'])
            
            resultado = CashbackService.aplicar_cashback_loja(
                regra_loja_id=regra_loja_id,
                cliente_id=cliente_id,
                loja_id=loja_id,
                canal_id=canal_id,
                transacao_tipo=transacao_tipo,
                transacao_id=transacao_id,
                valor_transacao=valor_transacao,
                valor_cashback=valor_cashback
            )
        else:
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'Tipo inválido. Use WALL ou LOJA'
            }, status=400)
        
        registrar_log(
            'cashback.api',
            f'Cashback aplicado - ID: {resultado["cashback_uso_id"]}, Status: {resultado["status"]}'
        )
        
        return JsonResponse({
            'sucesso': True,
            **resultado
        })
        
    except Exception as e:
        registrar_log('cashback.api', f'Erro ao aplicar cashback: {str(e)}', nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro ao aplicar cashback: {str(e)}'
        }, status=500)
