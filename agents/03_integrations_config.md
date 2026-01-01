# SUBAGENTE 3: Integrations Config

## Objetivo
Validar e configurar todas as integrações existentes do AgenticOS (Instantly, Apify, Google Sheets, Klap, Gemini).

## Contexto
Você é um subagente especializado em configuração de APIs e integrações. Sua tarefa é garantir que todas as integrações do projeto estão funcionando corretamente.

## Dependências
- SUBAGENTE 1 deve ter completado (.env configurado)

---

## TAREFAS A EXECUTAR

### 1. Criar tests/test_all_integrations.py

Script mestre que testa todas as integrações:

```python
"""
Test all AgenticOS integrations
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Results tracking
results = {}


def test_instantly():
    """Test Instantly.ai API connection"""
    print("\n🔍 Testing Instantly.ai...")

    api_key = os.getenv("INSTANTLY_API_KEY")
    if not api_key:
        results["instantly"] = "❌ INSTANTLY_API_KEY not set"
        return False

    try:
        import requests
        response = requests.get(
            "https://api.instantly.ai/api/v2/campaigns",
            headers={"Authorization": f"Bearer {api_key}"}
        )

        if response.status_code == 200:
            campaigns = response.json()
            results["instantly"] = f"✅ Connected - {len(campaigns)} campaigns found"
            return True
        else:
            results["instantly"] = f"❌ Error {response.status_code}: {response.text[:100]}"
            return False

    except Exception as e:
        results["instantly"] = f"❌ Error: {str(e)}"
        return False


def test_apify():
    """Test Apify API connection"""
    print("\n🔍 Testing Apify...")

    api_key = os.getenv("APIFY_API_KEY")
    if not api_key:
        results["apify"] = "❌ APIFY_API_KEY not set"
        return False

    try:
        from apify_client import ApifyClient
        client = ApifyClient(api_key)

        # Get user info
        user = client.user().get()
        results["apify"] = f"✅ Connected as {user.get('username', 'unknown')}"
        return True

    except Exception as e:
        results["apify"] = f"❌ Error: {str(e)}"
        return False


def test_google_sheets():
    """Test Google Sheets API connection"""
    print("\n🔍 Testing Google Sheets...")

    service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")
    spreadsheet_id = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")

    if not Path(service_account_file).exists():
        results["google_sheets"] = f"❌ Service account file not found: {service_account_file}"
        return False

    if not spreadsheet_id:
        results["google_sheets"] = "⚠️ GOOGLE_SHEETS_SPREADSHEET_ID not set (optional)"
        return True  # Not critical

    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]

        creds = Credentials.from_service_account_file(service_account_file, scopes=scopes)
        client = gspread.authorize(creds)

        # Try to open spreadsheet
        spreadsheet = client.open_by_key(spreadsheet_id)
        results["google_sheets"] = f"✅ Connected - Spreadsheet: {spreadsheet.title}"
        return True

    except Exception as e:
        results["google_sheets"] = f"❌ Error: {str(e)}"
        return False


def test_klap():
    """Test Klap API connection"""
    print("\n🔍 Testing Klap...")

    api_key = os.getenv("KLAP_API_KEY")
    if not api_key:
        results["klap"] = "❌ KLAP_API_KEY not set"
        return False

    try:
        import requests
        response = requests.get(
            "https://api.klap.app/v1/videos",
            headers={"Authorization": f"Bearer {api_key}"}
        )

        if response.status_code == 200:
            results["klap"] = "✅ Connected"
            return True
        elif response.status_code == 401:
            results["klap"] = "❌ Invalid API key"
            return False
        else:
            results["klap"] = f"⚠️ Status {response.status_code}"
            return True

    except Exception as e:
        results["klap"] = f"❌ Error: {str(e)}"
        return False


def test_gemini():
    """Test Google Gemini API connection"""
    print("\n🔍 Testing Gemini...")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        results["gemini"] = "❌ GEMINI_API_KEY not set"
        return False

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')

        # Quick test
        response = model.generate_content("Say 'API Connected' in 2 words")

        if response.text:
            results["gemini"] = "✅ Connected"
            return True
        else:
            results["gemini"] = "❌ No response"
            return False

    except Exception as e:
        results["gemini"] = f"❌ Error: {str(e)}"
        return False


def test_phantombuster():
    """Test PhantomBuster API connection"""
    print("\n🔍 Testing PhantomBuster...")

    api_key = os.getenv("PHANTOMBUSTER_API_KEY")
    if not api_key:
        results["phantombuster"] = "❌ PHANTOMBUSTER_API_KEY not set"
        return False

    try:
        import requests
        response = requests.get(
            "https://api.phantombuster.com/api/v2/user",
            headers={"X-Phantombuster-Key": api_key}
        )

        if response.status_code == 200:
            user = response.json()
            results["phantombuster"] = f"✅ Connected as {user.get('email', 'unknown')}"
            return True
        else:
            results["phantombuster"] = f"❌ Error {response.status_code}"
            return False

    except Exception as e:
        results["phantombuster"] = f"❌ Error: {str(e)}"
        return False


def test_ayrshare():
    """Test Ayrshare API connection"""
    print("\n🔍 Testing Ayrshare...")

    api_key = os.getenv("AYRSHARE_API_KEY")
    if not api_key:
        results["ayrshare"] = "❌ AYRSHARE_API_KEY not set"
        return False

    try:
        import requests
        response = requests.get(
            "https://app.ayrshare.com/api/user",
            headers={"Authorization": f"Bearer {api_key}"}
        )

        if response.status_code == 200:
            results["ayrshare"] = "✅ Connected"
            return True
        else:
            results["ayrshare"] = f"❌ Error {response.status_code}"
            return False

    except Exception as e:
        results["ayrshare"] = f"❌ Error: {str(e)}"
        return False


def test_database():
    """Test PostgreSQL database connection"""
    print("\n🔍 Testing Database...")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        results["database"] = "❌ DATABASE_URL not set"
        return False

    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(database_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            results["database"] = "✅ Connected"
            return True

    except Exception as e:
        results["database"] = f"❌ Error: {str(e)}"
        return False


def print_summary():
    """Print test results summary"""
    print("\n" + "="*60)
    print("📊 INTEGRATION TEST RESULTS")
    print("="*60)

    for integration, status in results.items():
        print(f"\n{integration.upper()}: {status}")

    print("\n" + "="*60)

    # Count results
    passed = sum(1 for s in results.values() if s.startswith("✅"))
    warnings = sum(1 for s in results.values() if s.startswith("⚠️"))
    failed = sum(1 for s in results.values() if s.startswith("❌"))

    print(f"\n✅ Passed: {passed}")
    print(f"⚠️ Warnings: {warnings}")
    print(f"❌ Failed: {failed}")
    print(f"\nTotal: {len(results)}")


def main():
    """Run all integration tests"""
    print("🚀 Starting Integration Tests...")
    print("="*60)

    # Run all tests
    test_instantly()
    test_apify()
    test_google_sheets()
    test_klap()
    test_gemini()
    test_phantombuster()
    test_ayrshare()
    test_database()

    # Print summary
    print_summary()

    # Return exit code based on critical failures
    critical_integrations = ["instantly", "database"]
    for integration in critical_integrations:
        if integration in results and results[integration].startswith("❌"):
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### 2. Atualizar implementation files com error handling

Revisar e garantir que cada arquivo em `implementation/` tem:
- Carregamento de variáveis de ambiente
- Try/except blocks
- Logging adequado
- Documentação de uso

### 3. Criar integration_status.json

Após rodar os testes, gerar:

```json
{
  "last_tested": "2024-12-27T00:00:00Z",
  "results": {
    "instantly": {
      "status": "connected",
      "details": "5 campaigns found",
      "required_env": ["INSTANTLY_API_KEY"]
    },
    "apify": {
      "status": "connected",
      "details": "Connected as user",
      "required_env": ["APIFY_API_KEY"]
    },
    "google_sheets": {
      "status": "connected",
      "details": "Spreadsheet accessible",
      "required_env": ["GOOGLE_SERVICE_ACCOUNT_FILE", "GOOGLE_SHEETS_SPREADSHEET_ID"]
    },
    "klap": {
      "status": "not_configured",
      "details": "API key not set",
      "required_env": ["KLAP_API_KEY"]
    },
    "gemini": {
      "status": "connected",
      "details": "API responding",
      "required_env": ["GEMINI_API_KEY"]
    },
    "phantombuster": {
      "status": "not_configured",
      "details": "API key not set",
      "required_env": ["PHANTOMBUSTER_API_KEY", "PHANTOMBUSTER_AGENT_ID"]
    },
    "ayrshare": {
      "status": "not_configured",
      "details": "API key not set",
      "required_env": ["AYRSHARE_API_KEY"]
    },
    "database": {
      "status": "connected",
      "details": "PostgreSQL accessible",
      "required_env": ["DATABASE_URL"]
    }
  }
}
```

### 4. Criar docs/INTEGRATIONS.md

```markdown
# AgenticOS Integrations Guide

## Quick Status

Run `python tests/test_all_integrations.py` to check all integrations.

---

## Instantly.ai

**Purpose:** Email marketing automation

**Required Environment Variables:**
- `INSTANTLY_API_KEY`

**How to get API key:**
1. Go to https://app.instantly.ai/
2. Navigate to Settings → Integrations → API
3. Copy your API key

**Available Scripts:**
- `implementation/instantly_analytics.py` - Daily email analytics
- `implementation/instantly_campaign_analytics.py` - Campaign performance
- `implementation/instantly_push.py` - Push leads to campaigns
- `implementation/instantly_create_campaign.py` - Create new campaigns

---

## Apify

**Purpose:** Web scraping automation

**Required Environment Variables:**
- `APIFY_API_KEY`

**How to get API key:**
1. Go to https://console.apify.com/
2. Navigate to Settings → Integrations
3. Copy your API token

**Available Scripts:**
- `implementation/apify_leads_sheet.py` - Lead generation workflow

---

## Google Sheets

**Purpose:** Data storage and management

**Required Files:**
- `service_account.json` - Google service account credentials

**Required Environment Variables:**
- `GOOGLE_SERVICE_ACCOUNT_FILE` (default: service_account.json)
- `GOOGLE_SHEETS_SPREADSHEET_ID`

**Setup Steps:**
1. Go to Google Cloud Console
2. Create a new project
3. Enable Google Sheets API and Google Drive API
4. Create a service account
5. Download JSON key as `service_account.json`
6. Share your spreadsheet with the service account email

---

## Klap

**Purpose:** Video processing and shorts generation

**Required Environment Variables:**
- `KLAP_API_KEY`

**Available Scripts:**
- `implementation/klap_generate_shorts.py` - Basic shorts generation
- `implementation/klap_generate_shorts_enhanced.py` - Advanced workflow

---

## Gemini

**Purpose:** AI content generation

**Required Environment Variables:**
- `GEMINI_API_KEY`

**How to get API key:**
1. Go to https://makersuite.google.com/app/apikey
2. Create a new API key

**Available Scripts:**
- `implementation/gemini_viral_shorts_post.py` - Viral content generation

---

## PhantomBuster

**Purpose:** LinkedIn automation

**Required Environment Variables:**
- `PHANTOMBUSTER_API_KEY`
- `PHANTOMBUSTER_AGENT_ID`

**Available Scripts:**
- `implementation/linkedin_connection_agent.py` - Connection tracking

---

## Ayrshare

**Purpose:** Social media publishing

**Required Environment Variables:**
- `AYRSHARE_API_KEY`

**Available Scripts:**
- `implementation/ayrshare_daily_analytics.py` - Social analytics

---

## Database (PostgreSQL)

**Purpose:** Data persistence

**Required Environment Variables:**
- `DATABASE_URL` (format: postgresql://user:pass@host:port/dbname)

**Schema:**
- See `database/schema.sql` for table definitions
```

---

## VALIDAÇÃO

```bash
# Rodar testes de integração
python tests/test_all_integrations.py

# Verificar arquivos criados
ls -la tests/test_all_integrations.py
ls -la docs/INTEGRATIONS.md
```

---

## OUTPUT ESPERADO

```
STATUS: SUCCESS / FAILURE

ARQUIVOS CRIADOS:
- tests/test_all_integrations.py: OK
- docs/INTEGRATIONS.md: OK

INTEGRAÇÕES TESTADAS:
- Instantly.ai: [status]
- Apify: [status]
- Google Sheets: [status]
- Klap: [status]
- Gemini: [status]
- PhantomBuster: [status]
- Ayrshare: [status]
- Database: [status]

TOTAL: X/8 conectados
```
