"""
Modelos para o sistema de checkout com link de pagamento.
"""
import secrets
from django.db import models
from django.utils import timezone
from datetime import timedelta


class CheckoutToken(models.Model):
    """Token temporário para acesso ao checkout"""
    token = models.CharField(max_length=64, unique=True, db_index=True)
    loja_id = models.IntegerField()
    item_nome = models.CharField(max_length=200)
    item_valor = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Dados do cliente
    nome_completo = models.CharField(max_length=200)
    cpf = models.CharField(max_length=11, db_index=True)
    celular = models.CharField(max_length=15)
    endereco_completo = models.TextField()
    
    # ID do pedido no sistema da loja (opcional)
    pedido_origem_loja = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    tentativas_pagamento = models.IntegerField(default=0, help_text="Número de tentativas de pagamento")
    created_by = models.CharField(max_length=100)  # Sistema que gerou
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'checkout_tokens'
        verbose_name = 'Token de Checkout'
        verbose_name_plural = 'Tokens de Checkout'
    
    @classmethod
    def generate_token(cls, loja_id, item_nome, item_valor, nome_completo, cpf, celular, endereco_completo, created_by, pedido_origem_loja=None):
        """Gera um token seguro para checkout"""
        token = secrets.token_urlsafe(48)  # 64 chars URL-safe
        from django.utils import timezone
        expires_at = timezone.now() + timedelta(minutes=30)  # 30 minutos para permitir múltiplas tentativas
        
        return cls.objects.create(
            token=token,
            loja_id=loja_id,
            item_nome=item_nome,
            item_valor=item_valor,
            nome_completo=nome_completo,
            cpf=cpf,
            celular=celular,
            endereco_completo=endereco_completo,
            pedido_origem_loja=pedido_origem_loja,
            expires_at=expires_at,
            created_by=created_by
        )
    
    def is_valid(self):
        """Verifica se o token ainda é válido"""
        from django.utils import timezone
        # Token válido se: não usado, não expirado e menos de 3 tentativas
        return not self.used and timezone.now() < self.expires_at and self.tentativas_pagamento < 3
    
    def incrementar_tentativa(self):
        """Incrementa contador de tentativas"""
        from django.utils import timezone
        self.tentativas_pagamento += 1
        if self.tentativas_pagamento >= 3:
            # Marcar como usado após 3 tentativas
            self.used = True
            self.used_at = timezone.now()
        self.save()
    
    def mark_as_used(self):
        """Marca token como utilizado (após transação aprovada)"""
        from django.utils import timezone
        self.used = True
        self.used_at = timezone.now()
        self.save()
    
    def __str__(self):
        return f"Token {self.token[:8]}... - {self.item_nome}"


class CheckoutSession(models.Model):
    """Sessão de checkout com dados temporários"""
    token = models.OneToOneField(CheckoutToken, on_delete=models.CASCADE)
    cpf = models.CharField(max_length=11)
    nome = models.CharField(max_length=200)
    celular = models.CharField(max_length=15)
    endereco = models.TextField()
    whatsapp_code = models.CharField(max_length=6, null=True, blank=True)
    whatsapp_expires_at = models.DateTimeField(null=True, blank=True)
    whatsapp_verified = models.BooleanField(default=False)
    
    # Dados do cartão (temporários, não persistidos após processamento)
    numero_cartao_hash = models.CharField(max_length=64, null=True, blank=True)  # Hash para auditoria
    data_validade = models.CharField(max_length=7, null=True, blank=True)  # MM/YYYY
    parcelas = models.IntegerField(default=1)
    tipo_pagamento = models.CharField(max_length=50, default='CREDIT_ONE_INSTALLMENT')
    
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'checkout_sessions'
        verbose_name = 'Sessão de Checkout'
        verbose_name_plural = 'Sessões de Checkout'
    
    def generate_whatsapp_code(self):
        """Gera código de confirmação via WhatsApp"""
        code = f"{secrets.randbelow(900000) + 100000:06d}"  # 6 dígitos
        self.whatsapp_code = code
        from datetime import datetime
        self.whatsapp_expires_at = datetime.now() + timedelta(minutes=5)
        self.whatsapp_verified = False
        self.save()
        return code
    
    def verify_whatsapp_code(self, code):
        """Verifica código do WhatsApp"""
        if not self.whatsapp_code or not self.whatsapp_expires_at:
            return False
        
        from datetime import datetime
        if datetime.now() > self.whatsapp_expires_at:
            return False
        
        if self.whatsapp_code == code:
            self.whatsapp_verified = True
            self.save()
            return True
        
        return False
    
    def __str__(self):
        return f"Sessão {self.cpf} - {self.token.item_nome}"


class CheckoutAttempt(models.Model):
    """Log de tentativas de acesso para auditoria"""
    token = models.CharField(max_length=64, db_index=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    success = models.BooleanField()
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'checkout_attempts'
        verbose_name = 'Tentativa de Checkout'
        verbose_name_plural = 'Tentativas de Checkout'


# CheckoutTransaction movido para checkout/models.py (core compartilhado)
# Importar de lá se necessário: from checkout.models import CheckoutTransaction

# Modelo CheckoutAPIKey removido - migrado para comum.autenticacao.models.APIKey
