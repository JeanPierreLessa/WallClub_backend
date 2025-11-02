"""
Service para gestão de terminais POS
Centraliza toda lógica de negócio relacionada a terminais
"""
from typing import Dict, List, Any, Optional
from datetime import date, datetime
from django.db import connection
from django.apps import apps
from wallclub_core.utilitarios.log_control import registrar_log


class TerminaisService:
    """Service para gestão de terminais POS"""
    
    @staticmethod
    def listar_terminais(canais_usuario: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """
        Lista terminais ativos com informações de loja e canal
        
        Args:
            canais_usuario: Lista de IDs de canais que o usuário pode acessar (None = acesso total)
            
        Returns:
            Lista de dicionários com dados dos terminais
        """
        # Filtro por canal se necessário
        if canais_usuario:
            canal_filter = f"AND c.id IN ({','.join(map(str, canais_usuario))})"
        else:
            canal_filter = ""
        
        query = f"""
            SELECT 
                t.id,
                t.loja_id,
                t.terminal,
                t.idterminal,
                t.endereco,
                t.contato,
                t.inicio,
                t.fim,
                l.razao_social as loja_nome,
                c.nome as canal_nome
            FROM terminais t
            LEFT JOIN loja l ON t.loja_id = l.id
            LEFT JOIN canal c ON l.canal_id = c.id
            WHERE (t.fim IS NULL OR t.fim = 0 OR t.fim > UNIX_TIMESTAMP()) {canal_filter}
            ORDER BY t.id DESC
        """
        
        with connection.cursor() as cursor:
            cursor.execute(query)
            terminais = cursor.fetchall()
        
        return [{
            'id': t[0],
            'loja_id': t[1],
            'terminal': t[2],
            'idterminal': t[3],
            'endereco': t[4],
            'contato': t[5],
            'inicio': t[6],
            'fim': t[7],
            'loja_nome': t[8],
            'canal_nome': t[9]
        } for t in terminais]
    
    @staticmethod
    def criar_terminal(
        loja_id: int,
        terminal: str,
        idterminal: Optional[str] = None,
        endereco: Optional[str] = None,
        contato: Optional[str] = None,
        inicio: Optional[date] = None,
        fim: Optional[date] = None,
        usuario_criador: str = "N/A"
    ) -> Dict[str, Any]:
        """
        Cria novo terminal POS
        
        Args:
            loja_id: ID da loja
            terminal: Nome/código do terminal
            idterminal: ID externo do terminal
            endereco: Endereço do terminal
            contato: Contato responsável
            inicio: Data de início
            fim: Data de fim
            usuario_criador: Nome do usuário que está criando
            
        Returns:
            Dict com sucesso e mensagem ou terminal criado
        """
        try:
            # Validar dados obrigatórios
            if not loja_id or not terminal:
                return {
                    'sucesso': False,
                    'mensagem': 'Loja e Terminal são obrigatórios'
                }
            
            # Verificar se já existe terminal ativo com mesmo número de série
            from django.db import connection
            from datetime import datetime
            
            with connection.cursor() as cursor:
                # Terminal está ativo se: fim = 0 (null) OU fim > hoje
                cursor.execute("""
                    SELECT id, loja_id 
                    FROM terminais 
                    WHERE terminal = %s 
                      AND (fim = 0 OR fim > %s)
                """, [terminal, int(datetime.now().timestamp())])
                
                terminal_ativo = cursor.fetchone()
                
                if terminal_ativo:
                    return {
                        'sucesso': False,
                        'mensagem': f'Já existe um terminal ativo com o número de série "{terminal}" (ID: {terminal_ativo[0]}, Loja: {terminal_ativo[1]})'
                    }
            
            # Criar terminal (lazy import)
            Terminal = apps.get_model('posp2', 'Terminal')
            terminal_obj = Terminal(
                loja_id=loja_id,
                terminal=terminal,
                idterminal=idterminal or '',
                endereco=endereco or '',
                contato=contato or ''
            )
            
            # Definir datas se fornecidas
            if inicio:
                terminal_obj.set_inicio_date(inicio)
            if fim:
                terminal_obj.set_fim_date(fim)
            
            terminal_obj.save()
            
            registrar_log(
                'portais.admin',
                f'TERMINAIS - Criado - ID: {terminal_obj.id}, Loja: {loja_id}, Terminal: {terminal} - Por: {usuario_criador}'
            )
            
            return {
                'sucesso': True,
                'mensagem': 'Terminal criado com sucesso!',
                'terminal': terminal_obj
            }
            
        except Exception as e:
            registrar_log(
                'portais.admin',
                f'TERMINAIS - Erro ao criar - Loja: {loja_id}, Terminal: {terminal} - Erro: {str(e)} - Por: {usuario_criador}',
                nivel='ERROR'
            )
            return {
                'sucesso': False,
                'mensagem': f'Erro ao criar terminal: {str(e)}'
            }
    
    @staticmethod
    def atualizar_datas_terminal(
        terminal_id: int,
        inicio: Optional[date] = None,
        fim: Optional[date] = None,
        limpar_fim: bool = False,
        usuario_editor: str = "N/A"
    ) -> Dict[str, Any]:
        """
        Atualiza datas de início e fim de um terminal
        
        Args:
            terminal_id: ID do terminal
            inicio: Nova data de início (None = não alterar)
            fim: Nova data de fim (None = não alterar)
            limpar_fim: Se True, limpa a data de fim
            usuario_editor: Nome do usuário que está editando
            
        Returns:
            Dict com sucesso e mensagem
        """
        try:
            Terminal = apps.get_model('posp2', 'Terminal')
            terminal_obj = Terminal.objects.get(id=terminal_id)
            hoje = date.today()
            
            # Validar e atualizar data de início
            if inicio:
                if inicio <= hoje:
                    return {
                        'sucesso': False,
                        'mensagem': 'Data de início só pode ser modificada para datas futuras'
                    }
                terminal_obj.set_inicio_date(inicio)
            
            # Validar e atualizar data de fim
            if limpar_fim:
                terminal_obj.fim = None
            elif fim:
                if terminal_obj.fim_date and terminal_obj.fim_date <= hoje:
                    return {
                        'sucesso': False,
                        'mensagem': 'Data de fim só pode ser modificada se for nula ou futura'
                    }
                terminal_obj.set_fim_date(fim)
            
            terminal_obj.save()
            
            registrar_log(
                'portais.admin',
                f'TERMINAIS - Datas atualizadas - ID: {terminal_id} - Por: {usuario_editor}'
            )
            
            return {
                'sucesso': True,
                'mensagem': 'Datas do terminal atualizadas com sucesso!'
            }
            
        except Terminal.DoesNotExist:
            return {
                'sucesso': False,
                'mensagem': 'Terminal não encontrado'
            }
        except Exception as e:
            registrar_log(
                'portais.admin',
                f'TERMINAIS - Erro ao atualizar datas - ID: {terminal_id} - Erro: {str(e)} - Por: {usuario_editor}',
                nivel='ERROR'
            )
            return {
                'sucesso': False,
                'mensagem': f'Erro ao atualizar datas: {str(e)}'
            }
    
    @staticmethod
    def encerrar_terminal(
        terminal_id: int,
        usuario_editor: str = "N/A"
    ) -> Dict[str, Any]:
        """
        Encerra um terminal definindo a data de fim para hoje
        
        Args:
            terminal_id: ID do terminal
            usuario_editor: Nome do usuário que está encerrando
            
        Returns:
            Dict com sucesso e mensagem
        """
        try:
            Terminal = apps.get_model('posp2', 'Terminal')
            terminal_obj = Terminal.objects.get(id=terminal_id)
            # Usar timestamp atual (agora) em vez de date.today()
            terminal_obj.fim = int(datetime.now().timestamp())
            terminal_obj.save()
            
            registrar_log(
                'portais.admin',
                f'TERMINAIS - Encerrado - ID: {terminal_id} - Por: {usuario_editor}'
            )
            
            return {
                'sucesso': True,
                'mensagem': 'Terminal encerrado com sucesso!'
            }
            
        except Terminal.DoesNotExist:
            return {
                'sucesso': False,
                'mensagem': 'Terminal não encontrado'
            }
        except Exception as e:
            registrar_log(
                'portais.admin',
                f'TERMINAIS - Erro ao encerrar - ID: {terminal_id} - Erro: {str(e)} - Por: {usuario_editor}',
                nivel='ERROR'
            )
            return {
                'sucesso': False,
                'mensagem': f'Erro ao encerrar terminal: {str(e)}'
            }
    
    @staticmethod
    def remover_terminal(
        terminal_id: int,
        usuario_removedor: str = "N/A"
    ) -> Dict[str, Any]:
        """
        Remove um terminal
        
        Args:
            terminal_id: ID do terminal
            usuario_removedor: Nome do usuário que está removendo
            
        Returns:
            Dict com sucesso e mensagem
        """
        try:
            Terminal = apps.get_model('posp2', 'Terminal')
            terminal_obj = Terminal.objects.get(id=terminal_id)
            terminal_info = f"ID: {terminal_obj.id}, Loja: {terminal_obj.loja_id}, Terminal: {terminal_obj.terminal}"
            terminal_obj.delete()
            
            registrar_log(
                'portais.admin',
                f'TERMINAIS - Removido - {terminal_info} - Por: {usuario_removedor}'
            )
            
            return {
                'sucesso': True,
                'mensagem': 'Terminal removido com sucesso!'
            }
            
        except Terminal.DoesNotExist:
            return {
                'sucesso': False,
                'mensagem': 'Terminal não encontrado'
            }
        except Exception as e:
            registrar_log(
                'portais.admin',
                f'TERMINAIS - Erro ao remover - ID: {terminal_id} - Erro: {str(e)} - Por: {usuario_removedor}',
                nivel='ERROR'
            )
            return {
                'sucesso': False,
                'mensagem': f'Erro ao remover terminal: {str(e)}'
            }
    
    @staticmethod
    def obter_terminal(terminal_id: int) -> Optional[Any]:
        """
        Obtém um terminal pelo ID
        
        Args:
            terminal_id: ID do terminal
            
        Returns:
            Terminal ou None se não encontrado
        """
        try:
            Terminal = apps.get_model('posp2', 'Terminal')
            return Terminal.objects.get(id=terminal_id)
        except Terminal.DoesNotExist:
            return None
    
    @staticmethod
    def obter_lojas_para_select(canais_usuario: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """
        Obtém lista de lojas para select dropdown, filtradas por canal se necessário
        
        Args:
            canais_usuario: Lista de IDs de canais que o usuário pode acessar (None = acesso total)
            
        Returns:
            Lista de dicionários com id e razao_social das lojas
        """
        if canais_usuario:
            canal_filter = f"WHERE l.canal_id IN ({','.join(map(str, canais_usuario))})"
        else:
            canal_filter = ""
        
        query = f"""
            SELECT l.id, l.razao_social
            FROM loja l
            {canal_filter}
            ORDER BY l.razao_social
        """
        
        with connection.cursor() as cursor:
            cursor.execute(query)
            lojas = cursor.fetchall()
        
        return [{'id': l[0], 'razao_social': l[1]} for l in lojas]
