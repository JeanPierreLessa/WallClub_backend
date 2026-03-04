from django.db import models


class ValidacaoBiometrica(models.Model):
    """
    Registro de validação biométrica de identidade
    Usado por checkout e POS para validar identidade do cliente
    """

    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('APROVADO', 'Aprovado'),
        ('REJEITADO', 'Rejeitado'),
        ('ERRO', 'Erro'),
    ]

    TIPO_DOCUMENTO_CHOICES = [
        ('RG', 'RG'),
        ('CNH', 'CNH'),
    ]

    # Identificação
    cpf = models.CharField(max_length=11, db_index=True)

    # Etapa 1: Liveness Detection (FaceTec)
    liveness_aprovado = models.BooleanField(default=False)
    liveness_session_id = models.CharField(max_length=255, null=True, blank=True)
    selfie_url = models.CharField(max_length=500, null=True, blank=True)

    # Etapa 2: OCR Documento (Google Vision)
    ocr_aprovado = models.BooleanField(default=False)
    documento_tipo = models.CharField(max_length=10, choices=TIPO_DOCUMENTO_CHOICES, null=True, blank=True)
    documento_numero = models.CharField(max_length=50, null=True, blank=True)
    cpf_extraido = models.CharField(max_length=11, null=True, blank=True)
    nome_extraido = models.CharField(max_length=255, null=True, blank=True)
    data_nascimento_extraida = models.DateField(null=True, blank=True)
    documento_url = models.CharField(max_length=500, null=True, blank=True)
    foto_documento_url = models.CharField(max_length=500, null=True, blank=True)

    # Etapa 3: Face Match (AWS Rekognition)
    face_match_aprovado = models.BooleanField(default=False)
    face_match_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    face_match_confianca = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Etapa 4: Validação CPF (BigDataCorp)
    cpf_validado = models.BooleanField(default=False)
    cpf_ativo = models.BooleanField(default=False, null=True, blank=True)
    cpf_dados_conferem = models.BooleanField(default=False, null=True, blank=True)

    # Status geral
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE', db_index=True)
    motivo_rejeicao = models.TextField(null=True, blank=True)

    # Auditoria
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'validacao_biometrica'
        verbose_name = 'Validação Biométrica'
        verbose_name_plural = 'Validações Biométricas'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['cpf', 'status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Validação {self.cpf} - {self.status}"

    @property
    def todas_etapas_aprovadas(self):
        """Verifica se todas as etapas foram aprovadas"""
        return all([
            self.liveness_aprovado,
            self.ocr_aprovado,
            self.face_match_aprovado,
            self.cpf_validado
        ])

    def atualizar_status(self):
        """Atualiza status geral baseado nas etapas"""
        if self.todas_etapas_aprovadas:
            self.status = 'APROVADO'
        elif any([
            self.liveness_aprovado is False and self.liveness_session_id,
            self.ocr_aprovado is False and self.documento_url,
            self.face_match_aprovado is False and self.face_match_score,
            self.cpf_validado is False and self.cpf_extraido
        ]):
            self.status = 'REJEITADO'
        else:
            self.status = 'PENDENTE'

        self.save()
