"""
Modal Cron Job: Instantly Analytics

Runs every day at 9 AM UTC to fetch email analytics from Instantly.ai
and store in the database.

Deploy: modal deploy modal_instantly_analytics.py
Test:   modal run modal_instantly_analytics.py
"""

import modal

# Create Modal app
app = modal.App("instantly-analytics")

# Create image with dependencies
image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "requests",
    "psycopg2-binary",
)

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("agenticos-secrets")],
    schedule=modal.Cron("0 23 * * *"),  # 11 PM UTC = 6 PM EST daily
    timeout=300,  # 5 minute timeout
)
def run_instantly_analytics():
    """Fetch daily email analytics from Instantly.ai and store in database"""
    import os
    import requests
    import psycopg2
    from datetime import datetime
    
    print("🚀 Instantly Analytics - Modal Cron Job")
    print("=" * 50)
    print("⏰ Schedule: 6:00 PM EST daily (11:00 PM UTC)")
    
    # Get credentials from secrets
    api_key = os.environ['INSTANTLY_API_KEY']
    database_url = os.environ['DATABASE_URL']
    
    # Today's date
    target_date = datetime.now().strftime('%Y-%m-%d')
    print(f"📅 Fetching analytics for: {target_date}")
    
    # Fetch from Instantly API
    response = requests.get(
        "https://api.instantly.ai/api/v2/accounts/analytics/daily",
        params={'start_date': target_date, 'end_date': target_date},
        headers={'Authorization': f'Bearer {api_key}'}
    )
    
    if response.status_code != 200:
        print(f"❌ API Error {response.status_code}: {response.text}")
        raise Exception(f"API Error: {response.status_code}")
    
    analytics_data = response.json()
    print(f"✅ Fetched data for {len(analytics_data)} email accounts")
    
    # Store in database
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()
    
    stored_count = 0
    total_sent = 0
    total_bounced = 0
    
    for account in analytics_data:
        email = account.get('email_account', 'unknown')
        sent = account.get('sent', 0)
        bounced = account.get('bounced', 0)
        
        total_sent += sent
        total_bounced += bounced
        
        # Upsert record
        cursor.execute("""
            INSERT INTO instantly_email_daily_analytics 
            (date, email_account, sent, bounced, created_at, updated_at)
            VALUES (%s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (date, email_account) 
            DO UPDATE SET sent = EXCLUDED.sent, bounced = EXCLUDED.bounced, updated_at = NOW()
        """, (target_date, email, sent, bounced))
        
        bounce_rate = (bounced / sent * 100) if sent > 0 else 0
        print(f"  📧 {email}: sent={sent}, bounced={bounced} ({bounce_rate:.1f}%)")
        stored_count += 1
    
    conn.commit()
    cursor.close()
    conn.close()
    
    # Summary
    overall_bounce_rate = (total_bounced / total_sent * 100) if total_sent > 0 else 0
    print(f"\n{'='*50}")
    print(f"✅ Stored {stored_count} records in database")
    print(f"📊 Total: {total_sent} sent, {total_bounced} bounced ({overall_bounce_rate:.1f}%)")
    
    return {
        "date": target_date,
        "accounts": stored_count,
        "total_sent": total_sent,
        "total_bounced": total_bounced,
        "bounce_rate": overall_bounce_rate
    }


# For manual testing: modal run modal_instantly_analytics.py
@app.local_entrypoint()
def main():
    result = run_instantly_analytics.remote()
    print(f"\n🎉 Complete! Result: {result}")

