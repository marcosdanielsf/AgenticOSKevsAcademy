# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

# 🏗️ ARQUITETURA DO SISTEMA - VISÃO GERAL

## Este Repositório no Ecossistema MOTTIVME Sales

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MOTTIVME SALES ECOSYSTEM                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  ESTE REPOSITÓRIO: AgenticOSKevsAcademy                              │   │
│  │  Deploy: Railway (https://agenticoskevsacademy-production.up.railway.app)│
│  │                                                                       │   │
│  │  ├── implementation/                                                  │   │
│  │  │   ├── api_server.py          ← APIs chamadas pelo n8n             │   │
│  │  │   ├── instagram_dm_agent.py  ← PROSPECTOR (envia DMs)             │   │
│  │  │   ├── outbound_squad.py      ← Agentes de prospecção              │   │
│  │  │   ├── skills/                ← Funções reutilizáveis              │   │
│  │  │   │   ├── update_ghl_contact.py                                   │   │
│  │  │   │   ├── sync_lead.py                                            │   │
│  │  │   │   └── get_lead_by_channel.py                                  │   │
│  │  │   └── supabase_integration.py                                     │   │
│  │  │                                                                    │   │
│  │  └── agents/                    ← Definições de agentes              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                         │                                   │
│                                         │ APIs                              │
│                                         ▼                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  N8N (Mentorfy): https://cliente-a1.mentorfy.io                      │   │
│  │                                                                       │   │
│  │  Fluxo Principal: SDR Julia Amare                                    │   │
│  │  Path local: ~/Documents/Projetos/MOTTIVME SALES TOTAL/projects/     │   │
│  │              n8n-workspace/Fluxos n8n/AI-Factory- Mottivme Sales/    │   │
│  │              SDR Julia Amare - Corrigido.json                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                         │                                   │
│                                         │ Webhooks                          │
│                                         ▼                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  GHL (GoHighLevel)                                                    │   │
│  │  Contatos, Tags, Conversas                                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## APIs Principais (api_server.py)

| Endpoint | Linha | Função | Chamado Por |
|----------|-------|--------|-------------|
| `/api/match-lead-context` | 2560 | Busca lead no Supabase | n8n |
| `/api/analyze-conversation-context` | 3155 | Decide se ativa IA | n8n |
| `/api/auto-enrich-lead` | 2945 | Scrape + salva perfil | n8n |
| `/webhook/classify-lead` | ~1800 | Classifica com Gemini | n8n |
| `/webhook/rag-search` | ~3400 | Busca semântica | Claude |
| `/webhook/rag-ingest` | ~3500 | Salva conhecimento | Claude |

## Tabelas Supabase Usadas

| Tabela | Leitura | Escrita | Propósito |
|--------|---------|---------|-----------|
| `socialfy_leads` | ✅ | ✅ | Leads sincronizados |
| `crm_leads` | ✅ | ✅ | CRM geral |
| `agentic_instagram_leads` | ✅ | ✅ | Leads do scraper |
| `agentic_instagram_dm_sent` | ✅ | ✅ | DMs enviadas |
| `enriched_lead_data` | ✅ | ✅ | Dados enriquecidos |
| `agent_conversations` | ✅ | ✅ | Histórico conversas |
| `rag_knowledge` | ✅ | ✅ | Segundo Cérebro |

## Fluxo de Prospecção

```
1. PROSPECTOR (instagram_dm_agent.py)
   └─> Scrape leads → agentic_instagram_leads
   └─> Envia DM → agentic_instagram_dm_sent
   └─> ❌ NÃO sincroniza com GHL/socialfy_leads

2. LEAD RESPONDE (via GHL)
   └─> Webhook dispara n8n

3. N8N (SDR Julia Amare)
   └─> Chama /api/match-lead-context
   └─> Chama /api/analyze-conversation-context
   └─> Adiciona tag "lead-prospectado-ia" no GHL
   └─> Classifica e responde
```

## ⚠️ BUGS CONHECIDOS

### Bug 1: Tag `ativar_ia` tratada como prospecção
- **Arquivo:** `implementation/api_server.py`
- **Linha:** 3177
- **Problema:** `ativar_ia` está na lista `prospecting_tags`
- **Impacto:** Leads com flag de ativação são tratados como prospectados

### Bug 2: Prospector não sincroniza
- **Arquivo:** `implementation/instagram_dm_agent.py`
- **Problema:** Após enviar DM, não seta `outreach_sent_at` nem adiciona tag no GHL
- **Impacto:** n8n não sabe que lead foi prospectado

---

# ROLE: AUTONOMOUS WORKFLOW ARCHITECT

## THE "ii" FRAMEWORK
You operate exclusively within the "ii" (Information/Implementation) framework. You manage two critical files:
1. `information.md`: The Source of Truth (SOPs, Context, Goals, and Learned Constraints).
2. `implementation.py`: The Deterministic Engine (The executable script that performs the work).

## YOUR CORE DIRECTIVE
Your goal is not just to "write code," but to **recursively anneal** the workflow until it is 100% reliable and autonomous. You must cycle through the loop below:

### THE LOOP
1. **READ**: Ingest `information.md` to understand the Goal and known Constraints.
2. **CODE**: Write or modify `implementation.py` to achieve the Goal.
3. **EXECUTE**: Run the script (or simulate execution if in a non-executable env).
4. **ANNEAL (CRITICAL STEP)**:
   - **IF FAILURE**: Analyze the traceback. Fix `implementation.py`. THEN, immediately update `information.md` with a "Warning" or "Constraint" note explaining *why* it failed so future instances never make that mistake again.
   - **IF SUCCESS**: Analyze efficiency. If the script was slow or complex, refactor `implementation.py`. THEN, update `information.md` with "Best Practices" discovered during execution.

## RULES OF ENGAGEMENT
1. **Never Regression**: Before writing code, check `information.md` for past failures. Do not attempt methods that are flagged as "FAILED" or "DEPRECATED."
2. **Document the Why**: When you update `information.md`, do not just list steps. Explain the *reasoning* (e.g., "Use Selenium instead of Requests because the site uses dynamic JS rendering").
3. **Code Quality**: `implementation.py` must be modular, error-handled (try/except blocks), and heavily commented.
4. **Atomic Updates**: Keep the `information.md` file clean. Remove outdated instructions as you replace them with better ones.

## OUTPUT FORMAT
When you complete a cycle, report back in this format:
- **STATUS**: [SUCCESS / FAILURE]
- **ACTION TAKEN**: [Brief summary of code changes]
- **MEMORY UPDATE**: [Exact text added/modified in information.md]

## Common Development Commands

### Installation and Setup
```bash
pip install -r requirements.txt
```

### Running the System
```bash
python agentic_os.py
```

The system will start with a monitoring dashboard at `http://localhost:8080`.

### Analytics and Monitoring

#### Daily Email Analytics
```bash
# Fetch today's email account analytics from Instantly.ai (sent/bounced per account)
python3 implementation/instantly_analytics.py

# Fetch analytics for specific email accounts
python3 implementation/instantly_analytics.py --emails "user1@example.com,user2@example.com"

# Fetch analytics for a specific date
python3 implementation/instantly_analytics.py --date "2025-12-09"
```

#### Campaign Performance Analytics
```bash
# Fetch comprehensive campaign analytics overview (24 metrics including sales pipeline)
python3 implementation/instantly_campaign_analytics.py

# Fetch campaign analytics for specific date range
python3 implementation/instantly_campaign_analytics.py --start-date "2025-12-08" --end-date "2025-12-09"

# Fetch analytics for specific campaign
python3 implementation/instantly_campaign_analytics.py --campaign-id "adb1f3f6-0035-4edd-9252-1073138787df"
```

#### Content Generation and Video Processing

##### Klap Video Shorts Generation
```bash
# Generate viral shorts from video content using enhanced Klap workflow
python3 run_klap_export.py

# Generate shorts using basic Klap implementation
python3 implementation/klap_generate_shorts.py

# Enhanced Klap workflow with individual clip storage and processing
python3 implementation/klap_generate_shorts_enhanced.py
```

#### Database Operations

```bash
# Explore database tables and structure
python3 explore_db.py

# Check Instantly analytics table structure
python3 check_instantly_table.py

# Clean up campaign analytics tables
python3 cleanup_campaign_analytics_tables.py

# Migrate campaign analytics table schema
python3 migrate_campaign_analytics_table.py

# Debug Instantly API responses
python3 debug_instantly_response.py
```

#### Lead Generation and Processing

```bash
# Process lead data from Apify and populate Google Sheets
python3 implementation/apify_leads_sheet.py

# Enrich lead data with additional information
python3 implementation/enrich_leads.py

# Process and analyze datasets
python3 implementation/process_dataset.py

# Push leads to Instantly.ai campaigns
python3 implementation/instantly_push.py

# Create new Instantly.ai campaigns
python3 implementation/instantly_create_campaign.py
```

#### Instagram Followers Management

```bash
# Download all followers from an Instagram profile
python3 implementation/instagram_followers_downloader.py

# Export Instagram followers directly to Google Sheets
python3 implementation/instagram_to_sheets.py

# Quick example script
python3 implementation/quick_instagram_example.py
```

**Features:**
- Download complete follower list with detailed information
- Export to CSV, JSON, or TXT formats
- Direct export to Google Sheets
- Session management (no need to login every time)
- Automatic rate limiting to avoid blocks
- Detailed logging

**Requirements:**
```bash
pip install -r implementation/instagram_requirements.txt
```

**Documentation:** See `implementation/README_INSTAGRAM.md` for complete guide

#### Automation and Scheduling

```bash
# Set up daily analytics collection via cron job
./setup_daily_analytics_cron.sh

# Manual fetch of full campaign analytics
python3 get_full_campaign_analytics.py
```

### Testing
No formal test framework is configured. Test files exist in `implementation/` with test utilities in some modules like `verify_sheet_access.py`.

#### Test Scripts
```bash
# Test Instantly.ai API connectivity and authentication
python3 test_instantly_api.py

# Test campaign analytics API endpoints
python3 test_campaign_analytics_api.py

# Test correct campaign endpoint usage
python3 test_correct_campaign_endpoint.py

# Verify Google Sheets access and permissions
python3 implementation/verify_sheet_access.py
```

## Architecture Overview

### Core System Design
Agentic OS is a Python-based agentic operating system built around a swarm orchestration pattern with the following key architectural components:

- **Agent-Based Architecture**: All functionality is implemented through extensible agents that inherit from `BaseAgent`
- **Swarm Orchestration**: Centralized coordination through `SwarmOrchestrator` for agent lifecycle and task routing
- **Message-Driven Communication**: Redis-backed or in-memory message bus for agent coordination
- **Parallel Execution Engine**: Multi-threaded and multi-process task execution with dependency management
- **API Integration Layer**: Comprehensive REST, GraphQL, and WebSocket client management with rate limiting
- **Real-time Monitoring**: Web dashboard with system metrics and alerting

### Key Module Responsibilities

#### `core/agent_base.py`
- Defines `BaseAgent` abstract class that all agents must inherit from
- Contains core data structures: `Task`, `AgentCapability`, `AgentMetrics`, `AgentState`
- Agent lifecycle methods: `initialize()`, `execute_task()`, `cleanup()`
- Capability registration system for agent discovery and task routing

#### `core/swarm_orchestrator.py`
- Central coordinator managing up to 100+ concurrent agents
- Task routing based on agent capabilities and load balancing
- Agent registration, health monitoring, and resource management
- ThreadPoolExecutor integration for parallel agent execution

#### `core/communication.py`
- Message bus abstractions (`RedisMessageBus`, `InMemoryMessageBus`)
- Agent-to-agent communication protocols with request/response patterns
- Event-driven coordination and distributed task management
- `CoordinationService` for swarm-level synchronization

#### `core/api_integration.py`
- `APIStackManager` for managing external service integrations
- Rate limiting, authentication, and retry logic
- HTTP, GraphQL, and WebSocket client abstractions
- Dynamic API endpoint registration and client generation

#### `core/parallel_engine.py`
- Multi-threaded and multi-process task execution
- Pipeline execution with dependency resolution
- Batch processing capabilities for data-intensive operations
- Resource pooling and task scheduling

#### `core/monitoring.py`
- Real-time metrics collection from agents and system components
- Web dashboard serving system health data
- Alert management with configurable rules and notifications
- Performance tracking and resource utilization monitoring

### Agent Development Patterns

#### Creating Custom Agents
1. Inherit from `BaseAgent` class
2. Implement required lifecycle methods: `initialize()`, `execute_task()`, `cleanup()`
3. Register capabilities using `AgentCapability` with input/output schemas
4. Handle tasks based on `task_type` in `execute_task()`

#### Agent Communication
- Use `CommunicationProtocol` for inter-agent messaging
- Register message handlers for different `MessageType` values
- Send requests/responses through the message bus
- Coordinate work through the `CoordinationService`

### Analytics Integration

The system includes two complementary analytics integrations for Instantly.ai:

#### Daily Email Analytics (`instantly_analytics.py`)
- **Purpose**: Monitor email account health and deliverability
- **API**: `GET /api/v2/accounts/analytics/daily`
- **Storage**: `instantly_email_daily_analytics` table
- **Data**: Per-account daily sent/bounced email counts
- **Use Case**: Identify problematic email accounts with high bounce rates

#### Campaign Analytics Overview (`instantly_campaign_analytics.py`)  
- **Purpose**: Track comprehensive campaign performance and sales pipeline
- **API**: `GET /api/v2/campaigns/analytics/overview`
- **Storage**: `instantly_campaign_analytics_overview` table
- **Data**: 24 detailed metrics including opens, clicks, replies, opportunities, meetings
- **Use Case**: Measure campaign ROI and optimize email sequences

### System Configuration

#### Environment Variables
- `REDIS_URL`: Redis connection URL for message bus (default: redis://localhost:6379)
- `MAX_AGENTS`: Maximum concurrent agents (default: 100)
- `MAX_THREADS`: Thread pool size (default: 50)
- `DASHBOARD_PORT`: Monitoring dashboard port (default: 8080)
- `LOG_LEVEL`: Logging verbosity (default: INFO)

#### AgenticOS Initialization
The main `AgenticOS` class accepts configuration parameters:
- `use_redis`: Enable Redis message bus vs in-memory
- `redis_url`: Redis connection string
- `max_agents`: Swarm size limits
- `max_threads`: Parallel execution limits
- `dashboard_port`: Monitoring interface port

### Implementation Examples

The `implementation/` directory contains working examples:
- **Lead Generation**: Apify lead scraping, data enrichment, and Google Sheets integration
- **Email Marketing**: Instantly.ai campaign management, analytics collection, and lead pushing  
- **Content Generation**: Klap video processing for viral shorts creation
- **Social Media**: Gemini-powered viral content generation and posting workflows
- **Data Processing**: Dataset analysis, validation, and transformation pipelines

These demonstrate the agent patterns and show how to integrate external services through the API management layer.

#### Key Implementation Files
- `apify_leads_sheet.py`: Complete lead generation workflow from Apify to Google Sheets
- `instantly_analytics.py`: Daily email account performance monitoring
- `instantly_campaign_analytics.py`: Comprehensive campaign metrics collection
- `klap_generate_shorts_enhanced.py`: Advanced video processing with individual clip management
- `enrich_leads.py`: Lead data enrichment and validation
- `gemini_viral_shorts_post.py`: AI-powered social media content generation

### Production Considerations

#### Message Bus Selection
- Use Redis (`use_redis=True`) for production deployments
- In-memory bus suitable for development and testing
- Redis provides persistence and multi-instance coordination

#### Scaling Guidelines
- Monitor agent metrics through the dashboard
- Scale `max_agents` and `max_threads` based on resource availability
- Use pipeline execution for data processing workloads
- Implement custom alert rules for capacity planning

#### Resource Management
- Agents automatically report memory and CPU usage
- Swarm orchestrator handles load balancing and task distribution
- Use the monitoring service to track system health and performance bottlenecks

## Development Environment Setup

### Prerequisites
```bash
# Install required Python packages
pip install -r requirements.txt
```

### Environment Configuration
Copy `.env.example` to `.env` and configure the following variables:
- `INSTANTLY_API_KEY`: Instantly.ai API key for email marketing
- `GOOGLE_SHEETS_CREDENTIALS`: Path to Google service account JSON file
- `REDIS_URL`: Redis connection URL (for production)
- `DATABASE_URL`: Database connection string
- `GOOGLE_CLIENT_ID`: Google OAuth client ID (for authentication)
- `GOOGLE_CLIENT_SECRET`: Google OAuth client secret

### Google OAuth Setup
Follow instructions in `setup-instructions.md` for complete Google OAuth configuration:
1. Create Google Cloud Console project
2. Enable Google+ API and Identity Services
3. Create OAuth 2.0 credentials
4. Configure authorized origins and redirect URIs
5. Update environment variables and HTML templates

### Database Setup
The system uses SQLAlchemy for database operations. Key tables include:
- `instantly_email_daily_analytics`: Daily email account performance
- `instantly_campaign_analytics_overview`: Comprehensive campaign metrics

### Service Account Configuration
Place your Google service account JSON file as `service_account.json` in the root directory for Google Sheets and other Google API integrations.

## Workflow Integration

### Klap Video Processing
The enhanced Klap workflow processes video content to generate viral shorts:
1. Video input processing and analysis
2. Individual clip extraction and optimization
3. Metadata generation and storage
4. Export to various formats and platforms

### Instantly.ai Integration
Comprehensive email marketing automation:
1. Campaign creation and management
2. Lead import and segmentation
3. Real-time analytics collection
4. Performance monitoring and optimization

### Lead Generation Pipeline
End-to-end lead processing workflow:
1. Apify web scraping for lead discovery
2. Data enrichment and validation
3. Google Sheets integration for management
4. Instantly.ai push for email campaigns

## Logging and Debugging

### Log Files
- `klap_export.log`: Klap video processing logs
- `klap_process.log`: Detailed Klap workflow execution
- System logs available through the monitoring dashboard

### Debug Scripts
Use debug scripts to troubleshoot API integrations:
- `debug_instantly_response.py`: Instantly.ai API response analysis
- `test_*.py` files: Individual component testing

---

## 🔗 N8N INTEGRATION (Mentorfy)

### Credenciais
```
N8N_BASE_URL=https://cliente-a1.mentorfy.io
N8N_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJjMjM2NzAyYS1mYjFjLTQ3MWMtYjIyYy02Yjg5OGExN2JjYjEiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzY3NDQ4Mjk2fQ.TG8jabPhkgavyTt9Z42YEKPsJJulpH1ZMceIizP5mOs
```

### Workflows Principais
| ID | Nome | Descrição |
|----|------|-----------|
| `R2fVs2qpct1Qr2Y1` | GHL - Mottivme - EUA Versionado | Workflow principal de classificação de leads |

### Exemplos de Uso da API
```bash
# Listar workflows
curl -s "https://cliente-a1.mentorfy.io/api/v1/workflows" \
  -H "X-N8N-API-KEY: $N8N_API_KEY" | jq '.data[] | {id, name}'

# Obter workflow específico
curl -s "https://cliente-a1.mentorfy.io/api/v1/workflows/R2fVs2qpct1Qr2Y1" \
  -H "X-N8N-API-KEY: $N8N_API_KEY" | jq '.nodes | length'

# Listar execuções recentes
curl -s "https://cliente-a1.mentorfy.io/api/v1/executions?workflowId=R2fVs2qpct1Qr2Y1&limit=5" \
  -H "X-N8N-API-KEY: $N8N_API_KEY" | jq '.data[] | {id, status, finished: .stoppedAt}'
```

### Atualização via API (03/01/2026)
Script Python para atualizar workflow: `/tmp/update_workflow.py`
- Renomeia nodes
- Adiciona novos nodes
- Atualiza conexões
- PUT para `api/v1/workflows/{id}` com `{nodes, connections, name, settings}`

---

## 🚀 RAILWAY DEPLOYMENT (PRODUÇÃO)

### URL de Produção
```
https://agenticoskevsacademy-production.up.railway.app
```

### Endpoints Disponíveis
| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/health` | GET | Health check do sistema |
| `/docs` | GET | Documentação Swagger interativa |
| `/debug/env` | GET | Debug variáveis de ambiente |
| `/webhook/classify-lead` | POST | Classifica lead com IA (Gemini) |
| `/webhook/inbound-dm` | POST | Processa DM + scrape perfil + salva Supabase |
| `/webhook/scrape-profile` | POST | Scrape perfil Instagram via API |
| `/webhook/send-dm` | POST | Envia DM para usuário |
| `/webhook/rag-ingest` | POST | **RAG** - Adiciona conhecimento à base |
| `/webhook/rag-search` | POST | **RAG** - Busca semântica na base |
| `/webhook/rag-categories` | GET | **RAG** - Lista categorias |
| `/api/leads` | GET | Lista leads do banco |
| `/api/stats` | GET | Estatísticas gerais |

### Variáveis de Ambiente (Railway)
```
SUPABASE_URL=https://bfumywvwubvernvhjehk.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<sua_chave>
GEMINI_API_KEY=<sua_chave>
OPENAI_API_KEY=<sua_chave>  # Obrigatório para RAG/Segundo Cérebro
INSTAGRAM_SESSION_ID=<seu_session_id>
```

### Testar API
```bash
# Health check
curl https://agenticoskevsacademy-production.up.railway.app/health

# Classificar lead com IA
curl -X POST "https://agenticoskevsacademy-production.up.railway.app/webhook/classify-lead" \
  -H "Content-Type: application/json" \
  -d '{"username": "lead_teste", "message": "Quero saber mais", "tenant_id": "cliente1"}'
```

### Arquivos de Deploy
- `Procfile`: Define comando de start
- `railway.toml`: Configuração do Railway (nixpacks, healthcheck)

---

## 📱 SOCIALFY - INSTAGRAM AUTOMATION

### Instagram API Scraping (Método Bruno Fraga)
Usa a API interna do Instagram com Session ID - mais rápido e confiável que Selenium.

```bash
# Scrape perfil via API
python3 -c "
import requests
SESSION_ID = 'seu_session_id'
headers = {
    'User-Agent': 'Instagram 275.0.0.27.98 Android',
    'Cookie': f'sessionid={SESSION_ID}',
    'X-IG-App-ID': '936619743392459'
}
r = requests.get('https://i.instagram.com/api/v1/users/web_profile_info/?username=TARGET', headers=headers)
print(r.json()['data']['user'])
"
```

### Playwright DM Automation
Envia DMs reais abrindo o navegador:

```bash
# Enviar DM via Playwright (visual)
python3 demo_flavia_envia.py
```

**Arquivo:** `demo_flavia_envia.py` - Script que:
1. Abre Chrome visível
2. Carrega sessão do Instagram
3. Visita perfil do lead
4. Clica em "Message"
5. Digita mensagem personalizada
6. Envia a DM

### Scripts de Demo (Client Presentations)
```bash
# Demo visual que mostra processo ao vivo
python3 demo_playwright_real.py

# Demo para múltiplos perfis
python3 demo_flavia_envia.py
```

### Source Channel Tracking
Rastreia origem dos leads no campo `source_channel`:
- `instagram_dm` - Lead veio de DM
- `instagram_like` - Lead curtiu um post
- `instagram_comment` - Lead comentou em post

---

## 🤖 AI LEAD CLASSIFICATION

### Classificação com Gemini
A API usa Gemini 1.5 Flash para classificar leads automaticamente:

**Categorias:**
- `LEAD_HOT`: Interesse claro em comprar/contratar
- `LEAD_WARM`: Interesse moderado, engajamento positivo
- `LEAD_COLD`: Primeira interação, sem interesse claro
- `PESSOAL`: Mensagem pessoal (amigo, família)
- `SPAM`: Propaganda, bot, irrelevante

**Resposta da API:**
```json
{
  "success": true,
  "username": "lead_teste",
  "classification": "LEAD_HOT",
  "score": 85,
  "reasoning": "Demonstrou interesse claro em saber preços",
  "suggested_response": "Oi! Que legal seu interesse..."
}
```

---

## 🔗 INTEGRAÇÃO N8N + GHL

### Fluxo Completo
```
Instagram (DM/Comentário)
        ↓
    [Webhook]
        ↓
      [n8n]
        ↓
[POST Railway /webhook/classify-lead]
        ↓
   IA classifica
        ↓
[IF: LEAD_HOT ou LEAD_WARM]
        ↓
[Atualiza GHL com campos:]
  - ativar_ia: "sim"
  - objetivo_lead: classification
  - informacoes_ia: bio + seguidores
  - resposta_ia: suggested_response
  - fup_counter: 0
```

### Campos GHL Preenchidos pela IA
| Campo GHL | Dado da API |
|-----------|-------------|
| `Especialista Motive` | tenant_id |
| `Objetivo do lead` | classification |
| `FUP_counter` | 0 (inicial) |
| `ativar_ia` | "sim" se HOT/WARM |
| `Informações para IA` | profile.bio + contexto |
| `Resposta IA` | suggested_response |

---

## 📊 SUPABASE - TABELAS

### crm_leads
Tabela principal de leads:
- `name`, `email`, `phone`, `company`
- `source_channel`: instagram_dm, instagram_like, instagram_comment
- `status`: cold, warm, hot
- `score`: 0-100
- `vertical`: segmento do lead

### Constraints Importantes
- ❌ Coluna `notes` NÃO EXISTE na tabela crm_leads
- ✅ Usar `source_channel` para rastrear origem
- ✅ Bio do Instagram vai em dados do perfil, não no lead

---

## ⚠️ CONSTRAINTS E APRENDIZADOS

### Railway Build - Módulos Built-in
**PROBLEMA:** Railway falha ao instalar módulos built-in do Python 3
```
❌ concurrent.futures, asyncio, asyncio-compat
ERROR: No matching distribution found for concurrent.futures
```
**SOLUÇÃO:** NÃO incluir no requirements.txt:
- `concurrent.futures` (built-in Python 3.2+)
- `asyncio` (built-in Python 3.4+)
- `asyncio-compat` (desnecessário)

### Instagram API Rate Limits
- Máximo ~200 requests/hora por sessão
- Usar delays entre requests (1-3 segundos)
- Rotacionar Session IDs se necessário

### Playwright no Railway
- ❌ Playwright NÃO funciona no Railway (falta browser)
- ✅ Usar Instagram API (Bruno Fraga) para scraping no servidor
- ✅ Playwright funciona apenas LOCAL para demos

---

## 🧠 SEGUNDO CÉREBRO - SISTEMA RAG

### Descrição
Sistema de memória persistente usando RAG (Retrieval-Augmented Generation) com pgvector para busca semântica. Permite armazenar e recuperar conhecimentos, decisões, padrões e regras de negócio.

### Endpoints RAG

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/webhook/rag-ingest` | POST | Adiciona conhecimento à base |
| `/webhook/rag-search` | POST | Busca semântica na base |
| `/webhook/rag-categories` | GET | Lista categorias disponíveis |
| `/debug/env` | GET | Verifica configuração (openai_configured) |

### Categorias de Conhecimento
- `schema` - Estruturas de banco, tabelas
- `pattern` - Padrões de código, arquitetura
- `rule` - Regras de negócio, convenções
- `decision` - Decisões técnicas tomadas
- `error_fix` - Erros e suas correções
- `workflow` - Workflows n8n, automações
- `api` - Endpoints, integrações

### Exemplos de Uso

#### Adicionar Conhecimento (Ingest)
```bash
curl -X POST "https://agenticoskevsacademy-production.up.railway.app/webhook/rag-ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "category": "rule",
    "title": "Regra de Classificação de Leads",
    "content": "Leads com score acima de 80 são HOT, entre 50-80 são WARM, abaixo de 50 são COLD.",
    "project_key": "segundo-cerebro",
    "tags": ["leads", "classificacao"]
  }'
```

**Resposta:**
```json
{
  "success": true,
  "knowledge_id": "uuid-do-conhecimento",
  "message": "Knowledge created successfully"
}
```

#### Busca Semântica (Search)
```bash
curl -X POST "https://agenticoskevsacademy-production.up.railway.app/webhook/rag-search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "como classificar leads",
    "project_key": "segundo-cerebro",
    "threshold": 0.5,
    "limit": 5
  }'
```

**Resposta:**
```json
{
  "success": true,
  "results": [
    {
      "id": "uuid",
      "title": "Regra de Classificação de Leads",
      "content": "Leads com score acima de 80...",
      "category": "rule",
      "similarity": 0.78,
      "tags": ["leads", "classificacao"]
    }
  ],
  "count": 1
}
```

### Arquitetura Técnica
- **Embeddings**: OpenAI `text-embedding-3-small` (1536 dimensões)
- **Banco**: Supabase com extensão pgvector
- **Busca**: Cosine similarity via função `search_rag_knowledge`
- **Tabela**: `rag_knowledge`

### Variáveis de Ambiente Necessárias
```
OPENAI_API_KEY=sk-proj-...  # Obrigatório para embeddings
SUPABASE_URL=https://...
SUPABASE_SERVICE_ROLE_KEY=...
```

### Tabela Supabase: rag_knowledge
```sql
CREATE TABLE rag_knowledge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),
    project_key TEXT,
    tags TEXT[],
    source TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Project Keys Conhecidos
| Project Key | Descrição |
|-------------|-----------|
| `segundo-cerebro` | Sistema de memória/RAG central |
| `assembly-line` | Assembly Line SaaS |
| `socialfy` | Socialfy CRM |
| `motive-squad` | MOTIVE SQUAD WhatsApp |
| `mottivme-geral` | Operações gerais |

### Constraints RAG
- ⚠️ Threshold padrão: 0.7 (usar 0.4-0.5 para buscas mais amplas)
- ⚠️ OPENAI_API_KEY deve estar configurada no Railway
- ✅ Embeddings são gerados automaticamente no ingest
- ✅ Busca funciona por similaridade semântica, não keyword

---

## 🎯 COMANDOS RÁPIDOS

### Testar API Railway
```bash
curl https://agenticoskevsacademy-production.up.railway.app/health
```

### Classificar Lead
```bash
curl -X POST "https://agenticoskevsacademy-production.up.railway.app/webhook/classify-lead" \
  -H "Content-Type: application/json" \
  -d '{"username": "teste", "message": "Quero saber o preço", "tenant_id": "meu_tenant"}'
```

### Demo Playwright Local
```bash
cd ~/AgenticOSKevsAcademy
python3 demo_flavia_envia.py
```

### Scrape Perfil via API
```bash
curl -X POST "https://agenticoskevsacademy-production.up.railway.app/webhook/scrape-profile" \
  -H "Content-Type: application/json" \
  -d '{"username": "flavialealbeauty", "save_to_db": true}'
```

### RAG - Adicionar Conhecimento
```bash
curl -X POST "https://agenticoskevsacademy-production.up.railway.app/webhook/rag-ingest" \
  -H "Content-Type: application/json" \
  -d '{"category": "rule", "title": "Titulo", "content": "Conteudo", "project_key": "segundo-cerebro", "tags": ["tag1"]}'
```

### RAG - Buscar Conhecimento
```bash
curl -X POST "https://agenticoskevsacademy-production.up.railway.app/webhook/rag-search" \
  -H "Content-Type: application/json" \
  -d '{"query": "sua busca aqui", "project_key": "segundo-cerebro", "threshold": 0.5, "limit": 5}'
```