"""
Serviço de validação de CPF
- Validação de dígitos verificadores (algoritmo mod-11)
- Blacklist de CPFs bloqueados
- Cache Redis (24h)
"""
from django.core.cache import cache
from django.db import connection
from wallclub_core.utilitarios.log_control import registrar_log


class ValidadorCPFService:
    """Validador completo de CPF com blacklist e cache"""

    # CPFs conhecidos como inválidos (sequências repetidas)
    CPFS_INVALIDOS = [
        '00000000000', '11111111111', '22222222222', '33333333333',
        '44444444444', '55555555555', '66666666666', '77777777777',
        '88888888888', '99999999999', '12345678909'
    ]

    @staticmethod
    def validar_formato(cpf: str) -> tuple[bool, str]:
        """
        Valida formato básico do CPF

        Args:
            cpf: CPF a ser validado (com ou sem formatação)

        Returns:
            tuple: (valido: bool, motivo: str)
        """
        # Limpar CPF (apenas números)
        cpf_limpo = ''.join(filter(str.isdigit, cpf))

        # Verificar tamanho
        if len(cpf_limpo) != 11:
            return False, f"CPF deve ter 11 dígitos (recebido: {len(cpf_limpo)})"

        # Verificar sequências repetidas
        if cpf_limpo in ValidadorCPFService.CPFS_INVALIDOS:
            return False, "CPF inválido (sequência repetida)"

        return True, "Formato válido"

    @staticmethod
    def validar_digitos_verificadores(cpf: str) -> tuple[bool, str]:
        """
        Valida dígitos verificadores do CPF usando algoritmo mod-11

        Args:
            cpf: CPF limpo (11 dígitos)

        Returns:
            tuple: (valido: bool, motivo: str)
        """
        # Validar formato primeiro
        valido_formato, motivo_formato = ValidadorCPFService.validar_formato(cpf)
        if not valido_formato:
            return False, motivo_formato

        cpf_limpo = ''.join(filter(str.isdigit, cpf))

        # Calcular primeiro dígito verificador
        soma = 0
        for i in range(9):
            soma += int(cpf_limpo[i]) * (10 - i)

        resto = soma % 11
        digito1 = 0 if resto < 2 else 11 - resto

        if digito1 != int(cpf_limpo[9]):
            return False, "Primeiro dígito verificador inválido"

        # Calcular segundo dígito verificador
        soma = 0
        for i in range(10):
            soma += int(cpf_limpo[i]) * (11 - i)

        resto = soma % 11
        digito2 = 0 if resto < 2 else 11 - resto

        if digito2 != int(cpf_limpo[10]):
            return False, "Segundo dígito verificador inválido"

        return True, "Dígitos verificadores válidos"

    @staticmethod
    def verificar_blacklist(cpf: str) -> tuple[bool, str]:
        """
        Verifica se CPF está na blacklist

        Args:
            cpf: CPF limpo (11 dígitos)

        Returns:
            tuple: (bloqueado: bool, motivo: str)
        """
        cpf_limpo = ''.join(filter(str.isdigit, cpf))

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT motivo FROM blacklist_cpf WHERE cpf = %s AND ativo = 1",
                    [cpf_limpo]
                )
                resultado = cursor.fetchone()

                if resultado:
                    motivo = resultado[0] or "CPF bloqueado"
                    registrar_log('comum.seguranca',
                                f"CPF bloqueado detectado: {cpf_limpo[:3]}***{cpf_limpo[-2:]} - {motivo}",
                                nivel='WARNING')
                    return True, motivo

                return False, "CPF não está na blacklist"

        except Exception as e:
            registrar_log('comum.seguranca',
                        f"Erro ao verificar blacklist: {str(e)}",
                        nivel='ERROR')
            # Em caso de erro, permitir (fail-open para não bloquear operação)
            return False, "Erro ao verificar blacklist (permitido)"

    @staticmethod
    def validar_cpf_completo(cpf: str, usar_cache: bool = True) -> dict:
        """
        Validação completa de CPF com cache Redis

        Validações:
        1. Formato (11 dígitos)
        2. Dígitos verificadores (algoritmo mod-11)
        3. Blacklist
        4. Cache (24h)

        Args:
            cpf: CPF a ser validado (com ou sem formatação)
            usar_cache: Se deve usar cache Redis (padrão: True)

        Returns:
            dict: {
                "valido": bool,
                "motivo": str,
                "cpf_limpo": str,
                "cache_hit": bool
            }
        """
        # Limpar CPF
        cpf_limpo = ''.join(filter(str.isdigit, cpf))

        # Verificar cache se habilitado
        if usar_cache:
            cache_key = f"cpf_validacao:{cpf_limpo}"
            resultado_cache = cache.get(cache_key)

            if resultado_cache:
                resultado_cache['cache_hit'] = True
                registrar_log('comum.seguranca',
                            f"Validação CPF (cache hit): {cpf_limpo[:3]}***{cpf_limpo[-2:]}",
                            nivel='DEBUG')
                return resultado_cache

        # 1. Validar formato
        valido_formato, motivo_formato = ValidadorCPFService.validar_formato(cpf_limpo)
        if not valido_formato:
            resultado = {
                "valido": False,
                "motivo": motivo_formato,
                "cpf_limpo": cpf_limpo,
                "cache_hit": False
            }
            return resultado

        # 2. Validar dígitos verificadores
        valido_digitos, motivo_digitos = ValidadorCPFService.validar_digitos_verificadores(cpf_limpo)
        if not valido_digitos:
            resultado = {
                "valido": False,
                "motivo": motivo_digitos,
                "cpf_limpo": cpf_limpo,
                "cache_hit": False
            }
            return resultado

        # 3. Verificar blacklist
        bloqueado, motivo_bloqueio = ValidadorCPFService.verificar_blacklist(cpf_limpo)
        if bloqueado:
            resultado = {
                "valido": False,
                "motivo": f"CPF bloqueado: {motivo_bloqueio}",
                "cpf_limpo": cpf_limpo,
                "cache_hit": False
            }
            return resultado

        # CPF válido
        resultado = {
            "valido": True,
            "motivo": "CPF válido",
            "cpf_limpo": cpf_limpo,
            "cache_hit": False
        }

        # Salvar no cache (24 horas) se habilitado
        if usar_cache:
            cache_key = f"cpf_validacao:{cpf_limpo}"
            cache.set(cache_key, resultado, 86400)  # 24 horas
            registrar_log('comum.seguranca',
                        f"Validação CPF completa (cache miss): {cpf_limpo[:3]}***{cpf_limpo[-2:]}",
                        nivel='DEBUG')

        return resultado

    @staticmethod
    def limpar_cache_cpf(cpf: str) -> bool:
        """
        Remove CPF do cache (útil após adicionar à blacklist)

        Args:
            cpf: CPF a ser removido do cache

        Returns:
            bool: True se removido com sucesso
        """
        cpf_limpo = ''.join(filter(str.isdigit, cpf))
        cache_key = f"cpf_validacao:{cpf_limpo}"

        try:
            cache.delete(cache_key)
            registrar_log('comum.seguranca',
                        f"Cache CPF removido: {cpf_limpo[:3]}***{cpf_limpo[-2:]}",
                        nivel='INFO')
            return True
        except Exception as e:
            registrar_log('comum.seguranca',
                        f"Erro ao remover cache CPF: {str(e)}",
                        nivel='ERROR')
            return False
