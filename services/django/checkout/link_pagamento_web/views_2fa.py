"""
Views para 2FA no Checkout Web
Novas APIs para fluxo com segurança reforçada
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from decimal import Decimal
from django.core.cache import cache
from wallclub_core.utilitarios.log_control import registrar_log
from .services_2fa import CheckoutSecurityService
from .models import CheckoutToken


def get_client_ip(request):
    """Obtém IP real do cliente"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def extract_device_fingerprint(request):
    """Extrai device fingerprint do request"""
    return request.META.get('HTTP_X_DEVICE_FINGERPRINT', '')


def validate_origin(request):
    """Valida origem da requisição (CORS manual)"""
    origin = request.META.get('HTTP_ORIGIN', '')
    referer = request.META.get('HTTP_REFERER', '')
    
    # Domínios permitidos
    allowed_domains = [
        'wallclub.com.br',
        'apidj.wallclub.com.br',
        'localhost',  # Desenvolvimento
        '127.0.0.1',  # Desenvolvimento
    ]
    
    # Verificar origin ou referer
    request_source = origin or referer
    
    # Log para debug
    registrar_log('checkout.2fa', 
                 f"CORS Debug - Origin: {origin} | Referer: {referer} | Source: {request_source}",
                 nivel='INFO')
    
    if not request_source:
        registrar_log('checkout.2fa', "CORS: Sem origin/referer - PERMITIDO", nivel='INFO')
        return True  # Permitir se não houver origin/referer (apps mobile)
    
    # Verificar se contém algum domínio permitido
    for domain in allowed_domains:
        if domain in request_source:
            registrar_log('checkout.2fa', 
                         f"CORS: Domínio {domain} encontrado em {request_source} - PERMITIDO",
                         nivel='INFO')
            return True
    
    registrar_log('checkout.2fa', 
                 f"CORS: Origem {request_source} NÃO PERMITIDA",
                 nivel='WARNING')
    return False


def check_otp_rate_limit(token: str) -> tuple:
    """Verifica rate limit de tentativas de OTP por token"""
    cache_key = f"otp_attempts:{token}"
    attempts = cache.get(cache_key, 0)
    
    MAX_ATTEMPTS = 3
    WINDOW_SECONDS = 300  # 5 minutos
    
    if attempts >= MAX_ATTEMPTS:
        return False, f"Máximo de {MAX_ATTEMPTS} tentativas excedido. Aguarde 5 minutos."
    
    # Incrementar contador
    cache.set(cache_key, attempts + 1, timeout=WINDOW_SECONDS)
    
    return True, None


class SolicitarOTPCheckoutView(APIView):
    """
    Solicita OTP para checkout após validações de segurança
    POST /api/checkout/solicitar-otp/
    """
    authentication_classes = []  # Desabilitar SessionAuthentication
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Executa validações de segurança e envia OTP
        
        Body:
        {
            "token": "abc123...",
            "cpf": "12345678901",
            "telefone": "11999999999",
            "valor": 150.00,
            "ultimos_4_digitos_cartao": "1234" (opcional - para mensagem WhatsApp)
        }
        """
        try:
            # Validar campos obrigatórios
            token = request.data.get('token')
            cpf = request.data.get('cpf')
            telefone = request.data.get('telefone')
            valor = request.data.get('valor')
            
            if not all([token, cpf, telefone, valor]):
                return Response({
                    'sucesso': False,
                    'mensagem': 'Campos obrigatórios: token, cpf, telefone, valor'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validar token
            try:
                token_obj = CheckoutToken.objects.get(token=token)
                if not token_obj.is_valid():
                    return Response({
                        'sucesso': False,
                        'mensagem': 'Token inválido ou expirado'
                    }, status=status.HTTP_400_BAD_REQUEST)
            except CheckoutToken.DoesNotExist:
                return Response({
                    'sucesso': False,
                    'mensagem': 'Token não encontrado'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Converter valor
            try:
                valor_decimal = Decimal(str(valor))
            except:
                return Response({
                    'sucesso': False,
                    'mensagem': 'Valor inválido'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Obter IP e device fingerprint
            ip_address = get_client_ip(request)
            device_fingerprint = extract_device_fingerprint(request)
            
            # Últimos 4 dígitos do cartão (opcional - para mensagem WhatsApp)
            ultimos_4_digitos = request.data.get('ultimos_4_digitos_cartao')
            
            # Executar validações de segurança e gerar OTP
            resultado = CheckoutSecurityService.processar_checkout_com_2fa(
                token=token,
                cpf=cpf,
                telefone=telefone,
                valor=valor_decimal,
                ip_address=ip_address,
                device_fingerprint=device_fingerprint,
                ultimos_4_digitos_cartao=ultimos_4_digitos
            )
            
            if not resultado['aprovado']:
                registrar_log(
                    'checkout.2fa',
                    f"Checkout bloqueado: {resultado['motivo_bloqueio']} - Token: {token[:8]}...",
                    nivel='WARNING'
                )
                return Response({
                    'sucesso': False,
                    'mensagem': resultado['motivo_bloqueio'],
                    'detalhes': resultado.get('detalhes', {})
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Sucesso - OTP enviado
            registrar_log(
                'checkout.2fa',
                f"OTP enviado com sucesso - Token: {token[:8]}..."
            )
            
            return Response({
                'sucesso': True,
                'mensagem': 'Código enviado via WhatsApp',
                'otp_validade': resultado.get('otp_validade'),
                'detalhes': resultado.get('detalhes', {})
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            registrar_log(
                'checkout.2fa',
                f"Erro ao solicitar OTP: {str(e)}",
                nivel='ERROR'
            )
            return Response({
                'sucesso': False,
                'mensagem': 'Erro interno do servidor'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ValidarOTPCheckoutView(APIView):
    """
    Valida OTP e processa pagamento
    POST /api/checkout/validar-otp/
    """
    authentication_classes = []  # Desabilitar SessionAuthentication
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Valida OTP e processa pagamento no Pinbank
        
        Body:
        {
            "token": "abc123...",
            "cpf": "12345678901",
            "telefone": "11999999999",
            "codigo_otp": "123456",
            "numero_cartao": "4111111111111111",
            "cvv": "123",
            "data_validade": "12/2025",
            "bandeira": "VISA",
            "parcelas": 1,
            "tipo_pagamento": "CREDIT_ONE_INSTALLMENT",
            "valor_total": 150.00,
            "nome": "João Silva",
            "endereco": "Rua X, 123",
            "salvar_cartao": false
        }
        """
        registrar_log('checkout.2fa', '>>> CHEGOU NO MÉTODO POST ValidarOTPCheckoutView', nivel='INFO')
        try:
            # 1. Validar origem (CORS)
            registrar_log('checkout.2fa', '>>> Passo 1: Validando CORS', nivel='INFO')
            if not validate_origin(request):
                registrar_log('checkout.2fa', 
                             f">>> BLOQUEADO POR CORS - Retornando 403",
                             nivel='ERROR')
                return Response({
                    'sucesso': False,
                    'mensagem': 'Origem não permitida'
                }, status=status.HTTP_403_FORBIDDEN)
            
            registrar_log('checkout.2fa', '>>> Passo 2: CORS OK, extraindo token', nivel='INFO')
            # Extrair token primeiro para rate limit
            token = request.data.get('token')
            if not token:
                registrar_log('checkout.2fa', '>>> ERRO: Token não fornecido - 400', nivel='ERROR')
                return Response({
                    'sucesso': False,
                    'mensagem': 'Token obrigatório'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            registrar_log('checkout.2fa', f'>>> Passo 3: Token {token[:8]}... - Verificando rate limit', nivel='INFO')
            # 2. Rate limit por token (3 tentativas de OTP)
            allowed, error_msg = check_otp_rate_limit(token)
            if not allowed:
                registrar_log('checkout.2fa',
                             f">>> BLOQUEADO POR RATE LIMIT - Retornando 429",
                             nivel='ERROR')
                return Response({
                    'sucesso': False,
                    'mensagem': error_msg
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)
            
            registrar_log('checkout.2fa', '>>> Passo 4: Rate limit OK, validando campos', nivel='INFO')
            # 3. Validar campos obrigatórios
            cpf = request.data.get('cpf')
            telefone = request.data.get('telefone')
            codigo_otp = request.data.get('codigo_otp')
            
            if not all([cpf, telefone, codigo_otp]):
                registrar_log('checkout.2fa', '>>> ERRO: Campos obrigatórios faltando - 400', nivel='ERROR')
                return Response({
                    'sucesso': False,
                    'mensagem': 'Campos obrigatórios: token, cpf, telefone, codigo_otp'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            registrar_log('checkout.2fa', '>>> Passo 5: Campos OK, validando token no banco', nivel='INFO')
            # Validar token
            try:
                token_obj = CheckoutToken.objects.get(token=token)
                if not token_obj.is_valid():
                    registrar_log('checkout.2fa', '>>> ERRO: Token inválido - 400', nivel='ERROR')
                    return Response({
                        'sucesso': False,
                        'mensagem': 'Token inválido ou expirado'
                    }, status=status.HTTP_400_BAD_REQUEST)
            except CheckoutToken.DoesNotExist:
                registrar_log('checkout.2fa', '>>> ERRO: Token não existe - 404', nivel='ERROR')
                return Response({
                    'sucesso': False,
                    'mensagem': 'Token não encontrado'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Obter IP e device fingerprint
            ip_address = get_client_ip(request)
            device_fingerprint = extract_device_fingerprint(request)
            
            # Converter valor
            try:
                valor_decimal = Decimal(str(request.data.get('valor_total')))
            except:
                return Response({
                    'sucesso': False,
                    'mensagem': 'Valor inválido'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            registrar_log('checkout.2fa', '>>> Passo 6: Token válido, chamando validar_otp_e_processar', nivel='INFO')
            # Validar OTP (sem processar ainda)
            resultado_otp = CheckoutSecurityService.validar_otp_e_processar(
                cpf=cpf,
                telefone=telefone,
                codigo_otp=codigo_otp,
                token=token,
                valor=valor_decimal,
                nsu=None,  # Ainda não temos NSU
                status='PENDENTE',  # Marca como pendente inicialmente
                ip_address=ip_address,
                device_fingerprint=device_fingerprint
            )
            
            if not resultado_otp['valido']:
                registrar_log('checkout.2fa', 
                             f">>> BLOQUEADO: OTP INVÁLIDO - Retornando 403: {resultado_otp['mensagem']}",
                             nivel='ERROR')
                return Response({
                    'sucesso': False,
                    'mensagem': resultado_otp['mensagem']
                }, status=status.HTTP_403_FORBIDDEN)
            
            # OTP válido - processar pagamento
            from checkout.link_pagamento_web.services import LinkPagamentoService
            
            dados_cartao = {
                'numero_cartao': request.data.get('numero_cartao'),
                'cvv': request.data.get('cvv'),
                'data_validade': request.data.get('data_validade'),
                'bandeira': request.data.get('bandeira')
            }
            
            dados_sessao = {
                'cpf': cpf,
                'nome': request.data.get('nome'),
                'celular': telefone,
                'endereco': request.data.get('endereco'),
                'parcelas': request.data.get('parcelas', 1),
                'tipo_pagamento': request.data.get('tipo_pagamento', 'CREDIT_ONE_INSTALLMENT'),
                'valor_total': valor_decimal,
                'salvar_cartao': request.data.get('salvar_cartao', False)
            }
            
            # Processar via service original
            resultado = LinkPagamentoService.processar_checkout_link_pagamento(
                token=token,
                dados_cartao=dados_cartao,
                dados_sessao=dados_sessao,
                ip_address=ip_address,
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            # Atualizar histórico com resultado real
            if resultado.get('sucesso'):
                # Atualizar para APROVADA com NSU
                CheckoutSecurityService.validar_otp_e_processar(
                    cpf=cpf,
                    telefone=telefone,
                    codigo_otp=codigo_otp,
                    token=token,
                    valor=valor_decimal,
                    nsu=resultado.get('nsu'),
                    status='APROVADA',
                    ip_address=ip_address,
                    device_fingerprint=device_fingerprint
                )
                
                registrar_log(
                    'checkout.2fa',
                    f"✅ Pagamento aprovado - Token: {token[:8]}... - NSU: {resultado.get('nsu')}"
                )
                
                # Enviar notificações de confirmação
                try:
                    from wallclub_core.integracoes.whatsapp_service import WhatsAppService
                    from wallclub_core.integracoes.notification_service import NotificationService
                    from wallclub_core.estr_organizacional.loja import Loja
                    
                    # Buscar nome da loja
                    loja = Loja.get_loja(token_obj.loja_id)
                    nome_loja = loja.razao_social if loja else 'Loja'
                    
                    # 1. Enviar WhatsApp
                    WhatsAppService.envia_whatsapp(
                        numero_telefone=telefone,
                        canal_id=1,  # Canal padrão
                        nome_template='checkout_pagamento_confirmado',
                        idioma_template='pt_BR',
                        parametros_corpo=[f"{valor_decimal:.2f}", nome_loja],
                        parametros_botao=None
                    )
                    
                    registrar_log('checkout.2fa', 
                                 f"📲 WhatsApp de confirmação enviado para {telefone[-4:]}",
                                 nivel='INFO')
                    
                    # 2. Enviar Push (se cliente tiver app)
                    try:
                        from apps.cliente.models import Cliente
                        cliente = Cliente.objects.filter(cpf=cpf).first()
                        
                        if cliente:
                            notification_service = NotificationService.get_instance(canal_id=1)
                            notification_service.send_push(
                                cliente_id=cliente.id,
                                id_template='checkout_pagamento_confirmado',
                                valor=f"{valor_decimal:.2f}",
                                estabelecimento=nome_loja
                            )
                            
                            registrar_log('checkout.2fa',
                                         f"🔔 Push de confirmação enviado para cliente {cliente.id}",
                                         nivel='INFO')
                    except Exception as e:
                        registrar_log('checkout.2fa',
                                     f"Erro ao enviar Push: {str(e)}",
                                     nivel='WARNING')
                    
                except Exception as e:
                    registrar_log('checkout.2fa',
                                 f"Erro ao enviar notificações: {str(e)}",
                                 nivel='ERROR')
            else:
                # Atualizar para NEGADA
                CheckoutSecurityService.validar_otp_e_processar(
                    cpf=cpf,
                    telefone=telefone,
                    codigo_otp=codigo_otp,
                    token=token,
                    valor=valor_decimal,
                    nsu=None,
                    status='NEGADA',
                    ip_address=ip_address,
                    device_fingerprint=device_fingerprint
                )
                
                registrar_log(
                    'checkout.2fa',
                    f"❌ Pagamento negado - Token: {token[:8]}...",
                    nivel='WARNING'
                )
            
            return Response(resultado, status=status.HTTP_200_OK if resultado.get('sucesso') else status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            registrar_log(
                'checkout.2fa',
                f"Erro ao validar OTP e processar: {str(e)}",
                nivel='ERROR'
            )
            return Response({
                'sucesso': False,
                'mensagem': 'Erro interno do servidor'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ConsultarLimiteProgressivoView(APIView):
    """
    Consulta limite progressivo do cliente
    GET /api/checkout/limite-progressivo/?cpf=12345678901
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Consulta limite atual do CPF"""
        try:
            cpf = request.query_params.get('cpf')
            
            if not cpf:
                return Response({
                    'sucesso': False,
                    'mensagem': 'CPF é obrigatório'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            from .models_2fa import CheckoutTransactionHelper
            
            limite = CheckoutTransactionHelper.calcular_limite_progressivo(cpf)
            transacoes = CheckoutTransactionHelper.contar_transacoes_aprovadas(cpf)
            
            return Response({
                'sucesso': True,
                'limite': float(limite) if limite > 0 else None,
                'sem_limite': limite == 0,
                'transacoes_aprovadas': transacoes,
                'mensagem': f'Limite atual: R$ {limite:.2f}' if limite > 0 else 'Sem limite'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            registrar_log(
                'checkout.2fa',
                f"Erro ao consultar limite: {str(e)}",
                nivel='ERROR'
            )
            return Response({
                'sucesso': False,
                'mensagem': 'Erro interno do servidor'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
