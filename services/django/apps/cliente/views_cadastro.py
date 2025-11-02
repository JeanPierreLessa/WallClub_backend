# apps/cliente/views_cadastro.py
"""
Endpoints para cadastro completo de cliente no app
Data: 27/10/2025
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from wallclub_core.oauth.decorators import require_oauth_apps
from wallclub_core.utilitarios.log_control import registrar_log
from apps.cliente.models import Cliente
from apps.cliente.services_cadastro import CadastroService


@api_view(['POST'])
@permission_classes([AllowAny])
@require_oauth_apps
def iniciar_cadastro(request):
    """
    Verifica se CPF existe e retorna dados faltantes
    
    Request:
        {
            "cpf": "17653377807",
            "canal_id": 1
        }
    
    Response - Cliente não existe (200):
        {
            "sucesso": true,
            "cliente_existe": false,
            "dados_necessarios": ["nome", "email", "celular", "senha"],
            "mensagem": "Preencha os dados para criar sua conta"
        }
    
    Response - Cliente existe sem cadastro (200):
        {
            "sucesso": true,
            "cliente_existe": true,
            "cadastro_completo": false,
            "dados_existentes": {
                "nome": "JOAO DA SILVA",
                "cpf": "17653377807",
                "email": "joao@email.com"
            },
            "dados_necessarios": ["celular", "senha"],
            "mensagem": "Complete seu cadastro"
        }
    
    Response - Cliente já cadastrado (400):
        {
            "sucesso": false,
            "mensagem": "CPF já cadastrado. Faça login ou recupere sua senha."
        }
    """
    try:
        cpf = request.data.get('cpf')
        canal_id = request.data.get('canal_id')
        
        if not cpf or not canal_id:
            return Response({
                'sucesso': False,
                'mensagem': 'CPF e canal_id são obrigatórios'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        resultado = CadastroService.verificar_cpf_cadastro(cpf, canal_id)
        
        if resultado['sucesso']:
            return Response(resultado, status=status.HTTP_200_OK)
        else:
            return Response(resultado, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        registrar_log('apps.cliente', 
            f"Erro ao verificar cadastro: {str(e)}", nivel='ERROR')
        
        return Response({
            'sucesso': False,
            'mensagem': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
@require_oauth_apps
def finalizar_cadastro(request):
    """
    Salva dados do cadastro + envia OTP para validação
    
    Request - Cliente novo:
        {
            "cpf": "17653377807",
            "canal_id": 1,
            "nome": "João da Silva",
            "email": "joao@email.com",
            "celular": "21987654321",
            "senha": "Senha@123"
        }
    
    Request - Cliente existente (só faltam campos):
        {
            "cpf": "17653377807",
            "canal_id": 1,
            "celular": "21987654321",
            "senha": "Senha@123"
        }
    
    Response (200):
        {
            "sucesso": true,
            "mensagem": "Código de verificação enviado via SMS",
            "celular_mascarado": "(21) 9****-4321"
        }
    
    Response - Erro validação (400):
        {
            "sucesso": false,
            "mensagem": "Senha fraca. Use no mínimo 8 caracteres com letras e números."
        }
    """
    try:
        dados = {
            'cpf': request.data.get('cpf'),
            'canal_id': request.data.get('canal_id'),
            'nome': request.data.get('nome'),
            'email': request.data.get('email'),
            'celular': request.data.get('celular'),
            'senha': request.data.get('senha')
        }
        
        resultado = CadastroService.finalizar_cadastro(dados)
        
        if resultado['sucesso']:
            return Response(resultado, status=status.HTTP_200_OK)
        else:
            return Response(resultado, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        registrar_log('apps.cliente', 
            f"Erro ao finalizar cadastro: {str(e)}", nivel='ERROR')
        
        return Response({
            'sucesso': False,
            'mensagem': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
@require_oauth_apps
def validar_otp_cadastro(request):
    """
    Valida OTP + finaliza cadastro (marca cadastro_completo=TRUE)
    
    Request:
        {
            "cpf": "17653377807",
            "codigo": "123456"
        }
    
    Response - Sucesso (200):
        {
            "sucesso": true,
            "mensagem": "Cadastro concluído com sucesso! Faça login para acessar sua conta."
        }
    
    Response - OTP inválido (400):
        {
            "sucesso": false,
            "mensagem": "Código inválido ou expirado",
            "tentativas_restantes": 2
        }
    """
    try:
        cpf = request.data.get('cpf')
        codigo = request.data.get('codigo')
        canal_id = request.data.get('canal_id')
        
        if not cpf or not codigo or not canal_id:
            return Response({
                'sucesso': False,
                'mensagem': 'CPF, código e canal_id são obrigatórios'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        resultado = CadastroService.validar_otp_cadastro(cpf, codigo, canal_id)
        
        if resultado['sucesso']:
            return Response(resultado, status=status.HTTP_200_OK)
        else:
            return Response(resultado, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        registrar_log('apps.cliente', 
            f"Erro ao validar OTP cadastro: {str(e)}", nivel='ERROR')
        
        return Response({
            'sucesso': False,
            'mensagem': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
