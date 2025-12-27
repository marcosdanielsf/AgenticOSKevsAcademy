"""
Setup Supabase tables for Instagram DM Agent
Run this once to create the necessary tables
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# Supabase connection
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # Use service role for admin operations

def get_supabase_client() -> Client:
    """Get Supabase client"""
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def create_tables_sql():
    """
    SQL to create tables - Run this in Supabase SQL Editor
    """
    return """
-- ============================================
-- Instagram DM Agent Tables
-- Run this in Supabase SQL Editor (supabase.com -> SQL Editor)
-- ============================================

-- Table: instagram_leads
-- Stores all leads to be contacted
CREATE TABLE IF NOT EXISTS instagram_leads (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(255),
    bio TEXT,
    followers_count INTEGER,
    following_count INTEGER,
    is_private BOOLEAN DEFAULT FALSE,
    is_verified BOOLEAN DEFAULT FALSE,
    profile_url VARCHAR(500),
    profile_pic_url TEXT,
    source VARCHAR(100) DEFAULT 'manual',
    tags TEXT[],
    enriched_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table: instagram_dm_sent
-- Tracks all DMs sent
CREATE TABLE IF NOT EXISTS instagram_dm_sent (
    id BIGSERIAL PRIMARY KEY,
    lead_id BIGINT REFERENCES instagram_leads(id),
    username VARCHAR(255) NOT NULL,
    message_template VARCHAR(100),
    message_sent TEXT NOT NULL,
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    status VARCHAR(50) DEFAULT 'sent',
    error_message TEXT,
    account_used VARCHAR(255) NOT NULL,
    response_received BOOLEAN DEFAULT FALSE,
    response_text TEXT,
    response_at TIMESTAMPTZ
);

-- Table: instagram_dm_agent_runs
-- Tracks each agent run session
CREATE TABLE IF NOT EXISTS instagram_dm_agent_runs (
    id BIGSERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    total_leads INTEGER DEFAULT 0,
    dms_sent INTEGER DEFAULT 0,
    dms_failed INTEGER DEFAULT 0,
    dms_skipped INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'running',
    error_log TEXT,
    account_used VARCHAR(255) NOT NULL,
    notes TEXT
);

-- Table: instagram_daily_stats
-- Daily aggregated stats
CREATE TABLE IF NOT EXISTS instagram_daily_stats (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    account_used VARCHAR(255) NOT NULL,
    dms_sent INTEGER DEFAULT 0,
    dms_failed INTEGER DEFAULT 0,
    responses_received INTEGER DEFAULT 0,
    new_leads_added INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_leads_username ON instagram_leads(username);
CREATE INDEX IF NOT EXISTS idx_leads_source ON instagram_leads(source);
CREATE INDEX IF NOT EXISTS idx_leads_created ON instagram_leads(created_at);
CREATE INDEX IF NOT EXISTS idx_dm_sent_username ON instagram_dm_sent(username);
CREATE INDEX IF NOT EXISTS idx_dm_sent_date ON instagram_dm_sent(sent_at);
CREATE INDEX IF NOT EXISTS idx_dm_sent_status ON instagram_dm_sent(status);
CREATE INDEX IF NOT EXISTS idx_runs_status ON instagram_dm_agent_runs(status);
CREATE INDEX IF NOT EXISTS idx_daily_stats_date ON instagram_daily_stats(date);

-- Enable Row Level Security (RLS) - optional but recommended
ALTER TABLE instagram_leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE instagram_dm_sent ENABLE ROW LEVEL SECURITY;
ALTER TABLE instagram_dm_agent_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE instagram_daily_stats ENABLE ROW LEVEL SECURITY;

-- Create policies for service role access
CREATE POLICY "Service role full access to leads" ON instagram_leads
    FOR ALL USING (true);
CREATE POLICY "Service role full access to dm_sent" ON instagram_dm_sent
    FOR ALL USING (true);
CREATE POLICY "Service role full access to runs" ON instagram_dm_agent_runs
    FOR ALL USING (true);
CREATE POLICY "Service role full access to daily_stats" ON instagram_daily_stats
    FOR ALL USING (true);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for instagram_leads
DROP TRIGGER IF EXISTS update_instagram_leads_updated_at ON instagram_leads;
CREATE TRIGGER update_instagram_leads_updated_at
    BEFORE UPDATE ON instagram_leads
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
"""


def test_connection():
    """Test Supabase connection"""
    try:
        supabase = get_supabase_client()
        # Try a simple query
        result = supabase.table('instagram_leads').select('count', count='exact').execute()
        print(f"✅ Supabase connected! Leads in database: {result.count or 0}")
        return True
    except Exception as e:
        if "relation" in str(e) and "does not exist" in str(e):
            print("⚠️  Tables don't exist yet. Run the SQL in Supabase SQL Editor.")
            print("\n" + "="*60)
            print("COPY THE SQL BELOW AND RUN IN SUPABASE SQL EDITOR:")
            print("="*60)
            print(create_tables_sql())
            return False
        else:
            print(f"❌ Connection error: {e}")
            return False


def add_sample_leads():
    """Add sample leads for testing"""
    supabase = get_supabase_client()

    sample_leads = [
        {"username": "entrepreneur_daily", "full_name": "John Smith", "source": "sample"},
        {"username": "marketing_tips", "full_name": "Sarah Johnson", "source": "sample"},
        {"username": "startup_founder", "full_name": "Mike Chen", "source": "sample"},
        {"username": "growth_hacker", "full_name": "Lisa Wang", "source": "sample"},
        {"username": "business_coach", "full_name": "David Brown", "source": "sample"},
    ]

    for lead in sample_leads:
        try:
            supabase.table('instagram_leads').upsert(lead).execute()
            print(f"  Added: @{lead['username']}")
        except Exception as e:
            print(f"  Skipped @{lead['username']}: {e}")

    print("✅ Sample leads added!")


if __name__ == "__main__":
    print("🔧 Setting up Supabase for Instagram DM Agent...")
    print("="*60)

    if test_connection():
        print("\n📝 Adding sample leads...")
        add_sample_leads()
    else:
        print("\n⚠️  Please create tables first, then run this script again.")
