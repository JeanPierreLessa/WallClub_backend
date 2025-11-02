"""
Service para gerenciamento de notificações de clientes.
Contém toda a lógica de negócio relacionada às notificações.
"""
from .models import Cliente, Notificacao
from wallclub_core.utilitarios.log_control import registrar_log


class NotificacaoService:
    """Service para notificações de clientes"""

    @staticmethod
    def listar_notificacoes(cliente_id, limite=30):
        """
        Lista as notificações do cliente
        
        Args:
            cliente_id (int): ID do cliente autenticado
            limite (int): Quantidade máxima de notificações (default: 30)
            
        Returns:
            dict: {'sucesso': bool, 'mensagem': str, 'dados': {...}}
        """
        try:
            # Buscar cliente
            cliente = Cliente.objects.get(id=cliente_id)
            
            # Buscar notificações do cliente
            notificacoes_cliente = Notificacao.listar_notificacoes(
                cpf=cliente.cpf,
                canal_id=cliente.canal_id,
                limite=limite
            )
            
            # Converter para lista de dicionários
            lista_notificacoes = []
            for notificacao in notificacoes_cliente:
                lista_notificacoes.append({
                    "id": notificacao.id,
                    "titulo": notificacao.titulo,
                    "mensagem": notificacao.mensagem,
                    "tipo": notificacao.tipo,
                    "data": notificacao.data_envio.strftime('%Y-%m-%d %H:%M:%S'),
                    "lida": notificacao.lida,
                    "dados_adicionais": notificacao.dados_adicionais or {}
                })
            
            # Calcular quantidade de notificações não lidas para badge
            quantidade_nao_lidas = sum(1 for n in lista_notificacoes if not n["lida"])
            
            # Preparar mensagem
            mensagem = "Notificações encontradas" if lista_notificacoes else "Nenhuma notificação encontrada"
            
            registrar_log('apps.cliente', f"Notificações listadas - Cliente ID: {cliente_id}, Quantidade: {len(lista_notificacoes)}, Não lidas: {quantidade_nao_lidas}")
            
            return {
                "sucesso": True,
                "mensagem": mensagem,
                "dados": {
                    "notificacoes": lista_notificacoes,
                    "quantidade": len(lista_notificacoes),
                    "quantidade_nao_lidas": quantidade_nao_lidas
                }
            }
            
        except Cliente.DoesNotExist:
            registrar_log('apps.cliente', f"Cliente não encontrado: {cliente_id}", nivel='ERROR')
            return {
                "sucesso": False,
                "mensagem": "Cliente não encontrado",
                "dados": {
                    "notificacoes": [],
                    "quantidade": 0,
                    "quantidade_nao_lidas": 0
                }
            }
        except Exception as e:
            registrar_log('apps.cliente', f"Erro ao listar notificações: {str(e)}", nivel='ERROR')
            return {
                "sucesso": False,
                "mensagem": "Erro ao processar notificações",
                "dados": {
                    "notificacoes": [],
                    "quantidade": 0,
                    "quantidade_nao_lidas": 0
                }
            }
    
    @staticmethod
    def marcar_notificacoes_como_lidas(cliente_id, notificacao_ids):
        """
        Marca uma ou mais notificações como lidas
        
        Args:
            cliente_id (int): ID do cliente autenticado
            notificacao_ids (list ou int): ID(s) da(s) notificação(ões)
            
        Returns:
            dict: {'sucesso': bool, 'mensagem': str, 'quantidade_atualizada': int}
        """
        try:
            # Buscar cliente para validação
            cliente = Cliente.objects.get(id=cliente_id)
            
            # Marcar notificações como lidas usando método do model
            resultado = Notificacao.marcar_como_lida(
                notificacao_ids=notificacao_ids,
                cpf=cliente.cpf,
                canal_id=cliente.canal_id
            )
            
            quantidade = resultado['quantidade_atualizada']
            
            # Preparar mensagem
            if quantidade > 0:
                mensagem = f"{quantidade} notificação" if quantidade == 1 else f"{quantidade} notificações"
                mensagem += " marcadas como lidas" if quantidade > 1 else " marcada como lida"
            else:
                mensagem = "Nenhuma notificação foi atualizada (já estavam lidas ou IDs inválidos)"
            
            registrar_log('apps.cliente', f"Notificações marcadas como lidas - Cliente ID: {cliente_id}, CPF: {cliente.cpf}, Quantidade: {quantidade}")
            
            return {
                'sucesso': True,
                'mensagem': mensagem,
                'quantidade_atualizada': quantidade
            }
            
        except Cliente.DoesNotExist:
            registrar_log('apps.cliente', f"Cliente não encontrado: {cliente_id}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Cliente não encontrado',
                'quantidade_atualizada': 0
            }
        except Exception as e:
            registrar_log('apps.cliente', f"Erro ao marcar notificações como lidas: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Erro ao processar notificações',
                'quantidade_atualizada': 0
            }
