"""
Service para operações de conta digital no POS.
Separado do POSP2Service para melhor organização.
USA APIs INTERNAS para comunicação com conta_digital (Fase 6B)
"""
import uuid
import hmac
import hashlib
import json
import base64
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from django.core.cache import cache
from django.db import connection
from django.conf import settings
from wallclub_core.utilitarios.log_control import registrar_log
from wallclub_core.integracoes.api_interna_service import APIInternaService


class SaldoService:
    """Service para operações de saldo da conta digital no POS"""
    
    @staticmethod
    def _gerar_token_validacao(valor: Decimal, cpf: str, terminal: str, valor_compra: Decimal) -> str:
        """
        Gera token de validação que autoriza o POS a usar aquele valor específico.
        Token expira em 5 minutos.
        
        Args:
            valor: Valor máximo permitido
            cpf: CPF do cliente
            terminal: Terminal
            valor_compra: Valor da compra
            
        Returns:
            Token de validação em base64
        """
        import time
        
        # Dados para validação
        dados = {
            'valor_max': str(valor.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
            'cpf': cpf,
            'terminal': terminal,
            'valor_compra': str(valor_compra.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
            'timestamp': int(time.time()),
            'expires_in': 300  # 5 minutos
        }
        
        # Serializar para JSON
        dados_json = json.dumps(dados, sort_keys=True)
        
        # Gerar assinatura HMAC
        secret_key = getattr(settings, 'SECRET_KEY', 'wallclub-secret-2024').encode('utf-8')
        assinatura = hmac.new(secret_key, dados_json.encode('utf-8'), hashlib.sha256).hexdigest()
        
        # Combinar dados + assinatura
        token_data = f"{dados_json}:{assinatura}"
        
        # Codificar em base64
        token = base64.b64encode(token_data.encode('utf-8')).decode('utf-8')
        
        return token
    
    @staticmethod
    def _validar_token_uso(token: str, valor_usar: Decimal, cpf: str, terminal: str) -> Dict[str, Any]:
        """
        Valida se o token autoriza o uso do valor solicitado.
        
        Args:
            token: Token de validação
            valor_usar: Valor que o POS quer usar
            cpf: CPF do cliente
            terminal: Terminal
            
        Returns:
            dict com valido=bool e dados
        """
        import time
        
        try:
            # Decodificar base64
            token_data = base64.b64decode(token.encode('utf-8')).decode('utf-8')
            
            # Separar dados e assinatura
            dados_json, assinatura_recebida = token_data.rsplit(':', 1)
            
            # Verificar assinatura
            secret_key = getattr(settings, 'SECRET_KEY', 'wallback-secret-2024').encode('utf-8')
            assinatura_calculada = hmac.new(secret_key, dados_json.encode('utf-8'), hashlib.sha256).hexdigest()
            
            if assinatura_recebida != assinatura_calculada:
                registrar_log('posp2', '❌ [TOKEN] Assinatura inválida', nivel='WARNING')
                return {'valido': False, 'mensagem': 'Token inválido'}
            
            # Decodificar dados
            dados = json.loads(dados_json)
            
            # Verificar expiração
            timestamp_atual = int(time.time())
            if timestamp_atual - dados['timestamp'] > dados['expires_in']:
                registrar_log('posp2', '❌ [TOKEN] Token expirado', nivel='WARNING')
                return {'valido': False, 'mensagem': 'Token expirado (5 min)'}
            
            # Verificar CPF e terminal
            if dados['cpf'] != cpf or dados['terminal'] != terminal:
                registrar_log('posp2', '❌ [TOKEN] CPF/Terminal divergente', nivel='WARNING')
                return {'valido': False, 'mensagem': 'Token não corresponde ao CPF/Terminal'}
            
            # Verificar se valor solicitado é <= valor máximo autorizado
            # Usar Decimal para comparação precisa
            valor_max_decimal = Decimal(dados['valor_max']).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            if valor_usar > valor_max_decimal:
                registrar_log('posp2', 
                    f'❌ [TOKEN] Valor excede limite: solicitado={valor_usar}, max={valor_max_decimal}',
                    nivel='WARNING')
                return {
                    'valido': False,
                    'mensagem': f'Valor solicitado (R$ {valor_usar}) excede máximo autorizado (R$ {valor_max_decimal})'
                }
            
            registrar_log('posp2', 
                f'✅ [TOKEN] Token válido: valor_max={valor_max_decimal}, solicitado={valor_usar}')
            
            return {
                'valido': True,
                'valor_max': str(valor_max_decimal),
                'valor_compra': str(Decimal(dados['valor_compra']).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                'cpf': dados['cpf'],
                'terminal': dados['terminal']
            }
            
        except Exception as e:
            registrar_log('posp2', f'❌ [TOKEN] Erro ao validar: {str(e)}', nivel='ERROR')
            return {'valido': False, 'mensagem': 'Token inválido'}
    
    @staticmethod
    def consultar_saldo_cliente(cpf: str, terminal: str, valor_compra: Decimal) -> Dict[str, Any]:
        """
        Consulta saldo do cliente sem validar senha.
        Verifica se cliente tem saldo disponível e calcula valor máximo permitido para uso.
        
        USA API INTERNA: POST /api/internal/conta-digital/consultar-saldo/
        USA API INTERNA: POST /api/internal/conta-digital/calcular-maximo/
        
        Args:
            cpf: CPF do cliente
            terminal: ID do terminal POS
            valor_compra: Valor da compra (obrigatório para calcular limite de uso)
            
        Returns:
            dict com sucesso, mensagem, tem_saldo, saldo_disponivel e valor_maximo_permitido
        """
        from .services import POSP2Service
        
        # Obter canal_id do terminal
        service = POSP2Service()
        dados_terminal = service.obter_dados_terminal(terminal)
        
        if not dados_terminal or 'canal_id' not in dados_terminal:
            registrar_log('posp2', f'❌ [CONSULTA] Terminal não encontrado: terminal={terminal}')
            return {
                'sucesso': False,
                'mensagem': 'Terminal não encontrado',
                'tem_saldo': False
            }
        
        canal_id = dados_terminal['canal_id']
        loja_id = dados_terminal.get('loja_id')
        
        try:
            # Chamar API interna para consultar saldo
            resultado = APIInternaService.chamar_api_interna(
                metodo='POST',
                endpoint='/api/internal/conta_digital/consultar_saldo/',
                payload={
                    'cpf': cpf,
                    'canal_id': canal_id
                },
                contexto='apis',
                timeout=5
            )
            
            if not resultado.get('sucesso'):
                return {
                    'sucesso': True,
                    'mensagem': 'Cliente não possui saldo',
                    'tem_saldo': False
                }
            
            tem_saldo = resultado.get('tem_saldo', False)
            saldo_disponivel = Decimal(resultado.get('saldo_disponivel', '0.00'))
            
            registrar_log('posp2', 
                f'✅ [CONSULTA API] Saldo consultado: cpf={cpf[:3]}***, saldo={saldo_disponivel}')
            
            # Preparar resposta base
            resposta = {
                'sucesso': True,
                'mensagem': 'Cliente possui saldo disponível' if tem_saldo else 'Cliente não possui saldo',
                'tem_saldo': tem_saldo,
                'valor_maximo_permitido': 0.0
            }
            
            # Calcular valor máximo permitido (sempre que tem saldo e loja)
            if tem_saldo and loja_id:
                try:
                    # Chamar API interna para calcular máximo
                    resultado_calculo = APIInternaService.chamar_api_interna(
                        metodo='POST',
                        endpoint='/api/internal/conta_digital/calcular_maximo/',
                        payload={
                            'cpf': cpf,
                            'canal_id': canal_id,
                            'loja_id': loja_id,
                            'valor_transacao': str(valor_compra)
                        },
                        contexto='apis',
                        timeout=5
                    )
                    
                    if resultado_calculo.get('sucesso'):
                        valor_permitido = Decimal(resultado_calculo['valor_maximo_permitido'])
                        
                        # Gerar token de validação
                        validation_token = SaldoService._gerar_token_validacao(
                            valor=valor_permitido,
                            cpf=cpf,
                            terminal=terminal,
                            valor_compra=valor_compra
                        )
                        
                        resposta['valor_maximo_permitido'] = str(valor_permitido)
                        resposta['validation_token'] = validation_token
                        
                        registrar_log('posp2',
                            f'💰 [CONSULTA API] Valor máximo calculado: '
                            f'compra={valor_compra}, saldo={saldo_disponivel}, '
                            f'permitido={valor_permitido:.2f}, validation_token_gerado=True')
                    else:
                        registrar_log('posp2',
                            f'⚠️ [CONSULTA API] Erro ao calcular valor máximo: {resultado_calculo.get("mensagem")}')
                except Exception as e:
                    registrar_log('posp2',
                        f'⚠️ [CONSULTA API] Exceção ao calcular máximo: {str(e)}',
                        nivel='WARNING')
            
            return resposta
            
        except Exception as e:
            registrar_log('posp2', 
                f'❌ [CONSULTA API] Erro ao consultar saldo: {str(e)}',
                nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Erro ao consultar saldo',
                'tem_saldo': False
            }
    
    @staticmethod
    def solicitar_autorizacao_uso_saldo(cpf: str, validation_token: str, valor_usar: float, terminal: str) -> Dict[str, Any]:
        """
        Solicita autorização para uso de saldo.
        Envia push notification para cliente aprovar no app.
        
        USA API INTERNA: POST /api/internal/conta-digital/autorizar-uso/
        
        Args:
            cpf: CPF do cliente
            validation_token: Token de validação obtido em consultar_saldo
            valor_usar: Valor que deseja usar do saldo
            terminal: ID do terminal POS
            
        Returns:
            dict com sucesso, autorizacao_id, status
        """
        from wallclub_core.integracoes.notification_service import NotificationService
        from .services import POSP2Service
        
        # Usar Decimal para precisão exata (importante para consistência)
        valor_usar = Decimal(str(valor_usar)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # Validar validation_token
        validacao = SaldoService._validar_token_uso(
            token=validation_token,
            valor_usar=valor_usar,
            cpf=cpf,
            terminal=terminal
        )
        
        if not validacao['valido']:
            registrar_log('posp2', f'❌ [AUTORIZAÇÃO] Token inválido: {validacao["mensagem"]}')
            return {
                'sucesso': False,
                'mensagem': validacao['mensagem']
            }
        
        registrar_log('posp2', 
            f'✅ [AUTORIZAÇÃO] Token válido: cpf={cpf[:3]}***, '
            f'valor_max={validacao["valor_max"]}, valor_usar={valor_usar}')
        
        # Obter dados do terminal
        service = POSP2Service()
        dados_terminal = service.obter_dados_terminal(terminal)
        
        if not dados_terminal or 'canal_id' not in dados_terminal:
            return {
                'sucesso': False,
                'mensagem': 'Terminal não encontrado'
            }
        
        canal_id = dados_terminal['canal_id']
        loja_id = dados_terminal.get('loja_id')
        
        try:
            # Chamar API interna para autorizar uso
            resultado = APIInternaService.chamar_api_interna(
                metodo='POST',
                endpoint='/api/internal/conta_digital/autorizar_uso/',
                payload={
                    'cpf': cpf,
                    'canal_id': canal_id,
                    'valor': str(valor_usar),
                    'loja_id': loja_id,
                    'terminal_id': terminal
                },
                contexto='apis',
                timeout=10
            )
            
            if not resultado.get('sucesso'):
                return resultado
            
            # Obter cliente_id para enviar push via API interna
            try:
                response = APIInternaService.chamar_api_interna(
                    metodo='POST',
                    endpoint='/api/internal/cliente/consultar_por_cpf/',
                    payload={'cpf': cpf, 'canal_id': canal_id},
                    contexto='apis'
                )
                
                if response.get('sucesso') and response.get('cliente'):
                    cliente_id = response['cliente']['id']
                else:
                    cliente_id = None
            except Exception as e:
                registrar_log('posp2', f'⚠️ [AUTORIZAÇÃO API] Cliente não encontrado para push: cpf={cpf[:3]}***', nivel='WARNING')
                return resultado  # Retorna sucesso mesmo sem push
            
            # Enviar push notification
            autorizacao_id = resultado['autorizacao_id']
            estabelecimento = dados_terminal.get('nome_loja', 'Estabelecimento')
            
            try:
                notification_service = NotificationService.get_instance(canal_id)
                notification_service.send_push(
                    cliente_id=cliente_id,
                    id_template='autorizacao_saldo',
                    valor=f"{valor_usar:.2f}".replace('.', ','),
                    autorizacao_id=autorizacao_id,
                    estabelecimento=estabelecimento
                )
                registrar_log('posp2', f'🔔 [AUTORIZAÇÃO API] Push enviado: {autorizacao_id[:8]}')
            except Exception as e:
                registrar_log('posp2', f'⚠️ [AUTORIZAÇÃO API] Erro ao enviar push: {str(e)}', nivel='ERROR')
            
            return resultado
            
        except requests.exceptions.Timeout:
            registrar_log('posp2', '❌ [AUTORIZAÇÃO API] Timeout na chamada da API', nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Timeout ao criar autorização'
            }
        except Exception as e:
            registrar_log('posp2', 
                f'❌ [AUTORIZAÇÃO API] Erro ao autorizar uso: {str(e)}',
                nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Erro ao criar autorização'
            }


class CashbackService:
    """Service para operações de cashback no POS"""
    
    @staticmethod
    def concessao_cashback(cliente_id: int, canal_id: int, loja_id: int, 
                          valor_transacao: Decimal, valor_cashback: Decimal,
                          nsu_transacao: str, cpf: str, terminal: str,
                          tipo_cashback: str = 'WALL', parametro_id: int = None) -> Dict[str, Any]:
        """
        Concede cashback na conta digital do cliente após transação POS.
        Usa sistema centralizado de cashback (apps/cashback/services.py).
        
        Args:
            cliente_id: ID do cliente
            canal_id: ID do canal
            loja_id: ID da loja
            valor_transacao: Valor total da transação
            valor_cashback: Valor do cashback a conceder
            nsu_transacao: NSU da transação origem
            cpf: CPF do cliente (para log)
            terminal: Terminal da transação
            tipo_cashback: 'WALL' ou 'LOJA' (padrão: WALL)
            parametro_id: ID do ParametrosWall ou RegraCashbackLoja
            
        Returns:
            Dict com sucesso, mensagem, cashback_uso_id, movimentacao_id, data_liberacao
        """
        from apps.cashback.services import CashbackService as CashbackServiceCentralizado
        
        try:
            registrar_log('posp2', 
                f'💎 [CASHBACK] Iniciando concessão: cliente={cliente_id}, '
                f'tipo={tipo_cashback}, valor={valor_cashback}, NSU={nsu_transacao}, terminal={terminal}')
            
            # Validar valor
            if valor_cashback <= 0:
                registrar_log('posp2', 
                    f'❌ [CASHBACK] Valor inválido: {valor_cashback}, NSU={nsu_transacao}')
                return {
                    'sucesso': False,
                    'mensagem': 'Valor de cashback deve ser positivo'
                }
            
            # Validar parametro_id
            if not parametro_id:
                registrar_log('posp2',
                    f'❌ [CASHBACK] parametro_id obrigatório para tipo={tipo_cashback}',
                    nivel='ERROR')
                return {
                    'sucesso': False,
                    'mensagem': f'parametro_id obrigatório para cashback {tipo_cashback}'
                }
            
            # Usar sistema centralizado baseado no tipo
            if tipo_cashback == 'WALL':
                resultado = CashbackServiceCentralizado.aplicar_cashback_wall(
                    parametro_wall_id=parametro_id,
                    cliente_id=cliente_id,
                    loja_id=loja_id,
                    canal_id=canal_id,
                    transacao_tipo='POS',
                    transacao_id=nsu_transacao,  # Usar NSU como ID da transação
                    valor_transacao=valor_transacao,
                    valor_cashback=valor_cashback
                )
                
                registrar_log('posp2',
                    f'✅ [CASHBACK WALL] Concedido: cashback_uso_id={resultado.get("cashback_uso_id")}, '
                    f'movimentacao_id={resultado.get("movimentacao_id")}, '
                    f'status={resultado.get("status")}, liberação={resultado.get("data_liberacao")}')
                
            elif tipo_cashback == 'LOJA':
                resultado = CashbackServiceCentralizado.aplicar_cashback_loja(
                    regra_loja_id=parametro_id,
                    cliente_id=cliente_id,
                    loja_id=loja_id,
                    canal_id=canal_id,
                    transacao_tipo='POS',
                    transacao_id=nsu_transacao,
                    valor_transacao=valor_transacao,
                    valor_cashback=valor_cashback
                )
                
                registrar_log('posp2',
                    f'✅ [CASHBACK LOJA] Concedido: cashback_uso_id={resultado.get("cashback_uso_id")}, '
                    f'movimentacao_id={resultado.get("movimentacao_id")}, '
                    f'status={resultado.get("status")}, liberação={resultado.get("data_liberacao")}')
            else:
                registrar_log('posp2',
                    f'❌ [CASHBACK] Tipo inválido: {tipo_cashback}',
                    nivel='ERROR')
                return {
                    'sucesso': False,
                    'mensagem': f'Tipo de cashback inválido: {tipo_cashback}'
                }
            
            # Adicionar flag de sucesso
            resultado['sucesso'] = True
            return resultado
            
        except Exception as e:
            registrar_log('posp2',
                f'❌ [CASHBACK] Exceção na concessão: {str(e)}, NSU={nsu_transacao}',
                nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': f'Erro ao conceder cashback: {str(e)}'
            }
