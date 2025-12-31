-- =====================================================
-- MIGRATION 005: MULTI-TENANT LEAD GENERATION PLATFORM
-- =====================================================
-- Implements best practices for Supabase multi-tenancy:
-- 1. tenant_id column on all tables for data segregation
-- 2. RLS policies for complete tenant isolation
-- 3. Versioning strategy for persona/ICP management
-- 4. Performance optimizations with indexes
-- 5. Audit trails with timestamps
-- =====================================================

-- =====================================================
-- TABLE: tenants
-- Purpose: Core tenant/organization management
-- =====================================================
CREATE TABLE IF NOT EXISTS public.tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    tier TEXT NOT NULL DEFAULT 'free', -- free, pro, enterprise
    status TEXT NOT NULL DEFAULT 'active', -- active, suspended, cancelled
    settings JSONB DEFAULT '{}'::jsonb,
    instagram_accounts JSONB DEFAULT '[]'::jsonb, -- Array of connected accounts
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_tier CHECK (tier IN ('free', 'pro', 'enterprise')),
    CONSTRAINT valid_status CHECK (status IN ('active', 'suspended', 'cancelled'))
);

-- Enable RLS
ALTER TABLE public.tenants ENABLE ROW LEVEL SECURITY;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_tenants_slug ON public.tenants(slug);
CREATE INDEX IF NOT EXISTS idx_tenants_status ON public.tenants(status);

-- RLS Policies
CREATE POLICY "tenants_select_own" ON public.tenants
    FOR SELECT USING (
        id = (auth.jwt() -> 'app_metadata' ->> 'tenant_id')::uuid
    );

CREATE POLICY "tenants_update_own" ON public.tenants
    FOR UPDATE USING (
        id = (auth.jwt() -> 'app_metadata' ->> 'tenant_id')::uuid
    );

-- =====================================================
-- TABLE: tenant_personas (with versioning)
-- Purpose: ICP/Persona definitions with version control
-- =====================================================
CREATE TABLE IF NOT EXISTS public.tenant_personas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,

    -- Persona identification
    name TEXT NOT NULL,
    slug TEXT NOT NULL,

    -- Versioning
    version INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT false,
    parent_version_id UUID REFERENCES public.tenant_personas(id),

    -- ICP Criteria
    icp_profile TEXT, -- Descrição do perfil ideal
    icp_pain_points TEXT, -- Dores do cliente
    icp_keywords TEXT[], -- Keywords para busca no bio
    icp_min_followers INTEGER DEFAULT 0,
    icp_max_followers INTEGER DEFAULT 10000000,
    icp_categories TEXT[], -- Categorias de conta (Creator, Business, etc)

    -- Messaging
    tone_of_voice TEXT DEFAULT 'profissional e amigável',
    dm_template TEXT, -- Template de primeira mensagem
    followup_template TEXT, -- Template de follow-up

    -- Scoring weights
    scoring_weights JSONB DEFAULT '{
        "followers": 0.2,
        "bio_keywords": 0.3,
        "is_business": 0.2,
        "engagement": 0.15,
        "verified": 0.15
    }'::jsonb,

    -- Metadata
    description TEXT,
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deprecated_at TIMESTAMPTZ,

    CONSTRAINT unique_tenant_persona_version UNIQUE (tenant_id, slug, version)
);

-- Enable RLS
ALTER TABLE public.tenant_personas ENABLE ROW LEVEL SECURITY;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_personas_tenant ON public.tenant_personas(tenant_id);
CREATE INDEX IF NOT EXISTS idx_personas_active ON public.tenant_personas(tenant_id, is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_personas_version ON public.tenant_personas(tenant_id, slug, version DESC);

-- RLS Policies
CREATE POLICY "personas_select_own" ON public.tenant_personas
    FOR SELECT USING (
        tenant_id = (auth.jwt() -> 'app_metadata' ->> 'tenant_id')::uuid
    );

CREATE POLICY "personas_insert_own" ON public.tenant_personas
    FOR INSERT WITH CHECK (
        tenant_id = (auth.jwt() -> 'app_metadata' ->> 'tenant_id')::uuid
    );

CREATE POLICY "personas_update_own" ON public.tenant_personas
    FOR UPDATE USING (
        tenant_id = (auth.jwt() -> 'app_metadata' ->> 'tenant_id')::uuid
    );

CREATE POLICY "personas_delete_own" ON public.tenant_personas
    FOR DELETE USING (
        tenant_id = (auth.jwt() -> 'app_metadata' ->> 'tenant_id')::uuid
    );

-- Trigger: Ensure only one active persona per tenant
CREATE OR REPLACE FUNCTION ensure_single_active_persona()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_active = true THEN
        UPDATE public.tenant_personas
        SET is_active = false, deprecated_at = NOW()
        WHERE tenant_id = NEW.tenant_id
        AND id != NEW.id
        AND is_active = true;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_single_active_persona
    BEFORE INSERT OR UPDATE ON public.tenant_personas
    FOR EACH ROW
    WHEN (NEW.is_active = true)
    EXECUTE FUNCTION ensure_single_active_persona();

-- =====================================================
-- TABLE: tenant_known_contacts (whitelist)
-- Purpose: Known contacts to skip in outreach
-- =====================================================
CREATE TABLE IF NOT EXISTS public.tenant_known_contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,

    -- Contact info
    username TEXT NOT NULL,
    full_name TEXT,

    -- Classification
    contact_type TEXT NOT NULL DEFAULT 'friend', -- friend, family, partner, employee, competitor
    reason TEXT,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,

    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT unique_tenant_contact UNIQUE (tenant_id, username),
    CONSTRAINT valid_contact_type CHECK (
        contact_type IN ('friend', 'family', 'partner', 'employee', 'competitor', 'other')
    )
);

-- Enable RLS
ALTER TABLE public.tenant_known_contacts ENABLE ROW LEVEL SECURITY;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_known_contacts_tenant ON public.tenant_known_contacts(tenant_id);
CREATE INDEX IF NOT EXISTS idx_known_contacts_username ON public.tenant_known_contacts(tenant_id, username);

-- RLS Policies
CREATE POLICY "known_contacts_select_own" ON public.tenant_known_contacts
    FOR SELECT USING (
        tenant_id = (auth.jwt() -> 'app_metadata' ->> 'tenant_id')::uuid
    );

CREATE POLICY "known_contacts_insert_own" ON public.tenant_known_contacts
    FOR INSERT WITH CHECK (
        tenant_id = (auth.jwt() -> 'app_metadata' ->> 'tenant_id')::uuid
    );

CREATE POLICY "known_contacts_delete_own" ON public.tenant_known_contacts
    FOR DELETE USING (
        tenant_id = (auth.jwt() -> 'app_metadata' ->> 'tenant_id')::uuid
    );

-- =====================================================
-- TABLE: classified_leads
-- Purpose: Leads classified by AI with scoring
-- =====================================================
CREATE TABLE IF NOT EXISTS public.classified_leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    persona_id UUID REFERENCES public.tenant_personas(id),

    -- Lead identification
    username TEXT NOT NULL,
    full_name TEXT,

    -- Profile data
    bio TEXT,
    followers_count INTEGER DEFAULT 0,
    following_count INTEGER DEFAULT 0,
    posts_count INTEGER DEFAULT 0,
    is_verified BOOLEAN DEFAULT false,
    is_private BOOLEAN DEFAULT false,
    category TEXT,
    profile_pic_url TEXT,

    -- Classification
    classification TEXT NOT NULL, -- LEAD_HOT, LEAD_WARM, LEAD_COLD, PESSOAL, SPAM
    score INTEGER DEFAULT 0, -- 0-100
    ai_reasoning TEXT,
    suggested_response TEXT,

    -- Source
    source TEXT NOT NULL, -- post_like, post_comment, follower, dm_received, manual
    source_url TEXT,
    original_message TEXT, -- Se foi mensagem recebida

    -- Status
    status TEXT DEFAULT 'new', -- new, contacted, replied, converted, ignored
    dm_sent_at TIMESTAMPTZ,
    replied_at TIMESTAMPTZ,

    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_classification CHECK (
        classification IN ('LEAD_HOT', 'LEAD_WARM', 'LEAD_COLD', 'PESSOAL', 'SPAM')
    ),
    CONSTRAINT valid_score CHECK (score BETWEEN 0 AND 100),
    CONSTRAINT valid_status CHECK (
        status IN ('new', 'contacted', 'replied', 'converted', 'ignored')
    )
);

-- Enable RLS
ALTER TABLE public.classified_leads ENABLE ROW LEVEL SECURITY;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_classified_tenant ON public.classified_leads(tenant_id);
CREATE INDEX IF NOT EXISTS idx_classified_persona ON public.classified_leads(tenant_id, persona_id);
CREATE INDEX IF NOT EXISTS idx_classified_username ON public.classified_leads(tenant_id, username);
CREATE INDEX IF NOT EXISTS idx_classified_classification ON public.classified_leads(tenant_id, classification);
CREATE INDEX IF NOT EXISTS idx_classified_score ON public.classified_leads(tenant_id, score DESC);
CREATE INDEX IF NOT EXISTS idx_classified_status ON public.classified_leads(tenant_id, status);
CREATE INDEX IF NOT EXISTS idx_classified_created ON public.classified_leads(tenant_id, created_at DESC);

-- RLS Policies
CREATE POLICY "classified_leads_select_own" ON public.classified_leads
    FOR SELECT USING (
        tenant_id = (auth.jwt() -> 'app_metadata' ->> 'tenant_id')::uuid
    );

CREATE POLICY "classified_leads_insert_own" ON public.classified_leads
    FOR INSERT WITH CHECK (
        tenant_id = (auth.jwt() -> 'app_metadata' ->> 'tenant_id')::uuid
    );

CREATE POLICY "classified_leads_update_own" ON public.classified_leads
    FOR UPDATE USING (
        tenant_id = (auth.jwt() -> 'app_metadata' ->> 'tenant_id')::uuid
    );

-- =====================================================
-- HELPER FUNCTIONS
-- =====================================================

-- Function: Get active persona for tenant
CREATE OR REPLACE FUNCTION public.get_active_persona(p_tenant_id UUID)
RETURNS public.tenant_personas AS $$
    SELECT * FROM public.tenant_personas
    WHERE tenant_id = p_tenant_id AND is_active = true
    LIMIT 1;
$$ LANGUAGE sql SECURITY DEFINER;

-- Function: Check if username is known contact
CREATE OR REPLACE FUNCTION public.is_known_contact(p_tenant_id UUID, p_username TEXT)
RETURNS BOOLEAN AS $$
    SELECT EXISTS(
        SELECT 1 FROM public.tenant_known_contacts
        WHERE tenant_id = p_tenant_id AND username = p_username
    );
$$ LANGUAGE sql SECURITY DEFINER;

-- Function: Save classified lead (upsert)
CREATE OR REPLACE FUNCTION public.save_classified_lead(
    p_tenant_id UUID,
    p_username TEXT,
    p_classification TEXT,
    p_score INTEGER,
    p_source TEXT,
    p_ai_reasoning TEXT DEFAULT NULL,
    p_suggested_response TEXT DEFAULT NULL,
    p_original_message TEXT DEFAULT NULL,
    p_persona_id UUID DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_lead_id UUID;
BEGIN
    INSERT INTO public.classified_leads (
        tenant_id, username, classification, score, source,
        ai_reasoning, suggested_response, original_message, persona_id
    ) VALUES (
        p_tenant_id, p_username, p_classification, p_score, p_source,
        p_ai_reasoning, p_suggested_response, p_original_message, p_persona_id
    )
    ON CONFLICT (tenant_id, username)
    DO UPDATE SET
        classification = EXCLUDED.classification,
        score = EXCLUDED.score,
        ai_reasoning = EXCLUDED.ai_reasoning,
        suggested_response = EXCLUDED.suggested_response,
        updated_at = NOW()
    RETURNING id INTO v_lead_id;

    RETURN v_lead_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function: Get lead stats for tenant
CREATE OR REPLACE FUNCTION public.get_lead_stats(p_tenant_id UUID)
RETURNS TABLE (
    total_leads BIGINT,
    hot_leads BIGINT,
    warm_leads BIGINT,
    cold_leads BIGINT,
    contacted BIGINT,
    converted BIGINT,
    avg_score NUMERIC
) AS $$
    SELECT
        COUNT(*) as total_leads,
        COUNT(*) FILTER (WHERE classification = 'LEAD_HOT') as hot_leads,
        COUNT(*) FILTER (WHERE classification = 'LEAD_WARM') as warm_leads,
        COUNT(*) FILTER (WHERE classification = 'LEAD_COLD') as cold_leads,
        COUNT(*) FILTER (WHERE status = 'contacted') as contacted,
        COUNT(*) FILTER (WHERE status = 'converted') as converted,
        ROUND(AVG(score), 2) as avg_score
    FROM public.classified_leads
    WHERE tenant_id = p_tenant_id;
$$ LANGUAGE sql SECURITY DEFINER;

-- =====================================================
-- VIEWS
-- =====================================================

-- View: Hot leads ready for outreach
CREATE OR REPLACE VIEW public.v_hot_leads_ready AS
SELECT
    cl.*,
    tp.name as persona_name,
    tp.dm_template
FROM public.classified_leads cl
LEFT JOIN public.tenant_personas tp ON cl.persona_id = tp.id
WHERE cl.classification = 'LEAD_HOT'
AND cl.status = 'new'
ORDER BY cl.score DESC;

-- View: Daily lead stats
CREATE OR REPLACE VIEW public.v_daily_lead_stats AS
SELECT
    tenant_id,
    DATE(created_at) as date,
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE classification = 'LEAD_HOT') as hot,
    COUNT(*) FILTER (WHERE classification = 'LEAD_WARM') as warm,
    COUNT(*) FILTER (WHERE classification = 'LEAD_COLD') as cold,
    ROUND(AVG(score), 2) as avg_score
FROM public.classified_leads
GROUP BY tenant_id, DATE(created_at)
ORDER BY date DESC;

-- =====================================================
-- GRANTS
-- =====================================================
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.tenants TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.tenant_personas TO authenticated;
GRANT SELECT, INSERT, DELETE ON public.tenant_known_contacts TO authenticated;
GRANT SELECT, INSERT, UPDATE ON public.classified_leads TO authenticated;
GRANT SELECT ON public.v_hot_leads_ready TO authenticated;
GRANT SELECT ON public.v_daily_lead_stats TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_active_persona TO authenticated;
GRANT EXECUTE ON FUNCTION public.is_known_contact TO authenticated;
GRANT EXECUTE ON FUNCTION public.save_classified_lead TO authenticated;
GRANT EXECUTE ON FUNCTION public.get_lead_stats TO authenticated;

-- =====================================================
-- COMMENTS
-- =====================================================
COMMENT ON TABLE public.tenants IS 'Multi-tenant organizations';
COMMENT ON TABLE public.tenant_personas IS 'ICP/Persona definitions with versioning';
COMMENT ON TABLE public.tenant_known_contacts IS 'Whitelist of known contacts to skip';
COMMENT ON TABLE public.classified_leads IS 'Leads classified by AI with scoring';
