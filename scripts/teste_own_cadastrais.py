#!/usr/bin/env python3
"""
Script de teste para consultar dados cadastrais na API Own
CNPJ: 52230932000124
"""

import requests
import json
from datetime import datetime


class OwnAPITester:
    def __init__(self, ambiente='qa'):
        """
        Inicializa o testador da API Own

        Args:
            ambiente: 'qa' ou 'prod'
        """
        self.base_url = (
            'https://acquirer-qa.own.financial' if ambiente == 'qa'
            else 'https://acquirer.own.financial'
        )
        self.token = None

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
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()

            data = response.json()
            self.token = data.get('access_token')

            if self.token:
                print(f"✓ Autenticação bem-sucedida")
                print(f"  Token expira em: {data.get('expires_in')} segundos")
                return True
            else:
                print(f"✗ Falha na autenticação: Token não retornado")
                return False

        except requests.exceptions.RequestException as e:
            print(f"✗ Erro na autenticação: {e}")
            if hasattr(e.response, 'text'):
                print(f"  Resposta: {e.response.text}")
            return False

    def consultar_cadastrais(self, cnpj=None, contrato=None, data_cadastro=None):
        """
        Consulta dados cadastrais de um estabelecimento

        Args:
            cnpj: CNPJ do estabelecimento
            contrato: Número do contrato
            data_cadastro: Data de cadastro (formato: YYYY-MM-DD)

        Returns:
            dict: Dados cadastrais ou None em caso de erro
        """
        if not self.token:
            print("✗ Token não disponível. Execute autenticar() primeiro.")
            return None

        url = f"{self.base_url}/agilli/indicadores/v2/cadastrais"

        # Monta os parâmetros (pelo menos 1 obrigatório)
        params = {}
        if cnpj:
            params['cpfCnpj'] = cnpj
        if contrato:
            params['contrato'] = contrato
        if data_cadastro:
            params['dataCadastro'] = data_cadastro

        if not params:
            print("✗ Informe pelo menos um parâmetro: cnpj, contrato ou data_cadastro")
            return None

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        try:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Consultando dados cadastrais...")
            print(f"  Parâmetros: {params}")

            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()

            data = response.json()

            print(f"✓ Consulta realizada com sucesso")
            print(f"  Total de registros: {len(data) if isinstance(data, list) else 1}")

            return data

        except requests.exceptions.RequestException as e:
            print(f"✗ Erro na consulta: {e}")
            if hasattr(e.response, 'text'):
                print(f"  Resposta: {e.response.text}")
            return None

    def exibir_dados_cadastrais(self, dados):
        """
        Exibe os dados cadastrais de forma formatada

        Args:
            dados: Lista ou dict com dados cadastrais
        """
        if not dados:
            print("\nNenhum dado para exibir")
            return

        # Garante que seja uma lista
        if not isinstance(dados, list):
            dados = [dados]

        print("\n" + "="*80)
        print("DADOS CADASTRAIS")
        print("="*80)

        for idx, registro in enumerate(dados, 1):
            print(f"\n--- Registro {idx} ---")
            print(f"CNPJ/CPF:        {registro.get('cnpj', 'N/A')}")
            print(f"Contrato:        {registro.get('contrato', 'N/A')}")
            print(f"Razão Social:    {registro.get('razaoSocial', 'N/A')}")
            print(f"Nome Fantasia:   {registro.get('nomeFantasia', 'N/A')}")
            print(f"Modalidade:      {registro.get('modalidade', 'N/A')}")
            print(f"Valor Tarifa:    R$ {registro.get('valor', 0):.2f}")
            print(f"MCC:             {registro.get('mcc', 'N/A')}")
            print(f"Cidade/UF:       {registro.get('cidade', 'N/A')}/{registro.get('uf', 'N/A')}")
            print(f"Data Entrada:    {registro.get('dataEntrada', 'N/A')}")

        print("\n" + "="*80)


def main():
    """
    Função principal para teste
    """
    print("="*80)
    print("TESTE API OWN - CONSULTA DADOS CADASTRAIS")
    print("="*80)

    # CNPJ a ser testado
    CNPJ_TESTE = "54430621000134"

    # Credenciais da API Own (ambiente QA)
    CLIENT_ID = "54430621000134-api-acquirer.wl"
    CLIENT_SECRET = "qLzQ5AI89DKY6SvEyz6DvJ1gtm5ECl5N"

    # Valida credenciais
    if "SEU_CLIENT_ID" in CLIENT_ID or "SEU_CLIENT_SECRET" in CLIENT_SECRET:
        print("\n⚠️  ATENÇÃO: Configure as credenciais no script antes de executar!")
        print("   CLIENT_ID e CLIENT_SECRET devem ser fornecidos pela Own")
        return

    # Inicializa o testador
    tester = OwnAPITester(ambiente='qa')

    # 1. Autentica
    if not tester.autenticar(CLIENT_ID, CLIENT_SECRET):
        print("\n✗ Falha na autenticação. Verifique as credenciais.")
        return

    # 2. Consulta dados cadastrais pelo CNPJ
    dados = tester.consultar_cadastrais(cnpj=CNPJ_TESTE)

    # 3. Exibe os dados
    if dados:
        tester.exibir_dados_cadastrais(dados)

        # Salva em arquivo JSON
        arquivo_saida = f"dados_cadastrais_{CNPJ_TESTE}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(arquivo_saida, 'w', encoding='utf-8') as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)
        print(f"\n✓ Dados salvos em: {arquivo_saida}")
    else:
        print("\n✗ Não foi possível obter os dados cadastrais")


if __name__ == "__main__":
    main()
