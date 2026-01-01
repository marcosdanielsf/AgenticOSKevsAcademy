#!/usr/bin/env python3
"""
Limpa leads antigos (samples) do Supabase
Mantém apenas os leads com source = 'test'
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}

def list_leads():
    """Lista todos os leads"""
    url = f"{SUPABASE_URL}/rest/v1/agentic_instagram_leads?select=id,username,source"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    return []

def delete_sample_leads():
    """Deleta leads com source diferente de 'test'"""
    # Deletar leads com source = 'sample'
    url = f"{SUPABASE_URL}/rest/v1/agentic_instagram_leads?source=eq.sample"
    response = requests.delete(url, headers=headers)
    print(f"Deleted sample leads: {response.status_code}")

    # Deletar leads com source = 'manual' (default do SQL)
    url = f"{SUPABASE_URL}/rest/v1/agentic_instagram_leads?source=eq.manual"
    response = requests.delete(url, headers=headers)
    print(f"Deleted manual leads: {response.status_code}")

def main():
    print("=" * 50)
    print("🧹 Limpando leads antigos")
    print("=" * 50)

    print("\n📋 Leads ANTES da limpeza:")
    leads = list_leads()
    for lead in leads:
        print(f"   • @{lead['username']} (source: {lead['source']})")
    print(f"   Total: {len(leads)}")

    print("\n🗑️  Deletando leads com source != 'test'...")
    delete_sample_leads()

    print("\n📋 Leads DEPOIS da limpeza:")
    leads = list_leads()
    for lead in leads:
        print(f"   • @{lead['username']} (source: {lead['source']})")
    print(f"   Total: {len(leads)}")

    print("\n✅ Limpeza concluída!")

if __name__ == "__main__":
    main()
