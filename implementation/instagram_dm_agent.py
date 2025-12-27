"""
Instagram DM Agent - Automated Outreach System
===============================================
Sends personalized DMs to leads using Playwright browser automation.
Stores all data in Supabase for tracking and analytics.

Usage:
    python instagram_dm_agent.py                    # Run with default settings
    python instagram_dm_agent.py --login-only       # Just login and save session
    python instagram_dm_agent.py --headless         # Run without browser window
    python instagram_dm_agent.py --limit 50         # Send max 50 DMs this run
    python instagram_dm_agent.py --template 2       # Use message template 2

Framework: ii (Information + Implementation)
"""

import os
import sys
import json
import random
import asyncio
import logging
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict

from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from dotenv import load_dotenv
import requests

# Load environment
load_dotenv()

# ============================================
# CONFIGURATION
# ============================================

# Paths
BASE_DIR = Path(__file__).parent.parent
SESSIONS_DIR = BASE_DIR / "sessions"
LOGS_DIR = BASE_DIR / "logs"
SESSIONS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Instagram
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD")
SESSION_PATH = SESSIONS_DIR / "instagram_session.json"

# Rate Limits
MAX_DMS_PER_HOUR = int(os.getenv("INSTAGRAM_DM_PER_HOUR", 10))
MAX_DMS_PER_DAY = int(os.getenv("INSTAGRAM_DM_PER_DAY", 200))
MIN_DELAY = int(os.getenv("INSTAGRAM_DM_DELAY_MIN", 30))
MAX_DELAY = int(os.getenv("INSTAGRAM_DM_DELAY_MAX", 60))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / f"instagram_dm_{date.today()}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("InstagramDMAgent")


# ============================================
# DATA CLASSES
# ============================================

@dataclass
class Lead:
    id: int
    username: str
    full_name: Optional[str] = None
    bio: Optional[str] = None
    source: Optional[str] = None

    @property
    def first_name(self) -> str:
        if self.full_name:
            return self.full_name.split()[0]
        return self.username.replace("_", " ").title().split()[0]


@dataclass
class DMResult:
    lead_id: int
    username: str
    success: bool
    message_sent: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


# ============================================
# MESSAGE TEMPLATES
# ============================================

MESSAGE_TEMPLATES = {
    1: """Hey {first_name}! 👋

Noticed you're into {interest}. Really cool stuff!

We built an AI system that automates Instagram outreach - sends 200+ personalized DMs daily on autopilot.

Would love to show you how it works. Interested?""",

    2: """{first_name}, quick question...

Do you spend hours manually DMing prospects on Instagram?

We automated this entire process. Now we send personalized messages while focusing on what matters.

Want me to show you how?""",

    3: """Hey {first_name}! 👋

Saw your profile and thought you'd appreciate this...

We're helping businesses automate their Instagram outreach with AI. Personalized DMs at scale, without the manual work.

30 sec to check it out?""",
}


# ============================================
# SUPABASE CLIENT (REST API)
# ============================================

class SupabaseDB:
    """Supabase database operations using REST API"""

    def __init__(self):
        self.base_url = f"{SUPABASE_URL}/rest/v1"
        self.headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        self.run_id: Optional[int] = None

    def _request(self, method: str, endpoint: str, params: dict = None, data: dict = None):
        """Make request to Supabase REST API"""
        url = f"{self.base_url}/{endpoint}"
        response = requests.request(
            method=method,
            url=url,
            headers=self.headers,
            params=params,
            json=data,
            timeout=30
        )
        response.raise_for_status()
        return response.json() if response.text else []

    def start_run(self, account: str) -> int:
        """Start a new agent run and return run ID"""
        result = self._request("POST", "agentic_instagram_dm_runs", data={
            'account_used': account,
            'status': 'running'
        })
        self.run_id = result[0]['id'] if result else None
        logger.info(f"Started run #{self.run_id}")
        return self.run_id

    def end_run(self, dms_sent: int, dms_failed: int, dms_skipped: int, status: str = 'completed', error_log: str = None):
        """End the current run"""
        if not self.run_id:
            return

        self._request("PATCH", "agentic_instagram_dm_runs",
            params={"id": f"eq.{self.run_id}"},
            data={
                'ended_at': datetime.now().isoformat(),
                'dms_sent': dms_sent,
                'dms_failed': dms_failed,
                'dms_skipped': dms_skipped,
                'status': status,
                'error_log': error_log
            }
        )
        logger.info(f"Ended run #{self.run_id} - Sent: {dms_sent}, Failed: {dms_failed}, Skipped: {dms_skipped}")

    def get_leads_to_contact(self, limit: int = 200) -> List[Lead]:
        """Get leads that haven't been contacted yet"""
        # Get all leads
        leads_data = self._request("GET", "agentic_instagram_leads", params={"select": "*"})

        # Get already contacted usernames
        contacted_data = self._request("GET", "agentic_instagram_dm_sent", params={"select": "username"})
        contacted_usernames = {r['username'] for r in contacted_data}

        # Filter and convert to Lead objects
        leads = []
        for lead_data in leads_data:
            if lead_data['username'] not in contacted_usernames:
                leads.append(Lead(
                    id=lead_data['id'],
                    username=lead_data['username'],
                    full_name=lead_data.get('full_name'),
                    bio=lead_data.get('bio'),
                    source=lead_data.get('source')
                ))

            if len(leads) >= limit:
                break

        logger.info(f"Found {len(leads)} leads to contact (limit: {limit})")
        return leads

    def record_dm_sent(self, result: DMResult, template: str, account: str):
        """Record a sent DM"""
        self._request("POST", "agentic_instagram_dm_sent", data={
            'lead_id': result.lead_id,
            'username': result.username,
            'message_template': template,
            'message_sent': result.message_sent or '',
            'status': 'sent' if result.success else 'failed',
            'error_message': result.error,
            'account_used': account
        })

    def get_dms_sent_today(self, account: str) -> int:
        """Get count of DMs sent today"""
        today = date.today().isoformat()
        headers = self.headers.copy()
        headers["Prefer"] = "count=exact"

        response = requests.get(
            f"{self.base_url}/agentic_instagram_dm_sent",
            headers=headers,
            params={
                "select": "*",
                "account_used": f"eq.{account}",
                "sent_at": f"gte.{today}T00:00:00"
            },
            timeout=30
        )
        # Get count from content-range header
        content_range = response.headers.get("content-range", "*/0")
        return int(content_range.split("/")[1]) if "/" in content_range else 0

    def get_dms_sent_last_hour(self, account: str) -> int:
        """Get count of DMs sent in last hour"""
        one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
        headers = self.headers.copy()
        headers["Prefer"] = "count=exact"

        response = requests.get(
            f"{self.base_url}/agentic_instagram_dm_sent",
            headers=headers,
            params={
                "select": "*",
                "account_used": f"eq.{account}",
                "sent_at": f"gte.{one_hour_ago}"
            },
            timeout=30
        )
        content_range = response.headers.get("content-range", "*/0")
        return int(content_range.split("/")[1]) if "/" in content_range else 0

    def update_daily_stats(self, account: str, dms_sent: int, dms_failed: int):
        """Update daily stats"""
        today = date.today().isoformat()

        # Try to get existing record
        existing = self._request("GET", "agentic_instagram_daily_stats", params={
            "select": "*",
            "date": f"eq.{today}",
            "account_used": f"eq.{account}"
        })

        if existing:
            # Update existing
            self._request("PATCH", "agentic_instagram_daily_stats",
                params={"id": f"eq.{existing[0]['id']}"},
                data={
                    'dms_sent': existing[0]['dms_sent'] + dms_sent,
                    'dms_failed': existing[0]['dms_failed'] + dms_failed
                }
            )
        else:
            # Create new
            self._request("POST", "agentic_instagram_daily_stats", data={
                'date': today,
                'account_used': account,
                'dms_sent': dms_sent,
                'dms_failed': dms_failed
            })


# ============================================
# INSTAGRAM DM AGENT
# ============================================

class InstagramDMAgent:
    """
    Autonomous Instagram DM Agent using Playwright
    """

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.db = SupabaseDB()
        self.results: List[DMResult] = []
        self.dms_sent = 0
        self.dms_failed = 0
        self.dms_skipped = 0

    async def start(self):
        """Initialize browser and load session"""
        logger.info("🚀 Starting Instagram DM Agent...")
        logger.info(f"   Account: @{INSTAGRAM_USERNAME}")
        logger.info(f"   Headless: {self.headless}")

        playwright = await async_playwright().start()

        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage'
            ]
        )

        # Browser context options
        context_options = {
            'viewport': {'width': 1280, 'height': 800},
            'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        # Try to load existing session
        if SESSION_PATH.exists():
            logger.info("📂 Loading existing session...")
            try:
                storage_state = json.loads(SESSION_PATH.read_text())
                context_options['storage_state'] = storage_state
            except Exception as e:
                logger.warning(f"Could not load session: {e}")

        self.context = await self.browser.new_context(**context_options)
        self.page = await self.context.new_page()

        # Set extra headers
        await self.page.set_extra_http_headers({
            'Accept-Language': 'en-US,en;q=0.9',
        })

    async def save_session(self):
        """Save browser session for reuse"""
        try:
            storage = await self.context.storage_state()
            SESSION_PATH.write_text(json.dumps(storage, indent=2))
            logger.info(f"💾 Session saved to {SESSION_PATH}")
        except Exception as e:
            logger.error(f"Failed to save session: {e}")

    async def take_screenshot(self, name: str) -> Path:
        """Take screenshot for debugging"""
        screenshot_path = LOGS_DIR / f"screenshot_{name}_{datetime.now().strftime('%H%M%S')}.png"
        await self.page.screenshot(path=str(screenshot_path))
        logger.info(f"📸 Screenshot: {screenshot_path}")
        return screenshot_path

    async def login(self) -> bool:
        """Login to Instagram and save session"""
        logger.info("🔐 Logging into Instagram...")

        try:
            await self.page.goto('https://www.instagram.com/', wait_until='networkidle')
            await asyncio.sleep(3)

            # Check if already logged in
            current_url = self.page.url
            if 'login' not in current_url and 'accounts' not in current_url:
                # Verify we're actually logged in by checking for profile icon
                try:
                    await self.page.wait_for_selector('svg[aria-label="Home"]', timeout=5000)
                    logger.info("✅ Already logged in!")
                    await self.save_session()
                    return True
                except:
                    pass

            # Navigate to login page
            await self.page.goto('https://www.instagram.com/accounts/login/', wait_until='networkidle')
            await asyncio.sleep(2)

            # Accept cookies if prompted
            try:
                cookie_btn = await self.page.wait_for_selector('button:has-text("Allow")', timeout=3000)
                if cookie_btn:
                    await cookie_btn.click()
                    await asyncio.sleep(1)
            except:
                pass

            # Fill login form
            logger.info("   Entering credentials...")
            await self.page.fill('input[name="username"]', INSTAGRAM_USERNAME)
            await asyncio.sleep(0.5)
            await self.page.fill('input[name="password"]', INSTAGRAM_PASSWORD)
            await asyncio.sleep(0.5)

            # Click login button
            await self.page.click('button[type="submit"]')
            await asyncio.sleep(5)

            # Check for 2FA
            if 'challenge' in self.page.url or 'two_factor' in self.page.url:
                logger.warning("⚠️  2FA required! Please complete verification in the browser...")
                logger.warning("   Waiting up to 2 minutes for manual 2FA...")

                try:
                    # Wait for redirect away from challenge page
                    await self.page.wait_for_url(
                        lambda url: 'challenge' not in url and 'two_factor' not in url,
                        timeout=120000
                    )
                    logger.info("✅ 2FA completed!")
                except:
                    logger.error("❌ 2FA timeout - please try again")
                    return False

            # Handle "Save Login Info" popup
            await asyncio.sleep(2)
            try:
                save_btn = await self.page.wait_for_selector('button:has-text("Save info")', timeout=5000)
                if save_btn:
                    await save_btn.click()
                    await asyncio.sleep(1)
            except:
                pass

            # Handle "Turn on Notifications" popup
            try:
                not_now = await self.page.wait_for_selector('button:has-text("Not Now")', timeout=5000)
                if not_now:
                    await not_now.click()
                    await asyncio.sleep(1)
            except:
                pass

            # Verify login success
            try:
                await self.page.wait_for_selector('svg[aria-label="Home"]', timeout=10000)
                logger.info("✅ Login successful!")
                await self.save_session()
                return True
            except:
                await self.take_screenshot("login_failed")
                logger.error("❌ Login verification failed")
                return False

        except Exception as e:
            logger.error(f"❌ Login error: {e}")
            await self.take_screenshot("login_error")
            return False

    def check_rate_limits(self) -> tuple[bool, str]:
        """Check if we can send more DMs"""
        dms_today = self.db.get_dms_sent_today(INSTAGRAM_USERNAME)
        dms_hour = self.db.get_dms_sent_last_hour(INSTAGRAM_USERNAME)

        if dms_today >= MAX_DMS_PER_DAY:
            return False, f"Daily limit reached ({dms_today}/{MAX_DMS_PER_DAY})"

        if dms_hour >= MAX_DMS_PER_HOUR:
            return False, f"Hourly limit reached ({dms_hour}/{MAX_DMS_PER_HOUR})"

        remaining_today = MAX_DMS_PER_DAY - dms_today
        remaining_hour = MAX_DMS_PER_HOUR - dms_hour

        logger.info(f"📊 Rate limits: {dms_hour}/{MAX_DMS_PER_HOUR}/hour, {dms_today}/{MAX_DMS_PER_DAY}/day")
        return True, f"OK - {min(remaining_today, remaining_hour)} DMs available"

    def get_personalized_message(self, lead: Lead, template_id: int = 1) -> str:
        """Generate personalized message for lead"""
        template = MESSAGE_TEMPLATES.get(template_id, MESSAGE_TEMPLATES[1])

        # Extract interest from bio or use default
        interest = "growth and business"
        if lead.bio:
            bio_lower = lead.bio.lower()
            if "marketing" in bio_lower:
                interest = "marketing"
            elif "startup" in bio_lower or "founder" in bio_lower:
                interest = "startups"
            elif "sales" in bio_lower:
                interest = "sales"
            elif "entrepreneur" in bio_lower:
                interest = "entrepreneurship"
            elif "coach" in bio_lower:
                interest = "coaching"

        return template.format(
            first_name=lead.first_name,
            interest=interest
        )

    async def send_dm(self, lead: Lead, message: str) -> DMResult:
        """Send DM to a single lead"""
        logger.info(f"💬 Sending DM to @{lead.username}...")

        try:
            # Go to Instagram Direct
            await self.page.goto('https://www.instagram.com/direct/inbox/', wait_until='networkidle')
            await asyncio.sleep(2)

            # Click "New Message" / "Send message" button
            try:
                new_msg_btn = await self.page.wait_for_selector(
                    'svg[aria-label="New message"]',
                    timeout=5000
                )
                await new_msg_btn.click()
                await asyncio.sleep(1)
            except:
                # Try alternative selector
                try:
                    compose_btn = await self.page.wait_for_selector(
                        'div[role="button"]:has-text("Send message")',
                        timeout=3000
                    )
                    await compose_btn.click()
                    await asyncio.sleep(1)
                except:
                    pass

            # Search for user
            await asyncio.sleep(1)
            search_input = await self.page.wait_for_selector(
                'input[placeholder="Search..."]',
                timeout=5000
            )
            await search_input.fill(lead.username)
            await asyncio.sleep(2)

            # Click on the user from search results
            try:
                user_result = await self.page.wait_for_selector(
                    f'div[role="button"] span:text-is("{lead.username}")',
                    timeout=5000
                )
                await user_result.click()
                await asyncio.sleep(1)
            except:
                # Try clicking any result with the username
                try:
                    await self.page.click(f'text="{lead.username}"')
                    await asyncio.sleep(1)
                except:
                    logger.warning(f"   Could not find @{lead.username} in search")
                    return DMResult(
                        lead_id=lead.id,
                        username=lead.username,
                        success=False,
                        error="User not found in search"
                    )

            # Click "Chat" or "Next" button
            try:
                next_btn = await self.page.wait_for_selector(
                    'div[role="button"]:has-text("Chat"), div[role="button"]:has-text("Next")',
                    timeout=3000
                )
                await next_btn.click()
                await asyncio.sleep(1)
            except:
                pass

            # Find message input and type
            await asyncio.sleep(1)
            message_input = await self.page.wait_for_selector(
                'textarea[placeholder="Message..."], div[role="textbox"]',
                timeout=5000
            )

            # Type message character by character for more human-like behavior
            await message_input.click()
            await asyncio.sleep(0.3)

            # Use fill for speed, but could use type() for more human-like
            await message_input.fill(message)
            await asyncio.sleep(0.5)

            # Send message
            await self.page.keyboard.press('Enter')
            await asyncio.sleep(2)

            logger.info(f"   ✅ DM sent to @{lead.username}")

            return DMResult(
                lead_id=lead.id,
                username=lead.username,
                success=True,
                message_sent=message
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"   ❌ Failed to send DM to @{lead.username}: {error_msg}")
            await self.take_screenshot(f"dm_error_{lead.username}")

            return DMResult(
                lead_id=lead.id,
                username=lead.username,
                success=False,
                error=error_msg
            )

    async def run_campaign(self, limit: int = 200, template_id: int = 1):
        """Run DM campaign"""
        logger.info("="*60)
        logger.info("🎯 STARTING DM CAMPAIGN")
        logger.info("="*60)

        # Check rate limits
        can_send, reason = self.check_rate_limits()
        if not can_send:
            logger.warning(f"⚠️  {reason}")
            return

        # Start run tracking
        self.db.start_run(INSTAGRAM_USERNAME)

        # Get leads
        leads = self.db.get_leads_to_contact(limit=limit)
        if not leads:
            logger.warning("⚠️  No leads to contact!")
            self.db.end_run(0, 0, 0, status='no_leads')
            return

        logger.info(f"📋 Processing {len(leads)} leads...")

        try:
            for i, lead in enumerate(leads):
                # Check rate limits before each DM
                can_send, reason = self.check_rate_limits()
                if not can_send:
                    logger.warning(f"⚠️  Stopping: {reason}")
                    break

                # Generate and send message
                message = self.get_personalized_message(lead, template_id)
                result = await self.send_dm(lead, message)

                # Record result
                self.results.append(result)
                self.db.record_dm_sent(result, f"template_{template_id}", INSTAGRAM_USERNAME)

                if result.success:
                    self.dms_sent += 1
                else:
                    self.dms_failed += 1

                # Progress update
                logger.info(f"📊 Progress: {i+1}/{len(leads)} | Sent: {self.dms_sent} | Failed: {self.dms_failed}")

                # Random delay between DMs
                if i < len(leads) - 1:
                    delay = random.randint(MIN_DELAY, MAX_DELAY)
                    logger.info(f"⏳ Waiting {delay} seconds...")
                    await asyncio.sleep(delay)

        except KeyboardInterrupt:
            logger.warning("⚠️  Campaign interrupted by user")
        except Exception as e:
            logger.error(f"❌ Campaign error: {e}")
            self.db.end_run(self.dms_sent, self.dms_failed, self.dms_skipped, status='error', error_log=str(e))
            raise

        # End run
        self.db.end_run(self.dms_sent, self.dms_failed, self.dms_skipped)
        self.db.update_daily_stats(INSTAGRAM_USERNAME, self.dms_sent, self.dms_failed)

        # Final summary
        logger.info("="*60)
        logger.info("📊 CAMPAIGN COMPLETE")
        logger.info(f"   DMs Sent: {self.dms_sent}")
        logger.info(f"   DMs Failed: {self.dms_failed}")
        logger.info(f"   Success Rate: {(self.dms_sent/(self.dms_sent+self.dms_failed)*100):.1f}%" if (self.dms_sent+self.dms_failed) > 0 else "N/A")
        logger.info("="*60)

        # Save session
        await self.save_session()

    async def stop(self):
        """Cleanup and close browser"""
        logger.info("🛑 Stopping agent...")
        if self.context:
            await self.save_session()
            await self.context.close()
        if self.browser:
            await self.browser.close()
        logger.info("👋 Agent stopped")


# ============================================
# MAIN
# ============================================

async def main():
    import argparse

    parser = argparse.ArgumentParser(description='Instagram DM Agent')
    parser.add_argument('--headless', action='store_true', help='Run without browser window')
    parser.add_argument('--login-only', action='store_true', help='Only login and save session')
    parser.add_argument('--limit', type=int, default=200, help='Max DMs to send this run')
    parser.add_argument('--template', type=int, default=1, choices=[1, 2, 3], help='Message template (1-3)')
    args = parser.parse_args()

    # Validate configuration
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("❌ Supabase not configured! Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
        return

    if not INSTAGRAM_USERNAME or not INSTAGRAM_PASSWORD:
        logger.error("❌ Instagram not configured! Set INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD")
        return

    agent = InstagramDMAgent(headless=args.headless)

    try:
        await agent.start()

        # Login
        if not await agent.login():
            logger.error("❌ Login failed, aborting")
            return

        if args.login_only:
            logger.info("✅ Login complete. Session saved.")
        else:
            # Run campaign
            await agent.run_campaign(limit=args.limit, template_id=args.template)

    except KeyboardInterrupt:
        logger.warning("⚠️  Interrupted by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        raise
    finally:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
