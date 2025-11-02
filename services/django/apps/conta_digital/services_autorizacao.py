"""
Service para gerenciamento de autorizações de uso de saldo no POS.
Cliente aprova no app antes do POS debitar.
"""
import uuid
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from wallclub_core.utilitarios.log_control import registrar_log
from .models import AutorizacaoUsoSaldo, ContaDigital, CashbackParamLoja
from .services import ContaDigitalService


class AutorizacaoService:
    """Service para controle de autorizações de uso de saldo"""
    
    @staticmethod
    def criar_autorizacao(cliente_id, canal_id, valor, terminal, ip_address=None):
        """
        Cria nova autorização para uso de saldo.
        
        Args:
            cliente_id: ID do cliente
            canal_id: ID do canal
            valor: Valor solicitado
            terminal: Terminal que está solicitando
            ip_address: IP da requisição
            
        Returns:
            dict com dados da autorização criada
        """
        try:
            # Usar Decimal para precisão exata (importante para consistência)
            valor = Decimal(str(valor)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            # Busca conta digital
            conta = ContaDigital.objects.get(cliente_id=cliente_id, canal_id=canal_id)
            
            # Valida saldo disponível
            saldo_total = conta.get_saldo_total_disponivel()
            if saldo_total < valor:
                registrar_log('apps.conta_digital', 
                    f'❌ [SALDO] Saldo insuficiente: cliente={cliente_id}, '
                    f'disponível={saldo_total}, solicitado={valor}')
                return {
                    'sucesso': False,
                    'mensagem': f'Saldo insuficiente. Disponível: R$ {saldo_total}'
                }
            
            # Gera ID único
            autorizacao_id = str(uuid.uuid4())
            
            # Define expiração (3 minutos para aprovar)
            data_expiracao = datetime.now() + timedelta(minutes=3)
            
            # Cria autorização
            autorizacao = AutorizacaoUsoSaldo.objects.create(
                autorizacao_id=autorizacao_id,
                cliente_id=cliente_id,
                conta_digital=conta,
                valor_solicitado=valor,
                terminal=terminal,
                ip_address=ip_address,
                status='PENDENTE',
                data_expiracao=data_expiracao
            )
            
            registrar_log('apps.conta_digital', 
                f'💳 [SALDO] Autorização criada: id={autorizacao_id[:8]}, '
                f'cliente={cliente_id}, valor={valor}, terminal={terminal}')
            
            return {
                'sucesso': True,
                'autorizacao_id': autorizacao_id,
                'status': 'PENDENTE',
                'valor': valor,
                'saldo_disponivel': saldo_total,
                'expira_em': 180  # segundos (3 minutos)
            }
            
        except ContaDigital.DoesNotExist:
            registrar_log('apps.conta_digital', 
                f'❌ [SALDO] Conta não encontrada: cliente={cliente_id}, canal={canal_id}')
            return {
                'sucesso': False,
                'mensagem': 'Conta digital não encontrada'
            }
        except Exception as e:
            registrar_log('apps.conta_digital', f'❌ [SALDO] Erro ao criar autorização: {str(e)}', nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': f'Erro ao criar autorização: {str(e)}'
            }
    
    @staticmethod
    @transaction.atomic
    def aprovar_autorizacao(autorizacao_id, cliente_id):
        """
        Cliente aprova uso do saldo no app.
        Bloqueia saldo para evitar double-spending.
        
        Args:
            autorizacao_id: ID da autorização
            cliente_id: ID do cliente (validação)
            
        Returns:
            dict com resultado da aprovação
        """
        try:
            # Busca autorização
            autorizacao = AutorizacaoUsoSaldo.objects.select_for_update().get(
                autorizacao_id=autorizacao_id,
                cliente_id=cliente_id
            )
            
            # Valida se pode aprovar
            if not autorizacao.pode_aprovar():
                registrar_log('apps.conta_digital', 
                    f'❌ [SALDO] Autorização não pode ser aprovada: {autorizacao_id[:8]}, '
                    f'status={autorizacao.status}')
                return {
                    'sucesso': False,
                    'mensagem': f'Autorização não pode ser aprovada (status: {autorizacao.status})'
                }
            
            # Bloqueia saldo
            conta = autorizacao.conta_digital
            valor = autorizacao.valor_solicitado
            
            # Valida saldo disponível novamente
            if conta.get_saldo_total_disponivel() < valor:
                registrar_log('apps.conta_digital', 
                    f'❌ [SALDO] Saldo insuficiente na aprovação: {autorizacao_id[:8]}')
                return {
                    'sucesso': False,
                    'mensagem': 'Saldo insuficiente'
                }
            
            # Bloqueia o saldo
            conta.saldo_bloqueado += valor
            conta.save()
            
            # Atualiza autorização
            autorizacao.status = 'APROVADO'
            autorizacao.data_aprovacao = datetime.now()
            autorizacao.valor_bloqueado = valor
            # Estende expiração para 2 minutos após aprovação
            autorizacao.data_expiracao = datetime.now() + timedelta(minutes=2)
            autorizacao.save()
            
            registrar_log('apps.conta_digital', 
                f'✅ [SALDO] Autorização aprovada: {autorizacao_id[:8]}, '
                f'valor_bloqueado={valor}, cliente={cliente_id}')
            
            return {
                'sucesso': True,
                'mensagem': 'Autorização aprovada',
                'valor_bloqueado': valor,
                'expira_em': 120  # segundos (2 minutos)
            }
            
        except AutorizacaoUsoSaldo.DoesNotExist:
            registrar_log('apps.conta_digital', 
                f'❌ [SALDO] Autorização não encontrada: {autorizacao_id[:8]}')
            return {
                'sucesso': False,
                'mensagem': 'Autorização não encontrada'
            }
        except Exception as e:
            registrar_log('apps.conta_digital', f'❌ [SALDO] Erro ao aprovar: {str(e)}', nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': f'Erro ao aprovar: {str(e)}'
            }
    
    @staticmethod
    @transaction.atomic
    def negar_autorizacao(autorizacao_id, cliente_id):
        """
        Cliente nega uso do saldo no app.
        Se já estava aprovado (com bloqueio), libera o saldo bloqueado.
        
        Args:
            autorizacao_id: ID da autorização
            cliente_id: ID do cliente (validação)
            
        Returns:
            dict com resultado
        """
        try:
            autorizacao = AutorizacaoUsoSaldo.objects.select_for_update().get(
                autorizacao_id=autorizacao_id,
                cliente_id=cliente_id
            )
            
            # Valida se pode negar
            if autorizacao.status not in ['PENDENTE', 'APROVADO']:
                return {
                    'sucesso': False,
                    'mensagem': f'Autorização não pode ser negada (status: {autorizacao.status})'
                }
            
            # Se já expirou, não precisa fazer nada
            if autorizacao.esta_expirada():
                autorizacao.status = 'EXPIRADO'
                autorizacao.save()
                return {
                    'sucesso': False,
                    'mensagem': 'Autorização já expirou'
                }
            
            # Se estava APROVADO, libera bloqueio
            if autorizacao.status == 'APROVADO' and autorizacao.valor_bloqueado:
                conta = autorizacao.conta_digital
                conta.saldo_bloqueado -= autorizacao.valor_bloqueado
                conta.save()
                
                registrar_log('apps.conta_digital', 
                    f'🔓 [SALDO] Bloqueio liberado: {autorizacao_id[:8]}, '
                    f'valor={autorizacao.valor_bloqueado}, cliente={cliente_id}')
            
            # Marca como negado
            autorizacao.status = 'NEGADO'
            autorizacao.save()
            
            registrar_log('apps.conta_digital', 
                f'🚫 [SALDO] Autorização negada: {autorizacao_id[:8]}, cliente={cliente_id}')
            
            return {
                'sucesso': True,
                'mensagem': 'Autorização negada',
                'bloqueio_liberado': bool(autorizacao.valor_bloqueado)
            }
            
        except AutorizacaoUsoSaldo.DoesNotExist:
            return {
                'sucesso': False,
                'mensagem': 'Autorização não encontrada'
            }
        except Exception as e:
            registrar_log('apps.conta_digital', f'❌ [SALDO] Erro ao negar: {str(e)}', nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': f'Erro ao negar: {str(e)}'
            }
    
    @staticmethod
    def verificar_autorizacao(autorizacao_id):
        """
        POS verifica status da autorização (polling).
        
        Args:
            autorizacao_id: ID da autorização
            
        Returns:
            dict com status atual
        """
        try:
            autorizacao = AutorizacaoUsoSaldo.objects.get(
                autorizacao_id=autorizacao_id
            )
            
            # Verifica expiração
            if autorizacao.esta_expirada() and autorizacao.status == 'PENDENTE':
                autorizacao.status = 'EXPIRADO'
                autorizacao.save()
                registrar_log('apps.conta_digital', 
                    f'⏰ [SALDO] Autorização expirada: {autorizacao_id[:8]}')
            
            # pode_processar indica se há ação disponível:
            # - PENDENTE: cliente pode aprovar no app (true)
            # - APROVADO: POS pode debitar (true se não expirou)
            # - NEGADO/EXPIRADO: nada mais a fazer (false)
            pode_processar = autorizacao.status in ['PENDENTE', 'APROVADO'] and not autorizacao.esta_expirada()
            
            return {
                'sucesso': True,
                'status': autorizacao.status,
                'valor_solicitado': str(autorizacao.valor_solicitado),
                'valor_bloqueado': str(autorizacao.valor_bloqueado) if autorizacao.valor_bloqueado else None,
                'pode_processar': pode_processar
            }
            
        except AutorizacaoUsoSaldo.DoesNotExist:
            return {
                'sucesso': False,
                'mensagem': 'Autorização não encontrada'
            }
    
    @staticmethod
    @transaction.atomic
    def debitar_saldo_autorizado(autorizacao_id, nsu_transacao):
        """
        POS debita saldo bloqueado após autorização aprovada.
        
        Args:
            autorizacao_id: ID da autorização
            nsu_transacao: NSU da transação POS
            
        Returns:
            dict com resultado do débito
        """
        try:
            autorizacao = AutorizacaoUsoSaldo.objects.select_for_update().get(
                autorizacao_id=autorizacao_id
            )
            
            # Valida se pode debitar
            if not autorizacao.pode_debitar():
                registrar_log('apps.conta_digital', 
                    f'❌ [SALDO] Não pode debitar: {autorizacao_id[:8]}, '
                    f'status={autorizacao.status}')
                return {
                    'sucesso': False,
                    'mensagem': f'Autorização não permite débito (status: {autorizacao.status})'
                }
            
            # Debita usando ContaDigitalService
            # IMPORTANTE: debitar() retorna objeto MovimentacaoContaDigital, não dict
            movimentacao = ContaDigitalService.debitar(
                cliente_id=autorizacao.cliente_id,
                canal_id=autorizacao.conta_digital.canal_id,
                valor=autorizacao.valor_bloqueado,
                descricao=f'Pagamento POS - Terminal {autorizacao.terminal}',
                tipo_codigo='DEBITO',
                referencia_externa=nsu_transacao,
                sistema_origem='POSP2'
            )
            
            # Libera bloqueio (já debitado)
            # CRÍTICO: buscar fresh do banco para não sobrescrever saldo_atual recém debitado
            conta = ContaDigital.objects.select_for_update().get(id=autorizacao.conta_digital.id)
            conta.saldo_bloqueado -= autorizacao.valor_bloqueado
            conta.save()
            
            # Atualiza autorização
            autorizacao.nsu_transacao = nsu_transacao
            autorizacao.movimentacao_debito_id = movimentacao.id
            autorizacao.status = 'CONCLUIDA'
            autorizacao.data_conclusao = datetime.now()
            autorizacao.save()
            
            registrar_log('apps.conta_digital', 
                f'💸 [SALDO] Débito autorizado: {autorizacao_id[:8]}, '
                f'NSU={nsu_transacao}, valor={autorizacao.valor_bloqueado}')
            
            return {
                'sucesso': True,
                'mensagem': 'Saldo debitado com sucesso',
                'valor_debitado': str(autorizacao.valor_bloqueado),
                'saldo_anterior': str(movimentacao.saldo_anterior),
                'saldo_posterior': str(movimentacao.saldo_posterior),
                'movimentacao_id': movimentacao.id
            }
            
        except AutorizacaoUsoSaldo.DoesNotExist:
            return {
                'sucesso': False,
                'mensagem': 'Autorização não encontrada'
            }
        except Exception as e:
            registrar_log('apps.conta_digital', f'❌ [SALDO] Erro ao debitar: {str(e)}', nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': f'Erro ao debitar: {str(e)}'
            }
    
    @staticmethod
    @transaction.atomic
    def estornar_transacao_saldo(nsu_transacao, motivo):
        """
        Estorna transação que usou saldo (idempotente).
        
        Args:
            nsu_transacao: NSU da transação
            motivo: Motivo do estorno
            
        Returns:
            dict com resultado do estorno
        """
        try:
            autorizacao = AutorizacaoUsoSaldo.objects.get(
                nsu_transacao=nsu_transacao
            )
            
            # Se já estornada, retorna sucesso (idempotente)
            if autorizacao.status == 'ESTORNADA':
                registrar_log('apps.conta_digital', 
                    f'ℹ️ [SALDO] Estorno já realizado: NSU={nsu_transacao}')
                return {
                    'sucesso': True,
                    'mensagem': 'Transação já estornada',
                    'valor_estornado': str(autorizacao.valor_bloqueado)
                }
            
            # Valida se pode estornar
            if not autorizacao.pode_estornar():
                return {
                    'sucesso': False,
                    'mensagem': f'Autorização não pode ser estornada (status: {autorizacao.status})'
                }
            
            # Estorna usando ContaDigitalService
            resultado = ContaDigitalService.creditar(
                cliente_id=autorizacao.cliente_id,
                canal_id=autorizacao.conta_digital.canal_id,
                valor=autorizacao.valor_bloqueado,
                descricao=f'Estorno - {motivo}',
                tipo_operacao='credito',
                referencia_externa=f'ESTORNO_{nsu_transacao}',
                sistema_origem='POSP2'
            )
            
            if not resultado['sucesso']:
                return resultado
            
            # Atualiza autorização
            autorizacao.movimentacao_estorno_id = resultado['movimentacao']['id']
            autorizacao.status = 'ESTORNADA'
            autorizacao.save()
            
            registrar_log('apps.conta_digital', 
                f'🔄 [SALDO] Estorno realizado: NSU={nsu_transacao}, '
                f'valor={autorizacao.valor_bloqueado}, motivo={motivo}')
            
            return {
                'sucesso': True,
                'mensagem': 'Estorno realizado com sucesso',
                'valor_estornado': str(autorizacao.valor_bloqueado),
                'saldo_atual': str(resultado['movimentacao']['saldo_posterior'])
            }
            
        except AutorizacaoUsoSaldo.DoesNotExist:
            registrar_log('apps.conta_digital', 
                f'❌ [SALDO] Autorização não encontrada para estorno: NSU={nsu_transacao}')
            return {
                'sucesso': False,
                'mensagem': 'Transação não encontrada'
            }
        except Exception as e:
            registrar_log('apps.conta_digital', f'❌ [SALDO] Erro ao estornar: {str(e)}', nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': f'Erro ao estornar: {str(e)}'
            }
    
    @staticmethod
    def expirar_autorizacoes_pendentes():
        """
        Job para expirar autorizações pendentes e liberar bloqueios.
        Deve ser executado a cada 1 minuto via cron.
        
        Returns:
            dict com estatísticas
        """
        try:
            # Busca autorizações expiradas
            agora = datetime.now()
            autorizacoes_expiradas = AutorizacaoUsoSaldo.objects.filter(
                status__in=['PENDENTE', 'APROVADO'],
                data_expiracao__lt=agora
            )
            
            total = 0
            liberado = Decimal('0.00')
            
            for autorizacao in autorizacoes_expiradas:
                # Libera bloqueio se estava aprovado
                if autorizacao.status == 'APROVADO' and autorizacao.valor_bloqueado:
                    conta = autorizacao.conta_digital
                    conta.saldo_bloqueado -= autorizacao.valor_bloqueado
                    conta.save()
                    liberado += autorizacao.valor_bloqueado
                
                # Marca como expirado
                autorizacao.status = 'EXPIRADO'
                autorizacao.save()
                total += 1
            
            if total > 0:
                registrar_log('apps.conta_digital', 
                    f'🔄 [SALDO] Autorizações expiradas: {total}, '
                    f'saldo liberado: R$ {liberado}')
            
            return {
                'sucesso': True,
                'total_expiradas': total,
                'saldo_liberado': liberado
            }
            
        except Exception as e:
            registrar_log('apps.conta_digital', 
                f'❌ [SALDO] Erro ao expirar autorizações: {str(e)}')
            return {
                'sucesso': False,
                'mensagem': f'Erro: {str(e)}'
            }


class CashbackService:
    """
    Service para cálculos de cashback baseado em parâmetros por loja.
    Controla tanto a utilização quanto a concessão de cashback.
    """
    
    @staticmethod
    def calcular_valor_utilizacao_maximo (valor_compra, saldo_disponivel, loja_id, processo_venda='POS'):
        """
        Calcula quanto do saldo pode ser usado para pagar a compra.
        
        Regras:
        - Limite é um percentual do valor da compra (ex: 5% de R$ 100 = R$ 5)
        - Cliente só pode usar até o limite OU até o saldo que tem (o menor)
        
        Exemplo:
        - Compra: R$ 100
        - Saldo disponível: R$ 10
        - Limite: 5%
        - Pode usar: R$ 5 (5% de 100, pois tem R$ 10 em saldo)
        
        Exemplo 2:
        - Compra: R$ 100
        - Saldo disponível: R$ 3
        - Limite: 5%
        - Pode usar: R$ 3 (tem apenas R$ 3, mesmo limite sendo R$ 5)
        
        Args:
            valor_compra: Valor total da compra
            saldo_disponivel: Saldo disponível do cliente
            loja_id: ID da loja
            processo_venda: 'POS' ou 'ECOMMERCE'
            
        Returns:
            dict com:
                - valor_permitido: Quanto pode usar
                - percentual_aplicado: Percentual configurado
                - limite_calculado: Limite teórico (percentual * valor_compra)
                - limitado_por: 'percentual' ou 'saldo'
        """
        try:
            # Busca parâmetros da loja
            param = CashbackParamLoja.objects.get(
                loja_id=loja_id,
                processo_venda=processo_venda
            )
            
            # Calcula limite teórico (percentual da compra)
            # Se percentual estiver em decimal (0.05), multiplica direto
            # Se estiver em inteiro (5), divide por 100
            percentual = Decimal(str(param.percentual_utilizacao))
            if percentual < 1:
                # Já está em formato decimal (0.05 = 5%)
                limite_teorico = Decimal(str(valor_compra)) * percentual
            else:
                # Está em formato inteiro (5 = 5%)
                limite_teorico = (Decimal(str(valor_compra)) * percentual) / Decimal('100')
            
            # Valor permitido é o menor entre limite e saldo
            valor_permitido = min(limite_teorico, Decimal(str(saldo_disponivel)))
            
            # Define o que limitou
            limitado_por = 'percentual' if valor_permitido == limite_teorico else 'saldo'
            
            registrar_log('apps.conta_digital',
                f'💰 [CASHBACK] Utilização calculada: loja={loja_id}, '
                f'compra={valor_compra}, saldo={saldo_disponivel}, '
                f'limite={param.percentual_utilizacao}%, pode_usar={valor_permitido}, '
                f'limitado_por={limitado_por}')
            
            return {
                'sucesso': True,
                'valor_permitido': valor_permitido.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                'percentual_aplicado': param.percentual_utilizacao,
                'limite_calculado': limite_teorico.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                'limitado_por': limitado_por
            }
            
        except CashbackParamLoja.DoesNotExist:
            registrar_log('apps.conta_digital',
                f'⚠️ [CASHBACK] Parâmetros não encontrados: loja={loja_id}, processo={processo_venda}',
                nivel='WARNING')
            return {
                'sucesso': False,
                'mensagem': f'Parâmetros de cashback não configurados para loja {loja_id}',
                'valor_permitido': 0.0
            }
        except Exception as e:
            registrar_log('apps.conta_digital',
                f'❌ [CASHBACK] Erro ao calcular utilização: {str(e)}',
                nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': f'Erro ao calcular: {str(e)}',
                'valor_permitido': 0.0
            }
    
    @staticmethod
    def calcular_valor_concessao (valor_transacao, loja_id, processo_venda='POS'):
        """
        Calcula quanto de cashback será concedido ao cliente.
        
        Regras:
        - Cashback é um percentual do valor da transação
        - Valor usado para calcular pode ser o valor original ou já descontado
          (depende da regra de negócio definida)
        
        Exemplo:
        - Transação: R$ 100
        - Percentual concessão: 2%
        - Cashback: R$ 2
        
        Args:
            valor_transacao: Valor da transação (pode ser original ou descontado)
            loja_id: ID da loja
            processo_venda: 'POS' ou 'ECOMMERCE'
            
        Returns:
            dict com:
                - valor_cashback: Valor a ser concedido
                - percentual_aplicado: Percentual configurado
        """
        try:
            # Busca parâmetros da loja
            param = CashbackParamLoja.objects.get(
                loja_id=loja_id,
                processo_venda=processo_venda
            )
            
            # Calcula cashback
            valor_cashback = (Decimal(str(valor_transacao)) * param.percentual_concessao) / Decimal('100')
            
            registrar_log('apps.conta_digital',
                f'💎 [CASHBACK] Concessão calculada: loja={loja_id}, '
                f'transacao={valor_transacao}, percentual={param.percentual_concessao}%, '
                f'cashback={valor_cashback}')
            
            return {
                'sucesso': True,
                'valor_cashback': valor_cashback.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                'percentual_aplicado': param.percentual_concessao
            }
            
        except CashbackParamLoja.DoesNotExist:
            registrar_log('apps.conta_digital',
                f'⚠️ [CASHBACK] Parâmetros não encontrados: loja={loja_id}, processo={processo_venda}',
                nivel='WARNING')
            return {
                'sucesso': False,
                'mensagem': f'Parâmetros de cashback não configurados para loja {loja_id}',
                'valor_cashback': 0.0
            }
        except Exception as e:
            registrar_log('apps.conta_digital',
                f'❌ [CASHBACK] Erro ao calcular concessão: {str(e)}',
                nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': f'Erro ao calcular: {str(e)}',
                'valor_cashback': 0.0
            }
