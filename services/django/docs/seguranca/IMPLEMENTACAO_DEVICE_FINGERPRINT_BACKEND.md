# Implementação Backend - Device Fingerprint com Análise de Similaridade

**Data:** 06/03/2026
**Versão:** 3.2.0
**Status:** ✅ IMPLEMENTADO

## Resumo Executivo

Implementação completa do sistema de device fingerprint híbrido no backend, conforme especificação do documento de correção de segurança. O sistema agora armazena **componentes individuais** do fingerprint e utiliza **algoritmo de similaridade** para detectar mudanças legítimas (ex: update do iOS) vs. tentativas de fraude.

## Arquivos Modificados

### 1. Modelo de Dados
**Arquivo:** `wallclub_core/seguranca/models.py`

**Campos adicionados ao modelo `DispositivoConfiavel`:**
- `native_id` - ID nativo (IDFV/androidId)
- `screen_resolution` - Resolução da tela
- `device_model` - Modelo do dispositivo
- `os_version` - Versão do SO
- `device_brand` - Fabricante
- `timezone` - Timezone
- `platform` - Plataforma (ios/android)

**Índices criados:**
- `idx_dispositivo_native_id_ativo` - Otimiza busca por native_id
- `idx_dispositivo_user_native` - Otimiza busca por user_id + native_id

### 2. Service de Gerenciamento
**Arquivo:** `wallclub_core/seguranca/services_device.py`

**Novos métodos implementados:**

#### `calcular_similaridade(fp_antigo, componentes_novos) -> int`
Calcula score de 0-100 comparando componentes individuais.

**Pesos:**
- `native_id`: 40 pontos
- `screen_resolution`: 20 pontos
- `device_model`: 20 pontos
- `device_brand`: 10 pontos
- `os_version`: 5 pontos (tolerante a updates)
- `timezone`: 5 pontos

#### `validar_dispositivo_com_similaridade(user_id, tipo_usuario, dados_dispositivo) -> Dict`
Valida dispositivo usando análise de similaridade.

**Retorna decisão:**
- `'allow'` - Dispositivo conhecido e válido
- `'require_otp'` - Requer validação 2FA
- `'block'` - Bloqueado (limite atingido)

**Lógica de decisão:**
- Hash exato encontrado e válido → `allow`
- Similaridade ≥ 90 → `allow` (1 componente mudou - provável update legítimo) **COM MONITORAMENTO**
- Similaridade 80-89 → `require_otp` (2 componentes mudaram - suspeito)
- Similaridade 50-79 → `require_otp` (suspeito)
- Similaridade < 50 → `require_otp` (novo dispositivo) ou `block` (limite atingido)

#### `_versoes_proximas(versao1, versao2) -> bool`
Verifica se duas versões de SO são próximas (ex: 17.2 e 17.3).

**Método atualizado:**

#### `registrar_dispositivo(...)`
Agora extrai e armazena componentes individuais do fingerprint recebido do app.

## Migration SQL

**Arquivo:** `docs/seguranca/migration_device_fingerprint_componentes.sql`

Execute este script para adicionar os novos campos ao banco:

```bash
psql -h <host> -U <user> -d <database> -f migration_device_fingerprint_componentes.sql
```

## Payload Esperado do App

O app mobile deve enviar os seguintes campos no login/cadastro:

```json
{
  "device_fingerprint": "a1b2c3d4e5f6...",
  "user_agent": "WallClubApp (iOS iPhone15,2 ABC123)",
  "device_name": "iPhone 14 Pro",

  "native_id": "ABC123-DEF456-GHI789",
  "device_model": "iPhone15,2",
  "os_version": "17.2",
  "device_brand": "Apple",
  "screen_resolution": "1170x2532",
  "timezone": "America/Sao_Paulo",
  "platform": "ios"
}
```

## Exemplos de Uso

### Exemplo 1: Validar dispositivo no login

```python
from wallclub_core.seguranca.services_device import DeviceManagementService

# Dados recebidos do app
dados_dispositivo = {
    'device_fingerprint': request.data.get('device_fingerprint'),
    'native_id': request.data.get('native_id'),
    'screen_resolution': request.data.get('screen_resolution'),
    'device_model': request.data.get('device_model'),
    'os_version': request.data.get('os_version'),
    'device_brand': request.data.get('device_brand'),
    'timezone': request.data.get('timezone'),
    'platform': request.data.get('platform'),
}

# Validar com análise de similaridade
resultado = DeviceManagementService.validar_dispositivo_com_similaridade(
    user_id=cliente_id,
    tipo_usuario='cliente',
    dados_dispositivo=dados_dispositivo
)

# Decisão baseada no resultado
if resultado['decisao'] == 'allow':
    # Dispositivo conhecido OU similaridade muito alta (≥90)

    # Se requer monitoramento, registrar para análise
    if resultado.get('requer_monitoramento'):
        registrar_log('apps.cliente',
            f"⚠️ Login permitido com similaridade {resultado['similaridade_max']}: MONITORAR",
            nivel='WARNING')

    return gerar_jwt_e_retornar(cliente)

elif resultado['decisao'] == 'require_otp':
    # Solicitar 2FA
    motivo = resultado['motivo']
    similaridade = resultado['similaridade_max']

    # Log para análise
    registrar_log('apps.cliente',
        f"2FA solicitado: {motivo} (similaridade: {similaridade})")

    return solicitar_2fa(cliente)

elif resultado['decisao'] == 'block':
    # Bloquear (limite atingido)
    return Response({
        'sucesso': False,
        'mensagem': resultado['motivo']
    }, status=403)
```

### Exemplo 2: Registrar dispositivo após validação 2FA

```python
# Após validar código OTP com sucesso
dispositivo, criado, mensagem = DeviceManagementService.registrar_dispositivo(
    user_id=cliente_id,
    tipo_usuario='cliente',
    dados_dispositivo=dados_dispositivo,
    ip_registro=ip_address,
    marcar_confiavel=True  # Válido por 30 dias
)

if dispositivo:
    registrar_log('apps.cliente',
        f"Dispositivo {'registrado' if criado else 'renovado'}: {dispositivo.nome_dispositivo}")
```

## Cenários de Teste

### Cenário A: Desinstalação e Reinstalação (iOS)
```
Componentes antigos:
- native_id: "ABC123"        ← MUDOU
- screen_resolution: "1170x2532"  ← IGUAL
- device_model: "iPhone15,2"      ← IGUAL
- os_version: "17.2"              ← IGUAL
- device_brand: "Apple"           ← IGUAL
- timezone: "America/Sao_Paulo"   ← IGUAL

Score: 0 + 20 + 20 + 10 + 5 + 5 = 60 pontos
Decisão: REQUIRE_OTP (suspeito - apenas IDFV mudou, mas score < 80)
```

### Cenário B: Update do Sistema Operacional
```
Apenas os_version muda: 17.2 → 17.3

Score: 40 + 20 + 20 + 10 + 3 + 5 = 98 pontos
Decisão: ALLOW ✅ (similaridade muito alta ≥90 - provável update legítimo)
Monitoramento: SIM (log de WARNING registrado)
```

### Cenário C: Dispositivo Completamente Diferente
```
Todos os componentes diferentes

Score: 0 pontos
Decisão: REQUIRE_OTP (novo dispositivo)
```

### Cenário D: IDFV Reset + Update iOS (2 componentes mudaram)
```
Componentes:
- native_id: "ABC123" → "XYZ789"  ← MUDOU
- os_version: "17.2" → "17.4"     ← MUDOU
- screen_resolution: "1170x2532"  ← IGUAL
- device_model: "iPhone15,2"      ← IGUAL
- device_brand: "Apple"           ← IGUAL
- timezone: "America/Sao_Paulo"   ← IGUAL

Score: 0 + 3 + 20 + 20 + 10 + 5 = 58 pontos
Decisão: REQUIRE_OTP (score < 80 - comportamento suspeito)
```

### Cenário E: Apenas IDFV Mudou (iOS - Desinstalou todos apps do vendor)
```
Componentes:
- native_id: "ABC123" → "XYZ789"  ← MUDOU
- screen_resolution: "1170x2532"  ← IGUAL
- device_model: "iPhone15,2"      ← IGUAL
- os_version: "17.2"              ← IGUAL
- device_brand: "Apple"           ← IGUAL
- timezone: "America/Sao_Paulo"   ← IGUAL

Score: 0 + 20 + 20 + 10 + 5 + 5 = 60 pontos
Decisão: REQUIRE_OTP (score < 80 - suspeito, pode ser fraude)
```

## Monitoramento e Logs

O sistema registra logs detalhados em `comum.seguranca`:

- ✅ Dispositivo conhecido validado
- 📊 Similaridade calculada com score
- ⚠️ Alta similaridade detectada (possível update)
- 🚨 Similaridade média (comportamento suspeito)
- 🆕 Novo dispositivo detectado
- 🚫 Limite de dispositivos atingido

**Exemplo de log:**
```
[INFO] ✅ Dispositivo conhecido validado: cliente ID:12345
[INFO] 📊 Similaridade máxima: 85 pontos (dispositivo: iPhone 14 Pro)
[WARNING] ⚠️ Alta similaridade detectada (85): possível update de SO ou IDFV reset
```

## Queries Úteis para Análise

### 1. Dispositivos com mudança de native_id (possível fraude)
```sql
SELECT
    d1.user_id,
    d1.native_id as native_id_antigo,
    d2.native_id as native_id_novo,
    d1.device_model,
    d1.ultimo_acesso as ultimo_acesso_antigo,
    d2.criado_em as criado_novo
FROM otp_dispositivo_confiavel d1
JOIN otp_dispositivo_confiavel d2
    ON d1.user_id = d2.user_id
    AND d1.device_model = d2.device_model
    AND d1.native_id != d2.native_id
WHERE d1.ativo = true
  AND d2.ativo = true
  AND d2.criado_em > d1.ultimo_acesso
ORDER BY d2.criado_em DESC;
```

### 2. Usuários com múltiplos dispositivos ativos
```sql
SELECT
    user_id,
    tipo_usuario,
    COUNT(*) as total_dispositivos,
    STRING_AGG(nome_dispositivo, ', ') as dispositivos
FROM otp_dispositivo_confiavel
WHERE ativo = true
GROUP BY user_id, tipo_usuario
HAVING COUNT(*) > 1
ORDER BY total_dispositivos DESC;
```

### 3. Dispositivos expirados (precisam revalidar)
```sql
SELECT
    user_id,
    tipo_usuario,
    nome_dispositivo,
    confiavel_ate,
    EXTRACT(DAY FROM (NOW() - confiavel_ate)) as dias_expirado
FROM otp_dispositivo_confiavel
WHERE ativo = true
  AND confiavel_ate < NOW()
ORDER BY confiavel_ate DESC;
```

## Compatibilidade com Código Existente

O método legado `validar_dispositivo()` foi **mantido** para compatibilidade com código existente. Ele continua funcionando normalmente.

**Migração gradual recomendada:**
1. Código novo deve usar `validar_dispositivo_com_similaridade()`
2. Código legado pode continuar usando `validar_dispositivo()`
3. Migrar gradualmente conforme necessidade

## Próximos Passos

- [ ] Executar migration SQL no banco de produção
- [ ] Atualizar views de login para usar `validar_dispositivo_com_similaridade()`
- [ ] Configurar alertas para similaridade média (50-79)
- [ ] Criar dashboard de monitoramento de dispositivos
- [ ] Implementar notificações push para mudanças suspeitas

## Referências

- Documento original: Correção Crítica de Segurança - Device Fingerprint
- Modelo: `wallclub_core/seguranca/models.py`
- Service: `wallclub_core/seguranca/services_device.py`
- Migration: `docs/seguranca/migration_device_fingerprint_componentes.sql`
