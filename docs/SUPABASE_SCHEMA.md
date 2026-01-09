# Supabase Schema - MOTTIVME Sales

> **Projeto:** `bfumywvwubvernvhjehk`
> **Última atualização:** 2026-01-09
> **Total de tabelas/views:** 390+
> **Tabelas documentadas:** 20

Este documento serve como referência para o schema do banco de dados Supabase usado nos projetos MOTTIVME Sales.

---

## 🔥 Tabelas Mais Ativas (por volume de registros)

| # | Tabela | Registros | Categoria |
|---|--------|-----------|-----------|
| 1 | `llm_costs` | 7.802 | Métricas/Custos IA |
| 2 | `agent_conversation_messages` | 5.094 | Conversas |
| 3 | `messages` | 3.660 | Mensagens gerais |
| 4 | `n8n_active_conversation` | 618 | Integração n8n |
| 5 | `agent_conversations` | 591 | Conversas |
| 6 | `fin_movimentacoes` | 303 | Financeiro |
| 7 | `n8n_historico_mensagens` | 194 | Integração n8n |
| 8 | `claude_conversations` | 177 | IA/Claude Code |
| 9 | `fin_categorias` | 123 | Financeiro |
| 10 | `crm_leads` | 93 | Leads |

---

## Índice

1. [Tabelas de Leads (Principal)](#1-tabelas-de-leads-principal)
2. [Tabelas de Configuração de Clientes](#2-tabelas-de-configuração-de-clientes)
3. [Tabelas de Conversas e Mensagens](#3-tabelas-de-conversas-e-mensagens)
4. [Tabelas de Prospecção Instagram](#4-tabelas-de-prospecção-instagram)
5. [Tabelas do Portal CRM](#5-tabelas-do-portal-crm)
6. [Tabelas de Métricas e Analytics](#6-tabelas-de-métricas-e-analytics)
7. [Tabelas Financeiras](#7-tabelas-financeiras)
8. [Tabelas de IA/RAG](#8-tabelas-de-iarag)
9. [Tabelas de Integração n8n](#9-tabelas-de-integração-n8n)
10. [Tabelas Claude Code](#10-tabelas-claude-code)
11. [Relacionamentos Entre Tabelas](#11-relacionamentos-entre-tabelas)
12. [Enums e Valores Válidos](#12-enums-e-valores-válidos)

---

## 1. Tabelas de Leads (Principal)

### 1.1 `growth_leads` ⭐ (Tabela Principal do Growth OS)

> **Status:** VAZIA - Pronta para receber dados via sync
> **Propósito:** Leads do Growth OS com funil completo e qualificação BANT

| Coluna | Tipo | Obrigatório | Default | Descrição |
|--------|------|-------------|---------|-----------|
| `id` | uuid | Sim | gen_random_uuid() | PK |
| `location_id` | text | **Sim** | - | ID do tenant/cliente (multi-tenant) |
| `ghl_contact_id` | text | Não | - | ID do contato no GHL |
| `name` | text | Não | - | Nome do lead |
| `email` | text | Não | - | Email |
| `phone` | text | Não | - | Telefone |
| `company` | text | Não | - | Empresa |
| `title` | text | Não | - | Cargo |
| `avatar_url` | text | Não | - | URL do avatar |
| `instagram_username` | text | Não | - | @ do Instagram |
| `linkedin_url` | text | Não | - | URL do LinkedIn |
| `whatsapp` | text | Não | - | WhatsApp |
| `source_channel` | text | **Sim** | - | Canal de origem |
| `source_campaign` | text | Não | - | Campanha de origem |
| `source_agent_code` | text | Não | - | Código do agente que originou |
| `assigned_agent_code` | text | Não | - | Agente atribuído |
| `assigned_user_id` | text | Não | - | Usuário atribuído |
| `funnel_stage` | text | Não | 'prospected' | Etapa do funil |
| `previous_stage` | text | Não | - | Etapa anterior |
| `stage_changed_at` | timestamptz | Não | - | Data mudança de etapa |
| `bant_budget_score` | integer | Não | 0 | Score BANT: Budget |
| `bant_authority_score` | integer | Não | 0 | Score BANT: Authority |
| `bant_need_score` | integer | Não | 0 | Score BANT: Need |
| `bant_timeline_score` | integer | Não | 0 | Score BANT: Timeline |
| `bant_total_score` | integer | Não | - | Score BANT total (calculado) |
| `lead_score` | integer | Não | 0 | Score geral do lead |
| `lead_temperature` | text | Não | 'cold' | Temperatura (cold/warm/hot) |
| `icp_score` | integer | Não | 0 | Score de ICP |
| `total_messages_sent` | integer | Não | 0 | Total mensagens enviadas |
| `total_messages_received` | integer | Não | 0 | Total mensagens recebidas |
| `total_calls` | integer | Não | 0 | Total de ligações |
| `total_meetings` | integer | Não | 0 | Total de reuniões |
| `last_contact_at` | timestamptz | Não | - | Último contato |
| `last_response_at` | timestamptz | Não | - | Última resposta |
| `response_time_avg_hours` | numeric | Não | - | Tempo médio de resposta |
| `meeting_scheduled_at` | timestamptz | Não | - | Data agendamento |
| `meeting_type` | text | Não | - | Tipo de reunião |
| `meeting_show_status` | text | Não | - | Status do comparecimento |
| `proposal_sent_at` | timestamptz | Não | - | Data envio proposta |
| `proposal_value` | numeric | Não | - | Valor da proposta |
| `proposal_status` | text | Não | - | Status da proposta |
| `converted_at` | timestamptz | Não | - | Data conversão |
| `conversion_value` | numeric | Não | - | Valor da conversão |
| `lost_at` | timestamptz | Não | - | Data perda |
| `lost_reason` | text | Não | - | Motivo da perda |
| `lost_competitor` | text | Não | - | Concorrente que ganhou |
| `reactivation_count` | integer | Não | 0 | Contagem reativações |
| `last_reactivation_at` | timestamptz | Não | - | Última reativação |
| `reactivation_responded` | boolean | Não | false | Se respondeu reativação |
| `sentiment_score` | numeric | Não | - | Score de sentimento |
| `detected_objections` | text[] | Não | - | Objeções detectadas |
| `custom_fields` | jsonb | Não | - | Campos customizados |
| `tags` | text[] | Não | - | Tags |
| `created_at` | timestamptz | Não | now() | Data criação |
| `updated_at` | timestamptz | Não | now() | Data atualização |

---

### 1.2 `socialfy_leads` (Leads do Socialfy)

> **Status:** POPULADA - ~5 registros
> **Propósito:** Leads capturados via scraping Instagram e LinkedIn

| Coluna | Tipo | Exemplo | Descrição |
|--------|------|---------|-----------|
| `id` | uuid | `44782d7c-aad4-...` | PK |
| `organization_id` | uuid | `11111111-1111-...` | Organização |
| `name` | text | `Dra Roberta Palmeira` | Nome |
| `title` | text | `Dra.`, `CEO` | Título |
| `company` | text | `TechVentures Brasil` | Empresa |
| `avatar_url` | text | null | Avatar |
| `email` | text | `ricardo@techventures.com.br` | Email |
| `phone` | text | `+558537714478` | Telefone |
| `linkedin_url` | text | `https://linkedin.com/in/...` | LinkedIn |
| `instagram_handle` | text | `@drarobertacostapalmeira` | Instagram |
| `whatsapp` | text | `+5511999990001` | WhatsApp |
| `status` | text | `available` | Status |
| `icp_score` | integer | 95 | Score ICP |
| `icp_tier` | text | `A`, `C` | Tier ICP |
| `channels` | text[] | `["instagram"]` | Canais ativos |
| `source` | text | `instagram_scraping` | Fonte |
| `source_data` | jsonb | `{"type": "profile_direct"}` | Dados da fonte |
| `cnpj` | text | null | CNPJ |
| `cnpj_data` | jsonb | `{}` | Dados CNPJ |
| `tags` | text[] | `["medico", "influenciador"]` | Tags |
| `list_ids` | text[] | `[]` | Listas |
| `custom_fields` | jsonb | `{"website": "..."}` | Campos custom |
| `ghl_contact_id` | text | `jAyiLADrjCF3J9uEZfVP` | ID no GHL |
| `location_id` | text | `sNwLyynZWP6jEtBy1ubf` | Location GHL |
| `vertical` | text | `medico` | Vertical |
| `vertical_data` | jsonb | `{}` | Dados da vertical |
| `instagram_followers` | integer | 10589 | Seguidores |
| `instagram_following` | integer | 2572 | Seguindo |
| `instagram_posts` | integer | 1047 | Posts |
| `instagram_bio` | text | Bio do perfil | Bio |
| `instagram_is_verified` | boolean | false | Verificado |
| `instagram_is_business` | boolean | true | Conta business |
| `instagram_url` | text | `https://instagram.com/...` | URL |
| `score_potencial` | integer | 35 | Score potencial |
| `scraped_at` | timestamptz | `2026-01-03T02:52:33` | Data scrape |
| `scrape_source` | text | `profile_direct` | Fonte scrape |
| `outreach_sent_at` | timestamptz | null | Data outreach |
| `last_outreach_message` | text | null | Última msg |
| `created_by` | uuid | null | Criado por |
| `created_at` | timestamptz | timestamp | Criação |
| `updated_at` | timestamptz | timestamp | Atualização |

**Exemplo de dados:**
```json
{
  "name": "Dra Roberta Palmeira | Pneumo Pediatra",
  "instagram_handle": "@drarobertacostapalmeira",
  "instagram_followers": 10589,
  "icp_tier": "A",
  "score_potencial": 35,
  "vertical": "medico",
  "source": "instagram_scraping"
}
```

---

### 1.3 `crm_leads` (Leads CRM Legado)

> **Status:** POPULADA - ~5 registros
> **Propósito:** CRM geral legado

| Coluna | Tipo | Exemplo | Descrição |
|--------|------|---------|-----------|
| `id` | uuid | uuid | PK |
| `proposal_id` | uuid | null | FK proposta |
| `name` | text | `Renan Porto` | Nome |
| `email` | text | `renan@renan.com` | Email |
| `phone` | text | null | Telefone |
| `company` | text | `Empresa XYZ` | Empresa |
| `score` | integer | 82 | Score (0-100) |
| `status` | text | `hot`, `pending` | Status |
| `last_activity` | timestamptz | null | Última atividade |
| `total_time_seconds` | integer | 0 | Tempo total |
| `visit_count` | integer | 0 | Visitas |
| `created_at` | timestamptz | timestamp | Criação |
| `ghl_contact_id` | text | null | ID GHL |
| `ghl_location_id` | text | null | Location GHL |
| `company_id` | uuid | null | FK empresa |
| `vertical` | text | null | Vertical |
| `source_channel` | text | `instagram` | Canal origem |
| `current_agent` | text | null | Agente atual |
| `notes` | text | null | Notas |

---

### 1.4 `enriched_lead_data` (Dados Enriquecidos)

> **Status:** VAZIA
> **Propósito:** Dados de enriquecimento de leads (CNPJ, Instagram, LinkedIn)

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | uuid | PK |
| `lead_id` | uuid | FK para lead |
| `source` | text | Fonte do enriquecimento |
| `confidence_score` | numeric | Score de confiança |
| `enriched_at` | timestamptz | Data enriquecimento |
| `expires_at` | timestamptz | Expiração |
| `raw_data` | jsonb | Dados brutos |
| **Dados CNPJ** | | |
| `cnpj` | text | CNPJ |
| `empresa` | text | Nome fantasia |
| `razao_social` | text | Razão social |
| `cnae_principal` | text | CNAE |
| `cnae_descricao` | text | Descrição CNAE |
| `setor` | text | Setor |
| `porte` | text | Porte |
| `faturamento_estimado` | numeric | Faturamento |
| **Dados Contato** | | |
| `cargo` | text | Cargo |
| **Dados Instagram** | | |
| `ig_handle` | text | Username |
| `ig_bio` | text | Bio |
| `ig_category` | text | Categoria |
| `ig_followers` | integer | Seguidores |
| `ig_following` | integer | Seguindo |
| `ig_posts` | integer | Posts |
| `ig_engagement_rate` | numeric | Engajamento |
| `ig_is_business` | boolean | Conta business |
| **Dados LinkedIn** | | |
| `li_url` | text | URL |
| `li_headline` | text | Headline |
| `li_connections` | integer | Conexões |
| `li_education` | text | Formação |
| `li_experience` | text | Experiência |

---

## 2. Tabelas de Configuração de Clientes

### 2.1 `growth_client_configs` ⭐

> **Status:** POPULADA - 1 registro
> **Propósito:** Configuração de cada cliente/tenant do Growth OS

| Coluna | Tipo | Exemplo | Descrição |
|--------|------|---------|-----------|
| `id` | uuid | uuid | PK |
| `location_id` | text | `dr_luiz_location_001` | **ID único do tenant** |
| `client_name` | text | `Clinica Dr. Luiz` | Nome do cliente |
| `nome_empresa` | text | `Clinica Dr. Luiz - Medicina Integrativa` | Nome completo |
| `tipo_negocio` | text | `Clinica Medica / Medicina Integrativa` | Tipo de negócio |
| `oferta_principal` | text | Texto descritivo | Oferta principal |
| `dor_principal` | text | Texto descritivo | Dor do cliente |
| `publico_alvo` | text | Descrição | Público-alvo |
| `diferenciais` | text[] | `["Consultas de 1 hora", ...]` | Diferenciais |
| `faixa_preco_texto` | text | `a partir de R$ 500` | Faixa de preço |
| `mostrar_preco` | boolean | false | Mostrar preço? |
| `ticket_medio` | numeric | 800 | Ticket médio |
| `tom_agente` | text | `consultivo` | Tom do agente |
| `nome_agente` | text | `Julia` | Nome do agente IA |
| `emoji_por_mensagem` | integer | 1 | Emojis por msg |
| `canais_ativos` | text[] | `["instagram", "whatsapp"]` | Canais |
| `horario_inicio` | time | `08:00:00` | Início atendimento |
| `horario_fim` | time | `18:00:00` | Fim atendimento |
| `timezone` | text | `America/Sao_Paulo` | Timezone |
| `perguntas_qualificacao` | jsonb | `{need, budget, timeline, authority}` | Perguntas BANT |
| `calendario_url` | text | `https://calendly.com/drluiz/consulta` | URL calendário |
| `tempo_consulta_minutos` | integer | 60 | Duração consulta |
| `max_followups` | integer | 3 | Máx follow-ups |
| `intervalo_followup_horas` | integer | 24 | Intervalo FUPs |
| `telefone_humano` | text | `+55 11 99999-9999` | Tel. escalação |
| `email_humano` | text | `contato@drluiz.com.br` | Email escalação |
| `gatilhos_escalacao` | text[] | `["reclamacao", "urgencia medica", ...]` | Gatilhos |
| `segment_id` | uuid | uuid | FK segmento |
| `meta_leads_mes` | integer | 100 | Meta leads/mês |
| `meta_agendamentos_mes` | integer | 30 | Meta agendamentos |
| `meta_vendas_mes` | integer | 20 | Meta vendas |
| `meta_receita_mes` | numeric | null | Meta receita |
| `custo_por_lead` | numeric | null | CPL |
| `custo_trafego_mensal` | numeric | null | Custo tráfego |
| `status` | text | `active` | Status |
| `created_at` | timestamptz | timestamp | Criação |
| `updated_at` | timestamptz | timestamp | Atualização |

**Exemplo completo:**
```json
{
  "location_id": "dr_luiz_location_001",
  "client_name": "Clinica Dr. Luiz",
  "nome_agente": "Julia",
  "tom_agente": "consultivo",
  "canais_ativos": ["instagram", "whatsapp"],
  "horario_inicio": "08:00:00",
  "horario_fim": "18:00:00",
  "ticket_medio": 800,
  "max_followups": 3,
  "intervalo_followup_horas": 24,
  "meta_leads_mes": 100,
  "meta_agendamentos_mes": 30,
  "meta_vendas_mes": 20
}
```

---

## 3. Tabelas de Conversas e Mensagens

### 3.1 `agent_conversations`

> **Status:** POPULADA
> **Propósito:** Histórico de conversas com agentes IA

| Coluna | Tipo | Exemplo | Descrição |
|--------|------|---------|-----------|
| `id` | uuid | uuid | PK |
| `agent_version_id` | uuid | uuid | FK versão do agente |
| `contact_id` | text | `xFtXlhhyjyWQfUjsr8w3` | ID contato GHL |
| `conversation_id` | text | `xFtXlhhyjyWQfUjsr8w3` | ID conversa |
| `channel` | text | `instagram`, `whatsapp`, `ghl` | Canal |
| `status` | text | `active`, `completed` | Status |
| `outcome` | text | `in_progress`, `scheduled` | Resultado |
| `mensagens_total` | integer | 7 | Total mensagens |
| `duracao_minutos` | integer | null | Duração |
| `objecoes_detectadas` | integer | 0 | Objeções |
| `agendou_consulta` | boolean | false | Agendou? |
| `consulta_id` | text | null | ID consulta |
| `escalou_para` | text | null | Escalado para |
| `motivo_escalacao` | text | null | Motivo |
| `started_at` | timestamptz | timestamp | Início |
| `ended_at` | timestamptz | null | Fim |
| `summary` | text | null | Resumo |
| `objecoes_json` | jsonb | null | Objeções JSON |
| `qualificacao_json` | jsonb | null | Qualificação |
| `qa_analyzed` | boolean | false | QA analisado? |
| `qa_score` | decimal | 9.54 | Score QA |
| `qa_analyzed_at` | timestamptz | null | Data análise |

---

### 3.2 `agent_conversation_messages` ⭐ (5.094 registros)

> **Status:** POPULADA - 2ª tabela mais ativa
> **Propósito:** Mensagens individuais das conversas com agentes IA

| Coluna | Tipo | Exemplo | Descrição |
|--------|------|---------|-----------|
| `id` | uuid | `3f64af23-...` | PK |
| `conversation_id` | uuid | `8a1b2c3d-...` | FK para agent_conversations |
| `message_text` | text | `Olá, gostaria de agendar...` | Conteúdo da mensagem |
| `is_from_lead` | boolean | true/false | true = lead, false = agente IA |
| `created_at` | timestamptz | `2026-01-09T14:30:00Z` | Data/hora da mensagem |

**Exemplo de dados:**
```json
{
  "id": "3f64af23-1234-5678-abcd-ef0123456789",
  "conversation_id": "8a1b2c3d-4567-890a-bcde-f12345678901",
  "message_text": "Bom dia! Gostaria de saber mais sobre a consulta",
  "is_from_lead": true,
  "created_at": "2026-01-09T14:30:00Z"
}
```

**Uso típico:**
```sql
-- Buscar histórico de uma conversa
SELECT message_text, is_from_lead, created_at
FROM agent_conversation_messages
WHERE conversation_id = 'UUID_DA_CONVERSA'
ORDER BY created_at ASC;
```

---

### 3.3 `messages` ⭐ (3.660 registros)

> **Status:** POPULADA - 3ª tabela mais ativa
> **Propósito:** Mensagens gerais com embeddings para busca semântica

| Coluna | Tipo | Exemplo | Descrição |
|--------|------|---------|-----------|
| `id` | uuid | `uuid` | PK |
| `contact_id` | text | `xFtXlhhyjyWQfUjsr8w3` | ID do contato |
| `sender_name` | text | `João Silva` | Nome do remetente |
| `sender_type` | text | `lead`, `agent` | Tipo do remetente |
| `message_type` | text | `text` | Tipo da mensagem |
| `message_body` | text | `Olá, quero agendar...` | Conteúdo |
| `workflow_name` | text | `SDR Julia Amare` | Nome do workflow n8n |
| `location_name` | text | `Instituto Amar` | Nome do cliente/tenant |
| `sentiment` | text | `neutral`, `positive` | Análise de sentimento |
| `is_group_message` | boolean | false | Se é mensagem de grupo |
| `embedding` | vector(1536) | vetor | Embedding para busca semântica |
| `created_at` | timestamptz | timestamp | Data criação |

**Colunas adicionais (27 no total):**
- `conversation_id`, `message_id`, `channel`
- `contact_name`, `contact_email`, `contact_phone`
- `location_id`, `workflow_id`, `execution_id`
- `is_automated`, `automation_type`, `tags`
- `metadata` (JSONB)

**Exemplo de dados:**
```json
{
  "sender_name": "Maria Santos",
  "sender_type": "lead",
  "message_body": "Olá! Vi o post sobre tratamento capilar",
  "workflow_name": "SDR Julia Amare",
  "location_name": "Marina Couto",
  "sentiment": "positive"
}
```

---

### 3.4 `portal_conversations`

> **Status:** VAZIA
> **Propósito:** Conversas sincronizadas do GHL para o Portal CRM

| Coluna | Tipo | Default | Descrição |
|--------|------|---------|-----------|
| `id` | uuid | gen_random_uuid() | PK |
| `location_id` | text | - | **Obrigatório** - Tenant |
| `lead_id` | uuid | - | FK para growth_leads |
| `ghl_conversation_id` | text | - | ID conversa GHL |
| `ghl_contact_id` | text | - | ID contato GHL |
| `channel` | text | - | **Obrigatório** (whatsapp, sms, email, instagram) |
| `channel_account_id` | text | - | ID conta do canal |
| `status` | text | 'open' | Status (open/closed) |
| `last_message` | text | - | Última mensagem |
| `last_message_at` | timestamptz | - | Data última msg |
| `last_message_direction` | text | - | inbound/outbound |
| `last_message_type` | text | - | Tipo da msg |
| `assigned_to` | text | - | Atribuído a |
| `is_ai_responding` | boolean | false | IA respondendo? |
| `unread_count` | integer | 0 | Não lidas |
| `total_messages` | integer | 0 | Total msgs |
| `metadata` | jsonb | - | Metadados |
| `created_at` | timestamptz | now() | Criação |
| `updated_at` | timestamptz | now() | Atualização |

---

### 3.5 `portal_messages`

> **Status:** VAZIA
> **Propósito:** Mensagens das conversas do Portal

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | uuid | PK |
| `conversation_id` | uuid | FK portal_conversations |
| `location_id` | text | Tenant |
| `ghl_message_id` | text | ID mensagem GHL |
| `sender_id` | text | ID remetente |
| `sender_name` | text | Nome remetente |
| `sender_type` | text | Tipo remetente |
| `direction` | text | inbound/outbound |
| `content` | text | Conteúdo |
| `content_type` | text | Tipo conteúdo |
| `media_url` | text | URL mídia |
| `media_metadata` | jsonb | Metadados mídia |
| `metadata` | jsonb | Metadados gerais |
| `status` | text | Status |
| `status_updated_at` | timestamptz | Atualização status |
| `is_from_ai` | boolean | Enviado por IA? |
| `ai_agent_code` | text | Código agente IA |
| `ai_model` | text | Modelo IA |
| `sent_at` | timestamptz | Enviado em |
| `delivered_at` | timestamptz | Entregue em |
| `read_at` | timestamptz | Lido em |
| `error_message` | text | Erro |
| `created_at` | timestamptz | Criação |

---

## 4. Tabelas de Prospecção Instagram

### 4.1 `agentic_instagram_leads`

> **Status:** POPULADA - 5 registros
> **Propósito:** Leads descobertos via scraping Instagram

| Coluna | Tipo | Exemplo | Descrição |
|--------|------|---------|-----------|
| `id` | serial | 1, 2, 3... | PK auto-increment |
| `username` | text | `entrepreneur_daily` | Username Instagram |
| `full_name` | text | `John Smith` | Nome completo |
| `bio` | text | null | Bio (geralmente null) |
| `source` | text | `sample`, `test` | Fonte |
| `created_at` | timestamptz | timestamp | Criação |

---

### 4.2 `agentic_instagram_dm_sent`

> **Status:** POPULADA - 5 registros
> **Propósito:** DMs enviadas pelo agente de prospecção

| Coluna | Tipo | Exemplo | Descrição |
|--------|------|---------|-----------|
| `id` | serial | 1, 2, 3... | PK |
| `lead_id` | integer | 1 | FK agentic_instagram_leads |
| `username` | text | `marketing_tips` | Username destino |
| `message_template` | text | `smart_fallback`, `smart_cold`, `smart_warm` | Template usado |
| `message_sent` | text | Texto completo | Mensagem enviada |
| `sent_at` | timestamptz | timestamp | Data envio |
| `status` | text | `sent`, `failed` | Status |
| `error_message` | text | `User not found in search` | Erro (se houver) |
| `account_used` | text | `marcosdanielsf` | Conta usada |

**Templates de mensagem:**
- `smart_fallback` - Mensagem genérica
- `smart_cold` - Primeira abordagem fria
- `smart_warm` - Abordagem mais quente

---

## 5. Tabelas do Portal CRM

### 5.1 `portal_users`

> **Status:** VAZIA
> **Propósito:** Usuários do Portal CRM

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | uuid | PK (ref auth.users) |
| `email` | text | Email único |
| `name` | text | Nome |
| `location_id` | text | Tenant |
| `role` | text | admin/manager/viewer |
| `avatar_url` | text | Avatar |
| `phone` | text | Telefone |
| `is_active` | boolean | Ativo? |
| `last_login_at` | timestamptz | Último login |
| `created_at` | timestamptz | Criação |
| `updated_at` | timestamptz | Atualização |

---

### 5.2 `portal_metrics_daily`

> **Status:** VAZIA
> **Propósito:** Métricas diárias do portal com breakdown outbound/inbound

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | uuid | PK |
| `location_id` | text | Tenant |
| `date` | date | Data |
| `funnel_prospected` | integer | Prospectados |
| `funnel_lead` | integer | Leads |
| `funnel_qualified` | integer | Qualificados |
| `funnel_scheduled` | integer | Agendados |
| `funnel_showed` | integer | Compareceram |
| `funnel_no_show` | integer | No-shows |
| `funnel_proposal` | integer | Propostas |
| `funnel_won` | integer | Ganhos |
| `funnel_lost` | integer | Perdidos |
| `outbound_prospected` | integer | Outbound prospectados |
| `outbound_leads` | integer | Outbound leads |
| `inbound_leads` | integer | Inbound leads |
| `rate_lead` | numeric | Taxa lead |
| `rate_qualification` | numeric | Taxa qualificação |
| `rate_scheduling` | numeric | Taxa agendamento |
| `rate_show` | numeric | Show rate |
| `rate_closing` | numeric | Taxa fechamento |
| `total_revenue` | numeric | Receita total |
| `avg_ticket` | numeric | Ticket médio |
| `cost_traffic` | numeric | Custo tráfego |
| `cost_per_lead` | numeric | CPL |
| `roi` | numeric | ROI |
| `created_at` | timestamptz | Criação |

---

## 6. Tabelas de Métricas e Analytics

### 6.1 `growth_funnel_daily`

> **Status:** VAZIA
> **Propósito:** Métricas diárias do funil Growth OS

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `id` | uuid | PK |
| `date` | date | Data |
| `location_id` | text | Tenant |
| `funnel_name` | text | Nome do funil |
| `source_channel` | text | Canal origem |
| `agent_code` | text | Código agente |
| **Contagens** | | |
| `lead_count` | integer | Leads |
| `prospected_count` | integer | Prospectados |
| `qualified_count` | integer | Qualificados |
| `scheduled_count` | integer | Agendados |
| `showed_count` | integer | Compareceram |
| `no_show_count` | integer | No-shows |
| `proposal_count` | integer | Propostas |
| `won_count` | integer | Ganhos |
| `lost_count` | integer | Perdidos |
| **Taxas** | | |
| `lead_rate` | numeric | Taxa leads |
| `qualification_rate` | numeric | Taxa qualificação |
| `scheduling_rate` | numeric | Taxa agendamento |
| `show_rate` | numeric | Show rate |
| `closing_rate` | numeric | Taxa fechamento |
| `total_conversion_rate` | numeric | Conversão total |
| **Financeiro** | | |
| `cost_spent` | numeric | Custo |
| `cpl` | numeric | CPL |
| `cpa` | numeric | CPA |
| `avg_ticket` | numeric | Ticket médio |
| `total_proposal_value` | numeric | Valor propostas |
| `total_won_value` | numeric | Valor vendas |
| `roi_percentage` | numeric | ROI % |
| **Tempos** | | |
| `avg_time_to_lead_hours` | numeric | Tempo até lead |
| `avg_time_to_qualified_hours` | numeric | Tempo até qualificado |
| `avg_time_to_scheduled_hours` | numeric | Tempo até agendado |
| `avg_time_to_close_hours` | numeric | Tempo até fechamento |
| `created_at` | timestamptz | Criação |

---

### 6.2 `llm_costs`

> **Status:** POPULADA
> **Propósito:** Custos de uso de LLMs

| Coluna | Tipo | Exemplo | Descrição |
|--------|------|---------|-----------|
| `id` | uuid | uuid | PK |
| `created_at` | timestamptz | timestamp | Criação |
| `workflow_id` | text | `GWKl5KuXAdeu4BLr` | ID workflow n8n |
| `workflow_name` | text | `[TOOL] Registrar Custo IA` | Nome workflow |
| `execution_id` | text | `428550` | ID execução |
| `location_id` | text | `Bgi2hFMgiLLoRlOO0K5b` | Location GHL |
| `location_name` | text | `Marina Couto` | Nome location |
| `contact_id` | text | null | ID contato |
| `contact_name` | text | `Fatma` | Nome contato |
| `modelo_ia` | text | `gemini-2.0-flash` | Modelo usado |
| `tokens_input` | integer | 500 | Tokens entrada |
| `tokens_output` | integer | 50 | Tokens saída |
| `custo_usd` | decimal | 0.00007 | Custo USD |
| `canal` | text | `instagram` | Canal |
| `tipo_acao` | text | `Agendar` | Tipo de ação |
| `mensagem_entrada` | text | null | Mensagem entrada |
| `mensagem_saida` | text | null | Mensagem saída |
| `consolidado` | boolean | false | Consolidado? |
| `consolidado_em` | timestamptz | null | Data consolidação |

---

## 7. Tabelas Financeiras

### 7.1 `fin_movimentacoes`

> **Status:** POPULADA
> **Propósito:** Movimentações financeiras (despesas/receitas)

| Coluna | Tipo | Exemplo | Descrição |
|--------|------|---------|-----------|
| `id` | uuid | uuid | PK |
| `tipo` | text | `despesa` | Tipo |
| `tipo_entidade` | text | `pf`, `pj` | PF ou PJ |
| `descricao` | text | `Apple.com/bill` | Descrição |
| `data_competencia` | date | null | Competência |
| `data_vencimento` | date | `2025-11-16` | Vencimento |
| `data_realizado` | date | null | Realização |
| `data_conciliacao` | date | null | Conciliação |
| `valor_previsto` | decimal | 39.90 | Valor previsto |
| `valor_realizado` | decimal | 39.90 | Valor realizado |
| `cliente_fornecedor_id` | uuid | null | FK cliente/fornecedor |
| `categoria_id` | uuid | null | FK categoria |
| `conta_bancaria_id` | uuid | null | FK conta |
| `centro_custo_id` | uuid | null | FK centro custo |
| `quitado` | boolean | false | Quitado? |
| `conciliado` | boolean | false | Conciliado? |
| `forma_pagamento_parcela` | text | null | Forma pgto |
| `numero_nota_fiscal` | text | null | NF |
| `observacao` | text | null | Obs |
| `created_at` | timestamptz | timestamp | Criação |
| `updated_at` | timestamptz | timestamp | Atualização |

---

### 7.2 `fin_categorias` ⭐ (123 registros)

> **Status:** POPULADA - Categorias financeiras
> **Propósito:** Categorização hierárquica de receitas e despesas

| Coluna | Tipo | Exemplo | Descrição |
|--------|------|---------|-----------|
| `id` | uuid | `uuid` | PK |
| `nome` | text | `Assinaturas SaaS`, `Salários` | Nome da categoria |
| `categoria_pai_id` | uuid | null ou uuid | FK para categoria pai (hierarquia) |
| `tipo` | text | `receita`, `despesa` | Tipo da categoria |
| `ativo` | boolean | true | Se está ativa |
| `cor` | text | `#4CAF50`, `#F44336` | Cor para display |
| `icone` | text | `credit-card`, `building` | Ícone para display |
| `ordem` | integer | 1, 2, 3... | Ordem de exibição |
| `created_at` | timestamptz | timestamp | Data criação |

**Hierarquia de categorias:**
```
Despesas (categoria_pai_id = null)
├── Infraestrutura
│   ├── Assinaturas SaaS
│   ├── Servidores
│   └── Domínios
├── Marketing
│   ├── Tráfego Pago
│   └── Conteúdo
└── Operacional
    ├── Salários
    └── Impostos
```

**Exemplo de dados:**
```json
{
  "nome": "Assinaturas SaaS",
  "tipo": "despesa",
  "cor": "#9C27B0",
  "icone": "credit-card",
  "ativo": true,
  "categoria_pai_id": "uuid-da-categoria-infraestrutura"
}
```

---

## 8. Tabelas de IA/RAG

### 8.1 `rag_knowledge` (Segundo Cérebro)

> **Status:** POPULADA - 5+ registros
> **Propósito:** Base de conhecimento com embeddings para busca semântica

| Coluna | Tipo | Exemplo | Descrição |
|--------|------|---------|-----------|
| `id` | uuid | uuid | PK |
| `category` | text | `rule`, `pattern`, `error_fix`, `workflow` | Categoria |
| `title` | text | `Arquitetura RAG com pgvector` | Título |
| `content` | text | Conteúdo longo | Conteúdo |
| `project_key` | text | `segundo-cerebro`, `socialfy` | Projeto |
| `tags` | text[] | `["arquitetura", "pgvector"]` | Tags |
| `source` | text | `api-2026-01-03` | Fonte |
| `embedding` | vector(1536) | Vetor | Embedding OpenAI |
| `confidence` | numeric | 1 | Confiança |
| `usage_count` | integer | 0 | Uso |
| `last_used_at` | timestamptz | null | Último uso |
| `created_at` | timestamptz | timestamp | Criação |
| `updated_at` | timestamptz | timestamp | Atualização |
| `created_by` | text | `api-server` | Criador |

**Categorias válidas:**
- `schema` - Estruturas de banco
- `pattern` - Padrões de código
- `rule` - Regras de negócio
- `decision` - Decisões técnicas
- `error_fix` - Correções de erros
- `workflow` - Workflows/automações
- `api` - Endpoints/integrações
- `system_config` - Configurações

---

## 9. Tabelas de Integração n8n

### 9.1 `n8n_active_conversation` ⭐ (618 registros)

> **Status:** POPULADA - 4ª tabela mais ativa
> **Propósito:** Conversas ativas gerenciadas pelo n8n (controle de fluxo)

| Coluna | Tipo | Exemplo | Descrição |
|--------|------|---------|-----------|
| `id` | text | `rec_abc123` | ID único do registro |
| `lead_id` | text | `xFtXlhhyjyWQfUjsr8w3` | ID do lead no GHL |
| `lead_name` | text | `Maria Silva` | Nome do lead |
| `status` | text | `active`, `paused`, `completed` | Status da conversa |
| `owner_id` | text | `user_123` | ID do usuário/owner |
| `workflow_id` | text | `wf_SDR_Julia` | ID do workflow n8n |
| `retries` | integer | 0, 1, 2 | Número de tentativas |
| `last_message_at` | timestamptz | timestamp | Última mensagem |
| `created_at` | timestamptz | timestamp | Criação |
| `updated_at` | timestamptz | timestamp | Atualização |

**Uso típico:**
```sql
-- Conversas ativas para processar
SELECT lead_id, lead_name, workflow_id, retries
FROM n8n_active_conversation
WHERE status = 'active'
  AND retries < 3
ORDER BY last_message_at DESC;
```

---

### 9.2 `n8n_historico_mensagens` ⭐ (194 registros)

> **Status:** POPULADA
> **Propósito:** Histórico de mensagens para memória de contexto nos workflows n8n

| Coluna | Tipo | Exemplo | Descrição |
|--------|------|---------|-----------|
| `id` | serial | 1, 2, 3... | PK auto-increment |
| `session_id` | text | `sess_abc123` | ID da sessão de conversa |
| `message` | jsonb | `{type, content}` | Mensagem em formato JSONB |
| `message_hash` | text | `md5_hash` | Hash MD5 para deduplicação |
| `location_id` | text | `Bgi2hFMgiLLoRlOO0K5b` | Location GHL |
| `created_at` | timestamptz | timestamp | Data criação |

**Estrutura do campo `message` (JSONB):**
```json
{
  "type": "ai",       // ou "human"
  "content": "Olá! Como posso ajudar você hoje?"
}
```

**Tipos de mensagem:**
- `ai` - Mensagem do agente IA
- `human` - Mensagem do lead/humano

**Uso típico:**
```sql
-- Buscar histórico de uma sessão
SELECT message->>'type' as tipo,
       message->>'content' as conteudo,
       created_at
FROM n8n_historico_mensagens
WHERE session_id = 'SESSAO_ID'
ORDER BY created_at ASC;
```

---

## 10. Tabelas Claude Code

### 10.1 `claude_conversations` ⭐ (177 registros)

> **Status:** POPULADA
> **Propósito:** Histórico de conversas com Claude Code (memória persistente)

| Coluna | Tipo | Exemplo | Descrição |
|--------|------|---------|-----------|
| `id` | uuid | `uuid` | PK |
| `session_id` | text | `sess_20260109_abc123` | ID único da sessão |
| `project_key` | text | `socialfy`, `ai-factory-agents` | Projeto relacionado |
| `role` | text | `assistant`, `user` | Papel (IA ou usuário) |
| `content` | text | Texto da mensagem | Conteúdo da mensagem |
| `platform` | text | `claude-code` | Plataforma de origem |
| `ai_model_used` | text | `claude-sonnet-4-5`, `claude-opus-4-5` | Modelo utilizado |
| `session_status` | text | `active`, `completed` | Status da sessão |
| `tokens_input` | integer | 1500 | Tokens de entrada |
| `tokens_output` | integer | 800 | Tokens de saída |
| `cost_usd` | decimal | 0.0045 | Custo em USD |
| `execution_time_ms` | integer | 2500 | Tempo de execução |
| `error_message` | text | null | Erro (se houver) |
| `metadata` | jsonb | `{}` | Metadados adicionais |
| `created_at` | timestamptz | timestamp | Data criação |
| `updated_at` | timestamptz | timestamp | Atualização |

**Project keys conhecidos:**
- `socialfy` - Socialfy CRM
- `ai-factory-agents` - Agentes de IA
- `segundo-cerebro` - Sistema RAG
- `mottivme-geral` - Operações gerais
- `assembly-line` - Assembly Line SaaS

**Exemplo de dados:**
```json
{
  "session_id": "sess_20260109_abc123",
  "project_key": "socialfy",
  "role": "assistant",
  "content": "Vou analisar a estrutura do banco de dados...",
  "platform": "claude-code",
  "ai_model_used": "claude-sonnet-4-5",
  "session_status": "active"
}
```

**Uso típico:**
```sql
-- Buscar últimas conversas de um projeto
SELECT session_id, role, content, ai_model_used, created_at
FROM claude_conversations
WHERE project_key = 'socialfy'
ORDER BY created_at DESC
LIMIT 20;

-- Custo total por projeto
SELECT project_key,
       SUM(cost_usd) as custo_total,
       COUNT(*) as total_mensagens
FROM claude_conversations
GROUP BY project_key
ORDER BY custo_total DESC;
```

---

## 11. Relacionamentos Entre Tabelas

```
┌─────────────────────────────────────────────────────────────────────┐
│                    RELACIONAMENTOS PRINCIPAIS                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  growth_client_configs                                               │
│       │                                                              │
│       │ location_id                                                  │
│       ▼                                                              │
│  growth_leads ◄──────────────► portal_conversations                  │
│       │              lead_id          │                              │
│       │                               │                              │
│       │                               ▼                              │
│       │                        portal_messages                       │
│       │                                                              │
│       │ ghl_contact_id                                               │
│       ▼                                                              │
│  socialfy_leads ◄─────────────► crm_leads                           │
│       │                               │                              │
│       │                               │                              │
│       ▼                               ▼                              │
│  agentic_instagram_leads      agent_conversations                    │
│       │                               │                              │
│       │ lead_id                       │ conversation_id              │
│       ▼                               ▼                              │
│  agentic_instagram_dm_sent    agent_conversation_messages            │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                     TABELAS DE INTEGRAÇÃO                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  n8n_active_conversation ◄───────► n8n_historico_mensagens          │
│       │    (lead_id)                     (session_id)               │
│       │                                                              │
│       │ location_id                                                  │
│       ▼                                                              │
│  messages ◄────────────────────► llm_costs                          │
│  (com embeddings)                 (custos de IA)                    │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                     TABELAS FINANCEIRAS                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  fin_categorias (hierárquica)                                        │
│       │                                                              │
│       │ categoria_id                                                 │
│       ▼                                                              │
│  fin_movimentacoes                                                   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

Chaves de Relacionamento:
- location_id: Identifica o tenant/cliente (multi-tenant)
- ghl_contact_id: ID do contato no GoHighLevel
- lead_id: FK entre tabelas de leads
- conversation_id: FK entre conversas e mensagens
- session_id: ID de sessão para histórico de mensagens n8n
- categoria_id: FK para categorias financeiras
```

---

## 12. Enums e Valores Válidos

### Funnel Stages (Growth OS)
```
prospected → lead → qualified → scheduled → showed → proposal → won
                                    ↓
                                 no_show → lost
```

### Source Channels

**Outbound:**
- `instagram_dm` - DM do Instagram
- `linkedin` - LinkedIn
- `cold_email` - Email frio
- `cold_call` - Ligação fria

**Inbound:**
- `ads` - Facebook/Instagram Ads
- `facebook_ads` - Facebook Ads
- `instagram_ads` - Instagram Ads
- `google_ads` - Google Ads
- `whatsapp` - WhatsApp direto
- `referral` - Indicação
- `organic` - Orgânico
- `inbound_call` - Ligação recebida

### Lead Temperature
- `cold` - Frio
- `warm` - Morno
- `hot` - Quente

### ICP Tiers
- `A` - Melhor fit
- `B` - Bom fit
- `C` - Fit médio
- `D` - Baixo fit

### Conversation Status
- `open` - Aberta
- `closed` - Fechada
- `active` - Ativa
- `completed` - Completa

### Message Direction
- `inbound` - Entrada (lead → empresa)
- `outbound` - Saída (empresa → lead)

---

## Consultas Úteis

### Leads por etapa do funil
```sql
SELECT funnel_stage, COUNT(*)
FROM growth_leads
WHERE location_id = 'SEU_LOCATION_ID'
GROUP BY funnel_stage;
```

### Leads outbound vs inbound
```sql
SELECT
  CASE
    WHEN source_channel IN ('instagram_dm', 'linkedin', 'cold_email', 'cold_call')
    THEN 'outbound'
    ELSE 'inbound'
  END as source_type,
  COUNT(*)
FROM growth_leads
WHERE location_id = 'SEU_LOCATION_ID'
GROUP BY source_type;
```

### Conversas com último contato
```sql
SELECT
  c.*,
  l.name as lead_name,
  l.funnel_stage
FROM portal_conversations c
JOIN growth_leads l ON l.id = c.lead_id
WHERE c.location_id = 'SEU_LOCATION_ID'
ORDER BY c.last_message_at DESC
LIMIT 50;
```

### Métricas do funil
```sql
SELECT
  date,
  funnel_prospected,
  funnel_lead,
  funnel_qualified,
  funnel_scheduled,
  funnel_showed,
  funnel_won,
  rate_show,
  rate_closing
FROM portal_metrics_daily
WHERE location_id = 'SEU_LOCATION_ID'
ORDER BY date DESC;
```

---

## Views Disponíveis

### Portal CRM
- `portal_vw_dashboard_summary` - Resumo do dashboard
- `portal_vw_funnel_by_source` - Funil por fonte
- `portal_vw_recent_conversations` - Conversas recentes

### Growth OS
- `growth_vw_agent_performance` - Performance dos agentes
- `growth_vw_funnel_by_channel` - Funil por canal
- `growth_vw_funnel_by_client` - Funil por cliente
- `growth_vw_funnel_global` - Funil global

### Socialfy
- `vw_socialfy_leads_by_vertical` - Leads por vertical
- `vw_socialfy_leads_for_ghl` - Leads formatados para GHL

---

## Notas Importantes

1. **Multi-tenant:** Use sempre `location_id` para filtrar dados por cliente
2. **RLS:** Tabelas do portal têm Row Level Security habilitado
3. **Embeddings:** Tabelas `rag_knowledge` e `messages` usam pgvector para busca semântica
4. **GHL IDs:** Campos `ghl_contact_id` e `ghl_conversation_id` linkam com GoHighLevel
5. **Timestamps:** Use `timestamptz` (com timezone) para datas
6. **n8n Integration:** Tabelas `n8n_active_conversation` e `n8n_historico_mensagens` para controle de fluxo
7. **Claude Code:** Tabela `claude_conversations` para memória persistente de sessões

---

> **Gerado em:** 2026-01-09
> **Atualizado em:** 2026-01-09 (adicionadas 6 tabelas mais ativas)
> **Autor:** Claude Code
> **Projeto:** MOTTIVME Sales
> **Tabelas documentadas:** 20
