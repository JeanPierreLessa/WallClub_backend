"""
Serializers para APIs REST de cupons
"""
from rest_framework import serializers
from .models import Cupom


class CupomAtivoSerializer(serializers.ModelSerializer):
    """Serializer para listar cupons ativos"""
    
    loja_nome = serializers.CharField(source='loja.nome_fantasia', read_only=True)
    tipo_cupom_display = serializers.CharField(source='get_tipo_cupom_display', read_only=True)
    tipo_desconto_display = serializers.CharField(source='get_tipo_desconto_display', read_only=True)
    
    class Meta:
        model = Cupom
        fields = [
            'id',
            'codigo',
            'loja_id',
            'loja_nome',
            'tipo_cupom',
            'tipo_cupom_display',
            'tipo_desconto',
            'tipo_desconto_display',
            'valor_desconto',
            'valor_minimo_compra',
            'limite_uso_total',
            'quantidade_usada',
            'data_inicio',
            'data_fim',
        ]


class CupomValidarSerializer(serializers.Serializer):
    """Serializer para validação de cupom"""
    
    codigo = serializers.CharField(required=True, max_length=50)
    loja_id = serializers.IntegerField(required=True)
    cliente_id = serializers.IntegerField(required=True)
    valor_transacao = serializers.DecimalField(required=True, max_digits=10, decimal_places=2)


class CupomValidarResponseSerializer(serializers.Serializer):
    """Serializer para resposta da validação"""
    
    valido = serializers.BooleanField()
    cupom_id = serializers.IntegerField(required=False, allow_null=True)
    valor_desconto = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    valor_final = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    mensagem = serializers.CharField()
