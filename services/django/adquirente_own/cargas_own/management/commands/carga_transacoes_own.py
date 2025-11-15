"""
Management command para carga de transações Own Financial
Uso: python manage.py carga_transacoes_own --cnpj=00000000000000 --data-inicial=2025-01-01 --data-final=2025-01-31
"""

from django.core.management.base import BaseCommand
from datetime import datetime
from adquirente_own.cargas_own.services_carga_transacoes import CargaTransacoesOwnService


class Command(BaseCommand):
    help = 'Executa carga de transações Own Financial'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cnpj',
            type=str,
            help='CNPJ do cliente (opcional, se não informado processa todos)'
        )
        parser.add_argument(
            '--data-inicial',
            type=str,
            help='Data inicial (formato: YYYY-MM-DD)'
        )
        parser.add_argument(
            '--data-final',
            type=str,
            help='Data final (formato: YYYY-MM-DD)'
        )
        parser.add_argument(
            '--diaria',
            action='store_true',
            help='Executa carga diária (ontem)'
        )

    def handle(self, *args, **options):
        service = CargaTransacoesOwnService()
        
        if options['diaria']:
            # Carga diária
            self.stdout.write(self.style.SUCCESS('🔄 Executando carga diária...'))
            resultado = service.executar_carga_diaria(cnpj_cliente=options.get('cnpj'))
            
        else:
            # Carga por período
            if not options['data_inicial'] or not options['data_final']:
                self.stdout.write(self.style.ERROR('❌ Informe --data-inicial e --data-final'))
                return
            
            cnpj = options.get('cnpj')
            if not cnpj:
                self.stdout.write(self.style.ERROR('❌ Informe --cnpj para carga por período'))
                return
            
            data_inicial = datetime.strptime(options['data_inicial'], '%Y-%m-%d')
            data_final = datetime.strptime(options['data_final'], '%Y-%m-%d')
            
            self.stdout.write(self.style.SUCCESS(f'🔄 Buscando transações: {data_inicial.date()} a {data_final.date()}'))
            
            # Buscar transações
            result = service.buscar_transacoes_gerais(
                cnpj_cliente=cnpj,
                data_inicial=data_inicial,
                data_final=data_final
            )
            
            if not result.get('sucesso'):
                self.stdout.write(self.style.ERROR(f'❌ Erro: {result.get("mensagem")}'))
                return
            
            # Processar transações
            total_processadas = 0
            for transacao_data in result.get('transacoes', []):
                transacao_obj = service.salvar_transacao(transacao_data)
                if not transacao_obj.processado:
                    service.processar_para_base_gestao(transacao_obj)
                    total_processadas += 1
            
            resultado = {
                'total_transacoes': result.get('total', 0),
                'total_processadas': total_processadas
            }
        
        # Exibir resultado
        self.stdout.write(self.style.SUCCESS(f'✅ Carga concluída!'))
        self.stdout.write(f'   Total transações: {resultado.get("total_transacoes", 0)}')
        self.stdout.write(f'   Total processadas: {resultado.get("total_processadas", 0)}')
