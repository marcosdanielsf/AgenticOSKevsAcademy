# AgenticOS - Lista de Tarefas

> **Atualizado em:** 2026-01-19 (manhã)
> **Status:** Block Detection implementado ✅
> **Leia este arquivo apos reset de memoria para saber onde parou**

---

## Legenda

- [ ] Pendente
- [x] Concluido
- [~] Em progresso

---

## Sessão 2026-01-17 - CONCLUÍDO

### Bugs Corrigidos
- [x] Corrigir `agent.start()` não chamado antes de `run_campaign()` (api_server.py)
- [x] Adicionar Pillow ao requirements.txt (Gemini Vision)
- [x] Implementar carregamento de sessão do banco Supabase
- [x] Atualizar sessão no banco via script `/tmp/claude/update_session.py`
- [x] Deploy no Railway com código novo
- [x] Testar campanha - **1 DM enviado com sucesso!**

### Templates Charlie Morgan
- [x] Reescrever templates para estilo curto/vago/curioso
- [x] Implementar extração de especialidades da bio
- [x] Adicionar novos hooks por profissão
- [x] Commit: `feat: rewrite message templates to Charlie Morgan style`
- [ ] **Git Push pendente** (problema de conexão)

---

## Sessão 2026-01-17 (Continuação) - MÉTODO KEVS IMPLEMENTADO

### ✅ Concluído: Prospecção Multi-Conta

- [x] **Suporte a múltiplos perfis de origem**
  - [x] Adicionar `target_type: "profiles"` (plural)
  - [x] Aceitar lista separada por vírgula
  - [x] Scrape followers de cada perfil

- [x] **Rotação Round-Robin entre contas**
  - [x] Implementar `RoundRobinAccountRotator` em `account_manager.py`
  - [x] Alternância A→B→C→A→B→C (não esgota uma conta antes)
  - [x] Pular conta se bloqueada automaticamente

- [x] **Delay Aleatório entre DMs (Método Kevs)**
  - [x] Adicionar parâmetros `delay_min` e `delay_max` em MINUTOS
  - [x] Jitter humano (±15% de variação)
  - [x] Novo método `run_campaign_kevs()` em `instagram_dm_agent.py`

### Fluxo Implementado:
```
08:00 → Conta A: DM1
08:05 → Conta B: DM2  (delay ~5 min)
08:11 → Conta C: DM3  (delay ~6 min)
08:17 → Conta A: DM4  ← volta pro início
...
```

### Parâmetros da Campanha Kevs:
```json
{
  "tenant_id": "mottivme",
  "target_type": "profiles",
  "target_value": "dr_joao,dra_maria,clinica_xyz",
  "limit": 150,
  "kevs_mode": true,
  "delay_min": 3,
  "delay_max": 7
}
```

## Sessão 2026-01-17 (Tarde) - SPINTAX + SOP

### ✅ Concluído: Análise de Documentação
- [x] Análise do Stack Kevin Badi (Claude Code + Playwright MCP)
- [x] Comparação de opções Playwright MCP (Stealth recomendado)
- [x] Clone System SOP documentado
- [x] Instagram Private API documentado

### ✅ Concluído: Spintax Híbrido
- [x] Função `expand_spintax()` para variação sintática
- [x] Templates de saudação com spintax
- [x] Templates de fechamento com spintax por nível
- [x] Método `generate_hybrid()` que combina spintax + IA
- [x] Conteúdo central continua personalizado por IA/bio

### Arquivos Criados/Modificados:
- `.claude/spec/clone-system-sop.md` - SOP completo do Clone System
- `implementation/message_generator.py` - Spintax híbrido adicionado

---

## Sessão 2026-01-19 - BLOCK DETECTION ✅

### ✅ Concluído: Sistema de Detecção de Bloqueio

- [x] **BlockType enum** com tipos de bloqueio:
  - `checkpoint` - Verificação do Instagram
  - `action_blocked` - Ação temporariamente bloqueada
  - `rate_limited` - Limite de taxa
  - `account_disabled` - Conta desabilitada
  - `suspicious_activity` - Atividade suspeita
  - `two_factor` - Desafio 2FA

- [x] **BlockDetectionResult dataclass**
  - `is_blocked`, `block_type`, `message`
  - `should_stop_campaign` property (bloqueios críticos)
  - `should_switch_account` property (para multi-conta)

- [x] **Método `check_for_block()`**
  - Detecção por URL (checkpoint, challenge, two_factor)
  - Detecção por conteúdo da página
  - Detecção em dialogs/popups
  - Screenshot automático em bloqueio

- [x] **Atualizado `send_dm()`**
  - Verifica bloqueio antes de enviar
  - Verifica bloqueio após enviar
  - Retorna erro no formato `BLOCKED:type:message`

- [x] **Atualizado `run_campaign()`**
  - Para campanha em bloqueios críticos
  - Aguarda 5min em rate limit

- [x] **Atualizado `run_campaign_kevs()`**
  - Remove conta bloqueada da rotação
  - Para se TODAS as contas bloqueadas

### Commit: `076b09e`

---

## PRÓXIMA SESSÃO - Implementações Pendentes

### P0 - Urgente
- [ ] Testar spintax híbrido em campanha real
- [ ] Testar block detection em campanha real

### P1 - Importante
- [ ] Warm-up protocol manager
- [ ] Instagram Private API extraction
- [ ] Proxy rotation infrastructure

### P2 - Infraestrutura
- [ ] Stealth Browser MCP integration
- [ ] Redis para rate limiting distribuído

---

## Backlog - Escalabilidade

### FASE 1 - URGENTE
- [ ] Redis para campanhas e rate limiting
- [ ] Connection pooling (httpx)
- [ ] Retry logic (tenacity)

### FASE 2 - IMPORTANTE
- [ ] Celery + Job Queue
- [ ] Checkpoint system para campanhas
- [ ] JWT auth + RBAC

### FASE 3 - OBSERVABILIDADE
- [ ] Sentry para erros
- [ ] Prometheus metrics
- [ ] Structured logging

---

## Arquivos Modificados (2026-01-17)

| Arquivo | Mudança |
|---------|---------|
| `implementation/api_server.py` | Adicionado `agent.start()` antes de `run_campaign()` |
| `implementation/instagram_dm_agent.py` | Carregamento de sessão do banco Supabase |
| `implementation/message_generator.py` | Templates Charlie Morgan |
| `requirements.txt` | Adicionado Pillow>=10.0.0 |

---

## Scripts Úteis

```bash
# Testar campanha
bash /tmp/claude/test_campaign.sh

# Verificar status
bash /tmp/claude/check_status.sh

# Atualizar sessão no banco
python /tmp/claude/update_session.py

# Push pendente
git push origin main
```

---

## Como Retomar

1. Ler `.claude/context.md` e `.claude/todos.md`
2. Fazer `git push origin main` (commit Charlie Morgan pendente)
3. Implementar rotação round-robin + delay (método Kevs)
4. Testar com múltiplas contas
