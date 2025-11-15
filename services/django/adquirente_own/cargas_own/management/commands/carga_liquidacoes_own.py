"""
Management command para carga de liquidações Own Financial
Uso: python manage.py carga_liquidacoes_own --cnpj=00000000000000 --data=2025-01-15
"""

from django.core.management.base import BaseCommand
from datetime import datetime
from adquirente_own.cargas_own.services_carga_liquidacoes import CargaLiquidacoesOwnService


class Command(BaseCommand):
    help = 'Executa carga de liquidações Own Financial'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cnpj',
            type=str,
            help='CNPJ do cliente (opcional, se não informado processa todos)'
        )
        parser.add_argument(
            '--data',
            type=str,
            help='Data do pagamento real (formato: YYYY-MM-DD)'
        )
        parser.add_argument(
            '--diaria',
            action='store_true',
            help='Executa carga diária (ontem)'
        )

    def handle(self, *args, **options):
        service = CargaLiquidacoesOwnService()
        
        if options['diaria']:
            # Carga diária
            self.stdout.write(self.style.SUCCESS('🔄 Executando carga diária de liquidações...'))
            resultado = service.executar_carga_diaria(cnpj_cliente=options.get('cnpj'))
            
        else:
            # Carga por data específica
            if not options['data']:
                self.stdout.write(self.style.ERROR('❌ Informe --data'))
                return
            
            cnpj = options.get('cnpj')
            if not cnpj:
                self.stdout.write(self.style.ERROR('❌ Informe --cnpj para carga por data'))
                return
            
            data_pagamento = datetime.strptime(options['data'], '%Y-%m-%d')
            
            self.stdout.write(self.style.SUCCESS(f'🔄 Consultando liquidações: {data_pagamento.date()}'))
            
            # Consultar liquidações
            result = service.consultar_liquidacoes(
                cnpj_cliente=cnpj,
                data_pagamento_real=data_pagamento
            )
            
            if not result.get('sucesso'):
                self.stdout.write(self.style.ERROR(f'❌ Erro: {result.get("mensagem")}'))
                return
            
            # Processar liquidações
            total_processadas = 0
            for liquidacao_data in result.get('liquidacoes', []):
                liquidacao_obj = service.salvar_liquidacao(liquidacao_data)
                if service.atualizar_status_transacao(liquidacao_obj):
                    total_processadas += 1
            
            resultado = {
                'total_liquidacoes': result.get('total', 0),
                'total_processadas': total_processadas
            }
        
        # Exibir resultado
        self.stdout.write(self.style.SUCCESS(f'✅ Carga concluída!'))
        self.stdout.write(f'   Total liquidações: {resultado.get("total_liquidacoes", 0)}')
        self.stdout.write(f'   Total processadas: {resultado.get("total_processadas", 0)}')
