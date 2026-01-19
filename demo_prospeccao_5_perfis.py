#!/usr/bin/env python3
"""
Demo Prospecção - 5 Perfis
==========================
Script para demonstração do AgenticOS enviando DMs automatizados.
Modo visual (navegador aberto) para apresentação.

Uso:
    python demo_prospeccao_5_perfis.py
"""

import asyncio
import sys
import os

# Add implementation to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'implementation'))

from dotenv import load_dotenv
load_dotenv()

# Import the DM agent
from instagram_dm_agent import InstagramDMAgent, SupabaseDB, logger

async def demo_prospeccao():
    """Executa prospecção de 5 perfis para demonstração"""

    print("="*60)
    print("🎯 DEMO PROSPECÇÃO AGENTIC OS")
    print("="*60)
    print()

    # 1. Verificar leads disponíveis
    print("📋 Verificando leads disponíveis...")
    db = SupabaseDB()
    leads = db.get_leads_to_contact(limit=10)

    if not leads:
        print("❌ Nenhum lead disponível para prospecção!")
        print()
        print("Para adicionar leads, você pode:")
        print("1. Usar o scraper de comentários/curtidas de posts")
        print("2. Importar leads manualmente via Supabase")
        print()
        return

    print(f"✅ {len(leads)} leads disponíveis")
    print()
    print("📝 Primeiros 5 leads que serão prospectados:")
    print("-"*40)
    for i, lead in enumerate(leads[:5], 1):
        score_info = f"Score: {lead.icp_score}" if lead.icp_score else "Sem score"
        print(f"   {i}. @{lead.username} | {lead.full_name or 'N/A'} | {score_info}")
    print("-"*40)
    print()

    # 2. Confirmação
    confirm = input("🚀 Iniciar prospecção de 5 perfis? (s/n): ").strip().lower()
    if confirm != 's':
        print("❌ Cancelado pelo usuário")
        return

    print()
    print("🚀 Iniciando AgenticOS em modo visual...")
    print("   O navegador vai abrir para você acompanhar")
    print()

    # 3. Iniciar agente
    agent = InstagramDMAgent(
        headless=False,     # Modo visual
        smart_mode=True,    # Análise de perfil + scoring
        tenant_id="DEFAULT"
    )

    try:
        await agent.start()

        # 4. Login
        print("🔐 Verificando sessão do Instagram...")
        if not await agent.login():
            print("❌ Falha no login. Verifique as credenciais.")
            return

        # 5. Executar campanha de 5 DMs
        print()
        print("="*60)
        print("🎯 INICIANDO CAMPANHA DE DEMONSTRAÇÃO")
        print("   Limite: 5 DMs")
        print("   Modo: Smart (análise de perfil + scoring)")
        print("="*60)
        print()

        await agent.run_campaign(
            limit=5,          # Apenas 5 perfis
            template_id=1,    # Template padrão (backup se smart falhar)
            min_score=0       # Sem filtro de score para demo
        )

    except KeyboardInterrupt:
        print("\n⚠️ Interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        raise
    finally:
        await agent.stop()

    print()
    print("="*60)
    print("✅ DEMO CONCLUÍDO!")
    print("="*60)
    print()
    print("📊 Resultados:")
    print(f"   DMs enviadas: {agent.dms_sent}")
    print(f"   DMs falharam: {agent.dms_failed}")
    print(f"   Leads pulados: {agent.dms_skipped}")
    print()
    print("Os leads prospectados foram sincronizados com:")
    print("   ✅ growth_leads (Supabase)")
    print("   ✅ GoHighLevel (se configurado)")
    print()


if __name__ == "__main__":
    asyncio.run(demo_prospeccao())
