"""
Context processors para o portal lojista
"""

def canal_context(request):
    """
    Adiciona informações do canal ao contexto dos templates
    """
    # Informações padrão
    canal_info = {
        'id': 1,
        'nome': 'WallClub',
        'marca': 'wallclub',
        'logo_id': '1'
    }
    
    # Se o middleware processou a marca, usar essas informações
    if hasattr(request, 'canal_info'):
        canal_info = request.canal_info
    
    return {
        'canal': canal_info,
        'marca_canal': canal_info['marca'],
        'logo_filename': f"{canal_info['logo_id']}.png"
    }
