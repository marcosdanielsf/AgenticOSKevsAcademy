-- =============================================================================
-- Migration: Growth OS - Sistema Universal de Agentes de Vendas
-- Date: 2026-01-04
-- Author: Claude Code + Marcos Daniels
-- =============================================================================
--
-- ARQUITETURA: 19 Agentes Hiperespecializados
-- - 14 Operacionais (cada um especialista em UM canal/processo)
-- - 5 Gestao (Diretor Comercial, 3 Gerentes, Sales Ops)
--
-- PREFIXO: growth_ (validado como seguro - nao conflita com outras tabelas)
--
-- DASHBOARD: Estrutura otimizada para metricas de gestao comercial
-- - Visao Global (todos os clientes)
-- - Visao por Cliente (location_id)
-- - Visao por Agente/Funcionario
-- - Visao por Canal/Processo
-- - Visao por Funil/Etapa
-- =============================================================================

-- =============================================================================
-- 1. LEADS DO GROWTH OS (Tabela central - inspirada no socialfy_leads)
-- =============================================================================
CREATE TABLE IF NOT EXISTS growth_leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Relacionamentos
    location_id TEXT NOT NULL,              -- GHL Location ID (cliente)
    ghl_contact_id TEXT,                    -- ID do GoHighLevel

    -- Dados Basicos
    name TEXT,
    email TEXT,
    phone TEXT,
    company TEXT,
    title TEXT,                             -- Cargo
    avatar_url TEXT,

    -- Canais de Contato
    instagram_username TEXT,
    linkedin_url TEXT,
    whatsapp TEXT,

    -- Origem e Atribuicao
    source_channel TEXT NOT NULL,           -- 'instagram_dm', 'cold_email', 'cold_call', 'inbound_call', 'linkedin', 'referral', 'reactivation', 'ads'
    source_campaign TEXT,                   -- ID da campanha de origem
    source_agent_code TEXT,                 -- Agente que gerou o lead
    assigned_agent_code TEXT,               -- Agente atualmente responsavel
    assigned_user_id TEXT,                  -- ID do vendedor humano (se escalado)

    -- Funil de Vendas (ETAPAS DO DASHBOARD)
    funnel_stage TEXT DEFAULT 'prospected', -- 'prospected', 'lead', 'qualified', 'scheduled', 'showed', 'proposal', 'won', 'lost', 'no_show'
    previous_stage TEXT,                    -- Etapa anterior (para calcular conversao)
    stage_changed_at TIMESTAMPTZ,

    -- Qualificacao BANT
    bant_budget_score INTEGER DEFAULT 0,    -- 0-25
    bant_authority_score INTEGER DEFAULT 0, -- 0-25
    bant_need_score INTEGER DEFAULT 0,      -- 0-25
    bant_timeline_score INTEGER DEFAULT 0,  -- 0-25
    bant_total_score INTEGER GENERATED ALWAYS AS (bant_budget_score + bant_authority_score + bant_need_score + bant_timeline_score) STORED,

    -- Score e Status
    lead_score INTEGER DEFAULT 0,           -- 0-100 (calculado por IA)
    lead_temperature TEXT DEFAULT 'cold',   -- 'cold', 'warm', 'hot'
    icp_score INTEGER DEFAULT 0,            -- 0-100 (fit com ICP)

    -- Engagement
    total_messages_sent INTEGER DEFAULT 0,
    total_messages_received INTEGER DEFAULT 0,
    total_calls INTEGER DEFAULT 0,
    total_meetings INTEGER DEFAULT 0,
    last_contact_at TIMESTAMPTZ,
    last_response_at TIMESTAMPTZ,
    response_time_avg_hours NUMERIC(10,2),

    -- Agendamento
    meeting_scheduled_at TIMESTAMPTZ,
    meeting_type TEXT,                      -- 'discovery', 'demo', 'proposal', 'closing'
    meeting_show_status TEXT,               -- 'pending', 'showed', 'no_show', 'rescheduled', 'cancelled'

    -- Proposta e Fechamento
    proposal_sent_at TIMESTAMPTZ,
    proposal_value NUMERIC(15,2),
    proposal_status TEXT,                   -- 'sent', 'viewed', 'accepted', 'rejected', 'negotiating'

    -- Conversao
    converted_at TIMESTAMPTZ,
    conversion_value NUMERIC(15,2),
    lost_at TIMESTAMPTZ,
    lost_reason TEXT,
    lost_competitor TEXT,

    -- Reativacao
    reactivation_count INTEGER DEFAULT 0,
    last_reactivation_at TIMESTAMPTZ,
    reactivation_responded BOOLEAN DEFAULT false,

    -- Sentimento e Objecoes
    sentiment_score NUMERIC(3,2),           -- -1 a 1
    detected_objections TEXT[],             -- Array de objecoes identificadas

    -- Custom Fields (flexibilidade)
    custom_fields JSONB DEFAULT '{}'::jsonb,
    tags TEXT[] DEFAULT '{}',

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    UNIQUE(location_id, ghl_contact_id)
);

-- Indices para performance
CREATE INDEX IF NOT EXISTS idx_growth_leads_location ON growth_leads(location_id);
CREATE INDEX IF NOT EXISTS idx_growth_leads_ghl ON growth_leads(ghl_contact_id);
CREATE INDEX IF NOT EXISTS idx_growth_leads_stage ON growth_leads(funnel_stage);
CREATE INDEX IF NOT EXISTS idx_growth_leads_source ON growth_leads(source_channel);
CREATE INDEX IF NOT EXISTS idx_growth_leads_agent ON growth_leads(assigned_agent_code);
CREATE INDEX IF NOT EXISTS idx_growth_leads_temperature ON growth_leads(lead_temperature);
CREATE INDEX IF NOT EXISTS idx_growth_leads_score ON growth_leads(lead_score DESC);
CREATE INDEX IF NOT EXISTS idx_growth_leads_meeting ON growth_leads(meeting_scheduled_at) WHERE meeting_scheduled_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_growth_leads_created ON growth_leads(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_growth_leads_tags ON growth_leads USING GIN(tags);

-- =============================================================================
-- 2. TEMPLATES DE AGENTES (Base universal para todos os clientes)
-- =============================================================================
CREATE TABLE IF NOT EXISTS growth_agent_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identificacao
    agent_code TEXT NOT NULL UNIQUE,        -- Ex: 'social_seller_instagram', 'sdr_inbound'
    agent_name TEXT NOT NULL,
    agent_category TEXT NOT NULL,           -- 'prospeccao_ativa', 'inbound', 'conversao', 'gestao'

    -- Hierarquia
    agent_level TEXT NOT NULL DEFAULT 'operacional',  -- 'operacional', 'tatico', 'estrategico'
    reports_to TEXT,                        -- agent_code do superior

    -- Especializacao
    channel TEXT,                           -- 'instagram', 'linkedin', 'whatsapp', 'email', 'phone'
    process_type TEXT,                      -- 'outbound', 'inbound', 'nurturing', 'closing', 'management'

    -- Prompt Base
    system_prompt_template TEXT NOT NULL,

    -- Modos de Operacao
    available_modes TEXT[] DEFAULT '{"first_contact", "qualifier", "scheduler", "followuper"}',

    -- Few-shot Examples
    few_shot_examples JSONB DEFAULT '[]'::jsonb,

    -- Gatilhos de Handoff
    handoff_triggers JSONB DEFAULT '[]'::jsonb,

    -- Metricas Esperadas
    expected_metrics JSONB DEFAULT '{}'::jsonb,

    -- Metadata
    version TEXT DEFAULT '1.0.0',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_growth_agent_templates_code ON growth_agent_templates(agent_code);
CREATE INDEX IF NOT EXISTS idx_growth_agent_templates_category ON growth_agent_templates(agent_category);

-- =============================================================================
-- 3. ESTRATEGIAS POR SEGMENTO (Customizacao por nicho)
-- =============================================================================
CREATE TABLE IF NOT EXISTS growth_segment_strategies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    segment_code TEXT NOT NULL UNIQUE,
    segment_name TEXT NOT NULL,

    typical_pain_points TEXT[],
    typical_objections TEXT[],
    typical_buyer_persona JSONB,

    tone_adjustments JSONB,
    vocabulary_preferences TEXT[],
    forbidden_words TEXT[],

    bant_questions JSONB,
    price_handling_strategy TEXT,
    value_anchors TEXT[],

    best_contact_hours JSONB,
    followup_intervals JSONB,

    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_growth_segment_code ON growth_segment_strategies(segment_code);

-- =============================================================================
-- 4. CONFIGURACAO DO CLIENTE
-- =============================================================================
CREATE TABLE IF NOT EXISTS growth_client_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    location_id TEXT NOT NULL UNIQUE,
    client_name TEXT NOT NULL,

    -- Variaveis de Contexto
    nome_empresa TEXT NOT NULL,
    tipo_negocio TEXT NOT NULL,
    oferta_principal TEXT NOT NULL,
    dor_principal TEXT NOT NULL,
    publico_alvo TEXT NOT NULL,
    diferenciais TEXT[] NOT NULL,

    -- Precos
    faixa_preco_texto TEXT,
    mostrar_preco BOOLEAN DEFAULT false,
    ticket_medio NUMERIC(15,2),

    -- Personalidade
    tom_agente TEXT DEFAULT 'consultivo',
    nome_agente TEXT DEFAULT 'Assistente',
    emoji_por_mensagem INTEGER DEFAULT 1,

    -- Canais
    canais_ativos TEXT[] DEFAULT '{"instagram", "whatsapp"}',

    -- Horarios
    horario_inicio TIME DEFAULT '08:00',
    horario_fim TIME DEFAULT '20:00',
    timezone TEXT DEFAULT 'America/Sao_Paulo',

    -- Qualificacao
    perguntas_qualificacao JSONB,

    -- Agendamento
    calendario_url TEXT,
    tempo_consulta_minutos INTEGER DEFAULT 30,

    -- Follow-up
    max_followups INTEGER DEFAULT 3,
    intervalo_followup_horas INTEGER DEFAULT 24,

    -- Escalacao
    telefone_humano TEXT,
    email_humano TEXT,
    gatilhos_escalacao TEXT[],

    -- Segmento
    segment_id UUID REFERENCES growth_segment_strategies(id),

    -- Metas Mensais (para dashboard)
    meta_leads_mes INTEGER,
    meta_agendamentos_mes INTEGER,
    meta_vendas_mes INTEGER,
    meta_receita_mes NUMERIC(15,2),

    -- Custos (para ROI)
    custo_por_lead NUMERIC(10,2),
    custo_trafego_mensal NUMERIC(15,2),

    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_growth_client_configs_location ON growth_client_configs(location_id);

-- =============================================================================
-- 5. INSTANCIAS DE AGENTES POR CLIENTE
-- =============================================================================
CREATE TABLE IF NOT EXISTS growth_client_agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    template_id UUID REFERENCES growth_agent_templates(id),
    config_id UUID REFERENCES growth_client_configs(id),
    location_id TEXT NOT NULL,

    agent_instance_name TEXT,
    compiled_prompt TEXT NOT NULL,
    client_variables JSONB NOT NULL,

    status TEXT DEFAULT 'active',

    -- Performance Acumulada
    total_conversations INTEGER DEFAULT 0,
    total_conversions INTEGER DEFAULT 0,
    avg_response_time_seconds INTEGER,
    current_conversion_rate NUMERIC(5,4),

    last_activity_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(template_id, location_id)
);

CREATE INDEX IF NOT EXISTS idx_growth_client_agents_location ON growth_client_agents(location_id);

-- =============================================================================
-- 6. ATIVIDADES/TOUCHPOINTS (Cada interacao com lead)
-- =============================================================================
CREATE TABLE IF NOT EXISTS growth_activities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Relacionamentos
    lead_id UUID NOT NULL REFERENCES growth_leads(id) ON DELETE CASCADE,
    location_id TEXT NOT NULL,
    agent_code TEXT,                        -- Agente que executou
    user_id TEXT,                           -- Vendedor humano (se aplicavel)

    -- Tipo de Atividade
    activity_type TEXT NOT NULL,            -- 'message', 'call', 'meeting', 'proposal', 'note', 'stage_change', 'handoff'
    channel TEXT,                           -- 'instagram', 'whatsapp', 'email', 'phone', 'linkedin'
    direction TEXT,                         -- 'inbound', 'outbound'

    -- Conteudo
    subject TEXT,
    content TEXT,

    -- Status
    status TEXT DEFAULT 'completed',        -- 'scheduled', 'completed', 'failed', 'cancelled'
    result TEXT,                            -- 'positive', 'negative', 'neutral', 'no_answer'

    -- Metricas
    duration_seconds INTEGER,               -- Para calls
    response_received BOOLEAN DEFAULT false,
    response_time_seconds INTEGER,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    performed_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_growth_activities_lead ON growth_activities(lead_id);
CREATE INDEX IF NOT EXISTS idx_growth_activities_location ON growth_activities(location_id);
CREATE INDEX IF NOT EXISTS idx_growth_activities_type ON growth_activities(activity_type);
CREATE INDEX IF NOT EXISTS idx_growth_activities_channel ON growth_activities(channel);
CREATE INDEX IF NOT EXISTS idx_growth_activities_agent ON growth_activities(agent_code);
CREATE INDEX IF NOT EXISTS idx_growth_activities_date ON growth_activities(performed_at DESC);

-- =============================================================================
-- 7. FUNIL DIARIO (Metricas agregadas por dia - BASE DO DASHBOARD)
-- =============================================================================
CREATE TABLE IF NOT EXISTS growth_funnel_daily (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Dimensoes
    date DATE NOT NULL,
    location_id TEXT NOT NULL,
    source_channel TEXT,                    -- NULL = total de todos os canais
    agent_code TEXT,                        -- NULL = total de todos os agentes
    funnel_name TEXT DEFAULT 'principal',   -- Para multiplos funis

    -- Volume por Etapa (como no dashboard que voce mostrou)
    prospected_count INTEGER DEFAULT 0,     -- Prospecao
    lead_count INTEGER DEFAULT 0,           -- Leads gerados
    qualified_count INTEGER DEFAULT 0,      -- Qualificados
    scheduled_count INTEGER DEFAULT 0,      -- Agendados
    showed_count INTEGER DEFAULT 0,         -- Compareceram
    no_show_count INTEGER DEFAULT 0,        -- No-show
    proposal_count INTEGER DEFAULT 0,       -- Proposta enviada
    won_count INTEGER DEFAULT 0,            -- Ganhos
    lost_count INTEGER DEFAULT 0,           -- Perdidos

    -- Taxas de Conversao (calculadas)
    lead_rate NUMERIC(5,2) DEFAULT 0,       -- lead/prospected
    qualification_rate NUMERIC(5,2) DEFAULT 0,
    scheduling_rate NUMERIC(5,2) DEFAULT 0,
    show_rate NUMERIC(5,2) DEFAULT 0,
    closing_rate NUMERIC(5,2) DEFAULT 0,
    total_conversion_rate NUMERIC(5,2) DEFAULT 0,  -- won/prospected

    -- Valores
    total_proposal_value NUMERIC(15,2) DEFAULT 0,
    total_won_value NUMERIC(15,2) DEFAULT 0,
    avg_ticket NUMERIC(15,2) DEFAULT 0,

    -- Custos e ROI
    cost_spent NUMERIC(15,2) DEFAULT 0,     -- Custo do dia
    cpl NUMERIC(10,2) DEFAULT 0,            -- Custo por Lead
    cpa NUMERIC(10,2) DEFAULT 0,            -- Custo por Aquisicao
    roi_percentage NUMERIC(10,2) DEFAULT 0, -- ROI %

    -- Timing
    avg_time_to_lead_hours NUMERIC(10,2),
    avg_time_to_qualified_hours NUMERIC(10,2),
    avg_time_to_scheduled_hours NUMERIC(10,2),
    avg_time_to_close_hours NUMERIC(10,2),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Unique indexes para garantir uma entrada por combinacao de dimensoes por dia
-- Index para totais (sem source_channel e agent_code)
CREATE UNIQUE INDEX IF NOT EXISTS idx_growth_funnel_daily_totals
ON growth_funnel_daily(date, location_id, funnel_name)
WHERE source_channel IS NULL AND agent_code IS NULL;

-- Index para entradas com source_channel
CREATE UNIQUE INDEX IF NOT EXISTS idx_growth_funnel_daily_by_source
ON growth_funnel_daily(date, location_id, source_channel, funnel_name)
WHERE source_channel IS NOT NULL AND agent_code IS NULL;

-- Index para entradas com agent_code
CREATE UNIQUE INDEX IF NOT EXISTS idx_growth_funnel_daily_by_agent
ON growth_funnel_daily(date, location_id, agent_code, funnel_name)
WHERE agent_code IS NOT NULL AND source_channel IS NULL;

-- Index para entradas com ambos
CREATE UNIQUE INDEX IF NOT EXISTS idx_growth_funnel_daily_full
ON growth_funnel_daily(date, location_id, source_channel, agent_code, funnel_name)
WHERE source_channel IS NOT NULL AND agent_code IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_growth_funnel_daily_date ON growth_funnel_daily(date DESC);
CREATE INDEX IF NOT EXISTS idx_growth_funnel_daily_location ON growth_funnel_daily(location_id);
CREATE INDEX IF NOT EXISTS idx_growth_funnel_daily_source ON growth_funnel_daily(source_channel);
CREATE INDEX IF NOT EXISTS idx_growth_funnel_daily_agent ON growth_funnel_daily(agent_code);

-- =============================================================================
-- 8. METRICAS POR AGENTE (Performance individual)
-- =============================================================================
CREATE TABLE IF NOT EXISTS growth_agent_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Dimensoes
    date DATE NOT NULL,
    location_id TEXT NOT NULL,
    agent_code TEXT NOT NULL,

    -- Volume
    conversations_started INTEGER DEFAULT 0,
    conversations_completed INTEGER DEFAULT 0,
    messages_sent INTEGER DEFAULT 0,
    messages_received INTEGER DEFAULT 0,
    calls_made INTEGER DEFAULT 0,
    calls_answered INTEGER DEFAULT 0,

    -- Conversao
    leads_generated INTEGER DEFAULT 0,
    leads_qualified INTEGER DEFAULT 0,
    meetings_booked INTEGER DEFAULT 0,
    deals_closed INTEGER DEFAULT 0,

    -- Handoffs
    handoffs_sent INTEGER DEFAULT 0,
    handoffs_received INTEGER DEFAULT 0,

    -- Timing
    avg_response_time_seconds INTEGER,
    avg_conversation_duration_seconds INTEGER,
    avg_time_to_qualify_hours NUMERIC(10,2),

    -- Qualidade
    escalations_to_human INTEGER DEFAULT 0,
    negative_sentiment_count INTEGER DEFAULT 0,
    positive_sentiment_count INTEGER DEFAULT 0,

    -- Objecoes Tratadas
    objections_handled INTEGER DEFAULT 0,
    objections_overcome INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(date, location_id, agent_code)
);

CREATE INDEX IF NOT EXISTS idx_growth_agent_metrics_date ON growth_agent_metrics(date DESC);
CREATE INDEX IF NOT EXISTS idx_growth_agent_metrics_location ON growth_agent_metrics(location_id);
CREATE INDEX IF NOT EXISTS idx_growth_agent_metrics_agent ON growth_agent_metrics(agent_code);

-- =============================================================================
-- 9. METRICAS GLOBAIS (Visao geral de todos os clientes)
-- =============================================================================
CREATE TABLE IF NOT EXISTS growth_global_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    date DATE NOT NULL UNIQUE,

    -- Total de Clientes
    active_clients INTEGER DEFAULT 0,

    -- Volume Total
    total_prospected INTEGER DEFAULT 0,
    total_leads INTEGER DEFAULT 0,
    total_qualified INTEGER DEFAULT 0,
    total_scheduled INTEGER DEFAULT 0,
    total_showed INTEGER DEFAULT 0,
    total_no_show INTEGER DEFAULT 0,
    total_proposals INTEGER DEFAULT 0,
    total_won INTEGER DEFAULT 0,
    total_lost INTEGER DEFAULT 0,

    -- Valores Totais
    total_proposal_value NUMERIC(15,2) DEFAULT 0,
    total_revenue NUMERIC(15,2) DEFAULT 0,
    avg_ticket_global NUMERIC(15,2) DEFAULT 0,

    -- Taxas Medias
    avg_conversion_rate NUMERIC(5,2) DEFAULT 0,
    avg_show_rate NUMERIC(5,2) DEFAULT 0,
    avg_close_rate NUMERIC(5,2) DEFAULT 0,

    -- Custos Totais
    total_cost NUMERIC(15,2) DEFAULT 0,
    avg_cpl NUMERIC(10,2) DEFAULT 0,
    avg_cpa NUMERIC(10,2) DEFAULT 0,
    avg_roi NUMERIC(10,2) DEFAULT 0,

    -- Crescimento vs Periodo Anterior
    leads_growth_pct NUMERIC(10,2),
    revenue_growth_pct NUMERIC(10,2),
    roi_growth_pct NUMERIC(10,2),
    efficiency_growth_pct NUMERIC(10,2),

    -- Agentes
    total_agents_active INTEGER DEFAULT 0,
    avg_conversations_per_agent NUMERIC(10,2),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_growth_global_metrics_date ON growth_global_metrics(date DESC);

-- =============================================================================
-- 10. LOG DE CONVERSAS (Para analise e debugging)
-- =============================================================================
CREATE TABLE IF NOT EXISTS growth_conversation_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    conversation_id TEXT NOT NULL,
    location_id TEXT NOT NULL,
    lead_id UUID REFERENCES growth_leads(id),

    lead_identifier TEXT,
    lead_source TEXT,

    agents_sequence TEXT[],
    handoff_log JSONB,

    messages JSONB NOT NULL,
    total_messages INTEGER DEFAULT 0,

    final_status TEXT,
    final_outcome TEXT,

    started_at TIMESTAMPTZ DEFAULT NOW(),
    last_message_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    qualification_data JSONB,
    sentiment_scores JSONB,

    test_run_id UUID,
    is_test BOOLEAN DEFAULT false,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_growth_conversation_id ON growth_conversation_logs(conversation_id);
CREATE INDEX IF NOT EXISTS idx_growth_conversation_location ON growth_conversation_logs(location_id);
CREATE INDEX IF NOT EXISTS idx_growth_conversation_lead ON growth_conversation_logs(lead_id);

-- =============================================================================
-- 11. PERSONAS DE TESTE (Simulador)
-- =============================================================================
CREATE TABLE IF NOT EXISTS growth_test_personas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    persona_code TEXT NOT NULL UNIQUE,
    persona_name TEXT NOT NULL,
    persona_description TEXT,

    profile JSONB NOT NULL,
    behavior_traits JSONB NOT NULL,
    likely_objections TEXT[],
    buying_signals TEXT[],

    difficulty_level TEXT DEFAULT 'medium',
    simulation_prompt TEXT NOT NULL,
    success_criteria JSONB,

    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- 12. CASOS E RUNS DE TESTE
-- =============================================================================
CREATE TABLE IF NOT EXISTS growth_test_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    test_code TEXT NOT NULL UNIQUE,
    test_name TEXT NOT NULL,
    test_description TEXT,

    entry_agent TEXT NOT NULL,
    expected_flow TEXT[],
    persona_id UUID REFERENCES growth_test_personas(id),

    initial_message TEXT NOT NULL,
    initial_context JSONB,

    max_messages INTEGER DEFAULT 20,
    max_handoffs INTEGER DEFAULT 5,
    must_reach_agent TEXT,
    must_achieve_outcome TEXT,

    validations JSONB,
    segment_id UUID REFERENCES growth_segment_strategies(id),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS growth_test_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    test_case_id UUID REFERENCES growth_test_cases(id),
    client_agent_id UUID REFERENCES growth_client_agents(id),

    status TEXT DEFAULT 'running',

    total_messages INTEGER DEFAULT 0,
    total_handoffs INTEGER DEFAULT 0,
    agents_visited TEXT[],
    final_agent TEXT,
    final_outcome TEXT,

    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_seconds INTEGER,

    failure_reason TEXT,
    failed_validation TEXT,

    conversation_log_id UUID REFERENCES growth_conversation_logs(id),

    run_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- VIEWS PARA DASHBOARD (Consultas otimizadas)
-- =============================================================================

-- View: Funil por Cliente (igual ao dashboard que voce mostrou)
CREATE OR REPLACE VIEW growth_vw_funnel_by_client AS
SELECT
    gcc.location_id,
    gcc.client_name,
    gcc.tipo_negocio as segment,

    -- Totais do periodo
    SUM(gfd.prospected_count) as total_prospected,
    SUM(gfd.lead_count) as total_leads,
    SUM(gfd.qualified_count) as total_qualified,
    SUM(gfd.scheduled_count) as total_scheduled,
    SUM(gfd.showed_count) as total_showed,
    SUM(gfd.no_show_count) as total_no_show,
    SUM(gfd.proposal_count) as total_proposals,
    SUM(gfd.won_count) as total_won,
    SUM(gfd.lost_count) as total_lost,

    -- Taxas
    ROUND(SUM(gfd.lead_count)::NUMERIC / NULLIF(SUM(gfd.prospected_count), 0) * 100, 1) as lead_rate,
    ROUND(SUM(gfd.qualified_count)::NUMERIC / NULLIF(SUM(gfd.lead_count), 0) * 100, 1) as qualification_rate,
    ROUND(SUM(gfd.scheduled_count)::NUMERIC / NULLIF(SUM(gfd.qualified_count), 0) * 100, 1) as scheduling_rate,
    ROUND(SUM(gfd.showed_count)::NUMERIC / NULLIF(SUM(gfd.scheduled_count), 0) * 100, 1) as show_rate,
    ROUND(SUM(gfd.won_count)::NUMERIC / NULLIF(SUM(gfd.proposal_count), 0) * 100, 1) as closing_rate,
    ROUND(SUM(gfd.won_count)::NUMERIC / NULLIF(SUM(gfd.prospected_count), 0) * 100, 1) as total_conversion_rate,

    -- Valores
    SUM(gfd.total_won_value) as total_revenue,
    ROUND(SUM(gfd.total_won_value) / NULLIF(SUM(gfd.won_count), 0), 2) as avg_ticket,

    -- ROI
    SUM(gfd.cost_spent) as total_cost,
    ROUND(SUM(gfd.cost_spent) / NULLIF(SUM(gfd.lead_count), 0), 2) as cpl,
    ROUND(SUM(gfd.cost_spent) / NULLIF(SUM(gfd.won_count), 0), 2) as cpa,
    ROUND((SUM(gfd.total_won_value) - SUM(gfd.cost_spent)) / NULLIF(SUM(gfd.cost_spent), 0) * 100, 1) as roi_pct

FROM growth_client_configs gcc
LEFT JOIN growth_funnel_daily gfd ON gcc.location_id = gfd.location_id
WHERE gfd.source_channel IS NULL  -- Total consolidado
  AND gfd.agent_code IS NULL
GROUP BY gcc.location_id, gcc.client_name, gcc.tipo_negocio;

-- View: Funil Global (todos os clientes somados)
CREATE OR REPLACE VIEW growth_vw_funnel_global AS
SELECT
    date,
    SUM(prospected_count) as prospected,
    SUM(lead_count) as leads,
    SUM(qualified_count) as qualified,
    SUM(scheduled_count) as scheduled,
    SUM(showed_count) as showed,
    SUM(no_show_count) as no_show,
    SUM(proposal_count) as proposals,
    SUM(won_count) as won,
    SUM(lost_count) as lost,
    SUM(total_won_value) as revenue,
    SUM(cost_spent) as cost,
    ROUND(SUM(won_count)::NUMERIC / NULLIF(SUM(prospected_count), 0) * 100, 1) as conversion_rate
FROM growth_funnel_daily
WHERE source_channel IS NULL
  AND agent_code IS NULL
GROUP BY date
ORDER BY date DESC;

-- View: Performance por Agente
CREATE OR REPLACE VIEW growth_vw_agent_performance AS
SELECT
    gam.agent_code,
    gat.agent_name,
    gat.agent_category,
    gat.channel,

    SUM(gam.conversations_started) as total_conversations,
    SUM(gam.leads_qualified) as total_qualified,
    SUM(gam.meetings_booked) as total_meetings,
    SUM(gam.deals_closed) as total_deals,

    ROUND(AVG(gam.avg_response_time_seconds), 0) as avg_response_time,
    ROUND(SUM(gam.deals_closed)::NUMERIC / NULLIF(SUM(gam.conversations_started), 0) * 100, 2) as conversion_rate,

    SUM(gam.escalations_to_human) as escalations,
    SUM(gam.objections_overcome) as objections_handled

FROM growth_agent_metrics gam
JOIN growth_agent_templates gat ON gam.agent_code = gat.agent_code
GROUP BY gam.agent_code, gat.agent_name, gat.agent_category, gat.channel;

-- View: Funil por Canal (source)
CREATE OR REPLACE VIEW growth_vw_funnel_by_channel AS
SELECT
    source_channel,
    SUM(prospected_count) as prospected,
    SUM(lead_count) as leads,
    SUM(qualified_count) as qualified,
    SUM(scheduled_count) as scheduled,
    SUM(won_count) as won,
    SUM(total_won_value) as revenue,
    ROUND(SUM(won_count)::NUMERIC / NULLIF(SUM(prospected_count), 0) * 100, 1) as conversion_rate,
    ROUND(SUM(cost_spent) / NULLIF(SUM(won_count), 0), 2) as cpa
FROM growth_funnel_daily
WHERE source_channel IS NOT NULL
  AND agent_code IS NULL
GROUP BY source_channel;

-- =============================================================================
-- FUNCTIONS: Atualizar metricas
-- =============================================================================

-- Function: Calcular metricas do funil para um dia/location
CREATE OR REPLACE FUNCTION growth_calculate_funnel_daily(
    p_date DATE,
    p_location_id TEXT
)
RETURNS void AS $$
BEGIN
    INSERT INTO growth_funnel_daily (
        date, location_id,
        prospected_count, lead_count, qualified_count, scheduled_count,
        showed_count, no_show_count, proposal_count, won_count, lost_count,
        lead_rate, qualification_rate, scheduling_rate, show_rate, closing_rate, total_conversion_rate
    )
    SELECT
        p_date,
        p_location_id,
        COUNT(*) FILTER (WHERE funnel_stage = 'prospected'),
        COUNT(*) FILTER (WHERE funnel_stage = 'lead'),
        COUNT(*) FILTER (WHERE funnel_stage = 'qualified'),
        COUNT(*) FILTER (WHERE funnel_stage = 'scheduled'),
        COUNT(*) FILTER (WHERE funnel_stage = 'showed'),
        COUNT(*) FILTER (WHERE funnel_stage = 'no_show'),
        COUNT(*) FILTER (WHERE funnel_stage = 'proposal'),
        COUNT(*) FILTER (WHERE funnel_stage = 'won'),
        COUNT(*) FILTER (WHERE funnel_stage = 'lost'),
        -- Taxas calculadas
        ROUND(COUNT(*) FILTER (WHERE funnel_stage = 'lead')::NUMERIC / NULLIF(COUNT(*) FILTER (WHERE funnel_stage = 'prospected'), 0) * 100, 2),
        ROUND(COUNT(*) FILTER (WHERE funnel_stage = 'qualified')::NUMERIC / NULLIF(COUNT(*) FILTER (WHERE funnel_stage = 'lead'), 0) * 100, 2),
        ROUND(COUNT(*) FILTER (WHERE funnel_stage = 'scheduled')::NUMERIC / NULLIF(COUNT(*) FILTER (WHERE funnel_stage = 'qualified'), 0) * 100, 2),
        ROUND(COUNT(*) FILTER (WHERE funnel_stage = 'showed')::NUMERIC / NULLIF(COUNT(*) FILTER (WHERE funnel_stage = 'scheduled'), 0) * 100, 2),
        ROUND(COUNT(*) FILTER (WHERE funnel_stage = 'won')::NUMERIC / NULLIF(COUNT(*) FILTER (WHERE funnel_stage = 'proposal'), 0) * 100, 2),
        ROUND(COUNT(*) FILTER (WHERE funnel_stage = 'won')::NUMERIC / NULLIF(COUNT(*) FILTER (WHERE funnel_stage = 'prospected'), 0) * 100, 2)
    FROM growth_leads
    WHERE location_id = p_location_id
      AND DATE(created_at) <= p_date
    ON CONFLICT (date, location_id, funnel_name) WHERE source_channel IS NULL AND agent_code IS NULL
    DO UPDATE SET
        prospected_count = EXCLUDED.prospected_count,
        lead_count = EXCLUDED.lead_count,
        qualified_count = EXCLUDED.qualified_count,
        scheduled_count = EXCLUDED.scheduled_count,
        showed_count = EXCLUDED.showed_count,
        no_show_count = EXCLUDED.no_show_count,
        proposal_count = EXCLUDED.proposal_count,
        won_count = EXCLUDED.won_count,
        lost_count = EXCLUDED.lost_count,
        lead_rate = EXCLUDED.lead_rate,
        qualification_rate = EXCLUDED.qualification_rate,
        scheduling_rate = EXCLUDED.scheduling_rate,
        show_rate = EXCLUDED.show_rate,
        closing_rate = EXCLUDED.closing_rate,
        total_conversion_rate = EXCLUDED.total_conversion_rate;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- TRIGGERS
-- =============================================================================

CREATE OR REPLACE FUNCTION growth_update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_growth_leads_updated
    BEFORE UPDATE ON growth_leads
    FOR EACH ROW EXECUTE FUNCTION growth_update_updated_at();

CREATE TRIGGER trigger_growth_agent_templates_updated
    BEFORE UPDATE ON growth_agent_templates
    FOR EACH ROW EXECUTE FUNCTION growth_update_updated_at();

CREATE TRIGGER trigger_growth_segment_strategies_updated
    BEFORE UPDATE ON growth_segment_strategies
    FOR EACH ROW EXECUTE FUNCTION growth_update_updated_at();

CREATE TRIGGER trigger_growth_client_configs_updated
    BEFORE UPDATE ON growth_client_configs
    FOR EACH ROW EXECUTE FUNCTION growth_update_updated_at();

CREATE TRIGGER trigger_growth_client_agents_updated
    BEFORE UPDATE ON growth_client_agents
    FOR EACH ROW EXECUTE FUNCTION growth_update_updated_at();

-- =============================================================================
-- GRANTS
-- =============================================================================

GRANT ALL ON TABLE growth_leads TO anon, authenticated, service_role;
GRANT ALL ON TABLE growth_agent_templates TO anon, authenticated, service_role;
GRANT ALL ON TABLE growth_segment_strategies TO anon, authenticated, service_role;
GRANT ALL ON TABLE growth_client_configs TO anon, authenticated, service_role;
GRANT ALL ON TABLE growth_client_agents TO anon, authenticated, service_role;
GRANT ALL ON TABLE growth_activities TO anon, authenticated, service_role;
GRANT ALL ON TABLE growth_funnel_daily TO anon, authenticated, service_role;
GRANT ALL ON TABLE growth_agent_metrics TO anon, authenticated, service_role;
GRANT ALL ON TABLE growth_global_metrics TO anon, authenticated, service_role;
GRANT ALL ON TABLE growth_conversation_logs TO anon, authenticated, service_role;
GRANT ALL ON TABLE growth_test_personas TO anon, authenticated, service_role;
GRANT ALL ON TABLE growth_test_cases TO anon, authenticated, service_role;
GRANT ALL ON TABLE growth_test_runs TO anon, authenticated, service_role;

GRANT SELECT ON growth_vw_funnel_by_client TO anon, authenticated, service_role;
GRANT SELECT ON growth_vw_funnel_global TO anon, authenticated, service_role;
GRANT SELECT ON growth_vw_agent_performance TO anon, authenticated, service_role;
GRANT SELECT ON growth_vw_funnel_by_channel TO anon, authenticated, service_role;

GRANT EXECUTE ON FUNCTION growth_calculate_funnel_daily TO anon, authenticated, service_role;

-- =============================================================================
-- COMENTARIOS
-- =============================================================================
COMMENT ON TABLE growth_leads IS 'Leads do Growth OS com funil completo e qualificacao BANT';
COMMENT ON TABLE growth_funnel_daily IS 'Metricas diarias do funil - base para dashboard como Mottivme Sales';
COMMENT ON TABLE growth_agent_metrics IS 'Performance individual de cada agente por dia';
COMMENT ON TABLE growth_global_metrics IS 'Visao consolidada de todos os clientes';
COMMENT ON VIEW growth_vw_funnel_by_client IS 'Dashboard: Funil por cliente com taxas e ROI';
COMMENT ON VIEW growth_vw_funnel_global IS 'Dashboard: Funil global agregado por data';
COMMENT ON VIEW growth_vw_agent_performance IS 'Dashboard: Performance comparativa dos agentes';
COMMENT ON VIEW growth_vw_funnel_by_channel IS 'Dashboard: Funil segmentado por canal de origem';
