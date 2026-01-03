#!/usr/bin/env python3
"""
Run Migration directly on Supabase PostgreSQL
==============================================
Executa a migração diretamente no PostgreSQL do Supabase.

Uso:
    python run_migration.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Carregar variáveis de ambiente do projeto
project_root = Path(__file__).parent.parent
load_dotenv(project_root / '.env')

try:
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
except ImportError:
    print("[ERRO] psycopg2 não instalado. Instalando...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


def get_db_connection_string():
    """Constrói a connection string do PostgreSQL do Supabase"""
    supabase_url = os.getenv('SUPABASE_URL', '')

    # Extrair o project ref da URL
    # https://bfumywvwubvernvhjehk.supabase.co -> bfumywvwubvernvhjehk
    project_ref = supabase_url.replace('https://', '').split('.')[0]

    # Conexão direta ao PostgreSQL do Supabase
    # Formato: postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres
    db_password = os.getenv('SUPABASE_DB_PASSWORD')

    if not db_password:
        print("[INFO] SUPABASE_DB_PASSWORD não encontrada.")
        print("       Usando método alternativo via Management API...")
        return None

    return f"postgresql://postgres:{db_password}@db.{project_ref}.supabase.co:5432/postgres"


def run_migration_via_api():
    """Executa a migração via Supabase Management API"""
    import requests

    supabase_url = os.getenv('SUPABASE_URL')
    service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

    # Ler o arquivo de migração
    migration_path = Path(__file__).parent / 'migrations' / '001_fase0_integration_tables.sql'
    with open(migration_path, 'r') as f:
        sql_content = f.read()

    # Dividir em statements individuais (simples, não trata strings com ;)
    statements = []
    current = []

    for line in sql_content.split('\n'):
        line_stripped = line.strip()

        # Pular comentários e linhas vazias
        if not line_stripped or line_stripped.startswith('--'):
            continue

        current.append(line)

        # Detectar fim de statement
        if line_stripped.endswith(';'):
            stmt = '\n'.join(current).strip()
            if stmt and not stmt.startswith('--'):
                statements.append(stmt)
            current = []

    print(f"\n[INFO] Encontrados {len(statements)} statements SQL")

    # Agrupar statements por tipo
    # Alguns podem ser executados via REST API criando funções RPC
    # Mas a melhor opção é usar o Dashboard

    print("\n" + "=" * 60)
    print("OPÇÕES PARA APLICAR A MIGRAÇÃO:")
    print("=" * 60)

    print("""
1. VIA SUPABASE DASHBOARD (RECOMENDADO):
   a) Acesse: https://supabase.com/dashboard/project/bfumywvwubvernvhjehk
   b) Vá em "SQL Editor" no menu lateral
   c) Clique em "New query"
   d) Cole o conteúdo do arquivo:
      supabase/migrations/001_fase0_integration_tables.sql
   e) Clique em "Run" (ou Ctrl+Enter)

2. VIA CONEXÃO DIRETA (se tiver a senha do DB):
   a) Adicione SUPABASE_DB_PASSWORD no .env
   b) Execute: python supabase/run_migration.py

3. VIA SUPABASE CLI (requer Docker):
   a) Inicie o Docker
   b) Execute: supabase db push
""")

    print("=" * 60)

    # Mostrar preview do SQL
    print("\n[PREVIEW] Primeiros statements:")
    for i, stmt in enumerate(statements[:5], 1):
        preview = stmt[:100].replace('\n', ' ')
        print(f"  {i}. {preview}...")

    return {
        'total_statements': len(statements),
        'method': 'manual',
        'note': 'Use o Supabase Dashboard para aplicar'
    }


def run_migration_via_psycopg2(connection_string: str):
    """Executa a migração diretamente via psycopg2"""
    migration_path = Path(__file__).parent / 'migrations' / '001_fase0_integration_tables.sql'

    with open(migration_path, 'r') as f:
        sql_content = f.read()

    print(f"\n[INFO] Conectando ao banco de dados...")

    try:
        conn = psycopg2.connect(connection_string)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        print("[INFO] Conexão estabelecida. Executando migração...")

        # Executar todo o SQL de uma vez (melhor para transações)
        cursor.execute(sql_content)

        print("[OK] Migração executada com sucesso!")

        # Verificar tabelas criadas
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('integration_sync_log', 'enriched_lead_data', 'lead_handoff_queue')
        """)

        tables = cursor.fetchall()
        print(f"\n[INFO] Tabelas criadas: {[t[0] for t in tables]}")

        cursor.close()
        conn.close()

        return {'success': True, 'tables_created': [t[0] for t in tables]}

    except Exception as e:
        print(f"[ERRO] Falha na migração: {e}")
        return {'success': False, 'error': str(e)}


def main():
    print("=" * 60)
    print("FASE 0 - Execução de Migração SQL")
    print("=" * 60)

    connection_string = get_db_connection_string()

    if connection_string:
        result = run_migration_via_psycopg2(connection_string)
    else:
        result = run_migration_via_api()

    return result


if __name__ == '__main__':
    main()
