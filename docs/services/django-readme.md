# WallClub Django

Sistema WallClub migrado de PHP para Python/Django - Backend completo para fintech de cashback e gestão financeira.

## Sobre o Projeto

Sistema financeiro completo implementado em Django com:
- **APIs REST** para apps móveis (autenticação JWT, transações, saldo, extrato, comprovante)
- **OAuth 2.0** para autenticação de terminais POS e apps móveis
- **Conta Digital** com controle de saldo, cashback, autorizações e bloqueios
- **Sistema de parâmetros financeiros** 100% migrado do PHP com validação completa
- **Cargas automatizadas** do Pinbank para processamento de transações (extrato POS + base gestão)
- **Portais administrativos** para gestão de usuários, lojas e configurações
- **Calculadoras financeiras** com fidelidade total ao sistema PHP legado
- **Integração AWS** (Secrets Manager) e deploy Docker em produção funcionando
- **Redis** para cache de tokens OAuth e sessões
- **Risk Engine** (container separado - porta 8004) - Sistema antifraude operacional em produção
- **2FA no Checkout Web** ✅ (Fase 4 - Semana 21 CONCLUÍDA) - Cliente autogerencia telefone + OTP via WhatsApp + rate limiting + limite progressivo + integração Risk Engine completa (Aguardando autorização Pinbank para produção)
- **Antifraude Checkout Web** ✅ (22/10/2025) - Todas transações link de pagamento protegidas: score 0-100, bloqueio automático, revisão manual, 7 campos novos em checkout_transactions
- **Login Simplificado - Modelo Fintech** ✅ (25/10/2025) - Fluxo moderno inspirado em Nubank/PicPay: senha sempre via SMS (4 dígitos), JWT 30 dias (era 1 dia), refresh token 60 dias (era 7), celular revalidado a cada 30 dias (era 90), biometria desde dia 1, 2FA apenas quando necessário (novo device ou token expirado). Endpoint criar_senha_definitiva removido, campo senha_temporaria deprecated. Zero fricção no onboarding (2 passos vs 4 passos). Documentação: docs/fluxo_login_revalidacao.md
- **Device Management + 2FA Login App** ✅ (Fase 4 - Semana 22-23 CONCLUÍDA + CORREÇÕES 26/10) - Sistema completo de autenticação em duas etapas: 6 endpoints (verificar_necessidade, solicitar_codigo, validar_codigo, trocar_no_login, meus, revogar), template WhatsApp 2fa_login_app, OTP 5min validade, **limite 2 dispositivos ATIVOS por cliente** (30 dias validade), troca de senha invalida todos devices. **Correções críticas 26/10:** rate_limiter_2fa.py (cache.ttl removido - não existe no LocMemCache), feature_flag extrai cliente_id do JWT (não do body), device_management cria NOVO registro ao reativar (preserva histórico auditoria), constraint UNIQUE composta (user_id + device_fingerprint + ativo), **revalidação celular (90 dias)** alterada para usar auth_token (OAuth) em vez de JWT (permite validar antes do login completo), sistema 2FA detecta celular expirado automaticamente, OTPService parâmetro 'contexto' removido (não existe), template WhatsApp unificado. Fluxo: login com novo device → erro device_limite_atingido (inclui cliente_id) → solicita 2FA via WhatsApp → valida código → troca device (remove antigos + registra novo). Contextos 2FA: novo_dispositivo, expirado >30d, **celular_expirado >90d**, alteração_dados, transferência, primeira_transação_dia, alto_valor >R$100. Portal Admin gestão completa de dispositivos
- **Segurança JWT - Validação Obrigatória** ✅ (26/10/2025) - **FALHA CRÍTICA CORRIGIDA:** Tokens JWT revogados (is_active=0) continuavam funcionando. Sistema apenas decodificava JWT sem consultar tabela de auditoria. **Correções:** ClienteJWTAuthentication.authenticate() valida obrigatoriamente contra cliente_jwt_tokens, verifica is_active=True e revoked_at=NULL, registra uso (last_used), rejeita tokens sem JTI. generate_cliente_jwt_token() revoga automaticamente todos tokens ativos anteriores antes de criar novo. Sistema gera 2 tokens por login (access 30 dias + refresh 60 dias) - padrão OAuth 2.0. Dispositivo confiável (30 dias) permite renovação automática via /2fa/verificar_necessidade/ sem pedir SMS. Validado em produção: token revogado → 401, token expirado → 401, novo login → tokens antigos revogados. Diretriz 9.2 adicionada em DIRETRIZES.md com 5 regras de ouro
- **Bypass 2FA para Testes Apple/Google** ✅ (31/10/2025) - Sistema permite login sem código OTP para revisores de lojas de apps. Campo bypass_2fa no modelo Cliente (default=False), verificação em services_2fa_login.verificar_necessidade_2fa(), cliente com bypass ativo retorna JWT diretamente (pula etapas de OTP). Segurança: apenas clientes específicos, rastreável via logs WARNING, reversível via SQL, não quebra fluxo do app (usa mesmo formato de resposta de dispositivo confiável). SQL: scripts/producao/release_3.1.0/001_add_bypass_2fa.sql. Arquivos: apps/cliente/models.py (campo bypass_2fa), apps/cliente/services_2fa_login.py (lógica de bypass). Documentação: DIRETRIZES.md seção 9.1
- **Release 3.1.0 - Autenticação com Senha** ✅ (27/10/2025) - Sistema completo de cadastro e autenticação com senha no app: **Cadastro:** 3 endpoints (iniciar → finalizar → validar_otp), /cadastro/iniciar/ consulta Bureau e cria cliente base automaticamente, OTP via WhatsApp (template 2fa_login_app), campos cadastro_completo/cadastro_iniciado_em/cadastro_concluido_em no model Cliente. **Login:** Validação de senha obrigatória antes de gerar JWT, controle tentativas Redis (5/15min, 10/1h, 15/24h), JWT alterado para Access 1 dia + Refresh 30 dias (era 30+60). **Reset senha:** 2 endpoints (solicitar → validar), OTP via WhatsApp. **Redis:** Configuração corrigida para usar hostname wallclub-redis (era IP 172.18.0.2), CACHE_CONFIG com RedisCache funcionando (era LocMemCache causando perda de OTP entre workers). Documentação completa: docs/mudancas_login_app.md. Arquivos: 8 novos (views_cadastro, services_cadastro, views_reset_senha, services_reset_senha, views_refresh_jwt, services_login_attempts, oauth/views_refresh), 5 modificados (jwt_cliente, services, views, serializers, urls, models, settings)
- **Sistema de Autenticação JWT Customizado - COMPLETO** ✅ (28/10/2025) - **18 cenários testados e validados em produção:** Sistema enterprise-grade com JWT customizado independente do Django User/Session. **FASE 1 - Cadastro (3 endpoints):** iniciar/validar_otp/finalizar com OTP via WhatsApp. **FASE 2 - Login (5 cenários):** rate limiting (5/15min, 10/1h, 20/24h), bloqueio automático progressivo (1h, 24h), contadores em cliente_autenticacao + cliente_bloqueios. **FASE 3 - Reset Senha (3 endpoints):** solicitar/validar com histórico em cliente_senhas_historico. **FASE 4 - 2FA + Dispositivos (5 endpoints):** verificar_necessidade/solicitar/validar/listar/revogar, device fingerprinting, limite 2 dispositivos/cliente (30 dias validade), OTP 6 dígitos (5 min). **FASE 5 - Refresh Token (2 testes):** renovar access_token preservando refresh token (reutilizável 30 dias), access tokens anteriores revogados automaticamente. **Tabelas:** cliente_jwt_tokens (token_type: access/refresh, auditoria completa), otp_autenticacao (códigos), otp_dispositivo_confiavel (fingerprints), cliente_autenticacao (tentativas), cliente_bloqueios (histórico), cliente_senhas_historico. **Correções SQL:** ALTER TABLE cliente_jwt_tokens ADD token_type VARCHAR(20), MODIFY user_agent TEXT NULL. **Segurança:** OTP WhatsApp, 2FA obrigatório novos devices, refresh não descartável, revogação automática, auditoria com IP/user-agent. Documentação: docs/TESTE_CURL_USUARIO.md (comandos curl + resultados reais). Sistema 100% operacional
- **Troca de Senha App + Consolidação WhatsApp** ✅ (28/10/2025) - **Endpoint /senha/solicitar_troca/ corrigido:** OTPService.gerar_otp() estava recebendo canal_id (parâmetro inexistente), corrigido para usar apenas user_id + tipo_usuario + telefone + ip_solicitacao. Código OTP agora é buscado do banco (AutenticacaoOTP) para envio via WhatsApp, não depende mais de DEBUG. **Template WhatsApp:** 2fa_login_app requer 2 parâmetros (1 body + 1 button URL), não apenas código. **Consolidação WhatsAppService:** Método duplicado envia_template() removido (78 linhas), mantido apenas envia_whatsapp() padrão usado em 9 arquivos. Rate limit OTP zerado via Redis: `docker exec wallclub-redis redis-cli FLUSHALL`. Arquivos: apps/cliente/views_senha.py, comum/seguranca/services_2fa.py, comum/integracoes/whatsapp_service.py. Documentação atualizada: DIRETRIZES.md seção 5.1
- **Sistema de Logs Padronizado** ✅ (28/10/2025) - Padronização completa de níveis de log em 6 módulos principais: **DEBUG** (validações bem-sucedidas, fluxo normal), **INFO** (operações concluídas), **WARNING** (validações negadas, anomalias), **ERROR** (exceções críticas). Módulos padronizados: comum/estr_organizacional, comum/integracoes, comum/middleware, comum/oauth, comum/seguranca, apps/cliente. Logs de autenticação JWT, IP capturado, validações de token agora em DEBUG (não poluem produção). Operações importantes (senha trocada, 2FA gerado, dispositivo registrado) em INFO. Tentativas inválidas, rate limits, sessões expiradas em WARNING. Boas práticas documentadas: sempre especificar nível, categoria consistente (comum.modulo/apps.modulo), mensagens descritivas. Documentação: DIRETRIZES.md seção 13
- **Gestão de Terminais POS** ✅ (23/10/2025) - Cadastro e encerramento de terminais POS: validação de duplicatas ativos (mesmo número série), timestamp atual no encerramento, model Terminal com db_table='terminais', métodos helper set_inicio_date/set_fim_date, TerminaisService completo, templates terminais_list + terminal_form
- **Sistema de Segurança Multi-Portal** ✅ (Fase 4 - Semana 23 CONCLUÍDA) - Middleware de validação de login + 6 detectores automáticos (Celery) + Telas gerenciamento (Atividades Suspeitas + Bloqueios) + APIs Risk Engine (validate-login, suspicious, blocks, investigate)
- **Portal Vendas + Recorrências** ✅ (Fase 5 - Semana 24 CONCLUÍDA + Atualizações 30/10) - Checkout direto + recorrências unificados: models (RecorrenciaAgendada + campo descricao), views (7 endpoints), templates (4 telas), fluxo separado link_recorrencia_web/ para tokenização de cartão (email customizado + checkout simplificado), decorator @requer_permissao funcional, integração completa. **Permissões Granulares (30/10):** recursos_permitidos em PortalPermissao (checkout: true/false, recorrencia: true/false), templatetag tem_permissao_recurso, menu dinâmico base.html (links aparecem apenas se permitido), interface admin usuario_form.html (checkboxes checkout + recorrência dentro do card Portal Vendas), UsuarioService atualizado (criar_usuario + atualizar_usuario salvam recursos JSON). **Correções Filtros (30/10):** Vendedor vendo apenas recorrências próprias corrigido - filtro vendedor_id removido de recorrencia_listar e recorrencia_relatorio_nao_cobrados (agora mostra todas da loja). Pendente: Celery Beat (tasks_recorrencia.py prontas)
- **Fase 6 - Separação em Múltiplos Containers** ✅ (Fase 6A+6B+6C CONCLUÍDAS - 30/10-02/11/2025) - **OBJETIVO:** Preparar código para separação física em 5 containers independentes. **6A - CORE Limpo (30/10):** Módulo `comum/*` (49 arquivos) 100% independente - 0 imports de apps, pronto para extração. **6B - Dependências Cruzadas (01/11):** 103 imports cruzados resolvidos - **26 APIs REST internas** (5 Conta Digital + 8 Checkout Recorrências + 6 Ofertas + 7 Parâmetros), OAuth 2.0 scope `internal`, sem rate limiting. **17 arquivos lazy imports** (apps.get_model). **2 classes SQL direto** (TransacoesQueries 7 métodos + TerminaisQueries 2 métodos) read-only. **Fix crítico RPR:** valores zerados corrigidos (dict.get vs getattr, 3 ocorrências em views_rpr.py). **6C - Monorepo Unificado (02/11):** wallclub_core extraído (52 arquivos), 113 arquivos migrados (108 Django + 5 Risk Engine), estrutura unificada wallclub/services/{django,riskengine,core}, diretório comum/ removido, 1 repositório git único, workspace VSCode configurado. **Validação:** Script validar_dependencias.sh passou - 0 imports diretos entre containers. **Próximo:** 6D (Separação física 5 containers). Arquivos chave: services/core/wallclub_core/, apps/conta_digital/views_internal_api.py, checkout/views_internal_api.py
- **Integração Risk Engine - Análise de Autenticação** ✅ (30/10/2025) - Endpoint exclusivo OAuth: GET /cliente/api/v1/autenticacao/analise/<cpf>/, decorator @require_oauth_riskengine, service ClienteAutenticacaoAnaliseService (consulta cliente_autenticacao, cliente_bloqueios, otp_dispositivo_confiavel), retorna 9 flags de risco (conta bloqueada, bloqueio recente <7d, múltiplos bloqueios 30d, alta taxa falha ≥30%, tentativas falhas 24h, múltiplos IPs/devices, devices novos, sem device confiável), usado pelo Risk Engine para calcular score autenticação 0-50 pontos. Documentação: docs/integracao_autenticacao_fraude.md
- **Checkout Web (Link de Pagamento)** ✅ (22-23/10/2025 + Atualizações 30/10) - Sistema completo: geração links únicos, sessão temporária 30min, cálculo descontos tempo real (Pinbank), tokenização cartões, antifraude (Risk Engine), limite progressivo R$100→R$200→R$500. **2FA Telefone:** CheckoutClienteTelefone (status -1/0/1), primeira_transacao_aprovada_em trava telefone, inativação automática de telefones antigos ao marcar transação, exibição obfuscada (21)****0901. **Antifraude:** transaction_id usa checkout_transactions.id (era token)
- **Cargas Automáticas Pinbank** ✅ (22-25/10/2025) - Processamento TEF + Credenciadora + Checkout: calculadora compartilhada 1178 linhas (130+ variáveis), baseTransacoesGestao + auditoria SQL triggers, streaming 100 registros/lote, commands carga_base_gestao/carga_credenciadora/carga_checkout. Correções: codigoCliente camelCase, tipo_operacao preservado, bug último lote <100 registros, info_loja/info_canal montados localmente, var45 sobrescrita removida (linha 755), var4 usando nome do canal, var45 preserva data do primeiro pagamento
- **Sistema de Notificações** ✅ (24/10/2025) - Correções Push/SMS: category dinâmico do template (não hardcode), UUID completo em autorizacao_id (não truncado), valor_solicitado na API verificação, URL encoding SMS correto (safe=':/'), timezone fix esta_expirada() (datetime.now() vs timezone.now()). Arquivos: apn_service.py, services_conta_digital.py, services_autorizacao.py, sms_service.py, models.py
- **Sistema de Mensagens WhatsApp + SMS** ✅ (29/10/2025) - Correções críticas: ordem parâmetros SMS (/TELEFONE/MENSAGEM/SHORTCODE/ASSUNTO), SHORTCODE_PREMIUM, encoding completo (safe=''), templates WhatsApp por categoria (AUTHENTICATION sempre entrega, MARKETING requer opt-in, UTILITY para funcionais), campo celular_validado_em adicionado (atualiza ao validar OTP, revalidação 90 dias), constraint dispositivos confiáveis corrigida (coluna virtual unique_check permite histórico completo), rate limit checado ANTES de exigir 2FA (evita travamento), revogar_dispositivo usa .update() (não .save()). Meta rate limit por número: status "accepted" ≠ entregue. Arquivos: sms_service.py, messages_template_service.py, services_2fa_login.py, services_revalidacao_celular.py, services_device.py, models.py (Cliente)
- **Simplificação de Portais** ✅ (24/10/2025) - Portal de recorrência removido (funcionalidades integradas no portal_vendas), redirect de sessão expirada corrigido (portal_admin/ sem /login/), dashboard vendas com autenticação obrigatória. Arquitetura reduzida: 4 portais ativos (admin, lojista, corporativo, vendas). Arquivos: urls.py, settings/base.py, middleware.py, decorators.py, views.py
- **Endpoint de Exclusão de Conta** ✅ (05/11/2025) - Soft delete de clientes via API: POST /api/cliente/excluir/ (JWT obrigatório), desativa conta (is_active=0), revoga todos tokens JWT ativos, operação atômica com transaction.atomic(), logs de auditoria completos. Cliente não consegue mais fazer login nem usar endpoints autenticados. Dados preservados no banco (histórico transações, conta digital, notificações). Service: ClienteAuthService.excluir_cliente(), View: excluir_conta(), Rota: /excluir/. Arquivos: apps/cliente/services.py, apps/cliente/views.py, apps/cliente/urls.py

## Arquitetura do Sistema

```
wallclub_django/
├── wallclub/                    # Configurações Django
│   ├── settings/               # Configurações por ambiente (base, dev, prod)
│   └── urls.py                # Roteamento principal
├── apps/                       # APIs para aplicativos móveis
│   ├── cliente/               # ✅ Sistema de Autenticação JWT Customizado (18 cenários testados)
│   │   ├── jwt_cliente.py     # JWT customizado independente (ClienteJWTAuthentication, refresh_cliente_access_token)
│   │   ├── models.py          # ClienteJWTToken (token_type, auditoria), ClienteSenhasHistorico
│   │   ├── services_login_persistent.py  # Rate limiting, bloqueios progressivos
│   │   ├── services_2fa_login.py         # 2FA e dispositivos confiáveis
│   │   ├── services_autenticacao_analise.py # ✅ ClienteAutenticacaoAnaliseService (integração Risk Engine)
│   │   ├── views.py           # Endpoints cadastro (iniciar, finalizar, validar_otp)
│   │   ├── views_2fa_login.py # Endpoints 2FA (verificar, solicitar, validar)
│   │   ├── views_dispositivos.py # Endpoints dispositivos (listar, revogar)
│   │   ├── views_senha.py     # Endpoints senha (solicitar_reset, validar_reset, trocar)
│   │   ├── views_refresh_jwt.py # Endpoint refresh token (renovar access_token)
│   │   ├── views_autenticacao_analise.py # ✅ GET /autenticacao/analise/<cpf>/ (OAuth Risk Engine only)
│   │   ├── views_saldo.py     # Endpoints autorização uso de saldo (JWT)
│   │   └── views.py (excluir_conta) # ✅ POST /excluir/ - Soft delete (is_active=0 + revoga tokens JWT)
│   ├── transacoes/            # Saldo, extrato, comprovantes
│   ├── conta_digital/         # Conta digital customizada (saldo, cashback, autorizações)
│   │   ├── services.py        # ContaDigitalService (creditar, debitar, obter_saldo)
│   │   └── services_autorizacao.py # AutorizacaoService, CashbackService (cálculo uso máximo)
│   └── ofertas/               # Sistema completo de ofertas push com segmentação
│       ├── models.py          # Oferta, GrupoSegmentacao, GrupoCliente, OfertaDisparo, OfertaEnvio
│       ├── services.py        # OfertaService (criar, disparar push, segmentação, grupos)
│       ├── views.py           # API lista_ofertas, detalhes_oferta (JWT protegido)
│       └── urls.py            # Rotas de ofertas
├── parametros_wallclub/        # Sistema de parâmetros financeiros
│   ├── models.py              # ConfiguracaoVigente, Plano (3.840 registros migrados)
│   └── services.py            # CalculadoraDesconto 100% validada vs PHP
├── posp2/                      # Sistema POSP2 (Terminal POS)
│   ├── models.py              # TransactionData (transactiondata com cashback_concedido)
│   ├── services.py            # POSP2Service (OAuth, terminais)
│   ├── services_transacao.py  # TRDataService (processamento transações, slip impressão)
│   ├── services_conta_digital.py # SaldoService, CashbackService (concessão com retenção 30 dias)
│   ├── services_sync.py       # TransactionSyncService (sincronização)
│   ├── views.py               # Endpoints POS (trdata, simula_parcelas, saldo, autorização)
│   └── urls.py                # Rotas POSP2
├── pinbank/cargas_pinbank/     # Automação de cargas Pinbank
│   ├── models.py              # PinbankExtratoPOS, BaseTransacoesGestao
│   ├── services.py            # CargaExtratoPOSService, CalculadoraBaseGestao
│   ├── services_ajustes_manuais.py # AjustesManuaisService (inserções/deleções corretivas)
│   └── management/commands/   # carga_extrato_pos, carga_base_gestao
├── portais/                    # Portais web administrativos
│   ├── controle_acesso/       # Sistema multi-portal de controle de acesso ✅ IMPLEMENTADO
│   │   ├── models.py          # PortalUsuario, PortalPermissao, PortalUsuarioAcesso
│   │   ├── services.py        # ControleAcessoService, AutenticacaoService, UsuarioService
│   │   ├── decorators.py      # @require_admin_access, @require_funcionalidade
│   │   └── middleware.py      # Portal detection, sessão segura
│   ├── admin/                 # Portal administrativo principal ✅ REFATORADO
│   │   ├── views_usuarios.py  # CRUD usuários com multi-portal e níveis granulares
│   │   ├── views_hierarquia.py # CRUD hierarquia (canais, regionais, vendedores, grupos, lojas)
│   │   ├── views_ofertas.py   # CRUD completo de ofertas (list, create, edit, disparar, historico)
│   │   ├── views_grupos_segmentacao.py # CRUD grupos (list, create, edit, gerenciar clientes)
│   │   ├── views_terminais.py # Gestão de terminais POS
│   │   ├── views_pagamentos.py # Gestão de pagamentos e lançamentos
│   │   ├── views_antifraude.py # Dashboard antifraude (integração Risk Engine)
│   │   ├── views_seguranca.py # ✅ Telas segurança (atividades suspeitas + bloqueios IP/CPF)
│   │   ├── services_terminais.py # TerminaisService
│   │   └── templates/         # 45+ templates (usuarios, hierarquia, ofertas, seguranca, etc)
│   ├── lojista/               # Portal do lojista
│   │   ├── views_ofertas.py   # CRUD de ofertas para lojistas
│   │   └── templates/ofertas/ # Templates de gestão de ofertas lojista
│   ├── corporativo/           # Portal corporativo
│   └── vendas/                # Portal de vendas (checkout presencial)
│       ├── views.py           # 17 views (login, dashboard, CRUD clientes, checkout)
│       ├── decorators.py      # @requer_checkout_vendedor
│       ├── templates/         # 9 templates (interface simplificada - pulldown unificado)
│       │   └── checkout.html  # Interface unificada: cartões salvos + "Usar novo cartão" no mesmo pulldown
│       └├── checkout/                    # Sistema de checkout e pagamentos
│   ├── link_pagamento_web/        # Checkout web (link de pagamento)
│   │   ├── models.py              # CheckoutToken, CheckoutSession, CheckoutTransaction
│   │   ├── models_2fa.py          # ✅ CheckoutClienteTelefone (autogerenciamento telefone)
│   │   ├── services.py            # CheckoutService (geração token, validação, processamento)
│   │   ├── services_2fa.py        # ✅ CheckoutSecurityService (OTP, telefone, 2FA)
│   │   ├── views.py               # Checkout flow (GET/POST)
│   │   ├── views_2fa.py           # ✅ Endpoints 2FA (solicitar_otp, validar_otp_e_processar)
│   │   └── templates/             # checkout.html, success.html, error.htmlizados
│   │   └── auditoria_service.py # AuditoriaService (570 linhas) - login, transações, usuários, configurações, dados sensíveis
│   ├── oauth/                 # Sistema OAuth 2.0 (POS + Apps) com Redis
│   ├── integracoes/           # NotificationService, Firebase, APN, WhatsAppService (OTP templates)
│   ├── utilitarios/           # ConfigManager, log_control (padrão auditoria.XX)
│   ├── middleware/            # ✅ SecurityValidationMiddleware (valida IP/CPF antes do login - fail-open)
│   ├── seguranca/             # ✅ Sistema de Segurança Completo
│   │   ├── models.py          # AutenticacaoOTP (códigos 6 dígitos, 5min), DispositivoConfiavel (30 dias)
│   │   ├── services_2fa.py    # OTPService (gerar, validar, WhatsApp)
│   │   └── services_device.py # DeviceManagementService (registrar, validar, revogar, limite 2 devices)
│   ├── estr_organizacional/   # Canal, Loja, Regional, GrupoEconomico, Vendedor
│   └── calculos/              # CalculadoraDesconto migrada do PHP
├── checkout/                   # Sistema de checkout (core compartilhado)
│   ├── models.py              # CheckoutCliente, CheckoutCartaoTokenizado, CheckoutTransaction (+ 7 campos antifraude: score_risco, decisao_antifraude, motivo_bloqueio, antifraude_response, revisado_por/em, observacao_revisao + status: BLOQUEADA_ANTIFRAUDE, PENDENTE_REVISAO), CheckoutTransactionAttempt
│   ├── models_recorrencia.py  # ✅ RecorrenciaAgendada (periodicidades, status, controle falhas, descricao)
│   ├── services.py            # ClienteService, CartaoTokenizadoService, CheckoutService
│   ├── services_antifraude.py # ✅ CheckoutAntifraudeService - Integração com Risk Engine (268 linhas)
│   ├── link_pagamento_web/    # Link de pagamento público (token único)
│   │   ├── models.py          # CheckoutToken, CheckoutSession
│   │   ├── models_2fa.py      # ✅ CheckoutClienteTelefone (telefone imutável), CheckoutTransactionHelper (usa checkout_transactions), CheckoutRateLimitControl
│   │   ├── services.py        # LinkPagamentoService (processar_checkout_link_pagamento + análise antifraude) - 330 linhas
│   │   ├── services_2fa.py    # ✅ CheckoutSecurityService - rate limiting (3/5/10), limite progressivo (R$100→200→500), Risk Engine, WhatsApp template
│   │   ├── serializers.py     # Validação de dados (CPF, cartão, bandeira)
│   │   ├── views.py           # Views refatoradas (50 linhas) - apenas orquestração
│   │   ├── views_2fa.py       # ✅ 3 APIs 2FA: solicitar-otp (com validações), validar-otp (processa pagamento), limite-progressivo
│   │   ├── urls_2fa.py        # ✅ Rotas 2FA (/2fa/solicitar-otp/, /2fa/validar-otp/, /2fa/limite-progressivo/)
│   │   └── templates/         # Interface HTML responsiva com JavaScript vanilla
│   └── link_recorrencia_web/  # ✅ Tokenização de cartão para recorrência (NOVO - 21/10/2025)
│       ├── models.py          # RecorrenciaToken (validade 72h)
│       ├── services.py        # RecorrenciaTokenService (criar_token_e_enviar_email, processar_cadastro_cartao)
│       ├── views.py           # checkout_recorrencia_view, processar_cadastro_cartao_view
│       ├── urls.py            # Rotas /api/v1/checkout/recorrencia/
│       └── templates/recorrencia/
│           ├── email_cadastro_cartao.html      # Email específico para recorrência
│           ├── checkout_recorrencia.html       # Formulário simplificado (só cartão)
│           ├── sucesso.html
│           └── erro.html
└── scripts/                    # Scripts de migração e validação

---

## WallClub Risk Engine (Container Separado - Porta 8004) ✅ **PRODUÇÃO**

**Status:** ✅ Operacional em produção desde 16/10/2025

**Integrações Concluídas:**
- ✅ **POSP2**: Intercepta transações antes do Pinbank (`posp2/services_antifraude.py` - 374 linhas)
- ✅ **Checkout Web - Link de Pagamento**: Intercepta antes do Pinbank (`checkout/link_pagamento_web/services.py` linha 117-183)
  - Service: `checkout/services_antifraude.py` (268 linhas)
  - Dados: CPF, valor, modalidade, parcelas, cartão, bandeira, IP, user_agent, device_fingerprint
  - Decisões: APROVADO (processa), REPROVADO (bloqueia + status='BLOQUEADA_ANTIFRAUDE'), REVISAR (processa + status='PENDENTE_REVISAO')
  - 7 campos novos em checkout_transactions: score_risco, decisao_antifraude, motivo_bloqueio, antifraude_response, revisado_por, revisado_em, observacao_revisao
  - SQL: `scripts/sql/adicionar_campos_antifraude_checkout.sql`
- ✅ **Autenticação Cliente** (30/10/2025): Score de autenticação 0-50 pontos
  - Endpoint: `GET /cliente/api/v1/autenticacao/analise/<cpf>/` (OAuth exclusivo Risk Engine)
  - Service: `services_autenticacao_analise.py` - ClienteAutenticacaoAnaliseService
  - Dados: status conta, histórico 24h, dispositivos, bloqueios 30d, 9 flags de risco
  - Integrado ao AnaliseRiscoService (soma ao score total)
  - 4 regras novas: dispositivo novo alto valor, IP novo + bloqueios, tentativas falhas, bloqueio recente
  - Configurações centralizadas: 29 parâmetros ConfiguracaoAntifraude (zero hardcode)
- ✅ **OAuth 2.0**: Autenticação client_credentials + Bearer token
- ✅ **Fail-open**: Erro no antifraude não bloqueia transações (segurança operacional)

```
wallclub-riskengine/
├── riskengine/                 # Configurações Django
│   ├── settings.py            # Configurações compartilhadas (MySQL + Redis)
│   └── urls.py                # Roteamento antifraude
├── antifraude/                # Sistema antifraude
│   ├── models.py              # TransacaoRisco, RegraAntifraude, DecisaoAntifraude
│   ├── services.py            # AnaliseRiscoService (5 regras básicas)
│   ├── notifications.py       # NotificacaoService (Email + Slack)
│   ├── views.py               # API análise automática (POST /api/antifraude/analisar/)
│   ├── views_revisao.py       # API revisão manual (pendentes, aprovar, reprovar)
│   └── urls.py                # Rotas /api/antifraude/
├── docs/                      # Documentação
│   └── engine_antifraude.md   # Guia completo do sistema
├── Dockerfile                 # Container isolado Python 3.11-slim
├── docker-compose.yml         # Deploy independente
└── requirements.txt           # Django 4.2.11 + gunicorn 21.2.0
```

**Arquitetura Docker - 5 Containers Orquestrados (19/10/2025):**
- **Orquestração:** docker-compose.yml centralizado em `/var/www/wallclub_django`
- **Repositório Risk Engine:** https://github.com/JeanPierreLessa/wallclub_django_risk_engine

**Containers em Produção:**
1. **wallclub-prod-release300** - Django principal (porta 8003)
   - 3 workers Gunicorn, 2GB RAM, 1.5 CPU
   - Network: default + wallclub-network
   
2. **wallclub-redis** - Cache compartilhado (porta 6379)
   - Volume persistente: redis_data
   - Tokens OAuth + sessões
   
3. **wallclub-riskengine** - APIs antifraude (porta 8004)
   - 3 workers Gunicorn, 512MB RAM, 0.5 CPU
   - Build: ../wallclub_django_risk_engine
   
4. **wallclub-celery-worker** - Tasks assíncronas
   - 4 workers, 256MB RAM, 0.5 CPU
   - 2 tasks: detectar_atividades_suspeitas, bloquear_automatico_critico
   
5. **wallclub-celery-beat** - Scheduler
   - 128MB RAM, 0.25 CPU
   - Executa tasks a cada 5min e 10min

**Deploy Unificado:**
```bash
cd /var/www/wallclub_django

# OPÇÃO 1: Subir todos os 5 containers
docker-compose down
docker-compose up -d --build

# OPÇÃO 2: Deploy seletivo (mantém Redis rodando)
docker-compose up -d --build --no-deps web riskengine celery-worker celery-beat

# Verificar status
docker-compose ps

# Logs individuais
docker-compose logs -f web
docker-compose logs -f riskengine
docker-compose logs -f celery-worker
```

**Credenciais OAuth (18/10/2025):**
- Separadas por contexto via AWS Secrets Manager (`wall/prod/db`)
- **Admin:** `RISK_ENGINE_ADMIN_CLIENT_ID/SECRET` (Portal Admin)
- **POS:** `RISK_ENGINE_POS_CLIENT_ID/SECRET` (POSP2 + Checkout)
- **Internal:** `RISK_ENGINE_INTERNAL_CLIENT_ID/SECRET` (Serviços internos)
- 3 clients OAuth cadastrados no Risk Engine: `wallclub-django`, `wallclub-pos-checkout`, `wallclub_django_internal`

**Portal Admin Integrado:**
- `/admin/antifraude/` - Dashboard de métricas completo
  - Filtros de período (Hoje, 7, 30, 90 dias)
  - Métricas: transações analisadas, decisões, taxa de aprovação, score médio
  - Performance: tempo médio e P95
  - Blacklist: total, ativos, bloqueios do período
  - Whitelist: total, automáticas, manuais, VIP
  - Transações por origem (POS, APP, WEB)
  - Top 5 regras acionadas com contadores
- `/admin/antifraude/pendentes/` - Transações para revisão
- `/admin/antifraude/historico/` - Histórico de revisões

**APIs Disponíveis:**
- `POST /api/antifraude/analisar/` - Análise de risco (score 0-100)
- `POST /api/antifraude/analyze/` - Análise completa (pública, usado por POS/Apps/Checkout)
- `GET /api/antifraude/decision/<id>/` - Consulta decisão de transação
- `POST /api/antifraude/validate-3ds/` - Valida autenticação 3D Secure
- `GET /api/antifraude/health/` - Health check do sistema
- `GET /api/antifraude/dashboard/?dias=7` - Métricas agregadas do período
- `GET /api/antifraude/revisao/pendentes/` - Lista pendentes
- `POST /api/antifraude/revisao/{id}/aprovar/` - Aprova transação
- `POST /api/antifraude/revisao/{id}/reprovar/` - Reprova transação
- `GET /api/antifraude/revisao/historico/` - Histórico

**Fase 2 Concluída (Semanas 8-14):**
-  MaxMind implementado (validação operacional pendente - fallback ativo)
-  3DS Service implementado (casca pronta para gateway real)
-  APIs REST públicas (analyze, decision, validate-3ds, health)
-  Integração POSP2 completa (intercepção antes do Pinbank)
-  Integração Checkout Web - Link de Pagamento completa (22/10/2025)
-  Logs detalhados de análise (score, regras, decisão, tempo)
-  Fail-open em caso de erro (segurança operacional)
-  Pendente: Apps Mobile, Testes E2E, Deploy staging

**Próximas Fases:** Integrar Apps Mobile, Testes E2E antifraude completo, Deploy staging

## Configuração de Desenvolvimento

### Pré-requisitos
- Docker e Docker Compose
- Credenciais AWS (para acesso ao Secrets Manager)
- **IMPORTANTE**: Banco de dados sempre via AWS Secrets Manager (sem fallback local)

### Instalação via Docker (Recomendado)

1. Clone o repositório:
```bash
git clone <url-do-repositorio>
cd wallclub_django
```

2. Configure as variáveis de ambiente:
```bash
cp .env.example .env
# Edite .env com suas configurações
```

3. Inicie o container:
```bash
docker-compose up --build
```

4. Acesse a aplicação:
- **Portais**: http://localhost:8005 (admin, vendas, lojista)
- **APIs**: http://localhost:8007/api/v1/
- **POS**: http://localhost:8006

### Instalação Local (Alternativa)

1. Crie ambiente virtual:
```bash
python3 -m venv venv
source venv/bin/activate
```

2. Instale dependências:
```bash
pip install -r requirements.txt
```

3. Configure banco via AWS Secrets Manager ou .env local

4. Execute migrações:
```bash
python manage.py migrate
```

## Padrões de Banco de Dados

### Collation Padronizada MySQL (OBRIGATÓRIO)

**Problema Resolvido:** Erro "Illegal mix of collations" em JOINs e WHERE

**Solução:** Padronização completa em `utf8mb4_unicode_ci` (compatível MySQL 5.7 e 8.0)

**Template para CREATE TABLE:**
```sql
CREATE TABLE nome_tabela (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    campo_texto VARCHAR(255) COLLATE utf8mb4_unicode_ci,
    campo_numero DECIMAL(10,2),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Conversão de Tabelas Existentes:**
```sql
-- CONVERT TO altera TODAS as colunas de texto automaticamente
ALTER TABLE nome_tabela 
  CONVERT TO CHARACTER SET utf8mb4 
  COLLATE utf8mb4_unicode_ci;
```

**Verificação de Inconsistências:**
```sql
-- Listar tabelas com collation diferente do padrão
SELECT TABLE_NAME, TABLE_COLLATION 
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'wallclub' 
  AND TABLE_COLLATION != 'utf8mb4_unicode_ci'
ORDER BY TABLE_NAME;

-- Listar COLUNAS com collation diferente
SELECT TABLE_NAME, COLUMN_NAME, COLLATION_NAME 
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = 'wallclub' 
  AND COLLATION_NAME IS NOT NULL
  AND COLLATION_NAME != 'utf8mb4_unicode_ci'
ORDER BY TABLE_NAME, COLUMN_NAME;
```

**Regra de Ouro:**
- ❌ NUNCA usar `COLLATE` em queries SQL
- ✅ Padronizar collation no schema usando `CONVERT TO`
- Se precisar COLLATE na query = schema está errado

**Tabelas Padronizadas (24/10/2025):**
- `wallclub.cliente` - Convertida para utf8mb4_unicode_ci
- `wallclub.baseTransacoesGestao` - Convertida para utf8mb4_unicode_ci
- `wallclub.pinbankExtratoPOS` - Convertida para utf8mb4_unicode_ci
- `wallclub.credenciaisExtratoContaPinbank` - Convertida para utf8mb4_unicode_ci
- `wallclub.transactiondata` - Convertida para utf8mb4_unicode_ci
- `wallclub.terminais` - Convertida para utf8mb4_unicode_ci

## Deploy em Produção

**Arquitetura: 5 Containers Orquestrados (19/10/2025)**

Sistema deployado via docker-compose em AWS EC2:
- **Servidor**: ubuntu@ip-10-0-1-46 (EC2)
- **Portas**: 8003 (Django), 8004 (Risk Engine), 6379 (Redis)
- **Configuração**: AWS Secrets Manager + IAM Role
- **Proxy**: Nginx + Gunicorn (3 workers por container)
- **Cache**: Redis com volume persistente
- **Tasks**: Celery (worker + beat) para detectores antifraude
- **Logs**: Docker logs + volumes mapeados (/logs)
- **Status**: 100% operacional em produção

**Benefícios:**
- ✅ Isolamento de responsabilidades (APIs, Cache, Tasks, Scheduler)
- ✅ Escalabilidade independente por container
- ✅ Resiliência (falha em task não afeta APIs)
- ✅ Deploy atômico ou seletivo
- ✅ Zero downtime de cache

## Status da Migração

### ✅ Módulos Funcionais (100%)
- [x] **APIs Mobile** - Login JWT, cadastro, saldo, extrato, comprovante
- [x] **Sistema de Parâmetros** - 3.840 configurações migradas, 100% validado vs PHP
- [x] **Calculadoras Financeiras** - CalculadoraDesconto com fidelidade total ao PHP
- [x] **Cargas Pinbank** - Extrato POS e Base Gestão (130+ variáveis) funcionando
- [x] **Autenticação** - JWT + API Keys + sistema de permissões
- [x] **Refatoração Services/Views (Fase 3)** - 25 queries diretas eliminadas, 22 métodos criados, views críticas 100% sem model.objects direto (17/10/2025)
- [x] **Deploy Produção** - Docker + AWS + MySQL operacional
- [x] **Portais Admin** - Interface administrativa Django completa
- [x] **Sistema Bancário** - Camada de serviços para operações financeiras
- [x] **Controle de Acesso Granular** - Sistema flexível com níveis admin_total, admin_canal, leitura_canal
- [x] **Gestão de Usuários Avançada** - Múltiplos acessos simultâneos, tipos de entidade, referências dinâmicas
- [x] **Sistema de Logs Customizado** - Controle dinâmico via banco, nomenclatura padronizada
- [x] **Lançamentos Manuais** - Interface completa para ajustes financeiros e cálculo de comissões
- [x] **Portal Lojista Otimizado** - Interface limpa, exportações AJAX, processamento em background
- [x] **Validação CPF + Blacklist** - Algoritmo mod-11, blacklist Redis, cache 24h, integração POSP2
- [x] **Decorators API Padronizados** - @handle_api_errors, @validate_required_params, 13 endpoints refatorados
- [x] **Templates WhatsApp/SMS Unificados** - senha_acesso e baixar_app padronizados entre canais
- [x] **Sistema de Exportações** - Processamento inteligente com email para arquivos grandes
- [x] **Conciliação Financeira** - Filtros TEF, múltiplos formatos de data, otimizações SQL
- [x] **Validação Completa** - Taxa de sucesso 100% Django vs PHP
- [x] **OAuth 2.0 Completo** - Autenticação para apps, checkout, posp2 com múltiplos contextos
- [x] **Sistema de Recorrência** - Módulo completo para pagamentos recorrentes
- [x] **Notificações Push** - Firebase para transações de cartão em tempo real
- [x] **API Pinbank Atualizada** - Tokenização de cartão com novo padrão
- [x] **Correção de Loops de Autenticação** - Inconsistências de sessão resolvidas
- [x] **Sistema de Primeiro Acesso** - Redirecionamento inteligente baseado em permissões
- [x] **Debugging de Autenticação** - Logs de senha temporária e validação completa
- [x] **Sistema de Email com Marca** - Identificação automática de canal para URLs personalizadas
- [x] **Portal Lojista Melhorado** - CSS de autenticação e templates otimizados
- [x] **Sistema Admin Canal** - Tipo de usuário admin_canal para gestão específica por canal
- [x] **Migração OAuth 2.0 Completa** - API Keys removidas, 100% OAuth 2.0
- [x] **Sistema de Checkout Completo** - Link público + Portal vendas com core compartilhado
- [x] **Transações Rastreáveis** - Transaction criada por vendedor (PENDENTE) → atualizada por cliente (APROVADA/NEGADA)
- [x] **Tabela de Tentativas** - CheckoutTransactionAttempt para auditoria de falhas sem poluir transaction principal
- [x] **Portal de Vendas** - CRUD clientes, tokenização cartões, 3 opções de pagamento, cálculo por bandeira
- [x] **Notificações PUSH Multi-Canal** - Sistema inteligente que envia push para app correto baseado na loja
- [x] **Query Extrato Otimizada** - Migrada para baseTransacoesGestao com filtro correto por canal
- [x] **Bundle ID Dinâmico** - APN busca bundle_id da tabela canal (não hardcoded)
- [x] **Módulo Pinbank Refatorado** - Services separados por responsabilidade, uso obrigatório de Decimal, comprovante com cashback
- [x] **Sistema de Autorização de Uso de Saldo - COMPLETO** - Fluxo end-to-end: validação → push → aprovação → débito → estorno/expiração
- [x] **Sistema de Ofertas Push** - CRUD completo (admin + lojista), segmentação customizada, disparo Firebase/APN, histórico
- [x] **Débito Automático** - Após INSERT em transactiondata, debita saldo automaticamente com lock pessimista
- [x] **Negação com Liberação** - Cliente pode negar mesmo após aprovar, libera saldo bloqueado
- [x] **Expiração Automática** - Django command para cron (1min), libera bloqueios expirados
- [x] **Slip com Saldo Usado** - Campo "Saldo utilizado de cashback" no comprovante POS
- [x] **Auth Tokens Seguros Redis** - Tokens temporários (15min) com cliente_id extraído do token (não da requisição)
- [x] **Endpoints Cliente + POS Separados** - apps/cliente/views_saldo.py (JWT) + posp2/views.py (OAuth POSP2)
- [x] **Lógica pode_processar** - PENDENTE/APROVADO = true, permite ação do cliente ou POS
- [x] **Bloqueio Inteligente de Saldo** - valor_bloqueado null (PENDENTE) → valor (APROVADO após cliente)
- [x] **Firebase Service Refatorado** - Método core genérico para push notifications, templates dinâmicos do banco
- [x] **Sistema de Cache Redis** - Redis em produção para auth tokens, sessões temporárias e validações
- [x] **Cálculo Dinâmico de Parcelas** - Todas as bandeiras (5) × 12 parcelas com valores calculados via ParametrosService
- [x] **Interface Checkout Responsiva** - Seletor de bandeira, parcelas dinâmicas, máscaras e validações
- [x] **Formato Resposta Padronizado** - Sempre {"sucesso": bool, "mensagem": str, ...} em todos endpoints
- [x] **Menu Lateral Responsivo** - Sidebar fixo desktop (280px) + hamburguer mobile (breakpoint 992px) nos portais Vendas e Lojista
- [x] **Ajustes Manuais de Base** - AjustesManuaisService para inserções/deleções corretivas (transactiondata + baseTransacoesGestao)
- [x] **Risk Engine em Produção** - Container separado (porta 8004) com 5 regras antifraude, portal de revisão manual integrado
- [x] **3DS Service Implementado** - Auth3DSService completo (casca pronta para gateway real: Adyen, Cybersource, Braspag)
- [x] **APIs REST Antifraude** - 4 endpoints públicos (analyze, decision, validate-3ds, health)
- [x] **Integração POSP2 com Antifraude** - Interceptação automática antes do Pinbank, fail-open, logs detalhados
- [x] **Otimizações de Performance** - 8 views críticas migradas de ORM para SQL direto (Portal Lojista + Portal Admin)
- [x] **Correção Bug Sobrescrita de Variáveis** - Bug crítico em posp2/services.py: id_loja buscado 4 vezes causava formas de pagamento usando loja errada (loja 1 vs 31). Correção: resolver id_loja uma única vez (linha 145), remover queries SQL desnecessárias em blocos de cashback (PIX/DÉBITO/CRÉDITO). Impacto: À VISTA retornava R$ 99.00 em vez de R$ 103.93. Backup: services.py.backup_20251024_140331 (24/10/2025)

### 🚧 Próximos Desenvolvimentos
- [ ] **Módulo Carteira** - Django-Ledger para controle financeiro
- [ ] **Sistema Cashback** - Regras customizadas + integração financeira
- [ ] **Campanhas Marketing** - Push notifications para lojistas
- [x] **OAuth 2.0** - Sistema completo implementado com múltiplos contextos
- [x] **Sistema de Recorrência** - Módulo completo para pagamentos recorrentes
- [x] **Notificações Push Firebase/APN** - Sistema completo com fallback automático (produção → sandbox)
- [x] **Sistema de Ofertas** - CRUD completo com segmentação, grupos customizados e upload de imagens
- [x] **Sistema de Auditoria de Login** - Registro completo de tentativas, bloqueio automático (5 falhas/15min), detecção de ataques
- [x] **Risk Engine Operacional** - Container em produção (porta 8004), portal admin integrado, APIs funcionais
- [ ] **Regras Antifraude Avançadas** - MaxMind, 3DS, velocity, listas (Semanas 8-14)
- [ ] **Integração POS/Checkout com Antifraude** - Intercepção automática (Semana 14)
- [ ] **Dashboard Analytics** - Métricas em tempo real para portais

### 📋 Funcionalidades Principais

**APIs REST (/api/v1/)**
- `POST /oauth/token/` - Autenticação OAuth 2.0
- `POST /auth/cliente/login/` - Login com OAuth + JWT
- `POST /auth/cliente/cadastro/` - Cadastro de clientes
- `POST /transacoes/saldo/` - Consulta saldo
- `POST /transacoes/extrato/` - Extrato com filtro por canal (baseTransacoesGestao)
- `POST /transacoes/comprovante/` - Comprovante detalhado com `valor_cashback` e `valor_pago_cliente`
- `POST /checkout/gerar-token/` - Checkout com OAuth
- `GET /recorrencia/cadastros/` - Gestão de recorrência
- `POST /posp2/consultar_saldo/` - Consulta saldo do cliente (sem senha)
- `POST /posp2/solicitar_autorizacao_saldo/` - Cria autorização + envia push para aprovação no app
- `POST /posp2/verificar_autorizacao/` - Polling de status (PENDENTE/APROVADO/NEGADO)
- `POST /posp2/simula_parcelas/` - Simula todas formas de pagamento + retorna `cards_principais: [3, 6, 10, 12]`
- `POST /posp2/trdata/` - Processa transação + movimentações automáticas em conta digital
  - **Movimentações Criadas** (até 2 por transação):
    1. **CRÉDITO Cashback** (se `cashback_concedido > 0`):
       - Método: `CashbackService.concessao_cashback()`
       - Destino: `cashback_bloqueado` (retenção de **30 dias**)
       - Tipo: `CASHBACK_CREDITO`, Status: `RETIDO`
       - Liberação automática após período
    2. **DÉBITO Uso de Saldo** (se `autorizacao_id` presente):
       - Método: `AutorizacaoService.debitar_saldo_autorizado()`
       - Origem: `cashback_disponivel` (saldo já liberado)
       - Tipo: `DEBITO_SALDO`, Status: `PROCESSADA`
       - Lock pessimista para concorrência
  - **Aceita campo `cashback_concedido`** no JSON de entrada
  - **Grava `cashback_concedido`** na tabela `transactiondata`
  - Slip de impressão inclui `saldo_usado` quando há autorização aprovada
  - Slip de impressão inclui `cashback_concedido` quando valor > 0
  - Cálculos ajustados: `vdesconto = valor_original - desconto_club - saldo_usado`
  - `vparcela = vdesconto / num_parcelas`
- `POST /cliente/aprovar_uso_saldo/` - Cliente aprova uso de saldo (JWT)
- `POST /cliente/negar_uso_saldo/` - Cliente nega uso de saldo (JWT, libera bloqueio se aprovado)
- `POST /cliente/verificar_autorizacao/` - Cliente verifica status (JWT)
- `POST /cliente/notificacoes/` - Lista últimas 30 notificações do cliente (JWT)
- `POST /cliente/notificacoes_ler/` - Marca notificações como lidas (JWT, aceita ID único ou array)
- `POST /ofertas/lista_ofertas/` - Lista ofertas vigentes (JWT, segmentação automática por canal/grupo)
- `POST /ofertas/detalhes_oferta/` - Busca oferta específica por ID (JWT, valida vigência e acesso)
- `POST /checkout/gerar-token/` - Gera token de checkout (OAuth autenticado)
- `GET /checkout/?token={token}` - Página HTML de checkout (público)
- `POST /checkout/simular_parcelas/` - Calcula todas bandeiras × 12 parcelas
- `POST /checkout/processar/` - Processa pagamento via Pinbank

**Calculadoras Financeiras**
- CalculadoraDesconto: PIX, Débito, Crédito, Parcelado (100% validado vs PHP)
- CalculadoraBaseGestao: 130+ variáveis financeiras migradas
- Parâmetros por loja/plano (Wall S/N) - 3.840 configurações ativas
- Lógica complexa preservada: valores[72], valores[74], valores[76]

**Sistema de Transações Pinbank**
- **Services Refatorados**:
  - `pinbank/services_transacoes_pagamento.py` - Transações com cartão (direto e tokenizado)
  - `pinbank/services_consulta_apps.py` - Consultas de extrato e comprovante
  - `pinbank/services.py` - Integração base e autenticação Pinbank
- **Métodos de Transação**:
  - `efetuar_transacao_cartao()` - Cartão direto (EfetuarTransacaoEncrypted)
  - `efetuar_transacao_cartao_tokenizado()` - Cartão salvo (EfetuarTransacaoCartaoIdEncrypted)
  - `incluir_cartao_tokenizado()` - Tokenização de cartão (IncluirCartaoEncrypted)
  - `consulta_dados_cartao_tokenizado()` - Consulta cartão salvo
- **Regras de Negócio**:
  - FormaPagamento automático: "1" (1 parcela) ou "2" (2-12 parcelas)
  - Valor sempre em centavos: `int(valor * 100)`
  - Simulação de parcelas: CRÉDITO 1x + PARCELADO 2-12x (PIX e DÉBITO comentados)
- **Integração**:
  - Usado em: Portal de Vendas, Link de Pagamento, Checkout Web
  - Criptografia AES-256 para comunicação com Pinbank
  - Logs detalhados de todas as transações

**Sistema de Ofertas Push com Segmentação**
- **Models**: `Oferta`, `GrupoSegmentacao`, `GrupoCliente`, `OfertaDisparo`, `OfertaEnvio`
- **Segmentação**: 
  - `todos_canal` - Disparo para todos clientes ativos do canal
  - `grupo_customizado` - Disparo para grupos específicos de clientes
- **Grupos de Segmentação**:
  - CRUD completo no portal admin
  - Gerenciamento manual de clientes (adicionar/remover)
  - Múltiplos grupos por canal
- **Upload de Imagens**:
  - Estrutura: `ofertas/oferta_{ID}_{TIMESTAMP}_{NOME_ORIGINAL}`
  - URLs completas: `https://apidj.wallclub.com.br/media/ofertas/...`
  - Volume mapeado: `-v $(pwd)/media:/app/media`
- **Push Notifications**:
  - Firebase: `custom_data = {"tipo": "oferta", "oferta_id": "X"}`
  - APN: Fallback automático produção → sandbox (certificado híbrido)
  - Templates dinâmicos por canal
- **APIs JWT**:
  - `POST /api/v1/ofertas/lista_ofertas/` - Lista ofertas vigentes
  - `POST /api/v1/ofertas/detalhes_oferta/` - Detalhes de oferta específica
- **Portais**:
  - Admin: CRUD + escolha canal + grupos + disparo push
  - Lojista: CRUD filtrado por canal da sessão
  - Histórico de disparos com estatísticas

**Cargas Automatizadas**
- Extrato POS Pinbank (30min, 72h, 60dias, ano) - Management commands
- Base Transações Gestão (130+ variáveis calculadas) - Migração PHP completa
- Sistema de lock, tratamento de erros e logs detalhados
- **AjustesManuaisService**: Correções automáticas de dados
  - Insere registros faltantes em `transactiondata` via cruzamento `pinbankExtratoPOS` × `terminais`
  - Remove duplicatas de `baseTransacoesGestao` sem `idFilaExtrato` (mantém versões válidas)
  - Queries SQL diretas com auditoria completa via logs
  - Localização: `pinbank/cargas_pinbank/services_ajustes_manuais.py`

**Sistema Bancário**
- PagamentoService: CRUD completo para pagamentos_efetuados
- LancamentoManual: Sistema completo de ajustes financeiros com auditoria
- Validações bancárias centralizadas e logs de auditoria
- Transações atômicas para operações críticas
- Arquitetura limpa: portais não manipulam tabelas financeiras diretamente
- Controles de integridade e conformidade com diretrizes do projeto

**Sistema de Controle de Acesso Granular**
- Níveis hierárquicos: `admin_total`, `admin_superusuario`, `admin_canal`, `leitura_canal`
- Models: `PortalUsuario`, `PortalPermissao`, `PortalUsuarioAcesso`
- Múltiplos acessos simultâneos por usuário (canal + regional + vendedor)
- Vínculos flexíveis: `entidade_tipo`/`entidade_id` (loja, canal, regional, grupo_economico, vendedor)
- Permissões granulares via JSON `recursos_permitidos`
- Service `ControleAcessoService` com mapeamento de strings para constantes
- Decorators: `@require_secao_permitida()` e `@require_acesso_padronizado()`
- Template tags: `tem_acesso`, `nivel_usuario`, `tem_secao_permitida`
- Filtros automáticos por canal em transações, RPR, hierarquia e terminais
- Queries otimizadas com `select_related` e campos inteiros para performance
- **Rotas otimizadas**: Portal admin e lojista com raiz como login (`/portal_admin/` → login, `/portal_admin/home/` → dashboard)
- **Filtros de listagem**: `admin_superusuario` não visualiza usuários com acesso ao portal admin
- **Logs otimizados**: Logs debug de controle de acesso removidos para melhor performance

**Sistema OAuth 2.0 Completo (100% Migrado)**
- Client Credentials Flow implementado
- Múltiplos contextos: `apps`, `checkout`, `posp2`, `pinbank`
- Decorators unificados em `comum/oauth/decorators.py`:
  - `@require_oauth_apps` - Apps móveis (aceita JWT de clientes)
  - `@require_oauth_checkout` - Checkout web
  - `@require_oauth_posp2` - Terminal POS/POSP2
- Tokens com expiração configurável (24h padrão)
- Refresh tokens automáticos
- **Segurança de Tokens:**
  - Access Token: 256 bits de entropia (`secrets.token_urlsafe(32)`)
  - Refresh Token: 256 bits de entropia (`secrets.token_urlsafe(32)`)
  - CSPRNG (Cryptographically Secure Pseudo-Random Number Generator)
  - Impossível de adivinhar por força bruta (~10⁷⁷ combinações)
- **API Keys completamente removidas**:
  - Pasta `comum/autenticacao/` deletada
  - Models `APIKey` e `APIUsage` removidos
  - Tabelas `api_keys` e `api_usage` drop via script SQL
  - `comum.autenticacao` removido do `INSTALLED_APPS`
  - Views de sistema desabilitadas (uso interno mantido via services)

**Sistema de Recorrência**
- Portal completo para gestão de pagamentos recorrentes
- Dashboard com métricas e filtros avançados
- Autenticação própria com login/logout
- Interface responsiva com Bootstrap 5
- Paginação e busca otimizada

**Sistema de Notificações PUSH Multi-Canal**
- **Push correto por canal**: Sistema identifica canal da LOJA (não do cliente)
- **Suporte multi-canal**: Cliente pode estar em vários canais simultaneamente (ex: WallClub + AgroClub)
- **Firebase + APN unificados**: Detecção automática do tipo de token
- **Bundle ID dinâmico**: Busca `bundle_id` da tabela `canal` (não hardcoded)
- **Templates customizáveis**: Sistema de templates para SMS e PUSH por canal (tabela `templates_envio_msg`)
- **Arquitetura refatorada**:
  - Método core `_enviar_push_core(cpf, ...)` para transações
  - Método core `_enviar_client_id_push_core(cliente_id, ...)` para autorizações
  - Templates JSON no banco: `{"title": "...", "body": "..."}`
  - Fallback automático se template não encontrado
- **Lógica implementada**:
  1. Busca canal via `loja_info.get('canal_id')` da transação
  2. Valida se cliente existe no canal específico da loja
  3. Envia push para o app correto (WallClub ou AgroClub)
- **pega_info_loja()** retorna: `{id, loja_id, loja, cnpj, canal_id}`
- **Logs detalhados**: Auditoria completa do fluxo de envio

**Fluxo de Uso de Saldo via POS (Wall Cashback)**
- **Validação de Senha**: POS valida CPF + senha, retorna saldo + auth_token (Redis 15min)
- **Segurança Auth Token**: `cliente_id` extraído do token (nunca aceito da requisição), validação de terminal e saldo
- **Solicitação de Autorização**: POS solicita uso de saldo com auth_token, push enviado automaticamente
- **Aprovação via App**: Cliente recebe push e aprova/nega no app (180s expiração)
- **Bloqueio de Saldo**: `valor_bloqueado` = `null` (PENDENTE) → `<valor>` (APROVADO após cliente aprovar)
- **Lógica `pode_processar`**: PENDENTE/APROVADO = `true`, NEGADO/EXPIRADO/CONCLUIDA = `false`
- **Débito de Saldo**: Após aprovação, POS debita saldo bloqueado
- **Finalização**: POS confirma com NSU ou estorna em caso de erro
- **Autenticação**: POS usa OAuth POSP2, cliente usa JWT próprio no app
- **Formato de Resposta**: `{"sucesso": bool, "mensagem": str, ...}` (NUNCA `success`/`error`/`data`)

**Sistema de Checkout Completo (Refatorado)**
- **Arquitetura Dupla**: Link de pagamento público + Portal de vendas compartilham core (`/checkout/`)
- **Models Core**: CheckoutCliente, CheckoutCartaoTokenizado, CheckoutTransaction, CheckoutTransactionAttempt
- **Fluxo de Transação**:
  1. **Vendedor cria transaction PENDENTE**: Via portal vendas, campos: token, cliente, loja_id, valor_transacao, vendedor_id, origem='CHECKOUT'
  2. **Envia email com link**: Cliente recebe link de pagamento
  3. **Cliente processa**: Acessa link, preenche cartão, processa via Pinbank
  4. **System atualiza transaction**: SE aprovado → nsu, codigo_autorizacao, forma_pagamento, parcelas, processed_at, status='APROVADA'
  5. **Registra tentativas**: SE negado → cria CheckoutTransactionAttempt, SE 3 tentativas → status='NEGADA'
- **CheckoutTransaction Refatorado**:
  - Campo `token` (UNIQUE) para relacionar com CheckoutToken
  - Campo `vendedor_id` para rastreamento
  - Timestamps separados: `created_at` (vendedor), `processed_at` (cliente)
  - Campos nullable até cliente processar: `forma_pagamento`, `nsu`, `codigo_autorizacao`
- **CheckoutTransactionAttempt** (nova tabela):
  - Auditoria de tentativas frustradas sem poluir transaction principal
  - Campos: tentativa_numero, erro_pinbank, pinbank_response, ip_address_cliente, numero_cartao_hash
- **Benefícios**: Zero duplicação, rastreabilidade completa, auditoria granular, queries otimizadas
- **Documentação**: `docs/4. sistema_checkout_completo.md`

**Sistema de Primeiro Acesso e Redirecionamento Inteligente**
- Ativação de conta via token de primeiro acesso
- Redirecionamento automático baseado em permissões do usuário:
  - 1 permissão → Portal específico (lojista, corporativo, recorrencia)
  - Múltiplas permissões → Portal admin
- Logs de debug para senha temporária e validação de autenticação
- Correção de inconsistências: `email_verificado=False` por padrão

**Correção de Loops de Autenticação**
- Diagnóstico e correção de inconsistências de sessão
- Padronização: sempre definir `portal_authenticated` + `portal_usuario_id`
- Debugging via container: verificação de código atual vs local
- Correção direta em produção quando necessário

## Stack Tecnológico

- **Backend**: Django 4.2.23 + Django REST Framework 3.16.1
- **Banco**: MySQL com tabelas wallclub + wclub (legado)
- **Cache**: Redis 7-alpine (IP fixo 172.18.0.2 em network Docker isolada)
- **Autenticação**: OAuth 2.0 (Client Credentials) + JWT (Simple JWT 5.5.1)
- **Financeiro**: Django-Ledger 0.5.6.5
- **Infraestrutura**: Docker + AWS Secrets Manager + Gunicorn + Redis
- **Integrações**: Pinbank API (refatorada), Bureau Service, AWS
- **Notificações**: Firebase Cloud Messaging + Apple Push Notification (HTTP/2)
- **Frontend**: Bootstrap 5.3.0 + JavaScript modular (portal-específico)
- **Exportações**: Processamento em background + envio por email
- **Logs**: Sistema customizado com controle dinâmico via banco
- **Segurança**: Rate limiting (Redis) + Auditoria de login + Bloqueio inteligente (CPF + IP)
- **Valores Monetários**: **SEMPRE** `Decimal` - NUNCA `float()`

## Padrões de Desenvolvimento

**Nomenclatura obrigatória (conforme diretrizes):**
- **Variáveis**: snake_case (`usuario_id`, `data_inicio`)
- **Funções**: snake_case (`buscar_usuario`, `calcular_desconto`)
- **Classes**: PascalCase (`UsuarioService`, `PagamentoEfetuado`)
- **Arquivos**: snake_case.py (`views_pagamentos.py`)
- **Templates**: snake_case.html (`usuario_form.html`)

**Estrutura obrigatória:**
- Services para toda manipulação de dados
- Utilitários centralizados em `comum/utilitarios/`
- Templates com herança obrigatória
- Validação de entrada em todas as funções

## Arquitetura e Models

### Visão Geral do Sistema

O WallClub Django é uma plataforma de gestão financeira com múltiplos portais:

- **Portal Admin**: Gestão completa do sistema
- **Portal Lojista**: Interface para lojistas  
- **Portal Recorrência**: Gestão de pagamentos recorrentes
- **Portal Vendas**: Checkout presencial com cadastro de clientes e tokenização
- **Sistema Bancário**: Transações e contas digitais

### Estrutura Organizacional (Hierarquia de Tabelas)

```
canal (id, nome) 
  ↓ canalId
regionais (id, nome, canalId)
  ↓ regionalId  
vendedores (id, nome, regionalId)
  ↓ vendedorId
gruposeconomicos (id, nome, vendedorId)
  ↓ GrupoEconomicoId
loja (id, razao_social, cnpj, GrupoEconomicoId, canal_id)
  ↓ loja_id
clientes (id, nome, cpf, loja_id)
```

### Sistema de Autenticação Multi-Portal

**Fluxo de Primeiro Acesso:**
1. Usuário é criado via portal admin com senha temporária
2. Email é enviado com link de ativação e senha temporária
3. Usuário acessa link, define nova senha
4. Sistema redireciona automaticamente baseado em permissões:
   - **Uma permissão**: Portal específico (lojista, corporativo, recorrencia)
   - **Múltiplas permissões**: Portal admin (controle total)

**Debugging de Autenticação:**
- Logs automáticos da senha temporária gerada
- Validação completa: `verificar_senha()`, `pode_acessar_portal()`, `ativo=True`, `email_verificado=True`
- Teste via `AutenticacaoService.autenticar_usuario()` para validar fluxo completo

### Sistema de Controle de Acesso Granular

**Arquitetura de 2 Tabelas:**

1. **`portais_permissoes`** - Define **O QUE** o usuário pode acessar
2. **`portais_usuario_acesso`** - Define **ONDE** o usuário tem acesso

**Níveis Granulares Implementados:**

```python
# Portal Admin
NIVEIS_ADMIN = [
    'admin_total',         # Acesso completo (inclui parâmetros)
    'admin_superusuario',  # Quase total (sem parâmetros)
    'admin_canal',         # Filtrado por canal
    'leitura_canal'        # Apenas leitura com filtro
]

# Portal Lojista  
NIVEIS_LOJISTA = [
    'admin_lojista',    # Todas as lojas
    'grupo_economico',  # Filtro por grupo
    'lojista'          # Loja específica
]
```

**Seções por Nível:**

```python
SECOES_POR_NIVEL = {
    'admin_total': [
        'dashboard', 'usuarios', 'transacoes', 'parametros',
        'relatorios', 'hierarquia', 'pagamentos', 'gestao_admin',
        'terminais', 'rpr'
    ],
    'admin_superusuario': [
        'dashboard', 'usuarios', 'transacoes', 'relatorios',
        'hierarquia', 'gestao_admin', 'terminais', 'rpr'
    ],
    'admin_canal': [
        'dashboard', 'transacoes', 'relatorios', 'hierarquia',
        'terminais', 'rpr', 'usuarios_canal'
    ]
}
```

**Validação em 2 Camadas:**

1. **Decorator `@require_secao_permitida('secao')`**: Bloqueia acesso via URL direta
2. **Template tag `{% tem_secao_permitida 'secao' %}`**: Esconde links no menu

**Exemplo de Uso:**

```python
# View protegida
@require_secao_permitida('gestao_admin')
def base_transacoes_gestao(request):
    # Apenas admin_total e admin_superusuario acessam
    pass
```

```django
<!-- Template com controle de menu -->
{% tem_secao_permitida 'gestao_admin' as pode_gestao %}
{% if pode_gestao %}
    <a href="...">Gestão Admin</a>
{% endif %}
```

**Múltiplos Acessos por Portal:**

O campo `portal` em `portais_usuario_acesso` permite que um usuário tenha diferentes entidades por portal:

```sql
-- Exemplo: Usuário 7 com múltiplos portais
SELECT * FROM portais_permissoes WHERE usuario_id = 7;
-- admin      | admin_superusuario
-- lojista    | admin_canal
-- recorrencia| operador  
-- vendas     | operador

SELECT * FROM portais_usuario_acesso WHERE usuario_id = 7;
-- portal='lojista'     | entidade_tipo='admin_canal' | entidade_id=6
-- portal='recorrencia' | entidade_tipo='loja'        | entidade_id=26
-- portal='vendas'      | entidade_tipo='loja'        | entidade_id=30
```

**Regras Críticas:**

1. ✅ `admin_total` e `admin_superusuario` **NÃO** criam registro em `portais_usuario_acesso` (acesso global)
2. ✅ Campo `portal` é **OBRIGATÓRIO** em `portais_usuario_acesso` (permite lojas diferentes por portal)
3. ✅ Constraint: `UNIQUE(usuario_id, portal, entidade_tipo, entidade_id)`
4. ✅ Delete + Insert ao editar usuário (garante consistência)

**Fluxo de Validação:**

1. Busca permissão: `PortalPermissao.objects.get(usuario=usuario, portal='admin')`
2. Obtém nível: `nivel_acesso = 'admin_superusuario'`
3. Busca seções: `SECOES_POR_NIVEL.get('admin_superusuario', [])`
4. Valida: `'gestao_admin' in secoes_permitidas`

**Debugging:**

```python
# Logs automáticos em desenvolvimento
registrar_log('portais.admin', 
    f'TEM_SECAO_PERMITIDA - Usuario: {usuario.id} - '
    f'Secao: {secao} - Nivel: {nivel_usuario} - '
    f'Secoes: {secoes_permitidas} - Tem acesso: {tem_acesso}'
)
```

### Models Principais por App

#### `comum/estr_organizacional/` - Hierarquia Organizacional
```python
# Tabelas: canal, regionais, vendedores, gruposeconomicos, loja
Canal: id, nome
Regional: id, nome, canalId → canal.id
Vendedor: id, nome, regionalId → regionais.id  
GrupoEconomico: id, nome, vendedorId → vendedores.id
Loja: id, razao_social, cnpj, GrupoEconomicoId → gruposeconomicos.id, canal_id
```

#### `portais/controle_acesso/` - Sistema de Permissões
```python
# Tabelas: portais_usuarios, portais_permissoes, portais_usuario_acesso
PortalUsuario: id, nome, email, senha
PortalPermissao: usuario_id → portais_usuarios.id, portal, nivel_acesso
PortalUsuarioAcesso: usuario_id → portais_usuarios.id, entidade_tipo, entidade_id, ativo
```

#### `apps/cliente/` - Gestão de Clientes
```python
# Tabelas: clientes, clientes_documentos
Cliente: id, nome, cpf, email, celular, loja_id → loja.id
ClienteDocumento: id, cliente_id → clientes.id, tipo_documento, numero
```

#### `apps/conta_digital/` - Contas Digitais
```python
# Tabelas: conta_digital, movimentacao_conta_digital, autorizacao_uso_saldo
ContaDigital: id, cliente_id, canal_id, saldo_atual, cashback_disponivel, cashback_bloqueado, ativa, bloqueada
MovimentacaoContaDigital: id, conta_digital_id, tipo_movimentacao_id, valor, saldo_anterior, saldo_posterior, 
                          descricao, referencia_externa, sistema_origem, status, data_liberacao, processada_em
AutorizacaoUsoSaldo: id, cliente_id, canal_id, valor_bloqueado, valor_usado, status (PENDENTE/APROVADO/NEGADO/EXPIRADO/CONCLUIDO),
                     autorizacao_id (UUID), terminal_id, expira_em, criado_em

# Tipos de Movimentação (por transação POS):
# 1. CASHBACK_CREDITO - Crédito de cashback com retenção de 30 dias (status=RETIDO, data_liberacao preenchida)
# 2. DEBITO_SALDO - Débito de uso de saldo aprovado via app (status=PROCESSADA)
```

#### `sistema_bancario/` - Transações
```python
# Tabelas: transacoes, contas_bancarias
Transacao: id, loja_id → loja.id, valor, status, tipo_transacao
ContaBancaria: id, loja_id → loja.id, banco, agencia, conta
```

#### `parametros_wallclub/` - Configurações
```python
# Tabelas: parametros_wall, configuracao_historico
ParametrosWall: id, loja_id → loja.id, taxa_desconto, prazo_pagamento
ConfiguracaoHistorico: id, loja_id → loja.id, data_alteracao, usuario_alteracao
```

### Queries SQL Essenciais

#### Navegação na Hierarquia Organizacional:
```sql
-- Lojas de um Canal
SELECT l.* FROM loja l 
JOIN gruposeconomicos ge ON l.GrupoEconomicoId = ge.id
JOIN vendedores v ON ge.vendedorId = v.id  
JOIN regionais r ON v.regionalId = r.id
WHERE r.canalId = ?

-- Lojas de um Grupo Econômico
SELECT * FROM loja WHERE GrupoEconomicoId = ?

-- Canal de uma Loja
SELECT c.* FROM canal c
JOIN regionais r ON c.id = r.canalId
JOIN vendedores v ON r.id = v.regionalId
JOIN gruposeconomicos ge ON v.id = ge.vendedorId
JOIN loja l ON ge.id = l.GrupoEconomicoId
WHERE l.id = ?
```

#### Sistema de Permissões:
```sql
-- Permissões de um usuário
SELECT portal, nivel_acesso FROM portais_permissoes WHERE usuario_id = ?

-- Vínculos de acesso
SELECT entidade_tipo, entidade_id FROM portais_usuario_acesso 
WHERE usuario_id = ? AND ativo = 1
```

### Fluxo de Dados Principal

1. **Loja** cria **Link de Pagamento**
2. **Cliente** efetua pagamento via **Checkout**  
3. **Transação** é registrada no **Sistema Bancário**
4. **Conta Digital** da loja é creditada
5. **Parâmetros** definem taxas e configurações por loja

## Problemas Conhecidos

### Checkout - Envio "baixar_app" Não Funciona (⚠️ PENDENTE)

**Status:** Problema não resolvido - pausado para priorizar outras features

**Descrição:**
- Template WhatsApp/SMS "baixar_app" não é enviado no fluxo de novo cadastro via Checkout (portal vendas)
- Logs mostram apenas envio de senha, não de "baixar_app"
- Templates existem no banco (canal_id=1, WhatsApp e SMS, ativos)
- POS funciona corretamente (envia "baixar_app" + senha na ordem)

**Código Implementado (não funcional):**
- Cache Bureau para evitar consulta dupla ✅
- Logs de diagnóstico em `portais/vendas/views.py`
- Ordem de envio: "baixar_app" → `cadastrar()` (senha)
- SMS "baixar_app" também implementado

**Próximos Passos (quando retomar):**
1. Verificar manualmente no container se código está atualizado
2. Investigar processo de deploy (Dockerfile COPY, volumes, cache)
3. Validar se `MessagesTemplateService.preparar_whatsapp(canal_id, 'baixar_app')` retorna template
4. Comparar fluxo POS (funcionando) vs Checkout (não funciona)

**Tempo Investido:** ~2h30 (16/10/2025)

**Referência:** Ver seção 35 em `docs/1. DIRETRIZES_CLAUDE.md` para detalhes técnicos completos

## Documentação

- `docs/1. DIRETRIZES_CLAUDE.md` - **DIRETRIZES OBRIGATÓRIAS** de desenvolvimento
- `docs/2. README.md` - Este documento (visão geral do sistema)
- `docs/4. sistema_checkout_completo.md` - Documentação completa do sistema de checkout (link + portal vendas)
- `docs/0. deploy_simplificado.md` - Setup Docker local e deploy AWS produção
- `docs/backups/estrategia_validacao_migracao.md` - Estratégia de migração PHP→Django
- `scripts/producao/` - Scripts de migração, validação e comparação Django vs PHP
- `curls_teste/checkout.txt` - Exemplos de uso da API de checkout

## Licença

Propriedade da WallClub.

```
{{ ... }}
├── Dockerfile                 # Container isolado Python 3.11-slim
├── docker-compose.yml         # Deploy independente
└── requirements.txt           # Django 4.2.11 + gunicorn 21.2.0
```

**## Deploy em Produção

**Ambiente:**
- AWS EC2 (Ubuntu 22.04)
- Docker + Docker Compose
- MySQL 8.0
- Redis 7.0
- Nginx (API Gateway)

**Containers Ativos:**
1. `wallclub-prod-release300` (porta 8003) - Monolito Django
2. `wallclub-prod-oauth` (porta 8005) - OAuth Server
3. `wallclub-riskengine` (porta 8004) - Risk Engine
4. `wallclub-redis` - Cache Redis

**Logs:**
- Application: `/app/logs/application.log`
- Auditoria: `/app/logs/auditoria.*.log`
- Checkout 2FA: `/app/logs/checkout.2fa.log`
- Antifraude: `/app/logs/antifraude.log`

---

## Status Atual do Projeto (18/10/2025)

**Progresso:** 21/31 semanas concluídas (~68%)

**✅ Fases Concluídas:**
- Fase 0: Preparação (2 semanas)
- Fase 1: Segurança Básica (4 semanas)
- Fase 2: Antifraude (8 semanas)
- Fase 3: Services e Refatoração (5 semanas)
- Fase 4: Semanas 20-21 - Sistema 2FA Checkout Web

**🟢 Concluído Recentemente:**
- **Fase 4 - Semana 21:** Sistema 2FA Checkout Web ✅ CONCLUÍDA (18/10/2025)
  - ✅ Backend completo (OTP, WhatsApp, rate limiting)
  - ✅ Frontend modal 3 etapas
  - ✅ Integração WhatsApp com template CURRENCY
  - ✅ Fail-open para APIs externas
  - ⏸️ **Aguardando autorização Pinbank para testes em produção**

- **Fase 4 - Semana 22:** Device Management ✅ CONCLUÍDA (18/10/2025)
  - ✅ DeviceManagementService (comum/seguranca/services_device.py)
  - ✅ Portal Admin: 5 endpoints + dashboard + menu
  - ✅ Limite 2 dispositivos por cliente, 2 por vendedor/lojista
  - ✅ Validade 30 dias, fingerprint MD5
  - ✅ Documentação completa para equipe mobile
  - ✅ Correções 31/10/2025: fingerprint do app sem modificação + verificação completa (elimina duplicidade)
  - ⏳ **Aguardando implementação mobile**

**⏳ Próximas Etapas:**
- Fase 4 - Semana 23: Risk Engine Bloqueios + Bureau CPF + Notificações Segurança + Revalidação Celular + App Móvel 2FA
- Fase 5: Quebra em Múltiplas Aplicações (6-8 semanas)

**🎯 Entregas Recentes:**
- Risk Engine operacional (16/10/2025)
- Sistema 2FA Checkout Web (18/10/2025)
- Gerenciamento de telefone com histórico completo
- Rate limiting persistente (BD + Redis)o_risk_engine

**Portal Admin Integrado:**
- `/admin/antifraude/` - Dashboard de métricas completo
  - Filtros de período (Hoje, 7, 30, 90 dias)
  - Métricas: transações analisadas, decisões, taxa de aprovação, score médio
{{ ... }}
- `docs/0. deploy_simplificado.md` - Setup Docker local e deploy AWS produção
- `docs/backups/estrategia_validacao_migracao.md` - Estratégia de migração PHP→Django
- `scripts/producao/` - Scripts de migração, validação e comparação Django vs PHP
- `curls_teste/checkout.txt` - Exemplos de uso da API de checkout

---

## Documentação Técnica

- **[ROTEIRO_MESTRE_SEQUENCIAL.md](plano_estruturado/ROTEIRO_MESTRE_SEQUENCIAL.md)** - Planejamento completo do projeto
- **[DIRETRIZES.md](1.%20DIRETRIZES.md)** - Padrões de código e arquitetura
- **[TESTE_CHECKOUT_2FA.md](fase4/TESTE_CHECKOUT_2FA.md)** - Testes do sistema 2FA

---

## Licença

Proprietary - WallClub Tecnologia Financeira.
