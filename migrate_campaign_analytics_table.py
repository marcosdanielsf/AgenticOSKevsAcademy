#!/usr/bin/env python3
"""
Migrate the campaign analytics table to add the completed_count field
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def migrate_table():
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cursor = conn.cursor()
        
        print("🔄 Migrating campaign analytics table...")
        
        # Add the completed_count column if it doesn't exist
        cursor.execute("""
            ALTER TABLE instantly_campaign_analytics_overview 
            ADD COLUMN IF NOT EXISTS completed_count INTEGER NOT NULL DEFAULT 0;
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✅ Migration completed successfully")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")

if __name__ == "__main__":
    migrate_table()