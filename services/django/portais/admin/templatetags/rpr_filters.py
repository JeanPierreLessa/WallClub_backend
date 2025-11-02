from django import template
from decimal import Decimal
import locale

register = template.Library()

@register.filter
def add_thousands_separator(value):
    """
    Adiciona separador de milhares aos valores monetários.
    Exemplo: 1415456.22 -> 1.415.456,22
    """
    if value is None:
        return '0,00'
    
    try:
        # Converter para float se for string ou Decimal
        if isinstance(value, str):
            value = float(value.replace(',', '.'))
        elif isinstance(value, Decimal):
            value = float(value)
        
        # Formatar com separador de milhares brasileiro
        # Usar formatação manual para garantir padrão brasileiro
        formatted = f"{value:,.2f}"
        
        # Converter formato americano (1,234.56) para brasileiro (1.234,56)
        formatted = formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
        
        return formatted
        
    except (ValueError, TypeError):
        return str(value)
