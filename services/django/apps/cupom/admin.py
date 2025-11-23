from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count
from .models import Cupom, CupomUso


@admin.register(Cupom)
class CupomAdmin(admin.ModelAdmin):
    list_display = [
        'codigo',
        'loja_id',
        'tipo_cupom',
        'tipo_desconto_display',
        'valor_desconto',
        'uso_display',
        'validade_display',
        'ativo_display',
    ]
    list_filter = [
        'tipo_cupom',
        'tipo_desconto',
        'ativo',
        'data_inicio',
        'data_fim',
    ]
    search_fields = [
        'codigo',
        'loja_id',
        'cliente_id',
    ]
    readonly_fields = [
        'quantidade_usada',
        'created_at',
        'updated_at',
    ]
    fieldsets = (
        ('Informações Básicas', {
            'fields': (
                'codigo',
                'loja_id',
                'tipo_cupom',
                'cliente_id',
                'ativo',
            )
        }),
        ('Configuração do Desconto', {
            'fields': (
                'tipo_desconto',
                'valor_desconto',
                'valor_minimo_compra',
            )
        }),
        ('Limites de Uso', {
            'fields': (
                'limite_uso_total',
                'limite_uso_por_cpf',
                'quantidade_usada',
            )
        }),
        ('Validade', {
            'fields': (
                'data_inicio',
                'data_fim',
            )
        }),
        ('Auditoria', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',)
        }),
    )
    
    def tipo_desconto_display(self, obj):
        if obj.tipo_desconto == 'FIXO':
            return f"R$ {obj.valor_desconto}"
        else:
            return f"{obj.valor_desconto}%"
    tipo_desconto_display.short_description = 'Desconto'
    
    def uso_display(self, obj):
        if obj.limite_uso_total:
            percentual = (obj.quantidade_usada / obj.limite_uso_total) * 100
            cor = 'green' if percentual < 80 else 'orange' if percentual < 100 else 'red'
            return format_html(
                '<span style="color: {};">{} / {}</span>',
                cor,
                obj.quantidade_usada,
                obj.limite_uso_total
            )
        return f"{obj.quantidade_usada} (ilimitado)"
    uso_display.short_description = 'Uso'
    
    def validade_display(self, obj):
        from datetime import datetime
        agora = datetime.now()
        
        if agora < obj.data_inicio:
            return format_html('<span style="color: gray;">Aguardando início</span>')
        elif agora > obj.data_fim:
            return format_html('<span style="color: red;">Expirado</span>')
        else:
            return format_html('<span style="color: green;">Válido</span>')
    validade_display.short_description = 'Status'
    
    def ativo_display(self, obj):
        if obj.ativo:
            return format_html('<span style="color: green;">✓ Ativo</span>')
        return format_html('<span style="color: red;">✗ Inativo</span>')
    ativo_display.short_description = 'Ativo'


@admin.register(CupomUso)
class CupomUsoAdmin(admin.ModelAdmin):
    list_display = [
        'cupom_id',
        'cliente_id',
        'loja_id',
        'transacao_tipo',
        'transacao_id',
        'valor_desconto_aplicado',
        'estornado_display',
        'usado_em',
    ]
    list_filter = [
        'transacao_tipo',
        'estornado',
        'usado_em',
    ]
    search_fields = [
        'cupom_id',
        'cliente_id',
        'transacao_id',
        'nsu',
    ]
    readonly_fields = [
        'cupom_id',
        'cliente_id',
        'loja_id',
        'transacao_tipo',
        'transacao_id',
        'nsu',
        'valor_transacao_original',
        'valor_desconto_aplicado',
        'valor_transacao_final',
        'estornado',
        'usado_em',
        'ip_address',
    ]
    
    def has_add_permission(self, request):
        # Não permite criar manualmente (apenas via sistema)
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Não permite deletar (auditoria)
        return False
    
    def estornado_display(self, obj):
        if obj.estornado:
            return format_html('<span style="color: red;">✗ Estornado</span>')
        return format_html('<span style="color: green;">✓ Ativo</span>')
    estornado_display.short_description = 'Status'
