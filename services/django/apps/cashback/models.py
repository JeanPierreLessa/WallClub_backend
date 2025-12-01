from django.db import models
from decimal import Decimal


class RegraCashback(models.Model):
    """
    Classe base abstrata para regras de cashback.
    Compartilhada entre Wall e Loja.
    """
    
    TIPO_CONCESSAO_CHOICES = [
        ('FIXO', 'Fixo (R$)'),
        ('PERCENTUAL', 'Percentual (%)'),
    ]
    
    # Identificação
    nome = models.CharField(max_length=100, verbose_name='Nome da Regra')
    descricao = models.TextField(verbose_name='Descrição')
    ativo = models.BooleanField(default=True, verbose_name='Ativo')
    prioridade = models.IntegerField(
        default=0,
        verbose_name='Prioridade',
        help_text='Maior número = maior prioridade'
    )
    
    # Tipo de concessão
    tipo_concessao = models.CharField(
        max_length=20,
        choices=TIPO_CONCESSAO_CHOICES,
        verbose_name='Tipo de Concessão'
    )
    valor_concessao = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Valor da Concessão',
        help_text='Valor fixo em R$ ou percentual (ex: 15.00 = 15%)'
    )
    
    # Condições
    valor_minimo_compra = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Valor Mínimo da Compra',
        help_text='Valor mínimo da transação para conceder cashback'
    )
    valor_maximo_cashback = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Valor Máximo de Cashback',
        help_text='Valor máximo de cashback concedido por transação (deixe em branco para ilimitado)'
    )
    
    # Vigência
    vigencia_inicio = models.DateTimeField(verbose_name='Início da Vigência')
    vigencia_fim = models.DateTimeField(verbose_name='Fim da Vigência')
    
    # Auditoria
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True
    
    def calcular_cashback(self, valor_base):
        """
        Calcula valor do cashback baseado no tipo de concessão.
        
        Args:
            valor_base: Valor da transação após todos os descontos
            
        Returns:
            Decimal: Valor do cashback calculado
        """
        if self.tipo_concessao == 'FIXO':
            cashback = self.valor_concessao
        else:  # PERCENTUAL
            cashback = valor_base * (self.valor_concessao / Decimal('100'))
        
        # Aplicar teto se configurado
        if self.valor_maximo_cashback:
            cashback = min(cashback, self.valor_maximo_cashback)
        
        # Cashback nunca pode ser maior que o valor da transação
        return min(cashback, valor_base)
    
    def __str__(self):
        return self.nome


class RegraCashbackLoja(RegraCashback):
    """
    Regras de cashback criadas pela loja.
    Aplicação automática baseada em condições.
    """
    
    loja_id = models.BigIntegerField(verbose_name='ID da Loja', db_index=True)
    
    class Meta:
        db_table = 'cashback_regra_loja'
        app_label = 'cashback'
        verbose_name = 'Regra de Cashback Loja'
        verbose_name_plural = 'Regras de Cashback Loja'
        ordering = ['-prioridade', '-created_at']
    
    # Filtros opcionais
    formas_pagamento = models.JSONField(
        null=True,
        blank=True,
        verbose_name='Formas de Pagamento',
        help_text='Lista de formas aceitas: ["PIX", "DEBITO", "CREDITO"]'
    )
    dias_semana = models.JSONField(
        null=True,
        blank=True,
        verbose_name='Dias da Semana',
        help_text='Dias da semana: [0,1,2,3,4,5,6] (0=domingo)'
    )
    horario_inicio = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Horário Início'
    )
    horario_fim = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Horário Fim'
    )
    
    # Limites de uso
    limite_uso_cliente_dia = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Limite de Uso por Cliente/Dia',
        help_text='Máximo de vezes que um cliente pode usar por dia'
    )
    limite_uso_cliente_mes = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Limite de Uso por Cliente/Mês',
        help_text='Máximo de vezes que um cliente pode usar por mês'
    )
    orcamento_mensal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Orçamento Mensal',
        help_text='Orçamento total da loja para cashback no mês'
    )
    gasto_mes_atual = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Gasto no Mês Atual',
        help_text='Total gasto no mês atual'
    )
    
    class Meta:
        db_table = 'cashback_regra_loja'
        verbose_name = 'Regra Cashback Loja'
        verbose_name_plural = 'Regras Cashback Loja'
        indexes = [
            models.Index(fields=['loja_id', 'ativo']),
            models.Index(fields=['vigencia_inicio', 'vigencia_fim']),
        ]


class CashbackUso(models.Model):
    """
    Histórico unificado de cashback aplicado (Wall + Loja).
    """
    
    TIPO_ORIGEM_CHOICES = [
        ('WALL', 'Cashback Wall'),
        ('LOJA', 'Cashback Loja'),
    ]
    
    TRANSACAO_TIPO_CHOICES = [
        ('POS', 'Terminal POS'),
        ('CHECKOUT', 'Checkout Web'),
    ]
    
    STATUS_CHOICES = [
        ('RETIDO', 'Retido (em carência)'),
        ('LIBERADO', 'Liberado'),
        ('EXPIRADO', 'Expirado'),
        ('ESTORNADO', 'Estornado'),
    ]
    
    # Origem
    tipo_origem = models.CharField(
        max_length=10,
        choices=TIPO_ORIGEM_CHOICES,
        verbose_name='Tipo de Origem'
    )
    parametro_wall_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name='ID do Parâmetro Wall',
        help_text='ID do ParametrosWall (wall=C) - apenas para tipo_origem=WALL'
    )
    regra_loja_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name='ID da Regra Loja',
        help_text='ID da RegraCashbackLoja - apenas para tipo_origem=LOJA'
    )
    
    # Transação
    cliente_id = models.BigIntegerField(db_index=True, verbose_name='ID do Cliente')
    loja_id = models.BigIntegerField(db_index=True, verbose_name='ID da Loja')
    canal_id = models.IntegerField(verbose_name='ID do Canal')
    transacao_tipo = models.CharField(
        max_length=20,
        choices=TRANSACAO_TIPO_CHOICES,
        verbose_name='Tipo de Transação'
    )
    transacao_id = models.BigIntegerField(verbose_name='ID da Transação')
    
    # Valores
    valor_transacao = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Valor da Transação'
    )
    valor_cashback = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Valor do Cashback'
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='RETIDO',
        verbose_name='Status'
    )
    
    # Datas
    aplicado_em = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='Aplicado em'
    )
    liberado_em = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Liberado em'
    )
    expira_em = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Expira em'
    )
    
    # Referência na conta digital
    movimentacao_id = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name='ID da Movimentação',
        help_text='ID da MovimentacaoContaDigital'
    )
    
    class Meta:
        db_table = 'cashback_uso'
        app_label = 'cashback'
        verbose_name = 'Uso de Cashback'
        verbose_name_plural = 'Usos de Cashback'
        indexes = [
            models.Index(fields=['cliente_id', 'aplicado_em']),
            models.Index(fields=['tipo_origem', 'status']),
            models.Index(fields=['transacao_tipo', 'transacao_id']),
            models.Index(fields=['status', 'liberado_em']),
            models.Index(fields=['status', 'expira_em']),
        ]
        ordering = ['-aplicado_em']
    
    def __str__(self):
        return f"Cashback {self.tipo_origem} - Cliente {self.cliente_id} - R$ {self.valor_cashback}"
