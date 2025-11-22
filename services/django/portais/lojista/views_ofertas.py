from django.shortcuts import render, redirect
from django.contrib import messages
from django.views import View
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from datetime import datetime
import json

from .mixins import LojistaAuthMixin, LojistaDataMixin
from wallclub_core.integracoes.ofertas_api_client import ofertas_api
from wallclub_core.utilitarios.log_control import registrar_log


class OfertasListView(LojistaAuthMixin, View):
    """Lista ofertas da loja/grupo econômico do usuário"""
    
    def get(self, request):
        try:
            from apps.ofertas.services import OfertaService
            
            # Buscar canal_id da sessão
            canal_id = request.session.get('canal_id')
            
            if not canal_id:
                messages.error(request, 'Canal não identificado')
                return redirect('lojista:home')
            
            # Buscar ofertas do canal via service
            todas_ofertas = OfertaService.listar_todas_ofertas()
            ofertas = [o for o in todas_ofertas if o.canal_id == canal_id]
            
            # Buscar total de disparos por oferta via service
            ofertas_com_disparos = []
            for oferta in ofertas:
                disparos = OfertaService.listar_disparos_oferta(oferta.id)
                ultimo_disparo = disparos[0] if disparos else None
                
                ofertas_com_disparos.append({
                    'oferta': oferta,
                    'total_disparos': len(disparos),
                    'ultimo_disparo': ultimo_disparo
                })
            
            context = {
                'current_page': 'ofertas',
                'ofertas_com_disparos': ofertas_com_disparos,
                'canal_id': canal_id
            }
            
            return render(request, 'portais/lojista/ofertas/list.html', context)
            
        except Exception as e:
            registrar_log('portais.lojista', f'Erro ao listar ofertas: {str(e)}', nivel='ERROR')
            messages.error(request, 'Erro ao carregar ofertas')
            return redirect('lojista:home')


class OfertasCreateView(LojistaAuthMixin, View):
    """Cria nova oferta"""
    
    def get(self, request):
        from apps.ofertas.services import OfertaService
        
        # Buscar grupos do canal para dropdown via service
        canal_id = request.session.get('canal_id')
        grupos = OfertaService.listar_grupos_segmentacao(canal_id=canal_id, apenas_ativos=True) if canal_id else []
        
        context = {
            'current_page': 'ofertas',
            'grupos': grupos
        }
        return render(request, 'portais/lojista/ofertas/form.html', context)
    
    def post(self, request):
        try:
            from apps.ofertas.services import OfertaService
            
            # Extrair dados do formulário
            titulo = request.POST.get('titulo')
            texto_push = request.POST.get('texto_push')
            descricao = request.POST.get('descricao')
            
            # Processar upload de imagem
            imagem_url = None
            if 'imagem' in request.FILES:
                from django.core.files.storage import default_storage
                import os
                from datetime import datetime
                
                imagem = request.FILES['imagem']
                # Gerar nome único para arquivo
                ext = os.path.splitext(imagem.name)[1]
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                nome_arquivo = f'ofertas/{timestamp}_{imagem.name}'
                
                # Salvar arquivo
                caminho = default_storage.save(nome_arquivo, imagem)
                imagem_url = f'{settings.MEDIA_BASE_URL}/media/{caminho}'
            vigencia_inicio_str = request.POST.get('vigencia_inicio')
            vigencia_fim_str = request.POST.get('vigencia_fim')
            tipo_segmentacao = request.POST.get('tipo_segmentacao', 'todos_canal')
            grupo_id = request.POST.get('grupo_id')
            ativo = request.POST.get('ativo') == 'on'
            
            # Validações
            if not titulo or not texto_push or not vigencia_inicio_str or not vigencia_fim_str:
                messages.error(request, 'Título, texto push, data início e data fim são obrigatórios')
                return redirect('lojista:ofertas_create')
            
            # Converter datas
            vigencia_inicio = datetime.strptime(vigencia_inicio_str, '%Y-%m-%dT%H:%M')
            vigencia_fim = datetime.strptime(vigencia_fim_str, '%Y-%m-%dT%H:%M')
            
            if vigencia_fim <= vigencia_inicio:
                messages.error(request, 'Data fim deve ser posterior à data início')
                return redirect('lojista:ofertas_create')
            
            # Validar segmentação
            if tipo_segmentacao == 'grupo_customizado' and not grupo_id:
                messages.error(request, 'Selecione um grupo para segmentação customizada')
                return redirect('lojista:ofertas_create')
            
            # Buscar canal_id
            canal_id = request.session.get('canal_id')
            if not canal_id:
                messages.error(request, 'Canal não identificado')
                return redirect('lojista:ofertas_create')
            
            # Criar oferta via service
            usuario_id = request.session.get('usuario_id')
            sucesso, mensagem, oferta_id = OfertaService.criar_oferta(
                titulo=titulo,
                texto_push=texto_push,
                descricao=descricao,
                imagem_url=imagem_url,
                vigencia_inicio=vigencia_inicio,
                vigencia_fim=vigencia_fim,
                canal_id=canal_id,
                tipo_segmentacao=tipo_segmentacao,
                grupo_id=int(grupo_id) if grupo_id else None,
                usuario_criador_id=usuario_id,
                ativo=ativo
            )
            
            if sucesso:
                messages.success(request, f'Oferta criada com sucesso! ID: {oferta_id}')
                return redirect('lojista:ofertas_list')
            else:
                messages.error(request, mensagem)
                return redirect('lojista:ofertas_create')
                
        except ValueError as e:
            messages.error(request, 'Formato de data inválido')
            return redirect('lojista:ofertas_create')
        except Exception as e:
            registrar_log('portais.lojista', f'Erro ao criar oferta: {str(e)}', nivel='ERROR')
            messages.error(request, 'Erro ao criar oferta')
            return redirect('lojista:ofertas_create')


class OfertasEditView(LojistaAuthMixin, View):
    """Edita oferta existente"""
    
    def get(self, request, oferta_id):
        try:
            from apps.ofertas.services import OfertaService
            
            # Buscar oferta via service
            oferta = OfertaService.obter_oferta_por_id(oferta_id)
            
            if not oferta:
                messages.error(request, 'Oferta não encontrada')
                return redirect('lojista:ofertas_list')
            
            # Verificar se usuário tem acesso (mesmo canal)
            canal_id = request.session.get('canal_id')
            if oferta.canal_id != canal_id:
                messages.error(request, 'Sem permissão para editar esta oferta')
                return redirect('lojista:ofertas_list')
            
            # Buscar grupos do canal para dropdown via service
            grupos = OfertaService.listar_grupos_segmentacao(canal_id=canal_id, apenas_ativos=True)
            
            context = {
                'current_page': 'ofertas',
                'oferta': oferta,
                'grupos': grupos,
                'vigencia_inicio_formatted': oferta.vigencia_inicio.strftime('%Y-%m-%dT%H:%M'),
                'vigencia_fim_formatted': oferta.vigencia_fim.strftime('%Y-%m-%dT%H:%M')
            }
            
            return render(request, 'portais/lojista/ofertas/form.html', context)
            
        except Exception as e:
            registrar_log('portais.lojista', f'Erro ao carregar oferta: {str(e)}', nivel='ERROR')
            messages.error(request, 'Erro ao carregar oferta')
            return redirect('lojista:ofertas_list')
    
    def post(self, request, oferta_id):
        try:
            from apps.ofertas.services import OfertaService
            
            # Buscar oferta via service
            oferta = OfertaService.obter_oferta_por_id(oferta_id)
            
            if not oferta:
                messages.error(request, 'Oferta não encontrada')
                return redirect('lojista:ofertas_list')
            
            # Verificar acesso
            canal_id = request.session.get('canal_id')
            if oferta.canal_id != canal_id:
                messages.error(request, 'Sem permissão para editar esta oferta')
                return redirect('lojista:ofertas_list')
            
            # Extrair dados
            titulo = request.POST.get('titulo')
            texto_push = request.POST.get('texto_push')
            descricao = request.POST.get('descricao')
            
            # Processar upload de imagem (se houver)
            imagem_url = oferta.imagem_url  # Manter a atual
            if 'imagem' in request.FILES:
                from django.core.files.storage import default_storage
                import os
                
                imagem = request.FILES['imagem']
                # Gerar nome único para arquivo
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                nome_arquivo = f'ofertas/{timestamp}_{imagem.name}'
                
                # Salvar arquivo
                caminho = default_storage.save(nome_arquivo, imagem)
                imagem_url = f'{settings.MEDIA_BASE_URL}/media/{caminho}'
            vigencia_inicio_str = request.POST.get('vigencia_inicio')
            vigencia_fim_str = request.POST.get('vigencia_fim')
            tipo_segmentacao = request.POST.get('tipo_segmentacao', 'todos_canal')
            grupo_id = request.POST.get('grupo_id')
            ativo = request.POST.get('ativo') == 'on'
            
            # Validações
            if not titulo or not texto_push or not vigencia_inicio_str or not vigencia_fim_str:
                messages.error(request, 'Título, texto push, data início e data fim são obrigatórios')
                return redirect('lojista:ofertas_edit', oferta_id=oferta_id)
            
            # Converter datas
            vigencia_inicio = datetime.strptime(vigencia_inicio_str, '%Y-%m-%dT%H:%M')
            vigencia_fim = datetime.strptime(vigencia_fim_str, '%Y-%m-%dT%H:%M')
            
            if vigencia_fim <= vigencia_inicio:
                messages.error(request, 'Data fim deve ser posterior à data início')
                return redirect('lojista:ofertas_edit', oferta_id=oferta_id)
            
            # Validar segmentação
            if tipo_segmentacao == 'grupo_customizado' and not grupo_id:
                messages.error(request, 'Selecione um grupo para segmentação customizada')
                return redirect('lojista:ofertas_edit', oferta_id=oferta_id)
            
            # Atualizar oferta
            oferta.titulo = titulo
            oferta.texto_push = texto_push
            oferta.descricao = descricao
            oferta.imagem_url = imagem_url
            oferta.vigencia_inicio = vigencia_inicio
            oferta.vigencia_fim = vigencia_fim
            oferta.tipo_segmentacao = tipo_segmentacao
            oferta.grupo_id = int(grupo_id) if grupo_id else None
            oferta.ativo = ativo
            oferta.updated_at = datetime.now()
            oferta.save()
            
            messages.success(request, 'Oferta atualizada com sucesso!')
            return redirect('lojista:ofertas_list')
            
        except Exception as e:
            registrar_log('portais.lojista', f'Erro ao atualizar oferta: {str(e)}', nivel='ERROR')
            messages.error(request, 'Erro ao atualizar oferta')
            return redirect('lojista:ofertas_edit', oferta_id=oferta_id)


@method_decorator(csrf_exempt, name='dispatch')
class OfertasDispararView(View):
    """Dispara push notification para oferta"""
    
    def post(self, request, oferta_id):
        # Verificar autenticação manualmente (não usar mixin em AJAX)
        if not request.session.get('lojista_authenticated'):
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'Sessão expirada. Faça login novamente.',
                'redirect': '/'
            }, status=401)
        try:
            from apps.ofertas.services import OfertaService
            
            data = json.loads(request.body)
            
            # Verificar se oferta existe via service
            oferta = OfertaService.obter_oferta_por_id(oferta_id)
            if not oferta:
                return JsonResponse({
                    'sucesso': False,
                    'mensagem': 'Oferta não encontrada'
                }, status=404)
            
            # Verificar permissão (mesmo canal)
            canal_id = request.session.get('canal_id')
            if oferta.canal_id != canal_id:
                return JsonResponse({
                    'sucesso': False,
                    'mensagem': 'Sem permissão para disparar esta oferta'
                }, status=403)
            
            # Disparar push via service
            usuario_id = request.session.get('usuario_id')
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
                
        except json.JSONDecodeError:
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'JSON inválido'
            }, status=400)
        except Exception as e:
            registrar_log('portais.lojista', f'Erro ao disparar oferta: {str(e)}', nivel='ERROR')
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'Erro ao disparar push'
            }, status=500)


class OfertasHistoricoView(LojistaAuthMixin, View):
    """Mostra histórico de disparos de uma oferta"""
    
    def get(self, request, oferta_id):
        try:
            from apps.ofertas.services import OfertaService
            
            # Buscar oferta via service
            oferta = OfertaService.obter_oferta_por_id(oferta_id)
            
            if not oferta:
                messages.error(request, 'Oferta não encontrada')
                return redirect('lojista:ofertas_list')
            
            # Buscar disparos via service
            disparos = OfertaService.listar_disparos_oferta(oferta_id)
            
            context = {
                'current_page': 'ofertas',
                'oferta': oferta,
                'disparos': disparos
            }
            
            return render(request, 'portais/lojista/ofertas/historico.html', context)
            
        except Exception as e:
            registrar_log('portais.lojista', f'Erro ao carregar histórico: {str(e)}', nivel='ERROR')
            messages.error(request, 'Erro ao carregar histórico')
            return redirect('lojista:ofertas_list')
