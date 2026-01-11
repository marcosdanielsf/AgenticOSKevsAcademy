# PROMPTS: Páginas Adicionais do Growth OS

O Dashboard principal já está pronto. Agora crie as páginas do menu lateral.

## CONEXÃO SUPABASE (mesma)
```env
NEXT_PUBLIC_SUPABASE_URL=https://bfumywvwubvernvhjehk.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJmdW15d3Z3dWJ2ZXJudmhqZWhrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTE0MDM3OTksImV4cCI6MjA2Njk3OTc5OX0.60VyeZ8XaD6kz7Eh5Ov_nEeDtu5woMwMJYgUM-Sruao
```

---

## PÁGINA 1: LEADS (/leads)

### Funcionalidades:
- Tabela completa de leads com paginação
- Filtros: status, canal, temperatura, score, data
- Busca por nome/email/telefone
- Ordenação por colunas
- Ações: ver detalhes, editar, deletar

### Tabela: `growth_leads`

### Colunas da tabela:
| Coluna | Tipo | Descrição |
|--------|------|-----------|
| Nome | text | name |
| Email | text | email |
| Telefone | text | phone |
| Empresa | text | company |
| Canal | badge | source_channel |
| Etapa | badge colorido | funnel_stage |
| Temperatura | badge | lead_temperature (cold/warm/hot) |
| Score | progress bar | lead_score (0-100) |
| BANT | texto | bant_total_score/100 |
| Última atividade | data relativa | last_contact_at |
| Criado em | data | created_at |
| Ações | botões | ver, editar, deletar |

### Filtros:
```typescript
// Etapas do funil
const stages = ['prospected', 'lead', 'qualified', 'scheduled', 'showed', 'no_show', 'proposal', 'won', 'lost'];

// Canais
const channels = ['instagram_dm', 'cold_email', 'cold_call', 'inbound_call', 'linkedin', 'referral', 'whatsapp', 'ads'];

// Temperatura
const temperatures = ['cold', 'warm', 'hot'];
```

### Modal de Detalhes do Lead:
- Dados básicos (nome, email, telefone, empresa)
- Scores BANT individuais (budget, authority, need, timeline)
- Timeline de atividades
- Histórico de etapas
- Agendamentos
- Notas

### Query:
```typescript
const { data, count } = await supabase
  .from('growth_leads')
  .select('*', { count: 'exact' })
  .eq('location_id', selectedLocation)
  .order('created_at', { ascending: false })
  .range(page * pageSize, (page + 1) * pageSize - 1);
```

---

## PÁGINA 2: CAMPANHAS (/campanhas)

### Funcionalidades:
- Lista de campanhas ativas
- Métricas por campanha
- Criar nova campanha
- Editar/pausar campanhas

### Estrutura de Campanha:
```typescript
interface Campaign {
  id: string;
  name: string;
  channel: string;           // 'instagram', 'email', 'linkedin'
  status: 'active' | 'paused' | 'completed';
  start_date: string;
  end_date?: string;
  target_audience: string;
  agent_code: string;        // Agente responsável
  // Métricas
  total_prospected: number;
  total_leads: number;
  total_conversions: number;
  conversion_rate: number;
  cost: number;
  revenue: number;
  roi: number;
}
```

### Cards de Campanha:
- Nome da campanha
- Canal (ícone)
- Status (badge)
- Período
- Métricas principais (leads, conversão, ROI)
- Agente responsável
- Ações (editar, pausar, ver detalhes)

### Criar Campanha (Modal):
- Nome
- Canal
- Data início/fim
- Público-alvo
- Agente responsável
- Orçamento

---

## PÁGINA 3: AGENTES IA (/agentes)

### Funcionalidades:
- Grid de cards dos 19 agentes
- Status de cada agente (ativo/inativo)
- Métricas de performance
- Configuração por agente
- Logs de conversas

### Tabelas:
- `growth_agent_templates` - Templates base
- `growth_client_agents` - Instâncias por cliente
- `growth_agent_metrics` - Métricas diárias

### Card do Agente:
```
┌─────────────────────────────────────┐
│ 🤖 Julia (Social Seller Instagram)  │
│ SSIG-DRLUIZ-001                     │
│ ────────────────────────────────── │
│ Status: ● Ativo                     │
│                                     │
│ Conversas hoje:     45              │
│ Taxa de qualificação: 32%           │
│ Meetings agendados:  8              │
│ Tempo resposta:      45s            │
│                                     │
│ [Ver Logs] [Configurar] [Pausar]    │
└─────────────────────────────────────┘
```

### Categorias de Agentes:
1. **Prospecção Ativa** (4 agentes)
   - Prospector, Reactivator, Referral Generator, Cold Emailer

2. **Social Selling** (2 agentes)
   - Social Seller Instagram, Social Seller LinkedIn

3. **Inbound** (2 agentes)
   - SDR Inbound, Inbound Caller

4. **Outbound** (2 agentes)
   - SDR Outbound, Cold Caller

5. **Conversão** (4 agentes)
   - Objection Handler, Scheduler, Concierge, Closer

6. **Gestão** (5 agentes)
   - Outbound Manager, Inbound Manager, Closing Manager, Sales Ops, Sales Director

### Queries:
```typescript
// Agentes do cliente
const { data: agents } = await supabase
  .from('growth_client_agents')
  .select(`
    *,
    template:growth_agent_templates(*)
  `)
  .eq('location_id', selectedLocation);

// Métricas do agente
const { data: metrics } = await supabase
  .from('growth_agent_metrics')
  .select('*')
  .eq('location_id', selectedLocation)
  .eq('agent_code', agentCode)
  .gte('date', startDate);
```

### Modal de Configuração do Agente:
- Nome personalizado
- Prompt customizado (readonly, mostrar compilado)
- Horários de funcionamento
- Canais ativos
- Limites (max mensagens/dia)
- Ativar/Desativar

### Modal de Logs:
- Lista de conversas do agente
- Filtro por data, resultado
- Ver conversa completa
- Exportar logs

---

## PÁGINA 4: AJUSTES (/ajustes)

### Seções:

#### 4.1 Dados do Cliente
```typescript
// Tabela: growth_client_configs
- nome_empresa
- tipo_negocio
- oferta_principal
- dor_principal
- publico_alvo
- diferenciais[]
```

#### 4.2 Configuração de Preços
```typescript
- faixa_preco_texto
- mostrar_preco (boolean)
- ticket_medio
```

#### 4.3 Personalidade do Agente
```typescript
- tom_agente ('consultivo', 'direto', 'amigavel')
- nome_agente
- emoji_por_mensagem (0-3)
```

#### 4.4 Horários
```typescript
- horario_inicio
- horario_fim
- timezone
- canais_ativos[]
```

#### 4.5 Qualificação
```typescript
- perguntas_qualificacao (JSONB)
  - budget
  - authority
  - need
  - timeline
```

#### 4.6 Agendamento
```typescript
- calendario_url
- tempo_consulta_minutos
```

#### 4.7 Follow-up
```typescript
- max_followups
- intervalo_followup_horas
```

#### 4.8 Escalação
```typescript
- telefone_humano
- email_humano
- gatilhos_escalacao[]
```

#### 4.9 Metas
```typescript
- meta_leads_mes
- meta_agendamentos_mes
- meta_vendas_mes
- meta_receita_mes
```

### Layout:
- Formulário em seções colapsáveis
- Salvar automático ou botão salvar
- Validação de campos
- Preview das mudanças

---

## COMPONENTES COMPARTILHADOS

### Badge de Status/Etapa:
```typescript
const stageBadgeColors = {
  prospected: 'bg-slate-100 text-slate-700',
  lead: 'bg-blue-100 text-blue-700',
  qualified: 'bg-violet-100 text-violet-700',
  scheduled: 'bg-pink-100 text-pink-700',
  showed: 'bg-orange-100 text-orange-700',
  no_show: 'bg-red-100 text-red-700',
  proposal: 'bg-yellow-100 text-yellow-700',
  won: 'bg-green-100 text-green-700',
  lost: 'bg-red-100 text-red-700',
};
```

### Badge de Temperatura:
```typescript
const tempBadgeColors = {
  cold: 'bg-blue-100 text-blue-700',
  warm: 'bg-orange-100 text-orange-700',
  hot: 'bg-red-100 text-red-700',
};
```

### Badge de Canal:
```typescript
const channelIcons = {
  instagram_dm: '📷',
  cold_email: '📧',
  cold_call: '📞',
  linkedin: '💼',
  whatsapp: '💬',
  referral: '🤝',
  ads: '📢',
};
```

---

## ORDEM DE PRIORIDADE

1. **Leads** - Mais importante, gestão direta
2. **Agentes IA** - Configuração e monitoramento
3. **Ajustes** - Configuração do cliente
4. **Campanhas** - Pode ser v2

---

## ESTILO

Manter o mesmo estilo do Dashboard:
- Clean, minimalista
- Cores consistentes
- shadcn/ui components
- Responsivo
- Loading states
- Empty states

---

**DICA**: Comece pela página de Leads que é a mais usada!
