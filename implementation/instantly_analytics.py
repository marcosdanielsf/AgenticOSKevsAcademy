#!/usr/bin/env python3
"""
Instantly Analytics - Fetch daily email analytics from Instantly.ai and store in database.

This script fetches email analytics for today and stores the results in the 
instantly_email_daily_analytics table.

Usage:
    ./venv/bin/python3 implementation/instantly_analytics.py
    ./venv/bin/python3 implementation/instantly_analytics.py --emails "user1@example.com,user2@example.com"
    ./venv/bin/python3 implementation/instantly_analytics.py --date "2024-01-15"

API Reference:
    - Endpoint: GET /api/v2/accounts/analytics/daily
    - Auth: Bearer token in Authorization header
    - Query params: emails, start_date, end_date
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

def get_instantly_analytics(emails=None, target_date=None):
    """
    Fetch daily analytics from Instantly.ai API
    
    Args:
        emails: Comma-separated email addresses (optional)
        target_date: Date string in YYYY-MM-DD format (defaults to today)
    
    Returns:
        dict: API response data
    """
    api_key = os.getenv('INSTANTLY_API_KEY')
    if not api_key:
        raise ValueError("INSTANTLY_API_KEY not found in environment variables")
    
    # Use today if no date specified
    if not target_date:
        target_date = datetime.now().strftime('%Y-%m-%d')
    
    # Build API URL
    base_url = "https://api.instantly.ai/api/v2/accounts/analytics/daily"
    params = {
        'start_date': target_date,
        'end_date': target_date
    }
    
    # Add emails parameter if specified
    if emails:
        params['emails'] = emails
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    print(f"🔄 Fetching analytics for date: {target_date}")
    if emails:
        print(f"📧 Email accounts: {emails}")
    else:
        print("📧 Fetching for all connected email accounts")
    
    try:
        response = requests.get(base_url, params=params, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Successfully fetched analytics data")
            return data
        else:
            print(f"❌ API Error {response.status_code}: {response.text}")
            return None
            
    except requests.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None

def store_analytics_in_db(analytics_data, target_date):
    """
    Store analytics data in the instantly_email_daily_analytics table
    
    Args:
        analytics_data: Response from Instantly API
        target_date: Date string in YYYY-MM-DD format
    """
    if not analytics_data:
        print("❌ No analytics data to store")
        return
    
    try:
        # Connect to database
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cursor = conn.cursor()
        
        print("🗄️ Storing analytics data in database...")
        
        # Handle response format - API returns a direct list
        if isinstance(analytics_data, list):
            account_data = analytics_data
        else:
            # Fallback for unexpected format
            account_data = [analytics_data] if isinstance(analytics_data, dict) else []
        
        stored_count = 0
        
        for account in account_data:
            email_account = account.get('email_account', 'unknown')
            sent = account.get('sent', 0)
            bounced = account.get('bounced', 0)
            
            # Check if record already exists for this date and email
            cursor.execute("""
                SELECT id FROM instantly_email_daily_analytics 
                WHERE date = %s AND email_account = %s
            """, (target_date, email_account))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing record
                cursor.execute("""
                    UPDATE instantly_email_daily_analytics 
                    SET sent = %s, bounced = %s, updated_at = NOW()
                    WHERE date = %s AND email_account = %s
                """, (sent, bounced, target_date, email_account))
                print(f"📝 Updated record for {email_account}: sent={sent}, bounced={bounced}")
            else:
                # Insert new record
                cursor.execute("""
                    INSERT INTO instantly_email_daily_analytics 
                    (date, email_account, sent, bounced, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, NOW(), NOW())
                """, (target_date, email_account, sent, bounced))
                print(f"➕ Created new record for {email_account}: sent={sent}, bounced={bounced}")
            
            stored_count += 1
        
        # Commit the transaction
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ Successfully stored {stored_count} analytics records")
        
        # Show summary
        show_analytics_summary(target_date)
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        if 'conn' in locals():
            conn.rollback()

def show_analytics_summary(target_date):
    """Show a summary of stored analytics for the date"""
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT email_account, sent, bounced 
            FROM instantly_email_daily_analytics 
            WHERE date = %s
            ORDER BY sent DESC
        """, (target_date,))
        
        records = cursor.fetchall()
        
        if records:
            print(f"\n📊 Analytics Summary for {target_date}:")
            print("-" * 60)
            total_sent = 0
            total_bounced = 0
            
            for email, sent, bounced in records:
                bounce_rate = (bounced / sent * 100) if sent > 0 else 0
                print(f"📧 {email:<30} Sent: {sent:>4} | Bounced: {bounced:>3} ({bounce_rate:.1f}%)")
                total_sent += sent
                total_bounced += bounced
            
            print("-" * 60)
            overall_bounce_rate = (total_bounced / total_sent * 100) if total_sent > 0 else 0
            print(f"📈 TOTAL:                         Sent: {total_sent:>4} | Bounced: {total_bounced:>3} ({overall_bounce_rate:.1f}%)")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error showing summary: {e}")

def main():
    parser = argparse.ArgumentParser(description='Fetch Instantly.ai email analytics and store in database')
    parser.add_argument('--emails', 
                       help='Comma-separated list of email accounts to fetch analytics for (optional)')
    parser.add_argument('--date', 
                       help='Date to fetch analytics for (YYYY-MM-DD format, defaults to today)')
    
    args = parser.parse_args()
    
    print("🚀 Instantly Analytics Fetcher")
    print("=" * 50)
    
    # Fetch analytics from API
    analytics_data = get_instantly_analytics(args.emails, args.date)
    
    # Store in database
    if analytics_data:
        target_date = args.date or datetime.now().strftime('%Y-%m-%d')
        store_analytics_in_db(analytics_data, target_date)
    else:
        print("❌ Failed to fetch analytics data")
        sys.exit(1)

if __name__ == "__main__":
    main()