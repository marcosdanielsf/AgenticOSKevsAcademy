"""
Supabase REST API Client
Simple client using requests instead of SDK to avoid dependency issues
"""

import os
import requests
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


class SupabaseClient:
    """Simple Supabase REST API client"""

    def __init__(self):
        self.base_url = f"{SUPABASE_URL}/rest/v1"
        self.headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

    def _request(self, method: str, endpoint: str, params: dict = None, data: dict = None) -> dict:
        """Make request to Supabase REST API"""
        url = f"{self.base_url}/{endpoint}"
        response = requests.request(
            method=method,
            url=url,
            headers=self.headers,
            params=params,
            json=data
        )
        response.raise_for_status()
        return response.json() if response.text else {}

    def select(self, table: str, columns: str = "*", filters: dict = None) -> List[dict]:
        """Select from table"""
        params = {"select": columns}
        if filters:
            for key, value in filters.items():
                params[key] = value
        return self._request("GET", table, params=params)

    def insert(self, table: str, data: dict) -> dict:
        """Insert into table"""
        result = self._request("POST", table, data=data)
        return result[0] if isinstance(result, list) else result

    def update(self, table: str, data: dict, filters: dict) -> dict:
        """Update table"""
        params = {}
        for key, value in filters.items():
            params[key] = f"eq.{value}"
        result = self._request("PATCH", table, params=params, data=data)
        return result[0] if isinstance(result, list) and result else result

    def upsert(self, table: str, data: dict) -> dict:
        """Upsert into table"""
        headers = self.headers.copy()
        headers["Prefer"] = "resolution=merge-duplicates,return=representation"
        url = f"{self.base_url}/{table}"
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        return result[0] if isinstance(result, list) else result

    def count(self, table: str, filters: dict = None) -> int:
        """Count rows in table"""
        headers = self.headers.copy()
        headers["Prefer"] = "count=exact"
        url = f"{self.base_url}/{table}"
        params = {"select": "*"}
        if filters:
            for key, value in filters.items():
                params[key] = value
        response = requests.head(url, headers=headers, params=params)
        return int(response.headers.get("content-range", "*/0").split("/")[1])


def test_connection():
    """Test Supabase connection"""
    print("🔧 Testing Supabase connection...")
    print(f"   URL: {SUPABASE_URL}")

    try:
        client = SupabaseClient()

        # Try to query the leads table
        leads = client.select("agentic_instagram_leads", columns="count")
        print(f"✅ Connected! Tables exist.")
        return True

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print("⚠️  Tables don't exist yet.")
            print("\n" + "="*60)
            print("EXECUTE O SQL ABAIXO NO SUPABASE SQL EDITOR:")
            print("https://supabase.com/dashboard/project/bfumywvwubvernvhjehk/sql")
            print("="*60)
            print(get_create_tables_sql())
            return False
        else:
            print(f"❌ HTTP Error: {e}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def get_create_tables_sql():
    """Return SQL to create tables"""
    return """
-- ============================================
-- AgenticOS - Instagram DM Agent Tables
-- Copie e cole no Supabase SQL Editor
-- ============================================

-- Table: agentic_instagram_leads
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

-- Indexes
CREATE INDEX IF NOT EXISTS idx_agentic_leads_username ON agentic_instagram_leads(username);
CREATE INDEX IF NOT EXISTS idx_agentic_dm_sent_username ON agentic_instagram_dm_sent(username);
CREATE INDEX IF NOT EXISTS idx_agentic_dm_sent_date ON agentic_instagram_dm_sent(sent_at);
CREATE INDEX IF NOT EXISTS idx_agentic_runs_status ON agentic_instagram_dm_runs(status);

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


if __name__ == "__main__":
    test_connection()
