"""
Modelos para mapeamento de campos entre diferentes adquirentes
Permite configurar via banco de dados como mapear campos de cada adquirente
para o formato padrão da calculadora
"""

from django.db import models


class MapeamentoCamposAdquirente(models.Model):
    """
    Tabela de mapeamento de campos entre adquirentes e formato padrão
    """
    
    ADQUIRENTES = [
        ('PINBANK', 'Pinbank'),
        ('OWN', 'Own Financial'),
        ('OUTROS', 'Outros')
    ]
    
    adquirente = models.CharField(
        max_length=50,
        choices=ADQUIRENTES,
        help_text='Adquirente de origem'
    )
    
    campo_origem = models.CharField(
        max_length=100,
        help_text='Nome do campo no adquirente de origem'
    )
    
    campo_destino = models.CharField(
        max_length=100,
        help_text='Nome do campo no formato padrão da calculadora'
    )
    
    valor_padrao = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Valor padrão caso o campo não exista (opcional)'
    )
    
    tipo_conversao = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        choices=[
            ('STRING', 'String'),
            ('INTEGER', 'Inteiro'),
            ('DECIMAL', 'Decimal'),
            ('DATETIME', 'Data/Hora'),
            ('BOOLEAN', 'Booleano'),
            ('CUSTOM', 'Conversão customizada')
        ],
        help_text='Tipo de conversão necessária'
    )
    
    funcao_conversao = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='Nome da função de conversão customizada (se tipo_conversao=CUSTOM)'
    )
    
    obrigatorio = models.BooleanField(
        default=False,
        help_text='Campo obrigatório para cálculo'
    )
    
    ativo = models.BooleanField(
        default=True,
        help_text='Mapeamento ativo'
    )
    
    observacao = models.TextField(
        null=True,
        blank=True,
        help_text='Observações sobre o mapeamento'
    )
    
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'parametros_mapeamento_campos_adquirente'
        verbose_name = 'Mapeamento de Campos'
        verbose_name_plural = 'Mapeamentos de Campos'
        unique_together = ['adquirente', 'campo_destino']
        ordering = ['adquirente', 'campo_destino']
    
    def __str__(self):
        return f"{self.adquirente}: {self.campo_origem} → {self.campo_destino}"
