# AgenticOS - Lista de Tarefas

> **Atualizado em:** 2026-01-16
> **Leia este arquivo após reset de memória para saber onde parou**

---

## Legenda

- [ ] Pendente
- [x] Concluído
- [~] Em progresso

---

## Fase Atual: Integração Socialfy

### Concluídas (2026-01-16)

- [x] Criar tabela `tenant_icp_config` no Supabase
- [x] Implementar scoring multi-tenant em `lead_scorer.py`
- [x] Adicionar `tenant_id` no `instagram_dm_agent.py`
- [x] Criar método `sync_to_ghl()` para sincronizar com GHL
- [x] Adicionar colunas de scoring na tabela `agentic_instagram_leads`
- [x] Deploy no Railway (funcionando)
- [x] Testar scoring com tenant DEFAULT
- [x] Testar scoring com tenant `startup_abc`
- [x] Criar sistema de memória estendida (.claude/)

### Próximas Tarefas

- [x] **Integrar Socialfy com Supabase real** ✅ (2026-01-16)
  - [x] Configurar variáveis de ambiente no Socialfy
  - [x] Criar hook `useLeads` no Socialfy
  - [x] Criar view de leads com filtro por prioridade
  - [x] Adicionar badges HOT/WARM/COLD nos cards

- [x] **Pipeline de Prospecção** ✅ (2026-01-16)
  - [x] Criar endpoint `/api/campaign/start` no AgenticOS
  - [x] Criar hook `useCampaigns` no Socialfy
  - [x] Criar modal "New Campaign" com formulário completo
  - [x] Integrar botões Start/Stop com API

- [ ] **Melhorias Futuras**
  - [ ] Adicionar logs em tempo real via WebSocket
  - [ ] Remover mock data do `useSupabaseData.ts`
  - [ ] Implementar persistência de campanhas no Supabase

---

## Backlog (Futuro)

- [ ] Implementar autenticação no Socialfy (Supabase Auth)
- [ ] Criar página de configuração de ICP por tenant
- [ ] Dashboard de analytics com Recharts
- [ ] Integrar com LinkedIn (scraping)
- [ ] Testes E2E com Playwright
- [ ] Atualizar Next.js para versão segura (>14.0.4)

---

## Bugs Conhecidos

| Bug | Status | Arquivo |
|-----|--------|---------|
| Terminal quebrando comandos multi-linha | Workaround: usar arquivos .py | N/A |

---

## Arquivos Modificados Recentemente

| Arquivo | Última Modificação | Descrição |
|---------|-------------------|-----------|
| `implementation/api_server.py` | 2026-01-16 | Endpoints /api/campaign/* |
| `socialfy-platform/hooks/useCampaigns.ts` | 2026-01-16 | Hook de campanhas |
| `socialfy-platform/views/CampaignsView.tsx` | 2026-01-16 | Modal nova campanha |
| `implementation/lead_scorer.py` | 2026-01-16 | Scoring multi-tenant |
| `implementation/instagram_dm_agent.py` | 2026-01-16 | tenant_id + sync_to_ghl |

---

## Notas de Sessão

**2026-01-16 (Noite):**
- ✅ Pipeline de Prospecção COMPLETO
- Arquivos criados/modificados:
  - `implementation/api_server.py`: Endpoints /api/campaign/start, /api/campaign/{id}, /api/campaigns, /api/campaign/{id}/stop
  - `socialfy-platform/hooks/useCampaigns.ts`: Hook completo com polling
  - `socialfy-platform/components/views/CampaignsView.tsx`: Modal de nova campanha, status badges, start/stop

**2026-01-16 (Tarde):**
- ✅ Integração Socialfy + Supabase COMPLETA
- ✅ Sistema de agentes especializados configurado
- ✅ Code review feito com 4 bugs críticos corrigidos
- Arquivos criados no Socialfy:
  - hooks/useLeads.ts, useTenants.ts, index.ts
  - components/leads/LeadCard.tsx, LeadFilters.tsx, PriorityBadge.tsx
  - components/views/LeadsView.tsx (reescrito)

**2026-01-16 (Manhã):**
- Scoring funcionando com dois tenants (DEFAULT, startup_abc)
- Mesmo lead: DEFAULT=45/COLD, startup_abc=55/WARM (provando multi-tenant)
- Frontend AgenticOS rodando em localhost:3001
