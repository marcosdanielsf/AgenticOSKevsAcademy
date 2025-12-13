# Ayrshare Daily Analytics Tracker

## GOAL
Track daily social media performance metrics across all connected platforms and store in database for growth analysis.

## API ENDPOINT
**POST** `https://api.ayrshare.com/api/analytics/social`

**Documentation**: [https://www.ayrshare.com/docs/apis/analytics/social](https://www.ayrshare.com/docs/apis/analytics/social)

## CONFIGURATION

### Environment Variables
```bash
AYRSHARE_API_KEY=3E5D1FD5-74D64298-AA26D196-F39B8107
AYRSHARE_PROFILE_KEY=2C5BBFC0-DF9C4454-A2D1401A-203086F9
DATABASE_URL=postgresql://...
```

### Connected Platforms (7)
- Facebook (Readyplayercreate.com)
- Instagram (@kevbuildsapps)
- LinkedIn (Kevin Badi)
- Threads (@kevbuildsapps) ✅ Verified
- TikTok (@kevindoesai)
- X/Twitter (@kevin_badii) 🔵 Premium
- YouTube (Kevin No Code)

---

## KEY METRICS TO TRACK

### 1. ENGAGEMENT METRICS 📈
Track daily interactions to measure content performance.

| Platform | Metrics |
|----------|---------|
| **Facebook** | `pagePostEngagements`, `pageMediaView`, `pagePostsImpressions` |
| **Instagram** | `reach`, `impressions`, `profileViews` |
| **TikTok** | `likeCountTotal`, `commentCountTotal`, `shareCountTotal`, `viewCountTotal` |
| **YouTube** | `likes`, `comments`, `shares`, `views` |
| **Twitter/X** | `likeCount`, `tweetCount` |
| **LinkedIn** | `followersCount` |
| **Threads** | `followersCount` |

### 2. AUDIENCE GROWTH 👥
Track follower/subscriber changes daily.

| Platform | Growth Metrics |
|----------|----------------|
| **Facebook** | `fanCount`, `followersCount`, `pageFollows` |
| **Instagram** | `followersCount`, `followsCount` |
| **TikTok** | `followerCount`, `followingCount` |
| **YouTube** | `subscriberCount`, `subscribersGained`, `subscribersLost` |
| **Twitter/X** | `followersCount`, `friendsCount` |
| **LinkedIn** | `followersCount` |
| **Threads** | `followersCount` |

### 3. CONTENT PERFORMANCE 🎬
Track views and watch time.

| Platform | Performance Metrics |
|----------|---------------------|
| **Facebook** | `pageVideoViews`, `pageVideoViewTime`, `pagePostsImpressionsOrganic` |
| **Instagram** | `reach`, `impressions` |
| **TikTok** | `viewCountTotal`, `profileViews`, `bioLinkClicks` |
| **YouTube** | `viewCount`, `estimatedMinutesWatched`, `averageViewDuration` |
| **Twitter/X** | `tweetCount` |

### 4. CALCULATED METRICS 📊
Derived metrics for dashboard.

```python
# Engagement Rate
engagement_rate = (likes + comments + shares) / reach * 100

# Growth Velocity (daily)
growth_velocity = followers_today - followers_yesterday

# Content Efficiency
content_efficiency = total_engagement / total_posts

# Retention (YouTube)
retention_rate = average_view_duration / video_duration * 100
```

---

## API REQUEST

### Request
```bash
curl \
-H "Authorization: Bearer API_KEY" \
-H "Profile-Key: PROFILE_KEY" \
-H "Content-Type: application/json" \
-d '{"platforms": ["facebook", "instagram", "linkedin", "threads", "tiktok", "twitter", "youtube"]}' \
-X POST https://api.ayrshare.com/api/analytics/social
```

### Response Structure (Per Platform)
```json
{
  "status": "success",
  "facebook": {
    "analytics": {
      "fanCount": 587,
      "followersCount": 587,
      "pagePostEngagements": 20,
      "pagePostsImpressions": 124,
      "pageMediaView": 929
    },
    "lastUpdated": "2025-12-12T17:15:50.784Z"
  },
  "instagram": {
    "analytics": {
      "followersCount": 1500,
      "followsCount": 200,
      "mediaCount": 150,
      "reach": 5000,
      "impressions": 8000,
      "profileViews": 300
    }
  },
  "tiktok": {
    "analytics": {
      "followerCount": 34,
      "followingCount": 39,
      "likeCountTotal": 2,
      "commentCountTotal": 1807,
      "shareCountTotal": 4,
      "viewCountTotal": 1493,
      "profileViews": 79346,
      "bioLinkClicks": 2
    }
  },
  "youtube": {
    "analytics": {
      "subscriberCount": "67",
      "subscribersGained": 34,
      "subscribersLost": 2,
      "viewCount": "5",
      "views": 44,
      "likes": 3,
      "comments": 8,
      "shares": 34,
      "estimatedMinutesWatched": 72,
      "averageViewDuration": 99
    }
  },
  "twitter": {
    "analytics": {
      "followersCount": 11253,
      "friendsCount": 4242,
      "likeCount": 561,
      "tweetCount": 2930
    }
  },
  "linkedin": {
    "analytics": {
      "followersCount": 500
    }
  },
  "threads": {
    "analytics": {
      "followersCount": 1000
    }
  }
}
```

---

## DATABASE SCHEMA

### Table: `social_media_analytics`
```sql
CREATE TABLE social_media_analytics (
    id SERIAL PRIMARY KEY,
    
    -- Timestamp
    recorded_at TIMESTAMP DEFAULT NOW(),
    date DATE DEFAULT CURRENT_DATE,
    
    -- Platform
    platform TEXT NOT NULL,
    
    -- Audience Metrics
    followers_count INTEGER,
    following_count INTEGER,
    subscribers_gained INTEGER,
    subscribers_lost INTEGER,
    
    -- Engagement Metrics
    likes_total INTEGER,
    comments_total INTEGER,
    shares_total INTEGER,
    engagement_total INTEGER,
    
    -- Content Performance
    views_total INTEGER,
    impressions INTEGER,
    reach INTEGER,
    profile_views INTEGER,
    
    -- Video Metrics (YouTube/TikTok/Facebook)
    watch_time_minutes INTEGER,
    avg_view_duration INTEGER,
    
    -- Calculated
    engagement_rate DECIMAL(5,2),
    growth_velocity INTEGER,
    
    -- Raw Data
    raw_data JSONB,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index for fast daily queries
CREATE INDEX idx_analytics_date_platform ON social_media_analytics(date, platform);
CREATE INDEX idx_analytics_platform ON social_media_analytics(platform);
```

---

## CRON SCHEDULE

- **Schedule**: Daily at 6:00 AM EST (11:00 AM UTC)
- **Cron Expression**: `0 11 * * *`
- **Platform**: Modal (serverless)

### Why 6 AM EST?
- Captures full previous day's data
- Before morning content posting
- Consistent daily snapshot

---

## WORKFLOW

### 1. Fetch Analytics
```python
response = requests.post(
    'https://api.ayrshare.com/api/analytics/social',
    headers={
        'Authorization': f'Bearer {API_KEY}',
        'Profile-Key': PROFILE_KEY,
        'Content-Type': 'application/json'
    },
    json={'platforms': ['facebook', 'instagram', 'linkedin', 'threads', 'tiktok', 'twitter', 'youtube']}
)
```

### 2. Parse Metrics
Extract key metrics from each platform's response.

### 3. Calculate Derived Metrics
- Engagement rate
- Growth velocity (compare to yesterday)
- Content efficiency

### 4. Store in Database
Insert row per platform with all metrics.

### 5. Return Summary
```json
{
  "status": "success",
  "date": "2025-12-12",
  "platforms_tracked": 7,
  "total_followers": 15000,
  "total_engagement": 500,
  "top_performer": "tiktok"
}
```

---

## SUCCESS CRITERIA

- ✅ Fetch analytics from all 7 connected platforms
- ✅ Store daily snapshot in database
- ✅ Calculate engagement rate and growth velocity
- ✅ Track follower count changes over time
- ✅ Run automatically at 6 AM EST daily
- ✅ Handle API errors gracefully

---

## DASHBOARD QUERIES

### Daily Growth
```sql
SELECT date, platform, followers_count,
       followers_count - LAG(followers_count) OVER (PARTITION BY platform ORDER BY date) as daily_growth
FROM social_media_analytics
WHERE date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY date DESC, platform;
```

### Best Performing Platform
```sql
SELECT platform, AVG(engagement_rate) as avg_engagement
FROM social_media_analytics
WHERE date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY platform
ORDER BY avg_engagement DESC;
```

### Weekly Summary
```sql
SELECT 
    platform,
    MAX(followers_count) - MIN(followers_count) as follower_growth,
    SUM(engagement_total) as total_engagement,
    AVG(engagement_rate) as avg_engagement_rate
FROM social_media_analytics
WHERE date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY platform;
```

