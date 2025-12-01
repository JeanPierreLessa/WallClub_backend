from decimal import Decimal
from datetime import datetime
from django.core.exceptions import ValidationError
from django.db import transaction, models
from django.apps import apps
import logging

logger = logging.getLogger('apps.cupom')


class CupomService:
    """
    Service para gerenciar validações e operações de cupons.
    """

    def validar_cupom(self, codigo, loja_id, cliente_id, valor_transacao):
        """
        Valida se um cupom pode ser usado em uma transação.

        Args:
            codigo: Código do cupom (case-insensitive)
            loja_id: ID da loja da transação
            cliente_id: ID do cliente
            valor_transacao: Valor da transação (já com descontos Pinbank/Wall)

        Returns:
            Cupom: Objeto do cupom validado

        Raises:
            ValidationError: Se o cupom não puder ser usado
        """
        Cupom = apps.get_model('cupom', 'Cupom')
        CupomUso = apps.get_model('cupom', 'CupomUso')

        # 1. Cupom existe e está ativo
        cupom = Cupom.objects.filter(
            codigo__iexact=codigo.strip(),
            ativo=True
        ).first()

        if not cupom:
            logger.warning(f"Cupom inválido ou inativo: {codigo}")
            raise ValidationError("Cupom inválido ou inativo")

        # 2. Validade
        agora = datetime.now()
        if not (cupom.data_inicio <= agora <= cupom.data_fim):
            logger.warning(f"Cupom fora da validade: {codigo}")
            raise ValidationError("Cupom fora do período de validade")

        # 3. Loja correta
        if cupom.loja_id != loja_id:
            logger.warning(f"Cupom {codigo} não pertence à loja {loja_id}")
            raise ValidationError("Cupom não pertence a esta loja")

        # 4. Valor mínimo
        if cupom.valor_minimo_compra and valor_transacao < cupom.valor_minimo_compra:
            logger.warning(
                f"Valor {valor_transacao} abaixo do mínimo {cupom.valor_minimo_compra}"
            )
            raise ValidationError(
                f"Valor mínimo para usar este cupom: R$ {cupom.valor_minimo_compra}"
            )

        # 5. Limite global
        if cupom.limite_uso_total and cupom.quantidade_usada >= cupom.limite_uso_total:
            logger.warning(f"Cupom {codigo} esgotado")
            raise ValidationError("Cupom esgotado")

        # 6. Limite por CPF (se tipo INDIVIDUAL)
        if cupom.tipo_cupom == 'INDIVIDUAL':
            usos_cliente = CupomUso.objects.filter(
                cupom_id=cupom.id,
                cliente_id=cliente_id
            ).count()

            if usos_cliente >= cupom.limite_uso_por_cpf:
                logger.warning(f"Cliente {cliente_id} já usou cupom {codigo}")
                raise ValidationError("Você já usou este cupom")

        # 7. Cliente vinculado (se tipo INDIVIDUAL com cliente específico)
        if cupom.tipo_cupom == 'INDIVIDUAL' and cupom.cliente_id:
            if cupom.cliente_id != cliente_id:
                logger.warning(
                    f"Cupom {codigo} vinculado a outro cliente"
                )
                raise ValidationError("Este cupom não é válido para você")

        logger.info(f"✅ Cupom {codigo} validado para cliente {cliente_id}")
        return cupom

    def calcular_desconto(self, cupom, valor_base):
        """
        Calcula o valor do desconto a ser aplicado.

        Args:
            cupom: Objeto Cupom
            valor_base: Valor sobre o qual aplicar o desconto

        Returns:
            Decimal: Valor do desconto
        """
        if cupom.tipo_desconto == 'FIXO':
            desconto = cupom.valor_desconto
        else:  # PERCENTUAL
            desconto = valor_base * (cupom.valor_desconto / Decimal('100'))

        # Desconto não pode ser maior que o valor base
        desconto_final = min(desconto, valor_base)

        logger.debug(
            f"Desconto calculado: {desconto_final} "
            f"(tipo: {cupom.tipo_desconto}, base: {valor_base})"
        )

        return desconto_final

    @transaction.atomic
    def registrar_uso(
        self,
        cupom,
        cliente_id,
        loja_id,
        transacao_tipo,
        transacao_id,
        valor_original,
        valor_desconto,
        valor_final,
        nsu=None,
        ip_address=None
    ):
        """
        Registra o uso de um cupom após transação aprovada.

        Args:
            cupom: Objeto Cupom
            cliente_id: ID do cliente
            loja_id: ID da loja
            transacao_tipo: 'POS' ou 'CHECKOUT'
            transacao_id: ID da TransactionData ou CheckoutTransaction
            valor_original: Valor antes do cupom
            valor_desconto: Valor do desconto aplicado
            valor_final: Valor após o cupom
            nsu: NSU da transação (opcional)
            ip_address: IP do cliente (opcional)

        Returns:
            CupomUso: Registro criado
        """
        Cupom = apps.get_model('cupom', 'Cupom')
        CupomUso = apps.get_model('cupom', 'CupomUso')

        # Incrementar contador de uso
        Cupom.objects.filter(id=cupom.id).update(
            quantidade_usada=models.F('quantidade_usada') + 1
        )

        # Criar registro de uso
        cupom_uso = CupomUso.objects.create(
            cupom_id=cupom.id,
            cliente_id=cliente_id,
            loja_id=loja_id,
            transacao_tipo=transacao_tipo,
            transacao_id=transacao_id,
            nsu=nsu,
            valor_transacao_original=valor_original,
            valor_desconto_aplicado=valor_desconto,
            valor_transacao_final=valor_final,
            ip_address=ip_address
        )

        logger.info(
            f"✅ Cupom {cupom.codigo} registrado - "
            f"Cliente {cliente_id}, Transação {transacao_tipo}:{transacao_id}"
        )

        return cupom_uso

    def registrar_estorno(self, transacao_tipo, transacao_id):
        """
        Marca um uso de cupom como estornado.

        IMPORTANTE: O cupom NÃO retorna para uso (prevenção de fraude).
        O contador quantidade_usada NÃO é decrementado.

        Args:
            transacao_tipo: 'POS' ou 'CHECKOUT'
            transacao_id: ID da transação estornada

        Returns:
            bool: True se encontrou e marcou como estornado
        """
        CupomUso = apps.get_model('cupom', 'CupomUso')

        cupom_uso = CupomUso.objects.filter(
            transacao_tipo=transacao_tipo,
            transacao_id=transacao_id
        ).first()

        if cupom_uso:
            cupom_uso.estornado = True
            cupom_uso.save()

            logger.warning(
                f"⚠️ Cupom estornado - Transação {transacao_tipo}:{transacao_id} "
                f"(cupom NÃO retorna)"
            )
            return True

        return False

    def obter_estatisticas_cupom(self, cupom_id):
        """
        Retorna estatísticas de uso de um cupom.

        Args:
            cupom_id: ID do cupom

        Returns:
            dict: Estatísticas do cupom
        """
        Cupom = apps.get_model('cupom', 'Cupom')
        CupomUso = apps.get_model('cupom', 'CupomUso')

        cupom = Cupom.objects.get(id=cupom_id)
        usos = CupomUso.objects.filter(cupom_id=cupom_id)

        total_desconto = sum(
            uso.valor_desconto_aplicado for uso in usos
        )

        return {
            'cupom_codigo': cupom.codigo,
            'quantidade_usada': cupom.quantidade_usada,
            'limite_uso_total': cupom.limite_uso_total,
            'percentual_uso': (
                (cupom.quantidade_usada / cupom.limite_uso_total * 100)
                if cupom.limite_uso_total else None
            ),
            'total_desconto_concedido': total_desconto,
            'usos_estornados': usos.filter(estornado=True).count(),
            'usos_ativos': usos.filter(estornado=False).count(),
        }
