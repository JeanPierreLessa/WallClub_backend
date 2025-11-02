"""
APIs Internas de Checkout
Comunicação entre containers (Portais → Checkout)
Sem rate limiting (middleware interno)
"""
import json
from decimal import Decimal
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from wallclub_core.utilitarios.log_control import registrar_log


@csrf_exempt
@require_http_methods(["GET"])
def listar_recorrencias(request):
    """
    Lista recorrências por filtros
    
    GET /api/internal/checkout/recorrencias/?loja_id=1&vendedor_id=5&status=ativo
    
    Response: {
        "sucesso": true,
        "total": 10,
        "recorrencias": [...]
    }
    """
    try:
        from checkout.models_recorrencia import RecorrenciaAgendada
        
        loja_id = request.GET.get('loja_id')
        vendedor_id = request.GET.get('vendedor_id')
        status = request.GET.get('status', 'ativo')
        
        queryset = RecorrenciaAgendada.objects.select_related(
            'cliente', 'cartao_tokenizado', 'loja'
        )
        
        if loja_id:
            queryset = queryset.filter(loja_id=loja_id)
        if vendedor_id:
            queryset = queryset.filter(vendedor_id=vendedor_id)
        if status:
            queryset = queryset.filter(status=status)
        
        recorrencias = []
        for rec in queryset[:100]:  # Limitar 100 resultados
            recorrencias.append({
                'id': rec.id,
                'cliente_nome': rec.cliente.nome if rec.cliente else None,
                'cliente_cpf': rec.cliente.cpf if rec.cliente else None,
                'valor_recorrencia': str(rec.valor_recorrencia),
                'periodicidade': rec.periodicidade,
                'proxima_cobranca': rec.proxima_cobranca.isoformat() if rec.proxima_cobranca else None,
                'status': rec.status,
                'tentativas_falhas': rec.tentativas_falhas_consecutivas,
                'loja_nome': rec.loja.nome if rec.loja else None,
            })
        
        registrar_log('checkout.internal_api',
                     f"Lista recorrências - Loja: {loja_id}, Status: {status}, Total: {len(recorrencias)}")
        
        return JsonResponse({
            'sucesso': True,
            'total': len(recorrencias),
            'recorrencias': recorrencias
        })
        
    except Exception as e:
        registrar_log('checkout.internal_api',
                     f"Erro ao listar recorrências: {str(e)}",
                     nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro ao listar recorrências: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def criar_recorrencia(request):
    """
    Cria nova recorrência
    
    POST /api/internal/checkout/recorrencias/
    Body: {
        "cliente_id": 123,
        "loja_id": 1,
        "vendedor_id": 5,
        "cartao_tokenizado_id": 456,
        "valor_recorrencia": "150.00",
        "periodicidade": "mensal",
        "dia_cobranca": 10,
        "descricao": "Assinatura mensal"
    }
    
    Response: {
        "sucesso": true,
        "recorrencia_id": 789,
        "proxima_cobranca": "2025-12-10"
    }
    """
    try:
        from checkout.models_recorrencia import RecorrenciaAgendada
        from datetime import datetime, timedelta
        
        data = json.loads(request.body)
        
        cliente_id = data.get('cliente_id')
        loja_id = data.get('loja_id')
        vendedor_id = data.get('vendedor_id')
        cartao_tokenizado_id = data.get('cartao_tokenizado_id')
        valor_recorrencia = Decimal(str(data.get('valor_recorrencia')))
        periodicidade = data.get('periodicidade', 'mensal')
        dia_cobranca = data.get('dia_cobranca', 10)
        descricao = data.get('descricao', '')
        
        if not all([cliente_id, loja_id, vendedor_id, cartao_tokenizado_id, valor_recorrencia]):
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'Campos obrigatórios: cliente_id, loja_id, vendedor_id, cartao_tokenizado_id, valor_recorrencia'
            }, status=400)
        
        # Calcular próxima cobrança
        hoje = datetime.now().date()
        if periodicidade == 'mensal':
            if hoje.day > dia_cobranca:
                # Próximo mês
                proxima = hoje.replace(day=dia_cobranca) + timedelta(days=32)
                proxima = proxima.replace(day=dia_cobranca)
            else:
                # Este mês
                proxima = hoje.replace(day=dia_cobranca)
        else:
            proxima = hoje + timedelta(days=7)  # Semanal default
        
        # Criar recorrência
        recorrencia = RecorrenciaAgendada.objects.create(
            cliente_id=cliente_id,
            loja_id=loja_id,
            vendedor_id=vendedor_id,
            cartao_tokenizado_id=cartao_tokenizado_id,
            valor_recorrencia=valor_recorrencia,
            periodicidade=periodicidade,
            dia_cobranca=dia_cobranca,
            descricao=descricao,
            proxima_cobranca=proxima,
            status='ativo',
            tentativas_falhas_consecutivas=0
        )
        
        registrar_log('checkout.internal_api',
                     f"Recorrência criada - ID: {recorrencia.id}, Cliente: {cliente_id}, Valor: R$ {valor_recorrencia}")
        
        return JsonResponse({
            'sucesso': True,
            'recorrencia_id': recorrencia.id,
            'proxima_cobranca': proxima.isoformat(),
            'mensagem': 'Recorrência criada com sucesso'
        })
        
    except Exception as e:
        registrar_log('checkout.internal_api',
                     f"Erro ao criar recorrência: {str(e)}",
                     nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro ao criar recorrência: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def pausar_recorrencia(request, recorrencia_id):
    """
    Pausa recorrência (não cobra até reativar)
    
    POST /api/internal/checkout/recorrencias/{id}/pausar/
    Body: {
        "motivo": "Solicitação do cliente"
    }
    
    Response: {
        "sucesso": true,
        "mensagem": "Recorrência pausada"
    }
    """
    try:
        from checkout.models_recorrencia import RecorrenciaAgendada
        
        data = json.loads(request.body)
        motivo = data.get('motivo', 'Pausado manualmente')
        
        recorrencia = RecorrenciaAgendada.objects.get(id=recorrencia_id)
        recorrencia.status = 'pausado'
        recorrencia.save()
        
        registrar_log('checkout.internal_api',
                     f"Recorrência pausada - ID: {recorrencia_id}, Motivo: {motivo}")
        
        return JsonResponse({
            'sucesso': True,
            'mensagem': 'Recorrência pausada com sucesso'
        })
        
    except RecorrenciaAgendada.DoesNotExist:
        return JsonResponse({
            'sucesso': False,
            'mensagem': 'Recorrência não encontrada'
        }, status=404)
    except Exception as e:
        registrar_log('checkout.internal_api',
                     f"Erro ao pausar recorrência {recorrencia_id}: {str(e)}",
                     nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro ao pausar recorrência: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def reativar_recorrencia(request, recorrencia_id):
    """
    Reativa recorrência pausada ou em hold
    
    POST /api/internal/checkout/recorrencias/{id}/reativar/
    Body: {
        "nova_data": "2025-12-10"  # opcional
    }
    
    Response: {
        "sucesso": true,
        "proxima_cobranca": "2025-12-10"
    }
    """
    try:
        from checkout.models_recorrencia import RecorrenciaAgendada
        from datetime import datetime
        
        data = json.loads(request.body)
        nova_data = data.get('nova_data')
        
        recorrencia = RecorrenciaAgendada.objects.get(id=recorrencia_id)
        recorrencia.status = 'ativo'
        recorrencia.tentativas_falhas_consecutivas = 0
        
        if nova_data:
            recorrencia.proxima_cobranca = datetime.strptime(nova_data, '%Y-%m-%d').date()
        
        recorrencia.save()
        
        registrar_log('checkout.internal_api',
                     f"Recorrência reativada - ID: {recorrencia_id}, Próxima: {recorrencia.proxima_cobranca}")
        
        return JsonResponse({
            'sucesso': True,
            'proxima_cobranca': recorrencia.proxima_cobranca.isoformat(),
            'mensagem': 'Recorrência reativada com sucesso'
        })
        
    except RecorrenciaAgendada.DoesNotExist:
        return JsonResponse({
            'sucesso': False,
            'mensagem': 'Recorrência não encontrada'
        }, status=404)
    except Exception as e:
        registrar_log('checkout.internal_api',
                     f"Erro ao reativar recorrência {recorrencia_id}: {str(e)}",
                     nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro ao reativar recorrência: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def cobrar_recorrencia(request, recorrencia_id):
    """
    Processa cobrança manual de recorrência
    
    POST /api/internal/checkout/recorrencias/{id}/cobrar/
    
    Response: {
        "sucesso": true,
        "nsu": "148482386",
        "valor_cobrado": "150.00"
    }
    """
    try:
        from portais.vendas.services import CheckoutVendasService
        
        resultado = CheckoutVendasService.processar_cobranca_agendada(recorrencia_id)
        
        if resultado['sucesso']:
            registrar_log('checkout.internal_api',
                         f"Cobrança manual aprovada - ID: {recorrencia_id}, NSU: {resultado.get('nsu')}")
        else:
            registrar_log('checkout.internal_api',
                         f"Cobrança manual negada - ID: {recorrencia_id}, Motivo: {resultado.get('mensagem')}",
                         nivel='WARNING')
        
        return JsonResponse(resultado)
        
    except Exception as e:
        registrar_log('checkout.internal_api',
                     f"Erro ao cobrar recorrência {recorrencia_id}: {str(e)}",
                     nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro ao processar cobrança: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["PUT"])
def atualizar_recorrencia(request, recorrencia_id):
    """
    Atualiza dados da recorrência
    
    PUT /api/internal/checkout/recorrencias/{id}/
    Body: {
        "valor_recorrencia": "200.00",
        "cartao_tokenizado_id": 999,
        "descricao": "Nova descrição"
    }
    
    Response: {
        "sucesso": true,
        "mensagem": "Recorrência atualizada"
    }
    """
    try:
        from checkout.models_recorrencia import RecorrenciaAgendada
        
        data = json.loads(request.body)
        recorrencia = RecorrenciaAgendada.objects.get(id=recorrencia_id)
        
        if 'valor_recorrencia' in data:
            recorrencia.valor_recorrencia = Decimal(str(data['valor_recorrencia']))
        if 'cartao_tokenizado_id' in data:
            recorrencia.cartao_tokenizado_id = data['cartao_tokenizado_id']
        if 'descricao' in data:
            recorrencia.descricao = data['descricao']
        if 'dia_cobranca' in data:
            recorrencia.dia_cobranca = data['dia_cobranca']
        
        recorrencia.save()
        
        registrar_log('checkout.internal_api',
                     f"Recorrência atualizada - ID: {recorrencia_id}")
        
        return JsonResponse({
            'sucesso': True,
            'mensagem': 'Recorrência atualizada com sucesso'
        })
        
    except RecorrenciaAgendada.DoesNotExist:
        return JsonResponse({
            'sucesso': False,
            'mensagem': 'Recorrência não encontrada'
        }, status=404)
    except Exception as e:
        registrar_log('checkout.internal_api',
                     f"Erro ao atualizar recorrência {recorrencia_id}: {str(e)}",
                     nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro ao atualizar recorrência: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
def deletar_recorrencia(request, recorrencia_id):
    """
    Cancela/deleta recorrência
    
    DELETE /api/internal/checkout/recorrencias/{id}/
    
    Response: {
        "sucesso": true,
        "mensagem": "Recorrência cancelada"
    }
    """
    try:
        from checkout.models_recorrencia import RecorrenciaAgendada
        
        recorrencia = RecorrenciaAgendada.objects.get(id=recorrencia_id)
        recorrencia.status = 'cancelado'
        recorrencia.save()
        
        registrar_log('checkout.internal_api',
                     f"Recorrência cancelada - ID: {recorrencia_id}")
        
        return JsonResponse({
            'sucesso': True,
            'mensagem': 'Recorrência cancelada com sucesso'
        })
        
    except RecorrenciaAgendada.DoesNotExist:
        return JsonResponse({
            'sucesso': False,
            'mensagem': 'Recorrência não encontrada'
        }, status=404)
    except Exception as e:
        registrar_log('checkout.internal_api',
                     f"Erro ao cancelar recorrência {recorrencia_id}: {str(e)}",
                     nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro ao cancelar recorrência: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def obter_recorrencia(request, recorrencia_id):
    """
    Obtém detalhes de uma recorrência
    
    GET /api/internal/checkout/recorrencias/{id}/
    
    Response: {
        "sucesso": true,
        "recorrencia": {...}
    }
    """
    try:
        from checkout.models_recorrencia import RecorrenciaAgendada
        
        recorrencia = RecorrenciaAgendada.objects.select_related(
            'cliente', 'cartao_tokenizado', 'loja'
        ).get(id=recorrencia_id)
        
        dados = {
            'id': recorrencia.id,
            'cliente': {
                'id': recorrencia.cliente.id if recorrencia.cliente else None,
                'nome': recorrencia.cliente.nome if recorrencia.cliente else None,
                'cpf': recorrencia.cliente.cpf if recorrencia.cliente else None,
            },
            'loja': {
                'id': recorrencia.loja.id if recorrencia.loja else None,
                'nome': recorrencia.loja.nome if recorrencia.loja else None,
            },
            'valor_recorrencia': str(recorrencia.valor_recorrencia),
            'periodicidade': recorrencia.periodicidade,
            'dia_cobranca': recorrencia.dia_cobranca,
            'proxima_cobranca': recorrencia.proxima_cobranca.isoformat() if recorrencia.proxima_cobranca else None,
            'status': recorrencia.status,
            'tentativas_falhas': recorrencia.tentativas_falhas_consecutivas,
            'descricao': recorrencia.descricao,
            'criado_em': recorrencia.criado_em.isoformat() if hasattr(recorrencia, 'criado_em') else None,
        }
        
        return JsonResponse({
            'sucesso': True,
            'recorrencia': dados
        })
        
    except RecorrenciaAgendada.DoesNotExist:
        return JsonResponse({
            'sucesso': False,
            'mensagem': 'Recorrência não encontrada'
        }, status=404)
    except Exception as e:
        registrar_log('checkout.internal_api',
                     f"Erro ao obter recorrência {recorrencia_id}: {str(e)}",
                     nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro ao obter recorrência: {str(e)}'
        }, status=500)


# ====================
# CLIENTES ENDPOINTS
# ====================

@csrf_exempt
@require_http_methods(["POST"])
def listar_clientes(request):
    """
    Lista clientes de checkout por filtros
    
    POST /api/internal/checkout/clientes/listar/
    Body: {
        "loja_id": 1,
        "cpf": "12345678900"  # opcional
    }
    
    Response: {
        "sucesso": true,
        "total": 10,
        "clientes": [...]
    }
    """
    try:
        from checkout.models import CheckoutCliente
        
        data = json.loads(request.body)
        loja_id = data.get('loja_id')
        cpf = data.get('cpf')
        cnpj = data.get('cnpj')
        email = data.get('email')
        
        queryset = CheckoutCliente.objects.filter(ativo=True)
        
        if loja_id:
            queryset = queryset.filter(loja_id=loja_id)
        if cpf:
            queryset = queryset.filter(cpf=cpf)
        if cnpj:
            queryset = queryset.filter(cnpj=cnpj)
        if email:
            queryset = queryset.filter(email__icontains=email)
        
        clientes = []
        for cliente in queryset[:100]:  # Limitar 100 resultados
            clientes.append({
                'id': cliente.id,
                'nome': cliente.nome,
                'cpf': cliente.cpf,
                'cnpj': cliente.cnpj,
                'email': cliente.email,
                'endereco': cliente.endereco,
                'cep': cliente.cep,
                'loja_id': cliente.loja_id,
                'created_at': cliente.created_at.isoformat(),
            })
        
        registrar_log('checkout.internal_api',
                     f"Lista clientes - Loja: {loja_id}, Total: {len(clientes)}")
        
        return JsonResponse({
            'sucesso': True,
            'total': len(clientes),
            'clientes': clientes
        })
        
    except Exception as e:
        registrar_log('checkout.internal_api',
                     f"Erro ao listar clientes: {str(e)}",
                     nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro ao listar clientes: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def criar_cliente(request):
    """
    Cria novo cliente de checkout
    
    POST /api/internal/checkout/clientes/
    Body: {
        "loja_id": 1,
        "cpf": "12345678900",
        "nome": "João Silva",
        "email": "joao@email.com",
        "endereco": "Rua X, 123",
        "cep": "12345678"
    }
    
    Response: {
        "sucesso": true,
        "cliente_id": 123
    }
    """
    try:
        from checkout.models import CheckoutCliente
        
        data = json.loads(request.body)
        
        loja_id = data.get('loja_id')
        cpf = data.get('cpf')
        cnpj = data.get('cnpj')
        nome = data.get('nome')
        email = data.get('email')
        endereco = data.get('endereco', '')
        cep = data.get('cep', '')
        
        if not all([loja_id, nome, email]):
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'Campos obrigatórios: loja_id, nome, email'
            }, status=400)
        
        if not cpf and not cnpj:
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'CPF ou CNPJ é obrigatório'
            }, status=400)
        
        # Verificar se já existe
        if cpf:
            existe = CheckoutCliente.objects.filter(loja_id=loja_id, cpf=cpf, ativo=True).first()
            if existe:
                return JsonResponse({
                    'sucesso': True,
                    'cliente_id': existe.id,
                    'mensagem': 'Cliente já existe'
                })
        
        # Criar cliente
        cliente = CheckoutCliente.objects.create(
            loja_id=loja_id,
            cpf=cpf,
            cnpj=cnpj,
            nome=nome,
            email=email,
            endereco=endereco,
            cep=cep,
            ip_address=data.get('ip_address'),
            user_agent=data.get('user_agent')
        )
        
        registrar_log('checkout.internal_api',
                     f"Cliente criado - ID: {cliente.id}, Nome: {nome}")
        
        return JsonResponse({
            'sucesso': True,
            'cliente_id': cliente.id,
            'mensagem': 'Cliente criado com sucesso'
        })
        
    except Exception as e:
        registrar_log('checkout.internal_api',
                     f"Erro ao criar cliente: {str(e)}",
                     nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro ao criar cliente: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def obter_cliente(request):
    """
    Obtém detalhes de um cliente
    
    POST /api/internal/checkout/clientes/obter/
    Body: {
        "cliente_id": 123
    }
    
    Response: {
        "sucesso": true,
        "cliente": {...}
    }
    """
    try:
        from checkout.models import CheckoutCliente
        
        data = json.loads(request.body)
        cliente_id = data.get('cliente_id')
        
        if not cliente_id:
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'cliente_id é obrigatório'
            }, status=400)
        
        cliente = CheckoutCliente.objects.get(id=cliente_id, ativo=True)
        
        dados = {
            'id': cliente.id,
            'nome': cliente.nome,
            'cpf': cliente.cpf,
            'cnpj': cliente.cnpj,
            'email': cliente.email,
            'endereco': cliente.endereco,
            'cep': cliente.cep,
            'loja_id': cliente.loja_id,
            'created_at': cliente.created_at.isoformat(),
            'updated_at': cliente.updated_at.isoformat(),
        }
        
        return JsonResponse({
            'sucesso': True,
            'cliente': dados
        })
        
    except CheckoutCliente.DoesNotExist:
        return JsonResponse({
            'sucesso': False,
            'mensagem': 'Cliente não encontrado'
        }, status=404)
    except Exception as e:
        registrar_log('checkout.internal_api',
                     f"Erro ao obter cliente {cliente_id}: {str(e)}",
                     nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro ao obter cliente: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def atualizar_cliente(request):
    """
    Atualiza dados do cliente
    
    POST /api/internal/checkout/clientes/atualizar/
    Body: {
        "cliente_id": 123,
        "nome": "João Silva Santos",
        "email": "joao.novo@email.com",
        "endereco": "Rua Y, 456"
    }
    
    Response: {
        "sucesso": true,
        "mensagem": "Cliente atualizado"
    }
    """
    try:
        from checkout.models import CheckoutCliente
        
        data = json.loads(request.body)
        cliente_id = data.get('cliente_id')
        
        if not cliente_id:
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'cliente_id é obrigatório'
            }, status=400)
        
        cliente = CheckoutCliente.objects.get(id=cliente_id, ativo=True)
        
        if 'nome' in data:
            cliente.nome = data['nome']
        if 'email' in data:
            cliente.email = data['email']
        if 'endereco' in data:
            cliente.endereco = data['endereco']
        if 'cep' in data:
            cliente.cep = data['cep']
        
        cliente.save()
        
        registrar_log('checkout.internal_api',
                     f"Cliente atualizado - ID: {cliente_id}")
        
        return JsonResponse({
            'sucesso': True,
            'mensagem': 'Cliente atualizado com sucesso'
        })
        
    except CheckoutCliente.DoesNotExist:
        return JsonResponse({
            'sucesso': False,
            'mensagem': 'Cliente não encontrado'
        }, status=404)
    except Exception as e:
        registrar_log('checkout.internal_api',
                     f"Erro ao atualizar cliente {cliente_id}: {str(e)}",
                     nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro ao atualizar cliente: {str(e)}'
        }, status=500)


# ====================
# LINKS/TOKENS ENDPOINTS
# ====================

@csrf_exempt
@require_http_methods(["POST"])
def listar_tokens(request):
    """
    Lista tokens/links de pagamento por filtros
    
    POST /api/internal/checkout/tokens/listar/
    Body: {
        "loja_id": 1,
        "cpf": "12345678900",  # opcional
        "usado": true  # opcional
    }
    
    Response: {
        "sucesso": true,
        "total": 10,
        "tokens": [...]
    }
    """
    try:
        from checkout.link_pagamento_web.models import CheckoutToken
        from django.utils import timezone
        
        data = json.loads(request.body)
        loja_id = data.get('loja_id')
        cpf = data.get('cpf')
        usado = data.get('usado')
        
        queryset = CheckoutToken.objects.all()
        
        if loja_id:
            queryset = queryset.filter(loja_id=loja_id)
        if cpf:
            queryset = queryset.filter(cpf=cpf)
        if usado is not None:
            # usado vem como boolean no JSON
            queryset = queryset.filter(used=usado)
        
        tokens = []
        for token in queryset.order_by('-created_at')[:100]:  # Limitar 100 resultados
            tokens.append({
                'id': token.id,
                'token': token.token,
                'loja_id': token.loja_id,
                'item_nome': token.item_nome,
                'item_valor': str(token.item_valor),
                'nome_completo': token.nome_completo,
                'cpf': token.cpf,
                'celular': token.celular,
                'pedido_origem_loja': token.pedido_origem_loja,
                'used': token.used,
                'expires_at': token.expires_at.isoformat(),
                'is_valid': token.is_valid(),
                'tentativas_pagamento': token.tentativas_pagamento,
                'created_at': token.created_at.isoformat(),
            })
        
        registrar_log('checkout.internal_api',
                     f"Lista tokens - Loja: {loja_id}, Total: {len(tokens)}")
        
        return JsonResponse({
            'sucesso': True,
            'total': len(tokens),
            'tokens': tokens
        })
        
    except Exception as e:
        registrar_log('checkout.internal_api',
                     f"Erro ao listar tokens: {str(e)}",
                     nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro ao listar tokens: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def criar_token(request):
    """
    Cria novo token/link de pagamento
    
    POST /api/internal/checkout/tokens/
    Body: {
        "loja_id": 1,
        "item_nome": "Produto X",
        "item_valor": "150.00",
        "nome_completo": "João Silva",
        "cpf": "12345678900",
        "celular": "11999999999",
        "endereco_completo": "Rua X, 123",
        "pedido_origem_loja": "PED123",
        "created_by": "portal_vendas"
    }
    
    Response: {
        "sucesso": true,
        "token": "abc123...",
        "token_id": 456,
        "link": "https://..."
    }
    """
    try:
        from checkout.link_pagamento_web.models import CheckoutToken
        
        data = json.loads(request.body)
        
        loja_id = data.get('loja_id')
        item_nome = data.get('item_nome')
        item_valor = Decimal(str(data.get('item_valor')))
        nome_completo = data.get('nome_completo')
        cpf = data.get('cpf')
        celular = data.get('celular')
        endereco_completo = data.get('endereco_completo')
        pedido_origem_loja = data.get('pedido_origem_loja')
        created_by = data.get('created_by', 'api_interna')
        
        if not all([loja_id, item_nome, item_valor, nome_completo, cpf, celular, endereco_completo]):
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'Campos obrigatórios: loja_id, item_nome, item_valor, nome_completo, cpf, celular, endereco_completo'
            }, status=400)
        
        # Criar token usando método da classe
        token_obj = CheckoutToken.generate_token(
            loja_id=loja_id,
            item_nome=item_nome,
            item_valor=item_valor,
            nome_completo=nome_completo,
            cpf=cpf,
            celular=celular,
            endereco_completo=endereco_completo,
            created_by=created_by,
            pedido_origem_loja=pedido_origem_loja
        )
        
        # TODO: Construir URL completa do link (necessita configuração de domínio)
        link = f"/checkout/{token_obj.token}/"
        
        registrar_log('checkout.internal_api',
                     f"Token criado - ID: {token_obj.id}, Loja: {loja_id}, Valor: R$ {item_valor}")
        
        return JsonResponse({
            'sucesso': True,
            'token': token_obj.token,
            'token_id': token_obj.id,
            'link': link,
            'expires_at': token_obj.expires_at.isoformat(),
            'mensagem': 'Token criado com sucesso'
        })
        
    except Exception as e:
        registrar_log('checkout.internal_api',
                     f"Erro ao criar token: {str(e)}",
                     nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro ao criar token: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def obter_token(request):
    """
    Obtém detalhes de um token pelo valor
    
    POST /api/internal/checkout/tokens/obter/
    Body: {
        "token": "abc123..."
    }
    
    Response: {
        "sucesso": true,
        "token": {...}
    }
    """
    try:
        from checkout.link_pagamento_web.models import CheckoutToken
        
        data = json.loads(request.body)
        token_value = data.get('token')
        
        if not token_value:
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'token é obrigatório'
            }, status=400)
        
        token = CheckoutToken.objects.get(token=token_value)
        
        dados = {
            'id': token.id,
            'token': token.token,
            'loja_id': token.loja_id,
            'item_nome': token.item_nome,
            'item_valor': str(token.item_valor),
            'nome_completo': token.nome_completo,
            'cpf': token.cpf,
            'celular': token.celular,
            'endereco_completo': token.endereco_completo,
            'pedido_origem_loja': token.pedido_origem_loja,
            'used': token.used,
            'used_at': token.used_at.isoformat() if token.used_at else None,
            'expires_at': token.expires_at.isoformat(),
            'is_valid': token.is_valid(),
            'tentativas_pagamento': token.tentativas_pagamento,
            'created_by': token.created_by,
            'created_at': token.created_at.isoformat(),
        }
        
        return JsonResponse({
            'sucesso': True,
            'token': dados
        })
        
    except CheckoutToken.DoesNotExist:
        return JsonResponse({
            'sucesso': False,
            'mensagem': 'Token não encontrado'
        }, status=404)
    except Exception as e:
        registrar_log('checkout.internal_api',
                     f"Erro ao obter token {token_value[:8]}...: {str(e)}",
                     nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro ao obter token: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def validar_token(request):
    """
    Valida se um token ainda é válido
    
    POST /api/internal/checkout/tokens/validar/
    Body: {
        "token": "abc123..."
    }
    
    Response: {
        "sucesso": true,
        "valido": true,
        "motivo": "Token válido"
    }
    """
    try:
        from checkout.link_pagamento_web.models import CheckoutToken
        from django.utils import timezone
        
        data = json.loads(request.body)
        token_value = data.get('token')
        
        if not token_value:
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'Token é obrigatório'
            }, status=400)
        
        try:
            token = CheckoutToken.objects.get(token=token_value)
        except CheckoutToken.DoesNotExist:
            return JsonResponse({
                'sucesso': True,
                'valido': False,
                'motivo': 'Token não encontrado'
            })
        
        # Verificar validade
        if token.used:
            motivo = 'Token já utilizado'
        elif timezone.now() >= token.expires_at:
            motivo = 'Token expirado'
        elif token.tentativas_pagamento >= 3:
            motivo = 'Limite de tentativas excedido'
        else:
            motivo = 'Token válido'
        
        valido = token.is_valid()
        
        registrar_log('checkout.internal_api',
                     f"Validação token - Válido: {valido}, Motivo: {motivo}")
        
        return JsonResponse({
            'sucesso': True,
            'valido': valido,
            'motivo': motivo,
            'tentativas_restantes': max(0, 3 - token.tentativas_pagamento) if not token.used else 0,
            'expires_at': token.expires_at.isoformat()
        })
        
    except Exception as e:
        registrar_log('checkout.internal_api',
                     f"Erro ao validar token: {str(e)}",
                     nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro ao validar token: {str(e)}'
        }, status=500)
