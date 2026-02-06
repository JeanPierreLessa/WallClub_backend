"""
Serviço para carga de extrato da API Own Financial
Endpoint: POST /agilli/transacoes/v2/buscaTransacoesGerais
Equivalente ao services_carga_extrato_pos.py do Pinbank
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta
from django.db import transaction
from adquirente_own.services import OwnService
from adquirente_own.cargas_own.models import OwnExtratoTransacoes
from wallclub_core.utilitarios.log_control import registrar_log


class CargaExtratoOwnService:
    """Serviço para carga de transações Own Financial"""

    def __init__(self):
        self.own_service = OwnService()

    def buscar_transacoes_gerais(
        self,
        cnpj_cliente: str,
        data_inicial: datetime,
        data_final: datetime,
        doc_parceiro: str = None
    ) -> Dict[str, Any]:
        """
        Busca transações gerais da API Own

        Args:
            cnpj_cliente: CNPJ do cliente
            data_inicial: Data inicial da busca
            data_final: Data final da busca
            doc_parceiro: CNPJ do parceiro (opcional)

        Returns:
            Dict com sucesso e lista de transações
        """
        from adquirente_own.models_cadastro import LojaOwn
        from wallclub_core.estr_organizacional.loja import Loja
        from adquirente_own.services_credenciais import CredenciaisOwnService

        # Obter loja OWN
        loja = Loja.objects.filter(cnpj=cnpj_cliente).first()
        if not loja:
            registrar_log('adquirente_own.cargas_own', f'❌ Loja não encontrada: {cnpj_cliente}', nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Loja não encontrada'
            }

        loja_own = LojaOwn.objects.filter(
            loja_id=loja.id,
            status_credenciamento='APROVADO',
            sincronizado=True
        ).first()

        if not loja_own:
            registrar_log('adquirente_own.cargas_own', f'❌ Loja OWN não encontrada ou não aprovada: {cnpj_cliente}', nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Loja OWN não encontrada ou não aprovada'
            }

        # Obter credenciais globais da OWN (AWS Secrets Manager)
        credenciais_service = CredenciaisOwnService()
        credenciais = credenciais_service.obter_credenciais_core()

        if not credenciais:
            registrar_log('adquirente_own.cargas_own', f'❌ Credenciais OWN não encontradas', nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Credenciais OWN não encontradas'
            }

        client_id = credenciais['client_id']
        client_secret = credenciais['client_secret']
        scope = credenciais['scope']

        # Preparar payload
        payload = {
            'cnpjCliente': cnpj_cliente,
            'dataInicial': data_inicial.strftime('%Y-%m-%d %H:%M'),
            'dataFinal': data_final.strftime('%Y-%m-%d %H:%M')
        }

        if doc_parceiro:
            payload['docParceiro'] = doc_parceiro

        registrar_log('adquirente_own.cargas_own', f'📥 Buscando transações: {data_inicial} a {data_final}')

        # Inicializar service com environment de produção
        own_service = OwnService(environment='production')

        # Fazer requisição
        response = own_service.fazer_requisicao_autenticada(
            method='POST',
            endpoint='/transacoes/v2/buscaTransacoesGerais',
            client_id=client_id,
            client_secret=client_secret,
            scope=scope,
            data=payload
        )

        if not response.get('sucesso'):
            return response

        transacoes = response.get('dados', [])
        registrar_log('adquirente_own.cargas_own', f'✅ {len(transacoes)} transações encontradas')

        return {
            'sucesso': True,
            'transacoes': transacoes,
            'total': len(transacoes)
        }

    def salvar_transacao(self, transacao_data: Dict[str, Any]) -> OwnExtratoTransacoes:
        """
        Salva ou atualiza transação no banco

        Args:
            transacao_data: Dados da transação da API Own

        Returns:
            OwnExtratoTransacoes criado ou atualizado
        """
        identificador = transacao_data['identificadorTransacao']

        # Verificar se já existe
        transacao_obj, created = OwnExtratoTransacoes.objects.update_or_create(
            identificadorTransacao=identificador,
            defaults={
                'cnpjCpfCliente': transacao_data.get('cnpjCpfCliente'),
                'cnpjCpfParceiro': transacao_data.get('cnpjCpfParceiro'),
                'data': datetime.fromisoformat(transacao_data['data'].replace('T', ' ')),
                'numeroSerieEquipamento': transacao_data.get('numeroSerieEquipamento'),
                'valor': transacao_data.get('valor', 0) / 100,  # Converter centavos para reais
                'quantidadeParcelas': transacao_data.get('quantidadeParcelas', 1),
                'mdr': transacao_data.get('mdr') / 100 if transacao_data.get('mdr') is not None else None,
                'valorAntecipacaoTotal': transacao_data.get('valorAntecipacaoTotal') / 100 if transacao_data.get('valorAntecipacaoTotal') else None,
                'taxaAntecipacaoTotal': transacao_data.get('taxaAntecipacaoTotal'),
                'statusTransacao': transacao_data.get('statusTransacao'),
                'bandeira': transacao_data.get('bandeira'),
                'modalidade': transacao_data.get('modalidade'),
                'codigoAutorizacao': transacao_data.get('codigoAutorizacao'),
                'numeroCartao': transacao_data.get('numeroCartao'),
                'lido': False,
                'processado': False
            }
        )

        # Processar parcelas se existirem
        if 'parcelas' in transacao_data and transacao_data['parcelas']:
            registrar_log('adquirente_own.cargas_own', f'📦 Transação {identificador} tem {len(transacao_data["parcelas"])} parcelas')
            self._processar_parcelas(transacao_obj, transacao_data['parcelas'])
        else:
            registrar_log('adquirente_own.cargas_own', f'⚠️ Transação {identificador} SEM array parcelas na resposta da API', nivel='WARNING')

        action = 'criada' if created else 'atualizada'
        registrar_log('adquirente_own.cargas_own', f'💾 Transação {action}: {identificador}')

        return transacao_obj

    def _processar_parcelas(self, transacao_obj: OwnExtratoTransacoes, parcelas: List[Dict]):
        """
        Processa parcelas da transação
        Atualiza campos de parcela na transação principal
        """
        if not parcelas:
            return

        # Pegar primeira parcela para atualizar dados
        primeira_parcela = parcelas[0]

        registrar_log('adquirente_own.cargas_own', f'🔍 Primeira parcela: {primeira_parcela}')

        transacao_obj.parcelaId = primeira_parcela.get('parcelaId')
        transacao_obj.statusPagamento = primeira_parcela.get('statusPagamento')
        transacao_obj.dataHoraTransacao = datetime.fromisoformat(primeira_parcela['dataHoraTransacao'].replace('T', ' ')) if primeira_parcela.get('dataHoraTransacao') else None
        transacao_obj.mdrParcela = primeira_parcela.get('mdr', 0) / 100 if primeira_parcela.get('mdr') else None
        transacao_obj.numeroParcela = primeira_parcela.get('numeroParcela')

        valor_parcela_raw = primeira_parcela.get('valorParcela')
        transacao_obj.valorParcela = valor_parcela_raw / 100 if valor_parcela_raw else None
        registrar_log('adquirente_own.cargas_own', f'💰 valorParcela calculado: {transacao_obj.valorParcela} (raw: {valor_parcela_raw})')
        transacao_obj.dataPagamentoPrevista = datetime.strptime(primeira_parcela['dataPagamentoPrevista'], '%Y-%m-%d').date() if primeira_parcela.get('dataPagamentoPrevista') else None
        transacao_obj.dataPagamentoReal = datetime.strptime(primeira_parcela['dataPagamentoReal'], '%Y-%m-%d').date() if primeira_parcela.get('dataPagamentoReal') else None
        transacao_obj.valorAntecipado = primeira_parcela.get('valorAntecipado', 0) / 100 if primeira_parcela.get('valorAntecipado') else None
        transacao_obj.taxaAntecipada = primeira_parcela.get('taxaAntecipada')
        transacao_obj.antecipado = primeira_parcela.get('antecipado')
        transacao_obj.numeroTitulo = primeira_parcela.get('numeroTitulo')

        transacao_obj.save()

    # DEPRECATED: Método removido - usar services_carga_base_unificada_pos.py
    # def processar_para_base_gestao(self, transacao: OwnExtratoTransacoes):
    #     pass

    def executar_carga_diaria(self, cnpj_cliente: str = None) -> Dict[str, Any]:
        """
        Executa carga diária de transações

        Args:
            cnpj_cliente: CNPJ específico ou None para todos

        Returns:
            Dict com resultado da carga
        """
        from adquirente_own.models_cadastro import LojaOwn
        from wallclub_core.estr_organizacional.loja import Loja

        # Data de ontem
        data_final = datetime.now()
        data_inicial = data_final - timedelta(days=1)

        registrar_log('adquirente_own.cargas_own', f'🔄 Iniciando carga diária: {data_inicial.date()}')

        # Buscar lojas OWN com credenciamento aprovado
        lojas_own = LojaOwn.objects.filter(
            status_credenciamento='APROVADO',
            sincronizado=True
        )

        total_transacoes = 0
        total_processadas = 0

        for loja_own in lojas_own:
            loja = Loja.objects.filter(id=loja_own.loja_id).first()
            if not loja:
                continue

            if cnpj_cliente and loja.cnpj != cnpj_cliente:
                continue

            registrar_log('adquirente_own.cargas_own', f'📋 Processando: {loja.razao_social} (CNPJ: {loja.cnpj})')

            # Buscar transações
            result = self.buscar_transacoes_gerais(
                cnpj_cliente=loja.cnpj,
                data_inicial=data_inicial,
                data_final=data_final
            )

            if not result.get('sucesso'):
                registrar_log('adquirente_own.cargas_own', f'❌ Erro ao buscar: {loja.razao_social}', nivel='ERROR')
                continue

            # Salvar transações
            for transacao_data in result.get('transacoes', []):
                try:
                    with transaction.atomic():
                        transacao_obj = self.salvar_transacao(transacao_data)
                        total_transacoes += 1

                        # Processar para base gestão se não processado
                        if not transacao_obj.processado:
                            self.processar_para_base_gestao(transacao_obj)
                            total_processadas += 1

                except Exception as e:
                    registrar_log('own.carga', f'❌ Erro ao processar: {str(e)}', nivel='ERROR')
                    continue

        registrar_log('own.carga', f'✅ Carga concluída: {total_transacoes} transações, {total_processadas} processadas')

        return {
            'sucesso': True,
            'total_transacoes': total_transacoes,
            'total_processadas': total_processadas
        }
