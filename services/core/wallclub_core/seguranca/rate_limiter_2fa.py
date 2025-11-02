"""
Rate Limiter específico para Login e 2FA
Controles por CPF, IP e Device Fingerprint
"""
from django.core.cache import cache
from datetime import datetime, timedelta
from wallclub_core.utilitarios.log_control import registrar_log


class Login2FARateLimiter:
    """Rate limiter específico para login e 2FA"""

    # Limites de login por CPF
    MAX_LOGIN_ATTEMPTS_CPF = 5  # tentativas por hora
    LOGIN_BLOCK_DURATION = 3600  # 1 hora

    # Limites de 2FA
    MAX_2FA_REQUESTS = 3  # solicitações por sessão
    OTP_COOLDOWN = 60  # 60 segundos entre códigos
    MAX_2FA_VALIDATIONS = 5  # validações por hora

    # Limites por device fingerprint
    MAX_CPFS_PER_DEVICE = 5  # CPFs diferentes por dia

    # Limites por IP
    MAX_LOGIN_ATTEMPTS_IP = 10  # tentativas por hora

    @classmethod
    def check_login_cpf(cls, cpf: str) -> tuple:
        """
        Verifica rate limit de login por CPF

        Returns:
            tuple: (allowed: bool, attempts_remaining: int, retry_after: int)
        """
        cache_key = f"login_cpf:{cpf}"
        attempts = cache.get(cache_key, 0)

        if attempts >= cls.MAX_LOGIN_ATTEMPTS_CPF:
            registrar_log('comum.seguranca',
                f"Login bloqueado por rate limit - CPF: {cpf}, tentativas: {attempts}",
                nivel='WARNING')
            return False, 0, cls.LOGIN_BLOCK_DURATION

        # Incrementar contador
        if attempts == 0:
            cache.set(cache_key, 1, timeout=cls.LOGIN_BLOCK_DURATION)
            registrar_log('comum.seguranca',
                f"Rate limiter iniciado: CPF={cpf[:3]}***, tentativas=1/{cls.MAX_LOGIN_ATTEMPTS_CPF}",
                nivel='DEBUG')
        else:
            cache.incr(cache_key)
            new_attempts = attempts + 1
            registrar_log('comum.seguranca',
                f"Rate limiter incrementado: CPF={cpf[:3]}***, tentativas={new_attempts}/{cls.MAX_LOGIN_ATTEMPTS_CPF}",
                nivel='WARNING' if new_attempts >= 3 else 'DEBUG')

        remaining = cls.MAX_LOGIN_ATTEMPTS_CPF - (attempts + 1)
        return True, remaining, 0

    @classmethod
    def check_login_ip(cls, ip_address: str) -> tuple:
        """
        Verifica rate limit de login por IP

        Returns:
            tuple: (allowed: bool, retry_after: int)
        """
        cache_key = f"login_ip:{ip_address}"
        attempts = cache.get(cache_key, 0)

        if attempts >= cls.MAX_LOGIN_ATTEMPTS_IP:
            registrar_log('comum.seguranca',
                f"Login bloqueado por rate limit - IP: {ip_address}, tentativas: {attempts}",
                nivel='WARNING')
            return False, cls.LOGIN_BLOCK_DURATION

        # Incrementar contador
        if attempts == 0:
            cache.set(cache_key, 1, timeout=cls.LOGIN_BLOCK_DURATION)
        else:
            cache.incr(cache_key)

        return True, 0

    @classmethod
    def check_device_fingerprint(cls, device_fingerprint: str, cpf: str) -> tuple:
        """
        Verifica se device tenta logar com muitos CPFs diferentes

        Returns:
            tuple: (allowed: bool, message: str)
        """
        cache_key = f"device_cpfs:{device_fingerprint}"
        cpfs_today = cache.get(cache_key, set())

        if isinstance(cpfs_today, str):
            cpfs_today = set([cpfs_today])

        if cpf not in cpfs_today and len(cpfs_today) >= cls.MAX_CPFS_PER_DEVICE:
            registrar_log('comum.seguranca',
                f"Device tentando múltiplos CPFs - Device: {device_fingerprint[:16]}, CPFs: {len(cpfs_today)}",
                nivel='WARNING')
            return False, f"Dispositivo bloqueado. Max {cls.MAX_CPFS_PER_DEVICE} CPFs/dia"

        # Adicionar CPF ao set
        cpfs_today.add(cpf)
        cache.set(cache_key, cpfs_today, timeout=86400)  # 24 horas

        return True, ""

    @classmethod
    def check_2fa_cooldown(cls, cliente_id: int) -> tuple:
        """
        Verifica cooldown entre solicitações de código 2FA

        Returns:
            tuple: (allowed: bool, retry_after: int)
        """
        cache_key = f"2fa_cooldown:{cliente_id}"
        last_request = cache.get(cache_key)

        if last_request:
            elapsed = (datetime.now() - last_request).total_seconds()
            if elapsed < cls.OTP_COOLDOWN:
                retry_after = int(cls.OTP_COOLDOWN - elapsed)
                return False, retry_after

        # Registrar nova solicitação
        cache.set(cache_key, datetime.now(), timeout=cls.OTP_COOLDOWN)
        return True, 0

    @classmethod
    def check_2fa_requests_limit(cls, cliente_id: int) -> tuple:
        """
        Verifica limite de solicitações 2FA por sessão de login

        Returns:
            tuple: (allowed: bool, requests_remaining: int)
        """
        cache_key = f"2fa_requests:{cliente_id}"
        requests = cache.get(cache_key, 0)

        if requests >= cls.MAX_2FA_REQUESTS:
            registrar_log('comum.seguranca',
                f"Limite de solicitações 2FA atingido - Cliente: {cliente_id}",
                nivel='WARNING')
            return False, 0

        # Incrementar contador (expira em 30 min)
        if requests == 0:
            cache.set(cache_key, 1, timeout=1800)
        else:
            cache.incr(cache_key)

        remaining = cls.MAX_2FA_REQUESTS - (requests + 1)
        return True, remaining

    @classmethod
    def check_2fa_validations(cls, cliente_id: int) -> tuple:
        """
        Verifica limite de tentativas de validação 2FA por hora

        Returns:
            tuple: (allowed: bool, attempts_remaining: int)
        """
        cache_key = f"2fa_validations:{cliente_id}"
        attempts = cache.get(cache_key, 0)

        if attempts >= cls.MAX_2FA_VALIDATIONS:
            registrar_log('comum.seguranca',
                f"Limite de validações 2FA atingido - Cliente: {cliente_id}",
                nivel='WARNING')
            return False, 0

        # Incrementar contador
        if attempts == 0:
            cache.set(cache_key, 1, timeout=3600)  # 1 hora
        else:
            cache.incr(cache_key)

        remaining = cls.MAX_2FA_VALIDATIONS - (attempts + 1)
        return True, remaining

    @classmethod
    def reset_login_attempts(cls, cpf: str):
        """Reseta tentativas de login após sucesso"""
        cache_key = f"login_cpf:{cpf}"
        cache.delete(cache_key)
        registrar_log('comum.seguranca',
            f"Rate limiter resetado para CPF: {cpf[:3]}***",
            nivel='DEBUG')

    @classmethod
    def reset_2fa_session(cls, cliente_id: int):
        """Reseta contadores de 2FA após login bem-sucedido"""
        cache.delete(f"2fa_requests:{cliente_id}")
        cache.delete(f"2fa_cooldown:{cliente_id}")
