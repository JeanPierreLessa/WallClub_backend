"""
Views para gerenciamento de senhas de clientes.
Endpoints: criar senha definitiva, trocar senha, recuperar senha.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from datetime import datetime

from .models import Cliente, ClienteAuth
from .services_senha import SenhaService
from wallclub_core.oauth.decorators import require_oauth_apps
from apps.conta_digital.decorators import require_jwt_only
from wallclub_core.utilitarios.log_control import registrar_log
from wallclub_core.seguranca.services_2fa import OTPService
from wallclub_core.seguranca.services_device import DeviceManagementService


@api_view(['POST'])
@require_jwt_only
def solicitar_troca_senha(request):
    """
    Solicita troca de senha: valida senha atual e envia código 2FA.
    
    Payload:
        {
            "senha_atual": "senha123"
        }
    
    Headers:
        - Authorization: Bearer <jwt_token> (JWT do cliente)
    
    Returns:
        {
            "sucesso": bool,
            "mensagem": str
        }
    """
    try:
        # Extrair cliente_id do JWT
        cliente_id = request.user.cliente_id
        
        # Buscar cliente no banco
        try:
            cliente = Cliente.objects.get(id=cliente_id, is_active=True)
        except Cliente.DoesNotExist:
            return Response({
                'sucesso': False,
                'mensagem': 'Cliente não encontrado'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Validar payload
        senha_atual = request.data.get('senha_atual')
        if not senha_atual:
            return Response({
                'sucesso': False,
                'mensagem': 'Senha atual é obrigatória'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validar senha atual
        if not cliente.check_password(senha_atual):
            registrar_log('apps.cliente',
                f"Tentativa de troca com senha incorreta: cliente_id={cliente_id}", nivel='WARNING')
            return Response({
                'sucesso': False,
                'mensagem': 'Senha atual incorreta'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Gerar código 2FA
        resultado_otp = OTPService.gerar_otp(
            user_id=cliente_id,
            tipo_usuario='cliente',
            telefone=cliente.celular,
            ip_solicitacao=request.META.get('REMOTE_ADDR')
        )
        
        if not resultado_otp['success']:
            return Response({
                'sucesso': False,
                'mensagem': resultado_otp['mensagem']
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Buscar código do banco para enviar via WhatsApp
        from wallclub_core.seguranca.models import AutenticacaoOTP
        otp_record = AutenticacaoOTP.objects.filter(
            id=resultado_otp['otp_id']
        ).first()
        
        if otp_record:
            # Enviar código via WhatsApp
            resultado_whats = OTPService.enviar_otp_whatsapp(
                canal_id=cliente.canal_id,
                telefone=cliente.celular,
                codigo=otp_record.codigo,
                nome=cliente.nome
            )
            
            if not resultado_whats['success']:
                registrar_log('apps.cliente',
                    f"Erro ao enviar WhatsApp para troca de senha: cliente_id={cliente_id} - {resultado_whats['mensagem']}", nivel='WARNING')
        else:
            registrar_log('apps.cliente',
                f"OTP não encontrado no banco: otp_id={resultado_otp.get('otp_id')}", nivel='ERROR')
        
        registrar_log('apps.cliente',
            f"Código 2FA gerado para troca de senha: cliente_id={cliente_id}",
            nivel='INFO')
        return Response({
            'sucesso': True,
            'mensagem': 'Código de confirmação enviado via WhatsApp'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        registrar_log('apps.cliente',
            f"Erro ao solicitar troca de senha: {str(e)}", nivel='ERROR')
        return Response({
            'sucesso': False,
            'mensagem': 'Erro ao processar solicitação'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@require_jwt_only
def trocar_senha(request):
    """
    Endpoint para trocar senha do cliente.
    
    Payload:
        {
            "senha_atual": "senha123",
            "nova_senha": "novaSenha456"
        }
    
    Headers:
        - Authorization: Bearer <jwt_token> (JWT do cliente)
    
    Returns:
        {
            "sucesso": bool,
            "mensagem": str
        }
    """
    try:
        # Extrair cliente_id do JWT
        cliente_id = request.user.cliente_id
        
        # Buscar cliente no banco
        try:
            cliente = Cliente.objects.get(id=cliente_id, is_active=True)
        except Cliente.DoesNotExist:
            return Response({
                'sucesso': False,
                'mensagem': 'Cliente não encontrado'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Validar payload
        senha_atual = request.data.get('senha_atual')
        nova_senha = request.data.get('nova_senha')
        codigo = request.data.get('codigo')
        
        if not senha_atual or not nova_senha or not codigo:
            return Response({
                'sucesso': False,
                'mensagem': 'Senha atual, nova senha e código são obrigatórios'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validar código 2FA primeiro
        validacao_2fa = OTPService.validar_otp(
            user_id=cliente_id,
            tipo_usuario='cliente',
            codigo=codigo
        )
        
        if not validacao_2fa['success']:
            return Response({
                'sucesso': False,
                'mensagem': validacao_2fa['mensagem']
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Trocar senha via service
        resultado = SenhaService.trocar_senha(cliente, senha_atual, nova_senha)
        
        if resultado['sucesso']:
            registrar_log('apps.cliente',
                f"Senha trocada com sucesso: cliente_id={cliente.id}",
                nivel='INFO')
            
            # Notificar troca de senha
            try:
                from wallclub_core.integracoes.notificacao_seguranca_service import NotificacaoSegurancaService
                NotificacaoSegurancaService.notificar_troca_senha(
                    cliente_id=cliente.id,
                    canal_id=cliente.canal_id,
                    celular=cliente.celular,
                    nome=cliente.nome
                )
            except Exception as e:
                registrar_log('apps.cliente',
                    f"Erro ao notificar troca de senha: {str(e)}", nivel='WARNING')
            
            return Response({
                'sucesso': True,
                'mensagem': resultado['mensagem']
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'sucesso': False,
                'mensagem': resultado['mensagem']
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        registrar_log('apps.cliente',
            f"Erro ao trocar senha: {str(e)}", nivel='ERROR')
        return Response({
            'sucesso': False,
            'mensagem': 'Erro ao processar solicitação'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


