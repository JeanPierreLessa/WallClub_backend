"""
Serviço para processar webhooks de status de credenciamento da Own Financial
"""

from typing import Dict, Any
from datetime import datetime
from adquirente_own.models_cadastro import LojaOwn
from wallclub_core.utilitarios.log_control import registrar_log


class WebhookOwnService:
    """Serviço para processar webhooks da Own Financial"""

    STATUS_VALIDOS = ['PENDENTE', 'APROVADO', 'REPROVADO', 'PROCESSANDO', 'EM_ANALISE']

    def processar_callback_credenciamento(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa callback de status de credenciamento

        Payload esperado:
        {
            "protocolo": "PROTO123456",
            "cnpj": "12345678000199",
            "status": "APROVADO",
            "conveniadaId": "OWN987654",
            "dataCredenciamento": "2026-01-13T21:00:00Z",
            "mensagem": "Credenciamento aprovado com sucesso"
        }

        Args:
            payload: Dados do webhook

        Returns:
            {
                'sucesso': bool,
                'mensagem': str
            }
        """
        try:
            # Extrair dados do payload
            protocolo = payload.get('protocolo')
            cnpj = payload.get('cnpj')
            status_credenciamento = payload.get('status')
            conveniada_id = payload.get('conveniadaId')
            data_credenciamento_str = payload.get('dataCredenciamento')
            mensagem = payload.get('mensagem', '')

            # Validar campos obrigatórios
            if not protocolo and not cnpj:
                registrar_log('adquirente_own', '❌ Webhook sem protocolo ou CNPJ', nivel='ERROR')
                return {
                    'sucesso': False,
                    'mensagem': 'Protocolo ou CNPJ obrigatório'
                }

            if not status_credenciamento:
                registrar_log('adquirente_own', '❌ Webhook sem status', nivel='ERROR')
                return {
                    'sucesso': False,
                    'mensagem': 'Status obrigatório'
                }

            # Validar status
            if status_credenciamento not in self.STATUS_VALIDOS:
                registrar_log('adquirente_own', f'⚠️ Status desconhecido: {status_credenciamento}', nivel='WARNING')

            # Buscar loja por protocolo ou CNPJ
            loja_own = None

            if protocolo:
                loja_own = LojaOwn.objects.filter(protocolo=protocolo).first()

            if not loja_own and cnpj:
                # Buscar por CNPJ (precisa fazer join com tabela loja)
                # TODO: Implementar busca por CNPJ quando model Loja estiver disponível
                registrar_log('adquirente_own', f'⚠️ Busca por CNPJ não implementada: {cnpj}', nivel='WARNING')

            if not loja_own:
                registrar_log('adquirente_own', f'❌ Loja não encontrada: protocolo={protocolo}, cnpj={cnpj}', nivel='ERROR')
                return {
                    'sucesso': False,
                    'mensagem': 'Loja não encontrada'
                }

            # Parsear data de credenciamento
            data_credenciamento = None
            if data_credenciamento_str:
                try:
                    data_credenciamento = datetime.fromisoformat(data_credenciamento_str.replace('Z', '+00:00'))
                except Exception as e:
                    registrar_log('adquirente_own', f'⚠️ Erro ao parsear data: {str(e)}', nivel='WARNING')

            # Atualizar status
            loja_own.status_credenciamento = status_credenciamento
            loja_own.mensagem_status = mensagem

            # Atualizar contrato se veio no payload
            contrato = payload.get('contrato')
            if contrato and contrato.strip():
                loja_own.contrato = contrato

            if data_credenciamento:
                loja_own.data_credenciamento = data_credenciamento

            loja_own.sincronizado = True
            loja_own.ultima_sincronizacao = datetime.now()
            loja_own.save()

            # Atualizar histórico do protocolo
            from adquirente_own.models_cadastro import LojaOwnProtocoloHistorico
            historico = LojaOwnProtocoloHistorico.objects.filter(
                loja_id=loja_own.loja_id,
                protocolo=protocolo
            ).first()

            if historico:
                historico.status = payload.get('status', status_credenciamento)
                historico.motivo = payload.get('motivo', mensagem)
                historico.contrato = contrato
                historico.data_retorno = datetime.now()
                historico.save()
                registrar_log('adquirente_own', f'✅ Histórico de protocolo atualizado: {protocolo}')

            registrar_log(
                'adquirente_own',
                f'✅ Status atualizado: loja_id={loja_own.loja_id}, status={status_credenciamento}, contrato={contrato}'
            )

            # TODO: Enviar notificação (email/push) para responsável

            return {
                'sucesso': True,
                'mensagem': 'Status atualizado com sucesso',
                'loja_id': loja_own.loja_id,
                'status': status_credenciamento
            }

        except Exception as e:
            registrar_log('adquirente_own', f'❌ Erro ao processar webhook: {str(e)}', nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': f'Erro ao processar webhook: {str(e)}'
            }

    def validar_assinatura_webhook(self, payload: Dict[str, Any], signature: str) -> bool:
        """
        Valida assinatura do webhook (se Own enviar)

        Args:
            payload: Dados do webhook
            signature: Assinatura recebida no header

        Returns:
            True se válido, False caso contrário
        """
        # TODO: Implementar validação de assinatura se Own fornecer
        # Por enquanto, retornar True
        return True
