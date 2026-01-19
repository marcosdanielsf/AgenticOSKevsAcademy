#!/bin/bash
# Script para salvar conhecimento no RAG (Segundo Cérebro)
# Execute quando a internet voltar: bash save_to_rag.sh

API_URL="https://agenticoskevsacademy-production.up.railway.app/webhook/rag-ingest"

echo "🧠 Salvando no Segundo Cérebro..."

# 1. Sistema Completo
curl -s -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "category": "pattern",
    "title": "Sistema Instagram DM Automation - Segurança 8/10",
    "content": "Sistema completo de prospecção Instagram implementado em 2026-01-19.\n\nCOMPONENTES:\n1. Proxy Residencial Decodo (gate.decodo.com:10001)\n2. Playwright Stealth (anti-detection)\n3. Warm-up Protocol (4 estágios)\n4. Block Detection (8 tipos)\n5. Spintax Híbrido\n6. Multi-Conta Round-Robin\n\nARQUIVOS:\n- instagram_dm_agent.py\n- proxy_manager.py\n- warmup_manager.py\n- message_generator.py\n\nTESTE: python3 test_campaign_full.py",
    "project_key": "agenticOS",
    "tags": ["instagram", "automation", "proxy", "stealth", "security"]
  }' && echo " ✅ Pattern salvo"

# 2. Decisão Arquitetural
curl -s -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "category": "decision",
    "title": "Arquitetura Segurança Instagram - Camadas",
    "content": "Decisão: Sistema de segurança em 4 camadas.\n\n1. REDE: Proxy residencial Decodo\n2. BROWSER: Playwright Stealth\n3. COMPORTAMENTO: Warm-up protocol\n4. DETECÇÃO: Block detection 8 tipos\n\nResultado: Nível 8/10 de segurança",
    "project_key": "agenticOS",
    "tags": ["arquitetura", "decisao", "seguranca"]
  }' && echo " ✅ Decisão salva"

# 3. Error Fix - Proxy
curl -s -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "category": "error_fix",
    "title": "HTTP 407 Proxy Authentication - Decodo Trial",
    "content": "ERRO: HTTP 407 Proxy Authentication Required\nCAUSA: Plano trial Decodo tem limite de conexões\nSOLUÇÃO: Ativar plano pago ($6/mês 2GB)\nRESULTADO: Proxy funciona imediatamente após pagamento",
    "project_key": "agenticOS",
    "tags": ["proxy", "error", "decodo", "authentication"]
  }' && echo " ✅ Error fix salvo"

# 4. Error Fix - Seletores
curl -s -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "category": "error_fix",
    "title": "Instagram Selector Not Found - Search Field",
    "content": "ERRO: input[placeholder=\"Search...\"] não encontrado\nCAUSA: Instagram mudou placeholder para \"Search\"\nSOLUÇÃO: Usar múltiplos fallbacks com div[role=\"dialog\"] como prefixo\nCÓDIGO:\nselectors = [\n  div[role=\"dialog\"] input[name=\"queryBox\"],\n  div[role=\"dialog\"] input[placeholder=\"Search...\"],\n  div[role=\"dialog\"] input[placeholder=\"Search\"]\n]",
    "project_key": "agenticOS",
    "tags": ["instagram", "selector", "error", "playwright"]
  }' && echo " ✅ Selector fix salvo"

echo ""
echo "🎉 Conhecimento salvo no Segundo Cérebro!"
