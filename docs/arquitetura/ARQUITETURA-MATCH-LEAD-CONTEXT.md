# ARQUITETURA: Endpoint /api/match-lead-context

**Data:** 2026-01-03
**Projeto:** MOTTIVME UNIFIED AI SYSTEM - FASE 0

---

## PROBLEMA RESOLVIDO

Quando lead responde no GHL (via webhook n8n), precisa saber:
1. Esse lead já foi prospectado pelo AgenticOS?
2. Se sim, quais dados enriquecidos temos (cargo, empresa, ICP)?
3. Qual foi o contexto da prospecção inicial?
4. Histórico de conversas anteriores?

---

## SOLUÇÃO: Um único endpoint que faz tudo

```
POST /api/match-lead-context
Body: { phone, email, ig_id, ghl_contact_id, location_id }
```

---

## RESPOSTA QUANDO ENCONTRA (já prospectado):

```json
{
  "matched": true,
  "source": "agenticos_prospecting",
  "lead_data": {
    "id": "uuid-123",
    "name": "Thiago Souza",
    "cargo": "CEO",
    "empresa": "TechBrasil",
    "setor": "Tecnologia",
    "porte": "PME",
    "icp_score": 85,
    "icp_tier": "HOT",
    "ig_followers": 12500,
    "ig_engagement": 3.2,
    "ig_bio": "Empreendedor | Investidor | Pai de 2"
  },
  "prospecting_context": {
    "was_prospected": true,
    "prospected_at": "2026-01-02T15:30:00Z",
    "outreach_message": "Oi Thiago! Vi que você é CEO da TechBrasil...",
    "outreach_channel": "instagram_dm"
  },
  "conversation_history": [
    {"role": "assistant", "content": "Oi Thiago! Vi que você é CEO...", "at": "2026-01-02T15:30:00Z"},
    {"role": "user", "content": "Oi! Interessante, me conta mais", "at": "2026-01-02T18:45:00Z"}
  ],
  "placeholders": {
    "{{nome}}": "Thiago",
    "{{cargo}}": "CEO",
    "{{empresa}}": "TechBrasil",
    "{{setor}}": "Tecnologia",
    "{{icp_score}}": "85",
    "{{icp_tier}}": "HOT",
    "{{contexto_prospeccao}}": "Lead prospectado em 02/01 via Instagram DM. Mensagem inicial foi sobre sua atuação como CEO da TechBrasil. Demonstrou interesse inicial."
  }
}
```

---

## RESPOSTA QUANDO NÃO ENCONTRA (lead novo):

```json
{
  "matched": false,
  "source": "unknown",
  "lead_data": null,
  "action_required": "scrape_profile",
  "scrape_target": {
    "ig_id": "1387060326464505",
    "phone": "+17745031765"
  }
}
```

---

## FLUXO NO N8N

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Webhook GHL recebe mensagem                              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. HTTP Request → POST /api/match-lead-context              │
│    Body: { phone, email, ig_id, ghl_contact_id }            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. IF matched == true                                       │
│    → Usa placeholders prontos no prompt                     │
│    → Adiciona conversation_history ao contexto              │
│    → Chama LLM                                              │
│                                                             │
│    ELSE                                                     │
│    → Ativa fluxo de scrape (Instagram API)                  │
│    → Busca bio, followers, posts recentes                   │
│    → Olha histórico de DMs no IG                            │
│    → Salva no AgenticOS                                     │
│    → Chama LLM com dados frescos                            │
└─────────────────────────────────────────────────────────────┘
```

---

## IDENTIFICADORES USADOS PARA MATCH

Ordem de prioridade:
1. `ghl_contact_id` - match direto se já sincronizado
2. `phone` - normalizado para formato internacional
3. `email` - lowercase, trimmed
4. `ig_id` - Instagram Session ID do attributionSource

---

## TABELAS SUPABASE ENVOLVIDAS

| Tabela | Uso |
|--------|-----|
| `socialfy_leads` | Dados principais do lead |
| `crm_leads` | Fallback para leads antigos |
| `enriched_lead_data` | Dados enriquecidos (cargo, empresa, setor) |
| `integration_sync_log` | Histórico de sincronizações |
| `agent_conversations` | Histórico de mensagens |

---

## EXEMPLO DE WEBHOOK GHL (input do n8n)

```json
{
  "body": {
    "contact_id": "ciKwCEauv8v5e2t5zAWk",
    "first_name": "Thiago",
    "phone": "+17745031765",
    "email": "souza0323@live.com",
    "location": {
      "id": "EKHxHl3KLPN0iRc69GNU"
    },
    "contact": {
      "attributionSource": {
        "igSid": "1387060326464505",
        "medium": "instagram"
      }
    },
    "message": {
      "body": "Mensagem do lead aqui"
    }
  }
}
```

---

## PRÓXIMOS PASSOS

1. [ ] Implementar endpoint `/api/match-lead-context`
2. [ ] Implementar busca por múltiplos identificadores
3. [ ] Adicionar busca de histórico de conversas
4. [ ] Testar integração com webhook GHL real
5. [ ] Configurar no n8n o HTTP Request node
