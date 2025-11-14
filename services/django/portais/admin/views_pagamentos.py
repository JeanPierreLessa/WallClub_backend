"""
Views para gerenciamento de pagamentos no portal administrativo.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.db import transaction
from django.urls import reverse
import csv
import io
import json
from datetime import datetime
from decimal import Decimal, InvalidOperation

from portais.controle_acesso.controle_acesso import require_funcionalidade, require_acesso_padronizado, require_secao_permitida
from wallclub_core.utilitarios.log_control import registrar_log
from django.apps import apps

from sistema_bancario.models import PagamentoEfetuado, LancamentoManual
from sistema_bancario.services import PagamentoService
from sistema_bancario.services_lancamento_manual import LancamentoManualService


@require_secao_permitida('pagamentos')
def pagamentos_list(request):
    """
    Lista pagamentos com filtros por NSU e data de criação.
    Por padrão, não mostra nenhum registro (função básica é inserção).
    """
    
    # Filtros
    search_nsu = request.GET.get('nsu', '').strip()
    search_data_inicio = request.GET.get('data_inicio', '').strip()
    search_data_fim = request.GET.get('data_fim', '').strip()
    
    # Usar serviço bancário para buscar pagamentos
    filtros = {}
    if search_nsu:
        filtros['nsu'] = search_nsu
    if search_data_inicio:
        filtros['data_inicio'] = search_data_inicio
    if search_data_fim:
        filtros['data_fim'] = search_data_fim
    
    pagamentos = PagamentoService.buscar_pagamentos(filtros)
    
    # Paginação
    paginator = Paginator(pagamentos, 20)
    page_number = request.GET.get('page')
    pagamentos_page = paginator.get_page(page_number)
    
    context = {
        'pagamentos': pagamentos_page,
        'search_nsu': search_nsu,
        'search_data_inicio': search_data_inicio,
        'search_data_fim': search_data_fim,
        'total_registros': paginator.count if pagamentos.exists() else 0,
        'has_filters': bool(search_nsu or search_data_inicio or search_data_fim),
    }
    
    return render(request, 'portais/admin/pagamentos_list.html', context)


@require_acesso_padronizado('pagamentos_create')
@require_http_methods(["POST"])
def pagamentos_upload_csv(request):
    """
    Processa upload de CSV com dados de pagamentos
    Estrutura esperada: nsu;var44;var45;var58;var59;var66;var71;var100;var111;var112
    Separador: ponto-e-vírgula (;)
    """
    try:
        if 'arquivo_csv' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'Nenhum arquivo enviado'})
        
        arquivo = request.FILES['arquivo_csv']
        
        if not arquivo.name.lower().endswith('.csv'):
            return JsonResponse({'success': False, 'error': 'Arquivo deve ser CSV'})
        
        # Ler conteúdo do arquivo
        try:
            conteudo = arquivo.read().decode('utf-8')
        except UnicodeDecodeError:
            try:
                conteudo = arquivo.read().decode('latin-1')
            except UnicodeDecodeError:
                return JsonResponse({'success': False, 'error': 'Erro de codificação do arquivo'})
        
        # Processar CSV com separador ponto-e-vírgula
        pagamentos = []
        linhas_erro = []
        
        reader = csv.DictReader(io.StringIO(conteudo), delimiter=';')
        
        # Verificar se tem as colunas necessárias
        colunas_esperadas = ['nsu', 'var44', 'var45', 'var58', 'var59', 'var66', 'var71', 'var100', 'var111', 'var112']
        colunas_arquivo = [col.strip() for col in reader.fieldnames] if reader.fieldnames else []
        
        if not all(col in colunas_arquivo for col in colunas_esperadas):
            return JsonResponse({
                'success': False, 
                'error': f'CSV deve conter as colunas (separadas por ponto-e-vírgula): {"; ".join(colunas_esperadas)}'
            })
        
        # Processar campos decimais
        def processar_decimal(valor, nome_campo, linha_num):
            if not valor or valor.strip() == '':
                return None
            try:
                from decimal import Decimal, ROUND_HALF_UP
                valor_limpo = valor.strip().replace(',', '.')
                return Decimal(valor_limpo).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            except ValueError:
                raise ValueError(f'Linha {linha_num}: {nome_campo} deve ser um número válido (valor: "{valor}")')
        
        # Processar campos texto
        def processar_texto(valor, max_length=20):
            if not valor:
                return ''
            texto = str(valor).strip()
            return texto[:max_length] if len(texto) > max_length else texto
        
        # FASE 1: VALIDAR TODAS AS LINHAS (tudo ou nada)
        registrar_log('portais.admin', f'PAGAMENTOS CSV - Iniciando validação de {sum(1 for _ in reader)} linhas')
        
        # Resetar reader
        conteudo_io = io.StringIO(conteudo)
        reader = csv.DictReader(conteudo_io, delimiter=';')
        next(reader)  # Pular header
        
        for i, linha in enumerate(reader, 1):
            try:
                # Validar NSU (obrigatório)
                nsu = linha.get('nsu', '').strip()
                if not nsu:
                    linhas_erro.append(f'Linha {i}: NSU é obrigatório')
                    continue
                
                try:
                    nsu_int = int(nsu)
                except ValueError:
                    linhas_erro.append(f'Linha {i}: NSU deve ser um número (valor: "{nsu}")')
                    continue
                
                # Validar campos decimais (sem processar ainda)
                try:
                    if linha.get('var44', '').strip():
                        processar_decimal(linha.get('var44', ''), 'var44', i)
                    if linha.get('var58', '').strip():
                        processar_decimal(linha.get('var58', ''), 'var58', i)
                    if linha.get('var111', '').strip():
                        processar_decimal(linha.get('var111', ''), 'var111', i)
                    if linha.get('var112', '').strip():
                        processar_decimal(linha.get('var112', ''), 'var112', i)
                except ValueError as e:
                    linhas_erro.append(str(e))
                    continue
                
            except Exception as e:
                linhas_erro.append(f'Linha {i}: Erro ao validar - {str(e)}')
        
        # Se houver erros, retornar ANTES de processar qualquer linha
        if linhas_erro:
            registrar_log('portais.admin', f'PAGAMENTOS CSV - Validação falhou com {len(linhas_erro)} erro(s)', level='WARNING')
            return JsonResponse({
                'success': False, 
                'error': f'Arquivo contém erros. Nenhum registro foi processado.\n\n' + '\n'.join(linhas_erro)
            })
        
        # FASE 2: PROCESSAR TODAS AS LINHAS (validação passou)
        registrar_log('portais.admin', f'PAGAMENTOS CSV - Validação OK. Processando linhas...')
        
        # Resetar reader novamente
        conteudo_io = io.StringIO(conteudo)
        reader = csv.DictReader(conteudo_io, delimiter=';')
        next(reader)  # Pular header
        
        for i, linha in enumerate(reader, 1):
            nsu = int(linha.get('nsu', '').strip())
            
            # Extrair valores dos campos
            var44 = processar_decimal(linha.get('var44', ''), 'var44', i)
            var45 = processar_texto(linha.get('var45', ''))
            var58 = processar_decimal(linha.get('var58', ''), 'var58', i)
            var59 = processar_texto(linha.get('var59', ''))
            var66 = processar_texto(linha.get('var66', ''))
            var71 = processar_texto(linha.get('var71', ''))
            var100 = processar_texto(linha.get('var100', ''))
            var111 = processar_decimal(linha.get('var111', ''), 'var111', i)
            var112 = processar_decimal(linha.get('var112', ''), 'var112', i)
            
            pagamento = {
                'nsu': nsu,
                'var44': var44,
                'var45': var45,
                'var58': var58,
                'var59': var59,
                'var66': var66,
                'var71': var71,
                'var100': var100,
                'var111': var111,
                'var112': var112,
            }
            
            pagamentos.append(pagamento)
        
        if not pagamentos:
            return JsonResponse({'success': False, 'error': 'Nenhum pagamento válido encontrado no CSV'})
        
        registrar_log('portais.admin', f'PAGAMENTOS CSV - ✅ {len(pagamentos)} pagamentos processados com sucesso')
        
        return JsonResponse({
            'success': True, 
            'pagamentos': pagamentos,
            'total': len(pagamentos)
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Erro interno: {str(e)}'})




@require_acesso_padronizado('pagamentos_create')
def pagamentos_create(request):
    """
    Cria novo registro de pagamento.
    """
    
    if request.method == 'POST':
        return _processar_criacao_pagamento(request)
    
    context = {
        'action': 'create',
        'title': 'Novo Pagamento',
    }
    
    return render(request, 'portais/admin/pagamentos_form.html', context)


@require_acesso_padronizado('pagamentos_edit')
def pagamentos_edit(request, pagamento_id):
    """
    Edita registro de pagamento existente.
    """
    
    pagamento = PagamentoService.obter_pagamento(pagamento_id)
    
    if request.method == 'POST':
        return _processar_edicao_pagamento(request, pagamento)
    
    context = {
        'pagamento': pagamento,
        'action': 'edit',
        'title': f'Editar Pagamento NSU {pagamento.nsu}',
    }
    
    return render(request, 'portais/admin/pagamentos_form.html', context)


@require_acesso_padronizado('pagamentos_delete')
def pagamentos_delete(request, pagamento_id):
    """
    Exclui registro de pagamento usando serviço bancário.
    """
    
    if request.method == 'POST':
        try:
            info_pagamento = PagamentoService.excluir_pagamento(pagamento_id, request.portal_usuario)
            messages.success(request, f'Pagamento NSU {info_pagamento["nsu"]} excluído com sucesso.')
        except Exception as e:
            messages.error(request, f'Erro ao excluir pagamento: {str(e)}')
    
    return redirect('portais_admin:pagamentos_list')


def _processar_criacao_pagamento(request):
    """
    Processa criação de novo pagamento usando serviço bancário.
    """
    
    try:
        # Extrair dados do formulário
        dados_pagamento = _extrair_dados_formulario(request)
        dados_pagamento['nsu'] = request.POST.get('nsu', '').strip()
        
        # Usar serviço bancário para criar pagamento
        pagamento = PagamentoService.criar_pagamento(dados_pagamento, request.portal_usuario)
        
        messages.success(request, f'Pagamento NSU {pagamento.nsu} criado com sucesso.')
        return redirect('portais_admin:pagamentos_edit', pagamento_id=pagamento.id)
    
    except ValueError as e:
        messages.error(request, str(e))
    except ValidationError as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, f'Erro ao criar pagamento: {str(e)}')
    
    return render(request, 'portais/admin/pagamentos_form.html', {
        'action': 'create',
        'title': 'Novo Pagamento',
    })


def _processar_edicao_pagamento(request, pagamento):
    """
    Processa edição de pagamento existente usando serviço bancário.
    """
    
    try:
        # Extrair dados do formulário
        dados_atualizados = _extrair_dados_formulario(request)
        
        # Usar serviço bancário para atualizar pagamento
        pagamento_atualizado = PagamentoService.atualizar_pagamento(
            pagamento.id, dados_atualizados, request.portal_usuario
        )
        
        messages.success(request, f'Pagamento NSU {pagamento_atualizado.nsu} atualizado com sucesso.')
        return redirect('portais_admin:pagamentos_edit', pagamento_id=pagamento_atualizado.id)
    
    except Exception as e:
        messages.error(request, f'Erro ao atualizar pagamento: {str(e)}')
    
    return render(request, 'portais/admin/pagamentos_form.html', {
        'pagamento': pagamento,
        'action': 'edit',
        'title': f'Editar Pagamento NSU {pagamento.nsu}',
    })


def _extrair_dados_formulario(request):
    """
    Extrai e valida dados do formulário de pagamento.
    """
    
    dados = {}
    
    # Campos monetários
    for campo in ['var44', 'var58', 'var111', 'var112']:
        valor = request.POST.get(campo, '').strip()
        if valor:
            try:
                # Converter vírgula para ponto e validar
                valor_decimal = Decimal(valor.replace(',', '.'))
                dados[campo] = valor_decimal
            except (ValueError, TypeError):
                dados[campo] = None
        else:
            dados[campo] = None
    
    # Campos de texto
    for campo in ['var45', 'var59', 'var66', 'var71', 'var100']:
        valor = request.POST.get(campo, '').strip()
        dados[campo] = valor if valor else None
    
    return dados


@require_secao_permitida('pagamentos')
def pagamentos_ajax_check_nsu(request):
    """
    Verifica se NSU já existe via AJAX usando serviço bancário.
    """
    
    nsu = request.GET.get('nsu', '').strip()
    
    if not nsu:
        return JsonResponse({'exists': False})
    
    try:
        exists = PagamentoService.verificar_nsu_existe(nsu)
        return JsonResponse({'exists': exists})
    except ValueError:
        return JsonResponse({'exists': False, 'error': 'NSU deve ser um número'})


@require_acesso_padronizado('pagamentos_create')
@require_http_methods(["POST"])
def pagamentos_bulk_create(request):
    """
    Cria múltiplos pagamentos em lote via AJAX.
    """
    
    try:
        # Parse do JSON
        data = json.loads(request.body)
        pagamentos_data = data.get('pagamentos', [])
        
        # LOG: Ver o que está chegando
        registrar_log('portais.admin', f'BULK CREATE - Recebidos {len(pagamentos_data)} pagamentos')
        registrar_log('portais.admin', f'BULK CREATE - Primeiro pagamento: {pagamentos_data[0] if pagamentos_data else "vazio"}')
        
        if not pagamentos_data:
            return JsonResponse({
                'success': False,
                'message': 'Nenhum pagamento fornecido'
            })
        
        created_count = 0
        errors = []
        
        with transaction.atomic():
            for i, pagamento_data in enumerate(pagamentos_data):
                try:
                    # LOG: Ver dados da linha
                    registrar_log('portais.admin', f'BULK CREATE - Linha {i+1}: {pagamento_data}')
                    
                    # Validar NSU obrigatório
                    nsu = pagamento_data.get('nsu')
                    registrar_log('portais.admin', f'BULK CREATE - NSU recebido: {nsu} (tipo: {type(nsu).__name__})')
                    
                    if nsu is None or nsu == '':
                        errors.append(f'Linha {i+1}: NSU é obrigatório')
                        continue
                    
                    # Converter NSU para string
                    nsu = str(nsu).strip() if nsu else None
                    if not nsu:
                        errors.append(f'Linha {i+1}: NSU é obrigatório')
                        continue
                    
                    # Verificar se NSU já existe usando serviço
                    if PagamentoService.verificar_nsu_existe(nsu):
                        errors.append(f'Linha {i+1}: NSU {nsu} já existe')
                        continue
                    
                    # Preparar dados do pagamento
                    dados_pagamento = {
                        'nsu': nsu
                    }
                    
                    # Campos monetários opcionais
                    for campo in ['var44', 'var58', 'var111', 'var112']:
                        valor = pagamento_data.get(campo)
                        if valor:
                            try:
                                dados_pagamento[campo] = Decimal(str(valor))
                            except (ValueError, TypeError):
                                dados_pagamento[campo] = None
                        else:
                            dados_pagamento[campo] = None
                    
                    # Campos de texto opcionais
                    for campo in ['var45', 'var59', 'var66', 'var71', 'var100']:
                        valor = pagamento_data.get(campo)
                        if valor is None or valor == '':
                            dados_pagamento[campo] = None
                        else:
                            dados_pagamento[campo] = str(valor).strip()
                    
                    # LOG: Dados que serão enviados ao serviço
                    registrar_log('portais.admin', f'BULK CREATE - Dados preparados: {dados_pagamento}')
                    
                    # Criar pagamento usando serviço
                    PagamentoService.criar_pagamento(dados_pagamento, request.portal_usuario)
                    created_count += 1
                    
                    registrar_log('portais.admin', f'BULK CREATE - Linha {i+1} salva com sucesso')
                    
                except ValueError as e:
                    registrar_log('portais.admin', f'BULK CREATE - ValueError na linha {i+1}: {str(e)}', level='ERROR')
                    errors.append(f'Linha {i+1}: NSU inválido - {str(e)}')
                except Exception as e:
                    registrar_log('portais.admin', f'BULK CREATE - Exception na linha {i+1}: {str(e)}', level='ERROR')
                    import traceback
                    registrar_log('portais.admin', f'BULK CREATE - Traceback: {traceback.format_exc()}', level='ERROR')
                    errors.append(f'Linha {i+1}: Erro - {str(e)}')
        
        if errors:
            return JsonResponse({
                'success': False,
                'message': f'{created_count} pagamento(s) criado(s), mas houve erros',
                'errors': errors,
                'created': created_count
            })
        
        return JsonResponse({
            'success': True,
            'message': f'{created_count} pagamento(s) criado(s) com sucesso',
            'created': created_count
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Dados JSON inválidos'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        })


# ===================== VIEWS LANÇAMENTOS MANUAIS =====================

@require_acesso_padronizado('pagamentos_create')
def lancamento_manual_form(request):
    """
    Exibe formulário para criar novo lançamento manual.
    """
    from wallclub_core.estr_organizacional.services import HierarquiaOrganizacionalService
    
    # Buscar lojas ordenadas por razão social
    lojas = HierarquiaOrganizacionalService.listar_todas_lojas()
    
    context = {
        'lojas': lojas
    }
    
    return render(request, 'portais/admin/lancamento_manual_form.html', context)


@require_acesso_padronizado('pagamentos_list')
def lancamentos_manuais_list(request):
    """
    Lista lançamentos manuais com filtros.
    Requer NSU ou range de datas para funcionar.
    """
    # Filtros
    search_loja_id = request.GET.get('loja_id', '').strip()
    search_data_inicio = request.GET.get('data_inicio', '').strip()
    search_data_fim = request.GET.get('data_fim', '').strip()
    search_tipo = request.GET.get('tipo_lancamento', '').strip()
    search_status = request.GET.get('status', '').strip()
    search_nsu = request.GET.get('nsu', '').strip()
    
    # Validar se tem parâmetros mínimos (NSU ou range de datas)
    tem_nsu = bool(search_nsu)
    tem_range_datas = bool(search_data_inicio and search_data_fim)
    
    if not tem_nsu and not tem_range_datas:
        # Retornar página vazia com mensagem
        context = {
            'page_obj': None,
            'search_loja_id': search_loja_id,
            'search_data_inicio': search_data_inicio,
            'search_data_fim': search_data_fim,
            'search_tipo': search_tipo,
            'search_status': search_status,
            'search_nsu': search_nsu,
            'tipos_choices': LancamentoManual.TIPO_CHOICES,
            'status_choices': LancamentoManual.STATUS_CHOICES,
            'erro_parametros': True,
        }
        return render(request, 'portais/admin/lancamentos_manuais_list.html', context)
    
    # Aplicar filtro por canal se necessário
    filtro_canal = None
    if hasattr(request, 'funcionalidade_requer_canal') and request.funcionalidade_requer_canal:
        # TODO: Implementar lógica de canal por usuário quando necessário
        pass

    # Usar serviço para buscar lançamentos
    filtros = {}
    if search_loja_id:
        filtros['loja_id'] = search_loja_id
    if search_data_inicio:
        filtros['data_inicio'] = search_data_inicio
    if search_data_fim:
        filtros['data_fim'] = search_data_fim
    if search_tipo:
        filtros['tipo_lancamento'] = search_tipo
    if search_status:
        filtros['status'] = search_status
    if search_nsu:
        filtros['nsu'] = search_nsu
    if filtro_canal:
        filtros['canal_filtro'] = filtro_canal
    
    lancamentos = LancamentoManualService.buscar_lancamentos(filtros)
    
    # Buscar nomes das lojas para cada lançamento
    from wallclub_core.estr_organizacional.loja import Loja
    
    # Criar dicionário de nomes das lojas
    lojas_ids = set(lancamento.loja_id for lancamento in lancamentos)
    lojas_dict = {}
    
    for loja_id in lojas_ids:
        # Usar método centralizado get_loja
        loja = Loja.get_loja(loja_id)
        if loja:
            lojas_dict[loja_id] = loja.razao_social or f'Loja {loja_id}'
        else:
            lojas_dict[loja_id] = f'Loja {loja_id} (não encontrada)'
    
    # Adicionar nome da loja a cada lançamento
    for lancamento in lancamentos:
        lancamento.loja_nome = lojas_dict.get(lancamento.loja_id, f'Loja {lancamento.loja_id}')
    
    # Paginação
    paginator = Paginator(lancamentos, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_loja_id': search_loja_id,
        'search_data_inicio': search_data_inicio,
        'search_data_fim': search_data_fim,
        'search_tipo': search_tipo,
        'search_status': search_status,
        'search_nsu': search_nsu,
        'tipos_choices': LancamentoManual.TIPO_CHOICES,
        'status_choices': LancamentoManual.STATUS_CHOICES,
        'erro_parametros': False,
    }
    
    return render(request, 'portais/admin/lancamentos_manuais_list.html', context)


@require_funcionalidade('pagamentos_create')
@csrf_exempt
@require_http_methods(["POST"])
def lancamento_manual_create(request):
    """
    Cria um novo lançamento manual via AJAX.
    """
    try:
        data = json.loads(request.body)
        
        # Validação básica
        required_fields = ['loja_id', 'tipo_lancamento', 'valor', 'descricao']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'success': False,
                    'message': f'Campo {field} é obrigatório'
                })
        
        # Criar lançamento usando o service
        # Tratar valor com vírgula brasileira
        valor_str = str(data['valor']).replace(',', '.')
        
        dados_lancamento = {
            'loja_id': int(data['loja_id']),
            'tipo_lancamento': data['tipo_lancamento'],
            'valor': Decimal(valor_str),
            'descricao': data['descricao'],
            'motivo': data.get('motivo', ''),
            'observacoes': data.get('observacoes', ''),
            'referencia_externa': data.get('referencia_externa', '')
        }
        
        # Obter ID do usuário logado na sessão do portal
        id_usuario = request.session.get('portal_usuario_id')
        if not id_usuario:
            return JsonResponse({
                'success': False,
                'message': 'Usuário não autenticado'
            })
        
        lancamento = LancamentoManualService.criar_lancamento(
            dados=dados_lancamento,
            id_usuario=id_usuario
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Lançamento manual criado com sucesso',
            'lancamento_id': lancamento.id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Dados JSON inválidos'
        })
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'message': f'Erro de validação: {str(e)}'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        })


@require_funcionalidade('pagamentos_edit')
@csrf_exempt
@require_http_methods(["POST"])
def lancamento_manual_update(request, lancamento_id):
    """
    Atualiza um lançamento manual existente.
    """
    try:
        data = json.loads(request.body)
        
        # Buscar lançamento
        lancamento = get_object_or_404(LancamentoManual, id=lancamento_id)
        
        # Atualizar usando o service
        lancamento_atualizado = LancamentoManualService.atualizar_lancamento(
            lancamento_id=lancamento_id,
            id_usuario=request.user.id,
            dados_atualizacao=data
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Lançamento manual atualizado com sucesso'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Dados JSON inválidos'
        })
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'message': f'Erro de validação: {str(e)}'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        })


@require_funcionalidade('pagamentos_edit')
@csrf_exempt
@require_http_methods(["POST"])
def lancamento_manual_cancel(request, lancamento_id):
    """
    Cancela um lançamento manual.
    """
    try:
        data = json.loads(request.body)
        motivo_cancelamento = data.get('motivo', 'Cancelado via portal admin')
        
        # Cancelar usando o service
        LancamentoManualService.cancelar_lancamento(
            lancamento_id=lancamento_id,
            id_usuario=request.user.id,
            motivo=motivo_cancelamento
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Lançamento manual cancelado com sucesso'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Dados JSON inválidos'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        })


@require_funcionalidade('pagamentos_edit')
@csrf_exempt
@require_http_methods(["POST"])
def lancamento_manual_process(request, lancamento_id):
    """
    Marca um lançamento manual como processado.
    """
    try:
        # Processar usando o service
        LancamentoManualService.processar_lancamento(
            lancamento_id=lancamento_id,
            id_usuario=request.user.id
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Lançamento manual processado com sucesso'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erro interno: {str(e)}'
        })


@require_funcionalidade('pagamentos_list')
def lancamento_manual_detail(request, lancamento_id):
    """
    Exibe detalhes de um lançamento manual específico.
    """
    from wallclub_core.estr_organizacional.loja import Loja
    from portais.controle_acesso.models import PortalUsuario
    
    lancamento = get_object_or_404(LancamentoManual, id=lancamento_id)
    
    # Buscar dados relacionados manualmente
    # Usar método centralizado get_loja
    loja = Loja.get_loja(lancamento.loja_id)
    if loja:
        loja_nome = loja.razao_social or f'Loja {lancamento.loja_id}'
    else:
        loja_nome = f'Loja {lancamento.loja_id} (não encontrada)'
    
    try:
        usuario = PortalUsuario.objects.get(id=lancamento.id_usuario)
        usuario_nome = usuario.nome or f'Usuário {lancamento.id_usuario}'
    except PortalUsuario.DoesNotExist:
        usuario_nome = f'Usuário {lancamento.id_usuario} (não encontrado)'
    
    historico = LancamentoManualService.obter_historico_loja(lancamento.loja_id)
    
    context = {
        'lancamento': lancamento,
        'loja_nome': loja_nome,
        'usuario_nome': usuario_nome,
        'historico': historico,
    }
    return render(request, 'portais/admin/lancamento_manual_detail.html', context)
