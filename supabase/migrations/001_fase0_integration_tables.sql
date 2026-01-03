-- =====================================================
-- FASE 0 - Integration Tables
-- Tabelas para integracao AgenticOS <-> AI Factory <-> GHL
-- =====================================================

-- 1. TABELA: integration_sync_log
-- Registra todas as sincronizacoes entre sistemas
-- =====================================================

CREATE TABLE IF NOT EXISTS integration_sync_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Sistemas envolvidos
    source_system VARCHAR(50) NOT NULL, -- 'agenticos', 'ai_factory', 'ghl'
    target_system VARCHAR(50) NOT NULL,

    -- Entidade sincronizada
    entity_type VARCHAR(50) NOT NULL, -- 'lead', 'conversation', 'qa_analysis'
    entity_id UUID NOT NULL,

    -- Status e dados
    sync_status VARCHAR(20) NOT NULL DEFAULT 'pending', -- 'pending', 'success', 'failed'
    sync_data JSONB,
    error_message TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT valid_sync_status CHECK (sync_status IN ('pending', 'success', 'failed'))
);

-- Indices para performance
CREATE INDEX IF NOT EXISTS idx_sync_log_status ON integration_sync_log(sync_status);
CREATE INDEX IF NOT EXISTS idx_sync_log_entity ON integration_sync_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_sync_log_created ON integration_sync_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sync_log_systems ON integration_sync_log(source_system, target_system);

-- Comentarios
COMMENT ON TABLE integration_sync_log IS 'Log de sincronizacao entre AgenticOS, AI Factory e GHL';
COMMENT ON COLUMN integration_sync_log.source_system IS 'Sistema de origem: agenticos, ai_factory, ghl';
COMMENT ON COLUMN integration_sync_log.target_system IS 'Sistema de destino';
COMMENT ON COLUMN integration_sync_log.entity_type IS 'Tipo de entidade: lead, conversation, qa_analysis';


-- 2. TABELA: enriched_lead_data
-- Dados enriquecidos dos leads (Instagram, LinkedIn, CNPJ)
-- =====================================================

CREATE TABLE IF NOT EXISTS enriched_lead_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Referencia ao lead
    lead_id UUID NOT NULL,
    source VARCHAR(50) NOT NULL, -- 'instagram', 'linkedin', 'cnpj', 'manual'

    -- Dados profissionais
    cargo VARCHAR(255),
    empresa VARCHAR(255),
    setor VARCHAR(100),
    porte VARCHAR(50),

    -- Dados Instagram
    ig_handle VARCHAR(100),
    ig_followers INTEGER,
    ig_following INTEGER,
    ig_posts INTEGER,
    ig_engagement_rate DECIMAL(5,2),
    ig_bio TEXT,
    ig_is_business BOOLEAN,
    ig_category VARCHAR(100),

    -- Dados LinkedIn
    li_url TEXT,
    li_headline TEXT,
    li_connections INTEGER,
    li_experience JSONB,
    li_education JSONB,

    -- Dados CNPJ
    cnpj VARCHAR(20),
    razao_social VARCHAR(255),
    cnae_principal VARCHAR(10),
    cnae_descricao VARCHAR(255),
    faturamento_estimado VARCHAR(50),

    -- Metadata
    raw_data JSONB,
    confidence_score DECIMAL(3,2),
    enriched_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,

    -- Unique constraint para evitar duplicatas
    UNIQUE(lead_id, source)
);

-- Indices
CREATE INDEX IF NOT EXISTS idx_enriched_lead ON enriched_lead_data(lead_id);
CREATE INDEX IF NOT EXISTS idx_enriched_source ON enriched_lead_data(source);
CREATE INDEX IF NOT EXISTS idx_enriched_ig_handle ON enriched_lead_data(ig_handle);
CREATE INDEX IF NOT EXISTS idx_enriched_empresa ON enriched_lead_data(empresa);

-- Comentarios
COMMENT ON TABLE enriched_lead_data IS 'Dados enriquecidos de leads de multiplas fontes';
COMMENT ON COLUMN enriched_lead_data.confidence_score IS 'Score de confianca dos dados (0.00 a 1.00)';
COMMENT ON COLUMN enriched_lead_data.expires_at IS 'Data de expiracao dos dados (para re-enriquecimento)';


-- 3. VIEW: unified_leads
-- Visao unificada de leads com dados de todos os sistemas
-- =====================================================

CREATE OR REPLACE VIEW unified_leads AS
SELECT
    -- Dados basicos do lead
    sl.id,
    sl.name,
    sl.email,
    sl.phone,
    sl.instagram_handle,

    -- Qualificacao
    sl.icp_score,
    sl.icp_tier,
    sl.status,

    -- Dados enriquecidos (consolidados)
    COALESCE(
        (SELECT cargo FROM enriched_lead_data WHERE lead_id = sl.id ORDER BY enriched_at DESC LIMIT 1),
        sl.source_data->>'cargo'
    ) as cargo,
    COALESCE(
        (SELECT empresa FROM enriched_lead_data WHERE lead_id = sl.id ORDER BY enriched_at DESC LIMIT 1),
        sl.source_data->>'empresa'
    ) as empresa,
    COALESCE(
        (SELECT setor FROM enriched_lead_data WHERE lead_id = sl.id ORDER BY enriched_at DESC LIMIT 1),
        sl.source_data->>'setor'
    ) as setor,
    COALESCE(
        (SELECT porte FROM enriched_lead_data WHERE lead_id = sl.id ORDER BY enriched_at DESC LIMIT 1),
        sl.source_data->>'porte'
    ) as porte,

    -- Dados Instagram
    (SELECT ig_followers FROM enriched_lead_data WHERE lead_id = sl.id AND source = 'instagram' LIMIT 1) as ig_followers,
    (SELECT ig_engagement_rate FROM enriched_lead_data WHERE lead_id = sl.id AND source = 'instagram' LIMIT 1) as ig_engagement,

    -- Referencia GHL
    sl.ghl_contact_id,
    sl.location_id,

    -- Metadata
    sl.source,
    sl.created_at,
    sl.updated_at,

    -- AI Factory data (se existir)
    (SELECT COUNT(*) FROM agent_conversations ac WHERE ac.contact_id = sl.id::text) as total_conversations,

    -- Ultima analise QA
    (SELECT qa.overall_score
     FROM qa_analyses qa
     WHERE qa.conversation_id IN (SELECT id FROM agent_conversations WHERE contact_id = sl.id::text)
     ORDER BY qa.created_at DESC
     LIMIT 1) as last_qa_score

FROM socialfy_leads sl;

COMMENT ON VIEW unified_leads IS 'Visao unificada de leads com dados do AgenticOS e AI Factory';


-- 4. TABELA: lead_handoff_queue
-- Fila de leads aguardando handoff para GHL
-- =====================================================

CREATE TABLE IF NOT EXISTS lead_handoff_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Lead
    lead_id UUID NOT NULL,
    location_id VARCHAR(100) NOT NULL,

    -- Status do handoff
    handoff_status VARCHAR(20) NOT NULL DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    handoff_reason VARCHAR(100), -- 'interested', 'requested_contact', 'scheduled_meeting'

    -- Intent analysis
    intent VARCHAR(50),
    intent_confidence DECIMAL(3,2),
    trigger_message TEXT,

    -- Resultado
    ghl_contact_id VARCHAR(100),
    error_message TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT valid_handoff_status CHECK (handoff_status IN ('pending', 'processing', 'completed', 'failed'))
);

-- Indices
CREATE INDEX IF NOT EXISTS idx_handoff_status ON lead_handoff_queue(handoff_status);
CREATE INDEX IF NOT EXISTS idx_handoff_lead ON lead_handoff_queue(lead_id);
CREATE INDEX IF NOT EXISTS idx_handoff_created ON lead_handoff_queue(created_at DESC);

COMMENT ON TABLE lead_handoff_queue IS 'Fila de leads para handoff do AgenticOS para GHL';


-- 5. Adicionar campos na tabela socialfy_leads (se existir)
-- =====================================================

DO $$
BEGIN
    -- Adicionar campo ghl_contact_id se nao existir
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'socialfy_leads' AND column_name = 'ghl_contact_id'
    ) THEN
        ALTER TABLE socialfy_leads ADD COLUMN ghl_contact_id VARCHAR(100);
    END IF;

    -- Adicionar campo location_id se nao existir
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'socialfy_leads' AND column_name = 'location_id'
    ) THEN
        ALTER TABLE socialfy_leads ADD COLUMN location_id VARCHAR(100);
    END IF;

    -- Adicionar campo icp_tier se nao existir
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'socialfy_leads' AND column_name = 'icp_tier'
    ) THEN
        ALTER TABLE socialfy_leads ADD COLUMN icp_tier VARCHAR(20);
    END IF;

    -- Adicionar campo outreach_sent_at se nao existir
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'socialfy_leads' AND column_name = 'outreach_sent_at'
    ) THEN
        ALTER TABLE socialfy_leads ADD COLUMN outreach_sent_at TIMESTAMPTZ;
    END IF;

    -- Adicionar campo last_outreach_message se nao existir
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'socialfy_leads' AND column_name = 'last_outreach_message'
    ) THEN
        ALTER TABLE socialfy_leads ADD COLUMN last_outreach_message TEXT;
    END IF;

EXCEPTION
    WHEN undefined_table THEN
        RAISE NOTICE 'Tabela socialfy_leads nao existe ainda';
END $$;


-- 6. RLS Policies (Row Level Security)
-- =====================================================

-- Habilitar RLS nas novas tabelas
ALTER TABLE integration_sync_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE enriched_lead_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE lead_handoff_queue ENABLE ROW LEVEL SECURITY;

-- Policy para service role (acesso total)
CREATE POLICY "Service role full access" ON integration_sync_log
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access" ON enriched_lead_data
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access" ON lead_handoff_queue
    FOR ALL USING (auth.role() = 'service_role');


-- =====================================================
-- FIM DA MIGRACAO
-- =====================================================
