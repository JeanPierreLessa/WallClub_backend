from django.shortcuts import render
from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)


def home_view(request):
    """Página inicial do portal corporativo (sem login)"""
    return render(request, 'portais/corporativo/home.html')


def para_voce_cliente_view(request):
    """Página para clientes"""
    return render(request, 'portais/corporativo/para_voce_cliente.html')


def para_voce_comerciante_view(request):
    """Página para comerciantes/lojistas"""
    return render(request, 'portais/corporativo/para_voce_comerciante.html')


def sobre_view(request):
    """Página sobre a empresa"""
    return render(request, 'portais/corporativo/sobre.html')


def download_app_view(request):
    """Página para download do app WALL CLUB"""
    return render(request, 'portais/corporativo/download_app.html')


def contato_view(request):
    """Página de contato com processamento de formulário"""
    if request.method == 'POST':
        try:
            # Obter dados do formulário
            name = request.POST.get('name')
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            contact_type = request.POST.get('type')
            message = request.POST.get('message')
            
            # Validação básica
            if not all([name, email, phone, contact_type, message]):
                return JsonResponse({
                    'success': False,
                    'message': 'Por favor, preencha todos os campos obrigatórios.'
                })
            
            # Log da mensagem recebida
            logger.info(f"Contato recebido - Nome: {name}, Email: {email}, Tipo: {contact_type}")
            
            # TODO: Implementar envio de email ou salvamento no banco
            # Por enquanto, apenas retorna sucesso
            
            return JsonResponse({
                'success': True,
                'message': 'Mensagem enviada com sucesso! Entraremos em contato em breve.'
            })
            
        except Exception as e:
            logger.error(f"Erro ao processar contato: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': 'Ocorreu um erro ao enviar sua mensagem. Por favor, tente novamente.'
            })
    
    return render(request, 'portais/corporativo/contato.html')


def api_informacoes(request):
    """API pública com informações corporativas"""
    dados = {
        'empresa': 'Wall Club',
        'razao_social': 'Wall Benefícios e Instituição de Pagamentos LTDA',
        'cnpj': '54.430.621/0001-34',
        'descricao': 'Plataforma de pagamentos e benefícios para clientes e lojistas',
        'servicos': [
            'Descontos para clientes',
            'Cashback',
            'Menores taxas para lojistas',
            'Seguros e assistências',
            'Pagamento de fornecedores'
        ],
        'contato': {
            'email': 'atendimento@wallclub.com.br',
            'telefone': '(11) 3254-7462',
            'endereco': 'Avenida Paulista, 726 18º andar - São Paulo - SP',
            'cep': '01.310-100'
        },
        'apps': {
            'ios': 'https://apps.apple.com/br/app/wall-club/id6480528775',
            'android': 'https://play.google.com/store/apps/details?id=com.wallclub.app'
        }
    }
    
    return JsonResponse(dados)
