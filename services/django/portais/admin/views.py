from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import connection
from django.core.paginator import Paginator
from functools import wraps
from portais.controle_acesso.decorators import require_admin_access
from portais.controle_acesso.models import PortalUsuario, PortalPermissao, PortalUsuarioAcesso
from portais.controle_acesso import require_funcionalidade
from datetime import datetime, timedelta
import secrets
import string
from wallclub_core.estr_organizacional.loja import Loja
from wallclub_core.estr_organizacional.grupo_economico import GrupoEconomico
from wallclub_core.estr_organizacional.canal import Canal
from wallclub_core.estr_organizacional.regional import Regional
from wallclub_core.estr_organizacional.vendedor import Vendedor
from ..controle_acesso.services import AutenticacaoService
from ..controle_acesso.decorators import require_admin_access
# Removido - usando controle_acesso
from ..controle_acesso.email_service import EmailService
from wallclub_core.utilitarios.log_control import registrar_log
from wallclub_core.decorators.api_decorators import handle_api_errors
from wallclub_core.database.queries import TransacoesQueries
from datetime import datetime, timedelta, date
from django.apps import apps
import secrets
import string
import json


def login_view(request):
    """View de login para o portal administrativo"""
    # Se já está logado, redirecionar para dashboard
    if request.session.get('portal_authenticated'):
        return redirect('portais_admin:dashboard')

    if request.method == 'POST':
        email = request.POST.get('email')
        senha = request.POST.get('senha')

        if not email or not senha:
            messages.error(request, 'Email e senha são obrigatórios.')
            return render(request, 'portais/admin/login.html')

        # Usar service centralizado de autenticação
        usuario, sucesso, mensagem = AutenticacaoService.autenticar_usuario(
            email, senha, 'admin'
        )

        if sucesso:
            # Criar sessão do portal
            AutenticacaoService.criar_sessao_portal(request, usuario, 'admin')
            registrar_log('portais.admin', f'LOGIN - Sucesso - Usuário: {usuario.nome} ({usuario.email}) - IP: {request.META.get("REMOTE_ADDR", "N/A")}')
            messages.success(request, f'Bem-vindo, {usuario.nome}!')
            return redirect('portais_admin:dashboard')
        else:
            registrar_log('portais.admin', f'LOGIN - Falha - Email: {email} - IP: {request.META.get("REMOTE_ADDR", "N/A")} - Erro: {mensagem}', nivel='ERROR')
            messages.error(request, mensagem)

    return render(request, 'portais/admin/login.html')

def logout_view(request):
    """Logout do portal administrativo"""
    usuario_nome = request.session.get('portal_usuario_nome', 'Usuário desconhecido')
    AutenticacaoService.limpar_sessao_portal(request)
    registrar_log('portais.admin', f'LOGOUT - Usuário: {usuario_nome} - IP: {request.META.get("REMOTE_ADDR", "N/A")}')
    messages.info(request, 'Logout realizado com sucesso.')
    return redirect('portais_admin:login')

@require_admin_access
def dashboard(request):
    """Dashboard principal do portal administrativo"""
    from django.db import connection
    from datetime import date
    from portais.controle_acesso.services import ControleAcessoService
    from portais.controle_acesso.filtros import FiltrosAcessoService

    usuario = request.portal_usuario

    # Obter resumo completo das permissões do usuário
    resumo_permissoes = ControleAcessoService.obter_resumo_permissoes(usuario)

    # Verificar níveis de acesso
    eh_admin_total = resumo_permissoes.get('acesso_global', False)
    eh_admin_canal = 'canal' in resumo_permissoes.get('vinculos', {})

    # Obter estatísticas filtradas baseadas nos vínculos do usuário
    estatisticas = FiltrosAcessoService.obter_estatisticas_filtradas(usuario)
    transacoes_hoje = estatisticas['transacoes_hoje']
    valor_hoje = estatisticas['valor_hoje']
    transacoes_mes = estatisticas['transacoes_mes']
    valor_mes = estatisticas['valor_mes']

    context = {
        'usuario': usuario,
        'resumo_permissoes': resumo_permissoes,
        'eh_admin_total': eh_admin_total,
        'eh_admin_canal': eh_admin_canal,
        'transacoes_hoje': transacoes_hoje,
        'valor_hoje': valor_hoje,
        'transacoes_mes': transacoes_mes,
        'valor_mes': valor_mes,
    }

    return render(request, 'portais/admin/dashboard.html', context)

def primeiro_acesso(request, token):
    """View para primeiro acesso do usuário com token"""
    from django.utils import timezone

    try:
        usuario = PortalUsuario.objects.get(
            token_primeiro_acesso=token,
            primeiro_acesso_expira__gt=datetime.now()
        )
    except PortalUsuario.DoesNotExist:
        messages.error(request, 'Token inválido ou expirado.')
        return redirect('portais_admin:login')

    if request.method == 'POST':
        senha_atual = request.POST.get('senha_atual')
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

                messages.success(request, 'Senha alterada com sucesso! Você já pode fazer login normalmente.')
                return redirect('/portal_lojista/')

    context = {
        'usuario': usuario,
        'token': token
    }
    return render(request, 'portais/admin/primeiro_acesso.html', context)

def configurar_2fa(request):
    """View para configurar autenticação de dois fatores"""
    if not hasattr(request, 'portal_usuario'):
        return redirect('portais_admin:login')

    usuario = request.portal_usuario

    if request.method == 'POST':
        acao = request.POST.get('acao')

        if acao == 'ativar':
            # Gerar secret key para 2FA
            import pyotp
            secret = pyotp.random_base32()
            usuario.secret_key_2fa = secret
            usuario.save()

            # Gerar QR Code
            totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
                name=usuario.email,
                issuer_name="WallClub"
            )

            context = {
                'usuario': usuario,
                'secret': secret,
                'qr_code_uri': totp_uri
            }
            return render(request, 'portais/admin/2fa_setup.html', context)

        elif acao == 'confirmar':
            codigo = request.POST.get('codigo')

            if usuario.secret_key_2fa:
                import pyotp
                totp = pyotp.TOTP(usuario.secret_key_2fa)

                if totp.verify(codigo):
                    usuario.two_factor_enabled = True
                    usuario.save()
                    messages.success(request, '2FA ativado com sucesso!')
                    return redirect('portais_admin:dashboard')
                else:
                    messages.error(request, 'Código inválido.')

        elif acao == 'desativar':
            usuario.two_factor_enabled = False
            usuario.secret_key_2fa = None
            usuario.save()
            messages.success(request, '2FA desativado.')
            return redirect('portais_admin:dashboard')

    context = {
        'usuario': usuario
    }
    return render(request, 'portais/admin/2fa_config.html', context)

@require_admin_access
def clientes_list(request):
    return render(request, 'portais/admin/clientes/list.html')

@require_admin_access
def cliente_detail(request, pk):
    return render(request, 'portais/admin/clientes/detail.html')

@require_admin_access
def transacoes_list(request):
    return render(request, 'portais/admin/transacoes/list.html')

@require_admin_access
def transacoes_export(request):
    return JsonResponse({'status': 'success'})

@require_admin_access
def relatorios_dashboard(request):
    return render(request, 'portais/admin/relatorios/dashboard.html')

@require_admin_access
def gestao_financeira(request):
    return render(request, 'portais/admin/relatorios/gestao_financeira.html')


# Placeholders para Fase 3 (Admin only)
@require_admin_access
def parametros_dashboard(request):
    if request.portal_usuario.tipo_usuario != 'admin':
        messages.error(request, 'Acesso negado. Apenas administradores totais.')
        return redirect('portais_admin:dashboard')
    return render(request, 'portais/admin/parametros/dashboard.html')


@require_admin_access
def parametros_canal(request):
    if request.portal_usuario.tipo_usuario != 'admin':
        messages.error(request, 'Acesso negado. Apenas administradores totais.')
        return redirect('portais_admin:dashboard')
    return render(request, 'portais/admin/parametros/canal.html')


@require_admin_access
def parametros_clientes(request):
    if request.portal_usuario.tipo_usuario != 'admin':
        messages.error(request, 'Acesso negado. Apenas administradores totais.')
        return redirect('portais_admin:dashboard')
    return render(request, 'portais/admin/parametros/clientes.html')

@require_admin_access
def vouchers_list(request):
    if request.portal_usuario.tipo_usuario != 'admin':
        messages.error(request, 'Acesso negado. Apenas administradores totais.')
        return redirect('portais_admin:dashboard')
    return render(request, 'portais/admin/vouchers/list.html')

@require_admin_access
def campanhas_list(request):
    if request.portal_usuario.tipo_usuario != 'admin':
        messages.error(request, 'Acesso negado. Apenas administradores totais.')
        return redirect('portais_admin:dashboard')
    return render(request, 'portais/admin/campanhas/list.html')

@require_admin_access
def indicadores_dashboard(request):
    return render(request, 'portais/admin/indicadores/dashboard.html')

def reset_senha_view(request, token):
    """View para reset de senha com token"""
    # Removido - usando controle_acesso
    from django.utils import timezone

    try:
        # Buscar usuário pelo token
        usuario = PortalUsuario.objects.get(
            token_reset_senha=token,
            reset_senha_expira__gt=datetime.now()
        )

        if request.method == 'POST':
            nova_senha = request.POST.get('nova_senha')
            confirmar_senha = request.POST.get('confirmar_senha')

            # Validar nova senha
            if nova_senha != confirmar_senha:
                messages.error(request, 'As senhas não coincidem.')
                return render(request, 'portais/admin/reset_senha.html', {'token': token})

            # Validar complexidade da nova senha
            from wallclub_core.utilitarios.senha_validator import validar_complexidade_senha
            senha_valida, mensagem_erro = validar_complexidade_senha(nova_senha)
            if not senha_valida:
                messages.error(request, mensagem_erro)
                return render(request, 'portais/admin/reset_senha.html', {'token': token})

            # Atualizar usuário
            usuario.set_password(nova_senha)
            usuario.token_reset_senha = None
            usuario.reset_senha_expira = None
            usuario.save()

            messages.success(request, 'Senha alterada com sucesso! Você já pode fazer login.')
            return redirect('portais_admin:login')

        return render(request, 'portais/admin/reset_senha.html', {'token': token})

    except PortalUsuario.DoesNotExist:
        messages.error(request, 'Token inválido ou expirado.')
        return redirect('portais_admin:login')

# Decorator simples para views AJAX
def ajax_admin_required(view_func):
    """Decorator para views AJAX que retorna JSON em caso de erro"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            from portais.controle_acesso.services import AutenticacaoService

            # Verificar se há usuário logado na sessão
            usuario = AutenticacaoService.obter_usuario_sessao(request)
            if not usuario:
                return JsonResponse({'error': 'Não autenticado'}, status=401)

            # Verificar se usuário pode acessar portal admin
            if not usuario.pode_acessar_portal('admin'):
                return JsonResponse({'error': 'Permissão negada'}, status=403)

            # Verificar se tem permissão admin usando controle de acesso centralizado
            from portais.controle_acesso.services import ControleAcessoService
            nivel_usuario = ControleAcessoService.obter_nivel_portal(usuario, 'admin')
            if nivel_usuario not in ['admin_total', 'admin_superusuario', 'admin_canal', 'admin', 'escrita']:
                return JsonResponse({'error': 'Permissão administrativa necessária'}, status=403)

            # Adicionar usuário ao request para uso nas views
            request.portal_usuario = usuario

            return view_func(request, *args, **kwargs)
        except Exception as e:
            return JsonResponse({'error': f'Erro interno: {str(e)}'}, status=500)
    return wrapper

# Views AJAX para carregar referências dinâmicas
@ajax_admin_required
@handle_api_errors
def ajax_lojas(request):
    """Retorna lista de lojas para select dinâmico"""
    from portais.controle_acesso.services import ControleAcessoService
    from django.db import connection

    usuario_logado = request.portal_usuario
    nivel_usuario = ControleAcessoService.obter_nivel_portal(usuario_logado, 'admin')

    with connection.cursor() as cursor:
        if nivel_usuario == 'admin_canal':
            # Filtrar lojas apenas do canal do usuário via hierarquia
            canal_ids = ControleAcessoService.obter_canais_usuario(usuario_logado)
            if not canal_ids:
                return JsonResponse([], safe=False)

            placeholders = ','.join(['%s'] * len(canal_ids))

            cursor.execute(f"""
                SELECT l.id, l.razao_social
                FROM loja l
                JOIN gruposeconomicos g ON l.GrupoEconomicoId = g.id
                JOIN vendedores v ON g.vendedorId = v.id
                JOIN regionais r ON v.regionalId = r.id
                WHERE l.razao_social IS NOT NULL
                AND r.canalId IN ({placeholders})
                ORDER BY l.razao_social
            """, canal_ids)
        else:
            # admin_total vê todas
            cursor.execute("""
                SELECT id, razao_social
                FROM loja
                WHERE razao_social IS NOT NULL
                ORDER BY razao_social
            """)

        lojas = cursor.fetchall()

    data = [{'id': loja[0], 'nome': f"{loja[1]} (ID: {loja[0]})"} for loja in lojas]
    return JsonResponse(data, safe=False)


@ajax_admin_required
@handle_api_errors
def ajax_grupos_economicos(request):
    """Retorna lista de grupos econômicos para select dinâmico"""
    from portais.controle_acesso.services import ControleAcessoService
    from portais.controle_acesso.services import AutenticacaoService

    usuario_logado = AutenticacaoService.obter_usuario_sessao(request)
    nivel_usuario = ControleAcessoService.obter_nivel_portal(usuario_logado, 'admin')

    with connection.cursor() as cursor:
        if nivel_usuario == 'admin_canal':
            # Filtrar apenas grupos econômicos do canal do usuário via hierarquia
            canal_ids = ControleAcessoService.obter_canais_usuario(usuario_logado)
            if not canal_ids:
                return JsonResponse([], safe=False)

            placeholders = ','.join(['%s'] * len(canal_ids))

            cursor.execute(f"""
                SELECT DISTINCT ge.id, ge.nome, ge.vendedorId
                FROM gruposeconomicos ge
                JOIN vendedores v ON ge.vendedorId = v.id
                JOIN regionais r ON v.regionalId = r.id
                WHERE ge.nome IS NOT NULL
                AND r.canalId IN ({placeholders})
                ORDER BY ge.nome
            """, canal_ids)
        else:
            # admin_total vê todos
            cursor.execute("""
                SELECT id, nome, vendedorId
                FROM gruposeconomicos
                WHERE nome IS NOT NULL
                ORDER BY nome
            """)

        grupos = cursor.fetchall()

    data = [{'id': grupo[0], 'nome': f"{grupo[1]} (Vendedor: {grupo[2]})"} for grupo in grupos]
    return JsonResponse(data, safe=False)


@ajax_admin_required
@handle_api_errors
def ajax_canais(request):
    """Retorna lista de canais para select dinâmico"""
    from portais.controle_acesso.services import ControleAcessoService

    usuario_logado = request.portal_usuario
    nivel_usuario = ControleAcessoService.obter_nivel_portal(usuario_logado, 'admin')

    with connection.cursor() as cursor:
        if nivel_usuario == 'admin_canal':
            # Filtrar apenas o canal do usuário
            canal_ids = ControleAcessoService.obter_canais_usuario(usuario_logado)
            if not canal_ids:
                return JsonResponse([], safe=False)

            placeholders = ','.join(['%s'] * len(canal_ids))

            cursor.execute(f"""
                SELECT id, nome
                FROM canal
                WHERE nome IS NOT NULL
                AND id IN ({placeholders})
                ORDER BY nome
            """, canal_ids)
        else:
            # admin_total e admin_superusuario veem todos
            cursor.execute("""
                SELECT id, nome
                FROM canal
                WHERE nome IS NOT NULL
                ORDER BY nome
            """)

        canais = cursor.fetchall()

    data = [{'id': canal[0], 'nome': f"{canal[1]}"} for canal in canais]
    return JsonResponse(data, safe=False)


@ajax_admin_required
@handle_api_errors
def ajax_regionais(request):
    """Retorna lista de regionais para select dinâmico"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, nome, canalId
            FROM regionais
            WHERE nome IS NOT NULL
            ORDER BY nome
        """)
        regionais = cursor.fetchall()

    data = [{'id': regional[0], 'nome': f"{regional[1]} (Canal: {regional[2]})"} for regional in regionais]
    return JsonResponse(data, safe=False)


@ajax_admin_required
@handle_api_errors
def ajax_vendedores(request):
    """Retorna lista de vendedores para select dinâmico"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, nome, regionalId
            FROM vendedores
            WHERE nome IS NOT NULL
            ORDER BY nome
        """)
        vendedores = cursor.fetchall()

    data = [{'id': vendedor[0], 'nome': f"{vendedor[1]} (Regional: {vendedor[2]})"} for vendedor in vendedores]
    return JsonResponse(data, safe=False)


@require_admin_access
def usuario_portais_ajax(request, pk):
    """Retorna permissões de portais do usuário via AJAX"""
    try:
        usuario = get_object_or_404(PortalUsuario, id=pk)

        # Buscar permissões específicas
        permissoes = PortalPermissao.objects.filter(usuario=usuario)
        portais_com_permissao = [p.portal for p in permissoes]

        return JsonResponse({
            'portais': portais_com_permissao,
            'usuario_id': usuario.id,
            'usuario_nome': usuario.nome
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
