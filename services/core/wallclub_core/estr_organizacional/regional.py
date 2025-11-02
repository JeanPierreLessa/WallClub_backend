"""
Modelo Regional - Estrutura Organizacional
"""

from django.db import models


class Regional(models.Model):
    """
    Modelo para regionais por canal
    """

    id = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=256, null=True, blank=True)
    canalId = models.PositiveIntegerField()

    class Meta:
        db_table = 'regionais'
        managed = False  # Django não gerencia esta tabela (legado)
        verbose_name = 'Regional'
        verbose_name_plural = 'Regionais'

    def __str__(self):
        return f"{self.nome} (Canal: {self.canalId})"

    @property
    def canal(self):
        """Retorna o canal da regional"""
        from .canal import Canal
        try:
            return Canal.objects.get(id=self.canalId)
        except Canal.DoesNotExist:
            return None

    @classmethod
    def get_regional(cls, regional_id):
        """
        Busca uma regional pelo ID

        Args:
            regional_id (int): ID da regional

        Returns:
            Regional: Objeto regional ou None se não encontrado
        """
        try:
            return cls.objects.get(id=regional_id)
        except cls.DoesNotExist:
            return None

    @classmethod
    def listar_por_canal(cls, canal_id):
        """
        Lista todas as regionais de um canal

        Args:
            canal_id (int): ID do canal

        Returns:
            QuerySet: Lista de regionais do canal
        """
        return cls.objects.filter(canalId=canal_id).order_by('nome')

    @classmethod
    def criar_regional(cls, nome, canal_id):
        """
        Cria uma nova regional

        Args:
            nome (str): Nome da regional
            canal_id (int): ID do canal

        Returns:
            tuple: (Regional, bool) - Objeto regional criado e flag indicando sucesso
        """
        try:
            regional = cls(nome=nome, canalId=canal_id)
            regional.save()
            return regional, True
        except Exception as e:
            from wallclub_core.utilitarios.log_control import registrar_log
            registrar_log('comum.estr_organizacional', f"Erro ao criar regional: {str(e)}", nivel='ERROR')
            return None, False

    @classmethod
    def atualizar_regional(cls, regional_id, **kwargs):
        """
        Atualiza dados de uma regional

        Args:
            regional_id (int): ID da regional
            **kwargs: Campos a serem atualizados (nome, canalId)

        Returns:
            tuple: (Regional, bool) - Objeto regional atualizado e flag indicando sucesso
        """
        try:
            regional = cls.get_regional(regional_id)
            if not regional:
                return None, False

            # Atualizar campos
            if 'nome' in kwargs:
                regional.nome = kwargs['nome']
            if 'canal_id' in kwargs:
                regional.canalId = kwargs['canal_id']

            regional.save()
            return regional, True
        except Exception as e:
            from wallclub_core.utilitarios.log_control import registrar_log
            registrar_log('comum.estr_organizacional', f"Erro ao atualizar regional: {str(e)}", nivel='ERROR')
            return None, False

    @property
    def vendedores(self):
        """Retorna os vendedores da regional"""
        from .vendedor import Vendedor
        return Vendedor.listar_por_regional(self.id)
