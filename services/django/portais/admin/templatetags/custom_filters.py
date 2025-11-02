from django import template
from datetime import datetime

register = template.Library()

@register.filter
def timestamp_to_date(timestamp):
    """Converte timestamp para formato Y-m-d"""
    if timestamp:
        try:
            return datetime.fromtimestamp(int(timestamp)).strftime('%Y-%m-%d')
        except (ValueError, TypeError):
            return ''
    return ''

@register.filter
def timestamp_to_display(timestamp):
    """Converte timestamp para formato DD/MM/YY HH24:MI"""
    if timestamp:
        try:
            return datetime.fromtimestamp(int(timestamp)).strftime('%d/%m/%y %H:%M')
        except (ValueError, TypeError):
            return '-'
    return '-'
