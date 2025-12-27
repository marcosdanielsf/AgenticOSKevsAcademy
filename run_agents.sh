#!/bin/bash
#
# AgenticOS - Script de Orquestração de Subagentes
#
# Este script executa múltiplos subagentes Claude em paralelo
# para configurar o projeto completo em tempo recorde.
#
# USO:
#   ./run_agents.sh [all|env|instagram|integrations]
#
# EXEMPLOS:
#   ./run_agents.sh all          # Executa todos os subagentes
#   ./run_agents.sh env          # Apenas environment setup
#   ./run_agents.sh instagram    # Apenas Instagram DM agent
#   ./run_agents.sh integrations # Apenas integrações
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOGS_DIR="$PROJECT_DIR/logs"

# Create logs directory
mkdir -p "$LOGS_DIR"

# Timestamp for logs
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           AgenticOS - Orquestrador de Subagentes             ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Function to run a subagent
run_subagent() {
    local agent_name=$1
    local agent_file=$2
    local log_file="$LOGS_DIR/${agent_name}_${TIMESTAMP}.log"

    echo -e "${YELLOW}▶ Iniciando $agent_name...${NC}"
    echo "  Log: $log_file"

    # Check if claude is available
    if ! command -v claude &> /dev/null; then
        echo -e "${RED}❌ Claude Code não encontrado. Instale com: npm install -g @anthropic-ai/claude-code${NC}"
        return 1
    fi

    # Run the agent in background
    cd "$PROJECT_DIR"
    claude --print "Você é um subagente especializado. Execute TODAS as tarefas descritas no arquivo $agent_file. Seja metódico e complete cada tarefa antes de passar para a próxima. Ao finalizar, reporte o STATUS (SUCCESS/FAILURE) e liste todos os arquivos criados/modificados." > "$log_file" 2>&1 &

    echo $!
}

# Function to wait for agent completion
wait_for_agent() {
    local pid=$1
    local agent_name=$2

    wait $pid
    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✅ $agent_name concluído com sucesso${NC}"
    else
        echo -e "${RED}❌ $agent_name falhou (exit code: $exit_code)${NC}"
    fi

    return $exit_code
}

# Parse command line arguments
COMMAND=${1:-all}

case $COMMAND in
    "all")
        echo -e "${BLUE}Executando TODOS os subagentes...${NC}\n"

        # Phase 1: Environment Setup (must run first)
        echo -e "${YELLOW}━━━ FASE 1: Environment Setup ━━━${NC}"
        PID_ENV=$(run_subagent "environment" "agents/01_environment_setup.md")
        wait_for_agent $PID_ENV "Environment Setup"

        echo ""

        # Phase 2: Instagram + Integrations (can run in parallel)
        echo -e "${YELLOW}━━━ FASE 2: Instagram Agent + Integrations (Paralelo) ━━━${NC}"
        PID_INSTAGRAM=$(run_subagent "instagram" "agents/02_instagram_dm_agent.md")
        PID_INTEGRATIONS=$(run_subagent "integrations" "agents/03_integrations_config.md")

        # Wait for both
        wait_for_agent $PID_INSTAGRAM "Instagram DM Agent"
        wait_for_agent $PID_INTEGRATIONS "Integrations Config"
        ;;

    "env")
        echo -e "${BLUE}Executando apenas Environment Setup...${NC}\n"
        PID=$(run_subagent "environment" "agents/01_environment_setup.md")
        wait_for_agent $PID "Environment Setup"
        ;;

    "instagram")
        echo -e "${BLUE}Executando apenas Instagram DM Agent...${NC}\n"
        PID=$(run_subagent "instagram" "agents/02_instagram_dm_agent.md")
        wait_for_agent $PID "Instagram DM Agent"
        ;;

    "integrations")
        echo -e "${BLUE}Executando apenas Integrations Config...${NC}\n"
        PID=$(run_subagent "integrations" "agents/03_integrations_config.md")
        wait_for_agent $PID "Integrations Config"
        ;;

    *)
        echo -e "${RED}Comando inválido: $COMMAND${NC}"
        echo ""
        echo "Uso: ./run_agents.sh [all|env|instagram|integrations]"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    Execução Concluída!                       ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Logs disponíveis em: $LOGS_DIR/"
echo ""
echo "Próximos passos:"
echo "  1. Verifique os logs para confirmar sucesso"
echo "  2. Configure as variáveis em .env"
echo "  3. Execute: python tests/test_all_integrations.py"
echo "  4. Execute: python tests/test_instagram_login.py"
