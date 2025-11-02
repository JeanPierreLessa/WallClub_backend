"""
Modelos para o sistema de parâmetros financeiros WallClub.

ARQUITETURA LIMPA:
- ConfiguracaoVigente: Configurações ativas no momento
- ConfiguracaoFutura: Configurações agendadas para ativação
- ImportacaoConfiguracoes: Controle de importações

ELIMINADO:
"""

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from decimal import Decimal

# Importar modelo Loja diretamente do módulo
from wallclub_core.estr_organizacional.loja import Loja

class ParametrosWall(models.Model):
    """
    Parâmetros financeiros do sistema WallClub.
    
    ESTRUTURA REAL DA TABELA parametros_wallclub:
    - Campos id_plano, wall, id_desc obrigatórios
    - Todos os parâmetros individuais (loja 1-30, uptal 1-6, wall 1-4)
    - Controle de vigência temporal
    - Usado pelo ParametrosService para buscar configurações
    """
    
    # Identificação
    loja_id = models.IntegerField(
        verbose_name="ID da Loja",
        help_text="Identificador único da loja no sistema"
    )
    
    id_desc = models.CharField(
        max_length=100,
        null=True, blank=True,
        verbose_name="ID Desc (Legado)",
        help_text="Identificador da versão dos parâmetros no sistema legado"
    )
    
    id_plano = models.IntegerField(
        verbose_name="ID do Plano",
        help_text="Identificador do plano de pagamento"
    )
    
    wall = models.CharField(
        max_length=1,
        choices=[
            ('S', 'Com Wall'),
            ('N', 'Sem Wall'),
            ('C', 'Cashback')
        ],
        verbose_name="Modalidade Wall",
        help_text="S=desconto aplicado no POS, N=sem desconto, C=desconto como cashback na conta digital"
    )
    
    # Controle de vigência
    vigencia_inicio = models.DateTimeField(
        verbose_name="Início da Vigência",
        help_text="Data e hora de início da vigência desta configuração"
    )
    
    vigencia_fim = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Fim da Vigência", 
        help_text="Data e hora de fim da vigência (null = vigência indefinida)"
    )
    
    # Parâmetros da loja (1-30)
    parametro_loja_1 = models.IntegerField(
        null=True, blank=True,
        verbose_name="Prazo Máximo Parcelas",
        help_text="Prazo máximo de nº de parcelas (dias)"
    )
    parametro_loja_2 = models.DecimalField(
        max_digits=12, decimal_places=10, null=True, blank=True,
        verbose_name="MDR Operação Normal",
        help_text="MDR Oper. Normal (%)"
    )
    parametro_loja_3 = models.DecimalField(
        max_digits=12, decimal_places=10, null=True, blank=True,
        verbose_name="Taxa Antecipação Mensal",
        help_text="Taxa Antecip. Oper Normal (% a.m.)"
    )
    parametro_loja_4 = models.DecimalField(
        max_digits=12, decimal_places=10, null=True, blank=True,
        verbose_name="Taxa Antecipação Período",
        help_text="Taxa Antecip. Oper Normal (% período)"
    )
    parametro_loja_5 = models.DecimalField(
        max_digits=12, decimal_places=10, null=True, blank=True,
        verbose_name="Taxa Retenção Total",
        help_text="Taxa Retenção Total Normal (% período)"
    )
    parametro_loja_6 = models.IntegerField(
        null=True, blank=True,
        verbose_name="Prazo Reembolso",
        help_text="Prazo de Reembolso (dias corridos a partir da data da compra)"
    )
    parametro_loja_7 = models.DecimalField(
        max_digits=12, decimal_places=10, null=True, blank=True,
        verbose_name="Desconto Cliente Negociado",
        help_text="Desconto Cliente à Vista Wall Negociado (na Nota Fiscal) - %"
    )
    parametro_loja_8 = models.DecimalField(
        max_digits=12, decimal_places=10, null=True, blank=True,
        verbose_name="Desconto Cliente Sugerido",
        help_text="Desconto Cliente à Vista Wall Sugerido (na Nota Fiscal) - %"
    )
    parametro_loja_9 = models.DecimalField(
        max_digits=12, decimal_places=10, null=True, blank=True,
        verbose_name="Desconto Cliente por Prazo",
        help_text="Desconto Cliente à Vista Sugerido por Prazo Máximo - %"
    )
    parametro_loja_10 = models.DecimalField(
        max_digits=12, decimal_places=10, null=True, blank=True,
        verbose_name="Desconto Parcelado",
        help_text="Desconto Cliente Parcelado Wall (Vlr Operação) - %"
    )
    parametro_loja_11 = models.DecimalField(
        max_digits=12, decimal_places=10, null=True, blank=True,
        verbose_name="Desconto PIX",
        help_text="Desconto Pagto a Vista - Pix c/ Tarifas Wall - %"
    )
    parametro_loja_12 = models.DecimalField(
        max_digits=12, decimal_places=10, null=True, blank=True,
        verbose_name="MDR Pago Wall",
        help_text="MDR Pago Wall - %"
    )
    parametro_loja_13 = models.DecimalField(
        max_digits=12, decimal_places=10, null=True, blank=True,
        verbose_name="Taxa Antecipação Wall Mensal",
        help_text="Taxa Antecipação Paga Wall - % (a.m.)"
    )
    parametro_loja_14 = models.DecimalField(
        max_digits=12, decimal_places=10, null=True, blank=True,
        verbose_name="Taxa Antecipação Wall Período",
        help_text="Taxa Antecipação Paga Wall - % (Período)"
    )
    parametro_loja_15 = models.DecimalField(
        max_digits=12, decimal_places=10, null=True, blank=True,
        verbose_name="Taxa Retenção Wall",
        help_text="Taxa Retenção Total c/Wall (% período)"
    )
    parametro_loja_16 = models.CharField(
        max_length=50, null=True, blank=True,
        verbose_name="Regime Tributação",
        help_text="Regime Tributação (MEI, Simples, Presumido, Real)"
    )
    parametro_loja_17 = models.DecimalField(
        max_digits=12, decimal_places=10, null=True, blank=True,
        verbose_name="Alíquota Imposto",
        help_text="Alíquota Imposto - %"
    )
    parametro_loja_18 = models.IntegerField(
        null=True, blank=True,
        verbose_name="Prazo Repasse Wall",
        help_text="Prazo Repasse Wall p/ Loja (nº dias)"
    )
    parametro_loja_19 = models.DecimalField(
        max_digits=12, decimal_places=10, null=True, blank=True,
        verbose_name="Divisão Ganho Impostos",
        help_text="Divisão Ganho Redução Impostos Loja (% Alvo)"
    )
    parametro_loja_20 = models.DecimalField(
        max_digits=12, decimal_places=10, null=True, blank=True,
        verbose_name="Divisão Resultado Wall",
        help_text="Divisão resultado Wall (% Loja)"
    )
    parametro_loja_21 = models.DecimalField(
        max_digits=12, decimal_places=10, null=True, blank=True,
        verbose_name="Divisão Ganho Tributário",
        help_text="Divisão Ganho tributário (% Loja)"
    )
    parametro_loja_22 = models.DecimalField(
        max_digits=12, decimal_places=10, null=True, blank=True,
        verbose_name="Rebate Tipo 1 Mínimo",
        help_text="Rebate Wall (%) Tipo 1 Mínimo"
    )
    parametro_loja_23 = models.DecimalField(
        max_digits=12, decimal_places=10, null=True, blank=True,
        verbose_name="Rebate Tipo 1 Negociado",
        help_text="Rebate Wall (%) Tipo 1 Negociado"
    )
    parametro_loja_24 = models.DecimalField(
        max_digits=12, decimal_places=10, null=True, blank=True,
        verbose_name="Rebate Tipo 2 Mínimo",
        help_text="Rebate Wall (%) Tipo 2 Mínimo"
    )
    parametro_loja_25 = models.DecimalField(
        max_digits=12, decimal_places=10, null=True, blank=True,
        verbose_name="Rebate Tipo 2 Negociado",
        help_text="Rebate Wall (%) Tipo 2 Negociado"
    )
    parametro_loja_26 = models.DecimalField(
        max_digits=12, decimal_places=10, null=True, blank=True,
        verbose_name="Rebate Tipo 3 Mínimo",
        help_text="Rebate Wall (%) Tipo 3 Mínimo"
    )
    parametro_loja_27 = models.DecimalField(
        max_digits=12, decimal_places=10, null=True, blank=True,
        verbose_name="Rebate Tipo 3 Negociado",
        help_text="Rebate Wall (%) Tipo 3 Negociado"
    )
    parametro_loja_28 = models.DecimalField(
        max_digits=12, decimal_places=10, null=True, blank=True,
        verbose_name="Rebate Total Mínimo",
        help_text="Rebate Total Mínimo %"
    )
    parametro_loja_29 = models.DecimalField(
        max_digits=12, decimal_places=10, null=True, blank=True,
        verbose_name="Rebate Total Negociado",
        help_text="Rebate Total Negociado %"
    )
    parametro_loja_30 = models.IntegerField(
        null=True, blank=True,
        verbose_name="Dia Pagamento Rebate",
        help_text="Dia mês pagto Rebate Loja"
    )
    
    # Parâmetros uptal (1-6)
    parametro_uptal_1 = models.DecimalField(
        max_digits=12, decimal_places=10, null=True, blank=True,
        verbose_name="MDR Uptal",
        help_text="MDR a Pagar Uptal - %"
    )
    parametro_uptal_2 = models.IntegerField(
        null=True, blank=True,
        verbose_name="Prazo Reembolso Normal",
        help_text="Prazo Reembolso Normal Uptal (dias)"
    )
    parametro_uptal_3 = models.IntegerField(
        null=True, blank=True,
        verbose_name="Prazo Reembolso Antecipado",
        help_text="Prazo Reembolso Antecipado Uptal (dias)"
    )
    parametro_uptal_4 = models.DecimalField(
        max_digits=12, decimal_places=10, null=True, blank=True,
        verbose_name="Taxa Antecipação Uptal Mensal",
        help_text="Taxa Antecipação a Pagar Uptal - % (a.m.)"
    )
    parametro_uptal_5 = models.DecimalField(
        max_digits=12, decimal_places=10, null=True, blank=True,
        verbose_name="Taxa Antecipação Uptal Período",
        help_text="Taxa Antecipação a Pagar Uptal - % (período)"
    )
    parametro_uptal_6 = models.DecimalField(
        max_digits=12, decimal_places=10, null=True, blank=True,
        verbose_name="Alíquota Imposto Wall",
        help_text="Alíquota Imposto a pagar Wall - %"
    )
    
    # Parâmetros wall (1-4)
    parametro_wall_1 = models.DecimalField(
        max_digits=12, decimal_places=10, null=True, blank=True,
        verbose_name="Taxa Serviço Wall",
        help_text="Taxa de Serviço Wall Cobrada Cliente - %"
    )
    parametro_wall_2 = models.DecimalField(
        max_digits=12, decimal_places=10, null=True, blank=True,
        verbose_name="Taxa Risco Fraude",
        help_text="Taxa Risco Fraude Wall Cobrada Cliente - %"
    )
    parametro_wall_3 = models.DecimalField(
        max_digits=12, decimal_places=10, null=True, blank=True,
        verbose_name="Total Taxas Wall",
        help_text="Total Taxa/Tarifas Wall Cobradas Cliente - %"
    )
    parametro_wall_4 = models.DecimalField(
        max_digits=12, decimal_places=10, null=True, blank=True,
        verbose_name="Encargos Financeiros",
        help_text="Encargos Financeiros Oper. Cartão - (% período)"
    )
    
    # Campos de auditoria
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    criado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="parametroswall_criado_set"
    )
    atualizado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="parametroswall_atualizado_set"
    )
    
    class Meta:
        db_table = 'parametros_wallclub'
        ordering = ['-vigencia_inicio']
        verbose_name = 'Parâmetros Wall'
        verbose_name_plural = 'Parâmetros Wall'
        indexes = [
            models.Index(fields=['loja_id', 'vigencia_inicio']),
            models.Index(fields=['id_plano']),
            models.Index(fields=['wall']),
            models.Index(fields=['vigencia_inicio']),
        ]
        
    def __str__(self):
        return f"Parâmetros Loja {self.loja_id} - Plano {self.id_plano} - {self.vigencia_inicio}"
    
    def get_parametro(self, codigo):
        """
        Busca um parâmetro pelo código (1-40).
        
        Args:
            codigo (int): Código do parâmetro (1-40)
            
        Returns:
            str: Valor do parâmetro ou None se não encontrado
        """
        if 1 <= codigo <= 30:
            # Parâmetros da loja (1-30)
            return getattr(self, f'parametro_loja_{codigo}', None)
        elif 31 <= codigo <= 36:
            # Parâmetros uptal (31-36)
            uptal_num = codigo - 30
            return getattr(self, f'parametro_uptal_{uptal_num}', None)
        elif 37 <= codigo <= 40:
            # Parâmetros wall (37-40)
            wall_num = codigo - 36
            return getattr(self, f'parametro_wall_{wall_num}', None)
        return None
    
    @classmethod
    def get_configuracao_ativa(cls, loja_id: int, data_referencia=None):
        """
        Busca configuração ativa para uma loja em uma data específica.
        
        Args:
            loja_id (int): ID da loja
            data_referencia (datetime, optional): Data de referência. Default: agora
            
        Returns:
            ParametrosWall: Configuração ativa ou None
        """
        if data_referencia is None:
            from datetime import datetime
            data_referencia = datetime.now()
            
        return cls.objects.filter(
            loja_id=loja_id,
            vigencia_inicio__lte=data_referencia
        ).filter(
            models.Q(vigencia_fim__isnull=True) | 
            models.Q(vigencia_fim__gte=data_referencia)
        ).first()

class Plano(models.Model):
    """
    Planos de pagamento como tabela de lookup simples.
    
    ESTRUTURA FINAL:
    - id: IDs 1-306 (apenas planos únicos)
    - Dados básicos: nome, prazo, bandeira
    - IDs originais mantidos para validação (TEMPORÁRIOS)
    - Mapeamento: parâmetros Wall (1-306) → busca direta
    - Mapeamento: parâmetros Sem Wall (1000+) → busca (id_plano - 999)
    """
    
    # ID 1-306 (planos únicos)
    id = models.IntegerField(primary_key=True)
    
    # IDs originais para validação (TEMPORÁRIOS - remover após validação)
    id_original_wall = models.IntegerField(
        verbose_name="ID Original (Wall)",
        help_text="ID original da tabela 'planos' - para validação",
        null=True,
        blank=True
    )
    
    id_original_sem_wall = models.IntegerField(
        verbose_name="ID Original (Sem Wall)", 
        help_text="ID original da tabela 'planos_sem_club' - para validação",
        null=True,
        blank=True
    )
    
    # Dados do plano
    nome = models.CharField(
        max_length=256,
        verbose_name="Nome do Plano",
        help_text="Descrição do plano (ex: PIX, A VISTA, PARCELADO SEM JUROS)"
    )
    
    prazo_dias = models.IntegerField(
        verbose_name="Prazo em Dias",
        help_text="Número de parcelas (0 para à vista/PIX)"
    )
    
    bandeira = models.CharField(
        max_length=256,
        verbose_name="Bandeira",
        help_text="Bandeira do cartão (MASTERCARD, VISA, PIX, etc.)"
    )
    
    # Campo wall removido - diferenciação ocorre nos parâmetros através do id_plano
    
    # Auditoria
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'parametros_wallclub_planos'
        verbose_name = 'Plano WallClub'
        verbose_name_plural = 'Planos WallClub'
        
        # Índices para performance
        indexes = [
            models.Index(fields=['bandeira'], name='idx_plano_bandeira'),
            models.Index(fields=['prazo_dias'], name='idx_plano_prazo'),
            models.Index(fields=['id_original_wall'], name='idx_plano_orig_wall'),
            models.Index(fields=['id_original_sem_wall'], name='idx_plano_orig_sem'),
        ]
        
    
    def __str__(self):
        return f"{self.nome} {self.prazo_dias}x {self.bandeira}"
    
    @classmethod
    def buscar_por_id_parametro(cls, id_plano):
        """
        Busca plano mapeando IDs de parâmetros para IDs de planos.
        - Wall (1-306): busca direta
        - Sem Wall (1000+): mapeia para (id_plano - 999)
        """
        if id_plano >= 1000:
            # Parâmetros Sem Wall: mapear 1000+ para 1-306
            id_lookup = id_plano - 999
        else:
            # Parâmetros Wall: busca direta
            id_lookup = id_plano
        
        return cls.objects.filter(id=id_lookup).first()

# ESTRUTURA LIMPA - MODELO UNIFICADO ParametrosWall
# Todas as configurações são armazenadas na tabela parametros_wallclub


class ImportacaoConfiguracoes(models.Model):
    """
    Controle de importações via planilha ou migração.
    
    RASTREABILIDADE: Cada importação é registrada para auditoria.
    """
    
    # Campos que correspondem à estrutura real da tabela no banco
    nome_arquivo = models.CharField(
        max_length=255,
        help_text="Nome do arquivo importado"
    )
    tamanho_arquivo = models.BigIntegerField(
        help_text="Tamanho do arquivo em bytes"
    )
    data_vigencia = models.DateField(
        help_text="Data de vigência dos parâmetros importados"
    )
    usuario_id = models.BigIntegerField(
        help_text="ID do usuário que fez a importação"
    )
    data_importacao = models.DateTimeField(
        auto_now_add=True,
        help_text="Data e hora da importação"
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('PROCESSANDO', 'Processando'),
            ('SUCESSO', 'Sucesso'),
            ('ERRO', 'Erro'),
        ],
        default='PROCESSANDO'
    )
    linhas_processadas = models.IntegerField(
        default=0,
        null=True, blank=True,
        help_text="Total de linhas processadas"
    )
    linhas_importadas = models.IntegerField(
        default=0,
        null=True, blank=True,
        help_text="Linhas importadas com sucesso"
    )
    linhas_erro = models.IntegerField(
        default=0,
        null=True, blank=True,
        help_text="Linhas com erro"
    )
    mensagem_erro = models.TextField(
        null=True, blank=True,
        help_text="Mensagem de erro detalhada"
    )
    arquivo_path = models.CharField(
        max_length=500,
        null=True, blank=True,
        help_text="Caminho do arquivo no servidor"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Data de criação do registro"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Data de última atualização"
    )
    
    class Meta:
        db_table = 'parametros_wallclub_importacoes'
        verbose_name = 'Importação Parâmetros WallClub'
        verbose_name_plural = 'Importações Parâmetros WallClub'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.nome_arquivo} - {self.status}"
