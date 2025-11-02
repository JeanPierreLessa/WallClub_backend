"""
Funções gerais importadas do sistema PHP original
"""
import math
from datetime import datetime, timedelta


def calcular_juros_compostos(i, P, V, n):
    """
    Calcula a diferença entre parcela informada e parcela calculada com juros compostos
    
    Args:
        i (float): Taxa de juros por período
        P (float): Valor da parcela informada
        V (float): Valor original do financiamento
        n (int): Número de parcelas
        
    Returns:
        float: Diferença entre parcela informada e calculada
    """
    # Converter todos os valores para float para evitar TypeError com Decimal
    i = float(i)
    P = float(P)
    V = float(V)
    n = int(n)
    
    if i == 0:
        return P - V / n  # Quando i = 0, assumimos juros zero (amortização simples)
    
    # Fórmula para calcular com juros compostos
    return P - V * (i * pow(1 + i, n)) / (pow(1 + i, n) - 1)


def calcular_cet(P, V, n, precisao=1e-8, limite_inferior=0, limite_superior=10):
    """
    Calcula o Custo Efetivo Total (CET) usando método da bisseção
    
    Args:
        P (float): Valor da parcela
        V (float): Valor original
        n (int): Número de parcelas
        precisao (float): Precisão do cálculo
        limite_inferior (float): Limite inferior para busca
        limite_superior (float): Limite superior para busca
        
    Returns:
        float: CET calculado em percentual ou None se não encontrar solução
    """
    # Verificar se algum valor é None e retornar 0.0
    if P is None or V is None or n is None:
        return 0.0
    
    # Converter todos os valores para float para evitar TypeError com Decimal
    try:
        P = float(P)
        V = float(V)
        n = int(n)
    except (ValueError, TypeError):
        return 0.0
    
    # Verificar se valores são válidos para cálculo
    if P <= 0 or V <= 0 or n <= 0:
        return 0.0
    
    a = limite_inferior
    b = limite_superior

    # Verificar se há uma solução válida entre os limites fornecidos
    if calcular_juros_compostos(a, P, V, n) * calcular_juros_compostos(b, P, V, n) >= 0:
        return None  # Solução não existe ou limites estão incorretos

    # Método da bisseção
    while (b - a) / 2 > precisao:
        c = (a + b) / 2  # Ponto médio

        if abs(calcular_juros_compostos(c, P, V, n)) < precisao:
            return c  # Solução encontrada

        # Atualizar o intervalo com base no sinal da função
        if calcular_juros_compostos(c, P, V, n) * calcular_juros_compostos(a, P, V, n) < 0:
            b = c  # A solução está entre a e c
        else:
            a = c  # A solução está entre c e b

    return round(((a + b) / 2) * 100, 2)


def formatar_valor_brasileiro(valor) -> str:
    """
    Formata valor no padrão brasileiro (R$ 1.234,56)
    """
    try:
        from decimal import Decimal
        
        # Se já está formatado como R$, retornar como está
        if isinstance(valor, str) and valor.startswith('R$'):
            return valor
        
        # Limpar formatação se for string
        if isinstance(valor, str):
            valor = valor.replace('R$', '').replace(' ', '').strip()
            # Tratar formato brasileiro: 5,28 -> 5.28
            if ',' in valor and '.' not in valor:
                valor = valor.replace(',', '.')
            elif ',' in valor and '.' in valor:
                # Formato com milhares: 1.234,56 -> 1234.56
                if valor.rfind(',') > valor.rfind('.'):
                    valor = valor.replace('.', '').replace(',', '.')
                else:
                    valor = valor.replace(',', '')
        
        # Converter para Decimal
        if not isinstance(valor, Decimal):
            valor = Decimal(str(valor))
            
        valor_str = f"{valor:.2f}".replace('.', ',')
        # Adicionar pontos para milhares
        partes = valor_str.split(',')
        inteira = partes[0]
        decimal = partes[1] if len(partes) > 1 else '00'
        
        # Adicionar pontos a cada 3 dígitos
        if len(inteira) > 3:
            inteira_formatada = ''
            for i, digito in enumerate(reversed(inteira)):
                if i > 0 and i % 3 == 0:
                    inteira_formatada = '.' + inteira_formatada
                inteira_formatada = digito + inteira_formatada
            inteira = inteira_formatada
        
        return f"R$ {inteira},{decimal}"
        
    except Exception as e:
        from wallclub_core.utilitarios.log_control import registrar_log
        registrar_log('comum.utilitarios', f'Erro ao formatar valor: {str(e)}', nivel='ERROR')
        return f"R$ {valor:.2f}"


def proxima_sexta_feira(data_str):
    """
    Encontra a próxima sexta-feira a partir de uma data
    
    Args:
        data_str (str): Data no formato 'dd/mm/yyyy'
        
    Returns:
        str: Data da próxima sexta-feira no formato 'dd/mm/yyyy'
    """
    # Converter a data de entrada para um objeto datetime
    data_obj = datetime.strptime(data_str, '%d/%m/%Y')

    # Encontrar o próximo dia que é sexta-feira
    # weekday() retorna 0=segunda, 1=terça, ..., 4=sexta, 5=sábado, 6=domingo
    while data_obj.weekday() != 4:  # 4 = sexta-feira
        data_obj += timedelta(days=1)

    # Retornar a data da próxima sexta-feira no formato dd/mm/yyyy
    return data_obj.strftime('%d/%m/%Y')


def proximo_dia_util(data_str):
    """
    Encontra o próximo dia útil (segunda a sexta) a partir de uma data
    
    Args:
        data_str (str): Data no formato 'dd/mm/yyyy'
        
    Returns:
        str: Data do próximo dia útil no formato 'dd/mm/yyyy'
    """
    # Converter a data de entrada para um objeto datetime
    data_obj = datetime.strptime(data_str, '%d/%m/%Y')
    
    # Avançar 1 dia
    data_obj += timedelta(days=1)
    
    # Pular finais de semana (sábado=5, domingo=6)
    while data_obj.weekday() >= 5:
        data_obj += timedelta(days=1)
    
    # Retornar o próximo dia útil no formato dd/mm/yyyy
    return data_obj.strftime('%d/%m/%Y')
