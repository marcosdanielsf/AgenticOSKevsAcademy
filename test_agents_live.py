#!/usr/bin/env python3
"""
🧪 TESTE PRÁTICO DOS AGENTES
============================
Execute este script no seu Mac para testar os agentes com dados reais.

Uso:
    python3 test_agents_live.py
"""

import os
import sys
import json
from datetime import datetime

# Adicionar path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from implementation.supabase_integration import SupabaseClient, SocialfyAgentIntegration


def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def test_supabase_connection():
    """Teste 1: Conexão com Supabase"""
    print_header("TESTE 1: Conexão com Supabase")

    try:
        client = SupabaseClient()
        print(f"✅ Conectado: {client.url}")
        return client
    except Exception as e:
        print(f"❌ Falha na conexão: {e}")
        return None


def test_fetch_leads(client):
    """Teste 2: Buscar leads existentes"""
    print_header("TESTE 2: Buscar Leads do Banco")

    result = client._request('GET', 'crm_leads', params={
        'limit': 10,
        'order': 'created_at.desc'
    })

    if isinstance(result, list):
        print(f"✅ {len(result)} leads encontrados:\n")
        for i, lead in enumerate(result, 1):
            name = lead.get('name', 'N/A')
            email = lead.get('email', 'N/A')
            company = lead.get('company', '')
            status = lead.get('status', 'N/A')
            source = lead.get('source_channel', 'N/A')
            score = lead.get('score', '-')

            print(f"  {i}. {name}")
            print(f"     Email: {email}")
            print(f"     Empresa: {company} | Status: {status} | Score: {score}")
            print()
        return result
    else:
        print(f"❌ Erro ao buscar leads: {result}")
        return []


def test_fetch_messages(client):
    """Teste 3: Buscar mensagens"""
    print_header("TESTE 3: Buscar Mensagens Recentes")

    result = client._request('GET', 'socialfy_messages', params={
        'limit': 5,
        'order': 'created_at.desc'
    })

    if isinstance(result, list):
        print(f"✅ {len(result)} mensagens encontradas:\n")
        for msg in result:
            direction = "📤" if msg.get('direction') == 'outbound' else "📥"
            status = msg.get('status', 'N/A')
            content = (msg.get('content') or '')[:50]
            print(f"  {direction} [{status}] {content}...")
        return result
    else:
        print(f"❌ Erro ou tabela vazia: {result}")
        return []


def test_fetch_analytics(client):
    """Teste 4: Analytics diárias"""
    print_header("TESTE 4: Analytics Diárias")

    result = client._request('GET', 'socialfy_analytics_daily', params={
        'limit': 7,
        'order': 'date.desc'
    })

    if isinstance(result, list) and result:
        print(f"✅ {len(result)} dias de analytics:\n")
        for day in result:
            date = day.get('date', 'N/A')
            leads = day.get('leads_discovered', 0)
            dms = day.get('dms_sent', 0)
            replies = day.get('replies_received', 0)
            print(f"  📅 {date}: {leads} leads | {dms} DMs | {replies} respostas")
        return result
    else:
        print(f"⚠️ Sem dados de analytics ainda (normal se novo)")
        return []


def test_lead_qualifier():
    """Teste 5: Testar o LeadQualifier com dados reais"""
    print_header("TESTE 5: LeadQualifier Agent")

    # Simular profile data
    test_profile = {
        "username": "teste_user",
        "full_name": "João Empreendedor",
        "bio": "CEO | Fundador da StartupXYZ | Mentor de negócios digitais | +10 anos em marketing",
        "followers_count": 15000,
        "following_count": 500,
        "posts_count": 150,
        "is_verified": False,
        "is_private": False,
        "category": "Entrepreneur"
    }

    print("📋 Profile de teste:")
    print(f"   @{test_profile['username']}")
    print(f"   Bio: {test_profile['bio'][:60]}...")
    print(f"   Seguidores: {test_profile['followers_count']}")
    print(f"   Categoria: {test_profile['category']}")
    print()

    try:
        from implementation.agents.outbound_squad import LeadQualifierAgent
        import asyncio

        qualifier = LeadQualifierAgent()

        # Rodar qualificação
        async def run_qualification():
            await qualifier.initialize()
            from implementation.agents.base_agent import Task

            task = Task(
                task_type="qualify_lead",
                payload={
                    "username": test_profile["username"],
                    "profile": test_profile
                }
            )

            result = await qualifier.execute_task(task)
            return result

        result = asyncio.run(run_qualification())

        print("🎯 Resultado da Qualificação:")
        print(f"   Score: {result.get('score', 0)}/100")
        print(f"   Classificação: {result.get('classification', 'N/A')}")
        print(f"   Prioridade: {result.get('priority', 'N/A')}")
        print(f"   Sinais detectados:")
        for signal in result.get('signals', []):
            print(f"      - {signal}")

        return result

    except Exception as e:
        print(f"❌ Erro no LeadQualifier: {e}")
        return None


def test_message_composer():
    """Teste 6: Testar o MessageComposer"""
    print_header("TESTE 6: MessageComposer Agent")

    test_profile = {
        "username": "joao_startup",
        "full_name": "João Silva",
        "bio": "Fundador da TechBR | Ajudo empresas a escalar com tecnologia",
        "category": "Entrepreneur"
    }

    test_qualification = {
        "classification": "LEAD_HOT",
        "score": 85
    }

    print(f"📋 Compondo mensagem para @{test_profile['username']}...")
    print(f"   Classificação: {test_qualification['classification']}")
    print()

    try:
        from implementation.agents.outbound_squad import MessageComposerAgent
        import asyncio

        composer = MessageComposerAgent()

        async def run_composition():
            await composer.initialize()
            from implementation.agents.base_agent import Task

            task = Task(
                task_type="compose_message",
                payload={
                    "username": test_profile["username"],
                    "profile": test_profile,
                    "qualification": test_qualification
                }
            )

            result = await composer.execute_task(task)
            return result

        result = asyncio.run(run_composition())

        print("💬 Mensagem Gerada:")
        print(f"   \"{result.get('message', 'N/A')}\"")
        print(f"\n   Template: {result.get('template_used', 'N/A')}")

        return result

    except Exception as e:
        print(f"❌ Erro no MessageComposer: {e}")
        return None


def test_integration_save():
    """Teste 7: Salvar dados via Integration"""
    print_header("TESTE 7: Integration Layer (Salvar Lead)")

    try:
        integration = SocialfyAgentIntegration()

        # Criar lead de teste com campos corretos
        timestamp = datetime.now().strftime("%H%M%S")
        test_name = f"Teste API {timestamp}"
        test_email = f"teste_{timestamp}@test.com"

        print(f"📝 Salvando lead de teste...")
        print(f"   Nome: {test_name}")
        print(f"   Email: {test_email}")

        result = integration.save_discovered_lead(
            name=test_name,
            email=test_email,
            source="test_script",
            profile_data={
                "company": "Empresa Teste",
                "phone": "+5511999999999",
                "status": "hot",  # Using existing lead's status
                "score": 50
            }
        )

        if isinstance(result, list) and result:
            print(f"✅ Lead salvo com sucesso!")
            print(f"   ID: {result[0].get('id', 'N/A')}")
        elif 'error' not in result:
            print(f"✅ Lead salvo: {result}")
        else:
            print(f"⚠️ Resposta: {result}")

        return result

    except Exception as e:
        print(f"❌ Erro: {e}")
        return None


def main():
    print("\n" + "🚀"*30)
    print("\n   SOCIALFY - TESTE PRÁTICO DOS AGENTES")
    print("\n" + "🚀"*30)

    # Teste 1: Conexão
    client = test_supabase_connection()
    if not client:
        print("\n❌ Não foi possível conectar ao Supabase. Verifique .env")
        return

    # Teste 2: Leads
    leads = test_fetch_leads(client)

    # Teste 3: Mensagens
    messages = test_fetch_messages(client)

    # Teste 4: Analytics
    analytics = test_fetch_analytics(client)

    # Teste 5: LeadQualifier
    qualification = test_lead_qualifier()

    # Teste 6: MessageComposer
    composed = test_message_composer()

    # Teste 7: Salvar lead
    saved = test_integration_save()

    # Resumo
    print_header("📊 RESUMO DOS TESTES")

    print(f"  ✅ Conexão Supabase: OK")
    print(f"  📋 Leads no banco: {len(leads)}")
    print(f"  💬 Mensagens: {len(messages)}")
    print(f"  📈 Dias de analytics: {len(analytics)}")
    print(f"  🎯 LeadQualifier: {'OK' if qualification else 'FALHOU'}")
    print(f"  ✍️ MessageComposer: {'OK' if composed else 'FALHOU'}")
    print(f"  💾 Integration Save: {'OK' if saved else 'FALHOU'}")

    print("\n" + "="*60)
    print("  Testes concluídos! Execute no seu Mac para ver os dados reais.")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()
