"""
Modelos para integrações (templates de mensagens)
"""
from django.db import models
from wallclub_core.estr_organizacional.canal import Canal


class TemplateEnvioMsg(models.Model):
    """Template para envio de SMS/WhatsApp"""
    
    TIPO_CHOICES = [
        ('SMS', 'SMS'),
        ('WHATSAPP', 'WhatsApp'),
        ('PUSH', 'Push Notification')
    ]
    
    TIPO_PUSH_CHOICES = [
        ('notificacao', 'Notificação'),
        ('autorizacao_saldo', 'Autorização de Saldo'),
        ('oferta', 'Oferta')
    ]
    
    id = models.AutoField(primary_key=True)
    canal = models.ForeignKey(Canal, on_delete=models.CASCADE, db_column='canal_id')
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    tipo_push = models.CharField(max_length=20, choices=TIPO_PUSH_CHOICES, null=True, blank=True)
    id_template = models.CharField(max_length=100)
    descricao = models.TextField(null=True, blank=True)
    mensagem = models.TextField(null=True, blank=True)  # Para SMS: texto direto, para PUSH: JSON {"title": "", "body": ""}
    parametros_esperados = models.JSONField(null=True, blank=True)
    idioma = models.CharField(max_length=10, default='pt_BR')
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'templates_envio_msg'
        unique_together = [['canal', 'tipo', 'id_template']]
        indexes = [
            models.Index(fields=['canal', 'tipo', 'ativo'], name='idx_canal_tipo_ativo')
        ]
        verbose_name = 'Template de Envio'
        verbose_name_plural = 'Templates de Envio'
    
    def __str__(self):
        return f"{self.tipo} - {self.id_template} (Canal {self.canal_id})"
    
    def formatar_mensagem(self, **params):
        """
        Formata mensagem substituindo placeholders
        
        Args:
            **params: Parâmetros para substituir (ex: senha='1234', cpf='12345678901')
            
        Returns:
            str: Mensagem formatada
        """
        if not self.mensagem:
            return ""
        
        mensagem_formatada = self.mensagem
        for key, value in params.items():
            placeholder = f"{{{key}}}"
            mensagem_formatada = mensagem_formatada.replace(placeholder, str(value))
        
        return mensagem_formatada
