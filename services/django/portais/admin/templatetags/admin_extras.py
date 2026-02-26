from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def lookup(dictionary, key):
    """Template filter para acessar valores de dicionário dinamicamente"""
    if isinstance(dictionary, dict):
        return dictionary.get(key, '')
    return getattr(dictionary, key, '')

@register.filter
def moeda(value):
    """Formata valor como moeda brasileira"""
    if value is None or value == '':
        return '-'
    try:
        valor_decimal = Decimal(str(value))
        return f"R$ {valor_decimal:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except (ValueError, TypeError, Exception):
        return '-'

@register.filter
def percentual(value):
    """Formata valor como percentual"""
    if value is None or value == '':
        return '-'
    try:
        valor_decimal = Decimal(str(value))
        percentual_formatado = f"{(valor_decimal * 100):.2f}%".replace('.', ',')
        return percentual_formatado
    except (ValueError, TypeError, Exception):
        return '-'
