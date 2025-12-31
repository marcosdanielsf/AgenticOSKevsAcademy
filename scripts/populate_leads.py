#!/usr/bin/env python3
"""
Populate Leads Script
=====================
Insere leads de demonstração na tabela agentic_instagram_leads
"""

import os
import requests
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

# Leads de teste - usernames reais
demo_leads = [
    {"username": "mottivme", "full_name": "Mottiv Me", "source": "test"},
    {"username": "socialfyselling", "full_name": "Socialfy Selling", "source": "test"},
    {"username": "hallennaiane", "full_name": "Hallen Naiane", "source": "test"},
    {"username": "eusoumarcos", "full_name": "Marcos", "source": "test"},
    {"username": "andrerosafc", "full_name": "Andre Rosa", "source": "test"},
    {"username": "gladinjr", "full_name": "Gladin Jr", "source": "test"},
]


def create_table_if_not_exists():
    """Cria a tabela se não existir"""
    # A tabela deve ser criada via SQL no Supabase Dashboard
    # Este script apenas verifica se a conexão funciona
    url = f"{SUPABASE_URL}/rest/v1/agentic_instagram_leads?select=count"
    response = requests.get(url, headers=headers)
    return response.status_code in [200, 406]  # 406 = tabela vazia mas existe


def insert_leads():
    """Insere os leads de demonstração"""
    url = f"{SUPABASE_URL}/rest/v1/agentic_instagram_leads"

    inserted = 0
    for lead in demo_leads:
        # Verifica se já existe
        check_url = f"{url}?username=eq.{lead['username']}"
        check = requests.get(check_url, headers=headers)

        if check.status_code == 200 and len(check.json()) > 0:
            print(f"⏭️  Lead @{lead['username']} já existe, pulando...")
            continue

        # Insere o lead
        response = requests.post(url, headers=headers, json=lead)

        if response.status_code in [200, 201]:
            print(f"✅ Lead @{lead['username']} inserido com sucesso!")
            inserted += 1
        else:
            print(f"❌ Erro ao inserir @{lead['username']}: {response.text}")

    return inserted


def main():
    print("=" * 50)
    print("🚀 Populando Leads de Demonstração")
    print("=" * 50)

    # Testa conexão
    print("\n📡 Testando conexão com Supabase...")
    if not create_table_if_not_exists():
        print("❌ Erro: Não foi possível conectar ao Supabase")
        print("   Verifique se a tabela 'agentic_instagram_leads' existe")
        return

    print("✅ Conexão OK!")

    # Insere leads
    print(f"\n📝 Inserindo {len(demo_leads)} leads de demonstração...")
    inserted = insert_leads()

    print("\n" + "=" * 50)
    print(f"✅ Concluído! {inserted} leads inseridos.")
    print("=" * 50)

    # Lista leads na tabela
    print("\n📋 Leads na tabela:")
    url = f"{SUPABASE_URL}/rest/v1/agentic_instagram_leads?select=username,full_name,status,priority&order=priority.asc"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        leads = response.json()
        for lead in leads:
            print(f"   • @{lead['username']} - {lead['full_name']} [{lead['status']}]")
        print(f"\n   Total: {len(leads)} leads")


if __name__ == "__main__":
    main()
