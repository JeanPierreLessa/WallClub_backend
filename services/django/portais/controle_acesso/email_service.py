from django.core.mail import send_mail, get_connection
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .services import ControleAcessoService
from wallclub_core.estr_organizacional.canal import Canal
from wallclub_core.utilitarios.log_control import registrar_log


class EmailService:
    """Serviço para envio de emails relacionados aos usuários"""
    
    @staticmethod
    def _obter_contexto_canal(usuario, canal_id_override=None):
        """Obtém informações do canal do usuário para templates de email"""
        from django.conf import settings
        
        # Usar canal_id fornecido ou buscar do usuário
        canal_id = canal_id_override or ControleAcessoService.obter_canal_principal_usuario(usuario)
        try:
            from wallclub_core.estr_organizacional.services import HierarquiaOrganizacionalService
            canal = HierarquiaOrganizacionalService.get_canal(canal_id)
            if not canal:
                canal = type('obj', (object,), {'marca': f'canal{canal_id}'})()
            logo_filename = f'{canal_id}.png'
            return {
                'canal_id': canal_id,
                'canal_nome': canal.descricao or canal.nome or 'WallClub',
                'canal_marca': canal.marca,
                'logo_filename': logo_filename,
                'logo_url': f'{settings.BASE_URL}/static/images/canais/{logo_filename}'
            }
        except:
            return {
                'canal_id': 1,
                'canal_nome': 'WallClub',
                'canal_marca': 'wallclub',
                'logo_filename': '1.png',
                'logo_url': f'{settings.BASE_URL}/static/images/canais/1.png'
            }
    
    @staticmethod
    def enviar_email_primeiro_acesso(usuario, senha_temporaria, token, canal_id=None, portal_destino='admin'):
        """
        Envia email com link para primeiro acesso e senha temporária
        """
        try:
            # Determinar URL baseada no portal de destino e canal
            if portal_destino == 'lojista' and canal_id:
                # Buscar nome do canal para URL
                from wallclub_core.estr_organizacional.services import HierarquiaOrganizacionalService
                try:
                    canal = HierarquiaOrganizacionalService.get_canal(canal_id)
                    # Usar marca do canal para URL
                    marca = canal.marca or f'canal{canal_id}'
                    link_primeiro_acesso = f"{settings.BASE_URL}/portal_lojista/{marca}/primeiro_acesso/{token}/"
                except Canal.DoesNotExist:
                    # Fallback para portal lojista sem canal específico
                    link_primeiro_acesso = f"{settings.BASE_URL}/portal_lojista/primeiro_acesso/{token}/"
            else:
                # Portal admin (padrão)
                link_primeiro_acesso = f"{settings.BASE_URL}/portal_admin/primeiro_acesso/{token}/"
            
            # Contexto para o template (forçar canal_id se fornecido)
            context = {
                'usuario': usuario,
                'senha_temporaria': senha_temporaria,
                'link_primeiro_acesso': link_primeiro_acesso,
                'validade_horas': 24,
                **EmailService._obter_contexto_canal(usuario, canal_id)
            }
            
            # Renderizar template HTML
            html_message = render_to_string('portais/controle_acesso/emails/primeiro_acesso.html', context)
            plain_message = strip_tags(html_message)
            
            # Criar conexão SMTP explícita
            connection = get_connection(
                backend=settings.EMAIL_BACKEND,
                host=settings.EMAIL_HOST,
                port=settings.EMAIL_PORT,
                username=settings.EMAIL_HOST_USER,
                password=settings.EMAIL_HOST_PASSWORD,
                use_tls=settings.EMAIL_USE_TLS,
                use_ssl=settings.EMAIL_USE_SSL,
                fail_silently=False,
            )
            
            # Obter contexto do canal para o assunto
            contexto_canal = EmailService._obter_contexto_canal(usuario, canal_id)
            
            # Enviar email com conexão explícita
            resultado = send_mail(
                subject=f'{contexto_canal["canal_nome"]} - Acesso ao Sistema Criado',
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[usuario.email],
                html_message=html_message,
                connection=connection,
                fail_silently=False,
            )
            
            registrar_log('portais.controle_acesso', f"Email de primeiro acesso enviado para {usuario.email}")
            return True, "Email enviado com sucesso"
            
        except Exception as e:
            registrar_log('portais.controle_acesso', f"Erro ao enviar email para {usuario.email}: {str(e)}", nivel='ERROR')
            return False, f"Erro ao enviar email: {str(e)}"
    
    @staticmethod
    def enviar_email_reset_senha(usuario, token):
        """
        Envia email para reset de senha
        """
        try:
            # URL para reset de senha
            link_reset = f"{settings.BASE_URL}/portal_admin/reset-senha/{token}/"
            
            context = {
                'usuario': usuario,
                'link_reset': link_reset,
                'validade_horas': 24,
                **EmailService._obter_contexto_canal(usuario)
            }
            
            html_message = render_to_string('portais/controle_acesso/emails/reset_senha.html', context)
            plain_message = strip_tags(html_message)
            
            # Criar conexão SMTP explícita
            connection = get_connection(
                backend=settings.EMAIL_BACKEND,
                host=settings.EMAIL_HOST,
                port=settings.EMAIL_PORT,
                username=settings.EMAIL_HOST_USER,
                password=settings.EMAIL_HOST_PASSWORD,
                use_tls=settings.EMAIL_USE_TLS,
                use_ssl=settings.EMAIL_USE_SSL,
                fail_silently=False,
            )
            
            # Obter contexto do canal para o assunto
            contexto_canal = EmailService._obter_contexto_canal(usuario)
            
            resultado = send_mail(
                subject=f'{contexto_canal["canal_nome"]} - Reset de Senha',
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[usuario.email],
                html_message=html_message,
                connection=connection,
                fail_silently=False,
            )
            
            registrar_log('portais.controle_acesso', f"Email de reset de senha enviado para {usuario.email}")
            return True, "Email enviado com sucesso"
            
        except Exception as e:
            registrar_log('portais.controle_acesso', f"Erro ao enviar email de reset para {usuario.email}: {str(e)}", nivel='ERROR')
            return False, f"Erro ao enviar email: {str(e)}"
    
    @staticmethod
    def enviar_email_senha_alterada(usuario):
        """
        Envia email de confirmação após alteração de senha
        """
        try:
            context = {
                'usuario': usuario,
                'data_alteracao': usuario.updated_at.strftime('%d/%m/%Y às %H:%M'),
                **EmailService._obter_contexto_canal(usuario)
            }
            
            html_message = render_to_string('portais/controle_acesso/emails/senha_alterada.html', context)
            plain_message = strip_tags(html_message)
            
            # Criar conexão SMTP explícita
            connection = get_connection(
                backend=settings.EMAIL_BACKEND,
                host=settings.EMAIL_HOST,
                port=settings.EMAIL_PORT,
                username=settings.EMAIL_HOST_USER,
                password=settings.EMAIL_HOST_PASSWORD,
                use_tls=settings.EMAIL_USE_TLS,
                use_ssl=settings.EMAIL_USE_SSL,
                fail_silently=False,
            )
            
            # Obter contexto do canal para o assunto
            contexto_canal = EmailService._obter_contexto_canal(usuario)
            
            resultado = send_mail(
                subject=f'{contexto_canal["canal_nome"]} - Senha Alterada com Sucesso',
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[usuario.email],
                html_message=html_message,
                connection=connection,
                fail_silently=False,
            )
            
            registrar_log('portais.controle_acesso', f"Email de confirmação de alteração de senha enviado para {usuario.email}")
            return True, "Email enviado com sucesso"
            
        except Exception as e:
            registrar_log('portais.controle_acesso', f"Erro ao enviar email de confirmação para {usuario.email}: {str(e)}", nivel='ERROR')
            return False, f"Erro ao enviar email: {str(e)}"
