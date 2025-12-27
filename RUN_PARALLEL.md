# Como Executar os Subagentes em Paralelo

## Opção 1: VS Code com Múltiplos Terminais

### Passo 1: Abra 3 terminais no VS Code
- Terminal 1: `Ctrl+Shift+` (novo terminal)
- Terminal 2: Clique no `+` na barra de terminais
- Terminal 3: Clique no `+` novamente

### Passo 2: Execute em cada terminal

**Terminal 1 - Environment Setup (PRIMEIRO)**
```bash
cd /home/user/AgenticOSKevsAcademy
claude "Execute as instruções em agents/01_environment_setup.md. Seja metódico, complete cada tarefa e reporte o status final."
```

**Terminal 2 - Instagram Agent (APÓS Terminal 1 concluir)**
```bash
cd /home/user/AgenticOSKevsAcademy
claude "Execute as instruções em agents/02_instagram_dm_agent.md. Crie todos os arquivos especificados e teste o que for possível."
```

**Terminal 3 - Integrations (PARALELO com Terminal 2)**
```bash
cd /home/user/AgenticOSKevsAcademy
claude "Execute as instruções em agents/03_integrations_config.md. Crie os scripts de teste e documente o status de cada integração."
```

---

## Opção 2: Script Automatizado

```bash
chmod +x run_agents.sh
./run_agents.sh all
```

---

## Opção 3: tmux (Terminal Multiplexer)

```bash
# Criar sessão tmux
tmux new-session -d -s agentic

# Janela 1: Environment
tmux send-keys -t agentic "cd /home/user/AgenticOSKevsAcademy && claude 'Execute agents/01_environment_setup.md'" Enter

# Dividir horizontalmente para janela 2
tmux split-window -h -t agentic
tmux send-keys -t agentic "cd /home/user/AgenticOSKevsAcademy && sleep 60 && claude 'Execute agents/02_instagram_dm_agent.md'" Enter

# Dividir verticalmente para janela 3
tmux split-window -v -t agentic
tmux send-keys -t agentic "cd /home/user/AgenticOSKevsAcademy && sleep 60 && claude 'Execute agents/03_integrations_config.md'" Enter

# Anexar à sessão
tmux attach -t agentic
```

---

## Opção 4: Execução Manual Sequencial (Mais Simples)

Se preferir executar um por um com controle total:

```bash
# 1. Environment Setup
cd /home/user/AgenticOSKevsAcademy
claude "Execute agents/01_environment_setup.md"

# 2. Instagram Agent
claude "Execute agents/02_instagram_dm_agent.md"

# 3. Integrations
claude "Execute agents/03_integrations_config.md"

# 4. Commit final
git add -A
git commit -m "feat: Complete AgenticOS setup with Instagram DM Agent"
git push -u origin claude/project-overview-VJwte
```

---

## Ordem de Execução Recomendada

```
┌─────────────────────────────────────────────────────────────┐
│ FASE 1 (5-10 min)                                           │
│ ┌─────────────────────────────────────────┐                 │
│ │  SUBAGENTE 1: Environment Setup         │                 │
│ │  - requirements.txt                      │                 │
│ │  - .env                                  │                 │
│ │  - Playwright install                    │                 │
│ │  - Estrutura de pastas                   │                 │
│ └─────────────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ FASE 2 (15-30 min) - PARALELO                               │
│ ┌───────────────────────┐  ┌───────────────────────┐        │
│ │ SUBAGENTE 2           │  │ SUBAGENTE 3           │        │
│ │ Instagram DM Agent    │  │ Integrations Config   │        │
│ │ - instruction/*.md    │  │ - tests/*.py          │        │
│ │ - implementation/*.py │  │ - docs/*.md           │        │
│ │ - Login flow          │  │ - Validar APIs        │        │
│ └───────────────────────┘  └───────────────────────┘        │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ FASE 3 (5 min)                                              │
│ ┌─────────────────────────────────────────┐                 │
│ │  Git Commit + Push                       │                 │
│ │  - Verificar todos os arquivos          │                 │
│ │  - Commit com mensagem descritiva       │                 │
│ │  - Push para branch                      │                 │
│ └─────────────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Tempo Total Estimado

| Fase | Tempo | Descrição |
|------|-------|-----------|
| Fase 1 | 5-10 min | Setup de ambiente |
| Fase 2 | 15-30 min | Instagram + Integrações (paralelo) |
| Fase 3 | 5 min | Git commit/push |
| **Total** | **25-45 min** | Projeto completo configurado |

---

## Verificação Final

Após todos os subagentes completarem, execute:

```bash
# Verificar estrutura
ls -la agents/ implementation/ instruction/ tests/ logs/ data/ sessions/

# Verificar integrações
python tests/test_all_integrations.py

# Verificar Instagram agent
python -c "from implementation.instagram_dm_agent import InstagramDMAgent; print('OK')"

# Status git
git status
```

---

## Troubleshooting

### Claude Code não encontrado
```bash
npm install -g @anthropic-ai/claude-code
```

### Playwright não instala
```bash
pip install playwright
playwright install chromium
```

### Erro de permissão no script
```bash
chmod +x run_agents.sh
```

### Subagente travou
- Verifique os logs em `logs/`
- Cancele com `Ctrl+C`
- Execute novamente apenas o subagente que falhou
