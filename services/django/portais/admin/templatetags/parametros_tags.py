"""
Template tags personalizados para parâmetros WallClub.
"""

from django import template

register = template.Library()


@register.filter
def get_param(config, param_num):
    """
    Retorna o valor de um parâmetro específico da configuração.
    
    Usage: {{ config|get_param:5 }}
    """
    try:
        param_num = int(param_num)
        
        # Mapear para os nomes corretos dos campos
        if 1 <= param_num <= 34:
            field_name = f'parametro_loja_{param_num}'
        elif 35 <= param_num <= 40:
            field_name = f'parametro_uptal_{param_num - 34}'
        elif 41 <= param_num <= 44:
            field_name = f'parametro_wall_{param_num - 40}'
        else:
            return 0.0
            
        value = getattr(config, field_name, 0.0)
        return value if value is not None else 0.0
    except (ValueError, AttributeError):
        return 0.0


@register.filter
def format_decimal(value):
    """
    Formata um valor decimal para exibição.
    
    Usage: {{ value|format_decimal }}
    """
    try:
        if value is None:
            return "0,00"
        return f"{float(value):.2f}".replace('.', ',')
    except (ValueError, TypeError):
        return "0,00"


@register.filter
def get_param_name(param_num):
    """
    Retorna o nome descritivo de um parâmetro.
    
    Usage: {{ param_num|get_param_name }}
    """
    param_names = {
        # Parâmetros de Loja (1-34)
        1: "Prazo Máximo de nº parcelas Loja",
        2: "MDR Oper. Normal (%)",
        3: "Taxa Antecip. Oper Normal (% a.m.)",
        4: "Taxa Antecip. Oper Normal (% período)",
        5: "Taxa Retenção Total Normal (% período)",
        6: "Prazo de Reembolso (em dias corridos a partir da data da compra)",
        7: "Desconto Cliente à VistaWall Negociado (na Nota Fiscal) - %",
        8: "Desconto Cliente à VistaWall Sugerido (na Nota Fiscal) - %",
        9: "Desconto Cliente à Vista Sugerido -por Prazo Máximo - %",
        10: "Desconto Cliente Parcelado Wall (Vlr Operação) - %",
        11: "Desconto Pagto a Vista - Pix c/ Tarifas Wall - %",
        12: "MDR Pago Wall - %",
        13: "Taxa Antecipação Paga Wall - % (a.m.)",
        14: "Taxa Antecipação Paga Wall - % (Periodo)",
        15: "Taxa Retenção Total c/Wall (% período)",
        16: "Regime Tributação (MEI, Simples, Presumido, Real)",
        17: "Alíquiota Imposto - %",
        18: "Prazo Repasse Wall p/ Loja (nº dias)",
        19: "Divisão Ganho Redução Impostos Loja (% Alvo)",
        20: "Divisão resultado Wall (% Loja)",
        21: "Divisão Ganho tributario (% Loja)",
        22: "Rebate Wall (%) Tipo 1 Mínimo",
        23: "Rebate Wall (%) Tipo 1 Negociado",
        24: "Rebate Wall (%) Tipo 2 Mínimo",
        25: "Rebate Wall (%) Tipo 2 Negociado",
        26: "Rebate Wall (%) Tipo 3 Mínimo",
        27: "Rebate Wall (%) Tipo 3 Negociado",
        28: "Rebate Total Mínimo %",
        29: "Rebate Total Negociado %",
        30: "Dia mês pagto Rebate Loja",
        31: "MDR a Pagar Uptal - %",
        32: "Prazo Reembolso Normal Uptal (dias)",
        33: "Prazo Reembolso Antecipado Uptal (dias)",
        34: "Taxa Antecipação a Pagar Uptal - % (a.m.)",
        
        # Parâmetros Uptal (35-40)
        35: "Taxa Antecipação a Pagar Uptal - % (período)",
        36: "Alíquiota Imposto a pagar Wall - %",
        37: "Taxa de Serviço Wall Cobrada Cliente - %",
        38: "Taxa Risco Fraude Wall Cobrada Cliente - %",
        39: "Total Taxa/Tarifas Wall Cobradas Cliente - %",
        40: "Encargos Financeiros Oper. Cartão - (% período)",
        
        # Parâmetros Wall (41-44)
        41: "Parâmetro Wall 1",
        42: "Parâmetro Wall 2",
        43: "Parâmetro Wall 3",
        44: "Parâmetro Wall 4",
    }
    
    try:
        param_num = int(param_num)
        return param_names.get(param_num, f"Parâmetro {param_num}")
    except (ValueError, TypeError):
        return "Parâmetro Desconhecido"


@register.filter
def get_param_group(param_num):
    """
    Retorna o grupo de um parâmetro (Loja, Wall, ClientesF).
    
    Usage: {{ param_num|get_param_group }}
    """
    try:
        param_num = int(param_num)
        if 1 <= param_num <= 34:
            return "Loja"
        elif 35 <= param_num <= 40:
            return "Uptal"
        elif 41 <= param_num <= 44:
            return "Wall"
        else:
            return "Desconhecido"
    except (ValueError, TypeError):
        return "Desconhecido"


@register.simple_tag
def param_range(start, end):
    """
    Gera um range de parâmetros para iteração no template.
    
    Usage: {% param_range 1 10 as params %}
    """
    return range(int(start), int(end) + 1)


@register.simple_tag
def get_plano_info(id_plano):
    """
    Busca informações do plano por ID usando consulta SQL direta.
    
    Usage: {% get_plano_info config.id_plano as plano_info %}
    """
    from django.db import connection
    
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT nome, prazo_dias, bandeira FROM parametros_wallclub_planos WHERE id = %s",
                [id_plano]
            )
            row = cursor.fetchone()
            
            if row:
                return {
                    'nome': row[0],
                    'prazo_dias': row[1],
                    'bandeira': row[2]
                }
            return None
    except Exception:
        return None
