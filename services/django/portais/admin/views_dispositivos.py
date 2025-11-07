"""
Views para gestão de dispositivos confiáveis - Portal Admin
"""
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Count
from portais.admin.decorators import admin_required
from wallclub_core.seguranca.models import DispositivoConfiavel
from wallclub_core.seguranca.services_device import DeviceManagementService
from wallclub_core.utilitarios.log_control import registrar_log


@admin_required
def listar_dispositivos(request):
    """
    GET /admin/dispositivos/
    Lista todos os dispositivos cadastrados com filtros
    """
    if request.method != 'GET':
        return JsonResponse({'erro': 'Método não permitido'}, status=405)
    
    try:
        # Parâmetros de filtro
        tipo_usuario = request.GET.get('tipo_usuario', '')
        status = request.GET.get('status', '')  # ativo, inativo, expirado
        user_id = request.GET.get('user_id', '')
        
        # Query base
        query = DispositivoConfiavel.objects.all()
        
        # Aplicar filtros
        if tipo_usuario:
            query = query.filter(tipo_usuario=tipo_usuario)
        
        if status == 'ativo':
            query = query.filter(ativo=True)
        elif status == 'inativo':
            query = query.filter(ativo=False)
        # TODO: filtro 'expirado' requer lógica adicional com confiavel_ate
        
        if user_id:
            query = query.filter(user_id=user_id)
        
        # Ordenar por último acesso
        dispositivos = query.select_related().order_by('-ultimo_acesso')[:200]
        
        # Formatar resposta
        resultado = []
        for disp in dispositivos:
            # Verificar se expirado
            expirado = False
            dias_restantes = None
            
            if disp.confiavel_ate:
                from datetime import datetime
                dias_restantes = (disp.confiavel_ate - datetime.now()).days
                expirado = dias_restantes < 0
            
            resultado.append({
                'id': disp.id,
                'user_id': disp.user_id,
                'tipo_usuario': disp.tipo_usuario,
                'nome_dispositivo': disp.nome_dispositivo,
                'fingerprint': disp.device_fingerprint[:16] + '...',
                'ip_registro': disp.ip_registro,
                'ultimo_acesso': disp.ultimo_acesso.strftime('%d/%m/%Y %H:%M'),
                'ativo': disp.ativo,
                'confiavel': disp.esta_confiavel(),
                'expirado': expirado,
                'dias_restantes': dias_restantes if dias_restantes and dias_restantes > 0 else 0,
                'criado_em': disp.criado_em.strftime('%d/%m/%Y %H:%M'),
                'revogado_em': disp.revogado_em.strftime('%d/%m/%Y %H:%M') if disp.revogado_em else None,
                'revogado_por': disp.revogado_por
            })
        
        registrar_log('portais.admin', f"Listados {len(resultado)} dispositivos")
        
        return JsonResponse({
            'sucesso': True,
            'dispositivos': resultado,
            'total': len(resultado)
        })
        
    except Exception as e:
        registrar_log('portais.admin', f"Erro ao listar dispositivos: {str(e)}", nivel='ERROR')
        return JsonResponse({'erro': str(e)}, status=500)


@admin_required
@require_http_methods(["POST"])
def revogar_dispositivo(request):
    """
    POST /admin/dispositivos/revogar/
    Revoga dispositivo remotamente (admin)
    
    Body: {"dispositivo_id": 123}
    """
    try:
        import json
        body = json.loads(request.body)
        dispositivo_id = body.get('dispositivo_id')
        
        if not dispositivo_id:
            return JsonResponse({'erro': 'dispositivo_id é obrigatório'}, status=400)
        
        # Revogar dispositivo
        sucesso, mensagem = DeviceManagementService.revogar_dispositivo(
            dispositivo_id=dispositivo_id,
            revogado_por='admin'
        )
        
        if sucesso:
            registrar_log('portais.admin', f"Dispositivo revogado: ID {dispositivo_id}")
            return JsonResponse({'sucesso': True, 'mensagem': mensagem})
        else:
            return JsonResponse({'erro': mensagem}, status=400)
        
    except json.JSONDecodeError:
        return JsonResponse({'erro': 'JSON inválido'}, status=400)
    except Exception as e:
        registrar_log('portais.admin', f"Erro ao revogar dispositivo: {str(e)}", nivel='ERROR')
        return JsonResponse({'erro': str(e)}, status=500)


@admin_required
@require_http_methods(["POST"])
def revogar_todos_dispositivos_usuario(request):
    """
    POST /admin/dispositivos/revogar-todos/
    Revoga TODOS os dispositivos de um usuário
    
    Body: {"user_id": 123, "tipo_usuario": "cliente"}
    """
    try:
        import json
        body = json.loads(request.body)
        user_id = body.get('user_id')
        tipo_usuario = body.get('tipo_usuario')
        
        if not user_id or not tipo_usuario:
            return JsonResponse({'erro': 'user_id e tipo_usuario são obrigatórios'}, status=400)
        
        # Revogar todos
        quantidade, mensagem = DeviceManagementService.revogar_todos_dispositivos(
            user_id=user_id,
            tipo_usuario=tipo_usuario,
            revogado_por='admin'
        )
        
        registrar_log(
            'portais.admin.dispositivos',
            f"Todos dispositivos revogados: {tipo_usuario} ID:{user_id} - {quantidade} dispositivos"
        )
        
        return JsonResponse({
            'sucesso': True,
            'mensagem': mensagem,
            'quantidade': quantidade
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'erro': 'JSON inválido'}, status=400)
    except Exception as e:
        registrar_log('portais.admin', f"Erro ao revogar todos dispositivos: {str(e)}", nivel='ERROR')
        return JsonResponse({'erro': str(e)}, status=500)


@admin_required
def dashboard_dispositivos(request):
    """
    GET /admin/dispositivos/dashboard/
    Retorna estatísticas de dispositivos para dashboard
    """
    if request.method != 'GET':
        return JsonResponse({'erro': 'Método não permitido'}, status=405)
    
    try:
        from datetime import datetime, timedelta
        from django.db.models import Count, Q
        
        # Total de dispositivos ativos
        total_ativos = DispositivoConfiavel.objects.filter(ativo=True).count()
        
        # Total de dispositivos inativos/revogados
        total_revogados = DispositivoConfiavel.objects.filter(ativo=False).count()
        
        # Dispositivos por tipo de usuário
        por_tipo = DispositivoConfiavel.objects.filter(ativo=True).values('tipo_usuario').annotate(
            total=Count('id')
        ).order_by('-total')
        
        dispositivos_por_tipo = {item['tipo_usuario']: item['total'] for item in por_tipo}
        
        # Dispositivos expirados (confiavel_ate < now)
        dispositivos_expirados = DispositivoConfiavel.objects.filter(
            ativo=True,
            confiavel_ate__lt=datetime.now()
        ).count()
        
        # Novos dispositivos nas últimas 24h
        ontem = datetime.now() - timedelta(days=1)
        novos_24h = DispositivoConfiavel.objects.filter(criado_em__gte=ontem).count()
        
        # Dispositivos revogados nas últimas 24h
        revogados_24h = DispositivoConfiavel.objects.filter(
            revogado_em__gte=ontem
        ).count()
        
        # Tentativas de login bloqueadas (dispositivos que tentaram acessar além do limite)
        # TODO: Isso requer tabela de auditoria de tentativas bloqueadas
        tentativas_bloqueadas = 0  # Placeholder
        
        resultado = {
            'total_ativos': total_ativos,
            'total_revogados': total_revogados,
            'total_expirados': dispositivos_expirados,
            'novos_24h': novos_24h,
            'revogados_24h': revogados_24h,
            'tentativas_bloqueadas': tentativas_bloqueadas,
            'por_tipo': dispositivos_por_tipo
        }
        
        registrar_log('portais.admin', "Dashboard de dispositivos consultado")
        
        return JsonResponse({
            'sucesso': True,
            'dados': resultado
        })
        
    except Exception as e:
        registrar_log('portais.admin', f"Erro ao gerar dashboard: {str(e)}", nivel='ERROR')
        return JsonResponse({'erro': str(e)}, status=500)


@admin_required
def buscar_dispositivos_usuario(request):
    """
    GET /admin/dispositivos/usuario/?user_id=123&tipo_usuario=cliente
    Busca dispositivos de um usuário específico
    """
    if request.method != 'GET':
        return JsonResponse({'erro': 'Método não permitido'}, status=405)
    
    try:
        user_id = request.GET.get('user_id')
        tipo_usuario = request.GET.get('tipo_usuario')
        
        if not user_id or not tipo_usuario:
            return JsonResponse({'erro': 'user_id e tipo_usuario são obrigatórios'}, status=400)
        
        # Listar dispositivos do usuário
        dispositivos = DeviceManagementService.listar_dispositivos(
            user_id=int(user_id),
            tipo_usuario=tipo_usuario,
            apenas_ativos=False  # Mostrar todos
        )
        
        registrar_log(
            'portais.admin.dispositivos',
            f"Dispositivos do usuário consultados: {tipo_usuario} ID:{user_id} - {len(dispositivos)} encontrados"
        )
        
        return JsonResponse({
            'sucesso': True,
            'dispositivos': dispositivos,
            'total': len(dispositivos)
        })
        
    except Exception as e:
        registrar_log('portais.admin', f"Erro ao buscar dispositivos do usuário: {str(e)}", nivel='ERROR')
        return JsonResponse({'erro': str(e)}, status=500)
