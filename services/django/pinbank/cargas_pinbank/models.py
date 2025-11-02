from django.db import models


class PinbankExtratoPOS(models.Model):
    """Modelo para armazenar extratos POS da Pinbank - Estrutura exata da tabela MySQL"""
    
    # Estrutura EXATA conforme CREATE TABLE
    id = models.AutoField(primary_key=True)  # Campo ID como chave primária
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    Lido = models.BooleanField(null=True, blank=True)
    codigo_cliente = models.CharField(max_length=10, null=True, blank=True)
    IdTerminal = models.CharField(max_length=256, null=True, blank=True)
    SerialNumber = models.CharField(max_length=256, null=True, blank=True)
    Terminal = models.CharField(max_length=256, null=True, blank=True)
    Bandeira = models.CharField(max_length=256, null=True, blank=True)
    TipoCompra = models.CharField(max_length=256, null=True, blank=True)
    DadosExtra = models.CharField(max_length=256, null=True, blank=True)
    CpfCnpjComprador = models.CharField(max_length=256, null=True, blank=True)
    NomeRazaoSocialComprador = models.CharField(max_length=256, null=True, blank=True)
    NumeroParcela = models.IntegerField()  # Parte da chave primária composta
    NumeroTotalParcelas = models.IntegerField(null=True, blank=True)
    DataTransacao = models.CharField(max_length=256, null=True, blank=True)
    DataFuturaPagamento = models.CharField(max_length=256, null=True, blank=True)
    CodAutorizAdquirente = models.CharField(max_length=256, null=True, blank=True)
    NsuOperacao = models.IntegerField()  # Parte da chave primária composta
    NsuOperacaoLoja = models.CharField(max_length=256, null=True, blank=True)
    ValorBruto = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ValorBrutoParcela = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ValorLiquidoRepasse = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ValorSplit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    IdStatus = models.CharField(max_length=256, null=True, blank=True)
    DescricaoStatus = models.CharField(max_length=256, null=True, blank=True)
    IdStatusPagamento = models.CharField(max_length=256, null=True, blank=True)
    DescricaoStatusPagamento = models.CharField(max_length=256, null=True, blank=True)
    ValorTaxaAdm = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ValorTaxaMes = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    NumeroCartao = models.CharField(max_length=256, null=True, blank=True)
    DataCancelamento = models.CharField(max_length=256, null=True, blank=True)
    Submerchant = models.CharField(max_length=256, null=True, blank=True)

    class Meta:
        db_table = 'pinbankExtratoPOS'
        managed = False  # Django não gerencia a estrutura da tabela
        unique_together = ('NsuOperacao', 'NumeroParcela')  # Chave primária composta
        verbose_name = 'Extrato POS Pinbank'
        verbose_name_plural = 'Extratos POS Pinbank'

    def __str__(self):
        return f"NSU {self.NsuOperacao} - Parcela {self.NumeroParcela}"


# BaseTransacoesGestao movido para pinbank.models


# BaseTransacoesGestaoErroCarga movido para pinbank.models


class CredenciaisExtratoContaPinbank(models.Model):
    """Modelo para credenciais de acesso à API Pinbank"""
    
    id = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=256, null=True, blank=True)
    cnpj = models.CharField(max_length=256, null=True, blank=True)
    username = models.CharField(max_length=256, null=True, blank=True)
    keyvalue = models.CharField(max_length=256, null=True, blank=True)
    canal = models.CharField(max_length=256, null=True, blank=True)
    codigo_cliente = models.CharField(max_length=10, null=True, blank=True)
    cliente_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'credenciaisExtratoContaPinbank'
        verbose_name = 'Credencial Pinbank'
        verbose_name_plural = 'Credenciais Pinbank'

    def __str__(self):
        return f"{self.username} - Canal {self.canal}"


class TestePinbankExtratoPOS(models.Model):
    """Modelo para tabela temporária de teste de extratos POS da Pinbank"""
    
    id = models.AutoField(primary_key=True)
    dataInsercao = models.DateTimeField()
    Lido = models.BooleanField(default=False, null=True)
    codigo_cliente = models.CharField(max_length=10, null=True)
    IdTerminal = models.CharField(max_length=256, null=True)
    SerialNumber = models.CharField(max_length=256, null=True)
    Terminal = models.CharField(max_length=256, null=True)
    Bandeira = models.CharField(max_length=256, null=True)
    TipoCompra = models.CharField(max_length=256, null=True)
    DadosExtra = models.CharField(max_length=256, null=True)
    CpfCnpjComprador = models.CharField(max_length=256, null=True)
    NomeRazaoSocialComprador = models.CharField(max_length=256, null=True)
    NumeroParcela = models.IntegerField()
    NumeroTotalParcelas = models.IntegerField(null=True)
    DataTransacao = models.CharField(max_length=256, null=True)
    DataFuturaPagamento = models.CharField(max_length=256, null=True)
    CodAutorizAdquirente = models.CharField(max_length=256, null=True)
    NsuOperacao = models.IntegerField()
    NsuOperacaoLoja = models.CharField(max_length=256, null=True)
    ValorBruto = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    ValorBrutoParcela = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    ValorLiquidoRepasse = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    ValorSplit = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    IdStatus = models.CharField(max_length=256, null=True)
    DescricaoStatus = models.CharField(max_length=256, null=True)
    IdStatusPagamento = models.CharField(max_length=256, null=True)
    DescricaoStatusPagamento = models.CharField(max_length=256, null=True)
    ValorTaxaAdm = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    ValorTaxaMes = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    NumeroCartao = models.CharField(max_length=256, null=True)
    DataCancelamento = models.CharField(max_length=256, null=True)
    Submerchant = models.CharField(max_length=256, null=True)

    class Meta:
        db_table = 'teste_pinbankExtratoPOS'
        constraints = [
            models.UniqueConstraint(fields=['NsuOperacao', 'NumeroParcela'], name='unique_nsu_parcela_teste')
        ]
        indexes = [
            models.Index(fields=['NsuOperacao'], name='idx_nsuoperacao_teste')
        ]
        verbose_name = 'Teste Extrato POS Pinbank'
        verbose_name_plural = 'Testes Extratos POS Pinbank'

    def __str__(self):
        return f"TESTE NSU {self.NsuOperacao} - Parcela {self.NumeroParcela}"
