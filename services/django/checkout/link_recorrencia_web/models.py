"""
Models para tokenização de cartão para recorrência.
Fluxo: Cliente recebe link → Cadastra cartão → Sistema tokeniza e ativa recorrência
"""
import secrets
from django.db import models
from datetime import timedelta


class RecorrenciaToken(models.Model):
    """
    Token temporário para cadastro de cartão em recorrência.
    Diferente do CheckoutToken: não processa pagamento, apenas tokeniza cartão.
    """
    token = models.CharField(max_length=64, unique=True, db_index=True)
    
    # Relacionamentos
    recorrencia = models.ForeignKey(
        'checkout.RecorrenciaAgendada',
        on_delete=models.CASCADE,
        related_name='tokens'
    )
    
    loja_id = models.IntegerField()
    
    # Dados do cliente (para preencher no checkout)
    cliente_nome = models.CharField(max_length=200)
    cliente_cpf = models.CharField(max_length=11, db_index=True)
    cliente_email = models.CharField(max_length=200)
    
    # Descrição da recorrência
    descricao_recorrencia = models.CharField(max_length=255)
    valor_recorrencia = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Controle
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'checkout_recorrencia_tokens'
        verbose_name = 'Token de Recorrência'
        verbose_name_plural = 'Tokens de Recorrência'
    
    @classmethod
    def generate_token(cls, recorrencia, loja_id, cliente_nome, cliente_cpf, cliente_email, descricao, valor):
        """Gera token seguro para cadastro de cartão em recorrência"""
        token = secrets.token_urlsafe(48)
        from datetime import datetime
        expires_at = datetime.now() + timedelta(hours=72)  # 72h para cadastrar cartão
        
        return cls.objects.create(
            token=token,
            recorrencia=recorrencia,
            loja_id=loja_id,
            cliente_nome=cliente_nome,
            cliente_cpf=cliente_cpf,
            cliente_email=cliente_email,
            descricao_recorrencia=descricao,
            valor_recorrencia=valor,
            expires_at=expires_at
        )
    
    def is_valid(self):
        """Verifica se token ainda é válido"""
        from datetime import datetime
        return not self.used and datetime.now() < self.expires_at
    
    def mark_as_used(self):
        """Marca token como utilizado após cartão tokenizado"""
        from datetime import datetime
        self.used = True
        self.used_at = datetime.now()
        self.save()
    
    def __str__(self):
        return f"Token Recorrência {self.token[:8]}... - {self.cliente_nome}"
