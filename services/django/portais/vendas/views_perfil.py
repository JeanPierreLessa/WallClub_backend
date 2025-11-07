"""
Views para perfil e troca de senha do portal de vendas
"""
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views import View
from .decorators import requer_checkout_vendedor
from portais.controle_acesso.models import PortalUsuario
from portais.controle_acesso.email_service import EmailService
from wallclub_core.utilitarios.log_control import registrar_log
import hashlib


@requer_checkout_vendedor
def perfil_view(request):
    """Exibir perfil do vendedor"""
    vendedor = request.vendedor
    
    context = {
        'vendedor': vendedor,
        'current_page': 'perfil'
    }
    
    return render(request, 'vendas/perfil.html', context)


class VendasTrocarSenhaView(View):
    """View para troca de senha com confirmação por token"""
    template_name = 'vendas/trocar_senha.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.session.get('vendas_authenticated'):
            return redirect('vendas:login')
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request):
        context = {
            'vendedor': request.vendedor,
            'current_page': 'perfil'
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        vendedor_id = request.session.get('vendedor_id')
        senha_atual = request.POST.get('senha_atual', '').strip()
        nova_senha = request.POST.get('nova_senha', '').strip()
        confirmar_senha = request.POST.get('confirmar_senha', '').strip()
        
        # Validações
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
            usuario = PortalUsuario.objects.get(id=vendedor_id)
            
            # Verificar senha atual
            if not usuario.verificar_senha(senha_atual):
                messages.error(request, 'Senha atual incorreta.')
                return self.get(request)
            
            # Gerar hash MD5 da nova senha
            nova_senha_hash = hashlib.md5(nova_senha.encode()).hexdigest()
            
            # Gerar token de confirmação
            token = usuario.gerar_token_troca_senha(nova_senha_hash)
            
            # Enviar email com token
            self._enviar_email_confirmacao(usuario, token)
            
            messages.success(request, 'Um token de confirmação foi enviado para seu email. Verifique sua caixa de entrada e digite o token para confirmar a alteração da senha.')
            return redirect('vendas:confirmar_troca_senha')
            
        except PortalUsuario.DoesNotExist:
            messages.error(request, 'Usuário não encontrado.')
            return redirect('vendas:login')
        except Exception as e:
            messages.error(request, f'Erro ao processar troca de senha: {str(e)}')
            return self.get(request)
    
    def _enviar_email_confirmacao(self, usuario, token):
        """Envia email com token de confirmação"""
        EmailService.enviar_email_token_troca_senha(usuario, token, validade_minutos=30, portal_destino='vendas')


class VendasConfirmarTrocaSenhaView(View):
    """View para confirmar troca de senha com token"""
    template_name = 'vendas/confirmar_troca_senha.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.session.get('vendas_authenticated'):
            return redirect('vendas:login')
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request):
        context = {
            'vendedor': request.vendedor,
            'current_page': 'perfil'
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        vendedor_id = request.session.get('vendedor_id')
        token_digitado = request.POST.get('token', '').strip()
        
        if not token_digitado:
            messages.error(request, 'Por favor, digite o token recebido por email.')
            return self.get(request)
        
        try:
            usuario = PortalUsuario.objects.get(id=vendedor_id)
            
            # Validar token
            if not usuario.validar_token_troca_senha(token_digitado):
                messages.error(request, 'Token inválido ou expirado. Solicite uma nova alteração de senha.')
                return redirect('vendas:trocar_senha')
            
            # Aplicar nova senha
            if usuario.confirmar_troca_senha(portal_destino='vendas'):
                messages.success(request, 'Senha alterada com sucesso!')
                registrar_log('portais.vendas', f'Senha alterada com sucesso para vendedor {usuario.email}')
                return redirect('vendas:perfil')
            else:
                messages.error(request, 'Erro ao aplicar nova senha.')
                return self.get(request)
            
        except PortalUsuario.DoesNotExist:
            messages.error(request, 'Usuário não encontrado.')
            return redirect('vendas:login')
        except Exception as e:
            messages.error(request, f'Erro ao confirmar troca de senha: {str(e)}')
            return self.get(request)
