"""
Views para APIs POSP2
Endpoints consolidados usando services
"""

import json
from decimal import Decimal, ROUND_HALF_UP
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View

from .services import POSP2Service
from .services_conta_digital import SaldoService, CashbackService
from .services_transacao import TRDataService
from .services_sync import TransactionSyncService
from wallclub_core.oauth.decorators import require_oauth_posp2
from wallclub_core.decorators.api_decorators import handle_api_errors, validate_required_params


@csrf_exempt
@require_http_methods(["POST"])
@require_oauth_posp2
@handle_api_errors
@validate_required_params('versao')
def validar_versao_terminal(request):
    """Valida se versão do terminal é permitida"""
    data = json.loads(request.body)
    versao = data.get('versao')
    
    service = POSP2Service()
    resultado = service.validar_versao_terminal(versao)
    
    return JsonResponse({
        'sucesso': resultado['sucesso'],
        'permitida': resultado.get('dados', {}).get('permitida', False),
        'mensagem': resultado['mensagem']
    })


@csrf_exempt
@require_http_methods(["POST"])
@require_oauth_posp2
@handle_api_errors
@validate_required_params('terminal')
def listar_operadores_pos(request):
    """Lista operadores disponíveis para um terminal"""
    data = json.loads(request.body)
    terminal = data.get('terminal')
    
    service = POSP2Service()
    resultado = service.listar_operadores_pos(terminal)
    
    return JsonResponse(resultado)


@csrf_exempt
@require_http_methods(["POST"])
@require_oauth_posp2
@handle_api_errors
@validate_required_params('valor', 'terminal')
def simular_parcelas(request):
    """Simula valores de parcelas para diferentes modalidades"""
    data = json.loads(request.body)
    valor = data.get('valor')
    terminal = data.get('terminal')
    wall = data.get('wall', 's')
    
    service = POSP2Service()
    resultado = service.simular_parcelas(valor, terminal, wall)
    
    return JsonResponse(resultado)


@csrf_exempt
@require_http_methods(["POST"])
@require_oauth_posp2
@handle_api_errors
@validate_required_params('valoro', 'forma', 'terminal')
def calcular_desconto_parcela(request):
    """Calcula desconto para forma de pagamento específica"""
    data = json.loads(request.body)
    valoro = data.get('valoro')
    forma = data.get('forma')
    parcelas = data.get('parcelas', 1)
    terminal = data.get('terminal')
    wall = data.get('wall', 's')
    
    service = POSP2Service()
    valor_decimal = Decimal(str(valoro)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    resultado = service.calcular_desconto_parcela(valor_decimal, forma, int(parcelas), terminal, wall)
    
    return JsonResponse(resultado)


@csrf_exempt
@require_http_methods(["POST"])
@require_oauth_posp2
@handle_api_errors
@validate_required_params('cpf')
def valida_cpf(request):
    """Valida CPF"""
    data = json.loads(request.body)
    cpf = data.get('cpf')
    terminal = data.get('terminal')
    
    service = POSP2Service()
    resultado = service.valida_cpf(cpf, terminal)
    
    # Ajustar resposta do service para usar 'sucesso' ao invés de 'valido'
    if 'valido' in resultado:
        resultado['sucesso'] = resultado.pop('valido')
    
    return JsonResponse(resultado)


@csrf_exempt
@require_http_methods(["POST"])
@require_oauth_posp2
@handle_api_errors
@validate_required_params('terminal')
def obter_logo_pos(request):
    """Retorna logo para terminal POS"""
    dados = json.loads(request.body)
    terminal = dados.get('terminal')
    
    service = POSP2Service()
    resultado = service.obter_logo_pos(terminal)
    
    return JsonResponse(resultado)

@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(require_oauth_posp2, name='dispatch')
@method_decorator(handle_api_errors, name='dispatch')
class TransactionSyncView(View):
    """View para sincronização de transações do app Android"""
    
    def post(self, request):
        """Processa sincronização de transações"""
        data = json.loads(request.body)
        transacoes = data.get('transacoes', [])
        
        if not transacoes:
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'Array de transações obrigatório'
            })
        
        service = TransactionSyncService()
        resultado = service.sincronizar_transacoes(transacoes)
        
        return JsonResponse(resultado)

@csrf_exempt
@require_http_methods(["POST"])
@require_oauth_posp2
@handle_api_errors
@validate_required_params('cpf', 'terminal', 'celular')
def atualiza_celular_envia_msg_app(request):
    """Atualiza celular do cliente e envia mensagem para baixar o app com nova senha"""
    data = json.loads(request.body)
    cpf = data.get('cpf')
    terminal = data.get('terminal')
    celular = data.get('celular')
    
    service = POSP2Service()
    resultado = service.atualiza_celular_envia_msg_app(cpf, terminal, celular)
    
    return JsonResponse(resultado)



@csrf_exempt
@require_http_methods(["POST"])
@require_oauth_posp2
@handle_api_errors
def processar_dados_transacao(request):
    """Processa dados de transação e gera comprovante"""
    dados_json = request.body.decode('utf-8')
    
    service = TRDataService()
    resultado = service.processar_dados_transacao(dados_json)
    
    return JsonResponse(resultado)


# ============================================
# ENDPOINTS DE USO DE SALDO NO POS
# ============================================

@csrf_exempt
@require_http_methods(["POST"])
@require_oauth_posp2
@handle_api_errors
@validate_required_params('cpf', 'terminal', 'valor_compra')
def consultar_saldo(request):
    """
    Consulta saldo do cliente sem validar senha.
    Calcula o valor máximo permitido para uso baseado no valor da compra.
    """
    data = json.loads(request.body)
    cpf = data.get('cpf')
    terminal = data.get('terminal')
    valor_compra = data.get('valor_compra')
    
    # Converter e validar valor_compra
    valor_compra = Decimal(str(valor_compra)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    if valor_compra <= 0:
        return JsonResponse({
            'sucesso': False,
            'mensagem': 'valor_compra deve ser maior que zero'
        })
    
    service = SaldoService()
    resultado = service.consultar_saldo_cliente(cpf, terminal, valor_compra)
    
    return JsonResponse(resultado)


@csrf_exempt
@require_http_methods(["POST"])
@require_oauth_posp2
@handle_api_errors
@validate_required_params('cpf', 'validation_token', 'valor_usar', 'terminal')
def solicitar_autorizacao_saldo(request):
    """POS solicita autorização para uso de saldo - envia push para cliente"""
    data = json.loads(request.body)
    cpf = data.get('cpf')
    validation_token = data.get('validation_token')
    valor_usar = data.get('valor_usar')
    terminal = data.get('terminal')
    
    service = SaldoService()
    resultado = service.solicitar_autorizacao_uso_saldo(cpf, validation_token, valor_usar, terminal)
    
    return JsonResponse(resultado)


@csrf_exempt
@require_http_methods(["POST"])
@require_oauth_posp2
@handle_api_errors
@validate_required_params('autorizacao_id')
def verificar_autorizacao(request):
    """POS verifica status da autorização (polling)"""
    from apps.conta_digital.services_autorizacao import AutorizacaoService
    
    data = json.loads(request.body)
    autorizacao_id = data.get('autorizacao_id')
    
    resultado = AutorizacaoService.verificar_autorizacao(autorizacao_id)
    return JsonResponse(resultado)


@csrf_exempt
@require_http_methods(["POST"])
@require_oauth_posp2
@handle_api_errors
@validate_required_params('autorizacao_id', 'nsu_transacao')
def debitar_saldo_transacao(request):
    """POS debita saldo após autorização aprovada"""
    from apps.conta_digital.services_autorizacao import AutorizacaoService
    
    data = json.loads(request.body)
    autorizacao_id = data.get('autorizacao_id')
    nsu_transacao = data.get('nsu_transacao')
    
    resultado = AutorizacaoService.debitar_saldo_autorizado(
        autorizacao_id=autorizacao_id,
        nsu_transacao=nsu_transacao
    )
    
    return JsonResponse(resultado)


@csrf_exempt
@require_http_methods(["POST"])
@require_oauth_posp2
@handle_api_errors
@validate_required_params('nsu_transacao')
def finalizar_transacao_saldo(request):
    """Confirma finalização da transação (apenas para registro)"""
    data = json.loads(request.body)
    nsu_transacao = data.get('nsu_transacao')
    status = data.get('status', 'APROVADA')
    
    return JsonResponse({
        'sucesso': True,
        'mensagem': 'Transação finalizada'
    })


@csrf_exempt
@require_http_methods(["POST"])
@require_oauth_posp2
@handle_api_errors
@validate_required_params('nsu_transacao')
def estornar_saldo_transacao(request):
    """Estorna saldo se transação foi negada (idempotente)"""
    from apps.conta_digital.services_autorizacao import AutorizacaoService
    
    data = json.loads(request.body)
    nsu_transacao = data.get('nsu_transacao')
    motivo = data.get('motivo', 'Transação negada')
    
    resultado = AutorizacaoService.estornar_transacao_saldo(
        nsu_transacao=nsu_transacao,
        motivo=motivo
    )
    
    return JsonResponse(resultado)


