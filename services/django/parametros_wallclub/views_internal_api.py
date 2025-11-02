"""
APIs Internas de Parâmetros WallClub
Comunicação entre containers (Portais → Parâmetros)
Sem rate limiting (middleware interno)
"""
import json
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from wallclub_core.utilitarios.log_control import registrar_log
from .services import ParametrosService


@csrf_exempt
@require_http_methods(["POST"])
def buscar_configuracoes_loja(request):
    """
    Busca configurações de uma loja em uma data específica
    
    POST /api/internal/parametros/configuracoes/loja/
    Body: {
        "loja_id": 1,
        "data_referencia": "2025-11-01T15:00:00"  # ISO format
    }
    
    Response: {
        "sucesso": true,
        "total": 10,
        "configuracoes": [...]
    }
    """
    try:
        data = json.loads(request.body)
        loja_id = data.get('loja_id')
        data_referencia_str = data.get('data_referencia')
        
        if not loja_id:
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'loja_id obrigatório'
            }, status=400)
        
        # Converter data
        if data_referencia_str:
            data_referencia = datetime.fromisoformat(data_referencia_str.replace('Z', '+00:00'))
        else:
            data_referencia = datetime.now()
        
        # Buscar configurações via service
        configuracoes = ParametrosService.buscar_configuracoes_loja(loja_id, data_referencia)
        
        # Serializar
        configs_list = []
        for config in configuracoes:
            configs_list.append({
                'id': config.id,
                'loja_id': config.loja_id,
                'id_plano': config.id_plano,
                'wall': config.wall,
                'vigencia_inicio': config.vigencia_inicio.isoformat(),
                'vigencia_fim': config.vigencia_fim.isoformat() if config.vigencia_fim else None,
                'parametro_loja_1': str(config.parametro_loja_1),
                'parametro_loja_2': str(config.parametro_loja_2),
                'parametro_loja_3': str(config.parametro_loja_3),
                'parametro_loja_4': str(config.parametro_loja_4),
                'parametro_loja_5': str(config.parametro_loja_5),
                'parametro_loja_6': str(config.parametro_loja_6),
                'parametro_loja_7': str(config.parametro_loja_7),
                'criado_em': config.criado_em.isoformat(),
                'atualizado_em': config.atualizado_em.isoformat(),
            })
        
        registrar_log('parametros.internal_api',
                     f"Buscar configs loja {loja_id} - Total: {len(configs_list)}")
        
        return JsonResponse({
            'sucesso': True,
            'total': len(configs_list),
            'configuracoes': configs_list
        })
        
    except Exception as e:
        registrar_log('parametros.internal_api',
                     f"Erro ao buscar configurações: {str(e)}",
                     nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro ao buscar configurações: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def contar_configuracoes_loja(request):
    """
    Conta configurações vigentes de uma loja
    
    POST /api/internal/parametros/configuracoes/contar/
    Body: {
        "loja_id": 1
    }
    
    Response: {
        "sucesso": true,
        "total": 15
    }
    """
    try:
        data = json.loads(request.body)
        loja_id = data.get('loja_id')
        
        if not loja_id:
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'loja_id obrigatório'
            }, status=400)
        
        total = ParametrosService.contar_configuracoes_loja(loja_id)
        
        return JsonResponse({
            'sucesso': True,
            'total': total
        })
        
    except Exception as e:
        registrar_log('parametros.internal_api',
                     f"Erro ao contar configurações: {str(e)}",
                     nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def obter_ultima_configuracao(request):
    """
    Obtém última configuração de uma loja
    
    POST /api/internal/parametros/configuracoes/ultima/
    Body: {
        "loja_id": 1
    }
    
    Response: {
        "sucesso": true,
        "configuracao": {...}
    }
    """
    try:
        data = json.loads(request.body)
        loja_id = data.get('loja_id')
        
        if not loja_id:
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'loja_id obrigatório'
            }, status=400)
        
        config = ParametrosService.obter_ultima_configuracao(loja_id)
        
        if not config:
            return JsonResponse({
                'sucesso': True,
                'configuracao': None
            })
        
        return JsonResponse({
            'sucesso': True,
            'configuracao': {
                'id': config.id,
                'loja_id': config.loja_id,
                'vigencia_inicio': config.vigencia_inicio.isoformat(),
                'atualizado_em': config.atualizado_em.isoformat(),
            }
        })
        
    except Exception as e:
        registrar_log('parametros.internal_api',
                     f"Erro ao obter última configuração: {str(e)}",
                     nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def verificar_modalidades_loja(request):
    """
    Verifica modalidades Wall S/N de uma loja
    
    POST /api/internal/parametros/loja/modalidades/
    Body: {
        "loja_id": 1
    }
    
    Response: {
        "sucesso": true,
        "wall_s": true,
        "wall_n": false,
        "modalidades": ["Wall S"]
    }
    """
    try:
        data = json.loads(request.body)
        loja_id = data.get('loja_id')
        
        if not loja_id:
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'loja_id obrigatório'
            }, status=400)
        
        wall_s = ParametrosService.loja_tem_wall_s(loja_id)
        wall_n = ParametrosService.loja_tem_wall_n(loja_id)
        
        modalidades = []
        if wall_s:
            modalidades.append('Wall S')
        if wall_n:
            modalidades.append('Wall N')
        
        return JsonResponse({
            'sucesso': True,
            'wall_s': wall_s,
            'wall_n': wall_n,
            'modalidades': modalidades
        })
        
    except Exception as e:
        registrar_log('parametros.internal_api',
                     f"Erro ao verificar modalidades: {str(e)}",
                     nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def listar_planos(request):
    """
    Lista todos os planos
    
    GET /api/internal/parametros/planos/
    
    Response: {
        "sucesso": true,
        "total": 50,
        "planos": [...]
    }
    """
    try:
        planos = ParametrosService.listar_todos_planos()
        
        planos_list = []
        for plano in planos:
            planos_list.append({
                'id': plano.id,
                'descricao': plano.descricao,
                'modalidade': plano.modalidade,
                'parcelas': plano.parcelas,
                'prazo_limite': plano.prazo_limite,
                'bandeira': plano.bandeira,
                'wall': plano.wall,
                'id_original_wall': plano.id_original_wall,
                'id_original_sem_wall': plano.id_original_sem_wall,
            })
        
        return JsonResponse({
            'sucesso': True,
            'total': len(planos_list),
            'planos': planos_list
        })
        
    except Exception as e:
        registrar_log('parametros.internal_api',
                     f"Erro ao listar planos: {str(e)}",
                     nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def listar_importacoes(request):
    """
    Lista últimas importações
    
    GET /api/internal/parametros/importacoes/?limit=10
    
    Response: {
        "sucesso": true,
        "total": 5,
        "importacoes": [...]
    }
    """
    try:
        limit = int(request.GET.get('limit', 10))
        
        importacoes = ParametrosService.listar_ultimas_importacoes(limit=limit)
        
        importacoes_list = []
        for imp in importacoes:
            importacoes_list.append({
                'id': imp.id,
                'nome_arquivo': imp.nome_arquivo,
                'linhas_processadas': imp.linhas_processadas,
                'linhas_importadas': imp.linhas_importadas,
                'linhas_erro': imp.linhas_erro,
                'status': imp.status,
                'usuario_id': imp.usuario_id,
                'data_importacao': imp.data_importacao.isoformat(),
            })
        
        return JsonResponse({
            'sucesso': True,
            'total': len(importacoes_list),
            'importacoes': importacoes_list
        })
        
    except Exception as e:
        registrar_log('parametros.internal_api',
                     f"Erro ao listar importações: {str(e)}",
                     nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def obter_importacao(request, importacao_id):
    """
    Obtém detalhes de uma importação
    
    GET /api/internal/parametros/importacoes/{id}/
    
    Response: {
        "sucesso": true,
        "importacao": {...}
    }
    """
    try:
        importacao = ParametrosService.obter_importacao(importacao_id)
        
        if not importacao:
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'Importação não encontrada'
            }, status=404)
        
        return JsonResponse({
            'sucesso': True,
            'importacao': {
                'id': importacao.id,
                'nome_arquivo': importacao.nome_arquivo,
                'linhas_processadas': importacao.linhas_processadas,
                'linhas_importadas': importacao.linhas_importadas,
                'linhas_erro': importacao.linhas_erro,
                'status': importacao.status,
                'mensagem_erro': importacao.mensagem_erro,
                'usuario_id': importacao.usuario_id,
                'data_importacao': importacao.data_importacao.isoformat(),
                'created_at': importacao.created_at.isoformat(),
                'updated_at': importacao.updated_at.isoformat(),
            }
        })
        
    except Exception as e:
        registrar_log('parametros.internal_api',
                     f"Erro ao obter importação: {str(e)}",
                     nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro: {str(e)}'
        }, status=500)
