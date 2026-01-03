#!/usr/bin/env python3
"""
Apply SQL Migration to Supabase
===============================
Aplica migrações SQL ao Supabase via REST API.

Uso:
    python apply_migration.py
    python apply_migration.py --file 001_fase0_integration_tables.sql
"""

import os
import sys
import requests
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Carregar variáveis de ambiente do projeto
project_root = Path(__file__).parent.parent
load_dotenv(project_root / '.env')


def apply_sql_migration(sql_content: str, supabase_url: str, service_key: str) -> dict:
    """
    Aplica SQL diretamente no Supabase.

    Nota: Supabase não permite SQL arbitrário via REST API.
    Para migrações, precisamos usar a Supabase CLI ou Dashboard.
    Este script divide o SQL em statements e tenta aplicar via RPC.
    """

    headers = {
        'apikey': service_key,
        'Authorization': f'Bearer {service_key}',
        'Content-Type': 'application/json',
    }

    # Tentar verificar se as tabelas já existem
    print("\n[INFO] Verificando tabelas existentes...")

    tables_to_check = [
        'integration_sync_log',
        'enriched_lead_data',
        'lead_handoff_queue'
    ]

    existing_tables = []
    for table in tables_to_check:
        try:
            response = requests.get(
                f"{supabase_url}/rest/v1/{table}",
                headers=headers,
                params={'limit': 0}
            )
            if response.status_code == 200:
                existing_tables.append(table)
                print(f"  [OK] Tabela {table} já existe")
            else:
                print(f"  [--] Tabela {table} não existe (será criada)")
        except Exception as e:
            print(f"  [!] Erro verificando {table}: {e}")

    return {
        'existing_tables': existing_tables,
        'tables_to_create': [t for t in tables_to_check if t not in existing_tables],
        'note': 'Para aplicar migrações completas, use Supabase Dashboard ou CLI'
    }


def check_socialfy_leads_columns(supabase_url: str, service_key: str) -> dict:
    """Verifica se as colunas necessárias existem em socialfy_leads"""

    headers = {
        'apikey': service_key,
        'Authorization': f'Bearer {service_key}',
        'Content-Type': 'application/json',
    }

    print("\n[INFO] Verificando colunas em socialfy_leads...")

    required_columns = [
        'ghl_contact_id',
        'location_id',
        'icp_tier',
        'outreach_sent_at',
        'last_outreach_message'
    ]

    try:
        # Buscar um registro para ver as colunas
        response = requests.get(
            f"{supabase_url}/rest/v1/socialfy_leads",
            headers=headers,
            params={'limit': 1, 'select': '*'}
        )

        if response.status_code == 200:
            data = response.json()
            if data and isinstance(data, list) and len(data) > 0:
                existing_cols = set(data[0].keys())
                missing = [c for c in required_columns if c not in existing_cols]

                if missing:
                    print(f"  [!] Colunas faltando: {missing}")
                else:
                    print("  [OK] Todas as colunas necessárias existem")

                return {
                    'table_exists': True,
                    'missing_columns': missing,
                    'existing_columns': list(existing_cols)
                }
            else:
                print("  [--] Tabela vazia, verificando estrutura...")
                return {
                    'table_exists': True,
                    'missing_columns': 'unknown',
                    'note': 'Tabela vazia'
                }
        else:
            print(f"  [!] Tabela não existe ou erro: {response.status_code}")
            return {'table_exists': False}

    except Exception as e:
        print(f"  [!] Erro: {e}")
        return {'error': str(e)}


def main():
    parser = argparse.ArgumentParser(description='Apply SQL migration to Supabase')
    parser.add_argument('--file', type=str, default='migrations/001_fase0_integration_tables.sql',
                       help='Migration file path (relative to supabase/)')
    args = parser.parse_args()

    # Carregar configurações
    supabase_url = os.getenv('SUPABASE_URL')
    service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

    if not supabase_url or not service_key:
        print("[ERRO] Variáveis SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY são obrigatórias")
        print("       Configure no arquivo .env")
        sys.exit(1)

    print("=" * 60)
    print("FASE 0 - Verificação de Migração")
    print("=" * 60)
    print(f"Supabase URL: {supabase_url}")

    # Carregar arquivo SQL
    migration_path = Path(__file__).parent / args.file
    if not migration_path.exists():
        print(f"[ERRO] Arquivo não encontrado: {migration_path}")
        sys.exit(1)

    with open(migration_path, 'r') as f:
        sql_content = f.read()

    print(f"Migration file: {migration_path.name}")
    print(f"SQL size: {len(sql_content)} bytes")

    # Verificar estado atual
    result = apply_sql_migration(sql_content, supabase_url, service_key)

    # Verificar socialfy_leads
    leads_check = check_socialfy_leads_columns(supabase_url, service_key)

    print("\n" + "=" * 60)
    print("RESULTADO DA VERIFICAÇÃO")
    print("=" * 60)

    if result.get('tables_to_create'):
        print(f"\n[!] TABELAS PRECISAM SER CRIADAS:")
        for t in result['tables_to_create']:
            print(f"    - {t}")
        print(f"\n    AÇÃO NECESSÁRIA:")
        print(f"    1. Acesse o Supabase Dashboard")
        print(f"    2. Vá em SQL Editor")
        print(f"    3. Cole o conteúdo de: {migration_path}")
        print(f"    4. Execute o SQL")
    else:
        print("\n[OK] Todas as tabelas de integração existem!")

    if leads_check.get('missing_columns') and leads_check['missing_columns'] != 'unknown':
        print(f"\n[!] COLUNAS PRECISAM SER ADICIONADAS em socialfy_leads:")
        for c in leads_check['missing_columns']:
            print(f"    - {c}")

    print("\n" + "=" * 60)

    # Gerar comando para aplicar via CLI (se disponível)
    print("\nALTERNATIVA - Via Supabase CLI:")
    print("  supabase db push --db-url postgresql://...")
    print("  supabase migration up")

    return result


if __name__ == '__main__':
    main()
