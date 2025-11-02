from django.core.management.base import BaseCommand
from pinbank.cargas_pinbank.services_ajustes_manuais import AjustesManuaisService
from wallclub_core.utilitarios.log_control import registrar_log


class Command(BaseCommand):
    help = 'Executa ajustes manuais de base (correções de inconsistências)'

    def handle(self, *args, **options):
        """Executa ajustes manuais de base"""
        self.stdout.write(self.style.SUCCESS('🔧 Iniciando ajustes manuais de base...'))
        
        try:
            resultado = AjustesManuaisService.ajustes_manuais_base()
            
            self.stdout.write(self.style.SUCCESS('\n✅ Ajustes concluídos com sucesso!'))
            self.stdout.write(self.style.SUCCESS(f"   📊 Inseridos em transactiondata: {resultado['inseridos_transactiondata']}"))
            self.stdout.write(self.style.SUCCESS(f"   🗑️  Duplicatas removidas de baseTransacoesGestao: {resultado['deletados_base_gestao']}"))
            
            registrar_log('pinbank.cargas_pinbank', f"Ajustes manuais concluídos - {resultado}")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Erro ao executar ajustes: {str(e)}'))
            registrar_log('pinbank.cargas_pinbank', f"Erro em ajustes manuais: {str(e)}", nivel='error')
            raise
