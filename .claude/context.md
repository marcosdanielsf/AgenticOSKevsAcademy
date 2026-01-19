# AgenticOS - Contexto do Projeto

> **Atualizado em:** 2026-01-19
> **Status:** SISTEMA COMPLETO - Proxy + Stealth + Warm-up ✅
> **Leia este arquivo primeiro após qualquer reset de memória**

---

## Objetivo Principal

Sistema de **prospecção automatizada B2B** com IA para a MOTTIVME. Faz scraping de leads no Instagram, qualifica com ICP scoring por tenant, envia DMs personalizadas e sincroniza com GHL (GoHighLevel).

---

## ÚLTIMA SESSÃO (2026-01-19) - SISTEMA COMPLETO 🎉

### ✅ Nível de Segurança: 8/10

| Feature | Status | Descrição |
|---------|--------|-----------|
| Proxy Residencial | ✅ | Decodo/Smartproxy (gate.decodo.com:10001) |
| Playwright Stealth | ✅ | Anti-detection ativado |
| Warm-up Protocol | ✅ | 4 estágios, limites automáticos |
| Block Detection | ✅ | 8 tipos de bloqueio detectados |
| Spintax Híbrido | ✅ | Mensagens únicas (anti-spam) |
| Multi-Conta | ✅ | Rotação round-robin |

### ✅ Proxy Decodo Configurado
```
Host: gate.decodo.com
Port: 10001
Provider: Smartproxy
Tipo: Residential (BR)
Plano: 2GB pago
```

### ✅ Playwright Stealth Implementado
```python
from playwright_stealth import stealth_async
await stealth_async(self.page)  # Oculta automação
```

### ✅ Warm-up Protocol
| Estágio | Dias | DMs/dia | DMs/hora |
|---------|------|---------|----------|
| NEW | 1-3 | 5 | 2 |
| WARMING | 4-7 | 15 | 4 |
| PROGRESSING | 8-14 | 30 | 7 |
| READY | 15+ | 50 | 10 |

### ✅ Teste Final (2026-01-19 18:23)
```
✅ PROXY: gate.decodo.com:10001 (Residential)
✅ SPINTAX: 3/3 mensagens únicas
✅ BLOCK_DETECTION: 8 tipos funcionando
🎉 Sistema pronto para campanha real!
```

---

## SESSÃO ANTERIOR (2026-01-17) - RESUMO

### ✅ Problemas Resolvidos
1. **Erro 400 em campanhas** - `agent.start()` não era chamado antes de `run_campaign()`
2. **PIL/Pillow warning** - Adicionado ao requirements.txt
3. **Sessão não carregava no Railway** - Implementado carregamento de sessão do banco Supabase
4. **DMs funcionando** - Campanha enviou 1 DM com sucesso, 1 skipped (score baixo)

### ✅ Templates Charlie Morgan Implementados
- Mensagens **curtas, vagas, curiosas**
- Baseadas na **bio do lead**
- Sem pitch direto (gera curiosidade primeiro)
- Arquivo: `implementation/message_generator.py`

### ✅ Método Kevs Anti-Block Implementado (2026-01-17)
1. **`RoundRobinAccountRotator`** - Classe para rotação round-robin entre contas
2. **`run_campaign_kevs()`** - Método com delay em MINUTOS e rotação
3. **`target_type: "profiles"`** - Suporte a múltiplos perfis separados por vírgula
4. **Jitter humano** - Variação ±15% no delay para parecer natural

Arquivos modificados:
- `implementation/account_manager.py` - Adicionada classe `RoundRobinAccountRotator`
- `implementation/instagram_dm_agent.py` - Adicionado método `run_campaign_kevs()`
- `implementation/api_server.py` - Novos parâmetros: `kevs_mode`, `delay_min`, `delay_max`

---

## Arquitetura Atual

```
┌─────────────────────────────────────────────────────────────────┐
│                    AgenticOSKevsAcademy                         │
│                    Deploy: Railway                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  implementation/                                                │
│  ├── api_server.py        ← FastAPI (endpoints principais)     │
│  ├── instagram_dm_agent.py ← PROSPECTOR (scrape + DMs)         │
│  ├── lead_scorer.py       ← ICP Scoring multi-tenant           │
│  └── skills/              ← Funções reutilizáveis              │
│      ├── sync_lead.py                                          │
│      └── update_ghl_contact.py                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
          │
          │ APIs
          ▼
┌─────────────────────────────────────────────────────────────────┐
│  Supabase (bfumywvwubvernvhjehk.supabase.co)                   │
│  ├── agentic_instagram_leads    ← Leads scraped + scores       │
│  ├── tenant_icp_config          ← Config ICP por cliente       │
│  ├── growth_leads               ← Leads qualificados           │
│  └── rag_knowledge              ← Segundo Cérebro (RAG)        │
└─────────────────────────────────────────────────────────────────┘
          │
          │ Webhooks
          ▼
┌─────────────────────────────────────────────────────────────────┐
│  n8n (Mentorfy) + GHL (GoHighLevel)                            │
│  ├── SDR Julia Amare                                           │
│  ├── Follow Up Eterno                                          │
│  └── Classificação de Leads                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Stack Tecnológica

| Componente | Tecnologia |
|------------|------------|
| Backend API | Python + FastAPI |
| Deploy | Railway |
| Banco de Dados | Supabase (PostgreSQL + pgvector) |
| Orquestração | n8n (Mentorfy) |
| CRM | GoHighLevel |
| IA Classification | Google Gemini |
| IA Embeddings | OpenAI (RAG) |

---

## URLs de Produção

- **API:** https://agenticoskevsacademy-production.up.railway.app
- **Health:** https://agenticoskevsacademy-production.up.railway.app/health
- **Docs:** https://agenticoskevsacademy-production.up.railway.app/docs

---

## Funcionalidades Implementadas

### Lead Scoring Multi-Tenant (2026-01-16)
- Tabela `tenant_icp_config` com keywords e thresholds por cliente
- Scoring em 4 categorias: Bio (30), Engagement (30), Profile (25), Recency (15)
- Prioridades: HOT (>=70), WARM (50-69), COLD (40-49), NURTURING (<40)
- Cache de configuração em memória para performance

### Prospector GHL Sync (2026-01-16)
- Método `sync_to_ghl()` no instagram_dm_agent.py
- Tags automáticas: prospectado, outbound-instagram
- Custom fields: outreach_sent_at, last_outreach_message, source_channel

### RAG / Segundo Cérebro
- Endpoints: /webhook/rag-ingest, /webhook/rag-search
- Embeddings OpenAI text-embedding-3-small
- Busca semântica com pgvector

### Multi-Tenant Instagram Accounts (2026-01-17)
- Tabela `instagram_accounts` com múltiplas contas por tenant
- Sessões salvas em `session_data` (JSON do Playwright)
- AccountManager faz rotação automática de contas
- Limites por conta: `daily_limit`, `hourly_limit`
- Arquivo: `implementation/account_manager.py`

### Message Generator - Charlie Morgan Style (2026-01-17)
- Templates curtos, vagos, curiosos
- Extrai especialidades da bio do lead
- Níveis: ultra (score>=70), high (>=50), medium (<50)
- Arquivo: `implementation/message_generator.py`

### Spintax Híbrido (2026-01-17)
- **Saudação**: Spintax (variação sintática anti-spam)
- **Conteúdo**: IA (personalização semântica baseada na bio)
- **Fechamento**: Spintax (variação sintática anti-spam)
- Função: `expand_spintax()` - Expande `{opção1|opção2}` aleatoriamente
- Método: `generate_hybrid()` - Combina spintax + personalização IA
- Arquivo: `implementation/message_generator.py`

### Clone System SOP (2026-01-17)
- Documento consolidado com melhores práticas
- Protocolo de warm-up 21 dias
- Limites de segurança por conta
- Infraestrutura de proxies recomendada
- Instagram Private API (FBID, geolocation)
- Arquivo: `.claude/spec/clone-system-sop.md`

---

## Frontends Relacionados

| Projeto | URL | Função |
|---------|-----|--------|
| Socialfy Platform | socialfy-platform.vercel.app | CRM Prospecção (precisa integrar) |
| Factory AI Dashboard | front-factorai-mottivme-sales.vercel.app | Dashboard com Gemini |
| AgenticOS Dashboard | localhost:3001 | Monitor interno (não produção) |

---

## Agentes Especializados

Configurados em `.claude/settings.local.json`:

| Agente | Modelo | Função |
|--------|--------|--------|
| 🎯 @planner | opus | Arquitetura e planejamento |
| 💻 @coder | opus | Implementação de código |
| 🔍 @reviewer | haiku | Code review |
| 🎨 @ui-expert | sonnet | React/Tailwind/UX |
| ⚙️ @backend-expert | sonnet | Python/FastAPI |
| 🎭 @orchestrator | opus | Coordena outros agentes |

---

## Próxima Integração: Socialfy + Supabase

**Spec completa:** `.claude/spec/socialfy-integration.md`

**Objetivo:** Conectar Socialfy Platform ao Supabase real

**Tracks paralelos:**
1. Setup Supabase → @backend-expert
2. Hooks de Dados → @coder
3. Componentes UI → @ui-expert
4. Integração → @coder
5. Review → @reviewer

---

## Credenciais (Variáveis de Ambiente)

Configuradas no Railway:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `GEMINI_API_KEY`
- `OPENAI_API_KEY`
- `GHL_API_KEY`
- `GHL_LOCATION_ID`
