from django import template

register = template.Library()

@register.filter
def lookup(dictionary, key):
    """Template filter para acessar valores de dicionário dinamicamente"""
    if isinstance(dictionary, dict):
        return dictionary.get(key, '')
    return getattr(dictionary, key, '')
