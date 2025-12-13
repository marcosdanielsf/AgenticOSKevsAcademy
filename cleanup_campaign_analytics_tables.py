#!/usr/bin/env python3
"""
Cleanup campaign analytics tables - remove the old table and keep the overview table
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def cleanup_tables():
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cursor = conn.cursor()
        
        print("🗑️ Cleaning up campaign analytics tables...")
        
        # Check what data exists before deletion
        cursor.execute("SELECT COUNT(*) FROM instantly_campaign_analytics")
        old_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM instantly_campaign_analytics_overview")  
        overview_count = cursor.fetchone()[0]
        
        print(f"📊 Current data:")
        print(f"   instantly_campaign_analytics: {old_count} rows")
        print(f"   instantly_campaign_analytics_overview: {overview_count} rows")
        
        # Drop the old table
        cursor.execute("DROP TABLE IF EXISTS instantly_campaign_analytics CASCADE")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✅ Successfully deleted instantly_campaign_analytics table")
        print("✅ Keeping instantly_campaign_analytics_overview table with all detailed metrics")
        
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")

if __name__ == "__main__":
    cleanup_tables()