"""
Views para gerenciamento de parâmetros WallClub.
Integração com parametros_wallclub, planos e loja.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db import transaction, models
from django.db.models import Q
from django.core.paginator import Paginator
from datetime import datetime

from wallclub_core.integracoes.parametros_api_client import parametros_api
from wallclub_core.estr_organizacional.loja import Loja
from wallclub_core.utilitarios.export_utils import exportar_csv
from wallclub_core.utilitarios.log_control import registrar_log
from ..controle_acesso.decorators import require_admin_access
from portais.controle_acesso.controle_acesso import require_acesso_padronizado


@require_acesso_padronizado('parametros_list')
def parametros_list(request):
    """
    Lista todas as configurações vigentes com dados da loja.
    Mostra apenas 1 configuração ativa por loja.
    """
    
    # Buscar todas as lojas com parâmetros vigentes
    from wallclub_core.estr_organizacional.services import HierarquiaOrganizacionalService
    lojas_com_parametros = HierarquiaOrganizacionalService.listar_lojas_com_parametros()
    
    # Filtros
    search = request.GET.get('search', '')
    if search:
        lojas_com_parametros = lojas_com_parametros.filter(
            Q(razao_social__icontains=search) |
            Q(cnpj__icontains=search) |
            Q(id__icontains=search)
        )
    
    # Paginação
    paginator = Paginator(lojas_com_parametros, 20)
    page_number = request.GET.get('page')
    lojas = paginator.get_page(page_number)
    
    # Para cada loja, buscar dados resumidos via API
    for loja in lojas:
        # Contar configurações vigentes
        loja.total_configuracoes = parametros_api.contar_configuracoes_loja(loja.id)
        
        # Última atualização
        ultima_config = parametros_api.obter_ultima_configuracao(loja.id)
        loja.ultima_atualizacao = ultima_config.get('atualizado_em') if ultima_config else None
        
        # Verificar modalidades
        modalidades_response = parametros_api.verificar_modalidades_loja(loja.id)
        loja.modalidades = modalidades_response.get('modalidades', []) if modalidades_response.get('sucesso') else []
    
    context = {
        'lojas': lojas,
        'search': search,
        'total_lojas': paginator.count if hasattr(paginator, 'count') else lojas_com_parametros.count(),
    }
    
    return render(request, 'portais/admin/parametros_list.html', context)








@require_acesso_padronizado('parametros_view')
def parametros_ajax_plano_info(request, plano_id):
    """
    Retorna informações de um plano via AJAX.
    """
    
    try:
        # Buscar plano via API
        planos = parametros_api.listar_planos()
        plano = next((p for p in planos if p['id'] == plano_id), None)
        
        if not plano:
        
            return JsonResponse({
                'success': False,
                'error': 'Plano não encontrado'
            }, status=404)
        
        data = {
            'success': True,
            'plano': plano
        }
    except Exception as e:
        data = {
            'success': False,
            'error': str(e)
        }
    
    return JsonResponse(data)



@require_acesso_padronizado('parametros_copy')
def parametros_download_csv(request, loja_id):
    """
    Gera arquivo CSV com todos os parâmetros de uma loja específica.
    Formato igual ao template de importação.
    """
    # Importar registrar_log localmente para evitar conflitos de escopo
    from wallclub_core.utilitarios.log_control import registrar_log as log_func
    
    try:
        # Validar acesso à loja
        from portais.controle_acesso.filtros import FiltrosAcessoService
        FiltrosAcessoService.validar_acesso_loja_ou_403(request.portal_usuario, loja_id)
        
        # Verificar se a loja existe
        loja = get_object_or_404(Loja, id=loja_id)
        
        # DEBUG: Verificar tipo do objeto loja
        from wallclub_core.utilitarios.log_control import registrar_log
        registrar_log('portais.admin', f"DEBUG CSV: Tipo da loja: {type(loja)}")
        registrar_log('portais.admin', f"DEBUG CSV: Loja ID: {loja.id}")
        registrar_log('portais.admin', f"DEBUG CSV: Loja razao_social: {loja.razao_social}")
        
        # Buscar configurações via API
        agora = datetime.now()
        response = parametros_api.buscar_configuracoes_loja(loja_id, agora)
        
        if not response.get('sucesso'):
            messages.error(request, response.get('mensagem', 'Erro ao buscar configurações'))
            return redirect('portais_admin:parametros_list')
        
        configuracoes = response.get('configuracoes', [])
        
        if not configuracoes:
            messages.warning(request, f'Nenhum parâmetro encontrado para a loja {loja.razao_social}')
            return redirect('portais_admin:parametros_list')
        
        # Preparar dados para export_utils
        dados = []
        log_func('portais.admin', f"DEBUG CSV: Iniciando preparação de dados para {len(configuracoes)} configurações")
        
        # Buscar planos para mapeamento
        planos = parametros_api.listar_planos()
        planos_dict = {p['id']: p for p in planos}
        
        for config in configuracoes:
            log_func('portais.admin', f"DEBUG CSV: Processando config ID {config['id']} - Loja {config['loja_id']}, Plano {config['id_plano']}")
            
            # Buscar dados do plano
            plano = planos_dict.get(config['id_plano'])
            log_func('portais.admin', f"DEBUG CSV: Plano encontrado: {plano['descricao'] if plano else 'None'}")
            
            linha_dados = {
                'loja_id': config['loja_id'],
                'id_plano': config['id_plano'],
                'nome_plano': plano['descricao'] if plano else '',
                'bandeira': plano['bandeira'] if plano else '',
                'prazo_dias': plano.get('prazo_limite', '') if plano else '',
                'wall': config['wall']
            }
            
            # Adicionar parâmetros loja (1-7 disponíveis na API)
            for i in range(1, 8):
                valor = config.get(f'parametro_loja_{i}')
                linha_dados[f'parametro_loja_{i}'] = valor if valor is not None else ''
            
            # Preencher demais parâmetros loja com vazio (8-30)
            for i in range(8, 31):
                linha_dados[f'parametro_loja_{i}'] = ''
                
            # Parâmetros uptal (1-6) - não disponíveis na API simplificada
            for i in range(1, 7):
                linha_dados[f'parametro_uptal_{i}'] = ''
                
            # Parâmetros wall (1-4) - não disponíveis na API simplificada
            for i in range(1, 5):
                linha_dados[f'parametro_wall_{i}'] = ''
            
            dados.append(linha_dados)
            log_func('portais.admin', f"DEBUG CSV: Linha adicionada aos dados")
        
        log_func('portais.admin', f"DEBUG CSV: Total de {len(dados)} linhas preparadas")
        log_func('portais.admin', f"DEBUG CSV: Tipo do primeiro item: {type(dados[0]) if dados else 'Lista vazia'}")
        
        # Cabeçalhos para o CSV
        cabecalhos = {
            'loja_id': 'loja_id',
            'id_plano': 'id_plano', 
            'nome_plano': 'nome_plano',
            'bandeira': 'bandeira',
            'prazo_dias': 'prazo_dias',
            'wall': 'wall'
        }
        
        # Adicionar cabeçalhos para parâmetros loja (1-30)
        for i in range(1, 31):
            cabecalhos[f'parametro_loja_{i}'] = f'parametro_loja_{i}'
            
        # Adicionar cabeçalhos para parâmetros uptal (1-6)
        for i in range(1, 7):
            cabecalhos[f'parametro_uptal_{i}'] = f'parametro_uptal_{i}'
            
        # Adicionar cabeçalhos para parâmetros wall (1-4)
        for i in range(1, 5):
            cabecalhos[f'parametro_wall_{i}'] = f'parametro_wall_{i}'
        
        # Usar export_utils para gerar o CSV
        import re
        nome_loja_limpo = re.sub(r'[^\w\s-]', '', loja.razao_social).replace(' ', '_')
        nome_arquivo = f'parametros_loja_{loja_id}_{nome_loja_limpo}'
        
        log_func('portais.admin', f"DEBUG CSV: Chamando exportar_csv com nome_arquivo={nome_arquivo}")
        log_func('portais.admin', f"DEBUG CSV: Dados para exportar: {len(dados)} itens")
        log_func('portais.admin', f"DEBUG CSV: Primeiro item dos dados: {dados[0] if dados else 'Vazio'}")
        
        try:
            resultado = exportar_csv(nome_arquivo, dados, cabecalhos)
            log_func('portais.admin', f"DEBUG CSV: Export realizado com sucesso")
            return resultado
        except Exception as export_error:
            import traceback
            traceback_str = traceback.format_exc()
            log_func('portais.admin', f"ERRO no exportar_csv: {str(export_error)}")
            log_func('portais.admin', f"TRACEBACK: {traceback_str}")
            raise export_error
        
    except Exception as e:
        import traceback
        traceback_str = traceback.format_exc()
        log_func('portais.admin', f'ERRO GERAL ao gerar CSV: {str(e)}')
        log_func('portais.admin', f'TRACEBACK GERAL: {traceback_str}')
        messages.error(request, f'Erro ao gerar CSV: {str(e)}')
        return redirect('portais_admin:parametros_list')
