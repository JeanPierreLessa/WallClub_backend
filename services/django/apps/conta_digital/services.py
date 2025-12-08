"""
Services para o sistema de conta digital customizada.
Operações atômicas e validações de negócio.
"""
from decimal import Decimal
from django.db import transaction
from datetime import datetime, timedelta
import pytz
from django.core.exceptions import ValidationError
from .models import ContaDigital, TipoMovimentacao, MovimentacaoContaDigital, ConfiguracaoContaDigital, CashbackRetencao
from apps.cliente.models import Cliente
from wallclub_core.utilitarios.log_control import registrar_log


class ContaDigitalService:
    """Service principal para operações da conta digital"""
    
    @staticmethod
    def _get_local_now():
        """Retorna datetime atual no timezone do Brasil"""
        brazil_tz = pytz.timezone('America/Sao_Paulo')
        from datetime import datetime
        return datetime.now()
    
    @staticmethod
    def obter_ou_criar_conta(cliente_id, canal_id):
        """
        Obtém a conta digital do cliente ou cria se não existir.
        """
        try:
            # Tentar obter conta existente
            conta = ContaDigital.objects.get(
                cliente_id=cliente_id,
                canal_id=canal_id
            )
            # Refresh para garantir dados mais recentes do banco
            conta.refresh_from_db()
            registrar_log('apps.conta_digital', f'Conta obtida: cliente={cliente_id}, canal={canal_id}, saldo={conta.saldo_atual}')
            return conta
        except ContaDigital.DoesNotExist:
            registrar_log('apps.conta_digital', f'Conta não existe para cliente={cliente_id}, canal={canal_id} - tentando criar')
            # Verificar se deve criar automaticamente
            config = ContaDigitalService._obter_configuracao_canal(canal_id)
            if not config.auto_criar_conta:
                registrar_log('apps.conta_digital', f'❌ Criação automática desabilitada para canal {canal_id}')
                raise ValueError("Conta digital não existe e criação automática está desabilitada")
            
            # Buscar dados do cliente
            try:
                cliente = Cliente.objects.get(id=cliente_id, canal_id=canal_id)
                return ContaDigitalService.criar_conta_digital(
                    cliente_id, canal_id, cliente.cpf
                )
            except Cliente.DoesNotExist:
                raise ValueError("Cliente não encontrado")
    
    @staticmethod
    def criar_conta_digital(cliente_id, canal_id, cpf):
        """
        Cria uma nova conta digital para o cliente.
        """
        try:
            registrar_log('apps.conta_digital', f'🏬 Criando conta digital para cliente {cliente_id}, canal {canal_id}')
            registrar_log('apps.conta_digital', f'🏬 Iniciando criação de conta: cliente={cliente_id}, canal={canal_id}, cpf={cpf[:3]}***')
            
            with transaction.atomic():
                # Verificar se já existe
                if ContaDigital.objects.filter(cliente_id=cliente_id, canal_id=canal_id).exists():
                    registrar_log('apps.conta_digital', f'⚠️ Conta digital já existe para cliente {cliente_id}')
                    return ContaDigital.objects.get(cliente_id=cliente_id, canal_id=canal_id)
                
                # Obter configurações do canal
                config = ContaDigitalService._obter_configuracao_canal(canal_id)
                
                # Criar conta digital
                conta = ContaDigital.objects.create(
                    cliente_id=cliente_id,
                    canal_id=canal_id,
                    cpf=cpf,
                    limite_diario=config.limite_diario_padrao,
                    limite_mensal=config.limite_mensal_padrao
                )
                
                registrar_log('apps.conta_digital', f'✅ Conta digital criada: {conta}, ID={conta.id}, saldo_inicial=0')
                return conta
                
        except Exception as e:
            registrar_log('apps.conta_digital', f'❌ Erro ao criar conta digital: {str(e)}', nivel='ERROR')
            raise
    
    @staticmethod
    def creditar(cliente_id, canal_id, valor, descricao, tipo_codigo='CREDITO',
                referencia_externa=None, sistema_origem=None):
        """
        Credita valor na conta digital do cliente.
        Suporta cashback com retenção automática.
        """
        try:
            registrar_log('apps.conta_digital', f'💰 Creditando R$ {valor} para cliente {cliente_id} - Tipo: {tipo_codigo}, origem={sistema_origem}, ref={referencia_externa}')
            
            with transaction.atomic():
                conta = ContaDigitalService.obter_ou_criar_conta(cliente_id, canal_id)
                tipo_movimentacao = TipoMovimentacao.objects.get(codigo=tipo_codigo)
                
                # Validações
                if not conta.ativa:
                    registrar_log('apps.conta_digital', f'❌ Conta inativa: cliente={cliente_id}')
                    raise ValidationError("Conta digital não está ativa")
                
                if conta.bloqueada:
                    registrar_log('apps.conta_digital', f'❌ Conta bloqueada: cliente={cliente_id}, motivo={conta.motivo_bloqueio}')
                    raise ValidationError(f"Conta digital bloqueada: {conta.motivo_bloqueio}")
                
                # Determinar se afeta cashback ou saldo normal
                if tipo_movimentacao.afeta_cashback:
                    registrar_log('apps.conta_digital', f'💎 Operação afeta cashback: cliente={cliente_id}, valor={valor}')
                    # Cashback - verificar se tem retenção
                    if tipo_movimentacao.periodo_retencao_dias > 0:
                        # Cashback com retenção - vai para cashback_bloqueado
                        saldo_anterior_cashback = conta.cashback_bloqueado
                        conta.cashback_bloqueado += valor
                        
                        # Criar movimentação
                        movimentacao = MovimentacaoContaDigital.objects.create(
                            conta_digital=conta,
                            tipo_movimentacao=tipo_movimentacao,
                            saldo_anterior=saldo_anterior_cashback,
                            saldo_posterior=conta.cashback_bloqueado,
                            valor=valor,
                            descricao=descricao,
                            referencia_externa=referencia_externa,
                            sistema_origem=sistema_origem,
                            status='PROCESSADA',
                            processada_em=ContaDigitalService._get_local_now()
                        )
                        
                        # Criar registro de retenção
                        data_liberacao = ContaDigitalService._get_local_now() + timedelta(days=tipo_movimentacao.periodo_retencao_dias)
                        CashbackRetencao.objects.create(
                            conta_digital=conta,
                            movimentacao_origem=movimentacao,
                            valor_retido=valor,
                            data_liberacao_prevista=data_liberacao,
                            motivo_retencao=f"Período de carência de {tipo_movimentacao.periodo_retencao_dias} dias"
                        )
                        
                        registrar_log('apps.conta_digital', f'💎 Cashback retido até {data_liberacao.strftime("%d/%m/%Y")}, valor={valor}, dias={tipo_movimentacao.periodo_retencao_dias}')
                        
                    else:
                        # Cashback sem retenção - vai direto para cashback_disponivel
                        saldo_anterior_cashback = conta.cashback_disponivel
                        conta.cashback_disponivel += valor
                        
                        movimentacao = MovimentacaoContaDigital.objects.create(
                            conta_digital=conta,
                            tipo_movimentacao=tipo_movimentacao,
                            saldo_anterior=saldo_anterior_cashback,
                            saldo_posterior=conta.cashback_disponivel,
                            valor=valor,
                            descricao=descricao,
                            referencia_externa=referencia_externa,
                            sistema_origem=sistema_origem,
                            status='PROCESSADA',
                            processada_em=ContaDigitalService._get_local_now()
                        )
                        
                        registrar_log('apps.conta_digital', f'💎 Cashback disponível imediatamente: valor={valor}, saldo_atual={conta.cashback_disponivel}')
                else:
                    # Crédito normal no saldo
                    saldo_anterior = conta.saldo_atual
                    conta.saldo_atual += valor
                    
                    movimentacao = MovimentacaoContaDigital.objects.create(
                        conta_digital=conta,
                        tipo_movimentacao=tipo_movimentacao,
                        saldo_anterior=saldo_anterior,
                        saldo_posterior=conta.saldo_atual,
                        valor=valor,
                        descricao=descricao,
                        referencia_externa=referencia_externa,
                        sistema_origem=sistema_origem,
                        status='PROCESSADA',
                        processada_em=datetime.now()
                    )
                
                conta.save()
                registrar_log('apps.conta_digital', f'✅ Crédito processado: {movimentacao}')
                return movimentacao
                
        except Exception as e:
            registrar_log('apps.conta_digital', f'❌ Erro ao creditar: {str(e)}', nivel='ERROR')
            raise
    
    @staticmethod
    def debitar(cliente_id, canal_id, valor, descricao, tipo_codigo='DEBITO',
               referencia_externa=None, sistema_origem=None):
        """
        Debita valor da conta digital do cliente.
        """
        try:
            registrar_log('apps.conta_digital', f'💸 Debitando R$ {valor} do cliente {cliente_id}, tipo={tipo_codigo}, origem={sistema_origem}')
            
            with transaction.atomic():
                conta = ContaDigitalService.obter_ou_criar_conta(cliente_id, canal_id)
                tipo_movimentacao = TipoMovimentacao.objects.get(codigo=tipo_codigo)
                
                # Validações
                if not conta.pode_movimentar(valor):
                    if not conta.ativa:
                        registrar_log('apps.conta_digital', f'❌ Débito negado - conta inativa: cliente={cliente_id}')
                        raise ValidationError("Conta digital não está ativa")
                    if conta.bloqueada:
                        registrar_log('apps.conta_digital', f'❌ Débito negado - conta bloqueada: cliente={cliente_id}')
                        raise ValidationError(f"Conta digital bloqueada: {conta.motivo_bloqueio}")
                    if not conta.tem_saldo_suficiente(valor):
                        registrar_log('apps.conta_digital', f'❌ Débito negado - saldo insuficiente: cliente={cliente_id}, disponível={conta.get_saldo_disponivel()}, solicitado={valor}')
                        raise ValidationError(
                            f"Saldo insuficiente. Disponível: R$ {conta.get_saldo_disponivel()}, "
                            f"Solicitado: R$ {valor}"
                        )
                
                # Capturar saldo anterior
                saldo_anterior = conta.saldo_atual
                
                # Atualizar saldo
                conta.saldo_atual -= valor
                conta.save()
                
                # Criar movimentação
                movimentacao = MovimentacaoContaDigital.objects.create(
                    conta_digital=conta,
                    tipo_movimentacao=tipo_movimentacao,
                    saldo_anterior=saldo_anterior,
                    saldo_posterior=conta.saldo_atual,
                    valor=valor,
                    descricao=descricao,
                    referencia_externa=referencia_externa,
                    sistema_origem=sistema_origem,
                    status='PROCESSADA',
                    processada_em=datetime.now()
                )
                
                registrar_log('apps.conta_digital', f'✅ Débito processado: {movimentacao}')
                return movimentacao
                
        except Exception as e:
            registrar_log('apps.conta_digital', f'❌ Erro ao debitar: {str(e)}', nivel='ERROR')
            raise
    
    @staticmethod
    def obter_saldo(cliente_id, canal_id):
        """
        Obtém informações de saldo da conta digital.
        """
        try:
            conta = ContaDigitalService.obter_ou_criar_conta(cliente_id, canal_id)
            
            return {
                'saldo_atual': conta.saldo_atual,
                'saldo_bloqueado': conta.saldo_bloqueado,
                'saldo_disponivel': conta.get_saldo_disponivel(),
                'cashback_disponivel': conta.cashback_disponivel,
                'cashback_bloqueado': conta.cashback_bloqueado,
                'cashback_total': conta.get_cashback_total(),
                'saldo_total_disponivel': conta.get_saldo_total_disponivel(),
                'limite_diario': conta.limite_diario,
                'limite_mensal': conta.limite_mensal,
                'conta_ativa': conta.ativa,
                'conta_bloqueada': conta.bloqueada,
                'motivo_bloqueio': conta.motivo_bloqueio
            }
        except Exception as e:
            registrar_log('apps.conta_digital', f'❌ Erro ao obter saldo: {str(e)}', nivel='ERROR')
            raise
    
    @staticmethod
    def obter_extrato(cliente_id, canal_id, data_inicio=None, data_fim=None, 
                     tipo_movimentacao=None, limite=50):
        """
        Obtém extrato de movimentações da conta digital.
        """
        try:
            registrar_log('apps.conta_digital', f'📊 Solicitação extrato: cliente={cliente_id}, canal={canal_id}, data_inicio={data_inicio}, data_fim={data_fim}, tipo={tipo_movimentacao}, limite={limite}')
            
            conta = ContaDigitalService.obter_ou_criar_conta(cliente_id, canal_id)
            
            # Filtros
            filtros = {
                'conta_digital': conta,
                'tipo_movimentacao__visivel_extrato': True
            }
            registrar_log('apps.conta_digital', f'🔍 Conta encontrada: ID={conta.id}, saldo_atual={conta.saldo_atual}, cashback_disponivel={conta.cashback_disponivel}')
            
            if data_inicio:
                # Se data_inicio for string de data, converter para datetime início do dia
                if isinstance(data_inicio, str) and len(data_inicio) == 10:  # YYYY-MM-DD
                    from datetime import datetime
                    data_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').replace(hour=0, minute=0, second=0)
                filtros['data_movimentacao__gte'] = data_inicio
            if data_fim:
                # Se data_fim for string de data, converter para datetime fim do dia
                if isinstance(data_fim, str) and len(data_fim) == 10:  # YYYY-MM-DD
                    from datetime import datetime
                    data_fim = datetime.strptime(data_fim, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                filtros['data_movimentacao__lte'] = data_fim
            if tipo_movimentacao:
                filtros['tipo_movimentacao__codigo'] = tipo_movimentacao
            
            registrar_log('apps.conta_digital', f'🔎 Filtros aplicados: {filtros}')
            
            movimentacoes = MovimentacaoContaDigital.objects.filter(**filtros).order_by('-data_movimentacao')[:limite]
            total_movimentacoes = movimentacoes.count()
            
            registrar_log('apps.conta_digital', f'📋 Movimentações encontradas: {total_movimentacoes} registros')
            registrar_log('apps.conta_digital', f'✅ Extrato gerado: {total_movimentacoes} movimentações, saldo_atual={conta.saldo_atual}')
            
            return {
                'saldo_atual': conta.saldo_atual,
                'movimentacoes': list(movimentacoes)  # Retorna objetos do modelo
            }
            
        except Exception as e:
            registrar_log('apps.conta_digital', f'❌ Erro ao obter extrato: cliente={cliente_id}, erro={str(e)}', nivel='ERROR')
            raise
    
    @staticmethod
    def bloquear_saldo(cliente_id, canal_id, valor, motivo):
        """
        Bloqueia uma quantia do saldo para uso futuro.
        """
        try:
            registrar_log('apps.conta_digital', f'🔒 Bloqueando R$ {valor} do cliente {cliente_id}')
            
            with transaction.atomic():
                conta = ContaDigitalService.obter_ou_criar_conta(cliente_id, canal_id)
                
                # Validar se tem saldo suficiente para bloquear
                if conta.get_saldo_disponivel() < valor:
                    raise ValidationError(
                        f"Saldo insuficiente para bloqueio. Disponível: R$ {conta.get_saldo_disponivel()}"
                    )
                
                # Bloquear saldo
                conta.saldo_bloqueado += valor
                conta.save()
                
                # Criar movimentação de bloqueio
                tipo_bloqueio = TipoMovimentacao.objects.get(codigo='BLOQUEIO')
                movimentacao = MovimentacaoContaDigital.objects.create(
                    conta_digital=conta,
                    tipo_movimentacao=tipo_bloqueio,
                    saldo_anterior=conta.saldo_atual,
                    saldo_posterior=conta.saldo_atual,  # Saldo atual não muda no bloqueio
                    valor=valor,
                    descricao=f"Bloqueio de saldo: {motivo}",
                    status='PROCESSADA',
                    processada_em=datetime.now()
                )
                
                registrar_log('apps.conta_digital', f'✅ Saldo bloqueado: {movimentacao}')
                return movimentacao
                
        except Exception as e:
            registrar_log('apps.conta_digital', f'❌ Erro ao bloquear saldo: {str(e)}', nivel='ERROR')
            raise
    
    @staticmethod
    def desbloquear_saldo(cliente_id, canal_id, valor, motivo):
        """
        Desbloqueia uma quantia do saldo bloqueado.
        """
        try:
            registrar_log('apps.conta_digital', f'🔓 Desbloqueando R$ {valor} do cliente {cliente_id}')
            
            with transaction.atomic():
                conta = ContaDigitalService.obter_ou_criar_conta(cliente_id, canal_id)
                
                # Validar se tem saldo bloqueado suficiente
                if conta.saldo_bloqueado < valor:
                    raise ValidationError(
                        f"Saldo bloqueado insuficiente. Bloqueado: R$ {conta.saldo_bloqueado}"
                    )
                
                # Desbloquear saldo
                conta.saldo_bloqueado -= valor
                conta.save()
                
                # Criar movimentação de desbloqueio
                tipo_desbloqueio = TipoMovimentacao.objects.get(codigo='DESBLOQUEIO')
                movimentacao = MovimentacaoContaDigital.objects.create(
                    conta_digital=conta,
                    tipo_movimentacao=tipo_desbloqueio,
                    saldo_anterior=conta.saldo_atual,
                    saldo_posterior=conta.saldo_atual,  # Saldo atual não muda no desbloqueio
                    valor=valor,
                    descricao=f"Desbloqueio de saldo: {motivo}",
                    status='PROCESSADA',
                    processada_em=datetime.now()
                )
                
                registrar_log('apps.conta_digital', f'✅ Saldo desbloqueado: {movimentacao}')
                return movimentacao
                
        except Exception as e:
            registrar_log('apps.conta_digital', f'❌ Erro ao desbloquear saldo: {str(e)}', nivel='ERROR')
            raise
    
    @staticmethod
    def estornar_movimentacao(movimentacao_id, motivo):
        """
        Estorna uma movimentação processada.
        """
        try:
            registrar_log('apps.conta_digital', f'↩️ Estornando movimentação {movimentacao_id}')
            
            with transaction.atomic():
                movimentacao_original = MovimentacaoContaDigital.objects.get(id=movimentacao_id)
                
                if movimentacao_original.status != 'PROCESSADA':
                    raise ValidationError("Apenas movimentações processadas podem ser estornadas")
                
                if not movimentacao_original.tipo_movimentacao.permite_estorno:
                    raise ValidationError("Este tipo de movimentação não permite estorno")
                
                conta = movimentacao_original.conta_digital
                
                # Determinar operação inversa
                if movimentacao_original.tipo_movimentacao.debita_saldo:
                    # Era débito, estorno é crédito
                    novo_saldo = conta.saldo_atual + movimentacao_original.valor
                else:
                    # Era crédito, estorno é débito
                    novo_saldo = conta.saldo_atual - movimentacao_original.valor
                    
                    # Validar se tem saldo suficiente para estorno de crédito
                    if novo_saldo < 0:
                        raise ValidationError("Saldo insuficiente para estornar esta movimentação")
                
                # Atualizar saldo
                saldo_anterior = conta.saldo_atual
                conta.saldo_atual = novo_saldo
                conta.save()
                
                # Criar movimentação de estorno
                tipo_estorno = TipoMovimentacao.objects.get(codigo='ESTORNO')
                movimentacao_estorno = MovimentacaoContaDigital.objects.create(
                    conta_digital=conta,
                    tipo_movimentacao=tipo_estorno,
                    saldo_anterior=saldo_anterior,
                    saldo_posterior=conta.saldo_atual,
                    valor=movimentacao_original.valor,
                    descricao=f"Estorno: {movimentacao_original.descricao}",
                    observacoes=motivo,
                    referencia_externa=f"EST_{movimentacao_original.id}",
                    sistema_origem="CONTA_DIGITAL",
                    movimentacao_estorno=movimentacao_original,
                    status='PROCESSADA',
                    processada_em=datetime.now()
                )
                
                # Marcar movimentação original como estornada
                movimentacao_original.status = 'ESTORNADA'
                movimentacao_original.save()
                
                registrar_log('apps.conta_digital', f'✅ Estorno processado: {movimentacao_estorno}')
                return movimentacao_estorno
                
        except Exception as e:
            registrar_log('apps.conta_digital', f'❌ Erro ao estornar movimentação: {str(e)}', nivel='ERROR')
            raise
    
    @staticmethod
    def _obter_configuracao_canal(canal_id):
        """
        Obtém configuração do canal ou cria uma padrão.
        """
        try:
            return ConfiguracaoContaDigital.objects.get(canal_id=canal_id)
        except ConfiguracaoContaDigital.DoesNotExist:
            # Criar configuração padrão
            return ConfiguracaoContaDigital.objects.create(
                canal_id=canal_id,
                nome_canal=f"Canal {canal_id}"
            )
    
    @staticmethod
    def liberar_cashback_retido(retencao_id, motivo="Liberação manual"):
        """
        Libera cashback retido manualmente antes do prazo.
        """
        try:
            registrar_log('apps.conta_digital', f'💎 Liberando cashback retido ID {retencao_id}')
            
            with transaction.atomic():
                retencao = CashbackRetencao.objects.get(id=retencao_id, status='RETIDO')
                conta = retencao.conta_digital
                
                # Transferir de cashback_bloqueado para cashback_disponivel
                valor_liberado = retencao.valor_retido - retencao.valor_liberado
                
                if valor_liberado <= 0:
                    raise ValidationError("Não há valor para liberar")
                
                # Atualizar saldos da conta
                conta.cashback_bloqueado -= valor_liberado
                conta.cashback_disponivel += valor_liberado
                conta.save()
                
                # Atualizar registro de retenção
                retencao.valor_liberado = retencao.valor_retido
                retencao.status = 'LIBERADO'
                retencao.data_liberacao_efetiva = ContaDigitalService._get_local_now()
                retencao.motivo_liberacao = motivo
                retencao.save()
                
                # Criar movimentação de liberação
                tipo_liberacao = TipoMovimentacao.objects.get(codigo='CASHBACK_CREDITO')
                movimentacao = MovimentacaoContaDigital.objects.create(
                    conta_digital=conta,
                    tipo_movimentacao=tipo_liberacao,
                    saldo_anterior=conta.cashback_disponivel - valor_liberado,
                    saldo_posterior=conta.cashback_disponivel,
                    valor=valor_liberado,
                    descricao=f"Liberação de cashback retido: {motivo}",
                    referencia_externa=f"LIB_RET_{retencao_id}",
                    sistema_origem="CONTA_DIGITAL",
                    status='PROCESSADA',
                    processada_em=datetime.now()
                )
                
                registrar_log('apps.conta_digital', f'✅ Cashback liberado: R$ {valor_liberado}')
                return {
                    'retencao': retencao,
                    'movimentacao': movimentacao,
                    'valor_liberado': valor_liberado
                }
                
        except CashbackRetencao.DoesNotExist:
            raise ValidationError("Retenção de cashback não encontrada ou já liberada")
        except Exception as e:
            registrar_log('apps.conta_digital', f'❌ Erro ao liberar cashback: {str(e)}', nivel='ERROR')
            raise
    
    @staticmethod
    def usar_cashback(cliente_id, canal_id, valor, descricao, referencia_externa=None, sistema_origem=None):
        """
        Usa cashback disponível para pagamento/desconto.
        """
        try:
            registrar_log('apps.conta_digital', f'💰 Usando R$ {valor} de cashback do cliente {cliente_id}')
            
            with transaction.atomic():
                conta = ContaDigitalService.obter_ou_criar_conta(cliente_id, canal_id)
                
                # Validar se tem cashback suficiente
                if conta.cashback_disponivel < valor:
                    raise ValidationError(
                        f"Cashback insuficiente. Disponível: R$ {conta.cashback_disponivel}, "
                        f"Solicitado: R$ {valor}"
                    )
                
                # Debitar cashback
                saldo_anterior = conta.cashback_disponivel
                conta.cashback_disponivel -= Decimal(str(valor))
                conta.save()
                
                # Criar movimentação
                tipo_uso = TipoMovimentacao.objects.get(codigo='CASHBACK_DEBITO')
                movimentacao = MovimentacaoContaDigital.objects.create(
                    conta_digital=conta,
                    tipo_movimentacao=tipo_uso,
                    saldo_anterior=saldo_anterior,
                    saldo_posterior=conta.cashback_disponivel,
                    valor=valor,
                    descricao=descricao,
                    referencia_externa=referencia_externa,
                    sistema_origem=sistema_origem,
                    status='PROCESSADA',
                    processada_em=datetime.now()
                )
                
                registrar_log('apps.conta_digital', f'✅ Cashback usado: R$ {valor}')
                return movimentacao
                
        except Exception as e:
            registrar_log('apps.conta_digital', f'❌ Erro ao usar cashback: {str(e)}', nivel='ERROR')
            raise
    
    @staticmethod
    def creditar_cashback_transacao_pos(cliente_id: int, canal_id: int, valor_cashback: Decimal, 
                                        nsu_transacao: str, descricao: str, 
                                        data_liberacao=None) -> dict:
        """
        Credita cashback na conta digital após transação POS aprovada (wall='C')
        
        Args:
            cliente_id: ID do cliente
            canal_id: ID do canal
            valor_cashback: Valor do cashback a creditar
            nsu_transacao: NSU da transação origem
            descricao: Descrição da movimentação
            data_liberacao: Data em que cashback ficará disponível (None = imediato)
            
        Returns:
            Dict com sucesso/mensagem/movimentacao_id
        """
        try:
            registrar_log('apps.conta_digital', f'💎 [POS] Solicitação crédito cashback: cliente={cliente_id}, canal={canal_id}, valor={valor_cashback}, NSU={nsu_transacao}')
            
            with transaction.atomic():
                # Buscar conta digital
                conta = ContaDigitalService.obter_ou_criar_conta(cliente_id, canal_id)
                
                # Validar valor
                if valor_cashback <= 0:
                    registrar_log('apps.conta_digital', f'❌ [POS] Valor inválido: valor={valor_cashback}, NSU={nsu_transacao}')
                    return {
                        'sucesso': False,
                        'mensagem': 'Valor de cashback deve ser positivo'
                    }
                
                # Determinar status inicial do cashback
                if data_liberacao:
                    status_inicial = 'BLOQUEADO'
                    saldo_anterior_disponivel = conta.cashback_disponivel
                    saldo_anterior_bloqueado = conta.cashback_bloqueado
                    
                    # Creditar em saldo bloqueado
                    conta.cashback_bloqueado += Decimal(str(valor_cashback))
                    conta.save()
                    
                    # Log via registrar_log abaixo
                    registrar_log('apps.conta_digital', f'🔒 [POS] Cashback BLOQUEADO até {data_liberacao}: cliente={cliente_id}, valor={valor_cashback}, NSU={nsu_transacao}')
                else:
                    status_inicial = 'DISPONIVEL'
                    saldo_anterior_disponivel = conta.cashback_disponivel
                    
                    # Creditar em saldo disponível
                    conta.cashback_disponivel += Decimal(str(valor_cashback))
                    conta.save()
                    
                    # Log via registrar_log abaixo
                    registrar_log('apps.conta_digital', f'✅ [POS] Cashback DISPONÍVEL: cliente={cliente_id}, valor={valor_cashback}, saldo={conta.cashback_disponivel}, NSU={nsu_transacao}')
                
                # Criar movimentação
                tipo_cashback = TipoMovimentacao.objects.get(codigo='CASHBACK_CREDITO')
                movimentacao = MovimentacaoContaDigital.objects.create(
                    conta_digital=conta,
                    tipo_movimentacao=tipo_cashback,
                    saldo_anterior=saldo_anterior_disponivel,
                    saldo_posterior=conta.cashback_disponivel,
                    valor=valor_cashback,
                    descricao=f'Cashback POS - NSU {nsu_transacao} - {descricao}',
                    referencia_externa=nsu_transacao,
                    sistema_origem='POSP2',
                    status='PROCESSADA',
                    processada_em=datetime.now(),
                    # Campos customizados (se existirem no modelo)
                    # status_cashback=status_inicial,
                    # data_liberacao=data_liberacao
                )
                
                return {
                    'sucesso': True,
                    'mensagem': 'Cashback creditado com sucesso',
                    'movimentacao_id': movimentacao.id,
                    'saldo_disponivel': str(conta.cashback_disponivel),
                    'saldo_bloqueado': str(conta.cashback_bloqueado) if hasattr(conta, 'cashback_bloqueado') else '0.00'
                }
                
        except ContaDigital.DoesNotExist:
            # Log via registrar_log abaixo
            registrar_log('apps.conta_digital', f'❌ [POS] Conta não encontrada: cliente={cliente_id}, canal={canal_id}, NSU={nsu_transacao}')
            return {
                'sucesso': False,
                'mensagem': 'Conta digital não encontrada ou inativa'
            }
        except TipoMovimentacao.DoesNotExist:
            # Log via registrar_log abaixo
            registrar_log('apps.conta_digital', f'❌ [POS] Tipo CASHBACK_CREDITO não cadastrado, NSU={nsu_transacao}')
            return {
                'sucesso': False,
                'mensagem': 'Tipo de movimentação de cashback não configurado'
            }
        except Exception as e:
            # Log via registrar_log abaixo
            registrar_log('apps.conta_digital', f'❌ [POS] Erro crédito cashback: {str(e)}, NSU={nsu_transacao}', nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': f'Erro ao creditar cashback: {str(e)}'
            }
    
    @staticmethod
    def estornar_cashback_transacao_pos(nsu_transacao: str) -> dict:
        """
        Estorna cashback de uma transação POS cancelada/estornada
        
        Args:
            nsu_transacao: NSU da transação a estornar
            
        Returns:
            Dict com sucesso/mensagem
        """
        try:
            registrar_log('apps.conta_digital', f'↩️ [POS] Solicitação estorno cashback: NSU={nsu_transacao}')
            
            with transaction.atomic():
                # Buscar movimentação original de cashback
                movimentacao_original = MovimentacaoContaDigital.objects.filter(
                    referencia_externa=nsu_transacao,
                    sistema_origem='POSP2',
                    tipo_movimentacao__codigo='CASHBACK_CREDITO',
                    status='PROCESSADA'
                ).first()
                
                if not movimentacao_original:
                    registrar_log('apps.conta_digital', f'❌ [POS] Cashback original não encontrado: NSU={nsu_transacao}')
                    return {
                        'sucesso': False,
                        'mensagem': 'Cashback original não encontrado para este NSU'
                    }
                
                conta = movimentacao_original.conta_digital
                valor_estorno = movimentacao_original.valor
                
                # Verificar se cashback já foi usado
                if conta.cashback_disponivel < valor_estorno:
                    # Log via registrar_log abaixo
                    registrar_log('apps.conta_digital', f'⚠️ [POS] Saldo insuficiente para estorno: NSU={nsu_transacao}, disponível={conta.cashback_disponivel}, necessario={valor_estorno}')
                    # Criar saldo negativo ou bloquear?
                    # Por enquanto, criar movimentação de estorno mesmo com saldo insuficiente
                
                # Debitar cashback
                saldo_anterior = conta.cashback_disponivel
                conta.cashback_disponivel -= valor_estorno
                conta.save()
                
                # Criar movimentação de estorno
                tipo_estorno = TipoMovimentacao.objects.get(codigo='CASHBACK_DEBITO')
                movimentacao_estorno = MovimentacaoContaDigital.objects.create(
                    conta_digital=conta,
                    tipo_movimentacao=tipo_estorno,
                    saldo_anterior=saldo_anterior,
                    saldo_posterior=conta.cashback_disponivel,
                    valor=valor_estorno,
                    descricao=f'Estorno Cashback - NSU {nsu_transacao}',
                    referencia_externa=nsu_transacao,
                    sistema_origem='POSP2',
                    status='PROCESSADA',
                    processada_em=datetime.now()
                )
                
                # Marcar movimentação original como estornada
                movimentacao_original.status = 'ESTORNADA'
                movimentacao_original.save()
                
                # Log via registrar_log abaixo
                registrar_log('apps.conta_digital', f'✅ [POS] Cashback estornado: NSU={nsu_transacao}, valor={valor_estorno}, saldo_atual={conta.cashback_disponivel}')
                
                return {
                    'sucesso': True,
                    'mensagem': 'Cashback estornado com sucesso',
                    'valor_estornado': str(valor_estorno),
                    'saldo_atual': str(conta.cashback_disponivel)
                }
                
        except TipoMovimentacao.DoesNotExist:
            # Log via registrar_log abaixo - sem nivel='ERROR'
            return {
                'sucesso': False,
                'mensagem': 'Tipo de movimentação de estorno não configurado'
            }
        except Exception as e:
            # Log via registrar_log abaixo - sem nivel='ERROR'
            return {
                'sucesso': False,
                'mensagem': f'Erro ao estornar: {str(e)}'
            }
    
    @staticmethod
    def registrar_compra_informativa(cliente_id, canal_id, valor, descricao,
                                     referencia_externa=None, sistema_origem='POSP2',
                                     dados_adicionais=None):
        """
        Registra uma compra como movimentação informativa (não afeta saldo).
        Usado para mostrar histórico completo de compras no extrato.
        
        Args:
            cliente_id: ID do cliente
            canal_id: ID do canal
            valor: Valor da compra
            descricao: Descrição da compra
            referencia_externa: NSU ou ID da transação
            sistema_origem: Sistema que originou (POSP2, CHECKOUT)
            dados_adicionais: Dict com informações extras (forma_pagamento, parcelas, etc)
        
        Returns:
            MovimentacaoContaDigital criada
        """
        try:
            registrar_log('apps.conta_digital', 
                f'🛒 Registrando compra informativa: cliente={cliente_id}, valor={valor}, ref={referencia_externa}')
            
            with transaction.atomic():
                # Obter ou criar conta
                conta = ContaDigitalService.obter_ou_criar_conta(cliente_id, canal_id)
                
                # Buscar tipo de movimentação COMPRA_CARTAO
                try:
                    tipo_compra = TipoMovimentacao.objects.get(codigo='COMPRA_CARTAO')
                except TipoMovimentacao.DoesNotExist:
                    registrar_log('apps.conta_digital', 
                        '⚠️ Tipo COMPRA_CARTAO não existe, criando...', nivel='WARNING')
                    tipo_compra = TipoMovimentacao.objects.create(
                        codigo='COMPRA_CARTAO',
                        nome='Compra com Cartão',
                        descricao='Registro informativo de compra (não afeta saldo)',
                        debita_saldo=False,
                        permite_estorno=False,
                        visivel_extrato=True,
                        categoria='DEBITO',
                        afeta_cashback=False
                    )
                
                # Saldo não muda (movimentação informativa)
                saldo_atual = conta.saldo_atual
                
                # Adicionar dados extras na observação
                observacoes = None
                if dados_adicionais:
                    import json
                    observacoes = json.dumps(dados_adicionais, ensure_ascii=False)
                
                # Criar movimentação informativa
                movimentacao = MovimentacaoContaDigital.objects.create(
                    conta_digital=conta,
                    tipo_movimentacao=tipo_compra,
                    saldo_anterior=saldo_atual,
                    saldo_posterior=saldo_atual,  # Não muda
                    valor=valor,
                    descricao=descricao,
                    observacoes=observacoes,
                    referencia_externa=referencia_externa,
                    sistema_origem=sistema_origem,
                    status='PROCESSADA',
                    processada_em=ContaDigitalService._get_local_now()
                )
                
                registrar_log('apps.conta_digital', 
                    f'✅ Compra informativa registrada: ID={movimentacao.id}, valor={valor}')
                
                return movimentacao
                
        except Exception as e:
            registrar_log('apps.conta_digital', 
                f'❌ Erro ao registrar compra informativa: {str(e)}', nivel='ERROR')
            raise
    
