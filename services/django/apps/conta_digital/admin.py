"""
Admin para o sistema de conta digital.
"""
from django.contrib import admin
from django.shortcuts import render, redirect
from django.urls import path
from django.contrib import messages
from django.utils.html import format_html
from decimal import Decimal
from .models import ContaDigital, TipoMovimentacao, MovimentacaoContaDigital, ConfiguracaoContaDigital
from .services import ContaDigitalService
from wallclub_core.utilitarios.log_control import registrar_log


@admin.register(ContaDigital)
class ContaDigitalAdmin(admin.ModelAdmin):
    list_display = [
        'cliente_id', 'canal_id', 'cpf', 'saldo_disponivel_display',
        'saldo_bloqueado', 'ativa_display', 'bloqueada_display', 'created_at'
    ]
    list_filter = ['ativa', 'bloqueada', 'canal_id', 'created_at']
    search_fields = ['cliente_id', 'cpf']
    readonly_fields = ['saldo_atual', 'saldo_bloqueado', 'created_at', 'updated_at']
    actions = ['action_creditar_manual', 'action_debitar_manual', 'action_ver_extrato']

    fieldsets = (
        ('Identificação', {
            'fields': ('cliente_id', 'canal_id', 'cpf')
        }),
        ('Saldos (Somente Leitura)', {
            'fields': ('saldo_atual', 'saldo_bloqueado'),
            'description': 'Use as actions "Creditar Manual" ou "Debitar Manual" para alterar saldos'
        }),
        ('Limites', {
            'fields': ('limite_diario', 'limite_mensal')
        }),
        ('Status', {
            'fields': ('ativa', 'bloqueada', 'motivo_bloqueio')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def saldo_disponivel_display(self, obj):
        """Exibe saldo disponível calculado"""
        saldo_disp = obj.get_saldo_disponivel()
        cor = 'green' if saldo_disp > 0 else 'red'
        valor_formatado = f'{float(saldo_disp):.2f}'
        return format_html('<strong style="color: {};">R$ {}</strong>', cor, valor_formatado)
    saldo_disponivel_display.short_description = 'Saldo Disponível'

    def ativa_display(self, obj):
        """Exibe status ativa com ícone"""
        if obj.ativa:
            return format_html('<span style="color: green;">✓ Ativa</span>')
        return format_html('<span style="color: red;">✗ Inativa</span>')
    ativa_display.short_description = 'Ativa'

    def bloqueada_display(self, obj):
        """Exibe status bloqueada com ícone"""
        if obj.bloqueada:
            return format_html('<span style="color: red;">🔒 Bloqueada</span>')
        return format_html('<span style="color: green;">🔓 Desbloqueada</span>')
    bloqueada_display.short_description = 'Bloqueio'

    def get_urls(self):
        """Adiciona URLs customizadas para actions"""
        urls = super().get_urls()
        custom_urls = [
            path('creditar-manual/', self.admin_site.admin_view(self.creditar_manual_view), name='conta_digital_creditar_manual'),
            path('debitar-manual/', self.admin_site.admin_view(self.debitar_manual_view), name='conta_digital_debitar_manual'),
        ]
        return custom_urls + urls

    def action_creditar_manual(self, request, queryset):
        """Action para creditar saldo manualmente"""
        if queryset.count() != 1:
            self.message_user(request, 'Selecione apenas uma conta por vez', level=messages.ERROR)
            return

        conta_ids = ','.join(str(c.id) for c in queryset)
        return redirect(f'/admin/conta_digital/contadigital/creditar-manual/?ids={conta_ids}')
    action_creditar_manual.short_description = '💰 Creditar Saldo Manual'

    def action_debitar_manual(self, request, queryset):
        """Action para debitar saldo manualmente"""
        if queryset.count() != 1:
            self.message_user(request, 'Selecione apenas uma conta por vez', level=messages.ERROR)
            return

        conta_ids = ','.join(str(c.id) for c in queryset)
        return redirect(f'/admin/conta_digital/contadigital/debitar-manual/?ids={conta_ids}')
    action_debitar_manual.short_description = '💸 Debitar Saldo Manual'

    def action_ver_extrato(self, request, queryset):
        """Action para ver extrato da conta"""
        if queryset.count() != 1:
            self.message_user(request, 'Selecione apenas uma conta por vez', level=messages.ERROR)
            return

        conta = queryset.first()
        return redirect(f'/admin/conta_digital/movimentacaocontadigital/?conta_digital__id__exact={conta.id}')
    action_ver_extrato.short_description = '📊 Ver Extrato'

    def creditar_manual_view(self, request):
        """View para formulário de crédito manual"""
        conta_ids = request.GET.get('ids', '').split(',')
        conta = ContaDigital.objects.get(id=conta_ids[0])

        if request.method == 'POST':
            try:
                valor = Decimal(request.POST.get('valor'))
                descricao = request.POST.get('descricao')
                tipo_operacao = request.POST.get('tipo_operacao', 'CREDITO_MANUAL')

                if valor <= 0:
                    messages.error(request, 'Valor deve ser maior que zero')
                    return redirect(request.path + f'?ids={conta.id}')

                # Usar service para creditar
                movimentacao = ContaDigitalService.creditar(
                    cliente_id=conta.cliente_id,
                    canal_id=conta.canal_id,
                    valor=valor,
                    descricao=descricao,
                    tipo_codigo=tipo_operacao,
                    referencia_externa=f'ADMIN-{request.user.id}',
                    sistema_origem='DJANGO_ADMIN'
                )

                # Log de auditoria
                registrar_log(
                    'apps.conta_digital',
                    f'Crédito manual: R$ {valor:.2f} para cliente {conta.cliente_id} (CPF: {conta.cpf}) por admin {request.user.username}',
                    nivel='INFO'
                )

                messages.success(request, f'Crédito de R$ {valor:.2f} realizado com sucesso!')
                return redirect('/admin/conta_digital/contadigital/')

            except Exception as e:
                messages.error(request, f'Erro ao creditar: {str(e)}')
                registrar_log('apps.conta_digital', f'Erro crédito manual: {str(e)}', nivel='ERROR')

        # Buscar tipos de movimentação de crédito
        tipos_credito = TipoMovimentacao.objects.filter(
            debita_saldo=False,
            ativo=True,
            categoria__in=['CREDITO', 'CASHBACK', 'TRANSFERENCIA']
        )

        context = {
            'conta': conta,
            'tipos_credito': tipos_credito,
            'titulo': 'Creditar Saldo Manual',
            'operacao': 'creditar'
        }
        return render(request, 'admin/conta_digital/operacao_manual.html', context)

    def debitar_manual_view(self, request):
        """View para formulário de débito manual"""
        conta_ids = request.GET.get('ids', '').split(',')
        conta = ContaDigital.objects.get(id=conta_ids[0])

        if request.method == 'POST':
            try:
                valor = Decimal(request.POST.get('valor'))
                descricao = request.POST.get('descricao')
                tipo_operacao = request.POST.get('tipo_operacao', 'DEBITO_MANUAL')

                if valor <= 0:
                    messages.error(request, 'Valor deve ser maior que zero')
                    return redirect(request.path + f'?ids={conta.id}')

                # Verificar saldo disponível
                saldo_disp = conta.get_saldo_disponivel()
                if valor > saldo_disp:
                    messages.error(request, f'Saldo insuficiente. Disponível: R$ {saldo_disp:.2f}')
                    return redirect(request.path + f'?ids={conta.id}')

                # Usar service para debitar
                movimentacao = ContaDigitalService.debitar(
                    cliente_id=conta.cliente_id,
                    canal_id=conta.canal_id,
                    valor=valor,
                    descricao=descricao,
                    tipo_codigo=tipo_operacao,
                    referencia_externa=f'ADMIN-{request.user.id}',
                    sistema_origem='DJANGO_ADMIN'
                )

                # Log de auditoria
                registrar_log(
                    'apps.conta_digital',
                    f'Débito manual: R$ {valor:.2f} para cliente {conta.cliente_id} (CPF: {conta.cpf}) por admin {request.user.username}',
                    nivel='INFO'
                )

                messages.success(request, f'Débito de R$ {valor:.2f} realizado com sucesso!')
                return redirect('/admin/conta_digital/contadigital/')

            except Exception as e:
                messages.error(request, f'Erro ao debitar: {str(e)}')
                registrar_log('apps.conta_digital', f'Erro débito manual: {str(e)}', nivel='ERROR')

        # Buscar tipos de movimentação de débito
        tipos_debito = TipoMovimentacao.objects.filter(
            debita_saldo=True,
            ativo=True,
            categoria__in=['DEBITO', 'TRANSFERENCIA', 'PAGAMENTO']
        )

        context = {
            'conta': conta,
            'tipos_debito': tipos_debito,
            'titulo': 'Debitar Saldo Manual',
            'operacao': 'debitar'
        }
        return render(request, 'admin/conta_digital/operacao_manual.html', context)


@admin.register(TipoMovimentacao)
class TipoMovimentacaoAdmin(admin.ModelAdmin):
    list_display = [
        'codigo', 'nome', 'categoria', 'debita_saldo',
        'permite_estorno', 'visivel_extrato', 'ativo'
    ]
    list_filter = ['categoria', 'debita_saldo', 'permite_estorno', 'ativo']
    search_fields = ['codigo', 'nome']
    readonly_fields = ['created_at']


@admin.register(MovimentacaoContaDigital)
class MovimentacaoContaDigitalAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'conta_display', 'tipo_display', 'valor_display',
        'status_display', 'data_movimentacao', 'sistema_origem', 'admin_display'
    ]
    list_filter = [
        'status', 'tipo_movimentacao', 'sistema_origem', 'data_movimentacao'
    ]
    search_fields = [
        'conta_digital__cliente_id', 'conta_digital__cpf',
        'referencia_externa', 'descricao'
    ]
    readonly_fields = [
        'conta_digital', 'tipo_movimentacao', 'valor',
        'saldo_anterior', 'saldo_posterior', 'descricao',
        'referencia_externa', 'sistema_origem', 'status',
        'processada_em', 'created_at', 'updated_at'
    ]

    def has_add_permission(self, request):
        """Desabilita criação manual - usar actions em ContaDigital"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Desabilita exclusão - usar estorno"""
        return False

    def conta_display(self, obj):
        """Exibe cliente e CPF"""
        return format_html(
            'Cliente: {} | CPF: {}',
            obj.conta_digital.cliente_id,
            obj.conta_digital.cpf
        )
    conta_display.short_description = 'Conta'

    def tipo_display(self, obj):
        """Exibe tipo com ícone"""
        icone = '➕' if not obj.tipo_movimentacao.debita_saldo else '➖'
        cor = 'green' if not obj.tipo_movimentacao.debita_saldo else 'red'
        return format_html(
            '<span style="color: {};">{} {}</span>',
            cor, icone, obj.tipo_movimentacao.nome
        )
    tipo_display.short_description = 'Tipo'

    def valor_display(self, obj):
        """Exibe valor com cor"""
        cor = 'green' if not obj.tipo_movimentacao.debita_saldo else 'red'
        sinal = '+' if not obj.tipo_movimentacao.debita_saldo else '-'
        valor_formatado = f'{float(obj.valor):.2f}'
        return format_html(
            '<strong style="color: {};">{} R$ {}</strong>',
            cor, sinal, valor_formatado
        )
    valor_display.short_description = 'Valor'

    def status_display(self, obj):
        """Exibe status com cor"""
        cores = {
            'PROCESSADA': 'green',
            'PENDENTE': 'orange',
            'ESTORNADA': 'gray',
            'ERRO': 'red'
        }
        cor = cores.get(obj.status, 'black')
        return format_html('<span style="color: {};">{}</span>', cor, obj.status)
    status_display.short_description = 'Status'

    def admin_display(self, obj):
        """Exibe admin que fez a operação (se via Django Admin)"""
        if obj.sistema_origem == 'DJANGO_ADMIN' and obj.referencia_externa:
            admin_id = obj.referencia_externa.replace('ADMIN-', '')
            return format_html('<span title="Admin ID: {}">🔧 Admin</span>', admin_id)
        return '-'
    admin_display.short_description = 'Operador'

    fieldsets = (
        ('Conta e Tipo', {
            'fields': ('conta_digital', 'tipo_movimentacao')
        }),
        ('Valores', {
            'fields': ('valor', 'saldo_anterior', 'saldo_posterior')
        }),
        ('Descrição', {
            'fields': ('descricao', 'observacoes')
        }),
        ('Referências', {
            'fields': ('referencia_externa', 'sistema_origem')
        }),
        ('Status', {
            'fields': ('status', 'movimentacao_estorno')
        }),
        ('Timestamps', {
            'fields': ('data_movimentacao', 'processada_em', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(ConfiguracaoContaDigital)
class ConfiguracaoContaDigitalAdmin(admin.ModelAdmin):
    list_display = [
        'canal_id', 'nome_canal', 'limite_diario_padrao',
        'limite_mensal_padrao', 'auto_criar_conta', 'ativo'
    ]
    list_filter = ['auto_criar_conta', 'permite_saldo_negativo', 'ativo']
    search_fields = ['canal_id', 'nome_canal']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Canal', {
            'fields': ('canal_id', 'nome_canal')
        }),
        ('Limites Padrão', {
            'fields': ('limite_diario_padrao', 'limite_mensal_padrao')
        }),
        ('Configurações', {
            'fields': ('permite_saldo_negativo', 'auto_criar_conta')
        }),
        ('Taxas', {
            'fields': ('taxa_transferencia', 'taxa_saque')
        }),
        ('Status', {
            'fields': ('ativo',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
