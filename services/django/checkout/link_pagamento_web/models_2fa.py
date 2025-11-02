"""
Models para 2FA no Checkout Web
Cliente autogerencia telefone e histórico de transações
"""
from django.db import models
from datetime import datetime, timedelta


class CheckoutClienteTelefone(models.Model):
    """
    Telefone autogerenciado pelo cliente.
    Imutável após primeira transação aprovada.
    """
    
    STATUS_CHOICES = [
        (-1, 'Pendente'),      # Aguardando primeira confirmação 2FA
        (0, 'Desabilitado'),   # Cliente desabilitou
        (1, 'Ativo'),          # Confirmado após 2FA
    ]
    
    cpf = models.CharField(max_length=11, db_index=True, help_text="CPF do cliente")
    telefone = models.CharField(max_length=15, db_index=True, help_text="Telefone com DDD")
    ativo = models.IntegerField(
        default=-1, 
        db_index=True, 
        choices=STATUS_CHOICES,
        help_text="Status: -1=Pendente, 0=Desabilitado, 1=Ativo"
    )
    
    # Primeira transação aprovada torna telefone imutável
    primeira_transacao_aprovada_em = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Quando primeira transação foi aprovada (torna telefone imutável)"
    )
    
    # Mudança de telefone (requer OTP no antigo + novo)
    telefone_anterior = models.CharField(
        max_length=15, 
        null=True, 
        blank=True,
        help_text="Telefone anterior antes da mudança"
    )
    mudado_em = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Quando telefone foi alterado"
    )
    
    # Auditoria
    criado_em = models.DateTimeField(auto_now_add=True, db_index=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'checkout_cliente_telefone'
        verbose_name = 'Telefone Cliente Checkout'
        verbose_name_plural = 'Telefones Cliente Checkout'
        unique_together = [['cpf', 'telefone']]
        indexes = [
            models.Index(fields=['cpf', 'ativo']),
            models.Index(fields=['telefone', 'ativo']),
        ]
    
    def __str__(self):
        status_map = {
            -1: "⏳ PENDENTE",
            0: "🔴 DESABILITADO",
            1: "✅ ATIVO"
        }
        status = status_map.get(self.ativo, "❓ DESCONHECIDO")
        imutavel = " 🔒 IMUTÁVEL" if self.primeira_transacao_aprovada_em else ""
        return f"{status}{imutavel} - CPF {self.cpf[:3]}***{self.cpf[-2:]} - Tel {self.telefone[-4:]}"
    
    def pode_alterar_telefone(self) -> bool:
        """Verifica se telefone pode ser alterado"""
        # Se nunca teve transação aprovada, pode alterar livremente
        if not self.primeira_transacao_aprovada_em:
            return True
        
        # Se já teve transação aprovada, telefone é imutável
        # Apenas processo especial de mudança (OTP duplo) permite
        return False
    
    def ativar_apos_2fa(self):
        """Ativa telefone após confirmação 2FA (muda de -1 para 1)"""
        if self.ativo == -1:  # Se estava pendente
            self.ativo = 1
            self.save(update_fields=['ativo', 'atualizado_em'])
    
    def marcar_primeira_transacao_aprovada(self):
        """Marca que primeira transação foi aprovada (torna telefone imutável)"""
        if not self.primeira_transacao_aprovada_em:
            self.primeira_transacao_aprovada_em = datetime.now()
            self.ativo = 1  # Garante que está ativo
            self.save(update_fields=['primeira_transacao_aprovada_em', 'ativo', 'atualizado_em'])
            
            # CRÍTICO: Inativar todos os outros telefones deste CPF
            CheckoutClienteTelefone.objects.filter(
                cpf=self.cpf
            ).exclude(
                id=self.id  # Exceto este telefone
            ).update(
                ativo=0,  # Inativar
                atualizado_em=datetime.now()
            )
    
    @classmethod
    def obter_ou_criar_telefone(cls, cpf: str, telefone: str):
        """
        Obtém telefone existente ou cria novo
        
        Args:
            cpf: CPF do cliente (11 dígitos)
            telefone: Telefone com DDD
            
        Returns:
            tuple: (CheckoutClienteTelefone, created: bool)
        """
        cpf_limpo = ''.join(filter(str.isdigit, cpf))
        telefone_limpo = ''.join(filter(str.isdigit, telefone))
        
        return cls.objects.get_or_create(
            cpf=cpf_limpo,
            telefone=telefone_limpo,
            defaults={
                'ativo': -1  # Pendente até primeira confirmação 2FA
            }
        )


# CheckoutTransacaoHistorico REMOVIDO - usar checkout.models.CheckoutTransaction
# Métodos auxiliares abaixo

class CheckoutTransactionHelper:
    """
    Helper para consultas em CheckoutTransaction relacionadas a 2FA
    Usa tabela checkout_transactions existente
    """
    
    @staticmethod
    def contar_transacoes_aprovadas(cpf: str) -> int:
        """
        Conta quantas transações aprovadas o CPF tem
        
        Args:
            cpf: CPF do cliente
            
        Returns:
            int: Número de transações aprovadas
        """
        from checkout.models import CheckoutTransaction
        
        cpf_limpo = ''.join(filter(str.isdigit, cpf))
        
        # Buscar por cliente_id que tem o CPF
        from checkout.models import CheckoutCliente
        
        try:
            cliente = CheckoutCliente.objects.get(cpf=cpf_limpo)
            return CheckoutTransaction.objects.filter(
                cliente_id=cliente.id,
                status__in=['APROVADA', 'APPROVED']
            ).count()
        except CheckoutCliente.DoesNotExist:
            return 0
    
    @staticmethod
    def calcular_limite_progressivo(cpf: str) -> float:
        """
        Calcula limite progressivo baseado no histórico
        
        Regras:
        - 0 transações aprovadas: R$ 100
        - 1 transação aprovada: R$ 200
        - 2 transações aprovadas: R$ 500
        - 3+ transações aprovadas: sem limite
        
        Args:
            cpf: CPF do cliente
            
        Returns:
            float: Limite em reais (0 = sem limite)
        """
        transacoes_aprovadas = CheckoutTransactionHelper.contar_transacoes_aprovadas(cpf)
        
        if transacoes_aprovadas == 0:
            return 100.00
        elif transacoes_aprovadas == 1:
            return 200.00
        elif transacoes_aprovadas == 2:
            return 500.00
        else:
            return 0.00  # Sem limite
    
    @staticmethod
    def verificar_multiplos_cartoes(telefone: str, dias: int = 1) -> int:
        """
        Verifica se telefone foi usado com múltiplos cartões diferentes
        
        Args:
            telefone: Telefone do cliente
            dias: Período em dias para verificar
            
        Returns:
            int: Número de cartões diferentes
        """
        from checkout.models import CheckoutTransaction, CheckoutCliente
        from datetime import datetime, timedelta
        
        telefone_limpo = ''.join(filter(str.isdigit, telefone))
        data_limite = datetime.now() - timedelta(days=dias)
        
        # Buscar CPFs que usam este telefone
        cpfs_com_telefone = list(CheckoutClienteTelefone.objects.filter(
            telefone=telefone_limpo,
            ativo=True
        ).values_list('cpf', flat=True))
        
        if not cpfs_com_telefone:
            return 0
        
        # Buscar clientes com esses CPFs (converter para list evita erro de collation)
        clientes = CheckoutCliente.objects.filter(cpf__in=cpfs_com_telefone)
        
        if not clientes.exists():
            return 0
        
        # Buscar cartões diferentes usados por estes clientes
        cartoes_diferentes = CheckoutTransaction.objects.filter(
            cliente_id__in=clientes.values_list('id', flat=True),
            created_at__gte=data_limite
        ).values_list('cartao_tokenizado_id', flat=True).distinct()
        
        return len([c for c in cartoes_diferentes if c is not None])


class CheckoutRateLimitControl(models.Model):
    """
    Controle de rate limiting específico do checkout
    Complementa o rate limiting do Redis com persistência
    """
    
    TIPO_CHOICES = [
        ('TELEFONE', 'Por Telefone'),
        ('CPF', 'Por CPF'),
        ('IP', 'Por IP'),
    ]
    
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, db_index=True)
    identificador = models.CharField(max_length=50, db_index=True, help_text="Telefone, CPF ou IP")
    tentativas = models.IntegerField(default=0, help_text="Número de tentativas")
    bloqueado_ate = models.DateTimeField(null=True, blank=True, help_text="Até quando está bloqueado")
    
    # Auditoria
    primeira_tentativa = models.DateTimeField(auto_now_add=True)
    ultima_tentativa = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'checkout_rate_limit'
        verbose_name = 'Rate Limit Checkout'
        verbose_name_plural = 'Rate Limits Checkout'
        unique_together = [['tipo', 'identificador']]
        indexes = [
            models.Index(fields=['tipo', 'identificador', 'bloqueado_ate']),
        ]
    
    def __str__(self):
        bloqueado = f" 🔴 BLOQUEADO até {self.bloqueado_ate.strftime('%d/%m %H:%M')}" if self.esta_bloqueado() else ""
        return f"{self.tipo} {self.identificador[-4:]} - {self.tentativas} tentativas{bloqueado}"
    
    def esta_bloqueado(self) -> bool:
        """Verifica se está bloqueado"""
        if not self.bloqueado_ate:
            return False
        return datetime.now() < self.bloqueado_ate
    
    @classmethod
    def verificar_e_incrementar(cls, tipo: str, identificador: str, limite: int = 3) -> tuple:
        """
        Verifica rate limit e incrementa contador
        
        Args:
            tipo: TELEFONE, CPF ou IP
            identificador: Valor do identificador
            limite: Limite de tentativas
            
        Returns:
            tuple: (bloqueado: bool, tentativas_restantes: int)
        """
        obj, created = cls.objects.get_or_create(
            tipo=tipo,
            identificador=identificador,
            defaults={'tentativas': 0}
        )
        
        # Se bloqueado, retorna
        if obj.esta_bloqueado():
            return True, 0
        
        # Se janela de 24h passou, reseta
        if (datetime.now() - obj.primeira_tentativa).total_seconds() > 86400:
            obj.tentativas = 0
            obj.bloqueado_ate = None
            obj.primeira_tentativa = datetime.now()
        
        # Incrementa
        obj.tentativas += 1
        
        # Se atingiu limite, bloqueia por 1h
        if obj.tentativas >= limite:
            obj.bloqueado_ate = datetime.now() + timedelta(hours=1)
            obj.save()
            return True, 0
        
        obj.save()
        tentativas_restantes = limite - obj.tentativas
        return False, tentativas_restantes
