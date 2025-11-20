from django.db import transaction
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from .models import LancamentoManual
from wallclub_core.utilitarios.log_control import registrar_log


class LancamentoManualService:
    """
    Service para operações com lançamentos manuais
    Mantém histórico completo de todas as operações
    """
    
    @staticmethod
    def criar_lancamento(dados, id_usuario):
        """
        Cria um novo lançamento manual
        
        Args:
            dados (dict): Dados do lançamento
            id_usuario (int): ID do usuário que está criando
            
        Returns:
            LancamentoManual: Instância criada
        """
        try:
            with transaction.atomic():
                # Validações básicas
                if not dados.get('loja_id'):
                    raise ValidationError("Loja ID é obrigatório")
                    
                if not dados.get('tipo_lancamento') or dados['tipo_lancamento'] not in ['C', 'D']:
                    raise ValidationError("Tipo de lançamento deve ser 'C' ou 'D'")
                    
                if not dados.get('valor') or Decimal(str(dados['valor'])) <= 0:
                    raise ValidationError("Valor deve ser maior que zero")
                    
                if not dados.get('descricao'):
                    raise ValidationError("Descrição é obrigatória")
                    
                # Criar lançamento
                lancamento = LancamentoManual.objects.create(
                    id_usuario=id_usuario,
                    loja_id=dados['loja_id'],
                    tipo_lancamento=dados['tipo_lancamento'],
                    descricao=dados['descricao'],
                    data_lancamento=dados.get('data_lancamento', datetime.now()),
                    valor=dados['valor'],
                    motivo=dados.get('motivo', ''),
                    status=dados.get('status', 'pendente'),  # Aceitar status do formulário
                    observacoes=dados.get('observacoes', ''),
                    referencia_externa=dados.get('referencia_externa', '')
                )
                
                registrar_log(
                    'sistema_bancario.lancamento_manual',
                    f"Lançamento manual criado - ID: {lancamento.id}, Loja: {lancamento.loja_id}, "
                    f"Tipo: {lancamento.tipo_lancamento}, Valor: R$ {lancamento.valor}, "
                    f"Usuário: {id_usuario}"
                )
                
                return lancamento
                
        except Exception as e:
            registrar_log(
                'sistema_bancario.lancamento_manual',
                f"Erro ao criar lançamento manual - Usuário: {id_usuario}, Erro: {str(e)}"
            )
            raise
    
    @staticmethod
    def buscar_lancamentos(filtros=None):
        """
        Busca lançamentos manuais com filtros
        
        Args:
            filtros (dict): Filtros de busca
            
        Returns:
            QuerySet: Lançamentos encontrados
        """
        queryset = LancamentoManual.objects.all()
        
        if not filtros:
            return queryset
            
        if filtros.get('loja_id'):
            queryset = queryset.filter(loja_id=filtros['loja_id'])
            
        if filtros.get('tipo_lancamento'):
            queryset = queryset.filter(tipo_lancamento=filtros['tipo_lancamento'])
            
        if filtros.get('status'):
            queryset = queryset.filter(status=filtros['status'])
            
        if filtros.get('data_inicio'):
            from datetime import datetime
            if isinstance(filtros['data_inicio'], str):
                data_inicio = datetime.strptime(filtros['data_inicio'], '%Y-%m-%d').replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                data_inicio = filtros['data_inicio']
            queryset = queryset.filter(data_lancamento__gte=data_inicio)
            
        if filtros.get('data_fim'):
            from datetime import datetime
            if isinstance(filtros['data_fim'], str):
                data_fim = datetime.strptime(filtros['data_fim'], '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=999999)
            else:
                data_fim = filtros['data_fim']
            queryset = queryset.filter(data_lancamento__lte=data_fim)
            
        if filtros.get('motivo'):
            queryset = queryset.filter(motivo__icontains=filtros['motivo'])
            
        if filtros.get('referencia_externa'):
            queryset = queryset.filter(referencia_externa__icontains=filtros['referencia_externa'])
            
        if filtros.get('nsu'):
            queryset = queryset.filter(referencia_externa__icontains=filtros['nsu'])
            
        return queryset.order_by('-created_at')
    
    @staticmethod
    def atualizar_lancamento(lancamento_id, dados, id_usuario):
        """
        Atualiza um lançamento manual existente
        
        Args:
            lancamento_id (int): ID do lançamento
            dados (dict): Novos dados
            id_usuario (int): ID do usuário que está atualizando
            
        Returns:
            LancamentoManual: Instância atualizada
        """
        try:
            with transaction.atomic():
                lancamento = LancamentoManual.objects.get(id=lancamento_id)
                
                # Salvar valores antigos para log
                valores_antigos = {
                    'tipo_lancamento': lancamento.tipo_lancamento,
                    'valor': lancamento.valor,
                    'status': lancamento.status,
                    'descricao': lancamento.descricao
                }
                
                # Atualizar campos permitidos
                campos_permitidos = [
                    'tipo_lancamento', 'descricao', 'data_lancamento', 
                    'valor', 'motivo', 'status', 'observacoes', 'referencia_externa'
                ]
                
                for campo in campos_permitidos:
                    if campo in dados:
                        setattr(lancamento, campo, dados[campo])
                
                lancamento.save()
                
                registrar_log(
                    'sistema_bancario.lancamento_manual',
                    f"Lançamento manual atualizado - ID: {lancamento.id}, "
                    f"Valores antigos: {valores_antigos}, "
                    f"Usuário: {id_usuario}"
                )
                
                return lancamento
                
        except LancamentoManual.DoesNotExist:
            raise ValidationError("Lançamento não encontrado")
        except Exception as e:
            registrar_log(
                'sistema_bancario.lancamento_manual',
                f"Erro ao atualizar lançamento manual - ID: {lancamento_id}, "
                f"Usuário: {id_usuario}, Erro: {str(e)}"
            )
            raise
    
    @staticmethod
    def cancelar_lancamento(lancamento_id, id_usuario, motivo_cancelamento=None):
        """
        Cancela um lançamento manual
        
        Args:
            lancamento_id (int): ID do lançamento
            id_usuario (int): ID do usuário que está cancelando
            motivo_cancelamento (str): Motivo do cancelamento
            
        Returns:
            LancamentoManual: Instância cancelada
        """
        try:
            with transaction.atomic():
                lancamento = LancamentoManual.objects.get(id=lancamento_id)
                
                if lancamento.status == 'cancelado':
                    raise ValidationError("Lançamento já está cancelado")
                    
                status_anterior = lancamento.status
                lancamento.status = 'cancelado'
                
                if motivo_cancelamento:
                    observacoes_atual = lancamento.observacoes or ""
                    lancamento.observacoes = f"{observacoes_atual}\n[CANCELAMENTO] {motivo_cancelamento}".strip()
                
                lancamento.save()
                
                registrar_log(
                    'sistema_bancario.lancamento_manual',
                    f"Lançamento manual cancelado - ID: {lancamento.id}, "
                    f"Status anterior: {status_anterior}, "
                    f"Motivo: {motivo_cancelamento}, "
                    f"Usuário: {id_usuario}"
                )
                
                return lancamento
                
        except LancamentoManual.DoesNotExist:
            raise ValidationError("Lançamento não encontrado")
        except Exception as e:
            registrar_log(
                'sistema_bancario.lancamento_manual',
                f"Erro ao cancelar lançamento manual - ID: {lancamento_id}, "
                f"Usuário: {id_usuario}, Erro: {str(e)}"
            )
            raise
    
    @staticmethod
    def processar_lancamento(lancamento_id, id_usuario):
        """
        Marca um lançamento como processado
        
        Args:
            lancamento_id (int): ID do lançamento
            id_usuario (int): ID do usuário que está processando
            
        Returns:
            LancamentoManual: Instância processada
        """
        try:
            with transaction.atomic():
                lancamento = LancamentoManual.objects.get(id=lancamento_id)
                
                if lancamento.status == 'processado':
                    raise ValidationError("Lançamento já está processado")
                    
                if lancamento.status == 'cancelado':
                    raise ValidationError("Não é possível processar lançamento cancelado")
                    
                status_anterior = lancamento.status
                lancamento.status = 'processado'
                lancamento.save()
                
                registrar_log(
                    'sistema_bancario.lancamento_manual',
                    f"Lançamento manual processado - ID: {lancamento.id}, "
                    f"Status anterior: {status_anterior}, "
                    f"Usuário: {id_usuario}"
                )
                
                return lancamento
                
        except LancamentoManual.DoesNotExist:
            raise ValidationError("Lançamento não encontrado")
        except Exception as e:
            registrar_log(
                'sistema_bancario.lancamento_manual',
                f"Erro ao processar lançamento manual - ID: {lancamento_id}, "
                f"Usuário: {id_usuario}, Erro: {str(e)}"
            )
            raise
    
    @staticmethod
    def obter_historico_loja(loja_id):
        """
        Obtém histórico completo de lançamentos de uma loja
        
        Args:
            loja_id (int): ID da loja
            
        Returns:
            QuerySet: Lançamentos da loja ordenados por data
        """
        return LancamentoManual.objects.filter(
            loja_id=loja_id
        ).order_by('-data_lancamento')
    
    @staticmethod
    def obter_estatisticas():
        """
        Obtém estatísticas dos lançamentos manuais
        
        Returns:
            dict: Estatísticas
        """
        from django.db.models import Count, Sum
        
        stats = LancamentoManual.objects.aggregate(
            total_lancamentos=Count('id'),
            total_creditos=Count('id', filter=models.Q(tipo_lancamento='C')),
            total_debitos=Count('id', filter=models.Q(tipo_lancamento='D')),
            valor_total_creditos=Sum('valor', filter=models.Q(tipo_lancamento='C')),
            valor_total_debitos=Sum('valor', filter=models.Q(tipo_lancamento='D')),
            pendentes=Count('id', filter=models.Q(status='pendente')),
            processados=Count('id', filter=models.Q(status='processado')),
            cancelados=Count('id', filter=models.Q(status='cancelado'))
        )
        
        return stats
