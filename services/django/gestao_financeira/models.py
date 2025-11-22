from django.db import models
from django.contrib.auth.models import User


class BaseTransacoesGestao(models.Model):
    """Modelo para base de transações de gestão - Estrutura exata da tabela MySQL"""
    
    class Meta:
        app_label = 'gestao_financeira'
        db_table = 'baseTransacoesGestao'
        verbose_name = 'Base Transação Gestão'
        verbose_name_plural = 'Base Transações Gestão'
    
    # Campos principais
    id = models.BigAutoField(primary_key=True)
    idFilaExtrato = models.PositiveIntegerField(null=True, blank=True)
    banco = models.CharField(max_length=10, null=True, blank=True)
    tipo_operacao = models.CharField(
        max_length=20,
        choices=[('Credenciadora', 'Credenciadora'), ('Wallet', 'Wallet')],
        null=True,
        blank=True
    )
    adquirente = models.CharField(
        max_length=20,
        choices=[('PINBANK', 'Pinbank'), ('OWN', 'Own Financial')],
        default='PINBANK',
        db_index=True
    )
    data_transacao = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # Variáveis string (var0-var12, var43, var45, etc.)
    var0 = models.CharField(max_length=10, null=True, blank=True)
    var1 = models.CharField(max_length=8, null=True, blank=True)
    var2 = models.CharField(max_length=20, null=True, blank=True)
    var3 = models.CharField(max_length=20, null=True, blank=True)
    var4 = models.CharField(max_length=10, null=True, blank=True)
    var5 = models.TextField(null=True, blank=True)
    var6 = models.CharField(max_length=3, null=True, blank=True)
    var7 = models.CharField(max_length=20, null=True, blank=True, db_index=True)
    var8 = models.CharField(max_length=20, null=True, blank=True)
    var9 = models.CharField(max_length=20, null=True, blank=True, db_index=True)
    var10 = models.CharField(max_length=20, null=True, blank=True)
    var11 = models.CharField(max_length=20, null=True, blank=True)
    var12 = models.CharField(max_length=20, null=True, blank=True)
    
    # Variáveis decimais (var13-var42)
    var13 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var14 = models.DecimalField(max_digits=12, decimal_places=10, null=True, blank=True)  # Percentual
    var15 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var16 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var17 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var18 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var19 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var20 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var21 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var22 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var23 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var24 = models.DecimalField(max_digits=12, decimal_places=10, null=True, blank=True)  # Percentual
    var25 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var26 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var27 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var28 = models.DecimalField(max_digits=12, decimal_places=10, null=True, blank=True)  # Percentual
    var29 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var30 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var31 = models.DecimalField(max_digits=12, decimal_places=10, null=True, blank=True)  # Percentual
    var32 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var33 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var34 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var35 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var36 = models.DecimalField(max_digits=12, decimal_places=10, null=True, blank=True)  # Percentual
    var37 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var38 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var39 = models.DecimalField(max_digits=12, decimal_places=10, null=True, blank=True)  # Percentual
    var40 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var41 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var42 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    
    # Variáveis mistas (var43-var130)
    var43 = models.CharField(max_length=20, null=True, blank=True)
    var44 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var45 = models.CharField(max_length=20, null=True, blank=True)
    var46 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var47 = models.DecimalField(max_digits=12, decimal_places=10, null=True, blank=True)  # Percentual
    var48 = models.DecimalField(max_digits=12, decimal_places=10, null=True, blank=True)  # Percentual
    var49 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var50 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var51 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var52 = models.DecimalField(max_digits=12, decimal_places=10, null=True, blank=True)  # Percentual
    var53 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var54 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var55 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var56 = models.DecimalField(max_digits=12, decimal_places=10, null=True, blank=True)  # Percentual
    var57 = models.CharField(max_length=20, null=True, blank=True)
    var58 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var59 = models.CharField(max_length=20, null=True, blank=True)
    var60 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var60_A = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    var61 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var61_A = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    var62 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var63 = models.DecimalField(max_digits=12, decimal_places=10, null=True, blank=True)  # Percentual
    var64 = models.DecimalField(max_digits=12, decimal_places=10, null=True, blank=True)  # Percentual
    var65 = models.CharField(max_length=20, null=True, blank=True)
    var66 = models.CharField(max_length=20, null=True, blank=True)
    var67 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var68 = models.CharField(max_length=256, null=True, blank=True)
    var69 = models.CharField(max_length=256, null=True, blank=True)
    var70 = models.CharField(max_length=100, null=True, blank=True)
    var71 = models.CharField(max_length=20, null=True, blank=True)
    var72 = models.DecimalField(max_digits=12, decimal_places=10, null=True, blank=True)  # Percentual
    var73 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var74 = models.DecimalField(max_digits=12, decimal_places=10, null=True, blank=True)  # Percentual
    var75 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var76 = models.DecimalField(max_digits=12, decimal_places=10, null=True, blank=True)  # Percentual
    var77 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var78 = models.DecimalField(max_digits=12, decimal_places=10, null=True, blank=True)  # Percentual
    var79 = models.DecimalField(max_digits=12, decimal_places=10, null=True, blank=True)  # Percentual
    var80 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var81 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var82 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var83 = models.DecimalField(max_digits=12, decimal_places=10, null=True, blank=True)  # Percentual
    var84 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var85 = models.DecimalField(max_digits=12, decimal_places=10, null=True, blank=True)  # Percentual
    var86 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var87 = models.DecimalField(max_digits=12, decimal_places=10, null=True, blank=True)  # Percentual
    var88 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var89 = models.DecimalField(max_digits=12, decimal_places=10, null=True, blank=True)  # Percentual
    var90 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var91 = models.DecimalField(max_digits=12, decimal_places=10, null=True, blank=True)  # Percentual
    var92 = models.DecimalField(max_digits=12, decimal_places=10, null=True, blank=True)  # Percentual
    var93 = models.DecimalField(max_digits=12, decimal_places=10, null=True, blank=True)  # Percentual
    var93_A = models.DecimalField(max_digits=12, decimal_places=10, null=True, blank=True)  # Percentual
    var94 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var94_A = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var94_B = models.CharField(max_length=30, null=True, blank=True)
    var95 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var96 = models.CharField(max_length=20, null=True, blank=True)
    var97 = models.CharField(max_length=50, null=True, blank=True)
    var98 = models.CharField(max_length=30, null=True, blank=True)
    var99 = models.CharField(max_length=30, null=True, blank=True)
    var100 = models.CharField(max_length=20, null=True, blank=True)
    var101 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var102 = models.CharField(max_length=30, null=True, blank=True)
    var103 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var103_A = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var104 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var105 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var106 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var107 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var107_A = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var108 = models.DecimalField(max_digits=12, decimal_places=10, null=True, blank=True)  # Percentual
    var109 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var109_A = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var110 = models.DecimalField(max_digits=12, decimal_places=10, null=True, blank=True)  # Percentual
    var111 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var111_A = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var111_B = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var112 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var112_A = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var112_B = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var113 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var113_A = models.CharField(max_length=30, null=True, blank=True)
    var114 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var114_A = models.CharField(max_length=30, null=True, blank=True)
    var115 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var115_A = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var116 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var116_A = models.CharField(max_length=30, null=True, blank=True)
    var117 = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    var117_A = models.CharField(max_length=30, null=True, blank=True)
    var118 = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    var118_A = models.CharField(max_length=30, null=True, blank=True)
    var119 = models.TextField(null=True, blank=True)
    var120 = models.CharField(max_length=20, null=True, blank=True)
    var121 = models.CharField(max_length=20, null=True, blank=True)
    var122 = models.CharField(max_length=20, null=True, blank=True)
    var123 = models.CharField(max_length=20, null=True, blank=True)
    var124 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var125 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var126 = models.CharField(max_length=30, null=True, blank=True)
    var127 = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    var128 = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    var129 = models.CharField(max_length=20, null=True, blank=True)
    var130 = models.CharField(max_length=20, null=True, blank=True)
    
    # Campos de controle
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"ID {self.idFilaExtrato} - NSU {self.var9}"


class BaseTransacoesGestaoErroCarga(models.Model):
    """Modelo para erros na carga de transações"""
    
    log_id = models.AutoField(primary_key=True)
    log_data = models.DateTimeField(auto_now_add=True)
    idFilaExtrato = models.PositiveIntegerField()
    mensagem = models.CharField(max_length=256, null=True, blank=True)

    class Meta:
        app_label = 'gestao_financeira'
        db_table = 'baseTransacoesGestaoErroCarga'
        verbose_name = 'Erro Carga Transação'
        verbose_name_plural = 'Erros Carga Transações'

    def __str__(self):
        return f"Erro ID {self.idFilaExtrato} - {self.log_data}"


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
    user_id = models.IntegerField(null=True, blank=True, verbose_name="ID do Usuário", help_text="FK manual para controle_acesso.PortalUsuario")
    
    class Meta:
        app_label = 'gestao_financeira'
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
        app_label = 'gestao_financeira'
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
