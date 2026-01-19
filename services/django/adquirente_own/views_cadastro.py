"""
Views para APIs de cadastro de estabelecimentos na Own Financial
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from adquirente_own.services_consultas import ConsultasOwnService
from adquirente_own.services_cadastro import CadastroOwnService
from adquirente_own.models_cadastro import LojaOwn
from wallclub_core.utilitarios.log_control import registrar_log


@require_http_methods(["GET"])
def consultar_cnae(request):
    """
    GET /api/own/cnae/
    Consulta atividades CNAE/MCC
    """
    # TODO: Adicionar autenticação depois de testar
    # if not request.user.is_authenticated:
    #     return JsonResponse({'erro': 'Não autenticado'}, status=401)

    try:
        descricao = request.GET.get('descricao')
        environment = request.GET.get('environment', 'LIVE')

        service = ConsultasOwnService(environment=environment)
        resultado = service.consultar_atividades(descricao=descricao)

        if not resultado.get('sucesso'):
            return JsonResponse(
                {'erro': resultado.get('mensagem')},
                status=500
            )

        return JsonResponse(resultado.get('dados', []), safe=False)

    except Exception as e:
        registrar_log('own.api', f'❌ Erro ao consultar CNAE: {str(e)}', nivel='ERROR')
        return JsonResponse(
            {'erro': str(e)},
            status=500
        )


@require_http_methods(["GET"])
def consultar_cestas(request):
    """
    GET /api/own/cestas/
    Consulta cestas de tarifas
    """
    # TODO: Adicionar autenticação depois de testar
    # if not request.user.is_authenticated:
    #     return JsonResponse({'erro': 'Não autenticado'}, status=401)

    try:
        nome_cesta = request.GET.get('nome_cesta')
        environment = request.GET.get('environment', 'LIVE')

        service = ConsultasOwnService(environment=environment)

        # Se não houver filtro, retornar lista de cestas únicas
        if not nome_cesta:
            cestas = service.listar_todas_cestas()
            return JsonResponse(cestas, safe=False)

        # Com filtro, retornar todas as tarifas
        resultado = service.consultar_cestas(nome_cesta=nome_cesta)

        if not resultado.get('sucesso'):
            return JsonResponse(
                {'erro': resultado.get('mensagem')},
                status=500
            )

        return JsonResponse(resultado.get('dados', []), safe=False)

    except Exception as e:
        registrar_log('own.api', f'❌ Erro ao consultar cestas: {str(e)}', nivel='ERROR')
        return JsonResponse(
            {'erro': str(e)},
            status=500
        )


@require_http_methods(["GET"])
def consultar_tarifas_cesta(request, cesta_id):
    """
    GET /api/own/cestas/{cesta_id}/tarifas/
    Consulta tarifas de uma cesta específica
    """
    # TODO: Adicionar autenticação depois de testar
    # if not request.user.is_authenticated:
    #     return JsonResponse({'erro': 'Não autenticado'}, status=401)

    try:
        environment = request.GET.get('environment', 'LIVE')

        service = ConsultasOwnService(environment=environment)
        resultado = service.obter_tarifas_cesta(cesta_id=int(cesta_id))

        if not resultado.get('sucesso'):
            return JsonResponse(
                {'erro': resultado.get('mensagem')},
                status=500
            )

        return JsonResponse(resultado)

    except Exception as e:
        registrar_log('own.api', f'❌ Erro ao consultar tarifas da cesta: {str(e)}', nivel='ERROR')
        return JsonResponse(
            {'erro': str(e)},
            status=500
        )


# Funções de cadastro e status removidas - não são usadas pelas URLs atuais
