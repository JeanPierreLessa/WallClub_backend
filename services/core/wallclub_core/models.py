"""
Modelos compartilhados do sistema WallClub.
"""
from django.db import models

# Sistema migrado para OAuth 2.0 - API Keys removidas


# Canal migrado para comum/estr_organizacional/canal.py


class LogParametro(models.Model):
    """Controle dinâmico de logs por processo"""
    id = models.AutoField(primary_key=True)
    processo = models.CharField(max_length=100, unique=True)
    ligado = models.BooleanField(default=True)
    nivel = models.CharField(max_length=10, default='DEBUG')  # DEBUG ou ERROR
    arquivo_log = models.CharField(max_length=200)
    descricao = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'log_parametros'
        verbose_name = 'Log Parametro'
        verbose_name_plural = 'Log Parametros'
    
    def __str__(self):
        return f"{self.processo}"


class AuditoriaValidacaoSenha(models.Model):
    """Auditoria de tentativas de login e validação de senha"""
    id = models.AutoField(primary_key=True)
    cliente_id = models.IntegerField(null=True, blank=True, db_index=True)
    cpf = models.CharField(max_length=14, db_index=True)
    sucesso = models.BooleanField(default=False, db_index=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True, null=True)
    canal_id = models.IntegerField(db_index=True)
    endpoint = models.CharField(max_length=200)  # /api/v1/cliente/login/ ou /api/oauth/token/
    motivo_falha = models.CharField(max_length=200, blank=True, null=True)  # senha_incorreta, cpf_nao_encontrado, etc
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'cliente_auditoria_validacao_senha'
        verbose_name = 'Cliente Auditoria Validação Senha'
        verbose_name_plural = 'Cliente Auditorias Validação Senha'
        indexes = [
            models.Index(fields=['cpf', 'timestamp']),
            models.Index(fields=['ip_address', 'timestamp']),
            models.Index(fields=['sucesso', 'timestamp']),
        ]
    
    def __str__(self):
        return f"CPF {self.cpf} - {'Sucesso' if self.sucesso else 'Falha'} - {self.timestamp}"
