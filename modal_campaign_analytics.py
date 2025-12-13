"""
Modal Cron Job: Instantly Campaign Analytics

Runs every day at 8:00 PM CST (2:00 AM UTC) to fetch campaign analytics
from Instantly.ai and store in the database.

Deploy: modal deploy modal_campaign_analytics.py
Test:   modal run modal_campaign_analytics.py
"""

import modal

# Create Modal app
app = modal.App("instantly-campaign-analytics")

# Create image with dependencies
image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "requests",
    "psycopg2-binary",
)

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("agenticos-secrets")],
    schedule=modal.Cron("0 23 * * *"),  # 11 PM UTC = 6 PM EST daily
    timeout=300,
)
def run_campaign_analytics():
    """Fetch campaign overview analytics from Instantly.ai and store in database"""
    import os
    import requests
    import psycopg2
    from datetime import datetime, timedelta
    
    print("🚀 Instantly Campaign Analytics - Modal Cron Job")
    print("=" * 60)
    print("⏰ Schedule: 6:00 PM EST daily (11:00 PM UTC)")
    
    # Get credentials
    api_key = os.environ['INSTANTLY_API_KEY']
    database_url = os.environ['DATABASE_URL']
    
    # Date range: yesterday to today
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    start_date = yesterday.strftime('%Y-%m-%d')
    end_date = today.strftime('%Y-%m-%d')
    
    print(f"📅 Date range: {start_date} to {end_date}")
    
    # Fetch from Instantly API
    response = requests.get(
        "https://api.instantly.ai/api/v2/campaigns/analytics/overview",
        params={'start_date': start_date, 'end_date': end_date},
        headers={'Authorization': f'Bearer {api_key}'}
    )
    
    if response.status_code != 200:
        print(f"❌ API Error {response.status_code}: {response.text}")
        raise Exception(f"API Error: {response.status_code}")
    
    data = response.json()
    print(f"✅ Fetched campaign analytics")
    
    # Connect to database
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()
    
    # Ensure table exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS instantly_campaign_analytics_overview (
            id SERIAL PRIMARY KEY,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            campaign_id TEXT NULL,
            open_count INTEGER DEFAULT 0,
            open_count_unique INTEGER DEFAULT 0,
            link_click_count INTEGER DEFAULT 0,
            link_click_count_unique INTEGER DEFAULT 0,
            reply_count INTEGER DEFAULT 0,
            reply_count_unique INTEGER DEFAULT 0,
            bounced_count INTEGER DEFAULT 0,
            unsubscribed_count INTEGER DEFAULT 0,
            completed_count INTEGER DEFAULT 0,
            emails_sent_count INTEGER DEFAULT 0,
            contacted_count INTEGER DEFAULT 0,
            new_leads_contacted_count INTEGER DEFAULT 0,
            total_opportunities INTEGER DEFAULT 0,
            total_opportunity_value INTEGER DEFAULT 0,
            total_interested INTEGER DEFAULT 0,
            total_meeting_booked INTEGER DEFAULT 0,
            total_meeting_completed INTEGER DEFAULT 0,
            total_closed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    # Check for existing record
    cursor.execute("""
        SELECT id FROM instantly_campaign_analytics_overview 
        WHERE start_date = %s AND end_date = %s AND campaign_id IS NULL
    """, (start_date, end_date))
    
    existing = cursor.fetchone()
    
    # Extract metrics
    sent = data.get('emails_sent_count', 0)
    opens = data.get('open_count_unique', 0)
    clicks = data.get('link_click_count_unique', 0)
    replies = data.get('reply_count_unique', 0)
    bounced = data.get('bounced_count', 0)
    
    if existing:
        # Update
        cursor.execute("""
            UPDATE instantly_campaign_analytics_overview SET
                open_count = %s, open_count_unique = %s,
                link_click_count = %s, link_click_count_unique = %s,
                reply_count = %s, reply_count_unique = %s,
                bounced_count = %s, unsubscribed_count = %s,
                completed_count = %s, emails_sent_count = %s,
                contacted_count = %s, new_leads_contacted_count = %s,
                total_opportunities = %s, total_opportunity_value = %s,
                total_interested = %s, total_meeting_booked = %s,
                total_meeting_completed = %s, total_closed = %s,
                updated_at = NOW()
            WHERE start_date = %s AND end_date = %s AND campaign_id IS NULL
        """, (
            data.get('open_count', 0), data.get('open_count_unique', 0),
            data.get('link_click_count', 0), data.get('link_click_count_unique', 0),
            data.get('reply_count', 0), data.get('reply_count_unique', 0),
            data.get('bounced_count', 0), data.get('unsubscribed_count', 0),
            data.get('completed_count', 0), data.get('emails_sent_count', 0),
            data.get('contacted_count', 0), data.get('new_leads_contacted_count', 0),
            data.get('total_opportunities', 0), data.get('total_opportunity_value', 0),
            data.get('total_interested', 0), data.get('total_meeting_booked', 0),
            data.get('total_meeting_completed', 0), data.get('total_closed', 0),
            start_date, end_date
        ))
        print(f"📝 Updated existing record")
    else:
        # Insert
        cursor.execute("""
            INSERT INTO instantly_campaign_analytics_overview (
                start_date, end_date,
                open_count, open_count_unique,
                link_click_count, link_click_count_unique,
                reply_count, reply_count_unique,
                bounced_count, unsubscribed_count,
                completed_count, emails_sent_count,
                contacted_count, new_leads_contacted_count,
                total_opportunities, total_opportunity_value,
                total_interested, total_meeting_booked,
                total_meeting_completed, total_closed
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            start_date, end_date,
            data.get('open_count', 0), data.get('open_count_unique', 0),
            data.get('link_click_count', 0), data.get('link_click_count_unique', 0),
            data.get('reply_count', 0), data.get('reply_count_unique', 0),
            data.get('bounced_count', 0), data.get('unsubscribed_count', 0),
            data.get('completed_count', 0), data.get('emails_sent_count', 0),
            data.get('contacted_count', 0), data.get('new_leads_contacted_count', 0),
            data.get('total_opportunities', 0), data.get('total_opportunity_value', 0),
            data.get('total_interested', 0), data.get('total_meeting_booked', 0),
            data.get('total_meeting_completed', 0), data.get('total_closed', 0)
        ))
        print(f"➕ Created new record")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    # Calculate rates
    open_rate = (opens / sent * 100) if sent > 0 else 0
    click_rate = (clicks / sent * 100) if sent > 0 else 0
    reply_rate = (replies / sent * 100) if sent > 0 else 0
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📊 Campaign Analytics Summary")
    print(f"{'='*60}")
    print(f"📧 Emails Sent: {sent:,}")
    print(f"👀 Opens: {opens:,} ({open_rate:.1f}%)")
    print(f"🔗 Clicks: {clicks:,} ({click_rate:.1f}%)")
    print(f"💬 Replies: {replies:,} ({reply_rate:.1f}%)")
    print(f"❌ Bounced: {bounced:,}")
    print(f"\n💰 Pipeline:")
    print(f"   Opportunities: {data.get('total_opportunities', 0)}")
    print(f"   Meetings Booked: {data.get('total_meeting_booked', 0)}")
    print(f"   Closed Deals: {data.get('total_closed', 0)}")
    
    return {
        "date_range": f"{start_date} to {end_date}",
        "emails_sent": sent,
        "opens": opens,
        "clicks": clicks,
        "replies": replies,
        "open_rate": open_rate,
        "reply_rate": reply_rate
    }


@app.local_entrypoint()
def main():
    result = run_campaign_analytics.remote()
    print(f"\n🎉 Complete! Result: {result}")

