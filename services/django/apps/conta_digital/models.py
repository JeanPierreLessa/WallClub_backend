"""
Modelos para o sistema de conta digital customizada.
Implementação simples e performática sem Django-Ledger.
"""
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal


class ContaDigital(models.Model):
    """
    Conta digital do cliente com controle direto de saldo.
    """
    cliente_id = models.IntegerField(db_index=True)
    canal_id = models.IntegerField()
    cpf = models.CharField(max_length=11, db_index=True)
    
    # Saldos
    saldo_atual = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Saldo atual disponível'
    )
    saldo_bloqueado = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Saldo temporariamente bloqueado'
    )
    cashback_disponivel = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Cashback disponível para uso'
    )
    cashback_bloqueado = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Cashback em retenção/bloqueio'
    )
    
    # Limites
    limite_diario = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('5000.00'),
        help_text='Limite de movimentação diária'
    )
    limite_mensal = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('50000.00'),
        help_text='Limite de movimentação mensal'
    )
    
    # Status
    ativa = models.BooleanField(default=True)
    bloqueada = models.BooleanField(default=False)
    motivo_bloqueio = models.TextField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'conta_digital'
        verbose_name = 'Conta Digital'
        verbose_name_plural = 'Contas Digitais'
        unique_together = [['cliente_id', 'canal_id']]
        indexes = [
            models.Index(fields=['cliente_id', 'canal_id']),
            models.Index(fields=['cpf']),
            models.Index(fields=['ativa', 'bloqueada']),
        ]
    
    def __str__(self):
        return f"Conta Digital Cliente {self.cliente_id} - Canal {self.canal_id}"
    
    def get_saldo_disponivel(self):
        """Retorna saldo disponível (atual - bloqueado)"""
        return self.saldo_atual - self.saldo_bloqueado
    
    def get_cashback_total(self):
        """Retorna cashback total (disponível + bloqueado)"""
        return self.cashback_disponivel + self.cashback_bloqueado
    
    def get_saldo_total_disponivel(self):
        """Retorna saldo total disponível (saldo + cashback disponível)"""
        return self.get_saldo_disponivel() + self.cashback_disponivel
    
    def tem_saldo_suficiente(self, valor):
        """Verifica se tem saldo suficiente para débito"""
        return self.get_saldo_disponivel() >= valor
    
    def tem_saldo_total_suficiente(self, valor):
        """Verifica se tem saldo total suficiente (incluindo cashback)"""
        return self.get_saldo_total_disponivel() >= valor
    
    def pode_movimentar(self, valor):
        """Verifica se pode movimentar o valor (conta ativa e não bloqueada)"""
        return self.ativa and not self.bloqueada and self.tem_saldo_suficiente(valor)


class TipoMovimentacao(models.Model):
    """
    Tipos de movimentações da conta digital.
    """
    codigo = models.CharField(max_length=30, unique=True)
    nome = models.CharField(max_length=100)
    descricao = models.TextField()
    
    # Configurações
    debita_saldo = models.BooleanField(
        default=False,
        help_text='Se True, debita do saldo. Se False, credita no saldo'
    )
    permite_estorno = models.BooleanField(default=True)
    requer_autorizacao = models.BooleanField(default=False)
    visivel_extrato = models.BooleanField(default=True)
    
    # Categorização
    categoria = models.CharField(max_length=50, choices=[
        ('CREDITO', 'Crédito'),
        ('DEBITO', 'Débito'),
        ('TRANSFERENCIA', 'Transferência'),
        ('CASHBACK', 'Cashback'),
        ('CASHBACK_BLOQUEIO', 'Cashback Bloqueio'),
        ('CASHBACK_LIBERACAO', 'Cashback Liberação'),
        ('ESTORNO', 'Estorno'),
        ('BLOQUEIO', 'Bloqueio'),
        ('DESBLOQUEIO', 'Desbloqueio'),
        ('TAXA', 'Taxa'),
        ('PIX', 'PIX'),
    ])
    
    # Configurações específicas para cashback
    afeta_cashback = models.BooleanField(
        default=False,
        help_text='Se True, afeta saldo de cashback ao invés do saldo normal'
    )
    periodo_retencao_dias = models.IntegerField(
        default=0,
        help_text='Dias de retenção para cashback (0 = sem retenção)'
    )
    
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'conta_digital_tipos_movimentacao'
        verbose_name = 'Tipo de Movimentação'
        verbose_name_plural = 'Tipos de Movimentação'
    
    def __str__(self):
        return f"{self.codigo} - {self.nome}"


class MovimentacaoContaDigital(models.Model):
    """
    Movimentações da conta digital com controle de saldo.
    """
    conta_digital = models.ForeignKey(
        ContaDigital,
        on_delete=models.CASCADE,
        related_name='movimentacoes'
    )
    tipo_movimentacao = models.ForeignKey(
        TipoMovimentacao,
        on_delete=models.PROTECT
    )
    
    # Controle de saldo
    saldo_anterior = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text='Saldo antes da movimentação'
    )
    saldo_posterior = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text='Saldo após a movimentação'
    )
    
    # Dados da movimentação
    valor = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    descricao = models.CharField(max_length=200)
    observacoes = models.TextField(null=True, blank=True)
    
    # Referências externas
    referencia_externa = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='ID da transação no sistema origem'
    )
    sistema_origem = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text='Sistema que originou a movimentação'
    )
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('PENDENTE', 'Pendente'),
        ('PROCESSADA', 'Processada'),
        ('CANCELADA', 'Cancelada'),
        ('ESTORNADA', 'Estornada'),
    ], default='PENDENTE')
    
    # Estorno
    movimentacao_estorno = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='estornos'
    )
    
    # Timestamps
    data_movimentacao = models.DateTimeField(default=timezone.now)
    processada_em = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'conta_digital_movimentacoes'
        verbose_name = 'Movimentação da Conta Digital'
        verbose_name_plural = 'Movimentações da Conta Digital'
        ordering = ['-data_movimentacao']
        indexes = [
            models.Index(fields=['conta_digital', 'data_movimentacao']),
            models.Index(fields=['referencia_externa', 'sistema_origem']),
            models.Index(fields=['status']),
            models.Index(fields=['tipo_movimentacao', 'data_movimentacao']),
        ]
    
    def __str__(self):
        return f"{self.tipo_movimentacao.codigo} - R$ {self.valor} - {self.conta_digital}"
    
    def processar(self):
        """Marca a movimentação como processada"""
        if self.status == 'PENDENTE':
            self.status = 'PROCESSADA'
            from datetime import datetime
            self.processada_em = datetime.now()
            self.save()
    
    def cancelar(self, motivo=""):
        """Cancela a movimentação"""
        if self.status == 'PENDENTE':
            self.status = 'CANCELADA'
            if motivo:
                self.observacoes = f"{self.observacoes or ''}\nCancelada: {motivo}".strip()
            self.save()
    
    def estornar(self, motivo=""):
        """Cria movimentação de estorno"""
        if self.status != 'PROCESSADA':
            raise ValueError("Apenas movimentações processadas podem ser estornadas")
        
        if not self.tipo_movimentacao.permite_estorno:
            raise ValueError("Este tipo de movimentação não permite estorno")
        
        # Será implementado no service
        from .services import ContaDigitalService
        return ContaDigitalService.estornar_movimentacao(self.id, motivo)


class CashbackRetencao(models.Model):
    """
    Controle de retenção de cashback com liberação automática.
    """
    conta_digital = models.ForeignKey(
        ContaDigital,
        on_delete=models.CASCADE,
        related_name='retencoes_cashback'
    )
    movimentacao_origem = models.ForeignKey(
        MovimentacaoContaDigital,
        on_delete=models.CASCADE,
        related_name='retencao_cashback'
    )
    
    # Valores
    valor_retido = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text='Valor do cashback em retenção'
    )
    valor_liberado = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Valor já liberado'
    )
    
    # Controle de retenção
    data_retencao = models.DateTimeField(default=timezone.now)
    data_liberacao_prevista = models.DateTimeField(
        help_text='Data prevista para liberação automática'
    )
    data_liberacao_efetiva = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Data efetiva da liberação'
    )
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('RETIDO', 'Retido'),
        ('LIBERADO', 'Liberado'),
        ('CANCELADO', 'Cancelado'),
    ], default='RETIDO')
    
    motivo_retencao = models.CharField(
        max_length=100,
        default='Período de carência cashback',
        help_text='Motivo da retenção'
    )
    motivo_liberacao = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='Motivo da liberação (manual ou automática)'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'conta_digital_cashback_retencoes'
        verbose_name = 'Retenção de Cashback'
        verbose_name_plural = 'Retenções de Cashback'
        ordering = ['-data_retencao']
        indexes = [
            models.Index(fields=['conta_digital', 'status']),
            models.Index(fields=['data_liberacao_prevista', 'status']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Retenção R$ {self.valor_retido} - {self.conta_digital}"
    
    def pode_liberar(self):
        """Verifica se pode liberar o cashback"""
        return (
            self.status == 'RETIDO' and 
            datetime.now() >= self.data_liberacao_prevista
        )
    
    def liberar(self, motivo="Liberação automática"):
        """Libera o cashback retido"""
        if not self.pode_liberar():
            raise ValueError("Cashback não pode ser liberado ainda")
        
        # Será implementado no service
        from .services import ContaDigitalService
        return ContaDigitalService.liberar_cashback_retido(self.id, motivo)


class ConfiguracaoContaDigital(models.Model):
    """
    Configurações globais da conta digital por canal.
    """
    canal_id = models.IntegerField(unique=True)
    nome_canal = models.CharField(max_length=100)
    
    # Limites padrão
    limite_diario_padrao = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('5000.00'),
        help_text='Limite diário padrão para novas contas'
    )
    limite_mensal_padrao = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal('50000.00'),
        help_text='Limite mensal padrão para novas contas'
    )
    
    # Configurações operacionais
    permite_saldo_negativo = models.BooleanField(
        default=False,
        help_text='Permite saldo negativo (crédito)'
    )
    auto_criar_conta = models.BooleanField(
        default=True,
        help_text='Cria conta automaticamente no primeiro acesso'
    )
    
    # Configurações de cashback
    periodo_retencao_cashback_dias = models.IntegerField(
        default=30,
        help_text='Dias de retenção padrão para cashback'
    )
    
    # Taxas
    taxa_transferencia = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Taxa para transferências'
    )
    taxa_saque = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Taxa para saques'
    )
    
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'conta_digital_configuracoes'
        verbose_name = 'Configuração da Conta Digital'
        verbose_name_plural = 'Configurações da Conta Digital'
    
    def __str__(self):
        return f"Config Conta Digital - {self.nome_canal}"


class AutorizacaoUsoSaldo(models.Model):
    """
    Controle de autorizações para uso de saldo no POS.
    Cliente aprova no app antes do POS debitar.
    """
    autorizacao_id = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text='UUID único da autorização'
    )
    cliente_id = models.IntegerField(db_index=True)
    conta_digital = models.ForeignKey(
        ContaDigital,
        on_delete=models.CASCADE,
        related_name='autorizacoes_uso_saldo'
    )
    
    # Valores
    valor_solicitado = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Valor solicitado para uso'
    )
    valor_bloqueado = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Valor efetivamente bloqueado'
    )
    
    # Origem
    terminal = models.CharField(
        max_length=50,
        help_text='Terminal que solicitou'
    )
    nsu_transacao = models.CharField(
        max_length=50,
        db_index=True,
        null=True,
        blank=True,
        help_text='NSU da transação POS'
    )
    ip_address = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('PENDENTE', 'Pendente'),
        ('APROVADO', 'Aprovado'),
        ('NEGADO', 'Negado'),
        ('EXPIRADO', 'Expirado'),
        ('CONCLUIDA', 'Concluída'),
        ('ESTORNADA', 'Estornada'),
    ], default='PENDENTE', db_index=True)
    
    # Timestamps
    data_solicitacao = models.DateTimeField(default=timezone.now)
    data_aprovacao = models.DateTimeField(null=True, blank=True)
    data_expiracao = models.DateTimeField(
        help_text='Data/hora de expiração da autorização'
    )
    data_conclusao = models.DateTimeField(null=True, blank=True)
    
    # Referências de movimentações
    movimentacao_debito = models.ForeignKey(
        MovimentacaoContaDigital,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='autorizacao_debito'
    )
    movimentacao_estorno = models.ForeignKey(
        MovimentacaoContaDigital,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='autorizacao_estorno'
    )
    
    # Timestamps de controle
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'conta_digital_autorizacao_uso_saldo'
        verbose_name = 'Autorização de Uso de Saldo'
        verbose_name_plural = 'Autorizações de Uso de Saldo'
        ordering = ['-data_solicitacao']
        indexes = [
            models.Index(fields=['autorizacao_id']),
            models.Index(fields=['cliente_id', 'status']),
            models.Index(fields=['status', 'data_expiracao']),
            models.Index(fields=['nsu_transacao']),
            models.Index(fields=['terminal', 'status']),
        ]
    
    def __str__(self):
        return f"Autorização {self.autorizacao_id[:8]}... - {self.status} - R$ {self.valor_solicitado}"
    
    def esta_expirada(self):
        """Verifica se a autorização está expirada"""
        from datetime import datetime
        return datetime.now() >= self.data_expiracao
    
    def pode_aprovar(self):
        """Verifica se pode ser aprovada"""
        return self.status == 'PENDENTE' and not self.esta_expirada()
    
    def pode_debitar(self):
        """Verifica se pode debitar saldo"""
        return self.status == 'APROVADO' and not self.esta_expirada()
    
    def pode_estornar(self):
        """Verifica se pode estornar"""
        return self.status == 'CONCLUIDA' and self.movimentacao_debito is not None


class CashbackParamLoja(models.Model):
    """
    Parâmetros de cashback por loja.
    Define percentuais de utilização e concessão de cashback.
    """
    PROCESSO_CHOICES = [
        ('POS', 'POS'),
        ('ECOMMERCE', 'E-commerce'),
    ]
    
    loja_id = models.IntegerField(db_index=True)
    processo_venda = models.CharField(
        max_length=15,
        choices=PROCESSO_CHOICES,
        help_text='Tipo de processo de venda'
    )
    percentual_utilizacao = models.DecimalField(
        max_digits=8,
        decimal_places=5,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Percentual máximo do valor da compra que pode ser pago com cashback'
    )
    percentual_concessao = models.DecimalField(
        max_digits=8,
        decimal_places=5,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Percentual de cashback concedido sobre o valor da transação'
    )
    
    class Meta:
        db_table = 'conta_digital_cashback_param_loja'
        verbose_name = 'Parâmetro de Cashback por Loja'
        verbose_name_plural = 'Parâmetros de Cashback por Loja'
        unique_together = [['loja_id', 'processo_venda']]
        indexes = [
            models.Index(fields=['loja_id', 'processo_venda']),
        ]
    
    def __str__(self):
        return f"Loja {self.loja_id} - {self.processo_venda} - Util: {self.percentual_utilizacao}% - Conc: {self.percentual_concessao}%"
