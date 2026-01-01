# Socialfy Multi-Agent Lead Generation System

## Overview

This project integrates 23 Python AI agents with the existing Socialfy Platform (deployed on Vercel with Supabase) to create a fully automated Instagram lead generation and DM automation system.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SOCIALFY PLATFORM (Vercel)                         │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐    │
│   │   1,247+    │  │   Pipeline  │  │  Cadences   │  │   Multi-Channel │    │
│   │   Leads     │  │  Management │  │ & Sequences │  │ (IG/LI/WA/Email)│    │
│   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘    │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            SUPABASE DATABASE                                 │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐    │
│   │  crm_leads  │  │  socialfy_  │  │   agent_    │  │   llm_costs     │    │
│   │             │  │  messages   │  │conversations│  │                 │    │
│   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘    │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
          ┌────────────────────┴────────────────────┐
          │        supabase_integration.py          │
          │    (REST API Bridge - Python Layer)     │
          └────────────────────┬────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       ORCHESTRATOR (Maestro Agent)                          │
│                   Routes tasks, manages workflows                           │
└─────┬───────────────────┬───────────────────┬───────────────────┬───────────┘
      │                   │                   │                   │
      ▼                   ▼                   ▼                   ▼
┌──────────┐      ┌──────────┐      ┌──────────────┐      ┌─────────────┐
│ OUTBOUND │      │ INBOUND  │      │INFRASTRUCTURE│      │  SECURITY   │
│  SQUAD   │      │  SQUAD   │      │    SQUAD     │      │   SQUAD     │
│ (5 agents)│     │(3 agents)│      │  (3 agents)  │      │ (4 agents)  │
└──────────┘      └──────────┘      └──────────────┘      └─────────────┘
      │                   │                   │                   │
      ▼                   ▼                   ▼                   ▼
┌──────────┐      ┌──────────┐
│PERFORMANCE│     │ QUALITY  │
│  SQUAD   │      │  SQUAD   │
│(4 agents)│      │(4 agents)│
└──────────┘      └──────────┘
```

---

## 6 Squads, 23 Agents

### 1. OUTBOUND SQUAD (Active Lead Hunt) - 5 Agents

| Agent | Purpose | Task Types |
|-------|---------|------------|
| **LeadDiscovery** | Finds leads from Instagram sources | `scrape_likers`, `scrape_commenters`, `scrape_followers` |
| **ProfileAnalyzer** | Analyzes profiles with Gemini Vision AI | `scrape_profile`, `analyze_posts` |
| **LeadQualifier** | Scores leads (HOT/WARM/COLD) | `qualify_lead`, `batch_qualify` |
| **MessageComposer** | Creates personalized DM messages | `compose_message`, `generate_hook` |
| **OutreachExecutor** | Sends DMs with human-like behavior | `send_dm`, `check_limits` |

### 2. INBOUND SQUAD (Lead Comes to Us) - 3 Agents

| Agent | Purpose | Task Types |
|-------|---------|------------|
| **InboxMonitor** | Monitors Instagram inbox | `check_inbox`, `get_new_messages`, `start_monitoring` |
| **LeadClassifier** | Classifies leads with Gemini AI | `classify_lead`, `check_whitelist` |
| **AutoResponder** | Generates contextual responses | `generate_response`, `send_response` |

### 3. INFRASTRUCTURE SQUAD (Support) - 3 Agents

| Agent | Purpose | Task Types |
|-------|---------|------------|
| **AccountManager** | Manages Instagram accounts | `verify_session`, `rotate_accounts` |
| **Analytics** | Tracks metrics and performance | `log_metrics`, `get_reports` |
| **ErrorHandler** | Handles errors and recovery | `handle_error`, `notify_admin` |

### 4. SECURITY SQUAD (Protection) - 4 Agents

| Agent | Purpose | Task Types |
|-------|---------|------------|
| **RateLimitGuard** | Enforces rate limits | `check_limits`, `throttle` |
| **SessionSecurity** | Manages session security | `verify_session`, `refresh_cookies` |
| **AntiDetection** | Human-like behavior simulation | `randomize_delays`, `human_patterns` |
| **Compliance** | GDPR/privacy compliance | `check_consent`, `log_data_access` |

### 5. PERFORMANCE SQUAD (Optimization) - 4 Agents

| Agent | Purpose | Task Types |
|-------|---------|------------|
| **CacheManager** | Manages data caching | `cache_profile`, `invalidate_cache` |
| **BatchProcessor** | Processes leads in batches | `batch_process`, `queue_tasks` |
| **QueueManager** | Manages task queues | `enqueue`, `dequeue`, `prioritize` |
| **LoadBalancer** | Balances load across accounts | `distribute_load`, `health_check` |

### 6. QUALITY SQUAD (Quality Assurance) - 4 Agents

| Agent | Purpose | Task Types |
|-------|---------|------------|
| **DataValidator** | Validates data integrity | `validate_lead`, `check_duplicates` |
| **MessageQuality** | Ensures message quality | `check_grammar`, `detect_spam` |
| **Deduplication** | Removes duplicate leads | `dedupe_leads`, `merge_records` |
| **AuditLogger** | Logs all actions for audit | `log_action`, `generate_audit_report` |

---

## Supabase Integration

### Configuration (.env)

```env
SUPABASE_URL=https://bfumywvwubvernvhjehk.supabase.co
SUPABASE_ANON_KEY=eyJhbG...
SUPABASE_SERVICE_ROLE_KEY=eyJhbG...
```

### Tables Used (Existing Socialfy Platform)

| Table | Purpose | Agent Integration |
|-------|---------|-------------------|
| `crm_leads` | Lead data from Instagram/LinkedIn | LeadDiscovery saves new leads |
| `socialfy_messages` | Messages sent/received | MessageComposer, OutreachExecutor |
| `socialfy_leads` | Lead intelligence with ICP scores | ProfileAnalyzer, LeadQualifier |
| `agent_conversations` | AI agent conversation tracking | LeadClassifier, AutoResponder |
| `llm_costs` | AI/LLM usage cost tracking | Analytics agent logs costs |
| `socialfy_analytics_daily` | Daily aggregated metrics | Analytics agent |
| `socialfy_pipeline_deals` | Sales pipeline tracking | All squads |

### Integration Layer (`implementation/supabase_integration.py`)

```python
from implementation.supabase_integration import SocialfyAgentIntegration

integration = SocialfyAgentIntegration()

# When LeadDiscovery finds a new lead:
integration.save_discovered_lead(
    username="@johndoe",
    source="instagram",
    profile_data={"bio": "CEO at...", "followers_count": 10000}
)

# When ProfileAnalyzer scores a lead:
integration.save_profile_analysis(
    lead_id="uuid",
    analysis={"score": 85, "reasoning": "High engagement, business profile"}
)

# When MessageComposer creates a message:
integration.save_composed_message(
    lead_id="uuid",
    message="Oi João! Vi que você trabalha com..."
)

# When OutreachExecutor sends a DM:
integration.mark_message_sent(message_id="uuid")

# When LeadClassifier classifies a lead:
integration.save_classification(
    lead_id="uuid",
    classification="LEAD_HOT",
    analysis={"reasoning": "Asked about pricing"}
)
```

---

## Workflows

### 1. Outbound Lead Pipeline

```
LeadDiscovery → ProfileAnalyzer → LeadQualifier → MessageComposer → OutreachExecutor
     │                │                │                │                │
     ▼                ▼                ▼                ▼                ▼
Find leads     Analyze profile   Score & classify   Personalize DM    Send DM
from posts     with AI vision    (HOT/WARM/COLD)    with hooks       (rate limited)
```

### 2. Inbound Message Handler

```
InboxMonitor → LeadClassifier → ProfileAnalyzer → AutoResponder
     │              │                │                │
     ▼              ▼                ▼                ▼
Poll inbox    Classify with AI  Fetch profile    Generate &
for new DMs   (HOT/WARM/COLD)   if needed        send response
```

### 3. Full Enrichment

```
ProfileAnalyzer → LeadQualifier → Analytics
      │                │              │
      ▼                ▼              ▼
Scrape full      Score lead      Save to
profile data     0-100           database
```

---

## Directory Structure

```
AgenticOSKevsAcademy/
├── implementation/
│   ├── agents/
│   │   ├── base_agent.py           # Base agent class
│   │   ├── orchestrator.py         # Central coordinator
│   │   ├── outbound_squad.py       # 5 outbound agents
│   │   ├── inbound_squad.py        # 3 inbound agents
│   │   ├── infrastructure_squad.py # 3 infrastructure agents
│   │   ├── security_squad.py       # 4 security agents
│   │   ├── performance_squad.py    # 4 performance agents
│   │   └── quality_squad.py        # 4 quality agents
│   ├── supabase_integration.py     # Supabase REST API client
│   ├── api_server.py               # FastAPI backend (port 8001)
│   ├── instagram_dm_agent.py       # Instagram DM automation
│   ├── instagram_profile_scraper_gemini.py  # Profile scraping
│   └── ...
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── index.tsx           # Dashboard
│   │   │   ├── logs.tsx            # Real-time logs
│   │   │   └── metrics.tsx         # Analytics
│   │   ├── components/
│   │   │   ├── SquadCard.tsx       # Squad display
│   │   │   └── StatsCard.tsx       # Stats display
│   │   └── lib/
│   │       └── api.ts              # API client
│   └── next.config.js              # Proxy to backend
├── sessions/
│   └── instagram_session.json      # Instagram session
├── .env                            # Environment variables
└── PROJECT_OVERVIEW.md             # This file
```

---

## Running the System

### 1. Start the Backend

```bash
cd implementation
pip install -r requirements.txt
python api_server.py
# Running on http://localhost:8001
```

### 2. Start the Frontend

```bash
cd frontend
npm install
npm run dev
# Running on http://localhost:3001
```

### 3. Test Supabase Connection

```bash
python implementation/supabase_integration.py
# Should output: ✅ Connected to: https://bfumywvwubvernvhjehk.supabase.co
```

---

## Rate Limits (Safety)

| Action | Limit |
|--------|-------|
| DMs per hour | 10 |
| DMs per day | 50-200 |
| Delay between DMs | 30-120 seconds |
| Profile scrapes per hour | 30 |
| Inbox checks per minute | 1 |

---

## Requirements

### Environment Variables

```env
# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=xxx
SUPABASE_SERVICE_ROLE_KEY=xxx

# Instagram
INSTAGRAM_USERNAME=xxx
INSTAGRAM_PASSWORD=xxx
INSTAGRAM_SESSION_PATH=sessions/instagram_session.json

# AI
GEMINI_API_KEY=xxx

# Rate Limits
INSTAGRAM_DM_PER_HOUR=10
INSTAGRAM_DM_PER_DAY=200
INSTAGRAM_DM_DELAY_MIN=30
INSTAGRAM_DM_DELAY_MAX=60
```

### Python Dependencies

- playwright
- google-generativeai
- requests
- python-dotenv
- fastapi
- uvicorn

### Node.js Dependencies (Frontend)

- next
- react
- swr
- tailwindcss

---

## Next Steps

1. **Create Instagram Session**: Login to Instagram once to save session
2. **Configure ICP**: Set up ideal customer profile keywords
3. **Test Pipelines**: Run test leads through the system
4. **Monitor Dashboard**: Watch agents process leads in real-time

---

## Support

- API Docs: http://localhost:8001/docs
- Dashboard: http://localhost:3001
- Logs: http://localhost:3001/logs
- Metrics: http://localhost:3001/metrics
