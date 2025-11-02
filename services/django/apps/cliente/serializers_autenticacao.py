"""
Serializers para dados de autenticação (análise de risco)
"""
from rest_framework import serializers


class StatusAutenticacaoSerializer(serializers.Serializer):
    """Status atual de autenticação do cliente"""
    bloqueado = serializers.BooleanField()
    bloqueado_ate = serializers.CharField(allow_null=True)
    bloqueio_motivo = serializers.CharField(allow_null=True)
    tentativas_15min = serializers.IntegerField()
    tentativas_1h = serializers.IntegerField()
    tentativas_24h = serializers.IntegerField()
    ultimo_ip = serializers.CharField(allow_null=True)
    ultimo_sucesso_em = serializers.CharField(allow_null=True)
    ultima_tentativa_em = serializers.CharField(allow_null=True)


class HistoricoRecenteSerializer(serializers.Serializer):
    """Estatísticas de tentativas recentes"""
    total_tentativas = serializers.IntegerField()
    tentativas_sucesso = serializers.IntegerField()
    tentativas_falhas = serializers.IntegerField()
    taxa_falha = serializers.FloatField()
    ips_distintos = serializers.IntegerField()
    devices_distintos = serializers.IntegerField()


class DispositivoConhecidoSerializer(serializers.Serializer):
    """Informações sobre dispositivo conhecido"""
    device_fingerprint = serializers.CharField()
    total_logins = serializers.IntegerField()
    total_sucesso = serializers.IntegerField()
    total_falhas = serializers.IntegerField()
    ultimo_uso = serializers.CharField(allow_null=True)
    primeiro_uso = serializers.CharField(allow_null=True)
    dias_desde_primeiro_uso = serializers.IntegerField()
    confiavel = serializers.BooleanField()


class BloqueioHistoricoSerializer(serializers.Serializer):
    """Histórico de bloqueio"""
    motivo = serializers.CharField()
    bloqueado_em = serializers.CharField()
    bloqueado_ate = serializers.CharField()
    desbloqueado_em = serializers.CharField(allow_null=True)
    desbloqueado_por = serializers.CharField(allow_null=True)
    ativo = serializers.BooleanField()
    tentativas_antes = serializers.IntegerField()


class ClienteAutenticacaoAnaliseSerializer(serializers.Serializer):
    """Análise completa de autenticação do cliente"""
    encontrado = serializers.BooleanField()
    cpf = serializers.CharField()
    cliente_id = serializers.IntegerField(required=False)
    canal_id = serializers.IntegerField(required=False)
    status_autenticacao = StatusAutenticacaoSerializer(required=False)
    historico_recente = HistoricoRecenteSerializer(required=False)
    dispositivos_conhecidos = DispositivoConhecidoSerializer(many=True, required=False)
    bloqueios_historico = BloqueioHistoricoSerializer(many=True, required=False)
    flags_risco = serializers.ListField(child=serializers.CharField(), required=False)
    timestamp_consulta = serializers.CharField(required=False)
    mensagem = serializers.CharField(required=False)
    erro = serializers.CharField(required=False)
