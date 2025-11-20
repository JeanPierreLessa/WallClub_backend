"""
Models para o app posp2
"""

from django.db import models
from django.utils import timezone


class POSP2Transaction(models.Model):
    """
    Model para armazenar transações sincronizadas do aplicativo POSP2
    """
    transaction_id = models.CharField(max_length=255, unique=True, verbose_name="ID da Transação")
    transaction_data = models.TextField(verbose_name="Dados da Transação (JSON)")
    cpf = models.CharField(max_length=11, blank=True, null=True, verbose_name="CPF")
    celular = models.CharField(max_length=20, blank=True, null=True, verbose_name="Celular")
    terminal = models.CharField(max_length=50, blank=True, null=True, verbose_name="Terminal")
    valor_original = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Valor Original")
    idempotency_key = models.CharField(max_length=255, unique=True, verbose_name="Chave de Idempotência")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    
    class Meta:
        db_table = 'posp2_transactions'
        verbose_name = "Transação POSP2"
        verbose_name_plural = "Transações POSP2"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Transação {self.transaction_id} - {self.terminal}"

class VersaoTerminal(models.Model):
    """
    Model para controle de versões permitidas dos terminais
    """
    versao_terminal = models.CharField(max_length=50, unique=True, verbose_name="Versão do Terminal")
    permitida = models.BooleanField(default=True, verbose_name="Permitida")
    
    class Meta:
        db_table = 'versoes_terminal'
        verbose_name = "Versão do Terminal"
        verbose_name_plural = "Versões dos Terminais"
        ordering = ['versao_terminal']
    
    def __str__(self):
        status = "Permitida" if self.permitida else "Bloqueada"
        return f"Versão {self.versao_terminal} - {status}"


class Terminal(models.Model):
    """
    Modelo para tabela terminais - informações dos terminais POS
    Usado no script pinbank_cria_base_gestao.php
    """
    
    id = models.PositiveIntegerField(primary_key=True)
    loja_id = models.IntegerField(null=True, blank=True, verbose_name="ID da Loja")
    terminal = models.CharField(max_length=256, null=True, blank=True, verbose_name="Número de Série Terminal")
    idterminal = models.CharField(max_length=256, null=True, blank=True, verbose_name="ID Terminal")
    endereco = models.CharField(max_length=1024, null=True, blank=True, verbose_name="Endereço")
    contato = models.CharField(max_length=256, null=True, blank=True, verbose_name="Contato")
    inicio = models.IntegerField(null=True, blank=True, verbose_name="Início (timestamp)")
    fim = models.IntegerField(null=True, blank=True, verbose_name="Fim (timestamp)")
    
    class Meta:
        db_table = 'terminais'
        managed = False  # Django não gerencia esta tabela (legado)
        verbose_name = 'Terminal'
        verbose_name_plural = 'Terminais'
    
    def __str__(self):
        return f"Terminal {self.idterminal} - Loja {self.loja_id}"
    
    def set_inicio_date(self, data):
        """Converte date para timestamp e define no campo inicio"""
        from datetime import datetime
        if data:
            self.inicio = int(datetime.combine(data, datetime.min.time()).timestamp())
        else:
            self.inicio = 0
    
    def set_fim_date(self, data):
        """Converte date para timestamp e define no campo fim"""
        from datetime import datetime
        if data:
            self.fim = int(datetime.combine(data, datetime.min.time()).timestamp())
        else:
            self.fim = 0


class TransactionData(models.Model):
    """
    Modelo para tabela transactiondata - dados de transações POS
    Usado no script pinbank_cria_base_gestao.php
    """
    
    id = models.PositiveIntegerField(primary_key=True)
    datahora = models.CharField(max_length=256, null=True, blank=True)
    valor_original = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    celular = models.CharField(max_length=256, null=True, blank=True)
    cpf = models.CharField(max_length=256, null=True, blank=True)
    terminal = models.CharField(max_length=256, null=True, blank=True)
    nsuHostCancellation = models.IntegerField(null=True, blank=True)
    amountCancellation = models.IntegerField(null=True, blank=True)
    originalAmount = models.IntegerField(null=True, blank=True)
    preAuthorizationConfirmationTimestamp = models.BigIntegerField(null=True, blank=True)
    amount = models.IntegerField(null=True, blank=True)
    nsuTerminal = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=256, null=True, blank=True)
    transactionWithSignature = models.BooleanField(null=True, blank=True)
    nsuAcquirer = models.CharField(max_length=256, null=True, blank=True)
    nsuPinbank = models.BigIntegerField(null=True, blank=True)
    arqc = models.CharField(max_length=256, null=True, blank=True)
    aid = models.CharField(max_length=256, null=True, blank=True)
    terminalTimestamp = models.BigIntegerField(null=True, blank=True)
    captureType = models.CharField(max_length=256, null=True, blank=True)
    hostTimestampCancellation = models.BigIntegerField(null=True, blank=True)
    authorizationCode = models.CharField(max_length=256, null=True, blank=True)
    nsuHost = models.IntegerField(null=True, blank=True)
    applicationName = models.CharField(max_length=256, null=True, blank=True)
    brand = models.CharField(max_length=256, null=True, blank=True)
    paymentMethod = models.CharField(max_length=256, null=True, blank=True)
    totalInstallments = models.IntegerField(null=True, blank=True)
    nsuTerminalCancellation = models.IntegerField(null=True, blank=True)
    billPaymentEffectiveDate = models.BigIntegerField(null=True, blank=True)
    pinCaptured = models.BooleanField(null=True, blank=True)
    hostTimestamp = models.BigIntegerField(null=True, blank=True)
    capturedTransaction = models.BooleanField(null=True, blank=True)
    cardName = models.CharField(max_length=256, null=True, blank=True)
    cardNumber = models.CharField(max_length=256, null=True, blank=True)
    
    # Campos para suporte a cashback (Wall='C')
    valor_desconto = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="Valor Desconto",
        help_text="Valor do desconto WallClub aplicado"
    )
    
    valor_cashback = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name="Valor Cashback",
        help_text="Valor do cashback creditado (wall='C')"
    )
    
    autorizacao_id = models.CharField(
        max_length=40, null=True, blank=True,
        verbose_name="ID Autorização",
        help_text="ID da autorização de uso de saldo"
    )
    
    cashback_concedido = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, default=0,
        verbose_name="Cashback Concedido",
        help_text="Valor do cashback concedido na transação"
    )
    
    saldo_usado = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name="Saldo Usado",
        help_text="Saldo da conta digital usado no pagamento"
    )
    
    modalidade_wall = models.CharField(
        max_length=1, null=True, blank=True,
        choices=[('S', 'Wall'), ('N', 'Sem Wall'), ('C', 'Cashback')],
        verbose_name="Modalidade Wall"
    )
    
    class Meta:
        db_table = 'transactiondata'
        managed = False  # Django não gerencia esta tabela (legado)
        verbose_name = 'Transaction Data'
        verbose_name_plural = 'Transaction Data'
    
    def __str__(self):
        return f"Transaction {self.id} - NSU: {self.nsuPinbank}"


class TransactionDataOwn(models.Model):
    """
    Modelo para tabela transactiondata_own - dados de transações POS via SDK Ágilli (Own)
    Estrutura específica para transações Own Financial
    """
    
    id = models.PositiveIntegerField(primary_key=True)
    datahora = models.DateTimeField(verbose_name="Data/Hora")
    valor_original = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor Original")
    
    # Identificação do cliente/terminal
    celular = models.CharField(max_length=256, null=True, blank=True)
    cpf = models.CharField(max_length=256, null=True, blank=True)
    terminal = models.CharField(max_length=256, verbose_name="ID do Terminal")
    operador_pos = models.CharField(max_length=10, null=True, blank=True)
    
    # Identificadores da transação Own
    txTransactionId = models.CharField(max_length=50, unique=True, verbose_name="ID Transação Own")
    nsuTerminal = models.CharField(max_length=50, null=True, blank=True, verbose_name="NSU Terminal")
    nsuHost = models.CharField(max_length=50, null=True, blank=True, verbose_name="NSU Host")
    authorizationCode = models.CharField(max_length=256, null=True, blank=True)
    transactionReturn = models.CharField(max_length=10, null=True, blank=True, verbose_name="Código Retorno")
    
    # Valores e parcelas
    amount = models.IntegerField(verbose_name="Valor em Centavos")
    originalAmount = models.IntegerField(verbose_name="Valor Original em Centavos")
    totalInstallments = models.IntegerField(default=1, verbose_name="Número de Parcelas")
    
    # Método de pagamento e operação
    operationId = models.IntegerField(verbose_name="ID Operação")
    paymentMethod = models.CharField(max_length=256, verbose_name="Método de Pagamento")
    
    # Dados do cartão
    brand = models.CharField(max_length=256, verbose_name="Bandeira")
    cardNumber = models.CharField(max_length=256, null=True, blank=True)
    cardName = models.CharField(max_length=256, null=True, blank=True)
    
    # Comprovantes Ágilli
    customerTicket = models.TextField(null=True, blank=True, verbose_name="Comprovante Cliente")
    estabTicket = models.TextField(null=True, blank=True, verbose_name="Comprovante Estabelecimento")
    e2ePixId = models.CharField(max_length=100, null=True, blank=True, verbose_name="ID E2E PIX")
    
    # Timestamps
    terminalTimestamp = models.BigIntegerField(null=True, blank=True)
    hostTimestamp = models.BigIntegerField(null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=256, verbose_name="Status")
    capturedTransaction = models.BooleanField(default=True)
    
    # Dados do estabelecimento
    cnpj = models.CharField(max_length=14, verbose_name="CNPJ")
    
    # Origem
    sdk = models.CharField(max_length=20, default='agilli', verbose_name="SDK")
    
    # Campos Wall Club
    valor_desconto = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, default=0,
        verbose_name="Valor Desconto"
    )
    valor_cashback = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, default=0,
        verbose_name="Valor Cashback"
    )
    autorizacao_id = models.CharField(max_length=40, null=True, blank=True)
    cashback_concedido = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, default=0,
        verbose_name="Cashback Concedido"
    )
    saldo_usado = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name="Saldo Usado"
    )
    modalidade_wall = models.CharField(
        max_length=1, null=True, blank=True,
        choices=[('S', 'Wall'), ('N', 'Sem Wall'), ('C', 'Cashback')]
    )
    
    # Auditoria
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'transactiondata_own'
        managed = False
        verbose_name = 'Transaction Data Own'
        verbose_name_plural = 'Transaction Data Own'
        indexes = [
            models.Index(fields=['datahora']),
            models.Index(fields=['cpf']),
            models.Index(fields=['terminal']),
            models.Index(fields=['txTransactionId']),
            models.Index(fields=['cnpj']),
            models.Index(fields=['sdk']),
            models.Index(fields=['status']),
            models.Index(fields=['operationId']),
        ]
    
    def __str__(self):
        return f"Transaction Own {self.id} - TxID: {self.txTransactionId}"
