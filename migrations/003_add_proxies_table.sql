-- =============================================
-- Migration: Add Instagram Proxies Table
-- Date: 2026-01-19
-- Description: Gerencia proxies por tenant/conta
-- =============================================

CREATE TABLE IF NOT EXISTS instagram_proxies (
    id SERIAL PRIMARY KEY,
    tenant_id TEXT NOT NULL,  -- 'global' para proxy compartilhado
    account_id INTEGER REFERENCES instagram_accounts(id) ON DELETE SET NULL,
    name TEXT,
    host TEXT NOT NULL,
    port INTEGER NOT NULL,
    username TEXT,
    password TEXT,
    proxy_type TEXT DEFAULT 'http' CHECK (proxy_type IN ('http', 'https', 'socks5')),
    provider TEXT DEFAULT 'custom' CHECK (provider IN ('brightdata', 'smartproxy', 'iproyal', 'oxylabs', 'custom')),
    country TEXT,  -- BR, US, etc
    city TEXT,
    is_residential BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMPTZ,
    last_failed_at TIMESTAMPTZ,
    fail_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(host, port, tenant_id)
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_proxies_tenant ON instagram_proxies(tenant_id);
CREATE INDEX IF NOT EXISTS idx_proxies_account ON instagram_proxies(account_id);
CREATE INDEX IF NOT EXISTS idx_proxies_active ON instagram_proxies(is_active);
CREATE INDEX IF NOT EXISTS idx_proxies_country ON instagram_proxies(country);

-- Trigger para updated_at automático
CREATE OR REPLACE FUNCTION update_proxy_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_proxy_updated_at ON instagram_proxies;
CREATE TRIGGER trigger_proxy_updated_at
    BEFORE UPDATE ON instagram_proxies
    FOR EACH ROW
    EXECUTE FUNCTION update_proxy_timestamp();

-- Comentários
COMMENT ON TABLE instagram_proxies IS 'Proxies para automação do Instagram por tenant';
COMMENT ON COLUMN instagram_proxies.tenant_id IS 'ID do tenant ou "global" para proxy compartilhado';
COMMENT ON COLUMN instagram_proxies.is_residential IS 'Proxies residential são melhores para Instagram (menos detecção)';
COMMENT ON COLUMN instagram_proxies.provider IS 'Provider do proxy: brightdata, smartproxy, iproyal, oxylabs ou custom';

-- =============================================
-- EXEMPLO DE USO:
--
-- Proxy específico para Dr. Alberto (Brasil):
-- INSERT INTO instagram_proxies (tenant_id, host, port, username, password, country, is_residential)
-- VALUES ('dr_alberto', 'br.smartproxy.com', 10000, 'user123', 'pass456', 'BR', true);
--
-- Proxy global compartilhado:
-- INSERT INTO instagram_proxies (tenant_id, host, port, country)
-- VALUES ('global', 'proxy.example.com', 8080, 'BR');
-- =============================================
