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

# Leads de demonstração - profissionais de saúde (exemplo)
# Estrutura conforme tabela agentic_instagram_leads
demo_leads = [
    {
        "username": "dr.exemplo1",
        "full_name": "Dr. João Silva",
        "bio": "Médico | Especialista em Cardiologia | Consultório em SP",
        "followers_count": 5420,
        "following_count": 890,
        "is_private": False,
        "is_verified": False,
        "profile_url": "https://instagram.com/dr.exemplo1",
        "source": "demo",
        "tags": ["médico", "cardiologia", "saúde"]
    },
    {
        "username": "dra.exemplo2",
        "full_name": "Dra. Maria Santos",
        "bio": "Dermatologista | Estética | Clínica própria | RJ",
        "followers_count": 12300,
        "following_count": 456,
        "is_private": False,
        "is_verified": True,
        "profile_url": "https://instagram.com/dra.exemplo2",
        "source": "demo",
        "tags": ["médica", "dermatologia", "estética"]
    },
    {
        "username": "fisio.exemplo3",
        "full_name": "Carlos Oliveira",
        "bio": "Fisioterapeuta | Pilates | Reabilitação | Atendimento domiciliar",
        "followers_count": 3200,
        "following_count": 1200,
        "is_private": False,
        "is_verified": False,
        "profile_url": "https://instagram.com/fisio.exemplo3",
        "source": "demo",
        "tags": ["fisioterapia", "pilates", "saúde"]
    },
    {
        "username": "nutri.exemplo4",
        "full_name": "Ana Paula Costa",
        "bio": "Nutricionista | Emagrecimento | Reeducação alimentar | Online",
        "followers_count": 8900,
        "following_count": 670,
        "is_private": False,
        "is_verified": False,
        "profile_url": "https://instagram.com/nutri.exemplo4",
        "source": "demo",
        "tags": ["nutrição", "emagrecimento", "saúde"]
    },
    {
        "username": "psicologo.exemplo5",
        "full_name": "Dr. Pedro Mendes",
        "bio": "Psicólogo Clínico | Terapia Cognitiva | Atendimento online",
        "followers_count": 6700,
        "following_count": 340,
        "is_private": False,
        "is_verified": False,
        "profile_url": "https://instagram.com/psicologo.exemplo5",
        "source": "demo",
        "tags": ["psicologia", "terapia", "saúde mental"]
    }
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
