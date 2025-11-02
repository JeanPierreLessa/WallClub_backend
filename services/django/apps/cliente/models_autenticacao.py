"""
Models para sistema de autenticação persistente
Substitui cliente_auth (deprecated)
"""
from django.db import models
from apps.cliente.models import Cliente


class ClienteAutenticacao(models.Model):
    """
    Estado atual de autenticação por cliente (1:1)
    Usado para verificações rápidas de bloqueio e contadores
    """
    cliente = models.OneToOneField(
        Cliente,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='autenticacao'
    )
    
    # Estado atual de bloqueio
    bloqueado = models.BooleanField(
        default=False,
        db_index=True,
        help_text='Conta bloqueada agora?'
    )
    bloqueado_ate = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text='Bloqueio ativo até quando'
    )
    bloqueio_motivo = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text='limite_15min, limite_1h, rate_limit'
    )
    
    # Contadores atuais (resetados no login com sucesso)
    tentativas_15min = models.IntegerField(
        default=0,
        help_text='Tentativas nos últimos 15 minutos'
    )
    tentativas_1h = models.IntegerField(
        default=0,
        help_text='Tentativas na última hora'
    )
    tentativas_24h = models.IntegerField(
        default=0,
        help_text='Tentativas nas últimas 24 horas'
    )
    
    # Última atividade
    ultima_tentativa_em = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Última tentativa (sucesso ou falha)'
    )
    ultimo_sucesso_em = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Último login bem-sucedido'
    )
    ultimo_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text='Último IP usado'
    )
    
    # Auditoria
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cliente_autenticacao'
        verbose_name = 'Autenticação Cliente'
        verbose_name_plural = 'Autenticações Clientes'
        indexes = [
            models.Index(fields=['bloqueado', 'bloqueado_ate']),
        ]
    
    def __str__(self):
        return f"Auth {self.cliente.cpf}"
    
    def esta_bloqueado(self):
        """Verifica se está bloqueado agora"""
        if not self.bloqueado:
            return False
        
        if not self.bloqueado_ate:
            return False
        
        from datetime import datetime
        return datetime.now() < self.bloqueado_ate
    
    def resetar_tentativas(self):
        """Reseta contadores após login com sucesso"""
        self.tentativas_15min = 0
        self.tentativas_1h = 0
        self.tentativas_24h = 0
        self.bloqueado = False
        self.bloqueado_ate = None
        self.bloqueio_motivo = None


class TentativaLogin(models.Model):
    """
    Histórico completo de tentativas de login
    REUTILIZA tabela existente: cliente_auditoria_validacao_senha
    Usado para auditoria e compliance
    """
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tentativas_login',
        db_column='cliente_id',
        help_text='NULL se CPF não existe'
    )
    cpf = models.CharField(
        max_length=14,  # Tabela existente usa varchar(14)
        db_index=True,
        help_text='CPF usado na tentativa'
    )
    canal_id = models.IntegerField(
        db_index=True,
        help_text='Canal da tentativa'
    )
    
    # Resultado
    sucesso = models.BooleanField(
        db_index=True,
        help_text='Login bem-sucedido?'
    )
    motivo_falha = models.CharField(
        max_length=200,  # Tabela existente usa varchar(200)
        null=True,
        blank=True,
        help_text='senha_incorreta, cpf_invalido, bloqueado, etc'
    )
    
    # Metadados da requisição
    ip_address = models.CharField(  # Tabela existente usa varchar(45)
        max_length=45,
        db_index=True,
        help_text='IP da tentativa'
    )
    user_agent = models.TextField(
        null=True,
        blank=True
    )
    endpoint = models.CharField(
        max_length=200,
        help_text='Endpoint usado (já existe na tabela)'
    )
    
    # NOVOS CAMPOS (serão adicionados via ALTER TABLE)
    device_fingerprint = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text='Identificador do dispositivo'
    )
    estava_bloqueado = models.BooleanField(
        default=False,
        help_text='Tentou login estando bloqueado?'
    )
    tentativas_antes = models.IntegerField(
        null=True,
        blank=True,
        help_text='Quantas tentativas tinha antes desta'
    )
    gerou_bloqueio = models.BooleanField(
        default=False,
        db_index=True,
        help_text='Esta tentativa gerou bloqueio?'
    )
    
    # Auditoria (campo existente)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'cliente_auditoria_validacao_senha'
        verbose_name = 'Tentativa de Login'
        verbose_name_plural = 'Tentativas de Login'
        ordering = ['-timestamp']
        managed = False  # Tabela já existe
    
    def __str__(self):
        status = '✅' if self.sucesso else '❌'
        return f"{status} {self.cpf} - {self.timestamp.strftime('%d/%m/%Y %H:%M')}"


class Bloqueio(models.Model):
    """
    Histórico de bloqueios aplicados
    Usado para rastreabilidade e compliance
    """
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bloqueios',
        help_text='NULL se CPF não existe'
    )
    cpf = models.CharField(
        max_length=11,
        db_index=True
    )
    canal_id = models.IntegerField(
        db_index=True
    )
    
    # Tipo de bloqueio
    motivo = models.CharField(
        max_length=50,
        db_index=True,
        help_text='limite_15min, limite_1h, limite_24h, rate_limit_cpf, rate_limit_ip, manual'
    )
    tentativas_antes_bloqueio = models.IntegerField(
        help_text='Quantas tentativas acumuladas'
    )
    
    # Período do bloqueio
    bloqueado_em = models.DateTimeField(
        db_index=True
    )
    bloqueado_ate = models.DateTimeField(
        db_index=True
    )
    tempo_bloqueio_segundos = models.IntegerField(
        help_text='Duração do bloqueio'
    )
    
    # Desbloqueio
    desbloqueado_em = models.DateTimeField(
        null=True,
        blank=True,
        help_text='NULL = ainda bloqueado'
    )
    desbloqueado_por = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text='sistema, admin, login_sucesso, expiracao'
    )
    
    # Metadados
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text='IP que causou o bloqueio'
    )
    notificacao_enviada = models.BooleanField(
        default=False,
        help_text='WhatsApp enviado?'
    )
    
    # Status
    ativo = models.BooleanField(
        default=True,
        db_index=True,
        help_text='1=bloqueio ativo, 0=desbloqueado'
    )
    
    # Auditoria
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cliente_bloqueios'
        verbose_name = 'Bloqueio'
        verbose_name_plural = 'Bloqueios'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['cpf', 'ativo']),
            models.Index(fields=['cliente', 'ativo']),
            models.Index(fields=['bloqueado_ate']),
            models.Index(fields=['motivo', '-created_at']),
            models.Index(fields=['canal_id', '-created_at']),
        ]
    
    def __str__(self):
        status = '🔒' if self.ativo else '🔓'
        return f"{status} {self.cpf} - {self.motivo} - {self.bloqueado_em.strftime('%d/%m/%Y %H:%M')}"
