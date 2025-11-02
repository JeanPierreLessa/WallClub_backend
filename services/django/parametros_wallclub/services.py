"""
Serviços para cálculo de parâmetros financeiros WallClub
Arquitetura otimizada que substitui a lógica complexa do PHP por calculadoras especializadas

NOVA ESTRUTURA MIGRADA:
- ConfiguracaoVigente: Configurações ativas (vigencia_fim = NULL)
- ConfiguracaoFutura: Configurações agendadas
- Plano: Planos consolidados (Wall + Sem Wall)
- Parâmetros: parametro_loja_*, parametro_uptal_*, parametro_wall_*
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Any, List
from django.utils import timezone
from django.db import connection, models
from parametros_wallclub.models import ParametrosWall, Plano, ImportacaoConfiguracoes
from wallclub_core.database.queries import TransacoesQueries
from datetime import datetime
from wallclub_core.utilitarios.log_control import registrar_log

class ParametrosService:
    """
    Serviço principal para buscar configurações e parâmetros
    Substitui a função retorna_parametro_loja() do PHP usando a nova estrutura migrada
    """

    @staticmethod
    def get_configuracao_ativa(loja_id: int, data_referencia: Optional[timezone.datetime] = None,
                              id_plano: Optional[int] = None, wall: Optional[str] = None) -> Optional[ParametrosWall]:
        """
        Busca a configuração ativa para uma loja em uma data específica

        Args:
            loja_id: ID da loja
            data_referencia: Data de referência (default: agora)
            id_plano: ID do plano (opcional - para busca específica)
            wall: 'S' ou 'N' para Wall (opcional - para busca específica)

        Returns:
            ParametrosWall ou None se não encontrada
        """
        if data_referencia is None:
            from datetime import datetime
            data_referencia = datetime.now()

        try:
            # Se id_plano e wall foram fornecidos, fazer busca específica
            if id_plano is not None and wall is not None:
                return ParametrosWall.objects.filter(
                    loja_id=loja_id,
                    id_plano=id_plano,
                    wall=wall.upper(),
                    vigencia_inicio__lte=data_referencia
                ).filter(
                    models.Q(vigencia_fim__isnull=True) |
                    models.Q(vigencia_fim__gte=data_referencia)
                ).first()
            else:
                # Busca tradicional apenas por loja e data
                return ParametrosWall.get_configuracao_ativa(loja_id, data_referencia)
        except Exception as e:
            registrar_log('parametros_wallclub', f"Erro ao buscar configuração ativa: {e}", nivel='ERROR')
            return None

    @staticmethod
    def get_parametro_por_codigo(config: ParametrosWall, codigo: int) -> Optional[Decimal]:
        """
        Busca um parâmetro específico por código na configuração

        Args:
            config: Configuração da loja
            codigo: Código do parâmetro (1-42)

        Returns:
            Valor do parâmetro ou None se não encontrado
        """
        if not config:
            return None

        # Mapear código para campo do modelo na nova estrutura
        # MAPEAMENTO CORRETO:
        # parametro_loja_{numero} ↔ wclub.parametros_loja (1-30)
        # parametro_uptal_{numero} ↔ wclub.parametros_wall (31-36)
        # parametro_wall_{numero} ↔ wclub.parametros_clientesf (37-40)
        if 1 <= codigo <= 30:
            campo = f'parametro_loja_{codigo}'
        elif 31 <= codigo <= 36:
            campo = f'parametro_uptal_{codigo - 30}'  # 31-36 → uptal_1-6
        elif 37 <= codigo <= 40:
            campo = f'parametro_wall_{codigo - 36}'   # 37-40 → wall_1-4
        else:
            return None

        valor = getattr(config, campo, None)

        # Converter string para Decimal se necessário (exceto parametro_loja_16 que é texto)
        if valor is not None and campo != 'parametro_loja_16':
            try:
                return Decimal(str(valor)) if valor else None
            except (ValueError, TypeError):
                return None

        return valor

    @staticmethod
    def busca_plano(forma: str, parcelas: int, bandeira: str, wall: str = 'S') -> int:
        """
        Busca o ID do plano baseado nos parâmetros da transação

        Args:
            forma: Tipo da transação (PIX, DEBITO, CREDITO, A VISTA, PARCELADO)
            parcelas: Número de parcelas
            bandeira: Bandeira do cartão ou PIX
            wall: Tipo de cliente ('S' para Wall, 'N' para Sem Wall)

        Returns:
            ID consolidado do plano ou 0 se não encontrado
        """
        # Tratamento para PIX
        if bandeira == 'PIX':
            parcelas = 0
            forma = 'PIX'

        # Tratamento para DEBITO
        if forma == 'DEBITO':
            parcelas = 0

        try:
            # Mapear forma para nome correto do plano
            if forma == 'PARCELADO':
                nome_plano = 'PARCELADO SEM JUROS'
            else:
                nome_plano = forma

            plano = Plano.objects.filter(
                nome=nome_plano,
                prazo_dias=parcelas,
                bandeira=bandeira
            ).first()

            if plano:
                registrar_log('parametros_wallclub', f"Plano encontrado: ID={plano.id}, nome={nome_plano}, parcelas={parcelas}, bandeira={bandeira}", nivel='DEBUG')
                return plano.id
            else:
                registrar_log('parametros_wallclub', f"Plano não encontrado: nome={nome_plano}, parcelas={parcelas}, bandeira={bandeira}", nivel='ERROR')
                return 0
        except Exception as e:
            registrar_log('parametros_wallclub', f"Erro ao buscar plano: {e}", nivel='ERROR')
            return 0

    @staticmethod
    def get_all_configuracoes_count() -> int:
        """
        Retorna o total de configurações na base para debug
        """
        try:
            return ConfiguracaoVigente.objects.count()
        except Exception:
            return 0

    @staticmethod
    def converter_para_timestamp(data: str) -> Optional[int]:
        """
        Converte data para timestamp

        Args:
            data: Data no formato 'YYYY-MM-DD', 'YYYY-MM-DDTHH:MM:SS' ou 'YYYY-MM-DDTHH:MM:SS.mmm'

        Returns:
            Timestamp como int ou None se erro
        """
        try:
            # Tentar primeiro formato ISO completo
            if 'T' in data:
                # Tentar com milissegundos primeiro
                if '.' in data:
                    dt = datetime.strptime(data, '%Y-%m-%dT%H:%M:%S.%f')
                else:
                    dt = datetime.strptime(data, '%Y-%m-%dT%H:%M:%S')
            else:
                dt = datetime.strptime(data, '%Y-%m-%d')
            # Usar datetime naive
            dt_naive = dt
            return int(dt_naive.timestamp())
        except ValueError:
            return None

    @staticmethod
    def retornar_parametro_loja(id_loja: int, data_ref: int, id_plano: int,
                               parametro: int, wall: str = 'S') -> Optional[float]:
        """Busca parâmetro da loja (1-30) - wclub.parametros_loja"""
        try:
            # Usar datetime naive
            data_referencia = datetime.fromtimestamp(data_ref)

            # Buscar configuração vigente
            config = ParametrosService.get_configuracao_ativa(
                loja_id=id_loja,
                id_plano=id_plano,
                wall=wall,
                data_referencia=data_referencia
            )

            if config:
                # Buscar o parâmetro específico
                campo_parametro = f'parametro_loja_{parametro}'
                valor = getattr(config, campo_parametro, None)

                return Decimal(str(valor)) if valor is not None else None

            return None

        except Exception as e:
            registrar_log('parametros_wallclub', f"Erro ao buscar parâmetro loja {parametro}: {e}", nivel='ERROR')
            return None

    @staticmethod
    def retornar_parametro_uptal(id_loja: int, data_ref: int, id_plano: int,
                                parametro: int, wall: str) -> Optional[float]:
        """Busca parâmetro uptal (31-36) - wclub.parametros_wall"""
        try:
            # Usar datetime naive
            data_referencia = datetime.fromtimestamp(data_ref)

            # Buscar configuração ativa da loja específica
            config = ParametrosService.get_configuracao_ativa(id_loja, data_referencia, id_plano, wall)

            if config:
                # Mapear parâmetro uptal para campo na estrutura consolidada
                # wclub.parametros_wall → parametro_uptal_{numero}
                campo_parametro = f'parametro_uptal_{parametro}'
                valor = getattr(config, campo_parametro, None)

                return Decimal(str(valor)) if valor is not None else None

            return None

        except Exception as e:
            registrar_log('parametros_wallclub', f"Erro ao buscar parâmetro uptal {parametro}: {e}", nivel='ERROR')
            return None

    @staticmethod
    def retornar_parametro_wall(id_loja: int, data_ref: int, id_plano: int,
                               parametro: int, wall: str) -> Optional[float]:
        """Busca parâmetro wall (37-40) - wclub.parametros_clientesf"""
        try:
            # Usar datetime naive
            data_referencia = datetime.fromtimestamp(data_ref)

            # Buscar configuração ativa da loja específica
            config = ParametrosService.get_configuracao_ativa(id_loja, data_referencia, id_plano, wall)

            if config:
                # Mapear parâmetro wall para campo na estrutura consolidada
                # wclub.parametros_clientesf → parametro_wall_{numero}
                campo_parametro = f'parametro_wall_{parametro}'
                valor = getattr(config, campo_parametro, None)

                return Decimal(str(valor)) if valor is not None else None

            return None

        except Exception as e:
            registrar_log('parametros_wallclub', f"Erro ao buscar parâmetro wall: {str(e)}", nivel='ERROR')
            return None

    @staticmethod
    def contar_configuracoes_loja(loja_id: int) -> int:
        """Conta total de configurações de uma loja"""
        return ParametrosWall.objects.filter(loja_id=loja_id).count()

    @staticmethod
    def obter_ultima_configuracao(loja_id: int) -> Optional[ParametrosWall]:
        """Busca última configuração criada de uma loja"""
        return ParametrosWall.objects.filter(loja_id=loja_id).order_by('-vigencia_inicio').first()

    @staticmethod
    def loja_tem_wall_s(loja_id: int) -> bool:
        """Verifica se loja tem configurações Wall S"""
        return ParametrosWall.objects.filter(loja_id=loja_id, wall='S').exists()

    @staticmethod
    def loja_tem_wall_n(loja_id: int) -> bool:
        """Verifica se loja tem configurações Wall N"""
        return ParametrosWall.objects.filter(loja_id=loja_id, wall='N').exists()

    @staticmethod
    def buscar_configuracoes_loja(loja_id: int, data_referencia=None) -> List[ParametrosWall]:
        """Busca configurações ativas de uma loja"""
        if data_referencia is None:
            data_referencia = datetime.now()

        return list(
            ParametrosWall.objects.filter(
                loja_id=loja_id,
                vigencia_inicio__lte=data_referencia
            ).filter(
                models.Q(vigencia_fim__isnull=True) |
                models.Q(vigencia_fim__gte=data_referencia)
            ).order_by('wall', 'id_plano')
        )

    @staticmethod
    def listar_todos_planos() -> List[Plano]:
        """Lista todos os planos ordenados por ID"""
        return list(Plano.objects.all().order_by('id'))

    @staticmethod
    def verificar_plano_existe(plano_id: int) -> bool:
        """Verifica se plano existe"""
        return Plano.objects.filter(id=plano_id).exists()

    @staticmethod
    def listar_ultimas_importacoes(limit: int = 10) -> List[ImportacaoConfiguracoes]:
        """Lista últimas importações"""
        return list(ImportacaoConfiguracoes.objects.all().order_by('-created_at')[:limit])

    @staticmethod
    def obter_importacao(importacao_id: int) -> Optional[ImportacaoConfiguracoes]:
        """Busca importação por ID"""
        try:
            return ImportacaoConfiguracoes.objects.get(id=importacao_id)
        except ImportacaoConfiguracoes.DoesNotExist:
            return None


class CalculadoraDesconto:
    """
    Calculadora de desconto que replica a lógica completa do PHP.
    Inclui todos os cálculos: parâmetros básicos, wall, clientesf e ajustes finais.
    """

    def __init__(self):
        self.valores = {}
        self.logs = []
        self.id_plano_encontrado = None

    def calcular_desconto(self, valor_original: Decimal, data: str, forma: str,
                         parcelas: int, id_loja: int, wall: str) -> Optional[Decimal]:
        """
        Calcula o desconto seguindo exatamente a lógica do PHP.

        Args:
            valor_original: Valor da transação
            data: Data da transação (formato YYYY-MM-DD)
            forma: Forma de pagamento (PIX, DEBITO, CREDITO, etc)
            parcelas: Número de parcelas
            id_loja: ID da loja
            wall: 's' ou 'n' para Wall

        Returns:
            Valor final calculado ou None em caso de erro
        """
        self.valores = {}
        self.logs = []

        # Normalizar wall para maiúsculo (base usa 'S'/'N')
        wall = wall.upper()

        self._log("=============================================")
        self._log("NOVO CICLO")
        self._log(f"Parâmetros: valor={valor_original}, data={data}, forma={forma}, "
                 f"parcelas={parcelas}, id_loja={id_loja}, wall={wall}")

        # Ajustar parcelas conforme forma de pagamento
        pixcartao = forma
        if forma in ["DEBITO", "PIX"]:
            parcelas = 0
        elif forma == "CREDITO" and parcelas == 1:
            forma = "A VISTA"  # Corrigir nome do plano para busca
        elif forma == "A VISTA":
            parcelas = 1

        # Converter data para timestamp
        data_ref = ParametrosService.converter_para_timestamp(data)
        if data_ref is None:
            self._log("ERRO: data_ref é NULL - retornando valor original")
            return valor_original

        # Determinar tipo de pagamento e buscar plano
        if pixcartao != "PIX":
            pixcartao = "CARTÃO"
            id_plano = ParametrosService.busca_plano(forma, parcelas, "MASTERCARD", wall)
        else:
            id_plano = ParametrosService.busca_plano(forma, parcelas, "PIX", wall)

        self._log(f"id_plano: {id_plano}")
        self.id_plano_encontrado = id_plano  # Armazenar para output

        if id_plano == 0:
            self._log("ERRO: id_plano é 0 - plano não encontrado - retornando valor original")
            return valor_original

        # CRÍTICO: Buscar configuração usando ID original do plano (não consolidado)
        # Para replicar comportamento PHP que usa IDs diferentes para wall='s' vs wall='n'
        from datetime import datetime
        data_referencia = datetime.now()

        # Primeiro tentar com ID original, depois com ID consolidado se não encontrar
        config = None

        self._log(f"Buscando configuração: loja_id={id_loja}, id_plano={id_plano}, wall={wall}, data={data_referencia}")

        # Buscar configuração
        config = ParametrosService.get_configuracao_ativa(
            loja_id=id_loja,
            id_plano=id_plano,
            wall=wall,
            data_referencia=data_referencia
        )

        self._log(f"Configuração encontrada: {config is not None}")
        if config:
            self._log(f"Config ID: {config.id}, loja_id: {config.loja_id}, plano: {config.id_plano}, wall: {config.wall}")
        else:
            self._log("ERRO: Nenhuma configuração encontrada - retornando valor original")
            self._log(f"Parâmetros de busca: id_loja={id_loja}, data={data_referencia}, plano={id_plano}, wall={wall}")

            # Log adicional para debug
            total_configs = ParametrosService.get_all_configuracoes_count()
            self._log(f"Total de configurações na base: {total_configs}")
            return valor_original

        # Log detalhado dos parâmetros encontrados
        self._log(f"Config ID: {config.id if hasattr(config, 'id') else 'N/A'}")
        self._log(f"Param 1: {getattr(config, 'parametro_loja_1', 'N/A')}")
        self._log(f"Param 7: {getattr(config, 'parametro_loja_7', 'N/A')}")
        self._log(f"Param 10: {getattr(config, 'parametro_loja_10', 'N/A')}")
        self._log(f"Param Wall 2: {getattr(config, 'parametro_wall_2', 'N/A')}")

        # Inicializar valores básicos
        self.valores[11] = valor_original  # Valor original
        self.valores[13] = parcelas        # Número de parcelas

        # Usar configuração já encontrada - parâmetro 7 (desconto PIX)
        param_7 = getattr(config, 'parametro_loja_7', None)

        # CRÍTICO: Interromper cálculo se param_7 é NULL (replicar comportamento PHP)
        if param_7 is None:
            self._log("ERRO: param_7 é NULL - retornando null da função")
            return None

        param_7 = param_7 or 0
        if wall in ['S', 'C']:  # S e C usam mesma lógica de cálculo
            self.valores[14] = self._format_decimal(100 * param_7)
        else:
            self.valores[14] = self._format_decimal(0)

        self._log(f"Valores[14]: {self.valores[14]}")

        # Usar configuração já encontrada - parâmetro 1 (prazo limite)
        param_1 = getattr(config, 'parametro_loja_1', None) or 0
        self.valores[29] = int(param_1)

        self._log(f"Valores[29]: {self.valores[29]}")

        # Calcular valores[16]
        if forma == "DEBITO":
            self.valores[16] = self._format_decimal(self.valores[11])
        else:
            diferenca = self.valores[13] - self.valores[29]
            if diferenca > 0:
                self.valores[16] = self._format_decimal(self.valores[11])
            else:
                self.valores[16] = self._format_decimal(
                    self.valores[11] * (1 - self.valores[14] / 100)
                )

        self._log(f"Valores[16]: {self.valores[16]}")

        # Usar configuração já encontrada - parâmetro 10 para valores[17]
        param_10 = getattr(config, 'parametro_loja_10', None) or 0
        if wall in ['S', 'C']:  # S e C usam mesma lógica de cálculo
            self.valores[17] = self._format_decimal(100 * param_10)  # Multiplicar por 100 como PHP linha 102
        else:
            self.valores[17] = self._format_decimal(0)

        self._log(f"Valores[17]: {self.valores[17]}")

        # Calcular valores[19] - REPLICAR LÓGICA PHP EXATA
        if forma == "DEBITO":
            self.valores[19] = self._format_decimal(self.valores[11])
        else:
            diferenca = self.valores[13] - self.valores[29]
            if diferenca > 0:
                self.valores[19] = self._format_decimal(
                    self.valores[11] * (1 - self.valores[14] / 100)
                )
            else:
                self.valores[19] = self._format_decimal(
                    self.valores[11] * (1 - self.valores[17] / 100)
                )

        # CRÍTICO: Ajuste especial para parcelados Wall S e C (PHP linha 113-116)
        if self.valores[13] > 0 and wall in ['S', 'C']:
            ref = self._format_decimal(self.valores[19] / self.valores[13])
            self.valores[19] = self._format_decimal(ref * self.valores[13])

        self._log(f"Valores[19]: {self.valores[19]}")

        # Calcular valores[72] - Parâmetro 10 com lógica especial
        # CORREÇÃO: Replicar lógica PHP exata (linhas 120-128)
        # Se parcelas > prazo_limite: aplicar taxa negativa (desconto)
        # Se parcelas <= prazo_limite: aplicar taxa positiva (acréscimo)

        if self.valores[13] > self.valores[29]:
            self.valores[72] = self._format_decimal(-1 * 100 * param_10)  # Multiplicar por 100 como PHP linha 131
        else:
            self.valores[72] = self._format_decimal(100 * param_10)  # Multiplicar por 100 como PHP linha 135
        self._log(f"Valores[72]: {self.valores[72]}")

        # Calcular valores[74] - Parâmetro wall 2
        param_wall_2 = getattr(config, 'parametro_wall_2', None) or 0
        self.valores[74] = self._format_decimal(param_wall_2)  # CORREÇÃO: sem multiplicar por 100

        self._log(f"Valores[74]: {self.valores[74]}")

        # Calcular valores[76] - Soma dos ajustes
        self.valores[76] = self._format_decimal(self.valores[72] + self.valores[74])
        self._log(f"Valores[76]: {self.valores[76]}")

        # Calcular valores[23] - REPLICAR LÓGICA PHP EXATA (linhas 143-152)
        if forma == "DEBITO":
            self.valores[23] = self._format_decimal(self.valores[11])
        else:
            diferenca = self.valores[13] - self.valores[29]
            if diferenca > 0:
                self.valores[23] = self._format_decimal(self.valores[11])
            else:
                self.valores[23] = self._format_decimal(
                    self.valores[11] * (1 - self.valores[14] / 100)
                )

        self._log(f"Valores[23] antes: {self.valores[23]}")
        self._log(f"Valores[76]: {self.valores[76]}")
        self._log(f"Valores[16]: {self.valores[16]}")
        self._log(f"Valores[23]: {self.valores[23]}")

        # CRÍTICO: Replicar lógica PHP exata - NÃO aplicar valores[76] no resultado final
        if pixcartao == "CARTÃO":
            self.valores[26] = self._format_decimal(self.valores[19])
            self._log(f"CARTÃO: Retornando valores[19]={self.valores[19]} SEM ajuste valores[76]")
        else:
            self.valores[26] = self._format_decimal(self.valores[23])
            self._log(f"PIX: Retornando valores[23]={self.valores[23]} SEM ajuste valores[76]")

        self._log(f"Valores[26]: {self.valores[26]}")

        # Retornar valores[26] sempre (PHP linha 168)
        return self.valores[26]

    def _format_decimal(self, value) -> Decimal:
        """Formata decimal com 2 casas decimais, igual ao PHP number_format"""
        if isinstance(value, Decimal):
            decimal_value = value
        else:
            decimal_value = Decimal(str(value))
        return decimal_value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def _log(self, message: str):
        """Log interno para debug"""
        from wallclub_core.utilitarios.log_control import registrar_log
        message_str = str(message) if message is not None else "None"
        self.logs.append(message_str)
        registrar_log('parametros_wallclub', f"CalculadoraDesconto: {message_str}")

    def calcular_cashback(self, valor_original: float, data: str, forma: str,
                         parcelas: int, id_loja: int, percentual_cashback: float = 5.0) -> Dict[str, Any]:
        """
        Calcula cashback sobre o valor já descontado (wall='C')

        Fluxo:
        1. Calcula desconto normal usando wall='C' (mesma lógica de wall='S')
        2. Cliente paga valor COM desconto no POS
        3. Cashback é calculado sobre o valor descontado

        Args:
            valor_original: Valor da transação sem desconto
            data: Data da transação (YYYY-MM-DD)
            forma: Forma de pagamento (PIX, DEBITO, CREDITO, etc)
            parcelas: Número de parcelas
            id_loja: ID da loja
            percentual_cashback: Percentual de cashback sobre valor descontado (default: 5%)

        Returns:
            Dict com:
            - sucesso: True/False
            - valor_original: Valor sem desconto
            - valor_com_desconto: Valor que cliente paga no POS
            - valor_desconto: Valor do desconto aplicado
            - valor_cashback: Valor do cashback sobre valor descontado
            - percentual_cashback: Percentual aplicado
            - mensagem: Mensagem de erro se houver
        """
        try:
            # 1. Calcular desconto usando wall='C' (mesma lógica de 'S')
            valor_com_desconto = self.calcular_desconto(
                valor_original=valor_original,
                data=data,
                forma=forma,
                parcelas=parcelas,
                id_loja=id_loja,
                wall='C'
            )

            # 2. Se não conseguiu calcular, retornar erro
            if valor_com_desconto is None:
                return {
                    'sucesso': False,
                    'mensagem': 'Não foi possível calcular desconto base',
                    'valor_original': valor_original,
                    'valor_com_desconto': valor_original,
                    'valor_desconto': 0,
                    'valor_cashback': 0,
                    'percentual_cashback': 0
                }

            # 3. Calcular valor do desconto
            valor_desconto = valor_original - valor_com_desconto

            # 4. Calcular cashback sobre o VALOR JÁ DESCONTADO
            valor_cashback = valor_com_desconto * (percentual_cashback / 100)

            # 5. Arredondar valores
            valor_cashback = self._format_decimal(valor_cashback)
            valor_desconto = self._format_decimal(valor_desconto)
            valor_com_desconto = self._format_decimal(valor_com_desconto)

            self._log(f"Cashback calculado: Original={valor_original}, "
                     f"Descontado={valor_com_desconto}, Desconto={valor_desconto}, "
                     f"Cashback={valor_cashback} ({percentual_cashback}%)")

            return {
                'sucesso': True,
                'valor_original': str(valor_original),
                'valor_com_desconto': str(valor_com_desconto),
                'valor_desconto': str(valor_desconto),
                'valor_cashback': str(valor_cashback),
                'percentual_cashback': str(percentual_cashback),
                'mensagem': 'Cashback calculado com sucesso'
            }

        except Exception as e:
            registrar_log('parametros_wallclub', f"Erro ao calcular cashback: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': f'Erro ao calcular cashback: {str(e)}',
                'valor_original': valor_original,
                'valor_com_desconto': valor_original,
                'valor_desconto': 0,
                'valor_cashback': 0,
                'percentual_cashback': 0
            }



