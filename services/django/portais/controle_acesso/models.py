"""Models para Sistema de Controle de Acesso - Opção 2: Apenas Permissões
Usa tabelas existentes, remove campo tipo_usuario
"""
from django.db import models
from django.contrib.auth.models import User


class PortalUsuario(models.Model):
    """
    Model para tabela portais_usuarios existente
    Opção 2: Remove campo tipo_usuario
    """
    nome = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    senha_hash = models.CharField(max_length=255)
    # tipo_usuario removido na Opção 2
    ativo = models.BooleanField(default=True)
    email_verificado = models.BooleanField(default=False)
    token_reset_senha = models.CharField(max_length=255, null=True, blank=True)
    reset_senha_expira = models.DateTimeField(null=True, blank=True)
    backup_codes_2fa = models.TextField(null=True, blank=True)
    secret_key_2fa = models.CharField(max_length=32, null=True, blank=True)
    two_factor_enabled = models.BooleanField(default=False)
    ultimo_login = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    primeiro_acesso_expira = models.DateTimeField(null=True, blank=True)
    senha_temporaria = models.BooleanField(default=True)
    token_primeiro_acesso = models.CharField(max_length=255, null=True, blank=True)
    aceite = models.BooleanField(default=False)
    data_aceite = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'portais_usuarios'
        verbose_name = 'Usuário Portal'
        verbose_name_plural = 'Usuários Portais'
        ordering = ['nome']
    
    def __str__(self):
        return f"{self.nome} ({self.email})"
    
    def pode_acessar_portal(self, portal):
        """Verifica se usuário pode acessar portal específico"""
        if not self.ativo:
            return False
        
        # Verifica se tem permissão específica para o portal
        return self.permissoes.filter(portal=portal).exists()
    
    def verificar_senha(self, senha_raw):
        """Verifica senha compatível com MD5 legado"""
        if not senha_raw:
            return False
        import hashlib
        senha_md5 = hashlib.md5(senha_raw.encode()).hexdigest()
        return self.senha_hash == senha_md5
    
    @property
    def is_usuario_valido(self):
        """Verifica se usuário está validado (email verificado e sem senha temporária)"""
        return self.email_verificado and not self.senha_temporaria
    
    @property
    def portais_acesso(self):
        """Retorna lista de portais que o usuário tem acesso"""
        mapa_nomes = {
            'admin': 'Admin',
            'lojista': 'Lojista',
            'recorrencia': 'Recorrência',
            'vendas': 'Vendas'
        }
        portais = self.permissoes.values_list('portal', flat=True).distinct()
        return [mapa_nomes.get(p, p.title()) for p in portais]
    
    @property
    def tipo_usuario(self):
        """Retorna tipo baseado nas permissões (para compatibilidade com template)"""
        # Verifica se tem permissão admin em qualquer portal
        if self.permissoes.filter(nivel_acesso='admin').exists():
            return 'admin'
        elif self.permissoes.exists():
            return 'usuario'
        else:
            return 'sem_acesso'
    
    def get_tipo_usuario_display(self):
        """Retorna descrição do tipo de usuário"""
        tipo = self.tipo_usuario
        if tipo == 'admin':
            return 'Administrador'
        elif tipo == 'usuario':
            return 'Usuário'
        else:
            return 'Sem Acesso'
    
    def set_password(self, senha_raw):
        """Define senha usando hash MD5 para compatibilidade legada"""
        import hashlib
        self.senha_hash = hashlib.md5(senha_raw.encode()).hexdigest()
    
    def gerar_token_primeiro_acesso(self):
        """Gera token para primeiro acesso do usuário"""
        import secrets
        import string
        from datetime import datetime, timedelta
        
        token = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
        self.token_primeiro_acesso = token
        self.primeiro_acesso_expira = datetime.now() + timedelta(days=7)
        self.save()
        return token
    
    def gerar_token_troca_senha(self, nova_senha_hash):
        """Gera token para confirmação de troca de senha"""
        import secrets
        from datetime import datetime, timedelta
        
        # Token de 6 números
        token = ''.join(secrets.choice('0123456789') for _ in range(6))
        self.token_reset_senha = token
        self.reset_senha_expira = datetime.now() + timedelta(hours=24)
        # Armazenar nova senha temporariamente no campo backup_codes_2fa
        self.backup_codes_2fa = nova_senha_hash
        self.save()
        return token
    
    def validar_token_troca_senha(self, token_digitado):
        """Valida token para confirmação de troca de senha"""
        from datetime import datetime
        
        # Verificar se token existe e não expirou
        if not self.token_reset_senha or not self.reset_senha_expira:
            return False
            
        # Verificar se token não expirou
        if datetime.now() > self.reset_senha_expira:
            return False
            
        # Verificar se token confere
        return self.token_reset_senha == token_digitado
    
    def confirmar_troca_senha(self, portal_destino='admin'):
        """Confirma a troca de senha aplicando a nova senha armazenada temporariamente"""
        if not self.backup_codes_2fa:
            return False
            
        # Aplicar nova senha que estava armazenada temporariamente
        self.senha_hash = self.backup_codes_2fa
        
        # Limpar campos de reset
        self.token_reset_senha = None
        self.reset_senha_expira = None
        self.backup_codes_2fa = None
        
        self.save()
        
        # Enviar email de confirmação
        try:
            from .email_service import EmailService
            EmailService.enviar_email_senha_alterada(self, portal_destino=portal_destino)
        except Exception as e:
            # Log do erro mas não falha a operação - usando registrar_log
            from wallclub_core.utilitarios.log_control import registrar_log
            registrar_log('portais.controle_acesso', f"Erro ao enviar email de confirmação de alteração de senha para {self.email}: {str(e)}", nivel='ERROR')
        
        return True


class PortalPermissao(models.Model):
    """
    Model para tabela portais_permissoes existente
    Define permissões de acesso aos portais
    """
    usuario = models.ForeignKey(PortalUsuario, on_delete=models.CASCADE, related_name='permissoes')
    portal = models.CharField(max_length=20)
    nivel_acesso = models.CharField(max_length=20)
    recursos_permitidos = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'portais_permissoes'
        verbose_name = 'Permissão Portal'
        verbose_name_plural = 'Permissões Portais'
        ordering = ['usuario__nome', 'portal']
    
    def __str__(self):
        return f"{self.usuario.nome} - {self.portal} ({self.nivel_acesso})"


class PortalUsuarioAcesso(models.Model):
    """
    Model para tabela portais_usuario_acesso existente
    Define vínculos específicos do usuário usando entidade_tipo/entidade_id
    """
    PORTAL_CHOICES = [
        ('admin', 'Portal Administrativo'),
        ('lojista', 'Portal Lojista'),
        ('recorrencia', 'Portal de Recorrência'),
        ('vendas', 'Portal de Vendas'),
    ]
    
    ENTIDADE_TIPOS = [
        ('loja', 'Loja'),
        ('grupo_economico', 'Grupo Econômico'),
        ('canal', 'Canal'),
        ('regional', 'Regional'),
        ('vendedor', 'Vendedor'),
        ('admin_canal', 'Admin Canal'),
        ('admin_loja', 'Admin Loja'),
        ('admin_regional', 'Admin Regional'),
        ('admin_vendedor', 'Admin Vendedor'),
    ]
    
    usuario = models.ForeignKey(PortalUsuario, on_delete=models.CASCADE, related_name='acessos')
    portal = models.CharField(max_length=20, choices=PORTAL_CHOICES, null=True, blank=True)
    entidade_tipo = models.CharField(max_length=30, choices=ENTIDADE_TIPOS)
    entidade_id = models.BigIntegerField()
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'portais_usuario_acesso'
        verbose_name = 'Acesso de Usuário'
        verbose_name_plural = 'Acessos de Usuários'
        ordering = ['usuario__nome', 'entidade_tipo']
        indexes = [
            models.Index(fields=['usuario', 'entidade_tipo']),
            models.Index(fields=['entidade_tipo', 'entidade_id']),
        ]
    
    def get_entidade_display_completo(self):
        """Retorna descrição completa da entidade"""
        return f"{self.get_entidade_tipo_display()} {self.entidade_id}"
    
    def __str__(self):
        portal_display = f"[{self.portal}] " if self.portal else ""
        return f"{self.usuario.nome} - {portal_display}{self.get_entidade_display_completo()}"


