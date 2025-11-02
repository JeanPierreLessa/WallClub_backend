"""Views do app principal."""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from wallclub_core.oauth.decorators import require_oauth_apps
from apps.conta_digital.decorators import require_jwt_only

# Views de autenticação foram movidas para apps.cliente
# Este arquivo agora contém apenas views não relacionadas à autenticação

@api_view(['GET'])
def health_check(request):
    """
    Health check da API
    """
    return Response({
        "status": "ok",
        "message": "API funcionando",
        "version": "1.0.0"
    })

@api_view(['POST'])
@require_oauth_apps
def versao_minima(request):
    """
    Retorna versão mínima dos apps mobile baseado no canal_id

    Body (JSON):
    {
        "canal_id": 6
    }
    """
    canal_id = request.data.get('canal_id', 1)

    # URLs diferentes por canal
    urls_por_canal = {
        1: {
            "url_android": "https://play.google.com/store/apps/details?id=com.wallclub.app&pli=1",
            "url_ios": "https://apps.apple.com/br/app/wall-club/id6480528775"
        },
        6: {
            "url_android": "https://play.google.com/store/apps/details?id=com.agroclub.app",
            "url_ios": "https://apps.apple.com/us/app/a-club/id6738631662"
        },
        # Adicionar outros canais conforme necessário
    }

    # URLs padrão caso canal não seja encontrado
    urls = urls_por_canal.get(canal_id, urls_por_canal[1])

    return Response({
        "versao_minima_android": "3.1.0",
        "versao_minima_ios": "3.1.0",
        "forca_atualizacao": True,
        "mensagem": "Uma nova versão está disponível. Atualize para continuar usando o app.",
        "canal_id": canal_id,
        **urls
    })

@api_view(['POST'])
@require_jwt_only
def feature_flag(request):
    """
    Retorna features habilitadas baseado na versão da aplicação e cliente

    Body (JSON):
    {
        "versao": "3.1.0"
    }
    
    Nota: cliente_id é extraído automaticamente do JWT
    """
    versao = request.data.get('versao', '3.1.0')
    
    # Extrair cliente_id do JWT
    cliente_id = None
    if hasattr(request, 'user') and hasattr(request.user, 'cliente_id'):
        cliente_id = request.user.cliente_id

    # Configuração de features por versão e cliente
    features_config = {
        "extrato_contas": False,  # Feature principal desabilitada
        # Adicionar outras features conforme necessário
    }

    # Lista de clientes permitidos para features em teste (quando feature=False)
    clientes_permitidos = {
        "extrato_contas": [1, 12, 32],  # IDs dos clientes de teste
        # Adicionar outras features com seus clientes permitidos
    }

    # Aplicar lógica de feature flags por cliente
    if cliente_id:
        for feature_name, feature_enabled in features_config.items():
            if not feature_enabled:  # Se feature está desabilitada globalmente
                # Verificar se cliente está na lista de permitidos
                clientes_feature = clientes_permitidos.get(feature_name, [])
                if cliente_id in clientes_feature:
                    features_config[feature_name] = True  # Habilitar para este cliente

    return Response({
        "versao": versao,
        "features": features_config
    })
