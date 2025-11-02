from django import template
from django.utils.formats import number_format
import locale

register = template.Library()

@register.filter
def format_number(value):
    """Formata números inteiros com separador de milhares"""
    try:
        if value is None:
            return "0"
        num = int(float(value))
        return f"{num:,}".replace(",", ".")
    except (ValueError, TypeError):
        return str(value)

@register.filter
def format_currency(value):
    """Formata valores monetários com separador de milhares e decimais"""
    try:
        if value is None:
            return "R$ 0,00"
        num = float(value)
        # Formatar com separador de milhares (ponto) e decimais (vírgula)
        formatted = f"{num:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {formatted}"
    except (ValueError, TypeError):
        return f"R$ {value}"
