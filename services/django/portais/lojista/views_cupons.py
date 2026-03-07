"""
Views para gerenciamento de cupons no portal lojista
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone
from django.views import View
from datetime import datetime, timedelta
from decimal import Decimal
from .mixins import LojistaAccessMixin, LojistaDataMixin
from apps.cupom.models import Cupom, CupomUso
from wallclub_core.utilitarios.log_control import registrar_log


class CupomListView(LojistaAccessMixin, LojistaDataMixin, View):
    """Lista de cupons da loja"""

    def get(self, request):
        lojas_ids = self.get_lojas_ids()

        # Filtros
        busca = request.GET.get('busca', '')
        status = request.GET.get('status', '')

        # Query base
        cupons = Cupom.objects.filter(loja_id__in=lojas_ids)

        # Aplicar filtros
        if busca:
            cupons = cupons.filter(
                Q(codigo__icontains=busca) |
                Q(nome__icontains=busca)
            )

        if status == 'ativo':
            cupons = cupons.filter(ativo=True)
        elif status == 'inativo':
            cupons = cupons.filter(ativo=False)
        elif status == 'vigente':
            agora = timezone.now()
            cupons = cupons.filter(
                ativo=True,
                data_inicio__lte=agora,
                data_fim__gte=agora
            )
        elif status == 'expirado':
            cupons = cupons.filter(data_fim__lt=timezone.now())

        # Ordenar
        cupons = cupons.order_by('-created_at')

        # Estatísticas (antes da paginação)
        total_cupons = Cupom.objects.filter(loja_id__in=lojas_ids)
        stats = {
            'total': total_cupons.count(),
            'ativos': total_cupons.filter(ativo=True).count(),
            'vigentes': total_cupons.filter(
                ativo=True,
                data_inicio__lte=timezone.now(),
                data_fim__gte=timezone.now()
            ).count(),
        }

        # Paginação
        paginator = Paginator(cupons, 20)
        page = request.GET.get('page', 1)
        cupons_page = paginator.get_page(page)


        context = {
            'cupons': cupons_page,
            'stats': stats,
            'busca': busca,
            'status': status,
        }

        return render(request, 'portais/lojista/cupons/lista.html', context)


class CupomCreateView(LojistaAccessMixin, LojistaDataMixin, View):
    """Criar novo cupom"""

    def get(self, request):
        lojas_acessiveis = self.get_lojas_acessiveis()
        loja_id_atual = request.session.get('loja_id')

        # Se não tem loja na sessão mas tem apenas uma loja acessível, usar essa
        if not loja_id_atual and len(lojas_acessiveis) == 1:
            loja_id_atual = lojas_acessiveis[0]['id']

        context = {
            'tipos_cupom': Cupom._meta.get_field('tipo_cupom').choices,
            'tipos_desconto': Cupom._meta.get_field('tipo_desconto').choices,
            'lojas_acessiveis': lojas_acessiveis,
            'loja_id_atual': loja_id_atual,
        }
        return render(request, 'portais/lojista/cupons/form.html', context)

    def post(self, request):
        try:
            # Pegar loja_id do formulário ou da sessão
            loja_id_raw = request.POST.get('loja_id', '').strip()
            if loja_id_raw and loja_id_raw != 'None':
                loja_id = int(loja_id_raw)
            else:
                loja_id = request.session.get('loja_id')

            # Validar se loja_id existe
            if not loja_id:
                messages.error(request, 'Loja não identificada. Faça login novamente.')
                return redirect('lojista:home')

            # Validar código único
            codigo = request.POST.get('codigo', '').strip().upper()
            if Cupom.objects.filter(codigo=codigo).exists():
                messages.error(request, f'Código "{codigo}" já está em uso')
                return redirect('lojista:cupom_create')

            # Criar cupom
            cliente_id_raw = request.POST.get('cliente_id', '').strip()
            cliente_id = int(cliente_id_raw) if cliente_id_raw and cliente_id_raw != 'None' else None

            cupom = Cupom.objects.create(
                loja_id=int(loja_id),
                codigo=codigo,
                tipo_cupom=request.POST.get('tipo_cupom'),
                tipo_desconto=request.POST.get('tipo_desconto'),
                valor_desconto=Decimal(request.POST.get('valor_desconto')),
                valor_minimo_compra=Decimal(request.POST.get('valor_minimo_compra', 0)),
                limite_uso_total=int(request.POST.get('limite_uso_total')) if request.POST.get('limite_uso_total') else None,
                limite_uso_por_cpf=int(request.POST.get('limite_uso_por_cpf', 1)),
                cliente_id=cliente_id,
                data_inicio=datetime.strptime(request.POST.get('data_inicio'), '%Y-%m-%dT%H:%M'),
                data_fim=datetime.strptime(request.POST.get('data_fim'), '%Y-%m-%dT%H:%M'),
                ativo=request.POST.get('ativo') == 'on'
            )

            registrar_log('portais.lojista', f'Cupom criado: {codigo} - Loja {loja_id}')
            messages.success(request, f'Cupom "{codigo}" criado com sucesso!')
            return redirect('lojista:cupom_detail', cupom_id=cupom.id)

        except Exception as e:
            registrar_log('portais.lojista', f'Erro ao criar cupom: {e}', nivel='ERROR')
            messages.error(request, f'Erro ao criar cupom: {str(e)}')
            return redirect('lojista:cupom_create')


class CupomDetailView(LojistaAccessMixin, LojistaDataMixin, View):
    """Detalhes do cupom"""

    def get(self, request, cupom_id):
        lojas_ids = self.get_lojas_ids()
        cupom = get_object_or_404(Cupom, id=cupom_id, loja_id__in=lojas_ids)

        # Estatísticas de uso
        usos = CupomUso.objects.filter(cupom_id=cupom.id)

        stats = {
            'total_usos': cupom.quantidade_usada,
            'total_desconto': usos.aggregate(Sum('valor_desconto_aplicado'))['valor_desconto_aplicado__sum'] or Decimal('0'),
            'usos_estornados': usos.filter(estornado=True).count(),
            'clientes_unicos': usos.values('cliente_id').distinct().count(),
        }

        # Últimos usos
        ultimos_usos = usos.order_by('-usado_em')[:10]

        # Status do cupom
        agora = timezone.now()
        if not cupom.ativo:
            status = 'inativo'
        elif agora < cupom.data_inicio:
            status = 'aguardando'
        elif agora > cupom.data_fim:
            status = 'expirado'
        elif cupom.limite_uso_total and cupom.quantidade_usada >= cupom.limite_uso_total:
            status = 'esgotado'
        else:
            status = 'vigente'

        context = {
            'cupom': cupom,
            'stats': stats,
            'ultimos_usos': ultimos_usos,
            'status': status,
        }

        return render(request, 'portais/lojista/cupons/detalhe.html', context)


class CupomEditView(LojistaAccessMixin, LojistaDataMixin, View):
    """Editar cupom"""

    def get(self, request, cupom_id):
        lojas_ids = self.get_lojas_ids()
        cupom = get_object_or_404(Cupom, id=cupom_id, loja_id__in=lojas_ids)

        lojas_acessiveis = self.get_lojas_acessiveis()

        # Verificar se cupom já foi usado
        from apps.cupom.models import CupomUso
        cupom_foi_usado = CupomUso.objects.filter(cupom_id=cupom.id).exists()

        context = {
            'cupom': cupom,
            'tipos_cupom': Cupom._meta.get_field('tipo_cupom').choices,
            'tipos_desconto': Cupom._meta.get_field('tipo_desconto').choices,
            'lojas_acessiveis': lojas_acessiveis,
            'loja_id_atual': cupom.loja_id,  # Usar loja do cupom, não da sessão
            'cupom_foi_usado': cupom_foi_usado,
        }
        return render(request, 'portais/lojista/cupons/form.html', context)

    def post(self, request, cupom_id):
        try:
            lojas_ids = self.get_lojas_ids()
            cupom = get_object_or_404(Cupom, id=cupom_id, loja_id__in=lojas_ids)

            # Verificar se cupom já foi usado
            from apps.cupom.models import CupomUso
            cupom_foi_usado = CupomUso.objects.filter(cupom_id=cupom.id).exists()

            if cupom_foi_usado:
                # Se já foi usado, permitir apenas alterar data_fim e ativo
                cupom.data_fim = datetime.strptime(request.POST.get('data_fim'), '%Y-%m-%dT%H:%M')
                cupom.ativo = request.POST.get('ativo') == 'on'
                cupom.save(update_fields=['data_fim', 'ativo'])
                registrar_log('portais.lojista', f'Cupom encerrado: {cupom.codigo} - Nova data_fim: {cupom.data_fim}')
                messages.success(request, f'Cupom "{cupom.codigo}" atualizado (apenas data de encerramento).')
            else:
                # Se não foi usado, permitir edição completa
                cliente_id_raw = request.POST.get('cliente_id', '').strip()
                cliente_id = int(cliente_id_raw) if cliente_id_raw and cliente_id_raw != 'None' else None

                cupom.tipo_cupom = request.POST.get('tipo_cupom')
                cupom.tipo_desconto = request.POST.get('tipo_desconto')
                cupom.valor_desconto = Decimal(request.POST.get('valor_desconto'))
                cupom.valor_minimo_compra = Decimal(request.POST.get('valor_minimo_compra', 0))
                cupom.limite_uso_total = int(request.POST.get('limite_uso_total')) if request.POST.get('limite_uso_total') else None
                cupom.limite_uso_por_cpf = int(request.POST.get('limite_uso_por_cpf', 1))
                cupom.cliente_id = cliente_id
                cupom.data_inicio = datetime.strptime(request.POST.get('data_inicio'), '%Y-%m-%dT%H:%M')
                cupom.data_fim = datetime.strptime(request.POST.get('data_fim'), '%Y-%m-%dT%H:%M')
                cupom.ativo = request.POST.get('ativo') == 'on'
                cupom.save()
                registrar_log('portais.lojista', f'Cupom atualizado: {cupom.codigo} - Loja {cupom.loja_id}')
                messages.success(request, f'Cupom "{cupom.codigo}" atualizado com sucesso!')

            return redirect('lojista:cupom_detail', cupom_id=cupom.id)

        except Exception as e:
            registrar_log('portais.lojista', f'Erro ao atualizar cupom: {e}', nivel='ERROR')
            messages.error(request, f'Erro ao atualizar cupom: {str(e)}')
            return redirect('lojista:cupom_edit', cupom_id=cupom_id)


class CupomToggleView(LojistaAccessMixin, LojistaDataMixin, View):
    """Ativar/Desativar cupom"""

    def post(self, request, cupom_id):
        try:
            lojas_ids = self.get_lojas_ids()
            cupom = get_object_or_404(Cupom, id=cupom_id, loja_id__in=lojas_ids)

            cupom.ativo = not cupom.ativo
            cupom.save()

            status = 'ativado' if cupom.ativo else 'desativado'
            registrar_log('portais.lojista', f'Cupom {status}: {cupom.codigo} - Loja {cupom.loja_id}')
            messages.success(request, f'Cupom "{cupom.codigo}" {status} com sucesso!')

        except Exception as e:
            registrar_log('portais.lojista', f'Erro ao alterar status do cupom: {e}', nivel='ERROR')
            messages.error(request, f'Erro ao alterar status: {str(e)}')

        return redirect('lojista:cupom_detail', cupom_id=cupom_id)


class CupomRelatorioView(LojistaAccessMixin, LojistaDataMixin, View):
    """Relatório de uso de cupons"""

    def get(self, request):
        lojas_ids = self.get_lojas_ids()

        # Filtros de data
        data_inicio = request.GET.get('data_inicio')
        data_fim = request.GET.get('data_fim')

        if not data_inicio:
            data_inicio = (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not data_fim:
            data_fim = timezone.now().strftime('%Y-%m-%d')

        # Usos no período
        usos = CupomUso.objects.filter(
            loja_id__in=lojas_ids,
            usado_em__date__gte=data_inicio,
            usado_em__date__lte=data_fim
        )

        # Estatísticas
        stats = {
            'total_usos': usos.count(),
            'total_desconto': usos.aggregate(Sum('valor_desconto_aplicado'))['valor_desconto_aplicado__sum'] or Decimal('0'),
            'ticket_medio': usos.aggregate(Avg('valor_transacao_original'))['valor_transacao_original__avg'] or Decimal('0'),
            'cupons_ativos': Cupom.objects.filter(loja_id__in=lojas_ids, ativo=True).count(),
        }

        # Ranking de cupons
        ranking = usos.values('cupom_id').annotate(
            total_usos=Count('id'),
            total_desconto=Sum('valor_desconto_aplicado')
        ).order_by('-total_usos')[:10]

        # Adicionar código do cupom
        for item in ranking:
            cupom = Cupom.objects.get(id=item['cupom_id'])
            item['codigo'] = cupom.codigo

        context = {
            'stats': stats,
            'ranking': ranking,
            'data_inicio': data_inicio,
            'data_fim': data_fim,
        }

        return render(request, 'portais/lojista/cupons/relatorio.html', context)
