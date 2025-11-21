"""
Services para o sistema de checkout via link de pagamento.
Lógica de negócio do fluxo público de checkout.
"""
from typing import Dict, Any
from decimal import Decimal
from django.db import transaction
from wallclub_core.utilitarios.log_control import registrar_log


def sanitize_for_json(obj):
    """Converte Decimals para float recursivamente para serialização JSON"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {key: sanitize_for_json(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(item) for item in obj]
    return obj


class LinkPagamentoService:
    """Serviço para processar pagamentos via link público"""
    
    @staticmethod
    @transaction.atomic
    def processar_checkout_link_pagamento(
        token: str,
        dados_cartao: Dict[str, Any],
        dados_sessao: Dict[str, Any],
        ip_address: str,
        user_agent: str
    ) -> Dict[str, Any]:
        """
        Processa pagamento via link de pagamento (checkout público)
        
        Args:
            token: Token do checkout
            dados_cartao: Dict com numero_cartao, cvv, data_validade, bandeira
            dados_sessao: Dict com cpf, nome, celular, endereco, parcelas, tipo_pagamento, valor_total, salvar_cartao
            ip_address: IP do cliente
            user_agent: User agent do cliente
            
        Returns:
            Dict com sucesso, transacao_id, nsu, mensagem, tentativas_restantes, pode_tentar_novamente
        """
        from checkout.link_pagamento_web.models import CheckoutToken, CheckoutSession
        from checkout.models import CheckoutTransaction, CheckoutTransactionAttempt, CheckoutCliente, CheckoutCartaoTokenizado
        from checkout.services_gateway_router import GatewayRouter
        import hashlib
        from datetime import datetime
        
        # Mapeamento de tipos de compra
        TIPO_COMPRA_MAP = {
            'CREDIT_IN_INSTALLMENTS_WITHOUT_INTEREST': '2',
            'CREDIT_ONE_INSTALLMENT': '1',
        }
        
        try:
            # Validar token
            try:
                token_obj = CheckoutToken.objects.get(token=token)
                if not token_obj.is_valid():
                    return {
                        'sucesso': False,
                        'mensagem': 'Token inválido ou expirado',
                        'tentativas_restantes': 0,
                        'pode_tentar_novamente': False
                    }
            except CheckoutToken.DoesNotExist:
                return {
                    'sucesso': False,
                    'mensagem': 'Token não encontrado',
                    'tentativas_restantes': 0,
                    'pode_tentar_novamente': False
                }
            
            # Hash do cartão para auditoria
            numero_cartao = dados_cartao['numero_cartao']
            cartao_hash = hashlib.sha256(numero_cartao.encode()).hexdigest()
            
            # Criar ou atualizar sessão
            session, created = CheckoutSession.objects.get_or_create(
                token=token_obj,
                defaults={
                    'cpf': dados_sessao['cpf'],
                    'nome': dados_sessao['nome'],
                    'celular': dados_sessao['celular'],
                    'endereco': dados_sessao['endereco'],
                    'numero_cartao_hash': cartao_hash,
                    'data_validade': dados_cartao['data_validade'],
                    'parcelas': dados_sessao['parcelas'],
                    'tipo_pagamento': dados_sessao['tipo_pagamento'],
                    'ip_address': ip_address,
                    'user_agent': user_agent
                }
            )
            
            if not created:
                # Atualizar dados existentes
                session.numero_cartao_hash = cartao_hash
                session.data_validade = dados_cartao['data_validade']
                session.parcelas = dados_sessao['parcelas']
                session.tipo_pagamento = dados_sessao['tipo_pagamento']
                session.cpf = dados_sessao['cpf']
                session.nome = dados_sessao['nome']
                session.celular = dados_sessao['celular']
                session.endereco = dados_sessao['endereco']
                session.save()
            
            # Buscar transação existente criada pelo vendedor
            try:
                transacao = CheckoutTransaction.objects.get(token=token)
            except CheckoutTransaction.DoesNotExist:
                registrar_log('checkout.link_pagamento_web', f"ERRO: Transaction não encontrada para token {token[:8]}...", nivel='ERROR')
                return {
                    'sucesso': False,
                    'mensagem': 'Transação não encontrada. Entre em contato com o vendedor.',
                    'tentativas_restantes': 0,
                    'pode_tentar_novamente': False
                }
            
            # =============================================================================
            # ANÁLISE ANTIFRAUDE (RISK ENGINE)
            # =============================================================================
            from checkout.services_antifraude import CheckoutAntifraudeService
            
            # Valores
            valor_original = Decimal(str(token_obj.item_valor)) if not isinstance(token_obj.item_valor, Decimal) else token_obj.item_valor
            valor_final = Decimal(str(dados_sessao['valor_total']))
            
            registrar_log('checkout.link_pagamento_web', '')
            registrar_log('checkout.link_pagamento_web', '=' * 80)
            registrar_log('checkout.link_pagamento_web', '🛡️  ANÁLISE ANTIFRAUDE - CHECKOUT WEB')
            registrar_log('checkout.link_pagamento_web', '=' * 80)
            
            # Chamar Risk Engine
            permitir, resultado_antifraude = CheckoutAntifraudeService.analisar_transacao(
                cpf=session.cpf,
                valor=valor_final,
                modalidade=session.tipo_pagamento,
                parcelas=session.parcelas,
                loja_id=token_obj.loja_id,
                canal_id=token_obj.canal_id if hasattr(token_obj, 'canal_id') else None,
                numero_cartao=numero_cartao,
                bandeira=dados_cartao.get('bandeira'),
                ip_address=ip_address,
                user_agent=user_agent,
                device_fingerprint=dados_sessao.get('device_fingerprint'),
                cliente_nome=session.nome,
                cliente_email=session.cpf,  # Usar CPF como identificador
                transaction_id=str(transacao.id)
            )
            
            # Salvar resultado antifraude na transação
            transacao.score_risco = resultado_antifraude.get('score_risco', 0)
            transacao.decisao_antifraude = resultado_antifraude.get('decisao', 'APROVADO')
            transacao.motivo_bloqueio = resultado_antifraude.get('motivo', '')
            transacao.antifraude_response = resultado_antifraude
            
            # Tratar decisão REPROVADO
            if not permitir or resultado_antifraude.get('decisao') == 'REPROVADO':
                transacao.status = 'BLOQUEADA_ANTIFRAUDE'
                transacao.save()
                
                registrar_log('checkout.link_pagamento_web', 
                             f"❌ TRANSAÇÃO BLOQUEADA PELO ANTIFRAUDE - Score: {transacao.score_risco}, Motivo: {transacao.motivo_bloqueio}", 
                             nivel='WARNING')
                registrar_log('checkout.link_pagamento_web', '=' * 80)
                
                return {
                    'sucesso': False,
                    'mensagem': 'Transação bloqueada por segurança. Entre em contato com o vendedor.',
                    'tentativas_restantes': 0,
                    'pode_tentar_novamente': False,
                    'motivo_tecnico': transacao.motivo_bloqueio
                }
            
            # Tratar decisão REVISAR (processar mas marcar para revisão)
            if resultado_antifraude.get('decisao') == 'REVISAR':
                transacao.status = 'PENDENTE_REVISAO'
                registrar_log('checkout.link_pagamento_web', 
                             f"⚠️ TRANSAÇÃO EM REVISÃO - Score: {transacao.score_risco}, será processada mas requer análise manual", 
                             nivel='WARNING')
            
            registrar_log('checkout.link_pagamento_web', 
                         f"✅ ANTIFRAUDE: {resultado_antifraude.get('decisao')} - Score: {transacao.score_risco}/100")
            registrar_log('checkout.link_pagamento_web', '=' * 80)
            registrar_log('checkout.link_pagamento_web', '')
            
            # =============================================================================
            # PROCESSAR PAGAMENTO VIA GATEWAY (PINBANK OU OWN)
            # =============================================================================
            # Obter service correto baseado no gateway da loja
            transacoes_service = GatewayRouter.obter_service_transacao(token_obj.loja_id)
            gateway_ativo = GatewayRouter.obter_gateway_loja(token_obj.loja_id)
            
            forma_pagamento_codigo = TIPO_COMPRA_MAP.get(session.tipo_pagamento, '1')
            
            dados_transacao = {
                'nome_impresso': session.nome.upper(),
                'data_validade': session.data_validade,
                'numero_cartao': numero_cartao,
                'codigo_seguranca': dados_cartao['cvv'],
                'valor': valor_final,
                'forma_pagamento': forma_pagamento_codigo,
                'quantidade_parcelas': session.parcelas,
                'descricao_pedido': f"{token_obj.item_nome} - Checkout WallClub",
                'ip_address_comprador': ip_address,
                'cpf_comprador': int(session.cpf),
                'nome_comprador': session.nome,
                'bandeira': dados_cartao.get('bandeira', 'VISA')
            }
            
            registrar_log('checkout.link_pagamento_web', 
                         f"Processando transação via {gateway_ativo} - Token: {token[:8]}..., Parcelas: {session.parcelas}, Valor Original: R$ {valor_original}, Valor Final: R$ {valor_final}")
            
            # Processar transação (interface unificada)
            resultado_transacao = transacoes_service.efetuar_transacao_cartao(dados_transacao)
            
            if not resultado_transacao.get('sucesso', False):
                # Incrementar tentativas do token
                token_obj.incrementar_tentativa()
                
                # Registrar tentativa frustrada
                CheckoutTransactionAttempt.objects.create(
                    transaction=transacao,
                    tentativa_numero=token_obj.tentativas_pagamento,
                    erro_pinbank=resultado_transacao.get('mensagem', 'Erro desconhecido'),
                    pinbank_response=sanitize_for_json(resultado_transacao),
                    ip_address_cliente=ip_address,
                    user_agent_cliente=user_agent,
                    numero_cartao_hash=cartao_hash
                )
                
                # Atualizar transação se limite de tentativas atingido
                if token_obj.tentativas_pagamento >= 3:
                    transacao.status = 'NEGADA'
                    transacao.erro_pinbank = f"Limite de tentativas atingido: {resultado_transacao.get('mensagem')}"
                    transacao.pinbank_response = sanitize_for_json(resultado_transacao)
                    transacao.save()
                
                # Verificar quantas tentativas restam
                tentativas_restantes = 3 - token_obj.tentativas_pagamento
                
                registrar_log('checkout.link_pagamento_web', f"Transação NEGADA para token {token[:8]}... - {resultado_transacao.get('mensagem')} - Tentativa {token_obj.tentativas_pagamento}/3")
                
                return {
                    'sucesso': False,
                    'mensagem': resultado_transacao.get('mensagem', 'Pagamento não autorizado'),
                    'tentativas_restantes': tentativas_restantes,
                    'pode_tentar_novamente': tentativas_restantes > 0
                }
            
            # Transação aprovada
            dados_transacao_aprovada = resultado_transacao.get('dados', {})
            nsu = dados_transacao_aprovada.get('nsu', '')
            codigo_autorizacao = dados_transacao_aprovada.get('codigo_autorizacao', '')
            
            # Atualizar transação existente com dados finais
            transacao.session = session
            transacao.nsu = nsu
            transacao.codigo_autorizacao = codigo_autorizacao
            
            # Status: Se estava em PENDENTE_REVISAO, manter; senão APROVADA
            if transacao.status != 'PENDENTE_REVISAO':
                transacao.status = 'APROVADA'
            
            transacao.forma_pagamento = session.tipo_pagamento
            transacao.parcelas = session.parcelas
            transacao.valor_transacao_original = valor_original
            transacao.valor_transacao_final = valor_final
            transacao.pinbank_response = sanitize_for_json(resultado_transacao)
            transacao.ip_address_cliente = ip_address
            transacao.user_agent_cliente = user_agent
            transacao.processed_at = datetime.now()
            transacao.save()
            
            # Marcar token como usado
            token_obj.mark_as_used()
            
            # Tokenizar cartão se solicitado
            if dados_sessao.get('salvar_cartao', False):
                try:
                    # Buscar ou criar cliente
                    cliente, _ = CheckoutCliente.objects.get_or_create(
                        loja_id=token_obj.loja_id,
                        cpf=session.cpf,
                        defaults={
                            'nome': session.nome,
                            'email': token_obj.nome_completo,  # Usar email do token se disponível
                            'endereco': session.endereco,
                            'ativo': True
                            # celular removido - gerenciado por checkout_cliente_telefone (2FA)
                        }
                    )
                    
                    # Tokenizar cartão (interface unificada - funciona com Pinbank e Own)
                    resultado_token = transacoes_service.incluir_cartao_tokenizado({
                        'numero_cartao': numero_cartao,
                        'data_validade': session.data_validade,
                        'codigo_seguranca': dados_cartao['cvv'],
                        'nome_impresso': session.nome.upper(),
                        'cpf_comprador': int(session.cpf),
                        'bandeira': dados_cartao.get('bandeira', 'VISA')
                    })
                    
                    if resultado_token.get('sucesso'):
                        # Ambos gateways retornam 'cartao_id'
                        cartao_id = resultado_token.get('cartao_id')
                        
                        # Gerar máscara do cartão (primeiros 6 + últimos 4 dígitos)
                        cartao_mascarado = f"{numero_cartao[:6]}******{numero_cartao[-4:]}"
                        
                        # Salvar cartão tokenizado
                        CheckoutCartaoTokenizado.objects.create(
                            cliente=cliente,
                            id_token=cartao_id,
                            cartao_mascarado=cartao_mascarado,
                            bandeira=dados_cartao['bandeira'],
                            validade=session.data_validade,
                            valido=True
                        )
                        registrar_log('checkout.link_pagamento_web', 
                                    f"Cartão tokenizado com sucesso via {gateway_ativo} - Cliente: {cliente.id}, CartaoId: {cartao_id}")
                    else:
                        registrar_log('checkout.link_pagamento_web', f"Falha ao tokenizar cartão: {resultado_token.get('mensagem')}", nivel='WARNING')
                        
                except Exception as e:
                    registrar_log('checkout.link_pagamento_web', f"Erro ao tokenizar cartão: {str(e)}", nivel='ERROR')
            
            registrar_log('checkout.link_pagamento_web', f"Transação APROVADA - ID: {transacao.id}, NSU: {nsu}")
            
            return {
                'sucesso': True,
                'transacao_id': transacao.id,
                'nsu': nsu,
                'codigo_autorizacao': codigo_autorizacao,
                'mensagem': 'Pagamento aprovado com sucesso!',
                'valor_original': float(valor_original),
                'valor_final': float(valor_final)
            }
            
        except Exception as e:
            registrar_log('checkout.link_pagamento_web', f"Erro ao processar checkout link pagamento: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': f'Erro ao processar pagamento: {str(e)}',
                'tentativas_restantes': 0,
                'pode_tentar_novamente': False
            }
