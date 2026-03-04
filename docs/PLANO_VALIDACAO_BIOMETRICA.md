# Plano de Execução - Validação Biométrica no Checkout

**Branch:** `release-teste-validacao-biometrica`

## Arquitetura Escolhida (Opção B - Ajustada)

- **OCR Documento:** Google Cloud Vision API
- **Liveness Detection:** FaceTec
- **Face Match:** AWS Rekognition
- **Validação CPF:** BigDataCorp (já integrado ✅)

---

## Fase 1: Setup e Credenciais ✅ CONCLUÍDA

### 1.1 FaceTec ✅
- [x] Criar conta em https://dev.facetec.com/
- [x] Obter SDK License Key (Device Key: dkZKeF3jEivGCthkIQPypNFfDGeeSyTK)
- [x] Configurar credenciais no `.env`
- [ ] Baixar SDK JavaScript/React Native (próxima fase)
- [ ] Revisar documentação de integração (próxima fase)
- [ ] Estimar custos por transação

### 1.2 Google Cloud Vision ✅ (substituiu Microblink)
- [x] Criar conta no Google Cloud Platform
- [x] Ativar Vision API
- [x] Criar Service Account e baixar credenciais JSON
- [x] Configurar credenciais no projeto (`biometria/chaves/`)
- [x] Testar OCR com CNH - **Sucesso: extraiu nome, CPF, RG, data nascimento**
- [x] Instalar biblioteca `google-cloud-vision==3.7.0`

**Nota:** Microblink foi substituído por Google Cloud Vision pois não permite trial self-service.

### 1.3 AWS Rekognition ✅
- [x] Verificar credenciais AWS existentes
- [x] Habilitar serviço Rekognition na conta
- [x] Configurar IAM Groups (WallClubRekognitionGroup, WallClubSecretsManagerGroup, WallClubS3BiometriaGroup)
- [x] Configurar credenciais no `.env` do backend
- [x] Testar API CompareFaces - **Resultado: 99.85% de similaridade**
- [x] Estimar custos por transação - **$0.001 por comparação**

**Entregável:** ✅ AWS Rekognition configurado e testado com sucesso

---

## Fase 2: POC FaceTec - Liveness Detection (3-5 dias)

### 2.1 Backend
- [ ] Criar service `BiometriaService` em `/services/django/checkout/services_biometria.py`
- [ ] Implementar endpoint `/api/checkout/biometria/liveness/` para receber resultado FaceTec
- [ ] Validar assinatura/token do FaceTec Server
- [ ] Armazenar foto da selfie temporariamente (S3 ou local)
- [ ] Criar modelo `ValidacaoBiometrica` para log de tentativas

### 2.2 Frontend (Mobile/Web)
- [ ] Integrar FaceTec SDK no app mobile
- [ ] Criar tela de captura de selfie com liveness
- [ ] Implementar fluxo de erro/retry
- [ ] Testar em diferentes dispositivos

### 2.3 Testes
- [ ] Testar liveness com pessoas reais
- [ ] Testar tentativas de fraude (foto de foto, vídeo)
- [ ] Validar taxa de sucesso (>95%)

**Entregável:** Endpoint funcional + tela mobile capturando selfie com liveness

---

## Fase 3: POC Microblink - OCR Documento (3-5 dias)

### 3.1 Backend
- [ ] Criar método `extrair_dados_documento()` no `BiometriaService`
- [ ] Integrar API Microblink BlinkID
- [ ] Implementar endpoint `/api/checkout/biometria/ocr/` para upload de documento
- [ ] Extrair: CPF, nome, data nascimento, número documento, foto do documento
- [ ] Validar qualidade da imagem (blur, glare)
- [ ] Armazenar imagem do documento temporariamente

### 3.2 Frontend
- [ ] Criar tela de captura de documento (frente e verso se CNH)
- [ ] Implementar guias visuais para posicionamento
- [ ] Validar qualidade antes de enviar
- [ ] Mostrar dados extraídos para confirmação do usuário

### 3.3 Testes
- [ ] Testar com RG (vários estados)
- [ ] Testar com CNH (nova e antiga)
- [ ] Validar taxa de extração correta (>90%)
- [ ] Testar com documentos danificados/antigos

**Entregável:** Endpoint funcional extraindo dados de RG/CNH

---

## Fase 4: Integração AWS Rekognition - Face Match (2-3 dias)

### 4.1 Backend
- [ ] Criar método `comparar_faces()` no `BiometriaService`
- [ ] Integrar AWS Rekognition API `compare_faces()`
- [ ] Implementar endpoint `/api/checkout/biometria/face-match/`
- [ ] Definir threshold de similaridade (recomendado: 90%)
- [ ] Retornar score de confiança
- [ ] Tratar erros (face não detectada, múltiplas faces)

### 4.2 Lógica de Validação
- [ ] Comparar selfie (FaceTec) com foto do documento (Microblink)
- [ ] Validar se ambas as fotos têm qualidade suficiente
- [ ] Registrar score no banco de dados
- [ ] Implementar retry em caso de falha

### 4.3 Testes
- [ ] Testar com mesma pessoa (deve aprovar)
- [ ] Testar com pessoas diferentes (deve rejeitar)
- [ ] Testar com fotos antigas vs recentes
- [ ] Validar taxa de falsos positivos/negativos

**Entregável:** Face match funcional com threshold ajustado

---

## Fase 5: Integração BigDataCorp - Validação CPF (1-2 dias)

### 5.1 Backend
- [ ] Verificar integração existente com BigDataCorp
- [ ] Criar método `validar_cpf_biometria()` no `BiometriaService`
- [ ] Validar CPF extraído do documento
- [ ] Cruzar dados: nome, data nascimento
- [ ] Verificar se CPF está ativo e válido
- [ ] Verificar se há restrições (Serasa, SPC)

### 5.2 Validação Cruzada
- [ ] Comparar nome do documento com nome do CPF
- [ ] Comparar data nascimento
- [ ] Calcular score de confiança dos dados
- [ ] Registrar resultado da validação

**Entregável:** Validação completa de CPF com dados biométricos

---

## Fase 6: Fluxo Completo - Integração no Checkout (5-7 dias)

### 6.1 Orquestração
- [ ] Criar método `validar_identidade_completa()` que orquestra:
  1. Liveness (FaceTec)
  2. OCR Documento (Microblink)
  3. Face Match (AWS Rekognition)
  4. Validação CPF (BigDataCorp)
- [ ] Implementar máquina de estados para o processo
- [ ] Permitir retry em cada etapa
- [ ] Definir regras de aprovação/rejeição

### 6.2 Modelo de Dados
```python
class ValidacaoBiometrica(models.Model):
    cliente = ForeignKey(Cliente)
    checkout_session = ForeignKey(CheckoutSession)

    # Etapas
    liveness_aprovado = BooleanField(default=False)
    liveness_score = DecimalField()

    ocr_aprovado = BooleanField(default=False)
    documento_tipo = CharField()  # RG, CNH
    documento_numero = CharField()
    cpf_extraido = CharField()
    nome_extraido = CharField()
    data_nascimento_extraida = DateField()

    face_match_aprovado = BooleanField(default=False)
    face_match_score = DecimalField()

    cpf_validado = BooleanField(default=False)
    cpf_ativo = BooleanField()

    # Status geral
    status = CharField()  # PENDENTE, APROVADO, REJEITADO, ERRO
    motivo_rejeicao = TextField()

    # Auditoria
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

### 6.3 Integração com Checkout
- [ ] Adicionar validação biométrica como etapa obrigatória
- [ ] Atualizar fluxo de cadastro de cliente
- [ ] Implementar tela de progresso (4 etapas)
- [ ] Salvar dados validados no perfil do cliente
- [ ] Marcar cliente como "verificado"

### 6.4 Regras de Negócio
- [ ] Definir quando exigir validação (valor mínimo, primeira compra, etc)
- [ ] Permitir pular validação para clientes já verificados
- [ ] Definir validade da verificação (ex: 1 ano)
- [ ] Implementar whitelist/blacklist

**Entregável:** Fluxo completo de validação integrado ao checkout

---

## Fase 7: Testes e Validação (3-5 dias)

### 7.1 Testes Funcionais
- [ ] Testar fluxo completo end-to-end
- [ ] Testar todos os cenários de erro
- [ ] Testar retry de cada etapa
- [ ] Testar timeout e conexão lenta
- [ ] Testar em diferentes dispositivos/navegadores

### 7.2 Testes de Segurança
- [ ] Tentar fraude com foto de foto
- [ ] Tentar fraude com vídeo gravado
- [ ] Tentar fraude com documento falso
- [ ] Tentar fraude com documento de terceiro
- [ ] Validar criptografia de dados sensíveis

### 7.3 Testes de Performance
- [ ] Medir tempo total do fluxo
- [ ] Otimizar upload de imagens
- [ ] Testar carga simultânea (10, 50, 100 usuários)
- [ ] Validar custos reais por transação

### 7.4 Ajustes de Threshold
- [ ] Ajustar threshold de face match (testar 85%, 90%, 95%)
- [ ] Ajustar qualidade mínima de imagem
- [ ] Balancear segurança vs taxa de aprovação
- [ ] Documentar decisões

**Entregável:** Relatório de testes + thresholds ajustados

---

## Fase 8: Deploy e Monitoramento (2-3 dias)

### 8.1 Preparação para Produção
- [ ] Migrar de credenciais trial para produção
- [ ] Configurar variáveis de ambiente
- [ ] Configurar armazenamento S3 para imagens
- [ ] Configurar política de retenção de dados (LGPD)
- [ ] Implementar logs estruturados

### 8.2 Monitoramento
- [ ] Criar dashboard de métricas:
  - Taxa de aprovação por etapa
  - Tempo médio por etapa
  - Taxa de erro por serviço
  - Custo por validação
- [ ] Configurar alertas:
  - Taxa de erro > 5%
  - Tempo de resposta > 10s
  - Custo diário acima do esperado
- [ ] Implementar retry automático com backoff

### 8.3 Documentação
- [ ] Documentar APIs internas
- [ ] Criar guia de troubleshooting
- [ ] Documentar fluxo para suporte
- [ ] Criar FAQ para usuários

### 8.4 Deploy
- [ ] Deploy em ambiente de staging
- [ ] Testes de smoke em staging
- [ ] Deploy gradual em produção (10%, 50%, 100%)
- [ ] Monitorar métricas nas primeiras 24h

**Entregável:** Sistema em produção com monitoramento ativo

---

## Estimativa de Tempo Total

| Fase | Duração | Dependências |
|------|---------|--------------|
| Fase 1 - Setup | 1-2 dias | - |
| Fase 2 - FaceTec | 3-5 dias | Fase 1 |
| Fase 3 - Microblink | 3-5 dias | Fase 1 |
| Fase 4 - Rekognition | 2-3 dias | Fase 2, 3 |
| Fase 5 - BigDataCorp | 1-2 dias | Fase 3 |
| Fase 6 - Integração | 5-7 dias | Fase 2, 3, 4, 5 |
| Fase 7 - Testes | 3-5 dias | Fase 6 |
| Fase 8 - Deploy | 2-3 dias | Fase 7 |

**Total: 20-32 dias úteis (4-6 semanas)**

---

## Estimativa de Custos (Pay-per-Use)

### Custos por Validação Completa

| Serviço | Custo Estimado | Observações |
|---------|----------------|-------------|
| FaceTec | $0.05 - $0.15 | Depende do volume |
| Microblink | $0.10 - $0.20 | BlinkID |
| AWS Rekognition | $0.001 | CompareFaces |
| BigDataCorp | $0.30 - $0.50 | Já contratado |
| **Total** | **$0.46 - $0.86** | Por validação |

### Projeção Mensal (exemplo)

- 1.000 validações/mês: $460 - $860
- 5.000 validações/mês: $2.300 - $4.300
- 10.000 validações/mês: $4.600 - $8.600

---

## Riscos e Mitigações

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Taxa de rejeição alta | Alto | Ajustar thresholds, melhorar UX de captura |
| Custos acima do esperado | Médio | Monitorar diariamente, implementar cache |
| Latência alta | Médio | Otimizar uploads, processar em paralelo |
| Fraudes passando | Alto | Testes rigorosos, ajustar thresholds |
| Problemas com documentos antigos | Médio | Fallback manual, suporte humano |

---

## Próximos Passos Imediatos

1. ✅ Criar branch `release-teste-validacao-biometrica`
2. ⏳ Criar contas trial em FaceTec e Microblink
3. ⏳ Validar credenciais AWS Rekognition
4. ⏳ Estimar custos reais com volumes esperados
5. ⏳ Iniciar Fase 2 (POC FaceTec)
