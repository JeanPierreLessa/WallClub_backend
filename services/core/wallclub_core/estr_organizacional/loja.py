"""
Modelo Loja - Estrutura Organizacional
Migrado de parametros_wallclub/models_loja.py
"""

from django.db import models


class Loja(models.Model):
    """
    Modelo para a tabela loja do sistema legado.
    Mantém estrutura original para compatibilidade.
    """

    id = models.AutoField(primary_key=True)
    razao_social = models.CharField(max_length=256, null=True, blank=True)
    cnpj = models.CharField(max_length=256, null=True, blank=True)
    complemento = models.TextField(null=True, blank=True)
    canal_id = models.IntegerField(null=True, blank=True)
    email = models.CharField(max_length=256, null=True, blank=True)
    senha = models.CharField(max_length=256, null=True, blank=True)
    cod_cliente = models.CharField(max_length=256, null=True, blank=True)
    celular = models.CharField(max_length=256, null=True, blank=True)
    aceite = models.IntegerField(default=0)
    nomebanco = models.CharField(max_length=256, null=True, blank=True)
    numerobanco = models.CharField(max_length=256, null=True, blank=True)
    agencia = models.CharField(max_length=256, null=True, blank=True)
    conta = models.CharField(max_length=256, null=True, blank=True)
    pix = models.CharField(max_length=256, null=True, blank=True)
    GrupoEconomicoId = models.PositiveIntegerField(null=True, blank=True)

    # Campos Pinbank
    pinbank_CodigoCanal = models.IntegerField(null=True, blank=True)
    pinbank_CodigoCliente = models.IntegerField(null=True, blank=True)
    pinbank_KeyValueLoja = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        db_table = 'loja'
        managed = False  # Django não gerencia esta tabela (legado)
        verbose_name = 'Loja'
        verbose_name_plural = 'Lojas'

    def __str__(self):
        return f"{self.razao_social or 'Loja'} (ID: {self.id})"

    @property
    def cnpj_formatado(self):
        """Formata CNPJ para exibição"""
        if not self.cnpj:
            return ''
        cnpj = ''.join(filter(str.isdigit, self.cnpj))
        if len(cnpj) == 14:
            return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
        return self.cnpj

    @property
    def tem_parametros_vigentes(self):
        """Verifica se a loja tem parâmetros vigentes"""
        from parametros_wallclub.models import ParametrosWall
        return ParametrosWall.objects.filter(loja_id=self.id).exists()

    def get_parametros_vigentes(self):
        """Retorna todos os parâmetros vigentes da loja"""
        from parametros_wallclub.models import ParametrosWall
        return ParametrosWall.objects.filter(loja_id=self.id).select_related()

    def get_historico_parametros(self):
        """Retorna histórico de parâmetros da loja"""
        from parametros_wallclub.models import ConfiguracaoHistorico
        return ConfiguracaoHistorico.objects.filter(loja_id=self.id).order_by('-data_alteracao')

    @property
    def grupo_economico(self):
        """Retorna o grupo econômico da loja"""
        if self.GrupoEconomicoId:
            from .grupo_economico import GrupoEconomico
            try:
                return GrupoEconomico.objects.get(id=self.GrupoEconomicoId)
            except GrupoEconomico.DoesNotExist:
                return None
        return None

    @classmethod
    def listar_por_canal(cls, canal_id):
        """Lista lojas de um canal específico"""
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT l.id, l.razao_social, l.cnpj, l.GrupoEconomicoId
                FROM loja l
                JOIN gruposeconomicos g ON l.GrupoEconomicoId = g.id
                JOIN vendedores v ON g.vendedorId = v.id
                JOIN regionais r ON v.regionalId = r.id
                WHERE r.canalId = %s
                ORDER BY l.razao_social
            """, [canal_id])

            return [
                {
                    'id': row[0],
                    'nome': row[1] or f'Loja {row[0]}',
                    'cnpj': row[2],
                    'grupo_economico_id': row[3]
                }
                for row in cursor.fetchall()
            ]

    @classmethod
    def listar_por_grupo_economico(cls, grupo_economico_id):
        """Lista lojas de um grupo econômico específico"""
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, razao_social, cnpj, GrupoEconomicoId
                FROM loja
                WHERE GrupoEconomicoId = %s
                ORDER BY razao_social
            """, [grupo_economico_id])

            return [
                {
                    'id': row[0],
                    'nome': row[1] or f'Loja {row[0]}',
                    'cnpj': row[2],
                    'grupo_economico_id': row[3]
                }
                for row in cursor.fetchall()
            ]

    @classmethod
    def listar_todas(cls):
        """Lista todas as lojas do sistema"""
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, razao_social, cnpj
                FROM loja
                ORDER BY razao_social
            """)

            return [
                {
                    'id': row[0],
                    'nome': row[1] or f'Loja {row[0]}',
                    'cnpj': row[2]
                }
                for row in cursor.fetchall()
            ]

    @classmethod
    def get_loja(cls, loja_id):
        """
        Busca uma loja pelo ID

        Args:
            loja_id (int): ID da loja

        Returns:
            Loja: Objeto loja ou None se não encontrado
        """
        try:
            return cls.objects.get(id=loja_id)
        except cls.DoesNotExist:
            return None

    @classmethod
    def criar_loja(cls, razao_social, grupo_economico_id, cnpj=None, canal_id=None, **kwargs):
        """
        Cria uma nova loja

        Args:
            razao_social (str): Nome da loja
            grupo_economico_id (int): ID do grupo econômico
            cnpj (str, optional): CNPJ da loja
            canal_id (int, optional): ID do canal
            **kwargs: Campos adicionais (email, celular, etc.)

        Returns:
            tuple: (Loja, bool) - Objeto loja criado e flag indicando sucesso
        """
        try:
            loja = cls(razao_social=razao_social,
                       GrupoEconomicoId=grupo_economico_id,
                       cnpj=cnpj,
                       canal_id=canal_id)

            # Atualizar campos adicionais
            for campo, valor in kwargs.items():
                if hasattr(loja, campo):
                    setattr(loja, campo, valor)

            loja.save()
            return loja, True
        except Exception as e:
            from wallclub_core.utilitarios.log_control import registrar_log
            registrar_log('comum.estr_organizacional', f"Erro ao criar loja: {str(e)}", nivel='ERROR')
            return None, False

    @classmethod
    def atualizar_loja(cls, loja_id, **kwargs):
        """
        Atualiza dados de uma loja

        Args:
            loja_id (int): ID da loja
            **kwargs: Campos a serem atualizados (razao_social, cnpj, GrupoEconomicoId, etc.)

        Returns:
            tuple: (Loja, bool) - Objeto loja atualizado e flag indicando sucesso
        """
        try:
            loja = cls.get_loja(loja_id)
            if not loja:
                return None, False

            # Campos comuns que podem ser atualizados
            campos_atualizaveis = [
                'razao_social', 'cnpj', 'complemento', 'canal_id', 'email',
                'senha', 'cod_cliente', 'celular', 'aceite', 'nomebanco',
                'numerobanco', 'agencia', 'conta', 'pix', 'GrupoEconomicoId',
                'pinbank_CodigoCanal', 'pinbank_CodigoCliente', 'pinbank_KeyValueLoja'
            ]

            # Atualizar campos
            for campo, valor in kwargs.items():
                if campo in campos_atualizaveis:
                    setattr(loja, campo, valor)

            loja.save()
            return loja, True
        except Exception as e:
            from wallclub_core.utilitarios.log_control import registrar_log
            registrar_log('comum.estr_organizacional', f"Erro ao atualizar loja: {str(e)}", nivel='ERROR')
            return None, False
