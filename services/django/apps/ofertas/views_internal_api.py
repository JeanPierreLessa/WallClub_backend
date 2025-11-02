"""
APIs Internas de Ofertas
Comunicação entre containers (Portais → Ofertas)
Sem rate limiting (middleware interno)
"""
import json
from decimal import Decimal
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from wallclub_core.utilitarios.log_control import registrar_log


@csrf_exempt
@require_http_methods(["POST"])
def listar_ofertas(request):
    """
    Lista ofertas com filtros
    
    POST /api/internal/ofertas/listar/
    Body: {
        "canal_id": 1,  # opcional
        "ativo": true,  # opcional
        "vigente": true  # opcional - apenas vigentes
    }
    
    Response: {
        "sucesso": true,
        "total": 10,
        "ofertas": [...]
    }
    """
    try:
        from .models import Oferta
        
        data = json.loads(request.body)
        canal_id = data.get('canal_id')
        ativo = data.get('ativo')
        vigente = data.get('vigente')
        
        queryset = Oferta.objects.all()
        
        if canal_id:
            queryset = queryset.filter(canal_id=canal_id)
        if ativo is not None:
            queryset = queryset.filter(ativo=ativo)
        
        if vigente:
            # Filtrar apenas vigentes
            agora = datetime.now()
            queryset = queryset.filter(
                vigencia_inicio__lte=agora,
                vigencia_fim__gte=agora,
                ativo=True
            )
        
        ofertas = []
        for oferta in queryset.order_by('-created_at')[:100]:
            ofertas.append({
                'id': oferta.id,
                'canal_id': oferta.canal_id,
                'titulo': oferta.titulo,
                'texto_push': oferta.texto_push,
                'descricao': oferta.descricao,
                'imagem_url': oferta.imagem_url,
                'vigencia_inicio': oferta.vigencia_inicio.isoformat(),
                'vigencia_fim': oferta.vigencia_fim.isoformat(),
                'ativo': oferta.ativo,
                'tipo_segmentacao': oferta.tipo_segmentacao,
                'grupo_id': oferta.grupo_id,
                'created_at': oferta.created_at.isoformat(),
            })
        
        registrar_log('ofertas.internal_api',
                     f"Lista ofertas - Canal: {canal_id}, Total: {len(ofertas)}")
        
        return JsonResponse({
            'sucesso': True,
            'total': len(ofertas),
            'ofertas': ofertas
        })
        
    except Exception as e:
        registrar_log('ofertas.internal_api',
                     f"Erro ao listar ofertas: {str(e)}",
                     nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro ao listar ofertas: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def criar_oferta(request):
    """
    Cria nova oferta
    
    POST /api/internal/ofertas/criar/
    Body: {
        "canal_id": 1,
        "titulo": "Oferta Especial",
        "texto_push": "Não perca!",
        "descricao": "Descrição completa...",
        "imagem_url": "https://...",
        "vigencia_inicio": "2025-11-01T00:00:00",
        "vigencia_fim": "2025-11-30T23:59:59",
        "tipo_segmentacao": "todos_canal",
        "grupo_id": null,
        "usuario_criador_id": 123,
        "ativo": true
    }
    
    Response: {
        "sucesso": true,
        "oferta_id": 456,
        "mensagem": "Oferta criada com sucesso"
    }
    """
    try:
        data = json.loads(request.body)
        
        titulo = data.get('titulo')
        texto_push = data.get('texto_push')
        descricao = data.get('descricao')
        imagem_url = data.get('imagem_url')
        vigencia_inicio = data.get('vigencia_inicio')
        vigencia_fim = data.get('vigencia_fim')
        canal_id = data.get('canal_id')
        tipo_segmentacao = data.get('tipo_segmentacao', 'todos_canal')
        grupo_id = data.get('grupo_id')
        usuario_criador_id = data.get('usuario_criador_id')
        ativo = data.get('ativo', True)
        
        if not all([titulo, texto_push, vigencia_inicio, vigencia_fim, canal_id]):
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'Campos obrigatórios: titulo, texto_push, vigencia_inicio, vigencia_fim, canal_id'
            }, status=400)
        
        # Converter datas
        vigencia_inicio_dt = datetime.fromisoformat(vigencia_inicio.replace('Z', '+00:00'))
        vigencia_fim_dt = datetime.fromisoformat(vigencia_fim.replace('Z', '+00:00'))
        
        # Usar service
        from .services import OfertaService
        
        sucesso, mensagem, oferta_id = OfertaService.criar_oferta(
            titulo=titulo,
            texto_push=texto_push,
            descricao=descricao,
            imagem_url=imagem_url,
            vigencia_inicio=vigencia_inicio_dt,
            vigencia_fim=vigencia_fim_dt,
            canal_id=canal_id,
            tipo_segmentacao=tipo_segmentacao,
            grupo_id=grupo_id,
            usuario_criador_id=usuario_criador_id,
            ativo=ativo
        )
        
        if sucesso:
            return JsonResponse({
                'sucesso': True,
                'oferta_id': oferta_id,
                'mensagem': mensagem
            })
        else:
            return JsonResponse({
                'sucesso': False,
                'mensagem': mensagem
            }, status=400)
        
    except Exception as e:
        registrar_log('ofertas.internal_api',
                     f"Erro ao criar oferta: {str(e)}",
                     nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro ao criar oferta: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def obter_oferta(request):
    """
    Obtém detalhes de uma oferta
    
    POST /api/internal/ofertas/obter/
    Body: {
        "oferta_id": 123
    }
    
    Response: {
        "sucesso": true,
        "oferta": {...}
    }
    """
    try:
        data = json.loads(request.body)
        oferta_id = data.get('oferta_id')
        
        if not oferta_id:
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'oferta_id é obrigatório'
            }, status=400)
        
        from .services import OfertaService
        
        oferta = OfertaService.obter_oferta_por_id(oferta_id)
        
        if not oferta:
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'Oferta não encontrada'
            }, status=404)
        
        dados = {
            'id': oferta.id,
            'canal_id': oferta.canal_id,
            'titulo': oferta.titulo,
            'texto_push': oferta.texto_push,
            'descricao': oferta.descricao,
            'imagem_url': oferta.imagem_url,
            'vigencia_inicio': oferta.vigencia_inicio.isoformat(),
            'vigencia_fim': oferta.vigencia_fim.isoformat(),
            'ativo': oferta.ativo,
            'tipo_segmentacao': oferta.tipo_segmentacao,
            'grupo_id': oferta.grupo_id,
            'usuario_criador_id': oferta.usuario_criador_id,
            'created_at': oferta.created_at.isoformat(),
            'updated_at': oferta.updated_at.isoformat() if oferta.updated_at else None,
        }
        
        return JsonResponse({
            'sucesso': True,
            'oferta': dados
        })
        
    except Exception as e:
        registrar_log('ofertas.internal_api',
                     f"Erro ao obter oferta: {str(e)}",
                     nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro ao obter oferta: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def atualizar_oferta(request):
    """
    Atualiza dados de uma oferta
    
    POST /api/internal/ofertas/atualizar/
    Body: {
        "oferta_id": 123,
        "titulo": "Novo título",
        "ativo": false,
        ...
    }
    
    Response: {
        "sucesso": true,
        "mensagem": "Oferta atualizada"
    }
    """
    try:
        data = json.loads(request.body)
        oferta_id = data.get('oferta_id')
        
        if not oferta_id:
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'oferta_id é obrigatório'
            }, status=400)
        
        # Remover oferta_id dos dados de atualização
        dados_update = {k: v for k, v in data.items() if k != 'oferta_id'}
        
        # Converter datas se necessário
        if 'vigencia_inicio' in dados_update:
            dados_update['vigencia_inicio'] = datetime.fromisoformat(
                dados_update['vigencia_inicio'].replace('Z', '+00:00')
            )
        if 'vigencia_fim' in dados_update:
            dados_update['vigencia_fim'] = datetime.fromisoformat(
                dados_update['vigencia_fim'].replace('Z', '+00:00')
            )
        
        from .services import OfertaService
        
        sucesso, mensagem = OfertaService.atualizar_oferta(oferta_id, dados_update)
        
        if sucesso:
            return JsonResponse({
                'sucesso': True,
                'mensagem': mensagem
            })
        else:
            return JsonResponse({
                'sucesso': False,
                'mensagem': mensagem
            }, status=400)
        
    except Exception as e:
        registrar_log('ofertas.internal_api',
                     f"Erro ao atualizar oferta: {str(e)}",
                     nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro ao atualizar oferta: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def listar_grupos(request):
    """
    Lista grupos de segmentação
    
    POST /api/internal/ofertas/grupos/listar/
    Body: {
        "canal_id": 1,  # opcional
        "apenas_ativos": true  # opcional
    }
    
    Response: {
        "sucesso": true,
        "total": 5,
        "grupos": [...]
    }
    """
    try:
        data = json.loads(request.body)
        canal_id = data.get('canal_id')
        apenas_ativos = data.get('apenas_ativos', True)
        
        from .services import OfertaService
        
        grupos = OfertaService.listar_grupos_segmentacao(canal_id, apenas_ativos)
        
        grupos_list = []
        for grupo in grupos:
            grupos_list.append({
                'id': grupo.id,
                'canal_id': grupo.canal_id,
                'nome': grupo.nome,
                'descricao': grupo.descricao,
                'criterio_tipo': grupo.criterio_tipo,
                'ativo': grupo.ativo,
                'created_at': grupo.created_at.isoformat(),
            })
        
        registrar_log('ofertas.internal_api',
                     f"Lista grupos - Canal: {canal_id}, Total: {len(grupos_list)}")
        
        return JsonResponse({
            'sucesso': True,
            'total': len(grupos_list),
            'grupos': grupos_list
        })
        
    except Exception as e:
        registrar_log('ofertas.internal_api',
                     f"Erro ao listar grupos: {str(e)}",
                     nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro ao listar grupos: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def criar_grupo(request):
    """
    Cria novo grupo de segmentação
    
    POST /api/internal/ofertas/grupos/criar/
    Body: {
        "canal_id": 1,
        "nome": "Clientes Premium",
        "descricao": "Clientes com alto valor",
        "criterio_tipo": "manual",
        "ativo": true
    }
    
    Response: {
        "sucesso": true,
        "grupo_id": 789,
        "mensagem": "Grupo criado com sucesso"
    }
    """
    try:
        data = json.loads(request.body)
        
        canal_id = data.get('canal_id')
        nome = data.get('nome')
        descricao = data.get('descricao', '')
        criterio_tipo = data.get('criterio_tipo', 'manual')
        ativo = data.get('ativo', True)
        
        if not all([canal_id, nome]):
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'Campos obrigatórios: canal_id, nome'
            }, status=400)
        
        from .models import GrupoSegmentacao
        
        # Criar grupo
        grupo = GrupoSegmentacao(
            canal_id=canal_id,
            nome=nome,
            descricao=descricao,
            criterio_tipo=criterio_tipo,
            ativo=ativo,
            created_at=datetime.now()
        )
        grupo.save()
        
        registrar_log('ofertas.internal_api',
                     f"Grupo criado - ID: {grupo.id}, Nome: {nome}")
        
        return JsonResponse({
            'sucesso': True,
            'grupo_id': grupo.id,
            'mensagem': 'Grupo criado com sucesso'
        })
        
    except Exception as e:
        registrar_log('ofertas.internal_api',
                     f"Erro ao criar grupo: {str(e)}",
                     nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro ao criar grupo: {str(e)}'
        }, status=500)
