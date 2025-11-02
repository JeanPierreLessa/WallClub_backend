"""
Serviço para autenticação de dois fatores (2FA) via OTP
Reutilizável para clientes, vendedores, admin e lojistas
"""
import random
import hashlib
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from wallclub_core.seguranca.models import AutenticacaoOTP
from wallclub_core.integracoes.whatsapp_service import WhatsAppService
from wallclub_core.utilitarios.log_control import registrar_log


class OTPService:
    """Service para gerenciar códigos OTP de autenticação 2FA"""

    # Configurações padrão
    TAMANHO_CODIGO = 6
    VALIDADE_MINUTOS = 5
    MAX_TENTATIVAS = 3
    MAX_CODIGOS_POR_HORA = 5
    DURACAO_BLOQUEIO_MINUTOS = 60

    @staticmethod
    def _gerar_codigo_aleatorio() -> str:
        """
        Gera código OTP aleatório de 6 dígitos

        Returns:
            str: Código de 6 dígitos
        """
        return ''.join([str(random.randint(0, 9)) for _ in range(OTPService.TAMANHO_CODIGO)])

    @staticmethod
    def _limpar_telefone(telefone: str) -> str:
        """
        Remove caracteres não numéricos do telefone

        Args:
            telefone: Telefone com formatação

        Returns:
            str: Apenas dígitos
        """
        return ''.join(filter(str.isdigit, telefone))

    @staticmethod
    def _verificar_rate_limit(user_id: int, tipo_usuario: str) -> tuple:
        """
        Verifica se usuário pode solicitar novo OTP (rate limiting)

        Args:
            user_id: ID do usuário
            tipo_usuario: Tipo (cliente, vendedor, admin, lojista)

        Returns:
            tuple: (pode_solicitar: bool, mensagem: str)
        """
        cache_key = f"otp_rate_limit_{tipo_usuario}_{user_id}"

        # Buscar contador no cache
        contador = cache.get(cache_key, 0)

        if contador >= OTPService.MAX_CODIGOS_POR_HORA:
            return False, f"Limite de {OTPService.MAX_CODIGOS_POR_HORA} códigos por hora atingido. Tente novamente em {OTPService.DURACAO_BLOQUEIO_MINUTOS} minutos."

        return True, ""

    @staticmethod
    def _incrementar_rate_limit(user_id: int, tipo_usuario: str):
        """
        Incrementa contador de rate limiting

        Args:
            user_id: ID do usuário
            tipo_usuario: Tipo (cliente, vendedor, admin, lojista)
        """
        cache_key = f"otp_rate_limit_{tipo_usuario}_{user_id}"
        contador = cache.get(cache_key, 0)
        cache.set(cache_key, contador + 1, OTPService.DURACAO_BLOQUEIO_MINUTOS * 60)

    @staticmethod
    def gerar_otp(user_id: int, tipo_usuario: str, telefone: str, ip_solicitacao: str = None) -> dict:
        """
        Gera novo código OTP para o usuário

        Args:
            user_id: ID do usuário
            tipo_usuario: Tipo (cliente, vendedor, admin, lojista)
            telefone: Telefone do usuário (com DDD)
            ip_solicitacao: IP que está solicitando

        Returns:
            dict: {
                'success': bool,
                'codigo': str (apenas em dev),
                'mensagem': str,
                'validade': datetime
            }
        """
        try:
            # Verificar rate limiting
            pode_solicitar, mensagem_erro = OTPService._verificar_rate_limit(user_id, tipo_usuario)
            if not pode_solicitar:
                registrar_log('comum.seguranca',
                    f"Rate limit atingido para {tipo_usuario} ID:{user_id}",
                    nivel='WARNING')
                return {
                    'success': False,
                    'mensagem': mensagem_erro
                }

            # Limpar telefone
            telefone_limpo = OTPService._limpar_telefone(telefone)

            # Gerar código
            codigo = OTPService._gerar_codigo_aleatorio()
            validade = datetime.now() + timedelta(minutes=OTPService.VALIDADE_MINUTOS)

            # Salvar no banco
            otp = AutenticacaoOTP.objects.create(
                codigo=codigo,
                user_id=user_id,
                tipo_usuario=tipo_usuario,
                telefone=telefone_limpo,
                validade=validade,
                tentativas=0,
                usado=False,
                ip_solicitacao=ip_solicitacao
            )

            # Incrementar rate limit
            OTPService._incrementar_rate_limit(user_id, tipo_usuario)

            registrar_log('comum.seguranca',
                f"OTP gerado para {tipo_usuario} ID:{user_id} - Tel: {telefone_limpo[-4:]} - Validade: {validade}",
                nivel='INFO')

            resultado = {
                'success': True,
                'mensagem': f'Código OTP enviado para {telefone_limpo[-4:]}. Válido por {OTPService.VALIDADE_MINUTOS} minutos.',
                'validade': validade,
                'otp_id': otp.id
            }

            # Em desenvolvimento, retornar código (NÃO fazer em produção)
            if settings.DEBUG:
                resultado['codigo'] = codigo

            return resultado

        except Exception as e:
            registrar_log('comum.seguranca',
                f"Erro ao gerar OTP para {tipo_usuario} ID:{user_id}: {str(e)}",
                nivel='ERROR')
            return {
                'success': False,
                'mensagem': 'Erro ao gerar código. Tente novamente.'
            }

    @staticmethod
    def validar_otp(user_id: int, tipo_usuario: str, codigo: str) -> dict:
        """
        Valida código OTP fornecido pelo usuário

        Args:
            user_id: ID do usuário
            tipo_usuario: Tipo (cliente, vendedor, admin, lojista)
            codigo: Código fornecido pelo usuário

        Returns:
            dict: {
                'success': bool,
                'mensagem': str
            }
        """
        try:
            # Buscar OTP mais recente não usado
            otp = AutenticacaoOTP.objects.filter(
                user_id=user_id,
                tipo_usuario=tipo_usuario,
                codigo=codigo,
                usado=False
            ).order_by('-criado_em').first()

            if not otp:
                registrar_log('comum.seguranca',
                    f"OTP não encontrado para {tipo_usuario} ID:{user_id} - Código: {codigo}",
                    nivel='WARNING')
                return {
                    'success': False,
                    'mensagem': 'Código inválido ou já utilizado.'
                }

            # Verificar tentativas
            if otp.tentativas >= OTPService.MAX_TENTATIVAS:
                registrar_log('comum.seguranca',
                    f"Máximo de tentativas atingido para {tipo_usuario} ID:{user_id}",
                    nivel='WARNING')
                return {
                    'success': False,
                    'mensagem': f'Máximo de {OTPService.MAX_TENTATIVAS} tentativas atingido. Solicite novo código.'
                }

            # Verificar validade
            if datetime.now() > otp.validade:
                registrar_log('comum.seguranca',
                    f"OTP expirado para {tipo_usuario} ID:{user_id}",
                    nivel='WARNING')
                return {
                    'success': False,
                    'mensagem': 'Código expirado. Solicite novo código.'
                }

            # Validar código
            if otp.codigo != codigo:
                # Incrementar tentativas
                otp.tentativas += 1
                otp.save()

                tentativas_restantes = OTPService.MAX_TENTATIVAS - otp.tentativas

                registrar_log('comum.seguranca',
                    f"Código incorreto para {tipo_usuario} ID:{user_id} - Tentativas restantes: {tentativas_restantes}",
                    nivel='WARNING')

                return {
                    'success': False,
                    'mensagem': f'Código incorreto. {tentativas_restantes} tentativa(s) restante(s).'
                }

            # Código válido! Marcar como usado
            otp.usado = True
            otp.usado_em = datetime.now()
            otp.save()

            registrar_log('comum.seguranca',
                f"✅ OTP validado com sucesso para {tipo_usuario} ID:{user_id}",
                nivel='INFO')

            return {
                'success': True,
                'mensagem': 'Código validado com sucesso!'
            }

        except Exception as e:
            registrar_log('comum.seguranca',
                f"Erro ao validar OTP para {tipo_usuario} ID:{user_id}: {str(e)}",
                nivel='ERROR')
            return {
                'success': False,
                'mensagem': 'Erro ao validar código. Tente novamente.'
            }

    @staticmethod
    def enviar_otp_whatsapp(canal_id: int, telefone: str, codigo: str, nome: str = None) -> dict:
        """
        Envia código OTP via WhatsApp

        Args:
            canal_id: ID do canal para buscar configuração WhatsApp
            telefone: Telefone com DDD (ex: 11999999999)
            codigo: Código OTP de 6 dígitos
            nome: Nome do usuário (opcional)

        Returns:
            dict: {
                'success': bool,
                'mensagem': str
            }
        """
        try:
            # Limpar telefone
            telefone_limpo = OTPService._limpar_telefone(telefone)

            # Enviar mensagem usando método padrão do WhatsAppService
            # Template 2fa_login_app:
            # - Body: 1 parâmetro (código)
            # - Button URL: 1 parâmetro (codigo para URL)
            parametros_corpo = [codigo]
            parametros_botao = [codigo]  # Parâmetro para botão URL

            sucesso = WhatsAppService.envia_whatsapp(
                numero_telefone=telefone_limpo,
                canal_id=canal_id,
                nome_template='2fa_login_app',
                idioma_template='pt_BR',
                parametros_corpo=parametros_corpo,
                parametros_botao=parametros_botao
            )

            if sucesso:
                registrar_log('comum.seguranca',
                    f"✅ OTP enviado via WhatsApp para {telefone_limpo[-4:]}",
                    nivel='INFO')
                return {
                    'success': True,
                    'mensagem': 'Código enviado via WhatsApp com sucesso.'
                }
            else:
                registrar_log('comum.seguranca',
                    f"❌ Erro ao enviar OTP via WhatsApp para {telefone_limpo[-4:]}",
                    nivel='ERROR')
                return {
                    'success': False,
                    'mensagem': 'Erro ao enviar WhatsApp. Tente novamente.'
                }

        except Exception as e:
            registrar_log('comum.seguranca',
                f"Erro ao enviar OTP via WhatsApp: {str(e)}",
                nivel='ERROR')
            return {
                'success': False,
                'mensagem': 'Erro ao enviar WhatsApp. Tente novamente.'
            }

    @staticmethod
    def enviar_otp_sms(telefone: str, codigo: str) -> dict:
        """
        Envia código OTP via SMS
        Placeholder - implementar integração com provedor SMS

        Args:
            telefone: Telefone com DDD
            codigo: Código OTP de 6 dígitos

        Returns:
            dict: {
                'success': bool,
                'mensagem': str
            }
        """
        # TODO: Implementar integração com provedor SMS (Twilio, AWS SNS, etc)
        registrar_log('comum.seguranca',
            f"SMS não implementado - Código {codigo} para {telefone[-4:]}",
            nivel='WARNING')

        return {
            'success': False,
            'mensagem': 'Envio via SMS não implementado ainda.'
        }

    @staticmethod
    def limpar_otp_expirados():
        """
        Remove códigos OTP expirados (cron job)
        Manter apenas últimos 7 dias
        """
        try:
            data_limite = datetime.now() - timedelta(days=7)

            deletados = AutenticacaoOTP.objects.filter(
                criado_em__lt=data_limite
            ).delete()

            registrar_log('comum.seguranca',
                f"🧹 Limpeza OTP: {deletados[0]} registros removidos",
                nivel='INFO')

            return deletados[0]

        except Exception as e:
            registrar_log('comum.seguranca',
                f"Erro ao limpar OTP expirados: {str(e)}",
                nivel='ERROR')
            return 0
