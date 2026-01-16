-- Migration: Add ICP scoring columns to agentic_instagram_leads
-- Date: 2026-01-16
-- Purpose: Enable lead quality filtering and prioritization

-- Add new columns for lead scoring
ALTER TABLE agentic_instagram_leads
ADD COLUMN IF NOT EXISTS icp_score INTEGER DEFAULT NULL,
ADD COLUMN IF NOT EXISTS priority TEXT DEFAULT NULL,
ADD COLUMN IF NOT EXISTS scored_at TIMESTAMPTZ DEFAULT NULL;

-- Add index for faster filtering by priority
CREATE INDEX IF NOT EXISTS idx_agentic_instagram_leads_priority
ON agentic_instagram_leads (priority);

-- Add index for faster filtering by score
CREATE INDEX IF NOT EXISTS idx_agentic_instagram_leads_icp_score
ON agentic_instagram_leads (icp_score DESC NULLS LAST);

-- Add composite index for optimized queries (priority + score)
CREATE INDEX IF NOT EXISTS idx_agentic_instagram_leads_priority_score
ON agentic_instagram_leads (priority, icp_score DESC NULLS LAST);

-- Comment on columns
COMMENT ON COLUMN agentic_instagram_leads.icp_score IS 'ICP score 0-100 calculated by LeadScorer';
COMMENT ON COLUMN agentic_instagram_leads.priority IS 'Priority: hot (>=70), warm (50-69), cold (40-49), nurturing (<40)';
COMMENT ON COLUMN agentic_instagram_leads.scored_at IS 'Timestamp when score was last calculated';

-- Verify migration
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'agentic_instagram_leads'
AND column_name IN ('icp_score', 'priority', 'scored_at');
