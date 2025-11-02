"""
Serviços do Sistema Bancário
Camada de negócio para operações financeiras e pagamentos
"""

from django.db import transaction
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import datetime
from wallclub_core.utilitarios.log_control import registrar_log
from .models import PagamentoEfetuado


class PagamentoService:
    """
    Serviço para gerenciamento de pagamentos efetuados.
    Centraliza todas as operações bancárias relacionadas a pagamentos.
    """
    
    @staticmethod
    def buscar_pagamentos(filtros=None):
        """
        Busca pagamentos com filtros opcionais.
        
        Args:
            filtros (dict): Filtros de busca (nsu, data_inicio, data_fim)
            
        Returns:
            QuerySet: Pagamentos filtrados
        """
        queryset = PagamentoEfetuado.objects.all()
        
        if not filtros:
            return queryset.none()  # Por padrão não retorna nada
        
        # Verificar se há pelo menos um filtro válido
        tem_filtro_valido = False
        
        if filtros.get('nsu'):
            try:
                nsu_int = int(filtros['nsu'])
                queryset = queryset.filter(nsu=nsu_int)
                tem_filtro_valido = True
            except ValueError:
                return queryset.none()
        
        # Filtros de data precisam processar em Python porque var45 está em formato DD/MM/YYYY
        if filtros.get('data_inicio') or filtros.get('data_fim'):
            try:
                data_inicio_obj = None
                data_fim_obj = None
                
                if filtros.get('data_inicio'):
                    data_inicio_obj = datetime.strptime(filtros['data_inicio'], '%Y-%m-%d').date()
                    tem_filtro_valido = True
                
                if filtros.get('data_fim'):
                    data_fim_obj = datetime.strptime(filtros['data_fim'], '%Y-%m-%d').date()
                    tem_filtro_valido = True
                
                # Buscar todos com var45 preenchido e filtrar em Python
                pagamentos_temp = queryset.filter(var45__isnull=False).exclude(var45='')
                ids_validos = []
                
                for pag in pagamentos_temp:
                    try:
                        # Converter var45 de DD/MM/YYYY para date
                        data_pag = datetime.strptime(pag.var45, '%d/%m/%Y').date()
                        
                        # Aplicar filtros
                        if data_inicio_obj and data_pag < data_inicio_obj:
                            continue
                        if data_fim_obj and data_pag > data_fim_obj:
                            continue
                        
                        ids_validos.append(pag.id)
                    except ValueError:
                        # Ignorar registros com data inválida
                        continue
                
                queryset = queryset.filter(id__in=ids_validos)
            except ValueError:
                pass
        
        # Se não há filtros válidos, retorna vazio
        if not tem_filtro_valido:
            return queryset.none()
        
        # Debug: adicionar logs para verificar filtros
        print(f"DEBUG PagamentoService: filtros={filtros}")
        print(f"DEBUG PagamentoService: tem_filtro_valido={tem_filtro_valido}")
        
        # Verificar se existem registros na tabela
        total_registros = PagamentoEfetuado.objects.count()
        print(f"DEBUG PagamentoService: total registros na tabela={total_registros}")
        
        # Contar registros após filtros
        resultado_count = queryset.count()
        print(f"DEBUG PagamentoService: registros após filtros={resultado_count}")
        
        # Se há filtros de data, mostrar alguns registros para debug
        if filtros.get('data_inicio') or filtros.get('data_fim'):
            sample_dates = PagamentoEfetuado.objects.values_list('created_at', flat=True)[:5]
            print(f"DEBUG PagamentoService: sample dates na tabela={list(sample_dates)}")
        
        return queryset.order_by('-created_at')
    
    @staticmethod
    def criar_pagamento(dados_pagamento, usuario):
        """
        Cria novo pagamento com validações bancárias.
        
        Args:
            dados_pagamento (dict): Dados do pagamento
            usuario: Usuário responsável pela operação
            
        Returns:
            PagamentoEfetuado: Pagamento criado
            
        Raises:
            ValidationError: Se dados inválidos
            ValueError: Se NSU já existe
        """
        with transaction.atomic():
            # Validar NSU obrigatório
            nsu = dados_pagamento.get('nsu')
            if not nsu:
                raise ValidationError('NSU é obrigatório')
            
            try:
                nsu_int = int(nsu)
            except (ValueError, TypeError):
                raise ValidationError('NSU deve ser um número válido')
            
            # Verificar se NSU já existe
            if PagamentoEfetuado.objects.filter(nsu=nsu_int).exists():
                raise ValueError(f'Já existe um pagamento com NSU {nsu_int}')
            
            # Validar campos monetários
            campos_monetarios = ['var44', 'var58', 'var111', 'var112']
            dados_validados = {'nsu': nsu_int, 'user': usuario}
            
            for campo in campos_monetarios:
                valor = dados_pagamento.get(campo)
                if valor:
                    try:
                        if isinstance(valor, str):
                            valor = valor.replace(',', '.')
                        dados_validados[campo] = Decimal(str(valor))
                    except (ValueError, TypeError):
                        dados_validados[campo] = None
                else:
                    dados_validados[campo] = None
            
            # Validar campos de texto
            campos_texto = ['var45', 'var59', 'var66', 'var71', 'var100']
            for campo in campos_texto:
                valor = dados_pagamento.get(campo, '').strip()
                dados_validados[campo] = valor if valor else None
            
            # Criar pagamento
            pagamento = PagamentoEfetuado.objects.create(**dados_validados)
            
            # Log de auditoria bancária
            registrar_log(
                'sistema_bancario.pagamentos',
                f'Pagamento criado - NSU: {nsu_int} - Usuário: {usuario.nome} - '
                f'Valores: var44={dados_validados.get("var44")}, var58={dados_validados.get("var58")}, '
                f'var111={dados_validados.get("var111")}, var112={dados_validados.get("var112")}'
            )
            
            return pagamento
    
    @staticmethod
    def atualizar_pagamento(pagamento_id, dados_atualizacao, usuario):
        """
        Atualiza pagamento existente com validações bancárias.
        
        Args:
            pagamento_id (int): ID do pagamento
            dados_atualizacao (dict): Dados para atualização
            usuario: Usuário responsável pela operação
            
        Returns:
            PagamentoEfetuado: Pagamento atualizado
            
        Raises:
            PagamentoEfetuado.DoesNotExist: Se pagamento não existe
            ValidationError: Se dados inválidos
        """
        with transaction.atomic():
            pagamento = PagamentoEfetuado.objects.get(id=pagamento_id)
            valores_anteriores = {
                'var44': pagamento.var44,
                'var58': pagamento.var58,
                'var111': pagamento.var111,
                'var112': pagamento.var112
            }
            
            # Validar e atualizar campos monetários
            campos_monetarios = ['var44', 'var58', 'var111', 'var112']
            for campo in campos_monetarios:
                if campo in dados_atualizacao:
                    valor = dados_atualizacao[campo]
                    if valor:
                        try:
                            if isinstance(valor, str):
                                valor = valor.replace(',', '.')
                            setattr(pagamento, campo, Decimal(str(valor)))
                        except (ValueError, TypeError):
                            setattr(pagamento, campo, None)
                    else:
                        setattr(pagamento, campo, None)
            
            # Validar e atualizar campos de texto
            campos_texto = ['var45', 'var59', 'var66', 'var71', 'var100']
            for campo in campos_texto:
                if campo in dados_atualizacao:
                    valor = dados_atualizacao[campo]
                    if isinstance(valor, str):
                        valor = valor.strip()
                    setattr(pagamento, campo, valor if valor else None)
            
            pagamento.save()
            
            # Log de auditoria bancária
            valores_novos = {
                'var44': pagamento.var44,
                'var58': pagamento.var58,
                'var111': pagamento.var111,
                'var112': pagamento.var112
            }
            
            registrar_log(
                'sistema_bancario.pagamentos',
                f'Pagamento atualizado - NSU: {pagamento.nsu} - Usuário: {usuario.nome} - '
                f'Valores anteriores: {valores_anteriores} - Valores novos: {valores_novos}'
            )
            
            return pagamento
    
    @staticmethod
    def excluir_pagamento(pagamento_id, usuario):
        """
        Exclui pagamento com log de auditoria.
        
        Args:
            pagamento_id (int): ID do pagamento
            usuario: Usuário responsável pela operação
            
        Returns:
            dict: Informações do pagamento excluído
            
        Raises:
            PagamentoEfetuado.DoesNotExist: Se pagamento não existe
        """
        with transaction.atomic():
            pagamento = PagamentoEfetuado.objects.get(id=pagamento_id)
            
            # Salvar informações para log
            info_pagamento = {
                'nsu': pagamento.nsu,
                'var44': pagamento.var44,
                'var58': pagamento.var58,
                'var111': pagamento.var111,
                'var112': pagamento.var112,
                'created_at': pagamento.created_at
            }
            
            # Excluir pagamento
            pagamento.delete()
            
            # Log de auditoria bancária
            registrar_log(
                'sistema_bancario.pagamentos',
                f'Pagamento excluído - NSU: {info_pagamento["nsu"]} - Usuário: {usuario.nome} - '
                f'Valores: var44={info_pagamento["var44"]}, var58={info_pagamento["var58"]}, '
                f'var111={info_pagamento["var111"]}, var112={info_pagamento["var112"]} - '
                f'Criado em: {info_pagamento["created_at"]}'
            )
            
            return info_pagamento
    
    @staticmethod
    def verificar_nsu_existe(nsu):
        """
        Verifica se NSU já existe no sistema.
        
        Args:
            nsu (str/int): NSU para verificar
            
        Returns:
            bool: True se NSU existe, False caso contrário
        """
        try:
            nsu_int = int(nsu)
            return PagamentoEfetuado.objects.filter(nsu=nsu_int).exists()
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def obter_pagamento(pagamento_id):
        """
        Obtém pagamento por ID.
        
        Args:
            pagamento_id (int): ID do pagamento
            
        Returns:
            PagamentoEfetuado: Pagamento encontrado
            
        Raises:
            PagamentoEfetuado.DoesNotExist: Se pagamento não existe
        """
        return PagamentoEfetuado.objects.get(id=pagamento_id)
    
    @staticmethod
    def listar_recebimentos(filtros=None):
        """
        Lista recebimentos com filtros avançados para relatórios.
        
        Args:
            filtros (dict): Filtros de busca (lojas, data_inicio, data_fim, tipo)
            
        Returns:
            QuerySet: Recebimentos filtrados com agregações
        """
        from wallclub_core.database.queries import TransacoesQueries
        from django.db.models import Q, Sum
        
        queryset = BaseTransacoesGestao.objects.all()
        
        if not filtros:
            return queryset.none()
        
        # Filtro base: apenas transações com data de recebimento
        filtros_q = Q(var45__isnull=False) & ~Q(var45='')
        
        # Filtro por lojas
        if filtros.get('lojas'):
            lojas_ids = filtros['lojas']
            if isinstance(lojas_ids, (list, tuple)):
                filtros_q &= Q(var6__in=lojas_ids)
            else:
                filtros_q &= Q(var6=lojas_ids)
        
        # Filtro por NSU
        if filtros.get('nsu'):
            filtros_q &= Q(var9__icontains=filtros['nsu'])
        
        queryset = queryset.filter(filtros_q)
        
        registrar_log(
            'sistema_bancario.recebimentos',
            f'Listando recebimentos - Filtros: {filtros} - Total: {queryset.count()}'
        )
        
        return queryset.order_by('-data_transacao')
    
    @staticmethod
    def obter_relatorio_financeiro(lojas_ids, data_inicio=None, data_fim=None):
        """
        Gera relatório financeiro agregado de recebimentos.
        
        Args:
            lojas_ids (list): IDs das lojas
            data_inicio (str): Data início formato YYYY-MM-DD
            data_fim (str): Data fim formato YYYY-MM-DD
            
        Returns:
            dict: Dados agregados do relatório
        """
        from wallclub_core.database.queries import TransacoesQueries
        from django.db.models import Sum, Count, Q, Avg
        from decimal import Decimal
        
        # Construir filtros
        filtros = Q(var6__in=lojas_ids) & Q(var45__isnull=False) & ~Q(var45='')
        
        # Processar datas
        if data_inicio or data_fim:
            transacoes = BaseTransacoesGestao.objects.filter(filtros)
            recebimentos_filtrados = []
            
            for t in transacoes:
                if not t.var45:
                    continue
                    
                try:
                    # Tentar vários formatos de data
                    data_recebimento = None
                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%Y%m%d']:
                        try:
                            data_recebimento = datetime.strptime(t.var45, fmt).date()
                            break
                        except ValueError:
                            continue
                    
                    if not data_recebimento:
                        continue
                    
                    # Aplicar filtros de data
                    if data_inicio:
                        data_ini_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
                        if data_recebimento < data_ini_obj:
                            continue
                    
                    if data_fim:
                        data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d').date()
                        if data_recebimento > data_fim_obj:
                            continue
                    
                    recebimentos_filtrados.append(t)
                    
                except Exception:
                    continue
            
            transacoes_queryset = recebimentos_filtrados
        else:
            transacoes_queryset = BaseTransacoesGestao.objects.filter(filtros)
        
        # Calcular agregações
        total_transacoes = len(transacoes_queryset) if isinstance(transacoes_queryset, list) else transacoes_queryset.count()
        
        valor_total = Decimal('0.00')
        for t in transacoes_queryset:
            if hasattr(t, 'var111') and t.var111:
                valor_total += Decimal(str(t.var111))
        
        valor_medio = valor_total / total_transacoes if total_transacoes > 0 else Decimal('0.00')
        
        resultado = {
            'total_transacoes': total_transacoes,
            'valor_total': valor_total,
            'valor_medio': valor_medio,
            'lojas_count': len(set(t.var6 for t in transacoes_queryset if hasattr(t, 'var6')))
        }
        
        registrar_log(
            'sistema_bancario.relatorios',
            f'Relatório financeiro gerado - Lojas: {len(lojas_ids)} - '
            f'Transações: {total_transacoes} - Total: R$ {valor_total}'
        )
        
        return resultado
    
    @staticmethod
    def processar_lote_pagamentos(pagamentos_dados, usuario):
        """
        Processa lote de pagamentos em transação atômica.
        
        Args:
            pagamentos_dados (list): Lista de dicts com dados dos pagamentos
            usuario: Usuário responsável pela operação
            
        Returns:
            dict: Resultado do processamento (criados, erros)
        """
        criados = []
        erros = []
        
        with transaction.atomic():
            for i, dados in enumerate(pagamentos_dados, 1):
                try:
                    # Validar NSU
                    nsu = dados.get('nsu')
                    if not nsu:
                        erros.append(f'Linha {i}: NSU obrigatório')
                        continue
                    
                    # Verificar duplicata
                    if PagamentoService.verificar_nsu_existe(nsu):
                        erros.append(f'Linha {i}: NSU {nsu} já existe')
                        continue
                    
                    # Criar pagamento
                    pagamento = PagamentoService.criar_pagamento(dados, usuario)
                    criados.append(pagamento)
                    
                except ValidationError as e:
                    erros.append(f'Linha {i}: {str(e)}')
                except ValueError as e:
                    erros.append(f'Linha {i}: {str(e)}')
                except Exception as e:
                    erros.append(f'Linha {i}: Erro inesperado - {str(e)}')
        
        registrar_log(
            'sistema_bancario.pagamentos',
            f'Lote processado - Criados: {len(criados)} - Erros: {len(erros)} - Usuário: {usuario.nome}',
            nivel='INFO' if not erros else 'WARNING'
        )
        
        return {
            'criados': criados,
            'erros': erros,
            'total_criados': len(criados),
            'total_erros': len(erros)
        }
    
    @staticmethod
    def conciliar_pagamentos(nsu_list):
        """
        Realiza conciliação de pagamentos por lista de NSUs.
        
        Args:
            nsu_list (list): Lista de NSUs para conciliar
            
        Returns:
            dict: Resultado da conciliação (encontrados, não encontrados)
        """
        encontrados = []
        nao_encontrados = []
        
        for nsu in nsu_list:
            try:
                nsu_int = int(nsu)
                pagamento = PagamentoEfetuado.objects.filter(nsu=nsu_int).first()
                
                if pagamento:
                    encontrados.append({
                        'nsu': nsu_int,
                        'id': pagamento.id,
                        'var44': pagamento.var44,
                        'var111': pagamento.var111,
                        'created_at': pagamento.created_at
                    })
                else:
                    nao_encontrados.append(nsu_int)
                    
            except (ValueError, TypeError):
                nao_encontrados.append(nsu)
        
        registrar_log(
            'sistema_bancario.conciliacao',
            f'Conciliação realizada - Encontrados: {len(encontrados)} - '
            f'Não encontrados: {len(nao_encontrados)}'
        )
        
        return {
            'encontrados': encontrados,
            'nao_encontrados': nao_encontrados,
            'total_encontrados': len(encontrados),
            'total_nao_encontrados': len(nao_encontrados)
        }
