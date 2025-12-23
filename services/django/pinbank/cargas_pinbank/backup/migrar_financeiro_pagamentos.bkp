from django.core.management.base import BaseCommand
from django.db import connections, transaction
# import logging - removido, usando registrar_log
from wallclub_core.utilitarios.log_control import registrar_log

class Command(BaseCommand):
    help = 'Migra dados da tabela financeiro (wclub) para pagamentos_efetuados (wallclub)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limite',
            type=int,
            default=1000,
            help='Limite de registros a processar por execução (padrão: 1000)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Executa sem fazer alterações no banco (apenas mostra o que seria feito)'
        )

    def handle(self, *args, **options):
        limite = options['limite']
        dry_run = options['dry_run']
        
        self.stdout.write(f"🔄 Iniciando migração financeiro → pagamentos_efetuados")
        self.stdout.write(f"📊 Limite: {limite} registros")
        if dry_run:
            self.stdout.write("🧪 Modo DRY-RUN ativado")
        
        try:
            with transaction.atomic():
                cursor = connections['default'].cursor()
                
                # Query para buscar registros a migrar
                sql_buscar = """
                SELECT 
                    CAST(nsu AS UNSIGNED) as nsu,
                    -- var44: campo 44 (DECIMAL)
                    CASE 
                        WHEN (SELECT valor FROM wclub.financeiro f44 WHERE f44.nsu = f.nsu AND f44.campo = 44 LIMIT 1) = '' THEN NULL
                        ELSE CAST((SELECT valor FROM wclub.financeiro f44 WHERE f44.nsu = f.nsu AND f44.campo = 44 LIMIT 1) AS DECIMAL(8,2))
                    END as var44,
                    
                    -- var45: campo 45 (VARCHAR)
                    NULLIF((SELECT valor FROM wclub.financeiro f45 WHERE f45.nsu = f.nsu AND f45.campo = 45 LIMIT 1), '') as var45,
                    
                    -- var58: campo 58 (DECIMAL)
                    CASE 
                        WHEN (SELECT valor FROM wclub.financeiro f58 WHERE f58.nsu = f.nsu AND f58.campo = 58 LIMIT 1) = '' THEN NULL
                        ELSE CAST((SELECT valor FROM wclub.financeiro f58 WHERE f58.nsu = f.nsu AND f58.campo = 58 LIMIT 1) AS DECIMAL(8,2))
                    END as var58,
                    
                    -- var59: campo 59 (VARCHAR)
                    NULLIF((SELECT valor FROM wclub.financeiro f59 WHERE f59.nsu = f.nsu AND f59.campo = 59 LIMIT 1), '') as var59,
                    
                    -- var66: campo 66 (VARCHAR)
                    NULLIF((SELECT valor FROM wclub.financeiro f66 WHERE f66.nsu = f.nsu AND f66.campo = 66 LIMIT 1), '') as var66,
                    
                    -- var71: campo 71 (VARCHAR)
                    NULLIF((SELECT valor FROM wclub.financeiro f71 WHERE f71.nsu = f.nsu AND f71.campo = 71 LIMIT 1), '') as var71,
                    
                    -- var100: campo 100 (VARCHAR)
                    NULLIF((SELECT valor FROM wclub.financeiro f100 WHERE f100.nsu = f.nsu AND f100.campo = 100 LIMIT 1), '') as var100,
                    
                    -- var111: campo 111 (DECIMAL)
                    CASE 
                        WHEN (SELECT valor FROM wclub.financeiro f111 WHERE f111.nsu = f.nsu AND f111.campo = 111 LIMIT 1) = '' THEN NULL
                        ELSE CAST((SELECT valor FROM wclub.financeiro f111 WHERE f111.nsu = f.nsu AND f111.campo = 111 LIMIT 1) AS DECIMAL(8,2))
                    END as var111,
                    
                    -- var112: campo 112 (DECIMAL)
                    CASE 
                        WHEN (SELECT valor FROM wclub.financeiro f112 WHERE f112.nsu = f.nsu AND f112.campo = 112 LIMIT 1) = '' THEN NULL
                        ELSE CAST((SELECT valor FROM wclub.financeiro f112 WHERE f112.nsu = f.nsu AND f112.campo = 112 LIMIT 1) AS DECIMAL(8,2))
                    END as var112
                    
                FROM (
                    SELECT DISTINCT nsu 
                    FROM wclub.financeiro 
                    WHERE campo IN (44, 45, 58, 59, 66, 71, 100, 111, 112)
                    AND nsu IS NOT NULL 
                    AND nsu != ''
                    AND nsu REGEXP '^[0-9]+$'
                    AND NOT EXISTS ( 
                        SELECT 1 
                        FROM wallclub.pagamentos_efetuados pe 
                        WHERE pe.nsu = CAST(financeiro.nsu AS UNSIGNED)
                    )
                    LIMIT %s
                ) f
                """
                
                if dry_run:
                    # Apenas contar quantos registros seriam processados
                    sql_count = """
                    SELECT COUNT(DISTINCT nsu) as total
                    FROM wclub.financeiro 
                    WHERE campo IN (44, 45, 58, 59, 66, 71, 100, 111, 112)
                    AND nsu IS NOT NULL 
                    AND nsu != ''
                    AND nsu REGEXP '^[0-9]+$'
                    AND NOT EXISTS ( 
                        SELECT 1 
                        FROM wallclub.pagamentos_efetuados pe 
                        WHERE pe.nsu = CAST(financeiro.nsu AS UNSIGNED)
                    )
                    LIMIT %s
                    """
                    cursor.execute(sql_count, [limite])
                    result = cursor.fetchone()
                    total_pendentes = result[0] if result else 0
                    
                    self.stdout.write(f"🧪 DRY-RUN: {total_pendentes} registros seriam migrados")
                    return
                
                # Buscar registros para migrar
                cursor.execute(sql_buscar, [limite])
                registros = cursor.fetchall()
                
                self.stdout.write(f"📊 Encontrados {len(registros)} registros para migrar")
                
                registros_inseridos = 0
                registros_atualizados = 0
                
                # Processar cada registro individualmente
                for registro in registros:
                    nsu, var44, var45, var58, var59, var66, var71, var100, var111, var112 = registro
                    
                    # Inserir em pagamentos_efetuados
                    cursor.execute("""
                        INSERT INTO wallclub.pagamentos_efetuados (
                            nsu, var44, var45, var58, var59, var66, var71, var100, var111, var112,
                            created_at, user_id
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), 1)
                    """, [nsu, var44, var45, var58, var59, var66, var71, var100, var111, var112])
                    
                    registros_inseridos += 1
                    
                    # Atualizar lido = 0 em pinbankExtratoPOS para este NSU
                    cursor.execute("""
                        UPDATE wallclub.pinbankExtratoPOS 
                        SET Lido = 0 
                        WHERE NsuOperacao = %s
                    """, [str(nsu)])
                    
                    if cursor.rowcount > 0:
                        registros_atualizados += 1
                
                self.stdout.write(f"✅ Migração concluída: {registros_inseridos} registros inseridos")
                self.stdout.write(f"🔄 Marcados {registros_atualizados} registros para reprocessamento (Lido = 0)")
                
                # Verificar resultado
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_registros,
                        COUNT(DISTINCT nsu) as nsus_unicos,
                        COUNT(var44) as var44_preenchidos,
                        COUNT(var45) as var45_preenchidos,
                        COUNT(var58) as var58_preenchidos,
                        COUNT(var59) as var59_preenchidos,
                        COUNT(var66) as var66_preenchidos,
                        COUNT(var71) as var71_preenchidos,
                        COUNT(var100) as var100_preenchidos,
                        COUNT(var111) as var111_preenchidos,
                        COUNT(var112) as var112_preenchidos
                    FROM wallclub.pagamentos_efetuados
                """)
                
                stats = cursor.fetchone()
                
                self.stdout.write(f"✅ Migração concluída!")
                self.stdout.write(f"📊 Registros inseridos nesta execução: {registros_inseridos}")
                self.stdout.write(f"📊 Total na tabela pagamentos_efetuados: {stats[0]}")
                self.stdout.write(f"📊 NSUs únicos: {stats[1]}")
                self.stdout.write(f"📊 Campos preenchidos:")
                self.stdout.write(f"   - var44: {stats[2]}")
                self.stdout.write(f"   - var45: {stats[3]}")
                self.stdout.write(f"   - var58: {stats[4]}")
                self.stdout.write(f"   - var59: {stats[5]}")
                self.stdout.write(f"   - var66: {stats[6]}")
                self.stdout.write(f"   - var71: {stats[7]}")
                self.stdout.write(f"   - var100: {stats[8]}")
                self.stdout.write(f"   - var111: {stats[9]}")
                self.stdout.write(f"   - var112: {stats[10]}")
                
                # Log para arquivo
                registrar_log('pinbank.cargas_pinbank', f"Migração financeiro→pagamentos_efetuados: {registros_inseridos} registros inseridos, {registros_atualizados} marcados para reprocessamento")
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Erro na migração: {str(e)}")
            )
            registrar_log('pinbank.cargas_pinbank', f"Erro na migração financeiro→pagamentos_efetuados: {str(e)}", nivel='ERROR')
            raise
