"""
Model para sessões de verificação de identidade via Veriff
"""
from django.db import models


class VeriffSession(models.Model):
    """Sessão de verificação de identidade via Veriff SDK"""

    id = models.BigAutoField(primary_key=True)
    cliente = models.ForeignKey(
        'cliente.Cliente',
        on_delete=models.CASCADE,
        related_name='veriff_sessions'
    )
    canal_id = models.IntegerField()
    session_id = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text='ID da sessão Veriff'
    )
    session_url = models.URLField(max_length=500, help_text='URL para o SDK abrir')
    status = models.CharField(
        max_length=30,
        default='created',
        help_text='created, submitted, approved, declined, resubmission_requested, expired, abandoned'
    )
    decision_time = models.DateTimeField(null=True, blank=True, help_text='Quando Veriff decidiu')
    veriff_reason = models.TextField(null=True, blank=True, help_text='Motivo da decisão')
    vendor_data = models.CharField(max_length=255, null=True, blank=True, help_text='Dados extras enviados')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'biometria'
        db_table = 'veriff_session'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['cliente']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Veriff {self.session_id} - Cliente {self.cliente_id} - {self.status}"
