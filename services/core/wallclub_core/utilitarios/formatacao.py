"""
Utilitários para formatação de valores monetários e percentuais.
Implementa as diretrizes do projeto para padronização de formatos.
"""
from decimal import Decimal
import re


def formatar_valor_monetario(valor, incluir_simbolo=True):
    """
    Formata valor monetário no padrão brasileiro.

    Args:
        valor: Decimal, float ou string com o valor
        incluir_simbolo: Se deve incluir 'R$ ' no início

    Returns:
        String formatada (ex: "R$ 1.234,56" ou "1.234,56")
    """
    if valor is None or valor == '':
        return "R$ 0,00" if incluir_simbolo else "0,00"

    try:
        # Converter para Decimal se necessário
        if isinstance(valor, str):
            # Remover caracteres não numéricos exceto vírgula e ponto
            valor_limpo = re.sub(r'[^\d,.-]', '', valor)

            # Se ficou vazio após limpeza, retornar 0
            if not valor_limpo or valor_limpo in ['-', '.', ',']:
                return "R$ 0,00" if incluir_simbolo else "0,00"

            # Converter vírgula para ponto se necessário
            if ',' in valor_limpo and '.' not in valor_limpo:
                valor_limpo = valor_limpo.replace(',', '.')
            elif ',' in valor_limpo and '.' in valor_limpo:
                # Formato brasileiro: 1.234,56 -> 1234.56
                valor_limpo = valor_limpo.replace('.', '').replace(',', '.')
            valor = Decimal(valor_limpo)
        elif isinstance(valor, (int, float)):
            valor = Decimal(str(valor))
        else:
            # Tipo não suportado
            return "R$ 0,00" if incluir_simbolo else "0,00"
    except (ValueError, TypeError, Exception):
        # Se houver qualquer erro na conversão, retornar 0
        return "R$ 0,00" if incluir_simbolo else "0,00"

    # Formatar com separador de milhares (ponto) e decimais (vírgula)
    valor_str = f"{valor:.2f}"
    partes = valor_str.split('.')
    inteira = partes[0]
    decimal = partes[1]

    # Separar sinal negativo se existir
    sinal = ""
    if inteira.startswith('-'):
        sinal = "-"
        inteira = inteira[1:]

    # Adicionar separador de milhares
    if len(inteira) > 3:
        inteira_formatada = ""
        for i, digito in enumerate(reversed(inteira)):
            if i > 0 and i % 3 == 0:
                inteira_formatada = "." + inteira_formatada
            inteira_formatada = digito + inteira_formatada
        inteira = inteira_formatada

    valor_formatado = f"{sinal}{inteira},{decimal}"

    if incluir_simbolo:
        return f"R$ {valor_formatado}"
    return valor_formatado


def formatar_percentual(valor, casas_decimais=2):
    """
    Formata valor percentual multiplicando por 100 e adicionando %.

    Args:
        valor: Decimal, float ou string com o valor (ex: 0.15 -> 15,00%)
        casas_decimais: Número de casas decimais

    Returns:
        String formatada (ex: "15,00%")
    """
    if valor is None or valor == '':
        return "0,00%"

    try:
        # Converter para Decimal se necessário
        if isinstance(valor, str):
            valor_limpo = re.sub(r'[^\d,.-]', '', valor)

            # Se ficou vazio após limpeza ou apenas símbolos, retornar 0
            if not valor_limpo or valor_limpo in ['-', '.', ',', '-.', '-,']:
                return "0,00%"

            if ',' in valor_limpo:
                valor_limpo = valor_limpo.replace(',', '.')
            valor = Decimal(valor_limpo)
        elif isinstance(valor, (int, float)):
            valor = Decimal(str(valor))
        elif isinstance(valor, Decimal):
            # Já é Decimal
            pass
        else:
            # Tipo não suportado
            return "0,00%"
    except (ValueError, TypeError, Exception):
        # Se houver qualquer erro na conversão, retornar 0
        return "0,00%"

    # Multiplicar por 100 para percentual
    percentual = valor * 100

    # Formatar com casas decimais
    formato = f"{{:.{casas_decimais}f}}"
    valor_str = formato.format(percentual)

    # Trocar ponto por vírgula
    valor_formatado = valor_str.replace('.', ',')

    return f"{valor_formatado}%"


def converter_valor_brasileiro_para_decimal(valor_str):
    """
    Converte string no formato brasileiro para Decimal.

    Args:
        valor_str: String no formato "1.234,56" ou "R$ 1.234,56"

    Returns:
        Decimal
    """
    if not valor_str:
        return Decimal('0')

    # Remover símbolos monetários e espaços
    valor_limpo = re.sub(r'[R$\s]', '', str(valor_str))

    # Se contém vírgula e ponto, assumir formato brasileiro
    if ',' in valor_limpo and '.' in valor_limpo:
        # Remover pontos (separador de milhares) e trocar vírgula por ponto
        valor_limpo = valor_limpo.replace('.', '').replace(',', '.')
    elif ',' in valor_limpo:
        # Apenas vírgula, trocar por ponto
        valor_limpo = valor_limpo.replace(',', '.')

    return Decimal(valor_limpo)


def validar_formato_monetario(valor_str):
    """
    Valida se string está no formato monetário brasileiro válido.

    Args:
        valor_str: String a ser validada

    Returns:
        bool: True se válido
    """
    if not valor_str:
        return False

    # Padrão para formato brasileiro: opcional R$, números com pontos como separador de milhares e vírgula como decimal
    padrao = r'^(R\$\s?)?(\d{1,3}(\.\d{3})*),\d{2}$|^(R\$\s?)?\d+,\d{2}$|^(R\$\s?)?\d+$'

    return bool(re.match(padrao, valor_str.strip()))
