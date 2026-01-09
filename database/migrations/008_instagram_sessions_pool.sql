-- ============================================
-- INSTAGRAM SESSIONS POOL
-- Para escalar scraping com múltiplas contas
-- ============================================

-- Tabela principal de sessions
CREATE TABLE IF NOT EXISTS instagram_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identificação da conta
    username VARCHAR(255) NOT NULL UNIQUE,
    session_id TEXT NOT NULL,

    -- Status e saúde
    status VARCHAR(50) DEFAULT 'active',  -- active, rate_limited, blocked, expired
    health_score INTEGER DEFAULT 100,      -- 0-100, decresce com erros

    -- Contadores de uso
    requests_today INTEGER DEFAULT 0,
    requests_total INTEGER DEFAULT 0,
    last_request_at TIMESTAMPTZ,

    -- Rate limiting
    rate_limited_until TIMESTAMPTZ,        -- Quando pode voltar a usar
    daily_limit INTEGER DEFAULT 200,       -- Limite diário por conta

    -- Erros
    consecutive_errors INTEGER DEFAULT 0,
    last_error TEXT,
    last_error_at TIMESTAMPTZ,

    -- Metadados
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices para busca rápida
CREATE INDEX IF NOT EXISTS idx_instagram_sessions_status ON instagram_sessions(status);
CREATE INDEX IF NOT EXISTS idx_instagram_sessions_health ON instagram_sessions(health_score DESC);
CREATE INDEX IF NOT EXISTS idx_instagram_sessions_requests ON instagram_sessions(requests_today);

-- Log de uso das sessions (para analytics)
CREATE TABLE IF NOT EXISTS instagram_session_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES instagram_sessions(id) ON DELETE CASCADE,

    -- Operação
    operation VARCHAR(100) NOT NULL,       -- scrape_profile, get_followers, search_hashtag
    target_username VARCHAR(255),

    -- Resultado
    success BOOLEAN DEFAULT true,
    response_status INTEGER,
    error_message TEXT,

    -- Performance
    duration_ms INTEGER,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_session_logs_session ON instagram_session_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_session_logs_created ON instagram_session_logs(created_at DESC);

-- Função para resetar contadores diários (rodar via cron)
CREATE OR REPLACE FUNCTION reset_daily_session_counters()
RETURNS void AS $$
BEGIN
    UPDATE instagram_sessions
    SET
        requests_today = 0,
        status = CASE
            WHEN status = 'rate_limited' AND rate_limited_until < NOW() THEN 'active'
            ELSE status
        END,
        updated_at = NOW()
    WHERE status IN ('active', 'rate_limited');
END;
$$ LANGUAGE plpgsql;

-- Função para pegar próxima session disponível (round-robin com health check)
CREATE OR REPLACE FUNCTION get_next_available_session()
RETURNS TABLE (
    id UUID,
    username VARCHAR(255),
    session_id TEXT,
    requests_today INTEGER,
    health_score INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.id,
        s.username,
        s.session_id,
        s.requests_today,
        s.health_score
    FROM instagram_sessions s
    WHERE
        s.status = 'active'
        AND s.requests_today < s.daily_limit
        AND (s.rate_limited_until IS NULL OR s.rate_limited_until < NOW())
        AND s.health_score > 20  -- Não usar sessions muito degradadas
    ORDER BY
        s.requests_today ASC,     -- Prioriza menos usadas
        s.health_score DESC,      -- Prioriza mais saudáveis
        s.last_request_at ASC     -- Round-robin por tempo
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Função para registrar uso de uma session
CREATE OR REPLACE FUNCTION record_session_usage(
    p_session_id UUID,
    p_operation VARCHAR(100),
    p_target_username VARCHAR(255),
    p_success BOOLEAN,
    p_response_status INTEGER DEFAULT NULL,
    p_error_message TEXT DEFAULT NULL,
    p_duration_ms INTEGER DEFAULT NULL
)
RETURNS void AS $$
BEGIN
    -- Inserir log
    INSERT INTO instagram_session_logs (
        session_id, operation, target_username,
        success, response_status, error_message, duration_ms
    ) VALUES (
        p_session_id, p_operation, p_target_username,
        p_success, p_response_status, p_error_message, p_duration_ms
    );

    -- Atualizar contadores da session
    IF p_success THEN
        UPDATE instagram_sessions
        SET
            requests_today = requests_today + 1,
            requests_total = requests_total + 1,
            last_request_at = NOW(),
            consecutive_errors = 0,
            -- Recupera health gradualmente em sucesso
            health_score = LEAST(100, health_score + 1),
            updated_at = NOW()
        WHERE id = p_session_id;
    ELSE
        UPDATE instagram_sessions
        SET
            requests_today = requests_today + 1,
            requests_total = requests_total + 1,
            last_request_at = NOW(),
            consecutive_errors = consecutive_errors + 1,
            last_error = p_error_message,
            last_error_at = NOW(),
            -- Degrada health em erro
            health_score = GREATEST(0, health_score - 10),
            -- Se muitos erros consecutivos, marcar como rate limited
            status = CASE
                WHEN consecutive_errors >= 3 THEN 'rate_limited'
                ELSE status
            END,
            rate_limited_until = CASE
                WHEN consecutive_errors >= 3 THEN NOW() + INTERVAL '1 hour'
                ELSE rate_limited_until
            END,
            updated_at = NOW()
        WHERE id = p_session_id;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- View para dashboard de sessions
CREATE OR REPLACE VIEW instagram_sessions_dashboard AS
SELECT
    s.id,
    s.username,
    s.status,
    s.health_score,
    s.requests_today,
    s.daily_limit,
    ROUND((s.requests_today::numeric / s.daily_limit::numeric) * 100, 1) as usage_percent,
    s.requests_total,
    s.consecutive_errors,
    s.last_request_at,
    s.rate_limited_until,
    s.last_error,
    -- Stats das últimas 24h
    (SELECT COUNT(*) FROM instagram_session_logs l
     WHERE l.session_id = s.id AND l.created_at > NOW() - INTERVAL '24 hours') as requests_24h,
    (SELECT COUNT(*) FROM instagram_session_logs l
     WHERE l.session_id = s.id AND l.success = true AND l.created_at > NOW() - INTERVAL '24 hours') as success_24h
FROM instagram_sessions s
ORDER BY s.health_score DESC, s.requests_today ASC;

-- Comentários
COMMENT ON TABLE instagram_sessions IS 'Pool de sessions do Instagram para scraping escalável';
COMMENT ON TABLE instagram_session_logs IS 'Log de uso das sessions para analytics e debug';
COMMENT ON FUNCTION get_next_available_session() IS 'Retorna próxima session disponível usando round-robin com health check';
COMMENT ON FUNCTION record_session_usage IS 'Registra uso de uma session e atualiza contadores/status';
