"""
Modelos OAuth 2.0 para WallClub.
Separados da autenticação básica para melhor organização.
"""
import secrets
import uuid
from django.db import models
from datetime import datetime, timedelta
from wallclub_core.utilitarios.log_control import registrar_log


class OAuthClient(models.Model):
    """Clientes OAuth 2.0 autorizados para acessar a API"""
    client_id = models.CharField(max_length=255, unique=True, db_index=True)
    client_secret = models.CharField(max_length=255)
    name = models.CharField(max_length=100)
    brand = models.CharField(max_length=50)  # wallclub, aclub, dotz
    is_active = models.BooleanField(default=True)
    allowed_scopes = models.CharField(max_length=500, default='read,write')
    rate_limit_per_hour = models.IntegerField(default=1000)
    
    # Controle de acesso por loja/grupo econômico
    loja_id = models.IntegerField(null=True, blank=True, db_index=True, help_text="Loja específica (se restrito)")
    grupo_economico_id = models.IntegerField(null=True, blank=True, db_index=True, help_text="Grupo econômico (se restrito)")
    nivel_acesso = models.CharField(
        max_length=20,
        choices=[
            ('LOJA', 'Restrito à Loja'),
            ('GRUPO', 'Grupo Econômico'),
            ('GLOBAL', 'Todas as lojas')
        ],
        default='GLOBAL',
        help_text="Nível de acesso do cliente OAuth"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'oauth_clients'
        verbose_name = 'OAuth Client'
        verbose_name_plural = 'OAuth Clients'
        ordering = ['-created_at']

    @classmethod
    def generate_client(cls, name, brand):
        """Gera um novo cliente OAuth com credenciais seguras"""
        client_id = f"{brand}_mobile_{datetime.now().year}"
        client_secret = f"{brand[:2]}_oauth_{secrets.token_urlsafe(32)}"
        
        return cls.objects.create(
            client_id=client_id,
            client_secret=client_secret,
            name=name,
            brand=brand
        )

    def pode_acessar_loja(self, loja_id: int) -> bool:
        """Verifica se o cliente OAuth pode acessar a loja específica"""
        if self.nivel_acesso == 'GLOBAL':
            return True
        
        if self.nivel_acesso == 'LOJA':
            return self.loja_id == loja_id
        
        if self.nivel_acesso == 'GRUPO':
            # TODO: Implementar validação de grupo econômico
            # Verificar se loja_id pertence ao grupo_economico_id
            return True  # Temporariamente permitir
        
        return False
    
    def get_loja_id(self) -> int:
        """Retorna loja_id do cliente OAuth (ou None se GLOBAL)"""
        if self.nivel_acesso == 'LOJA':
            return self.loja_id
        return None
    
    def __str__(self):
        nivel = f" [{self.nivel_acesso}]" if self.nivel_acesso else ""
        loja_info = f" Loja:{self.loja_id}" if self.loja_id else ""
        return f"{self.name} ({self.brand}){nivel}{loja_info} - {self.client_id}"


class OAuthToken(models.Model):
    """Tokens OAuth 2.0 com expiração automática"""
    client = models.ForeignKey(OAuthClient, on_delete=models.CASCADE)
    access_token = models.CharField(max_length=255, unique=True, db_index=True)
    refresh_token = models.CharField(max_length=255, unique=True, db_index=True)
    token_type = models.CharField(max_length=50, default='Bearer')
    expires_at = models.DateTimeField()
    scopes = models.CharField(max_length=500, default='read,write')
    is_active = models.BooleanField(default=True)
    device_fingerprint = models.CharField(
        max_length=255, 
        null=True, 
        blank=True, 
        db_index=True,
        help_text="Identificador único do dispositivo (hash MD5 de User-Agent + IP + outros fatores)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'oauth_tokens'
        verbose_name = 'OAuth Token'
        verbose_name_plural = 'OAuth Tokens'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['access_token', 'is_active']),
            models.Index(fields=['refresh_token', 'is_active']),
            models.Index(fields=['expires_at', 'is_active']),
        ]

    def is_expired(self):
        """Verifica se o token está expirado"""
        return datetime.now() > self.expires_at

    def refresh_access_token(self):
        """Gera novo access_token mantendo refresh_token"""
        self.access_token = self._generate_access_token()
        self.expires_at = datetime.now() + timedelta(hours=24)
        self.save(update_fields=['access_token', 'expires_at'])
        return self.access_token

    def _generate_access_token(self):
        """Gera access token seguro"""
        return f"wc_at_{secrets.token_urlsafe(32)}"

    @classmethod
    def generate_refresh_token(cls):
        """Gera refresh token seguro"""
        return f"wc_rt_{secrets.token_urlsafe(32)}"

    def record_usage(self):
        """Registra último uso do token"""
        self.last_used_at = datetime.now()
        self.save(update_fields=['last_used_at'])

    def __str__(self):
        status = "🟢" if not self.is_expired() and self.is_active else "🔴"
        return f"{status} {self.client.name} - {self.access_token[:12]}..."
