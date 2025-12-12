"""
Serializers para as APIs da conta digital.
"""
from rest_framework import serializers
from decimal import Decimal
from .models import ContaDigital, MovimentacaoContaDigital, TipoMovimentacao


class ContaDigitalSerializer(serializers.ModelSerializer):
    """Serializer para dados da conta digital"""
    saldo_disponivel = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    
    class Meta:
        model = ContaDigital
        fields = [
            'cliente_id', 'canal_id', 'cpf',
            'saldo_atual', 'saldo_bloqueado', 'saldo_disponivel',
            'limite_diario', 'limite_mensal',
            'ativa', 'bloqueada', 'motivo_bloqueio',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['cliente_id', 'canal_id', 'cpf', 'created_at', 'updated_at']
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['saldo_disponivel'] = instance.get_saldo_disponivel()
        return data


class SaldoSerializer(serializers.Serializer):
    """Serializer para resposta de consulta de saldo"""
    saldo_atual = serializers.DecimalField(max_digits=15, decimal_places=2)
    saldo_bloqueado = serializers.DecimalField(max_digits=15, decimal_places=2)
    saldo_disponivel = serializers.DecimalField(max_digits=15, decimal_places=2)
    cashback_disponivel = serializers.DecimalField(max_digits=15, decimal_places=2)
    cashback_bloqueado = serializers.DecimalField(max_digits=15, decimal_places=2)
    cashback_total = serializers.DecimalField(max_digits=15, decimal_places=2)
    saldo_total_disponivel = serializers.DecimalField(max_digits=15, decimal_places=2)
    limite_diario = serializers.DecimalField(max_digits=15, decimal_places=2)
    limite_mensal = serializers.DecimalField(max_digits=15, decimal_places=2)
    conta_ativa = serializers.BooleanField()
    conta_bloqueada = serializers.BooleanField()
    motivo_bloqueio = serializers.CharField(allow_null=True)


class MovimentacaoSerializer(serializers.ModelSerializer):
    """Serializer para movimentações da conta digital"""
    tipo_nome = serializers.CharField(source='tipo_movimentacao.nome', read_only=True)
    tipo_categoria = serializers.CharField(source='tipo_movimentacao.categoria', read_only=True)
    
    class Meta:
        model = MovimentacaoContaDigital
        fields = [
            'id', 'tipo_nome', 'tipo_categoria',
            'saldo_anterior', 'saldo_posterior', 'valor',
            'descricao', 'observacoes', 'referencia_externa',
            'sistema_origem', 'status', 'data_movimentacao',
            'processada_em', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def to_representation(self, instance):
        """Ajusta sinal do valor: positivo para crédito, negativo para débito"""
        from decimal import Decimal
        from datetime import datetime, timedelta
        data = super().to_representation(instance)
        
        # Converter valor de string para Decimal antes de aplicar abs()
        valor = Decimal(data['valor'])
        
        # Se é débito, inverte o sinal do valor
        if instance.tipo_movimentacao.debita_saldo:
            data['valor'] = str(-abs(valor))
        else:
            # Crédito mantém positivo
            data['valor'] = str(abs(valor))
        
        # Formatar datas no padrão YYYY-MM-DD HH:MM:SS
        for field in ['data_movimentacao', 'processada_em', 'created_at']:
            if data.get(field):
                if isinstance(data[field], str):
                    # Já é string, tentar parsear e reformatar
                    try:
                        dt = datetime.fromisoformat(data[field].replace('Z', '+00:00'))
                        data[field] = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass
                else:
                    # É datetime object
                    data[field] = data[field].strftime('%Y-%m-%d %H:%M:%S')
        
        # Adicionar informações de cashback se disponível no contexto
        cashback_info = self.context.get('cashback_info', {})
        if instance.id in cashback_info:
            cu = cashback_info[instance.id]
            
            # Calcular data de desbloqueio prevista (30 dias após aplicação)
            data_aplicacao = cu['aplicado_em']
            if isinstance(data_aplicacao, str):
                data_aplicacao = datetime.fromisoformat(data_aplicacao.replace('Z', '+00:00'))
            
            data_desbloqueio = data_aplicacao + timedelta(days=30)
            
            # Calcular dias para desbloqueio
            dias_para_desbloqueio = (data_desbloqueio - datetime.now()).days
            if dias_para_desbloqueio < 0:
                dias_para_desbloqueio = 0
            
            # Calcular data de expiração (90 dias após liberação)
            data_expiracao = data_desbloqueio + timedelta(days=90)
            
            data['cashback'] = {
                'tipo_origem': cu['tipo_origem'],
                'status': cu['status'],
                'bloqueado': cu['status'] == 'RETIDO',
                'data_aplicacao': data_aplicacao.strftime('%Y-%m-%d %H:%M:%S'),
                'data_desbloqueio_prevista': data_desbloqueio.strftime('%Y-%m-%d %H:%M:%S'),
                'data_expiracao': data_expiracao.strftime('%Y-%m-%d %H:%M:%S'),
                'dias_para_desbloqueio': dias_para_desbloqueio
            }
        
        return data


class ResumoCashbackSerializer(serializers.Serializer):
    """Serializer para resumo de cashback"""
    total_retido = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_disponivel = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_geral = serializers.DecimalField(max_digits=15, decimal_places=2)
    proxima_liberacao = serializers.DateTimeField(allow_null=True)
    
    def to_representation(self, instance):
        from datetime import datetime
        data = super().to_representation(instance)
        
        # Formatar data de próxima liberação
        if data.get('proxima_liberacao'):
            if isinstance(data['proxima_liberacao'], str):
                try:
                    dt = datetime.fromisoformat(data['proxima_liberacao'].replace('Z', '+00:00'))
                    data['proxima_liberacao'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    pass
            else:
                data['proxima_liberacao'] = data['proxima_liberacao'].strftime('%Y-%m-%d %H:%M:%S')
        
        return data


class ExtratoSerializer(serializers.Serializer):
    """Serializer para resposta de extrato"""
    saldo_atual = serializers.DecimalField(max_digits=15, decimal_places=2)
    cashback_disponivel = serializers.DecimalField(max_digits=15, decimal_places=2)
    cashback_bloqueado = serializers.DecimalField(max_digits=15, decimal_places=2)
    movimentacoes = MovimentacaoSerializer(many=True)
    resumo_cashback = ResumoCashbackSerializer()
    
    def to_representation(self, instance):
        # Passar cashback_info para o contexto das movimentações
        cashback_info = instance.get('cashback_info', {})
        self.fields['movimentacoes'].context['cashback_info'] = cashback_info
        return super().to_representation(instance)


class CreditarSerializer(serializers.Serializer):
    """Serializer para operação de crédito"""
    valor = serializers.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        min_value=Decimal('0.01')
    )
    descricao = serializers.CharField(max_length=200)
    tipo_operacao = serializers.CharField(max_length=30, default='credito')
    referencia_externa = serializers.CharField(max_length=100, required=False, allow_blank=True)
    sistema_origem = serializers.CharField(max_length=50, required=False, allow_blank=True)
    
    def validate_tipo_operacao(self, value):
        """Mapeia tipo_operacao para tipo_codigo e valida"""
        # Mapeamento de tipos de operação
        mapeamento = {
            'credito': 'CREDITO',
            'cashback': 'CASHBACK',
            'cashback_credito': 'CASHBACK_CREDITO',
            'transferencia': 'TRANSFERENCIA_CREDITO',
            'pix_credito': 'PIX_CREDITO'
        }
        
        tipo_codigo = mapeamento.get(value.lower())
        if not tipo_codigo:
            raise serializers.ValidationError(f"Tipo de operação '{value}' não suportado")
        
        try:
            tipo = TipoMovimentacao.objects.get(codigo=tipo_codigo, ativo=True)
            if tipo.debita_saldo:
                raise serializers.ValidationError("Tipo de movimentação deve ser de crédito")
            return tipo_codigo
        except TipoMovimentacao.DoesNotExist:
            raise serializers.ValidationError(f"Tipo de movimentação '{tipo_codigo}' não encontrado")


class DebitarSerializer(serializers.Serializer):
    """Serializer para operação de débito"""
    valor = serializers.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        min_value=Decimal('0.01')
    )
    descricao = serializers.CharField(max_length=200)
    tipo_codigo = serializers.CharField(max_length=30, default='DEBITO')
    referencia_externa = serializers.CharField(max_length=100, required=False, allow_blank=True)
    sistema_origem = serializers.CharField(max_length=50, required=False, allow_blank=True)
    
    def validate_tipo_codigo(self, value):
        """Valida se o tipo de movimentação existe e é de débito"""
        try:
            tipo = TipoMovimentacao.objects.get(codigo=value, ativo=True)
            if not tipo.debita_saldo:
                raise serializers.ValidationError("Tipo de movimentação deve ser de débito")
            return value
        except TipoMovimentacao.DoesNotExist:
            raise serializers.ValidationError("Tipo de movimentação não encontrado")


class BloquearSaldoSerializer(serializers.Serializer):
    """Serializer para bloqueio de saldo"""
    valor = serializers.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        min_value=Decimal('0.01')
    )
    motivo = serializers.CharField(max_length=200)


class DesbloquearSaldoSerializer(serializers.Serializer):
    """Serializer para desbloqueio de saldo"""
    valor = serializers.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        min_value=Decimal('0.01')
    )
    motivo = serializers.CharField(max_length=200)


class EstornarSerializer(serializers.Serializer):
    """Serializer para estorno de movimentação"""
    movimentacao_id = serializers.IntegerField()
    motivo = serializers.CharField(max_length=200)


class ExtratoFiltroSerializer(serializers.Serializer):
    """Serializer para filtros do extrato"""
    data_inicio = serializers.DateField(required=False)
    data_fim = serializers.DateField(required=False)
    tipo_movimentacao = serializers.CharField(max_length=30, required=False)
    limite = serializers.IntegerField(min_value=1, max_value=100, default=50)
    
    def validate(self, data):
        """Valida se data_inicio é anterior a data_fim e converte para datetime"""
        from datetime import datetime
        
        data_inicio = data.get('data_inicio')
        data_fim = data.get('data_fim')
        
        if data_inicio and data_fim and data_inicio > data_fim:
            raise serializers.ValidationError("Data de início deve ser anterior à data de fim")
        
        # Converter DateField para DateTime com hora apropriada
        if data_inicio:
            data['data_inicio'] = datetime.combine(data_inicio, datetime.min.time())  # 00:00:00
        
        if data_fim:
            data['data_fim'] = datetime.combine(data_fim, datetime.max.time())  # 23:59:59.999999
        
        return data


class MovimentacaoResponseSerializer(serializers.Serializer):
    """Serializer para resposta de operações de movimentação"""
    id = serializers.IntegerField()
    tipo = serializers.CharField()
    valor = serializers.DecimalField(max_digits=15, decimal_places=2)
    descricao = serializers.CharField()
    saldo_anterior = serializers.DecimalField(max_digits=15, decimal_places=2)
    saldo_posterior = serializers.DecimalField(max_digits=15, decimal_places=2)
    status = serializers.CharField()
    data_movimentacao = serializers.DateTimeField()
    referencia_externa = serializers.CharField(allow_null=True)
    sistema_origem = serializers.CharField(allow_null=True)
