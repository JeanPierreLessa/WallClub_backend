"""
Views para o sistema de checkout com proteções de segurança.
"""
# import logging - removido, usando registrar_log
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
# from django_ratelimit.decorators import ratelimit  # Temporariamente comentado para testes
from datetime import datetime

from .models import CheckoutToken, CheckoutSession, CheckoutAttempt
from checkout.models import CheckoutTransaction
from .serializers import (
    GerarTokenSerializer, ProcessarCheckoutSerializer, 
    ConfirmarCheckoutSerializer, StatusCheckoutSerializer
)
# from wallclub_core.integracoes.whatsapp_service import WhatsAppService  # Removido para teste direto
from wallclub_core.utilitarios.log_control import registrar_log
from .decorators import log_checkout_access, require_oauth_checkout


def get_client_ip(request):
    """Obtém IP real do cliente"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_attempt(token, request, success, error_message=None):
    """Log de tentativas para auditoria"""
    CheckoutAttempt.objects.create(
        token=token,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        success=success,
        error_message=error_message
    )


class GerarTokenView(APIView):
    """
    Gera token de checkout para um item específico.
    Requer API Key válida no header X-API-Key.
    """
    permission_classes = [AllowAny]
    
    @method_decorator(require_oauth_checkout)
    # @method_decorator(ratelimit(key='ip', rate='10/m', method='POST'))  # Temporariamente comentado
    def post(self, request):
        """Gera um token seguro para checkout"""
        try:
            serializer = GerarTokenSerializer(data=request.data)
            if not serializer.is_valid():
                registrar_log("checkout.link_pagamento_web", f"Dados inválidos: {serializer.errors}")
                return Response({
                    'sucesso': False,
                    'mensagem': 'Dados inválidos',
                    'erros': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validar loja_id com OAuth client (se restrito por loja)
            oauth_client = request.oauth_client  # Adicionado pelo decorator OAuth
            loja_id = serializer.validated_data['loja_id']
            
            # Se OAuth client tem loja_id definida, validar se loja está autorizada
            if oauth_client.nivel_acesso == 'LOJA':
                if oauth_client.loja_id != loja_id:
                    registrar_log("checkout.link_pagamento_web", 
                                 f"Loja {loja_id} não permitida para OAuth client {oauth_client.name} (Loja autorizada: {oauth_client.loja_id})")
                    return Response({
                        'sucesso': False,
                        'mensagem': f'Este token OAuth não tem permissão para a loja {loja_id}'
                    }, status=status.HTTP_403_FORBIDDEN)
            
            # Se OAuth client é de grupo econômico, validar se loja pertence ao grupo
            if oauth_client.nivel_acesso == 'GRUPO':
                from wallclub_core.estr_organizacional.loja import Loja
                loja = Loja.get_loja(loja_id)
                if not loja or loja.GrupoEconomicoId != oauth_client.grupo_economico_id:
                    registrar_log("checkout.link_pagamento_web", 
                                 f"Loja {loja_id} não pertence ao grupo econômico {oauth_client.grupo_economico_id}")
                    return Response({
                        'sucesso': False,
                        'mensagem': f'Esta loja não pertence ao grupo econômico autorizado'
                    }, status=status.HTTP_403_FORBIDDEN)
            
            # Gerar token
            token_obj = CheckoutToken.generate_token(
                loja_id=serializer.validated_data['loja_id'],
                item_nome=serializer.validated_data['item_nome'],
                item_valor=serializer.validated_data['item_valor'],
                nome_completo=serializer.validated_data['nome_completo'],
                cpf=serializer.validated_data['cpf'],
                celular=serializer.validated_data['celular'],
                endereco_completo=serializer.validated_data['endereco_completo'],
                pedido_origem_loja=serializer.validated_data.get('pedido_origem_loja'),
                created_by=oauth_client.name  # Usar nome do OAuth Client
            )
            
            registrar_log("checkout.link_pagamento_web", f"Token gerado: {token_obj.token[:8]}... para {token_obj.item_nome}")
            
            return Response({
                'sucesso': True,
                'token': token_obj.token,
                'expires_at': token_obj.expires_at,
                'checkout_url': f'/api/v1/checkout/?token={token_obj.token}'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            registrar_log("checkout.link_pagamento_web", f"Erro: {str(e)}", nivel='ERROR')
            return Response({
                'sucesso': False,
                'mensagem': 'Erro interno do servidor'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(never_cache, name='dispatch')
@method_decorator(csrf_exempt, name='dispatch')
class CheckoutPageView(View):
    """Página HTML do checkout"""
    
    def get(self, request):
        """Exibe página de checkout via GET (links de email)"""
        token = request.GET.get('token')
        
        if not token:
            log_attempt('', request, False, 'Token não fornecido')
            return JsonResponse({
                'error': 'Token não fornecido'
            }, status=400)
        
        try:
            token_obj = get_object_or_404(CheckoutToken, token=token)
            
            if not token_obj.is_valid():
                log_attempt(token, request, False, 'Token inválido ou expirado')
                return JsonResponse({
                    'error': 'Link expirado ou já utilizado'
                }, status=400)
            
            log_attempt(token, request, True)
            registrar_log("checkout.link_pagamento_web", f"Página acessada para token {token[:8]}...")
            
            # Buscar nome da loja
            from wallclub_core.estr_organizacional.loja import Loja
            loja = Loja.get_loja(token_obj.loja_id)
            loja_nome = loja.razao_social if loja else 'Loja'
            
            # Buscar telefone ativo (ativo=1) do cliente
            from checkout.link_pagamento_web.models_2fa import CheckoutClienteTelefone
            cpf_limpo = ''.join(filter(str.isdigit, token_obj.cpf))
            
            telefone_ativo = None
            pode_alterar_telefone = True
            
            try:
                telefone_obj = CheckoutClienteTelefone.objects.get(
                    cpf=cpf_limpo,
                    ativo=1  # Apenas ativos confirmados
                )
                telefone_ativo = telefone_obj.telefone
                pode_alterar_telefone = telefone_obj.pode_alterar_telefone()
            except CheckoutClienteTelefone.DoesNotExist:
                # Cliente não tem telefone ativo ainda
                pass
            
            # Celular editável se:
            # 1. Não existe telefone ativo (primeira vez)
            # 2. Existe telefone mas pode alterar (antes da primeira transação)
            celular_editavel = telefone_ativo is None or pode_alterar_telefone
            
            # Obfuscar telefone para exibição: (21)****0901
            telefone_obfuscado = ''
            if telefone_ativo:
                tel_limpo = telefone_ativo.replace('(', '').replace(')', '').replace('-', '').replace(' ', '')
                if len(tel_limpo) == 11:  # (DD)9xxxx-xxxx
                    telefone_obfuscado = f"({tel_limpo[:2]})****{tel_limpo[-4:]}"
                elif len(tel_limpo) == 10:  # (DD)xxxx-xxxx
                    telefone_obfuscado = f"({tel_limpo[:2]})****{tel_limpo[-4:]}"
                else:
                    telefone_obfuscado = "****" + tel_limpo[-4:] if len(tel_limpo) >= 4 else tel_limpo
            
            return render(request, 'checkout/checkout.html', {
                'token': token,
                'loja_id': token_obj.loja_id,
                'loja_nome': loja_nome,
                'item_nome': token_obj.item_nome,
                'item_valor': token_obj.item_valor,
                'nome_completo': token_obj.nome_completo,
                'cpf': token_obj.cpf,
                'celular': token_obj.celular or '',
                'celular_editavel': celular_editavel,
                'telefone_ativo': telefone_ativo,
                'telefone_obfuscado': telefone_obfuscado,
                'pode_alterar_telefone': pode_alterar_telefone,
                'endereco_completo': token_obj.endereco_completo,
                'pedido_origem_loja': token_obj.pedido_origem_loja,
                'expires_at': token_obj.expires_at
            })
            
        except Exception as e:
            log_attempt(token, request, False, str(e))
            return JsonResponse({
                'error': 'Erro interno'
            }, status=500)
    
    # @method_decorator(ratelimit(key='ip', rate='30/m', method='POST'))  # Temporariamente comentado
    def post(self, request):
        """Exibe página de checkout via POST (legado)"""
        token = request.POST.get('token')
        
        if not token:
            log_attempt('', request, False, 'Token não fornecido')
            return JsonResponse({
                'error': 'Token não fornecido'
            }, status=400)
        
        try:
            token_obj = get_object_or_404(CheckoutToken, token=token)
            
            if not token_obj.is_valid():
                log_attempt(token, request, False, 'Token inválido ou expirado')
                return JsonResponse({
                    'error': 'Link expirado ou já utilizado'
                }, status=400)
            
            log_attempt(token, request, True)
            registrar_log("checkout.link_pagamento_web", f"Página acessada para token {token[:8]}...")
            
            # Buscar nome da loja
            from wallclub_core.estr_organizacional.loja import Loja
            loja = Loja.get_loja(token_obj.loja_id)
            loja_nome = loja.razao_social if loja else 'Loja'
            
            # Buscar telefone ativo (ativo=1) do cliente
            from checkout.link_pagamento_web.models_2fa import CheckoutClienteTelefone
            cpf_limpo = ''.join(filter(str.isdigit, token_obj.cpf))
            
            telefone_ativo = None
            pode_alterar_telefone = True
            
            try:
                telefone_obj = CheckoutClienteTelefone.objects.get(
                    cpf=cpf_limpo,
                    ativo=1  # Apenas ativos confirmados
                )
                telefone_ativo = telefone_obj.telefone
                pode_alterar_telefone = telefone_obj.pode_alterar_telefone()
            except CheckoutClienteTelefone.DoesNotExist:
                # Cliente não tem telefone ativo ainda
                pass
            
            # Celular editável se:
            # 1. Não existe telefone ativo (primeira vez)
            # 2. Existe telefone mas pode alterar (antes da primeira transação)
            celular_editavel = telefone_ativo is None or pode_alterar_telefone
            
            # Obfuscar telefone para exibição: (21)****0901
            telefone_obfuscado = ''
            if telefone_ativo:
                tel_limpo = telefone_ativo.replace('(', '').replace(')', '').replace('-', '').replace(' ', '')
                if len(tel_limpo) == 11:  # (DD)9xxxx-xxxx
                    telefone_obfuscado = f"({tel_limpo[:2]})****{tel_limpo[-4:]}"
                elif len(tel_limpo) == 10:  # (DD)xxxx-xxxx
                    telefone_obfuscado = f"({tel_limpo[:2]})****{tel_limpo[-4:]}"
                else:
                    telefone_obfuscado = "****" + tel_limpo[-4:] if len(tel_limpo) >= 4 else tel_limpo
            
            return render(request, 'checkout/checkout.html', {
                'token': token,
                'loja_id': token_obj.loja_id,
                'loja_nome': loja_nome,
                'item_nome': token_obj.item_nome,
                'item_valor': token_obj.item_valor,
                'nome_completo': token_obj.nome_completo,
                'cpf': token_obj.cpf,
                'celular': token_obj.celular or '',
                'celular_editavel': celular_editavel,
                'telefone_ativo': telefone_ativo,
                'telefone_obfuscado': telefone_obfuscado,
                'pode_alterar_telefone': pode_alterar_telefone,
                'endereco_completo': token_obj.endereco_completo,
                'pedido_origem_loja': token_obj.pedido_origem_loja,
                'expires_at': token_obj.expires_at
            })
            
        except Exception as e:
            # Log via log_attempt abaixo
            log_attempt(token, request, False, str(e))
            return JsonResponse({
                'error': 'Erro interno'
            }, status=500)


class ProcessarCheckoutView(APIView):
    """API para processar dados do checkout"""
    permission_classes = [AllowAny]
    
    # @method_decorator(ratelimit(key='ip', rate='5/m', method='POST'))  # Temporariamente comentado
    def post(self, request):
        """Processa pagamento via link de checkout - delega para CheckoutService"""
        try:
            # Validar entrada
            serializer = ProcessarCheckoutSerializer(data=request.data)
            if not serializer.is_valid():
                registrar_log("checkout.link_pagamento_web", f"Dados inválidos: {serializer.errors}")
                return Response({
                    'sucesso': False,
                    'mensagem': 'Dados inválidos',
                    'erros': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Preparar dados para o service
            from checkout.link_pagamento_web.services import LinkPagamentoService
            
            dados_cartao = {
                'numero_cartao': serializer.validated_data['numero_cartao'],
                'cvv': serializer.validated_data['cvv'],
                'data_validade': serializer.validated_data['data_validade'],
                'bandeira': serializer.validated_data['bandeira']
            }
            
            dados_sessao = {
                'cpf': serializer.validated_data['cpf'],
                'nome': serializer.validated_data['nome'],
                'celular': serializer.validated_data['celular'],
                'endereco': serializer.validated_data['endereco'],
                'parcelas': serializer.validated_data['parcelas'],
                'tipo_pagamento': serializer.validated_data['tipo_pagamento'],
                'valor_total': serializer.validated_data['valor_total'],
                'salvar_cartao': serializer.validated_data.get('salvar_cartao', False)
            }
            
            # Processar via service
            resultado = LinkPagamentoService.processar_checkout_link_pagamento(
                token=serializer.validated_data['token'],
                dados_cartao=dados_cartao,
                dados_sessao=dados_sessao,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            # Registrar tentativa
            log_attempt(
                serializer.validated_data['token'],
                request,
                resultado.get('sucesso', False),
                resultado.get('mensagem') if not resultado.get('sucesso') else None
            )
            
            # Retornar resultado
            if resultado.get('sucesso'):
                return Response(resultado, status=status.HTTP_200_OK)
            else:
                return Response(resultado, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            registrar_log("checkout.link_pagamento_web", f"Erro: {str(e)}", nivel='ERROR')
            return Response({
                'sucesso': False,
                'mensagem': 'Erro interno do servidor'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ConfirmarCheckoutView removida - processamento direto no ProcessarCheckoutView


class SimularParcelasView(APIView):
    """API para simular parcelas usando CalculadoraDesconto"""
    permission_classes = [AllowAny]  # Público - chamado pelo browser do cliente no checkout
    
    def post(self, request):
        """Simula valores de parcelas para todas as bandeiras de cartão"""
        try:
            valor = request.data.get('valor')
            loja_id = request.data.get('loja_id')
            
            if not valor or not loja_id:
                return Response({
                    'sucesso': False,
                    'mensagem': 'Valor e loja_id são obrigatórios'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Converter valor para Decimal
            try:
                from decimal import Decimal, ROUND_HALF_UP
                valor = Decimal(str(valor)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            except (ValueError, TypeError):
                return Response({
                    'sucesso': False,
                    'mensagem': 'Valor inválido'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Importar CalculadoraDesconto
            from parametros_wallclub.services import CalculadoraDesconto
            from datetime import datetime
            
            calculadora = CalculadoraDesconto()
            
            # Obter data atual no formato YYYY-MM-DD
            data_atual = datetime.now().strftime('%Y-%m-%d')
            
            # Usar loja_id diretamente do request
            id_loja = loja_id
            
            # Wall = 'S' para checkout (assumindo que checkout usa Wall)
            wall = 'S'
            
            # Definir parcelas a simular: TODAS de 1 a 12
            opcoes_parcelas = list(range(1, 13))  # [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
            
            # Bandeiras de cartão aceitas
            bandeiras = [
                {'nome': 'MASTERCARD'},
                {'nome': 'VISA'},
                {'nome': 'ELO'},
            ]
            
            # Resultados por bandeira
            resultados_bandeiras = {}
            
            for bandeira_info in bandeiras:
                bandeira = bandeira_info['nome']
                
                opcoes = []
                
                for num_parcelas in opcoes_parcelas:
                    # Usar mesma lógica do Portal de Vendas
                    if num_parcelas == 1:
                        forma = 'A VISTA'
                    else:
                        forma = 'PARCELADO SEM JUROS'
                    
                    # Calcular valor com desconto usando CalculadoraDesconto
                    valor_calculado = calculadora.calcular_desconto(
                        valor_original=valor,
                        data=data_atual,
                        forma=forma,
                        parcelas=num_parcelas,
                        id_loja=id_loja,
                        wall=wall
                    )
                    
                    # FILTRO: Se calculadora retornar None, PULAR esta parcela
                    if valor_calculado is None:
                        continue
                    
                    # Calcular valor da parcela
                    valor_parcela = valor_calculado / num_parcelas
                    
                    # Determinar descrição baseada na comparação com valor original (mesma lógica do Portal)
                    if valor_calculado > valor:
                        info_extra = " (c/encargos)"
                    elif valor_calculado < valor:
                        info_extra = " (c/desconto)"
                    else:
                        info_extra = " (s/juros)"
                    
                    # Formato: 3x de R$ 30,00 (s/juros) - Valor Total: R$ 90,00 (cashback R$ XX,XX)
                    texto = f"{num_parcelas}x de R$ {valor_parcela:.2f}{info_extra} - Valor Total: R$ {valor_calculado:.2f}"
                    
                    # Cashback sempre 0 por enquanto (não implementado)
                    cashback = 0
                    if cashback > 0:
                        texto += f" (cashback R$ {cashback:.2f})"
                    
                    opcoes.append({
                        'parcelas': num_parcelas,
                        'valor_total': round(valor_calculado, 2),
                        'valor_parcela': round(valor_parcela, 2),
                        'cashback': cashback,
                        'texto': texto
                    })
                
                # Só adicionar bandeira se tiver pelo menos 1 opção válida
                if opcoes:
                    resultados_bandeiras[bandeira] = opcoes
            
            # Por padrão, retornar a primeira bandeira disponível
            opcoes_padrao = []
            if resultados_bandeiras:
                primeira_bandeira = list(resultados_bandeiras.keys())[0]
                opcoes_padrao = resultados_bandeiras[primeira_bandeira]
            
            registrar_log("checkout.link_pagamento_web", 
                         f"Simulação concluída - Valor: {valor}, Loja: {id_loja}")
            
            return Response({
                'sucesso': True,
                'opcoes': opcoes_padrao,  # Retorna MASTERCARD por padrão
                'todas_bandeiras': resultados_bandeiras  # Retorna todas para escolha futura
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            registrar_log("checkout.link_pagamento_web", f"Erro: {str(e)}", nivel='ERROR')
            return Response({
                'sucesso': False,
                'mensagem': 'Erro ao simular parcelas'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StatusCheckoutView(APIView):
    """API para consultar status do checkout"""
    permission_classes = [AllowAny]
    
    @method_decorator(require_oauth_checkout)
    # @method_decorator(ratelimit(key='ip', rate='20/m', method='GET'))  # Temporariamente comentado
    def get(self, request, token):
        """Consulta status do token"""
        try:
            token_obj = get_object_or_404(CheckoutToken, token=token)
            serializer = StatusCheckoutSerializer(token_obj)
            
            return Response({
                'sucesso': True,
                'dados': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            # Log removido - erro genérico
            return Response({
                'sucesso': False,
                'mensagem': 'Erro interno do servidor'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(never_cache, name='dispatch')
@method_decorator(csrf_exempt, name='dispatch')
class SimuladorDermaDreamView(View):
    """Página do simulador do sistema DermaDream"""
    
    def get(self, request):
        """Exibe página do simulador"""
        return render(request, 'checkout/simula_sistema_dermadream.html')
