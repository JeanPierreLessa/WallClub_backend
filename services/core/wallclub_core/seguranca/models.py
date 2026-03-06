"""
Models de segurança
"""
from django.db import models


class BlacklistCPF(models.Model):
    """Blacklist de CPFs bloqueados"""
    id = models.AutoField(primary_key=True)
    cpf = models.CharField(max_length=11, unique=True, db_index=True)
    motivo = models.CharField(max_length=255, null=True, blank=True, help_text="Motivo do bloqueio")
    bloqueado_por = models.CharField(max_length=100, null=True, blank=True, help_text="Usuário que bloqueou")
    ativo = models.BooleanField(default=True, db_index=True, help_text="1=ativo, 0=inativo")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'blacklist_cpf'
        verbose_name = 'Blacklist CPF'
        verbose_name_plural = 'Blacklist CPFs'
        ordering = ['-created_at']

    def __str__(self):
        status = "🔴 ATIVO" if self.ativo else "🟢 INATIVO"
        return f"{status} - CPF {self.cpf[:3]}***{self.cpf[-2:]} - {self.motivo or 'Sem motivo'}"

    @classmethod
    def adicionar_cpf(cls, cpf: str, motivo: str, bloqueado_por: str = 'sistema'):
        """
        Adiciona CPF à blacklist

        Args:
            cpf: CPF a ser bloqueado (11 dígitos)
            motivo: Motivo do bloqueio
            bloqueado_por: Usuário que bloqueou

        Returns:
            BlacklistCPF: Instância criada ou atualizada
        """
        cpf_limpo = ''.join(filter(str.isdigit, cpf))

        obj, created = cls.objects.update_or_create(
            cpf=cpf_limpo,
            defaults={
                'motivo': motivo,
                'bloqueado_por': bloqueado_por,
                'ativo': True
            }
        )

        # Limpar cache se existir
        from wallclub_core.seguranca.validador_cpf import ValidadorCPFService
        ValidadorCPFService.limpar_cache_cpf(cpf_limpo)

        return obj

    @classmethod
    def remover_cpf(cls, cpf: str):
        """
        Remove CPF da blacklist (marca como inativo)

        Args:
            cpf: CPF a ser desbloqueado

        Returns:
            bool: True se removido com sucesso
        """
        cpf_limpo = ''.join(filter(str.isdigit, cpf))

        try:
            obj = cls.objects.get(cpf=cpf_limpo)
            obj.ativo = False
            obj.save()

            # Limpar cache
            from wallclub_core.seguranca.validador_cpf import ValidadorCPFService
            ValidadorCPFService.limpar_cache_cpf(cpf_limpo)

            return True
        except cls.DoesNotExist:
            return False

    @classmethod
    def cpf_esta_bloqueado(cls, cpf: str) -> bool:
        """
        Verifica se CPF está bloqueado

        Args:
            cpf: CPF a verificar

        Returns:
            bool: True se bloqueado
        """
        cpf_limpo = ''.join(filter(str.isdigit, cpf))
        return cls.objects.filter(cpf=cpf_limpo, ativo=True).exists()


class AutenticacaoOTP(models.Model):
    """Model para armazenar códigos OTP de autenticação 2FA"""

    TIPO_USUARIO_CHOICES = [
        ('cliente', 'Cliente'),
        ('vendedor', 'Vendedor'),
        ('admin', 'Administrador'),
        ('lojista', 'Lojista'),
    ]

    id = models.AutoField(primary_key=True)
    codigo = models.CharField(max_length=6, db_index=True, help_text="Código OTP de 6 dígitos")
    user_id = models.IntegerField(db_index=True, help_text="ID do usuário (cliente_id, user_id, etc)")
    tipo_usuario = models.CharField(max_length=20, choices=TIPO_USUARIO_CHOICES, db_index=True)
    telefone = models.CharField(max_length=20, help_text="Telefone para onde foi enviado")
    validade = models.DateTimeField(db_index=True, help_text="Data/hora de expiração (5 minutos)")
    tentativas = models.IntegerField(default=0, help_text="Número de tentativas de validação")
    usado = models.BooleanField(default=False, db_index=True, help_text="Se o código já foi usado")
    ip_solicitacao = models.GenericIPAddressField(null=True, blank=True, help_text="IP que solicitou o OTP")
    criado_em = models.DateTimeField(auto_now_add=True, db_index=True)
    usado_em = models.DateTimeField(null=True, blank=True, help_text="Quando foi usado")

    class Meta:
        db_table = 'otp_autenticacao'
        verbose_name = 'Autenticação OTP'
        verbose_name_plural = 'Autenticações OTP'
        ordering = ['-criado_em']
        indexes = [
            models.Index(fields=['user_id', 'tipo_usuario', 'usado']),
            models.Index(fields=['codigo', 'validade']),
            models.Index(fields=['telefone', 'criado_em']),
        ]

    def __str__(self):
        status = "✅ USADO" if self.usado else "⏳ PENDENTE"
        return f"{status} - {self.tipo_usuario} ID:{self.user_id} - {self.codigo} - {self.telefone}"

    def esta_valido(self) -> bool:
        """Verifica se o código ainda está dentro da validade"""
        from datetime import datetime
        return datetime.now() < self.validade and not self.usado and self.tentativas < 3


class DispositivoConfiavel(models.Model):
    """Model para rastrear dispositivos confiáveis dos usuários"""

    TIPO_USUARIO_CHOICES = [
        ('cliente', 'Cliente'),
        ('vendedor', 'Vendedor'),
        ('admin', 'Administrador'),
        ('lojista', 'Lojista'),
    ]

    id = models.AutoField(primary_key=True)
    user_id = models.IntegerField(db_index=True, help_text="ID do usuário")
    tipo_usuario = models.CharField(max_length=20, choices=TIPO_USUARIO_CHOICES, db_index=True)
    device_fingerprint = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Hash MD5 do fingerprint do dispositivo (calculado a partir dos componentes)"
    )

    native_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_index=True,
        help_text="ID nativo do dispositivo (IDFV para iOS, androidId para Android)"
    )
    screen_resolution = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="Resolução da tela (ex: 1170x2532)"
    )
    device_model = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Modelo do dispositivo (ex: iPhone15,2 ou SM-G998B)"
    )
    os_version = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="Versão do sistema operacional (ex: 17.2 ou 14)"
    )
    device_brand = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Fabricante do dispositivo (ex: Apple, Samsung)"
    )
    timezone = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Timezone do dispositivo (ex: America/Sao_Paulo)"
    )
    platform = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text="Plataforma (ios ou android)"
    )
    nome_dispositivo = models.CharField(
        max_length=100,
        blank=True,
        help_text="Nome amigável (ex: iPhone 13, Chrome Desktop)"
    )
    user_agent = models.TextField(help_text="User-Agent completo do navegador/app")
    ip_registro = models.GenericIPAddressField(help_text="IP do primeiro registro")
    ultimo_acesso = models.DateTimeField(db_index=True, help_text="Último acesso com este dispositivo")
    ativo = models.BooleanField(default=True, db_index=True, help_text="Se o dispositivo está ativo/confiável")
    confiavel_ate = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Data até quando o dispositivo é confiável (30 dias - sliding window)"
    )
    ultima_revalidacao_2fa = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Data da última revalidação 2FA (força revalidação a cada 90 dias)"
    )
    criado_em = models.DateTimeField(auto_now_add=True, db_index=True)
    revogado_em = models.DateTimeField(null=True, blank=True, help_text="Quando foi revogado")
    revogado_por = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Quem revogou (sistema, usuário, admin)"
    )

    class Meta:
        db_table = 'otp_dispositivo_confiavel'
        verbose_name = 'Dispositivo Confiável'
        verbose_name_plural = 'Dispositivos Confiáveis'
        ordering = ['-ultimo_acesso']
        indexes = [
            models.Index(fields=['user_id', 'tipo_usuario', 'ativo']),
            models.Index(fields=['device_fingerprint', 'ativo']),
            models.Index(fields=['ultimo_acesso']),
            models.Index(fields=['native_id', 'ativo']),
            models.Index(fields=['user_id', 'native_id']),
        ]

    def __str__(self):
        status = "✅ ATIVO" if self.ativo else "🔴 REVOGADO"
        nome = self.nome_dispositivo or "Dispositivo sem nome"
        return f"{status} - {self.tipo_usuario} ID:{self.user_id} - {nome}"

    def esta_confiavel(self) -> bool:
        """Verifica se o dispositivo ainda está dentro do período de confiança"""
        from datetime import datetime
        if not self.ativo:
            return False
        if self.confiavel_ate:
            return datetime.now() < self.confiavel_ate
        return True
