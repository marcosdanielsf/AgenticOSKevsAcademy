#!/usr/bin/env python3
"""
Apply Growth OS migrations to Supabase
Executes:
1. 007_growth_os_tables.sql - Creates all Growth OS tables
2. clients/dr_luiz_config.sql - Configures first client (Dr. Luiz)
"""

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import requests
from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("❌ Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env")
    sys.exit(1)


def execute_sql(sql: str, description: str) -> bool:
    """Execute SQL via Supabase REST API using rpc"""

    # Supabase doesn't have a direct SQL execution endpoint via REST
    # We need to use the SQL Editor in the dashboard or use psql
    # For now, we'll print instructions

    print(f"\n{'='*60}")
    print(f"📋 {description}")
    print(f"{'='*60}")
    print("\n⚠️  Supabase REST API doesn't support direct SQL execution.")
    print("    Please execute the SQL manually via one of these methods:\n")
    print("    1. Supabase SQL Editor:")
    print(f"       https://supabase.com/dashboard/project/{SUPABASE_URL.split('//')[1].split('.')[0]}/sql/new")
    print("\n    2. Or use psql with your database connection string")
    print("="*60)

    return True


def check_tables_exist() -> dict:
    """Check which Growth OS tables already exist"""

    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    }

    tables_to_check = [
        "growth_leads",
        "growth_agent_templates",
        "growth_segment_strategies",
        "growth_client_configs",
        "growth_client_agents",
        "growth_activities",
        "growth_funnel_daily",
        "growth_agent_metrics",
        "growth_global_metrics",
        "growth_conversation_logs",
        "growth_test_personas",
        "growth_test_cases",
        "growth_test_runs"
    ]

    results = {}

    for table in tables_to_check:
        url = f"{SUPABASE_URL}/rest/v1/{table}?select=count&limit=0"
        try:
            response = requests.head(url, headers=headers)
            results[table] = response.status_code == 200
        except:
            results[table] = False

    return results


def main():
    print("\n" + "="*60)
    print("🚀 GROWTH OS - MIGRATION SCRIPT")
    print("="*60)
    print(f"\n📍 Supabase URL: {SUPABASE_URL}")

    # Check existing tables
    print("\n📊 Checking existing tables...")
    table_status = check_tables_exist()

    existing = [t for t, exists in table_status.items() if exists]
    missing = [t for t, exists in table_status.items() if not exists]

    if existing:
        print(f"\n✅ Tables already exist ({len(existing)}):")
        for t in existing:
            print(f"   • {t}")

    if missing:
        print(f"\n❌ Tables missing ({len(missing)}):")
        for t in missing:
            print(f"   • {t}")

    # Migration files
    migrations_dir = PROJECT_ROOT / "database" / "migrations"
    clients_dir = PROJECT_ROOT / "clients"

    migration_file = migrations_dir / "007_growth_os_tables.sql"
    client_file = clients_dir / "dr_luiz_config.sql"

    print("\n" + "="*60)
    print("📁 MIGRATION FILES")
    print("="*60)

    # Step 1: Growth OS Tables
    if missing:
        print(f"\n1️⃣  STEP 1: Create Growth OS Tables")
        print(f"    File: {migration_file}")

        if migration_file.exists():
            sql_content = migration_file.read_text()
            print(f"    Size: {len(sql_content):,} characters")
            print(f"\n    👉 Copy and paste the SQL from this file into Supabase SQL Editor:")
            print(f"       {migration_file}")
        else:
            print(f"    ❌ File not found!")
    else:
        print(f"\n1️⃣  STEP 1: ✅ All Growth OS tables already exist!")

    # Step 2: Dr. Luiz Config
    print(f"\n2️⃣  STEP 2: Configure Dr. Luiz (First Client)")
    print(f"    File: {client_file}")

    if client_file.exists():
        sql_content = client_file.read_text()
        print(f"    Size: {len(sql_content):,} characters")
        print(f"\n    👉 After Step 1, run this SQL to configure Dr. Luiz:")
        print(f"       {client_file}")
    else:
        print(f"    ❌ File not found!")

    # Quick link
    project_ref = SUPABASE_URL.split("//")[1].split(".")[0]
    sql_editor_url = f"https://supabase.com/dashboard/project/{project_ref}/sql/new"

    print("\n" + "="*60)
    print("🔗 QUICK LINKS")
    print("="*60)
    print(f"\n   SQL Editor: {sql_editor_url}")
    print(f"\n   Table Editor: https://supabase.com/dashboard/project/{project_ref}/editor")

    print("\n" + "="*60)
    print("📝 INSTRUCTIONS")
    print("="*60)
    print("""
    1. Open the Supabase SQL Editor link above

    2. If tables are missing:
       - Copy the entire content of 007_growth_os_tables.sql
       - Paste into SQL Editor and click "Run"
       - Wait for all tables/views/functions to be created

    3. Configure Dr. Luiz:
       - Copy the entire content of dr_luiz_config.sql
       - Paste into SQL Editor and click "Run"
       - This creates the segment strategy, client config, and test personas

    4. Verify:
       - Check the Table Editor to see the new tables
       - Query growth_client_configs to see Dr. Luiz config
       - Query growth_test_personas to see the 3 test personas
    """)

    print("="*60)
    print("✨ Ready to apply migrations!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
