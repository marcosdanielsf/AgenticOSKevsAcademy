# PROMPT: Dashboard Growth OS

## CONTEXTO

Você vai criar um dashboard de vendas para o **Growth OS** - um sistema de automação de vendas com 19 agentes de IA. O dashboard deve ser moderno, responsivo e conectar ao Supabase.

## STACK OBRIGATÓRIA

- **Framework**: Next.js 14+ (App Router)
- **UI**: Tailwind CSS + shadcn/ui
- **Gráficos**: Recharts ou Tremor
- **Database**: Supabase (PostgreSQL)
- **Auth**: Supabase Auth (opcional na v1)

## CONEXÃO SUPABASE

```env
NEXT_PUBLIC_SUPABASE_URL=https://bfumywvwubvernvhjehk.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJmdW15d3Z3dWJ2ZXJudmhqZWhrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTE0MDM3OTksImV4cCI6MjA2Njk3OTc5OX0.60VyeZ8XaD6kz7Eh5Ov_nEeDtu5woMwMJYgUM-Sruao
```

## TABELAS DISPONÍVEIS

### Principais para Dashboard:

```sql
-- Funil diário agregado (USAR ESTA PARA MÉTRICAS)
growth_funnel_daily (
    date, location_id, source_channel, agent_code, funnel_name,
    prospected_count, lead_count, qualified_count, scheduled_count,
    showed_count, no_show_count, proposal_count, won_count, lost_count,
    lead_rate, qualification_rate, scheduling_rate, show_rate, closing_rate,
    total_conversion_rate, total_proposal_value, total_won_value, avg_ticket,
    cost_spent, cpl, cpa, roi_percentage
)

-- Leads individuais
growth_leads (
    id, location_id, name, email, phone, company,
    source_channel, funnel_stage, lead_temperature,
    bant_budget_score, bant_authority_score, bant_need_score, bant_timeline_score,
    bant_total_score, lead_score, meeting_scheduled_at, proposal_value,
    converted_at, conversion_value, lost_reason
)

-- Métricas por agente
growth_agent_metrics (
    date, location_id, agent_code,
    conversations_started, messages_sent, messages_received,
    leads_qualified, meetings_booked, deals_closed,
    avg_response_time_seconds, escalations_to_human
)

-- Configuração do cliente
growth_client_configs (
    location_id, client_name, nome_empresa, tipo_negocio,
    meta_leads_mes, meta_agendamentos_mes, meta_vendas_mes, meta_receita_mes
)
```

### Views prontas:

```sql
-- Funil por cliente com taxas
growth_vw_funnel_by_client

-- Funil global agregado
growth_vw_funnel_global

-- Performance por agente
growth_vw_agent_performance

-- Funil por canal
growth_vw_funnel_by_channel
```

## LAYOUT DO DASHBOARD

### Header
- Logo "Growth OS"
- Seletor de Cliente (dropdown com location_id)
- Seletor de Período (7d, 30d, 90d, custom)
- Botão refresh

### Seção 1: KPIs Principais (Cards)
4 cards em linha:
1. **Leads Gerados** - lead_count com variação vs período anterior
2. **Taxa de Conversão** - total_conversion_rate %
3. **Receita** - total_won_value formatado em R$
4. **ROI** - roi_percentage %

### Seção 2: Funil de Vendas (Gráfico)
Gráfico de funil horizontal mostrando:
```
Prospecção → Leads → Qualificados → Agendados → Compareceram → Proposta → Ganhos
    100        80        50            30           25           20        15
```
Com taxas de conversão entre cada etapa.

### Seção 3: Gráficos em Grid (2 colunas)

**Coluna 1:**
- Gráfico de linha: Leads por dia (últimos 30 dias)
- Gráfico de pizza: Leads por Canal (source_channel)

**Coluna 2:**
- Gráfico de barras: Performance por Agente
- Gráfico de linha: Receita por dia

### Seção 4: Tabela de Leads Recentes
Tabela com:
- Nome, Email, Telefone
- Canal de origem
- Etapa do funil (com badge colorido)
- Score (barra de progresso)
- Data
- Ações (ver, editar)

### Seção 5: Performance dos Agentes
Cards para cada agente mostrando:
- Nome do agente
- Conversas iniciadas
- Taxa de qualificação
- Meetings agendados
- Tempo médio de resposta

## CORES E ESTILO

```css
/* Cores do funil */
--prospected: #94a3b8;  /* slate */
--lead: #60a5fa;        /* blue */
--qualified: #a78bfa;   /* violet */
--scheduled: #f472b6;   /* pink */
--showed: #fb923c;      /* orange */
--proposal: #facc15;    /* yellow */
--won: #4ade80;         /* green */
--lost: #f87171;        /* red */

/* Temperatura do lead */
--cold: #60a5fa;
--warm: #fb923c;
--hot: #ef4444;
```

## QUERIES EXEMPLO

### KPIs do período:
```typescript
const { data } = await supabase
  .from('growth_funnel_daily')
  .select('*')
  .eq('location_id', selectedLocation)
  .gte('date', startDate)
  .lte('date', endDate)
  .is('source_channel', null)
  .is('agent_code', null);
```

### Leads recentes:
```typescript
const { data } = await supabase
  .from('growth_leads')
  .select('*')
  .eq('location_id', selectedLocation)
  .order('created_at', { ascending: false })
  .limit(20);
```

### Performance por agente:
```typescript
const { data } = await supabase
  .from('growth_vw_agent_performance')
  .select('*');
```

## COMPONENTES NECESSÁRIOS

1. `DashboardLayout` - Layout principal com sidebar
2. `KPICard` - Card de métrica com ícone, valor e variação
3. `FunnelChart` - Gráfico de funil horizontal
4. `LineChart` - Gráfico de linha temporal
5. `BarChart` - Gráfico de barras comparativo
6. `PieChart` - Gráfico de pizza para distribuição
7. `LeadsTable` - Tabela de leads com paginação
8. `AgentCard` - Card de performance do agente
9. `DateRangePicker` - Seletor de período
10. `ClientSelector` - Dropdown de clientes

## ESTRUTURA DE PASTAS

```
app/
├── dashboard/
│   ├── page.tsx              # Dashboard principal
│   ├── leads/
│   │   └── page.tsx          # Lista de leads
│   ├── agents/
│   │   └── page.tsx          # Performance agentes
│   └── settings/
│       └── page.tsx          # Configurações
├── layout.tsx
└── globals.css

components/
├── dashboard/
│   ├── kpi-card.tsx
│   ├── funnel-chart.tsx
│   ├── leads-table.tsx
│   └── agent-card.tsx
├── charts/
│   ├── line-chart.tsx
│   ├── bar-chart.tsx
│   └── pie-chart.tsx
└── ui/
    └── [shadcn components]

lib/
├── supabase.ts               # Cliente Supabase
├── queries.ts                # Queries reutilizáveis
└── utils.ts                  # Formatadores
```

## FUNCIONALIDADES OBRIGATÓRIAS

1. ✅ Filtro por cliente (location_id)
2. ✅ Filtro por período
3. ✅ Atualização em tempo real (ou botão refresh)
4. ✅ Responsivo (mobile-first)
5. ✅ Loading states (skeletons)
6. ✅ Empty states
7. ✅ Formatação brasileira (R$, datas dd/mm/yyyy)

## DADOS DE EXEMPLO

Para desenvolvimento, criar dados mock ou inserir dados de teste:

```sql
-- Inserir dados de exemplo no funil
INSERT INTO growth_funnel_daily (
    date, location_id, funnel_name,
    prospected_count, lead_count, qualified_count, scheduled_count,
    showed_count, proposal_count, won_count, lost_count,
    total_won_value, cost_spent
) VALUES
    ('2026-01-01', 'dr_luiz_location_001', 'principal', 100, 80, 50, 30, 25, 20, 15, 5, 12000.00, 1500.00),
    ('2026-01-02', 'dr_luiz_location_001', 'principal', 120, 95, 60, 35, 28, 22, 18, 4, 14400.00, 1800.00),
    ('2026-01-03', 'dr_luiz_location_001', 'principal', 90, 70, 45, 28, 22, 18, 12, 6, 9600.00, 1350.00),
    ('2026-01-04', 'dr_luiz_location_001', 'principal', 110, 88, 55, 32, 26, 21, 16, 5, 12800.00, 1650.00);
```

## ENTREGA ESPERADA

1. Projeto Next.js funcional
2. Conectado ao Supabase
3. Dashboard com todas as seções
4. Código limpo e componentizado
5. README com instruções de deploy

## REFERÊNCIA VISUAL

Estilo similar ao:
- Vercel Analytics
- Stripe Dashboard
- Linear App

Clean, minimalista, dark mode opcional.

---

**IMPORTANTE**: Comece pelo MVP - KPIs + Funil + Tabela de Leads. Depois adicione os gráficos e features extras.
