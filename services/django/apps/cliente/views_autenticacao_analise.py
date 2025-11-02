"""
Views para análise de autenticação (usado pelo engine de fraude)
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from wallclub_core.oauth.decorators import require_oauth_riskengine
from wallclub_core.utilitarios.log_control import registrar_log
from .services_autenticacao_analise import ClienteAutenticacaoAnaliseService
from .serializers_autenticacao import ClienteAutenticacaoAnaliseSerializer


class ClienteAutenticacaoAnaliseView(APIView):
    """
    Endpoint para consulta de dados de autenticação para análise de risco
    Usado pelo wallclub-riskengine via OAuth 2.0
    
    GET /api/v1/cliente/autenticacao/analise/<cpf>/
    """
    
    @require_oauth_riskengine
    def get(self, request, cpf):
        """
        Retorna análise completa do histórico de autenticação
        
        Args:
            cpf: CPF do cliente (11 dígitos)
        
        Query params opcionais:
            canal_id: Filtrar por canal específico
        
        Returns:
            200: Dados de autenticação
            400: CPF inválido
            500: Erro interno
        """
        try:
            # Validar CPF
            if not cpf or len(cpf) != 11 or not cpf.isdigit():
                return Response(
                    {
                        'erro': 'CPF inválido. Deve conter 11 dígitos numéricos.',
                        'cpf_recebido': cpf
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Canal opcional
            canal_id = request.GET.get('canal_id')
            if canal_id:
                try:
                    canal_id = int(canal_id)
                except (ValueError, TypeError):
                    return Response(
                        {'erro': 'canal_id inválido'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Buscar análise
            resultado = ClienteAutenticacaoAnaliseService.analisar_historico_cliente(
                cpf=cpf,
                canal_id=canal_id
            )
            
            # Serializar resposta
            serializer = ClienteAutenticacaoAnaliseSerializer(data=resultado)
            serializer.is_valid(raise_exception=True)
            
            # Log de auditoria
            registrar_log(
                'apps.cliente.autenticacao_analise',
                f"Consulta de análise: CPF {cpf[:3]}*** - Encontrado: {resultado.get('encontrado')} - Flags: {len(resultado.get('flags_risco', []))}",
                nivel='INFO'
            )
            
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            registrar_log(
                'apps.cliente.autenticacao_analise',
                f"Erro ao processar consulta: {str(e)}",
                nivel='ERROR'
            )
            return Response(
                {
                    'erro': 'Erro interno ao processar consulta',
                    'detalhes': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
