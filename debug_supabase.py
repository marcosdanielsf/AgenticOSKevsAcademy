#!/usr/bin/env python3
"""
Debug Supabase connection and table schema
Run this locally or in Railway shell to diagnose issues
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://bfumywvwubvernvhjehk.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_KEY:
    print("❌ SUPABASE_SERVICE_ROLE_KEY not set!")
    print("Set it with: export SUPABASE_SERVICE_ROLE_KEY='your_key'")
    exit(1)

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

print(f"🔧 Testing Supabase connection...")
print(f"   URL: {SUPABASE_URL}")
print(f"   Key: {SUPABASE_KEY[:20]}...{SUPABASE_KEY[-10:]}")
print()

# Test 1: Check if key is valid
print("1️⃣ Testing API key validity...")
try:
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/",
        headers={"apikey": SUPABASE_KEY},
        timeout=10
    )
    print(f"   Status: {r.status_code}")
    if r.status_code == 200:
        print("   ✅ API key is valid!")
    else:
        print(f"   ❌ Error: {r.text[:200]}")
except Exception as e:
    print(f"   ❌ Connection error: {e}")
print()

# Test 2: Check if table exists
print("2️⃣ Checking if agentic_instagram_dm_runs table exists...")
try:
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/agentic_instagram_dm_runs?select=id&limit=1",
        headers=headers,
        timeout=10
    )
    print(f"   Status: {r.status_code}")
    if r.status_code == 200:
        print("   ✅ Table exists!")
        data = r.json()
        print(f"   Records: {len(data)}")
    elif r.status_code == 404:
        print("   ❌ Table NOT FOUND! Need to create it.")
    else:
        print(f"   ❌ Error: {r.text[:200]}")
except Exception as e:
    print(f"   ❌ Error: {e}")
print()

# Test 3: Try to INSERT
print("3️⃣ Testing INSERT into agentic_instagram_dm_runs...")
try:
    r = requests.post(
        f"{SUPABASE_URL}/rest/v1/agentic_instagram_dm_runs",
        headers=headers,
        json={
            'account_used': 'debug_test',
            'status': 'running'
        },
        timeout=10
    )
    print(f"   Status: {r.status_code}")
    if r.status_code in [200, 201]:
        print("   ✅ INSERT successful!")
        data = r.json()
        print(f"   Created ID: {data[0]['id'] if data else 'unknown'}")

        # Clean up - delete test record
        if data:
            del_r = requests.delete(
                f"{SUPABASE_URL}/rest/v1/agentic_instagram_dm_runs?id=eq.{data[0]['id']}",
                headers=headers
            )
            print(f"   🧹 Cleanup: deleted test record")
    else:
        print(f"   ❌ Error: {r.text}")
        print()
        print("   Possible causes:")
        print("   - Invalid API key (check SUPABASE_SERVICE_ROLE_KEY)")
        print("   - Table doesn't exist or has wrong schema")
        print("   - RLS policy blocking inserts")
except Exception as e:
    print(f"   ❌ Error: {e}")
print()

# Test 4: Check table schema
print("4️⃣ Checking table schema...")
try:
    # Query information_schema via RPC (if available)
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/agentic_instagram_dm_runs?select=*&limit=0",
        headers=headers,
        timeout=10
    )
    if r.status_code == 200:
        # Check the columns from the OPTIONS/HEAD response
        print("   ✅ Table accessible")
        print("   Expected columns: id, started_at, ended_at, total_leads, dms_sent, dms_failed, dms_skipped, status, error_log, account_used")
except Exception as e:
    print(f"   ❌ Error: {e}")

print()
print("="*60)
print("If INSERT fails with 400 Bad Request:")
print("1. Go to Supabase SQL Editor")
print("2. Run: SELECT * FROM agentic_instagram_dm_runs LIMIT 1;")
print("3. If error: Create table with SQL from database/setup_supabase.py")
print("4. After creating, add RLS policy:")
print("   ALTER TABLE agentic_instagram_dm_runs ENABLE ROW LEVEL SECURITY;")
print("   CREATE POLICY \"Allow all\" ON agentic_instagram_dm_runs FOR ALL USING (true) WITH CHECK (true);")
print("="*60)
