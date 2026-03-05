"""
Views para importação de parâmetros via planilha.
"""

import csv
import io
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from datetime import datetime
from decimal import Decimal
from wallclub_core.integracoes.parametros_api_client import parametros_api
from ..controle_acesso.decorators import require_admin_access
from wallclub_core.utilitarios.log_control import registrar_log
from parametros_wallclub.models import ImportacaoConfiguracoes, ParametrosWall, Plano


@require_admin_access
def importacao_parametros(request):
    """
    Interface para importação de parâmetros via planilha.
    """
    # Buscar últimas importações via API
    ultimas_importacoes = parametros_api.listar_importacoes(limit=10)

    context = {
        'ultimas_importacoes': ultimas_importacoes,
    }

    return render(request, 'portais/admin/parametros_importar.html', context)


@require_admin_access
def download_template_csv(request):
    """
    Gera arquivo CSV template para importação de parâmetros.
    Inclui todas as linhas de planos disponíveis.
    """
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="template_parametros_wallclub.csv"'

    # Adicionar BOM para UTF-8
    response.write('\ufeff')

    writer = csv.writer(response)

    # Cabeçalho
    headers = [
        'loja_id',
        'id_plano',
        'nome_plano',
        'bandeira',
        'prazo_dias',
        'wall'
    ]

    # Adicionar colunas dos parâmetros
    for i in range(1, 34):  # Parâmetros Loja 1-33
        headers.append(f'parametro_loja_{i}')

    for i in range(1, 8):   # Parâmetros Uptal 1-7
        headers.append(f'parametro_uptal_{i}')

    for i in range(1, 5):   # Parâmetros Wall 1-4
        headers.append(f'parametro_wall_{i}')

    writer.writerow(headers)

    # Buscar todos os planos via API
    planos = parametros_api.listar_planos()

    # Primeiro: planos com wall='S'
    for plano in planos:
        linha = [
            '1',                           # loja_id (exemplo)
            str(plano['id']),              # id_plano
            plano['descricao'],            # nome_plano
            plano['bandeira'],             # bandeira
            str(plano.get('prazo_limite', '')),  # prazo_dias
            'S',                           # wall=S
        ]

        # Valores zerados para todos os parâmetros
        for i in range(44):  # 33 + 7 + 4 = 44 parâmetros
            linha.append('0.00')

        writer.writerow(linha)

    # Depois: mesmos planos com wall='N'
    for plano in planos:
        linha = [
            '1',                           # loja_id (exemplo)
            str(plano['id']),              # id_plano
            plano['descricao'],            # nome_plano
            plano['bandeira'],             # bandeira
            str(plano.get('prazo_limite', '')),  # prazo_dias
            'N',                           # wall=N
        ]

        # Valores zerados para todos os parâmetros
        for i in range(44):  # 33 + 7 + 4 = 44 parâmetros
            linha.append('0.00')

        writer.writerow(linha)

    # Linha com comentários
    comentarios = [
        '# ID da loja (obrigatório)',
        '# ID do plano 1-306 (obrigatório)',
        '# Nome do plano',
        '# Bandeira do cartão',
        '# Prazo em dias',
        '# S=Com Wall, N=Sem Wall (obrigatório)',
    ]

    # Comentários dos parâmetros
    for i in range(44):
        comentarios.append(f'# Parâmetro {i+1}')

    writer.writerow(comentarios)

    return response


@require_admin_access
@require_http_methods(["POST"])
def processar_importacao_csv(request):
    """
    Processa o arquivo CSV enviado pelo usuário.
    """

    registrar_log('parametros_wallclub.services', "INICIO: Função processar_importacao_csv chamada")

    if 'arquivo_csv' not in request.FILES:
        messages.error(request, 'Nenhum arquivo foi enviado.')
        return redirect('portais_admin:importacao_parametros')

    arquivo = request.FILES['arquivo_csv']

    # Validar tipo de arquivo
    if not arquivo.name.endswith('.csv'):
        messages.error(request, 'Por favor, envie apenas arquivos CSV.')
        return redirect('portais_admin:importacao_parametros')

    # Cria registro de importação
    from datetime import date

    # Debug: verificar se request.user.id existe
    registrar_log('parametros_wallclub.services', f"Usuario ID: {request.user.id if request.user and hasattr(request.user, 'id') else 'NONE'}")

    importacao = ImportacaoConfiguracoes.objects.create(
        nome_arquivo=arquivo.name,
        tamanho_arquivo=arquivo.size,
        data_vigencia=date.today(),
        usuario_id=request.user.id if request.user and request.user.id else 1,
        status='PROCESSANDO'
    )

    registrar_log('parametros_wallclub.services', f"Registro de importação criado com ID: {importacao.id}")

    try:
        resultado = _processar_csv(arquivo, request, importacao)

        # Atualizar registro da importação (se existe)
        if importacao:
            importacao.linhas_processadas = resultado['total_linhas']
            importacao.linhas_importadas = resultado['linhas_importadas']
            importacao.linhas_erro = resultado['linhas_erro']
            importacao.mensagem_erro = resultado['relatorio_erros']
            importacao.status = 'SUCESSO' if resultado['sucesso'] else 'ERRO'
            importacao.save()

        if resultado['sucesso']:
            messages.success(request,
                f"Importação concluída com sucesso! "
                f"{resultado['linhas_importadas']} configurações importadas de {resultado['total_linhas']} linhas processadas.")
        else:
            messages.error(request,
                f"Importação falhou: {resultado['relatorio_erros']}")

    except Exception as e:
        # Marcar importação como erro (se existe)
        if importacao:
            importacao.status = 'ERRO'
            erro_str = str(e)
            # Limitar tamanho para não exceder campo TEXT (65535 chars)
            if len(erro_str) > 65000:
                importacao.mensagem_erro = erro_str[:65000] + '\n... (erro truncado)'
            else:
                importacao.mensagem_erro = erro_str
            importacao.processado_em = datetime.now()
            importacao.save()

        registrar_log('parametros_wallclub.services', f"ERRO GERAL na importação: {str(e)}", nivel='ERROR')
        messages.error(request, f'Erro durante a importação: {str(e)}')

    return redirect('portais_admin:importacao_parametros')


def _processar_csv(arquivo, request, importacao):
    """
    Processa o conteúdo do arquivo CSV.
    """

    resultado = {
        'sucesso': True,
        'total_linhas': 0,
        'linhas_importadas': 0,
        'linhas_erro': 0,
        'relatorio_erros': ''
    }

    erros = []

    try:
        # Ler arquivo
        conteudo = arquivo.read().decode('utf-8-sig')  # Remove BOM se existir
        registrar_log('parametros_wallclub.services', f"INICIO: Processando arquivo, tamanho: {len(conteudo)} bytes")

        # Detectar delimitador automaticamente
        primeira_linha = conteudo.split('\n')[0] if conteudo else ''
        delimiter = ';' if ';' in primeira_linha and primeira_linha.count(';') > primeira_linha.count(',') else ','
        registrar_log('parametros_wallclub.services', f"CSV: Delimitador detectado: '{delimiter}'")

        reader = csv.DictReader(io.StringIO(conteudo), delimiter=delimiter)
        registrar_log('parametros_wallclub.services', f"CSV: Headers encontrados: {reader.fieldnames}")

        with transaction.atomic():
            # Primeiro, identificar todas as lojas no CSV
            lojas_no_csv = set()
            linhas_validas = []

            # Primeira passada: coletar lojas e validar linhas
            for linha_num, row in enumerate(reader, start=2):
                resultado['total_linhas'] += 1

                # Pular linhas de comentário
                if row.get('loja_id', '').startswith('#'):
                    continue

                # Não pular linhas vazias - deixar a validação posterior falhar a importação inteira

                try:
                    loja_id = int(row['loja_id'])
                    lojas_no_csv.add(loja_id)
                    linhas_validas.append((linha_num, row))
                except ValueError:
                    registrar_log('parametros_wallclub.services', f"LINHA {linha_num}: Erro ao converter loja_id para int", nivel='ERROR')
                    continue

            registrar_log('parametros_wallclub.services', f"Primeira passada concluída: {len(linhas_validas)} linhas válidas")

            try:
                # Data de início da vigência - do formulário ou hoje se vazia
                vigencia_inicio_form = request.POST.get('data_vigencia')

                if vigencia_inicio_form:
                    # Converter data do formulário para datetime com hora atual
                    data_form = datetime.strptime(vigencia_inicio_form, '%Y-%m-%d').date()
                    agora = datetime.now()
                    vigencia_inicio = datetime.combine(data_form, agora.time())
                else:
                    vigencia_inicio = datetime.now()
            except Exception as e:
                registrar_log('parametros_wallclub.services', f"ERRO no processamento da data: {str(e)}", nivel='ERROR')
                vigencia_inicio = datetime.now()

            try:
                # Vencer TODAS as configurações ativas das lojas encontradas no CSV
                total_vencidas = 0
                for loja_id in lojas_no_csv:
                    configs_ativas = ParametrosWall.objects.filter(
                        loja_id=loja_id,
                        vigencia_fim__isnull=True  # Configurações ativas
                    )

                    count_vencidas = configs_ativas.update(vigencia_fim=vigencia_inicio)
                    total_vencidas += count_vencidas

                registrar_log('parametros_wallclub.services',
                            f"Vencimento em massa: {total_vencidas} configurações vencidas para {len(lojas_no_csv)} lojas")
            except Exception as e:
                registrar_log('parametros_wallclub.services',
                            f"ERRO no vencimento em massa: {str(e)}", nivel='ERROR')
                raise

            # Segunda passada: processar linhas válidas
            registrar_log('parametros_wallclub.services', f"Iniciando importação de {len(linhas_validas)} configurações...")

            # VALIDAÇÃO PRÉVIA: Verificar se há QUALQUER erro nas linhas (TUDO OU NADA)
            linhas_com_erro = []
            for linha_num, row in linhas_validas:
                try:
                    loja_id = int(row['loja_id'])
                    id_plano = int(row['id_plano'])
                    wall = row['wall'].upper()

                    # Verificar se o plano existe
                    plano_existe = Plano.objects.filter(id=id_plano).exists()
                    if not plano_existe:
                        linhas_com_erro.append(f"Linha {linha_num}: Plano {id_plano} não encontrado")
                        continue

                    # Contar parâmetros definidos
                    parametros_definidos = 0

                    # Validar parâmetros Loja (1 a 33)
                    for i in range(1, 34):
                        campo = f'parametro_loja_{i}'
                        if campo in row and row[campo]:
                            try:
                                if i == 16:  # CharField
                                    valor = str(row[campo])
                                else:  # DecimalField
                                    valor_str = str(row[campo]).strip()
                                    if valor_str != '' and valor_str.lower() != 'null':
                                        Decimal(valor_str)  # Testar conversão
                                parametros_definidos += 1
                            except (ValueError, decimal.InvalidOperation):
                                linhas_com_erro.append(f"Linha {linha_num}: Valor inválido para {campo}: '{row[campo]}'")

                    # Validar parâmetros Uptal (1 a 7)
                    for i in range(1, 8):
                        campo = f'parametro_uptal_{i}'
                        if campo in row and row[campo]:
                            try:
                                valor_str = str(row[campo]).strip()
                                if valor_str != '' and valor_str.lower() != 'null':
                                    Decimal(valor_str)  # Testar conversão
                                parametros_definidos += 1
                            except (ValueError, decimal.InvalidOperation):
                                linhas_com_erro.append(f"Linha {linha_num}: Valor inválido para {campo}: '{row[campo]}'")

                    # Validar parâmetros Wall (1 a 4)
                    for i in range(1, 5):
                        campo = f'parametro_wall_{i}'
                        if campo in row and row[campo]:
                            try:
                                valor_str = str(row[campo]).strip()
                                if valor_str != '' and valor_str.lower() != 'null':
                                    Decimal(valor_str)  # Testar conversão
                                parametros_definidos += 1
                            except (ValueError, decimal.InvalidOperation):
                                linhas_com_erro.append(f"Linha {linha_num}: Valor inválido para {campo}: '{row[campo]}'")

                    # Verificar se todos os parâmetros estão vazios
                    if parametros_definidos == 0:
                        linhas_com_erro.append(f"Linha {linha_num}: Todos os parâmetros estão vazios - Loja {loja_id}, Plano {id_plano}, Wall {wall}")

                except Exception as e:
                    linhas_com_erro.append(f"Linha {linha_num}: Erro de validação - {str(e)}")

            # REGRA: TUDO OU NADA - Se há QUALQUER erro, FALHAR a importação inteira
            if linhas_com_erro:
                registrar_log('parametros_wallclub.services', f"ERRO CRÍTICO: Encontrados {len(linhas_com_erro)} erros na validação", nivel='ERROR')
                for erro in linhas_com_erro:
                    registrar_log('parametros_wallclub.services', f"ERRO: {erro}", nivel='ERROR')

                # Criar mensagem detalhada com os primeiros 3 erros
                detalhes_erro = "; ".join(linhas_com_erro[:3])
                if len(linhas_com_erro) > 3:
                    detalhes_erro += f"; ... e mais {len(linhas_com_erro) - 3} erros"

                raise ValueError(f"Importação cancelada: {len(linhas_com_erro)} erros encontrados. DETALHES: {detalhes_erro}")

            for linha_num, row in linhas_validas:
                try:
                    loja_id = int(row['loja_id'])
                    id_plano = int(row['id_plano'])
                    wall = row['wall'].upper()

                    # Verificar se o plano existe
                    plano_existe = Plano.objects.filter(id=id_plano).exists()

                    if not plano_existe:
                        raise ValueError(f"Plano {id_plano} não encontrado")

                    # Criar nova configuração
                    config = ParametrosWall(
                        loja_id=loja_id,
                        id_plano=id_plano,
                        wall=wall,
                        vigencia_inicio=vigencia_inicio,
                        vigencia_fim=None  # Configuração ativa sem data fim
                    )

                    # Definir parâmetros (sempre definir todos os campos, com 0 se vazio)
                    parametros_definidos = 0
                    for i in range(1, 34):  # Parâmetros Loja (1 a 33)
                        campo = f'parametro_loja_{i}'
                        if campo in row and row[campo]:
                            # Campo 16 é CharField, outros são DecimalField
                            if i == 16:
                                valor = str(row[campo])  # CharField: manter como string
                            else:
                                # CSV deve usar formato americano (0.00) - sem conversão
                                valor_str = str(row[campo]).strip()
                                if valor_str == '' or valor_str.lower() == 'null':
                                    valor = None
                                else:
                                    valor = Decimal(valor_str)  # DecimalField: converter para Decimal
                            setattr(config, campo, valor)
                            parametros_definidos += 1
                            registrar_log('parametros_wallclub.services',
                                        f"DEBUG: {campo} = {valor}")
                        else:
                            setattr(config, campo, None)  # Define como None se vazio

                    for i in range(1, 8):   # Parâmetros Uptal
                        campo = f'parametro_uptal_{i}'
                        if campo in row and row[campo]:
                            # CSV deve usar formato americano (0.00) - sem conversão
                            valor_str = str(row[campo]).strip()
                            if valor_str == '' or valor_str.lower() == 'null':
                                valor = None
                            else:
                                valor = Decimal(valor_str)
                            setattr(config, campo, valor)
                            parametros_definidos += 1
                        else:
                            setattr(config, campo, None)  # Define como None se vazio

                    for i in range(1, 5):   # Parâmetros Wall
                        campo = f'parametro_wall_{i}'
                        if campo in row and row[campo]:
                            # CSV deve usar formato americano (0.00) - sem conversão
                            valor_str = str(row[campo]).strip()
                            if valor_str == '' or valor_str.lower() == 'null':
                                valor = None
                            else:
                                valor = Decimal(valor_str)
                            setattr(config, campo, valor)
                            parametros_definidos += 1
                        else:
                            setattr(config, campo, None)  # Define como None se vazio

                    # DIRETRIZ: OU IMPORTA TUDO OU NADA
                    # Se todos os parâmetros estão vazios, FALHAR a importação
                    if parametros_definidos == 0:
                        erro_msg = f"Linha {linha_num}: Todos os parâmetros estão vazios - Loja {loja_id}, Plano {id_plano}, Wall {wall}"
                        registrar_log('parametros_wallclub.services', f"ERRO CRÍTICO: {erro_msg}", nivel='ERROR')
                        raise ValueError(erro_msg)

                    # Salvar
                    try:
                        config.save()
                        resultado['linhas_importadas'] += 1
                    except Exception as save_error:
                        registrar_log('parametros_wallclub.services',
                                    f"ERRO NO SALVAMENTO: Linha {linha_num}, Loja {loja_id}, Plano {id_plano}, Wall {wall} - {str(save_error)}", nivel='ERROR')
                        raise save_error

                except Exception as e:
                    resultado['linhas_erro'] += 1
                    erros.append(f"Linha {linha_num}: {str(e)}")

            # Log de resumo após processamento
            registrar_log('parametros_wallclub.services',
                        f"Importação concluída: {resultado['linhas_importadas']} configurações importadas com sucesso")

    except Exception as e:
        resultado['sucesso'] = False
        erros.append(f"Erro geral: {str(e)}")

    # Compilar relatório de erros
    if erros:
        relatorio_completo = '\n'.join(erros)
        # Limitar tamanho para não exceder campo TEXT (65535 chars)
        if len(relatorio_completo) > 65000:
            resultado['relatorio_erros'] = relatorio_completo[:65000] + '\n... (relatório truncado - muitos erros)'
        else:
            resultado['relatorio_erros'] = relatorio_completo
        if resultado['linhas_erro'] > 0:
            resultado['sucesso'] = False

    return resultado


@require_admin_access
def visualizar_importacao(request, importacao_id):
    """
    Visualiza detalhes de uma importação específica.
    """
    # Buscar importação via API
    importacao = parametros_api.obter_importacao(importacao_id)
    if not importacao:
        messages.error(request, 'Importação não encontrada')
        return redirect('portais_admin:importacao_list')

    context = {
        'importacao': importacao,
    }

    return render(request, 'portais/admin/importacao_detalhes.html', context)
