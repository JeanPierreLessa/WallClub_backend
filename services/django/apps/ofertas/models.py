from django.db import models
from datetime import datetime


class GrupoSegmentacao(models.Model):
    """Model para ofertas_grupos_segmentacao - Grupos customizados de clientes"""
    
    CRITERIO_CHOICES = [
        ('manual', 'Manual'),
        ('regra_automatica', 'Regra Automática'),
    ]
    
    id = models.AutoField(primary_key=True)
    canal_id = models.IntegerField(help_text='Canal do grupo')
    
    nome = models.CharField(max_length=255, help_text='Nome do grupo (ex: Clientes Premium)')
    descricao = models.TextField(null=True, blank=True, help_text='Descrição do critério do grupo')
    
    criterio_tipo = models.CharField(max_length=20, choices=CRITERIO_CHOICES, default='manual', help_text='Manual ou por regras')
    criterio_json = models.JSONField(null=True, blank=True, help_text='Regras automáticas futuras')
    
    ativo = models.BooleanField(default=True, help_text='Grupo ativo')
    created_at = models.DateTimeField(help_text='Data/hora de criação')
    updated_at = models.DateTimeField(null=True, blank=True, help_text='Data/hora da última atualização')
    
    class Meta:
        managed = False
        db_table = 'ofertas_grupos_segmentacao'
    
    def __str__(self):
        return f"{self.nome} (Canal {self.canal_id})"


class GrupoCliente(models.Model):
    """Model para ofertas_grupos_clientes - Relacionamento N:N grupos e clientes"""
    
    id = models.AutoField(primary_key=True)
    grupo_id = models.IntegerField(help_text='ID do grupo')
    cliente_id = models.IntegerField(help_text='ID do cliente')
    adicionado_em = models.DateTimeField(help_text='Data/hora de adição ao grupo')
    
    class Meta:
        managed = False
        db_table = 'ofertas_grupos_clientes'
        unique_together = [['grupo_id', 'cliente_id']]
    
    def __str__(self):
        return f"Grupo {self.grupo_id} - Cliente {self.cliente_id}"


class Oferta(models.Model):
    """Model para tabela ofertas - Cadastro base de ofertas"""
    
    TIPO_SEGMENTACAO_CHOICES = [
        ('todos_canal', 'Todos do Canal'),
        ('grupo_customizado', 'Grupo Customizado'),
    ]
    
    id = models.AutoField(primary_key=True)
    canal_id = models.IntegerField(help_text='Canal da oferta')
    
    titulo = models.CharField(max_length=255, help_text='Título da oferta exibido no app')
    texto_push = models.CharField(max_length=255, help_text='Texto curto enviado via push notification')
    descricao = models.TextField(null=True, blank=True, help_text='Descrição detalhada exibida na página do app')
    imagem_url = models.CharField(max_length=500, null=True, blank=True, help_text='URL da imagem (S3/CDN)')
    
    # Controle de vigência
    vigencia_inicio = models.DateTimeField(help_text='Data/hora início da vigência')
    vigencia_fim = models.DateTimeField(help_text='Data/hora fim da vigência')
    ativo = models.BooleanField(default=True, help_text='Oferta ativa (1) ou inativa (0)')
    
    # Segmentação
    tipo_segmentacao = models.CharField(max_length=20, choices=TIPO_SEGMENTACAO_CHOICES, default='todos_canal', help_text='Enviar para todo canal ou grupo específico')
    grupo_id = models.IntegerField(null=True, blank=True, help_text='ID do grupo (obrigatório se tipo=grupo_customizado)')
    
    # Auditoria
    usuario_criador_id = models.IntegerField(null=True, blank=True, help_text='ID do usuário que criou a oferta')
    created_at = models.DateTimeField(help_text='Data/hora de criação')
    updated_at = models.DateTimeField(null=True, blank=True, help_text='Data/hora da última atualização')
    
    class Meta:
        managed = False
        db_table = 'ofertas'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['vigencia_inicio', 'vigencia_fim', 'ativo'], name='idx_vigencia'),
            models.Index(fields=['canal_id', 'ativo'], name='idx_canal'),
            models.Index(fields=['tipo_segmentacao', 'grupo_id'], name='idx_segmentacao'),
            models.Index(fields=['created_at'], name='idx_created'),
        ]
    
    def __str__(self):
        return f"{self.titulo} (Canal {self.canal_id})"
    
    def is_vigente(self):
        """Verifica se oferta está vigente no momento atual"""
        agora = datetime.now()
        return (
            self.ativo and 
            self.vigencia_inicio <= agora <= self.vigencia_fim
        )
    
    def save(self, *args, **kwargs):
        """Override save para atualizar updated_at"""
        if not self.created_at:
            self.created_at = datetime.now()
        self.updated_at = datetime.now()
        super().save(*args, **kwargs)


class OfertaDisparo(models.Model):
    """Model para tabela oferta_disparos - Histórico de disparos de push"""
    
    STATUS_CHOICES = [
        ('processando', 'Processando'),
        ('concluido', 'Concluído'),
        ('erro', 'Erro'),
    ]
    
    id = models.AutoField(primary_key=True)
    oferta_id = models.IntegerField(help_text='Referência à oferta disparada')
    
    # Controle do disparo
    data_disparo = models.DateTimeField(help_text='Data/hora do disparo')
    usuario_disparador_id = models.IntegerField(null=True, blank=True, help_text='Usuário que solicitou o disparo')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='processando', help_text='Status do processamento')
    
    # Métricas do disparo
    total_clientes = models.IntegerField(default=0, help_text='Total de clientes elegíveis')
    total_enviados = models.IntegerField(default=0, help_text='Total de pushes enviados com sucesso')
    total_falhas = models.IntegerField(default=0, help_text='Total de falhas no envio')
    
    # Auditoria
    created_at = models.DateTimeField(help_text='Data/hora de criação do registro')
    
    class Meta:
        managed = False
        db_table = 'oferta_disparos'
        ordering = ['-data_disparo']
        indexes = [
            models.Index(fields=['oferta_id'], name='idx_oferta'),
            models.Index(fields=['data_disparo'], name='idx_data_disparo'),
            models.Index(fields=['status'], name='idx_status'),
        ]
    
    def __str__(self):
        return f"Disparo #{self.id} - Oferta {self.oferta_id} ({self.status})"
    
    def taxa_sucesso(self):
        """Calcula taxa de sucesso do disparo"""
        if self.total_clientes == 0:
            return 0.0
        return round((self.total_enviados * 100.0 / self.total_clientes), 2)
    
    def save(self, *args, **kwargs):
        """Override save para garantir created_at"""
        if not self.created_at:
            self.created_at = datetime.now()
        if not self.data_disparo:
            self.data_disparo = datetime.now()
        super().save(*args, **kwargs)


class OfertaEnvio(models.Model):
    """Model para tabela oferta_envios - Controle individual de envios"""
    
    id = models.AutoField(primary_key=True)
    oferta_disparo_id = models.IntegerField(help_text='Referência ao disparo')
    cliente_id = models.IntegerField(help_text='ID do cliente que recebeu')
    
    # Controle de envio
    enviado = models.BooleanField(default=False, help_text='Push enviado (1) ou não (0)')
    data_envio = models.DateTimeField(null=True, blank=True, help_text='Data/hora do envio efetivo')
    erro = models.TextField(null=True, blank=True, help_text='Mensagem de erro caso falhe')
    
    # Auditoria
    created_at = models.DateTimeField(help_text='Data/hora de criação do registro')
    
    class Meta:
        managed = False
        db_table = 'oferta_envios'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['oferta_disparo_id'], name='idx_disparo'),
            models.Index(fields=['cliente_id'], name='idx_cliente'),
            models.Index(fields=['enviado'], name='idx_enviado'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['oferta_disparo_id', 'cliente_id'],
                name='uk_disparo_cliente'
            )
        ]
    
    def __str__(self):
        status = "Enviado" if self.enviado else "Pendente"
        return f"Envio #{self.id} - Cliente {self.cliente_id} ({status})"
    
    def save(self, *args, **kwargs):
        """Override save para garantir created_at e data_envio"""
        if not self.created_at:
            self.created_at = datetime.now()
        if self.enviado and not self.data_envio:
            self.data_envio = datetime.now()
        super().save(*args, **kwargs)
