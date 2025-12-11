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
    def _determinar_portal_prioritario(usuario):
        """
        Determina qual portal usar baseado na prioridade:
        1. Lojista (se tiver acesso)
        2. Vendas (se tiver acesso)
        3. Admin (fallback)
        
        Args:
            usuario: PortalUsuario
            
        Returns:
            str: 'lojista', 'vendas' ou 'admin'
        """
        # Verificar acesso ao lojista (prioridade 1)
        if ControleAcessoService.usuario_tem_acesso_portal(usuario, 'lojista'):
            return 'lojista'
        
        # Verificar acesso ao vendas (prioridade 2)
        if ControleAcessoService.usuario_tem_acesso_portal(usuario, 'vendas'):
            return 'vendas'
        
        # Fallback: admin (prioridade 3)
        return 'admin'
    
    @staticmethod
    def _obter_canal_hierarquia_loja(usuario):
        """
        Obtém o canal baseado na hierarquia de loja do usuário.
        Se usuário tem vínculo com loja, busca o canal da hierarquia.
        Caso contrário, retorna canal padrão (1 - WallClub).
        
        Args:
            usuario: PortalUsuario
            
        Returns:
            int: ID do canal (padrão: 1)
        """
        from wallclub_core.estr_organizacional.services import HierarquiaOrganizacionalService
        
        # Buscar vínculo com loja
        lojas_ids = ControleAcessoService.obter_lojas_usuario(usuario)
        
        if lojas_ids:
            # Pegar primeira loja e buscar hierarquia
            loja_id = lojas_ids[0]
            try:
                hierarquia = HierarquiaOrganizacionalService.get_loja_hierarquia_completa(loja_id)
                if hierarquia and 'canal' in hierarquia:
                    return hierarquia['canal']['id']
            except:
                pass
        
        # Fallback: canal padrão WallClub
        return 1
    
    @staticmethod
    def _obter_contexto_canal(usuario, canal_id_override=None):
        """Obtém informações do canal do usuário para templates de email"""
        from django.conf import settings
        
        # Usar canal_id fornecido ou buscar da hierarquia de loja
        if canal_id_override:
            canal_id = canal_id_override
        else:
            canal_id = EmailService._obter_canal_hierarquia_loja(usuario)
        
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
    def enviar_email_primeiro_acesso(usuario, senha_temporaria, token, canal_id=None, portal_destino=None):
        """
        Envia email com link para primeiro acesso e senha temporária.
        Usa o EmailService centralizado do wallclub_core.
        
        Args:
            usuario: PortalUsuario
            senha_temporaria: Senha temporária gerada
            token: Token de primeiro acesso
            canal_id: ID do canal (opcional, usa hierarquia de loja se não fornecido)
            portal_destino: Portal de destino (opcional, determina automaticamente se não fornecido)
        """
        try:
            # Determinar portal prioritário se não fornecido
            if not portal_destino:
                portal_destino = EmailService._determinar_portal_prioritario(usuario)
            
            # Determinar URL baseada no portal de destino - obrigatório via settings
            if portal_destino == 'lojista':
                link_primeiro_acesso = f"{settings.PORTAL_LOJISTA_URL}/primeiro_acesso/{token}/"
            elif portal_destino == 'vendas':
                link_primeiro_acesso = f"{settings.PORTAL_VENDAS_URL}/primeiro_acesso/{token}/"
            else:
                link_primeiro_acesso = f"{settings.BASE_URL}/primeiro_acesso/{token}/"
            
            # Contexto para o template (usa hierarquia de loja se canal_id não fornecido)
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
            elif portal_destino == 'vendas':
                template_html = 'emails/vendas/primeiro_acesso.html'
                assunto = f'{contexto_canal["canal_nome"]} - Acesso ao Portal Vendas Criado'
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
    def enviar_email_reset_senha(usuario, token, portal_destino=None):
        """
        Envia email para reset de senha.
        Usa o EmailService centralizado do wallclub_core.
        
        Args:
            usuario: PortalUsuario
            token: Token de reset de senha
            portal_destino: Portal de destino (opcional, determina automaticamente se não fornecido)
        """
        try:
            # Determinar portal prioritário se não fornecido
            if not portal_destino:
                portal_destino = EmailService._determinar_portal_prioritario(usuario)
            
            # URL para reset de senha baseada no portal - obrigatório via settings
            if portal_destino == 'lojista':
                link_reset = f"{settings.PORTAL_LOJISTA_URL}/reset-senha/{token}/"
            elif portal_destino == 'vendas':
                link_reset = f"{settings.PORTAL_VENDAS_URL}/reset-senha/{token}/"
            else:
                link_reset = f"{settings.BASE_URL}/reset-senha/{token}/"
            
            # Obter contexto do canal baseado na hierarquia de loja
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
            elif portal_destino == 'vendas':
                template_html = 'emails/vendas/reset_senha.html'
                assunto = f'{contexto_canal["canal_nome"]} - Reset de Senha - Portal Vendas'
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
    def enviar_email_token_troca_senha(usuario, token, validade_minutos=30, portal_destino=None):
        """
        Envia email com token para confirmação de troca de senha.
        Usado no fluxo de 2 etapas dos portais.
        
        Args:
            usuario: PortalUsuario
            token: Token de confirmação
            validade_minutos: Validade do token em minutos
            portal_destino: Portal de destino (opcional, determina automaticamente se não fornecido)
        """
        try:
            # Determinar portal prioritário se não fornecido
            if not portal_destino:
                portal_destino = EmailService._determinar_portal_prioritario(usuario)
            
            # Obter contexto do canal baseado na hierarquia de loja
            contexto_canal = EmailService._obter_contexto_canal(usuario)
            
            context = {
                'usuario': usuario,
                'token': token,
                'validade_minutos': validade_minutos,
                **contexto_canal
            }
            
            # Determinar template baseado no portal de destino
            if portal_destino == 'lojista':
                template_html = 'emails/lojista/token_troca_senha.html'
                assunto = f'{contexto_canal["canal_nome"]} - Token de Confirmação - Portal Lojista'
            elif portal_destino == 'vendas':
                template_html = 'emails/vendas/token_troca_senha.html'
                assunto = f'{contexto_canal["canal_nome"]} - Token de Confirmação - Portal Vendas'
            else:
                template_html = 'emails/admin/token_troca_senha.html'
                assunto = f'{contexto_canal["canal_nome"]} - Token de Confirmação - Portal Admin'
            
            # Enviar via EmailService centralizado
            resultado = EmailServiceCore.enviar_email(
                destinatarios=[usuario.email],
                assunto=assunto,
                template_html=template_html,
                template_context=context,
                fail_silently=False
            )
            
            if resultado['sucesso']:
                registrar_log('portais.controle_acesso', f"Email com token de troca de senha enviado para {usuario.email} (portal: {portal_destino})")
                return True, "Email enviado com sucesso"
            else:
                registrar_log('portais.controle_acesso', f"Erro ao enviar email: {resultado['mensagem']}", nivel='ERROR')
                return False, resultado['mensagem']
            
        except Exception as e:
            registrar_log('portais.controle_acesso', f"Erro ao enviar email com token para {usuario.email}: {str(e)}", nivel='ERROR')
            return False, f"Erro ao enviar email: {str(e)}"
    
    @staticmethod
    def enviar_email_senha_alterada(usuario, portal_destino=None):
        """
        Envia email de confirmação após alteração de senha.
        Usa o EmailService centralizado do wallclub_core.
        
        Args:
            usuario: PortalUsuario
            portal_destino: Portal de destino (opcional, determina automaticamente se não fornecido)
        """
        try:
            # Determinar portal prioritário se não fornecido
            if not portal_destino:
                portal_destino = EmailService._determinar_portal_prioritario(usuario)
            
            # Obter contexto do canal baseado na hierarquia de loja
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
            elif portal_destino == 'vendas':
                template_html = 'emails/vendas/senha_alterada.html'
                assunto = f'{contexto_canal["canal_nome"]} - Senha Alterada - Portal Vendas'
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
