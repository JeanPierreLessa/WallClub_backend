"""
Management command para executar carga da Base Unificada - Credenciadora
"""
from django.core.management.base import BaseCommand
from pinbank.cargas_pinbank.services_carga_base_unificada_credenciadora import CargaBaseUnificadaCredenciadoraService


class Command(BaseCommand):
    help = 'Executa carga de valores primários na Base Transações Unificadas - Credenciadora'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limite',
            type=int,
            help='Limite de registros a processar (para testes)',
        )
        parser.add_argument(
            '--nsu',
            type=str,
            help='NSU específico para processar (para debug)',
        )

    def handle(self, *args, **options):
        limite = options.get('limite')
        nsu = options.get('nsu')

        self.stdout.write(self.style.SUCCESS('Iniciando carga de base unificada Credenciadora (valores primários)'))

        service = CargaBaseUnificadaCredenciadoraService()
        registros_processados = service.carregar_valores_primarios(limite=limite, nsu=nsu)

        self.stdout.write(
            self.style.SUCCESS(f'✅ Processamento concluído: {registros_processados} registros processados')
        )
