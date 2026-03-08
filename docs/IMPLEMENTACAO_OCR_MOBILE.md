# Implementação OCR de Documentos no App Mobile

**Data:** 08/03/2026
**Objetivo:** Extração automática de dados de RG/CNH no app mobile para cadastro/validação de clientes

---

## ⚠️ IMPORTANTE: Solução Gratuita vs Paga

### ❌ O que NÃO fazer (Pago):
- **Google Cloud Vision API** → $1.50 por 1000 imagens
- **AWS Rekognition** → $0.001 por comparação
- **Microblink** → Licença comercial cara

### ✅ O que fazer (Grátis):
- **Google ML Kit Text Recognition** → **GRATUITO**
  - Processamento on-device (no celular)
  - Não precisa internet (offline)
  - Não envia dados para servidor
  - Performance rápida

**Conclusão:** Implementamos Google Cloud Vision no backend (pago) mas existe solução **gratuita** no mobile que é até melhor!

---

## Tecnologia Recomendada: Google ML Kit

### Vantagens:
- ✅ **100% Gratuito**
- ✅ **Offline** (não precisa internet)
- ✅ **Rápido** (processa no celular)
- ✅ **Privacidade** (dados não saem do dispositivo)
- ✅ **Suporte nativo** para React Native e Flutter
- ✅ **Sem limite de uso**

---

## Implementação

### **React Native**

#### Instalação
```bash
npm install @react-native-ml-kit/text-recognition
```

#### Código
```javascript
import TextRecognition from '@react-native-ml-kit/text-recognition';

// Capturar foto do documento
async function processarDocumento(imageUri) {
  try {
    // OCR
    const result = await TextRecognition.recognize(imageUri);
    const textoCompleto = result.text;

    // Extrair dados
    const dados = extrairDados(textoCompleto);

    // Validar
    const erros = validarDados(dados);

    if (erros.length > 0) {
      return { sucesso: false, erros };
    }

    return { sucesso: true, dados };

  } catch (error) {
    console.error('Erro no OCR:', error);
    return { sucesso: false, erros: ['Erro ao processar documento'] };
  }
}

// Extrair dados com regex
function extrairDados(texto) {
  return {
    cpf: texto.match(/\d{3}\.?\d{3}\.?\d{3}-?\d{2}/)?.[0]?.replace(/\D/g, ''),
    rg: texto.match(/\d{1,2}\.?\d{3}\.?\d{3}-?\d{1}/)?.[0]?.replace(/\D/g, ''),
    dataNascimento: texto.match(/\d{2}\/?\d{2}\/?\d{4}/)?.[0],
    nome: texto.match(/(?:NOME|FILIAÇÃO)\s*([A-Z\s]+)/)?.[1]?.trim(),
  };
}

// Validar dados extraídos
function validarDados(dados) {
  const erros = [];

  if (!dados.cpf || dados.cpf.length !== 11) {
    erros.push('CPF inválido ou não encontrado');
  }

  if (!dados.nome || dados.nome.length < 3) {
    erros.push('Nome não encontrado');
  }

  if (!dados.dataNascimento) {
    erros.push('Data de nascimento não encontrada');
  }

  return erros;
}
```

---

### **Flutter**

#### Instalação
```yaml
dependencies:
  google_mlkit_text_recognition: ^0.11.0
```

#### Código
```dart
import 'package:google_mlkit_text_recognition/google_mlkit_text_recognition.dart';

Future<Map<String, dynamic>> processarDocumento(String imagePath) async {
  final textRecognizer = TextRecognizer();
  final inputImage = InputImage.fromFilePath(imagePath);

  try {
    final recognizedText = await textRecognizer.processImage(inputImage);
    final texto = recognizedText.text;

    // Extrair dados
    final dados = extrairDados(texto);

    // Validar
    final erros = validarDados(dados);

    await textRecognizer.close();

    if (erros.isNotEmpty) {
      return {'sucesso': false, 'erros': erros};
    }

    return {'sucesso': true, 'dados': dados};

  } catch (e) {
    await textRecognizer.close();
    return {'sucesso': false, 'erros': ['Erro ao processar documento']};
  }
}
```

---

## Regex para Extração de Dados

```javascript
// CPF: 123.456.789-00 ou 12345678900
const cpfRegex = /\d{3}\.?\d{3}\.?\d{3}-?\d{2}/;

// RG: 12.345.678-9 ou 123456789
const rgRegex = /\d{1,2}\.?\d{3}\.?\d{3}-?\d{1}/;

// Data: 01/01/1990 ou 01011990
const dataRegex = /\d{2}\/?\d{2}\/?\d{4}/;

// Nome: Geralmente em MAIÚSCULAS após "NOME" ou "FILIAÇÃO"
const nomeRegex = /(?:NOME|FILIAÇÃO)\s*([A-Z\s]+)/;

// CNH: 11 dígitos
const cnhRegex = /\d{11}/;
```

---

## Fluxo UX Recomendado

### 1. **Tela de Captura**
```
┌─────────────────────────┐
│  📷 Tire foto do RG/CNH │
│                         │
│  ┌─────────────────┐   │
│  │                 │   │
│  │   [Moldura do   │   │
│  │    Documento]   │   │
│  │                 │   │
│  └─────────────────┘   │
│                         │
│ "Posicione o documento │
│  dentro da moldura"     │
│                         │
│    [Capturar Foto]      │
└─────────────────────────┘
```

### 2. **Processamento**
```
┌─────────────────────────┐
│   ⏳ Lendo documento... │
│                         │
│   [Loading spinner]     │
└─────────────────────────┘
```

### 3. **Confirmação**
```
┌─────────────────────────┐
│  ✅ Dados Extraídos     │
│                         │
│  Nome: João da Silva    │
│  CPF: 123.456.789-00    │
│  RG: 12.345.678-9       │
│  Nasc: 01/01/1990       │
│                         │
│  [Editar] [Confirmar]   │
│  [Tirar Nova Foto]      │
└─────────────────────────┘
```

### 4. **Envio para Backend**
```javascript
// Enviar dados + imagem para validação
POST /api/checkout/validar-documento/

{
  "cpf": "12345678900",
  "nome": "JOAO DA SILVA",
  "rg": "123456789",
  "data_nascimento": "01/01/1990",
  "tipo_documento": "CNH",
  "documento_imagem_base64": "data:image/jpeg;base64,/9j/4AAQ..."
}
```

---

## Melhorias de Qualidade

### Validação de Qualidade da Imagem
```javascript
async function validarQualidadeImagem(imageUri) {
  // Verificar blur
  const isBlurry = await detectBlur(imageUri);
  if (isBlurry) {
    return { valido: false, erro: 'Imagem desfocada' };
  }

  // Verificar iluminação
  const brightness = await getBrightness(imageUri);
  if (brightness < 50 || brightness > 200) {
    return { valido: false, erro: 'Iluminação inadequada' };
  }

  return { valido: true };
}
```

### Pré-processamento
```javascript
import ImageEditor from '@react-native-community/image-editor';

async function melhorarImagem(imageUri) {
  // Converter para escala de cinza
  // Aumentar contraste
  // Ajustar brilho

  return processedImageUri;
}
```

---

## Comparação de Custos

| Solução | Custo/1000 docs | Performance | Offline | Privacidade |
|---------|-----------------|-------------|---------|-------------|
| **Google ML Kit** | **R$ 0** | Rápido | ✅ Sim | ✅ Alta |
| Google Cloud Vision | R$ 7.50 | Muito rápido | ❌ Não | ⚠️ Média |
| Tesseract OCR | R$ 0 | Médio | ✅ Sim | ✅ Alta |
| Microblink | R$ 500+/mês | Muito rápido | ✅ Sim | ✅ Alta |

**Economia com ML Kit:** R$ 7.50 por 1000 documentos processados!

---

## Integração com Backend

### Endpoint Backend (já existe)
```python
# services/django/checkout/views.py

@api_view(['POST'])
def validar_documento(request):
    """
    Recebe dados extraídos pelo app + imagem
    Valida CPF com BigDataCorp
    Armazena para auditoria
    """
    cpf = request.data.get('cpf')
    nome = request.data.get('nome')
    documento_imagem = request.data.get('documento_imagem_base64')

    # Validar CPF com BigDataCorp (já integrado)
    cpf_valido = validar_cpf_bigdatacorp(cpf, nome)

    if not cpf_valido:
        return Response({
            'sucesso': False,
            'erro': 'CPF inválido ou dados não conferem'
        }, status=400)

    # Armazenar documento para auditoria
    salvar_documento_s3(cpf, documento_imagem)

    return Response({
        'sucesso': True,
        'mensagem': 'Documento validado com sucesso'
    })
```

---

## Checklist de Implementação

### Fase 1: Setup (1 dia)
- [ ] Instalar Google ML Kit no projeto mobile
- [ ] Configurar permissões de câmera
- [ ] Criar tela de captura com moldura

### Fase 2: OCR (2 dias)
- [ ] Implementar captura de foto
- [ ] Integrar ML Kit Text Recognition
- [ ] Implementar regex para extração de dados
- [ ] Validar dados extraídos

### Fase 3: UX (1 dia)
- [ ] Criar tela de confirmação de dados
- [ ] Permitir edição manual
- [ ] Implementar retry (tirar nova foto)

### Fase 4: Integração (1 dia)
- [ ] Integrar com endpoint backend
- [ ] Enviar imagem + dados extraídos
- [ ] Tratar erros de validação

### Fase 5: Testes (2 dias)
- [ ] Testar com RG de diferentes estados
- [ ] Testar com CNH (nova e antiga)
- [ ] Testar em diferentes condições de luz
- [ ] Ajustar regex conforme necessário

**Total:** 7 dias de desenvolvimento

---

## Documentação Oficial

- **ML Kit Text Recognition (React Native):** https://github.com/a7med3bdulbaset/react-native-ml-kit
- **ML Kit (Flutter):** https://pub.dev/packages/google_mlkit_text_recognition
- **ML Kit (Documentação Google):** https://developers.google.com/ml-kit/vision/text-recognition

---

## Observações Importantes

1. ✅ **Não precisa AWS Rekognition** (comparação de faces não é necessária)
2. ✅ **Não precisa FaceTec** (liveness detection não é obrigatório)
3. ✅ **Não precisa Google Cloud Vision** (ML Kit faz a mesma coisa de graça)
4. ✅ **Backend só valida CPF** com BigDataCorp (já integrado)
5. ✅ **Tudo roda no app** = mais rápido, mais barato, mais privado

---

## Conclusão

**Implementação atual (backend):**
- ❌ Google Cloud Vision → R$ 7.50 por 1000 docs
- ❌ AWS Rekognition → R$ 5.00 por 1000 comparações
- ❌ FaceTec → Licença comercial

**Implementação recomendada (mobile):**
- ✅ Google ML Kit → **GRATUITO**
- ✅ Processamento offline
- ✅ Mais rápido
- ✅ Mais privado

**Economia estimada:** R$ 12.50 por 1000 documentos processados

---

**Última Atualização:** 08/03/2026
