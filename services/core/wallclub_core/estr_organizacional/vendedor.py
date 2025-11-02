"""
Modelo Vendedor - Estrutura Organizacional
"""

from django.db import models


class Vendedor(models.Model):
    """
    Modelo para vendedores por regional
    """

    id = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=256, null=True, blank=True)
    regionalId = models.PositiveIntegerField()

    class Meta:
        db_table = 'vendedores'
        managed = False  # Django não gerencia esta tabela (legado)
        verbose_name = 'Vendedor'
        verbose_name_plural = 'Vendedores'

    def __str__(self):
        return f"{self.nome} (Regional: {self.regionalId})"

    @classmethod
    def get_vendedor(cls, vendedor_id):
        """
        Busca um vendedor pelo ID

        Args:
            vendedor_id (int): ID do vendedor

        Returns:
            Vendedor: Objeto vendedor ou None se não encontrado
        """
        try:
            return cls.objects.get(id=vendedor_id)
        except cls.DoesNotExist:
            return None

    @classmethod
    def listar_por_regional(cls, regional_id):
        """
        Lista todos os vendedores de uma regional

        Args:
            regional_id (int): ID da regional

        Returns:
            QuerySet: Lista de vendedores da regional
        """
        return cls.objects.filter(regionalId=regional_id).order_by('nome')

    @classmethod
    def criar_vendedor(cls, nome, regional_id):
        """
        Cria um novo vendedor

        Args:
            nome (str): Nome do vendedor
            regional_id (int): ID da regional

        Returns:
            tuple: (Vendedor, bool) - Objeto vendedor criado e flag indicando sucesso
        """
        try:
            vendedor = cls(nome=nome, regionalId=regional_id)
            vendedor.save()
            return vendedor, True
        except Exception as e:
            from wallclub_core.utilitarios.log_control import registrar_log
            registrar_log('comum.estr_organizacional', f"Erro ao criar vendedor: {str(e)}", nivel='ERROR')
            return None, False

    @classmethod
    def atualizar_vendedor(cls, vendedor_id, **kwargs):
        """
        Atualiza dados de um vendedor

        Args:
            vendedor_id (int): ID do vendedor
            **kwargs: Campos a serem atualizados (nome, regionalId)

        Returns:
            tuple: (Vendedor, bool) - Objeto vendedor atualizado e flag indicando sucesso
        """
        try:
            vendedor = cls.get_vendedor(vendedor_id)
            if not vendedor:
                return None, False

            # Atualizar campos
            if 'nome' in kwargs:
                vendedor.nome = kwargs['nome']
            if 'regional_id' in kwargs:
                vendedor.regionalId = kwargs['regional_id']

            vendedor.save()
            return vendedor, True
        except Exception as e:
            from wallclub_core.utilitarios.log_control import registrar_log
            registrar_log('comum.estr_organizacional', f"Erro ao atualizar vendedor: {str(e)}", nivel='ERROR')
            return None, False

    @property
    def regional(self):
        """Retorna a regional do vendedor"""
        from .regional import Regional
        try:
            return Regional.objects.get(id=self.regionalId)
        except Regional.DoesNotExist:
            return None
