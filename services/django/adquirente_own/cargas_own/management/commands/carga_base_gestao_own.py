"""
Management command para processar transações Own para BaseTransacoesGestao
Uso: python manage.py carga_base_gestao_own --limite=1000
"""

from django.core.management.base import BaseCommand
from adquirente_own.cargas_own.services_carga_base_unificada_pos import CargaBaseUnificadaOwnService


class Command(BaseCommand):
    help = 'Executa carga de valores primários na Base Transações Unificadas - Own'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limite',
            type=int,
            default=None,
            help='Limite de registros a processar'
        )
        parser.add_argument(
            '--identificador',
            type=str,
            default=None,
            help='Identificador específico da transação'
        )

    def handle(self, *args, **options):
        service = CargaBaseUnificadaOwnService()
        
        limite = options['limite']
        identificador = options['identificador']
        
        if identificador:
            self.stdout.write(self.style.SUCCESS(f' Processando transação específica: {identificador}'))
        else:
            msg = f'🔄 Processando transações Own não lidas'
            if limite:
                msg += f' (limite: {limite})'
            self.stdout.write(self.style.SUCCESS(msg))
        
        try:
            registros_processados = service.carregar_valores_primarios(
                limite=limite,
                identificador=identificador
            )
            
            # Resultado final
            self.stdout.write(self.style.SUCCESS(f'\n✅ Processamento concluído!'))
            self.stdout.write(f'   Total processadas: {registros_processados}')
            
        except Exception as e:
            import traceback
            erro_completo = traceback.format_exc()
            self.stdout.write(self.style.ERROR(f'❌ Erro ao processar: {str(e)}'))
            self.stdout.write(self.style.ERROR(f'Traceback: {erro_completo}'))
            return
