"""
Views para receber webhooks da Own Financial

Webhooks disponíveis:
1. Transações (vendas confirmadas/estornadas)
2. Liquidações (pagamentos realizados)
3. Cadastro de estabelecimentos (deferimento/indeferimento)
"""

import json
import logging
from datetime import datetime
from decimal import Decimal

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction

from wallclub_core.utilitarios.log_control import registrar_log
from adquirente_own.cargas_own.models import OwnExtratoTransacoes, OwnLiquidacoes

logger = logging.getLogger('own.webhook')


@csrf_exempt
@require_http_methods(["POST"])
def webhook_transacao(request):
    """
    Recebe notificações de transações da Own em tempo real
    
    Payload esperado:
    {
        "identificadorTransacao": "250106001859910574",
        "tipoTransacao": "VENDA CONFIRMADA" ou "VENDA ESTORNADA",
        "cnpjCliente": "00000000000000",
        "docParceiro": "11111111111111",
        "valor": 60,
        "quantidadeParcela": "1",
        "bandeira": "MASTERCARD",
        "modalide": "DEBITO",
        "mdr": 0.83,
        "data": "06/01/2025 20:57:25",
        "cartao": "550209******6512",
        "numeroSerie": "6M086053",
        "terminal": "01035279",
        "contrato": "029-227-58",
        "mcc": "8999",
        "customFields": "0.00|0.00",
        "nomePortador": null
    }
    """
    try:
        # Parse payload
        payload = json.loads(request.body.decode('utf-8'))
        identificador = payload.get('identificadorTransacao')
        
        registrar_log('adquirente_own', f'📥 Webhook transação recebido: {identificador}')
        
        # Validar campos obrigatórios
        campos_obrigatorios = [
            'identificadorTransacao', 'tipoTransacao', 'cnpjCliente', 
            'docParceiro', 'valor', 'data', 'bandeira'
        ]
        
        for campo in campos_obrigatorios:
            if campo not in payload:
                registrar_log('adquirente_own', f'❌ Campo obrigatório ausente: {campo}', nivel='ERROR')
                return JsonResponse({
                    'sucesso': False,
                    'mensagem': f'Campo obrigatório ausente: {campo}'
                }, status=400)
        
        # Verificar se já existe
        if OwnExtratoTransacoes.objects.filter(identificadorTransacao=identificador).exists():
            registrar_log('adquirente_own', f'⚠️ Transação já existe: {identificador}', nivel='WARNING')
            return JsonResponse({'sucesso': True, 'mensagem': 'Transação já processada'}, status=200)
        
        # Salvar transação
        with transaction.atomic():
            transacao = OwnExtratoTransacoes.objects.create(
                identificadorTransacao=identificador,
                cnpjCpfCliente=payload.get('cnpjCliente'),
                cnpjCpfParceiro=payload.get('docParceiro'),
                data=_parse_data_own(payload.get('data')),
                valor=Decimal(str(payload.get('valor'))),
                quantidadeParcelas=int(payload.get('quantidadeParcela', 1)),
                mdr=Decimal(str(payload.get('mdr', 0))),
                statusTransacao=payload.get('tipoTransacao'),
                bandeira=payload.get('bandeira'),
                modalidade=payload.get('modalide', ''),
                numeroCartao=payload.get('cartao'),
                numeroSerieEquipamento=payload.get('numeroSerie'),
                codigoAutorizacao=payload.get('contrato'),
                lido=False,
                processado=False
            )
            
            registrar_log('adquirente_own', f'✅ Transação salva: {identificador} - R$ {payload.get("valor")}')
        
        return JsonResponse({
            'sucesso': True,
            'mensagem': 'Transação recebida com sucesso',
            'identificador': identificador
        }, status=200)
        
    except json.JSONDecodeError as e:
        registrar_log('adquirente_own', f'❌ Erro ao decodificar JSON: {str(e)}', nivel='ERROR')
        return JsonResponse({'sucesso': False, 'mensagem': 'JSON inválido'}, status=400)
        
    except Exception as e:
        registrar_log('adquirente_own', f'❌ Erro ao processar webhook: {str(e)}', nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro ao processar: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def webhook_liquidacao(request):
    """
    Recebe notificações de liquidações da Own em tempo real
    
    Payload esperado (array):
    [
        {
            "lancamentoId": "1533589352",
            "statusPagamento": "Pago",
            "dataPagamentoPrevista": "10/04/25",
            "dataPagamentoReal": "13/01/25",
            "numeroParcela": "3",
            "valor": "416.66",
            "mdr": "12.46",
            "valorAntecipado": "404.20",
            "taxaAntecipacao": "24.99",
            "antecipada": "S",
            "identificadorTransacao": "250110001861985572",
            "bandeira": "MASTERCARD",
            "modalidade": "CREDITO PARC 7 A 12",
            "codigoCliente": "00000000000000",
            "docParceiro": "11111111111111",
            "nsuTransacao": "695449640",
            "numeroTitulo": "81214538"
        }
    ]
    """
    try:
        # Parse payload (array)
        payload = json.loads(request.body.decode('utf-8'))
        
        if not isinstance(payload, list):
            payload = [payload]  # Normalizar para array
        
        registrar_log('adquirente_own', f'📥 Webhook liquidação recebido: {len(payload)} registros')
        
        salvos = 0
        duplicados = 0
        
        for liquidacao_data in payload:
            lancamento_id = liquidacao_data.get('lancamentoId')
            
            # Verificar se já existe
            if OwnLiquidacoes.objects.filter(lancamentoId=lancamento_id).exists():
                duplicados += 1
                continue
            
            # Salvar liquidação
            try:
                with transaction.atomic():
                    OwnLiquidacoes.objects.create(
                        lancamentoId=int(lancamento_id),
                        statusPagamento=liquidacao_data.get('statusPagamento'),
                        dataPagamentoPrevista=_parse_data_br(liquidacao_data.get('dataPagamentoPrevista')),
                        dataPagamentoReal=_parse_data_br(liquidacao_data.get('dataPagamentoReal')),
                        numeroParcela=int(liquidacao_data.get('numeroParcela')),
                        valor=Decimal(str(liquidacao_data.get('valor'))),
                        antecipada=liquidacao_data.get('antecipada', 'N'),
                        identificadorTransacao=liquidacao_data.get('identificadorTransacao'),
                        bandeira=liquidacao_data.get('bandeira'),
                        modalidade=liquidacao_data.get('modalidade'),
                        codigoCliente=liquidacao_data.get('codigoCliente'),
                        docParceiro=liquidacao_data.get('docParceiro'),
                        nsuTransacao=liquidacao_data.get('nsuTransacao'),
                        numeroTitulo=liquidacao_data.get('numeroTitulo'),
                        processado=False
                    )
                    salvos += 1
                    
            except Exception as e:
                registrar_log('adquirente_own', f'❌ Erro ao salvar liquidação {lancamento_id}: {str(e)}', nivel='ERROR')
                continue
        
        registrar_log('adquirente_own', f'✅ Liquidações processadas: {salvos} salvos, {duplicados} duplicados')
        
        return JsonResponse({
            'sucesso': True,
            'mensagem': f'{salvos} liquidações salvas, {duplicados} duplicadas',
            'salvos': salvos,
            'duplicados': duplicados
        }, status=200)
        
    except json.JSONDecodeError as e:
        registrar_log('adquirente_own', f'❌ Erro ao decodificar JSON: {str(e)}', nivel='ERROR')
        return JsonResponse({'sucesso': False, 'mensagem': 'JSON inválido'}, status=400)
        
    except Exception as e:
        registrar_log('adquirente_own', f'❌ Erro ao processar webhook: {str(e)}', nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro ao processar: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def webhook_cadastro(request):
    """
    Recebe notificações de cadastro de estabelecimentos
    
    Payload esperado:
    {
        "protocoloCore": "000000002842",
        "identificadorCliente": "32430",
        "contrato": "029-196-35",
        "status": "SUCESSO" ou "ERRO",
        "tipo": "CREDENCIAMENTO",
        "reenvio": "N",
        "motivo": "INDEFERIMENTO..." (apenas se status=ERRO)
    }
    """
    try:
        payload = json.loads(request.body.decode('utf-8'))
        
        protocolo = payload.get('protocoloCore')
        status = payload.get('status')
        identificador = payload.get('identificadorCliente')
        
        registrar_log('adquirente_own', f'📥 Webhook cadastro: {protocolo} - {status}')
        
        # Log do resultado
        if status == 'SUCESSO':
            contrato = payload.get('contrato')
            registrar_log('adquirente_own', f'✅ Cadastro aprovado: {identificador} - Contrato: {contrato}')
        else:
            motivo = payload.get('motivo', 'Não informado')
            registrar_log('adquirente_own', f'❌ Cadastro reprovado: {identificador} - Motivo: {motivo}', nivel='WARNING')
        
        # TODO: Implementar lógica de atualização de status do estabelecimento
        # Exemplo: atualizar tabela de lojas com status de credenciamento
        
        return JsonResponse({
            'sucesso': True,
            'mensagem': 'Notificação de cadastro recebida',
            'protocolo': protocolo,
            'status': status
        }, status=200)
        
    except json.JSONDecodeError as e:
        registrar_log('adquirente_own', f'❌ Erro ao decodificar JSON: {str(e)}', nivel='ERROR')
        return JsonResponse({'sucesso': False, 'mensagem': 'JSON inválido'}, status=400)
        
    except Exception as e:
        registrar_log('adquirente_own', f'❌ Erro ao processar webhook: {str(e)}', nivel='ERROR')
        return JsonResponse({
            'sucesso': False,
            'mensagem': f'Erro ao processar: {str(e)}'
        }, status=500)


# =====================================================
# Funções auxiliares
# =====================================================

def _parse_data_own(data_str):
    """
    Converte data do formato Own para datetime
    Formato: "06/01/2025 20:57:25"
    """
    try:
        return datetime.strptime(data_str, '%d/%m/%Y %H:%M:%S')
    except ValueError:
        # Tentar formato alternativo
        try:
            return datetime.strptime(data_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            registrar_log('adquirente_own', f'⚠️ Formato de data inválido: {data_str}', nivel='WARNING')
            return datetime.now()


def _parse_data_br(data_str):
    """
    Converte data do formato brasileiro para date
    Formato: "10/04/25" ou "10/04/2025"
    """
    try:
        # Tentar formato com ano de 2 dígitos
        return datetime.strptime(data_str, '%d/%m/%y').date()
    except ValueError:
        try:
            # Tentar formato com ano de 4 dígitos
            return datetime.strptime(data_str, '%d/%m/%Y').date()
        except ValueError:
            registrar_log('adquirente_own', f'⚠️ Formato de data inválido: {data_str}', nivel='WARNING')
            return datetime.now().date()
