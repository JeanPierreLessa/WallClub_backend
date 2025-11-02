"""
Serializers para o sistema de checkout.
"""
import re
from rest_framework import serializers
from decimal import Decimal
from .models import CheckoutToken, CheckoutSession


class GerarTokenSerializer(serializers.Serializer):
    """Serializer para geração de token de checkout"""
    loja_id = serializers.IntegerField(min_value=1)
    item_nome = serializers.CharField(max_length=200)
    item_valor = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))
    
    # Dados do cliente
    nome_completo = serializers.CharField(max_length=200)
    cpf = serializers.CharField(max_length=11)
    celular = serializers.CharField(max_length=15)
    endereco_completo = serializers.CharField()
    
    # ID do pedido no sistema da loja (opcional)
    pedido_origem_loja = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True)
    
    def validate_item_nome(self, value):
        """Validar nome do item"""
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError("Nome do item deve ter pelo menos 3 caracteres")
        return value.strip()
    
    def validate_item_valor(self, value):
        """Validar valor do item"""
        if value <= 0:
            raise serializers.ValidationError("Valor deve ser maior que zero")
        if value > Decimal('999999.99'):
            raise serializers.ValidationError("Valor muito alto")
        return value
    
    def validate_cpf(self, value):
        """Validar CPF"""
        cpf = re.sub(r'\D', '', value)
        if len(cpf) != 11:
            raise serializers.ValidationError("CPF deve ter 11 dígitos")
        if cpf == cpf[0] * 11:
            raise serializers.ValidationError("CPF inválido")
        return cpf
    
    def validate_nome_completo(self, value):
        """Validar nome completo"""
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError("Nome deve ter pelo menos 3 caracteres")
        if not re.match(r'^[a-zA-ZÀ-ÿ\s]+$', value.strip()):
            raise serializers.ValidationError("Nome deve conter apenas letras")
        return value.strip().title()
    
    def validate_celular(self, value):
        """Validar celular"""
        celular = re.sub(r'\D', '', value)
        if len(celular) < 10 or len(celular) > 11:
            raise serializers.ValidationError("Celular deve ter 10 ou 11 dígitos")
        return celular
    
    def validate_endereco_completo(self, value):
        """Validar endereço completo"""
        if not value or len(value.strip()) < 10:
            raise serializers.ValidationError("Endereço deve ter pelo menos 10 caracteres")
        return value.strip()


class ProcessarCheckoutSerializer(serializers.Serializer):
    """Serializer para processar dados do checkout"""
    token = serializers.CharField(max_length=64)
    loja_id = serializers.IntegerField(min_value=1)
    cpf = serializers.CharField(max_length=11)
    nome = serializers.CharField(max_length=200)
    celular = serializers.CharField(max_length=15)
    endereco = serializers.CharField()
    
    # Dados do cartão (não salvos, apenas validados)
    numero_cartao = serializers.CharField(max_length=19)
    cvv = serializers.CharField(max_length=4)
    data_validade = serializers.CharField(max_length=7)  # MM/YYYY
    bandeira = serializers.ChoiceField(
        choices=[
            ('MASTERCARD', 'Mastercard'),
            ('VISA', 'Visa'),
            ('ELO', 'Elo')
        ]
    )
    parcelas = serializers.IntegerField(min_value=1, max_value=12)
    valor_total = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)  # Valor total com desconto do pulldown
    tipo_pagamento = serializers.ChoiceField(
        choices=[
            ('CREDIT_ONE_INSTALLMENT', 'Crédito à Vista'),
            ('CREDIT_IN_INSTALLMENTS_WITHOUT_INTEREST', 'Crédito Parcelado')
        ],
        default='CREDIT_ONE_INSTALLMENT'
    )
    
    # Opção para salvar cartão (opcional)
    salvar_cartao = serializers.BooleanField(required=False, default=False)
    
    def validate_cpf(self, value):
        """Validar CPF"""
        # Remove caracteres não numéricos
        cpf = re.sub(r'\D', '', value)
        
        if len(cpf) != 11:
            raise serializers.ValidationError("CPF deve ter 11 dígitos")
        
        # Validação básica de CPF
        if cpf == cpf[0] * 11:  # CPF com todos os dígitos iguais
            raise serializers.ValidationError("CPF inválido")
        
        return cpf
    
    def validate_nome(self, value):
        """Validar nome"""
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError("Nome deve ter pelo menos 3 caracteres")
        
        # Apenas letras, espaços e acentos
        if not re.match(r'^[a-zA-ZÀ-ÿ\s]+$', value.strip()):
            raise serializers.ValidationError("Nome deve conter apenas letras")
        
        return value.strip().title()
    
    def validate_celular(self, value):
        """Validar celular"""
        # Remove caracteres não numéricos
        celular = re.sub(r'\D', '', value)
        
        if len(celular) < 10 or len(celular) > 11:
            raise serializers.ValidationError("Celular deve ter 10 ou 11 dígitos")
        
        return celular
    
    def validate_numero_cartao(self, value):
        """Validar número do cartão"""
        # Remove espaços e hífens
        numero = re.sub(r'[\s\-]', '', value)
        
        if not numero.isdigit():
            raise serializers.ValidationError("Número do cartão deve conter apenas dígitos")
        
        if len(numero) < 13 or len(numero) > 19:
            raise serializers.ValidationError("Número do cartão inválido")
        
        return numero
    
    def validate_cvv(self, value):
        """Validar CVV"""
        if not value.isdigit():
            raise serializers.ValidationError("CVV deve conter apenas dígitos")
        
        if len(value) < 3 or len(value) > 4:
            raise serializers.ValidationError("CVV deve ter 3 ou 4 dígitos")
        
        return value
    
    def validate_data_validade(self, value):
        """Validar data de validade - formato MM/YYYY"""
        # Aceitar apenas MM/YYYY
        if not re.match(r'^\d{2}/\d{4}$', value):
            raise serializers.ValidationError('Formato inválido. Use MM/YYYY')
        
        # Validar mês (01-12)
        mes = int(value[:2])
        if mes < 1 or mes > 12:
            raise serializers.ValidationError('Mês inválido')
        
        # Validar ano e se não está expirado
        from datetime import datetime
        ano = int(value[3:7])
        
        hoje = datetime.now()
        if ano < hoje.year or (ano == hoje.year and mes < hoje.month):
            raise serializers.ValidationError('Cartão expirado')
        
        return value
    
    def validate(self, attrs):
        """Validação cruzada: ajustar tipo_pagamento baseado em parcelas"""
        parcelas = attrs.get('parcelas', 1)
        tipo_pagamento = attrs.get('tipo_pagamento')
        
        # LÓGICA AUTOMÁTICA: ajustar tipo_pagamento baseado em parcelas
        if parcelas == 1:
            # 1 parcela = À vista
            attrs['tipo_pagamento'] = 'CREDIT_ONE_INSTALLMENT'
        elif parcelas > 1:
            # 2+ parcelas = Parcelado
            attrs['tipo_pagamento'] = 'CREDIT_IN_INSTALLMENTS_WITHOUT_INTEREST'
        
        return attrs


class ConfirmarCheckoutSerializer(serializers.Serializer):
    """Serializer para confirmação via WhatsApp"""
    token = serializers.CharField(max_length=64)
    codigo_whatsapp = serializers.CharField(max_length=6)
    
    def validate_codigo_whatsapp(self, value):
        """Validar código do WhatsApp"""
        if not value.isdigit():
            raise serializers.ValidationError("Código deve conter apenas dígitos")
        
        if len(value) != 6:
            raise serializers.ValidationError("Código deve ter 6 dígitos")
        
        return value


class StatusCheckoutSerializer(serializers.ModelSerializer):
    """Serializer para status do checkout"""
    is_valid = serializers.SerializerMethodField()
    time_remaining = serializers.SerializerMethodField()
    
    class Meta:
        model = CheckoutToken
        fields = ['token', 'item_nome', 'item_valor', 'used', 'expires_at', 'is_valid', 'time_remaining']
    
    def get_is_valid(self, obj):
        """Verifica se o token ainda é válido"""
        return obj.is_valid()
    
    def get_time_remaining(self, obj):
        """Tempo restante em minutos"""
        if obj.used:
            return 0
        
        from datetime import datetime
        remaining = obj.expires_at - datetime.now()
        return max(0, int(remaining.total_seconds() / 60))
