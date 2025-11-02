"""
Filtros baseados em vínculos de acesso para controle de dados
Implementa lógica de filtragem conforme permissões do usuário
"""
from typing import List, Optional, Dict, Any
from django.db import connection
from .models import PortalUsuario, PortalPermissao, PortalUsuarioAcesso
from .services import ControleAcessoService


class FiltrosAcessoService:
    """
    Service para aplicar filtros baseados nos vínculos de acesso do usuário
    """
    
    @classmethod
    def filtrar_query_por_canal(cls, usuario: PortalUsuario, base_query: str, 
                               campo_canal: str = 'canal_id') -> str:
        """
        Aplica filtro de canal na query SQL baseado nos vínculos do usuário
        
        Args:
            usuario: Usuário Portal
            base_query: Query SQL base
            campo_canal: Nome do campo de canal na query
            
        Returns:
            str: Query com filtro aplicado
        """
        canais_usuario = ControleAcessoService.obter_canais_usuario(usuario)
        
        # Se lista vazia = acesso global (sem filtro)
        if not canais_usuario:
            return base_query
            
        # Aplicar filtro de canais específicos
        canais_str = ','.join(map(str, canais_usuario))
        
        # Adicionar WHERE ou AND conforme necessário
        if 'WHERE' in base_query.upper():
            return f"{base_query} AND {campo_canal} IN ({canais_str})"
        else:
            return f"{base_query} WHERE {campo_canal} IN ({canais_str})"
    
    @classmethod
    def filtrar_query_por_loja(cls, usuario: PortalUsuario, base_query: str,
                              campo_loja: str = 'loja_id') -> str:
        """
        Aplica filtro de loja na query SQL baseado nos vínculos do usuário
        
        Args:
            usuario: Usuário Portal
            base_query: Query SQL base
            campo_loja: Nome do campo de loja na query
            
        Returns:
            str: Query com filtro aplicado
        """
        lojas_usuario = ControleAcessoService.obter_lojas_usuario(usuario)
        
        # Se lista vazia = acesso global (sem filtro)
        if not lojas_usuario:
            return base_query
            
        # Aplicar filtro de lojas específicas
        lojas_str = ','.join(map(str, lojas_usuario))
        
        # Adicionar WHERE ou AND conforme necessário
        if 'WHERE' in base_query.upper():
            return f"{base_query} AND {campo_loja} IN ({lojas_str})"
        else:
            return f"{base_query} WHERE {campo_loja} IN ({lojas_str})"
    
    @classmethod
    def filtrar_query_por_grupo_economico(cls, usuario: PortalUsuario, base_query: str,
                                         campo_grupo: str = 'grupo_economico_id') -> str:
        """
        Aplica filtro de grupo econômico na query SQL baseado nos vínculos do usuário
        
        Args:
            usuario: Usuário Portal
            base_query: Query SQL base
            campo_grupo: Nome do campo de grupo econômico na query
            
        Returns:
            str: Query com filtro aplicado
        """
        vinculos = ControleAcessoService.obter_vinculos_usuario(usuario, 'grupo_economico')
        
        # Se sem vínculos = acesso global (sem filtro)
        if not vinculos:
            return base_query
            
        # Aplicar filtro de grupos específicos
        grupos_ids = [vinculo.entidade_id for vinculo in vinculos]
        grupos_str = ','.join(map(str, grupos_ids))
        
        # Adicionar WHERE ou AND conforme necessário
        if 'WHERE' in base_query.upper():
            return f"{base_query} AND {campo_grupo} IN ({grupos_str})"
        else:
            return f"{base_query} WHERE {campo_grupo} IN ({grupos_str})"
    
    @classmethod
    def obter_estatisticas_filtradas(cls, usuario: PortalUsuario) -> Dict[str, Any]:
        """
        Obtém estatísticas do dashboard filtradas pelos vínculos do usuário
        
        Args:
            usuario: Usuário Portal
            
        Returns:
            Dict: Estatísticas filtradas
        """
        # Query base para transações
        base_query = """
            SELECT COUNT(*) as transacoes, SUM(CAST(var19 as DECIMAL(10,2))) as valor
            FROM (
                SELECT var9, var19, var4,
                       ROW_NUMBER() OVER (PARTITION BY var9 ORDER BY id DESC) as rn
                FROM baseTransacoesGestao 
                WHERE {filtro_data}
                AND var19 IS NOT NULL AND var19 != ''
                AND var68 = 'TRANS. APROVADO'
            ) t WHERE rn = 1
        """
        
        # Aplicar filtros baseados nos vínculos do usuário
        canais_usuario = ControleAcessoService.obter_canais_usuario(usuario)
        
        # Se tem vínculos específicos, aplicar filtro por canal via var4
        if canais_usuario:
            # Buscar mapeamento dinâmico de canal_id para valores de var4
            from wallclub_core.estr_organizacional.canal import Canal
            
            valores_var4 = []
            for canal_id in canais_usuario:
                # Usar método centralizado para obter nome do canal
                canal_nome = Canal.get_canal_nome(canal_id)
                if canal_nome and canal_nome != f"Canal {canal_id}":
                    valores_var4.append(f"'{canal_nome}'")

            
            if valores_var4:
                filtro_canal = f" AND var4 IN ({','.join(valores_var4)})"
            else:
                filtro_canal = ""
        else:
            filtro_canal = ""
        
        # Query consolidada - calcula todas as estatísticas em uma única passada
        query_consolidada = f"""
            SELECT 
                COUNT(CASE WHEN data_transacao >= CURDATE() THEN 1 END) as transacoes_hoje,
                SUM(CASE WHEN data_transacao >= CURDATE() THEN CAST(var19 AS DECIMAL(10,2)) ELSE 0 END) as valor_hoje,
                COUNT(CASE WHEN YEAR(data_transacao) = YEAR(CURDATE()) AND MONTH(data_transacao) = MONTH(CURDATE()) THEN 1 END) as transacoes_mes,
                SUM(CASE WHEN YEAR(data_transacao) = YEAR(CURDATE()) AND MONTH(data_transacao) = MONTH(CURDATE()) THEN CAST(var19 AS DECIMAL(10,2)) ELSE 0 END) as valor_mes
            FROM (
                SELECT var9, var19, var4, data_transacao,
                       ROW_NUMBER() OVER (PARTITION BY var9 ORDER BY id DESC) as rn
                FROM baseTransacoesGestao 
                WHERE var19 IS NOT NULL
                AND var68 = 'TRANS. APROVADO'
                {filtro_canal}
            ) t WHERE rn = 1
        """
        
        with connection.cursor() as cursor:
            cursor.execute(query_consolidada)
            resultado = cursor.fetchone()
            transacoes_hoje = resultado[0] or 0
            valor_hoje = resultado[1] or 0
            transacoes_mes = resultado[2] or 0
            valor_mes = resultado[3] or 0
        
        return {
            'transacoes_hoje': transacoes_hoje,
            'valor_hoje': valor_hoje,
            'transacoes_mes': transacoes_mes,
            'valor_mes': valor_mes,
            'filtros_aplicados': bool(canais_usuario)
        }
    
    @classmethod
    def obter_lojas_acessiveis(cls, usuario: PortalUsuario, portal: str = 'lojista') -> List[Dict[str, Any]]:
        """
        Obtém lista de lojas que o usuário tem acesso
        
        Args:
            usuario: Usuário Portal
            portal: Portal específico para filtrar vínculos (default: 'lojista')
            
        Returns:
            List[Dict]: Lista de lojas acessíveis
        """
        from wallclub_core.estr_organizacional.services import HierarquiaOrganizacionalService
        from .models import PortalPermissao
        
        # Verificar nível de acesso do usuário no portal
        try:
            permissao = PortalPermissao.objects.get(usuario=usuario, portal=portal)
            nivel_acesso = permissao.nivel_acesso
        except PortalPermissao.DoesNotExist:
            nivel_acesso = None
        
        # Usuários com nível admin têm acesso a TODAS as lojas
        NIVEIS_ACESSO_GLOBAL = ['admin_total', 'lojista_admin', 'admin_superusuario']
        
        if nivel_acesso in NIVEIS_ACESSO_GLOBAL:
            # Acesso global - retornar todas as lojas
            lojas_queryset = HierarquiaOrganizacionalService.listar_todas_lojas()
            return [{
                'id': loja.id,
                'nome': loja.razao_social or f'Loja {loja.id}',
                'razao_social': loja.razao_social,
                'cnpj': loja.cnpj
            } for loja in lojas_queryset]
        
        # Para níveis restritos, verificar vínculos
        from django.db.models import Q
        vinculos_query = PortalUsuarioAcesso.objects.filter(
            Q(usuario=usuario, ativo=True) & 
            (Q(portal=portal) | Q(portal__isnull=True))
        )
        vinculos = list(vinculos_query)
        
        if not vinculos:
            # Sem vínculos e sem acesso global = sem lojas
            return []
        
        lojas_acessiveis = []
        
        for vinculo in vinculos:
            if vinculo.entidade_tipo == 'loja':
                # Acesso direto à loja
                loja = HierarquiaOrganizacionalService.get_loja(vinculo.entidade_id)
                if loja:
                    lojas_acessiveis.append({
                        'id': loja.id,
                        'nome': loja.razao_social or f'Loja {loja.id}',
                        'razao_social': loja.razao_social,
                        'cnpj': loja.cnpj
                    })
                    
            elif vinculo.entidade_tipo == 'canal':
                # Acesso a todas as lojas do canal via navegação hierárquica
                from wallclub_core.estr_organizacional.loja import Loja
                lojas_canal = Loja.objects.filter(
                    GrupoEconomicoId__in=HierarquiaOrganizacionalService.get_grupos_por_canal(vinculo.entidade_id)
                )
                for loja in lojas_canal:
                    lojas_acessiveis.append({
                        'id': loja.id,
                        'nome': loja.razao_social or f'Loja {loja.id}',
                        'razao_social': loja.razao_social,
                        'cnpj': loja.cnpj
                    })
                
            elif vinculo.entidade_tipo == 'grupo_economico':
                # Acesso a todas as lojas do grupo econômico
                from wallclub_core.estr_organizacional.loja import Loja
                lojas_grupo = Loja.objects.filter(GrupoEconomicoId=vinculo.entidade_id)
                for loja in lojas_grupo:
                    lojas_acessiveis.append({
                        'id': loja.id,
                        'nome': loja.razao_social or f'Loja {loja.id}',
                        'razao_social': loja.razao_social,
                        'cnpj': loja.cnpj
                    })
        
        # Remover duplicatas
        lojas_unicas = {}
        for loja in lojas_acessiveis:
            lojas_unicas[loja['id']] = loja
            
        return list(lojas_unicas.values())
    
    @classmethod
    def usuario_pode_acessar_loja(cls, usuario: PortalUsuario, loja_id: int) -> bool:
        """
        Verifica se usuário pode acessar uma loja específica
        
        Args:
            usuario: Usuário Portal
            loja_id: ID da loja
            
        Returns:
            bool: True se pode acessar, False caso contrário
        """
        lojas_acessiveis = cls.obter_lojas_acessiveis(usuario)
        return any(loja['id'] == loja_id for loja in lojas_acessiveis)
    
    @classmethod
    def validar_acesso_loja_ou_403(cls, usuario: PortalUsuario, loja_id: int):
        """
        Valida acesso à loja ou retorna 403 Forbidden
        
        Args:
            usuario: Usuário Portal
            loja_id: ID da loja
            
        Raises:
            PermissionDenied: Se usuário não tem acesso à loja
        """
        from django.core.exceptions import PermissionDenied
        
        if not cls.usuario_pode_acessar_loja(usuario, loja_id):
            raise PermissionDenied(f"Acesso negado à loja {loja_id}")
