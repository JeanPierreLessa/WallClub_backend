from django.db import models
from django.contrib.auth.models import User
from portais.controle_acesso.models import PortalUsuario


class PagamentoEfetuado(models.Model):
    """
    Modelo para tabela pagamentos_efetuados - substitui a antiga tabela financeiro
    Armazena valores financeiros específicos por NSU de transação
    """
    
    id = models.BigAutoField(primary_key=True)
    nsu = models.BigIntegerField(verbose_name="NSU da transação")
    var44 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var45 = models.CharField(max_length=20, null=True, blank=True)
    var58 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var59 = models.CharField(max_length=20, null=True, blank=True)
    var66 = models.CharField(max_length=20, null=True, blank=True)
    var71 = models.CharField(max_length=20, null=True, blank=True)
    var100 = models.CharField(max_length=20, null=True, blank=True)
    var111 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var112 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(PortalUsuario, on_delete=models.PROTECT, verbose_name="Usuário")
    
    class Meta:
        db_table = 'pagamentos_efetuados'
        verbose_name = 'Pagamento Efetuado'
        verbose_name_plural = 'Pagamentos Efetuados'
        indexes = [
            models.Index(fields=['nsu']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Pagamento NSU {self.nsu} - {self.created_at}"


class LancamentoManual(models.Model):
    """
    Modelo para lançamentos manuais no sistema bancário
    Tabela: lancamento_manual
    """
    
    TIPO_CHOICES = [
        ('C', 'Crédito'),
        ('D', 'Débito'),
    ]
    
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('processado', 'Processado'),
        ('cancelado', 'Cancelado'),
    ]
    
    id = models.AutoField(primary_key=True)
    id_usuario = models.IntegerField(verbose_name="ID do Usuário")
    loja_id = models.IntegerField(verbose_name="ID da Loja")
    tipo_lancamento = models.CharField(
        max_length=1,
        choices=TIPO_CHOICES,
        verbose_name="Tipo de Lançamento"
    )
    descricao = models.CharField(max_length=200, verbose_name="Descrição")
    data_lancamento = models.DateTimeField(verbose_name="Data do Lançamento")
    valor = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0.00,
        verbose_name="Valor"
    )
    motivo = models.CharField(max_length=100, null=True, blank=True, verbose_name="Motivo")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pendente',
        verbose_name="Status"
    )
    observacoes = models.TextField(null=True, blank=True, verbose_name="Observações")
    referencia_externa = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Referência Externa"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'lancamento_manual'
        indexes = [
            models.Index(fields=['loja_id'], name='idx_lancamento_loja'),
            models.Index(fields=['id_usuario'], name='idx_lancamento_usuario'),
            models.Index(fields=['data_lancamento'], name='idx_lancamento_data'),
        ]
        verbose_name = 'Lançamento Manual'
        verbose_name_plural = 'Lançamentos Manuais'
    
    def __str__(self):
        return f"{self.descricao} - Loja {self.loja_id} - R$ {self.valor}"
