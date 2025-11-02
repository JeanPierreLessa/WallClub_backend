"""
Serializers para autenticação de clientes (usuários do APP móvel).
Responsável apenas pela validação de dados de entrada.
A lógica de negócio fica no services.py
"""
from rest_framework import serializers
from .models import Cliente, ClienteAuth


class ClienteLoginSerializer(serializers.Serializer):
    """Serializer para login de clientes - COM SENHA + 2FA obrigatório"""
    cpf = serializers.CharField(max_length=11, min_length=11)
    canal_id = serializers.IntegerField(min_value=1)
    senha = serializers.CharField(required=True, allow_blank=False, min_length=4)
    firebase_token = serializers.CharField(required=False, allow_blank=True)
    
    def validate_cpf(self, value):
        """Valida formato do CPF"""
        cpf_limpo = ''.join(filter(str.isdigit, value))
        if len(cpf_limpo) != 11:
            raise serializers.ValidationError("CPF deve ter 11 dígitos")
        return cpf_limpo


class ClienteCadastroSerializer(serializers.Serializer):
    """
    Serializer para cadastro de clientes - campos padronizados
    Parâmetros: cpf, celular, canal_id, email
    """
    cpf = serializers.CharField(max_length=11, min_length=11)
    celular = serializers.CharField(max_length=15)
    canal_id = serializers.IntegerField(min_value=1)
    email = serializers.EmailField(required=False, allow_blank=True)
    
    def validate_cpf(self, value):
        """Valida formato do CPF"""
        cpf_limpo = ''.join(filter(str.isdigit, value))
        if len(cpf_limpo) != 11:
            raise serializers.ValidationError("CPF deve ter 11 dígitos")
        return cpf_limpo
    
    def validate_celular(self, value):
        """Valida formato do celular"""
        celular_limpo = ''.join(filter(str.isdigit, value))
        if len(celular_limpo) < 10 or len(celular_limpo) > 11:
            raise serializers.ValidationError("Celular deve ter 10 ou 11 dígitos")
        return celular_limpo



class ClientePerfilSerializer(serializers.ModelSerializer):
    """Serializer para perfil do cliente"""
    class Meta:
        model = Cliente
        fields = ['nome', 'celular', 'email', 'nome_mae', 'dt_nascimento', 'signo']
        

