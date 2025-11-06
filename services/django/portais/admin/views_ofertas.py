from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views import View
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
import json

from portais.admin.decorators import admin_required
from wallclub_core.integracoes.ofertas_api_client import ofertas_api
from wallclub_core.utilitarios.log_control import registrar_log
from wallclub_core.estr_organizacional.canal import Canal


@admin_required
def ofertas_list(request):
    """Lista todas as ofertas do sistema via API interna"""
    try:
        # Buscar todas as ofertas via API
        response = ofertas_api.listar_ofertas()
        
        if not response.get('sucesso'):
            messages.error(request, response.get('mensagem', 'Erro ao carregar ofertas'))
            return redirect('portais_admin:dashboard')
        
        ofertas = response.get('ofertas', [])
        
        # Converter dicts para objetos-like (para compatibilidade com template)
        class OfertaObj:
            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)
        
        ofertas_com_disparos = []
        for oferta_data in ofertas:
            # Formatar datas para exibição (remover segundos da string ISO)
            if 'vigencia_inicio' in oferta_data and oferta_data['vigencia_inicio']:
                oferta_data['vigencia_inicio_formatted'] = oferta_data['vigencia_inicio'][:16]
            if 'vigencia_fim' in oferta_data and oferta_data['vigencia_fim']:
                oferta_data['vigencia_fim_formatted'] = oferta_data['vigencia_fim'][:16]
            
            oferta_obj = OfertaObj(oferta_data)
            ofertas_com_disparos.append({
                'oferta': oferta_obj,
                'total_disparos': 0,  # TODO: API de disparos
                'ultimo_disparo': None
            })
        
        context = {
            'ofertas_com_disparos': ofertas_com_disparos,
        }
        
        return render(request, 'portais/admin/ofertas_list.html', context)
        
    except Exception as e:
        registrar_log('portais.admin', f'Erro ao listar ofertas: {str(e)}', nivel='ERROR')
        messages.error(request, 'Erro ao carregar ofertas')
        return redirect('portais_admin:dashboard')


@admin_required
def ofertas_create(request):
    """Cria nova oferta via API interna"""
    if request.method == 'GET':
        # Buscar canais da estrutura organizacional
        canais = Canal.listar_canais_ativos()
        
        # Buscar grupos de segmentação via API
        response = ofertas_api.listar_grupos()
        grupos = response.get('grupos', []) if response.get('sucesso') else []
        
        # Converter para objetos
        class GrupoObj:
            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)
        
        grupos = [GrupoObj(g) for g in grupos]
        
        context = {
            'canais': canais,
            'grupos': grupos
        }
        return render(request, 'portais/admin/ofertas_form.html', context)
    
    elif request.method == 'POST':
        try:
            # Extrair dados do formulário
            titulo = request.POST.get('titulo')
            texto_push = request.POST.get('texto_push')
            descricao = request.POST.get('descricao')
            
            # Processar upload de imagem
            imagem_url = None
            if 'imagem' in request.FILES:
                from django.core.files.storage import default_storage
                import os
                from pathlib import Path
                
                # Criar pasta ofertas se não existir
                pasta_ofertas = Path(settings.MEDIA_ROOT) / 'ofertas'
                pasta_ofertas.mkdir(parents=True, exist_ok=True)
                
                imagem = request.FILES['imagem']
                ext = os.path.splitext(imagem.name)[1]
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                # Incluir ID temporário (será atualizado após criação)
                nome_arquivo = f'ofertas/temp_{timestamp}_{imagem.name}'
                
                caminho = default_storage.save(nome_arquivo, imagem)
                imagem_url = f'https://apidj.wallclub.com.br/media/{caminho}'
            
            vigencia_inicio_str = request.POST.get('vigencia_inicio')
            vigencia_fim_str = request.POST.get('vigencia_fim')
            canal_id = int(request.POST.get('canal_id'))
            tipo_segmentacao = request.POST.get('tipo_segmentacao', 'todos_canal')
            grupo_id = request.POST.get('grupo_id')
            ativo = request.POST.get('ativo') == 'on'
            
            # Validações básicas
            if not titulo or not texto_push or not vigencia_inicio_str or not vigencia_fim_str or not canal_id:
                messages.error(request, 'Preencha todos os campos obrigatórios')
                return redirect('portais_admin:ofertas_create')
            
            # Converter datas
            vigencia_inicio = datetime.strptime(vigencia_inicio_str, '%Y-%m-%dT%H:%M')
            vigencia_fim = datetime.strptime(vigencia_fim_str, '%Y-%m-%dT%H:%M')
            
            if vigencia_fim <= vigencia_inicio:
                messages.error(request, 'Data fim deve ser posterior à data início')
                return redirect('portais_admin:ofertas_create')
            
            # Validar segmentação
            if tipo_segmentacao == 'grupo_customizado' and not grupo_id:
                messages.error(request, 'Selecione um grupo para segmentação customizada')
                return redirect('portais_admin:ofertas_create')
            
            # Criar oferta via API
            usuario_id = request.session.get('portal_usuario_id')
            
            dados = {
                'titulo': titulo,
                'texto_push': texto_push,
                'descricao': descricao,
                'imagem_url': imagem_url,
                'vigencia_inicio': vigencia_inicio.isoformat(),
                'vigencia_fim': vigencia_fim.isoformat(),
                'canal_id': canal_id,
                'tipo_segmentacao': tipo_segmentacao,
                'grupo_id': int(grupo_id) if grupo_id else None,
                'usuario_criador_id': usuario_id,
                'ativo': ativo
            }
            
            response = ofertas_api.criar_oferta(dados)
            
            if response.get('sucesso'):
                oferta_id = response.get('oferta_id')
                
                # Renomear arquivo com ID da oferta
                if imagem_url and oferta_id:
                    try:
                        import shutil
                        from pathlib import Path
                        
                        # Caminho antigo (temp)
                        caminho_antigo = Path(settings.MEDIA_ROOT) / caminho
                        
                        # Novo nome com ID da oferta
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        nome_final = f'ofertas/oferta_{oferta_id}_{timestamp}_{imagem.name}'
                        caminho_novo = Path(settings.MEDIA_ROOT) / nome_final
                        
                        # Renomear arquivo
                        if caminho_antigo.exists():
                            shutil.move(str(caminho_antigo), str(caminho_novo))
                            
                            # Atualizar URL via API
                            ofertas_api.atualizar_oferta(oferta_id, {
                                'imagem_url': f'https://apidj.wallclub.com.br/media/{nome_final}'
                            })
                            
                            registrar_log('portais.admin', f'Imagem renomeada: {nome_final}')
                    except Exception as e:
                        registrar_log('portais.admin', f'Erro ao renomear imagem: {str(e)}', nivel='ERROR')
                
                messages.success(request, response.get('mensagem', 'Oferta criada com sucesso'))
                return redirect('portais_admin:ofertas_list')
            else:
                messages.error(request, response.get('mensagem', 'Erro ao criar oferta'))
                return redirect('portais_admin:ofertas_create')
            
        except Exception as e:
            registrar_log('portais.admin', f'Erro ao criar oferta: {str(e)}', nivel='ERROR')
            messages.error(request, 'Erro ao criar oferta')
            return redirect('portais_admin:ofertas_create')


@admin_required
def ofertas_edit(request, oferta_id):
    """Edita oferta existente via API interna"""
    try:
        # Buscar oferta via API
        response = ofertas_api.obter_oferta(oferta_id)
        
        if not response.get('sucesso'):
            messages.error(request, 'Oferta não encontrada')
            return redirect('portais_admin:ofertas_list')
        
        oferta_data = response.get('oferta', {})
        
        # Converter para objeto
        class OfertaObj:
            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)
        
        oferta = OfertaObj(oferta_data)
        
        # Formatar datas para input datetime-local (formato: 2025-10-12T06:48)
        vigencia_inicio_formatted = None
        vigencia_fim_formatted = None
        
        if oferta.vigencia_inicio:
            # Remover segundos e timezone da string ISO
            vigencia_inicio_formatted = oferta.vigencia_inicio[:16]  # "2025-10-12T06:48:00" -> "2025-10-12T06:48"
        
        if oferta.vigencia_fim:
            vigencia_fim_formatted = oferta.vigencia_fim[:16]
        
        if request.method == 'GET':
            # Buscar grupos via API
            grupos_response = ofertas_api.listar_grupos()
            grupos = grupos_response.get('grupos', []) if grupos_response.get('sucesso') else []
            
            class GrupoObj:
                def __init__(self, data):
                    for key, value in data.items():
                        setattr(self, key, value)
            
            grupos = [GrupoObj(g) for g in grupos]
            
            context = {
                'oferta': oferta,
                'grupos': grupos,
                'vigencia_inicio_formatted': vigencia_inicio_formatted,
                'vigencia_fim_formatted': vigencia_fim_formatted
            }
            return render(request, 'portais/admin/ofertas_form.html', context)
        
        elif request.method == 'POST':
            # Extrair dados
            titulo = request.POST.get('titulo')
            texto_push = request.POST.get('texto_push')
            descricao = request.POST.get('descricao')
            
            # Processar upload de imagem
            imagem_url = oferta.imagem_url
            if 'imagem' in request.FILES:
                from django.core.files.storage import default_storage
                import os
                from pathlib import Path
                
                # Criar pasta ofertas se não existir
                pasta_ofertas = Path(settings.MEDIA_ROOT) / 'ofertas'
                pasta_ofertas.mkdir(parents=True, exist_ok=True)
                
                imagem = request.FILES['imagem']
                ext = os.path.splitext(imagem.name)[1]
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                # Incluir ID da oferta no nome
                nome_arquivo = f'ofertas/oferta_{oferta_id}_{timestamp}_{imagem.name}'
                
                caminho = default_storage.save(nome_arquivo, imagem)
                imagem_url = f'https://apidj.wallclub.com.br/media/{caminho}'
            
            vigencia_inicio_str = request.POST.get('vigencia_inicio')
            vigencia_fim_str = request.POST.get('vigencia_fim')
            tipo_segmentacao = request.POST.get('tipo_segmentacao', 'todos_canal')
            grupo_id = request.POST.get('grupo_id')
            ativo = request.POST.get('ativo') == 'on'
            
            # Validações
            if not titulo or not texto_push or not vigencia_inicio_str or not vigencia_fim_str:
                messages.error(request, 'Preencha todos os campos obrigatórios')
                return redirect('portais_admin:ofertas_edit', oferta_id=oferta_id)
            
            # Converter datas
            vigencia_inicio = datetime.strptime(vigencia_inicio_str, '%Y-%m-%dT%H:%M')
            vigencia_fim = datetime.strptime(vigencia_fim_str, '%Y-%m-%dT%H:%M')
            
            if vigencia_fim <= vigencia_inicio:
                messages.error(request, 'Data fim deve ser posterior à data início')
                return redirect('portais_admin:ofertas_edit', oferta_id=oferta_id)
            
            if tipo_segmentacao == 'grupo_customizado' and not grupo_id:
                messages.error(request, 'Selecione um grupo para segmentação customizada')
                return redirect('portais_admin:ofertas_edit', oferta_id=oferta_id)
            
            # Atualizar oferta via API
            dados_atualizacao = {
                'titulo': titulo,
                'texto_push': texto_push,
                'descricao': descricao,
                'imagem_url': imagem_url,
                'vigencia_inicio': vigencia_inicio.isoformat(),
                'vigencia_fim': vigencia_fim.isoformat(),
                'tipo_segmentacao': tipo_segmentacao,
                'grupo_id': int(grupo_id) if grupo_id else None,
                'ativo': ativo
            }
            
            response = ofertas_api.atualizar_oferta(oferta_id, dados_atualizacao)
            
            if response.get('sucesso'):
                messages.success(request, 'Oferta atualizada com sucesso!')
                return redirect('portais_admin:ofertas_list')
            else:
                messages.error(request, response.get('mensagem', 'Erro ao atualizar oferta'))
                return redirect('portais_admin:ofertas_edit', oferta_id=oferta_id)
            
    except Exception as e:
        registrar_log('portais.admin', f'Erro ao editar oferta: {str(e)}', nivel='ERROR')
        messages.error(request, 'Erro ao editar oferta')
        return redirect('portais_admin:ofertas_list')


@csrf_exempt
def ofertas_disparar(request, oferta_id):
    """Dispara push notification para oferta (AJAX)"""
    # Verificar autenticação manualmente (não usar @admin_required em AJAX)
    usuario_id = request.session.get('portal_usuario_id')
    if not usuario_id:
        return JsonResponse({
            'sucesso': False,
            'mensagem': 'Sessão expirada. Por favor, faça login novamente.',
            'redirect': '/portal_admin/'
        }, status=401)
    
    # Verificar permissão admin
    try:
        from portais.controle_acesso.models import PortalUsuario
        from portais.controle_acesso.services import ControleAcessoService
        
        usuario = PortalUsuario.objects.get(id=usuario_id, ativo=True)
        nivel_acesso = ControleAcessoService.obter_nivel_portal(usuario, 'admin')
        
        if nivel_acesso == 'negado':
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'Acesso negado. Permissões insuficientes.'
            }, status=403)
    except PortalUsuario.DoesNotExist:
        return JsonResponse({
            'sucesso': False,
            'mensagem': 'Sessão inválida. Faça login novamente.',
            'redirect': '/portal_admin/'
        }, status=401)
    
    if request.method == 'POST':
        try:
            # Verificar se oferta existe via API
            response = ofertas_api.obter_oferta(oferta_id)
            if not response.get('sucesso'):
                return JsonResponse({
                    'sucesso': False,
                    'mensagem': 'Oferta não encontrada'
                }, status=404)
            
            # Disparar push via service (mantém local - push não é API)
            from apps.ofertas.services import OfertaService
            sucesso, mensagem, disparo_id = OfertaService.disparar_push(
                oferta_id=oferta_id,
                usuario_disparador_id=usuario_id
            )
            
            if sucesso:
                return JsonResponse({
                    'sucesso': True,
                    'mensagem': mensagem,
                    'disparo_id': disparo_id
                })
            else:
                return JsonResponse({
                    'sucesso': False,
                    'mensagem': mensagem
                }, status=400)
                
        except Exception as e:
            registrar_log('portais.admin', f'Erro ao disparar oferta: {str(e)}', nivel='ERROR')
            return JsonResponse({
                'sucesso': False,
                'mensagem': f'Erro ao disparar push: {str(e)}'
            }, status=500)
    
    return JsonResponse({'sucesso': False, 'mensagem': 'Método não permitido'}, status=405)


@admin_required
def ofertas_historico(request, oferta_id):
    """Histórico de disparos da oferta"""
    try:
        # Buscar oferta via API
        response = ofertas_api.obter_oferta(oferta_id)
        
        if not response.get('sucesso'):
            messages.error(request, 'Oferta não encontrada')
            return redirect('portais_admin:ofertas_list')
        
        # Converter para objeto
        class OfertaObj:
            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)
        
        oferta = OfertaObj(response.get('oferta', {}))
        
        # Buscar disparos via service (mantém local - histórico não é API ainda)
        from apps.ofertas.services import OfertaService
        disparos = OfertaService.listar_disparos_oferta(oferta_id)
        
        context = {
            'oferta': oferta,
            'disparos': disparos
        }
        
        return render(request, 'portais/admin/ofertas_historico.html', context)
        
    except Exception as e:
        registrar_log('portais.admin', f'Erro ao buscar histórico: {str(e)}', nivel='ERROR')
        messages.error(request, 'Erro ao carregar histórico')
        return redirect('portais_admin:ofertas_list')
