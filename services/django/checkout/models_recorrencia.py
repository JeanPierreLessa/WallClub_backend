"""
Models de Recorrência de Pagamentos
Fase 5 - Unificação Portal Vendas + Recorrência

Estrutura limpa: RecorrenciaAgendada cadastra a recorrência,
cada execução gera um novo CheckoutTransaction vinculado.
"""
from django.db import models
from decimal import Decimal
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class RecorrenciaAgendada(models.Model):
    """
    Cadastro de recorrência de pagamento.
    Cada execução gera um novo CheckoutTransaction vinculado.
    """
    
    # Tipo de periodicidade
    TIPO_PERIODICIDADE_CHOICES = [
        ('mensal_dia_fixo', 'Mensal - Dia Fixo do Mês'),
        ('anual_data_fixa', 'Anual - Data Específica do Ano'),
    ]
    
    # Status da recorrência
    STATUS_CHOICES = [
        ('ativo', 'Ativo - Cobrando'),
        ('pausado', 'Pausado Temporariamente'),
        ('cancelado', 'Cancelado'),
        ('hold', 'Hold - Múltiplas Falhas'),
        ('concluido', 'Concluído'),
    ]
    
    # Relacionamentos
    cliente = models.ForeignKey(
        'checkout.CheckoutCliente',
        on_delete=models.PROTECT,
        related_name='recorrencias',
        help_text="Cliente que receberá as cobranças recorrentes"
    )
    
    cartao_tokenizado = models.ForeignKey(
        'checkout.CheckoutCartaoTokenizado',
        on_delete=models.PROTECT,
        related_name='recorrencias',
        help_text="Cartão tokenizado que será cobrado"
    )
    
    loja = models.ForeignKey(
        'estr_organizacional.Loja',
        on_delete=models.PROTECT,
        db_column='loja_id',
        related_name='recorrencias'
    )
    
    vendedor_id = models.IntegerField(
        help_text="ID do vendedor que criou a recorrência"
    )
    
    # Configuração da recorrência
    valor_recorrencia = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Valor fixo da cobrança recorrente"
    )
    
    tipo_periodicidade = models.CharField(
        max_length=20,
        choices=TIPO_PERIODICIDADE_CHOICES,
        help_text="Tipo de periodicidade: mensal ou anual"
    )
    
    # Para mensal: dia do mês (1-31)
    dia_cobranca = models.IntegerField(
        null=True,
        blank=True,
        help_text="Dia do mês para cobrança (1-31). Usado apenas se tipo=mensal_dia_fixo. "
                  "Se dia não existir no mês (ex: 31 em fevereiro), usa próximo dia útil."
    )
    
    # Para anual: data específica (MM-DD)
    mes_cobranca_anual = models.IntegerField(
        null=True,
        blank=True,
        help_text="Mês da cobrança anual (1-12). Usado apenas se tipo=anual_data_fixa."
    )
    
    dia_cobranca_anual = models.IntegerField(
        null=True,
        blank=True,
        help_text="Dia do mês da cobrança anual (1-31). Usado apenas se tipo=anual_data_fixa."
    )
    
    # Controle de execução
    proxima_cobranca = models.DateField(
        db_index=True,
        help_text="Data agendada para próxima cobrança"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ativo',
        db_index=True,
        help_text="Status atual da recorrência"
    )
    
    # Controle de falhas
    tentativas_falhas_consecutivas = models.IntegerField(
        default=0,
        help_text="Número de tentativas consecutivas que falharam"
    )
    
    max_tentativas = models.IntegerField(
        default=3,
        help_text="Máximo de tentativas antes de marcar como hold"
    )
    
    ultima_tentativa_em = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Data/hora da última tentativa de cobrança"
    )
    
    ultima_cobranca_sucesso_em = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Data/hora da última cobrança bem-sucedida"
    )
    
    # Auditoria
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by_vendedor_id = models.IntegerField(
        help_text="ID do vendedor que criou"
    )
    
    descricao = models.CharField(
        max_length=255,
        help_text="Descrição da cobrança enviada ao cliente (ex: Mensalidade Academia)"
    )
    
    class Meta:
        db_table = 'checkout_recorrencias'
        verbose_name = 'Recorrência Agendada'
        verbose_name_plural = 'Recorrências Agendadas'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'proxima_cobranca']),
            models.Index(fields=['loja', 'status']),
            models.Index(fields=['vendedor_id', 'status']),
            models.Index(fields=['cliente', 'status']),
        ]
    
    def __str__(self):
        return f"Recorrência #{self.id} - {self.cliente.nome if self.cliente else 'N/A'} - R$ {self.valor_recorrencia}"
    
    def calcular_proxima_cobranca(self, data_referencia=None):
        """
        Calcula a próxima data de cobrança baseado na periodicidade.
        
        Args:
            data_referencia: Data base para cálculo (default: hoje)
            
        Returns:
            date: Próxima data de cobrança
        """
        if data_referencia is None:
            data_referencia = datetime.now().date()
        
        if self.tipo_periodicidade == 'mensal_dia_fixo':
            # Mensal: avançar 1 mês e ajustar para o dia escolhido
            proxima = data_referencia + relativedelta(months=1)
            
            # Ajustar para o dia escolhido (evitar dias inválidos)
            try:
                # Tentar usar o dia escolhido
                proxima = proxima.replace(day=self.dia_cobranca)
            except ValueError:
                # Dia inválido (ex: 31 em fevereiro) - usar último dia do mês
                proxima = proxima + relativedelta(day=31)
            
            return proxima
            
        elif self.tipo_periodicidade == 'anual_data_fixa':
            # Anual: próximo ano, mesma data
            ano_proximo = data_referencia.year + 1
            
            try:
                proxima = datetime(ano_proximo, self.mes_cobranca_anual, self.dia_cobranca_anual).date()
            except ValueError:
                # Data inválida (ex: 29 de fevereiro em ano não bissexto)
                # Usar último dia do mês
                proxima = datetime(ano_proximo, self.mes_cobranca_anual, 1).date()
                proxima = proxima + relativedelta(day=31)
            
            return proxima
        
        # Fallback: 30 dias
        return data_referencia + timedelta(days=30)
    
    def ajustar_para_dia_util(self, data):
        """
        Se a data cair em fim de semana, ajusta para próxima segunda-feira.
        
        Args:
            data: Data a ser ajustada
            
        Returns:
            date: Data ajustada para dia útil
        """
        # 5 = sábado, 6 = domingo
        while data.weekday() in [5, 6]:
            data = data + timedelta(days=1)
        
        return data
    
    @property
    def periodicidade_display(self):
        """Retorna descrição legível da periodicidade"""
        if self.tipo_periodicidade == 'mensal_dia_fixo':
            return f"Mensal - Todo dia {self.dia_cobranca}"
        elif self.tipo_periodicidade == 'anual_data_fixa':
            return f"Anual - Todo dia {self.dia_cobranca_anual}/{self.mes_cobranca_anual}"
        return "Não definido"
    
    @property
    def total_cobrado(self):
        """Retorna total já cobrado (soma das transações aprovadas)"""
        from checkout.models import CheckoutTransaction
        
        total = CheckoutTransaction.objects.filter(
            checkout_recorrencia=self,
            status='APROVADO'
        ).aggregate(
            total=models.Sum('valor_transacao_final')
        )['total'] or Decimal('0.00')
        
        return total
    
    @property
    def total_execucoes(self):
        """Retorna total de execuções (tentativas de cobrança)"""
        from checkout.models import CheckoutTransaction
        
        return CheckoutTransaction.objects.filter(checkout_recorrencia=self).count()
