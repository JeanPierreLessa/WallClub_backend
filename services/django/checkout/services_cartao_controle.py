"""
Serviço de controle de falhas em cartões tokenizados.
Implementa invalidação automática após múltiplas falhas consecutivas.
Data: 30/10/2025
"""
from datetime import datetime
from django.db import transaction
from wallclub_core.utilitarios.log_control import registrar_log


class CartaoControleService:
    """
    Controla falhas consecutivas em cartões tokenizados.
    Invalida automaticamente após 5 falhas e bloqueia recorrências.
    """
    
    LIMITE_FALHAS = 5
    
    @staticmethod
    def registrar_transacao_negada(cartao_id: int, motivo_falha: str = None) -> dict:
        """
        Registra transação negada e incrementa contador de falhas.
        Invalida cartão automaticamente se atingir limite.
        
        Args:
            cartao_id: ID do cartão tokenizado
            motivo_falha: Motivo da negativa (opcional)
        
        Returns:
            dict: {
                'falhas_consecutivas': int,
                'cartao_invalidado': bool,
                'recorrencias_bloqueadas': int
            }
        """
        from checkout.models import CheckoutCartaoTokenizado
        from checkout.models_recorrencia import RecorrenciaAgendada
        
        try:
            with transaction.atomic():
                cartao = CheckoutCartaoTokenizado.objects.select_for_update().get(id=cartao_id)
                
                # Incrementar contador
                cartao.tentativas_falhas_consecutivas += 1
                cartao.ultima_falha_em = datetime.now()
                cartao.save(update_fields=['tentativas_falhas_consecutivas', 'ultima_falha_em', 'updated_at'])
                
                registrar_log(
                    'checkout.cartao_controle',
                    f"Falha registrada: Cartão ID={cartao_id}, "
                    f"Falhas consecutivas={cartao.tentativas_falhas_consecutivas}, "
                    f"Motivo={motivo_falha or 'N/A'}",
                    nivel='WARNING'
                )
                
                # Verificar se atingiu limite
                if cartao.tentativas_falhas_consecutivas >= CartaoControleService.LIMITE_FALHAS:
                    return CartaoControleService._invalidar_cartao_por_falhas(cartao)
                
                return {
                    'falhas_consecutivas': cartao.tentativas_falhas_consecutivas,
                    'cartao_invalidado': False,
                    'recorrencias_bloqueadas': 0
                }
                
        except CheckoutCartaoTokenizado.DoesNotExist:
            registrar_log(
                'checkout.cartao_controle',
                f"Cartão não encontrado: ID={cartao_id}",
                nivel='ERROR'
            )
            return {
                'falhas_consecutivas': 0,
                'cartao_invalidado': False,
                'recorrencias_bloqueadas': 0
            }
    
    @staticmethod
    def registrar_transacao_aprovada(cartao_id: int):
        """
        Registra transação aprovada e RESETA contador de falhas.
        
        Args:
            cartao_id: ID do cartão tokenizado
        """
        from checkout.models import CheckoutCartaoTokenizado
        
        try:
            cartao = CheckoutCartaoTokenizado.objects.get(id=cartao_id)
            
            # Resetar contador
            if cartao.tentativas_falhas_consecutivas > 0:
                falhas_anteriores = cartao.tentativas_falhas_consecutivas
                cartao.tentativas_falhas_consecutivas = 0
                cartao.ultima_falha_em = None
                cartao.save(update_fields=['tentativas_falhas_consecutivas', 'ultima_falha_em', 'updated_at'])
                
                registrar_log(
                    'checkout.cartao_controle',
                    f"✅ Contador resetado: Cartão ID={cartao_id}, "
                    f"Falhas anteriores={falhas_anteriores}",
                    nivel='INFO'
                )
                
        except CheckoutCartaoTokenizado.DoesNotExist:
            registrar_log(
                'checkout.cartao_controle',
                f"Cartão não encontrado ao resetar: ID={cartao_id}",
                nivel='ERROR'
            )
    
    @staticmethod
    def _invalidar_cartao_por_falhas(cartao) -> dict:
        """
        Invalida cartão por múltiplas falhas e bloqueia recorrências.
        
        Args:
            cartao: Instância de CheckoutCartaoTokenizado (já em transaction.atomic)
        
        Returns:
            dict com estatísticas da invalidação
        """
        from checkout.models_recorrencia import RecorrenciaAgendada
        
        # Marcar cartão como inválido
        cartao.valido = False
        cartao.motivo_invalidacao = f'Múltiplas falhas consecutivas ({cartao.tentativas_falhas_consecutivas})'
        cartao.invalidado_por = None  # Automático
        cartao.invalidado_em = datetime.now()
        cartao.save(update_fields=[
            'valido', 
            'motivo_invalidacao', 
            'invalidado_por', 
            'invalidado_em', 
            'updated_at'
        ])
        
        registrar_log(
            'checkout.cartao_controle',
            f"🚫 CARTÃO INVALIDADO AUTOMATICAMENTE: ID={cartao.id}, "
            f"Falhas={cartao.tentativas_falhas_consecutivas}, "
            f"Titular={cartao.nome_cliente}",
            nivel='ERROR'
        )
        
        # Bloquear recorrências ativas que usam este cartão
        recorrencias_ativas = RecorrenciaAgendada.objects.filter(
            cartao_tokenizado=cartao,
            status='ativo'
        )
        
        recorrencias_ids = list(recorrencias_ativas.values_list('id', flat=True))
        total_bloqueadas = recorrencias_ativas.update(status='hold')
        
        if total_bloqueadas > 0:
            registrar_log(
                'checkout.cartao_controle',
                f"⚠️ Recorrências bloqueadas: {total_bloqueadas} marcadas como HOLD. "
                f"IDs: {recorrencias_ids}",
                nivel='WARNING'
            )
        
        return {
            'falhas_consecutivas': cartao.tentativas_falhas_consecutivas,
            'cartao_invalidado': True,
            'recorrencias_bloqueadas': total_bloqueadas,
            'recorrencias_ids': recorrencias_ids
        }
    
    @staticmethod
    def invalidar_cartao_manual(cartao_id: int, usuario_id: int, motivo: str) -> dict:
        """
        Invalida cartão manualmente (ação de usuário).
        
        Args:
            cartao_id: ID do cartão tokenizado
            usuario_id: ID do usuário que está invalidando
            motivo: Motivo da invalidação
        
        Returns:
            dict: {'sucesso': bool, 'mensagem': str, 'recorrencias_bloqueadas': int}
        """
        from checkout.models import CheckoutCartaoTokenizado
        from checkout.models_recorrencia import RecorrenciaAgendada
        
        try:
            with transaction.atomic():
                cartao = CheckoutCartaoTokenizado.objects.select_for_update().get(id=cartao_id)
                
                if not cartao.valido:
                    return {
                        'sucesso': False,
                        'mensagem': 'Cartão já está inválido',
                        'recorrencias_bloqueadas': 0
                    }
                
                # Marcar como inválido
                cartao.valido = False
                cartao.motivo_invalidacao = motivo
                cartao.invalidado_por = usuario_id
                cartao.invalidado_em = datetime.now()
                cartao.save(update_fields=[
                    'valido', 
                    'motivo_invalidacao', 
                    'invalidado_por', 
                    'invalidado_em', 
                    'updated_at'
                ])
                
                # Bloquear recorrências
                total_bloqueadas = RecorrenciaAgendada.objects.filter(
                    cartao_tokenizado=cartao,
                    status='ativo'
                ).update(status='hold')
                
                registrar_log(
                    'checkout.cartao_controle',
                    f"Cartão invalidado manualmente: ID={cartao_id}, "
                    f"Usuário={usuario_id}, Motivo={motivo}, "
                    f"Recorrências bloqueadas={total_bloqueadas}",
                    nivel='INFO'
                )
                
                return {
                    'sucesso': True,
                    'mensagem': f'Cartão invalidado. {total_bloqueadas} recorrência(s) bloqueada(s).',
                    'recorrencias_bloqueadas': total_bloqueadas
                }
                
        except CheckoutCartaoTokenizado.DoesNotExist:
            return {
                'sucesso': False,
                'mensagem': 'Cartão não encontrado',
                'recorrencias_bloqueadas': 0
            }
