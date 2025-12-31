#!/bin/bash

# ============================================
# AgenticOS - Instagram DM Agent Runner
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║         AgenticOS - Instagram DM Agent                   ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ Arquivo .env não encontrado!${NC}"
    echo "   Copie o .env.example e configure suas credenciais."
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 não encontrado!${NC}"
    exit 1
fi

# Menu
show_menu() {
    echo -e "${YELLOW}Escolha uma opção:${NC}"
    echo ""
    echo "  1) 🔧 Setup - Criar tabelas no Supabase"
    echo "  2) 📥 Leads - Popular leads de demonstração"
    echo "  3) 🔐 Login - Fazer login no Instagram (salvar sessão)"
    echo "  4) 🚀 Run   - Executar campanha de DMs"
    echo "  5) 📊 Stats - Ver estatísticas"
    echo "  6) 🧪 Test  - Enviar DM de teste (1 mensagem)"
    echo ""
    echo "  0) ❌ Sair"
    echo ""
}

# Setup tables
setup_tables() {
    echo -e "${BLUE}🔧 Criando tabelas no Supabase...${NC}"
    python3 database/setup_supabase.py
}

# Populate leads
populate_leads() {
    echo -e "${BLUE}📥 Populando leads de demonstração...${NC}"
    python3 scripts/populate_leads.py
}

# Login only
login_only() {
    echo -e "${BLUE}🔐 Fazendo login no Instagram...${NC}"
    echo -e "${YELLOW}⚠️  Complete o 2FA no navegador se necessário${NC}"
    python3 implementation/instagram_dm_agent.py --login-only
}

# Run campaign
run_campaign() {
    read -p "Quantos DMs enviar? (padrão: 10): " limit
    limit=${limit:-10}

    read -p "Template (1, 2 ou 3): " template
    template=${template:-1}

    echo -e "${BLUE}🚀 Iniciando campanha...${NC}"
    echo "   Limite: $limit DMs"
    echo "   Template: $template"
    echo ""

    python3 implementation/instagram_dm_agent.py --limit "$limit" --template "$template"
}

# View stats
view_stats() {
    echo -e "${BLUE}📊 Estatísticas de hoje:${NC}"
    python3 -c "
import os
import requests
from datetime import date
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

headers = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}',
}

today = date.today().isoformat()

# Get today's stats
response = requests.get(
    f'{SUPABASE_URL}/rest/v1/agentic_instagram_daily_stats',
    headers=headers,
    params={'date': f'eq.{today}'}
)

if response.status_code == 200:
    stats = response.json()
    if stats:
        for stat in stats:
            print(f'   📧 DMs Enviados: {stat[\"dms_sent\"]}')
            print(f'   ❌ DMs Falharam: {stat[\"dms_failed\"]}')
            print(f'   📅 Data: {stat[\"date\"]}')
    else:
        print('   Nenhum dado para hoje.')
else:
    print(f'   Erro: {response.status_code}')
"
}

# Test DM
test_dm() {
    echo -e "${BLUE}🧪 Enviando DM de teste (1 mensagem)...${NC}"
    python3 implementation/instagram_dm_agent.py --limit 1
}

# Main loop
while true; do
    show_menu
    read -p "Opção: " choice
    echo ""

    case $choice in
        1) setup_tables ;;
        2) populate_leads ;;
        3) login_only ;;
        4) run_campaign ;;
        5) view_stats ;;
        6) test_dm ;;
        0) echo -e "${GREEN}👋 Até mais!${NC}"; exit 0 ;;
        *) echo -e "${RED}Opção inválida!${NC}" ;;
    esac

    echo ""
    read -p "Pressione ENTER para continuar..."
    echo ""
done
