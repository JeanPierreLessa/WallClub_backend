"""
Service para autenticação 2FA no login do App Móvel.
Implementa segunda camada de segurança com OTP e device management.

Gatilhos obrigatórios para 2FA:
- Login de novo dispositivo (device não reconhecido)
- Primeira transação do dia
- Transação > R$ 100,00
- Alteração de celular/email/senha
- Transferências (qualquer valor)
- Dispositivo confiável expirado (>30 dias)
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from django.core.cache import cache
from django.db import connection
from wallclub_core.utilitarios.log_control import registrar_log


class ClienteAuth2FAService:
    """Service para gerenciar 2FA no login do app móvel"""

    # Período de validade de dispositivo confiável (30 dias)
    DEVICE_TRUST_DIAS = 30

    @staticmethod
    def verificar_necessidade_2fa(
        auth_token: str,
        device_fingerprint: str,
        contexto: str = 'login'
    ) -> Dict[str, Any]:
        """
        Verifica se 2FA é necessário baseado no dispositivo e contexto.
        Usa auth_token para segurança (cliente_id nunca exposto).

        Args:
            auth_token: Token temporário do login (tipo auth_pending)
            device_fingerprint: Fingerprint do dispositivo
            contexto: Contexto da validação (login, transacao, alteracao_dados)

        Returns:
            dict: {
                'necessario': bool,
                'motivo': str,
                'dispositivo_confiavel': bool,
                'token': str (se não precisar 2FA)
            }
        """
        try:
            # Validar auth_token e extrair cliente_id
            from apps.cliente.jwt_cliente import validate_auth_pending_token

            payload = validate_auth_pending_token(auth_token)
            if not payload:
                return {
                    'necessario': True,
                    'motivo': 'auth_token_invalido',
                    'dispositivo_confiavel': False,
                    'mensagem': 'Token de autenticação inválido ou expirado'
                }

            cliente_id = payload.get('cliente_id')
            if not cliente_id:
                return {
                    'necessario': True,
                    'motivo': 'cliente_id_ausente',
                    'dispositivo_confiavel': False,
                    'mensagem': 'Token inválido'
                }

            registrar_log('apps.cliente',
                f"Verificando 2FA: cliente={cliente_id}, contexto={contexto}")

            # 0. Verificar BYPASS 2FA (clientes de teste Apple/Google)
            from apps.cliente.models import Cliente
            try:
                cliente_bypass = Cliente.objects.only('bypass_2fa', 'nome').get(id=cliente_id)
                if getattr(cliente_bypass, 'bypass_2fa', False):
                    # Cliente com bypass: gerar JWT diretamente
                    from apps.cliente.jwt_cliente import generate_cliente_jwt_token
                    
                    cliente_completo = Cliente.objects.get(id=cliente_id)
                    
                    class MockRequestBypass:
                        def __init__(self):
                            self.META = {
                                'REMOTE_ADDR': '0.0.0.0',
                                'HTTP_USER_AGENT': 'Apple Review Test Account'
                            }
                    
                    mock_request = MockRequestBypass()
                    jwt_data = generate_cliente_jwt_token(cliente_completo, request=mock_request)
                    
                    registrar_log('apps.cliente',
                        f"⚠️ BYPASS 2FA ATIVADO: cliente={cliente_id} ({cliente_bypass.nome})", nivel='WARNING')
                    
                    return {
                        'necessario': False,
                        'motivo': 'bypass_2fa_teste',
                        'dispositivo_confiavel': True,
                        'mensagem': 'Login direto - conta de teste',
                        'token': jwt_data['token'],
                        'refresh_token': jwt_data['refresh_token'],
                        'expires_at': jwt_data['expires_at'].isoformat()
                    }
            except Cliente.DoesNotExist:
                pass  # Cliente não existe, continua fluxo normal
            except Exception as e:
                registrar_log('apps.cliente',
                    f"Erro ao verificar bypass_2fa: {str(e)}", nivel='ERROR')
                # Continua fluxo normal em caso de erro

            # 1. Verificar rate limit ANTES de exigir 2FA
            from wallclub_core.seguranca.services_2fa import OTPService
            from django.core.cache import cache
            
            cache_key = f"otp_rate_limit_cliente_{cliente_id}"
            contador = cache.get(cache_key, 0)
            
            if contador >= OTPService.MAX_CODIGOS_POR_HORA:
                registrar_log('apps.cliente',
                    f"Rate limit atingido para cliente ID:{cliente_id}",
                    nivel='WARNING')
                return {
                    'bloqueado_temporariamente': True,
                    'motivo': 'rate_limit',
                    'mensagem': f'Muitas tentativas. Aguarde {OTPService.DURACAO_BLOQUEIO_MINUTOS} minutos.',
                    'necessario': False,
                    'dispositivo_confiavel': False
                }

            # 1. Verificar se dispositivo é confiável e válido
            from wallclub_core.seguranca.services_device import DeviceManagementService

            # validar_dispositivo retorna tupla (bool, dispositivo, mensagem)
            confiavel, dispositivo, mensagem = DeviceManagementService.validar_dispositivo(
                user_id=cliente_id,
                tipo_usuario='cliente',
                fingerprint=device_fingerprint
            )

            # Se dispositivo não existe: registrar automaticamente (facilita onboarding)
            if dispositivo is None:
                registrar_log('apps.cliente',
                    f"Novo dispositivo detectado - registrando automaticamente: cliente={cliente_id}")
                return {
                    'necessario': True,
                    'motivo': 'novo_dispositivo',
                    'dispositivo_confiavel': False,
                    'mensagem': 'Primeiro acesso neste dispositivo - validação necessária'
                }

            # Device expirado (confiavel_ate vencido)
            if not confiavel:
                registrar_log('apps.cliente',
                    f"2FA necessário: dispositivo expirado - cliente={cliente_id}")
                return {
                    'necessario': True,
                    'motivo': 'dispositivo_expirado',
                    'dispositivo_confiavel': False,
                    'mensagem': 'Dispositivo expirado - revalidação necessária'
                }

            # 2. Verificar se celular está expirado (90 dias)
            from apps.cliente.services_revalidacao_celular import RevalidacaoCelularService
            validade_celular = RevalidacaoCelularService.verificar_validade_celular(cliente_id)

            if validade_celular['precisa_revalidar']:
                dias_expirado = abs(validade_celular['dias_restantes'])
                registrar_log('apps.cliente',
                    f"2FA necessário: celular expirado - cliente={cliente_id}, dias_expirado={dias_expirado}")
                return {
                    'necessario': True,
                    'motivo': 'celular_expirado',
                    'dispositivo_confiavel': confiavel,
                    'mensagem': 'Seu celular precisa ser revalidado para continuar usando o app',
                    'dias_expirado': dias_expirado
                }

            # 3. Verificar contexto específico
            if contexto == 'alteracao_dados':
                # Sempre exigir 2FA para alteração de dados sensíveis
                return {
                    'necessario': True,
                    'motivo': 'alteracao_dados_sensivel',
                    'dispositivo_confiavel': True,
                    'mensagem': 'Alteração de dados requer 2FA'
                }

            if contexto == 'transferencia':
                # Sempre exigir 2FA para transferências
                return {
                    'necessario': True,
                    'motivo': 'transferencia',
                    'dispositivo_confiavel': True,
                    'mensagem': 'Transferência requer 2FA'
                }

            if contexto == 'primeira_transacao_dia':
                # Exigir 2FA na primeira transação do dia
                return {
                    'necessario': True,
                    'motivo': 'primeira_transacao_dia',
                    'dispositivo_confiavel': True,
                    'mensagem': 'Primeira transação do dia requer 2FA'
                }

            if contexto == 'transacao_alto_valor':
                # Exigir 2FA para transações >R$ 100
                return {
                    'necessario': True,
                    'motivo': 'transacao_alto_valor',
                    'dispositivo_confiavel': True,
                    'mensagem': 'Transação de alto valor requer 2FA'
                }

            # 4. Dispositivo confiável e contexto normal: retornar JWT
            # Registrar/renovar device automaticamente
            if dispositivo is None:
                # Nunca deveria chegar aqui (foi validado acima), mas por segurança
                dispositivo_criado, criado, mensagem_device = DeviceManagementService.registrar_dispositivo(
                    user_id=cliente_id,
                    tipo_usuario='cliente',
                    dados_dispositivo={'device_fingerprint': device_fingerprint},
                    ip_registro='0.0.0.0',
                    marcar_confiavel=True
                )

            # Gerar JWT
            from apps.cliente.models import Cliente
            from apps.cliente.jwt_cliente import generate_cliente_jwt_token

            try:
                cliente = Cliente.objects.get(id=cliente_id)

                # Criar objeto mock de request para passar metadados
                class MockRequest:
                    def __init__(self):
                        self.META = {
                            'REMOTE_ADDR': '0.0.0.0',
                            'HTTP_USER_AGENT': 'WallClub Mobile App - Device Confiavel'
                        }

                mock_request = MockRequest()
                jwt_data = generate_cliente_jwt_token(cliente, request=mock_request)

                registrar_log('apps.cliente',
                    f"JWT gerado via 2FA: cliente={cliente_id}, device confiável")

                return {
                    'necessario': False,
                    'motivo': 'dispositivo_confiavel_valido',
                    'dispositivo_confiavel': True,
                    'mensagem': 'Dispositivo confiável válido',
                    'token': jwt_data['token'],
                    'refresh_token': jwt_data['refresh_token'],
                    'expires_at': jwt_data['expires_at'].isoformat()
                }
            except Exception as e:
                registrar_log('apps.cliente',
                    f"Erro ao gerar JWT em verificar_necessidade: {str(e)}", nivel='ERROR')
                # Fallback: exigir 2FA se não conseguir gerar JWT
                return {
                    'necessario': True,
                    'motivo': 'erro_gerar_jwt',
                    'dispositivo_confiavel': True,
                    'mensagem': 'Erro ao gerar token - validação 2FA necessária'
                }

        except Exception as e:
            registrar_log('apps.cliente',
                f"Erro ao verificar necessidade 2FA: {str(e)}", nivel='ERROR')
            # Fail-secure: exigir 2FA em caso de erro
            return {
                'necessario': True,
                'motivo': 'erro_verificacao',
                'dispositivo_confiavel': False,
                'mensagem': 'Erro ao verificar dispositivo - 2FA obrigatório'
            }

    @staticmethod
    def solicitar_2fa_login(
        auth_token: str,
        device_fingerprint: str,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Solicita código 2FA para login do app.
        Usa auth_token para segurança (cliente_id nunca exposto).

        Args:
            auth_token: Token temporário do login
            device_fingerprint: Fingerprint do dispositivo
            ip_address: IP do cliente

        Returns:
            dict: Resultado da solicitação
        """
        try:
            # Validar auth_token e extrair dados
            from apps.cliente.jwt_cliente import validate_auth_pending_token

            payload = validate_auth_pending_token(auth_token)
            if not payload:
                return {
                    'sucesso': False,
                    'mensagem': 'Token de autenticação inválido ou expirado'
                }

            cliente_id = payload.get('cliente_id')
            canal_id = payload.get('canal_id')

            if not cliente_id or not canal_id:
                return {
                    'sucesso': False,
                    'mensagem': 'Token inválido'
                }

            # Rate limiting: cooldown de 60s entre solicitações
            from wallclub_core.seguranca.rate_limiter_2fa import Login2FARateLimiter

            allowed_cooldown, retry_after = Login2FARateLimiter.check_2fa_cooldown(cliente_id)
            if not allowed_cooldown:
                return {
                    'sucesso': False,
                    'mensagem': f'Aguarde {retry_after} segundos antes de solicitar novo código',
                    'retry_after': retry_after
                }

            # Rate limiting: max 3 solicitações por sessão
            allowed_requests, remaining = Login2FARateLimiter.check_2fa_requests_limit(cliente_id)
            if not allowed_requests:
                return {
                    'sucesso': False,
                    'mensagem': 'Limite de solicitações atingido. Tente fazer login novamente.',
                    'codigo': 'LIMITE_ATINGIDO'
                }

            # Buscar cliente
            from apps.cliente.models import Cliente
            try:
                cliente = Cliente.objects.only('celular', 'cpf', 'nome').get(
                    id=cliente_id, is_active=True
                )
            except Cliente.DoesNotExist:
                return {
                    'sucesso': False,
                    'mensagem': 'Cliente não encontrado'
                }

            if not cliente.celular:
                return {
                    'sucesso': False,
                    'mensagem': 'Cliente não possui celular cadastrado'
                }

            # Gerar OTP
            from wallclub_core.seguranca.services_2fa import OTPService

            resultado_otp = OTPService.gerar_otp(
                user_id=cliente_id,
                tipo_usuario='cliente',
                telefone=cliente.celular
            )

            if not resultado_otp['success']:
                return resultado_otp

            # Enviar OTP via WhatsApp
            from wallclub_core.integracoes.whatsapp_service import WhatsAppService
            from wallclub_core.integracoes.messages_template_service import MessagesTemplateService

            # Buscar código do banco (resultado_otp['codigo'] só existe em DEBUG)
            from wallclub_core.seguranca.models import AutenticacaoOTP
            otp = AutenticacaoOTP.objects.get(id=resultado_otp['otp_id'])

            template = MessagesTemplateService.preparar_whatsapp(
                canal_id=canal_id,
                id_template='2fa_login_app',
                codigo=otp.codigo,
                url_ref=otp.codigo  # Mesmo padrão do template senha_acesso
            )

            if template:
                whatsapp_enviado = WhatsAppService.envia_whatsapp(
                    numero_telefone=cliente.celular,
                    canal_id=canal_id,
                    nome_template=template['nome_template'],
                    idioma_template=template['idioma'],
                    parametros_corpo=template['parametros_corpo'],
                    parametros_botao=template.get('parametros_botao')
                )
            else:
                # Fallback: mensagem simples
                whatsapp_enviado = WhatsAppService.envia_whatsapp_texto_simples(
                    numero_telefone=cliente.celular,
                    canal_id=canal_id,
                    mensagem=f"🔐 *Código de Segurança*\n\n{cliente.nome}, seu código de acesso: {otp.codigo}\n\nVálido por 5 minutos."
                )

            # Registrar solicitação
            device_log = device_fingerprint[:20] if device_fingerprint else 'N/A'
            registrar_log('apps.cliente',
                f"2FA solicitado para login: cliente={cliente_id}, device={device_log}, ip={ip_address}")

            return {
                'sucesso': True,
                'mensagem': 'Código 2FA enviado',
                'whatsapp_enviado': whatsapp_enviado
            }

        except Exception as e:
            registrar_log('apps.cliente',
                f"Erro ao solicitar 2FA: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Erro ao solicitar código 2FA'
            }

    @staticmethod
    def validar_2fa_login(
        auth_token: str,
        codigo_otp: str,
        device_fingerprint: str,
        marcar_confiavel: bool = False,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        nome_dispositivo: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Valida código 2FA e registra dispositivo confiável.
        Retorna JWT final após validação bem-sucedida.

        Args:
            auth_token: Token temporário do login
            codigo_otp: Código OTP
            device_fingerprint: Fingerprint do dispositivo
            marcar_confiavel: Se deve marcar dispositivo como confiável
            ip_address: IP do cliente
            user_agent: User agent do navegador/app
            nome_dispositivo: Nome personalizado do dispositivo (opcional)

        Returns:
            dict: {sucesso, mensagem, token, refresh_token, expires_at}
        """
        try:
            # Validar auth_token e extrair cliente_id
            from apps.cliente.jwt_cliente import validate_auth_pending_token

            payload = validate_auth_pending_token(auth_token)
            if not payload:
                return {
                    'sucesso': False,
                    'mensagem': 'Token de autenticação inválido ou expirado'
                }

            cliente_id = payload.get('cliente_id')
            if not cliente_id:
                return {
                    'sucesso': False,
                    'mensagem': 'Token inválido'
                }

            # Rate limiting: max 5 validações por hora
            from wallclub_core.seguranca.rate_limiter_2fa import Login2FARateLimiter

            allowed_validations, remaining_validations = Login2FARateLimiter.check_2fa_validations(cliente_id)
            if not allowed_validations:
                return {
                    'sucesso': False,
                    'mensagem': 'Muitas tentativas de validação. Tente novamente em 1 hora.'
                }

            # Validar OTP
            from wallclub_core.seguranca.services_2fa import OTPService

            resultado_validacao = OTPService.validar_otp(
                user_id=cliente_id,
                tipo_usuario='cliente',
                codigo=codigo_otp
            )

            if not resultado_validacao['success']:
                registrar_log('apps.cliente',
                    f"2FA falhou: cliente={cliente_id}, codigo_invalido")
                return {
                    'sucesso': False,
                    'mensagem': resultado_validacao.get('mensagem', 'Código inválido')
                }

            # Atualizar celular_validado_em (revalida automaticamente ao validar OTP)
            from apps.cliente.models import Cliente
            try:
                Cliente.objects.filter(id=cliente_id).update(celular_validado_em=datetime.now())
                registrar_log('apps.cliente',
                    f"Celular revalidado automaticamente: cliente={cliente_id}", nivel='INFO')
            except Exception as e:
                # Não falhar se atualização falhar
                registrar_log('apps.cliente',
                    f"Erro ao atualizar celular_validado_em: {str(e)}", nivel='WARNING')

            # Registrar ou atualizar dispositivo
            from wallclub_core.seguranca.services_device import DeviceManagementService

            dispositivo = None
            criado = False
            mensagem_device = ''

            if marcar_confiavel:
                # Verificar limite de dispositivos (cliente: máximo 2)
                dispositivos = DeviceManagementService.listar_dispositivos(
                    user_id=cliente_id,
                    tipo_usuario='cliente'
                )

                # Verificar se o dispositivo já existe (comparar fingerprint COMPLETO)
                # CRÍTICO: Não comparar apenas primeiros 16 chars (pode gerar falso negativo)
                dispositivo_existente = None
                for d in dispositivos:
                    # Buscar fingerprint completo no banco
                    from wallclub_core.seguranca.models import DispositivoConfiavel
                    device_completo = DispositivoConfiavel.objects.filter(
                        id=d['id'],
                        device_fingerprint=device_fingerprint,
                        ativo=True
                    ).first()
                    
                    if device_completo:
                        dispositivo_existente = d
                        registrar_log('apps.cliente',
                            f"✅ Dispositivo já existe (fingerprint completo): {device_fingerprint[:8]}...", nivel='DEBUG')
                        break

                # Se já existe, pode renovar (não conta no limite)
                if not dispositivo_existente and len(dispositivos) >= 2:
                    # Cliente já tem 2 dispositivos e este é um novo: não permitir
                    registrar_log('apps.cliente',
                        f"Tentativa de adicionar 3º dispositivo bloqueada: cliente={cliente_id}")
                    return {
                        'sucesso': False,
                        'mensagem': 'Você já possui 2 dispositivos cadastrados. Remova um deles antes de adicionar outro.',
                        'codigo': 'LIMITE_DISPOSITIVOS'
                    }

                # Registrar dispositivo como confiável
                dados_dispositivo = {
                    'device_fingerprint': device_fingerprint,
                    'user_agent': user_agent or ''
                }
                
                # Adicionar nome_dispositivo se fornecido
                if nome_dispositivo:
                    dados_dispositivo['nome_dispositivo'] = nome_dispositivo
                
                dispositivo, criado, mensagem_device = DeviceManagementService.registrar_dispositivo(
                    user_id=cliente_id,
                    tipo_usuario='cliente',
                    dados_dispositivo=dados_dispositivo,
                    ip_registro=ip_address or '0.0.0.0',
                    marcar_confiavel=True
                )

                if dispositivo is None:
                    registrar_log('apps.cliente',
                        f"Erro ao registrar dispositivo: {mensagem_device}",
                        nivel='ERROR')

            # Notificar novo dispositivo (se for novo e confiável)
            if marcar_confiavel and criado:
                from wallclub_core.integracoes.notificacao_seguranca_service import NotificacaoSegurancaService
                from apps.cliente.models import Cliente

                try:
                    cliente = Cliente.objects.only('canal_id', 'celular', 'nome').get(id=cliente_id)
                    NotificacaoSegurancaService.notificar_login_novo_dispositivo(
                        cliente_id=cliente_id,
                        canal_id=cliente.canal_id,
                        celular=cliente.celular,
                        ip_address=ip_address or '0.0.0.0',
                        nome=cliente.nome,
                        device_name=user_agent or 'Dispositivo desconhecido'
                    )
                except Exception as e:
                    # Não falhar se notificação falhar
                    registrar_log('apps.cliente',
                        f"Erro ao notificar novo dispositivo: {str(e)}", nivel='ERROR')

            # Gerar JWT após validação 2FA
            from apps.cliente.models import Cliente
            from apps.cliente.jwt_cliente import generate_cliente_jwt_token

            try:
                cliente = Cliente.objects.get(id=cliente_id)

                # Criar objeto mock de request para passar metadados
                class MockRequest:
                    def __init__(self, ip, ua):
                        self.META = {
                            'REMOTE_ADDR': ip or '0.0.0.0',
                            'HTTP_USER_AGENT': ua or 'WallClub Mobile App'
                        }

                mock_request = MockRequest(ip_address, user_agent)
                jwt_data = generate_cliente_jwt_token(cliente, request=mock_request)

                registrar_log('apps.cliente',
                    f"2FA validado + JWT gerado: cliente={cliente_id}, confiavel={marcar_confiavel}")

                # Resetar contadores de rate limit após sucesso
                Login2FARateLimiter.reset_2fa_session(cliente_id)

                return {
                    'sucesso': True,
                    'mensagem': '2FA validado com sucesso',
                    'dispositivo_registrado': dispositivo is not None,
                    'token': jwt_data['token'],
                    'refresh_token': jwt_data['refresh_token'],
                    'expires_at': jwt_data['expires_at'].isoformat()
                }
            except Exception as e:
                registrar_log('apps.cliente',
                    f"Erro ao gerar JWT após 2FA: {str(e)}", nivel='ERROR')
                return {
                    'sucesso': False,
                    'mensagem': 'Erro ao gerar token de acesso'
                }

        except Exception as e:
            registrar_log('apps.cliente',
                f"Erro ao validar 2FA: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Erro ao validar 2FA'
            }

    @staticmethod
    def verificar_primeira_transacao_dia(cliente_id: int) -> bool:
        """
        Verifica se é a primeira transação do dia do cliente.

        Args:
            cliente_id: ID do cliente

        Returns:
            bool: True se é a primeira transação do dia
        """
        try:
            # Cache por 23 horas (resetado diariamente)
            cache_key = f"primeira_transacao_{cliente_id}_{datetime.now().strftime('%Y%m%d')}"

            if cache.get(cache_key):
                return False  # Já houve transação hoje

            # Verificar no banco
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM wallclub.transacoes
                    WHERE cliente_id = %s
                    AND DATE(data_transacao) = CURDATE()
                """, [cliente_id])

                count = cursor.fetchone()[0]

                if count > 0:
                    # Já houve transação hoje: cachear
                    cache.set(cache_key, True, 82800)  # 23 horas
                    return False

                return True  # Primeira transação do dia

        except Exception as e:
            registrar_log('apps.cliente',
                f"Erro ao verificar primeira transação: {str(e)}", nivel='ERROR')
            return False  # Fail-open

    @staticmethod
    def registrar_transacao_2fa(cliente_id: int) -> None:
        """
        Registra que cliente fez transação hoje (para controle de primeira transação).

        Args:
            cliente_id: ID do cliente
        """
        try:
            cache_key = f"primeira_transacao_{cliente_id}_{datetime.now().strftime('%Y%m%d')}"
            cache.set(cache_key, True, 82800)  # 23 horas

        except Exception as e:
            registrar_log('apps.cliente',
                f"Erro ao registrar transação 2FA: {str(e)}", nivel='ERROR')

    @staticmethod
    def invalidar_dispositivos_apos_troca_senha(cliente_id: int) -> Dict[str, Any]:
        """
        Invalida TODOS os dispositivos confiáveis após troca de senha.
        Cliente precisará fazer 2FA novamente.

        Args:
            cliente_id: ID do cliente

        Returns:
            dict: Resultado da operação
        """
        try:
            from wallclub_core.seguranca.services_device import DeviceManagementService

            # Listar todos dispositivos
            dispositivos = DeviceManagementService.listar_dispositivos(
                user_id=cliente_id,
                tipo_usuario='cliente'
            )

            revogados = 0
            for dispositivo in dispositivos['dispositivos']:
                resultado = DeviceManagementService.revogar_dispositivo(
                    user_id=cliente_id,
                    tipo_usuario='cliente',
                    device_fingerprint=dispositivo['device_fingerprint']
                )
                if resultado['sucesso']:
                    revogados += 1

            registrar_log('apps.cliente',
                f"Dispositivos invalidados após troca senha: cliente={cliente_id}, total={revogados}")

            return {
                'sucesso': True,
                'dispositivos_revogados': revogados
            }

        except Exception as e:
            registrar_log('apps.cliente',
                f"Erro ao invalidar dispositivos: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Erro ao invalidar dispositivos'
            }
