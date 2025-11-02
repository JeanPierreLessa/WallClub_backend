"""
Comando Django para processar carga de transações TEF
Migração do script pinbank_cria_base_gestao_tef.php
"""

from django.core.management.base import BaseCommand, CommandError
from datetime import datetime
from datetime import datetime, timedelta
from pinbank.cargas_pinbank.services import CargaTEFService
from wallclub_core.utilitarios.log_control import registrar_log


class Command(BaseCommand):
    help = 'Processa carga de transações TEF para base de gestão'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limite',
            type=int,
            default=100,
            help='Número máximo de transações para processar (padrão: 100)'
        )
        parser.add_argument(
            '--nsu',
            type=str,
            default=None,
            help='Filtrar por NSU específico (campo NsuOperacao)'
        )

    def handle(self, *args, **options):
        try:
            limite = options.get('limite', 100)
            nsu = options.get('nsu')
            
            self.stdout.write(
                self.style.SUCCESS(f'Iniciando carga TEF - Limite: {limite} transações' + 
                                 (f' - NSU: {nsu}' if nsu else ''))
            )
            
            # Registrar início da carga
            registrar_log('pinbank.cargas_pinbank', 
                         f'Início carga TEF - Limite: {limite}' + 
                         (f' - NSU: {nsu}' if nsu else ''))
            
            # Executar carga TEF
            carga_tef_service = CargaTEFService()
            resultado = carga_tef_service.processar_carga_tef(limite=limite, nsu=nsu)
            
            # Exibir resultados
            if resultado['sucesso']:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Carga TEF concluída com sucesso!')
                )
                self.stdout.write(f"📊 Transações encontradas: {resultado.get('encontradas', 0)}")
                self.stdout.write(f"⚙️  Transações processadas: {resultado.get('processadas', 0)}")
                self.stdout.write(f"💾 Registros inseridos: {resultado.get('inseridas', 0)}")
                
                # Log de sucesso
                registrar_log('pinbank.cargas_pinbank', 
                             f'Carga TEF concluída - Processadas: {resultado.get("processadas", 0)}, '
                             f'Inseridas: {resultado.get("inseridas", 0)}')
            else:
                self.stdout.write(
                    self.style.ERROR(f'❌ Erro na carga TEF: {resultado["mensagem"]}')
                )
                
                # Log de erro
                registrar_log('pinbank.cargas_pinbank', 
                             f'ERRO na carga TEF: {resultado["mensagem"]}')
                
                raise CommandError(f'Falha na carga TEF: {resultado["mensagem"]}')
                
        except Exception as e:
            error_msg = f'Erro inesperado na carga TEF: {str(e)}'
            self.stdout.write(self.style.ERROR(f'❌ {error_msg}'))
            registrar_log('pinbank.cargas_pinbank', f'ERRO: {error_msg}', nivel='ERROR')
            raise CommandError(error_msg)

    def _determinar_periodo(self, options):
        """
        Determina o período de processamento baseado nos argumentos
        """
        hoje = datetime.now().date()
        
        if options.get('data_inicial') and options.get('data_final'):
            # Período específico informado
            try:
                data_inicial = datetime.strptime(options['data_inicial'], '%Y-%m-%d').date()
                data_final = datetime.strptime(options['data_final'], '%Y-%m-%d').date()
                
                if data_inicial > data_final:
                    raise CommandError('Data inicial não pode ser maior que data final')
                    
                return data_inicial, data_final
                
            except ValueError:
                raise CommandError('Formato de data inválido. Use YYYY-MM-DD')
                
        elif options.get('data_inicial'):
            # Apenas data inicial informada
            try:
                data_inicial = datetime.strptime(options['data_inicial'], '%Y-%m-%d').date()
                return data_inicial, data_inicial
            except ValueError:
                raise CommandError('Formato de data inicial inválido. Use YYYY-MM-DD')
                
        elif options.get('data_final'):
            # Apenas data final informada
            try:
                data_final = datetime.strptime(options['data_final'], '%Y-%m-%d').date()
                return data_final, data_final
            except ValueError:
                raise CommandError('Formato de data final inválido. Use YYYY-MM-DD')
        else:
            # Usar período de dias a partir de hoje
            periodo_dias = options.get('periodo_dias', 1)
            data_inicial = hoje - timedelta(days=periodo_dias - 1)
            data_final = hoje
            
            return data_inicial, data_final
