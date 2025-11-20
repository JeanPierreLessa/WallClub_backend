"""
Serviço para carga de liquidações da API Own Financial
Endpoint: GET /agilli/parceiro/v2/consultaLiquidacoes
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta
from django.db import transaction
from adquirente_own.services import OwnService
from adquirente_own.cargas_own.models import OwnLiquidacoes
from wallclub_core.utilitarios.log_control import registrar_log


class CargaLiquidacoesOwnService:
    """Serviço para carga de liquidações Own Financial"""
    
    def __init__(self):
        self.own_service = OwnService()
    
    def consultar_liquidacoes(
        self,
        cnpj_cliente: str,
        data_pagamento_real: datetime,
        doc_parceiro: str = None
    ) -> Dict[str, Any]:
        """
        Consulta liquidações da API Own
        
        Args:
            cnpj_cliente: CNPJ do cliente
            data_pagamento_real: Data do pagamento real
            doc_parceiro: CNPJ do parceiro (opcional)
            
        Returns:
            Dict com sucesso e lista de liquidações
        """
        from adquirente_own.cargas_own.models import CredenciaisExtratoContaOwn
        
        # Obter credenciais
        credencial = CredenciaisExtratoContaOwn.objects.filter(
            cnpj_white_label=cnpj_cliente,
            ativo=True
        ).first()
        
        if not credencial:
            registrar_log('own.liquidacao', f'❌ Credenciais não encontradas: {cnpj_cliente}', nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Credenciais não encontradas'
            }
        
        # Preparar params
        params = {
            'dataPagamentoReal': data_pagamento_real.strftime('%Y-%m-%d'),
            'cnpjCliente': cnpj_cliente
        }
        
        if doc_parceiro:
            params['docParceiro'] = doc_parceiro
        
        registrar_log('own.liquidacao', f'📥 Consultando liquidações: {data_pagamento_real.date()}')
        
        # Inicializar service com environment correto
        own_service = OwnService(environment=credencial.environment)
        
        # Fazer requisição
        response = own_service.fazer_requisicao_autenticada(
            method='GET',
            endpoint='/parceiro/v2/consultaLiquidacoes',
            client_id=credencial.client_id,
            client_secret=credencial.client_secret,
            scope=credencial.scope,
            params=params
        )
        
        if not response.get('sucesso'):
            return response
        
        liquidacoes = response.get('dados', [])
        registrar_log('own.liquidacao', f'✅ {len(liquidacoes)} liquidações encontradas')
        
        return {
            'sucesso': True,
            'liquidacoes': liquidacoes,
            'total': len(liquidacoes)
        }
    
    def salvar_liquidacao(self, liquidacao_data: Dict[str, Any]) -> OwnLiquidacoes:
        """
        Salva ou atualiza liquidação no banco
        
        Args:
            liquidacao_data: Dados da liquidação da API Own
            
        Returns:
            OwnLiquidacoes criado ou atualizado
        """
        lancamento_id = liquidacao_data['lancamentoId']
        
        # Converter datas (formato DD/MM/YYYY)
        data_pagamento_prevista = datetime.strptime(
            liquidacao_data['dataPagamentoPrevista'], 
            '%d/%m/%Y'
        ).date()
        
        data_pagamento_real = datetime.strptime(
            liquidacao_data['dataPagamentoReal'], 
            '%d/%m/%Y'
        ).date()
        
        # Verificar se já existe
        liquidacao_obj, created = OwnLiquidacoes.objects.update_or_create(
            lancamentoId=lancamento_id,
            defaults={
                'statusPagamento': liquidacao_data.get('statusPagamento'),
                'dataPagamentoPrevista': data_pagamento_prevista,
                'numeroParcela': liquidacao_data.get('numeroParcela'),
                'valor': liquidacao_data.get('valor', 0),
                'dataPagamentoReal': data_pagamento_real,
                'antecipada': liquidacao_data.get('antecipada', 'N'),
                'identificadorTransacao': liquidacao_data.get('identificadorTransacao'),
                'bandeira': liquidacao_data.get('bandeira'),
                'modalidade': liquidacao_data.get('modalidade'),
                'codigoCliente': liquidacao_data.get('codigoCliente', ''),
                'docParceiro': liquidacao_data.get('docParceiro', ''),
                'nsuTransacao': liquidacao_data.get('nsuTransacao', ''),
                'numeroTitulo': liquidacao_data.get('numeroTitulo', ''),
                'processado': False
            }
        )
        
        action = 'criada' if created else 'atualizada'
        registrar_log('own.liquidacao', f'💾 Liquidação {action}: {lancamento_id}')
        
        return liquidacao_obj
    
    def atualizar_status_transacao(self, liquidacao: OwnLiquidacoes) -> bool:
        """
        Atualiza status da transação na BaseTransacoesGestao
        
        Args:
            liquidacao: OwnLiquidacoes
            
        Returns:
            True se atualizado com sucesso
        """
        from adquirente_own.cargas_own.models import OwnExtratoTransacoes
        from gestao_financeira.models import BaseTransacoesGestao
        
        try:
            # Buscar transação correspondente
            transacao = OwnExtratoTransacoes.objects.filter(
                identificadorTransacao=liquidacao.identificadorTransacao
            ).first()
            
            if not transacao:
                registrar_log('own.liquidacao', f'⚠️ Transação não encontrada: {liquidacao.identificadorTransacao}', nivel='WARNING')
                return False
            
            # Atualizar dados de liquidação na transação
            transacao.statusPagamento = liquidacao.statusPagamento
            transacao.dataPagamentoReal = liquidacao.dataPagamentoReal
            transacao.antecipado = liquidacao.antecipada
            transacao.numeroTitulo = liquidacao.numeroTitulo
            transacao.save()
            
            # Atualizar BaseTransacoesGestao se já processada
            if transacao.processado:
                base_transacao = BaseTransacoesGestao.objects.filter(
                    adquirente='OWN',
                    var9=liquidacao.identificadorTransacao
                ).first()
                
                if base_transacao:
                    # Atualizar status de pagamento
                    # TODO: Mapear campos específicos conforme necessário
                    base_transacao.save()
                    registrar_log('own.liquidacao', f'✅ Status atualizado: {liquidacao.identificadorTransacao}')
            
            liquidacao.processado = True
            liquidacao.save()
            
            return True
            
        except Exception as e:
            registrar_log('own.liquidacao', f'❌ Erro ao atualizar status: {str(e)}', nivel='ERROR')
            return False
    
    def executar_carga_diaria(self, cnpj_cliente: str = None) -> Dict[str, Any]:
        """
        Executa carga diária de liquidações
        
        Args:
            cnpj_cliente: CNPJ específico ou None para todos
            
        Returns:
            Dict com resultado da carga
        """
        from adquirente_own.cargas_own.models import CredenciaisExtratoContaOwn
        
        # Data de ontem
        data_pagamento = datetime.now() - timedelta(days=1)
        
        registrar_log('own.liquidacao', f'🔄 Iniciando carga diária liquidações: {data_pagamento.date()}')
        
        # Buscar credenciais ativas
        if cnpj_cliente:
            credenciais = CredenciaisExtratoContaOwn.objects.filter(cnpj_white_label=cnpj_cliente, ativo=True)
        else:
            credenciais = CredenciaisExtratoContaOwn.objects.filter(ativo=True)
        
        total_liquidacoes = 0
        total_processadas = 0
        
        for credencial in credenciais:
            registrar_log('own.liquidacao', f'📋 Processando: {credencial.nome}')
            
            # Consultar liquidações
            result = self.consultar_liquidacoes(
                cnpj_cliente=credencial.cnpj_white_label,
                data_pagamento_real=data_pagamento
            )
            
            if not result.get('sucesso'):
                registrar_log('own.liquidacao', f'❌ Erro ao consultar: {credencial.nome}', nivel='ERROR')
                continue
            
            # Salvar liquidações
            for liquidacao_data in result.get('liquidacoes', []):
                try:
                    with transaction.atomic():
                        liquidacao_obj = self.salvar_liquidacao(liquidacao_data)
                        total_liquidacoes += 1
                        
                        # Atualizar status da transação
                        if self.atualizar_status_transacao(liquidacao_obj):
                            total_processadas += 1
                            
                except Exception as e:
                    registrar_log('own.liquidacao', f'❌ Erro ao processar: {str(e)}', nivel='ERROR')
                    continue
        
        registrar_log('own.liquidacao', f'✅ Carga concluída: {total_liquidacoes} liquidações, {total_processadas} processadas')
        
        return {
            'sucesso': True,
            'total_liquidacoes': total_liquidacoes,
            'total_processadas': total_processadas
        }
