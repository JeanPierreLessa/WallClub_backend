"""
Modelo GrupoEconomico - Estrutura Organizacional
"""

from django.db import models


class GrupoEconomico(models.Model):
    """
    Modelo para grupos econômicos por vendedor
    """

    id = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=256, null=True, blank=True)
    vendedorId = models.PositiveIntegerField()

    class Meta:
        db_table = 'gruposeconomicos'
        managed = False  # Django não gerencia esta tabela (legado)
        verbose_name = 'Grupo Econômico'
        verbose_name_plural = 'Grupos Econômicos'

    def __str__(self):
        return f"{self.nome} (Vendedor: {self.vendedorId})"

    @property
    def vendedor(self):
        """Retorna o vendedor do grupo econômico"""
        from .vendedor import Vendedor
        try:
            return Vendedor.objects.get(id=self.vendedorId)
        except Vendedor.DoesNotExist:
            return None

    @property
    def lojas(self):
        """Retorna todas as lojas do grupo econômico"""
        from .loja import Loja
        return Loja.objects.filter(GrupoEconomicoId=self.id)

    @classmethod
    def get_grupo_economico(cls, grupo_id):
        """
        Busca um grupo econômico pelo ID

        Args:
            grupo_id (int): ID do grupo econômico

        Returns:
            GrupoEconomico: Objeto grupo econômico ou None se não encontrado
        """
        try:
            return cls.objects.get(id=grupo_id)
        except cls.DoesNotExist:
            return None

    @classmethod
    def listar_por_vendedor(cls, vendedor_id):
        """
        Lista todos os grupos econômicos de um vendedor

        Args:
            vendedor_id (int): ID do vendedor

        Returns:
            QuerySet: Lista de grupos econômicos do vendedor
        """
        return cls.objects.filter(vendedorId=vendedor_id).order_by('nome')

    @classmethod
    def criar_grupo_economico(cls, nome, vendedor_id):
        """
        Cria um novo grupo econômico

        Args:
            nome (str): Nome do grupo econômico
            vendedor_id (int): ID do vendedor

        Returns:
            tuple: (GrupoEconomico, bool) - Objeto grupo econômico criado e flag indicando sucesso
        """
        try:
            grupo = cls(nome=nome, vendedorId=vendedor_id)
            grupo.save()
            return grupo, True
        except Exception as e:
            from wallclub_core.utilitarios.log_control import registrar_log
            registrar_log('comum.estr_organizacional', f"Erro ao criar grupo econômico: {str(e)}", nivel='ERROR')
            return None, False

    @classmethod
    def atualizar_grupo_economico(cls, grupo_id, **kwargs):
        """
        Atualiza dados de um grupo econômico

        Args:
            grupo_id (int): ID do grupo econômico
            **kwargs: Campos a serem atualizados (nome, vendedorId)

        Returns:
            tuple: (GrupoEconomico, bool) - Objeto grupo econômico atualizado e flag indicando sucesso
        """
        try:
            grupo = cls.get_grupo_economico(grupo_id)
            if not grupo:
                return None, False

            # Atualizar campos
            if 'nome' in kwargs:
                grupo.nome = kwargs['nome']
            if 'vendedor_id' in kwargs:
                grupo.vendedorId = kwargs['vendedor_id']

            grupo.save()
            return grupo, True
        except Exception as e:
            from wallclub_core.utilitarios.log_control import registrar_log
            registrar_log('comum.estr_organizacional', f"Erro ao atualizar grupo econômico: {str(e)}", nivel='ERROR')
            return None, False
