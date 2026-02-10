"""
Models para cadastro de estabelecimentos na Own Financial
"""

from django.db import models


class LojaOwn(models.Model):
    """Dados específicos da integração com Own Financial"""

    id = models.AutoField(primary_key=True)
    loja_id = models.IntegerField(unique=True, db_index=True, help_text='FK para tabela loja')

    # Controle de cadastro
    cadastrar = models.BooleanField(default=False, help_text='Indica se deve cadastrar na Own')

    # Dados de credenciamento
    entity_id = models.CharField(max_length=100, null=True, blank=True, help_text='Entity ID para transações e-commerce/POS (obtido via /ecommerce/token)')
    access_token = models.CharField(max_length=512, null=True, blank=True, help_text='Access token para transações e-commerce/POS (obtido via /ecommerce/token)')
    status_credenciamento = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text='Status: PENDENTE, APROVADO, REPROVADO, PROCESSANDO'
    )
    protocolo = models.CharField(max_length=50, null=True, blank=True, help_text='Protocolo atual de cadastro na Own')
    contrato = models.CharField(max_length=50, null=True, blank=True, help_text='Número do contrato na Own')
    data_credenciamento = models.DateTimeField(null=True, blank=True, help_text='Data do credenciamento')
    mensagem_status = models.TextField(null=True, blank=True, help_text='Mensagem de retorno da Own')

    # Configurações de tarifação
    id_cesta = models.IntegerField(null=True, blank=True, help_text='ID da cesta de tarifas Own')

    # Dados de atividade econômica
    cnae = models.CharField(max_length=20, null=True, blank=True, help_text='CNAE principal')
    ramo_atividade = models.CharField(max_length=256, null=True, blank=True, help_text='Ramo de atividade')
    mcc = models.CharField(max_length=4, null=True, blank=True, help_text='MCC (Merchant Category Code)')
    mcc_id = models.IntegerField(null=True, blank=True, help_text='ID do MCC na Own')

    # Dados financeiros
    faturamento_previsto = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, help_text='Faturamento previsto')
    faturamento_contratado = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, help_text='Faturamento contratado')

    # Configurações de POS e antecipação
    quantidade_pos = models.IntegerField(null=True, blank=True, default=0, help_text='Quantidade de POS')
    antecipacao_automatica = models.CharField(max_length=1, null=True, blank=True, default='N', help_text='Antecipação automática (S/N)')
    taxa_antecipacao = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, default=0.00, help_text='Taxa de antecipação')
    tipo_antecipacao = models.CharField(max_length=20, null=True, blank=True, default='ROTATIVO', help_text='Tipo de antecipação')

    # Responsável pela assinatura
    responsavel_assinatura = models.CharField(max_length=256, null=True, blank=True, help_text='Nome do responsável')
    responsavel_assinatura_cpf = models.CharField(max_length=11, null=True, blank=True, help_text='CPF do responsável')
    responsavel_assinatura_email = models.CharField(max_length=256, null=True, blank=True, help_text='Email do responsável')

    # Configurações de captura
    aceita_ecommerce = models.BooleanField(default=False, help_text='Aceita pagamentos e-commerce')

    # Controle de sincronização
    sincronizado = models.BooleanField(default=False, help_text='Dados sincronizados com Own')
    ultima_sincronizacao = models.DateTimeField(null=True, blank=True, help_text='Data da última sincronização')

    # Auditoria
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'adquirente_own'
        db_table = 'loja_own'
        verbose_name = 'Loja Own'
        verbose_name_plural = 'Lojas Own'
        indexes = [
            models.Index(fields=['loja_id']),
            models.Index(fields=['status_credenciamento']),
            models.Index(fields=['protocolo']),
            models.Index(fields=['cadastrar']),
            models.Index(fields=['sincronizado']),
        ]

    def __str__(self):
        return f"LojaOwn {self.loja_id} - Status: {self.status_credenciamento or 'Não cadastrado'}"


class LojaPinbank(models.Model):
    """Dados específicos da integração com Pinbank"""

    id = models.AutoField(primary_key=True)
    loja_id = models.IntegerField(unique=True, db_index=True, help_text='FK para tabela loja')

    # Dados de integração Pinbank
    codigo_canal = models.IntegerField(null=True, blank=True, help_text='Código do canal Pinbank')
    codigo_cliente = models.IntegerField(null=True, blank=True, help_text='Código do cliente Pinbank')
    key_value_loja = models.CharField(max_length=20, null=True, blank=True, help_text='Chave de identificação da loja na Pinbank')

    # Status de integração
    ativo = models.BooleanField(default=True, help_text='Integração ativa')

    # Auditoria
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'adquirente_own'
        db_table = 'loja_pinbank'
        verbose_name = 'Loja Pinbank'
        verbose_name_plural = 'Lojas Pinbank'
        indexes = [
            models.Index(fields=['loja_id']),
            models.Index(fields=['codigo_canal']),
            models.Index(fields=['codigo_cliente']),
            models.Index(fields=['key_value_loja']),
        ]

    def __str__(self):
        return f"LojaPinbank {self.loja_id} - Canal: {self.codigo_canal}"


class LojaOwnTarifacao(models.Model):
    """Tarifas da cesta Own associadas à loja"""

    id = models.AutoField(primary_key=True)
    loja_own_id = models.IntegerField(db_index=True, help_text='FK para tabela loja_own')

    # Dados da tarifa
    cesta_valor_id = models.IntegerField(help_text='ID da tarifa na cesta Own')
    valor = models.DecimalField(max_digits=10, decimal_places=2, help_text='Valor da tarifa')
    descricao = models.CharField(max_length=256, null=True, blank=True, help_text='Descrição da tarifa')

    # Auditoria
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'adquirente_own'
        db_table = 'loja_own_tarifacao'
        verbose_name = 'Tarifação Own'
        verbose_name_plural = 'Tarifações Own'
        indexes = [
            models.Index(fields=['loja_own_id']),
            models.Index(fields=['cesta_valor_id']),
        ]

    def __str__(self):
        return f"Tarifação {self.cesta_valor_id} - R$ {self.valor}"


class LojaOwnProtocoloHistorico(models.Model):
    """Histórico de protocolos de cadastro/recadastro na Own"""

    id = models.AutoField(primary_key=True)
    loja_id = models.IntegerField(db_index=True, help_text='FK para tabela loja')

    # Dados do protocolo
    protocolo = models.CharField(max_length=50, db_index=True, help_text='Número do protocolo')
    tipo = models.CharField(max_length=20, help_text='CREDENCIAMENTO ou ADITIVO')
    reenvio = models.CharField(max_length=1, default='N', help_text='S=Sim, N=Não')

    # Status
    status = models.CharField(max_length=50, help_text='EM ANALISE, SUCESSO, ERRO, APPROVED, REPROVED')
    motivo = models.TextField(null=True, blank=True, help_text='Motivo em caso de reprovação')

    # Resultado
    contrato = models.CharField(max_length=50, null=True, blank=True, help_text='Número do contrato (se aprovado)')
    data_envio = models.DateTimeField(auto_now_add=True, help_text='Data de envio do protocolo')
    data_retorno = models.DateTimeField(null=True, blank=True, help_text='Data de retorno do webhook')

    # Auditoria
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'adquirente_own'
        db_table = 'loja_own_protocolo_historico'
        verbose_name = 'Histórico de Protocolo Own'
        verbose_name_plural = 'Histórico de Protocolos Own'
        indexes = [
            models.Index(fields=['loja_id']),
            models.Index(fields=['protocolo']),
            models.Index(fields=['status']),
            models.Index(fields=['data_envio']),
        ]
        ordering = ['-data_envio']

    def __str__(self):
        return f"Protocolo {self.protocolo} - Loja {self.loja_id} - {self.status}"


class LojaDocumentos(models.Model):
    """Documentos da loja e sócios para cadastro na Own"""

    TIPO_DOCUMENTO_CHOICES = [
        ('CONTRATO_SOCIAL', 'Contrato Social'),
        ('COMPROVANTE_ENDERECO', 'Comprovante de Endereço'),
        ('CARTAO_CNPJ', 'Cartão CNPJ'),
        ('RGFRENTE', 'RG Frente'),
        ('RGVERSO', 'RG Verso'),
    ]

    id = models.AutoField(primary_key=True)
    loja_id = models.IntegerField(db_index=True, help_text='FK para tabela loja')

    # Tipo de documento
    tipo_documento = models.CharField(
        max_length=50,
        choices=TIPO_DOCUMENTO_CHOICES,
        help_text='Tipo do documento'
    )

    # Dados do arquivo
    nome_arquivo = models.CharField(max_length=256, help_text='Nome original do arquivo')
    caminho_arquivo = models.CharField(max_length=512, help_text='Caminho no S3 ou storage')
    tamanho_bytes = models.BigIntegerField(null=True, blank=True, help_text='Tamanho do arquivo em bytes')
    mime_type = models.CharField(max_length=100, null=True, blank=True, help_text='Tipo MIME do arquivo')

    # Identificação do sócio (para documentos pessoais)
    cpf_socio = models.CharField(max_length=11, null=True, blank=True, help_text='CPF do sócio (para docs pessoais: RG)')
    nome_socio = models.CharField(max_length=256, null=True, blank=True, help_text='Nome do sócio')

    # Controle
    ativo = models.BooleanField(default=True, help_text='Documento ativo')

    # Auditoria
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'adquirente_own'
        db_table = 'loja_documentos'
        verbose_name = 'Documento Loja'
        verbose_name_plural = 'Documentos Loja'
        indexes = [
            models.Index(fields=['loja_id']),
            models.Index(fields=['tipo_documento']),
            models.Index(fields=['cpf_socio']),
            models.Index(fields=['ativo']),
            models.Index(fields=['loja_id', 'cpf_socio']),
        ]

    def __str__(self):
        if self.cpf_socio:
            return f"{self.tipo_documento} - Sócio {self.cpf_socio}"
        return f"{self.tipo_documento} - Loja {self.loja_id}"
