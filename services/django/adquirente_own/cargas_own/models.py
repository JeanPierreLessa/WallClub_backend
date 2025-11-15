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
    """Credenciais de acesso às APIs Own Financial"""
    
    id = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=256)
    cnpj = models.CharField(max_length=14, db_index=True)
    
    # OAuth 2.0 (APIs Adquirência)
    client_id = models.CharField(max_length=256)
    client_secret = models.CharField(max_length=512)
    scope = models.CharField(max_length=256)
    
    # e-SiTef (Transações)
    entity_id = models.CharField(max_length=100)
    access_token = models.CharField(max_length=512)
    environment = models.CharField(
        max_length=10,
        choices=[('TEST', 'Test'), ('LIVE', 'Live')],
        default='LIVE'
    )
    
    # Relacionamento
    cliente_id = models.IntegerField(null=True, blank=True, db_index=True)
    
    # Controle
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    
    class Meta:
        db_table = 'credenciaisExtratoContaOwn'
        verbose_name = 'Credencial Own'
        verbose_name_plural = 'Credenciais Own'
        indexes = [
            models.Index(fields=['cliente_id']),
            models.Index(fields=['cnpj']),
        ]
    
    def __str__(self):
        return f"{self.nome} - {self.cnpj}"
