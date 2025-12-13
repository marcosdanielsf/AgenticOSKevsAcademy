"""
Modal Cron Job: Ayrshare Daily Analytics Tracker

Daily snapshot of all social media metrics across platforms.
Stores in ayrshare_daily_analytics table.

Schedule: Daily at 6:00 PM EST (11:00 PM UTC)

Deploy: modal deploy modal_ayrshare_analytics.py
Test:   modal run modal_ayrshare_analytics.py
"""

import modal
import json

app = modal.App("ayrshare-daily-analytics")

image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "requests",
    "psycopg2-binary",
)

PLATFORMS = ['facebook', 'instagram', 'linkedin', 'threads', 'tiktok', 'twitter', 'youtube']


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("agenticos-secrets")],
    schedule=modal.Cron("0 23 * * *"),  # 11 PM UTC = 6 PM EST daily
    timeout=300,
)
def run_daily_analytics():
    """Fetch and store daily social media analytics snapshot"""
    import os
    import requests
    import psycopg2
    from datetime import date, timedelta

    print("🚀 Ayrshare Daily Analytics")
    print("=" * 60)
    print(f"📅 Date: {date.today()}")

    api_key = os.environ['AYRSHARE_API_KEY']
    profile_key = os.environ.get('AYRSHARE_PROFILE_KEY', '')
    database_url = os.environ['DATABASE_URL']

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    if profile_key:
        headers['Profile-Key'] = profile_key

    try:
        # Fetch analytics
        print("\n🔍 Fetching analytics from all platforms...")
        response = requests.post(
            'https://api.ayrshare.com/api/analytics/social',
            headers=headers,
            json={'platforms': PLATFORMS}
        )

        try:
            data = response.json()
        except:
            print(f"❌ Invalid JSON response")
            return {"status": "error", "error": "Invalid JSON"}

        # Check for valid platform data
        has_valid_data = any(
            platform in data and 'analytics' in data[platform]
            for platform in PLATFORMS
        )

        if not has_valid_data:
            print("❌ No valid analytics data found")
            return {"status": "error", "error": "No valid data"}

        print("✅ Successfully fetched analytics")
        if response.status_code != 200:
            print(f"   ⚠️  Warning: Some platforms may have errors")

        # Parse metrics
        all_metrics = []
        for platform in PLATFORMS:
            if platform in data and 'analytics' in data[platform]:
                analytics = data[platform]['analytics']
                metrics = parse_platform_metrics(platform, analytics)
                all_metrics.append(metrics)
                print(f"   📱 {platform}: {metrics['followers'] or 0:,} followers")

        # Store in database
        print("\n💾 Storing in ayrshare_daily_analytics...")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        # Ensure table exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ayrshare_daily_analytics (
                id SERIAL PRIMARY KEY,
                date DATE NOT NULL DEFAULT CURRENT_DATE,
                platform TEXT NOT NULL,
                followers INTEGER, following INTEGER,
                subscribers_gained INTEGER, subscribers_lost INTEGER,
                followers_change INTEGER, likes_change INTEGER, views_change INTEGER,
                likes INTEGER, comments INTEGER, shares INTEGER,
                reposts INTEGER, quotes INTEGER, replies INTEGER,
                reactions INTEGER, dislikes INTEGER,
                views INTEGER, reach INTEGER, impressions INTEGER, profile_views INTEGER,
                video_count INTEGER, video_views INTEGER, watch_time_minutes INTEGER,
                avg_view_duration_secs INTEGER, avg_view_percentage DECIMAL(5,2),
                playlist_adds INTEGER, playlist_removes INTEGER,
                bio_link_clicks INTEGER, email_clicks INTEGER, phone_clicks INTEGER,
                address_clicks INTEGER, app_download_clicks INTEGER,
                posts_count INTEGER, media_count INTEGER, tweet_count INTEGER, listed_count INTEGER,
                is_verified BOOLEAN, is_business BOOLEAN, is_monetized BOOLEAN,
                subscription_type TEXT,
                audience_ages JSONB, audience_countries JSONB, audience_genders JSONB,
                raw_data JSONB,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(date, platform)
            );
        ''')

        stored_count = 0
        total_followers = 0

        for m in all_metrics:
            platform = m['platform']

            # Get yesterday's data for change calculation
            yesterday = date.today() - timedelta(days=1)
            cursor.execute('''
                SELECT followers, likes, views FROM ayrshare_daily_analytics
                WHERE platform = %s AND date = %s
            ''', (platform, yesterday))
            yest = cursor.fetchone()

            followers_change = None
            likes_change = None
            views_change = None
            if yest:
                if m['followers'] and yest[0]:
                    followers_change = m['followers'] - yest[0]
                if m['likes'] and yest[1]:
                    likes_change = m['likes'] - yest[1]
                if m['views'] and yest[2]:
                    views_change = m['views'] - yest[2]

            cursor.execute('''
                INSERT INTO ayrshare_daily_analytics (
                    date, platform,
                    followers, following, subscribers_gained, subscribers_lost,
                    followers_change, likes_change, views_change,
                    likes, comments, shares, reposts, quotes, replies, reactions, dislikes,
                    views, reach, impressions, profile_views,
                    video_count, video_views, watch_time_minutes, avg_view_duration_secs, avg_view_percentage,
                    playlist_adds, playlist_removes,
                    bio_link_clicks, email_clicks, phone_clicks, address_clicks, app_download_clicks,
                    posts_count, media_count, tweet_count, listed_count,
                    is_verified, is_business, is_monetized, subscription_type,
                    audience_ages, audience_countries, audience_genders,
                    raw_data, created_at
                ) VALUES (
                    CURRENT_DATE, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, NOW()
                )
                ON CONFLICT (date, platform) DO UPDATE SET
                    followers = EXCLUDED.followers,
                    following = EXCLUDED.following,
                    subscribers_gained = EXCLUDED.subscribers_gained,
                    subscribers_lost = EXCLUDED.subscribers_lost,
                    followers_change = EXCLUDED.followers_change,
                    likes_change = EXCLUDED.likes_change,
                    views_change = EXCLUDED.views_change,
                    likes = EXCLUDED.likes,
                    comments = EXCLUDED.comments,
                    shares = EXCLUDED.shares,
                    reposts = EXCLUDED.reposts,
                    quotes = EXCLUDED.quotes,
                    replies = EXCLUDED.replies,
                    reactions = EXCLUDED.reactions,
                    dislikes = EXCLUDED.dislikes,
                    views = EXCLUDED.views,
                    reach = EXCLUDED.reach,
                    impressions = EXCLUDED.impressions,
                    profile_views = EXCLUDED.profile_views,
                    video_count = EXCLUDED.video_count,
                    video_views = EXCLUDED.video_views,
                    watch_time_minutes = EXCLUDED.watch_time_minutes,
                    avg_view_duration_secs = EXCLUDED.avg_view_duration_secs,
                    avg_view_percentage = EXCLUDED.avg_view_percentage,
                    playlist_adds = EXCLUDED.playlist_adds,
                    playlist_removes = EXCLUDED.playlist_removes,
                    bio_link_clicks = EXCLUDED.bio_link_clicks,
                    email_clicks = EXCLUDED.email_clicks,
                    phone_clicks = EXCLUDED.phone_clicks,
                    address_clicks = EXCLUDED.address_clicks,
                    app_download_clicks = EXCLUDED.app_download_clicks,
                    posts_count = EXCLUDED.posts_count,
                    media_count = EXCLUDED.media_count,
                    tweet_count = EXCLUDED.tweet_count,
                    listed_count = EXCLUDED.listed_count,
                    is_verified = EXCLUDED.is_verified,
                    is_business = EXCLUDED.is_business,
                    is_monetized = EXCLUDED.is_monetized,
                    subscription_type = EXCLUDED.subscription_type,
                    audience_ages = EXCLUDED.audience_ages,
                    audience_countries = EXCLUDED.audience_countries,
                    audience_genders = EXCLUDED.audience_genders,
                    raw_data = EXCLUDED.raw_data
            ''', (
                platform,
                m['followers'], m['following'], m['subscribers_gained'], m['subscribers_lost'],
                followers_change, likes_change, views_change,
                m['likes'], m['comments'], m['shares'], m['reposts'], m['quotes'], m['replies'], m['reactions'], m['dislikes'],
                m['views'], m['reach'], m['impressions'], m['profile_views'],
                m['video_count'], m['video_views'], m['watch_time_minutes'], m['avg_view_duration_secs'], m['avg_view_percentage'],
                m['playlist_adds'], m['playlist_removes'],
                m['bio_link_clicks'], m['email_clicks'], m['phone_clicks'], m['address_clicks'], m['app_download_clicks'],
                m['posts_count'], m['media_count'], m['tweet_count'], m['listed_count'],
                m['is_verified'], m['is_business'], m['is_monetized'], m['subscription_type'],
                json.dumps(m['audience_ages']) if m['audience_ages'] else None,
                json.dumps(m['audience_countries']) if m['audience_countries'] else None,
                json.dumps(m['audience_genders']) if m['audience_genders'] else None,
                json.dumps(m['raw_data']) if m['raw_data'] else None
            ))

            stored_count += 1
            total_followers += m['followers'] or 0
            fc_str = f" ({'+' if followers_change and followers_change >= 0 else ''}{followers_change} today)" if followers_change else ""
            print(f"   ✅ {platform}{fc_str}")

        conn.commit()
        cursor.close()
        conn.close()

        print(f"\n✅ WORKFLOW COMPLETE")
        print(f"   • Platforms: {stored_count}")
        print(f"   • Total Followers: {total_followers:,}")
        print(f"   • Next run: Tomorrow at 6:00 PM EST")

        return {
            "status": "success",
            "date": str(date.today()),
            "platforms": stored_count,
            "total_followers": total_followers
        }

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "error": str(e)}


def parse_platform_metrics(platform, a):
    """Parse platform-specific metrics"""
    m = {
        'platform': platform,
        'followers': None, 'following': None,
        'subscribers_gained': None, 'subscribers_lost': None,
        'likes': None, 'comments': None, 'shares': None,
        'reposts': None, 'quotes': None, 'replies': None,
        'reactions': None, 'dislikes': None,
        'views': None, 'reach': None, 'impressions': None, 'profile_views': None,
        'video_count': None, 'video_views': None, 'watch_time_minutes': None,
        'avg_view_duration_secs': None, 'avg_view_percentage': None,
        'playlist_adds': None, 'playlist_removes': None,
        'bio_link_clicks': None, 'email_clicks': None, 'phone_clicks': None,
        'address_clicks': None, 'app_download_clicks': None,
        'posts_count': None, 'media_count': None, 'tweet_count': None, 'listed_count': None,
        'is_verified': None, 'is_business': None, 'is_monetized': None, 'subscription_type': None,
        'audience_ages': None, 'audience_countries': None, 'audience_genders': None,
        'raw_data': a
    }

    if not a:
        return m

    if platform == 'tiktok':
        m['followers'] = a.get('followerCount')
        m['following'] = a.get('followingCount')
        m['likes'] = a.get('likeCountTotal')
        m['comments'] = a.get('commentCountTotal')
        m['shares'] = a.get('shareCountTotal')
        m['views'] = a.get('viewCountTotal')
        m['profile_views'] = a.get('profileViews')
        m['video_count'] = a.get('videoCountTotal')
        m['bio_link_clicks'] = a.get('bioLinkClicks')
        m['email_clicks'] = a.get('emailClicks')
        m['phone_clicks'] = a.get('phoneNumberClicks')
        m['address_clicks'] = a.get('addressClicks')
        m['app_download_clicks'] = a.get('appDownloadClicks')
        m['is_business'] = a.get('isBusinessAccount')
        m['audience_ages'] = a.get('audienceAges')
        m['audience_countries'] = a.get('audienceCountries')
        m['audience_genders'] = a.get('audienceGenders')

    elif platform == 'youtube':
        m['followers'] = int(a.get('subscriberCount', 0) or 0)
        m['subscribers_gained'] = a.get('subscribersGained')
        m['subscribers_lost'] = a.get('subscribersLost')
        m['likes'] = a.get('likes')
        m['comments'] = a.get('comments')
        m['shares'] = a.get('shares')
        m['dislikes'] = a.get('dislikes')
        m['views'] = int(a.get('viewCount', 0) or 0)
        m['video_count'] = int(a.get('videoCount', 0) or 0)
        m['watch_time_minutes'] = a.get('estimatedMinutesWatched')
        m['avg_view_duration_secs'] = a.get('averageViewDuration')
        m['avg_view_percentage'] = a.get('averageViewPercentage')
        m['playlist_adds'] = a.get('videosAddedToPlaylists')
        m['playlist_removes'] = a.get('videosRemovedFromPlaylists')
        m['is_monetized'] = a.get('isChannelMonetizationEnabled')

    elif platform == 'instagram':
        m['followers'] = a.get('followersCount')
        m['following'] = a.get('followsCount')
        m['likes'] = a.get('likeCount')
        m['comments'] = a.get('commentsCount')
        m['reach'] = a.get('reachCount')
        m['views'] = a.get('viewsCount')
        m['media_count'] = a.get('mediaCount')

    elif platform == 'twitter':
        m['followers'] = a.get('followersCount')
        m['following'] = a.get('followingCount') or a.get('friendsCount')
        m['likes'] = a.get('likeCount')
        m['tweet_count'] = a.get('tweetCount')
        m['listed_count'] = a.get('listedCount')
        m['is_verified'] = a.get('verified')
        m['subscription_type'] = a.get('subscriptionType')

    elif platform == 'facebook':
        m['followers'] = a.get('followersCount') or a.get('fanCount')
        m['likes'] = a.get('pagePostEngagements')
        m['views'] = a.get('pageMediaView')
        m['video_views'] = a.get('pageVideoViews')
        m['impressions'] = a.get('pagePostsImpressions')
        m['reach'] = a.get('pagePostsImpressionsUnique')
        if isinstance(a.get('reactions'), dict):
            m['reactions'] = a['reactions'].get('total')

    elif platform == 'linkedin':
        m['followers'] = a.get('followersCount')

    elif platform == 'threads':
        m['followers'] = a.get('followersCount')
        m['likes'] = a.get('likes')
        m['views'] = a.get('views')
        m['replies'] = a.get('replies')
        m['reposts'] = a.get('reposts')
        m['quotes'] = a.get('quotes')
        m['is_verified'] = a.get('isVerified')
        if a.get('followerDemographics'):
            m['audience_countries'] = a.get('followerDemographics')

    return m


@app.local_entrypoint()
def main():
    result = run_daily_analytics.remote()
    print(f"\n🎉 Complete! Result: {result}")
