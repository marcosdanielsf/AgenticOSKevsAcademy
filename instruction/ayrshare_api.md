# Ayrshare Social Media API - Master Documentation

## OVERVIEW

Ayrshare is a **unified social media API** that enables management of 13+ social networks through a single integration. Instead of dealing with 13 different APIs, use one API to schedule posts, get analytics, manage comments, send DMs, create ads, and more.

**Documentation Source**: [https://www.ayrshare.com/docs/introduction](https://www.ayrshare.com/docs/introduction)

## SUPPORTED PLATFORMS (13 Networks)

| Platform | Post | Analytics | Comments | Messages | Ads |
|----------|------|-----------|----------|----------|-----|
| **X (Twitter)** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Facebook** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Instagram** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **LinkedIn** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **TikTok** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **YouTube** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **Pinterest** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Google Business** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Reddit** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **Telegram** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Threads** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Bluesky** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Snapchat** | ✅ | ✅ | ❌ | ❌ | ❌ |

---

## API CONFIGURATION

### Base URL
```
https://api.ayrshare.com
```

### Authentication
```http
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json
```

### Environment Variables
```bash
AYRSHARE_API_KEY=your_api_key_here
```

---

## API ENDPOINTS (92 Total)

### 1. POST ENDPOINTS 📝
Core functionality for publishing content across platforms.

#### POST /post - Create Post
Publish to multiple platforms with one call.

```json
POST /post
{
  "post": "Check out our new product launch! 🚀",
  "platforms": ["x", "facebook", "instagram", "linkedin", "tiktok"],
  "mediaUrls": ["https://example.com/image.jpg"],
  "scheduleDate": "2025-12-01T10:00:00Z",
  "shortenLinks": true
}
```

**Parameters:**
- `post` (string, required): Text content of the post
- `platforms` (array, required): Target platforms
- `mediaUrls` (array, optional): URLs to images/videos
- `scheduleDate` (string, optional): ISO 8601 datetime for scheduling
- `shortenLinks` (boolean, optional): Auto-shorten links
- `autoHashtag` (boolean, optional): Auto-generate hashtags
- `title` (string, optional): Title for YouTube/Pinterest
- `thumbnailUrl` (string, optional): Video thumbnail
- `profileKey` (string, optional): For Business Plan multi-user

**Platform-Specific Options:**
- `twitterOptions`: { replyToId, quoteTweetId, poll }
- `facebookOptions`: { feedGroup, locationId }
- `instagramOptions`: { reels, stories, shareToFeed }
- `linkedinOptions`: { visibility, document }
- `youtubeOptions`: { visibility, tags, category }
- `tiktokOptions`: { brandContentToggle, brandOrganicToggle }
- `pinterestOptions`: { boardId, pinTitle, link }

#### DELETE /post - Delete Post
```json
DELETE /post
{
  "id": "post_id_here",
  "platform": "facebook"
}
```

#### PUT /post - Update Post
```json
PUT /post
{
  "id": "post_id_here",
  "platform": "facebook",
  "post": "Updated content"
}
```

#### POST /post/bulk - Bulk Post
```json
POST /post/bulk
{
  "posts": [
    { "post": "First post", "platforms": ["x"] },
    { "post": "Second post", "platforms": ["facebook"] }
  ]
}
```

---

### 2. ANALYTICS ENDPOINTS 📊
Retrieve performance metrics for posts and accounts.

#### GET /analytics/post
Get analytics for a specific post.

```json
GET /analytics/post?id=POST_ID&platforms=facebook,instagram
```

**Response includes:**
- Impressions, reach, engagement
- Likes, comments, shares
- Clicks, saves
- Video views (if applicable)

#### GET /analytics/social
Get account-level analytics.

```json
GET /analytics/social?platform=instagram
```

**Response includes:**
- Follower count
- Follower growth
- Engagement rate
- Top posts

#### GET /analytics/links
Get link click analytics.

```json
GET /analytics/links?linkId=LINK_ID
```

---

### 3. HISTORY ENDPOINTS 📜
View and manage post history.

#### GET /history
Get all posts history.

```json
GET /history?platform=all&status=success&limit=100
```

**Parameters:**
- `platform`: Filter by platform
- `status`: success, error, scheduled, pending
- `limit`: Max results (default 100)
- `lastRecordId`: Pagination cursor

#### GET /history/:id
Get specific post details.

```json
GET /history/POST_ID
```

---

### 4. COMMENTS ENDPOINTS 💬
Manage comments across platforms.

#### GET /comments
Get comments on a post.

```json
GET /comments?id=POST_ID&platform=facebook
```

#### POST /comments
Reply to a comment.

```json
POST /comments
{
  "id": "COMMENT_ID",
  "platforms": ["facebook"],
  "comment": "Thanks for your feedback!"
}
```

#### DELETE /comments
Delete a comment.

```json
DELETE /comments
{
  "id": "COMMENT_ID",
  "platform": "facebook"
}
```

---

### 5. MESSAGES ENDPOINTS 📨
Direct messaging (Instagram, Facebook, X).

#### GET /messages
Get inbox messages.

```json
GET /messages?platform=instagram
```

#### POST /messages
Send a direct message.

```json
POST /messages
{
  "platform": "instagram",
  "recipientId": "USER_ID",
  "message": "Hello! Thanks for reaching out."
}
```

#### GET /messages/conversations
Get conversation threads.

```json
GET /messages/conversations?platform=facebook
```

---

### 6. ADS ENDPOINTS 🎯
Create and manage Facebook ads.

#### POST /ads
Create ad from existing post.

```json
POST /ads
{
  "postId": "POST_ID",
  "objective": "OUTCOME_ENGAGEMENT",
  "budget": 500,
  "duration": 7,
  "targeting": {
    "age_min": 25,
    "age_max": 55,
    "genders": [1, 2],
    "geo_locations": {
      "countries": ["US", "CA"]
    },
    "interests": [
      { "id": "6003139266461", "name": "Fitness" }
    ]
  }
}
```

#### GET /ads
Get ad performance.

```json
GET /ads?adId=AD_ID
```

#### DELETE /ads
Delete an ad.

```json
DELETE /ads?adId=AD_ID
```

---

### 7. AUTO SCHEDULE ENDPOINTS ⏰
Set up automated posting schedules.

#### POST /auto-schedule/set
Configure auto-schedule times.

```json
POST /auto-schedule/set
{
  "schedule": ["09:00", "12:00", "18:00"],
  "timezone": "America/New_York"
}
```

#### GET /auto-schedule
Get current schedule settings.

#### DELETE /auto-schedule/delete
Remove auto-schedule.

---

### 8. MEDIA ENDPOINTS 🖼️
Upload and manage media files.

#### POST /media/upload
Upload media to Ayrshare storage.

```json
POST /media/upload
Content-Type: multipart/form-data

file: [binary data]
```

**Response:**
```json
{
  "url": "https://ayrshare-cdn.s3.amazonaws.com/...",
  "mediaId": "media_123"
}
```

#### GET /media
Get uploaded media library.

#### DELETE /media
Delete uploaded media.

---

### 9. GENERATE ENDPOINTS 🤖
AI-powered content generation.

#### POST /generate
Generate social media content using AI.

```json
POST /generate
{
  "text": "Write a post about our new AI product",
  "platform": "linkedin",
  "tone": "professional",
  "hashtags": true,
  "emojis": true
}
```

#### POST /generate/alt
Generate image alt text.

```json
POST /generate/alt
{
  "url": "https://example.com/image.jpg"
}
```

#### POST /generate/transcription
Transcribe video/audio.

```json
POST /generate/transcription
{
  "mediaUrl": "https://example.com/video.mp4"
}
```

---

### 10. HASHTAGS ENDPOINTS #️⃣
Get hashtag suggestions.

#### POST /hashtags/auto
Auto-generate hashtags.

```json
POST /hashtags/auto
{
  "post": "Check out our new fitness app!",
  "platform": "instagram",
  "max": 10
}
```

#### POST /hashtags/recommend
Get recommended hashtags.

```json
POST /hashtags/recommend
{
  "keyword": "fitness",
  "platform": "instagram"
}
```

---

### 11. LINKS ENDPOINTS 🔗
URL shortening and tracking.

#### POST /links/shorten
Shorten a URL.

```json
POST /links/shorten
{
  "url": "https://example.com/very/long/url",
  "title": "Product Launch"
}
```

#### GET /links
Get shortened links.

#### GET /links/:id/analytics
Get link click analytics.

---

### 12. FEED ENDPOINTS 📰
Get social media feeds.

#### GET /feed
Get feed from connected accounts.

```json
GET /feed?platform=instagram&limit=50
```

---

### 13. BRAND ENDPOINTS 🏷️
Manage brand guidelines.

#### POST /brand
Set brand guidelines.

```json
POST /brand
{
  "name": "My Brand",
  "tone": "professional",
  "keywords": ["innovation", "quality"],
  "avoid": ["competitor names"]
}
```

#### GET /brand
Get brand settings.

---

### 14. PROFILES ENDPOINTS 👤
Manage user profiles (Business Plan).

#### POST /profiles
Create a user profile.

```json
POST /profiles
{
  "title": "Client ABC"
}
```

**Response:**
```json
{
  "profileKey": "profile_abc123",
  "title": "Client ABC"
}
```

#### GET /profiles
Get all profiles.

#### DELETE /profiles
Delete a profile.

---

### 15. USER ENDPOINTS 🔐
Account and authentication management.

#### GET /user
Get current user info.

```json
GET /user
```

**Response:**
```json
{
  "email": "user@example.com",
  "plan": "business",
  "activeSocialAccounts": ["facebook", "instagram", "x"],
  "monthlyPostsRemaining": 500
}
```

#### GET /user/integrations
Get connected social accounts.

#### DELETE /user/social
Disconnect a social account.

```json
DELETE /user/social
{
  "platform": "facebook"
}
```

---

### 16. REVIEWS ENDPOINTS ⭐
Manage Google Business reviews.

#### GET /reviews
Get Google Business reviews.

```json
GET /reviews
```

#### POST /reviews/reply
Reply to a review.

```json
POST /reviews/reply
{
  "reviewId": "REVIEW_ID",
  "reply": "Thank you for your feedback!"
}
```

---

### 17. UTILS ENDPOINTS 🔧
Utility functions.

#### GET /utils/verify
Verify API connection.

```json
GET /utils/verify
```

#### POST /utils/preview
Preview how post will look.

```json
POST /utils/preview
{
  "post": "Test content",
  "platforms": ["instagram"]
}
```

---

### 18. VALIDATE ENDPOINTS ✅
Content validation.

#### POST /validate
Validate post before publishing.

```json
POST /validate
{
  "post": "Test content",
  "platforms": ["x", "instagram"],
  "mediaUrls": ["https://example.com/image.jpg"]
}
```

**Response:**
```json
{
  "valid": true,
  "errors": [],
  "warnings": ["Instagram posts perform better with hashtags"]
}
```

---

### 19. WEBHOOKS ENDPOINTS 🔔
Real-time notifications.

#### POST /webhooks
Register a webhook.

```json
POST /webhooks
{
  "url": "https://your-server.com/webhook",
  "events": ["post.published", "comment.new", "message.new"]
}
```

**Available Events:**
- `post.published` - Post successfully published
- `post.failed` - Post failed to publish
- `comment.new` - New comment received
- `message.new` - New DM received
- `analytics.ready` - Analytics data ready

#### GET /webhooks
Get registered webhooks.

#### DELETE /webhooks
Delete a webhook.

---

## RESPONSE FORMAT

### Success Response
```json
{
  "status": "success",
  "id": "post_123",
  "postIds": [
    { "platform": "facebook", "id": "fb_123", "status": "success" },
    { "platform": "instagram", "id": "ig_456", "status": "success" }
  ]
}
```

### Error Response
```json
{
  "status": "error",
  "code": 400,
  "message": "Invalid platform specified",
  "errors": ["Platform 'tiktokk' is not recognized"]
}
```

---

## RATE LIMITS

| Plan | Posts/Month | API Calls/Min |
|------|-------------|---------------|
| Free | 50 | 60 |
| Premium | 500 | 120 |
| Business | 5000+ | 300 |

---

## MEDIA SPECIFICATIONS

### Images
| Platform | Max Size | Formats | Dimensions |
|----------|----------|---------|------------|
| X | 5 MB | JPG, PNG, GIF | 1200x675 |
| Facebook | 4 MB | JPG, PNG | 1200x630 |
| Instagram | 8 MB | JPG, PNG | 1080x1080 |
| LinkedIn | 8 MB | JPG, PNG | 1200x627 |

### Videos
| Platform | Max Size | Max Duration | Formats |
|----------|----------|--------------|---------|
| X | 512 MB | 140 sec | MP4 |
| Facebook | 4 GB | 240 min | MP4 |
| Instagram Reels | 4 GB | 90 sec | MP4 |
| TikTok | 500 MB | 10 min | MP4 |
| YouTube | 128 GB | 12 hr | MP4 |

---

## BUSINESS PLAN - MULTI-USER

For managing multiple clients/users:

### Create User Profile
```json
POST /profiles
{
  "title": "Client ABC Corp"
}
```

### Post on Behalf of User
```json
POST /post
{
  "post": "Content for client",
  "platforms": ["facebook"],
  "profileKey": "profile_abc123"
}
```

### Get User-Specific Analytics
```json
GET /analytics/social?profileKey=profile_abc123
```

---

## ERROR CODES

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Invalid API key |
| 403 | Forbidden - Plan limit exceeded |
| 404 | Not Found - Resource not found |
| 429 | Rate Limited - Too many requests |
| 500 | Server Error - Try again later |

---

## PLATFORM IDENTIFIERS

Use these exact strings for `platforms` array:

```
"x"              - X (Twitter)
"facebook"       - Facebook
"instagram"      - Instagram
"linkedin"       - LinkedIn
"tiktok"         - TikTok
"youtube"        - YouTube
"pinterest"      - Pinterest
"gmb"            - Google Business
"reddit"         - Reddit
"telegram"       - Telegram
"threads"        - Threads
"bluesky"        - Bluesky
"snapchat"       - Snapchat
```

---

## IMPLEMENTATION NOTES

### Priority Endpoints for AgenticOS
1. **POST /post** - Core posting functionality
2. **GET /analytics/post** - Performance tracking
3. **GET /history** - Post management
4. **POST /webhooks** - Real-time notifications
5. **POST /generate** - AI content generation
6. **GET /comments** - Engagement management
7. **GET /messages** - DM handling

### Database Integration
Store in `ayrshare_posts` table:
- post_id
- platforms (array)
- content
- media_urls
- scheduled_date
- status (scheduled, published, failed)
- analytics_data (JSONB)
- created_at, updated_at

### Cron Job Schedule
- **Analytics Sync**: Every 6 hours
- **Comment Monitoring**: Every 15 minutes
- **Message Monitoring**: Every 5 minutes
- **Webhook Fallback**: Every hour

---

## NEXT STEPS

1. [ ] Set up Ayrshare API key in environment
2. [ ] Connect social media accounts via Ayrshare dashboard
3. [ ] Create database schema for posts/analytics
4. [ ] Implement core posting agent
5. [ ] Implement analytics sync agent
6. [ ] Set up webhook handlers
7. [ ] Create AI content generation workflow

