#!/usr/bin/env python3
"""
Run Supabase migrations for multi-tenant support.

Usage:
    python database/run_migration.py

Or execute the SQL directly in Supabase SQL Editor.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

def run_migration():
    """
    Executa as migrations de multi-tenant.

    Como o Supabase REST API não executa SQL diretamente,
    este script mostra as instruções para executar manualmente.
    """

    migrations_dir = Path(__file__).parent / "migrations"

    print("=" * 60)
    print("  AGENTICOSKEVSACADEMY - MULTI-TENANT MIGRATION")
    print("=" * 60)
    print()

    # Check connection
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY devem estar configurados")
        print("   Configure no arquivo .env ou como variáveis de ambiente")
        return False

    print(f"📍 Supabase URL: {SUPABASE_URL}")
    print()

    # Test connection
    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        }
        r = requests.get(f"{SUPABASE_URL}/rest/v1/", headers=headers, timeout=10)
        if r.status_code == 200:
            print("✅ Conexão com Supabase OK")
        else:
            print(f"⚠️  Status: {r.status_code}")
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")
        return False

    print()
    print("=" * 60)
    print("📋 EXECUTE O SQL ABAIXO NO SUPABASE SQL EDITOR:")
    print("   https://supabase.com/dashboard/project/_/sql/new")
    print("=" * 60)
    print()

    # Read and print migration SQL
    migration_file = migrations_dir / "001_instagram_accounts_multitenant.sql"
    if migration_file.exists():
        sql_content = migration_file.read_text()
        print(sql_content)
    else:
        print("❌ Migration file not found!")
        print(f"   Expected at: {migration_file}")
        return False

    print()
    print("=" * 60)
    print("✅ Após executar o SQL, a tabela instagram_accounts estará pronta!")
    print()
    print("📝 Próximos passos:")
    print("   1. Execute o SQL acima no Supabase SQL Editor")
    print("   2. Adicione suas contas Instagram via API:")
    print()
    print("   curl -X POST 'https://your-api/api/accounts' \\")
    print("     -H 'Content-Type: application/json' \\")
    print("     -d '{")
    print('       "tenant_id": "mottivme",')
    print('       "username": "marcosdanielsf",')
    print('       "session_id": "seu_session_id",')
    print('       "daily_limit": 100,')
    print('       "hourly_limit": 15')
    print("     }'")
    print()
    print("=" * 60)

    return True


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
