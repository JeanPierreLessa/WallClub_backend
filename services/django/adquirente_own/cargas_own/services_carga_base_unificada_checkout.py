"""
Serviço para carga da Base Transações Unificadas - Checkout OWN
Processa transações de checkout OWN (vendas diretas via portal de vendas)
Usa CalculadoraBaseUnificada (tipo_operacao: Wallet)

Similar ao Pinbank, mas para transações OWN:
- Insere em base_transacoes_unificadas
- 1 linha por transação (não duplica por parcela)
- tipo_operacao = 'Wallet' (não passa por credenciadora)
- adquirente = 'OWN'
"""

from typing import Dict, Any
from django.db import connection, transaction
from wallclub_core.utilitarios.log_control import registrar_log


class CargaBaseUnificadaCheckoutOwnService:
    """
    Serviço para carga da base unificada - Checkout OWN
    Regra: 1 linha por transação (NSU único), não por parcela
    Filtro: gateway = 'OWN' e status = 'APROVADA'
    Tipo: Wallet (vendas diretas)
    Adquirente: OWN
    """

    def __init__(self):
        from parametros_wallclub.calculadora_base_unificada import CalculadoraBaseUnificada
        self.calculadora = CalculadoraBaseUnificada()

    def carregar_valores_primarios(self, limite: int = None, nsu: str = None) -> int:
        """
        Rotina principal de carga de variáveis primárias
        Processa transações OWN de checkout ainda não processadas

        Args:
            limite: Limite de registros
            nsu: NSU específico

        Returns:
            Total de transações processadas
        """
        registrar_log('own.cargas_own', f"🚀 Iniciando carga Base Unificada Checkout OWN")

        limit_clause = f"LIMIT {limite}" if limite else ""
        nsu_clause = f"AND ct.nsu = '{nsu}'" if nsu else ""

        # Query para buscar transações OWN de checkout não processadas
        query = f"""
            SELECT
                oet.id,
                oet.identificadorTransacao,
                ct.loja_id,
                oet.valor,
                oet.quantidadeParcelas,
                oet.dataHoraTransacao,
                oet.modalidade,
                oet.codigoAutorizacao,
                l.canal_id,
                l.razao_social as loja_nome,
                c.nome as canal_nome,
                oet.bandeira,
                oet.numeroCartao,
                ct.id as checkout_transaction_id
            FROM ownExtratoTransacoes oet
            INNER JOIN checkout_transactions ct ON oet.identificadorTransacao = ct.tx_transaction_id
            INNER JOIN loja l ON ct.loja_id = l.id
            INNER JOIN canal c ON l.canal_id = c.id
            WHERE oet.lido = 0
                AND ct.gateway = 'OWN'
                AND ct.status = 'APROVADA'
                {nsu_clause}
            ORDER BY oet.id
            {limit_clause}
        """

        total_processadas = 0

        with connection.cursor() as cursor:
            # LOG TEMPORÁRIO: Ver query completa
            registrar_log('own.cargas_own', f"🔍 QUERY: {query}")

            cursor.execute(query)
            transacoes = cursor.fetchall()

            registrar_log('own.cargas_own', f"📊 Encontradas {len(transacoes)} transações OWN checkout para processar")

            # LOG TEMPORÁRIO: Ver primeiras transações
            if transacoes:
                registrar_log('own.cargas_own', f"📋 Primeira transação: {transacoes[0]}")

            for row in transacoes:
                try:
                    with transaction.atomic():
                        oet_id = row[0]
                        identificador_transacao = row[1]
                        loja_id = row[2]
                        valor = float(row[3])
                        parcelas = row[4] or 1
                        data_transacao = row[5]
                        modalidade = row[6]
                        codigo_autorizacao = row[7]
                        canal_id = row[8]
                        loja_nome = row[9]
                        canal_nome = row[10]
                        bandeira = row[11]
                        numero_cartao = row[12]
                        checkout_transaction_id = row[13]

                        # Preparar dados para calculadora (compatível com CalculadoraBaseUnificada)
                        dados_transacao = {
                            'id': oet_id,
                            'SerialNumber': '',  # Checkout não tem serial
                            'idTerminal': 0,  # Checkout não tem terminal
                            'NsuOperacao': str(identificador_transacao),
                            'DataTransacao': data_transacao.strftime('%Y-%m-%dT%H:%M:%S') if data_transacao else '',
                            'HoraTransacao': data_transacao.strftime('%H:%M:%S') if data_transacao else '',
                            'ValorTransacao': valor,
                            'ValorBruto': valor,
                            'valor_original': valor,
                            'ValorBrutoParcela': valor / parcelas if parcelas > 0 else valor,
                            'QuantidadeParcelas': parcelas,
                            'NumeroTotalParcelas': parcelas,
                            'NumeroParcela': 1,
                            'Bandeira': bandeira or 'VISA',
                            'TipoCompra': 'CREDITO' if 'CREDITO' in (modalidade or '') else 'DEBITO',
                            'CodigoAutorizacao': codigo_autorizacao or '',
                            'nsuAcquirer': codigo_autorizacao or '',
                            'cpf': '',  # Checkout não tem CPF
                            'DataCancelamento': None,
                            'tipo_operacao': 'Wallet',
                            'adquirente': 'OWN',
                            'origem_transacao': 'Checkout'
                        }

                        info_loja = {
                            'id': loja_id,
                            'nome': loja_nome,
                            'loja': loja_nome,
                            'canal_id': canal_id
                        }

                        info_canal = {
                            'id': canal_id,
                            'nome': canal_nome,
                            'canal': canal_nome
                        }

                        # Calcular variáveis
                        variaveis = self.calculadora.calcular_valores_primarios(
                            dados_linha=dados_transacao,
                            tabela='checkout_transactions',
                            info_loja=info_loja,
                            info_canal=info_canal
                        )

                        # DEBUG: Log do tipo e amostra das variáveis
                        registrar_log('own.cargas_own', f"DEBUG variaveis type: {type(variaveis)}")
                        if variaveis:
                            amostra = {k: v for k, v in list(variaveis.items())[:5]}
                            registrar_log('own.cargas_own', f"DEBUG variaveis amostra: {amostra}")

                        # Inserir na base unificada
                        self._inserir_base_unificada(variaveis)

                        # Marcar como lido e processado na tabela ownExtratoTransacoes
                        from adquirente_own.models import OwnExtratoTransacoes
                        OwnExtratoTransacoes.objects.filter(id=oet_id).update(lido=1, processado=1)

                        total_processadas += 1

                        if total_processadas % 100 == 0:
                            registrar_log('own.cargas_own', f"✅ Processadas {total_processadas} transações...")

                except Exception as e:
                    import traceback
                    registrar_log(
                        'own.cargas_own',
                        f"❌ Erro ao processar transação {identificador_transacao}: {str(e)}\n{traceback.format_exc()}",
                        nivel='ERROR'
                    )
                    continue

        registrar_log('own.cargas_own', f"✅ Carga concluída: {total_processadas} transações processadas")
        return total_processadas

    def _inserir_base_unificada(self, variaveis: Dict[str, Any]):
        """
        Insere registro na base_transacoes_unificadas

        Args:
            variaveis: Dicionário com todas as variáveis calculadas
        """
        # Preparar campos e valores - começar com campos obrigatórios
        campos = ['tipo_operacao', 'adquirente', 'origem_transacao', 'data_transacao']
        valores = [
            variaveis.get('tipo_operacao'),
            variaveis.get('adquirente'),
            variaveis.get('origem_transacao'),
            variaveis.get('data_transacao')
        ]

        for campo, valor in variaveis.items():
            if valor is not None and valor != '':
                # Pular campos que não existem na tabela ou já foram adicionados
                if campo in ['id_fila_extrato', 'canal_id', 'tipo_operacao', 'adquirente', 'origem_transacao', 'data_transacao']:
                    continue

                # Se valor é dict, extrair chave '0' (valor para Wallet/e-commerce)
                if isinstance(valor, dict):
                    if '0' in valor:
                        valor = valor['0']
                    elif 'A' in valor:
                        valor = valor['A']
                    else:
                        registrar_log('own.cargas_own', f"⚠️ Campo {campo} dict sem chave '0' ou 'A': {valor}", nivel='WARNING')
                        continue

                # Adicionar prefixo 'var' se for número
                nome_campo = f'var{campo}' if isinstance(campo, int) else str(campo)
                campos.append(nome_campo)
                valores.append(valor)

        if not campos:
            return

        campos_str = ', '.join(campos)
        placeholders = ', '.join(['%s'] * len(valores))

        # Montar SQL de insert com ON DUPLICATE KEY UPDATE
        campos_update = [f'{campo} = VALUES({campo})' for campo in campos if campo not in ['var9', 'tipo_operacao', 'adquirente']]
        update_clause = ', '.join(campos_update)

        sql = f"""
            INSERT INTO base_transacoes_unificadas ({campos_str})
            VALUES ({placeholders})
            ON DUPLICATE KEY UPDATE {update_clause}
        """

        with connection.cursor() as cursor:
            cursor.execute(sql, valores)

    def executar_carga_diaria(self) -> Dict[str, Any]:
        """
        Executa carga diária de transações OWN checkout
        Processa todas as transações pendentes

        Returns:
            Dict com resultado da carga
        """
        try:
            total = self.carregar_valores_primarios()

            return {
                'sucesso': True,
                'total_processadas': total,
                'mensagem': f'Carga concluída: {total} transações processadas'
            }
        except Exception as e:
            registrar_log('own.cargas_own', f"❌ Erro na carga diária: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': str(e)
            }
