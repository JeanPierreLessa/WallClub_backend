"""
Management command para carga de base de gestão
Migração fiel de pinbank_cria_base_gestao.php
"""

import fcntl
import os
import sys
from django.core.management.base import BaseCommand
from django.conf import settings
from pinbank.cargas_pinbank.services import CargaBaseGestaoService


class Command(BaseCommand):
    help = 'Executa carga de base de gestão (valores primários)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--limite',
            type=int,
            default=None,
            help='Limitar número de registros processados (para teste)'
        )
        parser.add_argument(
            '--nsu',
            type=str,
            default=None,
            help='Filtrar por NSU específico (campo NsuOperacao)'
        )
    
    def handle(self, *args, **options):
        # Sistema de lock para evitar execução simultânea
        lock_file_path = '/tmp/django_pinbank_cria_base_gestao.lock'
        
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
            
            # Executar carga de valores primários
            service = CargaBaseGestaoService()
            
            self.stdout.write('Iniciando carga de base de gestão (valores primários)')
            
            limite = options.get('limite')
            nsu = options.get('nsu')
            registros_processados = service.carregar_valores_primarios(limite=limite, nsu=nsu)
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Processamento concluído: {registros_processados} registros processados')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Erro ao processar base de gestão: {str(e)}')
            )
            sys.exit(1)
            
        finally:
            # Liberar lock
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                lock_file.close()
            except:
                pass
