"""
Management command para carga de extrato POS
Migração fiel de pinbank_carga_extrato_pos.php
"""

import fcntl
import os
import sys
from django.core.management.base import BaseCommand
from django.conf import settings
from pinbank.cargas_pinbank.services import CargaExtratoPOSService


class Command(BaseCommand):
    help = 'Executa carga de extrato POS da Pinbank'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'modo',
            nargs='?',
            default='30dias',
            choices=['80min', '30min', '72h', '60dias', '90dias', '30dias', 'ano'],
            help='Modo de execução: 30dias (padrão), 80min, 72h, 60dias, 90dias, ano'
        )
    
    def handle(self, *args, **options):
        # Sistema de lock para evitar execução simultânea
        lock_file_path = '/tmp/django_pinbank_carga_extrato_pos.lock'
        
        try:
            lock_file = open(lock_file_path, 'w')
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (IOError, OSError):
            self.stdout.write(
                self.style.WARNING('Já em execução. Abortando.')
            )
            sys.exit(1)
        
        try:
            # Criar diretório de logs se não existir
            log_dir = os.path.join(settings.BASE_DIR, 'logs')
            os.makedirs(log_dir, exist_ok=True)
            
            # Executar carga conforme modo
            modo = options['modo']
            service = CargaExtratoPOSService()
            
            self.stdout.write(f'Iniciando carga de extrato POS - Modo: {modo}')
            
            if modo == 'ano':
                transacoes = service.buscar_ultimo_ano()
            elif modo == '90dias':
                transacoes = service.buscar_ultimos_90_dias()
            elif modo == '60dias':
                transacoes = service.buscar_ultimos_60_dias()
            elif modo == '72h':
                transacoes = service.buscar_ultimas_72_horas()
            elif modo == '80min':
                transacoes = service.buscar_ultimos_80_minutos()
            else:  # 30dias (padrão)
                transacoes = service.buscar_ultimos_30_dias()
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Processamento concluído: {transacoes} transações processadas')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Erro ao processar transações: {str(e)}')
            )
            sys.exit(1)
            
        finally:
            # Liberar lock
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                lock_file.close()
            except:
                pass
