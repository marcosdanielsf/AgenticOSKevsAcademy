#!/usr/bin/env python3
"""
Ayrshare Daily Analytics Tracker - COMPLETE SOLUTION

Strategy: Store daily SNAPSHOTS of all metrics, then calculate
daily/weekly/monthly changes by comparing snapshots.

Features:
- Comprehensive metric collection for all platforms
- Daily snapshot storage with UPSERT
- Automatic daily change calculation (vs yesterday)
- Demographics storage (ages, countries, genders)
- Full raw data backup (JSONB)

Table: ayrshare_daily_analytics

Usage:
    python3 implementation/ayrshare_daily_analytics.py
    python3 implementation/ayrshare_daily_analytics.py --store
"""

import os
import json
import requests
import psycopg2
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
import argparse

load_dotenv()

# Configuration
AYRSHARE_API_KEY = os.getenv('AYRSHARE_API_KEY')
AYRSHARE_PROFILE_KEY = os.getenv('AYRSHARE_PROFILE_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')
API_BASE_URL = "https://api.ayrshare.com/api"

PLATFORMS = ['facebook', 'instagram', 'linkedin', 'threads', 'tiktok', 'twitter', 'youtube']

if not AYRSHARE_API_KEY:
    raise ValueError("AYRSHARE_API_KEY not found in environment variables")


def get_headers():
    """Get headers for Ayrshare API requests"""
    headers = {
        'Authorization': f'Bearer {AYRSHARE_API_KEY}',
        'Content-Type': 'application/json'
    }
    if AYRSHARE_PROFILE_KEY:
        headers['Profile-Key'] = AYRSHARE_PROFILE_KEY
    return headers


def fetch_social_analytics():
    """Fetch analytics from all connected social platforms"""
    url = f"{API_BASE_URL}/analytics/social"
    headers = get_headers()
    payload = {"platforms": PLATFORMS}

    print("🔍 Fetching social media analytics...")

    try:
        response = requests.post(url, headers=headers, json=payload)
        
        # API may return 400 if one platform has error, but still contains valid data
        try:
            data = response.json()
        except:
            print(f"❌ Invalid JSON response: {response.text[:200]}")
            return None
            
        # Check if we got any valid platform data
        has_valid_data = any(
            platform in data and 'analytics' in data[platform]
            for platform in PLATFORMS
        )
        
        if has_valid_data:
            print("✅ Successfully fetched analytics")
            if response.status_code != 200:
                print(f"   ⚠️  Warning: Some platforms may have errors (status {response.status_code})")
            return data
        else:
            print(f"❌ No valid analytics data found")
            return None

    except requests.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None


def parse_platform_metrics(platform, analytics_data):
    """Parse platform-specific metrics into standardized format"""
    m = {
        'platform': platform,
        # Audience
        'followers': None,
        'following': None,
        'subscribers_gained': None,
        'subscribers_lost': None,
        # Engagement
        'likes': None,
        'comments': None,
        'shares': None,
        'reposts': None,
        'quotes': None,
        'replies': None,
        'reactions': None,
        'dislikes': None,
        # Views & Reach
        'views': None,
        'reach': None,
        'impressions': None,
        'profile_views': None,
        # Video
        'video_count': None,
        'video_views': None,
        'watch_time_minutes': None,
        'avg_view_duration_secs': None,
        'avg_view_percentage': None,
        'playlist_adds': None,
        'playlist_removes': None,
        # CTA Clicks
        'bio_link_clicks': None,
        'email_clicks': None,
        'phone_clicks': None,
        'address_clicks': None,
        'app_download_clicks': None,
        # Content
        'posts_count': None,
        'media_count': None,
        'tweet_count': None,
        'listed_count': None,
        # Account
        'is_verified': None,
        'is_business': None,
        'is_monetized': None,
        'subscription_type': None,
        # Demographics
        'audience_ages': None,
        'audience_countries': None,
        'audience_genders': None,
        # Raw
        'raw_data': analytics_data
    }

    if not analytics_data:
        return m

    a = analytics_data

    # ============ TIKTOK ============
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

    # ============ YOUTUBE ============
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

    # ============ INSTAGRAM ============
    elif platform == 'instagram':
        m['followers'] = a.get('followersCount')
        m['following'] = a.get('followsCount')
        m['likes'] = a.get('likeCount')
        m['comments'] = a.get('commentsCount')
        m['reach'] = a.get('reachCount')
        m['views'] = a.get('viewsCount')
        m['media_count'] = a.get('mediaCount')

    # ============ TWITTER/X ============
    elif platform == 'twitter':
        m['followers'] = a.get('followersCount')
        m['following'] = a.get('followingCount') or a.get('friendsCount')
        m['likes'] = a.get('likeCount')
        m['tweet_count'] = a.get('tweetCount')
        m['listed_count'] = a.get('listedCount')
        m['is_verified'] = a.get('verified')
        m['subscription_type'] = a.get('subscriptionType')

    # ============ FACEBOOK ============
    elif platform == 'facebook':
        m['followers'] = a.get('followersCount') or a.get('fanCount')
        m['likes'] = a.get('pagePostEngagements')
        m['views'] = a.get('pageMediaView')
        m['video_views'] = a.get('pageVideoViews')
        m['impressions'] = a.get('pagePostsImpressions')
        m['reach'] = a.get('pagePostsImpressionsUnique')
        if isinstance(a.get('reactions'), dict):
            m['reactions'] = a['reactions'].get('total')
        m['is_verified'] = a.get('verified')

    # ============ LINKEDIN ============
    elif platform == 'linkedin':
        m['followers'] = a.get('followersCount')

    # ============ THREADS ============
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


def get_yesterday_metrics(cursor, platform):
    """Get yesterday's metrics for calculating daily changes"""
    yesterday = date.today() - timedelta(days=1)
    
    cursor.execute('''
        SELECT followers, likes, comments, shares, views, reach, profile_views,
               bio_link_clicks, subscribers_gained, subscribers_lost
        FROM ayrshare_daily_analytics
        WHERE platform = %s AND date = %s
    ''', (platform, yesterday))
    
    row = cursor.fetchone()
    if row:
        return {
            'followers': row[0],
            'likes': row[1],
            'comments': row[2],
            'shares': row[3],
            'views': row[4],
            'reach': row[5],
            'profile_views': row[6],
            'bio_link_clicks': row[7],
            'subscribers_gained': row[8],
            'subscribers_lost': row[9]
        }
    return None


def calculate_daily_changes(current, yesterday):
    """Calculate daily changes between today and yesterday"""
    if not yesterday:
        return {}
    
    changes = {}
    
    def safe_diff(key):
        curr = current.get(key) or 0
        yest = yesterday.get(key) or 0
        return curr - yest if curr and yest else None
    
    changes['followers_change'] = safe_diff('followers')
    changes['likes_change'] = safe_diff('likes')
    changes['comments_change'] = safe_diff('comments')
    changes['shares_change'] = safe_diff('shares')
    changes['views_change'] = safe_diff('views')
    changes['reach_change'] = safe_diff('reach')
    changes['profile_views_change'] = safe_diff('profile_views')
    changes['bio_link_clicks_change'] = safe_diff('bio_link_clicks')
    
    return changes


def display_analytics(all_metrics, daily_changes=None):
    """Display comprehensive analytics summary"""
    print("\n" + "=" * 70)
    print("📊 DAILY SOCIAL MEDIA ANALYTICS SNAPSHOT")
    print("=" * 70)
    print(f"📅 Date: {date.today()}")
    print()

    total_followers = 0
    total_engagement = 0

    for m in all_metrics:
        platform = m['platform'].upper()
        followers = m['followers'] or 0
        
        # Calculate engagement
        engagement = sum(filter(None, [
            m['likes'], m['comments'], m['shares'],
            m['replies'], m['reposts'], m['reactions']
        ]))
        
        total_followers += followers
        total_engagement += engagement

        print(f"📱 {platform}")
        
        # Followers with daily change
        change_str = ""
        if daily_changes and platform.lower() in daily_changes:
            fc = daily_changes[platform.lower()].get('followers_change')
            if fc is not None:
                sign = '+' if fc >= 0 else ''
                change_str = f" ({sign}{fc:,} today)"
        print(f"   👥 Followers: {followers:,}{change_str}")
        
        # Engagement metrics
        if m['likes']:
            print(f"   ❤️  Likes: {m['likes']:,}")
        if m['comments']:
            print(f"   💬 Comments: {m['comments']:,}")
        if m['shares']:
            print(f"   🔄 Shares: {m['shares']:,}")
        if m['dislikes']:
            print(f"   👎 Dislikes: {m['dislikes']:,}")
            
        # Views & Reach
        if m['views']:
            print(f"   👁️  Views: {m['views']:,}")
        if m['reach']:
            print(f"   🎯 Reach: {m['reach']:,}")
        if m['profile_views']:
            print(f"   👤 Profile Views: {m['profile_views']}")
            
        # YouTube specifics
        if m['subscribers_gained']:
            print(f"   📈 Subs Gained (lifetime): +{m['subscribers_gained']:,}")
        if m['subscribers_lost']:
            print(f"   📉 Subs Lost (lifetime): -{m['subscribers_lost']:,}")
        if m['watch_time_minutes']:
            hours = m['watch_time_minutes'] // 60
            print(f"   ⏱️  Watch Time: {hours:,} hours")
        if m['avg_view_duration_secs']:
            mins = m['avg_view_duration_secs'] // 60
            secs = m['avg_view_duration_secs'] % 60
            print(f"   ⏳ Avg Duration: {mins}:{secs:02d}")
            
        # TikTok CTAs
        if m['bio_link_clicks']:
            print(f"   🔗 Bio Link Clicks: {m['bio_link_clicks']}")
        if m['email_clicks']:
            print(f"   📧 Email Clicks: {m['email_clicks']}")
        
        print()

    print("=" * 70)
    print("📈 TOTALS ACROSS ALL PLATFORMS")
    print("=" * 70)
    print(f"   👥 Total Followers: {total_followers:,}")
    print(f"   💪 Total Engagement: {total_engagement:,}")
    print()


def ensure_table_exists(cursor):
    """Create the analytics table if it doesn't exist"""
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ayrshare_daily_analytics (
            id SERIAL PRIMARY KEY,
            date DATE NOT NULL DEFAULT CURRENT_DATE,
            platform TEXT NOT NULL,
            
            -- Audience
            followers INTEGER,
            following INTEGER,
            subscribers_gained INTEGER,
            subscribers_lost INTEGER,
            
            -- Daily Changes (calculated)
            followers_change INTEGER,
            likes_change INTEGER,
            views_change INTEGER,
            
            -- Engagement
            likes INTEGER,
            comments INTEGER,
            shares INTEGER,
            reposts INTEGER,
            quotes INTEGER,
            replies INTEGER,
            reactions INTEGER,
            dislikes INTEGER,
            
            -- Views & Reach
            views INTEGER,
            reach INTEGER,
            impressions INTEGER,
            profile_views INTEGER,
            
            -- Video
            video_count INTEGER,
            video_views INTEGER,
            watch_time_minutes INTEGER,
            avg_view_duration_secs INTEGER,
            avg_view_percentage DECIMAL(5,2),
            playlist_adds INTEGER,
            playlist_removes INTEGER,
            
            -- CTA Clicks
            bio_link_clicks INTEGER,
            email_clicks INTEGER,
            phone_clicks INTEGER,
            address_clicks INTEGER,
            app_download_clicks INTEGER,
            
            -- Content
            posts_count INTEGER,
            media_count INTEGER,
            tweet_count INTEGER,
            listed_count INTEGER,
            
            -- Account Status
            is_verified BOOLEAN,
            is_business BOOLEAN,
            is_monetized BOOLEAN,
            subscription_type TEXT,
            
            -- Demographics (JSONB)
            audience_ages JSONB,
            audience_countries JSONB,
            audience_genders JSONB,
            
            -- Raw Data
            raw_data JSONB,
            
            -- Metadata
            created_at TIMESTAMP DEFAULT NOW(),
            
            UNIQUE(date, platform)
        );
        
        CREATE INDEX IF NOT EXISTS idx_ayrshare_date ON ayrshare_daily_analytics(date);
        CREATE INDEX IF NOT EXISTS idx_ayrshare_platform ON ayrshare_daily_analytics(platform);
    ''')


def store_analytics(all_metrics):
    """Store analytics in database with daily change calculations"""
    if not DATABASE_URL:
        print("❌ DATABASE_URL not set")
        return False

    print("\n💾 Storing in ayrshare_daily_analytics...")

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Ensure table exists
        ensure_table_exists(cursor)
        conn.commit()

        stored_count = 0
        daily_changes = {}
        
        for m in all_metrics:
            platform = m['platform']
            
            # Get yesterday's data for change calculation
            yesterday = get_yesterday_metrics(cursor, platform)
            changes = calculate_daily_changes(m, yesterday)
            daily_changes[platform] = changes

            # UPSERT into database
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
                changes.get('followers_change'), changes.get('likes_change'), changes.get('views_change'),
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
            fc = changes.get('followers_change')
            fc_str = f" ({'+' if fc and fc >= 0 else ''}{fc} today)" if fc else ""
            print(f"   ✅ {platform}: {m['followers'] or 0:,} followers{fc_str}")

        conn.commit()
        cursor.close()
        conn.close()

        print(f"\n✅ Stored {stored_count} platforms to database")
        return daily_changes

    except Exception as e:
        print(f"❌ Database error: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    parser = argparse.ArgumentParser(description='Ayrshare Daily Analytics Tracker')
    parser.add_argument('--store', action='store_true', help='Store results in database')

    args = parser.parse_args()

    print("🚀 Ayrshare Daily Analytics Tracker")
    print("=" * 50)
    print(f"📅 Date: {date.today()}")

    # Fetch analytics
    data = fetch_social_analytics()

    if not data:
        print("❌ Failed to fetch analytics")
        return

    # Parse metrics for each platform
    all_metrics = []
    for platform in PLATFORMS:
        if platform in data and 'analytics' in data[platform]:
            analytics = data[platform]['analytics']
            metrics = parse_platform_metrics(platform, analytics)
            all_metrics.append(metrics)
        else:
            print(f"⚠️  No data for {platform}")

    # Store in database if requested
    daily_changes = None
    if args.store:
        daily_changes = store_analytics(all_metrics)

    # Display analytics
    display_analytics(all_metrics, daily_changes)

    print("✅ Done!")


if __name__ == "__main__":
    main()
