from django.shortcuts import render
from django.http import JsonResponse


def home_view(request):
    """Página inicial do portal corporativo (sem login)"""
    return render(request, 'portais/corporativo/home.html')


def sobre_view(request):
    """Página sobre a empresa"""
    return render(request, 'portais/corporativo/sobre.html')


def servicos_view(request):
    """Página de serviços"""
    return render(request, 'portais/corporativo/servicos.html')


def download_app_view(request):
    """Página para download do app WALL CLUB"""
    return render(request, 'portais/corporativo/download_app.html')


def contato_view(request):
    """Página de contato"""
    if request.method == 'POST':
        # Processar formulário de contato
        nome = request.POST.get('nome')
        email = request.POST.get('email')
        mensagem = request.POST.get('mensagem')
        
        # TODO: Implementar envio de email ou salvamento no banco
        
        return JsonResponse({
            'sucesso': True,
            'mensagem': 'Mensagem enviada com sucesso!'
        })
    
    return render(request, 'portais/corporativo/contato.html')


def api_informacoes(request):
    """API pública com informações corporativas"""
    dados = {
        'empresa': 'WallClub',
        'descricao': 'Plataforma de pagamentos e benefícios',
        'servicos': [
            'Pagamentos PIX',
            'Cartão de Débito/Crédito',
            'Cashback',
            'Gestão Financeira'
        ],
        'contato': {
            'email': 'contato@wallclub.com.br',
            'telefone': '(11) 9999-9999'
        }
    }
    
    return JsonResponse(dados)
