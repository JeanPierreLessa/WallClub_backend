"""
Service para sincronização de transações do app Android
Extraído de posp2/services.py
"""
import json
from datetime import datetime
from typing import Dict, Any, List
from django.db import connection

from .models import POSP2Transaction
from wallclub_core.utilitarios.log_control import registrar_log


class TransactionSyncService:
    """
    Serviço para sincronização de transações do app Android
    Migração fiel de TransactionSyncService.php
    """
    
    def __init__(self):
        pass
    
    def sincronizar_transacoes(self, transacoes_data: List[Dict]) -> Dict[str, Any]:
        """
        Sincroniza array de transações do app Android
        Replicando exatamente a lógica do PHP
        """
        try:
            registrar_log('posp2', f'posp2.transaction_sync - Iniciando sincronização de {len(transacoes_data)} transações')
            
            # Contadores como no PHP
            total_processed = 0
            total_success = 0
            total_errors = 0
            
            # Arrays como no PHP
            success_transactions = []
            duplicate_transactions = []
            error_messages = []
            
            # Processar cada transação individualmente (como no PHP)
            for transaction in transacoes_data:
                total_processed += 1
                registrar_log('posp2', f'posp2.transaction_sync - Processando transação #{total_processed}')
                
                try:
                    # Verificar campos obrigatórios
                    if not transaction.get("id") or not transaction.get("transaction_data"):
                        error_messages.append({
                            "id": transaction.get("id", "unknown"),
                            "error": "Campos obrigatórios ausentes (id ou transaction_data)",
                            "error_code": "MISSING_FIELDS"
                        })
                        total_errors += 1
                        registrar_log('posp2', 'posp2.transaction_sync - Transação rejeitada: campos obrigatórios ausentes')
                        continue
                    
                    # Extrair dados da transação (como no PHP)
                    transaction_id = transaction["id"]
                    transaction_data = transaction["transaction_data"]
                    cpf = transaction.get("cpf", "")
                    celular = transaction.get("celular", "")
                    terminal = transaction.get("terminal", "")
                    valor_original = transaction.get("valor_original", "0")
                    retry_count = transaction.get("retry_count", 0)
                    
                    # Extrair dados para idempotência (como no PHP)
                    tr_data = {}
                    nsu = "N/A"
                    timestamp = int(datetime.now().timestamp())
                    
                    try:
                        tr_data = json.loads(transaction_data)
                        if isinstance(tr_data, dict):
                            if tr_data.get('nsu'):
                                nsu = tr_data['nsu']
                            if tr_data.get('timestamp'):
                                timestamp = tr_data['timestamp']
                    except:
                        if transaction.get('nsu'):
                            nsu = transaction['nsu']
                    
                    # Gerar ou usar idempotency_key (como no PHP)
                    if transaction.get('idempotency_key') and transaction['idempotency_key'].strip():
                        idempotency_key = transaction['idempotency_key']
                        registrar_log('posp2', f'posp2.transaction_sync - Usando idempotency_key enviado pelo app: {idempotency_key}')
                    else:
                        # Fallback: gerar chave de idempotência (compatibilidade com versões antigas)
                        idempotency_key = f"{terminal}_{nsu}_{timestamp}_{valor_original}"
                        registrar_log('posp2', f'posp2.transaction_sync - App não enviou idempotency_key. Gerando no servidor: {idempotency_key}')
                    
                    # Log de debug
                    registrar_log('posp2', f'posp2.transaction_sync - Processando transação ID: {transaction_id}')
                    registrar_log('posp2', f'posp2.transaction_sync - Terminal: {terminal}, NSU: {nsu}')
                    registrar_log('posp2', f'posp2.transaction_sync - Chave de idempotência: {idempotency_key}')
                    registrar_log('posp2', f'posp2.transaction_sync - Tentativa #{retry_count + 1}')
                    
                    # Verificar se a transação já existe (idempotência)
                    registrar_log('posp2', f'posp2.transaction_sync - Verificando duplicidade por idempotency_key: {idempotency_key}')
                    transacao_existente = POSP2Transaction.objects.filter(
                        idempotency_key=idempotency_key
                    ).first()
                    
                    if transacao_existente:
                        registrar_log('posp2', f'posp2.transaction_sync - Transação duplicada detectada: terminal={terminal}, nsu={nsu}')
                        duplicate_transactions.append({
                            "id": transaction_id,
                            "nsu": nsu,
                            "status": "duplicate",
                            "idempotency_key": idempotency_key,
                            "message": "Transação já processada anteriormente"
                        })
                        total_success += 1  # Consideramos como sucesso pois a transação já existe
                        continue
                    
                    # Usar transação atômica individual (como mysqli_begin_transaction no PHP)
                    from django.db import transaction as db_transaction
                    with db_transaction.atomic():
                        # INSERT com ON DUPLICATE KEY UPDATE via SQL raw (como no PHP)
                        with connection.cursor() as cursor:
                            sql = """
                                INSERT INTO posp2_transactions (
                                    transaction_id, transaction_data, cpf, celular, terminal, valor_original, idempotency_key
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                                ON DUPLICATE KEY UPDATE
                                    transaction_data = VALUES(transaction_data),
                                    cpf = VALUES(cpf),
                                    celular = VALUES(celular),
                                    terminal = VALUES(terminal),
                                    valor_original = VALUES(valor_original),
                                    idempotency_key = VALUES(idempotency_key)
                            """
                            
                            cursor.execute(sql, [
                                transaction_id, transaction_data, cpf, celular, 
                                terminal, valor_original, idempotency_key
                            ])
                        
                        total_success += 1
                        
                        # Adicionar à lista de transações bem-sucedidas (como no PHP)
                        success_transactions.append({
                            "id": transaction_id,
                            "nsu": nsu,
                            "status": "success",
                            "terminal": terminal,
                            "idempotency_key": idempotency_key,
                            "retry_count": retry_count,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        
                        registrar_log('posp2', f'posp2.transaction_sync - Transação ID: {transaction_id} processada com sucesso')
                
                except Exception as e:
                    error_msg = str(e)
                    registrar_log('posp2', f'posp2.transaction_sync - Exceção ao processar transação: {error_msg}')
                    error_messages.append({
                        "id": transaction.get("id", "unknown"),
                        "nsu": nsu if 'nsu' in locals() else "N/A",
                        "error": f"Exceção ao processar transação: {error_msg}",
                        "error_code": "EXCEPTION",
                        "retry_count": transaction.get("retry_count", 0)
                    })
                    total_errors += 1
            
            registrar_log('posp2', f'posp2.transaction_sync - Processamento concluído. Sucessos: {total_success}, Erros: {total_errors}, Duplicatas: {len(duplicate_transactions)}')
            
            # Preparar resposta
            response = {
                "sucesso": total_errors == 0,
                "mensagem": "Processamento concluído",
                "total_processed": total_processed,
                "total_success": total_success,
                "total_errors": total_errors,
                "total_duplicates": len(duplicate_transactions),
                "success_transactions": success_transactions,
                "duplicates": duplicate_transactions,
                "errors": error_messages,
                "server_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "api_version": "2.1.0"
            }
            
            registrar_log('posp2', f'posp2.transaction_sync - Resposta JSON: {json.dumps(response)}')
            
            return response
            
        except Exception as e:
            registrar_log('posp2', f'ERRO GERAL em transaction_sync: {str(e)}', nivel='ERROR')
            
            # Preparar resposta de erro
            return {
                "sucesso": False,
                "mensagem": f"Erro ao processar dados: {str(e)}"
            }
