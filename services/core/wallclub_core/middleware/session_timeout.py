"""
Middleware para controle de timeout de sessão dos portais.
Implementa logout automático por inatividade.
"""

import time
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from django.conf import settings
from wallclub_core.utilitarios.log_control import registrar_log


class PortalSessionTimeoutMiddleware:
    """
    Middleware que controla timeout de sessão dos portais administrativos.

    Funcionalidades:
    - Logout automático após período de inatividade
    - Renovação automática da sessão em requests ativos
    - Logs de timeout para auditoria
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # Timeout em segundos (configurado via PORTAL_SESSION_TIMEOUT_MINUTES)
        self.timeout_seconds = getattr(settings, 'SESSION_COOKIE_AGE', 1800)  # Default 30min

    def __call__(self, request):
        # Verificar se é request de portal
        if self._is_portal_request(request):
            # Verificar timeout apenas se usuário logado
            if self._has_portal_session(request):
                if self._is_session_expired(request):
                    return self._handle_session_timeout(request)
                else:
                    # Atualizar timestamp da última atividade
                    self._update_last_activity(request)

        response = self.get_response(request)
        return response

    def _is_portal_request(self, request):
        """Verifica se é request para portal administrativo"""
        portal_paths = ['/portal_admin/', '/portal_lojista/', '/portal_corporativo/']
        return any(request.path.startswith(path) for path in portal_paths)

    def _has_portal_session(self, request):
        """Verifica se há sessão ativa do portal"""
        return bool(request.session.get('portal_usuario_id'))

    def _is_session_expired(self, request):
        """Verifica se a sessão expirou por inatividade"""
        last_activity = request.session.get('last_activity')

        if not last_activity:
            # Primeira vez - definir timestamp atual
            self._update_last_activity(request)
            return False

        # Calcular tempo de inatividade
        current_time = time.time()
        inactive_time = current_time - last_activity

        return inactive_time > self.timeout_seconds

    def _update_last_activity(self, request):
        """Atualiza timestamp da última atividade"""
        request.session['last_activity'] = time.time()

    def _handle_session_timeout(self, request):
        """Processa timeout da sessão"""
        # Obter dados do usuário antes de limpar sessão
        usuario_nome = request.session.get('portal_usuario_nome', 'Usuário desconhecido')
        usuario_id = request.session.get('portal_usuario_id', 'N/A')

        # Log de timeout
        registrar_log(
            'comum.middleware',
            f'Sessão expirada por inatividade - Usuário: {usuario_nome} (ID: {usuario_id}) - '
            f'IP: {request.META.get("REMOTE_ADDR", "N/A")} - '
            f'Timeout: {self.timeout_seconds}s',
            nivel='WARNING'
        )

        # Limpar sessão
        request.session.flush()

        # Mensagem para usuário
        messages.warning(
            request,
            f'Sua sessão expirou após {self.timeout_seconds // 60} minutos de inatividade. '
            'Faça login novamente.'
        )

        # Redirecionar para login do portal apropriado
        if request.path.startswith('/portal_admin/'):
            return redirect('portais_admin:login')
        elif request.path.startswith('/portal_lojista/'):
            return redirect('portais_lojista:login')
        elif request.path.startswith('/portal_corporativo/'):
            return redirect('portais_corporativo:login')
        else:
            # Fallback para admin
            return redirect('portais_admin:login')


class PortalSessionSecurityMiddleware:
    """
    Middleware adicional para segurança de sessão dos portais.

    Funcionalidades:
    - Validação de IP (opcional)
    - Detecção de mudança de User-Agent
    - Logs de segurança
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # Configurações de segurança
        self.check_ip_change = getattr(settings, 'PORTAL_CHECK_IP_CHANGE', False)
        self.check_user_agent_change = getattr(settings, 'PORTAL_CHECK_USER_AGENT_CHANGE', True)

    def __call__(self, request):
        # Verificar apenas requests de portal com sessão ativa
        if self._is_portal_request(request) and self._has_portal_session(request):
            if self._detect_session_hijacking(request):
                return self._handle_security_violation(request)

        response = self.get_response(request)
        return response

    def _is_portal_request(self, request):
        """Verifica se é request para portal administrativo"""
        portal_paths = ['/portal_admin/', '/portal_lojista/', '/portal_corporativo/']
        return any(request.path.startswith(path) for path in portal_paths)

    def _has_portal_session(self, request):
        """Verifica se há sessão ativa do portal"""
        return bool(request.session.get('portal_usuario_id'))

    def _detect_session_hijacking(self, request):
        """Detecta possível sequestro de sessão"""
        current_ip = request.META.get('REMOTE_ADDR', '')
        current_user_agent = request.META.get('HTTP_USER_AGENT', '')

        session_ip = request.session.get('session_ip')
        session_user_agent = request.session.get('session_user_agent')

        # Primeira vez - armazenar dados da sessão
        if not session_ip or not session_user_agent:
            request.session['session_ip'] = current_ip
            request.session['session_user_agent'] = current_user_agent
            return False

        # Verificar mudança de IP (se habilitado)
        if self.check_ip_change and session_ip != current_ip:
            registrar_log(
                'comum.middleware',
                f'Mudança de IP detectada - Usuário: {request.session.get("portal_usuario_nome", "N/A")} - '
                f'IP Original: {session_ip} - IP Atual: {current_ip}',
                nivel='WARNING'
            )
            return True

        # Verificar mudança de User-Agent (se habilitado)
        if self.check_user_agent_change and session_user_agent != current_user_agent:
            registrar_log(
                'comum.middleware',
                f'Mudança de User-Agent detectada - Usuário: {request.session.get("portal_usuario_nome", "N/A")} - '
                f'UA Original: {session_user_agent[:100]}... - UA Atual: {current_user_agent[:100]}...',
                nivel='WARNING'
            )
            return True

        return False

    def _handle_security_violation(self, request):
        """Processa violação de segurança"""
        # Obter dados do usuário
        usuario_nome = request.session.get('portal_usuario_nome', 'Usuário desconhecido')
        usuario_id = request.session.get('portal_usuario_id', 'N/A')

        # Log crítico de segurança
        registrar_log(
            'comum.middleware',
            f'POSSÍVEL SEQUESTRO DE SESSÃO - Usuário: {usuario_nome} (ID: {usuario_id}) - '
            f'IP: {request.META.get("REMOTE_ADDR", "N/A")} - '
            f'User-Agent: {request.META.get("HTTP_USER_AGENT", "N/A")[:100]}...',
            nivel='ERROR'
        )

        # Limpar sessão por segurança
        request.session.flush()

        # Mensagem de segurança
        messages.error(
            request,
            'Atividade suspeita detectada. Sua sessão foi encerrada por segurança. '
            'Faça login novamente.'
        )

        # Redirecionar para login
        if request.path.startswith('/portal_admin/'):
            return redirect('portais_admin:login')
        elif request.path.startswith('/portal_lojista/'):
            return redirect('portais_lojista:login')
        elif request.path.startswith('/portal_corporativo/'):
            return redirect('portais_corporativo:login')
        else:
            return redirect('portais_admin:login')
