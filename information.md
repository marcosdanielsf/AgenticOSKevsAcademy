# INFORMATION.MD - Source of Truth

> Framework "ii" - Este arquivo contém SOPs, Context, Goals, e Constraints Aprendidas.
> Última atualização: 2025-12-31 (v2.0 - 23 Agentes)

---

## 1. VISÃO GERAL DO PROJETO

### Socialfy - Lead Generation & DM Automation System

Sistema multi-agente de nível **UNICÓRNIO** para geração de leads e automação de DMs no Instagram.

**Arquitetura:**
- **23 agentes especializados em 6 squads**
- Orchestrator central (Maestro)
- API Server (FastAPI) para integração com n8n
- Supabase como banco de dados (REST API + RLS multi-tenant)
- Gemini Vision para análise de perfis (GRATUITO)
- Multi-tenant com versionamento de personas

---

## 2. ARQUITETURA DE AGENTES (23 AGENTES)

### 2.1 Orchestrator (Maestro)
- Coordena todos os 23 sub-agentes
- Roteia tasks por tipo
- Executa workflows multi-step
- Monitora saúde do sistema
- Failover automático

### 2.2 OUTBOUND SQUAD (Busca Ativa) - 5 Agentes

| Agente | Responsabilidade | Task Types |
|--------|------------------|------------|
| LeadDiscoveryAgent | Encontrar leads de múltiplas fontes | scrape_likers, scrape_commenters, scrape_followers |
| ProfileAnalyzerAgent | Analisar perfis com Gemini Vision | scrape_profile, analyze_posts |
| LeadQualifierAgent | Pontuar leads (0-100) por ICP | qualify_lead, batch_qualify |
| MessageComposerAgent | Criar mensagens personalizadas | compose_message, generate_hook |
| OutreachExecutorAgent | Enviar DMs com comportamento humano | send_dm, check_limits |

### 2.3 INBOUND SQUAD (Lead nos Aborda) - 3 Agentes

| Agente | Responsabilidade | Task Types |
|--------|------------------|------------|
| InboxMonitorAgent | Monitorar inbox por novas mensagens | check_inbox, start_monitoring |
| LeadClassifierAgent | Classificar leads com AI | classify_lead, check_whitelist |
| AutoResponderAgent | Gerar e enviar respostas contextuais | generate_response, send_response |

### 2.4 INFRASTRUCTURE SQUAD (Suporte) - 3 Agentes

| Agente | Responsabilidade | Task Types |
|--------|------------------|------------|
| AccountManagerAgent | Gerenciar contas, sessões, rotação | load_session, rotate_account |
| AnalyticsAgent | Coletar métricas e reports | get_daily_stats, track_event |
| ErrorHandlerAgent | Recovery, retry, alertas | handle_error, check_alerts |

### 2.5 SECURITY SQUAD (Segurança) - 4 Agentes

| Agente | Responsabilidade | Task Types |
|--------|------------------|------------|
| RateLimitGuardAgent | Proteção contra rate limiting | check_can_perform, consume_quota, report_warning |
| SessionSecurityAgent | Validação e refresh de sessão | validate_session, check_login_state |
| AntiDetectionAgent | Evitar detecção de bot | get_random_delay, simulate_human_typing |
| ComplianceAgent | GDPR/LGPD compliance | check_can_contact, record_opt_out |

### 2.6 PERFORMANCE SQUAD (Performance) - 4 Agentes

| Agente | Responsabilidade | Task Types |
|--------|------------------|------------|
| CacheManagerAgent | Cache de perfis e dados | cache_get, cache_set, cache_stats |
| BatchProcessorAgent | Processamento em lote | create_batch, process_batch, get_batch_status |
| QueueManagerAgent | Filas de prioridade | queue_push, queue_pop, queue_stats |
| LoadBalancerAgent | Distribuição de carga entre contas | get_next_account, report_health, rebalance |

### 2.7 QUALITY SQUAD (Qualidade) - 4 Agentes

| Agente | Responsabilidade | Task Types |
|--------|------------------|------------|
| DataValidatorAgent | Validação de dados | validate_username, validate_profile, detect_bot |
| MessageQualityAgent | Qualidade de mensagens | validate_message, check_personalization, analyze_tone |
| DeduplicationAgent | Prevenção de duplicatas | check_duplicate_lead, check_can_contact, mark_contacted |
| AuditLoggerAgent | Logging de auditoria | log_action, log_error, get_summary, export_logs |

---

## 3. CLASSIFICAÇÃO DE LEADS

### Tipos de Classificação
- **LEAD_HOT**: Interesse claro em comprar (score 70-100)
- **LEAD_WARM**: Interesse moderado (score 40-69)
- **LEAD_COLD**: Primeiro contato, sem interesse claro (score 0-39)
- **PESSOAL**: Contato conhecido (amigo, família)
- **SPAM**: Propaganda, bot, irrelevante

### Critérios de Scoring
| Critério | Pontos |
|----------|--------|
| Followers 100k+ | +20 |
| Followers 10k+ | +15 |
| Followers 1k+ | +10 |
| Keywords no bio (CEO, founder, etc) | +10 cada (max 30) |
| Conta business/creator | +20 |
| Verificado | +15 |
| Conta pública | +10 |
| 50+ posts | +5 |

---

## 4. API ENDPOINTS

### Base URL: `http://localhost:8000`

### Endpoints para n8n

```
POST /webhook/scrape-profile
  Body: { username, tenant_id?, save_to_db? }
  Response: { success, username, bio, followers_count, ... }

POST /webhook/scrape-likers
  Body: { post_url, limit?, tenant_id? }
  Response: { status: "started", check_results: "/api/leads" }

POST /webhook/scrape-commenters
  Body: { post_url, limit?, tenant_id? }
  Response: { status: "started" }

POST /webhook/send-dm
  Body: { username, message, tenant_id?, persona_id? }
  Response: { success, message_sent }

POST /webhook/classify-lead
  Body: { username, message, tenant_id, persona_id? }
  Response: { classification, score, reasoning, suggested_response }

POST /webhook/enrich-lead
  Body: { username, tenant_id? }
  Response: { profile, lead_score }

POST /webhook/check-inbox
  Body: { tenant_id?, limit? }
  Response: { unread_count, unread_conversations }

POST /webhook/n8n
  Body: { event, data, tenant_id? }
  Events: new_message, new_follower, post_liked, scheduled_dm
```

---

## 5. BANCO DE DADOS (SUPABASE)

### Tabelas Principais

```sql
-- Leads capturados
agentic_instagram_leads (
  id, username, full_name, bio,
  followers_count, following_count, posts_count,
  is_verified, is_private, source, source_url,
  tenant_id, created_at
)

-- DMs enviados
agentic_instagram_dm_sent (
  id, username, message, tenant_id, persona_id, sent_at
)

-- Leads classificados
classified_leads (
  id, tenant_id, persona_id, username,
  original_message, classification, score,
  ai_reasoning, suggested_response, classified_at
)

-- Multi-tenant
tenants (id, name, slug, settings)
tenant_personas (id, tenant_id, name, is_active, icp_pain_points, tone_of_voice)
tenant_known_contacts (id, tenant_id, username, contact_type)
```

---

## 6. CONSTRAINTS APRENDIDAS

### 6.1 Instagram Login
**PROBLEMA**: Seletores de login variam por idioma
```
❌ 'svg[aria-label="Home"]' - Só funciona em inglês
```
**SOLUÇÃO**: Usar múltiplos seletores + fallback por URL
```python
login_indicators = [
    'svg[aria-label="Home"]',           # EN
    'svg[aria-label="Página inicial"]', # PT-BR
    'svg[aria-label="Inicio"]',         # ES
    'a[href="/direct/inbox/"]',         # Universal
    'span:has-text("Pesquisa")',        # PT-BR
    'span:has-text("Search")',          # EN
]
# Fallback: verificar se URL não contém '/login'
```

### 6.2 Supabase Insertion
**PROBLEMA**: Campo inexistente causa 400 Bad Request
```
❌ Inserir campo 'notes' que não existe na tabela
```
**SOLUÇÃO**: Usar apenas campos existentes, filtrar dados antes de inserir

### 6.3 Gemini Vision
**PROBLEMA**: Claude API é caro para análise de perfis
```
❌ Usar claude-3-sonnet para cada perfil ($$$)
```
**SOLUÇÃO**: Usar Gemini 1.5 Flash (GRATUITO)
```python
import google.generativeai as genai
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")
```

### 6.4 Rate Limiting Instagram
**PROBLEMA**: Muitas ações = block temporário
**SOLUÇÃO**:
- Warmup gradual (7 dias)
- Limites: 50 DMs/dia, 10/hora
- Delays humanos: 30-120 segundos entre ações
- Rotação de contas

### 6.5 Git Divergent Branches
**PROBLEMA**: Conflito com outras sessões Claude
**SOLUÇÃO**:
```bash
git stash
git pull --rebase
git stash pop
```

### 6.6 Railway Build - Built-in Modules
**PROBLEMA**: Railway falha ao instalar módulos built-in do Python 3
```
❌ concurrent.futures, asyncio, asyncio-compat
ERROR: No matching distribution found for concurrent.futures
```
**SOLUÇÃO**: Não incluir no requirements.txt:
- `concurrent.futures` (built-in Python 3.2+)
- `asyncio` (built-in Python 3.4+)
- `asyncio-compat` (desnecessário, pode puxar concurrent.futures)

---

## 7. BEST PRACTICES

### 7.1 Sessões Instagram
- Salvar em `sessions/instagram_session.json`
- Carregar storage_state no context do Playwright
- Verificar login antes de qualquer ação

### 7.2 Mensagens Personalizadas
- Extrair primeiro nome do full_name
- Usar bio para criar hooks de conexão
- Adaptar tom por classificação (HOT=direto, COLD=acolhedor)
- Máximo 1-2 emojis

### 7.3 Error Handling
- Retry com exponential backoff (2^n segundos)
- Max 3 retries
- Rotação de conta em caso de block
- Alertas após 5 erros do mesmo tipo

### 7.4 Multi-tenant
- Todas as queries filtram por tenant_id
- Cada tenant tem suas próprias personas
- Whitelist de contatos conhecidos por tenant

---

## 8. COMANDOS DE EXECUÇÃO

```bash
# Instalar dependências
pip install -r requirements.txt
pip install playwright fastapi uvicorn google-generativeai
playwright install chromium

# Iniciar sistema completo
python implementation/socialfy_main.py

# Apenas API (para n8n)
python implementation/socialfy_main.py --api-only --port 8000

# Processar um lead
python implementation/socialfy_main.py --process @username

# Monitorar inbox
python implementation/socialfy_main.py --monitor-inbox

# Ver status do sistema
python implementation/socialfy_main.py --status
```

---

## 9. VARIÁVEIS DE AMBIENTE

```env
# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbG...

# Gemini (GRATUITO)
GEMINI_API_KEY=AIzaSy...

# API Server
API_SECRET_KEY=socialfy-secret-2024

# Instagram (opcional - credenciais são via sessão)
INSTAGRAM_USERNAME=
INSTAGRAM_PASSWORD=
```

---

## 10. INTEGRAÇÃO COM N8N

### Workflow de Classificação Inbox

```
[Webhook Trigger]
    → [Get Tenant]
    → [Check Whitelist]
    → [Get Persona]
    → [Scrape Profile]
    → [Classify with AI]
    → [Save to DB]
    → [Auto-respond if needed]
```

### Chamada do n8n para API

```javascript
// HTTP Request node
{
  "method": "POST",
  "url": "http://localhost:8000/webhook/classify-lead",
  "headers": {
    "Content-Type": "application/json",
    "X-API-Key": "socialfy-secret-2024"
  },
  "body": {
    "username": "{{ $json.from_username }}",
    "message": "{{ $json.message_text }}",
    "tenant_id": "{{ $json.tenant_id }}"
  }
}
```

---

## 11. PRÓXIMOS PASSOS

### ⚠️ TAREFA PENDENTE: Deploy Railway
**Status**: Aguardando deploy
**Branch**: `claude/project-overview-VJwte`
**PR**: https://github.com/marcosdanielsf/AgenticOSKevsAcademy/compare/main...claude/project-overview-VJwte

**Arquivos prontos para Railway:**
- `Procfile` - Configurado
- `railway.toml` - Configurado
- `requirements.txt` - Completo

**Variáveis de ambiente necessárias:**
```
INSTAGRAM_SESSION_ID=258328766%3AEKJ8m0QEivWYrN%3A26%3AAYhUMNhVmKHrhGMaUHaGq8g0VeaX8khoySa6eU2mfw
SUPABASE_URL=https://bfumywvwubvernvhjehk.supabase.co
SUPABASE_SERVICE_ROLE_KEY=(pegar em Supabase → Settings → API)
```

**Depois do deploy, usar no n8n:**
```
POST https://[URL-RAILWAY]/webhook/scrape-profile
Body: {"username": "perfil_instagram"}
```

### Bruno Fraga API Method (IMPLEMENTADO ✅)
Método de scraping via API interna do Instagram que extrai dados ocultos:
- Email real (não placeholder)
- Telefone
- WhatsApp linked
- User ID
- Facebook ID

**Arquivo**: `implementation/instagram_api_scraper.py`
**Uso**: Requer INSTAGRAM_SESSION_ID do cookie do navegador

### Source Channel Tracking (IMPLEMENTADO ✅)
Rastreamento de origem dos leads:
- `instagram_dm` - Leads de DMs
- `instagram_like` - Leads de curtidas em posts
- `instagram_comment` - Leads de comentários

### Pendente
- [ ] **Deploy no Railway** (tarefa salva acima)
- [ ] Integrar webhook com n8n existente (Mentorfy)
- [ ] Conectar com AI Factory Dashboard (Prompt Studio)
- [ ] Adicionar mais agentes para robustez
- [ ] Implementar testes automatizados
- [ ] Dashboard de métricas em tempo real

### Futuro
- [ ] Suporte a LinkedIn
- [ ] Suporte a Twitter/X
- [ ] AI Agent para CRM
- [ ] Integração com WhatsApp Business

---

## 12. LINKS RELACIONADOS

- **Repositório**: AgenticOSKevsAcademy (este)
- **socialfy-platform**: https://github.com/marcosdanielsf/socialfy-platform
- **n8n Workflows**: Dashboard → Automações
- **Supabase**: https://supabase.com/dashboard
- **Gemini API**: https://ai.google.dev/

---

> **REGRA DE OURO**: Sempre atualizar este arquivo após descobrir uma nova constraint ou best practice.
