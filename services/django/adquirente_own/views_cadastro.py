"""
Views para APIs de cadastro de estabelecimentos na Own Financial
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication
from adquirente_own.services_consultas import ConsultasOwnService
from adquirente_own.services_cadastro import CadastroOwnService
from adquirente_own.serializers import (
    CnaeSerializer, CestaSerializer, CestaTarifaSerializer,
    CadastroOwnRequestSerializer, CadastroOwnResponseSerializer,
    LojaOwnSerializer
)
from adquirente_own.models_cadastro import LojaOwn
from wallclub_core.utilitarios.log_control import registrar_log


class ConsultarCnaeView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    """
    GET /api/own/cnae/
    Consulta atividades CNAE/MCC
    """

    def get(self, request):
        try:
            descricao = request.query_params.get('descricao')
            environment = request.query_params.get('environment', 'LIVE')

            service = ConsultasOwnService(environment=environment)
            resultado = service.consultar_atividades(descricao=descricao)

            if not resultado.get('sucesso'):
                return Response(
                    {'erro': resultado.get('mensagem')},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            serializer = CnaeSerializer(resultado.get('dados', []), many=True)
            return Response(serializer.data)

        except Exception as e:
            registrar_log('own.api', f'❌ Erro ao consultar CNAE: {str(e)}', nivel='ERROR')
            return Response(
                {'erro': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ConsultarCestasView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    """
    GET /api/own/cestas/
    Consulta cestas de tarifas
    """

    def get(self, request):
        try:
            nome_cesta = request.query_params.get('nome_cesta')
            environment = request.query_params.get('environment', 'LIVE')

            service = ConsultasOwnService(environment=environment)

            # Se não houver filtro, retornar lista de cestas únicas
            if not nome_cesta:
                cestas = service.listar_todas_cestas()
                serializer = CestaSerializer(cestas, many=True)
                return Response(serializer.data)

            # Com filtro, retornar todas as tarifas
            resultado = service.consultar_cestas(nome_cesta=nome_cesta)

            if not resultado.get('sucesso'):
                return Response(
                    {'erro': resultado.get('mensagem')},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            return Response(resultado.get('dados', []))

        except Exception as e:
            registrar_log('own.api', f'❌ Erro ao consultar cestas: {str(e)}', nivel='ERROR')
            return Response(
                {'erro': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ConsultarTarifasCestaView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    """
    GET /api/own/cestas/{cesta_id}/tarifas/
    Consulta tarifas de uma cesta específica
    """

    def get(self, request, cesta_id):
        try:
            environment = request.query_params.get('environment', 'LIVE')

            service = ConsultasOwnService(environment=environment)
            resultado = service.obter_tarifas_cesta(cesta_id=int(cesta_id))

            if not resultado.get('sucesso'):
                return Response(
                    {'erro': resultado.get('mensagem')},
                    status=status.HTTP_404_NOT_FOUND
                )

            return Response(resultado)

        except Exception as e:
            registrar_log('own.api', f'❌ Erro ao consultar tarifas da cesta: {str(e)}', nivel='ERROR')
            return Response(
                {'erro': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CadastrarEstabelecimentoView(APIView):
    """
    POST /api/own/cadastrar-estabelecimento/
    Cadastra estabelecimento na Own Financial
    """

    def post(self, request):
        try:
            # Validar dados de entrada
            serializer = CadastroOwnRequestSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {'erro': 'Dados inválidos', 'detalhes': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )

            loja_id = request.data.get('loja_id')
            if not loja_id:
                return Response(
                    {'erro': 'loja_id é obrigatório'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            environment = request.data.get('environment', 'LIVE')

            # Validar dados obrigatórios
            service = CadastroOwnService(environment=environment)
            validacao = service.validar_dados_cadastro(serializer.validated_data)

            if not validacao['valido']:
                return Response(
                    {'erro': 'Dados incompletos', 'detalhes': validacao['erros']},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Cadastrar estabelecimento
            resultado = service.cadastrar_estabelecimento(
                loja_id=loja_id,
                loja_data=serializer.validated_data
            )

            if not resultado.get('sucesso'):
                return Response(
                    {'erro': resultado.get('mensagem')},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            response_serializer = CadastroOwnResponseSerializer(resultado)
            return Response(response_serializer.data)

        except Exception as e:
            registrar_log('own.api', f'❌ Erro ao cadastrar estabelecimento: {str(e)}', nivel='ERROR')
            return Response(
                {'erro': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StatusCredenciamentoView(APIView):
    """
    GET /api/own/status-credenciamento/{loja_id}/
    Consulta status de credenciamento de uma loja
    """

    def get(self, request, loja_id):
        try:
            loja_own = LojaOwn.objects.filter(loja_id=loja_id).first()

            if not loja_own:
                return Response(
                    {'erro': 'Loja não cadastrada na Own'},
                    status=status.HTTP_404_NOT_FOUND
                )

            serializer = LojaOwnSerializer(loja_own)
            return Response(serializer.data)

        except Exception as e:
            registrar_log('own.api', f'❌ Erro ao consultar status: {str(e)}', nivel='ERROR')
            return Response(
                {'erro': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
