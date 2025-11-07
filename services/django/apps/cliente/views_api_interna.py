"""
Views de API Interna para comunicação entre containers
Endpoints usados pelo container POS para acessar dados de clientes
"""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from wallclub_core.oauth.decorators import require_oauth_internal
from wallclub_core.utilitarios.log_control import registrar_log
from .models import Cliente
from .services import ClienteAuthService


@api_view(['POST'])
@require_oauth_internal
def consultar_por_cpf(request):
    """
    Consulta cliente por CPF e canal_id
    Usado pelo container POS
    """
    try:
        cpf = request.data.get('cpf')
        canal_id = request.data.get('canal_id')
        
        if not cpf or not canal_id:
            return Response({
                'sucesso': False,
                'mensagem': 'CPF e canal_id são obrigatórios'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Buscar cliente
        cliente = Cliente.objects.filter(cpf=cpf, canal_id=canal_id).first()
        
        if not cliente:
            return Response({
                'sucesso': False,
                'mensagem': 'Cliente não encontrado',
                'cliente': None
            })
        
        # Retornar dados do cliente
        return Response({
            'sucesso': True,
            'cliente': {
                'id': cliente.id,
                'cpf': cliente.cpf,
                'nome': cliente.nome,
                'celular': cliente.celular or '',
                'email': cliente.email or '',
                'firebase_token': cliente.firebase_token or '',
                'is_active': cliente.is_active,
                'canal_id': cliente.canal_id
            }
        })
        
    except Exception as e:
        registrar_log('apps.cliente', f'Erro ao consultar cliente: {str(e)}', nivel='ERROR')
        return Response({
            'sucesso': False,
            'mensagem': f'Erro ao consultar cliente: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@require_oauth_internal
def cadastrar(request):
    """
    Cadastra novo cliente (com consulta bureau)
    Usado pelo container POS
    """
    try:
        cpf = request.data.get('cpf')
        celular = request.data.get('celular', '')
        canal_id = request.data.get('canal_id')
        
        if not cpf or not canal_id:
            return Response({
                'sucesso': False,
                'mensagem': 'CPF e canal_id são obrigatórios'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Usar serviço de cadastro
        resultado = ClienteAuthService.cadastrar(cpf, celular, canal_id)
        
        return Response(resultado)
        
    except Exception as e:
        registrar_log('apps.cliente', f'Erro ao cadastrar cliente: {str(e)}', nivel='ERROR')
        return Response({
            'sucesso': False,
            'mensagem': f'Erro ao cadastrar cliente: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@require_oauth_internal
def obter_cliente_id(request):
    """
    Obtém ID do cliente por CPF e canal_id
    Usado pelo container POS
    """
    try:
        cpf = request.data.get('cpf')
        canal_id = request.data.get('canal_id')
        
        if not cpf or not canal_id:
            return Response({
                'sucesso': False,
                'mensagem': 'CPF e canal_id são obrigatórios'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        resultado = ClienteAuthService.obter_cliente_id(cpf, canal_id)
        return Response(resultado)
        
    except Exception as e:
        registrar_log('apps.cliente', f'Erro ao obter cliente_id: {str(e)}', nivel='ERROR')
        return Response({
            'sucesso': False,
            'mensagem': f'Erro: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@require_oauth_internal
def atualizar_celular(request):
    """
    Atualiza celular do cliente
    Usado pelo container POS
    """
    try:
        cliente_id = request.data.get('cliente_id')
        celular = request.data.get('celular')
        
        if not cliente_id or not celular:
            return Response({
                'sucesso': False,
                'mensagem': 'cliente_id e celular são obrigatórios'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        resultado = ClienteAuthService.atualizar_celular_cliente(cliente_id, celular)
        return Response(resultado)
        
    except Exception as e:
        registrar_log('apps.cliente', f'Erro ao atualizar celular: {str(e)}', nivel='ERROR')
        return Response({
            'sucesso': False,
            'mensagem': f'Erro: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@require_oauth_internal
def obter_dados_cliente(request):
    """
    Obtém dados completos do cliente
    Usado pelo container POS
    """
    try:
        cpf = request.data.get('cpf')
        canal_id = request.data.get('canal_id')
        
        if not cpf or not canal_id:
            return Response({
                'sucesso': False,
                'mensagem': 'CPF e canal_id são obrigatórios'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        resultado = ClienteAuthService.obter_dados_cliente(cpf, canal_id)
        
        if resultado:
            return Response({
                'sucesso': True,
                'dados': resultado
            })
        else:
            return Response({
                'sucesso': False,
                'mensagem': 'Cliente não encontrado'
            })
        
    except Exception as e:
        registrar_log('apps.cliente', f'Erro ao obter dados do cliente: {str(e)}', nivel='ERROR')
        return Response({
            'sucesso': False,
            'mensagem': f'Erro: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@require_oauth_internal
def verificar_cadastro(request):
    """
    Verifica se cliente tem cadastro no canal
    Usado pelo container POS
    """
    try:
        cpf = request.data.get('cpf')
        canal_id = request.data.get('canal_id')
        
        if not cpf or not canal_id:
            return Response({
                'sucesso': False,
                'mensagem': 'CPF e canal_id são obrigatórios'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        tem_cadastro = Cliente.objects.filter(cpf=cpf, canal_id=canal_id).exists()
        
        return Response({
            'sucesso': True,
            'tem_cadastro': tem_cadastro
        })
        
    except Exception as e:
        registrar_log('apps.cliente', f'Erro ao verificar cadastro: {str(e)}', nivel='ERROR')
        return Response({
            'sucesso': False,
            'mensagem': f'Erro: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
