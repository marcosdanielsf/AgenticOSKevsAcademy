# Backup Supabase - MOTTIVME

## Visão Geral

Sistema de backup automático diário do banco Supabase usando GitHub Actions.

**Frequência:** Diário às 3h (horário de Brasília)
**Retenção:** Últimos 30 backups
**Armazenamento:** Diretório `/backups` no repositório

---

## O que é salvo

| Arquivo | Conteúdo |
|---------|----------|
| `schema_*.sql` | Estrutura das tabelas, views, functions |
| `data_*.sql` | Todos os dados das tabelas |
| `roles_*.sql` | Permissões RLS e roles |

Tudo é comprimido em um único arquivo `backup_YYYY-MM-DD_HH-MM-SS.tar.gz`.

---

## Setup Inicial (OBRIGATÓRIO)

### 1. Obter a Connection String do Supabase

1. Acesse: https://supabase.com/dashboard/project/bfumywvwubvernvhjehk/settings/database
2. Em **Connection string** → **URI**, copie a string
3. Substitua `[YOUR-PASSWORD]` pela senha do banco

Formato:
```
postgresql://postgres.bfumywvwubvernvhjehk:[PASSWORD]@aws-0-sa-east-1.pooler.supabase.com:6543/postgres
```

### 2. Configurar Secret no GitHub

1. Acesse: https://github.com/marcosdanielsf/AgenticOSKevsAcademy/settings/secrets/actions
2. Clique em **New repository secret**
3. Nome: `SUPABASE_DB_URL`
4. Valor: Cole a connection string do passo anterior
5. Clique em **Add secret**

### 3. Testar o Backup

1. Acesse: https://github.com/marcosdanielsf/AgenticOSKevsAcademy/actions
2. Clique em **Supabase Daily Backup**
3. Clique em **Run workflow** → **Run workflow**
4. Aguarde completar (~2-5 minutos)
5. Verifique se o arquivo apareceu em `/backups/`

---

## Restaurar Backup

### Opção 1: Script automático

```bash
# Definir a URL do banco
export SUPABASE_DB_URL='postgresql://postgres.bfumywvwubvernvhjehk:SENHA@aws-0-sa-east-1.pooler.supabase.com:6543/postgres'

# Listar backups disponíveis
ls -la backups/

# Restaurar um backup específico
./scripts/restore-backup.sh backups/backup_2026-01-09_06-00-00.tar.gz
```

### Opção 2: Manual com psql

```bash
# Extrair o backup
tar -xzf backups/backup_2026-01-09_06-00-00.tar.gz -C /tmp/

# Restaurar schema primeiro
psql "$SUPABASE_DB_URL" -f /tmp/schema_2026-01-09_06-00-00.sql

# Depois os dados
psql "$SUPABASE_DB_URL" -f /tmp/data_2026-01-09_06-00-00.sql

# Por fim as roles
psql "$SUPABASE_DB_URL" -f /tmp/roles_2026-01-09_06-00-00.sql
```

---

## Rodar Backup Manualmente

### Via GitHub Actions (recomendado)
1. Acesse: https://github.com/marcosdanielsf/AgenticOSKevsAcademy/actions
2. Clique em **Supabase Daily Backup**
3. Clique em **Run workflow**

### Via CLI local
```bash
# Instalar Supabase CLI
npm install -g supabase

# Definir URL
export SUPABASE_DB_URL='postgresql://...'

# Fazer backup
supabase db dump --db-url "$SUPABASE_DB_URL" -f backup_manual.sql
```

---

## Monitoramento

### Verificar últimos backups
```bash
ls -lah backups/ | head -10
```

### Ver histórico de execuções
https://github.com/marcosdanielsf/AgenticOSKevsAcademy/actions/workflows/supabase-backup.yml

### Alertas de falha
GitHub envia email automático se o workflow falhar.

---

## Troubleshooting

### Erro: "password authentication failed"
- Verifique se a senha está correta no secret `SUPABASE_DB_URL`
- Regenere a senha em: Dashboard → Settings → Database → Reset database password

### Erro: "connection refused"
- Verifique se o IP do GitHub Actions está na whitelist
- Por padrão, Supabase permite conexões de qualquer IP

### Backup muito grande (>100MB)
- Considere usar compressão adicional
- Ou fazer backup apenas de tabelas específicas

### Workflow não roda automaticamente
- Verifique se o arquivo está em `.github/workflows/`
- Verifique se o cron está correto: `0 6 * * *` = 6h UTC = 3h Brasília

---

## Arquivos Relacionados

| Arquivo | Descrição |
|---------|-----------|
| `.github/workflows/supabase-backup.yml` | Workflow do GitHub Actions |
| `scripts/restore-backup.sh` | Script para restaurar backup |
| `backups/` | Diretório com backups comprimidos |

---

## Custos

- **GitHub Actions:** Gratuito (2000 min/mês no plano free)
- **Armazenamento:** Gratuito (conta como arquivos do repo)
- **Supabase:** Já incluso no seu plano

---

> **Última atualização:** 2026-01-09
> **Autor:** Claude Code
