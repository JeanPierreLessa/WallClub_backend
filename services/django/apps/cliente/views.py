"""
Views para autenticação de clientes (usuários do APP móvel).
Responsável apenas pela orquestração dos endpoints.
A lógica de negócio fica no services.py

USA SISTEMA CENTRALIZADO:
- API Key obrigatória em todos os endpoints
- Login retorna JWT Token
- Cadastro e reset-senha apenas validam API Key
"""
from django.shortcuts import render
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.utils.decorators import method_decorator
import json

from .serializers import (
    ClienteLoginSerializer, ClienteCadastroSerializer
)
from .services import ClienteAuthService
from .services_notificacoes import NotificacaoService
from wallclub_core.integracoes.notificacao_seguranca_service import NotificacaoSegurancaService
from wallclub_core.oauth.decorators import require_oauth_apps
from apps.conta_digital.decorators import require_jwt_only
from wallclub_core.utilitarios.log_control import registrar_log


def get_client_ip(request):
    """Obtém o IP real do cliente considerando proxies"""
    # Tentar múltiplos headers usados por proxies
    headers_to_check = [
        'HTTP_X_REAL_IP',           # Nginx
        'HTTP_X_FORWARDED_FOR',     # Padrão proxy
        'HTTP_CF_CONNECTING_IP',    # Cloudflare
        'HTTP_X_CLUSTER_CLIENT_IP', # Load balancers
    ]
    
    for header in headers_to_check:
        ip = request.META.get(header)
        if ip:
            # X-Forwarded-For pode ter múltiplos IPs separados por vírgula
            ip = ip.split(',')[0].strip()
            registrar_log('apps.cliente', f"IP capturado via {header}: {ip}", nivel='DEBUG')
            return ip
    
    # Fallback: REMOTE_ADDR (IP direto da conexão)
    ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
    registrar_log('apps.cliente', f"IP capturado via REMOTE_ADDR: {ip}", nivel='DEBUG')
    return ip


# === ENDPOINTS PARA CLIENTES ===


@api_view(['POST'])
@permission_classes([AllowAny])
@require_oauth_apps
def cliente_login(request):
    """
    Endpoint para login de clientes
    Aceita JSON: CPF, SENHA (obrigatória), canal_id
    Retorna formato padronizado: {sucesso: bool, mensagem: string, auth_token: string}

    REQUER OAUTH TOKEN no header Authorization: Bearer
    RETORNA auth_token temporário (5min) - JWT final via 2FA
    """
    serializer = ClienteLoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({
            'sucesso': False,
            'mensagem': 'Dados inválidos'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Extrair dados validados do serializer
        cpf_limpo = serializer.validated_data['cpf']
        canal_id = serializer.validated_data['canal_id']
        senha = serializer.validated_data.get('senha')  # NOVO: senha obrigatória
        firebase_token = serializer.validated_data.get('firebase_token')

        # Login via service (COM SENHA + 2FA obrigatório)
        resultado = ClienteAuthService.login(
            cpf=cpf_limpo,
            canal_id=canal_id,
            senha=senha,  # NOVO: validar senha antes de gerar auth_token
            firebase_token=firebase_token,
            ip_address=get_client_ip(request),
            request=request
        )

        if resultado['sucesso']:
            # Retornar resposta padronizada completa
            return Response(resultado, status=status.HTTP_200_OK)
        else:
            # Retornar dicionário completo do service (inclui erro, bloqueio, tentativas, etc)
            return Response(resultado, status=status.HTTP_200_OK)

    except Exception as e:
        registrar_log('apps.cliente', f"Erro no endpoint login: {str(e)}", nivel='ERROR')
        return Response({
            'sucesso': False,
            'mensagem': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
@require_oauth_apps
def cliente_cadastro(request):
    """
    Endpoint para cadastro de clientes
    Usa BureauService para validar CPF e WhatsAppService para enviar senha

    REQUER API KEY no header X-API-Key
    NÃO retorna JWT Token (cliente deve fazer login após cadastro)
    """
    try:
        serializer = ClienteCadastroSerializer(data=request.data)
        if serializer.is_valid():
            # Extrair dados validados
            dados = serializer.validated_data

            # Chamada para o serviço de cadastro - canal_id direto
            email = dados.get('email')

            resultado = ClienteAuthService.cadastrar(
                cpf=dados['cpf'],
                celular=dados['celular'],
                canal_id=dados['canal_id'],  # Canal ID direto, sem conversão
                email=email  # Campo email opcional sem valor default
            )

            if resultado['sucesso']:
                return Response(resultado, status=status.HTTP_201_CREATED)
            else:
                return Response(resultado, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        import traceback
        registrar_log('apps.cliente', f"Erro no endpoint cadastro: {str(e)}", nivel='ERROR')
        return Response({
            'sucesso': False,
            'codigo': 0,
            'mensagem': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@require_jwt_only
def perfil_cliente(request):
    """
    Endpoint para consultar perfil do cliente (nome e celular)

    REQUER JWT TOKEN no header Authorization: Bearer <token>
    """

    try:
        # Extrair cliente_id do JWT customizado
        cliente_id = request.user.cliente_id

        # Obter perfil do cliente
        resultado = ClienteAuthService.obter_perfil_cliente(cliente_id)

        if resultado['sucesso']:
            return Response(resultado, status=status.HTTP_200_OK)
        else:
            return Response(resultado, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        registrar_log('apps.cliente', f"Erro no endpoint perfil_cliente: {str(e)}", nivel='ERROR')
        return Response({
            'sucesso': False,
            'mensagem': 'Erro interno do servidor',
            'dados': None
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@require_jwt_only
def atualiza_celular(request):
    """
    Endpoint para atualizar celular do cliente

    REQUER JWT TOKEN no header Authorization: Bearer <token>

    Body (JSON):
    {
        "novo_celular": "21999730901"
    }
    """
    try:
        # Extrair cliente_id do token JWT (mesmo padrão dos outros endpoints)
        cliente_id = request.user.cliente_id

        # Validar dados do body
        novo_celular = request.data.get('novo_celular')
        if not novo_celular:
            return Response({
                'sucesso': False,
                'mensagem': 'Campo novo_celular é obrigatório'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Buscar celular antigo ANTES de atualizar
        from apps.cliente.models import Cliente
        cliente = Cliente.objects.only('celular', 'canal_id').get(id=cliente_id)
        celular_antigo = cliente.celular

        # Atualizar celular via service
        resultado = ClienteAuthService.atualizar_celular_cliente(cliente_id, novo_celular)

        if resultado['sucesso']:
            # Notificar alteração de celular (WhatsApp vai para número ANTIGO)
            try:
                NotificacaoSegurancaService.notificar_alteracao_dados(
                    cliente_id=cliente_id,
                    canal_id=cliente.canal_id,
                    celular=novo_celular,  # Celular novo (para enviar push)
                    campo_alterado='celular',
                    nome=cliente.nome if hasattr(cliente, 'nome') else '',
                    celular_antigo=celular_antigo  # WhatsApp vai para antigo
                )
            except Exception as e:
                registrar_log('apps.cliente', f"Erro ao notificar alteração celular: {str(e)}", nivel='ERROR')
            
            return Response(resultado, status=status.HTTP_200_OK)
        else:
            return Response(resultado, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        registrar_log('apps.cliente', f"Erro no endpoint atualiza_celular: {str(e)}", nivel='ERROR')
        return Response({
            'sucesso': False,
            'mensagem': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@require_jwt_only
def atualiza_email(request):
    """
    Endpoint para atualizar email do cliente

    REQUER JWT TOKEN no header Authorization: Bearer <token>

    Body (JSON):
    {
        "novo_email": "cliente@exemplo.com"
    }
    """
    try:
        # Extrair cliente_id do token JWT (mesmo padrão dos outros endpoints)
        cliente_id = request.user.cliente_id

        # Validar dados do body
        novo_email = request.data.get('novo_email')
        if not novo_email:
            return Response({
                'sucesso': False,
                'mensagem': 'Campo novo_email é obrigatório'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Atualizar email via service
        resultado = ClienteAuthService.atualizar_email_cliente(cliente_id, novo_email)

        if resultado['sucesso']:
            # Notificar alteração de email
            try:
                from apps.cliente.models import Cliente
                cliente = Cliente.objects.only('canal_id', 'celular', 'nome').get(id=cliente_id)
                NotificacaoSegurancaService.notificar_alteracao_dados(
                    cliente_id=cliente_id,
                    canal_id=cliente.canal_id,
                    celular=cliente.celular,
                    campo_alterado='email',
                    nome=cliente.nome
                )
            except Exception as e:
                registrar_log('apps.cliente', f"Erro ao notificar alteração email: {str(e)}", nivel='ERROR')
            
            return Response(resultado, status=status.HTTP_200_OK)
        else:
            return Response(resultado, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        registrar_log('apps.cliente', f"Erro no endpoint atualiza_email: {str(e)}", nivel='ERROR')
        return Response({
            'sucesso': False,
            'mensagem': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@require_jwt_only
def grava_firebase_token(request):
    """
    Endpoint para gravar token Firebase do cliente para notificações push

    REQUER JWT TOKEN no header Authorization: Bearer <token>

    Body (JSON):
    {
        "firebase_token": "token_firebase_aqui"
    }
    """
    try:
        # Extrair cliente_id do token JWT (mesmo padrão dos outros endpoints)
        cliente_id = request.user.cliente_id

        # Validar dados do body
        firebase_token = request.data.get('firebase_token')
        if not firebase_token:
            return Response({
                'sucesso': False,
                'mensagem': 'Campo firebase_token é obrigatório'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Gravar token Firebase via service
        resultado = ClienteAuthService.gravar_firebase_token(cliente_id, firebase_token)

        if resultado['sucesso']:
            return Response(resultado, status=status.HTTP_200_OK)
        else:
            return Response(resultado, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        registrar_log('apps.cliente', f"Erro no endpoint grava_firebase_token: {str(e)}", nivel='ERROR')
        return Response({
            'sucesso': False,
            'mensagem': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@require_jwt_only
def notificacoes(request):
    """
    Endpoint para consultar notificações do cliente

    Headers obrigatórios:
    - Authorization: Bearer <jwt_token>

    Retorna lista das últimas 30 notificações do cliente
    """
    try:
        # Extrair cliente_id do token JWT
        cliente_id = request.user.cliente_id

        # Processar via service
        resultado = NotificacaoService.listar_notificacoes(
            cliente_id=cliente_id,
            limite=30
        )

        # Retornar resposta
        if resultado['sucesso']:
            return Response(resultado, status=status.HTTP_200_OK)
        else:
            return Response(resultado, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        registrar_log('apps.cliente', f"Erro no endpoint notificacoes: {str(e)}", nivel='ERROR')
        return Response({
            "sucesso": False,
            "mensagem": "Erro interno do servidor",
            "dados": {
                "notificacoes": [],
                "quantidade": 0,
                "quantidade_nao_lidas": 0
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@require_jwt_only
def notificacoes_ler(request):
    """
    Endpoint para marcar notificações como lidas

    Headers obrigatórios:
    - Authorization: Bearer <jwt_token>

    Body (JSON):
    {
        "notificacao_ids": [1, 2, 3]  // Array de IDs ou ID único (int)
    }

    Retorna:
    {
        "sucesso": true,
        "mensagem": "X notificações marcadas como lidas",
        "dados": {
            "quantidade_atualizada": 3
        }
    }
    """
    try:
        # Extrair cliente_id do token JWT
        cliente_id = request.user.cliente_id

        # Validar parâmetro obrigatório
        notificacao_ids = request.data.get('notificacao_ids')
        if not notificacao_ids:
            return Response({
                'sucesso': False,
                'mensagem': 'Campo notificacao_ids é obrigatório'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Processar via service
        resultado = NotificacaoService.marcar_notificacoes_como_lidas(
            cliente_id=cliente_id,
            notificacao_ids=notificacao_ids
        )

        # Retornar resposta
        if resultado['sucesso']:
            return Response({
                'sucesso': True,
                'mensagem': resultado['mensagem'],
                'dados': {
                    'quantidade_atualizada': resultado['quantidade_atualizada']
                }
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'sucesso': False,
                'mensagem': resultado['mensagem']
            }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        registrar_log('apps.cliente', f"Erro no endpoint notificacoes_ler: {str(e)}", nivel='ERROR')
        return Response({
            'sucesso': False,
            'mensagem': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@require_jwt_only
def excluir_conta(request):
    """
    Endpoint para exclusão de conta do cliente (soft delete)
    
    Headers obrigatórios:
    - Authorization: Bearer <jwt_token>
    
    Ações realizadas:
    - Desativa a conta (is_active = False)
    - Revoga todos os tokens JWT ativos
    - Cliente não poderá mais fazer login
    
    Retorna:
    {
        "sucesso": true,
        "mensagem": "Cliente excluído com sucesso",
        "dados": {
            "cliente_id": 123,
            "tokens_revogados": 2
        }
    }
    """
    try:
        # Extrair cliente_id do token JWT
        cliente_id = request.user.cliente_id
        
        registrar_log('apps.cliente', 
            f"Solicitação de exclusão de conta - Cliente ID: {cliente_id}", 
            nivel='INFO')
        
        # Processar exclusão via service
        resultado = ClienteAuthService.excluir_cliente(cliente_id)
        
        if resultado['sucesso']:
            return Response(resultado, status=status.HTTP_200_OK)
        else:
            return Response(resultado, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        registrar_log('apps.cliente', 
            f"Erro no endpoint excluir_conta: {str(e)}", 
            nivel='ERROR')
        return Response({
            'sucesso': False,
            'mensagem': 'Erro interno do servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


