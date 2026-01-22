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


@require_http_methods(["GET"])
def consultar_protocolo(request):
    """
    GET /api/own/protocolo/
    Consulta status de protocolo de cadastro Own

    Params:
        loja_id: ID da loja (obrigatório)
    """
    try:
        loja_id = request.GET.get('loja_id')

        if not loja_id:
            return JsonResponse(
                {'erro': 'loja_id é obrigatório'},
                status=400
            )

        # Buscar dados da loja
        try:
            loja_own = LojaOwn.objects.get(loja_id=loja_id)
        except LojaOwn.DoesNotExist:
            return JsonResponse(
                {'erro': 'Loja não possui dados Own'},
                status=404
            )

        # Buscar CNPJ da loja
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT cnpj FROM loja WHERE id = %s", [loja_id])
            row = cursor.fetchone()
            if not row or not row[0]:
                return JsonResponse(
                    {'erro': 'CNPJ da loja não encontrado'},
                    status=404
                )
            cnpj = row[0]

        environment = request.GET.get('environment', 'LIVE')

        service = ConsultasOwnService(environment=environment)
        resultado = service.consultar_protocolo(
            cnpj_estabelecimento=cnpj,
            protocolo=loja_own.protocolo
        )

        if not resultado.get('sucesso'):
            return JsonResponse(
                {'erro': resultado.get('mensagem')},
                status=500
            )

        dados = resultado.get('dados', [])

        # Se encontrou protocolo, retornar o primeiro (mais recente)
        if dados:
            protocolo_info = dados[0]
            return JsonResponse({
                'sucesso': True,
                'protocolo': protocolo_info.get('protocoloCore'),
                'status': protocolo_info.get('status'),
                'dataRecebimento': protocolo_info.get('dataRecebimento'),
                'motivo': protocolo_info.get('motivo'),
                'tipo': protocolo_info.get('tipo'),
                'reenvio': protocolo_info.get('reenvio'),
                'contrato': protocolo_info.get('contrato'),
                'podeReenviar': protocolo_info.get('status') in ['ERRO', 'REPROVED']
            })

        return JsonResponse({
            'sucesso': False,
            'erro': 'Protocolo não encontrado na Own'
        }, status=404)

    except Exception as e:
        registrar_log('adquirente_own', f'❌ Erro ao consultar protocolo: {str(e)}', nivel='ERROR')
        return JsonResponse(
            {'erro': str(e)},
            status=500
        )
