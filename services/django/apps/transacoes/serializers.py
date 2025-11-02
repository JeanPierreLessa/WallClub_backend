"""
Serializers para o módulo de transações
"""
from rest_framework import serializers
from datetime import datetime


class ExtratoRequestSerializer(serializers.Serializer):
    """
    Serializer para solicitação de extrato
    Dados do usuário vêm do JWT Token automaticamente
    """
    data_inicio = serializers.DateField(required=False)
    data_fim = serializers.DateField(required=False)
    limite = serializers.IntegerField(min_value=1, max_value=100, default=50)
    
    def validate(self, data):
        """Validações customizadas"""
        data_inicio = data.get('data_inicio')
        data_fim = data.get('data_fim')
        
        # Se não informar datas, usar últimos 30 dias
        if not data_inicio and not data_fim:
            from datetime import date, timedelta
            data['data_fim'] = date.today()
            data['data_inicio'] = data['data_fim'] - timedelta(days=30)
        
        # Validar ordem das datas
        if data_inicio and data_fim and data_inicio > data_fim:
            raise serializers.ValidationError("Data início deve ser anterior à data fim")
        
        return data


class SaldoResponseSerializer(serializers.Serializer):
    """Serializer para resposta de saldo"""
    sucesso = serializers.BooleanField()
    saldo_atual = serializers.DecimalField(max_digits=10, decimal_places=2)
    saldo_bloqueado = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    ultima_atualizacao = serializers.DateTimeField()
    canal_id = serializers.IntegerField()


class TransacaoSerializer(serializers.Serializer):
    """Serializer para transação individual"""
    id = serializers.IntegerField()
    data_transacao = serializers.DateTimeField()
    tipo = serializers.CharField(max_length=50)
    descricao = serializers.CharField(max_length=255)
    valor = serializers.DecimalField(max_digits=10, decimal_places=2)
    saldo_anterior = serializers.DecimalField(max_digits=10, decimal_places=2)
    saldo_posterior = serializers.DecimalField(max_digits=10, decimal_places=2)
    status = serializers.CharField(max_length=20)


class ExtratoResponseSerializer(serializers.Serializer):
    """Serializer para resposta de extrato"""
    sucesso = serializers.BooleanField()
    periodo_inicio = serializers.DateField()
    periodo_fim = serializers.DateField()
    total_transacoes = serializers.IntegerField()
    transacoes = TransacaoSerializer(many=True)
    saldo_inicial = serializers.DecimalField(max_digits=10, decimal_places=2)
    saldo_final = serializers.DecimalField(max_digits=10, decimal_places=2)


class ComprovanteResponseSerializer(serializers.Serializer):
    """Serializer para resposta de comprovante"""
    sucesso = serializers.BooleanField()
    comprovante = serializers.DictField()  # Dados do comprovante
    codigo_comprovante = serializers.CharField(max_length=50)
    nsu_pinbank = serializers.CharField(max_length=50)
    comprovante_url = serializers.URLField(required=False)
