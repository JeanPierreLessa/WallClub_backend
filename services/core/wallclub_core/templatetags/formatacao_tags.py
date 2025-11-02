"""
Template tags para formatação de valores monetários e percentuais.
Implementa as diretrizes do projeto para padronização de formatos.
"""
from django import template
from wallclub_core.utilitarios.formatacao import formatar_valor_monetario, formatar_percentual

register = template.Library()


@register.filter
def moeda(valor, incluir_simbolo=True):
    """
    Formata valor como moeda brasileira.
    
    Uso: {{ valor|moeda }} ou {{ valor|moeda:False }}
    """
    return formatar_valor_monetario(valor, incluir_simbolo)


@register.filter
def percentual(valor, casas_decimais=2):
    """
    Formata valor como percentual brasileiro.
    
    Uso: {{ valor|percentual }} ou {{ valor|percentual:1 }}
    """
    return formatar_percentual(valor, casas_decimais)


@register.filter
def moeda_sem_simbolo(valor):
    """
    Formata valor como moeda brasileira sem o símbolo R$.
    
    Uso: {{ valor|moeda_sem_simbolo }}
    """
    return formatar_valor_monetario(valor, incluir_simbolo=False)
