# apps/cliente/views_reset_senha.py
"""
Endpoints para reset de senha via OTP
Data: 27/10/2025
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from wallclub_core.oauth.decorators import require_oauth_apps
from wallclub_core.utilitarios.log_control import registrar_log
from apps.cliente.services_reset_senha import ResetSenhaService


@api_view(['POST'])
@permission_classes([AllowAny])
@require_oauth_apps
def solicitar_reset_senha(request):
    """
    Envia OTP para reset de senha
    
    Request:
        {
            "cpf": "17653377807",
            "canal_id": 1
        }
    
    Response (200):
        {
            "sucesso": true,
            "mensagem": "Código enviado via SMS para (21) 9****-4321"
        }
    
    Response - Cliente não cadastrado (400):
        {
            "sucesso": false,
            "mensagem": "CPF não encontrado. Complete seu cadastro primeiro."
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
        
        resultado = ResetSenhaService.solicitar_reset(cpf, canal_id)
        
        if resultado['sucesso']:
            return Response(resultado, status=status.HTTP_200_OK)
        else:
            return Response(resultado, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        registrar_log('apps.cliente', 
            f"Erro ao solicitar reset senha: {str(e)}", nivel='ERROR')
        
        return Response({
            'sucesso': False,
            'mensagem': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
@require_oauth_apps
def validar_reset_senha(request):
    """
    Valida OTP + permite criar nova senha
    
    Request:
        {
            "cpf": "17653377807",
            "codigo": "123456",
            "nova_senha": "NovaSenha@456"
        }
    
    Response - Sucesso (200):
        {
            "sucesso": true,
            "mensagem": "Senha alterada com sucesso! Faça login com a nova senha."
        }
    
    Response - OTP inválido (400):
        {
            "sucesso": false,
            "mensagem": "Código inválido ou expirado",
            "tentativas_restantes": 1
        }
    """
    try:
        cpf = request.data.get('cpf')
        codigo = request.data.get('codigo')
        nova_senha = request.data.get('nova_senha')
        
        if not cpf or not codigo or not nova_senha:
            return Response({
                'sucesso': False,
                'mensagem': 'CPF, código e nova senha são obrigatórios'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        resultado = ResetSenhaService.validar_reset(cpf, codigo, nova_senha)
        
        if resultado['sucesso']:
            return Response(resultado, status=status.HTTP_200_OK)
        else:
            return Response(resultado, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        registrar_log('apps.cliente', 
            f"Erro ao validar reset senha: {str(e)}", nivel='ERROR')
        
        return Response({
            'sucesso': False,
            'mensagem': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
