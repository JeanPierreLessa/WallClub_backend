"""
Views para Revisão Manual de Transações Antifraude
"""
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from portais.controle_acesso.decorators import require_admin_access
from wallclub_core.utilitarios.log_control import registrar_log
from .services_antifraude import AntifraudeService


@require_admin_access
@require_http_methods(['GET'])
def antifraude_dashboard(request):
    """
    Dashboard principal de antifraude com métricas
    
    GET /admin/antifraude/?dias=7
    """
    try:
        # Parâmetro de dias (padrão: 7)
        dias = int(request.GET.get('dias', 7))
        
        # Buscar métricas completas
        metricas = AntifraudeService.obter_metricas_dashboard(dias=dias)
        
        context = {
            'metricas': metricas,
            'dias_selecionado': dias,
            'usuario_nome': request.session.get('portal_usuario_nome', 'Usuário'),
        }
        
        return render(request, 'portais/admin/antifraude_dashboard.html', context)
        
    except Exception as e:
        registrar_log('portais.admin', f'Erro no dashboard antifraude: {str(e)}', nivel='ERROR')
        context = {
            'erro': 'Erro ao carregar dashboard',
            'metricas': AntifraudeService._metricas_vazias(),
            'dias_selecionado': 7
        }
        return render(request, 'portais/admin/antifraude_dashboard.html', context)


@require_admin_access
@require_http_methods(['GET'])
def antifraude_pendentes(request):
    """
    Lista de transações pendentes de revisão
    
    GET /admin/antifraude/pendentes/
    """
    try:
        # Buscar pendentes
        resultado = AntifraudeService.listar_pendentes()
        
        context = {
            'pendentes': resultado.get('pendentes', []),
            'total': resultado.get('total', 0),
            'erro_conexao': resultado.get('erro_conexao', False),
            'usuario_nome': request.session.get('portal_usuario_nome', 'Usuário'),
        }
        
        return render(request, 'portais/admin/antifraude_pendentes.html', context)
        
    except Exception as e:
        registrar_log('portais.admin', f'Erro ao listar pendentes: {str(e)}', nivel='ERROR')
        context = {
            'erro': 'Erro ao carregar transações pendentes',
            'pendentes': [],
            'total': 0,
            'erro_conexao': True
        }
        return render(request, 'portais/admin/antifraude_pendentes.html', context)


@require_admin_access
@require_http_methods(['GET'])
def antifraude_historico(request):
    """
    Histórico de revisões realizadas
    
    GET /admin/antifraude/historico/
    """
    try:
        # Parâmetros
        limit = int(request.GET.get('limit', 50))
        
        # Buscar histórico
        resultado = AntifraudeService.listar_historico(limit=limit)
        
        context = {
            'revisoes': resultado.get('revisoes', []),
            'total': resultado.get('total', 0),
            'limit': limit,
            'erro_conexao': resultado.get('erro_conexao', False),
            'usuario_nome': request.session.get('portal_usuario_nome', 'Usuário'),
        }
        
        return render(request, 'portais/admin/antifraude_historico.html', context)
        
    except Exception as e:
        registrar_log('portais.admin', f'Erro ao listar histórico: {str(e)}', nivel='ERROR')
        context = {
            'erro': 'Erro ao carregar histórico',
            'revisoes': [],
            'total': 0,
            'erro_conexao': True
        }
        return render(request, 'portais/admin/antifraude_historico.html', context)


@require_admin_access
@require_http_methods(['POST'])
def antifraude_aprovar(request):
    """
    Aprova transação via AJAX
    
    POST /admin/antifraude/aprovar/
    
    Body JSON:
    {
        "decisao_id": 123,
        "observacao": "Cliente verificado por telefone"
    }
    """
    try:
        import json
        
        # Parse JSON body
        data = json.loads(request.body)
        decisao_id = data.get('decisao_id')
        observacao = data.get('observacao', '')
        
        if not decisao_id:
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'decisao_id é obrigatório'
            }, status=400)
        
        # Obter ID do usuário logado
        usuario_id = request.session.get('portal_usuario_id')
        
        if not usuario_id:
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'Usuário não identificado'
            }, status=401)
        
        # Aprovar
        resultado = AntifraudeService.aprovar_transacao(
            decisao_id=int(decisao_id),
            usuario_id=int(usuario_id),
            observacao=observacao
        )
        
        return JsonResponse(resultado)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'sucesso': False,
            'mensagem': 'JSON inválido'
        }, status=400)
    except Exception as e:
        registrar_log('portais.admin', f'Erro ao aprovar transação: {str(e)}', nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro ao processar aprovação: {str(e)}'
        }, status=500)


@require_admin_access
@require_http_methods(['POST'])
def antifraude_reprovar(request):
    """
    Reprova transação via AJAX
    
    POST /admin/antifraude/reprovar/
    
    Body JSON:
    {
        "decisao_id": 123,
        "observacao": "CPF em blacklist"
    }
    """
    try:
        import json
        
        # Parse JSON body
        data = json.loads(request.body)
        decisao_id = data.get('decisao_id')
        observacao = data.get('observacao', '')
        
        if not decisao_id:
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'decisao_id é obrigatório'
            }, status=400)
        
        # Obter ID do usuário logado
        usuario_id = request.session.get('portal_usuario_id')
        
        if not usuario_id:
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'Usuário não identificado'
            }, status=401)
        
        # Reprovar
        resultado = AntifraudeService.reprovar_transacao(
            decisao_id=int(decisao_id),
            usuario_id=int(usuario_id),
            observacao=observacao
        )
        
        return JsonResponse(resultado)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'sucesso': False,
            'mensagem': 'JSON inválido'
        }, status=400)
    except Exception as e:
        registrar_log('portais.admin', f'Erro ao reprovar transação: {str(e)}', nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro ao processar reprovação: {str(e)}'
        }, status=500)
