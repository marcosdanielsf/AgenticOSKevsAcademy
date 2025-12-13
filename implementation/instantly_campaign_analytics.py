#!/usr/bin/env python3
"""
Instantly Campaign Analytics - Fetch campaign overview analytics from Instantly.ai and store in database.

This script fetches comprehensive campaign analytics including opens, clicks, replies, 
bounces, and sales metrics, then stores the results in the database.

Usage:
    ./venv/bin/python3 implementation/instantly_campaign_analytics.py
    ./venv/bin/python3 implementation/instantly_campaign_analytics.py --start-date "2025-12-08" --end-date "2025-12-09"
    ./venv/bin/python3 implementation/instantly_campaign_analytics.py --campaign-id "adb1f3f6-0035-4edd-9252-1073138787df"

API Reference:
    - Endpoint: GET /api/v2/campaigns/analytics/overview
    - Auth: Bearer token in Authorization header
    - Query params: start_date, end_date, campaign_id (optional)
"""

import os
import sys
import argparse
import requests
import psycopg2
from datetime import datetime, timedelta
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

def get_campaign_analytics(start_date=None, end_date=None, campaign_id=None):
    """
    Fetch campaign analytics overview from Instantly.ai API
    
    Args:
        start_date: Start date string in YYYY-MM-DD format (defaults to yesterday)
        end_date: End date string in YYYY-MM-DD format (defaults to today)
        campaign_id: Specific campaign ID to filter analytics (optional)
    
    Returns:
        dict: API response data
    """
    api_key = os.getenv('INSTANTLY_API_KEY')
    if not api_key:
        raise ValueError("INSTANTLY_API_KEY not found in environment variables")
    
    # Use default date range if not specified
    if not start_date or not end_date:
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        start_date = start_date or yesterday.strftime('%Y-%m-%d')
        end_date = end_date or today.strftime('%Y-%m-%d')
    
    # Build API URL
    base_url = "https://api.instantly.ai/api/v2/campaigns/analytics/overview"
    params = {
        'start_date': start_date,
        'end_date': end_date
    }
    
    # Add campaign filter if specified
    if campaign_id:
        params['campaign_id'] = campaign_id
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    print(f"🔄 Fetching campaign analytics...")
    print(f"📅 Date range: {start_date} to {end_date}")
    if campaign_id:
        print(f"🎯 Campaign ID: {campaign_id}")
    else:
        print("🎯 All campaigns")
    
    try:
        response = requests.get(base_url, params=params, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Successfully fetched campaign analytics")
            return data
        else:
            print(f"❌ API Error {response.status_code}: {response.text}")
            return None
            
    except requests.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None

def create_campaign_analytics_table():
    """
    Create the campaign analytics table if it doesn't exist
    """
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cursor = conn.cursor()
        
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS instantly_campaign_analytics_overview (
            id SERIAL PRIMARY KEY,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            campaign_id TEXT NULL,
            
            -- Email Engagement Metrics
            open_count INTEGER NOT NULL DEFAULT 0,
            open_count_unique INTEGER NOT NULL DEFAULT 0,
            open_count_unique_by_step INTEGER NOT NULL DEFAULT 0,
            link_click_count INTEGER NOT NULL DEFAULT 0,
            link_click_count_unique INTEGER NOT NULL DEFAULT 0,
            link_click_count_unique_by_step INTEGER NOT NULL DEFAULT 0,
            
            -- Reply Metrics
            reply_count INTEGER NOT NULL DEFAULT 0,
            reply_count_unique INTEGER NOT NULL DEFAULT 0,
            reply_count_unique_by_step INTEGER NOT NULL DEFAULT 0,
            reply_count_automatic INTEGER NOT NULL DEFAULT 0,
            reply_count_automatic_unique INTEGER NOT NULL DEFAULT 0,
            reply_count_automatic_unique_by_step INTEGER NOT NULL DEFAULT 0,
            
            -- Email Status Metrics
            bounced_count INTEGER NOT NULL DEFAULT 0,
            unsubscribed_count INTEGER NOT NULL DEFAULT 0,
            completed_count INTEGER NOT NULL DEFAULT 0,
            emails_sent_count INTEGER NOT NULL DEFAULT 0,
            contacted_count INTEGER NOT NULL DEFAULT 0,
            new_leads_contacted_count INTEGER NOT NULL DEFAULT 0,
            
            -- Sales Pipeline Metrics
            total_opportunities INTEGER NOT NULL DEFAULT 0,
            total_opportunity_value INTEGER NOT NULL DEFAULT 0,
            total_interested INTEGER NOT NULL DEFAULT 0,
            total_meeting_booked INTEGER NOT NULL DEFAULT 0,
            total_meeting_completed INTEGER NOT NULL DEFAULT 0,
            total_closed INTEGER NOT NULL DEFAULT 0,
            
            -- Metadata
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
        
        -- Create unique constraint to prevent duplicate entries
        CREATE UNIQUE INDEX IF NOT EXISTS idx_campaign_analytics_unique 
        ON instantly_campaign_analytics_overview (start_date, end_date, COALESCE(campaign_id, ''));
        """
        
        cursor.execute(create_table_sql)
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✅ Campaign analytics table ready")
        
    except Exception as e:
        print(f"❌ Error creating table: {e}")

def store_campaign_analytics_in_db(analytics_data, start_date, end_date, campaign_id=None):
    """
    Store campaign analytics data in the database
    
    Args:
        analytics_data: Response from Instantly API
        start_date: Start date string
        end_date: End date string
        campaign_id: Campaign ID (optional)
    """
    if not analytics_data:
        print("❌ No analytics data to store")
        return
    
    try:
        # Ensure table exists
        create_campaign_analytics_table()
        
        # Connect to database
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cursor = conn.cursor()
        
        print("🗄️ Storing campaign analytics in database...")
        
        # Check if record already exists
        cursor.execute("""
            SELECT id FROM instantly_campaign_analytics_overview 
            WHERE start_date = %s AND end_date = %s AND COALESCE(campaign_id, '') = %s
        """, (start_date, end_date, campaign_id or ''))
        
        existing = cursor.fetchone()
        
        if existing:
            # Update existing record
            update_sql = """
                UPDATE instantly_campaign_analytics_overview SET
                    open_count = %s,
                    open_count_unique = %s,
                    open_count_unique_by_step = %s,
                    link_click_count = %s,
                    link_click_count_unique = %s,
                    link_click_count_unique_by_step = %s,
                    reply_count = %s,
                    reply_count_unique = %s,
                    reply_count_unique_by_step = %s,
                    reply_count_automatic = %s,
                    reply_count_automatic_unique = %s,
                    reply_count_automatic_unique_by_step = %s,
                    bounced_count = %s,
                    unsubscribed_count = %s,
                    completed_count = %s,
                    emails_sent_count = %s,
                    contacted_count = %s,
                    new_leads_contacted_count = %s,
                    total_opportunities = %s,
                    total_opportunity_value = %s,
                    total_interested = %s,
                    total_meeting_booked = %s,
                    total_meeting_completed = %s,
                    total_closed = %s,
                    updated_at = NOW()
                WHERE start_date = %s AND end_date = %s AND COALESCE(campaign_id, '') = %s
            """
            
            cursor.execute(update_sql, (
                analytics_data.get('open_count', 0),
                analytics_data.get('open_count_unique', 0),
                analytics_data.get('open_count_unique_by_step', 0),
                analytics_data.get('link_click_count', 0),
                analytics_data.get('link_click_count_unique', 0),
                analytics_data.get('link_click_count_unique_by_step', 0),
                analytics_data.get('reply_count', 0),
                analytics_data.get('reply_count_unique', 0),
                analytics_data.get('reply_count_unique_by_step', 0),
                analytics_data.get('reply_count_automatic', 0),
                analytics_data.get('reply_count_automatic_unique', 0),
                analytics_data.get('reply_count_automatic_unique_by_step', 0),
                analytics_data.get('bounced_count', 0),
                analytics_data.get('unsubscribed_count', 0),
                analytics_data.get('completed_count', 0),
                analytics_data.get('emails_sent_count', 0),
                analytics_data.get('contacted_count', 0),
                analytics_data.get('new_leads_contacted_count', 0),
                analytics_data.get('total_opportunities', 0),
                analytics_data.get('total_opportunity_value', 0),
                analytics_data.get('total_interested', 0),
                analytics_data.get('total_meeting_booked', 0),
                analytics_data.get('total_meeting_completed', 0),
                analytics_data.get('total_closed', 0),
                start_date, end_date, campaign_id or ''
            ))
            
            print(f"📝 Updated existing record for {start_date} to {end_date}")
        else:
            # Insert new record
            insert_sql = """
                INSERT INTO instantly_campaign_analytics_overview (
                    start_date, end_date, campaign_id,
                    open_count, open_count_unique, open_count_unique_by_step,
                    link_click_count, link_click_count_unique, link_click_count_unique_by_step,
                    reply_count, reply_count_unique, reply_count_unique_by_step,
                    reply_count_automatic, reply_count_automatic_unique, reply_count_automatic_unique_by_step,
                    bounced_count, unsubscribed_count, completed_count, emails_sent_count, contacted_count, new_leads_contacted_count,
                    total_opportunities, total_opportunity_value, total_interested,
                    total_meeting_booked, total_meeting_completed, total_closed
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(insert_sql, (
                start_date, end_date, campaign_id,
                analytics_data.get('open_count', 0),
                analytics_data.get('open_count_unique', 0),
                analytics_data.get('open_count_unique_by_step', 0),
                analytics_data.get('link_click_count', 0),
                analytics_data.get('link_click_count_unique', 0),
                analytics_data.get('link_click_count_unique_by_step', 0),
                analytics_data.get('reply_count', 0),
                analytics_data.get('reply_count_unique', 0),
                analytics_data.get('reply_count_unique_by_step', 0),
                analytics_data.get('reply_count_automatic', 0),
                analytics_data.get('reply_count_automatic_unique', 0),
                analytics_data.get('reply_count_automatic_unique_by_step', 0),
                analytics_data.get('bounced_count', 0),
                analytics_data.get('unsubscribed_count', 0),
                analytics_data.get('completed_count', 0),
                analytics_data.get('emails_sent_count', 0),
                analytics_data.get('contacted_count', 0),
                analytics_data.get('new_leads_contacted_count', 0),
                analytics_data.get('total_opportunities', 0),
                analytics_data.get('total_opportunity_value', 0),
                analytics_data.get('total_interested', 0),
                analytics_data.get('total_meeting_booked', 0),
                analytics_data.get('total_meeting_completed', 0),
                analytics_data.get('total_closed', 0)
            ))
            
            print(f"➕ Created new record for {start_date} to {end_date}")
        
        # Commit the transaction
        conn.commit()
        cursor.close()
        conn.close()
        
        print("✅ Successfully stored campaign analytics")
        
        # Show summary
        show_campaign_analytics_summary(analytics_data, start_date, end_date)
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        if 'conn' in locals():
            conn.rollback()

def show_campaign_analytics_summary(analytics_data, start_date, end_date):
    """Show a summary of the campaign analytics"""
    print(f"\n📊 Campaign Analytics Summary ({start_date} to {end_date}):")
    print("=" * 70)
    
    # Email Performance
    sent = analytics_data.get('emails_sent_count', 0)
    opens = analytics_data.get('open_count_unique', 0)
    clicks = analytics_data.get('link_click_count_unique', 0)
    replies = analytics_data.get('reply_count_unique', 0)
    bounced = analytics_data.get('bounced_count', 0)
    
    open_rate = (opens / sent * 100) if sent > 0 else 0
    click_rate = (clicks / sent * 100) if sent > 0 else 0
    reply_rate = (replies / sent * 100) if sent > 0 else 0
    bounce_rate = (bounced / sent * 100) if sent > 0 else 0
    
    completed = analytics_data.get('completed_count', 0)
    contacted = analytics_data.get('contacted_count', 0)
    
    # Get automatic reply metrics
    auto_replies = analytics_data.get('reply_count_automatic_unique', 0)
    
    print(f"📧 Email Performance:")
    print(f"   Emails Sent: {sent:,}")
    print(f"   Contacted: {contacted:,}")
    print(f"   Completed: {completed:,}")
    print(f"   Opens: {opens:,} ({open_rate:.1f}%)")
    print(f"   Clicks: {clicks:,} ({click_rate:.1f}%)")
    print(f"   Human Replies: {replies:,} ({reply_rate:.1f}%)")
    print(f"   Auto Replies: {auto_replies:,} (out-of-office, bounces)")
    print(f"   Bounced: {bounced:,} ({bounce_rate:.1f}%)")
    
    # Sales Pipeline
    opportunities = analytics_data.get('total_opportunities', 0)
    interested = analytics_data.get('total_interested', 0)
    meetings_booked = analytics_data.get('total_meeting_booked', 0)
    meetings_completed = analytics_data.get('total_meeting_completed', 0)
    closed = analytics_data.get('total_closed', 0)
    
    print(f"\n💰 Sales Pipeline:")
    print(f"   Opportunities: {opportunities:,}")
    print(f"   Interested: {interested:,}")
    print(f"   Meetings Booked: {meetings_booked:,}")
    print(f"   Meetings Completed: {meetings_completed:,}")
    print(f"   Closed Deals: {closed:,}")

def main():
    parser = argparse.ArgumentParser(description='Fetch Instantly.ai campaign analytics and store in database')
    parser.add_argument('--start-date', 
                       help='Start date for analytics (YYYY-MM-DD, defaults to yesterday)')
    parser.add_argument('--end-date', 
                       help='End date for analytics (YYYY-MM-DD, defaults to today)')
    parser.add_argument('--campaign-id', 
                       help='Specific campaign ID to analyze (optional)')
    
    args = parser.parse_args()
    
    print("🚀 Instantly Campaign Analytics Fetcher")
    print("=" * 60)
    
    # Fetch analytics from API
    analytics_data = get_campaign_analytics(args.start_date, args.end_date, args.campaign_id)
    
    # Store in database
    if analytics_data:
        start_date = args.start_date or (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        end_date = args.end_date or datetime.now().strftime('%Y-%m-%d')
        store_campaign_analytics_in_db(analytics_data, start_date, end_date, args.campaign_id)
    else:
        print("❌ Failed to fetch campaign analytics data")
        sys.exit(1)

if __name__ == "__main__":
    main()