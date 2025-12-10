"""
Management command para executar carga completa da Base Unificada
Executa POS e Credenciadora em sequência
"""
from django.core.management.base import BaseCommand
from pinbank.cargas_pinbank.services_carga_base_unificada_pos import CargaBaseUnificadaPOSService
from pinbank.cargas_pinbank.services_carga_base_unificada_credenciadora import CargaBaseUnificadaCredenciadoraService


class Command(BaseCommand):
    help = 'Executa carga completa da Base Unificada (POS + Credenciadora)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limite',
            type=int,
            help='Limite de registros a processar por tipo (para testes)',
        )
        parser.add_argument(
            '--nsu',
            type=str,
            help='NSU específico para processar (para debug)',
        )

    def handle(self, *args, **options):
        limite = options.get('limite')
        nsu = options.get('nsu')

        self.stdout.write(self.style.SUCCESS('=== Iniciando carga Base Unificada ==='))

        # 1. Processar POS
        self.stdout.write(self.style.SUCCESS('\n[1/2] Processando POS...'))
        service_pos = CargaBaseUnificadaPOSService()
        registros_pos = service_pos.carregar_valores_primarios(limite=limite, nsu=nsu)
        self.stdout.write(self.style.SUCCESS(f'✅ POS: {registros_pos} registros processados'))

        # 2. Processar Credenciadora
        self.stdout.write(self.style.SUCCESS('\n[2/2] Processando Credenciadora...'))
        service_credenciadora = CargaBaseUnificadaCredenciadoraService()
        registros_credenciadora = service_credenciadora.carregar_valores_primarios(limite=limite, nsu=nsu)
        self.stdout.write(self.style.SUCCESS(f'✅ Credenciadora: {registros_credenciadora} registros processados'))

        # Resumo
        total = registros_pos + registros_credenciadora
        self.stdout.write(self.style.SUCCESS(f'\n=== Carga concluída: {total} registros no total ==='))
