# Integração n8n: Detectar Origem da Conversa (Paliativo BDR Manual)

> **Data:** 2026-01-19
> **Endpoint:** `/api/detect-conversation-origin`
> **Propósito:** Detectar se conversa foi iniciada por BDR (outbound) ou Lead (inbound)

---

## Problema

O BDR está prospectando manualmente pelo Instagram, mas o AgenticOS ainda não está 100% integrado. Precisamos que o n8n consiga:

1. Identificar se a conversa foi iniciada pela empresa (BDR abordou) ou pelo lead (novo seguidor)
2. Marcar tags automaticamente para diferenciar
3. Ativar o agente `social_seller_instagram` com o contexto correto

---

## Solução

Novo endpoint que analisa a **primeira mensagem** da conversa no GHL:

- Se primeira msg foi **outbound** (empresa enviou) → BDR abordou → Tags: `outbound-instagram`, `bdr-abordou`
- Se primeira msg foi **inbound** (lead enviou) → Novo seguidor/orgânico → Tags: `novo-seguidor`, `inbound-organico`

---

## Fluxo no n8n

```
[Webhook GHL: Nova Mensagem]
         │
         ▼
[HTTP Request: /api/detect-conversation-origin]
         │
         ├─── origin = "outbound" ──▶ [Branch: BDR abordou]
         │                                   │
         │                                   ▼
         │                           [Contexto: prospecting_response]
         │                           [Tom: direto, dar continuidade]
         │
         └─── origin = "inbound" ───▶ [Branch: Novo seguidor]
                                             │
                                             ▼
                                     [Contexto: inbound_organic]
                                     [Tom: receptivo, qualificar]
         │
         ▼
[HTTP Request: /api/analyze-conversation-context]
         │
         ▼
[Ativar social_seller_instagram]
```

---

## Nó HTTP Request no n8n

### Configuração

```
Method: POST
URL: https://agenticoskevsacademy-production.up.railway.app/api/detect-conversation-origin

Headers:
  Content-Type: application/json

Body (JSON):
{
  "contact_id": "{{ $json.contact_id }}",
  "location_id": "{{ $json.location_id }}",
  "auto_tag": true,
  "channel_filter": "instagram"
}
```

### JSON do Nó (Importar no n8n)

```json
{
  "nodes": [
    {
      "parameters": {
        "method": "POST",
        "url": "https://agenticoskevsacademy-production.up.railway.app/api/detect-conversation-origin",
        "sendHeaders": true,
        "headerParameters": {
          "parameters": [
            {
              "name": "Content-Type",
              "value": "application/json"
            }
          ]
        },
        "sendBody": true,
        "bodyParameters": {
          "parameters": [
            {
              "name": "contact_id",
              "value": "={{ $json.contact_id }}"
            },
            {
              "name": "location_id",
              "value": "={{ $json.location_id }}"
            },
            {
              "name": "auto_tag",
              "value": "={{ true }}"
            },
            {
              "name": "channel_filter",
              "value": "instagram"
            }
          ]
        },
        "options": {}
      },
      "name": "Detectar Origem Conversa",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.1,
      "position": [450, 300]
    }
  ]
}
```

---

## Response do Endpoint

```json
{
  "origin": "outbound",
  "origin_label": "BDR/Empresa iniciou (prospecção)",
  "first_message_direction": "outbound",
  "first_message_date": "2026-01-19T10:30:00Z",
  "first_message_preview": "Oi! Vi que você trabalha com...",
  "conversation_id": "conv_abc123",
  "conversation_type": "instagram",
  "total_messages": 5,
  "tags_added": ["outbound-instagram", "bdr-abordou", "prospectado"],
  "contact_id": "contact_xyz",
  "agent_context": {
    "should_activate": true,
    "context_type": "prospecting_response",
    "source_channel": "instagram_dm",
    "recommendation": "Lead respondendo prospecção - ativar qualificação imediata"
  }
}
```

---

## Campos Importantes para o Fluxo

| Campo | Uso |
|-------|-----|
| `origin` | "outbound" ou "inbound" - usar no IF/Switch |
| `agent_context.context_type` | Passar para `/api/analyze-conversation-context` |
| `agent_context.recommendation` | Usar como contexto para o agente |
| `tags_added` | Confirmar que tags foram adicionadas |

---

## Exemplo de IF no n8n

```javascript
// Condição para branch "BDR Abordou"
{{ $json.origin === "outbound" }}

// Condição para branch "Novo Seguidor"
{{ $json.origin === "inbound" }}

// Condição para erro
{{ $json.origin === "unknown" }}
```

---

## Integração com analyze-conversation-context

Após detectar a origem, chame o endpoint de análise passando o contexto:

```json
{
  "contact_id": "{{ $json.contact_id }}",
  "location_id": "{{ $json.location_id }}",
  "current_message": "{{ $json.message_body }}",
  "contact_tags": {{ $json.tags_added }},
  "last_message_direction": "inbound",
  "conversation_count": {{ $json.total_messages }}
}
```

O `analyze-conversation-context` agora terá as tags corretas (`outbound-instagram` ou `novo-seguidor`) e vai decidir corretamente se ativa a IA.

---

## Troubleshooting

### origin = "unknown"

Possíveis causas:
1. `GHL_API_KEY` não configurada no Railway
2. Conversa não encontrada no GHL
3. Conversa sem mensagens

### Tags não adicionadas

Verificar:
1. `auto_tag: true` no request
2. Permissões da API key no GHL
3. Logs no Railway: `railway logs`

---

## Deploy

Após criar o endpoint, fazer deploy:

```bash
cd /Users/marcosdaniels/Projects/mottivme/ai-factory-mottivme-sales/socialfy-platform/AgenticOSKevsAcademy
git add .
git commit -m "feat: add /api/detect-conversation-origin endpoint (paliativo BDR manual)"
git push origin main
```

O Railway faz deploy automático.
