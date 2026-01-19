-- =============================================
-- Migration: Add Instagram Account Warmup Table
-- Date: 2026-01-19
-- Description: Rastreia o warm-up gradual de contas
-- =============================================

-- Tabela de warmup de contas Instagram
CREATE TABLE IF NOT EXISTS instagram_account_warmup (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL UNIQUE REFERENCES instagram_accounts(id) ON DELETE CASCADE,
    username TEXT NOT NULL,
    warmup_started_at TIMESTAMPTZ DEFAULT NOW(),
    stage TEXT DEFAULT 'new' CHECK (stage IN ('new', 'warming', 'progressing', 'ready')),
    last_active_at TIMESTAMPTZ DEFAULT NOW(),
    is_ready BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_warmup_account_id ON instagram_account_warmup(account_id);
CREATE INDEX IF NOT EXISTS idx_warmup_stage ON instagram_account_warmup(stage);
CREATE INDEX IF NOT EXISTS idx_warmup_is_ready ON instagram_account_warmup(is_ready);

-- Trigger para updated_at automático
CREATE OR REPLACE FUNCTION update_warmup_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_warmup_updated_at ON instagram_account_warmup;
CREATE TRIGGER trigger_warmup_updated_at
    BEFORE UPDATE ON instagram_account_warmup
    FOR EACH ROW
    EXECUTE FUNCTION update_warmup_timestamp();

-- Comentários para documentação
COMMENT ON TABLE instagram_account_warmup IS 'Rastreia o warm-up de contas Instagram para evitar bloqueios';
COMMENT ON COLUMN instagram_account_warmup.stage IS 'Estágio do warmup: new (1-3d, 5 DMs), warming (4-7d, 15 DMs), progressing (8-14d, 30 DMs), ready (15+d, 50 DMs)';
COMMENT ON COLUMN instagram_account_warmup.is_ready IS 'True quando warmup completo (dia 15+) - pode usar limites normais';
COMMENT ON COLUMN instagram_account_warmup.last_active_at IS 'Última vez que a conta foi usada - detecta inatividade';

-- =============================================
-- WARMUP STAGES:
--
-- NEW (Dia 1-3):        5 DMs/dia,  2 DMs/hora
-- WARMING (Dia 4-7):   15 DMs/dia,  4 DMs/hora
-- PROGRESSING (8-14):  30 DMs/dia,  7 DMs/hora
-- READY (Dia 15+):     50 DMs/dia, 10 DMs/hora
-- =============================================
