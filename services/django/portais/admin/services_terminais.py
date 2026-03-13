"""
Service para gestão de terminais POS
Centraliza toda lógica de negócio relacionada a terminais
"""
from typing import Dict, List, Any, Optional
from datetime import date, datetime
from django.db import connection
from django.apps import apps
from wallclub_core.utilitarios.log_control import registrar_log

# Modelos de POS aceitos pela Own Financial
MODELOS_POS_OWN = [
    'POS GPOS 700X',
]


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
                c.nome as canal_nome,
                tow.numero_contrato as own_contrato
            FROM terminais t
            LEFT JOIN loja l ON t.loja_id = l.id
            LEFT JOIN canal c ON l.canal_id = c.id
            LEFT JOIN terminais_own tow ON tow.terminal_id = t.id AND tow.ativo = 1
            WHERE (t.fim IS NULL OR t.fim > NOW()) {canal_filter}
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
            'canal_nome': t[9],
            'own_contrato': t[10]
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
                # Terminal está ativo se: fim IS NULL OU fim > agora
                cursor.execute("""
                    SELECT id, loja_id 
                    FROM terminais 
                    WHERE terminal = %s 
                      AND (fim IS NULL OR fim > NOW())
                """, [terminal])
                
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
                terminal_obj.inicio = datetime.combine(inicio, datetime.min.time())
            if fim:
                terminal_obj.fim = datetime.combine(fim, datetime.min.time())
            
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
                terminal_obj.inicio = datetime.combine(inicio, datetime.min.time())
            
            # Validar e atualizar data de fim
            if limpar_fim:
                terminal_obj.fim = None
            elif fim:
                if terminal_obj.fim_date and terminal_obj.fim_date <= hoje:
                    return {
                        'sucesso': False,
                        'mensagem': 'Data de fim só pode ser modificada se for nula ou futura'
                    }
                terminal_obj.fim = datetime.combine(fim, datetime.min.time())
            
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
            # Definir data/hora de fim para agora
            terminal_obj.fim = datetime.now()
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

    @staticmethod
    def obter_lojas_own_para_select() -> List[Dict[str, Any]]:
        """
        Obtém lojas cadastradas na Own com contrato aprovado para dropdown.

        Returns:
            Lista de dicts com loja_id, razao_social e contrato
        """
        query = """
            SELECT lo.loja_id, l.razao_social, lo.contrato
            FROM loja_own lo
            INNER JOIN loja l ON lo.loja_id = l.id
            WHERE lo.contrato IS NOT NULL
              AND lo.contrato != ''
              AND lo.status_credenciamento = 'APROVADO'
            ORDER BY l.razao_social
        """

        with connection.cursor() as cursor:
            cursor.execute(query)
            lojas = cursor.fetchall()

        return [{
            'loja_id': l[0],
            'razao_social': l[1],
            'contrato': l[2]
        } for l in lojas]

    @staticmethod
    def configurar_equipamento_own(
        terminal_id: int,
        numero_serie: str,
        modelo: str,
        numero_contrato: str,
        usuario: str = "N/A"
    ) -> Dict[str, Any]:
        """
        Cadastra equipamento POS na Own Financial via API configuraEquipamento
        e salva o vínculo na tabela terminal_own.

        Args:
            terminal_id: ID do terminal na tabela terminais
            numero_serie: Número de série do POS
            modelo: Modelo do equipamento (ex: POS PAX D195)
            numero_contrato: Número do contrato do estabelecimento na Own
            usuario: Nome do usuário que está realizando a operação
        """
        try:
            from adquirente_own.services import OwnService
            from adquirente_own.models_cadastro import TerminalOwn

            own_service = OwnService()
            credenciais = own_service.obter_credenciais_white_label()

            if not credenciais:
                return {
                    'sucesso': False,
                    'mensagem': 'Credenciais Own não encontradas'
                }

            payload = {
                "terminais": [{
                    "numeroSerie": numero_serie,
                    "modelo": modelo,
                    "numeroSerieAntigo": ""
                }],
                "numeroContrato": numero_contrato
            }

            registrar_log(
                'portais.admin',
                f'TERMINAIS OWN - Configurando equipamento: serie={numero_serie}, modelo={modelo}, contrato={numero_contrato} - Por: {usuario}'
            )

            resultado = own_service.fazer_requisicao_autenticada(
                method='POST',
                endpoint='/parceiro/configuraEquipamento',
                client_id=credenciais['client_id'],
                client_secret=credenciais['client_secret'],
                scope=credenciais['scope'],
                data=payload
            )

            if resultado.get('sucesso'):
                # Salvar vínculo na tabela terminal_own
                terminal_own, created = TerminalOwn.objects.update_or_create(
                    terminal_id=terminal_id,
                    defaults={
                        'numero_contrato': numero_contrato,
                        'modelo': modelo,
                        'numero_serie': numero_serie,
                        'ativo': True,
                    }
                )

                registrar_log(
                    'portais.admin',
                    f'TERMINAIS OWN - Equipamento configurado com sucesso: serie={numero_serie}, contrato={numero_contrato} - Por: {usuario}'
                )
                return {
                    'sucesso': True,
                    'mensagem': 'Equipamento configurado na Own com sucesso'
                }
            else:
                mensagem = resultado.get('mensagem', 'Erro desconhecido')
                registrar_log(
                    'portais.admin',
                    f'TERMINAIS OWN - Erro ao configurar equipamento: {mensagem} - Por: {usuario}',
                    nivel='ERROR'
                )
                return {
                    'sucesso': False,
                    'mensagem': f'Erro ao configurar na Own: {mensagem}'
                }

        except Exception as e:
            registrar_log(
                'portais.admin',
                f'TERMINAIS OWN - Exceção ao configurar equipamento: {str(e)} - Por: {usuario}',
                nivel='ERROR'
            )
            return {
                'sucesso': False,
                'mensagem': f'Erro ao configurar na Own: {str(e)}'
            }

    @staticmethod
    def desativar_equipamento_own(
        terminal_id: int,
        usuario: str = "N/A"
    ) -> Dict[str, Any]:
        """
        Desativa equipamento POS na Own Financial via API configuraEquipamento.
        Busca dados do vínculo na tabela terminal_own.

        Args:
            terminal_id: ID do terminal na tabela terminais
            usuario: Nome do usuário que está realizando a operação
        """
        try:
            from adquirente_own.services import OwnService
            from adquirente_own.models_cadastro import TerminalOwn

            # Buscar vínculo ativo
            terminal_own = TerminalOwn.objects.filter(
                terminal_id=terminal_id, ativo=True
            ).first()

            if not terminal_own:
                return {
                    'sucesso': True,
                    'mensagem': 'Terminal não possui vínculo ativo com a Own'
                }

            own_service = OwnService()
            credenciais = own_service.obter_credenciais_white_label()

            if not credenciais:
                return {
                    'sucesso': False,
                    'mensagem': 'Credenciais Own não encontradas'
                }

            payload = {
                "terminais": [{
                    "numeroSerieAntigo": terminal_own.numero_serie
                }],
                "numeroContrato": terminal_own.numero_contrato
            }

            registrar_log(
                'portais.admin',
                f'TERMINAIS OWN - Desativando equipamento: serie={terminal_own.numero_serie}, contrato={terminal_own.numero_contrato} - Por: {usuario}'
            )

            resultado = own_service.fazer_requisicao_autenticada(
                method='POST',
                endpoint='/parceiro/configuraEquipamento',
                client_id=credenciais['client_id'],
                client_secret=credenciais['client_secret'],
                scope=credenciais['scope'],
                data=payload
            )

            if resultado.get('sucesso'):
                terminal_own.ativo = False
                terminal_own.save()

                registrar_log(
                    'portais.admin',
                    f'TERMINAIS OWN - Equipamento desativado com sucesso: serie={terminal_own.numero_serie}, contrato={terminal_own.numero_contrato} - Por: {usuario}'
                )
                return {
                    'sucesso': True,
                    'mensagem': 'Equipamento desativado na Own com sucesso'
                }
            else:
                mensagem = resultado.get('mensagem', 'Erro desconhecido')
                registrar_log(
                    'portais.admin',
                    f'TERMINAIS OWN - Erro ao desativar equipamento: {mensagem} - Por: {usuario}',
                    nivel='ERROR'
                )
                return {
                    'sucesso': False,
                    'mensagem': f'Erro ao desativar na Own: {mensagem}'
                }

        except Exception as e:
            registrar_log(
                'portais.admin',
                f'TERMINAIS OWN - Exceção ao desativar equipamento: {str(e)} - Por: {usuario}',
                nivel='ERROR'
            )
            return {
                'sucesso': False,
                'mensagem': f'Erro ao desativar na Own: {str(e)}'
            }
