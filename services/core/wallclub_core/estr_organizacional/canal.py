"""
Modelo Canal - Estrutura Organizacional
Migrado de comum/models.py
"""

from django.db import models


class Canal(models.Model):
    """
    Modelo para configurações de canais/marcas.
    Contém configurações específicas por canal incluindo WhatsApp/Facebook.
    """
    id = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=256, null=True, blank=True)
    cnpj = models.CharField(max_length=256, null=True, blank=True)
    descricao = models.CharField(max_length=1024, null=True, blank=True)
    username = models.CharField(max_length=256, null=True, blank=True)
    keyvalue = models.CharField(max_length=256, null=True, blank=True)
    canal = models.CharField(max_length=256, null=True, blank=True)
    codigo_cliente = models.CharField(max_length=256, null=True, blank=True)
    marca = models.CharField(max_length=10, null=True, blank=True)
    json_firebase = models.CharField(max_length=100, null=True, blank=True)
    bundle_id = models.CharField(max_length=100, null=True, blank=True)  # Bundle ID para APN
    facebook_url = models.CharField(max_length=100, null=True, blank=True)
    facebook_token = models.CharField(max_length=256, null=True, blank=True)
    logo_pos = models.CharField(max_length=30, null=True, blank=True)

    class Meta:
        db_table = 'canal'
        verbose_name = 'Canal'
        verbose_name_plural = 'Canais'

    def __str__(self):
        return f"{self.nome} ({self.marca})"

    @classmethod
    def get_canal_nome(cls, canal_id):
        """
        Busca o nome do canal pelo canal_id

        Args:
            canal_id (int): ID do canal

        Returns:
            str: Nome do canal ou string padrão se não encontrado
        """
        try:
            canal = cls.objects.filter(id=canal_id).first()
            if canal and canal.nome:
                return canal.nome
            return f"Canal {canal_id}"
        except Exception:
            return f"Canal {canal_id}"

    @classmethod
    def get_canal_info(cls, canal_id):
        """
        Busca informações completas do canal pelo canal_id

        Args:
            canal_id (int): ID do canal

        Returns:
            dict: Dicionário com informações do canal ou None se não encontrado
        """
        try:
            canal = cls.objects.filter(id=canal_id).first()
            if not canal:
                return None

            return {
                'id': canal.id,
                'nome': canal.nome,
                'cnpj': canal.cnpj,
                'descricao': canal.descricao,
                'marca': canal.marca,
                'json_firebase': canal.json_firebase,
                'bundle_id': canal.bundle_id
            }
        except Exception:
            return None

    @classmethod
    def listar_canais_ativos(cls):
        """
        Lista todos os canais ativos

        Returns:
            list: Lista de objetos Canal
        """
        return cls.objects.all().order_by('nome')

    @classmethod
    def filtrar_por_marca(cls, marca):
        """
        Filtra canais por marca

        Args:
            marca (str): Nome da marca

        Returns:
            list: Lista de objetos Canal filtrados pela marca
        """
        return cls.objects.filter(marca=marca).order_by('nome')

    @classmethod
    def get_canal(cls, canal_id):
        """
        Busca um canal pelo ID

        Args:
            canal_id (int): ID do canal

        Returns:
            Canal: Objeto canal ou None se não encontrado
        """
        try:
            return cls.objects.get(id=canal_id)
        except cls.DoesNotExist:
            return None

    @classmethod
    def criar_canal(cls, nome, marca, cnpj=None, **kwargs):
        """
        Cria um novo canal

        Args:
            nome (str): Nome do canal
            marca (str): Marca do canal (wallclub, aclub, etc.)
            cnpj (str, optional): CNPJ do canal
            **kwargs: Campos adicionais (descricao, keyvalue, etc.)

        Returns:
            tuple: (Canal, bool) - Objeto canal criado e flag indicando sucesso
        """
        try:
            canal = cls(nome=nome, marca=marca, cnpj=cnpj)

            # Atualizar campos adicionais
            for campo, valor in kwargs.items():
                if hasattr(canal, campo):
                    setattr(canal, campo, valor)

            canal.save()
            return canal, True
        except Exception as e:
            from wallclub_core.utilitarios.log_control import registrar_log
            registrar_log('comum.estr_organizacional', f"Erro ao criar canal: {str(e)}", nivel='ERROR')
            return None, False

    @classmethod
    def atualizar_canal(cls, canal_id, **kwargs):
        """
        Atualiza dados de um canal

        Args:
            canal_id (int): ID do canal
            **kwargs: Campos a serem atualizados (nome, marca, cnpj, etc.)

        Returns:
            tuple: (Canal, bool) - Objeto canal atualizado e flag indicando sucesso
        """
        try:
            canal = cls.get_canal(canal_id)
            if not canal:
                return None, False

            # Campos comuns que podem ser atualizados
            campos_atualizaveis = [
                'nome', 'cnpj', 'descricao', 'username', 'keyvalue',
                'canal', 'codigo_cliente', 'marca', 'json_firebase',
                'bundle_id', 'facebook_url', 'facebook_token', 'logo_pos'
            ]

            # Atualizar campos
            for campo, valor in kwargs.items():
                if campo in campos_atualizaveis:
                    setattr(canal, campo, valor)

            canal.save()
            return canal, True
        except Exception as e:
            from wallclub_core.utilitarios.log_control import registrar_log
            registrar_log('comum.estr_organizacional', f"Erro ao atualizar canal: {str(e)}", nivel='ERROR')
            return None, False

    @property
    def regionais(self):
        """Retorna as regionais do canal"""
        from .regional import Regional
        return Regional.listar_por_canal(self.id)
