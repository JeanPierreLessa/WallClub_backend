from django.conf import settings
from .services import ControleAcessoService
from wallclub_core.estr_organizacional.canal import Canal
from wallclub_core.utilitarios.log_control import registrar_log
from wallclub_core.integracoes.email_service import EmailService as EmailServiceCore


class EmailService:
    """
    Serviço para envio de emails relacionados aos usuários dos portais.
    Usa o EmailService centralizado do wallclub_core.
    """
    
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
        Envia email com link para primeiro acesso e senha temporária.
        Usa o EmailService centralizado do wallclub_core.
        """
        try:
            # Determinar URL baseada no portal de destino
            if portal_destino == 'lojista':
                # Portal lojista usa subdomínio wclojista.wallclub.com.br
                link_primeiro_acesso = f"https://wclojista.wallclub.com.br/primeiro_acesso/{token}/"
            else:
                # Portal admin responde na raiz (sem /portal_admin/)
                link_primeiro_acesso = f"{settings.BASE_URL}/primeiro_acesso/{token}/"
            
            # Contexto para o template (forçar canal_id se fornecido)
            contexto_canal = EmailService._obter_contexto_canal(usuario, canal_id)
            context = {
                'usuario': usuario,
                'senha_temporaria': senha_temporaria,
                'link_primeiro_acesso': link_primeiro_acesso,
                'validade_horas': 24,
                **contexto_canal
            }
            
            # Determinar template baseado no portal de destino
            if portal_destino == 'lojista':
                template_html = 'emails/lojista/primeiro_acesso.html'
                assunto = f'{contexto_canal["canal_nome"]} - Acesso ao Portal Lojista Criado'
            else:
                template_html = 'emails/admin/primeiro_acesso.html'
                assunto = f'{contexto_canal["canal_nome"]} - Acesso ao Portal Admin Criado'
            
            # Enviar via EmailService centralizado
            resultado = EmailServiceCore.enviar_email(
                destinatarios=[usuario.email],
                assunto=assunto,
                template_html=template_html,
                template_context=context,
                fail_silently=False
            )
            
            if resultado['sucesso']:
                registrar_log('portais.controle_acesso', f"Email de primeiro acesso enviado para {usuario.email} (portal: {portal_destino})")
                return True, "Email enviado com sucesso"
            else:
                registrar_log('portais.controle_acesso', f"Erro ao enviar email: {resultado['mensagem']}", nivel='ERROR')
                return False, resultado['mensagem']
            
        except Exception as e:
            registrar_log('portais.controle_acesso', f"Erro ao enviar email para {usuario.email}: {str(e)}", nivel='ERROR')
            return False, f"Erro ao enviar email: {str(e)}"
    
    @staticmethod
    def enviar_email_reset_senha(usuario, token, portal_destino='admin'):
        """
        Envia email para reset de senha.
        Usa o EmailService centralizado do wallclub_core.
        """
        try:
            # URL para reset de senha baseada no portal
            if portal_destino == 'lojista':
                # Portal lojista usa subdomínio wclojista.wallclub.com.br
                link_reset = f"https://wclojista.wallclub.com.br/reset-senha/{token}/"
            else:
                # Portal admin responde na raiz (sem /portal_admin/)
                link_reset = f"{settings.BASE_URL}/reset-senha/{token}/"
            
            # Obter contexto do canal para o assunto
            contexto_canal = EmailService._obter_contexto_canal(usuario)
            
            context = {
                'usuario': usuario,
                'link_reset': link_reset,
                'validade_horas': 24,
                **contexto_canal
            }
            
            # Determinar template baseado no portal de destino
            if portal_destino == 'lojista':
                template_html = 'emails/lojista/reset_senha.html'
                assunto = f'{contexto_canal["canal_nome"]} - Reset de Senha - Portal Lojista'
            else:
                template_html = 'emails/admin/reset_senha.html'
                assunto = f'{contexto_canal["canal_nome"]} - Reset de Senha - Portal Admin'
            
            # Enviar via EmailService centralizado
            resultado = EmailServiceCore.enviar_email(
                destinatarios=[usuario.email],
                assunto=assunto,
                template_html=template_html,
                template_context=context,
                fail_silently=False
            )
            
            if resultado['sucesso']:
                registrar_log('portais.controle_acesso', f"Email de reset de senha enviado para {usuario.email} (portal: {portal_destino})")
                return True, "Email enviado com sucesso"
            else:
                registrar_log('portais.controle_acesso', f"Erro ao enviar email: {resultado['mensagem']}", nivel='ERROR')
                return False, resultado['mensagem']
            
        except Exception as e:
            registrar_log('portais.controle_acesso', f"Erro ao enviar email de reset para {usuario.email}: {str(e)}", nivel='ERROR')
            return False, f"Erro ao enviar email: {str(e)}"
    
    @staticmethod
    def enviar_email_senha_alterada(usuario, portal_destino='admin'):
        """
        Envia email de confirmação após alteração de senha.
        Usa o EmailService centralizado do wallclub_core.
        """
        try:
            # Obter contexto do canal para o assunto
            contexto_canal = EmailService._obter_contexto_canal(usuario)
            
            context = {
                'usuario': usuario,
                'data_alteracao': usuario.updated_at.strftime('%d/%m/%Y às %H:%M'),
                **contexto_canal
            }
            
            # Determinar template baseado no portal de destino
            if portal_destino == 'lojista':
                template_html = 'emails/lojista/senha_alterada.html'
                assunto = f'{contexto_canal["canal_nome"]} - Senha Alterada - Portal Lojista'
            else:
                template_html = 'emails/admin/senha_alterada.html'
                assunto = f'{contexto_canal["canal_nome"]} - Senha Alterada - Portal Admin'
            
            # Enviar via EmailService centralizado
            resultado = EmailServiceCore.enviar_email(
                destinatarios=[usuario.email],
                assunto=assunto,
                template_html=template_html,
                template_context=context,
                fail_silently=False
            )
            
            if resultado['sucesso']:
                registrar_log('portais.controle_acesso', f"Email de confirmação de alteração de senha enviado para {usuario.email} (portal: {portal_destino})")
                return True, "Email enviado com sucesso"
            else:
                registrar_log('portais.controle_acesso', f"Erro ao enviar email: {resultado['mensagem']}", nivel='ERROR')
                return False, resultado['mensagem']
            
        except Exception as e:
            registrar_log('portais.controle_acesso', f"Erro ao enviar email de confirmação para {usuario.email}: {str(e)}", nivel='ERROR')
            return False, f"Erro ao enviar email: {str(e)}"
