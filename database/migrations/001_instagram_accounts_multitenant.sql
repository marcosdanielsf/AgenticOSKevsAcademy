-- ============================================
-- Migration 001: Instagram Accounts Multi-Tenancy
-- AgenticOS - Socialfy Platform
-- ============================================

-- Tabela de contas Instagram por tenant
CREATE TABLE IF NOT EXISTS instagram_accounts (
    id BIGSERIAL PRIMARY KEY,
    tenant_id VARCHAR(100) NOT NULL,
    username VARCHAR(255) NOT NULL,
    session_id TEXT,                          -- Session cookie do Instagram
    session_data JSONB,                       -- Dados completos da sessão (cookies, headers)
    status VARCHAR(50) DEFAULT 'active',      -- active, paused, blocked, expired
    daily_limit INTEGER DEFAULT 50,           -- Limite de DMs por dia
    hourly_limit INTEGER DEFAULT 10,          -- Limite de DMs por hora
    last_used_at TIMESTAMPTZ,
    blocked_until TIMESTAMPTZ,                -- Se bloqueado temporariamente
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, username)
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_instagram_accounts_tenant ON instagram_accounts(tenant_id);
CREATE INDEX IF NOT EXISTS idx_instagram_accounts_status ON instagram_accounts(status);
CREATE INDEX IF NOT EXISTS idx_instagram_accounts_tenant_active ON instagram_accounts(tenant_id, status) WHERE status = 'active';

-- RLS Policy
ALTER TABLE instagram_accounts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow all for service role" ON instagram_accounts;
CREATE POLICY "Allow all for service role" ON instagram_accounts
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Atualizar tabela de runs para incluir tenant_id
ALTER TABLE agentic_instagram_dm_runs
ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(100);

-- Atualizar tabela de leads para incluir tenant_id
ALTER TABLE agentic_instagram_leads
ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(100);

-- Atualizar tabela de DMs enviadas para incluir tenant_id
ALTER TABLE agentic_instagram_dm_sent
ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(100);

-- Índices para queries por tenant
CREATE INDEX IF NOT EXISTS idx_dm_runs_tenant ON agentic_instagram_dm_runs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_leads_tenant ON agentic_instagram_leads(tenant_id);
CREATE INDEX IF NOT EXISTS idx_dm_sent_tenant ON agentic_instagram_dm_sent(tenant_id);

-- Função para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger para instagram_accounts
DROP TRIGGER IF EXISTS update_instagram_accounts_updated_at ON instagram_accounts;
CREATE TRIGGER update_instagram_accounts_updated_at
    BEFORE UPDATE ON instagram_accounts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Inserir conta padrão para teste (MOTTIVME)
INSERT INTO instagram_accounts (tenant_id, username, session_id, status, daily_limit, hourly_limit, notes)
VALUES (
    'mottivme',
    'marcosdanielsf',
    '258328766%3AEKJ8m0QEivWYrN%3A26%3AAYhUMNhVmKHrhGMaUHaGq8g0VeaX8khoySa6eU2mfw',
    'active',
    200,
    20,
    'Conta principal MOTTIVME'
)
ON CONFLICT (tenant_id, username) DO UPDATE SET
    session_id = EXCLUDED.session_id,
    status = EXCLUDED.status,
    updated_at = NOW();

-- View para estatísticas por tenant
CREATE OR REPLACE VIEW v_tenant_instagram_stats AS
SELECT
    a.tenant_id,
    a.username,
    a.status,
    a.daily_limit,
    a.hourly_limit,
    COALESCE(today_stats.dms_today, 0) as dms_sent_today,
    COALESCE(hour_stats.dms_last_hour, 0) as dms_sent_last_hour,
    a.daily_limit - COALESCE(today_stats.dms_today, 0) as remaining_today,
    a.hourly_limit - COALESCE(hour_stats.dms_last_hour, 0) as remaining_this_hour,
    a.last_used_at,
    a.blocked_until
FROM instagram_accounts a
LEFT JOIN (
    SELECT account_used, COUNT(*) as dms_today
    FROM agentic_instagram_dm_sent
    WHERE sent_at >= CURRENT_DATE
    GROUP BY account_used
) today_stats ON a.username = today_stats.account_used
LEFT JOIN (
    SELECT account_used, COUNT(*) as dms_last_hour
    FROM agentic_instagram_dm_sent
    WHERE sent_at >= NOW() - INTERVAL '1 hour'
    GROUP BY account_used
) hour_stats ON a.username = hour_stats.account_used;

-- Confirmar migração
SELECT 'Migration 001 completed successfully!' as status;
