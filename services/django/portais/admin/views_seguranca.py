"""
Views de Segurança - Atividades Suspeitas e Bloqueios
Portal Admin - Fase 4 - Semana 23
"""
import requests
import json
import logging
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.core.paginator import Paginator
from datetime import datetime

from portais.controle_acesso.decorators import require_admin_access

logger = logging.getLogger('wallclub.admin.seguranca')


def get_risk_engine_token():
    """
    Obtém token OAuth para autenticar com Risk Engine
    """
    from django.core.cache import cache
    
    token = cache.get('risk_engine_oauth_token')
    if token:
        return token
    
    try:
        oauth_url = getattr(settings, 'RISK_ENGINE_URL', 'http://wallclub-riskengine:8000')
        token_url = f"{oauth_url}/oauth/token/"
        
        # Usar credenciais ADMIN específicas para Portal Admin
        client_id = getattr(settings, 'RISK_ENGINE_ADMIN_CLIENT_ID', 'wallclub-django')
        client_secret = getattr(settings, 'RISK_ENGINE_ADMIN_CLIENT_SECRET', '')
        
        response = requests.post(
            token_url,
            json={
                'grant_type': 'client_credentials',
                'client_id': client_id,
                'client_secret': client_secret
            },
            timeout=3
        )
        
        if response.status_code == 200:
            data = response.json()
            token = data.get('access_token')
            expires_in = data.get('expires_in', 3600)
            cache.set('risk_engine_oauth_token', token, expires_in * 0.9)
            return token
        else:
            logger.error(f"Erro ao obter token: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"Erro ao gerar token: {str(e)}")
        return None


@require_admin_access
def atividades_suspeitas(request):
    """
    Lista atividades suspeitas detectadas pelo Risk Engine
    """
    try:
        # Parâmetros de filtro
        status = request.GET.get('status', 'pendente')
        tipo = request.GET.get('tipo', '')
        portal = request.GET.get('portal', '')
        dias = request.GET.get('dias', '7')
        
        # Chamar API do Risk Engine
        risk_engine_url = getattr(settings, 'RISK_ENGINE_URL', 'http://wallclub-riskengine:8000')
        api_url = f"{risk_engine_url}/api/antifraude/suspicious/"
        
        token = get_risk_engine_token()
        if not token:
            messages.error(request, 'Erro ao conectar com Risk Engine')
            return render(request, 'admin/seguranca/atividades_suspeitas.html', {
                'atividades': [],
                'erro_conexao': True
            })
        
        headers = {'Authorization': f'Bearer {token}'}
        params = {
            'status': status,
            'dias': dias
        }
        if tipo:
            params['tipo'] = tipo
        if portal:
            params['portal'] = portal
        
        response = requests.get(api_url, headers=headers, params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            atividades = data.get('atividades', [])
            total = data.get('total', 0)
            pendentes = data.get('pendentes', 0)
            
            # Paginação
            paginator = Paginator(atividades, 25)
            page_number = request.GET.get('page', 1)
            page_obj = paginator.get_page(page_number)
            
            context = {
                'atividades': page_obj,
                'total': total,
                'pendentes': pendentes,
                'filtros': {
                    'status': status,
                    'tipo': tipo,
                    'portal': portal,
                    'dias': dias
                },
                'tipos_disponiveis': [
                    ('login_multiplo', 'Múltiplos Logins'),
                    ('tentativa_falha', 'Tentativas Falhas'),
                    ('ip_novo', 'IP Novo'),
                    ('horario_suspeito', 'Horário Suspeito'),
                    ('velocidade_transacao', 'Velocidade Anormal'),
                ],
                'portais_disponiveis': [
                    ('admin', 'Admin'),
                    ('lojista', 'Lojista'),
                    ('vendas', 'Vendas'),
                    ('app', 'App'),
                ],
                'status_disponiveis': [
                    ('pendente', 'Pendente'),
                    ('investigado', 'Investigado'),
                    ('bloqueado', 'Bloqueado'),
                    ('falso_positivo', 'Falso Positivo'),
                    ('ignorado', 'Ignorado'),
                ]
            }
            
            return render(request, 'admin/seguranca/atividades_suspeitas.html', context)
        else:
            messages.error(request, f'Erro ao buscar atividades: {response.status_code}')
            return render(request, 'admin/seguranca/atividades_suspeitas.html', {
                'atividades': [],
                'erro_api': True
            })
            
    except requests.Timeout:
        messages.error(request, 'Timeout ao conectar com Risk Engine')
        return render(request, 'admin/seguranca/atividades_suspeitas.html', {
            'atividades': [],
            'erro_timeout': True
        })
    except Exception as e:
        logger.error(f"Erro em atividades_suspeitas: {str(e)}")
        messages.error(request, f'Erro: {str(e)}')
        return render(request, 'admin/seguranca/atividades_suspeitas.html', {
            'atividades': [],
            'erro_geral': True
        })


@require_admin_access
def investigar_atividade(request, atividade_id):
    """
    Investiga uma atividade suspeita e toma ação
    """
    if request.method != 'POST':
        return redirect('admin_atividades_suspeitas')
    
    try:
        acao = request.POST.get('acao')
        observacoes = request.POST.get('observacoes', '')
        
        # Validar ação
        acoes_validas = ['marcar_investigado', 'bloquear_ip', 'bloquear_cpf', 'falso_positivo', 'ignorar']
        if acao not in acoes_validas:
            messages.error(request, 'Ação inválida')
            return redirect('admin_atividades_suspeitas')
        
        # Chamar API do Risk Engine
        risk_engine_url = getattr(settings, 'RISK_ENGINE_URL', 'http://wallclub-riskengine:8000')
        api_url = f"{risk_engine_url}/api/antifraude/investigate/"
        
        token = get_risk_engine_token()
        if not token:
            messages.error(request, 'Erro ao conectar com Risk Engine')
            return redirect('admin_atividades_suspeitas')
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'atividade_id': int(atividade_id),
            'acao': acao,
            'usuario_id': request.user.id if hasattr(request, 'user') else None,
            'observacoes': observacoes
        }
        
        response = requests.post(api_url, headers=headers, json=payload, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            
            # Mensagens de sucesso
            mensagens_acao = {
                'marcar_investigado': 'Atividade marcada como investigada',
                'bloquear_ip': f"IP bloqueado com sucesso (Bloqueio #{data.get('bloqueio_criado_id')})",
                'bloquear_cpf': f"CPF bloqueado com sucesso (Bloqueio #{data.get('bloqueio_criado_id')})",
                'falso_positivo': 'Atividade marcada como falso positivo',
                'ignorar': 'Atividade ignorada'
            }
            
            messages.success(request, mensagens_acao.get(acao, 'Ação executada com sucesso'))
            logger.info(f"✅ Ação '{acao}' executada na atividade #{atividade_id} por usuário #{request.user.id if hasattr(request, 'user') else 'N/A'}")
        else:
            error_data = response.json() if response.content else {}
            messages.error(request, f"Erro: {error_data.get('error', 'Erro desconhecido')}")
            logger.error(f"Erro ao investigar atividade: {response.status_code} - {error_data}")
        
        return redirect('admin_atividades_suspeitas')
        
    except Exception as e:
        logger.error(f"Erro em investigar_atividade: {str(e)}")
        messages.error(request, f'Erro: {str(e)}')
        return redirect('admin_atividades_suspeitas')


@require_admin_access
def bloqueios_seguranca(request):
    """
    Lista bloqueios de segurança (IPs e CPFs bloqueados)
    """
    try:
        # Parâmetros de filtro
        tipo = request.GET.get('tipo', '')
        ativo = request.GET.get('ativo', 'true')
        dias = request.GET.get('dias', '30')
        
        # Chamar API do Risk Engine
        risk_engine_url = getattr(settings, 'RISK_ENGINE_URL', 'http://wallclub-riskengine:8000')
        api_url = f"{risk_engine_url}/api/antifraude/blocks/"
        
        token = get_risk_engine_token()
        if not token:
            messages.error(request, 'Erro ao conectar com Risk Engine')
            return render(request, 'admin/seguranca/bloqueios.html', {
                'bloqueios': [],
                'erro_conexao': True
            })
        
        headers = {'Authorization': f'Bearer {token}'}
        params = {'dias': dias}
        if tipo:
            params['tipo'] = tipo
        if ativo:
            params['ativo'] = ativo
        
        response = requests.get(api_url, headers=headers, params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            bloqueios = data.get('bloqueios', [])
            total = data.get('total', 0)
            
            # Paginação
            paginator = Paginator(bloqueios, 25)
            page_number = request.GET.get('page', 1)
            page_obj = paginator.get_page(page_number)
            
            context = {
                'bloqueios': page_obj,
                'total': total,
                'filtros': {
                    'tipo': tipo,
                    'ativo': ativo,
                    'dias': dias
                }
            }
            
            return render(request, 'admin/seguranca/bloqueios.html', context)
        else:
            messages.error(request, f'Erro ao buscar bloqueios: {response.status_code}')
            return render(request, 'admin/seguranca/bloqueios.html', {
                'bloqueios': [],
                'erro_api': True
            })
            
    except Exception as e:
        logger.error(f"Erro em bloqueios_seguranca: {str(e)}")
        messages.error(request, f'Erro: {str(e)}')
        return render(request, 'admin/seguranca/bloqueios.html', {
            'bloqueios': [],
            'erro_geral': True
        })


@require_admin_access
def criar_bloqueio(request):
    """
    Cria um bloqueio manual de IP ou CPF
    """
    if request.method != 'POST':
        return redirect('admin_bloqueios_seguranca')
    
    try:
        tipo = request.POST.get('tipo')
        valor = request.POST.get('valor')
        motivo = request.POST.get('motivo')
        portal = request.POST.get('portal', '')
        
        # Validações
        if tipo not in ['ip', 'cpf']:
            messages.error(request, 'Tipo deve ser IP ou CPF')
            return redirect('admin_bloqueios_seguranca')
        
        if not valor or not motivo:
            messages.error(request, 'Valor e motivo são obrigatórios')
            return redirect('admin_bloqueios_seguranca')
        
        # Chamar API do Risk Engine
        risk_engine_url = getattr(settings, 'RISK_ENGINE_URL', 'http://wallclub-riskengine:8000')
        api_url = f"{risk_engine_url}/api/antifraude/block/"
        
        token = get_risk_engine_token()
        if not token:
            messages.error(request, 'Erro ao conectar com Risk Engine')
            return redirect('admin_bloqueios_seguranca')
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'tipo': tipo,
            'valor': valor,
            'motivo': motivo,
            'bloqueado_por': f"admin_{request.user.username if hasattr(request, 'user') else 'sistema'}",
            'portal': portal
        }
        
        response = requests.post(api_url, headers=headers, json=payload, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            messages.success(request, f"Bloqueio criado com sucesso (ID: {data.get('bloqueio_id')})")
            logger.warning(f"🚫 Bloqueio manual criado - {tipo.upper()}: {valor} por {payload['bloqueado_por']}")
        else:
            error_data = response.json() if response.content else {}
            messages.error(request, f"Erro: {error_data.get('error', 'Erro desconhecido')}")
            logger.error(f"Erro ao criar bloqueio: {response.status_code} - {error_data}")
        
        return redirect('admin_bloqueios_seguranca')
        
    except Exception as e:
        logger.error(f"Erro em criar_bloqueio: {str(e)}")
        messages.error(request, f'Erro: {str(e)}')
        return redirect('admin_bloqueios_seguranca')
