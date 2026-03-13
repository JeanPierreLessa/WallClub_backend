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
    veriff_reason_code = models.IntegerField(null=True, blank=True, help_text='Código do motivo da decisão')
    veriff_code = models.IntegerField(null=True, blank=True, help_text='Código da decisão Veriff (ex: 9001=approved)')
    vendor_data = models.CharField(max_length=255, null=True, blank=True, help_text='Dados extras enviados')

    # Dados da pessoa verificada
    pessoa_nome = models.CharField(max_length=255, null=True, blank=True, help_text='Nome completo no documento')
    pessoa_cpf = models.CharField(max_length=20, null=True, blank=True, help_text='CPF/ID number do documento')
    pessoa_nascimento = models.DateField(null=True, blank=True, help_text='Data de nascimento')
    pessoa_nacionalidade = models.CharField(max_length=10, null=True, blank=True, help_text='Código país (ex: BR)')
    pessoa_genero = models.CharField(max_length=20, null=True, blank=True)
    pessoa_pep_sanction = models.CharField(max_length=30, null=True, blank=True, help_text='Resultado PEP/sanção')

    # Dados do documento
    doc_tipo = models.CharField(max_length=50, null=True, blank=True, help_text='Tipo do documento (DRIVERS_LICENSE, ID_CARD, etc)')
    doc_numero = models.CharField(max_length=100, null=True, blank=True, help_text='Número do documento')
    doc_pais = models.CharField(max_length=10, null=True, blank=True, help_text='País do documento')
    doc_validade = models.DateField(null=True, blank=True, help_text='Data de validade do documento')

    # Risco
    risk_score = models.FloatField(null=True, blank=True, help_text='Score de risco retornado pelo Veriff')
    risk_labels = models.JSONField(null=True, blank=True, help_text='Labels de risco detalhados')

    # Dados técnicos
    ip_verificacao = models.GenericIPAddressField(null=True, blank=True, help_text='IP do usuário durante verificação')
    attempt_id = models.CharField(max_length=100, null=True, blank=True, help_text='ID da tentativa no Veriff')

    # Timestamps Veriff
    acceptance_time = models.DateTimeField(null=True, blank=True, help_text='Quando usuário aceitou termos')
    submission_time = models.DateTimeField(null=True, blank=True, help_text='Quando usuário submeteu verificação')

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
