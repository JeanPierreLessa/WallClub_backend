"""
Service para processamento de dados de transação (TRData)
Extraído de posp2/services.py
"""
import json
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any
from django.db import connection

from wallclub_core.utilitarios.funcoes_gerais import calcular_cet
from parametros_wallclub.services import ParametrosService
from parametros_wallclub.calculadora_base_gestao import CalculadoraBaseGestao
from pinbank.services import PinbankService
from gestao_financeira.models import BaseTransacoesGestao
from wallclub_core.utilitarios.log_control import registrar_log
from wallclub_core.services.auditoria_service import AuditoriaService
from django.apps import apps
from .services_antifraude import interceptar_transacao_pos


class TRDataService:
    """Serviço para processamento de dados de transação (TRData)"""
    
    # Mapeamento centralizado de PaymentMethod para TipoCompra
    TIPO_COMPRA_MAP = {
        'CREDIT_IN_INSTALLMENTS_WITHOUT_INTEREST': 'PARCELADO SEM JUROS',
        'CREDIT_ONE_INSTALLMENT': 'A VISTA',
        'DEBIT': 'DEBITO',
        'CASH': 'PIX'
    }
    
    def __init__(self):
        self.parametros_service = ParametrosService()
        self.pinbank_service = PinbankService()
    
    def determinar_wall_cliente(self, cpf: str, canal_id: int) -> str:
        """
        Determina modalidade wall do cliente
        
        Regras:
        - Tem CPF cadastrado → 'S' (Cliente identificado)
        - Não tem CPF → 'N' (Cliente anônimo)
        """
        try:
            from wallclub_core.integracoes.api_interna_service import APIInternaService
            
            # Verificar cadastro via API interna
            response = APIInternaService.chamar_api_interna(
                metodo='POST',
                endpoint='/api/internal/cliente/verificar_cadastro/',
                payload={'cpf': cpf, 'canal_id': canal_id},
                contexto='apis'
            )
            
            tem_cadastro = response.get('tem_cadastro', False) if response.get('sucesso') else False
            
            if tem_cadastro:
                registrar_log('posp2', f'Cliente {cpf[:3]}*** tem cadastro → wall=S')
                return 'S'
            
            registrar_log('posp2', f'Cliente {cpf[:3]}*** sem cadastro → wall=N')
            return 'N'
            
        except Exception as e:
            registrar_log('posp2', f'Erro ao determinar wall: {str(e)} → Default wall=N')
            return 'N'
    
    def processar_dados_transacao(self, dados_json: str) -> Dict[str, Any]:
        """
        Processa dados de transação e gera informações para comprovante
        Replicando interface exata do trdata.php
        
        Args:
            dados_json: JSON bruto com todos os dados da requisição
        """
        try:
            registrar_log('posp2', '========================================')
            registrar_log('posp2', f'{datetime.now().strftime("%d/%m/%Y %H:%M:%S")} - Processamento de Transação')
            registrar_log('posp2', '========================================')
            registrar_log('posp2', 'Iniciando processamento de dados de transação')
            
            # Log do JSON de request recebido
            registrar_log('posp2', f'=== REQUEST JSON RECEBIDO ===')
            registrar_log('posp2', f'JSON completo: {dados_json}')
            registrar_log('posp2', f'Tamanho do JSON: {len(dados_json)} caracteres')
            registrar_log('posp2', f'=============================')
            
            # Parse do JSON recebido
            try:
                dados = json.loads(dados_json)
            except json.JSONDecodeError as e:
                registrar_log('posp2', f'Erro ao decodificar JSON: {e}', nivel='ERROR')
                return {
                    'sucesso': False,
                    'mensagem': f'Erro ao decodificar JSON: {e}'
                }
            
            # 1. Extrair parâmetros do JSON
            celular = dados.get('celular', '')
            cpf = dados.get('cpf', '')
            trdata = dados.get('trdata', '')
            terminal = dados.get('terminal', '')
            valororiginal = dados.get('valororiginal', '')
            operador_pos = dados.get('operador_pos', '')
            
            # Extrair valores já calculados pelo POS (vindos da simulação)
            valor_desconto_pos = dados.get('valor_desconto', 0)
            valor_cashback_pos = dados.get('valor_cashback', 0)
            cashback_concedido_pos = dados.get('cashback_concedido', 0)
            autorizacao_id = dados.get('autorizacao_id', '')
            modalidade_wall = dados.get('modalidade_wall', '')
            
            registrar_log('posp2', f'Parâmetros extraídos - Terminal: {terminal}, CPF: {cpf}, '
                        f'Valor Desconto: {valor_desconto_pos}, Valor Cashback: {valor_cashback_pos}, '
                        f'Cashback Concedido: {cashback_concedido_pos}, '
                        f'Autorizacao ID: {autorizacao_id if autorizacao_id else "N/A"}, '
                        f'Modalidade Wall: {modalidade_wall if modalidade_wall else "N/A"}')
            
            # 2. Validar dados obrigatórios (CPF e celular são opcionais para venda normal)
            campos_obrigatorios = {
                'trdata': trdata,
                'terminal': terminal,
                'valororiginal': valororiginal
            }
            
            for campo, valor in campos_obrigatorios.items():
                if not valor:
                    return {
                        'sucesso': False,
                        'mensagem': f'Campo obrigatório ausente: {campo}'
                    }
            
            # Log se é venda normal (sem CPF/celular) ou com Wall Club
            if not cpf and not celular:
                registrar_log('posp2', 'Processando VENDA NORMAL (sem CPF/celular)')
            else:
                registrar_log('posp2', 'Processando venda COM WALL CLUB (CPF/celular fornecidos)')
            
            # 3. Parse do JSON trdata (replicando lógica PHP)
            try:
                registrar_log('posp2', f'=== DEBUG JSON DECODE ===')
                registrar_log('posp2', f'TrData recebido (primeiros 500 chars): {trdata[:500]}')
                registrar_log('posp2', f'TrData length: {len(trdata)}')
                
                dados_trdata = json.loads(trdata)
                
                registrar_log('posp2', 'JSON decodificado com sucesso!')
                registrar_log('posp2', f'Campos encontrados: {", ".join(dados_trdata.keys())}')
                
                # Verificar se formaPagamento contém um JSON string
                if 'formaPagamento' in dados_trdata and isinstance(dados_trdata['formaPagamento'], str):
                    registrar_log('posp2', 'ATENÇÃO: Dados JSON detectados em formaPagamento!')
                    try:
                        forma_pagamento_data = json.loads(dados_trdata['formaPagamento'])
                        registrar_log('posp2', 'JSON em formaPagamento decodificado com sucesso')
                        
                        # Mesclar os dados de formaPagamento com o objeto principal
                        dados_trdata.update(forma_pagamento_data)
                        registrar_log('posp2', 'Dados extraídos de formaPagamento e mesclados ao objeto principal')
                    except json.JSONDecodeError:
                        pass
                
                
                # Log dos campos importantes após o processamento
                registrar_log('posp2', '=== CAMPOS APÓS PROCESSAMENTO ===')
                registrar_log('posp2', f'aid: {dados_trdata.get("aid", "NÃO ENCONTRADO")}')
                registrar_log('posp2', f'paymentMethod: {dados_trdata.get("paymentMethod", "NÃO ENCONTRADO")}')
                registrar_log('posp2', f'amount: {dados_trdata.get("amount", "NÃO ENCONTRADO")}')
                registrar_log('posp2', f'brand: {dados_trdata.get("brand", "NÃO ENCONTRADO")}')
                registrar_log('posp2', f'cardNumber: {dados_trdata.get("cardNumber", "NÃO ENCONTRADO")}')
                registrar_log('posp2', f'nsuPinbank: {dados_trdata.get("nsuPinbank", "NÃO ENCONTRADO")}')
                registrar_log('posp2', f'status: {dados_trdata.get("status", "NÃO ENCONTRADO")}')
                registrar_log('posp2', f'totalInstallments: {dados_trdata.get("totalInstallments", "NÃO ENCONTRADO")}')
                registrar_log('posp2', '==========================')
                
            except json.JSONDecodeError as e:
                registrar_log('posp2', f'Erro ao decodificar trdata JSON: {e}', nivel='ERROR')
                return {
                    'sucesso': False,
                    'mensagem': f'Erro ao decodificar trdata JSON: {e}'
                }
            
            # 4. Preparar dados unificados para processamento
            # Se valororiginal não existe, usar o valor da operação
            if not valororiginal:
                valor_operacao = Decimal(str(dados_trdata.get('amount', 0))) / Decimal('100')
                valororiginal = valor_operacao
                registrar_log('posp2', f'valororiginal não informado, usando valor da operação: {valororiginal}')
            
            # Mesclar dados_trdata com parâmetros principais
            dados_trdata.update({
                'celular': celular,
                'cpf': cpf,
                'terminal': terminal,
                'valororiginal': valororiginal,
                'operador_pos': operador_pos,
                'valor_desconto': valor_desconto_pos,
                'valor_cashback': valor_cashback_pos,
                'cashback_concedido': cashback_concedido_pos,
                'autorizacao_id': autorizacao_id,
                'modalidade_wall': modalidade_wall
            })
            
            # 5. Extrair e converter dados para formato da calculadora
            host_timestamp = dados_trdata.get('hostTimestamp', '')
            payment_method = dados_trdata.get('paymentMethod', '')
            nsu_acquirer = dados_trdata.get('nsuAcquirer', '')
            valor_orig_raw = dados_trdata.get('amount', 0)
            # Corrigir valor que vem multiplicado por 100
            valor_orig = Decimal(str(valor_orig_raw)) / Decimal('100')
            registrar_log('posp2', f'Valor original corrigido: {valor_orig_raw} -> {valor_orig}')
            brand = dados_trdata.get('brand', '')
            total_installments = dados_trdata.get('totalInstallments', 1)
            
            # Log do paymentMethod recebido
            registrar_log('posp2', f'PaymentMethod da transactiondata: "{payment_method}" (tipo: {type(payment_method)})')
            
            # 6. Converter PaymentMethod para TipoCompra
            tipo_compra = self.TIPO_COMPRA_MAP.get(payment_method, payment_method or '')
            registrar_log('posp2', f'TipoCompra mapeado: "{tipo_compra}"')
            
            # 7. Preparar dados para calculadora (formato unificado)
            # Converter hostTimestamp (formato: 20250912130603) para ISO
            if host_timestamp and str(host_timestamp).strip() and str(host_timestamp) != '0':
                # Converter de 20250912130603 para 2025-09-12T13:06:03
                timestamp_str = str(host_timestamp)
                if len(timestamp_str) == 14:
                    data_transacao_iso = f"{timestamp_str[:4]}-{timestamp_str[4:6]}-{timestamp_str[6:8]}T{timestamp_str[8:10]}:{timestamp_str[10:12]}:{timestamp_str[12:14]}"
                    registrar_log('posp2', f'hostTimestamp convertido: {host_timestamp} -> {data_transacao_iso}')
                else:
                    # Fallback para timestamp atual se formato inválido
                    data_transacao_iso = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
                    registrar_log('posp2', f'hostTimestamp formato inválido ({host_timestamp}), usando timestamp atual: {data_transacao_iso}')
            else:
                # Se hostTimestamp está vazio, usar timestamp atual
                data_transacao_iso = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
                registrar_log('posp2', f'hostTimestamp estava vazio ({host_timestamp}), usando timestamp atual: {data_transacao_iso}')
            
            # Usar valororiginal para calculadora se disponível, senão usar amount corrigido
            if valororiginal:
                # Converter valororiginal de "R$4,70" para 4.70
                valor_original_limpo = str(valororiginal).replace('R$', '').replace(' ', '').strip()
                if ',' in valor_original_limpo and '.' not in valor_original_limpo:
                    valor_original_limpo = valor_original_limpo.replace(',', '.')
                valor_para_calculadora = Decimal(valor_original_limpo).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                registrar_log('posp2', f'valororiginal convertido: "{valororiginal}" -> {valor_para_calculadora}')
            else:
                valor_para_calculadora = valor_orig
                registrar_log('posp2', f'Usando amount corrigido: {valor_para_calculadora}')
            
            registrar_log('posp2', f'Valor final para calculadora: {valor_para_calculadora}')
            
            dados_linha = {
                'id': dados_trdata.get('id', 0),
                'DataTransacao': data_transacao_iso,
                'SerialNumber': terminal,
                'idTerminal': terminal,
                'cpf': cpf,
                'TipoCompra': tipo_compra,
                'NsuOperacao': dados_trdata.get('nsuPinbank', ''),
                'nsuAcquirer': nsu_acquirer,
                'valor_original': valor_para_calculadora,
                'ValorBruto': valor_para_calculadora,
                'ValorBrutoParcela': valor_para_calculadora,
                'Bandeira': brand,
                'NumeroTotalParcelas': total_installments,
                'ValorTaxaAdm': 0,
                'ValorTaxaMes': 0,
                'ValorSplit': 0,
                'DescricaoStatus': 'Processado',
                'DescricaoStatusPagamento': 'Pendente',
                'IdStatusPagamento': 1,
                'DataCancelamento': None,
                'DataFuturaPagamento': None
            }
            
            # Usar dados_trdata como dados principais (elimina duplicação)
            dados = dados_trdata
            
            # 8. INSERIR NA TRANSACTIONDATA
            registrar_log('posp2', 'Iniciando inserção na transactiondata...')
            self._inserir_transaction_data(dados, {}, autorizacao_id, modalidade_wall, cashback_concedido_pos)
            registrar_log('posp2', 'Inserção na transactiondata concluída')
            
            # 9. CALCULAR VALORES APÓS INSERÇÃO
            calculadora = CalculadoraBaseGestao()
            registrar_log('posp2', f'Chamando calcular_valores_primarios com dados_linha: {dados_linha}')
            try:
                valores_calculados = calculadora.calcular_valores_primarios(dados_linha, tabela='transactiondata')
                registrar_log('posp2', 'Calculadora executada com sucesso')
                
                # Log completo dos valores calculados
                registrar_log('posp2', f'Valores calculados - Total de campos: {len(valores_calculados)}')
                registrar_log('posp2', f'Valores calculados completos: {valores_calculados}')
            except Exception as e:
                registrar_log('posp2', f'ERRO na calculadora: {str(e)}')
                # Continuar com valores vazios para não interromper o fluxo
                valores_calculados = {}
            
            # 9.5. BUSCAR LOJA PRIMEIRO (necessário para obter canal_id)
            nsu_pinbank = dados.get('nsuPinbank')
            loja_info = None
            if nsu_pinbank:
                registrar_log('posp2', f'nsuPinbank extraído: "{nsu_pinbank}"')
                registrar_log('posp2', f'Buscando loja para nsuPinbank: "{nsu_pinbank}" (tipo: {type(nsu_pinbank)})')
                
                from pinbank.services import PinbankService
                pinbank_service = PinbankService()
                loja_info = pinbank_service.pega_info_loja(int(nsu_pinbank), tabela='transactiondata')
                registrar_log('posp2', f'Chamando pega_info_loja({nsu_pinbank})')
                registrar_log('posp2', f'Loja encontrada: {loja_info}')
            
            # 9.6. DETERMINAR MODALIDADE WALL
            valor_desconto = Decimal(str(valor_desconto_pos)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) if valor_desconto_pos else Decimal('0')
            modalidade_wall = 'N'
            
            registrar_log('posp2', f'Valores recebidos do POS - Desconto: {valor_desconto}')
            
            if cpf:
                try:
                    # Determinar wall do cliente
                    canal_id = loja_info.get('canal_id') if loja_info else 1  # Default canal 1 se loja não encontrada
                    modalidade_wall = self.determinar_wall_cliente(cpf, canal_id)
                    
                    registrar_log('posp2', f'Modalidade wall determinada: {modalidade_wall} para CPF {cpf[:3]}***')
                        
                except Exception as e:
                    registrar_log('posp2', f'❌ Erro ao determinar wall: {str(e)}')
                    modalidade_wall = 'N'
            else:
                registrar_log('posp2', f'CPF não fornecido, transação sem wall (modalidade=N)')
            
            # Adicionar campos aos valores calculados para salvar no banco
            valores_calculados['modalidade_wall'] = modalidade_wall
            valores_calculados['valor_desconto'] = valor_desconto
            
            # ========== INTERCEPTAÇÃO ANTIFRAUDE (Fase 2 - Semana 14) ==========
            if cpf and valor_para_calculadora > 0:
                try:
                    registrar_log('posp2', '🛡️ [ANTIFRAUDE] Iniciando análise de risco da transação')
                    
                    # Determinar modalidade (PIX, CREDITO, DEBITO)
                    modalidade_map = {
                        'DEBITO': 'DEBITO',
                        'A VISTA': 'CREDITO',
                        'PARCELADO SEM JUROS': 'CREDITO',
                        'PARCELADO COM JUROS': 'CREDITO'
                    }
                    modalidade_antifraude = modalidade_map.get(tipo_compra, 'CREDITO')
                    
                    # Obter loja_id e canal_id
                    loja_id = loja_info.get('loja_id', 1) if loja_info else 1
                    canal_id = loja_info.get('canal_id', 1) if loja_info else 1
                    
                    # Interceptar transação
                    permitir, resultado_antifraude = interceptar_transacao_pos(
                        cpf=cpf,
                        valor=valor_para_calculadora,
                        modalidade=modalidade_antifraude,
                        parcelas=int(total_installments),
                        terminal=terminal,
                        loja_id=loja_id,
                        canal_id=canal_id,
                        numero_cartao=dados.get('cardNumber'),
                        bandeira=brand,
                        nsu=nsu_pinbank
                    )
                    
                    registrar_log(
                        'posp2',
                        f'🛡️ [ANTIFRAUDE] Decisão: {resultado_antifraude.get("decisao")} | '
                        f'Score: {resultado_antifraude.get("score_risco")} | '
                        f'Permitir: {permitir}'
                    )
                    
                    # Se transação REPROVADA, bloquear
                    if not permitir:
                        registrar_log(
                            'posp2',
                            f'❌ [ANTIFRAUDE] Transação BLOQUEADA - {resultado_antifraude.get("motivo")}',
                            nivel='ERROR'
                        )
                        return {
                            'sucesso': False,
                            'mensagem': 'Transação bloqueada pelo sistema antifraude',
                            'motivo_antifraude': resultado_antifraude.get('motivo'),
                            'decisao_antifraude': resultado_antifraude.get('decisao'),
                            'score_risco': resultado_antifraude.get('score_risco')
                        }
                    
                    # Se REQUER_3DS, retornar para cliente completar autenticação
                    if resultado_antifraude.get('requer_3ds'):
                        registrar_log('posp2', '🔐 [ANTIFRAUDE] Transação requer autenticação 3DS')
                        dados_3ds = resultado_antifraude.get('dados_3ds', {})
                        return {
                            'sucesso': False,
                            'mensagem': 'Autenticação 3D Secure necessária',
                            'requer_3ds': True,
                            'auth_id': dados_3ds.get('auth_id'),
                            'redirect_url': dados_3ds.get('redirect_url'),
                            'transacao_id': resultado_antifraude.get('transacao_id')
                        }
                    
                    registrar_log('posp2', '✅ [ANTIFRAUDE] Transação aprovada, continuando processamento')
                    
                except Exception as e:
                    registrar_log(
                        'posp2',
                        f'⚠️ [ANTIFRAUDE] Erro ao analisar transação: {str(e)} - Continuando (fail-open)',
                        nivel='ERROR'
                    )
                    # Em caso de erro, continuar processamento (fail-open)
            else:
                registrar_log('posp2', '⏭️ [ANTIFRAUDE] Pulando análise (sem CPF ou valor zero)')
            # ========== FIM INTERCEPTAÇÃO ANTIFRAUDE ==========
            
            # NOTA: NÃO fazemos UPDATE aqui porque os valores já foram inseridos corretamente no INSERT inicial
            # O UPDATE estava sobrescrevendo os valores corretos do JSON com valores calculados posteriormente
            registrar_log('posp2', f'✅ Valores de cashback já inseridos via INSERT - NSU {dados.get("nsuPinbank")}: '
                        f'desconto={valor_desconto_pos}, cashback={valor_cashback_pos}')
            
            # 10. INSERIR EM BASETRANSACOESGESTAO
            # Usar o mesmo hostTimestamp parseado que foi usado para transactiondata
            host_timestamp = dados.get('hostTimestamp', '')
            if host_timestamp and str(host_timestamp).strip() and str(host_timestamp) != '0':
                timestamp_str = str(host_timestamp)
                if len(timestamp_str) == 14:
                    # Converter 20250912130603 para datetime naive (sem timezone)
                    data_transacao_dt = datetime.strptime(timestamp_str, '%Y%m%d%H%M%S')
                else:
                    data_transacao_dt = datetime.now().replace(microsecond=0)
            else:
                data_transacao_dt = datetime.now().replace(microsecond=0)
            
            registrar_log('posp2', f'Passando data_transacao_dt para baseTransacoesGestao: {data_transacao_dt}')
            self._inserir_base_transacoes_gestao(dados, valores_calculados, data_transacao_dt)
            
            # 12 ENVIAR NOTIFICAÇÃO PUSH PARA O APP (Firebase ou APN)
            try:
                from wallclub_core.integracoes.notification_service import NotificationService
                
                # Obter CPF do cliente - garantir formato correto sem pontos e traços
                cpf = dados.get('cpf')
                if cpf:
                    # Remover pontos e traços para garantir formato correto
                    cpf = cpf.replace('.', '').replace('-', '')
                    registrar_log('posp2', f'CPF formatado para envio de push: {cpf}')
                
                # Buscar canal_id da LOJA (cliente pode estar em múltiplos canais)
                # loja_info já foi buscado anteriormente (linha 1078)
                canal_id = None
                id_loja = None
                
                if loja_info:
                    try:
                        # Buscar canal e id da loja do loja_info
                        canal_id = loja_info.get('canal_id')
                        id_loja = loja_info.get('loja_id')
                        
                        if canal_id and id_loja:
                            registrar_log('posp2', f'Canal da loja {id_loja}: {canal_id}')
                            
                            # Validar que o cliente existe neste canal específico via API interna
                            from wallclub_core.integracoes.api_interna_service import APIInternaService
                            
                            response = APIInternaService.chamar_api_interna(
                                metodo='POST',
                                endpoint='/api/internal/cliente/consultar_por_cpf/',
                                payload={'cpf': cpf, 'canal_id': canal_id},
                                contexto='apis'
                            )
                            
                            cliente_canal = response.get('cliente') if response.get('sucesso') else None
                            
                            if not cliente_canal or not cliente_canal.get('is_active'):
                                registrar_log('posp2', f'AVISO: Cliente {cpf} não encontrado no canal {canal_id} da loja {id_loja}')
                                canal_id = None
                            else:
                                registrar_log('posp2', f'Cliente {cpf} confirmado no canal {canal_id}')
                        else:
                            registrar_log('posp2', f'Dados incompletos em loja_info: canal_id={canal_id}, loja_id={id_loja}')
                            canal_id = None
                    except Exception as e:
                        registrar_log('posp2', f'Erro ao processar loja_info: {str(e)}')
                        canal_id = None
                else:
                    registrar_log('posp2', f'loja_info não disponível para buscar canal')
                
                # Log para debug
                if not canal_id:
                    registrar_log('posp2', f'Push não enviado: canal_id não encontrado (loja_info={loja_info})')
                
                if cpf and canal_id:
                    # Calcular valor final para push (usar amount se valores_calculados[26] for None)
                    valor_transacao = valores_calculados.get(26)
                    if not valor_transacao or valor_transacao == 0:
                        # Usar amount (valor cobrado do cartão)
                        amount_centavos = dados.get('amount', 0)
                        if amount_centavos:
                            valor_transacao = float(amount_centavos) / 100
                        else:
                            valor_transacao = valor_para_calculadora
                    
                    registrar_log('posp2', f'Usando valor final com desconto para push: {valor_transacao} (original: {valor_para_calculadora})')
                    
                    # Usar loja_info para obter o nome do estabelecimento
                    nome_estabelecimento = 'Estabelecimento'
                    if loja_info and isinstance(loja_info, dict):
                        # Usar loja do loja_info
                        if loja_info.get('loja'):
                            nome_estabelecimento = loja_info.get('loja')
                        
                        registrar_log('posp2', f'Nome do estabelecimento obtido de loja_info: {nome_estabelecimento}')
                    
                    # Registrar informações para debug
                    registrar_log('posp2', f'Valor da transação para push: {valor_transacao}')
                    registrar_log('posp2', f'Nome do estabelecimento para push: {nome_estabelecimento}')
                    
                    # Preparar dados da transação para notificação
                    notification_data = {
                        'valor': valor_transacao,
                        'tipo_transacao': valores_calculados.get('tipo_transacao', 'Compra'),
                        'estabelecimento': nome_estabelecimento,
                        'data_hora': data_transacao_dt.strftime('%Y-%m-%d %H:%M:%S'),
                        'id': dados.get('nsu', '0')
                    }
                    
                    # Inicializar serviço unificado de notificação para o canal
                    # Enviar notificação usando sistema unificado de templates
                    notification_service = NotificationService.get_instance(canal_id)
                    
                    registrar_log('posp2', f'Enviando push notification para CPF {cpf} no canal {canal_id}')
                    
                    try:
                        # Extrair dados da notificação
                        valor_formatado = notification_data.get('valor', '0,00')
                        estabelecimento = notification_data.get('estabelecimento', 'Estabelecimento')
                        tipo_transacao = notification_data.get('tipo_transacao', 'Transação')
                        
                        push_result = notification_service.send_push(
                            cpf=cpf,
                            id_template='transacao_aprovada',
                            tipo_transacao=tipo_transacao,
                            valor=valor_formatado,
                            estabelecimento=estabelecimento,
                            data_hora=notification_data.get('data_hora', ''),
                            transacao_id=notification_data.get('id', '')
                        )
                        registrar_log('posp2', f'Resultado do envio de push notification: {push_result}')
                    except Exception as push_error:
                        registrar_log('posp2', f'ERRO ao enviar push: {str(push_error)}', nivel='ERROR')
                        import traceback
                        registrar_log('posp2', f'Traceback: {traceback.format_exc()}', nivel='ERROR')
                else:
                    registrar_log('posp2', f'Não foi possível enviar push: CPF não encontrado')
            except Exception as e:
                # Não interromper o fluxo se houver erro no envio da notificação
                registrar_log('posp2', f'Erro ao enviar push notification: {str(e)}')
            
            # 13. GERAR E DEVOLVER JSON DE RESPOSTA
            json_resposta = self._gerar_slip_impressao(dados, valores_calculados, loja_info)
            
            registrar_log('posp2', f'JSON resposta gerado: {json_resposta}')
            
            # 14. CONCEDER CASHBACK (SE HOUVER)
            # Converter para Decimal para comparação
            cashback_concedido_decimal = Decimal(str(cashback_concedido_pos)) if cashback_concedido_pos else Decimal('0')
            
            if cashback_concedido_decimal > 0 and cpf:
                try:
                    from .services_conta_digital import CashbackService
                    
                    registrar_log('posp2', 
                        f'💰 [CASHBACK] Iniciando concessão: '
                        f'cpf={cpf[:3]}***, valor={cashback_concedido_decimal}, NSU={nsu_pinbank}')
                    
                    # Buscar cliente pelo CPF
                    try:
                        cliente = Cliente.objects.get(cpf=cpf, canal_id=canal_id)
                        
                        # Conceder cashback com retenção de 30 dias
                        resultado_cashback = CashbackService.concessao_cashback(
                            cliente_id=cliente.id,
                            canal_id=canal_id,
                            valor_cashback=cashback_concedido_decimal,
                            nsu_transacao=str(nsu_pinbank),
                            cpf=cpf,
                            terminal=terminal
                        )
                        
                        if resultado_cashback['sucesso']:
                            registrar_log('posp2',
                                f'✅ [CASHBACK] Concedido com sucesso: '
                                f'movimentacao={resultado_cashback.get("movimentacao_id")}, '
                                f'liberação={resultado_cashback.get("data_liberacao")}')
                        else:
                            registrar_log('posp2',
                                f'❌ [CASHBACK] Erro na concessão: {resultado_cashback.get("mensagem")}',
                                nivel='ERROR')
                    
                    except Cliente.DoesNotExist:
                        registrar_log('posp2',
                            f'⚠️ [CASHBACK] Cliente não encontrado: cpf={cpf[:3]}***, canal={canal_id}')
                
                except Exception as e:
                    # NÃO interromper o fluxo - transação já foi gravada
                    registrar_log('posp2',
                        f'❌ [CASHBACK] Exceção ao conceder: {str(e)}',
                        nivel='ERROR')
            elif cashback_concedido_decimal > 0 and not cpf:
                registrar_log('posp2',
                    f'⚠️ [CASHBACK] Cashback informado mas sem CPF: valor={cashback_concedido_decimal}')
            
            registrar_log('posp2', 'Processamento concluído com sucesso')
            
            return {
                'sucesso': True,
                'mensagem': 'Dados processados com sucesso',
                **json_resposta  # Retorna dados formatados para impressão (já implementado em _gerar_json_resposta)
            }
        
        except json.JSONDecodeError as e:
            registrar_log('posp2', f'Erro ao decodificar JSON: {e}')
            return {
                'sucesso': False,
                'mensagem': f'Erro ao decodificar JSON: {e}'
            }
        except Exception as e:
            import traceback
            registrar_log('posp2', f'ERRO CAPTURADO no processar_dados_transacao: {str(e)}')
            registrar_log('posp2', f'TIPO DO ERRO: {type(e).__name__}')
            registrar_log('posp2', f'TRACEBACK COMPLETO: {traceback.format_exc()}')
            return {
                'sucesso': False,
                'mensagem': f'Erro interno: {e}'
            }
    
    def _criar_array_base(self, dados: Dict, valores_calculados: Dict, cpf: str, nome: str, 
                         cnpj: str, data_formatada: str, hora: str, forma: str, 
                         nopwall: str, autwall: str, terminal: str, nsu: str, cet: str) -> Dict:
        """Cria array base comum para todas as respostas"""
        def mascarar_cpf(cpf_str):
            if not cpf_str:
                return cpf_str
            # Remover formatação (pontos e hífen) para trabalhar apenas com números
            cpf_numeros = ''.join(filter(str.isdigit, cpf_str))
            if len(cpf_numeros) < 11:
                return cpf_str
            # Mascarar CPF mostrando apenas os últimos 3 dígitos no formato ********807
            return f"*******{cpf_numeros[-3:]}"
        
        array_base = {
            "cpf": mascarar_cpf(cpf) if cpf else "",
            "nome": nome,
            "estabelecimento": valores_calculados.get(5, ''),  # var5 = nome da loja
            "cnpj": cnpj,
            "data": f"{data_formatada} {hora}",
            "forma": forma,
            "parcelas": valores_calculados.get(13, 1),
            "nopwall": nopwall,
            "autwall": autwall,
            "terminal": terminal,
            "nsu": nsu
        }
        
        # Só incluir CET se tiver valor
        if cet and cet.strip() and not cet.endswith(': -'):
            array_base["cet"] = cet
            
        return array_base
    
    def _gerar_slip_impressao(self, dados: Dict, valores_calculados: Dict, loja_info: Dict) -> Dict:
        """Gera JSON de resposta formatado exatamente como o PHP trdata.php"""
        try:
            registrar_log('posp2', f'Iniciando _gerar_json_resposta')
            registrar_log('posp2', f'Dados recebidos: {list(dados.keys())}')
            registrar_log('posp2', f'Valores calculados recebidos: {len(valores_calculados)} campos')
            
            # Usar loja_info já obtida anteriormente (evita nova consulta)
            info_loja = loja_info
            registrar_log('posp2', f'Usando loja_info já obtida: {info_loja}')
            
            # Dados básicos
            cpf = dados.get('cpf', '')
            
            # Buscar nome do cliente usando obter_dados_cliente
            nome = ''
            if cpf:
                try:
                    # Usar canal_id dos valores calculados
                    from wallclub_core.integracoes.api_interna_service import APIInternaService
                    
                    canal_id = valores_calculados['canal_id']
                    
                    # Obter dados via API interna
                    response = APIInternaService.chamar_api_interna(
                        metodo='POST',
                        endpoint='/api/internal/cliente/obter_dados_cliente/',
                        payload={'cpf': cpf, 'canal_id': canal_id},
                        contexto='apis'
                    )
                    
                    dados_cliente = response.get('dados') if response.get('sucesso') else None
                    if dados_cliente and dados_cliente.get('nome'):
                        nome = dados_cliente['nome']
                        registrar_log('posp2', f'Nome do cliente encontrado: {nome} (canal_id: {canal_id})')
                    else:
                        registrar_log('posp2', f'Cliente não encontrado para CPF: {cpf} (canal_id: {canal_id})')
                except Exception as e:
                    registrar_log('posp2', f'Erro ao buscar dados do cliente: {str(e)}')
            
            wall = 's' if cpf and len(cpf.strip()) > 0 else 'n'  # Determinar wall baseado no CPF
            
            # Mapear paymentMethod para forma de pagamento usando o mapeamento centralizado
            payment_method = dados.get('paymentMethod', '')
            brand = dados.get('brand', '')
            
            # Se brand é PIX, sempre usar PIX independente do paymentMethod
            if brand == 'PIX':
                forma = 'PIX'
            else:
                forma = self.TIPO_COMPRA_MAP.get(payment_method, payment_method or '')
            
            # Valores calculados - função segura para converter valores monetários
            def safe_float_convert(value):
                if not value:
                    return 0.0
                if isinstance(value, str):
                    value = value.replace('R$', '').replace(' ', '').strip()
                    if ',' in value and '.' not in value:
                        value = value.replace(',', '.')
                    elif ',' in value and '.' in value:
                        # Formato com milhares: 1.234,56 -> 1234.56
                        if value.rfind(',') > value.rfind('.'):
                            value = value.replace('.', '').replace(',', '.')
                        else:
                            value = value.replace(',', '')
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return 0.0
            
            # Obter valor original (valororiginal) para exibição no JSON
            valor_original_str = dados.get('valororiginal', '')
            if valor_original_str:
                # Converter string "R$500,00" para float 500.0
                valor_original_display = safe_float_convert(valor_original_str)
            else:
                valor_original_display = valores_calculados.get(11, 0)
            registrar_log('posp2', f'=== DADOS COMPLETOS CHEGANDO NO _gerar_json_resposta ===')
            registrar_log('posp2', f'TODOS OS DADOS:')
            for key in sorted(dados.keys()):
                registrar_log('posp2', f' dados[{key}] = {dados[key]}')
            registrar_log('posp2', f'VALORES CALCULADOS COMPLETOS (130 variáveis):')
            for i in range(131):  # 0 a 130
                if i in valores_calculados:
                    registrar_log('posp2', f' valores_calculados[{i}] = {valores_calculados.get(i)}')
            registrar_log('posp2', f'Valor original para display: {valor_original_display}')
            registrar_log('posp2', f'=== FIM DADOS COMPLETOS ===')
            
            terminal = dados.get('terminal', '')
            # Corrigir inversão: nsu deve ser nsuPinbank, nopwall deve ser nsuAcquirer
            nsu = dados.get('nsu', dados.get('nsuPinbank', ''))
            nopwall = dados.get('nopwall', dados.get('nsuAcquirer', ''))
            autwall = dados.get('autwall', dados.get('authorizationCode', ''))
            cnpj = info_loja.get('cnpj', '')
            
            def formatar_valor_monetario(valor):
                """Formatar valor monetário com 2 decimais, tratando None como 0"""
                if valor is None:
                    return "0.00"
                try:
                    return f"{float(valor):.2f}"
                except (ValueError, TypeError):
                    return "0.00"
            
            registrar_log('posp2', f'Dados básicos extraídos:')
            registrar_log('posp2', f' cpf: "{cpf}"')
            registrar_log('posp2', f' nome: "{nome}"')
            registrar_log('posp2', f' wall: "{wall}"')
            registrar_log('posp2', f' forma: "{forma}"')
            registrar_log('posp2', f' terminal: "{terminal}"')
            registrar_log('posp2', f' nsu: "{nsu}"')
            registrar_log('posp2', f' cnpj: "{cnpj}"')
            
            # Valores calculados - função segura para converter valores monetários
            def safe_float_convert(value):
                if not value:
                    return 0.0
                if isinstance(value, str):
                    value = value.replace('R$', '').replace(' ', '').strip()
                    if ',' in value and '.' not in value:
                        value = value.replace(',', '.')
                    elif ',' in value and '.' in value:
                        # Formato com milhares: 1.234,56 -> 1234.56
                        if value.rfind(',') > value.rfind('.'):
                            value = value.replace('.', '').replace(',', '.')
                        else:
                            value = value.replace(',', '')
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return 0.0
            
            # Lógica condicional do PHP: PIX usa valores[15], outros usam valores[18]
            pixcartao = self.TIPO_COMPRA_MAP.get(dados.get('paymentMethod', ''), '')
            if pixcartao == 'PIX':
                pixcartao_tipo = "PIX"
            else:
                pixcartao_tipo = "CARTÃO"
            
            # Implementar lógica exata do PHP dados_impressao
            if valores_calculados.get(12) == "PIX" or pixcartao_tipo == "PIX":
                desconto = safe_float_convert(valores_calculados.get(15, 0))
            else:
                desconto = safe_float_convert(valores_calculados.get(18, 0))
            
            # Valores conforme PHP
            parte0 = safe_float_convert(valores_calculados.get(26, 0))  # valor final
            
            # Se parte0 for zero/None, usar amount (valor real cobrado)
            if not parte0 or parte0 == 0:
                # Usar amount (valor cobrado do cartão) em vez de valororiginal
                amount_centavos = dados.get('amount', 0)
                if amount_centavos:
                    parte0 = safe_float_convert(amount_centavos) / 100
                    registrar_log('posp2', f'💰 [AMOUNT] Usando amount: {amount_centavos} centavos = R$ {parte0}')
                else:
                    # Fallback: usar valor original
                    valor_original = safe_float_convert(valores_calculados.get(11, 0))
                    parte0 = valor_original
                    registrar_log('posp2', f'💰 [FALLBACK] Usando valor original: {parte0}')
            
            parte1 = abs(desconto)  # valor absoluto do desconto
            
            # vparcela e cálculos de tarifas/encargos conforme PHP
            parcelas = int(valores_calculados.get(13, 1))
            
            # === CORREÇÃO TARIFAS/ENCARGOS SEGUINDO PHP ===
            registrar_log('posp2', f'VALORES PHP PARA CÁLCULO:')
            registrar_log('posp2', f'valores[13] (parcelas) = {valores_calculados.get(13)}')
            registrar_log('posp2', f'valores[20] (vparcela) = {valores_calculados.get(20)}')
            registrar_log('posp2', f'valores[16] (valor_liquido) = {valores_calculados.get(16)}')
            registrar_log('posp2', f'valores[88] = {valores_calculados.get(88)}')
            registrar_log('posp2', f'valores[94] = {valores_calculados.get(94)}')
            
            # SEGUIR EXATAMENTE O PHP:
            # $encargos = abs($valores[88] + $valores[94]["0"]);
            valores_94 = valores_calculados.get(94, {})
            if isinstance(valores_94, dict):
                valores_94_0 = valores_94.get('0', 0)
            else:
                valores_94_0 = 0
            encargos = abs((valores_calculados.get(88) or 0) + valores_94_0)
            
            # $vparcela = $valores[20];
            vparcela = valores_calculados.get(20, 0)
            # Para débito e PIX, se vparcela for nulo ou zero, usar parte0 / parcelas
            if vparcela is None or vparcela == 0:
                vparcela = parte0 / parcelas if parcelas > 0 else parte0
            
            # $tarifas = abs($valores[13] * $vparcela - $valores[16]) - $encargos;
            valor_liquido = valores_calculados.get(16, 0)
            tarifas = round(abs(valores_calculados.get(13, 1) * vparcela - valor_liquido) - encargos, 2)
            
            registrar_log('posp2', f'=== CÁLCULO PHP REPLICADO ===')
            registrar_log('posp2', f'encargos = abs({valores_calculados.get(88, 0)} + {valores_94_0}) = {encargos}')
            registrar_log('posp2', f'vparcela = {vparcela} (valores[20] direto)')
            registrar_log('posp2', f'tarifas = abs({valores_calculados.get(13, 1)} * {vparcela} - {valor_liquido}) - {encargos} = {tarifas}')
            
            registrar_log('posp2', f'=== RESULTADO FINAL ===')
            registrar_log('posp2', f'vparcela = {vparcela}')
            registrar_log('posp2', f'encargos = {encargos}')
            
            # Buscar saldo usado de cashback via autorizacao_id
            saldo_cashback_usado = 0.0
            autorizacao_id = dados.get('autorizacao_id', '')
            if autorizacao_id:
                try:
                    from apps.conta_digital.services_autorizacao import AutorizacaoService
                    resultado = AutorizacaoService.verificar_autorizacao(autorizacao_id)
                    if resultado.get('sucesso') and resultado.get('status') in ['APROVADO', 'CONCLUIDA']:
                        valor_bloqueado = resultado.get('valor_bloqueado')
                        if valor_bloqueado:
                            saldo_cashback_usado = float(valor_bloqueado)
                            registrar_log('posp2', f'💸 [SALDO] Saldo cashback usado encontrado: R$ {saldo_cashback_usado:.2f}, status={resultado.get("status")}')
                except Exception as e:
                    registrar_log('posp2', f'❌ [SALDO] Erro ao buscar saldo usado: {str(e)}', nivel='ERROR')
            
            # Extrair cashback_concedido dos dados
            cashback_concedido = safe_float_convert(dados.get('cashback_concedido', 0))
            registrar_log('posp2', f'💰 [CASHBACK] Cashback concedido: R$ {cashback_concedido:.2f}')
            
            # AJUSTAR vdesconto e vparcela considerando saldo usado
            # vdesconto = valor_original - desconto_club - saldo_usado
            vdesconto_final = parte0 - saldo_cashback_usado
            
            # vparcela = vdesconto / parcelas
            vparcela_ajustado = vdesconto_final / parcelas if parcelas > 0 else vdesconto_final
            
            registrar_log('posp2', f'💰 [AJUSTE SALDO] parte0={parte0:.2f}, saldo_usado={saldo_cashback_usado:.2f}, vdesconto_final={vdesconto_final:.2f}')
            registrar_log('posp2', f'💰 [AJUSTE SALDO] vparcela original={vparcela:.2f}, vparcela_ajustado={vparcela_ajustado:.2f}, parcelas={parcelas}')
            
            # Data e hora
            agora = datetime.now()
            data_formatada = valores_calculados.get(0, agora.strftime('%Y-%m-%d'))
            hora = agora.strftime('%H:%M:%S')
            
            # CET para parcelado
            cet = ""
            parcelas = int(valores_calculados.get(13, 1))
            if parcelas > 1:
                valor_original = float(valores_calculados.get(11, 0))
                cetn = calcular_cet(vparcela, valor_original, parcelas)
                if cetn is None or cetn == "":
                    cet = "CET (Custo Efetivo Total) %am: -"
                else:
                    cetn = round(float(cetn), 2)
                    cet = f"CET (Custo Efetivo Total) %am: {cetn}"
            
            # Inicializar array
            array = {}
            
            # Lógica condicional do PHP
            registrar_log('posp2', f'Iniciando lógica condicional - wall: "{wall}", forma: "{forma}"')
            
            if wall == 's':  # COM WALL CLUB
                registrar_log('posp2', f'Processando COM WALL CLUB')
                
                if forma in ["PIX", "DEBITO"]:
                    registrar_log('posp2', f'Forma PIX/DEBITO detectada')
                    array = self._criar_array_base(dados, valores_calculados, cpf, nome, cnpj, 
                                                  data_formatada, hora, forma, nopwall, autwall, terminal, nsu, cet)
                    array_update = {
                        "voriginal": f"Valor original da loja: R$ {formatar_valor_monetario(valor_original_display)}",
                        "desconto": f"Valor do desconto CLUB: R$ {formatar_valor_monetario(desconto)}",
                    }
                    
                    # Adicionar saldo usado se existir
                    if saldo_cashback_usado > 0:
                        array_update["saldo_usado"] = f"Saldo utilizado de cashback: R$ {formatar_valor_monetario(saldo_cashback_usado)}"
                    
                    # Adicionar cashback concedido se existir
                    if cashback_concedido > 0:
                        array_update["cashback_concedido"] = f"Cashback concedido: R$ {formatar_valor_monetario(cashback_concedido)}"
                    
                    array_update.update({
                        "vdesconto": f"Valor total pago:\nR$ {formatar_valor_monetario(vdesconto_final)}",
                        "pagoavista": f"Valor pago à loja à vista: R$ {formatar_valor_monetario(valores_calculados.get(16, 0))}",
                        "vparcela": f"R$ {formatar_valor_monetario(vparcela_ajustado)}",
                        "tarifas": "Tarifas CLUB: -- ",
                        "encargos": ""
                    })
                    array.update(array_update)
                    registrar_log('posp2', f'Array PIX/DEBITO criado com {len(array)} campos')
                
                elif (forma in ["PARCELADO SEM JUROS", "A VISTA", "PARCELADO COM JUROS"]) and desconto >= 0:
                    array = self._criar_array_base(dados, valores_calculados, cpf, nome, cnpj, 
                                                  data_formatada, hora, forma, nopwall, autwall, terminal, nsu, cet)
                    array_update = {
                        "voriginal": f"Valor original da loja: R$ {formatar_valor_monetario(valor_original_display)}",
                        "desconto": f"Valor do desconto CLUB: R$ {formatar_valor_monetario(parte1)}",
                    }
                    
                    # Adicionar saldo usado se existir
                    if saldo_cashback_usado > 0:
                        array_update["saldo_usado"] = f"Saldo utilizado de cashback: R$ {formatar_valor_monetario(saldo_cashback_usado)}"
                    
                    # Adicionar cashback concedido se existir
                    if cashback_concedido > 0:
                        array_update["cashback_concedido"] = f"Cashback concedido: R$ {formatar_valor_monetario(cashback_concedido)}"
                    
                    array_update.update({
                        "vdesconto": f"Valor pago com desconto:\nR$ {formatar_valor_monetario(vdesconto_final)}",
                        "pagoavista": f"Valor pago à loja à vista: R$ {formatar_valor_monetario(valores_calculados.get(16, 0))}",
                        "vparcela": f"R$ {formatar_valor_monetario(vparcela_ajustado)}",
                        "tarifas": f"Tarifas CLUB: R$ {formatar_valor_monetario(tarifas)}",
                        "encargos": f"Encargos financeiros: R$ {formatar_valor_monetario(encargos)}"
                    })
                    array.update(array_update)
                
                elif (forma in ["PARCELADO SEM JUROS", "A VISTA", "PARCELADO COM JUROS"]) and desconto < 0:
                    array = self._criar_array_base(dados, valores_calculados, cpf, nome, cnpj, 
                                                  data_formatada, hora, forma, nopwall, autwall, terminal, nsu, cet)
                    array_update = {
                        "voriginal": f"Valor original da loja: R$ {formatar_valor_monetario(valor_original_display)}",
                        "desconto": f"Valor total dos encargos: R$ {formatar_valor_monetario(parte1)}",
                    }
                    
                    # Adicionar saldo usado se existir
                    if saldo_cashback_usado > 0:
                        array_update["saldo_usado"] = f"Saldo utilizado de cashback: R$ {formatar_valor_monetario(saldo_cashback_usado)}"
                    
                    # Adicionar cashback concedido se existir
                    if cashback_concedido > 0:
                        array_update["cashback_concedido"] = f"Cashback concedido: R$ {formatar_valor_monetario(cashback_concedido)}"
                    
                    array_update.update({
                        "vdesconto": f"Valor total pago com encargos:\nR$ {formatar_valor_monetario(vdesconto_final)}",
                        "pagoavista": f"Valor pago à loja à vista: R$ {formatar_valor_monetario(valores_calculados.get(16, 0))}",
                        "vparcela": f"R$ {formatar_valor_monetario(vparcela_ajustado)}",
                        "tarifas": f"Tarifas CLUB: R$ {formatar_valor_monetario(tarifas)}",
                        "encargos": f"Encargos pagos a operadora de cartão: R$ {formatar_valor_monetario(encargos)}"
                    })
                    array.update(array_update)
                
            else:  # SEM WALL CLUB (wall != 's') - Venda normal sem CPF
                registrar_log('posp2', f'Processando SEM WALL CLUB - venda normal')
                array = self._criar_array_base(dados, valores_calculados, "", "", cnpj, 
                                              data_formatada, hora, forma, nopwall, autwall, terminal, nsu, cet)
                
                # Para venda normal: valor da transação vai direto para pagoavista
                valor_transacao = valores_calculados.get(11, valor_original_display)  # var11 = valor original
                
                # Corrigir parcelas para débito (deve ser 0, não 1)
                if forma == "DEBITO":
                    array["parcelas"] = 0
                
                # Texto do pagoavista conforme PHP
                pagoavista_text = "Valor pago à loja a vista" if forma in ["PIX", "DEBITO"] else "Valor pago à loja"
                
                # Valor da parcela individual para parcelado
                valor_parcela_individual = valores_calculados.get(20, valor_transacao)  # var20 = valor da parcela
                
                array.update({
                    "voriginal": f"Valor original da loja: R$ {formatar_valor_monetario(valor_original_display)}",
                    "desconto": "",  # Vazio para venda normal (igual PHP)
                    "vdesconto": f"Valor total pago:\nR$ {formatar_valor_monetario(valor_transacao)}", # Valor real (igual PHP)
                    "pagoavista": f"{pagoavista_text}: R$ {formatar_valor_monetario(valor_transacao)}",
                    "vparcela": f"R$ {formatar_valor_monetario(valor_parcela_individual)}",
                    "tarifas": "Tarifas CLUB: --",
                    "encargos": ""
                })
                registrar_log('posp2', f'Array venda normal criado com {len(array)} campos')
            
            registrar_log('posp2', f'Array final criado com {len(array)} campos')
            registrar_log('posp2', f'Retornando array: {array}')
            return array
            
        except Exception as e:
            registrar_log('posp2', f'Erro ao gerar JSON resposta: {e}')
            import traceback
            registrar_log('posp2', f'Traceback completo: {traceback.format_exc()}')
            return {}
      
    def _converter_tipos_dados(self, dados: Dict) -> Dict:
        """Converte tipos de dados para inserção na base (igual ao PHP)"""
        # Campos inteiros (com valor padrão 0) - igual ao PHP
        int_fields = ['amount', 'amountCancellation', 'nsuHost', 'nsuHostCancellation', 
                     'nsuPinbank', 'nsuTerminal', 'nsuTerminalCancellation', 
                     'originalAmount', 'totalInstallments']
        
        # Campos booleanos (com valor padrão 0) - igual ao PHP
        bool_fields = ['capturedTransaction', 'pinCaptured', 'transactionWithSignature']
        
        # Converter campos para tipos corretos (replicando lógica PHP)
        for field in int_fields:
            if field in dados:
                dados[field] = int(dados[field]) if dados[field] else 0
                registrar_log('posp2', f'Convertido {field} para inteiro: {dados[field]}')
            else:
                dados[field] = 0
                registrar_log('posp2', f'Campo {field} não encontrado, usando valor padrão: 0')
        
        for field in bool_fields:
            if field in dados:
                dados[field] = 1 if dados[field] else 0
                registrar_log('posp2', f'Convertido {field} para booleano: {dados[field]}')
            else:
                dados[field] = 0
                registrar_log('posp2', f'Campo {field} não encontrado, usando valor padrão: 0')
        
        return dados
    
    def _converter_valor_monetario(self, valor) -> float:
        """Converte valor monetário para float"""
        registrar_log('posp2', f'=== CONVERTER VALOR MONETÁRIO ===')
        registrar_log('posp2', f'Valor original: {valor} (tipo: {type(valor)})')
        
        if isinstance(valor, str):
            valor_original = valor
            # Remover formatação monetária brasileira
            valor = valor.replace('R$', '').replace(' ', '').strip()
            registrar_log('posp2', f'Após remover R$ e espaços: {valor}')
            
            # Tratar formato brasileiro: R$17,00 -> 17.00
            if ',' in valor and '.' not in valor:
                # Formato simples: 17,00
                valor = valor.replace(',', '.')
                registrar_log('posp2', f'Formato simples - após trocar vírgula: {valor}')
            elif ',' in valor and '.' in valor:
                # Formato com milhares: 1.234,56 -> 1234.56
                # Último ponto/vírgula é decimal
                if valor.rfind(',') > valor.rfind('.'):
                    # Vírgula é decimal: 1.234,56
                    valor = valor.replace('.', '').replace(',', '.')
                    registrar_log('posp2', f'Formato milhares (vírgula decimal): {valor}')
                else:
                    # Ponto é decimal: 1,234.56 (formato americano)
                    valor = valor.replace(',', '')
                    registrar_log('posp2', f'Formato americano (ponto decimal): {valor}')
            
            resultado = float(valor) if valor else 0.0
            registrar_log('posp2', f'Conversão: {valor_original} → {resultado}')
            return resultado
        
        registrar_log('posp2', f'Valor não é string, retornando: {float(valor) if valor else 0.0}')
        return float(valor) if valor else 0.0
    
    def _inserir_transaction_data(self, dados: Dict, resultado: Dict, autorizacao_id: str = '', modalidade_wall: str = '', cashback_concedido: float = 0):
        """Insere dados na tabela transactiondata replicando lógica PHP"""
        try:
            registrar_log('posp2', f'=== INÍCIO _inserir_transaction_data ===')
            registrar_log('posp2', f'Dados recebidos: {list(dados.keys())}')
            registrar_log('posp2', f'DEBUG ANTES conversão: valor_desconto={dados.get("valor_desconto")}, valor_cashback={dados.get("valor_cashback")}')
            
            # Converter tipos de dados
            dados = self._converter_tipos_dados(dados)
            registrar_log('posp2', f'Dados após conversão: {list(dados.keys())}')
            registrar_log('posp2', f'DEBUG DEPOIS conversão: valor_desconto={dados.get("valor_desconto")}, valor_cashback={dados.get("valor_cashback")}')
            
            # Converter valor_original para decimal
            valor_original = self._converter_valor_monetario(dados.get('valororiginal', 0))
            registrar_log('posp2', f'Valor original convertido: {valor_original}')
            
            # Preparar dados para inserção usando campos convertidos
            campos_string = ['aid', 'applicationName', 'arqc', 'authorizationCode', 
                           'billPaymentEffectiveDate', 'brand', 'captureType', 'cardName', 
                           'cardNumber', 'hostTimestamp', 'hostTimestampCancellation', 
                           'nsuAcquirer', 'paymentMethod', 'status', 'terminalTimestamp',
                           'preAuthorizationConfirmationTimestamp', 'celular', 'cpf', 'terminal', 'operador_pos']
            
            # Campos numéricos com valores padrão seguros
            campos_numericos = ['amount', 'amountCancellation', 'nsuHost', 'nsuHostCancellation',
                              'nsuTerminal', 'nsuTerminalCancellation', 'capturedTransaction', 
                              'nsuPinbank', 'totalInstallments', 'pinCaptured', 'originalAmount',
                              'transactionWithSignature']
            
            # Converter hostTimestamp para datahora
            host_timestamp = dados.get('hostTimestamp', '')
            if host_timestamp and str(host_timestamp).strip() and str(host_timestamp) != '0':
                timestamp_str = str(host_timestamp)
                if len(timestamp_str) == 14:
                    # Converter 20250912130603 para datetime NAIVE (sem timezone)
                    # hostTimestamp já vem no horário local brasileiro
                    datahora_tz = datetime.strptime(timestamp_str, '%Y%m%d%H%M%S')
                else:
                    # Usar datetime naive para fallback também
                    datahora_tz = datetime.now().replace(microsecond=0)
            else:
                # Usar datetime naive para fallback também
                datahora_tz = datetime.now().replace(microsecond=0)

            dados_para_inserir = {
                **{campo: dados.get(campo, '') for campo in campos_string},
                **{campo: dados.get(campo, 0) for campo in campos_numericos},  # Usar .get() com padrão
                'datahora': datahora_tz,
                'valor_original': valor_original
            }
            
            registrar_log('posp2', f'Dados preparados para inserção - NSU: {dados_para_inserir.get("nsuPinbank")}')
            
            # Extrair valores de cashback vindos do JSON (já calculados pelo POS)
            registrar_log('posp2', f'DEBUG: valor_desconto do dados dict: {dados.get("valor_desconto")} (tipo: {type(dados.get("valor_desconto"))})')
            registrar_log('posp2', f'DEBUG: valor_cashback do dados dict: {dados.get("valor_cashback")} (tipo: {type(dados.get("valor_cashback"))})')
            registrar_log('posp2', f'DEBUG: cashback_concedido do dados dict: {dados.get("cashback_concedido")} (tipo: {type(dados.get("cashback_concedido"))})')
            registrar_log('posp2', f'DEBUG: Chaves disponíveis em dados: {list(dados.keys())}')
            
            valor_desconto_json = self._converter_valor_monetario(dados.get('valor_desconto', 0))
            valor_cashback_json = self._converter_valor_monetario(dados.get('valor_cashback', 0))
            cashback_concedido_json = self._converter_valor_monetario(cashback_concedido if cashback_concedido else dados.get('cashback_concedido', 0))
            
            registrar_log('posp2', f'Valores extraídos do JSON: desconto={valor_desconto_json}, cashback={valor_cashback_json}, cashback_concedido={cashback_concedido_json}')
            
            # Log detalhado dos valores finais que serão inseridos
            registrar_log('posp2', f'VALORES FINAIS PARA INSERT:')
            registrar_log('posp2', f'operador_pos={dados_para_inserir.get("operador_pos")}')
            registrar_log('posp2', f'valor_desconto_json={valor_desconto_json} (tipo: {type(valor_desconto_json)})')
            registrar_log('posp2', f'valor_cashback_json={valor_cashback_json} (tipo: {type(valor_cashback_json)})')
            registrar_log('posp2', f'cashback_concedido_json={cashback_concedido_json} (tipo: {type(cashback_concedido_json)})')
            
            # Inserir diretamente na tabela transactiondata
            with connection.cursor() as cursor:
                # Log dos últimos valores que serão inseridos
                registrar_log('posp2', f'Valores do INSERT: operador={dados_para_inserir.get("operador_pos")}, desconto={valor_desconto_json}, cashback={valor_cashback_json}, cashback_concedido={cashback_concedido_json}')
                
                cursor.execute("""
                    INSERT INTO transactiondata (
                        datahora, valor_original, celular, cpf, terminal,
                        nsuHostCancellation, amountCancellation, originalAmount,
                        preAuthorizationConfirmationTimestamp, amount, nsuTerminal,
                        status, transactionWithSignature, nsuAcquirer, nsuPinbank,
                        arqc, aid, terminalTimestamp, captureType,
                        hostTimestampCancellation, authorizationCode, nsuHost,
                        applicationName, brand, paymentMethod, totalInstallments,
                        nsuTerminalCancellation, billPaymentEffectiveDate,
                        pinCaptured, hostTimestamp, capturedTransaction,
                        cardName, cardNumber, operador_pos,
                        valor_desconto, valor_cashback, autorizacao_id, cashback_concedido, modalidade_wall
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """, (
                    dados_para_inserir.get('datahora'),
                    dados_para_inserir.get('valor_original'),
                    dados_para_inserir.get('celular'),
                    dados_para_inserir.get('cpf'),
                    dados_para_inserir.get('terminal'),
                    dados_para_inserir.get('nsuHostCancellation'),
                    dados_para_inserir.get('amountCancellation'),
                    dados_para_inserir.get('originalAmount'),
                    dados_para_inserir.get('preAuthorizationConfirmationTimestamp'),
                    dados_para_inserir.get('amount'),
                    dados_para_inserir.get('nsuTerminal'),
                    dados_para_inserir.get('status'),
                    dados_para_inserir.get('transactionWithSignature'),
                    dados_para_inserir.get('nsuAcquirer'),
                    dados_para_inserir.get('nsuPinbank'),
                    dados_para_inserir.get('arqc'),
                    dados_para_inserir.get('aid'),
                    dados_para_inserir.get('terminalTimestamp'),
                    dados_para_inserir.get('captureType'),
                    dados_para_inserir.get('hostTimestampCancellation'),
                    dados_para_inserir.get('authorizationCode'),
                    dados_para_inserir.get('nsuHost'),
                    dados_para_inserir.get('applicationName'),
                    dados_para_inserir.get('brand'),
                    dados_para_inserir.get('paymentMethod'),
                    dados_para_inserir.get('totalInstallments'),
                    dados_para_inserir.get('nsuTerminalCancellation'),
                    dados_para_inserir.get('billPaymentEffectiveDate'),
                    dados_para_inserir.get('pinCaptured'),
                    dados_para_inserir.get('hostTimestamp'),
                    dados_para_inserir.get('capturedTransaction'),
                    dados_para_inserir.get('cardName'),
                    dados_para_inserir.get('cardNumber'),
                    dados_para_inserir.get('operador_pos'),
                    valor_desconto_json,
                    valor_cashback_json,
                    autorizacao_id if autorizacao_id else None,
                    cashback_concedido_json,
                    modalidade_wall if modalidade_wall else None
                ))
            
            registrar_log('posp2', f'INSERT executado com sucesso - NSU: {dados_para_inserir.get("nsuPinbank")}')
            
            # Registrar auditoria da transação
            try:
                AuditoriaService.registrar_transacao(
                    acao='criacao',
                    transacao_id=dados_para_inserir.get('nsuPinbank', 0),
                    usuario_id=0,  # POS não tem usuário específico
                    valor_novo=float(dados_para_inserir.get('amount', 0) or 0),
                    status_novo=dados_para_inserir.get('status', 'DESCONHECIDO'),
                    motivo=f"Transação POS - Terminal: {dados_para_inserir.get('terminal')}, PaymentMethod: {dados_para_inserir.get('paymentMethod')}",
                    ip_address=None
                )
            except Exception as e_audit:
                registrar_log('posp2', f'⚠️ Erro ao registrar auditoria: {str(e_audit)}', nivel='WARNING')
            
            # Debitar saldo autorizado se houver autorizacao_id
            if autorizacao_id:
                try:
                    from apps.conta_digital.services_autorizacao import AutorizacaoService
                    nsu_transacao = str(dados_para_inserir.get('nsuPinbank'))
                    
                    registrar_log('posp2', f'💳 [SALDO] Debitando saldo autorizado: autorizacao={autorizacao_id[:8]}, NSU={nsu_transacao}')
                    
                    resultado_debito = AutorizacaoService.debitar_saldo_autorizado(
                        autorizacao_id=autorizacao_id,
                        nsu_transacao=nsu_transacao
                    )
                    
                    if resultado_debito['sucesso']:
                        registrar_log('posp2', 
                            f'✅ [SALDO] Débito realizado: R$ {resultado_debito["valor_debitado"]:.2f}, '
                            f'saldo_anterior={resultado_debito["saldo_anterior"]}, '
                            f'saldo_posterior={resultado_debito["saldo_posterior"]}')
                    else:
                        registrar_log('posp2', 
                            f'❌ [SALDO] Erro ao debitar: {resultado_debito.get("mensagem")}', 
                            nivel='ERROR')
                        # NÃO interromper o fluxo - transação já foi gravada
                        # O estorno pode ser feito manualmente se necessário
                        
                except Exception as e:
                    registrar_log('posp2', f'❌ [SALDO] Exceção ao debitar: {str(e)}', nivel='ERROR')
                    # NÃO interromper o fluxo
            
            registrar_log('posp2', f'=== FIM _inserir_transaction_data ===')
            
            return {'sucesso': True}
            
        except Exception as e:
            registrar_log('posp2', f'ERRO CRÍTICO ao inserir transaction data: {str(e)}')
            registrar_log('posp2', f'Dados que causaram erro: {dados_para_inserir if "dados_para_inserir" in locals() else "N/A"}')
            return {
                'sucesso': False,
                'mensagem': f'Erro ao gravar dados na base: {e}'
            }
    
    def _inserir_base_transacoes_gestao(self, dados: Dict, valores_calculados: Dict, data_transacao=None):
        """
        Insere dados calculados na tabela baseTransacoesGestao
        """
        try:
            from gestao_financeira.models import BaseTransacoesGestao
            
            # Para chamadas POS: idFilaExtrato sempre NULL
            # Para carga Pinbank: idFilaExtrato vem dos dados
            id_fila_extrato = None  # Sempre NULL para transações POS
            
            # Usar data_transacao passada ou datetime.now() como fallback
            registrar_log('posp2', f'_inserir_base_transacoes_gestao recebeu data_transacao: {data_transacao} (tipo: {type(data_transacao)})')
            if data_transacao is None:
                data_transacao = datetime.now().replace(microsecond=0)
                registrar_log('posp2', f'data_transacao era None, usando datetime.now(): {data_transacao}')
            else:
                registrar_log('posp2', f'Usando data_transacao recebida: {data_transacao}')
            
            # Mapear TODOS os campos calculados para o modelo
            dados_base_gestao = {
                'idFilaExtrato': id_fila_extrato,
                'banco': 'PINBANK',
                'tipo_operacao': 'Wallet',
                'data_transacao': data_transacao,
            }
            
            # Campos que devem ser string (varchar/text) - todos os outros são decimal/float
            varchar_fields = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 43, 45, 57, 59, 65, 66, 68, 69, 70, 71, 96, 97, 98, 99, 100, 102, 119, 120, 121, 122, 123, 126, 129, 130}
            
            # Mapear variáveis 0-130 com tipos corretos
            for i in range(131):
                if i in valores_calculados:
                    valor = valores_calculados[i]
                    campo_nome = f'var{i}'
                    
                    # Tratar valores None
                    if valor is None:
                        dados_base_gestao[campo_nome] = None
                    # Tratar arrays (converter para string do primeiro valor)
                    elif isinstance(valor, dict):
                        if '0' in valor:
                            valor_final = valor['0']
                        else:
                            valor_final = str(valor)
                        
                        # Aplicar tipo correto
                        if i in varchar_fields:
                            dados_base_gestao[campo_nome] = str(valor_final) if valor_final is not None else None
                        else:  # decimal fields - usar float
                            try:
                                dados_base_gestao[campo_nome] = float(valor_final) if valor_final is not None else None
                            except (ValueError, TypeError) as conv_error:
                                registrar_log('posp2', f'ERRO conversão dict campo {campo_nome}: valor="{valor_final}" tipo={type(valor_final)} erro={conv_error}')
                                dados_base_gestao[campo_nome] = 0.0
                    # Aplicar tipo baseado no campo
                    elif i in varchar_fields:
                        dados_base_gestao[campo_nome] = str(valor)
                    else:  # decimal fields - usar float
                        try:
                            dados_base_gestao[campo_nome] = float(valor)
                        except (ValueError, TypeError) as conv_error:
                            registrar_log('posp2', f'ERRO conversão campo {campo_nome}: valor="{valor}" tipo={type(valor)} erro={conv_error}')
                            dados_base_gestao[campo_nome] = 0.0  # Valor padrão
            
            # Mapear campos especiais com sufixos (_A, _B) - APENAS se existem no modelo
            for key, valor in valores_calculados.items():
                if isinstance(key, str) and '_' in key:
                    campo_nome = f'var{key}'
                    # Verificar se campo existe no modelo antes de adicionar
                    if hasattr(BaseTransacoesGestao, campo_nome) and valor is not None:
                        dados_base_gestao[campo_nome] = str(valor)
            
            # Usar SQL raw para evitar conversão de timezone pelo Django ORM
            from django.db import connection
            
            registrar_log('posp2', f'Dados finais para inserção na BaseTransacoesGestao: data_transacao={dados_base_gestao["data_transacao"]}')
            
            # Separar data_transacao dos outros campos
            data_transacao_valor = dados_base_gestao.pop('data_transacao')
            
            # Construir SQL INSERT
            campos = list(dados_base_gestao.keys()) + ['data_transacao']
            valores = list(dados_base_gestao.values()) + [data_transacao_valor.strftime('%Y-%m-%d %H:%M:%S')]
            
            placeholders = ', '.join(['%s'] * len(valores))
            campos_sql = ', '.join(campos)
            
            sql = f"INSERT INTO baseTransacoesGestao ({campos_sql}) VALUES ({placeholders})"
            
            with connection.cursor() as cursor:
                cursor.execute(sql, valores)
                base_id = cursor.lastrowid
                
            registrar_log('posp2', f'BaseTransacoesGestao inserida com sucesso via SQL raw. ID: {base_id}, data_transacao: {data_transacao_valor}')
            
        except Exception as e:
            registrar_log('posp2', f'ERRO ao inserir BaseTransacoesGestao: {e}')
            raise
