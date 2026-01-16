# AgenticOS - Contexto do Projeto

> **Atualizado em:** 2026-01-16
> **Leia este arquivo primeiro após qualquer reset de memória**

---

## Objetivo Principal

Sistema de **prospecção automatizada B2B** com IA para a MOTTIVME. Faz scraping de leads no Instagram, qualifica com ICP scoring por tenant, envia DMs personalizadas e sincroniza com GHL (GoHighLevel).

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
