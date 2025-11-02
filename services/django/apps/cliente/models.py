from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from datetime import timedelta, datetime
import hashlib


class Cliente(models.Model):
    """
    Modelo para clientes (usuários dos apps móveis).
    Separado completamente do sistema de usuários Django.
    Suporta multi-marca: mesmo CPF pode existir em diferentes canais.
    """
    id = models.BigAutoField(primary_key=True)
    cpf = models.CharField(max_length=11)
    canal_id = models.IntegerField()
    hash_senha = models.CharField(max_length=256)
    nome = models.CharField(max_length=256)
    celular = models.CharField(max_length=15)
    celular_validado_em = models.DateTimeField(null=True, blank=True, help_text='Data da última validação do celular (90 dias)')
    email = models.EmailField(null=True, blank=True)

    # Campos específicos do negócio
    firebase_token = models.CharField(max_length=256, null=True, blank=True)
    nome_mae = models.CharField(max_length=256, null=True, blank=True)
    dt_nascimento = models.DateField(null=True, blank=True)
    signo = models.CharField(max_length=50, null=True, blank=True)
    qtd_semapp = models.IntegerField(default=0)

    # Campos de controle
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)

    # Campos de cadastro completo (Release 3.1.0)
    cadastro_completo = models.BooleanField(default=False, help_text='Cliente finalizou cadastro no app')
    cadastro_iniciado_em = models.DateTimeField(null=True, blank=True, help_text='Data do primeiro acesso ao cadastro')
    cadastro_concluido_em = models.DateTimeField(null=True, blank=True, help_text='Data da conclusão do cadastro')
    
    # Bypass 2FA para testes (Release 3.1.0)
    bypass_2fa = models.BooleanField(default=False, help_text='Bypass 2FA para testes Apple/Google (uso temporário)')

    class Meta:
        db_table = 'cliente'
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        unique_together = ('cpf', 'canal_id')

    def set_password(self, raw_password):
        """Define a senha com hash seguro"""
        self.hash_senha = make_password(raw_password)

    def check_password(self, raw_password):
        """Verifica se a senha está correta"""
        return check_password(raw_password, self.hash_senha)

    def update_last_login(self):
        """Atualiza o último login"""
        from datetime import datetime
        self.last_login = datetime.now()
        self.save(update_fields=['last_login'])

    # Métodos necessários para compatibilidade com Django REST Framework
    @property
    def is_authenticated(self):
        """Sempre True para clientes ativos (necessário para DRF)"""
        return self.is_active

    @property
    def is_anonymous(self):
        """Sempre False para clientes (necessário para DRF)"""
        return False

    def __str__(self):
        return f"{self.nome} ({self.cpf}) - Canal {self.canal_id}"


class ClienteAuth(models.Model):
    """
    DEPRECATED: Será removido após container legacy morrer.
    Usar: apps.cliente.models_autenticacao (ClienteAutenticacao, TentativaLogin, Bloqueio)

    Modelo legado para controle de autenticação.
    NÃO USAR EM CÓDIGO NOVO.
    """
    cliente = models.OneToOneField(Cliente, on_delete=models.CASCADE, related_name='auth')
    reset_token = models.CharField(max_length=256, null=True, blank=True)
    reset_token_expires = models.DateTimeField(null=True, blank=True)
    failed_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    last_failed_login = models.DateTimeField(null=True, blank=True)
    last_ip = models.GenericIPAddressField(null=True, blank=True)

    # Campos para sistema de senhas forte
    senha_temporaria = models.BooleanField(default=False, help_text="DEPRECATED: Não usado no novo fluxo. Toda senha é via SMS com revalidação 30 dias")
    last_password_change = models.DateTimeField(null=True, blank=True, help_text="Data da última troca de senha")

    class Meta:
        db_table = 'cliente_auth'
        verbose_name = 'Autenticação de Cliente'
        verbose_name_plural = 'Autenticações de Clientes'

    def generate_reset_token(self):
        """Gera token para reset de senha"""
        self.reset_token = str(uuid.uuid4())
        from datetime import datetime, timedelta
        self.reset_token_expires = datetime.now() + timedelta(hours=24)
        self.save(update_fields=['reset_token', 'reset_token_expires'])
        return self.reset_token

    def is_reset_token_valid(self, token):
        """Verifica se o token de reset é válido"""
        if not self.reset_token or not self.reset_token_expires:
            return False

        if self.reset_token != token:
            return False

        from datetime import datetime
        if datetime.now() > self.reset_token_expires:
            return False

        return True

    def clear_reset_token(self):
        """Limpa o token de reset após uso"""
        self.reset_token = None
        self.reset_token_expires = None
        self.save(update_fields=['reset_token', 'reset_token_expires'])

    def is_locked(self):
        """Verifica se a conta está bloqueada"""
        if not self.locked_until:
            return False

        from datetime import datetime
        return datetime.now() < self.locked_until

    def get_unlock_time(self):
        """Retorna quantos minutos faltam para desbloquear a conta"""
        if not self.locked_until:
            return 0

        from datetime import datetime
        delta = self.locked_until - datetime.now()
        minutos = int(delta.total_seconds() / 60)
        return max(0, minutos)

    def lock_account(self, minutes=30):
        """Bloqueia a conta por X minutos"""
        from datetime import datetime, timedelta
        self.locked_until = datetime.now() + timedelta(minutes=minutes)
        self.save(update_fields=['locked_until'])

    def unlock_account(self):
        """Desbloqueia a conta"""
        self.locked_until = None
        self.failed_attempts = 0
        self.save(update_fields=['locked_until', 'failed_attempts'])

    def record_failed_attempt(self):
        """Registra tentativa de login falhada - USA INCREMENTO ATÔMICO"""
        from datetime import datetime, timedelta
        from django.db.models import F
        from wallclub_core.utilitarios.log_control import registrar_log

        # INCREMENTO ATÔMICO: usa F() para evitar race condition
        # Atualiza diretamente no banco sem ler o valor antes
        ClienteAuth.objects.filter(id=self.id).update(
            failed_attempts=F('failed_attempts') + 1,
            last_failed_login=datetime.now()
        )

        # Recarregar do banco para ter o valor atualizado
        self.refresh_from_db()

        registrar_log('apps.cliente',
            f"[ClienteAuth] failed_attempts atualizado atomicamente para {self.failed_attempts} (cliente_id={self.cliente_id})")

        # Bloquear após 5 tentativas
        if self.failed_attempts >= 5:
            self.locked_until = datetime.now() + timedelta(minutes=30)
            self.save(update_fields=['locked_until'])
            registrar_log('apps.cliente',
                f"[ClienteAuth] Conta bloqueada (cliente_id={self.cliente_id}, tentativas={self.failed_attempts})", nivel='WARNING')

    def record_successful_login(self, ip_address=None):
        """Registra login bem-sucedido"""
        self.failed_attempts = 0
        if ip_address:
            self.last_ip = ip_address
        self.save(update_fields=['failed_attempts', 'last_ip'])

    def __str__(self):
        return f"Auth para {self.cliente}"


class SenhaHistorico(models.Model):
    """
    Histórico de senhas dos clientes para evitar reutilização.
    Mantém as últimas 3 senhas de cada cliente.
    """
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='historico_senhas')
    password_hash = models.CharField(max_length=256)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cliente_senha_historico'
        verbose_name = 'Histórico de Senha'
        verbose_name_plural = 'Históricos de Senhas'
        ordering = ['-criado_em']
        indexes = [
            models.Index(fields=['cliente', '-criado_em']),
        ]

    def __str__(self):
        return f"Senha de {self.cliente.cpf} em {self.criado_em.strftime('%d/%m/%Y %H:%M')}"


class ClienteJWTToken(models.Model):
    """
    Auditoria e controle de tokens JWT customizados para clientes.
    Permite revogação, rastreamento de uso e segurança.
    """
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='jwt_tokens')
    jti = models.CharField(max_length=36, unique=True, db_index=True, help_text="JWT ID único")
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    token_type = models.CharField(max_length=20, default='access', db_index=True, help_text="Tipo: access ou refresh")
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    # Metadados de segurança
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        db_table = 'cliente_jwt_tokens'
        verbose_name = 'Token JWT Cliente'
        verbose_name_plural = 'Tokens JWT Clientes'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['cliente', 'is_active']),
            models.Index(fields=['jti']),
            models.Index(fields=['expires_at', 'is_active']),
        ]

    def is_valid(self):
        """Verifica se o token ainda é válido"""
        return (
            self.is_active and
            self.expires_at > datetime.now() and
            not self.revoked_at
        )

    def record_usage(self, ip_address=None):
        """Registra uso do token"""
        from datetime import datetime
        self.last_used = datetime.now()
        if ip_address:
            self.ip_address = ip_address
        self.save(update_fields=['last_used', 'ip_address'])

    def revoke(self, reason=None):
        """Revoga o token"""
        self.is_active = False
        from datetime import datetime
        self.revoked_at = datetime.now()
        self.save(update_fields=['is_active', 'revoked_at'])

    @classmethod
    def create_from_token(cls, cliente, token, jti, expires_at, token_type='access', ip_address=None, user_agent=None):
        """Cria registro de auditoria a partir de token JWT"""
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        return cls.objects.create(
            cliente=cliente,
            jti=jti,
            token_hash=token_hash,
            token_type=token_type,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )

    @classmethod
    def validate_token(cls, token, jti):
        """Valida token JWT contra registro de auditoria"""
        try:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            jwt_record = cls.objects.get(
                jti=jti,
                token_hash=token_hash,
                is_active=True
            )

            if jwt_record.is_valid():
                return jwt_record
            else:
                return None

        except cls.DoesNotExist:
            return None

    def __str__(self):
        status = "✅" if self.is_valid() else "❌"
        return f"{status} JWT {self.cliente.cpf} - {self.jti[:8]}..."


class Notificacao(models.Model):
    """
    Modelo para notificações enviadas aos clientes.
    Mapeamento da tabela notificacoes existente.
    """
    id = models.BigAutoField(primary_key=True)
    cpf = models.CharField(max_length=11)
    canal_id = models.IntegerField()
    titulo = models.CharField(max_length=100, null=True)
    mensagem = models.CharField(max_length=500, null=True)
    tipo = models.CharField(max_length=50, default='transacao')
    data_envio = models.DateTimeField()
    lida = models.BooleanField(default=False)
    dados_adicionais = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'notificacoes'  # Nome atual da tabela no banco
        managed = False  # Não gerenciar migrações para esta tabela
        ordering = ['-data_envio']

    def __str__(self):
        return f"Notificação {self.id} - {self.cpf} - {self.titulo}"

    @classmethod
    def listar_notificacoes(cls, cpf, canal_id, limite=30):
        """
        Lista as últimas notificações de um cliente por CPF e canal_id

        Args:
            cpf (str): CPF do cliente
            canal_id (int): ID do canal
            limite (int): Quantidade máxima de notificações a retornar

        Returns:
            QuerySet: Últimas notificações do cliente
        """
        return cls.objects.filter(
            cpf=cpf,
            canal_id=canal_id
        ).order_by('-data_envio')[:limite]

    @classmethod
    def criar_notificacao(cls, cpf, canal_id, titulo, mensagem, tipo='transacao', dados_adicionais=None):
        """
        Cria uma nova notificação para o cliente

        Args:
            cpf (str): CPF do cliente
            canal_id (int): ID do canal
            titulo (str): Título da notificação
            mensagem (str): Conteúdo da notificação
            tipo (str): Tipo da notificação (default: 'transacao')
            dados_adicionais (dict): Dados adicionais em formato JSON

        Returns:
            Notificacao: Objeto da notificação criada
        """
        from django.utils import timezone

        return cls.objects.create(
            cpf=cpf,
            canal_id=canal_id,
            titulo=titulo,
            mensagem=mensagem,
            tipo=tipo,
            data_envio=timezone.now(),
            lida=False,
            dados_adicionais=dados_adicionais
        )

    @classmethod
    def marcar_como_lida(cls, notificacao_ids, cpf, canal_id):
        """
        Marca uma ou mais notificações como lidas

        Args:
            notificacao_ids (list ou int): ID(s) da(s) notificação(ões)
            cpf (str): CPF do cliente (segurança)
            canal_id (int): ID do canal (segurança)

        Returns:
            dict: {'sucesso': bool, 'quantidade_atualizada': int}
        """
        # Garantir que notificacao_ids seja uma lista
        if isinstance(notificacao_ids, int):
            notificacao_ids = [notificacao_ids]

        # Atualizar apenas notificações do cliente autenticado
        quantidade_atualizada = cls.objects.filter(
            id__in=notificacao_ids,
            cpf=cpf,
            canal_id=canal_id,
            lida=False
        ).update(lida=True)

        return {
            'sucesso': True,
            'quantidade_atualizada': quantidade_atualizada
        }

