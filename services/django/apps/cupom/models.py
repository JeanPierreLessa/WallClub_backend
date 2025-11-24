from django.db import models
from decimal import Decimal


class Cupom(models.Model):
    """
    Model para cupons de desconto
    Descontos:
    - FIXO: Valor fixo em reais (ex: R$ 10,00)
    - PERCENTUAL: Percentual sobre o valor (ex: 15%)
    """
    
    TIPO_CUPOM_CHOICES = [
        ('GENERICO', 'Genérico'),
        ('INDIVIDUAL', 'Individual'),
    ]
    
    TIPO_DESCONTO_CHOICES = [
        ('FIXO', 'Fixo (R$)'),
        ('PERCENTUAL', 'Percentual (%)'),
    ]
    
    codigo = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name='Código do Cupom',
        help_text='Código único que o cliente digitará (ex: PROMO10)'
    )
    loja_id = models.BigIntegerField(
        verbose_name='Loja',
        help_text='Loja que criou o cupom'
    )
    tipo_cupom = models.CharField(
        max_length=20,
        choices=TIPO_CUPOM_CHOICES,
        default='GENERICO',
        verbose_name='Tipo de Cupom'
    )
    tipo_desconto = models.CharField(
        max_length=20,
        choices=TIPO_DESCONTO_CHOICES,
        verbose_name='Tipo de Desconto'
    )
    valor_desconto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Valor do Desconto',
        help_text='Valor fixo em R$ ou percentual (ex: 15.00 = 15%)'
    )
    valor_minimo_compra = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Valor Mínimo de Compra',
        help_text='Valor mínimo da transação para usar o cupom (0 = sem mínimo)'
    )
    limite_uso_total = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Limite de Uso Total',
        help_text='Quantidade máxima de usos (NULL = ilimitado)'
    )
    limite_uso_por_cpf = models.IntegerField(
        default=1,
        verbose_name='Limite de Uso por CPF',
        help_text='Quantas vezes o mesmo CPF pode usar este cupom'
    )
    quantidade_usada = models.IntegerField(
        default=0,
        verbose_name='Quantidade Usada',
        help_text='Contador de usos do cupom'
    )
    cliente_id = models.BigIntegerField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name='Cliente',
        help_text='Se tipo INDIVIDUAL, CPF vinculado ao cupom'
    )
    data_inicio = models.DateTimeField(
        verbose_name='Data de Início',
        help_text='Data/hora de início da validade'
    )
    data_fim = models.DateTimeField(
        verbose_name='Data de Fim',
        help_text='Data/hora de fim da validade'
    )
    ativo = models.BooleanField(
        default=True,
        verbose_name='Ativo'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Criado em'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Atualizado em'
    )
    
    class Meta:
        app_label = 'cupom'
        db_table = 'cupom'
        verbose_name = 'Cupom'
        verbose_name_plural = 'Cupons'
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['loja_id', 'ativo']),
            models.Index(fields=['cliente_id']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.codigo} - {self.get_tipo_desconto_display()}"
    
    def esta_valido(self):
        """Verifica se o cupom está dentro do período de validade"""
        from datetime import datetime
        agora = datetime.now()
        return self.data_inicio <= agora <= self.data_fim
    
    def pode_ser_usado(self):
        """Verifica se o cupom ainda pode ser usado (limite global)"""
        if not self.limite_uso_total:
            return True
        return self.quantidade_usada < self.limite_uso_total
    
    def calcular_desconto(self, valor_base):
        """
        Calcula o valor do desconto a ser aplicado.
        
        Args:
            valor_base: Valor sobre o qual aplicar o desconto
            
        Returns:
            Decimal: Valor do desconto (nunca maior que valor_base)
        """
        if self.tipo_desconto == 'FIXO':
            desconto = self.valor_desconto
        else:  # PERCENTUAL
            desconto = valor_base * (self.valor_desconto / Decimal('100'))
        
        # Desconto não pode ser maior que o valor base
        return min(desconto, valor_base)


class CupomUso(models.Model):
    """
    Histórico de uso de cupons.
    Registra cada vez que um cupom é usado em uma transação.
    """
    
    TRANSACAO_TIPO_CHOICES = [
        ('POS', 'Terminal POS'),
        ('CHECKOUT', 'Checkout Web'),
    ]
    
    cupom_id = models.BigIntegerField(
        db_index=True,
        verbose_name='Cupom'
    )
    cliente_id = models.BigIntegerField(
        db_index=True,
        verbose_name='Cliente'
    )
    loja_id = models.BigIntegerField(
        db_index=True,
        verbose_name='Loja'
    )
    transacao_tipo = models.CharField(
        max_length=20,
        choices=TRANSACAO_TIPO_CHOICES,
        verbose_name='Tipo de Transação'
    )
    transacao_id = models.BigIntegerField(
        verbose_name='ID da Transação',
        help_text='ID da TransactionData ou CheckoutTransaction'
    )
    nsu = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='NSU',
        help_text='NSU da transação (se disponível)'
    )
    valor_transacao_original = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Valor Original',
        help_text='Valor da transação antes do cupom'
    )
    valor_desconto_aplicado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Valor do Desconto',
        help_text='Valor do desconto aplicado'
    )
    valor_transacao_final = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Valor Final',
        help_text='Valor da transação após o cupom'
    )
    estornado = models.BooleanField(
        default=False,
        verbose_name='Estornado',
        help_text='Se a transação foi estornada (cupom NÃO retorna)'
    )
    usado_em = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Usado em'
    )
    ip_address = models.CharField(
        max_length=45,
        null=True,
        blank=True,
        verbose_name='IP Address'
    )
    
    class Meta:
        app_label = 'cupom'
        db_table = 'cupom_uso'
        verbose_name = 'Uso de Cupom'
        verbose_name_plural = 'Usos de Cupons'
        indexes = [
            models.Index(fields=['cupom_id']),
            models.Index(fields=['cliente_id']),
            models.Index(fields=['transacao_tipo', 'transacao_id']),
            models.Index(fields=['usado_em']),
        ]
        ordering = ['-usado_em']
    
    def __str__(self):
        return f"Cupom {self.cupom_id} - Cliente {self.cliente_id} - {self.usado_em}"
