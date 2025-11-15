"""
Serviços utilitários para cargas Own Financial
Funções auxiliares e helpers
"""

from typing import Dict, Any, Optional
from datetime import datetime
from django.db import connection
from wallclub_core.utilitarios.log_control import registrar_log


class OwnCargasUtilService:
    """Utilitários para cargas Own Financial"""
    
    @staticmethod
    def verificar_transacao_existe(identificador_transacao: str) -> bool:
        """
        Verifica se transação já existe na base
        
        Args:
            identificador_transacao: Identificador da transação Own
            
        Returns:
            True se existe
        """
        from adquirente_own.cargas_own.models import OwnExtratoTransacoes
        
        return OwnExtratoTransacoes.objects.filter(
            identificadorTransacao=identificador_transacao
        ).exists()
    
    @staticmethod
    def verificar_liquidacao_existe(lancamento_id: int) -> bool:
        """
        Verifica se liquidação já existe na base
        
        Args:
            lancamento_id: ID do lançamento Own
            
        Returns:
            True se existe
        """
        from adquirente_own.cargas_own.models import OwnLiquidacoes
        
        return OwnLiquidacoes.objects.filter(
            lancamentoId=lancamento_id
        ).exists()
    
    @staticmethod
    def obter_estatisticas_transacoes() -> Dict[str, Any]:
        """
        Retorna estatísticas das transações Own
        
        Returns:
            Dict com estatísticas
        """
        from adquirente_own.cargas_own.models import OwnExtratoTransacoes
        
        total = OwnExtratoTransacoes.objects.count()
        nao_lidas = OwnExtratoTransacoes.objects.filter(lido=False).count()
        nao_processadas = OwnExtratoTransacoes.objects.filter(processado=False).count()
        
        return {
            'total': total,
            'nao_lidas': nao_lidas,
            'nao_processadas': nao_processadas,
            'processadas': total - nao_processadas
        }
    
    @staticmethod
    def obter_estatisticas_liquidacoes() -> Dict[str, Any]:
        """
        Retorna estatísticas das liquidações Own
        
        Returns:
            Dict com estatísticas
        """
        from adquirente_own.cargas_own.models import OwnLiquidacoes
        
        total = OwnLiquidacoes.objects.count()
        nao_processadas = OwnLiquidacoes.objects.filter(processado=False).count()
        
        return {
            'total': total,
            'nao_processadas': nao_processadas,
            'processadas': total - nao_processadas
        }
    
    @staticmethod
    def marcar_como_lido(identificador_transacao: str) -> bool:
        """
        Marca transação como lida
        
        Args:
            identificador_transacao: Identificador da transação
            
        Returns:
            True se marcado com sucesso
        """
        from adquirente_own.cargas_own.models import OwnExtratoTransacoes
        
        try:
            transacao = OwnExtratoTransacoes.objects.get(
                identificadorTransacao=identificador_transacao
            )
            transacao.lido = True
            transacao.save()
            return True
        except OwnExtratoTransacoes.DoesNotExist:
            return False
    
    @staticmethod
    def limpar_transacoes_antigas(dias: int = 90) -> int:
        """
        Remove transações processadas com mais de X dias
        
        Args:
            dias: Número de dias para manter
            
        Returns:
            Número de registros removidos
        """
        from adquirente_own.cargas_own.models import OwnExtratoTransacoes
        from datetime import timedelta
        
        data_limite = datetime.now() - timedelta(days=dias)
        
        registros_removidos = OwnExtratoTransacoes.objects.filter(
            processado=True,
            data__lt=data_limite
        ).delete()[0]
        
        registrar_log('own.utils', f'🗑️ Removidas {registros_removidos} transações antigas')
        
        return registros_removidos
    
    @staticmethod
    def reprocessar_transacao(identificador_transacao: str) -> bool:
        """
        Marca transação para reprocessamento
        
        Args:
            identificador_transacao: Identificador da transação
            
        Returns:
            True se marcado com sucesso
        """
        from adquirente_own.cargas_own.models import OwnExtratoTransacoes
        
        try:
            transacao = OwnExtratoTransacoes.objects.get(
                identificadorTransacao=identificador_transacao
            )
            transacao.processado = False
            transacao.lido = False
            transacao.save()
            
            registrar_log('own.utils', f'🔄 Transação marcada para reprocessamento: {identificador_transacao}')
            return True
            
        except OwnExtratoTransacoes.DoesNotExist:
            registrar_log('own.utils', f'❌ Transação não encontrada: {identificador_transacao}', nivel='ERROR')
            return False
