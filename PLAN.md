# PLAN.md - Plano de Execução Paralela AgenticOS

## Visão Geral

Este plano organiza a execução paralela do setup completo do AgenticOS por múltiplos subagentes Claude especializados.

---

## Arquitetura de Execução

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ORQUESTRADOR PRINCIPAL                           │
│                    (Terminal/VS Code)                               │
└─────────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  SUBAGENTE 1  │    │  SUBAGENTE 2  │    │  SUBAGENTE 3  │
│  Environment  │    │  Instagram    │    │  Integrations │
│    Setup      │    │   DM Agent    │    │    Config     │
└───────────────┘    └───────────────┘    └───────────────┘
        │                     │                     │
        ▼                     ▼                     ▼
   .env config          Playwright +          Instantly +
   requirements         DM workflow           Apify + Klap
   PostgreSQL           Session mgmt         Google Sheets
```

---

## Subagentes e Suas Responsabilidades

### SUBAGENTE 1: Environment Setup
**Arquivo de instrução:** `agents/01_environment_setup.md`
**Tempo estimado:** 20-30 min
**Dependências:** Nenhuma (pode rodar primeiro ou em paralelo)

**Tarefas:**
- [ ] Criar `.env` com todas as variáveis necessárias
- [ ] Atualizar `requirements.txt` com Playwright e dependências
- [ ] Configurar estrutura de pastas (`agents/`, `sessions/`, `logs/`)
- [ ] Setup inicial do PostgreSQL (tabelas base)
- [ ] Criar `service_account.json` template

---

### SUBAGENTE 2: Instagram DM Agent
**Arquivo de instrução:** `agents/02_instagram_dm_agent.md`
**Tempo estimado:** 1-2 horas
**Dependências:** SUBAGENTE 1 (precisa do Playwright instalado)

**Tarefas:**
- [ ] Criar `instruction/instagram_dm_agent.md` (cérebro do agente)
- [ ] Criar `implementation/instagram_dm_agent.py` (executor)
- [ ] Implementar login com sessão persistente
- [ ] Implementar loop de envio de DMs
- [ ] Configurar limites anti-ban (10/hora, 200/dia)
- [ ] Criar tabela de tracking no banco
- [ ] Implementar sistema de leads (CSV/banco)

---

### SUBAGENTE 3: Integrations Config
**Arquivo de instrução:** `agents/03_integrations_config.md`
**Tempo estimado:** 30-45 min
**Dependências:** SUBAGENTE 1 (precisa do .env configurado)

**Tarefas:**
- [ ] Validar configuração Instantly.ai
- [ ] Validar configuração Apify
- [ ] Validar configuração Google Sheets
- [ ] Validar configuração Klap
- [ ] Validar configuração Gemini
- [ ] Criar scripts de teste para cada integração
- [ ] Documentar status de cada integração

---

## Ordem de Execução

```
FASE 1 (Paralelo):
├── SUBAGENTE 1: Environment Setup ──────────────────────┐
│                                                         │
FASE 2 (Após SUBAGENTE 1):                               │
├── SUBAGENTE 2: Instagram DM Agent ◄────────────────────┤
├── SUBAGENTE 3: Integrations Config ◄───────────────────┘
│
FASE 3 (Após todos):
└── Commit + Push para GitHub
```

---

## Comandos de Execução

### Terminal 1 - Subagente 1 (Environment)
```bash
cd /home/user/AgenticOSKevsAcademy
claude --print "Execute as instruções em agents/01_environment_setup.md"
```

### Terminal 2 - Subagente 2 (Instagram Agent)
```bash
cd /home/user/AgenticOSKevsAcademy
claude --print "Execute as instruções em agents/02_instagram_dm_agent.md"
```

### Terminal 3 - Subagente 3 (Integrations)
```bash
cd /home/user/AgenticOSKevsAcademy
claude --print "Execute as instruções em agents/03_integrations_config.md"
```

---

## Estrutura Final do Projeto

```
AgenticOSKevsAcademy/
├── .env                              # Configurações (NÃO commitar)
├── .env.example                      # Template de configurações
├── CLAUDE.md                         # Instruções para Claude Code
├── PLAN.md                           # Este arquivo
├── README.md                         # Documentação do projeto
├── requirements.txt                  # Dependências Python
│
├── agents/                           # Instruções para subagentes
│   ├── 01_environment_setup.md
│   ├── 02_instagram_dm_agent.md
│   └── 03_integrations_config.md
│
├── core/                             # Framework base
│   ├── agent_base.py
│   ├── api_integration.py
│   ├── communication.py
│   ├── monitoring.py
│   ├── parallel_engine.py
│   └── swarm_orchestrator.py
│
├── implementation/                   # Implementações dos agentes
│   ├── instagram_dm_agent.py         # NOVO
│   ├── instantly_analytics.py
│   ├── instantly_campaign_analytics.py
│   ├── instantly_push.py
│   ├── apify_leads_sheet.py
│   ├── klap_generate_shorts_enhanced.py
│   ├── gemini_viral_shorts_post.py
│   └── ...
│
├── instruction/                      # Cérebros dos agentes (information.md)
│   ├── instagram_dm_agent.md         # NOVO
│   ├── instantly_analytics_overview.md
│   ├── klap_generate_shorts.md
│   └── ...
│
├── sessions/                         # Sessões salvas (cookies, etc)
│   └── instagram_session.json        # NOVO
│
├── logs/                             # Logs de execução
│   └── instagram_dm.log              # NOVO
│
├── data/                             # Dados de leads e resultados
│   └── instagram_leads.csv           # NOVO
│
└── tests/                            # Scripts de teste
    ├── test_instagram_login.py       # NOVO
    ├── test_instantly_api.py
    └── ...
```

---

## Variáveis de Ambiente Necessárias

```bash
# === CORE ===
DATABASE_URL=postgresql://user:pass@host:5432/dbname
REDIS_URL=redis://localhost:6379

# === INSTAGRAM DM AGENT ===
INSTAGRAM_USERNAME=your_username
INSTAGRAM_PASSWORD=your_password

# === INSTANTLY.AI ===
INSTANTLY_API_KEY=your_key

# === APIFY ===
APIFY_API_KEY=your_key

# === GOOGLE ===
GOOGLE_CLIENT_ID=your_id
GOOGLE_CLIENT_SECRET=your_secret
GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id

# === KLAP ===
KLAP_API_KEY=your_key

# === GEMINI ===
GEMINI_API_KEY=your_key

# === PHANTOMBUSTER ===
PHANTOMBUSTER_API_KEY=your_key
PHANTOMBUSTER_AGENT_ID=your_agent_id

# === AYRSHARE ===
AYRSHARE_API_KEY=your_key
```

---

## Checklist de Conclusão

### Environment Setup
- [ ] `.env` criado com todas as variáveis
- [ ] `requirements.txt` atualizado
- [ ] Pastas criadas (`agents/`, `sessions/`, `logs/`, `data/`, `tests/`)
- [ ] PostgreSQL configurado
- [ ] Playwright instalado

### Instagram DM Agent
- [ ] `instruction/instagram_dm_agent.md` criado
- [ ] `implementation/instagram_dm_agent.py` criado
- [ ] Login funcionando
- [ ] Sessão sendo salva
- [ ] DMs sendo enviados
- [ ] Limites configurados
- [ ] Logs funcionando

### Integrations
- [ ] Instantly.ai testado
- [ ] Apify testado
- [ ] Google Sheets testado
- [ ] Klap testado
- [ ] Gemini testado

### Git/GitHub
- [ ] Todos os arquivos commitados
- [ ] Push para branch `claude/project-overview-VJwte`
- [ ] README atualizado

---

## Notas Importantes

1. **Sessões do Instagram**: Salvar em `sessions/` e adicionar ao `.gitignore`
2. **Credenciais**: NUNCA commitar `.env` - usar `.env.example` como template
3. **Limites Instagram**: 10 DMs/hora, 200 DMs/dia, pausas de 30-60s entre envios
4. **Playwright**: Usar modo headless para produção, headed para debug
5. **Logs**: Todos os agentes devem logar em `logs/` com timestamp

---

## Próximos Passos Após Setup

1. Testar cada agente individualmente
2. Configurar Modal para jobs agendados
3. Criar dashboard de monitoramento
4. Escalar para múltiplas contas Instagram
5. Integrar com CRM (HubSpot, etc)
