"""
Comando Django para executar carga da Base Unificada - Checkout OWN
Uso: python manage.py carga_base_unificada_checkout_own [--limite N] [--nsu NSU]
"""

from django.core.management.base import BaseCommand
from adquirente_own.cargas_own.services_carga_base_unificada_checkout import CargaBaseUnificadaCheckoutOwnService
from wallclub_core.utilitarios.log_control import registrar_log


class Command(BaseCommand):
    help = 'Executa carga da Base Transações Unificadas - Checkout OWN'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limite',
            type=int,
            help='Limite de registros a processar'
        )
        parser.add_argument(
            '--nsu',
            type=str,
            help='NSU específico para processar'
        )

    def handle(self, *args, **options):
        limite = options.get('limite')
        nsu = options.get('nsu')

        self.stdout.write(self.style.SUCCESS('🚀 Iniciando carga Base Unificada Checkout OWN'))

        if limite:
            self.stdout.write(f'📊 Limite: {limite} registros')
        if nsu:
            self.stdout.write(f'🔍 NSU específico: {nsu}')

        try:
            service = CargaBaseUnificadaCheckoutOwnService()
            total = service.carregar_valores_primarios(limite=limite, nsu=nsu)

            self.stdout.write(self.style.SUCCESS(f'✅ Carga concluída: {total} transações processadas'))
            registrar_log('own.cargas_own', f'✅ Carga manual concluída: {total} transações')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Erro: {str(e)}'))
            registrar_log('own.cargas_own', f'❌ Erro na carga manual: {str(e)}', nivel='ERROR')
            raise
