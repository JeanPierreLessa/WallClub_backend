# Configuração de Certificados APN

## Estrutura de Arquivos

Coloque os certificados APN neste diretório com a seguinte nomenclatura:

```
apn_configs/
├── wallclub_apn_cert.pem    # Certificado para canal WallClub
├── wallclub_apn_key.pem     # Chave privada para canal WallClub
├── aclub_apn_cert.pem       # Certificado para canal AClub
├── aclub_apn_key.pem        # Chave privada para canal AClub
└── README.md                # Este arquivo
```

## Processo de Criação dos Certificados

### 1. Apple Developer Console
1. Acesse https://developer.apple.com
2. Vá em **Certificates, Identifiers & Profiles**
3. Crie **App ID** com Push Notifications habilitado
4. Crie certificado **Apple Push Notification service SSL**

### 2. Gerar CSR no Mac
```bash
# No Keychain Access:
# Menu → Certificate Assistant → Request Certificate from CA
# Salvar como .certSigningRequest
```

### 3. Converter Certificados
```bash
# Após download do .cer e exportação como .p12:
openssl pkcs12 -in certificado.p12 -out apn_cert.pem -clcerts -nokeys
openssl pkcs12 -in certificado.p12 -out apn_key.pem -nocerts -nodes
```

### 4. Configuração no Banco
Atualizar tabela `canal` com os nomes dos arquivos:

```sql
UPDATE canal 
SET apn_cert_path = 'wallclub_apn_cert.pem', 
    apn_key_path = 'wallclub_apn_key.pem' 
WHERE id = 1;

UPDATE canal 
SET apn_cert_path = 'aclub_apn_cert.pem', 
    apn_key_path = 'aclub_apn_key.pem' 
WHERE id = 6;
```

## Segurança

- **NUNCA** commitar certificados no Git
- Adicionar `*.pem` no .gitignore
- Usar permissões 600 nos arquivos de certificado
- Renovar certificados anualmente
