-- =============================================================================
-- Migration: Portal CRM Multi-Tenant MOTTIVME Sales
-- Date: 2026-01-08
-- Author: Claude Code + Marcos Daniels
-- =============================================================================
--
-- INTEGRAÇÃO: Este portal utiliza as tabelas do Growth OS (migration 007)
-- - growth_client_configs: Configuração do cliente (tenant)
-- - growth_leads: Leads do sistema
-- - growth_funnel_daily: Métricas do funil
-- - growth_activities: Atividades/touchpoints
--
-- NOVAS TABELAS:
-- - portal_users: Usuários que fazem login no portal
-- - portal_conversations: Conversas sincronizadas do GHL
-- - portal_messages: Mensagens das conversas
-- - portal_metrics_daily: Métricas agregadas adicionais (tráfego)
--
-- PREFIXO: portal_ (para não conflitar com growth_)
-- =============================================================================

-- =============================================================================
-- 1. PORTAL_USERS - Usuários do Portal (vinculados ao Supabase Auth)
-- =============================================================================
CREATE TABLE IF NOT EXISTS portal_users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Identificação
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    avatar_url TEXT,

    -- Vínculo com tenant
    location_id TEXT NOT NULL,              -- FK para growth_client_configs.location_id

    -- Permissões
    role TEXT NOT NULL DEFAULT 'viewer',    -- admin, manager, viewer
    permissions JSONB DEFAULT '{"can_view_leads": true, "can_view_conversations": true, "can_view_metrics": true, "can_export": false}'::jsonb,

    -- Preferências
    preferences JSONB DEFAULT '{"theme": "dark", "notifications": true, "default_period": "7d"}'::jsonb,

    -- Status
    is_active BOOLEAN DEFAULT true,
    last_login_at TIMESTAMPTZ,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_portal_users_location ON portal_users(location_id);
CREATE INDEX IF NOT EXISTS idx_portal_users_email ON portal_users(email);

-- =============================================================================
-- 2. PORTAL_CONVERSATIONS - Conversas sincronizadas do GHL
-- =============================================================================
CREATE TABLE IF NOT EXISTS portal_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Relacionamentos
    location_id TEXT NOT NULL,
    lead_id UUID REFERENCES growth_leads(id) ON DELETE SET NULL,
    ghl_conversation_id TEXT,                -- ID da conversa no GHL
    ghl_contact_id TEXT,                     -- ID do contato no GHL

    -- Canal
    channel TEXT NOT NULL,                   -- instagram, whatsapp, sms, email, facebook
    channel_account_id TEXT,                 -- ID da conta do canal (se aplicável)

    -- Status da conversa
    status TEXT DEFAULT 'open',              -- open, closed, snoozed

    -- Última mensagem
    last_message TEXT,
    last_message_at TIMESTAMPTZ,
    last_message_direction TEXT,             -- inbound, outbound
    last_message_type TEXT,                  -- text, image, audio, video

    -- Atendimento
    assigned_to TEXT,                        -- user_id ou agent_code
    is_ai_responding BOOLEAN DEFAULT false,

    -- Contadores
    unread_count INTEGER DEFAULT 0,
    total_messages INTEGER DEFAULT 0,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    UNIQUE(location_id, ghl_conversation_id)
);

CREATE INDEX IF NOT EXISTS idx_portal_conversations_location ON portal_conversations(location_id);
CREATE INDEX IF NOT EXISTS idx_portal_conversations_lead ON portal_conversations(lead_id);
CREATE INDEX IF NOT EXISTS idx_portal_conversations_ghl ON portal_conversations(ghl_conversation_id);
CREATE INDEX IF NOT EXISTS idx_portal_conversations_channel ON portal_conversations(channel);
CREATE INDEX IF NOT EXISTS idx_portal_conversations_last_message ON portal_conversations(last_message_at DESC);
CREATE INDEX IF NOT EXISTS idx_portal_conversations_status ON portal_conversations(status) WHERE status = 'open';

-- =============================================================================
-- 3. PORTAL_MESSAGES - Mensagens das conversas
-- =============================================================================
CREATE TABLE IF NOT EXISTS portal_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Relacionamentos
    conversation_id UUID NOT NULL REFERENCES portal_conversations(id) ON DELETE CASCADE,
    location_id TEXT NOT NULL,
    ghl_message_id TEXT,                     -- ID da mensagem no GHL

    -- Conteúdo
    content TEXT,
    content_type TEXT DEFAULT 'text',        -- text, image, audio, video, file, location
    media_url TEXT,
    media_metadata JSONB,                    -- { width, height, duration, filename, etc }

    -- Direção
    direction TEXT NOT NULL,                 -- inbound, outbound

    -- Remetente
    sender_type TEXT NOT NULL,               -- lead, ai, human
    sender_name TEXT,
    sender_id TEXT,

    -- Status de entrega
    status TEXT DEFAULT 'sent',              -- pending, sent, delivered, read, failed
    status_updated_at TIMESTAMPTZ,
    error_message TEXT,

    -- IA
    is_from_ai BOOLEAN DEFAULT false,
    ai_agent_code TEXT,                      -- Qual agente gerou a mensagem
    ai_model TEXT,                           -- gemini, openai, etc

    -- Timing
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    delivered_at TIMESTAMPTZ,
    read_at TIMESTAMPTZ,

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_portal_messages_conversation ON portal_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_portal_messages_location ON portal_messages(location_id);
CREATE INDEX IF NOT EXISTS idx_portal_messages_ghl ON portal_messages(ghl_message_id);
CREATE INDEX IF NOT EXISTS idx_portal_messages_sent ON portal_messages(sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_portal_messages_direction ON portal_messages(direction);

-- =============================================================================
-- 4. PORTAL_METRICS_DAILY - Métricas adicionais (complementa growth_funnel_daily)
-- =============================================================================
CREATE TABLE IF NOT EXISTS portal_metrics_daily (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Dimensões
    date DATE NOT NULL,
    location_id TEXT NOT NULL,

    -- Breakdown por fonte (Outbound vs Inbound)
    -- OUTBOUND (Social Selling)
    prospected_outbound INTEGER DEFAULT 0,   -- DMs enviadas (Instagram, LinkedIn, etc)
    leads_outbound INTEGER DEFAULT 0,        -- Respostas recebidas do outbound

    -- INBOUND (Tráfego + Orgânico)
    leads_inbound INTEGER DEFAULT 0,         -- Leads de ads + orgânico

    -- Breakdown por canal específico
    leads_instagram_dm INTEGER DEFAULT 0,    -- Outbound: DM Instagram
    leads_linkedin INTEGER DEFAULT 0,        -- Outbound: LinkedIn
    leads_cold_email INTEGER DEFAULT 0,      -- Outbound: Email frio
    leads_cold_call INTEGER DEFAULT 0,       -- Outbound: Ligação

    leads_facebook_ads INTEGER DEFAULT 0,    -- Inbound: Facebook Ads
    leads_instagram_ads INTEGER DEFAULT 0,   -- Inbound: Instagram Ads
    leads_google_ads INTEGER DEFAULT 0,      -- Inbound: Google Ads
    leads_whatsapp INTEGER DEFAULT 0,        -- Inbound: WhatsApp direto
    leads_referral INTEGER DEFAULT 0,        -- Inbound: Indicação
    leads_organic INTEGER DEFAULT 0,         -- Inbound: Orgânico

    -- Métricas de Tráfego (se cliente tem módulo de tráfego)
    traffic_spend NUMERIC(12,2) DEFAULT 0,   -- Gasto total em ads
    traffic_impressions INTEGER DEFAULT 0,
    traffic_clicks INTEGER DEFAULT 0,
    traffic_ctr NUMERIC(5,2) DEFAULT 0,      -- CTR %

    -- Custos calculados
    cpl_outbound NUMERIC(12,2) DEFAULT 0,    -- Custo por lead outbound (custo operacional)
    cpl_inbound NUMERIC(12,2) DEFAULT 0,     -- Custo por lead inbound (ads)
    cpl_total NUMERIC(12,2) DEFAULT 0,       -- Custo médio por lead
    cpa NUMERIC(12,2) DEFAULT 0,             -- Custo por aquisição (venda)

    -- ROI/ROAS
    revenue NUMERIC(12,2) DEFAULT 0,         -- Receita do dia
    roi_percentage NUMERIC(8,2) DEFAULT 0,   -- ROI em %
    roas NUMERIC(8,2) DEFAULT 0,             -- ROAS (retorno por real investido)

    -- Conversas
    conversations_opened INTEGER DEFAULT 0,
    conversations_closed INTEGER DEFAULT 0,
    messages_sent INTEGER DEFAULT 0,
    messages_received INTEGER DEFAULT 0,
    avg_response_time_minutes NUMERIC(10,2),

    -- Engagement
    ai_messages_sent INTEGER DEFAULT 0,
    human_messages_sent INTEGER DEFAULT 0,
    escalations_to_human INTEGER DEFAULT 0,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    UNIQUE(date, location_id)
);

CREATE INDEX IF NOT EXISTS idx_portal_metrics_daily_date ON portal_metrics_daily(date DESC);
CREATE INDEX IF NOT EXISTS idx_portal_metrics_daily_location ON portal_metrics_daily(location_id);

-- =============================================================================
-- 5. PORTAL_AUDIT_LOG - Log de ações no portal (para segurança)
-- =============================================================================
CREATE TABLE IF NOT EXISTS portal_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Quem
    user_id UUID REFERENCES portal_users(id),
    location_id TEXT NOT NULL,

    -- O quê
    action TEXT NOT NULL,                    -- login, logout, view_lead, export_data, etc
    resource_type TEXT,                      -- lead, conversation, metrics
    resource_id TEXT,

    -- Detalhes
    details JSONB DEFAULT '{}'::jsonb,
    ip_address TEXT,
    user_agent TEXT,

    -- Quando
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_portal_audit_log_user ON portal_audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_portal_audit_log_location ON portal_audit_log(location_id);
CREATE INDEX IF NOT EXISTS idx_portal_audit_log_action ON portal_audit_log(action);
CREATE INDEX IF NOT EXISTS idx_portal_audit_log_date ON portal_audit_log(created_at DESC);

-- =============================================================================
-- ROW LEVEL SECURITY (RLS) - Multi-Tenant Isolation
-- =============================================================================

-- Habilitar RLS em todas as tabelas do portal
ALTER TABLE portal_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE portal_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE portal_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE portal_metrics_daily ENABLE ROW LEVEL SECURITY;
ALTER TABLE portal_audit_log ENABLE ROW LEVEL SECURITY;

-- =============================================================================
-- FUNÇÃO: Obter location_id do usuário autenticado
-- =============================================================================
CREATE OR REPLACE FUNCTION portal_get_user_location_id()
RETURNS TEXT AS $$
    SELECT location_id
    FROM portal_users
    WHERE id = auth.uid()
$$ LANGUAGE sql SECURITY DEFINER STABLE;

-- =============================================================================
-- POLÍTICAS RLS: portal_users
-- =============================================================================

-- SELECT: Usuário só vê seu próprio registro
CREATE POLICY "portal_users_select_own" ON portal_users
    FOR SELECT
    USING (id = auth.uid());

-- UPDATE: Usuário pode atualizar apenas suas próprias preferências
CREATE POLICY "portal_users_update_own" ON portal_users
    FOR UPDATE
    USING (id = auth.uid())
    WITH CHECK (id = auth.uid());

-- =============================================================================
-- POLÍTICAS RLS: portal_conversations
-- =============================================================================

-- SELECT: Usuário só vê conversas do seu tenant
CREATE POLICY "portal_conversations_tenant_isolation" ON portal_conversations
    FOR SELECT
    USING (location_id = portal_get_user_location_id());

-- UPDATE: Usuário pode atualizar conversas do seu tenant
CREATE POLICY "portal_conversations_update" ON portal_conversations
    FOR UPDATE
    USING (location_id = portal_get_user_location_id())
    WITH CHECK (location_id = portal_get_user_location_id());

-- =============================================================================
-- POLÍTICAS RLS: portal_messages
-- =============================================================================

-- SELECT: Usuário só vê mensagens de conversas do seu tenant
CREATE POLICY "portal_messages_tenant_isolation" ON portal_messages
    FOR SELECT
    USING (location_id = portal_get_user_location_id());

-- =============================================================================
-- POLÍTICAS RLS: portal_metrics_daily
-- =============================================================================

-- SELECT: Usuário só vê métricas do seu tenant
CREATE POLICY "portal_metrics_tenant_isolation" ON portal_metrics_daily
    FOR SELECT
    USING (location_id = portal_get_user_location_id());

-- =============================================================================
-- POLÍTICAS RLS: portal_audit_log
-- =============================================================================

-- SELECT: Apenas admins podem ver logs de auditoria do tenant
CREATE POLICY "portal_audit_log_admin_only" ON portal_audit_log
    FOR SELECT
    USING (
        location_id = portal_get_user_location_id()
        AND EXISTS (
            SELECT 1 FROM portal_users
            WHERE id = auth.uid()
            AND role = 'admin'
        )
    );

-- INSERT: Qualquer usuário autenticado pode criar log (sistema)
CREATE POLICY "portal_audit_log_insert" ON portal_audit_log
    FOR INSERT
    WITH CHECK (location_id = portal_get_user_location_id());

-- =============================================================================
-- POLÍTICAS PARA SERVICE_ROLE (bypassa RLS para sync)
-- =============================================================================

-- Permitir service_role fazer tudo (para sync do n8n/backend)
CREATE POLICY "portal_service_role_all_users" ON portal_users
    FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "portal_service_role_all_conversations" ON portal_conversations
    FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "portal_service_role_all_messages" ON portal_messages
    FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "portal_service_role_all_metrics" ON portal_metrics_daily
    FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "portal_service_role_all_audit" ON portal_audit_log
    FOR ALL
    USING (auth.role() = 'service_role');

-- =============================================================================
-- TRIGGERS: Atualização de updated_at
-- =============================================================================

CREATE TRIGGER trigger_portal_users_updated
    BEFORE UPDATE ON portal_users
    FOR EACH ROW EXECUTE FUNCTION growth_update_updated_at();

CREATE TRIGGER trigger_portal_conversations_updated
    BEFORE UPDATE ON portal_conversations
    FOR EACH ROW EXECUTE FUNCTION growth_update_updated_at();

CREATE TRIGGER trigger_portal_metrics_updated
    BEFORE UPDATE ON portal_metrics_daily
    FOR EACH ROW EXECUTE FUNCTION growth_update_updated_at();

-- =============================================================================
-- TRIGGER: Atualizar contadores da conversa quando mensagem é inserida
-- =============================================================================

CREATE OR REPLACE FUNCTION portal_update_conversation_on_message()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE portal_conversations
    SET
        total_messages = total_messages + 1,
        last_message = LEFT(NEW.content, 200),
        last_message_at = NEW.sent_at,
        last_message_direction = NEW.direction,
        last_message_type = NEW.content_type,
        unread_count = CASE
            WHEN NEW.direction = 'inbound' THEN unread_count + 1
            ELSE unread_count
        END,
        updated_at = NOW()
    WHERE id = NEW.conversation_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_portal_message_inserted
    AFTER INSERT ON portal_messages
    FOR EACH ROW EXECUTE FUNCTION portal_update_conversation_on_message();

-- =============================================================================
-- VIEWS: Dashboard Queries Otimizadas
-- =============================================================================

-- View: Resumo do Dashboard por Cliente
CREATE OR REPLACE VIEW portal_vw_dashboard_summary AS
SELECT
    gcc.location_id,
    gcc.client_name,

    -- Totais do Growth OS
    COUNT(DISTINCT gl.id) FILTER (WHERE gl.funnel_stage = 'prospected') as prospected_count,
    COUNT(DISTINCT gl.id) FILTER (WHERE gl.funnel_stage = 'lead') as lead_count,
    COUNT(DISTINCT gl.id) FILTER (WHERE gl.funnel_stage = 'qualified') as qualified_count,
    COUNT(DISTINCT gl.id) FILTER (WHERE gl.funnel_stage = 'scheduled') as scheduled_count,
    COUNT(DISTINCT gl.id) FILTER (WHERE gl.funnel_stage = 'showed') as showed_count,
    COUNT(DISTINCT gl.id) FILTER (WHERE gl.funnel_stage = 'no_show') as no_show_count,
    COUNT(DISTINCT gl.id) FILTER (WHERE gl.funnel_stage = 'proposal') as proposal_count,
    COUNT(DISTINCT gl.id) FILTER (WHERE gl.funnel_stage = 'won') as won_count,
    COUNT(DISTINCT gl.id) FILTER (WHERE gl.funnel_stage = 'lost') as lost_count,

    -- Breakdown por tipo (Outbound vs Inbound)
    COUNT(DISTINCT gl.id) FILTER (
        WHERE gl.source_channel IN ('instagram_dm', 'linkedin', 'cold_email', 'cold_call')
    ) as outbound_count,
    COUNT(DISTINCT gl.id) FILTER (
        WHERE gl.source_channel IN ('ads', 'inbound_call', 'referral', 'whatsapp', 'reactivation')
        OR gl.source_channel NOT IN ('instagram_dm', 'linkedin', 'cold_email', 'cold_call')
    ) as inbound_count,

    -- Valores
    SUM(gl.conversion_value) FILTER (WHERE gl.funnel_stage = 'won') as total_revenue,
    AVG(gl.conversion_value) FILTER (WHERE gl.funnel_stage = 'won') as avg_ticket,

    -- Config do cliente
    CASE WHEN gcc.custo_trafego_mensal > 0 THEN true ELSE false END as has_traffic_module,
    gcc.custo_trafego_mensal as monthly_traffic_budget

FROM growth_client_configs gcc
LEFT JOIN growth_leads gl ON gcc.location_id = gl.location_id
GROUP BY gcc.location_id, gcc.client_name, gcc.custo_trafego_mensal;

-- View: Funil por Canal
CREATE OR REPLACE VIEW portal_vw_funnel_by_source AS
SELECT
    location_id,
    source_channel,
    CASE
        WHEN source_channel IN ('instagram_dm', 'linkedin', 'cold_email', 'cold_call') THEN 'outbound'
        ELSE 'inbound'
    END as source_type,
    COUNT(*) as total_leads,
    COUNT(*) FILTER (WHERE funnel_stage = 'qualified') as qualified,
    COUNT(*) FILTER (WHERE funnel_stage = 'scheduled') as scheduled,
    COUNT(*) FILTER (WHERE funnel_stage = 'won') as won,
    SUM(conversion_value) FILTER (WHERE funnel_stage = 'won') as revenue
FROM growth_leads
GROUP BY location_id, source_channel;

-- View: Conversas recentes
CREATE OR REPLACE VIEW portal_vw_recent_conversations AS
SELECT
    pc.id,
    pc.location_id,
    pc.channel,
    pc.status,
    pc.last_message,
    pc.last_message_at,
    pc.last_message_direction,
    pc.unread_count,
    pc.total_messages,
    pc.is_ai_responding,
    gl.name as lead_name,
    gl.instagram_username,
    gl.phone as lead_phone,
    gl.funnel_stage as lead_stage,
    gl.lead_temperature
FROM portal_conversations pc
LEFT JOIN growth_leads gl ON pc.lead_id = gl.id
ORDER BY pc.last_message_at DESC;

-- =============================================================================
-- FUNCTIONS: APIs do Portal
-- =============================================================================

-- Function: Obter resumo do dashboard
CREATE OR REPLACE FUNCTION portal_get_dashboard_summary(
    p_location_id TEXT,
    p_start_date DATE DEFAULT CURRENT_DATE - INTERVAL '30 days',
    p_end_date DATE DEFAULT CURRENT_DATE
)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
BEGIN
    SELECT jsonb_build_object(
        'kpis', jsonb_build_object(
            'prospected', COUNT(*) FILTER (WHERE funnel_stage = 'prospected'),
            'leads', COUNT(*) FILTER (WHERE funnel_stage IN ('lead', 'qualified', 'scheduled', 'showed', 'no_show', 'proposal', 'won')),
            'qualified', COUNT(*) FILTER (WHERE funnel_stage IN ('qualified', 'scheduled', 'showed', 'no_show', 'proposal', 'won')),
            'scheduled', COUNT(*) FILTER (WHERE funnel_stage IN ('scheduled', 'showed', 'no_show', 'proposal', 'won')),
            'showed', COUNT(*) FILTER (WHERE funnel_stage IN ('showed', 'proposal', 'won')),
            'won', COUNT(*) FILTER (WHERE funnel_stage = 'won'),
            'lost', COUNT(*) FILTER (WHERE funnel_stage = 'lost')
        ),
        'breakdown', jsonb_build_object(
            'outbound', COUNT(*) FILTER (WHERE source_channel IN ('instagram_dm', 'linkedin', 'cold_email', 'cold_call')),
            'inbound', COUNT(*) FILTER (WHERE source_channel NOT IN ('instagram_dm', 'linkedin', 'cold_email', 'cold_call'))
        ),
        'revenue', jsonb_build_object(
            'total', COALESCE(SUM(conversion_value) FILTER (WHERE funnel_stage = 'won'), 0),
            'avg_ticket', COALESCE(AVG(conversion_value) FILTER (WHERE funnel_stage = 'won'), 0)
        ),
        'period', jsonb_build_object(
            'start_date', p_start_date,
            'end_date', p_end_date
        )
    ) INTO result
    FROM growth_leads
    WHERE location_id = p_location_id
      AND created_at >= p_start_date
      AND created_at <= p_end_date + INTERVAL '1 day';

    RETURN result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function: Obter leads paginados
CREATE OR REPLACE FUNCTION portal_get_leads(
    p_location_id TEXT,
    p_page INTEGER DEFAULT 1,
    p_limit INTEGER DEFAULT 20,
    p_stage TEXT DEFAULT NULL,
    p_source_type TEXT DEFAULT NULL,  -- 'outbound', 'inbound', NULL para todos
    p_search TEXT DEFAULT NULL
)
RETURNS JSONB AS $$
DECLARE
    result JSONB;
    v_offset INTEGER;
    v_total INTEGER;
BEGIN
    v_offset := (p_page - 1) * p_limit;

    -- Contar total
    SELECT COUNT(*) INTO v_total
    FROM growth_leads
    WHERE location_id = p_location_id
      AND (p_stage IS NULL OR funnel_stage = p_stage)
      AND (p_source_type IS NULL
           OR (p_source_type = 'outbound' AND source_channel IN ('instagram_dm', 'linkedin', 'cold_email', 'cold_call'))
           OR (p_source_type = 'inbound' AND source_channel NOT IN ('instagram_dm', 'linkedin', 'cold_email', 'cold_call')))
      AND (p_search IS NULL OR name ILIKE '%' || p_search || '%' OR email ILIKE '%' || p_search || '%');

    -- Buscar leads
    SELECT jsonb_build_object(
        'leads', COALESCE(jsonb_agg(lead_data ORDER BY created_at DESC), '[]'::jsonb),
        'pagination', jsonb_build_object(
            'page', p_page,
            'limit', p_limit,
            'total', v_total,
            'pages', CEIL(v_total::NUMERIC / p_limit)
        )
    ) INTO result
    FROM (
        SELECT jsonb_build_object(
            'id', id,
            'name', name,
            'email', email,
            'phone', phone,
            'instagram', instagram_username,
            'source_channel', source_channel,
            'source_type', CASE
                WHEN source_channel IN ('instagram_dm', 'linkedin', 'cold_email', 'cold_call') THEN 'outbound'
                ELSE 'inbound'
            END,
            'funnel_stage', funnel_stage,
            'lead_temperature', lead_temperature,
            'lead_score', lead_score,
            'bant_total_score', bant_total_score,
            'last_contact_at', last_contact_at,
            'created_at', created_at
        ) as lead_data
        FROM growth_leads
        WHERE location_id = p_location_id
          AND (p_stage IS NULL OR funnel_stage = p_stage)
          AND (p_source_type IS NULL
               OR (p_source_type = 'outbound' AND source_channel IN ('instagram_dm', 'linkedin', 'cold_email', 'cold_call'))
               OR (p_source_type = 'inbound' AND source_channel NOT IN ('instagram_dm', 'linkedin', 'cold_email', 'cold_call')))
          AND (p_search IS NULL OR name ILIKE '%' || p_search || '%' OR email ILIKE '%' || p_search || '%')
        ORDER BY created_at DESC
        LIMIT p_limit
        OFFSET v_offset
    ) sub;

    RETURN result;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =============================================================================
-- GRANTS
-- =============================================================================

GRANT ALL ON TABLE portal_users TO anon, authenticated, service_role;
GRANT ALL ON TABLE portal_conversations TO anon, authenticated, service_role;
GRANT ALL ON TABLE portal_messages TO anon, authenticated, service_role;
GRANT ALL ON TABLE portal_metrics_daily TO anon, authenticated, service_role;
GRANT ALL ON TABLE portal_audit_log TO anon, authenticated, service_role;

GRANT SELECT ON portal_vw_dashboard_summary TO anon, authenticated, service_role;
GRANT SELECT ON portal_vw_funnel_by_source TO anon, authenticated, service_role;
GRANT SELECT ON portal_vw_recent_conversations TO anon, authenticated, service_role;

GRANT EXECUTE ON FUNCTION portal_get_user_location_id TO anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION portal_get_dashboard_summary TO anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION portal_get_leads TO anon, authenticated, service_role;

-- =============================================================================
-- COMENTÁRIOS
-- =============================================================================

COMMENT ON TABLE portal_users IS 'Usuários do Portal CRM vinculados ao Supabase Auth com isolamento multi-tenant';
COMMENT ON TABLE portal_conversations IS 'Conversas sincronizadas do GHL com RLS por location_id';
COMMENT ON TABLE portal_messages IS 'Mensagens das conversas com histórico completo';
COMMENT ON TABLE portal_metrics_daily IS 'Métricas diárias incluindo breakdown Outbound/Inbound e ROI de tráfego';
COMMENT ON TABLE portal_audit_log IS 'Log de auditoria de ações no portal para segurança';

COMMENT ON FUNCTION portal_get_user_location_id IS 'Retorna location_id do usuário autenticado para RLS';
COMMENT ON FUNCTION portal_get_dashboard_summary IS 'API: Resumo do dashboard com KPIs e breakdown';
COMMENT ON FUNCTION portal_get_leads IS 'API: Lista paginada de leads com filtros';

COMMENT ON VIEW portal_vw_dashboard_summary IS 'View otimizada para dashboard principal';
COMMENT ON VIEW portal_vw_funnel_by_source IS 'View do funil segmentado por canal/tipo';
COMMENT ON VIEW portal_vw_recent_conversations IS 'View das conversas recentes com dados do lead';
