#!/bin/bash

# =============================================================================
# RESTORE BACKUP - Supabase MOTTIVME
# =============================================================================
# Uso: ./restore-backup.sh <arquivo_backup.tar.gz>
# Exemplo: ./restore-backup.sh backups/backup_2026-01-09_06-00-00.tar.gz
# =============================================================================

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verificar argumento
if [ -z "$1" ]; then
    echo -e "${RED}Erro: Informe o arquivo de backup${NC}"
    echo "Uso: ./restore-backup.sh <arquivo_backup.tar.gz>"
    echo ""
    echo "Backups disponíveis:"
    ls -la backups/*.tar.gz 2>/dev/null || echo "  Nenhum backup encontrado em ./backups/"
    exit 1
fi

BACKUP_FILE=$1

# Verificar se arquivo existe
if [ ! -f "$BACKUP_FILE" ]; then
    echo -e "${RED}Erro: Arquivo não encontrado: $BACKUP_FILE${NC}"
    exit 1
fi

# Verificar variável de ambiente
if [ -z "$SUPABASE_DB_URL" ]; then
    echo -e "${YELLOW}SUPABASE_DB_URL não definida.${NC}"
    echo ""
    echo "Defina com:"
    echo "  export SUPABASE_DB_URL='postgresql://postgres.REF:PASSWORD@aws-0-us-east-1.pooler.supabase.com:5432/postgres'"
    echo ""
    echo "Ou adicione no arquivo .env e rode:"
    echo "  source .env && ./scripts/restore-backup.sh $BACKUP_FILE"
    exit 1
fi

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}   RESTORE SUPABASE BACKUP${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""
echo -e "Arquivo: ${GREEN}$BACKUP_FILE${NC}"
echo ""
echo -e "${RED}ATENÇÃO: Isso vai SOBRESCREVER os dados atuais!${NC}"
echo ""
read -p "Tem certeza que deseja continuar? (digite 'sim' para confirmar): " confirm

if [ "$confirm" != "sim" ]; then
    echo "Operação cancelada."
    exit 0
fi

# Criar diretório temporário
TEMP_DIR=$(mktemp -d)
echo ""
echo "Extraindo backup..."

# Extrair backup
tar -xzf "$BACKUP_FILE" -C "$TEMP_DIR"

# Listar arquivos extraídos
echo "Arquivos encontrados:"
ls -la "$TEMP_DIR"

# Restore Schema (estrutura)
SCHEMA_FILE=$(ls "$TEMP_DIR"/schema_*.sql 2>/dev/null | head -1)
if [ -n "$SCHEMA_FILE" ]; then
    echo ""
    echo -e "${YELLOW}Restaurando schema...${NC}"
    psql "$SUPABASE_DB_URL" -f "$SCHEMA_FILE"
    echo -e "${GREEN}Schema restaurado!${NC}"
fi

# Restore Data (dados)
DATA_FILE=$(ls "$TEMP_DIR"/data_*.sql 2>/dev/null | head -1)
if [ -n "$DATA_FILE" ]; then
    echo ""
    echo -e "${YELLOW}Restaurando dados...${NC}"
    psql "$SUPABASE_DB_URL" -f "$DATA_FILE"
    echo -e "${GREEN}Dados restaurados!${NC}"
fi

# Restore Roles (permissões)
ROLES_FILE=$(ls "$TEMP_DIR"/roles_*.sql 2>/dev/null | head -1)
if [ -n "$ROLES_FILE" ]; then
    echo ""
    echo -e "${YELLOW}Restaurando roles/permissões...${NC}"
    psql "$SUPABASE_DB_URL" -f "$ROLES_FILE" || echo "Alguns roles podem já existir (ok)"
    echo -e "${GREEN}Roles restaurados!${NC}"
fi

# Limpar
rm -rf "$TEMP_DIR"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   RESTORE COMPLETO!${NC}"
echo -e "${GREEN}========================================${NC}"
