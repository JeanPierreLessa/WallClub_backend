from django import template
from datetime import datetime

register = template.Library()

@register.filter
def timestamp_to_date(value):
    """Converte timestamp ou datetime para formato Y-m-d"""
    if value:
        try:
            # Se já é datetime, converter direto
            if isinstance(value, datetime):
                return value.strftime('%Y-%m-%d')
            # Se é timestamp Unix (int), converter
            return datetime.fromtimestamp(int(value)).strftime('%Y-%m-%d')
        except (ValueError, TypeError):
            return ''
    return ''

@register.filter
def timestamp_to_display(value):
    """Converte timestamp ou datetime para formato DD/MM/YY HH24:MI"""
    if value:
        try:
            # Se já é datetime, converter direto
            if isinstance(value, datetime):
                return value.strftime('%d/%m/%y %H:%M')
            # Se é timestamp Unix (int), converter
            return datetime.fromtimestamp(int(value)).strftime('%d/%m/%y %H:%M')
        except (ValueError, TypeError):
            return '-'
    return '-'
