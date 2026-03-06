"""
Views para checkout de recorrência (cadastro de cartão).
"""
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from checkout.link_recorrencia_web.services import RecorrenciaTokenService
from wallclub_core.utilitarios.log_control import registrar_log
import json


@require_http_methods(["GET"])
def checkout_recorrencia_view(request):
    """
    Tela de cadastro de cartão para recorrência.
    GET: Valida token e exibe formulário
    """
    token = request.GET.get('token')

    if not token:
        return render(request, 'recorrencia/erro.html', {
            'mensagem': 'Token não fornecido'
        })

    try:
        from checkout.link_recorrencia_web.models import RecorrenciaToken

        # Validar token
        try:
            token_obj = RecorrenciaToken.objects.select_related(
                'recorrencia', 'recorrencia__cliente'
            ).get(token=token)
        except RecorrenciaToken.DoesNotExist:
            return render(request, 'recorrencia/erro.html', {
                'mensagem': 'Token inválido ou não encontrado'
            })

        # Verificar se já foi usado
        if token_obj.used:
            return render(request, 'recorrencia/sucesso.html', {
                'titulo': 'Cartão já cadastrado',
                'mensagem': 'Este cartão já foi cadastrado anteriormente. Sua recorrência está ativa.',
                'recorrencia': token_obj.recorrencia
            })

        # Verificar se expirou
        if not token_obj.is_valid():
            return render(request, 'recorrencia/erro.html', {
                'mensagem': 'Este link expirou. Entre em contato com a loja.'
            })

        # Renderizar formulário
        context = {
            'token': token,
            'cliente_nome': token_obj.cliente_nome,
            'cliente_cpf': token_obj.cliente_cpf,
            'descricao': token_obj.descricao_recorrencia,
            'valor': token_obj.valor_recorrencia,
            'recorrencia': token_obj.recorrencia,
            'expires_at': token_obj.expires_at
        }

        return render(request, 'recorrencia/checkout_recorrencia.html', context)

    except Exception as e:
        registrar_log('checkout', f"Erro ao carregar checkout: {str(e)}", nivel='ERROR')
        return render(request, 'recorrencia/erro.html', {
            'mensagem': 'Erro ao carregar página. Tente novamente.'
        })


@csrf_exempt
@require_http_methods(["POST"])
def enviar_otp_view(request):
    """
    Envia código OTP para telefone do cliente.
    POST: {token, telefone}
    """
    try:
        data = json.loads(request.body)
        token = data.get('token')
        telefone = data.get('telefone', '').replace('(', '').replace(')', '').replace('-', '').replace(' ', '')
        ultimos_4_digitos = data.get('ultimos_4_digitos')  # Últimos 4 dígitos do cartão

        if not token or not telefone:
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'Token e telefone são obrigatórios'
            })

        # Validar token
        from checkout.link_recorrencia_web.models import RecorrenciaToken
        try:
            token_obj = RecorrenciaToken.objects.get(token=token)
        except RecorrenciaToken.DoesNotExist:
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'Token inválido'
            })

        # Enviar OTP usando o mesmo service do checkout
        from checkout.link_pagamento_web.services_2fa import CheckoutSecurityService
        from wallclub_core.seguranca.services_2fa import OTPService

        cpf_limpo = token_obj.cliente_cpf.replace('.', '').replace('-', '')

        # 1. Validar e registrar telefone
        resultado_telefone = CheckoutSecurityService.validar_telefone_cliente(cpf_limpo, telefone)
        if not resultado_telefone['sucesso']:
            return JsonResponse({
                'sucesso': False,
                'mensagem': resultado_telefone['mensagem']
            })

        telefone_obj = resultado_telefone['telefone_obj']

        # 2. Gerar OTP
        resultado_otp = OTPService.gerar_otp(
            user_id=telefone_obj.id,
            tipo_usuario='cliente',
            telefone=telefone,
            ip_solicitacao=request.META.get('REMOTE_ADDR', '')
        )

        if not resultado_otp['success']:
            return JsonResponse({
                'sucesso': False,
                'mensagem': resultado_otp.get('mensagem', 'Erro ao gerar código')
            })

        # 3. Buscar código do banco (em produção não retorna no resultado)
        from wallclub_core.seguranca.models import AutenticacaoOTP
        otp_obj = AutenticacaoOTP.objects.get(id=resultado_otp['otp_id'])

        # 4. Enviar OTP via WhatsApp
        from decimal import Decimal
        otp_enviado = CheckoutSecurityService.enviar_otp_checkout(
            telefone=telefone,
            codigo_otp=otp_obj.codigo,
            valor=Decimal(str(token_obj.valor_recorrencia)),
            ultimos_4_digitos=ultimos_4_digitos
        )

        resultado = {
            'sucesso': otp_enviado,
            'mensagem': 'Código enviado via WhatsApp' if otp_enviado else 'Erro ao enviar código'
        }

        if resultado['sucesso']:
            registrar_log('checkout', f"OTP enviado para telefone {telefone[-4:]}***")

        return JsonResponse(resultado)

    except Exception as e:
        registrar_log('checkout', f"Erro ao enviar OTP: {str(e)}", nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro ao enviar código: {str(e)}'
        })


@csrf_exempt
@require_http_methods(["POST"])
def processar_cadastro_cartao_view(request):
    """
    Processa cadastro de cartão (tokenização).
    POST: Recebe dados do cartão, valida OTP e tokeniza
    """
    try:
        data = json.loads(request.body)

        token = data.get('token')
        telefone = data.get('telefone', '').replace('(', '').replace(')', '').replace('-', '').replace(' ', '')
        otp_code = data.get('otp_code')
        numero_cartao = data.get('numero_cartao', '').replace(' ', '')
        validade = data.get('validade', '')
        cvv = data.get('cvv', '')
        nome_cartao = data.get('nome_cartao', '')

        # Validações básicas
        if not all([token, telefone, otp_code, numero_cartao, validade, cvv, nome_cartao]):
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'Todos os campos são obrigatórios'
            })

        # Validar token
        from checkout.link_recorrencia_web.models import RecorrenciaToken
        try:
            token_obj = RecorrenciaToken.objects.get(token=token)
        except RecorrenciaToken.DoesNotExist:
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'Token inválido'
            })

        # Validar OTP
        from checkout.link_pagamento_web.models_2fa import CheckoutClienteTelefone
        from wallclub_core.seguranca.services_2fa import OTPService
        from checkout.models import CheckoutCliente

        cpf_limpo = token_obj.cliente_cpf.replace('.', '').replace('-', '')

        # Buscar cliente da mesma loja da recorrência
        from checkout.models_recorrencia import RecorrenciaAgendada
        recorrencia = RecorrenciaAgendada.objects.get(id=token_obj.recorrencia_id)

        cliente = CheckoutCliente.objects.filter(
            cpf=cpf_limpo,
            loja_id=recorrencia.loja_id
        ).first()

        if not cliente:
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'Cliente não encontrado'
            })

        # Buscar telefone
        try:
            telefone_obj = CheckoutClienteTelefone.objects.get(
                cliente=cliente,
                telefone=telefone,
                ativo__in=[-1, 1]  # Pendente ou ativo
            )
        except CheckoutClienteTelefone.DoesNotExist:
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'Telefone não encontrado'
            })

        # Validar OTP
        resultado_validacao = OTPService.validar_otp(
            user_id=telefone_obj.id,
            tipo_usuario='cliente',
            codigo=otp_code
        )

        if not resultado_validacao['success']:
            return JsonResponse({
                'sucesso': False,
                'mensagem': resultado_validacao.get('mensagem', 'Código inválido')
            })

        # Ativar telefone se estava pendente
        if telefone_obj.ativo == -1:
            telefone_obj.ativo = 1
            telefone_obj.save(update_fields=['ativo'])
            registrar_log('checkout', f'Telefone ativado: {telefone[-4:]}***')

        # Processar via service
        ip_address = request.META.get('REMOTE_ADDR', '')

        resultado = RecorrenciaTokenService.processar_cadastro_cartao(
            token=token,
            numero_cartao=numero_cartao,
            validade=validade,
            cvv=cvv,
            nome_cartao=nome_cartao,
            ip_address=ip_address
        )

        return JsonResponse(resultado)

    except json.JSONDecodeError:
        return JsonResponse({
            'sucesso': False,
            'mensagem': 'Dados inválidos'
        })
    except Exception as e:
        registrar_log('checkout', f"Erro ao processar cadastro: {str(e)}", nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro ao processar: {str(e)}'
        })


@require_http_methods(["GET"])
def sucesso_view(request):
    """
    Página de sucesso após cadastro de cartão.
    GET: Exibe mensagem de sucesso
    """
    mensagem = request.GET.get('msg', 'Cartão cadastrado com sucesso!')

    return render(request, 'recorrencia/sucesso.html', {
        'mensagem': mensagem
    })
