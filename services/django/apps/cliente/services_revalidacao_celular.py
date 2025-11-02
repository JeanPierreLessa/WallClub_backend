"""
Service para revalidação de celular a cada 30 dias.
Garante que o cliente mantenha um contato atualizado para notificações de segurança.

IMPORTANTE: Bloqueio se aplica APENAS ao APP MÓVEL.
POS e Checkout Web NÃO são bloqueados por celular expirado.
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from django.core.cache import cache
from django.db import connection
from wallclub_core.utilitarios.log_control import registrar_log


class RevalidacaoCelularService:
    """Service para gerenciação de revalidação periódica de celular"""
    
    # Período de validade do celular (90 dias)
    VALIDADE_DIAS = 90
    
    # Período de aviso prévio (7 dias antes de expirar)
    DIAS_AVISO_PREVIO = 7
    
    @staticmethod
    def verificar_validade_celular(cliente_id: int) -> Dict[str, Any]:
        """
        Verifica se o celular do cliente precisa ser revalidado.
        
        Args:
            cliente_id: ID do cliente
            
        Returns:
            dict: {
                'valido': bool,
                'dias_restantes': int,
                'precisa_revalidar': bool,
                'ultima_validacao': datetime ou None
            }
        """
        try:
            # Cache por 1 hora
            cache_key = f"celular_validade_{cliente_id}"
            resultado_cache = cache.get(cache_key)
            if resultado_cache:
                return resultado_cache
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT celular_validado_em
                    FROM wallclub.cliente
                    WHERE id = %s AND is_active = 1
                """, [cliente_id])
                
                row = cursor.fetchone()
                if not row:
                    return {
                        'valido': False,
                        'dias_restantes': 0,
                        'precisa_revalidar': True,
                        'ultima_validacao': None,
                        'mensagem': 'Cliente não encontrado'
                    }
                
                celular_validado_em = row[0]
                
                # Se nunca foi validado, precisa validar
                if not celular_validado_em:
                    resultado = {
                        'valido': False,
                        'dias_restantes': 0,
                        'precisa_revalidar': True,
                        'ultima_validacao': None,
                        'mensagem': 'Celular nunca foi validado'
                    }
                    cache.set(cache_key, resultado, 3600)
                    return resultado
                
                # Calcular dias desde última validação
                if isinstance(celular_validado_em, str):
                    celular_validado_em = datetime.strptime(celular_validado_em, '%Y-%m-%d %H:%M:%S')
                
                dias_desde_validacao = (datetime.now() - celular_validado_em).days
                dias_restantes = RevalidacaoCelularService.VALIDADE_DIAS - dias_desde_validacao
                
                # Verificar se expirou
                valido = dias_restantes > 0
                precisa_revalidar = dias_restantes <= 0
                
                resultado = {
                    'valido': valido,
                    'dias_restantes': max(0, dias_restantes),
                    'precisa_revalidar': precisa_revalidar,
                    'ultima_validacao': celular_validado_em,
                    'mensagem': 'Celular válido' if valido else 'Celular expirado - revalidação necessária'
                }
                
                # Cache por 1 hora
                cache.set(cache_key, resultado, 3600)
                
                return resultado
                
        except Exception as e:
            registrar_log('apps.cliente', 
                f"Erro ao verificar validade celular: {str(e)}", nivel='ERROR')
            return {
                'valido': True,  # Fail-open: não bloquear em caso de erro
                'dias_restantes': 99,
                'precisa_revalidar': False,
                'ultima_validacao': None,
                'mensagem': 'Erro ao verificar validade'
            }

    @staticmethod
    def solicitar_revalidacao_celular(cliente_id: int, canal_id: int) -> Dict[str, Any]:
        """
        Solicita revalidação enviando OTP para o celular cadastrado.
        
        Args:
            cliente_id: ID do cliente
            canal_id: ID do canal
            
        Returns:
            dict: Resultado da solicitação
        """
        try:
            # Buscar cliente
            from apps.cliente.models import Cliente
            try:
                cliente = Cliente.objects.only('celular', 'cpf').get(
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
            
            # Gerar OTP usando o service de 2FA
            from wallclub_core.seguranca.services_2fa import OTPService
            
            resultado_otp = OTPService.gerar_otp(
                user_id=cliente_id,
                tipo_usuario='cliente',
                telefone=cliente.celular
            )
            
            if not resultado_otp['success']:
                return resultado_otp
            
            # Buscar código do banco (resultado_otp['codigo'] só existe em DEBUG)
            from wallclub_core.seguranca.models import AutenticacaoOTP
            otp = AutenticacaoOTP.objects.get(id=resultado_otp['otp_id'])
            
            # Enviar OTP via WhatsApp
            from wallclub_core.integracoes.whatsapp_service import WhatsAppService
            from wallclub_core.integracoes.messages_template_service import MessagesTemplateService
            
            template = MessagesTemplateService.preparar_whatsapp(
                canal_id=canal_id,
                id_template='2fa_login_app',
                codigo=otp.codigo,
                url_ref=otp.codigo
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
                    mensagem=f"Seu código de revalidação de celular: {otp.codigo}\n\nVálido por 5 minutos."
                )
            
            # Marcar flag de revalidação solicitada
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE wallclub.cliente
                    SET celular_revalidacao_solicitada = 1
                    WHERE id = %s
                """, [cliente_id])
            
            registrar_log('apps.cliente', 
                f"Revalidação de celular solicitada: cliente={cliente_id}")
            
            return {
                'sucesso': True,
                'mensagem': 'Código de revalidação enviado',
                'whatsapp_enviado': whatsapp_enviado
            }
            
        except Exception as e:
            registrar_log('apps.cliente', 
                f"Erro ao solicitar revalidação: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Erro ao solicitar revalidação'
            }

    @staticmethod
    def validar_celular(cliente_id: int, codigo_otp: str) -> Dict[str, Any]:
        """
        Valida o código OTP e atualiza data de validação do celular.
        
        Args:
            cliente_id: ID do cliente
            codigo_otp: Código OTP informado pelo cliente
            
        Returns:
            dict: Resultado da validação
        """
        try:
            # Validar OTP
            from wallclub_core.seguranca.services_2fa import OTPService
            
            resultado_validacao = OTPService.validar_otp(
                user_id=cliente_id,
                tipo_usuario='cliente',
                codigo=codigo_otp
            )
            
            if not resultado_validacao['success']:
                return {
                    'sucesso': False,
                    'mensagem': resultado_validacao.get('mensagem', 'Código inválido')
                }
            
            # Atualizar data de validação
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE wallclub.cliente
                    SET celular_validado_em = NOW(),
                        celular_revalidacao_solicitada = 0
                    WHERE id = %s
                """, [cliente_id])
            
            # Invalidar cache
            cache_key = f"celular_validade_{cliente_id}"
            cache.delete(cache_key)
            
            registrar_log('apps.cliente', 
                f"Celular revalidado com sucesso: cliente={cliente_id}")
            
            return {
                'sucesso': True,
                'mensagem': 'Celular revalidado com sucesso'
            }
            
        except Exception as e:
            registrar_log('apps.cliente', 
                f"Erro ao validar celular: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Erro ao validar celular'
            }

    @staticmethod
    def bloquear_por_celular_expirado(cliente_id: int, origem: str) -> Dict[str, Any]:
        """
        Verifica se deve bloquear transação por celular expirado.
        
        IMPORTANTE: Bloqueio se aplica APENAS ao APP MÓVEL.
        POS e Checkout Web NÃO são bloqueados.
        
        Args:
            cliente_id: ID do cliente
            origem: Origem da transação ('app', 'pos', 'checkout')
            
        Returns:
            dict: {
                'bloqueado': bool,
                'mensagem': str,
                'dias_expirado': int
            }
        """
        try:
            # Verificar origem: apenas APP é bloqueado
            if origem.lower() not in ['app', 'mobile', 'app_mobile']:
                return {
                    'bloqueado': False,
                    'mensagem': 'Origem não requer validação de celular'
                }
            
            # Verificar validade do celular
            validade = RevalidacaoCelularService.verificar_validade_celular(cliente_id)
            
            if validade['precisa_revalidar']:
                dias_expirado = abs(validade['dias_restantes'])
                
                registrar_log('apps.cliente', 
                    f"Transação bloqueada por celular expirado: cliente={cliente_id}, dias_expirado={dias_expirado}")
                
                return {
                    'bloqueado': True,
                    'mensagem': 'Seu celular precisa ser revalidado para fazer transações',
                    'dias_expirado': dias_expirado,
                    'codigo': 'CELULAR_EXPIRADO'
                }
            
            return {
                'bloqueado': False,
                'mensagem': 'Celular válido'
            }
            
        except Exception as e:
            registrar_log('apps.cliente', 
                f"Erro ao verificar bloqueio: {str(e)}", nivel='ERROR')
            # Fail-open: não bloquear em caso de erro
            return {
                'bloqueado': False,
                'mensagem': 'Erro ao verificar celular'
            }

    @staticmethod
    def listar_clientes_proximos_expirar(dias_antes: int = 7) -> list:
        """
        Lista clientes cujo celular está próximo de expirar.
        Usado pelo job Celery para enviar lembretes.
        
        Args:
            dias_antes: Dias antes da expiração para listar
            
        Returns:
            list: Lista de dicts com dados dos clientes
        """
        try:
            data_limite = datetime.now() - timedelta(
                days=RevalidacaoCelularService.VALIDADE_DIAS - dias_antes
            )
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        id,
                        nome,
                        celular,
                        canal_id,
                        celular_validado_em,
                        DATEDIFF(NOW(), celular_validado_em) as dias_desde_validacao
                    FROM wallclub.cliente
                    WHERE is_active = 1
                    AND celular IS NOT NULL
                    AND celular != ''
                    AND celular_validado_em IS NOT NULL
                    AND celular_validado_em <= %s
                    AND (celular_revalidacao_solicitada = 0 OR celular_revalidacao_solicitada IS NULL)
                    ORDER BY celular_validado_em ASC
                    LIMIT 1000
                """, [data_limite])
                
                columns = [col[0] for col in cursor.description]
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]
                
                return results
                
        except Exception as e:
            registrar_log('apps.cliente', 
                f"Erro ao listar clientes próximos expirar: {str(e)}", nivel='ERROR')
            return []

    @staticmethod
    def listar_clientes_expirados() -> list:
        """
        Lista clientes cujo celular já expirou.
        Usado pelo job Celery para enviar alertas e bloquear.
        
        Returns:
            list: Lista de dicts com dados dos clientes
        """
        try:
            data_limite = datetime.now() - timedelta(
                days=RevalidacaoCelularService.VALIDADE_DIAS
            )
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        id,
                        nome,
                        celular,
                        canal_id,
                        celular_validado_em,
                        DATEDIFF(NOW(), celular_validado_em) as dias_desde_validacao
                    FROM wallclub.cliente
                    WHERE is_active = 1
                    AND celular IS NOT NULL
                    AND celular != ''
                    AND celular_validado_em IS NOT NULL
                    AND celular_validado_em < %s
                    ORDER BY celular_validado_em ASC
                    LIMIT 1000
                """, [data_limite])
                
                columns = [col[0] for col in cursor.description]
                results = [dict(zip(columns, row)) for row in cursor.fetchall()]
                
                return results
                
        except Exception as e:
            registrar_log('apps.cliente', 
                f"Erro ao listar clientes expirados: {str(e)}", nivel='ERROR')
            return []

    @staticmethod
    def enviar_lembrete_revalidacao(cliente_id: int, canal_id: int, dias_restantes: int) -> bool:
        """
        Envia lembrete de revalidação de celular.
        
        Args:
            cliente_id: ID do cliente
            canal_id: ID do canal
            dias_restantes: Dias restantes até expiração
            
        Returns:
            bool: True se enviado com sucesso
        """
        try:
            from apps.cliente.models import Cliente
            
            cliente = Cliente.objects.only('celular', 'firebase_token').get(
                id=cliente_id, is_active=True
            )
            
            if not cliente.celular:
                return False
            
            # Enviar via Push
            from wallclub_core.integracoes.notification_service import NotificationService
            
            notification_service = NotificationService.get_instance(canal_id)
            notification_service.send_push(
                cliente_id=cliente_id,
                id_template='lembrete_revalidacao',
                dias_restantes=str(dias_restantes)
            )
            
            # Enviar via WhatsApp
            from wallclub_core.integracoes.whatsapp_service import WhatsAppService
            
            WhatsAppService.envia_whatsapp_texto_simples(
                numero_telefone=cliente.celular,
                canal_id=canal_id,
                mensagem=f"🔔 *Lembrete Importante*\n\nSeu celular precisa ser revalidado em {dias_restantes} dias.\n\nRevalide agora no app para continuar usando normalmente."
            )
            
            registrar_log('apps.cliente', 
                f"Lembrete de revalidação enviado: cliente={cliente_id}, dias_restantes={dias_restantes}")
            
            return True
            
        except Exception as e:
            registrar_log('apps.cliente', 
                f"Erro ao enviar lembrete: {str(e)}", nivel='ERROR')
            return False

    @staticmethod
    def enviar_alerta_expirado(cliente_id: int, canal_id: int) -> bool:
        """
        Envia alerta de celular expirado.
        
        Args:
            cliente_id: ID do cliente
            canal_id: ID do canal
            
        Returns:
            bool: True se enviado com sucesso
        """
        try:
            from apps.cliente.models import Cliente
            
            cliente = Cliente.objects.only('celular', 'firebase_token').get(
                id=cliente_id, is_active=True
            )
            
            if not cliente.celular:
                return False
            
            # Enviar via Push
            from wallclub_core.integracoes.notification_service import NotificationService
            
            notification_service = NotificationService.get_instance(canal_id)
            notification_service.send_push(
                cliente_id=cliente_id,
                id_template='celular_expirado'
            )
            
            # Enviar via WhatsApp
            from wallclub_core.integracoes.whatsapp_service import WhatsAppService
            
            WhatsAppService.envia_whatsapp_texto_simples(
                numero_telefone=cliente.celular,
                canal_id=canal_id,
                mensagem="⚠️ *Ação Necessária*\n\nSeu celular expirou e suas transações no app estão bloqueadas.\n\n*Revalide agora* para continuar usando."
            )
            
            registrar_log('apps.cliente', 
                f"Alerta de celular expirado enviado: cliente={cliente_id}")
            
            return True
            
        except Exception as e:
            registrar_log('apps.cliente', 
                f"Erro ao enviar alerta: {str(e)}", nivel='ERROR')
            return False
