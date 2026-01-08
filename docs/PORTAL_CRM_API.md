# Portal CRM API - MOTTIVME Sales

## Visão Geral

APIs para o Portal CRM Multi-Tenant, permitindo que cada cliente veja seu dashboard personalizado com funil de vendas, leads e conversas.

**Base URL:** `https://agenticoskevsacademy-production.up.railway.app`

---

## Endpoints de Sincronização (n8n → Supabase)

### POST `/api/portal/sync/lead`

Sincroniza um lead do GHL para o Supabase. Chamado pelo n8n quando um contato é criado/atualizado.

**Request:**
```json
{
  "ghl_contact_id": "abc123",
  "location_id": "loc_xyz",
  "name": "Maria Silva",
  "email": "maria@email.com",
  "phone": "+5511999999999",
  "instagram_username": "mariasilva",
  "source_channel": "instagram_dm",
  "source_campaign": "campanha_janeiro",
  "funnel_stage": "lead",
  "lead_temperature": "warm",
  "lead_score": 75,
  "tags": ["interessado", "premium"],
  "custom_fields": {}
}
```

**Response:**
```json
{
  "success": true,
  "action": "created",
  "lead_id": "uuid-do-lead",
  "ghl_contact_id": "abc123"
}
```

---

### POST `/api/portal/sync/message`

Sincroniza uma mensagem do GHL. Cria conversa se não existir.

**Request:**
```json
{
  "ghl_conversation_id": "conv_123",
  "ghl_message_id": "msg_456",
  "location_id": "loc_xyz",
  "ghl_contact_id": "abc123",
  "content": "Olá, quero saber mais!",
  "direction": "inbound",
  "channel": "instagram",
  "sent_at": "2026-01-08T10:30:00Z",
  "sender_name": "Maria Silva",
  "is_from_ai": false,
  "content_type": "text"
}
```

**Response:**
```json
{
  "success": true,
  "action": "created",
  "conversation_id": "uuid-conversa",
  "message_id": "uuid-mensagem"
}
```

---

### POST `/api/portal/sync/metrics`

Calcula métricas diárias para um tenant. Chamado via cron.

**Request:**
```json
{
  "location_id": "loc_xyz",
  "date": "2026-01-08"
}
```

**Response:**
```json
{
  "success": true,
  "location_id": "loc_xyz",
  "date": "2026-01-08",
  "funnel": {
    "prospected": 85,
    "lead": 42,
    "qualified": 28,
    "scheduled": 15,
    "showed": 12,
    "no_show": 3,
    "proposal": 8,
    "won": 5,
    "lost": 2
  },
  "breakdown": {
    "outbound": {"prospected": 85, "leads": 14},
    "inbound": {"leads": 28}
  },
  "rates": {
    "lead_rate": 49.41,
    "qualification_rate": 66.67,
    "show_rate": 80.0,
    "closing_rate": 62.5
  },
  "revenue": 25000
}
```

---

## Endpoints do Dashboard

### GET `/api/portal/dashboard/summary`

Resumo do dashboard com KPIs principais.

**Query Params:**
| Param | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| location_id | string | Sim | ID do tenant |
| period | string | Não | 7d, 30d, 90d (default: 30d) |

**Response:**
```json
{
  "success": true,
  "data": {
    "kpis": {
      "prospected": 85,
      "leads": 42,
      "qualified": 28,
      "scheduled": 15,
      "showed": 12,
      "won": 5,
      "lost": 2
    },
    "breakdown": {
      "outbound": 14,
      "inbound": 28
    },
    "revenue": {
      "total": 25000,
      "avg_ticket": 5000
    }
  },
  "period": {
    "days": 30,
    "start": "2025-12-09",
    "end": "2026-01-08"
  }
}
```

---

### GET `/api/portal/dashboard/funnel`

Dados do funil de vendas com taxas de conversão.

**Query Params:**
| Param | Tipo | Descrição |
|-------|------|-----------|
| location_id | string | ID do tenant |
| period | string | 7d, 30d, 90d |
| source_type | string | outbound, inbound (opcional) |

---

## Endpoints de Leads

### GET `/api/portal/leads`

Lista leads com paginação e filtros.

**Query Params:**
| Param | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| location_id | string | - | ID do tenant (obrigatório) |
| page | int | 1 | Página atual |
| limit | int | 20 | Itens por página (max: 100) |
| stage | string | null | Filtro por etapa |
| source_type | string | null | outbound ou inbound |
| search | string | null | Busca por nome/email |

**Stages válidos:**
- `prospected` - Prospecção
- `lead` - Lead novo
- `qualified` - Qualificado
- `scheduled` - Agendado
- `showed` - Compareceu
- `no_show` - No-show
- `proposal` - Proposta
- `won` - Fechado
- `lost` - Perdido

**Response:**
```json
{
  "success": true,
  "data": {
    "leads": [
      {
        "id": "uuid",
        "name": "Maria Silva",
        "email": "maria@email.com",
        "phone": "+5511999999999",
        "instagram": "mariasilva",
        "source_channel": "instagram_dm",
        "source_type": "outbound",
        "funnel_stage": "qualified",
        "lead_temperature": "hot",
        "lead_score": 85,
        "created_at": "2026-01-05T10:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 42,
      "pages": 3
    }
  }
}
```

---

### GET `/api/portal/leads/{lead_id}`

Detalhes completos de um lead.

**Query Params:**
| Param | Tipo | Descrição |
|-------|------|-----------|
| location_id | string | ID do tenant |

**Response:**
```json
{
  "success": true,
  "data": {
    "lead": {
      "id": "uuid",
      "name": "Maria Silva",
      "email": "maria@email.com",
      "source_channel": "instagram_dm",
      "source_type": "outbound",
      "funnel_stage": "qualified",
      "lead_temperature": "hot",
      "bant_total_score": 75,
      "last_contact_at": "2026-01-07T15:30:00Z"
    },
    "conversations": [
      {
        "id": "uuid",
        "channel": "instagram",
        "last_message": "Vamos agendar...",
        "total_messages": 12
      }
    ],
    "activities": [
      {
        "activity_type": "message",
        "channel": "instagram",
        "direction": "outbound",
        "performed_at": "2026-01-07T15:30:00Z"
      }
    ]
  }
}
```

---

## Endpoints de Conversas

### GET `/api/portal/conversations`

Lista conversas do tenant.

**Query Params:**
| Param | Tipo | Descrição |
|-------|------|-----------|
| location_id | string | ID do tenant |
| page | int | Página atual |
| limit | int | Itens por página |
| channel | string | instagram, whatsapp, sms, email |
| status | string | open, closed |

---

### GET `/api/portal/conversations/{conversation_id}/messages`

Mensagens de uma conversa.

**Query Params:**
| Param | Tipo | Descrição |
|-------|------|-----------|
| location_id | string | ID do tenant |
| limit | int | Máximo de mensagens (default: 50) |

**Response:**
```json
{
  "success": true,
  "data": {
    "messages": [
      {
        "id": "uuid",
        "content": "Olá!",
        "direction": "inbound",
        "sender_type": "lead",
        "is_from_ai": false,
        "sent_at": "2026-01-07T10:00:00Z"
      },
      {
        "id": "uuid",
        "content": "Oi! Como posso ajudar?",
        "direction": "outbound",
        "sender_type": "ai",
        "is_from_ai": true,
        "sent_at": "2026-01-07T10:01:00Z"
      }
    ]
  }
}
```

---

## Endpoints de Tenant

### POST `/api/portal/tenant/ensure`

Garante que um tenant existe. Cria se necessário.

**Query Params:**
| Param | Tipo | Descrição |
|-------|------|-----------|
| location_id | string | ID do GHL |
| client_name | string | Nome do cliente (opcional) |

**Response:**
```json
{
  "success": true,
  "action": "created",
  "tenant": {
    "id": "uuid",
    "location_id": "loc_xyz",
    "client_name": "Dr. Luiz",
    "status": "active"
  }
}
```

---

## Source Channels

### Outbound (Social Selling)
| Channel | Descrição |
|---------|-----------|
| `instagram_dm` | DM do Instagram |
| `linkedin` | LinkedIn |
| `cold_email` | Email frio |
| `cold_call` | Ligação fria |

### Inbound (Tráfego + Orgânico)
| Channel | Descrição |
|---------|-----------|
| `ads` | Facebook/Instagram Ads |
| `facebook_ads` | Facebook Ads específico |
| `instagram_ads` | Instagram Ads específico |
| `google_ads` | Google Ads |
| `whatsapp` | WhatsApp direto |
| `referral` | Indicação |
| `organic` | Orgânico |
| `inbound_call` | Ligação recebida |

---

## Integração n8n

### Workflow: Portal Sync Lead

```
[Webhook GHL: Contact Created/Updated]
    ↓
[HTTP Request]
POST /api/portal/sync/lead
Body: {
  ghl_contact_id: {{$json.contact_id}},
  location_id: {{$json.location_id}},
  name: {{$json.full_name}},
  email: {{$json.email}},
  phone: {{$json.phone}},
  source_channel: {{$json.source}},
  funnel_stage: {{$json.pipeline_stage}},
  lead_temperature: {{$json.tags_temperature}},
  tags: {{$json.tags}}
}
```

### Workflow: Portal Sync Message

```
[Webhook GHL: Message Received]
    ↓
[HTTP Request]
POST /api/portal/sync/message
Body: {
  ghl_conversation_id: {{$json.conversation_id}},
  ghl_message_id: {{$json.message_id}},
  location_id: {{$json.location_id}},
  ghl_contact_id: {{$json.contact_id}},
  content: {{$json.body}},
  direction: {{$json.direction}},
  channel: {{$json.type}},
  sent_at: {{$json.date_created}}
}
```

### Workflow: Daily Metrics (Cron 23:59)

```
[Cron: 23:59 daily]
    ↓
[Loop: Para cada location_id ativo]
    ↓
[HTTP Request]
POST /api/portal/sync/metrics
Body: {
  location_id: {{$json.location_id}},
  date: {{$today}}
}
```

---

## Tabelas Supabase

| Tabela | Propósito |
|--------|-----------|
| `growth_leads` | Leads do sistema (Growth OS) |
| `growth_client_configs` | Configuração dos tenants |
| `growth_funnel_daily` | Métricas do funil por dia |
| `portal_users` | Usuários do portal |
| `portal_conversations` | Conversas sincronizadas |
| `portal_messages` | Mensagens das conversas |
| `portal_metrics_daily` | Métricas com breakdown outbound/inbound |

---

## RLS (Row Level Security)

Todas as tabelas do portal têm RLS ativado:
- Usuários só veem dados do seu `location_id`
- Service role bypassa RLS (para sync via n8n)
- Admins podem ver logs de auditoria

---

## Erros Comuns

| Código | Erro | Causa |
|--------|------|-------|
| 503 | Portal service not available | Módulo portal_service não carregado |
| 404 | Lead not found | Lead não existe ou não pertence ao tenant |
| 404 | Conversation not found | Conversa não existe ou não pertence ao tenant |
| 500 | Internal server error | Erro no Supabase ou processamento |
