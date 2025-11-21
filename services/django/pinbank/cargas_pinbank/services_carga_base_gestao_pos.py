"""
Serviço para carga da Base de Gestão POS (Wallet)
Processa transações da tabela transactiondata (Wallet)
Usa CalculadoraBaseGestao
"""

from typing import Dict, Any
from django.db import connection, transaction
from .models import PinbankExtratoPOS
from gestao_financeira.models import BaseTransacoesGestao, BaseTransacoesGestaoErroCarga
from wallclub_core.utilitarios.log_control import registrar_log


class CargaBaseGestaoPOSService:
    """
    Serviço principal para carga da base de gestão POS (Wallet)
    Migração fiel de mainCarregaValoresPrimarios()
    """

    def __init__(self):
        # Import local para evitar import circular
        from parametros_wallclub.calculadora_base_gestao import CalculadoraBaseGestao
        self.calculadora = CalculadoraBaseGestao()

    def carregar_valores_primarios(self, limite: int = None, nsu: str = None) -> int:
        """
        Rotina principal de carga de variáveis primárias
        Processa registros com lido = 0
        """
        registrar_log('pinbank.cargas_pinbank', "Iniciando carga de valores primários")

        # Query principal - busca registros não lidos
        limit_clause = f"LIMIT {limite}" if limite else ""
        nsu_clause = f"AND pep.NsuOperacao = '{nsu}'" if nsu else ""

        with connection.cursor() as cursor:
            cursor.execute(f"""
                SELECT   pep.id,
                         pep.codigo_cliente,
                         pep.idTerminal,
                         pep.SerialNumber,
                         pep.Terminal,
                         pep.Bandeira,
                         pep.TipoCompra,
                         pep.DadosExtra,
                         pep.CpfCnpjComprador,
                         pep.NomeRazaoSocialComprador,
                         pep.NumeroParcela,
                         pep.NumeroTotalParcelas,
                         pep.DataTransacao,
                         pep.DataFuturaPagamento,
                         pep.CodAutorizAdquirente,
                         pep.NsuOperacao,
                         pep.NsuOperacaoLoja,
                         pep.ValorBruto,
                         pep.ValorBrutoParcela,
                         pep.ValorLiquidoRepasse,
                         pep.ValorSplit,
                         pep.IdStatus,
                         pep.DescricaoStatus,
                         pep.IdStatusPagamento,
                         pep.DescricaoStatusPagamento,
                         pep.ValorTaxaAdm,
                         pep.ValorTaxaMes,
                         pep.NumeroCartao,
                         pep.DataCancelamento,
                         pep.Submerchant,
                         t.cpf,
                         t.nsuAcquirer,
                         t.valor_original,
                         ( SELECT  SUM(pep2.ValorLiquidoRepasse)
                            FROM   wallclub.pinbankExtratoPOS pep2
                            WHERE  pep.nsuOperacao = pep2.NsuOperacao
                                   AND pep2.DescricaoStatusPagamento in ('Pago','Pago-M'))   vRepasse,
                         pe.var44 f44,
                         pe.var45 f45,
                         pe.var58 f58,
                         pe.var59 f59,
                         pe.var66 f66,
                         pe.var71 f71,
                         pe.var100 f100,
                         pe.var111 f111,
                         pe.var112 f112
                FROM     wallclub.pinbankExtratoPOS pep
                INNER JOIN wallclub.transactiondata t ON pep.NsuOperacao = t.nsuPinbank
                LEFT JOIN wallclub.pagamentos_efetuados pe ON pe.nsu = t.nsuPinbank
                WHERE    1=1
                         and pep.lido = 0
                         {nsu_clause}
                ORDER BY pep.id
                {limit_clause}
            """)

            colunas = [desc[0] for desc in cursor.description]
            registros_processados = 0

            # Processar em lotes de 100 registros SEM carregar tudo em memória
            BATCH_SIZE = 100
            registros_processados_total = 0
            lote_atual = []
            numero_lote = 1

            # Processar linha por linha (streaming)
            while True:
                row = cursor.fetchone()
                if row is None:
                    break

                lote_atual.append(row)

                # Quando completar um lote de 100, processar
                if len(lote_atual) >= BATCH_SIZE:
                    registrar_log('pinbank.cargas_pinbank', f"Processando lote {numero_lote}: {len(lote_atual)} registros")

                    with transaction.atomic():
                        for row_lote in lote_atual:
                            linha = dict(zip(colunas, row_lote))

                            try:
                                # Calcular valores primários
                                valores = self.calculadora.calcular_valores_primarios(linha, tabela='transactiondata')

                                # Inserir na base de gestão
                                sucesso = self._inserir_valores_base_gestao(valores, linha.get('codigo_cliente'))

                                if sucesso:
                                    # Marcar como lido
                                    PinbankExtratoPOS.objects.filter(id=linha['id']).update(Lido=1)
                                    registros_processados += 1
                                else:
                                    registrar_log('pinbank.cargas_pinbank', f"Valores primários não foram atualizados para ID={linha['id']}", nivel='ERROR')

                            except Exception as e:
                                import traceback
                                erro_detalhado = traceback.format_exc()
                                registrar_log('pinbank.cargas_pinbank', f"Erro crítico (MainCarregaValoresPrimarios): ID={linha['id']}, Erro: {str(e)}", nivel='ERROR')
                                registrar_log('pinbank.cargas_pinbank', f"Traceback completo: {erro_detalhado}", nivel='ERROR')

                                # Registrar erro
                                BaseTransacoesGestaoErroCarga.objects.create(
                                    idFilaExtrato=linha['id'],
                                    mensagem=str(e)
                                )

                    registrar_log('pinbank.cargas_pinbank', f"Lote {numero_lote} commitado com sucesso ({len(lote_atual)} registros processados)")
                    lote_atual = []
                    numero_lote += 1

            # Processar último lote se houver registros restantes
            if lote_atual:
                registrar_log('pinbank.cargas_pinbank', f"Processando último lote {numero_lote}: {len(lote_atual)} registros")

                with transaction.atomic():
                    for row_lote in lote_atual:
                        linha = dict(zip(colunas, row_lote))

                        try:
                            # Preservar campos originais importantes antes dos cálculos
                            campos_originais = {
                                'DataTransacao': linha.get('DataTransacao'),
                                'DataFuturaPagamento': linha.get('DataFuturaPagamento'),
                                'NsuOperacao': linha.get('NsuOperacao'),
                                'id': linha.get('id')
                            }

                            # Calcular valores usando a calculadora
                            valores_calculados = self.calculadora.calcular_valores_primarios(linha, tabela='transactiondata')

                            # Atualizar transação com valores calculados
                            linha.update(valores_calculados)

                            # Restaurar campos originais importantes
                            linha.update(campos_originais)

                            # Inserir na base de gestão
                            sucesso = self._inserir_valores_base_gestao(linha, linha.get('codigo_cliente'))

                            if sucesso:
                                # Marcar como lido
                                PinbankExtratoPOS.objects.filter(id=linha['id']).update(Lido=1)
                                registros_processados += 1
                            else:
                                registrar_log('pinbank.cargas_pinbank', f"Valores primários não foram atualizados para ID={linha['id']}")

                        except Exception as e:
                            import traceback
                            erro_detalhado = traceback.format_exc()
                            registrar_log('pinbank.cargas_pinbank', f"Erro crítico (MainCarregaValoresPrimarios): ID={linha['id']}, Erro: {str(e)}", nivel='ERROR')
                            registrar_log('pinbank.cargas_pinbank', f"Traceback completo: {erro_detalhado}", nivel='ERROR')

                            # Registrar erro
                            BaseTransacoesGestaoErroCarga.objects.create(
                                idFilaExtrato=linha['id'],
                                mensagem=str(e)
                            )

                registrar_log('pinbank.cargas_pinbank', f"Último lote {numero_lote} commitado com sucesso ({len(lote_atual)} registros processados)")

        registrar_log('pinbank.cargas_pinbank', f"Carga de valores primários finalizada. Registros processados: {registros_processados}")
        return registros_processados

    def _inserir_valores_base_gestao(self, valores: Dict[int, Any], codigo_cliente: int = None) -> bool:
        """Insere valores na base de gestão usando SQL direto"""
        try:
            # Usar idFilaExtrato como chave primária
            id_fila_extrato = valores.get('id_fila_extrato')
            if not id_fila_extrato:
                return False

            # Mapear valores para campos
            campos_mapeados = self._mapear_valores_para_campos(valores)

            # CargaBaseGestaoPOSService SEMPRE é Wallet
            campos_mapeados['banco'] = 'PIN'
            campos_mapeados['tipo_operacao'] = 'Wallet'

            # Usar SQL direto para evitar problemas do Django ORM
            with connection.cursor() as cursor:
                # Verificar se registro já existe
                cursor.execute(
                    "SELECT id FROM wallclub.baseTransacoesGestao WHERE idFilaExtrato = %s",
                    [id_fila_extrato]
                )
                registro_existente = cursor.fetchone()

                if registro_existente:
                    # Atualizar registro existente
                    self._atualizar_registro_sql(cursor, registro_existente[0], campos_mapeados)
                else:
                    # Inserir novo registro
                    self._inserir_registro_sql(cursor, id_fila_extrato, campos_mapeados)

            return True

        except Exception as e:
            import traceback
            erro_completo = traceback.format_exc()
            registrar_log('pinbank.cargas_pinbank', f"Erro ao inserir valores na base de gestão: {str(e)}", nivel='ERROR')
            registrar_log('pinbank.cargas_pinbank', f"Traceback completo: {erro_completo}", nivel='ERROR')
            return False

    def _mapear_valores_para_campos(self, valores: Dict[int, Any]) -> Dict[str, Any]:
        """Mapeia valores calculados para campos do modelo"""
        campos = {}

        # Mapear valores numerados para campos var0-var130
        for i in range(131):  # 0 a 130
            if i in valores:
                campo_nome = f'var{i}'
                if hasattr(BaseTransacoesGestao, campo_nome):
                    valor = valores[i]
                    # Extrair valor correto se for um dicionário (arrays do PHP)
                    if isinstance(valor, dict):
                        # Mapear chave "0" para campo principal (prioridade)
                        if "0" in valor:
                            campos[campo_nome] = valor["0"]
                        else:
                            # Se não tem chave "0", usar None para campo principal
                            campos[campo_nome] = None

                        # Mapear chaves adicionais para campos específicos
                        if "A" in valor and hasattr(BaseTransacoesGestao, f'{campo_nome}_A'):
                            campos[f'{campo_nome}_A'] = valor["A"]
                        if "B" in valor and hasattr(BaseTransacoesGestao, f'{campo_nome}_B'):
                            campos[f'{campo_nome}_B'] = valor["B"]
                    else:
                        campos[campo_nome] = valor

        # Mapear campos especiais
        if 'banco' in valores:
            campos['banco'] = valores['banco']

        # Popular data_transacao a partir de var0 (data) e var1 (hora)
        if 0 in valores and 1 in valores:
            try:
                from datetime import datetime
                data_str = valores[0]  # var0 = data no formato dd/mm/yyyy
                hora_str = valores[1]  # var1 = hora no formato HH:MM:SS

                if data_str and hora_str:
                    # Converter data de dd/mm/yyyy para yyyy-mm-dd
                    data_parts = data_str.split('/')
                    if len(data_parts) == 3:
                        data_formatada = f"{data_parts[2]}-{data_parts[1]}-{data_parts[0]}"
                        datetime_str = f"{data_formatada} {hora_str}"
                        # Usar datetime NAIVE para evitar conversão de timezone
                        campos['data_transacao'] = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
            except Exception as e:
                campos['data_transacao'] = None

        # Adicionar campos de timestamp obrigatórios usando horário local brasileiro
        import os
        from datetime import datetime

        # Forçar timezone brasileiro no container
        os.environ['TZ'] = 'America/Sao_Paulo'

        # Usar datetime naive em horário brasileiro (força local)
        agora_naive = datetime.now()
        campos['created_at'] = agora_naive

        return campos

    def _inserir_registro_sql(self, cursor, id_fila_extrato: int, campos: Dict[str, Any]):
        """Insere novo registro usando SQL direto"""
        # Construir lista de campos e valores
        campos['idFilaExtrato'] = id_fila_extrato

        # Primeiro, verificar estrutura da tabela
        cursor.execute("DESCRIBE wallclub.baseTransacoesGestao")
        colunas_tabela = [row[0] for row in cursor.fetchall()]

        # Identificar campos faltando
        campos_faltando = set(colunas_tabela) - set(campos.keys()) - {'id'}  # Excluir id que é auto_increment

        # Adicionar campos faltando com valores apropriados (se houver)
        if campos_faltando:
            for campo_faltando in campos_faltando:
                # SÓ adicionar se o campo realmente não existe em campos
                if campo_faltando not in campos:
                    # Campos var*_A são geralmente decimais, usar 0.0
                    if campo_faltando.endswith('_A') or campo_faltando.endswith('_B'):
                        campos[campo_faltando] = 0.0
                    elif campo_faltando == 'updated_at':
                        # updated_at deve ser datetime atual na criação
                        from datetime import datetime
                        campos[campo_faltando] = datetime.now()
                    elif campo_faltando == 'tipo_operacao':
                        # NUNCA sobrescrever tipo_operacao - já foi definido antes
                        pass
                    else:
                        campos[campo_faltando] = ''

        # Filtrar apenas campos que existem na tabela
        campos_validos = {}
        for campo, valor in campos.items():
            if campo in colunas_tabela:
                campos_validos[campo] = valor

        # Ordenar campos para garantir consistência - SEMPRE usar a mesma ordem
        campos_ordenados = sorted(campos_validos.keys())

        # Montar valores_ordenados usando dict por nome
        valores_por_nome = {}
        for campo, valor in campos_validos.items():
            # Manter valores None como None para compatibilidade com PHP
            # Apenas converter None para valores padrão em campos que realmente precisam
            if valor is None and campo in ['banco', 'idFilaExtrato']:
                # Apenas campos obrigatórios que não podem ser None
                if campo == 'banco':
                    valor = 'PIN'
                elif campo == 'idFilaExtrato':
                    valor = 0

            valores_por_nome[campo] = valor

        # Montar valores_ordenados na MESMA ordem que campos_ordenados
        valores_ordenados = [valores_por_nome[campo] for campo in campos_ordenados]

        # Construir SQL de INSERT
        campos_sql = ', '.join(campos_ordenados)
        placeholders = ', '.join(['%s'] * len(campos_ordenados))

        sql = f"""
            INSERT INTO wallclub.baseTransacoesGestao ({campos_sql})
            VALUES ({placeholders})
        """

        # Converter datetime para string para evitar conversão de timezone
        valores_finais = []
        for i, valor in enumerate(valores_ordenados):
            if hasattr(valor, 'strftime'):  # É um datetime
                valores_finais.append(valor.strftime('%Y-%m-%d %H:%M:%S'))
            else:
                valores_finais.append(valor)

        # Executar INSERT completo
        cursor.execute(sql, valores_finais)

        # APÓS INSERIR: Remover registros duplicados com idFilaExtrato = null
        self._remover_duplicados_com_id_fila_null(cursor, campos)

    def _atualizar_registro_sql(self, cursor, registro_id: int, campos: Dict[str, Any]):
        """Atualiza registro existente usando SQL direto"""
        # Construir SET clause - EXCLUIR created_at do UPDATE
        set_clauses = []
        valores = []

        for campo, valor in campos.items():
            # NUNCA atualizar created_at - deve preservar valor original
            if campo == 'created_at':
                continue

            set_clauses.append(f"{campo} = %s")
            # Converter datetime para string para evitar conversão de timezone
            if hasattr(valor, 'strftime'):  # É um datetime
                valores.append(valor.strftime('%Y-%m-%d %H:%M:%S'))
            else:
                valores.append(valor)

        # Adicionar updated_at = NOW() para marcar quando foi atualizado
        set_clauses.append("updated_at = NOW()")

        sql = f"""
            UPDATE wallclub.baseTransacoesGestao
            SET {', '.join(set_clauses)}
            WHERE id = %s
        """
        valores.append(registro_id)

        cursor.execute(sql, valores)

    def _remover_duplicados_com_id_fila_null(self, cursor, campos: Dict[str, Any]):
        """Remove registros duplicados com idFilaExtrato = null para o mesmo var9"""
        try:
            # Obter var9 do registro recém inserido para identificar duplicados
            var9 = campos.get('var9')
            if not var9:
                return

            # Buscar registros com mesmo var9 mas idFilaExtrato = null
            sql_buscar_duplicados = """
                SELECT id, idFilaExtrato
                FROM wallclub.baseTransacoesGestao
                WHERE var9 = %s AND idFilaExtrato IS NULL
            """

            cursor.execute(sql_buscar_duplicados, [var9])
            duplicados = cursor.fetchall()

            if duplicados:
                ids_para_remover = [dup[0] for dup in duplicados]
                registrar_log('pinbank.cargas_pinbank', f"Encontrados {len(duplicados)} registros duplicados com idFilaExtrato=null para var9={var9}", nivel='INFO')

                # Remover registros duplicados
                sql_remover = """
                    DELETE FROM wallclub.baseTransacoesGestao
                    WHERE id IN ({})
                """.format(','.join(['%s'] * len(ids_para_remover)))

                cursor.execute(sql_remover, ids_para_remover)
                registrar_log('pinbank.cargas_pinbank', f"Removidos {cursor.rowcount} registros duplicados com idFilaExtrato=null para var9={var9}", nivel='INFO')

        except Exception as e:
            registrar_log('pinbank.cargas_pinbank', f"Erro ao remover duplicados com idFilaExtrato=null: {str(e)}", nivel='ERROR')
