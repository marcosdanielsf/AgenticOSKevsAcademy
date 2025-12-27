"""
Setup Supabase tables for AgenticOS Instagram DM Agent
Run this once to create the necessary tables
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Supabase connection
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


def get_create_tables_sql():
    """
    SQL to create tables - Run this in Supabase SQL Editor
    """
    return """
-- ============================================
-- AgenticOS - Instagram DM Agent Tables
-- Run this in Supabase SQL Editor
-- https://supabase.com/dashboard/project/YOUR_PROJECT/sql/new
-- ============================================

-- Table: agentic_instagram_leads
-- Stores all leads to be contacted
CREATE TABLE IF NOT EXISTS agentic_instagram_leads (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(255),
    bio TEXT,
    followers_count INTEGER,
    following_count INTEGER,
    is_private BOOLEAN DEFAULT FALSE,
    is_verified BOOLEAN DEFAULT FALSE,
    profile_url VARCHAR(500),
    source VARCHAR(100) DEFAULT 'manual',
    tags TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table: agentic_instagram_dm_sent
-- Tracks all DMs sent
CREATE TABLE IF NOT EXISTS agentic_instagram_dm_sent (
    id BIGSERIAL PRIMARY KEY,
    lead_id BIGINT REFERENCES agentic_instagram_leads(id),
    username VARCHAR(255) NOT NULL,
    message_template VARCHAR(100),
    message_sent TEXT NOT NULL,
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    status VARCHAR(50) DEFAULT 'sent',
    error_message TEXT,
    account_used VARCHAR(255) NOT NULL
);

-- Table: agentic_instagram_dm_runs
-- Tracks each agent run session
CREATE TABLE IF NOT EXISTS agentic_instagram_dm_runs (
    id BIGSERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    total_leads INTEGER DEFAULT 0,
    dms_sent INTEGER DEFAULT 0,
    dms_failed INTEGER DEFAULT 0,
    dms_skipped INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'running',
    error_log TEXT,
    account_used VARCHAR(255) NOT NULL
);

-- Table: agentic_instagram_daily_stats
-- Daily aggregated stats
CREATE TABLE IF NOT EXISTS agentic_instagram_daily_stats (
    id BIGSERIAL PRIMARY KEY,
    date DATE NOT NULL,
    account_used VARCHAR(255) NOT NULL,
    dms_sent INTEGER DEFAULT 0,
    dms_failed INTEGER DEFAULT 0,
    responses_received INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(date, account_used)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_agentic_leads_username ON agentic_instagram_leads(username);
CREATE INDEX IF NOT EXISTS idx_agentic_leads_source ON agentic_instagram_leads(source);
CREATE INDEX IF NOT EXISTS idx_agentic_dm_sent_username ON agentic_instagram_dm_sent(username);
CREATE INDEX IF NOT EXISTS idx_agentic_dm_sent_date ON agentic_instagram_dm_sent(sent_at);
CREATE INDEX IF NOT EXISTS idx_agentic_runs_status ON agentic_instagram_dm_runs(status);
CREATE INDEX IF NOT EXISTS idx_agentic_daily_stats_date ON agentic_instagram_daily_stats(date);

-- Sample leads for testing
INSERT INTO agentic_instagram_leads (username, full_name, source) VALUES
    ('entrepreneur_daily', 'John Smith', 'sample'),
    ('marketing_tips', 'Sarah Johnson', 'sample'),
    ('startup_founder', 'Mike Chen', 'sample'),
    ('growth_hacker', 'Lisa Wang', 'sample'),
    ('business_coach', 'David Brown', 'sample')
ON CONFLICT (username) DO NOTHING;

SELECT 'AgenticOS tables created successfully!' as status;
"""


def test_connection():
    """Test Supabase connection using REST API"""
    print("🔧 Testing Supabase connection...")
    print(f"   URL: {SUPABASE_URL}")

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set in .env")
        return False

    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        }

        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/agentic_instagram_leads?select=count",
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            print("✅ Connected! Tables exist.")
            return True
        elif response.status_code == 404:
            print("⚠️  Tables don't exist yet.")
            return False
        else:
            print(f"⚠️  Status {response.status_code}: {response.text[:100]}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("="*60)
    print("  AgenticOS - Supabase Setup")
    print("="*60)

    connected = test_connection()

    if not connected:
        print("\n" + "="*60)
        print("📋 EXECUTE O SQL ABAIXO NO SUPABASE SQL EDITOR:")
        print("="*60)
        print(get_create_tables_sql())
        print("="*60)
        print("\n🔗 Acesse: https://supabase.com/dashboard -> SQL Editor")
