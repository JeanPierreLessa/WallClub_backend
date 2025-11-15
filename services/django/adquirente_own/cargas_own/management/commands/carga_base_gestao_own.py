"""
Management command para processar transações Own para BaseTransacoesGestao
Uso: python manage.py carga_base_gestao_own --limite=1000
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from adquirente_own.cargas_own.models import OwnExtratoTransacoes
from adquirente_own.cargas_own.services_carga_transacoes import CargaTransacoesOwnService


class Command(BaseCommand):
    help = 'Processa transações Own não processadas para BaseTransacoesGestao'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limite',
            type=int,
            default=1000,
            help='Número máximo de registros a processar (padrão: 1000)'
        )
        parser.add_argument(
            '--identificador',
            type=str,
            help='Processar transação específica por identificador'
        )

    def handle(self, *args, **options):
        service = CargaTransacoesOwnService()
        
        if options['identificador']:
            # Processar transação específica
            identificador = options['identificador']
            
            self.stdout.write(self.style.SUCCESS(f'🔄 Processando transação: {identificador}'))
            
            try:
                transacao = OwnExtratoTransacoes.objects.get(
                    identificadorTransacao=identificador
                )
                
                with transaction.atomic():
                    base_transacao = service.processar_para_base_gestao(transacao)
                    
                self.stdout.write(self.style.SUCCESS(f'✅ Transação processada: {base_transacao.id}'))
                
            except OwnExtratoTransacoes.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'❌ Transação não encontrada: {identificador}'))
                return
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Erro ao processar: {str(e)}'))
                return
        
        else:
            # Processar transações não processadas
            limite = options['limite']
            
            self.stdout.write(self.style.SUCCESS(f'🔄 Processando até {limite} transações não processadas...'))
            
            transacoes = OwnExtratoTransacoes.objects.filter(
                processado=False
            ).order_by('data')[:limite]
            
            total = transacoes.count()
            processadas = 0
            erros = 0
            
            self.stdout.write(f'📊 Total a processar: {total}')
            
            for transacao in transacoes:
                try:
                    with transaction.atomic():
                        service.processar_para_base_gestao(transacao)
                        processadas += 1
                        
                        # Log a cada 100 registros
                        if processadas % 100 == 0:
                            self.stdout.write(f'   Processadas: {processadas}/{total}')
                            
                except Exception as e:
                    erros += 1
                    self.stdout.write(self.style.WARNING(f'⚠️ Erro em {transacao.identificadorTransacao}: {str(e)}'))
                    continue
            
            # Resultado final
            self.stdout.write(self.style.SUCCESS(f'\n✅ Processamento concluído!'))
            self.stdout.write(f'   Total processadas: {processadas}')
            self.stdout.write(f'   Total erros: {erros}')
            
            if erros > 0:
                self.stdout.write(self.style.WARNING(f'⚠️ {erros} transações com erro'))
