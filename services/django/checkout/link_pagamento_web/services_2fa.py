"""
Services para 2FA no Checkout Web
Cliente autogerencia telefone + camadas de proteção contra fraude
"""
from typing import Dict, Any, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
from django.conf import settings
from wallclub_core.utilitarios.log_control import registrar_log
from wallclub_core.seguranca.services_2fa import OTPService
from .models_2fa import (
    CheckoutClienteTelefone,
    CheckoutTransactionHelper,
    CheckoutRateLimitControl
)


class CheckoutSecurityService:
    """
    Serviço de segurança para checkout web
    Implementa 2FA + rate limiting + score de risco + limite progressivo
    """
    
    # Limites de rate limiting
    LIMITE_TELEFONE_DIA = 3  # 3 tentativas por telefone/dia
    LIMITE_CPF_DIA = 5       # 5 tentativas por CPF/dia
    LIMITE_IP_DIA = 10       # 10 tentativas por IP/dia
    
    # Score de risco threshold
    RISK_SCORE_THRESHOLD = 70  # Bloqueia se score > 70
    
    # Detecção de múltiplos cartões
    MAX_CARTOES_POR_TELEFONE_DIA = 2  # Max 2 cartões diferentes no mesmo telefone/dia
    
    @staticmethod
    def validar_telefone_cliente(cpf: str, telefone: str) -> Dict[str, Any]:
        """
        Valida e registra telefone do cliente
        
        Args:
            cpf: CPF do cliente (11 dígitos)
            telefone: Telefone com DDD
            
        Returns:
            dict: {
                'sucesso': bool,
                'mensagem': str,
                'telefone_obj': CheckoutClienteTelefone,
                'pode_alterar': bool
            }
        """
        try:
            # Limpar CPF e telefone
            cpf_limpo = ''.join(filter(str.isdigit, cpf))
            telefone_limpo = ''.join(filter(str.isdigit, telefone))
            
            # Validações básicas
            if len(cpf_limpo) != 11:
                return {
                    'sucesso': False,
                    'mensagem': 'CPF inválido',
                    'pode_alterar': False
                }
            
            if len(telefone_limpo) < 10 or len(telefone_limpo) > 11:
                return {
                    'sucesso': False,
                    'mensagem': 'Telefone inválido (use DDD + número)',
                    'pode_alterar': False
                }
            
            # Obter ou criar telefone
            telefone_obj, created = CheckoutClienteTelefone.obter_ou_criar_telefone(
                cpf=cpf_limpo,
                telefone=telefone_limpo
            )
            
            # Verificar se telefone foi desabilitado (ativo=0)
            if telefone_obj.ativo == 0:
                registrar_log(
                    'checkout.2fa',
                    f'Telefone desabilitado - CPF: {cpf_limpo[:3]}***{cpf_limpo[-2:]}',
                    nivel='WARNING'
                )
                return {
                    'sucesso': False,
                    'mensagem': 'Telefone desativado. Entre em contato com o suporte.',
                    'pode_alterar': False
                }
            
            # Status -1 (pendente) ou 1 (ativo) são permitidos
            
            # Log
            if created:
                registrar_log(
                    'checkout.2fa',
                    f'Novo telefone cadastrado - CPF: {cpf_limpo[:3]}***{cpf_limpo[-2:]}'
                )
            else:
                registrar_log(
                    'checkout.2fa',
                    f'Telefone existente validado - CPF: {cpf_limpo[:3]}***{cpf_limpo[-2:]}'
                )
            
            return {
                'sucesso': True,
                'mensagem': 'Telefone validado' if not created else 'Telefone cadastrado',
                'telefone_obj': telefone_obj,
                'pode_alterar': telefone_obj.pode_alterar_telefone(),
                'primeiro_uso': created
            }
            
        except Exception as e:
            registrar_log(
                'checkout.2fa',
                f'Erro ao validar telefone: {str(e)}',
                nivel='ERROR'
            )
            return {
                'sucesso': False,
                'mensagem': 'Erro ao validar telefone',
                'pode_alterar': False
            }
    
    @staticmethod
    def verificar_rate_limiting(cpf: str, telefone: str, ip_address: str) -> Dict[str, Any]:
        """
        Verifica rate limiting em múltiplas camadas
        
        Args:
            cpf: CPF do cliente
            telefone: Telefone do cliente
            ip_address: IP do cliente
            
        Returns:
            dict: {
                'bloqueado': bool,
                'motivo': str,
                'tentativas_restantes': dict
            }
        """
        cpf_limpo = ''.join(filter(str.isdigit, cpf))
        telefone_limpo = ''.join(filter(str.isdigit, telefone))
        
        # Verificar telefone
        bloqueado_tel, tentativas_tel = CheckoutRateLimitControl.verificar_e_incrementar(
            tipo='TELEFONE',
            identificador=telefone_limpo,
            limite=CheckoutSecurityService.LIMITE_TELEFONE_DIA
        )
        
        if bloqueado_tel:
            registrar_log(
                'checkout.2fa',
                f'Rate limit: Telefone bloqueado - {telefone_limpo[-4:]}',
                nivel='WARNING'
            )
            return {
                'bloqueado': True,
                'motivo': f'Telefone atingiu limite de {CheckoutSecurityService.LIMITE_TELEFONE_DIA} tentativas/dia',
                'tentativas_restantes': {'telefone': 0}
            }
        
        # Verificar CPF
        bloqueado_cpf, tentativas_cpf = CheckoutRateLimitControl.verificar_e_incrementar(
            tipo='CPF',
            identificador=cpf_limpo,
            limite=CheckoutSecurityService.LIMITE_CPF_DIA
        )
        
        if bloqueado_cpf:
            registrar_log(
                'checkout.2fa',
                f'Rate limit: CPF bloqueado - {cpf_limpo[:3]}***{cpf_limpo[-2:]}',
                nivel='WARNING'
            )
            return {
                'bloqueado': True,
                'motivo': f'CPF atingiu limite de {CheckoutSecurityService.LIMITE_CPF_DIA} tentativas/dia',
                'tentativas_restantes': {'cpf': 0}
            }
        
        # Verificar IP
        bloqueado_ip, tentativas_ip = CheckoutRateLimitControl.verificar_e_incrementar(
            tipo='IP',
            identificador=ip_address,
            limite=CheckoutSecurityService.LIMITE_IP_DIA
        )
        
        if bloqueado_ip:
            registrar_log(
                'checkout.2fa',
                f'Rate limit: IP bloqueado - {ip_address}',
                nivel='WARNING'
            )
            return {
                'bloqueado': True,
                'motivo': f'IP atingiu limite de {CheckoutSecurityService.LIMITE_IP_DIA} tentativas/dia',
                'tentativas_restantes': {'ip': 0}
            }
        
        return {
            'bloqueado': False,
            'motivo': '',
            'tentativas_restantes': {
                'telefone': tentativas_tel,
                'cpf': tentativas_cpf,
                'ip': tentativas_ip
            }
        }
    
    @staticmethod
    def verificar_limite_progressivo(cpf: str, valor: Decimal) -> Dict[str, Any]:
        """
        Verifica limite progressivo baseado no histórico
        
        Args:
            cpf: CPF do cliente
            valor: Valor da transação
            
        Returns:
            dict: {
                'aprovado': bool,
                'limite': float,
                'mensagem': str
            }
        """
        cpf_limpo = ''.join(filter(str.isdigit, cpf))
        
        # Calcular limite
        limite = CheckoutTransactionHelper.calcular_limite_progressivo(cpf_limpo)
        
        # Se sem limite (3+ transações), aprovar
        if limite == 0:
            return {
                'aprovado': True,
                'limite': 0,
                'mensagem': 'Sem limite (cliente confiável)'
            }
        
        # Verificar se valor está dentro do limite
        valor_float = float(valor)
        
        if valor_float > limite:
            registrar_log(
                'checkout.2fa',
                f'Limite progressivo: Valor R$ {valor_float:.2f} > Limite R$ {limite:.2f} - CPF: {cpf_limpo[:3]}***{cpf_limpo[-2:]}',
                nivel='WARNING'
            )
            return {
                'aprovado': False,
                'limite': limite,
                'mensagem': f'Valor máximo para esta transação: R$ {limite:.2f}'
            }
        
        return {
            'aprovado': True,
            'limite': limite,
            'mensagem': f'Dentro do limite (R$ {limite:.2f})'
        }
    
    @staticmethod
    def verificar_multiplos_cartoes(telefone: str) -> Dict[str, Any]:
        """
        Detecta múltiplos cartões no mesmo telefone (possível teste de cartão roubado)
        
        Args:
            telefone: Telefone do cliente
            
        Returns:
            dict: {
                'suspeito': bool,
                'quantidade_cartoes': int,
                'mensagem': str
            }
        """
        telefone_limpo = ''.join(filter(str.isdigit, telefone))
        
        # Verificar últimas 24h
        quantidade = CheckoutTransactionHelper.verificar_multiplos_cartoes(
            telefone=telefone_limpo,
            dias=1
        )
        
        # Se mais que o limite, bloquear
        if quantidade > CheckoutSecurityService.MAX_CARTOES_POR_TELEFONE_DIA:
            registrar_log(
                'checkout.2fa',
                f'Múltiplos cartões detectados: {quantidade} cartões no telefone {telefone_limpo[-4:]}',
                nivel='ERROR'
            )
            return {
                'suspeito': True,
                'quantidade_cartoes': quantidade,
                'mensagem': f'Detectados {quantidade} cartões diferentes. Possível fraude.'
            }
        
        return {
            'suspeito': False,
            'quantidade_cartoes': quantidade,
            'mensagem': 'Padrão normal'
        }
    
    @staticmethod
    def consultar_risk_engine(
        cpf: str,
        telefone: str,
        valor: Decimal,
        ip_address: str,
        device_fingerprint: str = None
    ) -> Dict[str, Any]:
        """
        Consulta Risk Engine para análise de fraude
        
        Args:
            cpf: CPF do cliente
            telefone: Telefone do cliente
            valor: Valor da transação
            ip_address: IP do cliente
            device_fingerprint: Fingerprint do dispositivo
            
        Returns:
            dict: {
                'score': int (0-100),
                'bloqueado': bool,
                'motivo': str,
                'detalhes': dict
            }
        """
        # Verificar se Risk Engine está habilitado
        if not getattr(settings, 'ANTIFRAUDE_ENABLED', False):
            registrar_log(
                'checkout.2fa',
                'Risk Engine desabilitado - pulando validação',
                nivel='WARNING'
            )
            return {
                'score': 0,
                'bloqueado': False,
                'motivo': 'Risk Engine desabilitado',
                'detalhes': {}
            }
        
        try:
            # Importar service do Risk Engine
            import requests
            
            riskengine_url = getattr(settings, 'RISK_ENGINE_URL', 'http://wallclub-riskengine:8004')
            
            # Preparar dados
            dados = {
                'cpf': cpf,
                'telefone': telefone,
                'valor': float(valor),
                'ip': ip_address,
                'device_fingerprint': device_fingerprint or '',
                'origem': 'checkout_web'
            }
            
            registrar_log(
                'checkout.2fa',
                f'Consultando Risk Engine: {riskengine_url}/antifraude/analisar/'
            )
            
            # Chamar Risk Engine (com timeout curto)
            response = requests.post(
                f'{riskengine_url}/antifraude/analisar/',
                json=dados,
                timeout=3
            )
            
            if response.status_code == 200:
                resultado = response.json()
                score = resultado.get('score', 0)
                bloqueado = score > CheckoutSecurityService.RISK_SCORE_THRESHOLD
                
                if bloqueado:
                    registrar_log(
                        'checkout.2fa',
                        f'Risk Engine BLOQUEOU: Score {score} > {CheckoutSecurityService.RISK_SCORE_THRESHOLD}',
                        nivel='ERROR'
                    )
                else:
                    registrar_log(
                        'checkout.2fa',
                        f'Risk Engine APROVOU: Score {score}'
                    )
                
                return {
                    'score': score,
                    'bloqueado': bloqueado,
                    'motivo': f'Score de risco: {score}' if bloqueado else '',
                    'detalhes': resultado
                }
            else:
                registrar_log(
                    'checkout.2fa',
                    f'Risk Engine erro HTTP {response.status_code}',
                    nivel='ERROR'
                )
                # Em caso de erro, aprovar (fail-open)
                return {
                    'score': 0,
                    'bloqueado': False,
                    'motivo': 'Risk Engine indisponível',
                    'detalhes': {}
                }
                
        except Exception as e:
            registrar_log(
                'checkout.2fa',
                f'Erro ao consultar Risk Engine: {str(e)}',
                nivel='ERROR'
            )
            # Em caso de erro, aprovar (fail-open)
            return {
                'score': 0,
                'bloqueado': False,
                'motivo': f'Erro: {str(e)}',
                'detalhes': {}
            }
    
    @staticmethod
    def enviar_otp_checkout(
        telefone: str,
        codigo_otp: str,
        valor: Decimal,
        ultimos_4_digitos: str = None
    ) -> bool:
        """
        Envia OTP via WhatsApp usando template autorizar_transacao_cartao
        
        Args:
            telefone: Telefone do cliente (com DDD)
            codigo_otp: Código OTP de 6 dígitos
            valor: Valor da transação
            ultimos_4_digitos: Últimos 4 dígitos do cartão (opcional)
            
        Returns:
            bool: True se enviado com sucesso
        """
        try:
            from wallclub_core.integracoes.whatsapp_service import WhatsAppService
            
            # Formatar valor CURRENCY conforme documentação Meta
            # amount_1000: valor multiplicado por 1000 (milésimos)
            # Exemplo: R$ 10.00 = 10000, R$ 123.45 = 123450
            valor_float = float(valor)
            amount_1000 = int(valor_float * 1000)
            
            valor_currency = {
                "type": "currency",
                "currency": {
                    "fallback_value": f"R${valor_float:.2f}",
                    "code": "BRL",
                    "amount_1000": amount_1000
                }
            }
            
            # Usar últimos 4 dígitos ou asteriscos se não fornecido
            cartao_final = ultimos_4_digitos if ultimos_4_digitos else '****'
            
            # Parâmetros do template: código, valor (currency), últimos_4_digitos
            parametros_corpo = [
                codigo_otp,
                valor_currency,
                cartao_final
            ]
            
            # Parâmetro do botão: código OTP (para copiar)
            parametros_botao = [codigo_otp]
            
            # Canal padrão (ajustar conforme necessário)
            # TODO: Buscar canal correto baseado na loja do checkout
            canal_id = 1
            
            # Limpar telefone
            telefone_limpo = ''.join(filter(str.isdigit, telefone))
            
            # Enviar via WhatsApp
            sucesso = WhatsAppService.envia_whatsapp(
                numero_telefone=telefone_limpo,
                canal_id=canal_id,
                nome_template='autorizar_transacao_cartao',
                idioma_template='pt_BR',
                parametros_corpo=parametros_corpo,
                parametros_botao=parametros_botao
            )
            
            if sucesso:
                registrar_log(
                    'checkout.2fa',
                    f'OTP enviado via WhatsApp - Telefone: {telefone_limpo[-4:]}'
                )
            else:
                registrar_log(
                    'checkout.2fa',
                    f'Erro ao enviar OTP via WhatsApp - Telefone: {telefone_limpo[-4:]}',
                    nivel='ERROR'
                )
            
            return sucesso
            
        except Exception as e:
            registrar_log(
                'checkout.2fa',
                f'Erro ao enviar OTP via WhatsApp: {str(e)}',
                nivel='ERROR'
            )
            return False
    
    @staticmethod
    def processar_checkout_com_2fa(
        token: str,
        cpf: str,
        telefone: str,
        valor: Decimal,
        ip_address: str,
        device_fingerprint: str = None,
        ultimos_4_digitos_cartao: str = None
    ) -> Dict[str, Any]:
        """
        Fluxo completo de segurança antes de processar checkout
        
        Args:
            token: Token do checkout
            cpf: CPF do cliente
            telefone: Telefone do cliente
            valor: Valor da transação
            ip_address: IP do cliente
            device_fingerprint: Fingerprint do dispositivo
            
        Returns:
            dict: {
                'aprovado': bool,
                'motivo_bloqueio': str,
                'otp_enviado': bool,
                'telefone_obj': CheckoutClienteTelefone,
                'detalhes': dict
            }
        """
        detalhes = {}
        
        # 1. Validar telefone
        resultado_telefone = CheckoutSecurityService.validar_telefone_cliente(cpf, telefone)
        if not resultado_telefone['sucesso']:
            return {
                'aprovado': False,
                'motivo_bloqueio': resultado_telefone['mensagem'],
                'otp_enviado': False,
                'detalhes': {'etapa': 'validacao_telefone'}
            }
        
        telefone_obj = resultado_telefone['telefone_obj']
        detalhes['telefone_validado'] = True
        
        # 2. Rate limiting
        resultado_rate = CheckoutSecurityService.verificar_rate_limiting(cpf, telefone, ip_address)
        if resultado_rate['bloqueado']:
            return {
                'aprovado': False,
                'motivo_bloqueio': resultado_rate['motivo'],
                'otp_enviado': False,
                'detalhes': {
                    'etapa': 'rate_limiting',
                    'tentativas_restantes': resultado_rate['tentativas_restantes']
                }
            }
        
        detalhes['rate_limit_ok'] = True
        detalhes['tentativas_restantes'] = resultado_rate['tentativas_restantes']
        
        # 3. Limite progressivo
        resultado_limite = CheckoutSecurityService.verificar_limite_progressivo(cpf, valor)
        if not resultado_limite['aprovado']:
            return {
                'aprovado': False,
                'motivo_bloqueio': resultado_limite['mensagem'],
                'otp_enviado': False,
                'detalhes': {
                    'etapa': 'limite_progressivo',
                    'limite': resultado_limite['limite']
                }
            }
        
        detalhes['limite_progressivo_ok'] = True
        detalhes['limite'] = resultado_limite['limite']
        
        # 4. Múltiplos cartões
        resultado_cartoes = CheckoutSecurityService.verificar_multiplos_cartoes(telefone)
        if resultado_cartoes['suspeito']:
            return {
                'aprovado': False,
                'motivo_bloqueio': resultado_cartoes['mensagem'],
                'otp_enviado': False,
                'detalhes': {
                    'etapa': 'multiplos_cartoes',
                    'quantidade': resultado_cartoes['quantidade_cartoes']
                }
            }
        
        detalhes['multiplos_cartoes_ok'] = True
        
        # 5. Risk Engine
        resultado_risk = CheckoutSecurityService.consultar_risk_engine(
            cpf=cpf,
            telefone=telefone,
            valor=valor,
            ip_address=ip_address,
            device_fingerprint=device_fingerprint
        )
        
        if resultado_risk['bloqueado']:
            return {
                'aprovado': False,
                'motivo_bloqueio': resultado_risk['motivo'],
                'otp_enviado': False,
                'detalhes': {
                    'etapa': 'risk_engine',
                    'score': resultado_risk['score']
                }
            }
        
        detalhes['risk_engine_ok'] = True
        detalhes['risk_score'] = resultado_risk['score']
        
        # 6. Gerar e enviar OTP
        telefone_limpo = ''.join(filter(str.isdigit, telefone))
        resultado_otp = OTPService.gerar_otp(
            user_id=telefone_obj.id,
            tipo_usuario='cliente',
            telefone=telefone_limpo,
            ip_solicitacao=ip_address
        )
        
        if not resultado_otp['success']:
            return {
                'aprovado': False,
                'motivo_bloqueio': resultado_otp['mensagem'],
                'otp_enviado': False,
                'detalhes': {
                    'etapa': 'geracao_otp'
                }
            }
        
        # Enviar OTP via WhatsApp
        otp_enviado_whatsapp = CheckoutSecurityService.enviar_otp_checkout(
            telefone=telefone_limpo,
            codigo_otp=resultado_otp['codigo'],
            valor=valor,
            ultimos_4_digitos=ultimos_4_digitos_cartao
        )
        
        if not otp_enviado_whatsapp:
            registrar_log(
                'checkout.2fa',
                f'Falha ao enviar OTP via WhatsApp - Token: {token[:8]}...',
                nivel='WARNING'
            )
            # Continua mesmo se WhatsApp falhar (fail-open)
        
        registrar_log(
            'checkout.2fa',
            f'✅ Validações completas - OTP gerado - Token: {token[:8]}...'
        )
        
        return {
            'aprovado': True,
            'motivo_bloqueio': '',
            'otp_enviado': True,
            'telefone_obj': telefone_obj,
            'otp_validade': resultado_otp['validade'],
            'detalhes': detalhes
        }
    
    @staticmethod
    def validar_otp_e_processar(
        cpf: str,
        telefone: str,
        codigo_otp: str,
        token: str,
        valor: Decimal,
        nsu: str = None,
        status: str = 'APROVADA',
        ip_address: str = '',
        device_fingerprint: str = None
    ) -> Dict[str, Any]:
        """
        Valida OTP e registra transação no histórico
        
        Args:
            cpf: CPF do cliente
            telefone: Telefone do cliente
            codigo_otp: Código OTP fornecido
            token: Token do checkout
            valor: Valor da transação
            nsu: NSU do Pinbank (se aprovada)
            status: Status da transação
            ip_address: IP do cliente
            device_fingerprint: Fingerprint do dispositivo
            
        Returns:
            dict: {
                'valido': bool,
                'mensagem': str,
                'primeira_transacao': bool
            }
        """
        # Obter telefone cadastrado
        cpf_limpo = ''.join(filter(str.isdigit, cpf))
        telefone_limpo = ''.join(filter(str.isdigit, telefone))
        
        try:
            # Buscar telefone pendente (ativo=-1) ou ativo (ativo=1)
            # NÃO buscar desabilitados (ativo=0)
            telefone_obj = CheckoutClienteTelefone.objects.get(
                cpf=cpf_limpo,
                telefone=telefone_limpo,
                ativo__in=[-1, 1]  # Aceita pendente (-1) ou ativo (1)
            )
            
            registrar_log(
                'checkout.2fa',
                f'Telefone encontrado - CPF: {cpf_limpo[:3]}***{cpf_limpo[-2:]} - Status: {telefone_obj.ativo}',
                nivel='INFO'
            )
        except CheckoutClienteTelefone.DoesNotExist:
            registrar_log(
                'checkout.2fa',
                f'Telefone NÃO encontrado - CPF: {cpf_limpo[:3]}***{cpf_limpo[-2:]} - Tel: {telefone_limpo[-4:]}',
                nivel='ERROR'
            )
            return {
                'valido': False,
                'mensagem': 'Telefone não encontrado',
                'primeira_transacao': False
            }
        
        # Validar OTP
        resultado = OTPService.validar_otp(
            user_id=telefone_obj.id,
            tipo_usuario='cliente',
            codigo=codigo_otp
        )
        
        if not resultado['success']:
            registrar_log(
                'checkout.2fa',
                f'OTP inválido - CPF: {cpf_limpo[:3]}***{cpf_limpo[-2:]}',
                nivel='WARNING'
            )
            return {
                'valido': False,
                'mensagem': resultado['mensagem'],
                'primeira_transacao': False
            }
        
        # Atualizar campos de segurança na transação existente
        # (Transação já foi criada pelo LinkPagamentoService)
        from checkout.models import CheckoutTransaction
        
        try:
            transaction = CheckoutTransaction.objects.filter(token=token).latest('created_at')
            if device_fingerprint and not transaction.device_fingerprint:
                transaction.device_fingerprint = device_fingerprint
                transaction.save(update_fields=['device_fingerprint'])
        except CheckoutTransaction.DoesNotExist:
            registrar_log(
                'checkout.2fa',
                f'Transação não encontrada para atualizar device_fingerprint - Token: {token[:8]}...',
                nivel='WARNING'
            )
        
        # Ativar telefone após primeira validação 2FA
        if telefone_obj.ativo == -1:  # Se estava pendente
            telefone_obj.ativar_apos_2fa()
            registrar_log(
                'checkout.2fa',
                f'✅ Telefone ATIVADO após confirmação 2FA - CPF: {cpf_limpo[:3]}***{cpf_limpo[-2:]}'
            )
        
        # Se primeira transação aprovada, marcar telefone como imutável
        primeira_transacao = False
        if status == 'APROVADA' and not telefone_obj.primeira_transacao_aprovada_em:
            telefone_obj.marcar_primeira_transacao_aprovada()
            primeira_transacao = True
            registrar_log(
                'checkout.2fa',
                f'✅ Primeira transação aprovada - Telefone agora IMUTÁVEL - CPF: {cpf_limpo[:3]}***{cpf_limpo[-2:]}'
            )
        
        return {
            'valido': True,
            'mensagem': 'OTP válido',
            'primeira_transacao': primeira_transacao
        }
