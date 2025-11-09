"""
Modelos core do sistema de checkout.
Compartilhados entre link de pagamento e portal de vendas.
"""
from django.db import models
from django.core.exceptions import ValidationError

# Importar models de arquivos separados para Django registrar
from .models_recorrencia import RecorrenciaAgendada  # noqa: F401


class CheckoutCliente(models.Model):
    """Cadastro permanente de clientes para checkout"""
    
    loja = models.ForeignKey(
        'estr_organizacional.Loja',
        on_delete=models.PROTECT,
        db_column='loja_id',
        related_name='checkout_clientes'
    )
    cpf = models.CharField(max_length=11, null=True, blank=True, db_index=True)
    cnpj = models.CharField(max_length=14, null=True, blank=True, db_index=True)
    nome = models.CharField(max_length=200)
    email = models.EmailField(max_length=200)
    # celular removido - agora gerenciado por checkout_cliente_telefone (2FA)
    endereco = models.CharField(max_length=300, null=True, blank=True)
    cep = models.CharField(max_length=8, null=True, blank=True)
    
    # Auditoria
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'checkout_cliente'
        verbose_name = 'Cliente de Checkout'
        verbose_name_plural = 'Clientes de Checkout'
        # NOTA: UniqueConstraints com condition removidas pois MySQL não suporta
        # As constraints UNIQUE KEY uq_loja_cpf e uq_loja_cnpj existem no banco via SQL
        constraints = [
            models.CheckConstraint(
                check=models.Q(cpf__isnull=False) | models.Q(cnpj__isnull=False),
                name='chk_cpf_ou_cnpj'
            )
        ]
        indexes = [
            models.Index(fields=['loja', 'cpf'], name='idx_loja_cpf'),
            models.Index(fields=['loja', 'cnpj'], name='idx_loja_cnpj'),
        ]
    
    def clean(self):
        """Validação customizada"""
        if not self.cpf and not self.cnpj:
            raise ValidationError('CPF ou CNPJ é obrigatório')
        
        if self.cpf and self.cnpj:
            raise ValidationError('Informe apenas CPF ou CNPJ, não ambos')
    
    def __str__(self):
        doc = self.cpf or self.cnpj
        return f"{self.nome} - {doc}"


class CheckoutCartaoTokenizado(models.Model):
    """Cartões tokenizados (salvos) via Pinbank"""
    
    cliente = models.ForeignKey(
        CheckoutCliente,
        on_delete=models.CASCADE,
        related_name='cartoes'
    )
    cartao_mascarado = models.CharField(
        max_length=20,
        help_text="Formato: 4444########5435"
    )
    validade = models.CharField(max_length=7, help_text="Formato: MM/YYYY")
    bandeira = models.CharField(max_length=50)
    nome_cliente = models.CharField(max_length=200)
    
    # Token do Pinbank (NUNCA armazenar número completo ou CVV)
    id_token = models.CharField(max_length=200, unique=True, db_index=True)
    tokenizadora = models.CharField(max_length=20, default='PINBANK')
    
    valido = models.BooleanField(default=True, help_text="Cartão ativo/válido")
    apelido = models.CharField(max_length=50, null=True, blank=True, help_text="Ex: Cartão Principal")
    
    # Controle de falhas consecutivas
    tentativas_falhas_consecutivas = models.IntegerField(
        default=0,
        help_text="Contador de transações negadas consecutivas (reseta ao aprovar)"
    )
    ultima_falha_em = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Data/hora da última transação negada"
    )
    motivo_invalidacao = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Motivo da invalidação (ex: Múltiplas falhas, Solicitação do cliente)"
    )
    invalidado_por = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="ID do usuário que invalidou manualmente (null se automático)"
    )
    invalidado_em = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Data/hora da invalidação"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'checkout_cartao_tokenizado'
        verbose_name = 'Cartão Tokenizado'
        verbose_name_plural = 'Cartões Tokenizados'
        indexes = [
            models.Index(fields=['cliente', 'valido'], name='idx_cliente_valido'),
            models.Index(fields=['id_token'], name='idx_token'),
        ]
    
    def __str__(self):
        apelido = f" ({self.apelido})" if self.apelido else ""
        return f"{self.bandeira} {self.cartao_mascarado}{apelido}"


class CheckoutTransaction(models.Model):
    """Registro de transações do checkout (criada pelo vendedor, finalizada pelo cliente)"""
    
    # Relacionamento com sessão (apenas para link de pagamento)
    session = models.OneToOneField(
        'link_pagamento_web.CheckoutSession',
        on_delete=models.CASCADE,
        related_name='transaction',
        null=True,
        blank=True
    )
    
    # Relacionamento com cliente e cartão tokenizado (portal de vendas)
    cliente = models.ForeignKey(
        CheckoutCliente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transacoes'
    )
    cartao_tokenizado = models.ForeignKey(
        CheckoutCartaoTokenizado,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transacoes'
    )
    
    # Origem da transação
    ORIGEM_CHOICES = [
        ('CHECKOUT', 'Portal de Vendas - Link Enviado'),
        ('LINK', 'Integração Direta API'),
        ('RECORRENCIA', 'Recorrência Agendada'),
    ]
    origem = models.CharField(max_length=20, choices=ORIGEM_CHOICES, default='CHECKOUT')
    
    # Vínculo com recorrência (se esta transação foi gerada por uma recorrência)
    checkout_recorrencia = models.ForeignKey(
        'checkout.RecorrenciaAgendada',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transacoes_executadas',
        db_column='checkout_recorrencia_id',
        db_index=True,
        help_text="Recorrência que gerou esta transação (null se não for recorrente)"
    )
    
    # Relacionamento com loja
    loja = models.ForeignKey(
        'estr_organizacional.Loja',
        on_delete=models.PROTECT,
        db_column='loja_id',
        null=False,
        blank=False,
        related_name='checkout_transactions'
    )
    
    # Token do link de pagamento (relaciona com CheckoutToken)
    token = models.CharField(max_length=100, unique=True, null=True, blank=True, db_index=True, help_text="Token do link de pagamento")
    
    # Dados da transação
    nsu = models.CharField(max_length=50, unique=True, db_index=True, null=True, blank=True, help_text="NSU retornado pelo Pinbank")
    codigo_autorizacao = models.CharField(max_length=50, null=True, blank=True, help_text="Código de autorização do Pinbank")
    valor_transacao_original = models.DecimalField(max_digits=10, decimal_places=2, help_text="Valor definido pelo vendedor")
    valor_transacao_final = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Valor final cobrado (após escolha do cliente)")
    
    # Status da transação
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente - Aguardando Cliente'),
        ('APROVADA', 'Aprovada'),
        ('NEGADA', 'Negada'),
        ('ERRO', 'Erro no processamento'),
        ('CANCELADA', 'Cancelada'),
        ('BLOQUEADA_ANTIFRAUDE', 'Bloqueada pelo Antifraude'),
        ('PENDENTE_REVISAO', 'Pendente de Revisão Manual'),
    ]
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='PENDENTE', db_index=True)
    
    # Dados do pagamento
    forma_pagamento = models.CharField(max_length=50, null=True, blank=True, help_text="Tipo de pagamento usado")
    parcelas = models.IntegerField(null=True, blank=True, help_text="Número de parcelas (NULL quando cliente ainda não escolheu)")
    
    # ID do pedido no sistema da loja (opcional)
    pedido_origem_loja = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    
    # Código do item no sistema da loja (opcional)
    cod_item_origem_loja = models.CharField(max_length=100, null=True, blank=True, help_text="Código/SKU do produto")
    
    # Vendedor que criou a transação (portais_usuarios renomeado)
    vendedor_id = models.BigIntegerField(null=True, blank=True, db_index=True, db_column='vendedor_id', help_text="ID do vendedor que criou (ex-portais_usuarios_id)")
    
    # Dados da API Pinbank
    pinbank_response = models.JSONField(null=True, blank=True, help_text="Resposta completa do Pinbank")
    erro_pinbank = models.TextField(null=True, blank=True, help_text="Mensagem de erro se houver")
    
    # Dados do Antifraude (Risk Engine)
    score_risco = models.IntegerField(null=True, blank=True, db_index=True, help_text="Score de risco 0-100")
    decisao_antifraude = models.CharField(max_length=20, null=True, blank=True, db_index=True, help_text="APROVADO, REPROVADO, REVISAR")
    motivo_bloqueio = models.TextField(null=True, blank=True, help_text="Motivo do bloqueio/revisão")
    antifraude_response = models.JSONField(null=True, blank=True, help_text="Resposta completa do Risk Engine")
    revisado_por = models.BigIntegerField(null=True, blank=True, help_text="ID do analista que revisou")
    revisado_em = models.DateTimeField(null=True, blank=True, help_text="Quando foi revisado")
    observacao_revisao = models.TextField(null=True, blank=True, help_text="Observação da revisão manual")
    
    # Auditoria do cliente (preenchido apenas quando cliente processa)
    ip_address_cliente = models.GenericIPAddressField(null=True, blank=True, help_text="IP do cliente ao processar")
    user_agent_cliente = models.TextField(null=True, blank=True, help_text="User agent do cliente")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, help_text="Quando vendedor criou")
    updated_at = models.DateTimeField(auto_now=True, help_text="Última atualização")
    processed_at = models.DateTimeField(null=True, blank=True, db_index=True, help_text="Quando cliente processou")
    
    class Meta:
        db_table = 'checkout_transactions'
        verbose_name = 'Transação de Checkout'
        verbose_name_plural = 'Transações de Checkout'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['loja', 'status']),
            models.Index(fields=['vendedor_id', 'created_at']),
            models.Index(fields=['checkout_recorrencia', 'created_at']),
        ]
    
    def clean(self):
        """Validações customizadas"""
        # Validar consistência em transações de recorrência
        if self.origem == 'RECORRENCIA':
            if not self.checkout_recorrencia:
                raise ValidationError('Recorrência obrigatória para origem=RECORRENCIA')
            
            # Validar consistência de cliente
            if self.cliente and self.checkout_recorrencia.cliente:
                if self.cliente.id != self.checkout_recorrencia.cliente.id:
                    raise ValidationError(
                        f'Cliente inconsistente: transação tem cliente_id={self.cliente.id}, '
                        f'mas recorrência tem cliente_id={self.checkout_recorrencia.cliente.id}'
                    )
            
            # Validar consistência de cartão
            if self.cartao_tokenizado and self.checkout_recorrencia.cartao_tokenizado:
                if self.cartao_tokenizado.id != self.checkout_recorrencia.cartao_tokenizado.id:
                    raise ValidationError(
                        f'Cartão inconsistente: transação tem cartao_id={self.cartao_tokenizado.id}, '
                        f'mas recorrência tem cartao_id={self.checkout_recorrencia.cartao_tokenizado.id}'
                    )
    
    @property
    def valor_transacao(self):
        """Propriedade para compatibilidade: retorna valor final se existir, senão original"""
        return self.valor_transacao_final if self.valor_transacao_final else self.valor_transacao_original
    
    @property
    def nome_cliente(self):
        """Retorna nome do cliente (session ou cliente)"""
        if self.session:
            return self.session.nome
        elif self.cliente:
            return self.cliente.nome
        return 'N/A'
    
    @property
    def cpf_cliente(self):
        """Retorna CPF do cliente (session ou cliente)"""
        if self.session:
            return self.session.cpf
        elif self.cliente:
            return self.cliente.cpf
        return 'N/A'
    
    def __str__(self):
        if self.nsu:
            return f"NSU {self.nsu} - {self.status}"
        return f"ID {self.id} - {self.status} ({self.origem})"


class CheckoutTransactionAttempt(models.Model):
    """Registro de tentativas frustradas de pagamento"""
    
    # Relacionamento com transação principal
    transaction = models.ForeignKey(
        CheckoutTransaction,
        on_delete=models.CASCADE,
        related_name='attempts'
    )
    
    # Número da tentativa
    tentativa_numero = models.IntegerField(help_text="Número da tentativa (1, 2, 3...)")
    
    # Dados do erro
    erro_pinbank = models.TextField(null=True, blank=True, help_text="Mensagem de erro do Pinbank")
    pinbank_response = models.JSONField(null=True, blank=True, help_text="Resposta completa da API Pinbank")
    
    # Dados do cliente nesta tentativa
    ip_address_cliente = models.GenericIPAddressField(help_text="IP do cliente nesta tentativa")
    user_agent_cliente = models.TextField(help_text="User agent do cliente")
    
    # Hash do cartão para auditoria
    numero_cartao_hash = models.CharField(max_length=64, null=True, blank=True, help_text="Hash SHA256 dos últimos 4 dígitos")
    
    # Timestamp
    attempted_at = models.DateTimeField(auto_now_add=True, db_index=True, help_text="Data/hora da tentativa")
    
    class Meta:
        db_table = 'checkout_transaction_attempts'
        verbose_name = 'Tentativa de Pagamento'
        verbose_name_plural = 'Tentativas de Pagamento'
        ordering = ['transaction', 'tentativa_numero']
        indexes = [
            models.Index(fields=['transaction', 'attempted_at']),
        ]
    
    def __str__(self):
        return f"Tentativa {self.tentativa_numero} - Transaction {self.transaction_id}"
