# Instantly.ai Analytics Integration Overview

This document covers the two different analytics API integrations for Instantly.ai and their respective database storage.

## Analytics API Types

### 1. **Daily Email Analytics** (`instantly_analytics.py`)

**Purpose**: Track daily email account performance
**API Endpoint**: `POST /api/v2/accounts/analytics/daily`
**Database Table**: `instantly_email_daily_analytics`

#### API Schema:
```json
[
  {
    "date": "2025-12-09",
    "email_account": "adrian@provazenpathdyno.org",
    "sent": 2,
    "bounced": 2
  }
]
```

#### Database Schema:
```sql
CREATE TABLE instantly_email_daily_analytics (
  id SERIAL PRIMARY KEY,
  date TEXT NOT NULL,
  email_account TEXT NOT NULL,
  sent INTEGER NOT NULL DEFAULT 0,
  bounced INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

#### Usage:
```bash
# Fetch today's email analytics
python3 implementation/instantly_analytics.py

# Fetch for specific date
python3 implementation/instantly_analytics.py --date "2025-12-09"

# Fetch for specific email accounts
python3 implementation/instantly_analytics.py --emails "user1@example.com,user2@example.com"
```

---

### 2. **Campaign Analytics Overview** (`instantly_campaign_analytics.py`)

**Purpose**: Track comprehensive campaign performance and sales pipeline
**API Endpoint**: `GET /api/v2/campaigns/analytics/overview`
**Database Table**: `instantly_campaign_analytics_overview`

#### API Schema (24 Fields):
```json
{
  "open_count": 800,
  "open_count_unique": 800,
  "open_count_unique_by_step": 800,
  "link_click_count": 800,
  "link_click_count_unique": 800,
  "link_click_count_unique_by_step": 800,
  "reply_count": 300,
  "reply_count_unique": 300,
  "reply_count_unique_by_step": 300,
  "reply_count_automatic": 50,
  "reply_count_automatic_unique": 45,
  "reply_count_automatic_unique_by_step": 45,
  "bounced_count": 50,
  "unsubscribed_count": 20,
  "completed_count": 1100,
  "emails_sent_count": 5000,
  "contacted_count": 4500,
  "new_leads_contacted_count": 200,
  "total_opportunities": 10,
  "total_opportunity_value": 1000,
  "total_interested": 103,
  "total_meeting_booked": 45,
  "total_meeting_completed": 12,
  "total_closed": 10
}
```

#### Database Schema:
```sql
CREATE TABLE instantly_campaign_analytics_overview (
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
```

#### Usage:
```bash
# Fetch campaign analytics for yesterday-today
python3 implementation/instantly_campaign_analytics.py

# Fetch for specific date range
python3 implementation/instantly_campaign_analytics.py --start-date "2025-12-08" --end-date "2025-12-09"

# Fetch for specific campaign
python3 implementation/instantly_campaign_analytics.py --campaign-id "adb1f3f6-0035-4edd-9252-1073138787df"
```

## Key Differences

| Feature | Daily Email Analytics | Campaign Analytics Overview |
|---------|----------------------|------------------------------|
| **Granularity** | Per email account, per day | Aggregated campaign data |
| **Metrics** | Basic: sent, bounced | Comprehensive: 24 engagement & sales metrics |
| **Time Range** | Single day focus | Flexible date ranges |
| **Use Case** | Email deliverability monitoring | Campaign performance & ROI tracking |
| **API Method** | GET | GET |
| **Response Format** | Array of account objects | Single aggregated object |

## Common Workflows

### Daily Monitoring
```bash
# Check email health daily
python3 implementation/instantly_analytics.py

# Check campaign performance for date range
python3 implementation/instantly_campaign_analytics.py --start-date "2025-12-01" --end-date "2025-12-09"
```

### Account Health Check
```bash
# Monitor specific problematic accounts
python3 implementation/instantly_analytics.py --emails "high-bounce-account@domain.com"
```

### Campaign Performance Analysis
```bash
# Analyze specific campaign performance
python3 implementation/instantly_campaign_analytics.py --campaign-id "campaign-uuid"
```

## Database Relationships

- **Email Analytics**: Track individual email account performance over time
- **Campaign Analytics**: Track overall campaign success metrics and sales pipeline
- Both tables are independent but complementary for comprehensive email marketing analysis

## Alert Thresholds

### Email Health (Daily Analytics)
- **Bounce Rate > 20%**: Email account needs attention
- **Bounce Rate > 50%**: Email account at risk of being blacklisted

### Campaign Performance (Campaign Analytics)
- **Open Rate < 20%**: Subject lines need optimization
- **Reply Rate < 2%**: Message content needs improvement
- **No opportunities generated**: Lead qualification or targeting issues