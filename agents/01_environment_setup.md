# SUBAGENTE 1: Environment Setup

## Objetivo
Configurar todo o ambiente base do AgenticOS para que os outros subagentes possam executar suas tarefas.

## Contexto
Você é um subagente especializado em configuração de ambientes Python. Sua tarefa é preparar o projeto AgenticOS para execução.

---

## TAREFAS A EXECUTAR

### 1. Atualizar requirements.txt

Adicionar as seguintes dependências que estão faltando:

```
# Browser Automation
playwright==1.40.0
playwright-stealth==1.0.6

# Database
psycopg2-binary==2.9.9
alembic==1.13.1

# API clients
requests==2.31.0
python-dotenv==1.0.0

# Google
google-auth==2.25.2
google-auth-oauthlib==1.2.0
google-api-python-client==2.111.0
gspread==5.12.3

# Apify
apify-client==1.6.4

# AI
google-generativeai==0.3.2
anthropic==0.8.1

# Video
yt-dlp==2023.12.30

# Utils
pandas==2.1.4
python-dateutil==2.8.2
```

### 2. Criar .env completo

Criar arquivo `.env` baseado no `.env.example` com TODAS as variáveis necessárias:

```bash
# === CORE ===
DATABASE_URL=postgresql://localhost:5432/agentic_os
REDIS_URL=redis://localhost:6379
LOG_LEVEL=INFO

# === INSTAGRAM DM AGENT ===
INSTAGRAM_USERNAME=
INSTAGRAM_PASSWORD=
INSTAGRAM_SESSION_PATH=sessions/instagram_session.json

# === INSTANTLY.AI ===
INSTANTLY_API_KEY=

# === APIFY ===
APIFY_API_KEY=
APIFY_GOOGLE_MAPS_ACTOR=compass/crawler-google-places
APIFY_CONTACT_SCRAPER_ACTOR=voyager/contact-scraper

# === GOOGLE ===
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_API_KEY=
GOOGLE_PROJECT_ID=
GOOGLE_SHEETS_SPREADSHEET_ID=
GOOGLE_SERVICE_ACCOUNT_FILE=service_account.json

# === KLAP ===
KLAP_API_KEY=
KLAP_WEBHOOK_URL=

# === GEMINI ===
GEMINI_API_KEY=

# === PHANTOMBUSTER ===
PHANTOMBUSTER_API_KEY=
PHANTOMBUSTER_AGENT_ID=

# === AYRSHARE ===
AYRSHARE_API_KEY=
AYRSHARE_BASE_URL=https://app.ayrshare.com/api
AYRSHARE_PROFILE_KEY=

# === NOTIFICATIONS ===
NOTIFICATION_WEBHOOK_URL=
```

### 3. Atualizar .gitignore

Garantir que o `.gitignore` inclui:

```
# Environment
.env
.env.local
.env.*.local

# Sessions & Credentials
sessions/
*.json
!.env.example
!package.json

# Logs
logs/
*.log

# Python
__pycache__/
*.py[cod]
*$py.class
.Python
venv/
env/
.venv/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Data
data/*.csv
data/*.json

# OS
.DS_Store
Thumbs.db
```

### 4. Criar estrutura de banco de dados

Criar arquivo `database/schema.sql`:

```sql
-- Instagram DM Agent Tables
CREATE TABLE IF NOT EXISTS instagram_leads (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(255),
    bio TEXT,
    followers_count INTEGER,
    following_count INTEGER,
    is_private BOOLEAN DEFAULT FALSE,
    profile_url VARCHAR(500),
    source VARCHAR(100),
    enriched_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS instagram_dm_sent (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER REFERENCES instagram_leads(id),
    username VARCHAR(255) NOT NULL,
    message_template VARCHAR(100),
    message_sent TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'sent',
    error_message TEXT,
    account_used VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS instagram_dm_agent_runs (
    id SERIAL PRIMARY KEY,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    total_leads INTEGER DEFAULT 0,
    dms_sent INTEGER DEFAULT 0,
    dms_failed INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'running',
    error_log TEXT,
    account_used VARCHAR(255)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_instagram_leads_username ON instagram_leads(username);
CREATE INDEX IF NOT EXISTS idx_instagram_dm_sent_lead_id ON instagram_dm_sent(lead_id);
CREATE INDEX IF NOT EXISTS idx_instagram_dm_sent_sent_at ON instagram_dm_sent(sent_at);
```

### 5. Instalar Playwright

Executar os comandos:

```bash
pip install playwright
playwright install chromium
```

### 6. Criar arquivo de configuração centralizado

Criar `config.py` na raiz:

```python
"""
Configuração centralizada do AgenticOS
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Paths
BASE_DIR = Path(__file__).parent
SESSIONS_DIR = BASE_DIR / "sessions"
LOGS_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"

# Garantir que os diretórios existem
SESSIONS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost:5432/agentic_os")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Instagram
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD")
INSTAGRAM_SESSION_PATH = SESSIONS_DIR / "instagram_session.json"

# Rate Limits
INSTAGRAM_DM_PER_HOUR = 10
INSTAGRAM_DM_PER_DAY = 200
INSTAGRAM_DM_DELAY_MIN = 30  # seconds
INSTAGRAM_DM_DELAY_MAX = 60  # seconds

# Instantly
INSTANTLY_API_KEY = os.getenv("INSTANTLY_API_KEY")
INSTANTLY_BASE_URL = "https://api.instantly.ai/api/v2"

# Apify
APIFY_API_KEY = os.getenv("APIFY_API_KEY")

# Google
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")
GOOGLE_SHEETS_SPREADSHEET_ID = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")

# Klap
KLAP_API_KEY = os.getenv("KLAP_API_KEY")

# Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
```

---

## VALIDAÇÃO

Após completar todas as tarefas, executar:

```bash
# Verificar instalação do Playwright
python -c "from playwright.sync_api import sync_playwright; print('Playwright OK')"

# Verificar variáveis de ambiente
python -c "from config import *; print('Config OK')"

# Verificar estrutura de pastas
ls -la sessions/ logs/ data/ agents/
```

---

## OUTPUT ESPERADO

Ao finalizar, reportar:

```
STATUS: SUCCESS / FAILURE
ARQUIVOS CRIADOS:
- requirements.txt (atualizado)
- .env (criado)
- .gitignore (atualizado)
- config.py (criado)
- database/schema.sql (criado)

DEPENDÊNCIAS INSTALADAS:
- playwright: OK/ERRO
- chromium: OK/ERRO

PASTAS CRIADAS:
- agents/: OK
- sessions/: OK
- logs/: OK
- data/: OK
- tests/: OK
- database/: OK
```
