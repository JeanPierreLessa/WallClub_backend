"""
Validador de complexidade de senhas
Critérios: mínimo 8 caracteres, maiúscula, minúscula, número e símbolo
"""
import re


def validar_complexidade_senha(senha):
    """
    Valida se a senha atende aos critérios de complexidade
    
    Critérios:
    - Mínimo 8 caracteres
    - Pelo menos 1 letra maiúscula
    - Pelo menos 1 letra minúscula  
    - Pelo menos 1 número
    - Pelo menos 1 símbolo (!@#$%^&*()_+-=[]{}|;:,.<>?)
    
    Args:
        senha (str): Senha a ser validada
        
    Returns:
        tuple: (bool, str) - (é_válida, mensagem_erro)
    """
    if not senha:
        return False, "Senha é obrigatória."
    
    # Verificar comprimento mínimo
    if len(senha) < 8:
        return False, "A senha deve ter pelo menos 8 caracteres."
    
    # Verificar letra maiúscula
    if not re.search(r'[A-Z]', senha):
        return False, "A senha deve conter pelo menos uma letra maiúscula."
    
    # Verificar letra minúscula
    if not re.search(r'[a-z]', senha):
        return False, "A senha deve conter pelo menos uma letra minúscula."
    
    # Verificar número
    if not re.search(r'[0-9]', senha):
        return False, "A senha deve conter pelo menos um número."
    
    # Verificar símbolo
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', senha):
        return False, "A senha deve conter pelo menos um símbolo (!@#$%^&*()_+-=[]{}|;:,.<>?)."
    
    return True, "Senha válida."


def obter_criterios_senha():
    """
    Retorna string com os critérios de senha para exibição ao usuário
    
    Returns:
        str: Texto com os critérios
    """
    return (
        "A senha deve conter:\n"
        "• Mínimo 8 caracteres\n"
        "• Pelo menos 1 letra maiúscula\n"
        "• Pelo menos 1 letra minúscula\n"
        "• Pelo menos 1 número\n"
        "• Pelo menos 1 símbolo (!@#$%^&*()_+-=[]{}|;:,.<>?)"
    )
