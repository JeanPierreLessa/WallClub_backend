"""
Management command para executar carga completa da Base Unificada
Executa POS, Credenciadora e Checkout em sequência
"""
from django.core.management.base import BaseCommand
from pinbank.cargas_pinbank.services_carga_base_unificada_pos import CargaBaseUnificadaPOSService
from pinbank.cargas_pinbank.services_carga_base_unificada_credenciadora import CargaBaseUnificadaCredenciadoraService
from pinbank.cargas_pinbank.services_carga_base_unificada_checkout import CargaBaseUnificadaCheckoutService


class Command(BaseCommand):
    help = 'Executa carga completa da Base Unificada (POS + Credenciadora + Checkout)'

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
        parser.add_argument(
            '--worker_id',
            type=int,
            help='ID do worker para processamento paralelo (0-9)',
        )

    def handle(self, *args, **options):
        limite = options.get('limite')
        nsu = options.get('nsu')
        worker_id = options.get('worker_id')

        # 1. Processar POS
        service_pos = CargaBaseUnificadaPOSService()
        registros_pos = service_pos.carregar_valores_primarios(limite=limite, nsu=nsu, worker_id=worker_id)

        # 2. Processar Credenciadora
        service_credenciadora = CargaBaseUnificadaCredenciadoraService()
        registros_credenciadora = service_credenciadora.carregar_valores_primarios(limite=limite, nsu=nsu, worker_id=worker_id)

        # 3. Processar Checkout
        service_checkout = CargaBaseUnificadaCheckoutService()
        registros_checkout = service_checkout.carregar_valores_primarios(limite=limite, nsu=nsu, worker_id=worker_id)

        # 4. Atualizar cancelamentos
        cancelamentos_atualizados = service_credenciadora.atualizar_cancelamentos()

        # Resumo
        total = registros_pos + registros_credenciadora + registros_checkout
        if worker_id is not None:
            self.stdout.write(self.style.SUCCESS(f'\n=== Worker {worker_id} concluído: {total} registros ==='))
        else:
            self.stdout.write(self.style.SUCCESS(f'\n=== Carga concluída: {total} registros no total ==='))
