from decimal import Decimal
from datetime import datetime, timedelta
from django.db import transaction
from django.core.exceptions import ValidationError
from wallclub_core.utilitarios.log_control import registrar_log


class CashbackService:
    """Service centralizado para toda lógica de cashback"""
    
    @staticmethod
    def aplicar_cashback_wall(parametro_wall_id, cliente_id, loja_id, canal_id,
                              transacao_tipo, transacao_id, valor_transacao, 
                              valor_cashback, periodo_retencao_dias=None, 
                              periodo_expiracao_dias=None):
        """
        Aplica cashback Wall após transação.
        Usa diretamente ParametrosWall (wall='C') - não cria regra intermediária.
        
        Args:
            parametro_wall_id: ID do ParametrosWall (wall='C')
            cliente_id: ID do cliente
            loja_id: ID da loja
            canal_id: ID do canal
            transacao_tipo: 'POS' ou 'CHECKOUT'
            transacao_id: ID da transação
            valor_transacao: Valor final da transação
            valor_cashback: Valor do cashback calculado
            periodo_retencao_dias: Dias de retenção (padrão: 30)
            periodo_expiracao_dias: Dias até expirar (padrão: 90)
            
        Returns:
            CashbackUso: Registro do cashback aplicado
        """
        from apps.cashback.models import CashbackUso
        from apps.conta_digital.services import ContaDigitalService
        from parametros_wallclub.models import ParametrosWall
        from django.conf import settings
        
        # Usar configurações globais se não fornecidas
        if periodo_retencao_dias is None:
            periodo_retencao_dias = settings.CASHBACK_PERIODO_RETENCAO_DIAS
        if periodo_expiracao_dias is None:
            periodo_expiracao_dias = settings.CASHBACK_PERIODO_EXPIRACAO_DIAS
        
        with transaction.atomic():
            # Buscar parâmetro Wall para obter nome/descrição
            parametro = ParametrosWall.objects.get(id=parametro_wall_id)
            nome_plano = parametro.plano.nome if parametro.plano else 'Padrão'
            
            # Calcular datas
            agora = datetime.now()
            data_liberacao = agora + timedelta(days=periodo_retencao_dias)
            data_expiracao = None
            if periodo_expiracao_dias > 0:
                data_expiracao = data_liberacao + timedelta(days=periodo_expiracao_dias)
            
            # Creditar na conta digital
            movimentacao = ContaDigitalService.creditar(
                cliente_id=cliente_id,
                canal_id=canal_id,
                valor=valor_cashback,
                descricao=f"Cashback Wall - {nome_plano}",
                tipo_codigo='CASHBACK_WALL',
                referencia_externa=f'WALL:{parametro_wall_id}',
                sistema_origem='CASHBACK'
            )
            
            # Registrar histórico
            cashback_uso = CashbackUso.objects.create(
                tipo_origem='WALL',
                parametro_wall_id=parametro_wall_id,
                cliente_id=cliente_id,
                loja_id=loja_id,
                canal_id=canal_id,
                transacao_tipo=transacao_tipo,
                transacao_id=transacao_id,
                valor_transacao=valor_transacao,
                valor_cashback=valor_cashback,
                status='RETIDO' if periodo_retencao_dias > 0 else 'LIBERADO',
                liberado_em=data_liberacao,
                expira_em=data_expiracao,
                movimentacao_id=movimentacao.id
            )
            
            registrar_log(
                'apps.cashback',
                f'Cashback Wall aplicado - Cliente: {cliente_id}, Valor: {valor_cashback}, '
                f'Status: {cashback_uso.status}, Parâmetro: {parametro_wall_id}'
            )
            
            return {
                'cashback_uso_id': cashback_uso.id,
                'movimentacao_id': movimentacao.id,
                'status': cashback_uso.status,
                'data_liberacao': data_liberacao.isoformat() if data_liberacao else None,
                'data_expiracao': data_expiracao.isoformat() if data_expiracao else None,
            }
    
    @staticmethod
    def simular_cashback_loja(loja_id, cliente_id, canal_id, valor_transacao, forma_pagamento):
        """
        Simula cashback de loja sem aplicar.
        Retorna a melhor regra aplicável.
        
        Args:
            loja_id: ID da loja
            cliente_id: ID do cliente
            canal_id: ID do canal
            valor_transacao: Valor da transação
            forma_pagamento: 'PIX', 'DEBITO', 'CREDITO'
            
        Returns:
            dict: Dados da simulação com estrutura padronizada
        """
        from apps.cashback.models import RegraCashbackLoja
        
        agora = datetime.now()
        dia_semana = agora.weekday()
        horario = agora.time()
        
        # Buscar regras ativas
        regras = RegraCashbackLoja.objects.filter(
            loja_id=loja_id,
            ativo=True,
            vigencia_inicio__lte=agora,
            vigencia_fim__gte=agora
        ).order_by('-prioridade', '-valor_concessao')
        
        for regra in regras:
            # Validar condições
            if not CashbackService._valida_condicoes_loja(
                regra, valor_transacao, forma_pagamento, dia_semana, horario
            ):
                continue
            
            # Validar limites
            if not CashbackService._valida_limites_loja(regra, cliente_id):
                continue
            
            # Calcular cashback
            valor_cashback = regra.calcular_cashback(valor_transacao)
            
            return {
                'aplicavel': True,
                'valor': float(valor_cashback),
                'regra_id': regra.id,
                'regra_nome': regra.nome,
                'tipo_concessao': regra.tipo_concessao,
                'valor_concessao': float(regra.valor_concessao),
            }
        
        return None
    
    @staticmethod
    def aplicar_cashback_loja(regra_loja_id, cliente_id, loja_id, canal_id,
                              transacao_tipo, transacao_id, valor_transacao, 
                              valor_cashback, periodo_retencao_dias=None, 
                              periodo_expiracao_dias=None):
        """
        Aplica cashback de loja após transação.
        
        Args:
            regra_loja_id: ID da RegraCashbackLoja
            cliente_id: ID do cliente
            loja_id: ID da loja
            canal_id: ID do canal
            transacao_tipo: 'POS' ou 'CHECKOUT'
            transacao_id: ID da transação
            valor_transacao: Valor final da transação
            valor_cashback: Valor do cashback calculado
            periodo_retencao_dias: Dias de retenção (padrão: 30)
            periodo_expiracao_dias: Dias até expirar (padrão: 90)
            
        Returns:
            dict: Dados do cashback aplicado
        """
        from apps.cashback.models import RegraCashbackLoja, CashbackUso
        from apps.conta_digital.services import ContaDigitalService
        from django.conf import settings
        
        # Usar configurações globais se não fornecidas
        if periodo_retencao_dias is None:
            periodo_retencao_dias = settings.CASHBACK_PERIODO_RETENCAO_DIAS
        if periodo_expiracao_dias is None:
            periodo_expiracao_dias = settings.CASHBACK_PERIODO_EXPIRACAO_DIAS
        
        with transaction.atomic():
            regra = RegraCashbackLoja.objects.get(id=regra_loja_id)
            
            # Calcular datas
            agora = datetime.now()
            data_liberacao = agora + timedelta(days=periodo_retencao_dias)
            data_expiracao = None
            if periodo_expiracao_dias > 0:
                data_expiracao = data_liberacao + timedelta(days=periodo_expiracao_dias)
            
            # Creditar na conta digital
            movimentacao = ContaDigitalService.creditar(
                cliente_id=cliente_id,
                canal_id=canal_id,
                valor=valor_cashback,
                descricao=f"Cashback Loja - {regra.nome}",
                tipo_codigo='CASHBACK_LOJA',
                referencia_externa=f'LOJA:{regra_loja_id}',
                sistema_origem='CASHBACK'
            )
            
            # Registrar histórico
            cashback_uso = CashbackUso.objects.create(
                tipo_origem='LOJA',
                regra_loja_id=regra_loja_id,
                cliente_id=cliente_id,
                loja_id=loja_id,
                canal_id=canal_id,
                transacao_tipo=transacao_tipo,
                transacao_id=transacao_id,
                valor_transacao=valor_transacao,
                valor_cashback=valor_cashback,
                status='RETIDO' if periodo_retencao_dias > 0 else 'LIBERADO',
                liberado_em=data_liberacao,
                expira_em=data_expiracao,
                movimentacao_id=movimentacao.id
            )
            
            # Atualizar gasto mensal da regra
            regra.gasto_mes_atual += valor_cashback
            regra.save(update_fields=['gasto_mes_atual'])
            
            registrar_log(
                'apps.cashback',
                f'Cashback Loja aplicado - Cliente: {cliente_id}, Valor: {valor_cashback}, '
                f'Status: {cashback_uso.status}, Regra: {regra.nome}'
            )
            
            return {
                'cashback_uso_id': cashback_uso.id,
                'movimentacao_id': movimentacao.id,
                'status': cashback_uso.status,
                'data_liberacao': data_liberacao.isoformat() if data_liberacao else None,
                'data_expiracao': data_expiracao.isoformat() if data_expiracao else None,
            }
    
    @staticmethod
    def aplicar_cashback_loja_automatico(loja_id, cliente_id, canal_id,
                                         valor_transacao, forma_pagamento,
                                         transacao_tipo, transacao_id):
        """
        Verifica e aplica regras de cashback da loja automaticamente.
        
        Args:
            loja_id: ID da loja
            cliente_id: ID do cliente
            canal_id: ID do canal
            valor_transacao: Valor final da transação
            forma_pagamento: 'PIX', 'DEBITO', 'CREDITO', etc
            transacao_tipo: 'POS' ou 'CHECKOUT'
            transacao_id: ID da transação
            
        Returns:
            CashbackUso ou None: Registro do cashback aplicado ou None se nenhuma regra aplicável
        """
        from apps.cashback.models import RegraCashbackLoja
        
        agora = datetime.now()
        dia_semana = agora.weekday()
        horario = agora.time()
        
        # Buscar regras ativas
        regras = RegraCashbackLoja.objects.filter(
            loja_id=loja_id,
            ativo=True,
            vigencia_inicio__lte=agora,
            vigencia_fim__gte=agora
        ).order_by('-prioridade', '-valor_desconto')
        
        for regra in regras:
            # Validar condições
            if not CashbackService._valida_condicoes_loja(
                regra, valor_transacao, forma_pagamento, dia_semana, horario
            ):
                continue
            
            # Validar limites
            if not CashbackService._valida_limites_loja(regra, cliente_id):
                continue
            
            # Calcular cashback
            valor_cashback = regra.calcular_cashback(valor_transacao)
            
            # Aplicar
            cashback_uso = CashbackService._aplicar_cashback_loja(
                regra, cliente_id, loja_id, canal_id, transacao_tipo,
                transacao_id, valor_transacao, valor_cashback
            )
            
            registrar_log(
                'apps.cashback',
                f'Cashback Loja aplicado - Cliente: {cliente_id}, Loja: {loja_id}, '
                f'Valor: {valor_cashback}, Regra: {regra.nome}'
            )
            
            return cashback_uso  # Aplica apenas 1 regra
        
        return None
    
    @staticmethod
    def liberar_cashback(cashback_uso_id):
        """
        Libera cashback retido (move de bloqueado para disponível).
        
        Args:
            cashback_uso_id: ID do CashbackUso
        """
        from apps.cashback.models import CashbackUso
        from apps.conta_digital.models import ContaDigital
        
        with transaction.atomic():
            cashback = CashbackUso.objects.select_for_update().get(id=cashback_uso_id)
            
            if cashback.status != 'RETIDO':
                registrar_log(
                    'apps.cashback',
                    f'Tentativa de liberar cashback não retido - ID: {cashback_uso_id}, Status: {cashback.status}',
                    nivel='WARNING'
                )
                return
            
            # Atualizar conta digital
            conta = ContaDigital.objects.select_for_update().get(
                cliente_id=cashback.cliente_id,
                canal_id=cashback.canal_id
            )
            
            conta.cashback_bloqueado -= cashback.valor_cashback
            conta.cashback_disponivel += cashback.valor_cashback
            conta.save()
            
            # Atualizar status
            cashback.status = 'LIBERADO'
            cashback.save()
            
            registrar_log(
                'apps.cashback',
                f'Cashback liberado - ID: {cashback_uso_id}, Cliente: {cashback.cliente_id}, '
                f'Valor: {cashback.valor_cashback}'
            )
    
    @staticmethod
    def expirar_cashback(cashback_uso_id):
        """
        Expira cashback vencido (remove de disponível).
        
        Args:
            cashback_uso_id: ID do CashbackUso
        """
        from apps.cashback.models import CashbackUso
        from apps.conta_digital.services import ContaDigitalService
        
        with transaction.atomic():
            cashback = CashbackUso.objects.select_for_update().get(id=cashback_uso_id)
            
            if cashback.status != 'LIBERADO':
                registrar_log(
                    'apps.cashback',
                    f'Tentativa de expirar cashback não liberado - ID: {cashback_uso_id}, Status: {cashback.status}',
                    nivel='WARNING'
                )
                return
            
            # Debitar da conta digital
            ContaDigitalService.debitar(
                cliente_id=cashback.cliente_id,
                canal_id=cashback.canal_id,
                valor=cashback.valor_cashback,
                descricao=f"Expiração de cashback",
                tipo_codigo='CASHBACK_EXPIRACAO',
                sistema_origem='CASHBACK'
            )
            
            # Atualizar status
            cashback.status = 'EXPIRADO'
            cashback.save()
            
            registrar_log(
                'apps.cashback',
                f'Cashback expirado - ID: {cashback_uso_id}, Cliente: {cashback.cliente_id}, '
                f'Valor: {cashback.valor_cashback}'
            )
    
    @staticmethod
    def estornar_cashback(transacao_tipo, transacao_id):
        """
        Estorna cashback de uma transação estornada.
        
        Args:
            transacao_tipo: 'POS' ou 'CHECKOUT'
            transacao_id: ID da transação
        """
        from apps.cashback.models import CashbackUso
        from apps.conta_digital.models import ContaDigital
        from apps.conta_digital.services import ContaDigitalService
        
        with transaction.atomic():
            cashbacks = CashbackUso.objects.select_for_update().filter(
                transacao_tipo=transacao_tipo,
                transacao_id=transacao_id,
                status__in=['RETIDO', 'LIBERADO']
            )
            
            for cashback in cashbacks:
                if cashback.status == 'RETIDO':
                    # Remove de bloqueado
                    conta = ContaDigital.objects.select_for_update().get(
                        cliente_id=cashback.cliente_id,
                        canal_id=cashback.canal_id
                    )
                    conta.cashback_bloqueado -= cashback.valor_cashback
                    conta.save()
                
                elif cashback.status == 'LIBERADO':
                    # Debita de disponível
                    ContaDigitalService.debitar(
                        cliente_id=cashback.cliente_id,
                        canal_id=cashback.canal_id,
                        valor=cashback.valor_cashback,
                        descricao=f"Estorno de cashback",
                        tipo_codigo='CASHBACK_ESTORNO',
                        sistema_origem='CASHBACK'
                    )
                
                cashback.status = 'ESTORNADO'
                cashback.save()
                
                registrar_log(
                    'apps.cashback',
                    f'Cashback estornado - ID: {cashback.id}, Cliente: {cashback.cliente_id}, '
                    f'Valor: {cashback.valor_cashback}, Transação: {transacao_tipo}:{transacao_id}'
                )
    
    # ===== MÉTODOS PRIVADOS =====
    
    @staticmethod
    def _valida_condicoes_loja(regra, valor_transacao, forma_pagamento, dia_semana, horario):
        """
        Valida se a transação atende as condições da regra de loja.
        
        Returns:
            bool: True se atende todas as condições
        """
        # Valor mínimo
        if valor_transacao < regra.valor_minimo_compra:
            return False
        
        # Forma de pagamento
        if regra.formas_pagamento and forma_pagamento not in regra.formas_pagamento:
            return False
        
        # Dia da semana
        if regra.dias_semana and dia_semana not in regra.dias_semana:
            return False
        
        # Horário
        if regra.horario_inicio and regra.horario_fim:
            if not (regra.horario_inicio <= horario <= regra.horario_fim):
                return False
        
        return True
    
    @staticmethod
    def _valida_limites_loja(regra, cliente_id):
        """
        Valida se o cliente não excedeu os limites de uso da regra.
        
        Returns:
            bool: True se não excedeu limites
        """
        from apps.cashback.models import CashbackUso
        from datetime import date
        
        hoje = date.today()
        
        # Limite por dia
        if regra.limite_uso_cliente_dia:
            usos_hoje = CashbackUso.objects.filter(
                regra_loja_id=regra.id,
                cliente_id=cliente_id,
                aplicado_em__date=hoje
            ).count()
            
            if usos_hoje >= regra.limite_uso_cliente_dia:
                return False
        
        # Limite por mês
        if regra.limite_uso_cliente_mes:
            primeiro_dia_mes = hoje.replace(day=1)
            usos_mes = CashbackUso.objects.filter(
                regra_loja_id=regra.id,
                cliente_id=cliente_id,
                aplicado_em__date__gte=primeiro_dia_mes
            ).count()
            
            if usos_mes >= regra.limite_uso_cliente_mes:
                return False
        
        # Orçamento mensal
        if regra.orcamento_mensal:
            if regra.gasto_mes_atual >= regra.orcamento_mensal:
                return False
        
        return True
    
    @staticmethod
    def _aplicar_cashback_loja(regra, cliente_id, loja_id, canal_id, transacao_tipo,
                               transacao_id, valor_transacao, valor_cashback):
        """
        Aplica cashback de loja e registra histórico.
        
        Returns:
            CashbackUso: Registro do cashback aplicado
        """
        from apps.cashback.models import CashbackUso
        from apps.conta_digital.services import ContaDigitalService
        
        with transaction.atomic():
            # Calcular datas
            agora = datetime.now()
            data_liberacao = agora + timedelta(days=regra.periodo_retencao_dias)
            data_expiracao = None
            if regra.periodo_expiracao_dias > 0:
                data_expiracao = data_liberacao + timedelta(days=regra.periodo_expiracao_dias)
            
            # Creditar na conta digital
            movimentacao = ContaDigitalService.creditar(
                cliente_id=cliente_id,
                canal_id=canal_id,
                valor=valor_cashback,
                descricao=f"Cashback Loja - {regra.nome}",
                tipo_codigo='CASHBACK_LOJA',
                referencia_externa=f'LOJA:{regra.id}',
                sistema_origem='CASHBACK'
            )
            
            # Registrar histórico
            cashback_uso = CashbackUso.objects.create(
                tipo_origem='LOJA',
                regra_loja_id=regra.id,
                cliente_id=cliente_id,
                loja_id=loja_id,
                canal_id=canal_id,
                transacao_tipo=transacao_tipo,
                transacao_id=transacao_id,
                valor_transacao=valor_transacao,
                valor_cashback=valor_cashback,
                status='RETIDO' if regra.periodo_retencao_dias > 0 else 'LIBERADO',
                liberado_em=data_liberacao,
                expira_em=data_expiracao,
                movimentacao_id=movimentacao.id
            )
            
            # Atualizar gasto mensal da regra
            regra.gasto_mes_atual += valor_cashback
            regra.save(update_fields=['gasto_mes_atual'])
            
            return cashback_uso
