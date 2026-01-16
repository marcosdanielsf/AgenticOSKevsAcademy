# Spec: Integração Socialfy + Supabase

> **Criado em:** 2026-01-16
> **Status:** Planejamento
> **Owner:** @orchestrator

---

## Objetivo

Conectar o frontend **Socialfy Platform** ao **Supabase real** para exibir leads com scores do AgenticOS, permitindo filtragem por prioridade (HOT/WARM/COLD).

---

## Requisitos Funcionais

### RF01: Listar Leads com Scores
- Exibir lista de leads da tabela `agentic_instagram_leads`
- Mostrar: username, full_name, bio, followers, icp_score, priority
- Ordenar por score (maior primeiro)

### RF02: Filtrar por Prioridade
- Filtros: ALL, HOT (>=70), WARM (50-69), COLD (40-49), NURTURING (<40)
- Filtro persistente via URL query param

### RF03: Badges Visuais
- HOT: Badge vermelho/laranja
- WARM: Badge amarelo
- COLD: Badge azul
- NURTURING: Badge cinza

### RF04: Detalhes do Lead
- Clicar no lead abre modal/drawer com:
  - Perfil completo do Instagram
  - Breakdown do score (bio, engagement, profile, recency)
  - Histórico de DMs enviadas
  - Ações: Enviar DM, Adicionar nota, Marcar como convertido

### RF05: Integração com Tenant
- Selector de tenant no header
- Filtrar leads por tenant_id
- Mostrar config de ICP do tenant selecionado

---

## Arquitetura Técnica

```
┌─────────────────────────────────────────────────────────────────┐
│  SOCIALFY PLATFORM (React + Vite)                               │
│  ~/Projects/mottivme/socialfy-platform                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  hooks/                                                         │
│  ├── useLeads.ts          ← CRIAR: Fetch leads com scores      │
│  ├── useTenants.ts        ← CRIAR: Fetch tenants disponíveis   │
│  └── useSupabaseData.ts   ← MODIFICAR: Remover mock data       │
│                                                                 │
│  components/                                                    │
│  ├── LeadCard.tsx         ← CRIAR: Card com score badge        │
│  ├── LeadFilters.tsx      ← CRIAR: Filtros de prioridade       │
│  ├── LeadDetails.tsx      ← CRIAR: Modal de detalhes           │
│  └── TenantSelector.tsx   ← CRIAR: Dropdown de tenants         │
│                                                                 │
│  lib/                                                           │
│  └── supabase.ts          ← CRIAR: Cliente Supabase            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
          │
          │ Supabase Client
          ▼
┌─────────────────────────────────────────────────────────────────┐
│  SUPABASE (bfumywvwubvernvhjehk.supabase.co)                   │
├─────────────────────────────────────────────────────────────────┤
│  Tabelas:                                                       │
│  ├── agentic_instagram_leads    ← Leads com scores             │
│  ├── tenant_icp_config          ← Config de ICP                │
│  └── agentic_instagram_dm_sent  ← DMs enviadas                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tracks de Implementação

### Track 1: Setup Supabase (Backend Expert)
- [ ] Criar `lib/supabase.ts` com cliente configurado
- [ ] Configurar variáveis de ambiente
- [ ] Testar conexão

### Track 2: Hooks de Dados (Coder)
- [ ] Criar `useLeads.ts` com query otimizada
- [ ] Criar `useTenants.ts` para listar tenants
- [ ] Adicionar filtros e paginação

### Track 3: Componentes UI (UI Expert)
- [ ] Criar `LeadCard.tsx` com badges de prioridade
- [ ] Criar `LeadFilters.tsx` com chips de filtro
- [ ] Criar `TenantSelector.tsx` dropdown
- [ ] Criar `LeadDetails.tsx` modal

### Track 4: Integração na View (Coder)
- [ ] Modificar `App.tsx` ou view de Leads
- [ ] Conectar hooks aos componentes
- [ ] Adicionar loading/error states

### Track 5: Review e Polish (Reviewer + UI Expert)
- [ ] Code review de todos os arquivos
- [ ] Verificar responsividade
- [ ] Testar fluxo completo
- [ ] Fix bugs encontrados

---

## Dependências entre Tracks

```
Track 1 (Setup) ──┬──> Track 2 (Hooks) ──┬──> Track 4 (Integração)
                  │                      │
                  └──> Track 3 (UI) ─────┘
                                         │
                                         └──> Track 5 (Review)
```

**Paralelo:** Track 2 e Track 3 podem rodar em paralelo após Track 1.

---

## Variáveis de Ambiente Necessárias

```env
VITE_SUPABASE_URL=https://bfumywvwubvernvhjehk.supabase.co
VITE_SUPABASE_ANON_KEY=<anon_key_aqui>
```

---

## Critérios de Aceite

- [ ] Leads são listados com scores reais do Supabase
- [ ] Filtros funcionam corretamente
- [ ] Badges mostram prioridade correta
- [ ] Tenant selector funciona
- [ ] Loading states presentes
- [ ] Error handling implementado
- [ ] Mobile responsive
- [ ] Dark mode funcional
