"""
Services para tokenização de cartão em recorrências.
"""
from typing import Dict, Any
from decimal import Decimal
from django.db import transaction
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from wallclub_core.utilitarios.log_control import registrar_log


class RecorrenciaTokenService:
    """
    Service para gerenciar tokens de cadastro de cartão em recorrências.
    """
    
    @staticmethod
    def criar_token_e_enviar_email(
        recorrencia_id: int,
        loja_id: int,
        cliente_nome: str,
        cliente_cpf: str,
        cliente_email: str,
        descricao: str,
        valor: Decimal,
        loja_nome: str
    ) -> Dict[str, Any]:
        """
        Cria token para cadastro de cartão e envia email para cliente.
        
        Args:
            recorrencia_id: ID da recorrência
            loja_id: ID da loja
            cliente_nome: Nome do cliente
            cliente_cpf: CPF do cliente
            cliente_email: Email do cliente
            descricao: Descrição da recorrência
            valor: Valor da recorrência
            loja_nome: Nome da loja
            
        Returns:
            Dict com sucesso, mensagem e link
        """
        try:
            from checkout.models_recorrencia import RecorrenciaAgendada
            from checkout.link_recorrencia_web.models import RecorrenciaToken
            
            # Buscar recorrência
            recorrencia = RecorrenciaAgendada.objects.get(id=recorrencia_id)
            
            # Gerar token
            token_obj = RecorrenciaToken.generate_token(
                recorrencia=recorrencia,
                loja_id=loja_id,
                cliente_nome=cliente_nome,
                cliente_cpf=cliente_cpf,
                cliente_email=cliente_email,
                descricao=descricao,
                valor=valor
            )
            
            # Gerar link
            base_url = settings.BASE_URL or 'https://apidj.wallclub.com.br'
            link_checkout = f"{base_url}/api/v1/checkout/recorrencia/?token={token_obj.token}"
            
            # Enviar email
            assunto = f'Cadastre seu cartão para cobrança recorrente - {loja_nome}'
            
            html_message = render_to_string('recorrencia/email_cadastro_cartao.html', {
                'cliente_nome': cliente_nome,
                'descricao': descricao,
                'valor': valor,
                'loja_nome': loja_nome,
                'link_checkout': link_checkout,
                'validade_horas': 72
            })
            
            send_mail(
                subject=assunto,
                message=f'Olá {cliente_nome},\n\nAcesse o link para cadastrar seu cartão: {link_checkout}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[cliente_email],
                html_message=html_message,
                fail_silently=False
            )
            
            registrar_log(
                'checkout.recorrencia',
                f"Email de cadastro de cartão enviado: Recorrência={recorrencia_id}, Email={cliente_email}"
            )
            
            return {
                'sucesso': True,
                'mensagem': f'Link de cadastro enviado para {cliente_email}',
                'link': link_checkout,
                'token': token_obj.token
            }
            
        except Exception as e:
            registrar_log('checkout.recorrencia', f"Erro ao criar token: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': f'Erro ao enviar link: {str(e)}'
            }
    
    @staticmethod
    @transaction.atomic
    def processar_cadastro_cartao(
        token: str,
        numero_cartao: str,
        validade: str,
        cvv: str,
        nome_cartao: str,
        ip_address: str
    ) -> Dict[str, Any]:
        """
        Processa cadastro de cartão para recorrência (tokenização).
        
        Args:
            token: Token de recorrência
            numero_cartao: Número do cartão
            validade: Validade MM/YYYY
            cvv: CVV
            nome_cartao: Nome no cartão
            ip_address: IP do cliente
            
        Returns:
            Dict com sucesso e mensagem
        """
        try:
            from checkout.link_recorrencia_web.models import RecorrenciaToken
            from checkout.models import CheckoutCartaoTokenizado
            from checkout.services import CartaoTokenizadoService
            
            # Validar token
            try:
                token_obj = RecorrenciaToken.objects.select_related('recorrencia', 'recorrencia__cliente').get(token=token)
            except RecorrenciaToken.DoesNotExist:
                return {'sucesso': False, 'mensagem': 'Token inválido ou expirado'}
            
            if not token_obj.is_valid():
                return {'sucesso': False, 'mensagem': 'Token expirado ou já utilizado'}
            
            recorrencia = token_obj.recorrencia
            cliente = recorrencia.cliente
            
            # Detectar bandeira
            primeiro_digito = numero_cartao[0]
            if primeiro_digito in ['4']:
                bandeira = 'VISA'
            elif primeiro_digito in ['5']:
                bandeira = 'MASTERCARD'
            elif primeiro_digito in ['3']:
                bandeira = 'AMEX'
            elif primeiro_digito in ['6']:
                bandeira = 'ELO'
            else:
                bandeira = 'VISA'  # default
            
            # Tokenizar cartão via Pinbank
            dados_cartao = {
                'numero': numero_cartao,
                'validade': validade,
                'cvv': cvv,
                'nome_titular': nome_cartao,
                'bandeira': bandeira
            }
            
            resultado_token = CartaoTokenizadoService.tokenizar_cartao(
                cliente_id=cliente.id,
                dados_cartao=dados_cartao
            )
            
            if not resultado_token.get('sucesso'):
                return {
                    'sucesso': False,
                    'mensagem': f'Erro ao tokenizar cartão: {resultado_token.get("mensagem")}'
                }
            
            # Buscar cartão tokenizado criado
            cartao_tokenizado = CheckoutCartaoTokenizado.objects.get(id=resultado_token['cartao_id'])
            
            # Atualizar recorrência: vincular cartão e ativar
            recorrencia.cartao_tokenizado = cartao_tokenizado
            recorrencia.status = 'ativo'
            
            # Calcular próxima cobrança
            from datetime import datetime
            hoje = datetime.now().date()
            proxima = recorrencia.calcular_proxima_cobranca(hoje)
            proxima = recorrencia.ajustar_para_dia_util(proxima)
            recorrencia.proxima_cobranca = proxima
            
            recorrencia.save()
            
            # Marcar token como usado
            token_obj.mark_as_used()
            
            registrar_log(
                'checkout.recorrencia',
                f"Cartão cadastrado e recorrência ativada: Recorrência={recorrencia.id}, "
                f"Cartão={cartao_tokenizado.cartao_mascarado}, Próxima cobrança={proxima}"
            )
            
            return {
                'sucesso': True,
                'mensagem': 'Cartão cadastrado com sucesso! Sua recorrência está ativa.',
                'proxima_cobranca': proxima.strftime('%d/%m/%Y'),
                'recorrencia_id': recorrencia.id
            }
            
        except Exception as e:
            registrar_log('checkout.recorrencia', f"Erro ao processar cadastro: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': f'Erro ao processar cadastro: {str(e)}'
            }
