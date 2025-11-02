"""
Admin interface para modelos do app comum.
"""
from django.contrib import admin
from .estr_organizacional.canal import Canal
from .models import LogParametro


class CanalAdmin(admin.ModelAdmin):
    """Admin para modelo Canal"""
    list_display = ['id', 'nome', 'marca', 'cnpj', 'canal']
    list_filter = ['marca']
    search_fields = ['nome', 'marca', 'cnpj']
    ordering = ['id']


class LogParametroAdmin(admin.ModelAdmin):
    """Admin para modelo LogParametro"""
    list_display = ['processo', 'ligado', 'arquivo_log', 'descricao', 'updated_at']
    list_filter = ['ligado', 'updated_at']
    search_fields = ['processo', 'arquivo_log', 'descricao']
    ordering = ['processo']
    list_editable = ['ligado']  # Permite editar diretamente na lista
    readonly_fields = ['created_at', 'updated_at']



# Registrar explicitamente
admin.site.register(Canal, CanalAdmin)
admin.site.register(LogParametro, LogParametroAdmin)

# NOTA: Modelos de autenticação já estão registrados em comum/autenticacao/admin.py
# com @admin.register decorators, não precisam ser registrados novamente aqui
