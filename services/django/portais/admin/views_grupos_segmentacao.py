from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.db import connection
from datetime import datetime

from portais.admin.decorators import admin_required
from django.apps import apps
from wallclub_core.estr_organizacional.canal import Canal
from wallclub_core.utilitarios.log_control import registrar_log


@admin_required
def grupos_list(request):
    """Lista todos os grupos de segmentação"""
    try:
        GrupoSegmentacao = apps.get_model('ofertas', 'GrupoSegmentacao')
        GrupoCliente = apps.get_model('ofertas', 'GrupoCliente')
        
        grupos = GrupoSegmentacao.objects.all().order_by('canal_id', 'nome')
        
        # Contar clientes por grupo
        grupos_com_total = []
        for grupo in grupos:
            total_clientes = GrupoCliente.objects.filter(grupo_id=grupo.id).count()
            grupos_com_total.append({
                'grupo': grupo,
                'total_clientes': total_clientes
            })
        
        context = {
            'grupos_com_total': grupos_com_total
        }
        
        return render(request, 'portais/admin/grupos_segmentacao_list.html', context)
        
    except Exception as e:
        registrar_log('portais.admin', f'Erro ao listar grupos: {str(e)}', nivel='ERROR')
        messages.error(request, 'Erro ao carregar grupos')
        return redirect('portais_admin:dashboard')


@admin_required
def grupos_create(request):
    """Cria novo grupo de segmentação"""
    if request.method == 'GET':
        # Buscar canais
        canais = Canal.listar_canais_ativos()
        
        context = {
            'canais': canais
        }
        return render(request, 'portais/admin/grupos_segmentacao_form.html', context)
    
    elif request.method == 'POST':
        try:
            GrupoSegmentacao = apps.get_model('ofertas', 'GrupoSegmentacao')
            
            nome = request.POST.get('nome')
            descricao = request.POST.get('descricao')
            canal_id = int(request.POST.get('canal_id'))
            criterio_tipo = request.POST.get('criterio_tipo', 'manual')
            ativo = request.POST.get('ativo') == 'on'
            
            # Validações
            if not nome or not canal_id:
                messages.error(request, 'Preencha os campos obrigatórios')
                return redirect('portais_admin:grupos_create')
            
            # Criar grupo
            grupo = GrupoSegmentacao(
                nome=nome,
                descricao=descricao,
                canal_id=canal_id,
                criterio_tipo=criterio_tipo,
                ativo=ativo,
                created_at=datetime.now()
            )
            grupo.save()
            
            messages.success(request, f'Grupo "{nome}" criado com sucesso!')
            return redirect('portais_admin:grupos_list')
            
        except Exception as e:
            registrar_log('portais.admin', f'Erro ao criar grupo: {str(e)}', nivel='ERROR')
            messages.error(request, 'Erro ao criar grupo')
            return redirect('portais_admin:grupos_create')


@admin_required
def grupos_edit(request, grupo_id):
    """Edita grupo de segmentação"""
    try:
        GrupoSegmentacao = apps.get_model('apps.ofertas', 'GrupoSegmentacao')
        
        grupo = GrupoSegmentacao.objects.filter(id=grupo_id).first()
        if not grupo:
            messages.error(request, 'Grupo não encontrado')
            return redirect('portais_admin:grupos_list')
        
        if request.method == 'GET':
            canais = Canal.listar_canais_ativos()
            
            context = {
                'grupo': grupo,
                'canais': canais
            }
            return render(request, 'portais/admin/grupos_segmentacao_form.html', context)
        
        elif request.method == 'POST':
            nome = request.POST.get('nome')
            descricao = request.POST.get('descricao')
            canal_id = int(request.POST.get('canal_id'))
            criterio_tipo = request.POST.get('criterio_tipo', 'manual')
            ativo = request.POST.get('ativo') == 'on'
            
            # Validações
            if not nome or not canal_id:
                messages.error(request, 'Preencha os campos obrigatórios')
                return redirect('portais_admin:grupos_edit', grupo_id=grupo_id)
            
            # Atualizar
            grupo.nome = nome
            grupo.descricao = descricao
            grupo.canal_id = canal_id
            grupo.criterio_tipo = criterio_tipo
            grupo.ativo = ativo
            grupo.updated_at = datetime.now()
            grupo.save()
            
            messages.success(request, 'Grupo atualizado com sucesso!')
            return redirect('portais_admin:grupos_list')
            
    except Exception as e:
        registrar_log('portais.admin', f'Erro ao editar grupo: {str(e)}', nivel='ERROR')
        messages.error(request, 'Erro ao editar grupo')
        return redirect('portais_admin:grupos_list')


@admin_required
def grupos_clientes(request, grupo_id):
    """Gerencia clientes do grupo"""
    try:
        GrupoSegmentacao = apps.get_model('ofertas', 'GrupoSegmentacao')
        GrupoCliente = apps.get_model('ofertas', 'GrupoCliente')
        Cliente = apps.get_model('cliente', 'Cliente')
        
        grupo = GrupoSegmentacao.objects.filter(id=grupo_id).first()
        if not grupo:
            messages.error(request, 'Grupo não encontrado')
            return redirect('portais_admin:grupos_list')
        
        # Buscar clientes do grupo
        vinculos = GrupoCliente.objects.filter(grupo_id=grupo_id).order_by('-adicionado_em')
        
        # Buscar dados dos clientes
        clientes_grupo = []
        for vinculo in vinculos:
            cliente = Cliente.objects.filter(id=vinculo.cliente_id).first()
            if cliente:
                clientes_grupo.append({
                    'vinculo': vinculo,
                    'cliente': cliente
                })
        
        # Buscar clientes disponíveis do canal (para adicionar)
        clientes_no_grupo = [v.cliente_id for v in vinculos]
        clientes_disponiveis = Cliente.objects.filter(
            canal_id=grupo.canal_id,
            ativo=True
        ).exclude(id__in=clientes_no_grupo).order_by('nome')[:100]  # Limitar 100
        
        context = {
            'grupo': grupo,
            'clientes_grupo': clientes_grupo,
            'clientes_disponiveis': clientes_disponiveis,
            'total_clientes': len(clientes_grupo)
        }
        
        return render(request, 'portais/admin/grupos_segmentacao_clientes.html', context)
        
    except Exception as e:
        registrar_log('portais.admin', f'Erro ao gerenciar clientes: {str(e)}', nivel='ERROR')
        messages.error(request, 'Erro ao carregar clientes')
        return redirect('portais_admin:grupos_list')


@admin_required
def grupos_adicionar_cliente(request, grupo_id):
    """Adiciona cliente ao grupo (AJAX)"""
    if request.method == 'POST':
        try:
            GrupoCliente = apps.get_model('ofertas', 'GrupoCliente')
            
            import json
            data = json.loads(request.body)
            cliente_id = int(data.get('cliente_id'))
            
            # Verificar se já existe
            existe = GrupoCliente.objects.filter(grupo_id=grupo_id, cliente_id=cliente_id).first()
            if existe:
                return JsonResponse({'sucesso': False, 'mensagem': 'Cliente já está no grupo'}, status=400)
            
            # Adicionar
            vinculo = GrupoCliente(
                grupo_id=grupo_id,
                cliente_id=cliente_id,
                adicionado_em=datetime.now()
            )
            vinculo.save()
            
            return JsonResponse({'sucesso': True, 'mensagem': 'Cliente adicionado'})
            
        except Exception as e:
            registrar_log('portais.admin', f'Erro ao adicionar cliente: {str(e)}', nivel='ERROR')
            return JsonResponse({'sucesso': False, 'mensagem': str(e)}, status=500)
    
    return JsonResponse({'sucesso': False}, status=405)


@admin_required
def grupos_remover_cliente(request, grupo_id, cliente_id):
    """Remove cliente do grupo (AJAX)"""
    if request.method == 'POST':
        try:
            GrupoCliente = apps.get_model('ofertas', 'GrupoCliente')
            
            vinculo = GrupoCliente.objects.filter(grupo_id=grupo_id, cliente_id=cliente_id).first()
            if not vinculo:
                return JsonResponse({'sucesso': False, 'mensagem': 'Vínculo não encontrado'}, status=404)
            
            vinculo.delete()
            
            return JsonResponse({'sucesso': True, 'mensagem': 'Cliente removido'})
            
        except Exception as e:
            registrar_log('portais.admin', f'Erro ao remover cliente: {str(e)}', nivel='ERROR')
            return JsonResponse({'sucesso': False, 'mensagem': str(e)}, status=500)
    
    return JsonResponse({'sucesso': False}, status=405)
