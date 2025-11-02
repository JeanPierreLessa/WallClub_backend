# apps/cliente/services_reset_senha.py
"""
Service para reset de senha via OTP
Data: 27/10/2025
"""

import re
from datetime import datetime
from django.core.cache import cache
from apps.cliente.models import Cliente
from wallclub_core.integracoes.sms_service import enviar_sms
from wallclub_core.utilitarios.log_control import registrar_log


class ResetSenhaService:
    """Service para reset de senha via OTP"""
    
    @staticmethod
    def solicitar_reset(cpf: str, canal_id: int) -> dict:
        """
        Envia OTP para reset de senha
        
        Args:
            cpf: CPF do cliente
            canal_id: ID do canal
            
        Returns:
            dict com resultado
        """
        try:
            # Limpar CPF
            cpf_limpo = ''.join(filter(str.isdigit, cpf))
            if len(cpf_limpo) != 11:
                return {
                    'sucesso': False,
                    'mensagem': 'CPF inválido'
                }
            
            # Rate limiting: 3 solicitações por hora
            rate_key = f"reset_senha_rate_{cpf_limpo}"
            tentativas = cache.get(rate_key, 0)
            
            if tentativas >= 3:
                return {
                    'sucesso': False,
                    'mensagem': 'Limite de solicitações atingido. Tente novamente em 1 hora.'
                }
            
            # Buscar cliente
            try:
                cliente = Cliente.objects.get(
                    cpf=cpf_limpo, 
                    canal_id=canal_id, 
                    is_active=True
                )
                
                # Verificar se completou cadastro
                if not cliente.cadastro_completo:
                    return {
                        'sucesso': False,
                        'mensagem': 'CPF não encontrado. Complete seu cadastro primeiro.'
                    }
                
            except Cliente.DoesNotExist:
                return {
                    'sucesso': False,
                    'mensagem': 'CPF não encontrado. Complete seu cadastro primeiro.'
                }
            
            # Gerar OTP
            codigo_otp = ResetSenhaService._gerar_otp()
            
            # Salvar OTP no cache (5 minutos)
            cache_key = f"reset_senha_otp_{cpf_limpo}"
            cache.set(cache_key, {
                'codigo': codigo_otp,
                'tentativas': 0,
                'cliente_id': cliente.id
            }, 300)  # 5 minutos
            
            # Incrementar rate limiting
            cache.set(rate_key, tentativas + 1, 3600)  # 1 hora
            
            # Enviar OTP via WhatsApp
            from wallclub_core.integracoes.messages_template_service import MessagesTemplateService
            from wallclub_core.integracoes.whatsapp_service import WhatsAppService
            
            template_whatsapp = MessagesTemplateService.preparar_whatsapp(
                canal_id=canal_id,
                id_template='2fa_login_app',
                codigo=codigo_otp,
                url_ref=codigo_otp
            )
            
            if template_whatsapp:
                whatsapp_enviado = WhatsAppService.envia_whatsapp(
                    numero_telefone=cliente.celular,
                    canal_id=canal_id,
                    nome_template=template_whatsapp['nome_template'],
                    idioma_template=template_whatsapp['idioma'],
                    parametros_corpo=template_whatsapp['parametros_corpo'],
                    parametros_botao=template_whatsapp.get('parametros_botao')
                )
                
                if whatsapp_enviado:
                    registrar_log('apps.cliente', 
                        f"OTP reset senha enviado via WhatsApp: {cpf_limpo[:3]}***, ID={cliente.id}")
                else:
                    registrar_log('apps.cliente', 
                        f"Falha ao enviar WhatsApp reset senha", 
                        nivel='WARNING')
            
            # Mascarar celular
            celular_limpo = ''.join(filter(str.isdigit, cliente.celular))
            celular_mascarado = f"({celular_limpo[:2]}) {celular_limpo[2]}****-{celular_limpo[-4:]}"
            
            return {
                'sucesso': True,
                'mensagem': f'Código enviado via WhatsApp para {celular_mascarado}'
            }
        
        except Exception as e:
            registrar_log('apps.cliente', 
                f"Erro ao solicitar reset senha: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Erro ao processar solicitação'
            }
    
    @staticmethod
    def validar_reset(cpf: str, codigo: str, nova_senha: str) -> dict:
        """
        Valida OTP + cria nova senha
        
        Args:
            cpf: CPF do cliente
            codigo: Código OTP
            nova_senha: Nova senha
            
        Returns:
            dict com resultado
        """
        try:
            # Limpar CPF
            cpf_limpo = ''.join(filter(str.isdigit, cpf))
            
            # Validar senha forte
            if not ResetSenhaService._validar_senha_forte(nova_senha):
                return {
                    'sucesso': False,
                    'mensagem': 'Senha fraca. Use no mínimo 8 caracteres com letras e números.'
                }
            
            # Buscar OTP no cache
            cache_key = f"reset_senha_otp_{cpf_limpo}"
            dados_otp = cache.get(cache_key)
            
            if not dados_otp:
                return {
                    'sucesso': False,
                    'mensagem': 'Código expirado. Solicite um novo código.'
                }
            
            # Verificar tentativas
            if dados_otp['tentativas'] >= 3:
                cache.delete(cache_key)
                return {
                    'sucesso': False,
                    'mensagem': 'Número máximo de tentativas excedido. Solicite um novo código.'
                }
            
            # Validar código
            if dados_otp['codigo'] != codigo:
                dados_otp['tentativas'] += 1
                cache.set(cache_key, dados_otp, 300)
                
                tentativas_restantes = 3 - dados_otp['tentativas']
                
                return {
                    'sucesso': False,
                    'mensagem': 'Código inválido ou expirado',
                    'tentativas_restantes': tentativas_restantes
                }
            
            # Código válido - atualizar senha
            try:
                cliente = Cliente.objects.get(id=dados_otp['cliente_id'], is_active=True)
                
                # Atualizar senha
                cliente.set_password(nova_senha)
                cliente.save()
                
                # Atualizar ClienteAuth
                from apps.cliente.models import ClienteAuth
                try:
                    cliente_auth = ClienteAuth.objects.get(cliente=cliente)
                    cliente_auth.senha_temporaria = False
                    cliente_auth.last_password_change = datetime.now()
                    cliente_auth.save()
                except ClienteAuth.DoesNotExist:
                    ClienteAuth.objects.create(
                        cliente=cliente,
                        senha_temporaria=False,
                        last_password_change=datetime.now()
                    )
                
                # Remover OTP do cache
                cache.delete(cache_key)
                
                # CRÍTICO: Invalidar todos dispositivos confiáveis por segurança
                try:
                    from wallclub_core.seguranca.services_device import DeviceManagementService
                    DeviceManagementService.revogar_todos_dispositivos(
                        user_id=cliente.id,
                        tipo_usuario='cliente'
                    )
                    registrar_log('apps.cliente',
                        f"Dispositivos invalidados após reset de senha: ID={cliente.id}", nivel='INFO')
                except Exception as e:
                    registrar_log('apps.cliente',
                        f"Erro ao invalidar dispositivos: {str(e)}", nivel='WARNING')
                
                # Limpar bloqueios e tentativas de login
                try:
                    from apps.cliente.services_login_persistent import LoginPersistentService
                    LoginPersistentService.limpar_tentativas(cpf_limpo)
                    registrar_log('apps.cliente',
                        f"Bloqueios limpos após reset de senha: {cpf_limpo[:3]}***", nivel='INFO')
                except Exception as e:
                    registrar_log('apps.cliente',
                        f"Erro ao limpar bloqueios: {str(e)}", nivel='WARNING')
                
                registrar_log('apps.cliente', 
                    f"✅ Senha alterada via reset: {cpf_limpo[:3]}***, ID={cliente.id}")
                
                # Notificar troca de senha
                try:
                    from wallclub_core.integracoes.notificacao_seguranca_service import NotificacaoSegurancaService
                    NotificacaoSegurancaService.notificar_troca_senha(
                        cliente_id=cliente.id,
                        canal_id=cliente.canal_id,
                        celular=cliente.celular,
                        nome=cliente.nome
                    )
                except Exception as e:
                    registrar_log('apps.cliente',
                        f"Erro ao notificar reset de senha: {str(e)}", nivel='WARNING')
                
                return {
                    'sucesso': True,
                    'mensagem': 'Senha alterada com sucesso! Faça login com a nova senha.'
                }
                
            except Cliente.DoesNotExist:
                return {
                    'sucesso': False,
                    'mensagem': 'Cliente não encontrado'
                }
        
        except Exception as e:
            registrar_log('apps.cliente', 
                f"Erro ao validar reset senha: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Erro ao processar reset de senha'
            }
    
    @staticmethod
    def _gerar_otp() -> str:
        """Gera código OTP de 6 dígitos"""
        import random
        return str(random.randint(100000, 999999))
    
    @staticmethod
    def _validar_senha_forte(senha: str) -> bool:
        """
        Valida se senha é forte
        Critérios: mínimo 8 caracteres, pelo menos 1 letra e 1 número
        """
        if len(senha) < 8:
            return False
        
        tem_letra = bool(re.search(r'[a-zA-Z]', senha))
        tem_numero = bool(re.search(r'\d', senha))
        
        return tem_letra and tem_numero
