"""
Views para gerenciamento de cashback no portal lojista
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.views import View
from datetime import datetime, timedelta
from decimal import Decimal
from .mixins import LojistaAccessMixin, LojistaDataMixin
from wallclub_core.utilitarios.log_control import registrar_log


class CashbackListView(LojistaAccessMixin, LojistaDataMixin, View):
    """Lista de regras de cashback da loja"""
    
    def get(self, request):
        from django.apps import apps
        RegraCashbackLoja = apps.get_model('cashback', 'RegraCashbackLoja')
        
        lojas_ids = self.get_lojas_ids()
        
        # Filtros
        busca = request.GET.get('busca', '')
        status = request.GET.get('status', '')
        
        # Query base
        regras = RegraCashbackLoja.objects.filter(loja_id__in=lojas_ids)
        
        # Aplicar filtros
        if busca:
            regras = regras.filter(
                Q(nome__icontains=busca) |
                Q(descricao__icontains=busca)
            )
        
        if status == 'ativo':
            regras = regras.filter(ativo=True)
        elif status == 'inativo':
            regras = regras.filter(ativo=False)
        elif status == 'vigente':
            agora = timezone.now()
            regras = regras.filter(
                ativo=True,
                vigencia_inicio__lte=agora,
                vigencia_fim__gte=agora
            )
        elif status == 'expirado':
            regras = regras.filter(vigencia_fim__lt=timezone.now())
        
        # Ordenar
        regras = regras.order_by('-prioridade', '-created_at')
        
        # Estatísticas
        total_regras = RegraCashbackLoja.objects.filter(loja_id__in=lojas_ids)
        stats = {
            'total': total_regras.count(),
            'ativos': total_regras.filter(ativo=True).count(),
            'vigentes': total_regras.filter(
                ativo=True,
                vigencia_inicio__lte=timezone.now(),
                vigencia_fim__gte=timezone.now()
            ).count(),
        }
        
        # Paginação
        paginator = Paginator(regras, 20)
        page = request.GET.get('page', 1)
        regras_page = paginator.get_page(page)
        
        context = {
            'regras': regras_page,
            'stats': stats,
            'busca': busca,
            'status': status,
        }
        
        return render(request, 'portais/lojista/cashback/lista.html', context)


class CashbackCreateView(LojistaAccessMixin, LojistaDataMixin, View):
    """Criar nova regra de cashback"""
    
    def get(self, request):
        from django.apps import apps
        RegraCashbackLoja = apps.get_model('cashback', 'RegraCashbackLoja')
        
        lojas_acessiveis = self.get_lojas_acessiveis()
        loja_id_atual = request.session.get('loja_id')
        
        context = {
            'tipos_concessao': RegraCashbackLoja._meta.get_field('tipo_concessao').choices,
            'lojas_acessiveis': lojas_acessiveis,
            'loja_id_atual': loja_id_atual,
        }
        return render(request, 'portais/lojista/cashback/form.html', context)
    
    def post(self, request):
        from django.apps import apps
        RegraCashbackLoja = apps.get_model('cashback', 'RegraCashbackLoja')
        
        try:
            loja_id = request.POST.get('loja_id') or request.session.get('loja_id')
            
            if not loja_id:
                messages.error(request, 'Loja não identificada')
                return redirect('lojista:cashback_lista')
            
            # Validar acesso à loja
            if int(loja_id) not in self.get_lojas_ids():
                messages.error(request, 'Você não tem permissão para criar cashback nesta loja')
                return redirect('lojista:cashback_lista')
            
            # Criar regra
            regra = RegraCashbackLoja.objects.create(
                loja_id=loja_id,
                nome=request.POST.get('nome'),
                descricao=request.POST.get('descricao', ''),
                ativo=request.POST.get('ativo') == 'on',
                prioridade=int(request.POST.get('prioridade', 0)),
                tipo_concessao=request.POST.get('tipo_concessao'),
                valor_concessao=Decimal(request.POST.get('valor_concessao')),
                valor_minimo_compra=Decimal(request.POST.get('valor_minimo_compra', '0.00')),
                valor_maximo_cashback=Decimal(request.POST.get('valor_maximo_cashback')) if request.POST.get('valor_maximo_cashback') else None,
                vigencia_inicio=datetime.strptime(request.POST.get('vigencia_inicio'), '%Y-%m-%dT%H:%M'),
                vigencia_fim=datetime.strptime(request.POST.get('vigencia_fim'), '%Y-%m-%dT%H:%M'),
                formas_pagamento=request.POST.getlist('formas_pagamento') if request.POST.getlist('formas_pagamento') else None,
                dias_semana=[int(d) for d in request.POST.getlist('dias_semana')] if request.POST.getlist('dias_semana') else None,
                horario_inicio=request.POST.get('horario_inicio') if request.POST.get('horario_inicio') else None,
                horario_fim=request.POST.get('horario_fim') if request.POST.get('horario_fim') else None,
                limite_uso_cliente_dia=int(request.POST.get('limite_uso_cliente_dia')) if request.POST.get('limite_uso_cliente_dia') else None,
                limite_uso_cliente_mes=int(request.POST.get('limite_uso_cliente_mes')) if request.POST.get('limite_uso_cliente_mes') else None,
                orcamento_mensal=Decimal(request.POST.get('orcamento_mensal')) if request.POST.get('orcamento_mensal') else None,
            )
            
            usuario_nome = getattr(request.portal_usuario, 'nome', None) or getattr(request.portal_usuario, 'username', 'N/A')
            registrar_log(
                'portais.lojista.cashback',
                f'Regra de cashback criada - ID: {regra.id}, Loja: {loja_id}, Nome: {regra.nome}, '
                f'Usuário: {usuario_nome}'
            )
            
            messages.success(request, f'Regra de cashback "{regra.nome}" criada com sucesso!')
            return redirect('lojista:cashback_detalhe', regra_id=regra.id)
            
        except Exception as e:
            registrar_log(
                'portais.lojista.cashback',
                f'Erro ao criar regra de cashback: {str(e)}',
                nivel='ERROR'
            )
            messages.error(request, f'Erro ao criar regra: {str(e)}')
            return redirect('lojista:cashback_lista')


class CashbackEditView(LojistaAccessMixin, LojistaDataMixin, View):
    """Editar regra de cashback"""
    
    def get(self, request, regra_id):
        from django.apps import apps
        RegraCashbackLoja = apps.get_model('cashback', 'RegraCashbackLoja')
        
        regra = get_object_or_404(RegraCashbackLoja, id=regra_id)
        
        # Validar acesso
        if regra.loja_id not in self.get_lojas_ids():
            messages.error(request, 'Você não tem permissão para editar esta regra')
            return redirect('lojista:cashback_lista')
        
        lojas_acessiveis = self.get_lojas_acessiveis()
        
        # Converter valores decimais para string com ponto (formato US)
        valor_concessao_str = str(regra.valor_concessao) if regra.valor_concessao is not None else ''
        valor_minimo_str = str(regra.valor_minimo_compra) if regra.valor_minimo_compra is not None else '0.00'
        valor_maximo_str = str(regra.valor_maximo_cashback) if regra.valor_maximo_cashback else ''
        
        context = {
            'regra': regra,
            'tipos_concessao': RegraCashbackLoja._meta.get_field('tipo_concessao').choices,
            'lojas_acessiveis': lojas_acessiveis,
            'valor_concessao_str': valor_concessao_str,
            'valor_minimo_str': valor_minimo_str,
            'valor_maximo_str': valor_maximo_str,
        }
        return render(request, 'portais/lojista/cashback/form.html', context)
    
    def post(self, request, regra_id):
        from django.apps import apps
        RegraCashbackLoja = apps.get_model('cashback', 'RegraCashbackLoja')
        
        try:
            regra = get_object_or_404(RegraCashbackLoja, id=regra_id)
            
            # Validar acesso
            if regra.loja_id not in self.get_lojas_ids():
                messages.error(request, 'Você não tem permissão para editar esta regra')
                return redirect('lojista:cashback_lista')
            
            # Atualizar campos
            regra.nome = request.POST.get('nome')
            regra.descricao = request.POST.get('descricao', '')
            regra.ativo = request.POST.get('ativo') == 'on'
            regra.prioridade = int(request.POST.get('prioridade', 0))
            regra.tipo_concessao = request.POST.get('tipo_concessao')
            regra.valor_concessao = Decimal(request.POST.get('valor_concessao'))
            regra.valor_minimo_compra = Decimal(request.POST.get('valor_minimo_compra', '0.00'))
            regra.valor_maximo_cashback = Decimal(request.POST.get('valor_maximo_cashback')) if request.POST.get('valor_maximo_cashback') else None
            regra.vigencia_inicio = datetime.strptime(request.POST.get('vigencia_inicio'), '%Y-%m-%dT%H:%M')
            regra.vigencia_fim = datetime.strptime(request.POST.get('vigencia_fim'), '%Y-%m-%dT%H:%M')
            regra.formas_pagamento = request.POST.getlist('formas_pagamento') if request.POST.getlist('formas_pagamento') else None
            regra.dias_semana = [int(d) for d in request.POST.getlist('dias_semana')] if request.POST.getlist('dias_semana') else None
            regra.horario_inicio = request.POST.get('horario_inicio') if request.POST.get('horario_inicio') else None
            regra.horario_fim = request.POST.get('horario_fim') if request.POST.get('horario_fim') else None
            regra.limite_uso_cliente_dia = int(request.POST.get('limite_uso_cliente_dia')) if request.POST.get('limite_uso_cliente_dia') else None
            regra.limite_uso_cliente_mes = int(request.POST.get('limite_uso_cliente_mes')) if request.POST.get('limite_uso_cliente_mes') else None
            regra.orcamento_mensal = Decimal(request.POST.get('orcamento_mensal')) if request.POST.get('orcamento_mensal') else None
            
            regra.save()
            
            usuario_nome = getattr(request.portal_usuario, 'nome', None) or getattr(request.portal_usuario, 'username', 'N/A')
            registrar_log(
                'portais.lojista.cashback',
                f'Regra de cashback editada - ID: {regra.id}, Nome: {regra.nome}, '
                f'Usuário: {usuario_nome}'
            )
            
            messages.success(request, f'Regra "{regra.nome}" atualizada com sucesso!')
            return redirect('lojista:cashback_detalhe', regra_id=regra.id)
            
        except Exception as e:
            registrar_log(
                'portais.lojista.cashback',
                f'Erro ao editar regra de cashback {regra_id}: {str(e)}',
                nivel='ERROR'
            )
            messages.error(request, f'Erro ao atualizar regra: {str(e)}')
            return redirect('lojista:cashback_lista')


class CashbackDetailView(LojistaAccessMixin, LojistaDataMixin, View):
    """Detalhes da regra de cashback"""
    
    def get(self, request, regra_id):
        from django.apps import apps
        RegraCashbackLoja = apps.get_model('cashback', 'RegraCashbackLoja')
        CashbackUso = apps.get_model('cashback', 'CashbackUso')
        
        regra = get_object_or_404(RegraCashbackLoja, id=regra_id)
        
        # Validar acesso
        if regra.loja_id not in self.get_lojas_ids():
            messages.error(request, 'Você não tem permissão para visualizar esta regra')
            return redirect('lojista:cashback_lista')
        
        # Estatísticas de uso
        usos = CashbackUso.objects.filter(regra_loja_id=regra.id)
        
        stats = {
            'total_usos': usos.count(),
            'valor_total': usos.aggregate(Sum('valor_cashback'))['valor_cashback__sum'] or Decimal('0.00'),
            'retidos': usos.filter(status='RETIDO').count(),
            'liberados': usos.filter(status='LIBERADO').count(),
            'expirados': usos.filter(status='EXPIRADO').count(),
            'estornados': usos.filter(status='ESTORNADO').count(),
        }
        
        # Últimos usos
        ultimos_usos = usos.order_by('-aplicado_em')[:10]
        
        context = {
            'regra': regra,
            'stats': stats,
            'ultimos_usos': ultimos_usos,
        }
        
        return render(request, 'portais/lojista/cashback/detalhe.html', context)


class CashbackToggleView(LojistaAccessMixin, LojistaDataMixin, View):
    """Ativar/Desativar regra de cashback"""
    
    def post(self, request, regra_id):
        from django.apps import apps
        RegraCashbackLoja = apps.get_model('cashback', 'RegraCashbackLoja')
        
        try:
            regra = get_object_or_404(RegraCashbackLoja, id=regra_id)
            
            # Validar acesso
            if regra.loja_id not in self.get_lojas_ids():
                messages.error(request, 'Você não tem permissão para modificar esta regra')
                return redirect('lojista:cashback_lista')
            
            regra.ativo = not regra.ativo
            regra.save()
            
            status = 'ativada' if regra.ativo else 'desativada'
            
            registrar_log(
                'portais.lojista.cashback',
                f'Regra de cashback {status} - ID: {regra.id}, Nome: {regra.nome}, '
                f'Usuário: {request.portal_usuario.nome}'
            )
            
            messages.success(request, f'Regra "{regra.nome}" {status} com sucesso!')
            return redirect('lojista:cashback_detalhe', regra_id=regra.id)
            
        except Exception as e:
            registrar_log(
                'portais.lojista.cashback',
                f'Erro ao alterar status da regra {regra_id}: {str(e)}',
                nivel='ERROR'
            )
            messages.error(request, f'Erro ao alterar status: {str(e)}')
            return redirect('lojista:cashback_lista')


class CashbackRelatorioView(LojistaAccessMixin, LojistaDataMixin, View):
    """Relatório de uso de cashback"""
    
    def get(self, request):
        from django.apps import apps
        CashbackUso = apps.get_model('cashback', 'CashbackUso')
        
        lojas_ids = self.get_lojas_ids()
        
        # Filtros
        regra_id = request.GET.get('regra_id', '')
        status = request.GET.get('status', '')
        data_inicio = request.GET.get('data_inicio', '')
        data_fim = request.GET.get('data_fim', '')
        
        # Query base
        usos = CashbackUso.objects.filter(
            tipo_origem='LOJA',
            loja_id__in=lojas_ids
        )
        
        # Aplicar filtros
        if regra_id:
            usos = usos.filter(regra_loja_id=regra_id)
        
        if status:
            usos = usos.filter(status=status)
        
        if data_inicio:
            usos = usos.filter(aplicado_em__gte=datetime.strptime(data_inicio, '%Y-%m-%d'))
        
        if data_fim:
            usos = usos.filter(aplicado_em__lte=datetime.strptime(data_fim, '%Y-%m-%d'))
        
        # Ordenar
        usos = usos.order_by('-aplicado_em')
        
        # Estatísticas
        stats = {
            'total_usos': usos.count(),
            'valor_total': usos.aggregate(Sum('valor_cashback'))['valor_cashback__sum'] or Decimal('0.00'),
            'por_status': {
                'retidos': usos.filter(status='RETIDO').aggregate(Sum('valor_cashback'))['valor_cashback__sum'] or Decimal('0.00'),
                'liberados': usos.filter(status='LIBERADO').aggregate(Sum('valor_cashback'))['valor_cashback__sum'] or Decimal('0.00'),
                'expirados': usos.filter(status='EXPIRADO').aggregate(Sum('valor_cashback'))['valor_cashback__sum'] or Decimal('0.00'),
                'estornados': usos.filter(status='ESTORNADO').aggregate(Sum('valor_cashback'))['valor_cashback__sum'] or Decimal('0.00'),
            }
        }
        
        # Paginação
        paginator = Paginator(usos, 50)
        page = request.GET.get('page', 1)
        usos_page = paginator.get_page(page)
        
        # Regras disponíveis para filtro
        regras = RegraCashbackLoja.objects.filter(loja_id__in=lojas_ids).order_by('nome')
        
        context = {
            'usos': usos_page,
            'stats': stats,
            'regras': regras,
            'regra_id': regra_id,
            'status': status,
            'data_inicio': data_inicio,
            'data_fim': data_fim,
        }
        
        return render(request, 'portais/lojista/cashback/relatorio.html', context)
