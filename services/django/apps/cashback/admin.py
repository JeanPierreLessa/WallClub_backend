from django.contrib import admin
from apps.cashback.models import RegraCashbackLoja, CashbackUso


@admin.register(RegraCashbackLoja)
class RegraCashbackLojaAdmin(admin.ModelAdmin):
    """Admin para regras de cashback Loja"""
    
    list_display = [
        'id', 'nome', 'loja_id', 'tipo_desconto', 'valor_desconto',
        'periodo_retencao_dias', 'ativo', 'vigencia_inicio', 'vigencia_fim'
    ]
    list_filter = ['ativo', 'tipo_desconto', 'vigencia_inicio', 'loja_id']
    search_fields = ['nome', 'descricao', 'loja_id']
    readonly_fields = ['created_at', 'updated_at', 'gasto_mes_atual']
    
    fieldsets = (
        ('Identificação', {
            'fields': ('nome', 'descricao', 'loja_id', 'ativo', 'prioridade')
        }),
        ('Desconto', {
            'fields': ('tipo_desconto', 'valor_desconto', 'valor_minimo_compra', 'valor_maximo_cashback')
        }),
        ('Retenção e Expiração', {
            'fields': ('periodo_retencao_dias', 'periodo_expiracao_dias')
        }),
        ('Filtros Opcionais', {
            'fields': ('formas_pagamento', 'dias_semana', 'horario_inicio', 'horario_fim'),
            'classes': ('collapse',)
        }),
        ('Limites de Uso', {
            'fields': (
                'limite_uso_cliente_dia', 'limite_uso_cliente_mes',
                'orcamento_mensal', 'gasto_mes_atual'
            ),
            'classes': ('collapse',)
        }),
        ('Vigência', {
            'fields': ('vigencia_inicio', 'vigencia_fim')
        }),
        ('Auditoria', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CashbackUso)
class CashbackUsoAdmin(admin.ModelAdmin):
    """Admin para histórico de uso de cashback"""
    
    list_display = [
        'id', 'tipo_origem', 'cliente_id', 'loja_id', 'valor_cashback',
        'status', 'transacao_tipo', 'aplicado_em'
    ]
    list_filter = ['tipo_origem', 'status', 'transacao_tipo', 'aplicado_em']
    search_fields = ['cliente_id', 'loja_id', 'transacao_id']
    readonly_fields = [
        'tipo_origem', 'parametro_wall_id', 'regra_loja_id', 'cliente_id', 'loja_id',
        'canal_id', 'transacao_tipo', 'transacao_id', 'valor_transacao',
        'valor_cashback', 'aplicado_em', 'liberado_em', 'expira_em', 'movimentacao_id'
    ]
    date_hierarchy = 'aplicado_em'
    
    fieldsets = (
        ('Origem', {
            'fields': ('tipo_origem', 'parametro_wall_id', 'regra_loja_id')
        }),
        ('Transação', {
            'fields': (
                'cliente_id', 'loja_id', 'canal_id',
                'transacao_tipo', 'transacao_id'
            )
        }),
        ('Valores', {
            'fields': ('valor_transacao', 'valor_cashback')
        }),
        ('Status e Datas', {
            'fields': ('status', 'aplicado_em', 'liberado_em', 'expira_em')
        }),
        ('Referência', {
            'fields': ('movimentacao_id',)
        }),
    )
    
    def has_add_permission(self, request):
        """Não permite criar manualmente via admin"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Não permite deletar via admin"""
        return False
