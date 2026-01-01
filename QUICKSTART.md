# AgenticOS - Quick Start Guide

## Instagram DM Agent - Execução Rápida

### 1. Pré-requisitos

```bash
# Instalar dependências
pip install playwright python-dotenv requests

# Instalar browser do Playwright
playwright install chromium
```

### 2. Configurar Supabase

Acesse: https://supabase.com/dashboard → SQL Editor

Execute o SQL em `database/setup_supabase.py` (função `get_create_tables_sql()`)

### 3. Executar

```bash
# Opção 1: Menu interativo
./run_instagram_agent.sh

# Opção 2: Comandos diretos
python implementation/instagram_dm_agent.py --login-only      # Login + salvar sessão
python implementation/instagram_dm_agent.py --limit 10        # Enviar 10 DMs
python implementation/instagram_dm_agent.py --headless        # Modo sem janela
```

### 4. Resolver 2FA

1. Execute `--login-only`
2. Complete o 2FA no navegador (2 minutos)
3. Sessão será salva automaticamente

### 5. Adicionar Leads

```bash
python scripts/populate_leads.py
```

Ou adicione diretamente no Supabase Dashboard → Table Editor → agentic_instagram_leads

---

## Estrutura de Arquivos

```
├── implementation/
│   └── instagram_dm_agent.py    # Agente principal
├── config/
│   └── dm_templates.py          # Mensagens de abordagem
├── scripts/
│   └── populate_leads.py        # Popular leads demo
├── database/
│   └── setup_supabase.py        # SQL das tabelas
├── sessions/
│   └── instagram_session.json   # Sessão do Instagram
├── logs/
│   └── instagram_dm_*.log       # Logs de execução
└── .env                         # Credenciais
```

## Rate Limits

- **10 DMs/hora** (configurável em .env)
- **200 DMs/dia** (configurável em .env)
- **30-60 seg delay** entre DMs (aleatório)

## Tabelas Supabase

| Tabela | Descrição |
|--------|-----------|
| `agentic_instagram_leads` | Leads para contatar |
| `agentic_instagram_dm_sent` | DMs enviados |
| `agentic_instagram_dm_runs` | Execuções do agente |
| `agentic_instagram_daily_stats` | Estatísticas diárias |

## Comandos Úteis

```bash
# Ver status
./run_instagram_agent.sh  # Opção 5

# Testar 1 DM
python implementation/instagram_dm_agent.py --limit 1

# Executar 50 DMs
python implementation/instagram_dm_agent.py --limit 50

# Usar template 2
python implementation/instagram_dm_agent.py --template 2
```
