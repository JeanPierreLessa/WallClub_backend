from django import template
from django.utils.safestring import mark_safe
import json

register = template.Library()

@register.filter
def format_currency(value):
    """Formata valor como moeda brasileira com separador de milhares"""
    try:
        if value is None or value == '':
            return "0,00"
        
        # Converter para float se for string
        if isinstance(value, str):
            value = float(value)
        
        # Formatar com separador de milhares
        formatted = f"{value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        return formatted
    except (ValueError, TypeError):
        return "0,00"

@register.filter
def format_number(value):
    """Formata número inteiro com separador de milhares"""
    try:
        if value is None or value == '':
            return "0"
        
        # Converter para int se for string
        if isinstance(value, str):
            value = int(float(value))
        
        # Formatar com separador de milhares
        return f"{value:,}".replace(',', '.')
    except (ValueError, TypeError):
        return "0"

@register.filter
def to_json_safe(value):
    """Converte valor para JSON de forma segura para uso em JavaScript"""
    return mark_safe(json.dumps(value))
