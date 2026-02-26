"""
Serializers para APIs Own Financial
"""

from rest_framework import serializers
from adquirente_own.models_cadastro import LojaOwn, LojaPinbank, LojaOwnTarifacao, LojaDocumentos


class CnaeSerializer(serializers.Serializer):
    """Serializer para atividades CNAE/MCC"""
    codCnae = serializers.CharField()
    descCnae = serializers.CharField()
    codMcc = serializers.IntegerField()


class CestaSerializer(serializers.Serializer):
    """Serializer para cestas de tarifas"""
    cestaId = serializers.IntegerField()
    nomeCesta = serializers.CharField()


class CestaTarifaSerializer(serializers.Serializer):
    """Serializer para tarifas de uma cesta"""
    cesta_valor_id = serializers.IntegerField()
    valor = serializers.DecimalField(max_digits=10, decimal_places=2)
    descricao = serializers.CharField(required=False, allow_blank=True)


class LojaOwnSerializer(serializers.ModelSerializer):
    """Serializer para LojaOwn"""

    class Meta:
        model = LojaOwn
        fields = [
            'id', 'loja_id', 'cadastrar',
            'status_credenciamento', 'protocolo', 'data_credenciamento',
            'mensagem_status', 'id_cesta', 'aceita_ecommerce',
            'sincronizado', 'ultima_sincronizacao', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class LojaPinbankSerializer(serializers.ModelSerializer):
    """Serializer para LojaPinbank"""

    class Meta:
        model = LojaPinbank
        fields = [
            'id', 'loja_id', 'codigo_canal', 'codigo_cliente',
            'key_value_loja', 'ativo', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class LojaOwnTarifacaoSerializer(serializers.ModelSerializer):
    """Serializer para LojaOwnTarifacao"""

    class Meta:
        model = LojaOwnTarifacao
        fields = [
            'id', 'loja_own_id', 'cesta_valor_id', 'valor',
            'descricao', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class LojaDocumentosSerializer(serializers.ModelSerializer):
    """Serializer para LojaDocumentos"""

    class Meta:
        model = LojaDocumentos
        fields = [
            'id', 'loja_id', 'tipo_documento', 'nome_arquivo',
            'caminho_arquivo', 'tamanho_bytes', 'mime_type',
            'cpf_socio', 'nome_socio', 'ativo',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CadastroOwnRequestSerializer(serializers.Serializer):
    """Serializer para request de cadastro na Own"""

    # Dados do estabelecimento
    cnpj = serializers.CharField(max_length=14)
    razao_social = serializers.CharField(max_length=256)
    nome_fantasia = serializers.CharField(max_length=256)
    email = serializers.EmailField()

    # Atividade econômica
    cnae = serializers.CharField(max_length=20)
    ramo_atividade = serializers.CharField(max_length=256)
    mcc = serializers.CharField(max_length=4)

    # Dados financeiros
    faturamento_previsto = serializers.DecimalField(max_digits=15, decimal_places=2)
    faturamento_contratado = serializers.DecimalField(max_digits=15, decimal_places=2)

    # Contato
    ddd_telefone_comercial = serializers.CharField(max_length=2)
    telefone_comercial = serializers.CharField(max_length=20)
    ddd_celular = serializers.CharField(max_length=2)
    celular = serializers.CharField(max_length=20)

    # Endereço
    cep = serializers.CharField(max_length=8)
    logradouro = serializers.CharField(max_length=256)
    numero_endereco = serializers.IntegerField()
    complemento = serializers.CharField(max_length=256, required=False, allow_blank=True)
    bairro = serializers.CharField(max_length=100)
    municipio = serializers.CharField(max_length=100)
    uf = serializers.CharField(max_length=2)

    # Responsável
    responsavel_assinatura = serializers.CharField(max_length=256)

    # Configurações de pagamento
    quantidade_pos = serializers.IntegerField(default=1)
    antecipacao_automatica = serializers.CharField(max_length=1, default='N')
    taxa_antecipacao = serializers.DecimalField(max_digits=5, decimal_places=2, default=0)
    tipo_antecipacao = serializers.CharField(max_length=20, default='ROTATIVO')

    # Dados bancários
    codigo_banco = serializers.CharField(max_length=3)
    agencia = serializers.CharField(max_length=10)
    digito_agencia = serializers.CharField(max_length=1, required=False, allow_blank=True)
    numero_conta = serializers.CharField(max_length=20)
    digito_conta = serializers.CharField(max_length=1)

    # Configurações Own
    id_cesta = serializers.IntegerField()
    tarifacao = serializers.ListField(
        child=serializers.DictField(),
        help_text='Lista de tarifas: [{"id": int, "valor": float}]'
    )
    aceita_ecommerce = serializers.BooleanField(default=False)

    # Opcionais
    cnpj_canal_wl = serializers.CharField(max_length=14, required=False, allow_blank=True)
    cnpj_origem = serializers.CharField(max_length=14, required=False, allow_blank=True)
    identificador_cliente = serializers.CharField(max_length=50, required=False, allow_blank=True)
    url_callback = serializers.URLField(required=False, allow_blank=True)


class CadastroOwnResponseSerializer(serializers.Serializer):
    """Serializer para response de cadastro na Own"""
    sucesso = serializers.BooleanField()
    protocolo = serializers.CharField(required=False)
    mensagem = serializers.CharField()
