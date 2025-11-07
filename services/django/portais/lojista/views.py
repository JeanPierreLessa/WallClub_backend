"""
Views principais do Portal Lojista - Autenticação e navegação
"""
from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.views import View
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.urls import reverse
from datetime import datetime, timedelta
# import logging - removido, usando registrar_log
import json
import csv
import io
import hashlib
from decimal import Decimal

from portais.controle_acesso.models import PortalUsuario, PortalPermissao
from portais.controle_acesso.services import AutenticacaoService
from portais.controle_acesso.email_service import EmailService
from portais.controle_acesso.filtros import FiltrosAcessoService
from wallclub_core.utilitarios.log_control import registrar_log
from wallclub_core.estr_organizacional.loja import Loja
from wallclub_core.database.queries import TransacoesQueries

from .mixins import LojistaAccessMixin, LojistaDataMixin


class LojistaLoginView(View):
    """View de login para o portal lojista"""
    template_name = 'portais/lojista/login.html'
    
    def get(self, request, marca=None):
        # Se já está logado, redirecionar
        if request.session.get('lojista_authenticated'):
            aceite = request.session.get('lojista_aceite', False)
            if aceite:
                return redirect('lojista:home')
            else:
                return redirect('lojista:aceite')
        
        return render(request, self.template_name)
    
    def post(self, request, marca=None):
        email = request.POST.get('email')
        senha = request.POST.get('senha')
        
        if not email or not senha:
            messages.error(request, 'Por favor, preencha todos os campos.')
            return render(request, self.template_name)
        
        # Validar senha usando modelo ORM Django
        try:
            # Primeiro tentar encontrar usuário ativo
            usuario = PortalUsuario.objects.get(
                email=email,
                ativo=True,
                email_verificado=True
            )
            
            # Verificar se pode acessar portal lojista
            if not usuario.pode_acessar_portal('lojista'):
                raise PortalUsuario.DoesNotExist()
            
            # Verificar senha usando método do modelo
            if usuario.verificar_senha(senha):
                # Buscar canal_id do usuário
                from portais.controle_acesso.services import ControleAcessoService
                canal_id = ControleAcessoService.obter_canal_principal_usuario(usuario)
                
                # Salvar na sessão
                request.session['lojista_authenticated'] = True
                request.session['lojista_usuario_id'] = usuario.id
                request.session['lojista_usuario_nome'] = usuario.nome
                request.session['lojista_usuario_email'] = usuario.email
                request.session['lojista_aceite'] = usuario.aceite
                request.session['canal_id'] = canal_id
                
                # Redirecionar baseado no aceite
                if usuario.aceite:
                    return redirect('lojista:home')
                else:
                    return redirect('lojista:aceite')
            else:
                messages.error(request, 'Email ou senha inválidos. Por favor, tente novamente.')
                
        except PortalUsuario.DoesNotExist:
            messages.error(request, 'Email ou senha inválidos. Por favor, tente novamente.')
        except Exception as e:
            messages.error(request, 'Erro interno. Tente novamente.')
        
        return render(request, self.template_name)


class LojistaLogoutView(View):
    """Logout do portal lojista"""
    
    def get(self, request, marca=None):
        nome_usuario = request.session.get('lojista_usuario_nome', 'Usuário')
        
        # Limpar sessão
        request.session.flush()
        
        return redirect('lojista:login')


class LojistaHomeView(TemplateView):
    """View da home com dashboard financeiro"""
    template_name = 'portais/lojista/home.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.session.get('lojista_authenticated'):
            return redirect('lojista:login')
        
        # Validar acesso à loja antes de processar a view
        usuario_id = request.session.get('lojista_usuario_id')
        loja_id = request.GET.get('loja_id', '')
        
        if loja_id and usuario_id:
            try:
                from portais.controle_acesso.models import PortalUsuario
                from portais.controle_acesso.filtros import FiltrosAcessoService
                
                usuario = PortalUsuario.objects.get(id=usuario_id)
                lojas_acessiveis = FiltrosAcessoService.obter_lojas_acessiveis(usuario)
                lojas_ids = [loja['id'] for loja in lojas_acessiveis]
                
                loja_id_int = int(loja_id)
                if loja_id_int not in lojas_ids:
                    messages.error(request, 'Você não tem permissão para acessar esta loja.')
                    return redirect('lojista:home')  # Redirect sem parâmetro loja_id
            except (ValueError, PortalUsuario.DoesNotExist):
                pass  # Ignorar erros de validação, será tratado no get_context_data
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        from django.db import connection
        from datetime import date
        
        context = super().get_context_data(**kwargs)
        usuario_id = self.request.session.get('lojista_usuario_id')
        
        # Verificar se é usuário admin
        from portais.controle_acesso.models import PortalUsuario, PortalPermissao
        is_admin = False
        try:
            usuario = PortalUsuario.objects.get(id=usuario_id)
            # Verificar se tem permissão admin (tipo_usuario removido)
            try:
                permissao = PortalPermissao.objects.get(usuario=usuario, portal='lojista')
                # Só é admin se nivel_acesso for 'admin_lojista'
                is_admin = (permissao.nivel_acesso == 'admin_lojista')
            except PortalPermissao.DoesNotExist:
                pass
        except PortalUsuario.DoesNotExist:
            pass
        
        # Obter lojas acessíveis ao usuário usando serviço centralizado
        try:
            usuario = PortalUsuario.objects.get(id=usuario_id)
            lojas_acessiveis = FiltrosAcessoService.obter_lojas_acessiveis(usuario)
            lojas_ids = [loja['id'] for loja in lojas_acessiveis]
        except PortalUsuario.DoesNotExist:
            # Se usuário não existe, retornar contexto vazio (redirect será feito no dispatch)
            lojas_acessiveis = []
            lojas_ids = []
        
        # Obter filtro de loja selecionada (validação já feita no dispatch)
        loja_id = self.request.GET.get('loja_id', '')
        
        # Verificar se loja_id é válido
        if loja_id:
            try:
                loja_id_int = int(loja_id)
                # Se chegou até aqui, o acesso já foi validado no dispatch
            except ValueError:
                loja_id = None  # Ignorar valor inválido
        
        # Construir WHERE clause baseado no filtro
        where_clause = ""
        if loja_id:
            # Filtro por loja específica (já validado acesso acima)
            where_clause = f"AND btg.var6 = '{loja_id}'"
        elif not is_admin and lojas_ids:
            # Para não-admin: filtrar por lojas acessíveis
            where_clause = f"AND btg.var6 IN ({','.join(map(str, lojas_ids))})"
        # Para admin sem filtro específico: sem WHERE clause = todas as lojas
        
        # Buscar estatísticas consolidadas em uma única query
        with connection.cursor() as cursor:
            cursor.execute(f"""
                SELECT 
                    COUNT(CASE WHEN data_transacao >= CURDATE() THEN 1 END) as transacoes_hoje,
                    SUM(CASE WHEN data_transacao >= CURDATE() THEN CAST(var19 AS DECIMAL(10,2)) ELSE 0 END) as valor_hoje,
                    COUNT(CASE WHEN YEAR(data_transacao) = YEAR(CURDATE()) AND MONTH(data_transacao) = MONTH(CURDATE()) THEN 1 END) as transacoes_mes,
                    SUM(CASE WHEN YEAR(data_transacao) = YEAR(CURDATE()) AND MONTH(data_transacao) = MONTH(CURDATE()) THEN CAST(var19 AS DECIMAL(10,2)) ELSE 0 END) as valor_mes
                FROM (
                    SELECT var9, var19, data_transacao,
                           ROW_NUMBER() OVER (PARTITION BY var9 ORDER BY id DESC) as rn
                    FROM baseTransacoesGestao btg
                    WHERE var68 = 'TRANS. APROVADO'
                    AND var19 IS NOT NULL
                    {where_clause}
                ) t WHERE rn = 1
            """)
            row = cursor.fetchone()
            transacoes_hoje = row[0] or 0
            valor_hoje = row[1] or 0
            transacoes_mes = row[2] or 0
            valor_mes = row[3] or 0
        
        context.update({
            'nome_usuario': self.request.session.get('lojista_usuario_nome', 'Usuário'),
            'current_page': 'home',
            'transacoes_hoje': transacoes_hoje,
            'valor_hoje': valor_hoje,
            'transacoes_mes': transacoes_mes,
            'valor_mes': valor_mes,
            'lojas_acessiveis': lojas_acessiveis,
            'loja_id': loja_id,
        })
        
        return context


class LojistaAceiteView(TemplateView):
    """View de aceite de termos"""
    template_name = 'portais/lojista/aceite.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.session.get('lojista_authenticated'):
            return redirect('lojista:login')
        return super().dispatch(request, *args, **kwargs)


@method_decorator(csrf_exempt, name='dispatch')
class LojistaProcessarAceiteView(View):
    """Processar aceite de termos"""
    
    def post(self, request, marca=None):
        if not request.session.get('lojista_authenticated'):
            return redirect('lojista:login')
        
        # O aceite é processado automaticamente quando o formulário é enviado
        # (similar ao PHP que não verifica checkbox específico)
        id_usuario = request.session.get('lojista_usuario_id')
        
        try:
            # Buscar usuário e atualizar aceite usando ORM
            usuario = PortalUsuario.objects.get(id=id_usuario)
            
            # Verificar se já aceitou
            if usuario.aceite:
                request.session['lojista_aceite'] = True
                return redirect('lojista:home')
            
            # Atualizar aceite
            from datetime import datetime
            usuario.aceite = True
            usuario.data_aceite = datetime.now()
            usuario.save()
            
            # Log da ação
            registrar_log(
                'portais.lojista',
                f"Aceite de termos processado para usuário ID {id_usuario}"
            )
            
            request.session['lojista_aceite'] = True
            messages.success(request, 'Termos aceitos com sucesso!')
            return redirect('lojista:home')
                    
        except PortalUsuario.DoesNotExist:
            messages.error(request, 'Usuário não encontrado.')
            return redirect('lojista:login')
        except Exception as e:
            # Log do erro
            registrar_log(
                'portais.lojista',
                f"Erro ao processar aceite para usuário ID {id_usuario}: {str(e)}"
            )
            messages.error(request, 'Ocorreu um erro ao processar o aceite dos termos. Por favor, tente novamente.')
            return redirect('lojista:aceite')


class LojistaTrocarSenhaView(View):
    """View para alterar senha"""
    template_name = 'portais/lojista/trocar_senha.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.session.get('lojista_authenticated'):
            return redirect('lojista:login')
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request, marca=None):
        context = {
            'current_page': 'trocar_senha'
        }
        return render(request, self.template_name, context)
    
    def post(self, request, marca=None):
        usuario_id = request.session.get('lojista_usuario_id')
        
        if not usuario_id:
            messages.error(request, 'Sessão inválida.')
            return redirect('lojista:login')
        
        senha_atual = request.POST.get('senha_atual', '').strip()
        nova_senha = request.POST.get('nova_senha', '').strip()
        confirmar_senha = request.POST.get('confirmar_senha', '').strip()
        
        # Validações básicas
        if not senha_atual or not nova_senha or not confirmar_senha:
            messages.error(request, 'Todos os campos são obrigatórios.')
            return self.get(request)
        
        if nova_senha != confirmar_senha:
            messages.error(request, 'A nova senha e a confirmação não coincidem.')
            return self.get(request)
        
        # Validar complexidade da nova senha
        from wallclub_core.utilitarios.senha_validator import validar_complexidade_senha
        senha_valida, mensagem_erro = validar_complexidade_senha(nova_senha)
        if not senha_valida:
            messages.error(request, mensagem_erro)
            return self.get(request)
        
        try:
            usuario = PortalUsuario.objects.get(id=usuario_id)
            
            # Verificar senha atual
            if not usuario.verificar_senha(senha_atual):
                messages.error(request, 'Senha atual incorreta.')
                return self.get(request)
            
            # Gerar hash MD5 da nova senha
            nova_senha_hash = hashlib.md5(nova_senha.encode()).hexdigest()
            
            # Gerar token de confirmação usando campos existentes
            token = usuario.gerar_token_troca_senha(nova_senha_hash)
            
            # Enviar email com token
            self._enviar_email_confirmacao(usuario, token)
            
            messages.success(request, 'Um token de confirmação foi enviado para seu email. Verifique sua caixa de entrada e digite o token para confirmar a alteração da senha.')
            return redirect('lojista:confirmar_troca_senha')
            
        except PortalUsuario.DoesNotExist:
            messages.error(request, 'Usuário não encontrado.')
            return redirect('lojista:login')
        except Exception as e:
            messages.error(request, f'Erro ao processar troca de senha: {str(e)}')
            return self.get(request)
    
    def _enviar_email_confirmacao(self, usuario, token):
        """Envia email com token de confirmação"""
        from portais.controle_acesso.email_service import EmailService
        
        # Enviar email com token (não é confirmação ainda, é solicitação)
        EmailService.enviar_email_token_troca_senha(usuario, token, validade_minutos=30, portal_destino='lojista')


class LojistaConfirmarTrocaSenhaView(View):
    """View para confirmar troca de senha com token"""
    template_name = 'portais/lojista/confirmar_troca_senha.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.session.get('lojista_authenticated'):
            return redirect('lojista:login')
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request, marca=None):
        context = {
            'current_page': 'confirmar_troca_senha'
        }
        return render(request, self.template_name, context)
    
    def post(self, request, marca=None):
        usuario_id = request.session.get('lojista_usuario_id')
        token_digitado = request.POST.get('token', '').strip()
        
        if not token_digitado:
            messages.error(request, 'Por favor, digite o token recebido por email.')
            return self.get(request)
        
        try:
            usuario = PortalUsuario.objects.get(id=usuario_id)
            
            # Validar token usando campos existentes
            if not usuario.validar_token_troca_senha(token_digitado):
                messages.error(request, 'Token inválido ou expirado. Solicite uma nova alteração de senha.')
                return redirect('lojista:trocar_senha')
            
            # Aplicar nova senha
            if usuario.confirmar_troca_senha():
                messages.success(request, 'Senha alterada com sucesso!')
                return redirect('lojista:perfil')
            else:
                messages.error(request, 'Erro ao aplicar nova senha.')
                return self.get(request)
            
        except PortalUsuario.DoesNotExist:
            messages.error(request, 'Usuário não encontrado.')
            return redirect('lojista:login')
        except Exception as e:
            messages.error(request, f'Erro ao confirmar troca de senha: {str(e)}')
            return self.get(request)


class LojistaValidarUsuarioView(View):
    """View para recuperação de senha"""
    template_name = 'portais/lojista/validar_usuario.html'
    
    def get(self, request, marca=None):
        return render(request, self.template_name)
    
    def post(self, request, marca=None):
        email = request.POST.get('email')
        
        if not email:
            messages.error(request, 'Por favor, informe seu email.')
            return render(request, self.template_name)
        
        try:
            # Buscar usuário pelo email
            usuario = PortalUsuario.objects.get(email=email)
            
            # Verificar se pode acessar portal lojista
            if not usuario.pode_acessar_portal('lojista'):
                messages.error(request, 'Este email não tem acesso ao portal lojista.')
                return render(request, self.template_name)
            
            # Usar EmailService para enviar reset de senha
            from portais.controle_acesso.email_service import EmailService
            import secrets
            import string
            from datetime import datetime, timedelta
            
            # Gerar token de reset
            token_reset = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
            
            # Configurar token no usuário
            usuario.token_reset_senha = token_reset
            usuario.reset_senha_expira = datetime.now() + timedelta(hours=24)
            usuario.save()
            
            # Enviar email de reset
            sucesso, mensagem = EmailService.enviar_email_reset_senha(usuario, token_reset)
            
            if sucesso:
                messages.success(request, 'Um link para redefinir sua senha foi enviado para seu email.')
            else:
                messages.error(request, f'Erro ao enviar email: {mensagem}')
                
        except PortalUsuario.DoesNotExist:
            # Por segurança, não revelar se o email existe ou não
            messages.success(request, 'Se o email estiver cadastrado, você receberá um link para redefinir sua senha.')
        except Exception as e:
            messages.error(request, 'Erro interno. Tente novamente mais tarde.')
            
        return render(request, self.template_name)


class LojistaPerfilView(View):
    """View para gerenciar perfil do usuário"""
    template_name = 'portais/lojista/perfil.html'
    
    def get(self, request, marca=None):
        # Verificar autenticação
        if not request.session.get('lojista_authenticated'):
            return redirect('lojista:login')
        
        # Buscar dados do usuário
        usuario_id = request.session.get('lojista_usuario_id')
        usuario_data = {}
        lojas_vinculadas = []
        
        if usuario_id:
            try:
                usuario = PortalUsuario.objects.get(id=usuario_id)
                usuario_data = {
                    'nome': usuario.nome,
                    'email': usuario.email,
                    'telefone': '',  # PortalUsuario não tem telefone
                    'cargo': '',     # PortalUsuario não tem cargo
                    'usuario': usuario.email,  # Email como username
                }
                
                # Obter lojas vinculadas usando serviço centralizado
                from portais.controle_acesso.filtros import FiltrosAcessoService
                lojas_vinculadas = FiltrosAcessoService.obter_lojas_acessiveis(usuario)
                
            except PortalUsuario.DoesNotExist:
                messages.error(request, 'Usuário não encontrado.')
        
        context = {
            'usuario': usuario_data,
            'lojas_vinculadas': lojas_vinculadas,
            'current_page': 'perfil'
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request):
        # Verificar autenticação
        if not request.session.get('lojista_authenticated'):
            return redirect('lojista:login')
        
        usuario_id = request.session.get('lojista_usuario_id')
        
        if not usuario_id:
            messages.error(request, 'Sessão inválida.')
            return redirect('lojista:login')
        
        try:
            usuario = PortalUsuario.objects.get(id=usuario_id)
            
            # Atualizar dados do usuário (apenas nome, pois PortalUsuario só tem nome e email)
            usuario.nome = request.POST.get('nome', '').strip()
            
            # Validar email se foi alterado
            novo_email = request.POST.get('email', '').strip()
            if novo_email != usuario.email:
                # Verificar se email já existe
                if PortalUsuario.objects.filter(email=novo_email).exclude(id=usuario_id).exists():
                    messages.error(request, 'Este e-mail já está sendo usado por outro usuário.')
                    return self.get(request)
                
                usuario.email = novo_email
                # Atualizar sessão se email mudou
                request.session['lojista_usuario_nome'] = usuario.nome
                request.session['lojista_usuario_email'] = usuario.email
            
            usuario.save()
            
            messages.success(request, 'Perfil atualizado com sucesso!')
            
        except PortalUsuario.DoesNotExist:
            messages.error(request, 'Usuário não encontrado.')
        except Exception as e:
            messages.error(request, f'Erro ao atualizar perfil: {str(e)}')
        
        return self.get(request)


class LojistaPrimeiroAcessoView(View):
    """View para primeiro acesso do usuário lojista com token"""
    template_name = 'portais/lojista/primeiro_acesso.html'
    
    def get(self, request, token, marca=None):
        try:
            usuario = PortalUsuario.objects.get(
                token_primeiro_acesso=token,
                primeiro_acesso_expira__gt=datetime.now()
            )
        except PortalUsuario.DoesNotExist:
            messages.error(request, 'Token inválido ou expirado.')
            return redirect('lojista:login')
        
        context = {
            'usuario': usuario,
            'token': token,
            'marca': marca
        }
        return render(request, self.template_name, context)
    
    def post(self, request, token, marca=None):
        try:
            usuario = PortalUsuario.objects.get(
                token_primeiro_acesso=token,
                primeiro_acesso_expira__gt=datetime.now()
            )
        except PortalUsuario.DoesNotExist:
            messages.error(request, 'Token inválido ou expirado.')
            return redirect('lojista:login')
        
        senha_atual = request.POST.get('senha_temporaria')
        nova_senha = request.POST.get('nova_senha')
        confirmar_senha = request.POST.get('confirmar_senha')
        
        # Validar senha atual
        if not usuario.verificar_senha(senha_atual):
            messages.error(request, 'Senha atual incorreta.')
        elif nova_senha != confirmar_senha:
            messages.error(request, 'Nova senha e confirmação não coincidem.')
        else:
            # Validar complexidade da nova senha
            from wallclub_core.utilitarios.senha_validator import validar_complexidade_senha
            senha_valida, mensagem_erro = validar_complexidade_senha(nova_senha)
            if not senha_valida:
                messages.error(request, mensagem_erro)
            else:
                # Atualizar senha e validar usuário
                usuario.set_password(nova_senha)
                usuario.senha_temporaria = False
                usuario.email_verificado = True
                usuario.token_primeiro_acesso = None
                usuario.primeiro_acesso_expira = None
                usuario.save()
                
                registrar_log('portais.lojista', f'PRIMEIRO_ACESSO - Concluído - Usuário: {usuario.email}')
                messages.success(request, 'Senha alterada com sucesso! Você já pode fazer login normalmente.')
                
                # Redirecionar para portal lojista com marca se disponível
                if marca:
                    return redirect(f'/portal_lojista/{marca}/')
                else:
                    return redirect('lojista:login')
        
        context = {
            'usuario': usuario,
            'token': token,
            'marca': marca
        }
        return render(request, self.template_name, context)
