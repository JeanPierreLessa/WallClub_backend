"""
Serviço para carga de extrato POS da Pinbank
Migração fiel de pinbank_carga_extrato_pos.php
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from django.db import connection, transaction
from .models import (
    CredenciaisExtratoContaPinbank,
    PinbankExtratoPOS
)
from pinbank.services import PinbankService
from wallclub_core.utilitarios.log_control import registrar_log


class CargaExtratoPOSService:
    """
    Serviço para carga de extrato POS da Pinbank
    Migração fiel de pinbank_carga_extrato_pos.php
    """

    def __init__(self):
        self.pinbank_service = PinbankService()
        self.modelo_tabela = PinbankExtratoPOS

    def traz_extrato_periodo(self, data_inicial: str, data_final: str) -> int:
        """
        Consulta e insere extrato POS da Pinbank no banco local

        Args:
            data_inicial: Data inicial no formato ISO (Y-m-d\TH:i:s.000\Z)
            data_final: Data final no formato ISO (Y-m-d\TH:i:s.000\Z)

        Returns:
            int: Número total de transações processadas
        """
        registrar_log('pinbank.cargas_pinbank', f"Iniciando trazExtratoPeriodo, período {data_inicial} a {data_final}")

        total_transacoes = 0

        # Buscar todas as credenciais
        credenciais = CredenciaisExtratoContaPinbank.objects.all()

        for credencial in credenciais:
            try:
                registrar_log('pinbank.cargas_pinbank', f"Processando estabelecimento - username: {credencial.username}, canal: {credencial.canal}, codigo_cliente: {credencial.codigo_cliente}")

                # Validar dados obrigatórios
                if not all([credencial.username, credencial.keyvalue,
                           credencial.canal, credencial.codigo_cliente]):
                    registrar_log('pinbank.cargas_pinbank', "Dados incompletos para este registro, pulando.")
                    continue

                # Montar payload de consulta - LIMITADO A 100000 LINHAS PARA TESTE
                quantidade_linhas = 100000
                dados_requisicao = {
                    "Data": {
                        "CodigoCanal": credencial.canal,
                        "CodigoCliente": credencial.codigo_cliente,
                        "DataInicial": data_inicial,
                        "DataFinal": data_final,
                        "Status": "Todos",
                        "MeioCaptura": "Todos",
                        "QuantidadeLinhasRetorno": quantidade_linhas
                    }
                }

                # Log simplificado (apenas para arquivo via log_control)
                registrar_log('pinbank.cargas_pinbank', f"Requisição: {credencial.username} | Canal: {credencial.canal} | Cliente: {credencial.codigo_cliente} | Período: {data_inicial} a {data_final}")

                # Fazer requisição para API Pinbank
                try:
                    registros = self.pinbank_service.consultar_extrato_pos_encrypted(
                        username=credencial.username,
                        password=credencial.keyvalue,
                        dados=dados_requisicao
                    )

                    if not isinstance(registros, list):
                        # Verificar se é "Sem resultado"
                        if (hasattr(registros, 'ResultCode') and registros.ResultCode == 1 and
                            hasattr(registros, 'Message') and registros.Message == 'Sem resultado.'):
                            registrar_log('pinbank.cargas_pinbank', "Sem resultado para este período/estabelecimento")
                            registros = []
                        else:
                            raise Exception("Formato de resposta inesperado da API: não é um array")

                    registrar_log('pinbank.cargas_pinbank', f"Registros decodificados com sucesso. Total: {len(registros)}")

                except Exception as e:
                    if '"Message": "Sem resultado."' in str(e):
                        registrar_log('pinbank.cargas_pinbank', "Sem resultado para este período/estabelecimento")
                        registros = []
                    else:
                        registrar_log('pinbank.cargas_pinbank', f"Erro ao processar resposta - {str(e)}", nivel='ERROR')
                        raise Exception(f"Erro ao processar resposta da API: {str(e)}")

                # Contar transações processadas
                total_transacoes += len(registros)

                # Processar registros em lotes de 100 para commit
                BATCH_SIZE = 100
                for i in range(0, len(registros), BATCH_SIZE):
                    lote = registros[i:i+BATCH_SIZE]
                    registrar_log('pinbank.cargas_pinbank', f"Processando lote {i//BATCH_SIZE + 1}: registros {i+1} a {min(i+BATCH_SIZE, len(registros))} de {len(registros)}")

                    with transaction.atomic():
                        for dados in lote:
                            self._processar_registro_extrato(dados, credencial.codigo_cliente)

                    registrar_log('pinbank.cargas_pinbank', f"Lote {i//BATCH_SIZE + 1} commitado com sucesso ({len(lote)} registros)")

            except Exception as e:
                registrar_log('pinbank.cargas_pinbank', f"Erro crítico (trazExtratoPeriodo): {str(e)}", nivel='ERROR')
                continue

        return total_transacoes

    def _processar_registro_extrato(self, dados: Dict, codigo_cliente: int):
        """
        Processa um registro individual do extrato
        Faz INSERT ou UPDATE conforme necessário
        """
        try:
            nsu_operacao = dados['NsuOperacao']
            numero_parcela = dados['NumeroParcela']

            # Verificar se registro já existe
            registro_existente = self.modelo_tabela.objects.filter(
                NsuOperacao=nsu_operacao,
                NumeroParcela=numero_parcela
            ).first()

            if not registro_existente:
                # Log detalhado do NSU sendo inserido
                nsu = dados.get('NsuOperacao')
                status_pag = dados.get('DescricaoStatusPagamento')
                id_status_pag = dados.get('IdStatusPagamento')
                registrar_log('pinbank.cargas_pinbank', f"Inserindo NSU {nsu} - Status: {status_pag} (ID: {id_status_pag})")

                # Usar SQL direto para INSERT - omitir campo id (AUTO_INCREMENT)
                with connection.cursor() as cursor:
                    cursor.execute(f"""
                        INSERT INTO wallclub.pinbankExtratoPOS (
                            codigo_cliente, IdTerminal, SerialNumber, Terminal, Bandeira, TipoCompra, DadosExtra,
                            CpfCnpjComprador, NomeRazaoSocialComprador, NumeroParcela, NumeroTotalParcelas,
                            DataTransacao, DataFuturaPagamento, CodAutorizAdquirente, NsuOperacao,
                            NsuOperacaoLoja, ValorBruto, ValorBrutoParcela, ValorLiquidoRepasse,
                            ValorSplit, IdStatus, DescricaoStatus, IdStatusPagamento,
                            DescricaoStatusPagamento, ValorTaxaAdm, ValorTaxaMes, NumeroCartao,
                            DataCancelamento, Submerchant, Lido
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                    """, [
                        codigo_cliente,  # codigo_cliente
                        dados.get('IdTerminal'),  # IdTerminal
                        dados.get('SerialNumber'),  # SerialNumber
                        dados.get('Terminal'),  # Terminal
                        dados.get('Bandeira'),  # Bandeira
                        dados.get('TipoCompra'),  # TipoCompra
                        dados.get('DadosExtra'),  # DadosExtra
                        dados.get('CpfCnpjComprador'),  # CpfCnpjComprador
                        dados.get('NomeRazaoSocialComprador'),  # NomeRazaoSocialComprador
                        dados.get('NumeroParcela'),  # NumeroParcela
                        dados.get('NumeroTotalParcelas'),  # NumeroTotalParcelas
                        dados.get('DataTransacao'),  # DataTransacao
                        dados.get('DataFuturaPagamento'),  # DataFuturaPagamento
                        dados.get('CodAutorizAdquirente'),  # CodAutorizAdquirente
                        dados.get('NsuOperacao'),  # NsuOperacao
                        dados.get('NsuOperacaoLoja'),  # NsuOperacaoLoja
                        dados.get('ValorBruto'),  # ValorBruto
                        dados.get('ValorBrutoParcela'),  # ValorBrutoParcela
                        dados.get('ValorLiquidoRepasse'),  # ValorLiquidoRepasse
                        dados.get('ValorSplit'),  # ValorSplit
                        dados.get('IdStatus'),  # IdStatus
                        dados.get('DescricaoStatus'),  # DescricaoStatus
                        dados.get('IdStatusPagamento'),  # IdStatusPagamento
                        dados.get('DescricaoStatusPagamento'),  # DescricaoStatusPagamento
                        dados.get('ValorTaxaAdm'),  # ValorTaxaAdm
                        dados.get('ValorTaxaMes'),  # ValorTaxaMes
                        dados.get('NumeroCartao'),  # NumeroCartao
                        dados.get('DataCancelamento'),  # DataCancelamento
                        dados.get('Submerchant'),  # Submerchant
                        0  # Lido = 0 (novo registro não processado)
                    ])

            else:
                # Registro existe, verificar apenas campos que podem mudar
                campos_alterados = {}

                # Verificar apenas os 8 campos que podem mudar conforme especificação
                campos_verificar = {
                    'DadosExtra': dados.get('DadosExtra'),
                    'DataFuturaPagamento': dados.get('DataFuturaPagamento'),
                    'CodAutorizAdquirente': dados.get('CodAutorizAdquirente'),
                    'IdStatus': dados.get('IdStatus'),
                    'DescricaoStatus': dados.get('DescricaoStatus'),
                    'IdStatusPagamento': dados.get('IdStatusPagamento'),
                    'DescricaoStatusPagamento': dados.get('DescricaoStatusPagamento'),
                    'DataCancelamento': dados.get('DataCancelamento')
                }

                # Verificar se algum campo relevante mudou
                campos_mudaram = False
                for campo, novo_valor in campos_verificar.items():
                    valor_atual = getattr(registro_existente, campo)
                    if str(valor_atual) != str(novo_valor):
                        campos_alterados[campo] = novo_valor
                        campos_mudaram = True

                # Se algum campo mudou, setar Lido = 0 para reprocessamento
                if campos_mudaram:
                    campos_alterados['Lido'] = 0

                    # Log detalhado do NSU sendo atualizado
                    nsu = dados.get('NsuOperacao')
                    status_pag_novo = dados.get('DescricaoStatusPagamento')
                    id_status_pag_novo = dados.get('IdStatusPagamento')
                    registrar_log('pinbank.cargas_pinbank', f"Atualizando NSU {nsu} - Novo Status: {status_pag_novo} (ID: {id_status_pag_novo})")

                # Atualizar se houver campos alterados
                if campos_alterados:
                    for campo, valor in campos_alterados.items():
                        setattr(registro_existente, campo, valor)
                    registro_existente.save()
        except Exception as e:
            raise

    def buscar_ultimo_ano(self) -> int:
        """Busca transações do último ano"""
        data_inicio = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%dT%H:%M:%S.000Z')
        data_fim = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')

        transacoes = self.traz_extrato_periodo(data_inicio, data_fim)
        return transacoes

    def buscar_ultimos_60_dias(self) -> int:
        """Busca transações dos últimos 60 dias"""
        data_inicio = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%dT%H:%M:%S.000Z')
        data_fim = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')

        transacoes = self.traz_extrato_periodo(data_inicio, data_fim)
        return transacoes

    def buscar_ultimas_72_horas(self) -> int:
        """Busca transações das últimas 72 horas"""
        data_inicio = (datetime.now() - timedelta(hours=72)).strftime('%Y-%m-%dT%H:%M:%S.000Z')
        data_fim = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')

        transacoes = self.traz_extrato_periodo(data_inicio, data_fim)
        return transacoes

    def buscar_ultimos_80_minutos(self) -> int:
        """Busca transações dos últimos 30 minutos"""
        data_inicio = (datetime.now() - timedelta(minutes=80)).strftime('%Y-%m-%dT%H:%M:%S.000Z')
        data_fim = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')

        transacoes = self.traz_extrato_periodo(data_inicio, data_fim)
        return transacoes

    def buscar_ultimos_90_dias(self) -> int:
        """Busca transações dos últimos 90 dias"""
        data_inicio = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%dT%H:%M:%S.000Z')
        data_fim = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')

        transacoes = self.traz_extrato_periodo(data_inicio, data_fim)
        return transacoes

    def buscar_ultimos_30_dias(self) -> int:
        """Busca transações dos últimos 30 dias"""
        data_inicio = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%dT00:00:00.000Z')
        data_fim = datetime.now().strftime('%Y-%m-%dT23:59:59.000Z')

        transacoes = self.traz_extrato_periodo(data_inicio, data_fim)
        return transacoes
