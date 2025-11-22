from django.db import models


class OwnExtratoTransacoes(models.Model):
    """Armazena transações consultadas da API Own Financial"""
    
    id = models.AutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    lido = models.BooleanField(default=False)
    
    # Identificação
    cnpjCpfCliente = models.CharField(max_length=14, db_index=True)
    cnpjCpfParceiro = models.CharField(max_length=14, null=True, blank=True)
    identificadorTransacao = models.CharField(max_length=50, unique=True, db_index=True)
    
    # Dados da transação
    data = models.DateTimeField(db_index=True)
    numeroSerieEquipamento = models.CharField(max_length=50, null=True, blank=True)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    quantidadeParcelas = models.IntegerField()
    mdr = models.DecimalField(max_digits=10, decimal_places=2)
    valorAntecipacaoTotal = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    taxaAntecipacaoTotal = models.DecimalField(max_digits=12, decimal_places=10, null=True, blank=True)
    
    # Status e classificação
    statusTransacao = models.CharField(max_length=50)
    bandeira = models.CharField(max_length=30)
    modalidade = models.CharField(max_length=100)
    codigoAutorizacao = models.CharField(max_length=20, null=True, blank=True)
    numeroCartao = models.CharField(max_length=20, null=True, blank=True)
    
    # Dados da parcela
    parcelaId = models.BigIntegerField(null=True, blank=True)
    statusPagamento = models.CharField(max_length=30, null=True, blank=True)
    dataHoraTransacao = models.DateTimeField(null=True, blank=True)
    mdrParcela = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    numeroParcela = models.IntegerField(null=True, blank=True)
    valorParcela = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    dataPagamentoPrevista = models.DateField(null=True, blank=True)
    dataPagamentoReal = models.DateField(null=True, blank=True)
    valorAntecipado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    taxaAntecipada = models.DecimalField(max_digits=12, decimal_places=10, null=True, blank=True)
    antecipado = models.CharField(max_length=1, null=True, blank=True)
    numeroTitulo = models.CharField(max_length=20, null=True, blank=True)
    
    # Controle
    processado = models.BooleanField(default=False, db_index=True)
    
    class Meta:
        app_label = 'adquirente_own'
        db_table = 'ownExtratoTransacoes'
        verbose_name = 'Extrato Transação Own'
        verbose_name_plural = 'Extratos Transações Own'
        indexes = [
            models.Index(fields=['identificadorTransacao']),
            models.Index(fields=['cnpjCpfCliente']),
            models.Index(fields=['data']),
            models.Index(fields=['lido']),
            models.Index(fields=['processado']),
        ]
    
    def __str__(self):
        return f"Own {self.identificadorTransacao} - R$ {self.valor}"


class OwnLiquidacoes(models.Model):
    """Armazena liquidações consultadas da API Own Financial"""
    
    id = models.AutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    
    lancamentoId = models.BigIntegerField(unique=True, db_index=True)
    statusPagamento = models.CharField(max_length=30)
    dataPagamentoPrevista = models.DateField()
    numeroParcela = models.IntegerField()
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    dataPagamentoReal = models.DateField(db_index=True)
    antecipada = models.CharField(max_length=1)
    identificadorTransacao = models.CharField(max_length=50, db_index=True)
    bandeira = models.CharField(max_length=30)
    modalidade = models.CharField(max_length=100)
    codigoCliente = models.CharField(max_length=14)
    docParceiro = models.CharField(max_length=14)
    nsuTransacao = models.CharField(max_length=50)
    numeroTitulo = models.CharField(max_length=20)
    
    processado = models.BooleanField(default=False, db_index=True)
    
    class Meta:
        app_label = 'adquirente_own'
        db_table = 'ownLiquidacoes'
        verbose_name = 'Liquidação Own'
        verbose_name_plural = 'Liquidações Own'
        indexes = [
            models.Index(fields=['lancamentoId']),
            models.Index(fields=['identificadorTransacao']),
            models.Index(fields=['dataPagamentoReal']),
            models.Index(fields=['processado']),
        ]
    
    def __str__(self):
        return f"Liquidação {self.lancamentoId} - R$ {self.valor}"


class CredenciaisExtratoContaOwn(models.Model):
    """
    Credenciais OAuth 2.0 do cliente White Label (WallClub)
    
    Cada registro representa um conjunto de credenciais para acessar APIs Own.
    As lojas individuais são identificadas via docParceiro nas consultas.
    """
    
    id = models.AutoField(primary_key=True)
    
    # Identificação do Cliente White Label
    nome = models.CharField(max_length=256, help_text='Nome do cliente White Label')
    cnpj_white_label = models.CharField(
        max_length=14, 
        unique=True,
        db_index=True,
        help_text='CNPJ do cliente White Label (usado como cnpjCliente nas APIs)'
    )
    
    # OAuth 2.0 (APIs Adquirência)
    client_id = models.CharField(max_length=256, help_text='Identificador do cliente Own')
    client_secret = models.CharField(max_length=512, help_text='Chave secreta OAuth 2.0')
    scope = models.CharField(max_length=256, help_text='Escopo de integração liberado')
    
    # e-SiTef (Transações E-commerce)
    entity_id = models.CharField(max_length=100, help_text='Entity ID para transações e-SiTef')
    access_token = models.CharField(max_length=512, help_text='Access token e-SiTef')
    
    # Ambiente
    environment = models.CharField(
        max_length=10,
        choices=[('TEST', 'Test'), ('LIVE', 'Live')],
        default='LIVE',
        db_index=True,
        help_text='Ambiente: LIVE ou TEST'
    )
    
    # Controle
    ativo = models.BooleanField(default=True, help_text='Credencial ativa')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    
    class Meta:
        app_label = 'adquirente_own'
        db_table = 'credenciaisExtratoContaOwn'
        verbose_name = 'Credencial Own'
        verbose_name_plural = 'Credenciais Own'
        indexes = [
            models.Index(fields=['cnpj_white_label']),
            models.Index(fields=['environment']),
        ]
    
    def __str__(self):
        return f"{self.nome} - {self.cnpj_white_label} ({self.environment})"
