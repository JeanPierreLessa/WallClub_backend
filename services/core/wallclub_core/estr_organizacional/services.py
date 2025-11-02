"""
HierarquiaOrganizacionalService - Serviço para gerenciar a estrutura organizacional
Hierarquia: Canal → Regional → Vendedor → Grupo Econômico → Loja
"""

from typing import Optional, Dict, List, Tuple
from django.db import transaction
from wallclub_core.utilitarios.log_control import registrar_log

from .canal import Canal
from .regional import Regional
from .vendedor import Vendedor
from .grupo_economico import GrupoEconomico
from .loja import Loja


class HierarquiaOrganizacionalService:
    """
    Service centralizado para operações de estrutura organizacional.
    Gerencia toda a hierarquia: Canal → Regional → Vendedor → Grupo → Loja
    """
    
    MODULO = 'comum.estr_organizacional'
    
    # ==================== CANAL ====================
    
    @classmethod
    def get_canal(cls, canal_id: int) -> Optional[Canal]:
        """Busca um canal pelo ID"""
        try:
            return Canal.get_canal(canal_id)
        except Exception as e:
            registrar_log(cls.MODULO, f"Erro ao buscar canal {canal_id}: {str(e)}", nivel='ERROR')
            return None
    
    @classmethod
    def listar_canais(cls) -> List[Canal]:
        """Lista todos os canais ativos"""
        try:
            return Canal.listar_canais_ativos()
        except Exception as e:
            registrar_log(cls.MODULO, f"Erro ao listar canais: {str(e)}", nivel='ERROR')
            return []
    
    @classmethod
    def get_canal_info_completa(cls, canal_id: int) -> Optional[Dict]:
        """Retorna informações completas do canal incluindo regionais"""
        try:
            canal = cls.get_canal(canal_id)
            if not canal:
                return None
            
            regionais = Regional.listar_por_canal(canal_id)
            
            return {
                'id': canal.id,
                'nome': canal.nome,
                'cnpj': canal.cnpj,
                'marca': canal.marca,
                'descricao': canal.descricao,
                'total_regionais': regionais.count(),
                'regionais': [{'id': r.id, 'nome': r.nome} for r in regionais]
            }
        except Exception as e:
            registrar_log(cls.MODULO, f"Erro ao buscar info do canal {canal_id}: {str(e)}", nivel='ERROR')
            return None
    
    @classmethod
    @transaction.atomic
    def criar_canal(cls, nome: str, marca: str, cnpj: str = None, **kwargs) -> Tuple[Optional[Canal], bool]:
        """Cria um novo canal"""
        try:
            if not nome or not marca:
                registrar_log(cls.MODULO, "Nome e marca são obrigatórios", nivel='WARNING')
                return None, False
            
            canal, sucesso = Canal.criar_canal(nome, marca, cnpj, **kwargs)
            if sucesso:
                registrar_log(cls.MODULO, f"Canal criado: {canal.id} - {canal.nome}", nivel='INFO')
            return canal, sucesso
        except Exception as e:
            registrar_log(cls.MODULO, f"Erro ao criar canal: {str(e)}", nivel='ERROR')
            return None, False
    
    @classmethod
    @transaction.atomic
    def atualizar_canal(cls, canal_id: int, **kwargs) -> Tuple[Optional[Canal], bool]:
        """Atualiza um canal existente"""
        try:
            canal, sucesso = Canal.atualizar_canal(canal_id, **kwargs)
            if sucesso:
                registrar_log(cls.MODULO, f"Canal atualizado: {canal_id}", nivel='INFO')
            return canal, sucesso
        except Exception as e:
            registrar_log(cls.MODULO, f"Erro ao atualizar canal {canal_id}: {str(e)}", nivel='ERROR')
            return None, False
    
    # ==================== REGIONAL ====================
    
    @classmethod
    def get_regional(cls, regional_id: int) -> Optional[Regional]:
        """Busca uma regional pelo ID"""
        try:
            return Regional.get_regional(regional_id)
        except Exception as e:
            registrar_log(cls.MODULO, f"Erro ao buscar regional {regional_id}: {str(e)}", nivel='ERROR')
            return None
    
    @classmethod
    def listar_regionais_por_canal(cls, canal_id: int) -> List[Regional]:
        """Lista todas as regionais de um canal"""
        try:
            return list(Regional.listar_por_canal(canal_id))
        except Exception as e:
            registrar_log(cls.MODULO, f"Erro ao listar regionais: {str(e)}", nivel='ERROR')
            return []
    
    @classmethod
    def get_regional_info_completa(cls, regional_id: int) -> Optional[Dict]:
        """Retorna informações completas da regional incluindo vendedores"""
        try:
            regional = cls.get_regional(regional_id)
            if not regional:
                return None
            
            vendedores = Vendedor.listar_por_regional(regional_id)
            
            return {
                'id': regional.id,
                'nome': regional.nome,
                'canal_id': regional.canalId,
                'canal_nome': Canal.get_canal_nome(regional.canalId),
                'total_vendedores': vendedores.count(),
                'vendedores': [{'id': v.id, 'nome': v.nome} for v in vendedores]
            }
        except Exception as e:
            registrar_log(cls.MODULO, f"Erro ao buscar info regional {regional_id}: {str(e)}", nivel='ERROR')
            return None
    
    @classmethod
    @transaction.atomic
    def criar_regional(cls, nome: str, canal_id: int) -> Tuple[Optional[Regional], bool]:
        """Cria uma nova regional"""
        try:
            if not nome or not canal_id:
                registrar_log(cls.MODULO, "Nome e canal_id são obrigatórios", nivel='WARNING')
                return None, False
            
            if not cls.get_canal(canal_id):
                registrar_log(cls.MODULO, f"Canal {canal_id} não encontrado", nivel='WARNING')
                return None, False
            
            regional, sucesso = Regional.criar_regional(nome, canal_id)
            if sucesso:
                registrar_log(cls.MODULO, f"Regional criada: {regional.id} - {regional.nome}", nivel='INFO')
            return regional, sucesso
        except Exception as e:
            registrar_log(cls.MODULO, f"Erro ao criar regional: {str(e)}", nivel='ERROR')
            return None, False
    
    @classmethod
    @transaction.atomic
    def atualizar_regional(cls, regional_id: int, **kwargs) -> Tuple[Optional[Regional], bool]:
        """Atualiza uma regional existente"""
        try:
            regional, sucesso = Regional.atualizar_regional(regional_id, **kwargs)
            if sucesso:
                registrar_log(cls.MODULO, f"Regional atualizada: {regional_id}", nivel='INFO')
            return regional, sucesso
        except Exception as e:
            registrar_log(cls.MODULO, f"Erro ao atualizar regional {regional_id}: {str(e)}", nivel='ERROR')
            return None, False
    
    # ==================== VENDEDOR ====================
    
    @classmethod
    def get_vendedor(cls, vendedor_id: int) -> Optional[Vendedor]:
        """Busca um vendedor pelo ID"""
        try:
            return Vendedor.get_vendedor(vendedor_id)
        except Exception as e:
            registrar_log(cls.MODULO, f"Erro ao buscar vendedor {vendedor_id}: {str(e)}", nivel='ERROR')
            return None
    
    @classmethod
    def listar_vendedores_por_regional(cls, regional_id: int) -> List[Vendedor]:
        """Lista todos os vendedores de uma regional"""
        try:
            return list(Vendedor.listar_por_regional(regional_id))
        except Exception as e:
            registrar_log(cls.MODULO, f"Erro ao listar vendedores: {str(e)}", nivel='ERROR')
            return []
    
    @classmethod
    def get_vendedor_info_completa(cls, vendedor_id: int) -> Optional[Dict]:
        """Retorna informações completas do vendedor incluindo grupos econômicos"""
        try:
            vendedor = cls.get_vendedor(vendedor_id)
            if not vendedor:
                return None
            
            grupos = GrupoEconomico.listar_por_vendedor(vendedor_id)
            regional = cls.get_regional(vendedor.regionalId)
            
            return {
                'id': vendedor.id,
                'nome': vendedor.nome,
                'regional_id': vendedor.regionalId,
                'regional_nome': regional.nome if regional else None,
                'total_grupos': grupos.count(),
                'grupos': [{'id': g.id, 'nome': g.nome} for g in grupos]
            }
        except Exception as e:
            registrar_log(cls.MODULO, f"Erro ao buscar info vendedor {vendedor_id}: {str(e)}", nivel='ERROR')
            return None
    
    @classmethod
    @transaction.atomic
    def criar_vendedor(cls, nome: str, regional_id: int) -> Tuple[Optional[Vendedor], bool]:
        """Cria um novo vendedor"""
        try:
            if not nome or not regional_id:
                registrar_log(cls.MODULO, "Nome e regional_id são obrigatórios", nivel='WARNING')
                return None, False
            
            if not cls.get_regional(regional_id):
                registrar_log(cls.MODULO, f"Regional {regional_id} não encontrada", nivel='WARNING')
                return None, False
            
            vendedor, sucesso = Vendedor.criar_vendedor(nome, regional_id)
            if sucesso:
                registrar_log(cls.MODULO, f"Vendedor criado: {vendedor.id} - {vendedor.nome}", nivel='INFO')
            return vendedor, sucesso
        except Exception as e:
            registrar_log(cls.MODULO, f"Erro ao criar vendedor: {str(e)}", nivel='ERROR')
            return None, False
    
    @classmethod
    @transaction.atomic
    def atualizar_vendedor(cls, vendedor_id: int, **kwargs) -> Tuple[Optional[Vendedor], bool]:
        """Atualiza um vendedor existente"""
        try:
            vendedor, sucesso = Vendedor.atualizar_vendedor(vendedor_id, **kwargs)
            if sucesso:
                registrar_log(cls.MODULO, f"Vendedor atualizado: {vendedor_id}", nivel='INFO')
            return vendedor, sucesso
        except Exception as e:
            registrar_log(cls.MODULO, f"Erro ao atualizar vendedor {vendedor_id}: {str(e)}", nivel='ERROR')
            return None, False
    
    # ==================== GRUPO ECONÔMICO ====================
    
    @classmethod
    def get_grupo_economico(cls, grupo_id: int) -> Optional[GrupoEconomico]:
        """Busca um grupo econômico pelo ID"""
        try:
            return GrupoEconomico.get_grupo_economico(grupo_id)
        except Exception as e:
            registrar_log(cls.MODULO, f"Erro ao buscar grupo {grupo_id}: {str(e)}", nivel='ERROR')
            return None
    
    @classmethod
    def listar_grupos_por_vendedor(cls, vendedor_id: int) -> List[GrupoEconomico]:
        """Lista todos os grupos econômicos de um vendedor"""
        try:
            return list(GrupoEconomico.listar_por_vendedor(vendedor_id))
        except Exception as e:
            registrar_log(cls.MODULO, f"Erro ao listar grupos: {str(e)}", nivel='ERROR')
            return []
    
    @classmethod
    def get_grupo_info_completa(cls, grupo_id: int) -> Optional[Dict]:
        """Retorna informações completas do grupo incluindo lojas"""
        try:
            grupo = cls.get_grupo_economico(grupo_id)
            if not grupo:
                return None
            
            lojas = Loja.listar_por_grupo_economico(grupo_id)
            vendedor = cls.get_vendedor(grupo.vendedorId)
            
            return {
                'id': grupo.id,
                'nome': grupo.nome,
                'vendedor_id': grupo.vendedorId,
                'vendedor_nome': vendedor.nome if vendedor else None,
                'total_lojas': len(lojas),
                'lojas': lojas
            }
        except Exception as e:
            registrar_log(cls.MODULO, f"Erro ao buscar info grupo {grupo_id}: {str(e)}", nivel='ERROR')
            return None
    
    @classmethod
    @transaction.atomic
    def criar_grupo_economico(cls, nome: str, vendedor_id: int) -> Tuple[Optional[GrupoEconomico], bool]:
        """Cria um novo grupo econômico"""
        try:
            if not nome or not vendedor_id:
                registrar_log(cls.MODULO, "Nome e vendedor_id são obrigatórios", nivel='WARNING')
                return None, False
            
            if not cls.get_vendedor(vendedor_id):
                registrar_log(cls.MODULO, f"Vendedor {vendedor_id} não encontrado", nivel='WARNING')
                return None, False
            
            grupo, sucesso = GrupoEconomico.criar_grupo_economico(nome, vendedor_id)
            if sucesso:
                registrar_log(cls.MODULO, f"Grupo criado: {grupo.id} - {grupo.nome}", nivel='INFO')
            return grupo, sucesso
        except Exception as e:
            registrar_log(cls.MODULO, f"Erro ao criar grupo: {str(e)}", nivel='ERROR')
            return None, False
    
    @classmethod
    @transaction.atomic
    def atualizar_grupo_economico(cls, grupo_id: int, **kwargs) -> Tuple[Optional[GrupoEconomico], bool]:
        """Atualiza um grupo econômico existente"""
        try:
            grupo, sucesso = GrupoEconomico.atualizar_grupo_economico(grupo_id, **kwargs)
            if sucesso:
                registrar_log(cls.MODULO, f"Grupo atualizado: {grupo_id}", nivel='INFO')
            return grupo, sucesso
        except Exception as e:
            registrar_log(cls.MODULO, f"Erro ao atualizar grupo {grupo_id}: {str(e)}", nivel='ERROR')
            return None, False
    
    # ==================== LOJA ====================
    
    @classmethod
    def get_loja(cls, loja_id: int) -> Optional[Loja]:
        """Busca uma loja pelo ID"""
        try:
            return Loja.get_loja(loja_id)
        except Exception as e:
            registrar_log(cls.MODULO, f"Erro ao buscar loja {loja_id}: {str(e)}", nivel='ERROR')
            return None
    
    @classmethod
    def listar_lojas_por_grupo(cls, grupo_id: int) -> List[Dict]:
        """Lista todas as lojas de um grupo econômico"""
        try:
            return Loja.listar_por_grupo_economico(grupo_id)
        except Exception as e:
            registrar_log(cls.MODULO, f"Erro ao listar lojas: {str(e)}", nivel='ERROR')
            return []
    
    @classmethod
    def listar_lojas_por_canal(cls, canal_id: int) -> List[Dict]:
        """Lista todas as lojas de um canal"""
        try:
            return Loja.listar_por_canal(canal_id)
        except Exception as e:
            registrar_log(cls.MODULO, f"Erro ao listar lojas: {str(e)}", nivel='ERROR')
            return []
    
    @classmethod
    def get_loja_hierarquia_completa(cls, loja_id: int) -> Optional[Dict]:
        """Retorna toda a hierarquia de uma loja"""
        try:
            loja = cls.get_loja(loja_id)
            if not loja:
                return None
            
            resultado = {
                'loja': {
                    'id': loja.id,
                    'razao_social': loja.razao_social,
                    'cnpj': loja.cnpj,
                    'grupo_economico_id': loja.GrupoEconomicoId
                }
            }
            
            if loja.GrupoEconomicoId:
                grupo = cls.get_grupo_economico(loja.GrupoEconomicoId)
                if grupo:
                    resultado['grupo'] = {'id': grupo.id, 'nome': grupo.nome, 'vendedor_id': grupo.vendedorId}
                    
                    vendedor = cls.get_vendedor(grupo.vendedorId)
                    if vendedor:
                        resultado['vendedor'] = {'id': vendedor.id, 'nome': vendedor.nome, 'regional_id': vendedor.regionalId}
                        
                        regional = cls.get_regional(vendedor.regionalId)
                        if regional:
                            resultado['regional'] = {'id': regional.id, 'nome': regional.nome, 'canal_id': regional.canalId}
                            
                            canal = cls.get_canal(regional.canalId)
                            if canal:
                                resultado['canal'] = {'id': canal.id, 'nome': canal.nome, 'marca': canal.marca}
            
            return resultado
        except Exception as e:
            registrar_log(cls.MODULO, f"Erro ao buscar hierarquia loja {loja_id}: {str(e)}", nivel='ERROR')
            return None
    
    @classmethod
    @transaction.atomic
    def criar_loja(cls, razao_social: str, grupo_economico_id: int, cnpj: str = None, 
                   canal_id: int = None, **kwargs) -> Tuple[Optional[Loja], bool]:
        """Cria uma nova loja"""
        try:
            if not razao_social or not grupo_economico_id:
                registrar_log(cls.MODULO, "Razão social e grupo_economico_id são obrigatórios", nivel='WARNING')
                return None, False
            
            if not cls.get_grupo_economico(grupo_economico_id):
                registrar_log(cls.MODULO, f"Grupo econômico {grupo_economico_id} não encontrado", nivel='WARNING')
                return None, False
            
            loja, sucesso = Loja.criar_loja(razao_social, grupo_economico_id, cnpj, canal_id, **kwargs)
            if sucesso:
                registrar_log(cls.MODULO, f"Loja criada: {loja.id} - {loja.razao_social}", nivel='INFO')
            return loja, sucesso
        except Exception as e:
            registrar_log(cls.MODULO, f"Erro ao criar loja: {str(e)}", nivel='ERROR')
            return None, False
    
    @classmethod
    @transaction.atomic
    def atualizar_loja(cls, loja_id: int, **kwargs) -> Tuple[Optional[Loja], bool]:
        """Atualiza uma loja existente"""
        try:
            loja, sucesso = Loja.atualizar_loja(loja_id, **kwargs)
            if sucesso:
                registrar_log(cls.MODULO, f"Loja atualizada: {loja_id}", nivel='INFO')
            return loja, sucesso
        except Exception as e:
            registrar_log(cls.MODULO, f"Erro ao atualizar loja {loja_id}: {str(e)}", nivel='ERROR')
            return None, False
    
    # ==================== VALIDAÇÃO ====================
    
    @classmethod
    def validar_hierarquia_loja(cls, loja_id: int) -> Tuple[bool, List[str]]:
        """Valida se a hierarquia de uma loja está íntegra"""
        erros = []
        try:
            loja = cls.get_loja(loja_id)
            if not loja:
                erros.append(f"Loja {loja_id} não encontrada")
                return False, erros
            
            if not loja.GrupoEconomicoId:
                erros.append("Loja sem grupo econômico vinculado")
            else:
                grupo = cls.get_grupo_economico(loja.GrupoEconomicoId)
                if not grupo:
                    erros.append(f"Grupo {loja.GrupoEconomicoId} não encontrado")
                else:
                    vendedor = cls.get_vendedor(grupo.vendedorId)
                    if not vendedor:
                        erros.append(f"Vendedor {grupo.vendedorId} não encontrado")
                    else:
                        regional = cls.get_regional(vendedor.regionalId)
                        if not regional:
                            erros.append(f"Regional {vendedor.regionalId} não encontrada")
                        else:
                            canal = cls.get_canal(regional.canalId)
                            if not canal:
                                erros.append(f"Canal {regional.canalId} não encontrado")
            
            return len(erros) == 0, erros
        except Exception as e:
            erros.append(f"Erro ao validar: {str(e)}")
            registrar_log(cls.MODULO, f"Erro ao validar loja {loja_id}: {str(e)}", nivel='ERROR')
            return False, erros
    
    # ==================== MÉTODOS DE LISTAGEM ====================
    
    @classmethod
    def listar_todas_lojas(cls):
        """
        Lista todas as lojas ordenadas por razão social
        
        Returns:
            QuerySet: QuerySet de lojas ordenadas
        """
        try:
            return Loja.objects.all().order_by('razao_social')
        except Exception as e:
            registrar_log(cls.MODULO, f"Erro ao listar lojas: {str(e)}", nivel='ERROR')
            return Loja.objects.none()
    
    @classmethod
    def filtrar_lojas_por_ids(cls, lojas_ids: List[int]):
        """
        Filtra lojas por lista de IDs
        
        Args:
            lojas_ids: Lista de IDs de lojas
            
        Returns:
            QuerySet: QuerySet de lojas filtradas
        """
        try:
            if not lojas_ids:
                return Loja.objects.none()
            return Loja.objects.filter(id__in=lojas_ids)
        except Exception as e:
            registrar_log(cls.MODULO, f"Erro ao filtrar lojas: {str(e)}", nivel='ERROR')
            return Loja.objects.none()
    
    @classmethod
    def listar_lojas_com_parametros(cls):
        """
        Lista lojas que possuem parâmetros vigentes
        
        Returns:
            QuerySet: QuerySet de lojas com parâmetros
        """
        try:
            from parametros_wallclub.models import ParametrosWall
            return Loja.objects.filter(
                id__in=ParametrosWall.objects.values_list('loja_id', flat=True).distinct()
            ).order_by('razao_social')
        except Exception as e:
            registrar_log(cls.MODULO, f"Erro ao listar lojas com parâmetros: {str(e)}", nivel='ERROR')
            return Loja.objects.none()
    
    @classmethod
    def get_grupos_por_canal(cls, canal_id: int) -> List[int]:
        """
        Retorna lista de IDs de grupos econômicos que pertencem a um canal
        
        Args:
            canal_id: ID do canal
            
        Returns:
            List[int]: Lista de IDs de grupos econômicos
        """
        try:
            # Canal -> Regional -> Vendedor -> Grupo Econômico
            # Buscar todas regionais do canal
            regionais = Regional.objects.filter(canalId=canal_id)
            regional_ids = [r.id for r in regionais]
            
            if not regional_ids:
                return []
            
            # Buscar todos vendedores das regionais
            vendedores = Vendedor.objects.filter(regionalId__in=regional_ids)
            vendedor_ids = [v.id for v in vendedores]
            
            if not vendedor_ids:
                return []
            
            # Buscar todos grupos dos vendedores
            grupos = GrupoEconomico.objects.filter(vendedorId__in=vendedor_ids)
            return [g.id for g in grupos]
            
        except Exception as e:
            registrar_log(cls.MODULO, f"Erro ao buscar grupos do canal {canal_id}: {str(e)}", nivel='ERROR')
            return []
