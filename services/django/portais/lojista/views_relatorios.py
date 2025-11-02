"""
Views do Portal Lojista - Módulo de Relatórios
"""
from django.shortcuts import redirect
from django.views.generic import TemplateView, View
from django.http import JsonResponse


class LojistaRecebimentosView(TemplateView):
    """View de recebimentos"""
    template_name = 'portais/lojista/recebimentos.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.session.get('lojista_authenticated'):
            return redirect('lojista:login')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nome_usuario'] = self.request.session.get('lojista_usuario_nome', 'Usuário')
        context['current_page'] = 'recebimentos.php'
        return context


class LojistaCancelamentosView(TemplateView):
    """View de cancelamentos"""
    template_name = 'portais/lojista/cancelamentos.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.session.get('lojista_authenticated'):
            return redirect('lojista:login')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nome_usuario'] = self.request.session.get('lojista_usuario_nome', 'Usuário')
        context['current_page'] = 'cancelamentos.php'
        return context


class LojistaConciliacaoView(TemplateView):
    """View de conciliação"""
    template_name = 'portais/lojista/conciliacao.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.session.get('lojista_authenticated'):
            return redirect('lojista:login')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nome_usuario'] = self.request.session.get('lojista_usuario_nome', 'Usuário')
        context['current_page'] = 'conciliacao.php'
        return context


class LojistaTerminaisView(TemplateView):
    """View de terminais"""
    template_name = 'portais/lojista/terminais.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.session.get('lojista_authenticated'):
            return redirect('lojista:login')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nome_usuario'] = self.request.session.get('lojista_usuario_nome', 'Usuário')
        context['current_page'] = 'terminais.php'
        return context


# AJAX Views para relatórios
class LojistaRecebimentosAjaxView(View):
    """AJAX para buscar recebimentos"""
    
    def post(self, request):
        if not request.session.get('lojista_authenticated'):
            return JsonResponse({'error': 'Não autenticado'}, status=401)
        
        return JsonResponse({'html': '<div class="alert alert-info">Funcionalidade em desenvolvimento</div>'})


class LojistaCancelamentosAjaxView(View):
    """AJAX para buscar cancelamentos"""
    
    def post(self, request):
        if not request.session.get('lojista_authenticated'):
            return JsonResponse({'error': 'Não autenticado'}, status=401)
        
        return JsonResponse({'html': '<div class="alert alert-info">Funcionalidade em desenvolvimento</div>'})


