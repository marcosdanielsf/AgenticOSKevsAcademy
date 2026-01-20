# Instruções para Atualizar o Workflow n8n

> **Data:** 2026-01-20
> **Problema:** IA de qualificação não recebe contexto do perfil do lead
> **Solução:** Passar bio, especialidade e origem da conversa para o endpoint

---

## O Que Foi Alterado no Backend

### 1. Novo Modelo de Request (`api_server.py`)

O endpoint `/webhook/classify-lead` agora aceita dois novos campos opcionais:

```python
class ClassifyLeadRequest(BaseModel):
    username: str
    message: str
    tenant_id: str
    persona_id: Optional[str] = None

    # NOVOS CAMPOS
    profile_context: Optional[LeadProfileContext] = None
    origin_context: Optional[ConversationOriginContext] = None
```

### 2. Prompt Atualizado

O prompt do Gemini agora:
- Usa a **bio do perfil** para entender melhor o lead
- Considera a **origem da conversa** (outbound vs inbound)
- Personaliza a sugestão de resposta com base no contexto
- Evita introduções genéricas como "Alberto Correia por aqui"

---

## Como Atualizar o n8n

### Passo 1: Abrir o Workflow

1. Acesse: https://cliente-a1.mentorfy.io
2. Abra o workflow "Agente Administrativo - Versionado"
3. Localize o nó **"Classificar Lead IA"**

### Passo 2: Substituir o JSON Body

No nó "Classificar Lead IA", substitua o campo `jsonBody` pelo seguinte:

```json
{
  "username": "{{ $('Info').first().json.first_name || 'lead' }}",
  "message": "{{ $('Mensagem recebida').first().json.body?.message?.body || $('Mensagem recebida').first().json.body?.lastMessage?.body || '' }}",
  "tenant_id": "{{ $('Info').first().json.location_id || 'default' }}",

  "profile_context": {
    "bio": "{{ $('Auto Enrich Lead').first().json.lead_data?.bio || $('Auto Enrich Lead').first().json.bio || '' }}",
    "especialidade": "{{ $('Auto Enrich Lead').first().json.lead_data?.detected_specialty || $('Auto Enrich Lead').first().json.profile_analysis?.specialty || '' }}",
    "followers": {{ $('Auto Enrich Lead').first().json.lead_data?.followers_count || $('Auto Enrich Lead').first().json.followers_count || 0 }},
    "is_verified": {{ $('Auto Enrich Lead').first().json.lead_data?.is_verified || false }},
    "source_channel": "{{ $('Info').first().json.source || 'instagram' }}"
  },

  "origin_context": {
    "origem": "{{ $json.origem_conversa || $('Info').first().json.origem_conversa || '' }}",
    "context_type": "{{ $json.context_type || $('Info').first().json.context_type || '' }}",
    "tom_agente": "{{ $json.tom_agente || $('Info').first().json.tom_agente || '' }}",
    "mensagem_abordagem": ""
  },

  "context": {
    "source": "{{ $('Mensagem recebida').first().json.body?.contact?.attributionSource?.medium || $('Mensagem recebida').first().json.body?.contact_source || 'unknown' }}",
    "phone": "{{ $('Info').first().json.telefone || $('Mensagem recebida').first().json.body?.phone || '' }}",
    "email": "{{ $('Info').first().json.email || '' }}",
    "tags": "{{ $('Mensagem recebida').first().json.body?.tags || '' }}"
  }
}
```

### Passo 3: Verificar Conexões

Certifique-se de que o fluxo está assim:

```
Auto Enrich Lead ─────► Classificar Lead IA
                            │
                            │ (precisa ter acesso aos dados
                            │  do Auto Enrich Lead)
```

Se o nó "Classificar Lead IA" não tiver acesso direto aos dados do "Auto Enrich Lead", use um **Merge** ou **Set** intermediário para consolidar os dados.

### Passo 4: Salvar e Testar

1. Salvar o workflow
2. Testar com um lead real (enviar mensagem para a sub-conta)
3. Verificar nos logs se o `profile_context` está sendo enviado corretamente

---

## Verificação Pós-Deploy

### Testar via cURL

```bash
curl -X POST "https://agenticoskevsacademy-production.up.railway.app/webhook/classify-lead" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "lead_teste",
    "message": "Oi, vi seu conteúdo e quero saber mais",
    "tenant_id": "location_123",
    "profile_context": {
      "bio": "Dermatologista | Especialista em pele | São Paulo",
      "especialidade": "Dermatologista",
      "followers": 15000,
      "is_verified": false,
      "source_channel": "instagram"
    },
    "origin_context": {
      "origem": "outbound",
      "context_type": "prospecting_response",
      "tom_agente": "direto, dar continuidade",
      "mensagem_abordagem": ""
    }
  }'
```

### Resultado Esperado

```json
{
  "success": true,
  "username": "lead_teste",
  "classification": "LEAD_WARM",
  "score": 70,
  "reasoning": "Lead dermatologista respondendo prospecção com interesse",
  "suggested_response": "Que bom que se interessou! Vi que você é dermatologista em SP. Nosso método tem ajudado vários médicos a..."
}
```

---

## Troubleshooting

### Erro: profile_context chega vazio

**Causa:** O nó "Auto Enrich Lead" não está retornando `lead_data.bio`

**Verificar:**
1. Output do nó "Auto Enrich Lead" no n8n
2. Se o endpoint `/api/auto-enrich-lead` está funcionando

### Erro: origem_conversa não está disponível

**Causa:** Os dados do nó "Contexto: BDR Abordou" não estão fluindo para o "Classificar Lead IA"

**Solução:** Adicionar um nó **Set** antes do "Classificar Lead IA" que consolida:
- Dados do Info
- Dados do Auto Enrich Lead
- Dados do Contexto de Origem

---

## Arquivos Relacionados

- `/implementation/api_server.py` - Endpoint atualizado
- `/.claude/n8n-classificar-lead-ia-novo-body.json` - JSON body completo
- `/.claude/insights.md` - Histórico de decisões
