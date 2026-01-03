# Processo de Prospecao de Leads no Instagram com Classificacao Automatica por IA

**Versao:** 1.0
**Data:** 03/01/2026
**Autor:** MOTTIVME
**Status:** Implementado e Operacional

---

## Indice

1. [Visao Geral](#visao-geral)
2. [Arquitetura do Sistema](#arquitetura-do-sistema)
3. [Fluxo Detalhado](#fluxo-detalhado)
4. [APIs e Endpoints](#apis-e-endpoints)
5. [Workflow n8n](#workflow-n8n)
6. [Automacoes GHL](#automacoes-ghl)
7. [Exemplos de Requisicoes](#exemplos-de-requisicoes)
8. [Troubleshooting](#troubleshooting)
9. [Metricas de Sucesso](#metricas-de-sucesso)
10. [Checklist Operacional](#checklist-operacional)

---

## Visao Geral

Este documento descreve o processo completo de prospeccao de leads via Instagram, desde a identificacao do perfil ate a ativacao da IA para atendimento automatizado no GoHighLevel.

### Stack Tecnologico

| Componente | Tecnologia | Funcao |
|------------|------------|--------|
| Scraper | AgenticOS (Railway) | Coleta dados do perfil |
| Banco de Dados | AgenticOS PostgreSQL | Armazena leads e contexto |
| Envio DM | Playwright + Python | Automacao de mensagens |
| Orquestracao | n8n | Processamento e classificacao |
| CRM | GoHighLevel | Gestao de leads e automacoes |
| IA | Claude/OpenAI | Classificacao de leads |

---

## Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                    PROCESSO DE PROSPECCAO INSTAGRAM                              │
└─────────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
    │   ETAPA 1    │     │   ETAPA 2    │     │   ETAPA 3    │
    │    SCRAPE    │────▶│    SALVAR    │────▶│  ENVIAR DM   │
    │   PERFIL     │     │  AGENTICOS   │     │  PLAYWRIGHT  │
    └──────────────┘     └──────────────┘     └──────────────┘
           │                    │                    │
           ▼                    ▼                    ▼
    ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
    │ API Railway  │     │   lead_id    │     │  Navegador   │
    │ /scrape-     │     │    unico     │     │    Local     │
    │   profile    │     │   gerado     │     │  Instagram   │
    └──────────────┘     └──────────────┘     └──────────────┘


                              │
                              │ Lead responde no Instagram
                              ▼

    ┌──────────────────────────────────────────────────────────┐
    │                      ETAPA 4-5                            │
    │                 PROCESSAMENTO N8N                         │
    │                                                           │
    │  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌────────┐ │
    │  │ Webhook │───▶│Verifica │───▶│  Match  │───▶│Classif.│ │
    │  │   GHL   │    │ Trafego │    │ Context │    │   IA   │ │
    │  └─────────┘    └─────────┘    └─────────┘    └────────┘ │
    │                      │              │              │      │
    │                      ▼              ▼              ▼      │
    │                 [SKIP se      [matched=    [LEAD_* ou    │
    │                  UTM]          true]      SPAM/PESSOAL]  │
    └──────────────────────────────────────────────────────────┘
                              │
                              ▼
    ┌──────────────────────────────────────────────────────────┐
    │                      ETAPA 6                              │
    │                   GHL AUTOMATION                          │
    │                                                           │
    │     ┌─────────────────┐    ┌─────────────────────────┐   │
    │     │  Tag Aplicada   │───▶│   Campos Atualizados    │   │
    │     │                 │    │                         │   │
    │     │ - lead-         │    │ - ativar_ia = sim       │   │
    │     │   prospectado-  │    │ - agente_ia = [nome]    │   │
    │     │   ia            │    │ - origem = prospeccao   │   │
    │     │ - lead-         │    │ - data_ativacao = now() │   │
    │     │   classificado- │    │                         │   │
    │     │   ia            │    └─────────────────────────┘   │
    │     │ - perdido       │                                   │
    │     └─────────────────┘                                   │
    └──────────────────────────────────────────────────────────┘
```

---

## Fluxo Detalhado

### ETAPA 1: Scrape do Perfil

**Objetivo:** Coletar dados publicos do perfil Instagram para analise e scoring.

```
┌────────────────────────────────────────────────────┐
│                 SCRAPE DO PERFIL                    │
├────────────────────────────────────────────────────┤
│                                                     │
│  Input: username do Instagram                       │
│                                                     │
│  Processo:                                          │
│  1. Requisicao POST para AgenticOS                 │
│  2. Coleta: bio, followers, following, posts       │
│  3. Calcula score de qualificacao                  │
│  4. Classifica inicialmente (LEAD_*, SPAM, etc)    │
│  5. Opcionalmente salva no banco                   │
│                                                     │
│  Output:                                            │
│  - Dados completos do perfil                       │
│  - Score numerico (0-100)                          │
│  - Classificacao inicial                           │
│                                                     │
└────────────────────────────────────────────────────┘
```

### ETAPA 2: Salvar no AgenticOS

**Objetivo:** Registrar o lead no banco de dados para rastreamento futuro.

```
┌────────────────────────────────────────────────────┐
│               SALVAR NO AGENTICOS                   │
├────────────────────────────────────────────────────┤
│                                                     │
│  Input: username, tenant_id                         │
│                                                     │
│  Processo:                                          │
│  1. Cria registro na tabela leads                  │
│  2. Gera lead_id unico (UUID)                      │
│  3. Associa ao tenant (mottivme)                   │
│  4. Marca origem como "prospeccao_instagram"       │
│                                                     │
│  Output:                                            │
│  - lead_id (UUID)                                  │
│  - Confirmacao de criacao                          │
│                                                     │
└────────────────────────────────────────────────────┘
```

### ETAPA 3: Enviar DM

**Objetivo:** Iniciar conversa com o lead via mensagem direta.

```
┌────────────────────────────────────────────────────┐
│                   ENVIAR DM                         │
├────────────────────────────────────────────────────┤
│                                                     │
│  Tecnologia: Playwright (Python)                   │
│  Execucao: Local (requer sessao Instagram ativa)   │
│                                                     │
│  Processo:                                          │
│  1. Abre navegador com sessao salva               │
│  2. Navega para perfil do lead                     │
│  3. Clica em "Mensagem"                           │
│  4. Envia texto personalizado                      │
│  5. Registra envio no AgenticOS                    │
│                                                     │
│  Personalizacao:                                    │
│  - Nome do lead (se disponivel)                    │
│  - Referencia ao nicho/bio                         │
│  - CTA especifico                                  │
│                                                     │
└────────────────────────────────────────────────────┘
```

### ETAPA 4: Lead Responde

**Objetivo:** Capturar resposta e iniciar processamento.

```
┌────────────────────────────────────────────────────┐
│              LEAD RESPONDE                          │
├────────────────────────────────────────────────────┤
│                                                     │
│  Trigger: Mensagem recebida no Instagram           │
│                                                     │
│  Fluxo:                                             │
│  1. Integracao Instagram ↔ GHL recebe mensagem    │
│  2. Webhook GHL dispara para n8n                   │
│  3. Payload inclui:                                │
│     - contact_id                                   │
│     - message_text                                 │
│     - timestamp                                    │
│     - channel = "instagram"                        │
│                                                     │
└────────────────────────────────────────────────────┘
```

### ETAPA 5: Processamento n8n

**Objetivo:** Classificar e rotear o lead automaticamente.

```
┌────────────────────────────────────────────────────────────────────────┐
│                    WORKFLOW N8N (R2fVs2qpct1Qr2Y1)                      │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐                                                        │
│  │   Webhook   │                                                        │
│  │    GHL      │                                                        │
│  └──────┬──────┘                                                        │
│         │                                                               │
│         ▼                                                               │
│  ┌─────────────────┐                                                    │
│  │ IF "Veio de     │──── SIM (tem UTM) ────▶ [SKIP - Lead de Trafego]  │
│  │   Trafego?"     │                                                    │
│  └────────┬────────┘                                                    │
│           │ NAO                                                         │
│           ▼                                                               │
│  ┌─────────────────┐                                                    │
│  │  Match Lead     │   Busca username no AgenticOS                     │
│  │    Context      │   GET /api/leads?username=XXX                     │
│  └────────┬────────┘                                                    │
│           │                                                               │
│           ▼                                                               │
│  ┌─────────────────┐                                                    │
│  │ IF matched=true │──── SIM ────▶ Tag: "lead-prospectado-ia"          │
│  │                 │              (Lead veio da prospeccao)             │
│  └────────┬────────┘                                                    │
│           │ NAO                                                         │
│           ▼                                                               │
│  ┌─────────────────┐                                                    │
│  │  Classificar    │   IA analisa mensagem + perfil                    │
│  │    com IA       │                                                    │
│  └────────┬────────┘                                                    │
│           │                                                               │
│           ▼                                                               │
│  ┌─────────────────┐                                                    │
│  │ Resultado IA    │                                                    │
│  ├─────────────────┤                                                    │
│  │ LEAD_QUENTE     │────▶ Tag: "lead-classificado-ia"                  │
│  │ LEAD_MORNO      │────▶ Tag: "lead-classificado-ia"                  │
│  │ LEAD_FRIO       │────▶ Tag: "lead-classificado-ia"                  │
│  │ SPAM            │────▶ Tag: "perdido"                               │
│  │ PESSOAL         │────▶ Tag: "perdido"                               │
│  └─────────────────┘                                                    │
│                                                                         │
│  ┌─────────────────┐                                                    │
│  │ IF "Ja Ativou   │   Verifica se tag ja existe                       │
│  │     IA?"        │   (evita duplicacao)                              │
│  └─────────────────┘                                                    │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘
```

### ETAPA 6: Automacao GHL

**Objetivo:** Reagir as tags e preparar lead para atendimento IA.

```
┌────────────────────────────────────────────────────┐
│               GHL AUTOMATION                        │
├────────────────────────────────────────────────────┤
│                                                     │
│  Trigger: Tag adicionada ao contato                │
│                                                     │
│  Se tag = "lead-prospectado-ia":                   │
│  ├── ativar_ia = "sim"                             │
│  ├── agente_ia = "SDR Prospeccao"                  │
│  ├── origem_lead = "prospeccao_instagram"          │
│  └── data_ativacao_ia = {{ now }}                  │
│                                                     │
│  Se tag = "lead-classificado-ia":                  │
│  ├── ativar_ia = "sim"                             │
│  ├── agente_ia = "SDR Inbound"                     │
│  ├── classificacao_ia = {{ resultado }}            │
│  └── data_ativacao_ia = {{ now }}                  │
│                                                     │
│  Se tag = "perdido":                               │
│  ├── ativar_ia = "nao"                             │
│  ├── motivo_perda = "spam_ou_pessoal"              │
│  └── data_descarte = {{ now }}                     │
│                                                     │
└────────────────────────────────────────────────────┘
```

---

## APIs e Endpoints

### AgenticOS - Railway

**Base URL:** `https://agenticoskevsacademy-production.up.railway.app`

| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/webhook/scrape-profile` | POST | Scrape de perfil Instagram |
| `/webhook/inbound-dm` | POST | Registrar lead/DM |
| `/api/leads` | GET | Buscar leads |
| `/api/leads/:id` | GET | Detalhes do lead |

### GoHighLevel

| Endpoint | Descricao |
|----------|-----------|
| Webhook de mensagem | Dispara quando recebe msg Instagram |
| API Contacts | Gerenciar contatos e tags |
| API Custom Fields | Atualizar campos personalizados |

### n8n

| Workflow ID | Nome | Descricao |
|-------------|------|-----------|
| R2fVs2qpct1Qr2Y1 | Classificacao Lead Instagram | Processa e classifica leads |

---

## Exemplos de Requisicoes

### 1. Scrape de Perfil

```bash
# Scrape basico
curl -X POST "https://agenticoskevsacademy-production.up.railway.app/webhook/scrape-profile" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "perfil_exemplo",
    "save_to_db": true
  }'
```

**Resposta esperada:**
```json
{
  "success": true,
  "data": {
    "username": "perfil_exemplo",
    "full_name": "Nome Completo",
    "bio": "Descricao do perfil...",
    "followers": 15000,
    "following": 500,
    "posts": 120,
    "is_business": true,
    "category": "Entrepreneur",
    "score": 78,
    "classification": "LEAD_MORNO",
    "scraped_at": "2026-01-03T10:30:00Z"
  }
}
```

### 2. Salvar Lead no AgenticOS

```bash
curl -X POST "https://agenticoskevsacademy-production.up.railway.app/webhook/inbound-dm" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "perfil_exemplo",
    "message": "",
    "tenant_id": "mottivme"
  }'
```

**Resposta esperada:**
```json
{
  "success": true,
  "lead_id": "550e8400-e29b-41d4-a716-446655440000",
  "created": true,
  "message": "Lead registered successfully"
}
```

### 3. Buscar Lead por Username

```bash
curl -X GET "https://agenticoskevsacademy-production.up.railway.app/api/leads?username=perfil_exemplo&tenant_id=mottivme" \
  -H "Content-Type: application/json"
```

**Resposta esperada:**
```json
{
  "success": true,
  "matched": true,
  "lead": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "perfil_exemplo",
    "tenant_id": "mottivme",
    "source": "prospeccao_instagram",
    "created_at": "2026-01-03T10:30:00Z",
    "last_interaction": "2026-01-03T14:22:00Z"
  }
}
```

### 4. Script Python - Envio de DM

```python
#!/usr/bin/env python3
"""
Script para envio de DM via Playwright
Requer sessao Instagram ativa
"""

import asyncio
from playwright.async_api import async_playwright
import json

async def send_dm(username: str, message: str):
    async with async_playwright() as p:
        # Usar sessao salva
        browser = await p.chromium.launch_persistent_context(
            user_data_dir="~/.instagram-session",
            headless=False
        )

        page = await browser.new_page()

        # Navegar para o perfil
        await page.goto(f"https://instagram.com/{username}")
        await page.wait_for_load_state("networkidle")

        # Clicar em Mensagem
        await page.click('text="Mensagem"')
        await page.wait_for_selector('textarea[placeholder*="Mensagem"]')

        # Digitar e enviar
        await page.fill('textarea[placeholder*="Mensagem"]', message)
        await page.click('button:has-text("Enviar")')

        print(f"DM enviada para @{username}")

        await browser.close()

# Uso
if __name__ == "__main__":
    asyncio.run(send_dm(
        username="perfil_alvo",
        message="Oi! Vi seu perfil e achei muito interessante..."
    ))
```

### 5. Teste do Workflow n8n

```bash
# Simular webhook do GHL
curl -X POST "https://seu-n8n.com/webhook/R2fVs2qpct1Qr2Y1" \
  -H "Content-Type: application/json" \
  -d '{
    "contact_id": "abc123",
    "contact_email": "lead@exemplo.com",
    "contact_phone": "+5511999999999",
    "instagram_username": "perfil_exemplo",
    "message": "Oi, vi sua mensagem!",
    "channel": "instagram",
    "location_id": "xxx",
    "utm_source": null,
    "utm_medium": null
  }'
```

---

## Workflow n8n

### Estrutura do Workflow R2fVs2qpct1Qr2Y1

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         WORKFLOW NODES                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  [1] Webhook GHL                                                         │
│      Trigger: POST /webhook/R2fVs2qpct1Qr2Y1                            │
│      Output: contact_id, message, instagram_username, utm_*             │
│                                                                          │
│  [2] IF - Veio de Trafego?                                              │
│      Condicao: {{ $json.utm_source != null }}                           │
│      TRUE  → [END] Skip - Lead de Trafego                               │
│      FALSE → [3] Match Lead Context                                      │
│                                                                          │
│  [3] HTTP Request - Match Lead Context                                   │
│      URL: AgenticOS /api/leads?username={{ $json.instagram_username }}  │
│      Method: GET                                                         │
│      Output: matched (boolean), lead (object)                           │
│                                                                          │
│  [4] IF - Lead Matched?                                                  │
│      Condicao: {{ $json.matched == true }}                              │
│      TRUE  → [5a] Aplicar Tag "lead-prospectado-ia"                     │
│      FALSE → [5b] Classificar com IA                                     │
│                                                                          │
│  [5a] GHL - Adicionar Tag                                               │
│      Tag: "lead-prospectado-ia"                                         │
│      → [7] IF Ja Ativou IA?                                             │
│                                                                          │
│  [5b] OpenAI - Classificar Lead                                          │
│      Prompt: Analise esta mensagem e classifique...                     │
│      Output: classification (LEAD_*, SPAM, PESSOAL)                     │
│      → [6] Switch por Classificacao                                      │
│                                                                          │
│  [6] Switch - Resultado Classificacao                                    │
│      LEAD_QUENTE  → Tag: "lead-classificado-ia"                         │
│      LEAD_MORNO   → Tag: "lead-classificado-ia"                         │
│      LEAD_FRIO    → Tag: "lead-classificado-ia"                         │
│      SPAM         → Tag: "perdido"                                       │
│      PESSOAL      → Tag: "perdido"                                       │
│      → [7] IF Ja Ativou IA?                                             │
│                                                                          │
│  [7] IF - Ja Ativou IA?                                                  │
│      Condicao: {{ $json.tags.includes("ia-ativada") }}                  │
│      TRUE  → [END] Skip - Ja processado                                  │
│      FALSE → [8] GHL Update Contact                                      │
│                                                                          │
│  [8] GHL - Update Contact                                                │
│      Campos atualizados conforme tag aplicada                           │
│      → [END] Sucesso                                                     │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Prompt de Classificacao IA

```
Voce e um classificador de leads para uma agencia de marketing digital.

Analise a mensagem abaixo e classifique o remetente em UMA das categorias:

- LEAD_QUENTE: Demonstra interesse claro, faz perguntas sobre servicos, menciona orcamento ou prazo
- LEAD_MORNO: Responde de forma positiva mas sem urgencia, curioso sobre o servico
- LEAD_FRIO: Resposta neutra ou educada sem demonstrar interesse real
- SPAM: Mensagem automatizada, propaganda, ou conteudo irrelevante
- PESSOAL: Mensagem pessoal nao relacionada a negocios

Mensagem do lead:
"""
{{ message }}
"""

Contexto do perfil (se disponivel):
- Bio: {{ bio }}
- Followers: {{ followers }}
- Categoria: {{ category }}

Responda APENAS com a classificacao (ex: LEAD_QUENTE)
```

---

## Automacoes GHL

### Automation 1: Lead Prospectado

**Trigger:** Tag "lead-prospectado-ia" adicionada

```yaml
name: "IA - Ativar para Lead Prospectado"
trigger:
  type: tag_added
  tag: "lead-prospectado-ia"

actions:
  - type: update_contact
    fields:
      ativar_ia: "sim"
      agente_ia: "SDR Prospeccao"
      origem_lead: "prospeccao_instagram"
      data_ativacao_ia: "{{ now }}"

  - type: add_tag
    tag: "ia-ativada"

  - type: internal_notification
    message: "Novo lead de prospeccao Instagram ativado para IA"
```

### Automation 2: Lead Classificado

**Trigger:** Tag "lead-classificado-ia" adicionada

```yaml
name: "IA - Ativar para Lead Classificado"
trigger:
  type: tag_added
  tag: "lead-classificado-ia"

actions:
  - type: update_contact
    fields:
      ativar_ia: "sim"
      agente_ia: "SDR Inbound"
      classificacao_ia: "{{ custom_field.classificacao_resultado }}"
      data_ativacao_ia: "{{ now }}"

  - type: add_tag
    tag: "ia-ativada"
```

### Automation 3: Lead Perdido

**Trigger:** Tag "perdido" adicionada

```yaml
name: "IA - Marcar como Perdido"
trigger:
  type: tag_added
  tag: "perdido"

actions:
  - type: update_contact
    fields:
      ativar_ia: "nao"
      motivo_perda: "classificado_spam_ou_pessoal"
      data_descarte: "{{ now }}"

  - type: move_pipeline_stage
    pipeline: "Prospeccao"
    stage: "Perdido"
```

---

## Troubleshooting

### Problema 1: Scrape retorna erro 429

**Sintoma:** API retorna "Too Many Requests"

**Causa:** Rate limit do Instagram

**Solucao:**
```bash
# Aguardar 5-10 minutos entre requisicoes
# Usar proxy rotativo se necessario
# Verificar se conta nao esta bloqueada
```

### Problema 2: Lead nao e matchado no AgenticOS

**Sintoma:** `matched: false` mesmo para lead prospectado

**Causa:** Username diferente ou nao salvo

**Verificacao:**
```bash
# Verificar se lead existe
curl "https://agenticoskevsacademy-production.up.railway.app/api/leads?username=XXXXX&tenant_id=mottivme"

# Se nao existir, verificar se foi salvo na Etapa 2
```

**Solucao:**
- Garantir que username esta padronizado (sem @)
- Verificar tenant_id correto
- Re-executar Etapa 2 se necessario

### Problema 3: Workflow n8n nao dispara

**Sintoma:** Mensagem chega no GHL mas n8n nao processa

**Causas possiveis:**
1. Webhook desabilitado
2. URL do webhook incorreta no GHL
3. Workflow pausado

**Verificacao:**
```bash
# Testar webhook manualmente
curl -X POST "https://seu-n8n.com/webhook/R2fVs2qpct1Qr2Y1" \
  -H "Content-Type: application/json" \
  -d '{"test": true}'
```

### Problema 4: Tag nao e aplicada no GHL

**Sintoma:** Workflow executa mas tag nao aparece

**Causas possiveis:**
1. API Key GHL expirada
2. Tag nao existe no GHL
3. Permissoes insuficientes

**Solucao:**
```bash
# Verificar tags disponiveis
curl "https://rest.gohighlevel.com/v1/tags" \
  -H "Authorization: Bearer SUA_API_KEY"

# Criar tag se nao existir
curl -X POST "https://rest.gohighlevel.com/v1/tags" \
  -H "Authorization: Bearer SUA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "lead-prospectado-ia"}'
```

### Problema 5: Playwright nao consegue enviar DM

**Sintoma:** Script trava ou erro de elemento nao encontrado

**Causas possiveis:**
1. Sessao expirada
2. Instagram mudou layout
3. Conta bloqueada temporariamente

**Solucao:**
```python
# Verificar se sessao esta valida
# Login manual se necessario
# Atualizar seletores se layout mudou
# Aguardar 24-48h se conta bloqueada
```

### Problema 6: IA classifica incorretamente

**Sintoma:** Leads bons marcados como SPAM ou vice-versa

**Solucao:**
1. Revisar prompt de classificacao
2. Adicionar mais exemplos (few-shot)
3. Incluir mais contexto do perfil
4. Ajustar temperatura do modelo (0.3-0.5)

---

## Metricas de Sucesso

### KPIs Principais

| Metrica | Meta | Calculo |
|---------|------|---------|
| Taxa de Resposta | > 15% | Respostas / DMs enviadas |
| Taxa de Match | > 90% | Leads matchados / Leads que responderam |
| Precisao IA | > 85% | Classificacoes corretas / Total classificado |
| Conversao para Oportunidade | > 5% | Oportunidades / Leads classificados |

### Dashboard Sugerido

```sql
-- Query para metricas diarias
SELECT
  DATE(created_at) as data,
  COUNT(*) FILTER (WHERE source = 'prospeccao_instagram') as leads_prospectados,
  COUNT(*) FILTER (WHERE matched = true) as leads_matchados,
  COUNT(*) FILTER (WHERE classification LIKE 'LEAD_%') as leads_qualificados,
  COUNT(*) FILTER (WHERE classification IN ('SPAM', 'PESSOAL')) as leads_descartados,
  ROUND(
    COUNT(*) FILTER (WHERE matched = true)::decimal /
    NULLIF(COUNT(*), 0) * 100,
  2) as taxa_match_percent
FROM leads
WHERE tenant_id = 'mottivme'
  AND created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY data DESC;
```

### Relatorio Semanal

```
============================================
RELATORIO SEMANAL - PROSPECCAO INSTAGRAM
Periodo: {{ semana }}
============================================

VOLUME
- DMs Enviadas: {{ total_dms }}
- Respostas Recebidas: {{ total_respostas }}
- Taxa de Resposta: {{ taxa_resposta }}%

CLASSIFICACAO
- LEAD_QUENTE: {{ count_quente }} ({{ pct_quente }}%)
- LEAD_MORNO: {{ count_morno }} ({{ pct_morno }}%)
- LEAD_FRIO: {{ count_frio }} ({{ pct_frio }}%)
- SPAM/PESSOAL: {{ count_descartado }} ({{ pct_descartado }}%)

CONVERSAO
- Leads para Oportunidade: {{ leads_opp }}
- Taxa Conversao: {{ taxa_conversao }}%

OBSERVACOES
{{ observacoes_manuais }}
============================================
```

---

## Checklist Operacional

### Diario

- [ ] Verificar se workflow n8n esta ativo
- [ ] Checar fila de mensagens nao processadas
- [ ] Revisar leads classificados como SPAM (falsos positivos)
- [ ] Monitorar rate limits do Instagram

### Semanal

- [ ] Analisar metricas de conversao
- [ ] Ajustar mensagens de prospeccao se necessario
- [ ] Revisar precisao da classificacao IA
- [ ] Atualizar lista de perfis alvo

### Mensal

- [ ] Gerar relatorio completo de performance
- [ ] Revisar e otimizar prompt de classificacao
- [ ] Atualizar automacoes GHL se necessario
- [ ] Backup de dados AgenticOS

---

## Contatos e Suporte

| Sistema | Responsavel | Contato |
|---------|-------------|---------|
| AgenticOS | MOTTIVME | suporte@mottivme.com |
| n8n | MOTTIVME | - |
| GHL | MOTTIVME | - |
| Instagram | - | - |

---

## Changelog

| Versao | Data | Alteracao |
|--------|------|-----------|
| 1.0 | 03/01/2026 | Documentacao inicial |

---

*Documento gerado para MOTTIVME - Todos os direitos reservados*
