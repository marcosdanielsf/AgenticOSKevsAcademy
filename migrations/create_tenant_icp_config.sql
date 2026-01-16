-- Migration: Create tenant_icp_config table
-- Date: 2026-01-16
-- Purpose: Allow per-tenant ICP scoring configuration

-- Create the tenant ICP config table
CREATE TABLE IF NOT EXISTS tenant_icp_config (
    tenant_id TEXT PRIMARY KEY,

    -- Nome do cliente para referência
    tenant_name TEXT,

    -- Profissões/cargos de decisores (alto valor)
    decision_maker_keywords TEXT[] DEFAULT ARRAY[
        'ceo', 'fundador', 'founder', 'dono', 'proprietário', 'diretor',
        'empresário', 'empreendedor', 'sócio', 'gestor', 'gerente',
        'médico', 'médica', 'dentista', 'advogado', 'advogada'
    ],

    -- Interesses relevantes por categoria
    interest_keywords JSONB DEFAULT '{
        "marketing": ["marketing", "growth", "vendas", "sales", "leads", "tráfego"],
        "tecnologia": ["tech", "startup", "saas", "software", "automação", "ia"],
        "negocios": ["business", "negócio", "empresa", "empreend", "lucro"],
        "estetica": ["estética", "beleza", "clínica", "procedimento", "harmonização"],
        "saude": ["saúde", "bem-estar", "fitness", "nutrição", "medicina"]
    }'::jsonb,

    -- Localizações de alto valor
    high_value_locations TEXT[] DEFAULT ARRAY[
        'sp', 'são paulo', 'rj', 'rio de janeiro', 'bh', 'belo horizonte',
        'brasília', 'curitiba', 'porto alegre', 'florianópolis', 'salvador'
    ],

    -- Faixas de seguidores
    min_followers INT DEFAULT 200,
    max_followers INT DEFAULT 100000,
    ideal_min_followers INT DEFAULT 500,
    ideal_max_followers INT DEFAULT 50000,

    -- Taxa de engajamento mínima
    min_engagement_rate DECIMAL(5,2) DEFAULT 1.0,
    ideal_engagement_rate DECIMAL(5,2) DEFAULT 2.0,

    -- Thresholds de classificação
    hot_threshold INT DEFAULT 70,
    warm_threshold INT DEFAULT 50,
    cold_threshold INT DEFAULT 40,

    -- Pesos customizáveis (somam 100)
    weight_bio INT DEFAULT 30,
    weight_engagement INT DEFAULT 30,
    weight_profile INT DEFAULT 25,
    weight_recency INT DEFAULT 15,

    -- Configurações adicionais
    skip_private_profiles BOOLEAN DEFAULT true,
    require_bio BOOLEAN DEFAULT false,
    require_business_account BOOLEAN DEFAULT false,

    -- GHL integration
    ghl_location_id TEXT,

    -- Metadata
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index para busca rápida
CREATE INDEX IF NOT EXISTS idx_tenant_icp_config_active
ON tenant_icp_config (is_active) WHERE is_active = true;

-- Index para GHL location
CREATE INDEX IF NOT EXISTS idx_tenant_icp_config_ghl
ON tenant_icp_config (ghl_location_id) WHERE ghl_location_id IS NOT NULL;

-- Trigger para atualizar updated_at
CREATE OR REPLACE FUNCTION update_tenant_icp_config_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_tenant_icp_config_updated_at ON tenant_icp_config;
CREATE TRIGGER trigger_tenant_icp_config_updated_at
    BEFORE UPDATE ON tenant_icp_config
    FOR EACH ROW
    EXECUTE FUNCTION update_tenant_icp_config_updated_at();

-- Inserir config DEFAULT (usado quando tenant não tem config específica)
INSERT INTO tenant_icp_config (tenant_id, tenant_name)
VALUES ('DEFAULT', 'Configuração Padrão')
ON CONFLICT (tenant_id) DO NOTHING;

-- Comments
COMMENT ON TABLE tenant_icp_config IS 'Configuração de ICP scoring por tenant/cliente';
COMMENT ON COLUMN tenant_icp_config.decision_maker_keywords IS 'Keywords que identificam decisores (CEO, médico, etc)';
COMMENT ON COLUMN tenant_icp_config.interest_keywords IS 'JSONB com categorias de interesse e suas keywords';
COMMENT ON COLUMN tenant_icp_config.hot_threshold IS 'Score mínimo para classificar como HOT (default: 70)';
COMMENT ON COLUMN tenant_icp_config.warm_threshold IS 'Score mínimo para classificar como WARM (default: 50)';
COMMENT ON COLUMN tenant_icp_config.cold_threshold IS 'Score mínimo para classificar como COLD (default: 40)';

-- Verificar criação
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'tenant_icp_config'
ORDER BY ordinal_position;
