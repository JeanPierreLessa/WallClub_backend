"""
Views para gestão de lojas com integração Own Financial
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.http import JsonResponse

from portais.controle_acesso import require_funcionalidade
from adquirente_own.services_cadastro import CadastroOwnService
from adquirente_own.services_consultas import ConsultasOwnService
from adquirente_own.models_cadastro import LojaOwn, LojaDocumentos
from wallclub_core.utilitarios.log_control import registrar_log


@require_funcionalidade('hierarquia_create')
@require_http_methods(["GET", "POST"])
def cadastrar_loja(request):
    """View para cadastrar nova loja"""

    if request.method == 'GET':
        return render(request, 'admin/cadastro_loja_own.html')

    # POST - processar cadastro
    try:
        with transaction.atomic():
            # Extrair dados do formulário
            loja_data = {
                # Dados básicos
                'cnpj': request.POST.get('cnpj'),
                'razao_social': request.POST.get('razao_social'),
                'nome_fantasia': request.POST.get('nome_fantasia'),
                'email': request.POST.get('email'),

                # Contato
                'ddd_telefone_comercial': request.POST.get('ddd_telefone_comercial'),
                'telefone_comercial': request.POST.get('telefone_comercial'),
                'ddd_celular': request.POST.get('ddd_celular'),
                'celular': request.POST.get('celular'),

                # Endereço
                'cep': request.POST.get('cep'),
                'logradouro': request.POST.get('logradouro'),
                'numero_endereco': request.POST.get('numero_endereco'),
                'complemento': request.POST.get('complemento', ''),
                'bairro': request.POST.get('bairro'),
                'municipio': request.POST.get('municipio'),
                'uf': request.POST.get('uf'),

                # Dados bancários
                'codigo_banco': request.POST.get('codigo_banco'),
                'agencia': request.POST.get('agencia'),
                'digito_agencia': request.POST.get('digito_agencia', ''),
                'numero_conta': request.POST.get('numero_conta'),
                'digito_conta': request.POST.get('digito_conta'),
            }

            # TODO: Criar registro na tabela Loja (modelo principal)
            # Por enquanto, vamos simular com loja_id = 1
            loja_id = 1

            # Verificar se deve cadastrar na Own
            cadastrar_own = request.POST.get('cadastrar_own') == '1'

            if cadastrar_own:
                # Adicionar dados específicos da Own
                loja_data.update({
                    'cnae': request.POST.get('cnae'),
                    'ramo_atividade': request.POST.get('ramo_atividade'),
                    'mcc': request.POST.get('mcc'),
                    'faturamento_previsto': request.POST.get('faturamento_previsto'),
                    'faturamento_contratado': request.POST.get('faturamento_contratado'),
                    'id_cesta': request.POST.get('id_cesta'),
                    'responsavel_assinatura': request.POST.get('responsavel_assinatura'),
                    'quantidade_pos': request.POST.get('quantidade_pos', 1),
                    'antecipacao_automatica': request.POST.get('antecipacao_automatica', 'N'),
                    'taxa_antecipacao': request.POST.get('taxa_antecipacao', 0),
                    'tipo_antecipacao': 'ROTATIVO',
                    'tarifacao': []  # TODO: Montar lista de tarifas
                })

                # Cadastrar na Own
                service = CadastroOwnService(environment='LIVE')
                resultado = service.cadastrar_estabelecimento(loja_id, loja_data)

                if resultado.get('sucesso'):
                    messages.success(
                        request,
                        f'Loja cadastrada com sucesso! Protocolo Own: {resultado.get("protocolo")}'
                    )
                else:
                    messages.warning(
                        request,
                        f'Loja cadastrada, mas houve erro ao cadastrar na Own: {resultado.get("mensagem")}'
                    )
            else:
                messages.success(request, 'Loja cadastrada com sucesso!')

            return redirect('portais_admin:lista_lojas')

    except Exception as e:
        registrar_log('admin.lojas', f'❌ Erro ao cadastrar loja: {str(e)}', nivel='ERROR')
        messages.error(request, f'Erro ao cadastrar loja: {str(e)}')
        return render(request, 'admin/cadastro_loja_own.html')


@require_funcionalidade('hierarquia_edit')
@require_http_methods(["GET", "POST"])
def editar_loja(request, loja_id):
    """View para editar loja existente"""

    # TODO: Buscar loja do banco de dados
    # loja = get_object_or_404(Loja, id=loja_id)

    if request.method == 'GET':
        # Buscar status Own se existir
        try:
            loja_own = LojaOwn.objects.filter(loja_id=loja_id).first()
        except:
            loja_own = None

        context = {
            # 'loja': loja,
            'loja_own': loja_own,
            'loja_id': loja_id
        }

        return render(request, 'admin/editar_loja_own.html', context)

    # POST - processar edição
    # Similar ao cadastro
    pass


@require_funcionalidade('hierarquia_edit')
@require_http_methods(["POST"])
def cadastrar_loja_own_posterior(request, loja_id):
    """Cadastra uma loja existente na Own Financial"""

    try:
        # TODO: Buscar loja do banco
        # loja = get_object_or_404(Loja, id=loja_id)

        # Verificar se já está cadastrada
        loja_own = LojaOwn.objects.filter(loja_id=loja_id).first()
        if loja_own and loja_own.conveniada_id:
            messages.warning(request, 'Esta loja já está cadastrada na Own')
            return redirect('portais_admin:editar_loja', loja_id=loja_id)

        # Extrair dados do formulário (similar ao cadastro)
        loja_data = {
            # ... preencher com dados da loja e do formulário
        }

        # Cadastrar na Own
        service = CadastroOwnService(environment='LIVE')
        resultado = service.cadastrar_estabelecimento(loja_id, loja_data)

        if resultado.get('sucesso'):
            messages.success(
                request,
                f'Loja cadastrada na Own com sucesso! Protocolo: {resultado.get("protocolo")}'
            )
        else:
            messages.error(
                request,
                f'Erro ao cadastrar na Own: {resultado.get("mensagem")}'
            )

        return redirect('portais_admin:editar_loja', loja_id=loja_id)

    except Exception as e:
        registrar_log('admin.lojas', f'❌ Erro ao cadastrar loja na Own: {str(e)}', nivel='ERROR')
        messages.error(request, f'Erro ao cadastrar na Own: {str(e)}')
        return redirect('portais_admin:editar_loja', loja_id=loja_id)


@require_funcionalidade('hierarquia_list')
def status_credenciamento_own(request, loja_id):
    """Retorna status de credenciamento da loja na Own (AJAX)"""

    try:
        loja_own = LojaOwn.objects.filter(loja_id=loja_id).first()

        if not loja_own:
            return JsonResponse({
                'cadastrado': False,
                'mensagem': 'Loja não cadastrada na Own'
            })

        return JsonResponse({
            'cadastrado': True,
            'status': loja_own.status_credenciamento,
            'protocolo': loja_own.protocolo,
            'conveniada_id': loja_own.conveniada_id,
            'data_credenciamento': loja_own.data_credenciamento.isoformat() if loja_own.data_credenciamento else None,
            'mensagem_status': loja_own.mensagem_status,
            'sincronizado': loja_own.sincronizado,
            'ultima_sincronizacao': loja_own.ultima_sincronizacao.isoformat() if loja_own.ultima_sincronizacao else None
        })

    except Exception as e:
        registrar_log('admin.lojas', f'❌ Erro ao consultar status Own: {str(e)}', nivel='ERROR')
        return JsonResponse({
            'erro': str(e)
        }, status=500)
