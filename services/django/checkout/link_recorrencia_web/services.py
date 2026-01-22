"""
Services para tokenização de cartão em recorrências.
"""
from typing import Dict, Any
from decimal import Decimal
from django.db import transaction
from django.conf import settings
from wallclub_core.utilitarios.log_control import registrar_log
from wallclub_core.integracoes.email_service import EmailService


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
            link_checkout = f"{settings.CHECKOUT_BASE_URL}/api/v1/checkout/recorrencia/?token={token_obj.token}"
            
            # Enviar email usando serviço centralizado
            context = {
                'cliente_nome': cliente_nome,
                'descricao': descricao,
                'valor': valor,
                'loja_nome': loja_nome,
                'link_checkout': link_checkout,
                'validade_horas': 72
            }
            
            resultado = EmailService.enviar_email(
                destinatarios=[cliente_email],
                assunto=f'Cadastre seu cartão para cobrança recorrente - {loja_nome}',
                template_html='emails/checkout/link_recorrencia.html',
                template_context=context,
                fail_silently=False
            )
            
            if resultado['sucesso']:
                registrar_log(
                    'checkout.recorrencia',
                    f"Email de cadastro de cartão enviado: Recorrência={recorrencia_id}, Email={cliente_email}"
                )
            else:
                registrar_log(
                    'checkout.recorrencia',
                    f"Erro ao enviar email: {resultado['mensagem']}",
                    nivel='ERROR'
                )
            
            return {
                'sucesso': True,
                'mensagem': f'Link de cadastro enviado para {cliente_email}',
                'link': link_checkout,
                'token': token_obj.token
            }
            
        except Exception as e:
            registrar_log('checkout', f"Erro ao criar token: {str(e)}", nivel='ERROR')
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
        
        FLUXO:
        1. Valida token
        2. Faz pré-autorização de R$ 1,00 para validar cartão
        3. Cancela a pré-autorização (estorna)
        4. Tokeniza o cartão
        5. Vincula cartão à recorrência
        
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
            from checkout.services_gateway_router import GatewayRouter
            
            # Validar token
            try:
                token_obj = RecorrenciaToken.objects.select_related('recorrencia', 'recorrencia__cliente').get(token=token)
            except RecorrenciaToken.DoesNotExist:
                return {'sucesso': False, 'mensagem': 'Token inválido ou expirado'}
            
            if not token_obj.is_valid():
                return {'sucesso': False, 'mensagem': 'Token expirado ou já utilizado'}
            
            recorrencia = token_obj.recorrencia
            cliente = recorrencia.cliente
            loja_id = token_obj.loja_id
            
            # Obter service correto baseado no gateway da loja
            transacoes_service = GatewayRouter.obter_service_transacao(loja_id)
            gateway_ativo = GatewayRouter.obter_gateway_loja(loja_id)
            
            registrar_log(
                'checkout.recorrencia',
                f"💳 [VALIDAÇÃO] Iniciando validação de cartão via {gateway_ativo} para recorrência {recorrencia.id}"
            )
            
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
            
            # ========== ETAPA 1: PRÉ-AUTORIZAÇÃO DE R$ 1,00 ==========
            registrar_log(
                'checkout.recorrencia',
                f"🔐 [VALIDAÇÃO] Etapa 1: Pré-autorizando R$ 1,00 via {gateway_ativo} para validar cartão"
            )
            
            # Preparar dados para pré-autorização
            cpf_limpo = cliente.cpf.replace('.', '').replace('-', '')
            
            dados_preautorizacao = {
                'numero_cartao': numero_cartao,
                'data_validade': validade,
                'codigo_seguranca': cvv,
                'nome_impresso': nome_cartao.upper(),
                'bandeira': bandeira,
                'valor': Decimal('1.00'),  # R$ 1,00
                'quantidade_parcelas': 1,
                'forma_pagamento': '1',  # Crédito à vista
                'descricao_pedido': 'Validação de cartão - WallClub',
                'ip_address_comprador': ip_address,
                'cpf_comprador': int(cpf_limpo),
                'nome_comprador': cliente.nome,
                'transacao_pre_autorizada': True  # PRÉ-AUTORIZAÇÃO
            }
            
            # Interface unificada - funciona com Pinbank e Own
            resultado_preauth = transacoes_service.efetuar_transacao_cartao(dados_preautorizacao)
            
            if not resultado_preauth.get('sucesso'):
                registrar_log(
                    'checkout.recorrencia',
                    f"❌ [VALIDAÇÃO] Pré-autorização negada: {resultado_preauth.get('mensagem')}",
                    nivel='WARNING'
                )
                return {
                    'sucesso': False,
                    'mensagem': f'Cartão inválido ou sem saldo: {resultado_preauth.get("mensagem")}'
                }
            
            # Extrair NSU da pré-autorização
            nsu_preauth = resultado_preauth.get('nsu') or resultado_preauth.get('dados', {}).get('nsu')
            
            if not nsu_preauth:
                registrar_log(
                    'checkout.recorrencia',
                    f"⚠️ [VALIDAÇÃO] NSU não retornado na pré-autorização",
                    nivel='WARNING'
                )
                return {
                    'sucesso': False,
                    'mensagem': 'Erro ao validar cartão (NSU não retornado)'
                }
            
            registrar_log(
                'checkout.recorrencia',
                f"✅ [VALIDAÇÃO] Pré-autorização aprovada: NSU={nsu_preauth}"
            )
            
            # ========== ETAPA 2: CANCELAR PRÉ-AUTORIZAÇÃO (ESTORNO) ==========
            registrar_log(
                'checkout.recorrencia',
                f"↩️ [VALIDAÇÃO] Etapa 2: Cancelando pré-autorização via {gateway_ativo} (estorno de R$ 1,00)"
            )
            
            # Interface unificada - funciona com Pinbank e Own
            resultado_cancelamento = transacoes_service.cancelar_transacao(
                nsu_operacao=nsu_preauth,
                valor=Decimal('1.00')
            )
            
            if not resultado_cancelamento.get('sucesso'):
                registrar_log(
                    'checkout.recorrencia',
                    f"⚠️ [VALIDAÇÃO] Erro ao cancelar pré-autorização: {resultado_cancelamento.get('mensagem')}",
                    nivel='WARNING'
                )
                # Continuar mesmo se cancelamento falhar (cartão já foi validado)
            else:
                registrar_log(
                    'checkout.recorrencia',
                    f"✅ [VALIDAÇÃO] Pré-autorização cancelada com sucesso (estorno processado)"
                )
            
            # ========== ETAPA 3: TOKENIZAR CARTÃO ==========
            registrar_log(
                'checkout.recorrencia',
                f"🔑 [VALIDAÇÃO] Etapa 3: Tokenizando cartão para uso futuro"
            )
            
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
                registrar_log(
                    'checkout.recorrencia',
                    f"❌ [VALIDAÇÃO] Erro ao tokenizar cartão: {resultado_token.get('mensagem')}",
                    nivel='ERROR'
                )
                return {
                    'sucesso': False,
                    'mensagem': f'Erro ao tokenizar cartão: {resultado_token.get("mensagem")}'
                }
            
            # ========== ETAPA 4: VINCULAR CARTÃO À RECORRÊNCIA ==========
            registrar_log(
                'checkout.recorrencia',
                f"🔗 [VALIDAÇÃO] Etapa 4: Vinculando cartão à recorrência"
            )
            
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
                f"✅ [VALIDAÇÃO] Cartão validado e cadastrado com sucesso: "
                f"Recorrência={recorrencia.id}, Cartão={cartao_tokenizado.cartao_mascarado}, "
                f"Próxima cobrança={proxima}, NSU validação={nsu_preauth}"
            )
            
            return {
                'sucesso': True,
                'mensagem': 'Cartão validado e cadastrado com sucesso! Sua recorrência está ativa.',
                'proxima_cobranca': proxima.strftime('%d/%m/%Y'),
                'recorrencia_id': recorrencia.id,
                'validacao_realizada': True
            }
            
        except Exception as e:
            registrar_log('checkout', f"Erro ao processar cadastro: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': f'Erro ao processar cadastro: {str(e)}'
            }
