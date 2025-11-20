#!/usr/bin/env python3
"""
Script de teste para consultar transações na API Own
Endpoint: POST /agilli/transacoes/v2/buscaTransacoesGerais
"""

import requests
import json
from datetime import datetime, timedelta


class OwnTransacoesAPI:
    def __init__(self, ambiente='qa'):
        """
        Inicializa o cliente da API Own para transações
        
        Args:
            ambiente: 'qa' ou 'prod'
        """
        self.base_url = (
            'https://acquirer-qa.own.financial' if ambiente == 'qa'
            else 'https://acquirer.own.financial'
        )
        self.token = None
        self.token_expira_em = None

    def autenticar(self, client_id, client_secret):
        """
        Autentica na API Own e obtém o token Bearer
        
        Args:
            client_id: Client ID fornecido pela Own
            client_secret: Client Secret fornecido pela Own
            
        Returns:
            bool: True se autenticação bem-sucedida
        """
        url = f"{self.base_url}/agilli/v2/auth"
        
        payload = {
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "wl.api_acquirer.api",
            "grant_type": "client_credentials"
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Autenticando na API Own...")
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            self.token = data.get('access_token')
            self.token_expira_em = data.get('expires_in', 300)
            
            if self.token:
                print(f"✓ Autenticação bem-sucedida")
                print(f"  Token expira em: {self.token_expira_em} segundos")
                return True
            else:
                print(f"✗ Falha na autenticação: Token não retornado")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"✗ Erro na autenticação: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  Resposta: {e.response.text[:500]}")
            return False

    def buscar_transacoes(self, cnpj_cliente, doc_parceiro=None, identificador_transacao=None,
                         status_transacao=None, data_inicial=None, data_final=None):
        """
        Busca transações gerais
        
        Args:
            cnpj_cliente: CNPJ do cliente White Label (obrigatório)
            doc_parceiro: CPF/CNPJ do estabelecimento (opcional)
            identificador_transacao: ID único da transação (opcional)
            status_transacao: Status da transação (opcional)
                - VENDA CONFIRMADA
                - VENDA ESTORNADA
                - VENDA CANCELADA
                - VENDA PENDENTE
                - VENDA LIQUIDADA
                - VENDA LIQUIDADA PARCIALMENTE
            data_inicial: Data inicial no formato "YYYY-MM-DD HH:MM" (obrigatório)
            data_final: Data final no formato "YYYY-MM-DD HH:MM" (obrigatório)
            
        Returns:
            list: Lista de transações ou None em caso de erro
        """
        if not self.token:
            print("✗ Token não disponível. Execute autenticar() primeiro.")
            return None
            
        url = f"{self.base_url}/agilli/transacoes/v2/buscaTransacoesGerais"
        
        payload = {
            "cnpjCliente": cnpj_cliente,
            "dataInicial": data_inicial,
            "dataFinal": data_final
        }
        
        # Adiciona campos opcionais apenas se tiverem valor
        if doc_parceiro:
            payload["docParceiro"] = doc_parceiro
        if identificador_transacao:
            payload["identificadorTransacao"] = identificador_transacao
        if status_transacao:
            payload["statusTransacao"] = status_transacao
        
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        try:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Buscando transações...")
            print(f"  CNPJ Cliente: {cnpj_cliente}")
            if doc_parceiro:
                print(f"  Doc Parceiro: {doc_parceiro}")
            print(f"  Período: {data_inicial} até {data_final}")
            if status_transacao:
                print(f"  Status: {status_transacao}")
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            print(f"✓ Consulta realizada com sucesso")
            print(f"  Total de transações: {len(data) if isinstance(data, list) else 0}")
            
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"✗ Erro na consulta: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  Status Code: {e.response.status_code}")
                print(f"  Resposta: {e.response.text[:500]}")
            return None

    def exibir_transacoes(self, transacoes):
        """
        Exibe as transações de forma formatada
        
        Args:
            transacoes: Lista de transações
        """
        if not transacoes:
            print("\nNenhuma transação encontrada")
            return
            
        print("\n" + "="*100)
        print("TRANSAÇÕES ENCONTRADAS")
        print("="*100)
        
        for idx, tx in enumerate(transacoes, 1):
            print(f"\n--- Transação {idx} ---")
            print(f"ID Transação:        {tx.get('identificadorTransacao', 'N/A')}")
            print(f"Data/Hora:           {tx.get('data', 'N/A')}")
            print(f"CNPJ Cliente:        {tx.get('cnpjCpfCliente', 'N/A')}")
            print(f"CNPJ Parceiro:       {tx.get('cnpjCpfParceiro', 'N/A')}")
            print(f"Valor:               R$ {tx.get('valor', 0)/100:.2f}")
            print(f"Parcelas:            {tx.get('quantidadeParcelas', 'N/A')}")
            print(f"Bandeira:            {tx.get('bandeira', 'N/A')}")
            print(f"Modalidade:          {tx.get('modalidade', 'N/A')}")
            print(f"Status:              {tx.get('statusTransacao', 'N/A')}")
            print(f"Nº Série Equip.:     {tx.get('numeroSerieEquipamento', 'N/A')}")
            print(f"Cód. Autorização:    {tx.get('codigoAutorizacao', 'N/A')}")
            print(f"Nº Cartão:           {tx.get('numeroCartao', 'N/A')}")
            print(f"MDR:                 R$ {tx.get('mdr', 0)/100:.2f}")
            print(f"Valor Antecipado:    R$ {tx.get('valorAntecipacaoTotal', 0)/100:.2f}")
            
            # Exibe parcelas se houver
            parcelas = tx.get('parcelas', [])
            if parcelas:
                print(f"\n  Parcelas ({len(parcelas)}):")
                for p in parcelas:
                    print(f"    - Parcela {p.get('numeroParcela')}: R$ {p.get('valorParcela', 0)/100:.2f} "
                          f"(Vencimento: {p.get('dataPagamentoReal', 'N/A')}) - {p.get('statusPagamento', 'N/A')}")
        
        print("\n" + "="*100)


def main():
    """
    Função principal para teste
    """
    print("="*100)
    print("TESTE API OWN - CONSULTA TRANSAÇÕES")
    print("="*100)
    
    # Credenciais da API Own (ambiente QA)
    CLIENT_ID = "54430621000134-api-acquirer.wl"
    CLIENT_SECRET = "qLzQ5AI89DKY6SvEyz6DvJ1gtm5ECl5N"
    CNPJ_CLIENTE = "54430621000134"
    
    # Período de busca (últimos 7 dias)
    data_final = datetime.now()
    data_inicial = data_final - timedelta(days=7)
    
    data_inicial_str = data_inicial.strftime("%Y-%m-%d 00:00")
    data_final_str = data_final.strftime("%Y-%m-%d 23:59")
    
    # Inicializa o cliente
    api = OwnTransacoesAPI(ambiente='qa')
    
    # 1. Autentica
    if not api.autenticar(CLIENT_ID, CLIENT_SECRET):
        print("\n✗ Falha na autenticação. Verifique as credenciais.")
        return
    
    # 2. Busca transações
    transacoes = api.buscar_transacoes(
        cnpj_cliente=CNPJ_CLIENTE,
        data_inicial=data_inicial_str,
        data_final=data_final_str
    )
    
    # 3. Exibe as transações
    if transacoes:
        api.exibir_transacoes(transacoes)
        
        # Salva em arquivo JSON
        arquivo_saida = f"transacoes_{CNPJ_CLIENTE}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(arquivo_saida, 'w', encoding='utf-8') as f:
            json.dump(transacoes, f, indent=2, ensure_ascii=False)
        print(f"\n✓ Transações salvas em: {arquivo_saida}")
    else:
        print("\n✗ Não foi possível obter as transações")
    
    print("\n" + "="*100)
    print("TESTE CONCLUÍDO")
    print("="*100)


if __name__ == "__main__":
    main()
