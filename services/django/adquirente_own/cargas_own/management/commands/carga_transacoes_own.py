"""
Management command para carga de extrato Own Financial
Uso: python manage.py carga_transacoes_own --cnpj=00000000000000 --data-inicial=2025-01-01 --data-final=2025-01-31
"""

from django.core.management.base import BaseCommand
from datetime import datetime
from adquirente_own.cargas_own.services_carga_extrato_pos import CargaExtratoOwnService


class Command(BaseCommand):
    help = 'Executa carga de extrato Own Financial'

    def add_arguments(self, parser):
        parser.add_argument(
            '--diaria',
            action='store_true',
            help='Executa carga diária (últimas 24h)'
        )
        parser.add_argument(
            '--cnpj',
            type=str,
            help='CNPJ específico do cliente'
        )
        parser.add_argument(
            '--data-inicial',
            type=str,
            help='Data inicial (YYYY-MM-DD)'
        )
        parser.add_argument(
            '--data-final',
            type=str,
            help='Data final (YYYY-MM-DD)'
        )
        parser.add_argument(
            '--nsu',
            type=str,
            help='NSU específico da transação (identificadorTransacao)'
        )

    def handle(self, *args, **options):
        from datetime import timedelta
        service = CargaExtratoOwnService()

        if options['diaria']:
            # Carga diária
            self.stdout.write(self.style.SUCCESS('🔄 Executando carga diária...'))
            resultado = service.executar_carga_diaria(cnpj_cliente=options.get('cnpj'))

        else:
            # Determinar período
            if options.get('dias'):
                # Usar dias retroativos
                data_final = datetime.now()
                data_inicial = data_final - timedelta(days=options['dias'])
            elif options['data_inicial'] and options['data_final']:
                # Usar datas específicas (dia completo: 00:00 até 23:59)
                data_inicial = datetime.strptime(options['data_inicial'], '%Y-%m-%d')
                data_final = datetime.strptime(options['data_final'], '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            else:
                self.stdout.write(self.style.ERROR('❌ Informe --dias OU --data-inicial e --data-final'))
                return

            # Buscar lojas OWN cadastradas
            from adquirente_own.models_cadastro import LojaOwn
            from wallclub_core.estr_organizacional.loja import Loja

            # CNPJ WallClub (sempre usado como cnpjCliente)
            CNPJ_WALLCLUB = '54430621000134'

            cnpj_loja_especifico = options.get('cnpj')

            if cnpj_loja_especifico:
                # Processar apenas uma loja específica
                lojas_cnpj = [cnpj_loja_especifico]
            else:
                # Processar todas as lojas OWN aprovadas
                lojas_own_ids = LojaOwn.objects.filter(
                    status_credenciamento='APROVADO',
                    sincronizado=True
                ).values_list('loja_id', flat=True)

                lojas_cnpj = list(Loja.objects.filter(
                    id__in=lojas_own_ids
                ).values_list('cnpj', flat=True))

                if not lojas_cnpj:
                    self.stdout.write(self.style.WARNING('⚠️  Nenhuma loja OWN aprovada encontrada. Buscando todas as transações do WallClub...'))
                    lojas_cnpj = [None]  # Buscar sem filtro de loja

            self.stdout.write(self.style.SUCCESS(f'🔄 Processando {len(lojas_cnpj)} loja(s): {data_inicial.date()} a {data_final.date()}'))

            total_geral_transacoes = 0
            total_geral_processadas = 0

            # Processar cada loja
            for doc_parceiro in lojas_cnpj:
                if doc_parceiro:
                    self.stdout.write(f'\n📋 Loja: {doc_parceiro}')
                else:
                    self.stdout.write(f'\n📋 Todas as lojas WallClub')

                # Buscar por NSU específico ou por período
                nsu = options.get('nsu')
                if nsu:
                    self.stdout.write(f'🔍 Buscando NSU: {nsu}')

                result = service.buscar_transacoes_gerais(
                    cnpj_cliente=CNPJ_WALLCLUB,
                    doc_parceiro=doc_parceiro,
                    data_inicial=data_inicial,
                    data_final=data_final,
                    identificador_transacao=nsu
                )

                if not result.get('sucesso'):
                    self.stdout.write(self.style.WARNING(f'   ⚠️  {result.get("mensagem")}'))
                    continue

                # Processar transações
                total_novas = 0
                for transacao_data in result.get('transacoes', []):
                    transacao_obj = service.salvar_transacao(transacao_data)
                    # Contar apenas transações novas (created=True no update_or_create)
                    if transacao_obj:
                        total_novas += 1

                total_transacoes = result.get('total', 0)
                total_geral_transacoes += total_transacoes
                total_geral_processadas += total_novas

                self.stdout.write(f'   ✅ {total_transacoes} transações encontradas, {total_novas} novas salvas')

            resultado = {
                'total_transacoes': total_geral_transacoes,
                'total_processadas': total_geral_processadas
            }

        # Exibir resultado
        self.stdout.write(self.style.SUCCESS(f'✅ Carga concluída!'))
        self.stdout.write(f'   Total transações: {resultado.get("total_transacoes", 0)}')
        self.stdout.write(f'   Total processadas: {resultado.get("total_processadas", 0)}')
