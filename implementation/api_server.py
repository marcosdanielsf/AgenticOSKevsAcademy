#!/usr/bin/env python3
"""
Socialfy API Server
===================
FastAPI server that bridges n8n workflows with Python agents.
This is the central hub for all automation operations.

Endpoints:
- /webhook/inbound-dm - Process inbound DM (scrape, qualify, save to Supabase)
- /webhook/scrape-profile - Scrape Instagram profile via API with scoring
- /webhook/scrape-post-likers - Scrape post likers and save to Supabase
- /webhook/scrape-likers - Scrape post likers (legacy)
- /webhook/scrape-commenters - Scrape post commenters
- /webhook/send-dm - Send DM to user
- /webhook/check-inbox - Check for new messages
- /webhook/classify-lead - Classify a lead with AI
- /webhook/enrich-lead - Enrich lead with profile data

Usage:
    python api_server.py
    # Server runs on http://localhost:8000
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
from dotenv import load_dotenv
import requests

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()

# ============================================
# CONFIGURATION
# ============================================

BASE_DIR = Path(__file__).parent.parent
SESSIONS_DIR = BASE_DIR / "sessions"
LOGS_DIR = BASE_DIR / "logs"
SESSIONS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "socialfy-secret-2024")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / "api_server.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SocialfyAPI")


# ============================================
# PYDANTIC MODELS
# ============================================

class ScrapeProfileRequest(BaseModel):
    username: str
    tenant_id: Optional[str] = None
    save_to_db: bool = True

class ScrapeProfileResponse(BaseModel):
    success: bool
    username: str
    full_name: Optional[str] = None
    bio: Optional[str] = None
    followers_count: int = 0
    following_count: int = 0
    posts_count: int = 0
    is_verified: bool = False
    is_private: bool = False
    category: Optional[str] = None
    error: Optional[str] = None

class ScrapeLikersRequest(BaseModel):
    post_url: str
    limit: int = 200
    tenant_id: Optional[str] = None
    save_to_db: bool = True

class ScrapeCommentersRequest(BaseModel):
    post_url: str
    limit: int = 100
    tenant_id: Optional[str] = None
    save_to_db: bool = True

class SendDMRequest(BaseModel):
    username: str
    message: str
    tenant_id: Optional[str] = None
    persona_id: Optional[str] = None
    log_to_db: bool = True

class SendDMResponse(BaseModel):
    success: bool
    username: str
    message_sent: Optional[str] = None
    error: Optional[str] = None

class ClassifyLeadRequest(BaseModel):
    username: str
    message: str
    tenant_id: str
    persona_id: Optional[str] = None

class ClassifyLeadResponse(BaseModel):
    success: bool
    username: str
    classification: str  # LEAD_HOT, LEAD_WARM, LEAD_COLD, PESSOAL, SPAM
    score: int  # 0-100
    reasoning: str
    suggested_response: Optional[str] = None

class EnrichLeadRequest(BaseModel):
    username: str
    tenant_id: Optional[str] = None

class CheckInboxRequest(BaseModel):
    tenant_id: Optional[str] = None
    account_username: Optional[str] = None
    limit: int = 20

class WebhookPayload(BaseModel):
    event: str
    data: Dict[str, Any]
    tenant_id: Optional[str] = None
    timestamp: Optional[str] = None

class InboundDMRequest(BaseModel):
    username: str
    message: str
    tenant_id: Optional[str] = None

class InboundDMResponse(BaseModel):
    success: bool
    username: str
    lead_id: Optional[str] = None
    score: int = 0
    classification: str = "LEAD_COLD"
    suggested_response: Optional[str] = None
    profile: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class ScrapePostLikersRequest(BaseModel):
    post_url: str
    max_likers: int = 50
    tenant_id: Optional[str] = None
    save_to_db: bool = True

class ScrapePostLikersResponse(BaseModel):
    success: bool
    total_scraped: int = 0
    leads_saved: int = 0
    post_url: str
    error: Optional[str] = None


# ============================================
# SUPABASE CLIENT
# ============================================

class SupabaseClient:
    """Simple Supabase REST API client"""

    def __init__(self):
        self.base_url = f"{SUPABASE_URL}/rest/v1"
        self.headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

    def get_tenant(self, tenant_id: str) -> Optional[Dict]:
        """Get tenant by ID or slug"""
        try:
            # Try by UUID first
            response = requests.get(
                f"{self.base_url}/tenants",
                headers=self.headers,
                params={"id": f"eq.{tenant_id}"}
            )
            if response.status_code == 200:
                data = response.json()
                if data:
                    return data[0]

            # Fallback to slug
            response = requests.get(
                f"{self.base_url}/tenants",
                headers=self.headers,
                params={"slug": f"eq.{tenant_id}"}
            )
            if response.status_code == 200:
                data = response.json()
                return data[0] if data else None
            return None
        except Exception as e:
            logger.error(f"Error fetching tenant: {e}")
            return None

    def resolve_tenant_id(self, tenant_id: str) -> Optional[str]:
        """Resolve tenant_id (slug or UUID) to UUID"""
        tenant = self.get_tenant(tenant_id)
        return tenant.get("id") if tenant else None

    def get_active_persona(self, tenant_id: str) -> Optional[Dict]:
        """Get active persona for tenant"""
        try:
            response = requests.get(
                f"{self.base_url}/tenant_personas",
                headers=self.headers,
                params={
                    "tenant_id": f"eq.{tenant_id}",
                    "is_active": "eq.true"
                }
            )
            data = response.json()
            return data[0] if data else None
        except Exception as e:
            logger.error(f"Error fetching persona: {e}")
            return None

    def is_known_contact(self, tenant_id: str, username: str) -> bool:
        """Check if username is a known contact"""
        try:
            # Resolve tenant_id to UUID if needed
            resolved_id = self.resolve_tenant_id(tenant_id)
            if not resolved_id:
                logger.warning(f"Could not resolve tenant_id: {tenant_id}")
                return False

            response = requests.get(
                f"{self.base_url}/tenant_known_contacts",
                headers=self.headers,
                params={
                    "tenant_id": f"eq.{resolved_id}",
                    "username": f"eq.{username}"
                }
            )
            # Only count as known if response is successful and has data
            if response.status_code != 200:
                logger.error(f"Error checking known contact: {response.text}")
                return False
            data = response.json()
            return isinstance(data, list) and len(data) > 0
        except Exception as e:
            logger.error(f"Error checking known contact: {e}")
            return False

    def save_lead(self, lead_data: Dict) -> bool:
        """Save or update lead in database"""
        try:
            # Check if exists
            check = requests.get(
                f"{self.base_url}/agentic_instagram_leads",
                headers=self.headers,
                params={"username": f"eq.{lead_data['username']}"}
            )

            if check.json():
                # Update existing
                response = requests.patch(
                    f"{self.base_url}/agentic_instagram_leads",
                    headers=self.headers,
                    params={"username": f"eq.{lead_data['username']}"},
                    json=lead_data
                )
            else:
                # Insert new
                response = requests.post(
                    f"{self.base_url}/agentic_instagram_leads",
                    headers=self.headers,
                    json=lead_data
                )

            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Error saving lead: {e}")
            return False

    def save_classified_lead(self, data: Dict) -> bool:
        """Save classified lead"""
        try:
            response = requests.post(
                f"{self.base_url}/classified_leads",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Error saving classified lead: {e}")
            return False

    def log_dm_sent(self, data: Dict) -> bool:
        """Log sent DM"""
        try:
            response = requests.post(
                f"{self.base_url}/agentic_instagram_dm_sent",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Error logging DM: {e}")
            return False


# ============================================
# BROWSER MANAGER (Singleton)
# ============================================

class BrowserManager:
    """Manages browser instance for scraping operations"""

    _instance = None
    _lock = asyncio.Lock()

    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.is_initialized = False

    @classmethod
    async def get_instance(cls):
        async with cls._lock:
            if cls._instance is None:
                cls._instance = BrowserManager()
            return cls._instance

    async def initialize(self, headless: bool = True):
        """Initialize browser if not already done"""
        if self.is_initialized:
            return

        try:
            from playwright.async_api import async_playwright

            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=headless,
                args=['--disable-blink-features=AutomationControlled']
            )

            # Load session if exists
            context_options = {
                'viewport': {'width': 1280, 'height': 800},
                'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }

            session_path = SESSIONS_DIR / "instagram_session.json"
            if session_path.exists():
                try:
                    storage_state = json.loads(session_path.read_text())
                    context_options['storage_state'] = storage_state
                    logger.info("Loaded existing session")
                except Exception as e:
                    logger.warning(f"Could not load session: {e}")

            self.context = await self.browser.new_context(**context_options)
            self.page = await self.context.new_page()
            self.is_initialized = True
            logger.info("Browser initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            raise

    async def close(self):
        """Close browser and cleanup"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self.is_initialized = False
        logger.info("Browser closed")


# ============================================
# AGENT IMPORTS (Lazy loading)
# ============================================

def get_profile_scraper(page):
    """Get profile scraper instance"""
    try:
        from instagram_profile_scraper_gemini import InstagramProfileScraperGemini
        return InstagramProfileScraperGemini(page)
    except ImportError:
        from instagram_profile_scraper import InstagramProfileScraper
        return InstagramProfileScraper(page)


# ============================================
# FASTAPI APP
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle"""
    logger.info("Starting Socialfy API Server...")

    # Initialize browser on startup
    try:
        browser_manager = await BrowserManager.get_instance()
        await browser_manager.initialize(headless=True)
    except Exception as e:
        logger.warning(f"Browser not initialized on startup: {e}")

    yield

    # Cleanup on shutdown
    try:
        browser_manager = await BrowserManager.get_instance()
        await browser_manager.close()
    except:
        pass

    logger.info("Socialfy API Server stopped")


app = FastAPI(
    title="Socialfy API",
    description="API Server for Instagram Lead Generation & DM Automation",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database client
db = SupabaseClient()


# ============================================
# AUTH DEPENDENCY
# ============================================

async def verify_api_key(x_api_key: str = Header(None)):
    """Verify API key for protected endpoints"""
    if x_api_key != API_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True


# ============================================
# HEALTH CHECK
# ============================================

@app.get("/health")
async def health_check():
    """Health check endpoint with full system status for dashboard"""
    browser_manager = await BrowserManager.get_instance()

    # Agent definitions for all 6 squads (23 agents)
    agents_data = {
        # Outbound Squad (5 agents)
        "LeadDiscovery": {"squad": "outbound", "state": "idle", "tasks_completed": 0, "tasks_failed": 0, "success_rate": 1.0},
        "ProfileAnalyzer": {"squad": "outbound", "state": "idle", "tasks_completed": 0, "tasks_failed": 0, "success_rate": 1.0},
        "LeadQualifier": {"squad": "outbound", "state": "idle", "tasks_completed": 0, "tasks_failed": 0, "success_rate": 1.0},
        "MessageComposer": {"squad": "outbound", "state": "idle", "tasks_completed": 0, "tasks_failed": 0, "success_rate": 1.0},
        "OutreachExecutor": {"squad": "outbound", "state": "idle", "tasks_completed": 0, "tasks_failed": 0, "success_rate": 1.0},
        # Inbound Squad (3 agents)
        "InboxMonitor": {"squad": "inbound", "state": "idle", "tasks_completed": 0, "tasks_failed": 0, "success_rate": 1.0},
        "LeadClassifier": {"squad": "inbound", "state": "idle", "tasks_completed": 0, "tasks_failed": 0, "success_rate": 1.0},
        "AutoResponder": {"squad": "inbound", "state": "idle", "tasks_completed": 0, "tasks_failed": 0, "success_rate": 1.0},
        # Infrastructure Squad (3 agents)
        "AccountManager": {"squad": "infrastructure", "state": "idle", "tasks_completed": 0, "tasks_failed": 0, "success_rate": 1.0},
        "Analytics": {"squad": "infrastructure", "state": "idle", "tasks_completed": 0, "tasks_failed": 0, "success_rate": 1.0},
        "ErrorHandler": {"squad": "infrastructure", "state": "idle", "tasks_completed": 0, "tasks_failed": 0, "success_rate": 1.0},
        # Security Squad (4 agents)
        "RateLimitGuard": {"squad": "security", "state": "idle", "tasks_completed": 0, "tasks_failed": 0, "success_rate": 1.0},
        "SessionSecurity": {"squad": "security", "state": "idle", "tasks_completed": 0, "tasks_failed": 0, "success_rate": 1.0},
        "AntiDetection": {"squad": "security", "state": "idle", "tasks_completed": 0, "tasks_failed": 0, "success_rate": 1.0},
        "Compliance": {"squad": "security", "state": "idle", "tasks_completed": 0, "tasks_failed": 0, "success_rate": 1.0},
        # Performance Squad (4 agents)
        "CacheManager": {"squad": "performance", "state": "idle", "tasks_completed": 0, "tasks_failed": 0, "success_rate": 1.0},
        "BatchProcessor": {"squad": "performance", "state": "idle", "tasks_completed": 0, "tasks_failed": 0, "success_rate": 1.0},
        "QueueManager": {"squad": "performance", "state": "idle", "tasks_completed": 0, "tasks_failed": 0, "success_rate": 1.0},
        "LoadBalancer": {"squad": "performance", "state": "idle", "tasks_completed": 0, "tasks_failed": 0, "success_rate": 1.0},
        # Quality Squad (4 agents)
        "DataValidator": {"squad": "quality", "state": "idle", "tasks_completed": 0, "tasks_failed": 0, "success_rate": 1.0},
        "MessageQuality": {"squad": "quality", "state": "idle", "tasks_completed": 0, "tasks_failed": 0, "success_rate": 1.0},
        "Deduplication": {"squad": "quality", "state": "idle", "tasks_completed": 0, "tasks_failed": 0, "success_rate": 1.0},
        "AuditLogger": {"squad": "quality", "state": "idle", "tasks_completed": 0, "tasks_failed": 0, "success_rate": 1.0},
    }

    return {
        "status": "healthy" if browser_manager.is_initialized else "degraded",
        "timestamp": datetime.now().isoformat(),
        "browser_ready": browser_manager.is_initialized,
        "version": "1.0.0",
        "system_metrics": {
            "total_tasks_routed": 0,
            "active_agents": 23,
            "workflows_completed": 0,
            "workflows_failed": 0
        },
        "total_tasks_processed": 0,
        "total_errors": 0,
        "overall_success_rate": 1.0,
        "agents": agents_data,
        "active_workflows": 0
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "Socialfy API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# ============================================
# SCRAPING ENDPOINTS
# ============================================

@app.post("/webhook/scrape-profile")
async def scrape_profile(request: ScrapeProfileRequest):
    """
    Scrape Instagram profile data via API.
    Called by n8n when a new lead needs enrichment.

    Returns full profile data with score and classification.
    """
    logger.info(f"Scraping profile: @{request.username}")

    try:
        # Use the Instagram API scraper for more data
        from instagram_api_scraper import InstagramAPIScraper
        from supabase_integration import SocialfyAgentIntegration

        scraper = InstagramAPIScraper()
        profile = scraper.get_profile(request.username)

        if not profile.get("success"):
            return {
                "success": False,
                "username": request.username,
                "error": profile.get("error", "Failed to scrape profile")
            }

        # Calculate lead score
        score_data = scraper.calculate_lead_score(profile)

        # Save to database if requested
        if request.save_to_db:
            integration = SocialfyAgentIntegration()
            integration.save_discovered_lead(
                name=profile.get("full_name") or request.username,
                email=profile.get("email") or f"{request.username}@instagram.com",
                source="api_scrape",
                profile_data={
                    "username": request.username,
                    "bio": profile.get("bio"),
                    "followers_count": profile.get("followers_count"),
                    "following_count": profile.get("following_count"),
                    "is_business": profile.get("is_business"),
                    "is_verified": profile.get("is_verified"),
                    "score": score_data.get("score", 0),
                    "status": "warm" if score_data.get("score", 0) >= 40 else "cold",
                    "phone": profile.get("phone") or profile.get("phone_hint"),
                    "company": profile.get("category")
                }
            )

        # Return comprehensive profile data with score
        return {
            "success": True,
            "username": profile.get("username"),
            "full_name": profile.get("full_name"),
            "bio": profile.get("bio"),
            "followers_count": profile.get("followers_count", 0),
            "following_count": profile.get("following_count", 0),
            "posts_count": profile.get("posts_count", 0),
            "is_verified": profile.get("is_verified", False),
            "is_private": profile.get("is_private", False),
            "is_business": profile.get("is_business", False),
            "category": profile.get("category"),
            "profile_pic_url": profile.get("profile_pic_url_hd") or profile.get("profile_pic_url"),
            "external_url": profile.get("external_url"),
            "email": profile.get("email"),
            "email_hint": profile.get("email_hint"),
            "phone": profile.get("phone"),
            "phone_hint": profile.get("phone_hint"),
            "whatsapp_linked": profile.get("whatsapp_linked"),
            "user_id": profile.get("user_id"),
            "fb_id": profile.get("fb_id"),
            "score": score_data.get("score", 0),
            "classification": score_data.get("classification", "LEAD_COLD"),
            "signals": score_data.get("signals", []),
            "scraped_at": profile.get("scraped_at"),
            "method": profile.get("method")
        }

    except Exception as e:
        logger.error(f"Error scraping profile: {e}", exc_info=True)
        return {
            "success": False,
            "username": request.username,
            "error": str(e)
        }


@app.post("/webhook/scrape-likers")
async def scrape_likers(request: ScrapeLikersRequest, background_tasks: BackgroundTasks):
    """
    Scrape users who liked a post.
    Runs in background and saves to database.
    """
    logger.info(f"Scraping likers for: {request.post_url}")

    async def scrape_task():
        try:
            from instagram_post_likers_scraper import PostLikersScraper

            scraper = PostLikersScraper(headless=True)
            await scraper.start()

            if await scraper.verify_login():
                likers = await scraper.scrape_likers(request.post_url, limit=request.limit)

                if request.save_to_db:
                    await scraper.save_to_supabase(likers)

                logger.info(f"Scraped {len(likers)} likers")

            await scraper.stop()

        except Exception as e:
            logger.error(f"Error in likers scrape task: {e}")

    background_tasks.add_task(scrape_task)

    return {
        "status": "started",
        "message": f"Scraping likers from {request.post_url} (limit: {request.limit})",
        "check_results": "/api/leads?source=post_like"
    }


@app.post("/webhook/scrape-post-likers", response_model=ScrapePostLikersResponse)
async def scrape_post_likers(request: ScrapePostLikersRequest, background_tasks: BackgroundTasks):
    """
    Scrape users who liked a post (n8n endpoint).
    Scrapes likers, saves to Supabase, and returns summary.

    This endpoint returns immediately and processes in background.
    For synchronous processing, increase timeout.
    """
    logger.info(f"Scraping post likers: {request.post_url} (max: {request.max_likers})")

    response = ScrapePostLikersResponse(
        success=False,
        post_url=request.post_url
    )

    async def scrape_task():
        """Background task to scrape likers"""
        try:
            from instagram_post_likers_scraper import PostLikersScraper
            from supabase_integration import SocialfyAgentIntegration

            scraper = PostLikersScraper(headless=True)
            integration = SocialfyAgentIntegration()

            await scraper.start()

            if await scraper.verify_login():
                # Scrape likers
                likers = await scraper.scrape_likers(request.post_url, limit=request.max_likers)

                logger.info(f"Scraped {len(likers)} likers from post")

                # Save to Supabase if requested
                if request.save_to_db:
                    saved_count = 0
                    for liker in likers:
                        try:
                            # Save each liker as a lead
                            integration.save_discovered_lead(
                                name=liker.get("full_name") or liker.get("username"),
                                email=f"{liker.get('username')}@instagram.com",  # Placeholder
                                source="post_like",
                                profile_data={
                                    "username": liker.get("username"),
                                    "bio": liker.get("bio"),
                                    "followers_count": liker.get("followers_count", 0),
                                    "is_verified": liker.get("is_verified", False),
                                    "is_private": liker.get("is_private", False),
                                    "source_url": request.post_url
                                }
                            )
                            saved_count += 1
                        except Exception as e:
                            logger.warning(f"Failed to save liker {liker.get('username')}: {e}")

                    logger.info(f"Saved {saved_count}/{len(likers)} likers to Supabase")

            await scraper.stop()

        except Exception as e:
            logger.error(f"Error in post likers scrape task: {e}", exc_info=True)

    # Start background task
    background_tasks.add_task(scrape_task)

    # Return immediate response
    return ScrapePostLikersResponse(
        success=True,
        total_scraped=0,  # Will be updated in background
        leads_saved=0,    # Will be updated in background
        post_url=request.post_url
    )


@app.post("/webhook/scrape-commenters")
async def scrape_commenters(request: ScrapeCommentersRequest, background_tasks: BackgroundTasks):
    """
    Scrape users who commented on a post.
    Runs in background and saves to database.
    """
    logger.info(f"Scraping commenters for: {request.post_url}")

    async def scrape_task():
        try:
            from instagram_post_commenters_scraper import PostCommentersScraper

            scraper = PostCommentersScraper(headless=True)
            await scraper.start()

            if await scraper.verify_login():
                commenters = await scraper.scrape_commenters(request.post_url, limit=request.limit)

                if request.save_to_db:
                    await scraper.save_to_supabase(commenters)

                logger.info(f"Scraped {len(commenters)} commenters")

            await scraper.stop()

        except Exception as e:
            logger.error(f"Error in commenters scrape task: {e}")

    background_tasks.add_task(scrape_task)

    return {
        "status": "started",
        "message": f"Scraping commenters from {request.post_url} (limit: {request.limit})",
        "check_results": "/api/leads?source=post_comment"
    }


# ============================================
# DM ENDPOINTS
# ============================================

@app.post("/webhook/inbound-dm", response_model=InboundDMResponse)
async def webhook_inbound_dm(request: InboundDMRequest):
    """
    Process an inbound DM from n8n.
    Scrapes the user's profile, qualifies the lead, and saves to Supabase.

    Flow:
    1. Scrape profile using Instagram API
    2. Calculate lead score
    3. Save to Supabase (crm_leads + socialfy_leads)
    4. Generate AI classification and suggested response
    5. Return lead data with score and suggested response
    """
    logger.info(f"Processing inbound DM from @{request.username}")

    result = InboundDMResponse(
        success=False,
        username=request.username
    )

    try:
        # Import the API scraper and Supabase integration
        from instagram_api_scraper import InstagramAPIScraper
        from supabase_integration import SocialfyAgentIntegration

        # Initialize scraper and integration
        scraper = InstagramAPIScraper()
        integration = SocialfyAgentIntegration()

        # 1. Scrape the user's profile
        logger.info(f"Scraping profile for @{request.username}")
        profile = scraper.get_profile(request.username)

        if not profile.get("success"):
            result.error = f"Failed to scrape profile: {profile.get('error', 'Unknown error')}"
            return result

        # 2. Calculate lead score
        score_data = scraper.calculate_lead_score(profile)
        score = score_data.get("score", 0)
        classification = score_data.get("classification", "LEAD_COLD")

        logger.info(f"Lead score for @{request.username}: {score}/100 ({classification})")

        # 3. Save to Supabase
        # Save to crm_leads
        lead_record = integration.save_discovered_lead(
            name=profile.get("full_name") or request.username,
            email=profile.get("email") or f"{request.username}@instagram.com",  # Placeholder email
            source="instagram_dm",
            profile_data={
                "username": request.username,
                "bio": profile.get("bio"),
                "followers_count": profile.get("followers_count"),
                "following_count": profile.get("following_count"),
                "is_business": profile.get("is_business"),
                "is_verified": profile.get("is_verified"),
                "score": score,
                "status": "warm" if score >= 40 else "cold",
                "phone": profile.get("phone") or profile.get("phone_hint"),
                "company": profile.get("category")
            }
        )

        # Extract lead_id from response
        lead_id = None
        if isinstance(lead_record, list) and lead_record:
            lead_id = lead_record[0].get("id")
        elif isinstance(lead_record, dict):
            lead_id = lead_record.get("id")

        # Save the received message
        if lead_id:
            integration.save_received_message(
                lead_id=lead_id,
                message=request.message
            )

        # 4. Generate AI classification and suggested response using Gemini
        suggested_response = None
        try:
            import google.generativeai as genai

            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-2.5-flash")

                prompt = f"""Você é um assistente de vendas no Instagram.

Recebeu uma DM de @{request.username}:
"{request.message}"

Perfil do lead:
- Nome: {profile.get('full_name', 'N/A')}
- Bio: {profile.get('bio', 'N/A')}
- Seguidores: {profile.get('followers_count', 0):,}
- Business: {'Sim' if profile.get('is_business') else 'Não'}
- Score: {score}/100 ({classification})

Gere uma resposta natural e amigável que:
1. Agradeça pela mensagem
2. Demonstre interesse genuíno
3. Faça uma pergunta relevante para qualificar o lead
4. Seja concisa (máx 2-3 frases)

Responda APENAS com o texto da mensagem, sem explicações."""

                response = model.generate_content(prompt)
                suggested_response = response.text.strip()

                logger.info(f"Generated suggested response: {suggested_response[:50]}...")

        except Exception as e:
            logger.warning(f"Failed to generate suggested response: {e}")

        # 5. Return result
        result.success = True
        result.lead_id = lead_id
        result.score = score
        result.classification = classification
        result.suggested_response = suggested_response
        result.profile = {
            "username": profile.get("username"),
            "full_name": profile.get("full_name"),
            "bio": profile.get("bio"),
            "followers_count": profile.get("followers_count"),
            "following_count": profile.get("following_count"),
            "posts_count": profile.get("posts_count"),
            "is_business": profile.get("is_business"),
            "is_verified": profile.get("is_verified"),
            "category": profile.get("category")
        }

        logger.info(f"✅ Inbound DM processed successfully for @{request.username}")
        return result

    except Exception as e:
        logger.error(f"Error processing inbound DM: {e}", exc_info=True)
        result.error = str(e)
        return result


@app.post("/webhook/send-dm", response_model=SendDMResponse)
async def send_dm(request: SendDMRequest):
    """
    Send a DM to a user.
    Called by n8n for automated outreach.
    """
    logger.info(f"Sending DM to @{request.username}")

    try:
        browser_manager = await BrowserManager.get_instance()
        if not browser_manager.is_initialized:
            await browser_manager.initialize(headless=True)

        page = browser_manager.page

        # Navigate to DM
        dm_url = f"https://www.instagram.com/direct/t/{request.username}/"
        await page.goto(dm_url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(2)

        # Try to find and use message input
        message_input = await page.wait_for_selector(
            'textarea[placeholder*="Message"], div[contenteditable="true"]',
            timeout=10000
        )

        if message_input:
            await message_input.fill(request.message)
            await asyncio.sleep(0.5)

            # Send
            send_btn = await page.query_selector('button:has-text("Send")')
            if send_btn:
                await send_btn.click()
                await asyncio.sleep(1)

                # Log to database
                if request.log_to_db:
                    db.log_dm_sent({
                        "username": request.username,
                        "message": request.message,
                        "tenant_id": request.tenant_id,
                        "persona_id": request.persona_id,
                        "sent_at": datetime.now().isoformat()
                    })

                return SendDMResponse(
                    success=True,
                    username=request.username,
                    message_sent=request.message
                )

        return SendDMResponse(
            success=False,
            username=request.username,
            error="Could not find message input"
        )

    except Exception as e:
        logger.error(f"Error sending DM: {e}")
        return SendDMResponse(
            success=False,
            username=request.username,
            error=str(e)
        )


# ============================================
# CLASSIFICATION ENDPOINTS
# ============================================

@app.post("/webhook/classify-lead", response_model=ClassifyLeadResponse)
async def classify_lead(request: ClassifyLeadRequest):
    """
    Classify a lead using AI.
    Called by n8n when processing inbox messages.
    """
    logger.info(f"Classifying lead: @{request.username}")

    try:
        # Get persona for context
        persona = None
        if request.persona_id:
            persona = db.get_active_persona(request.tenant_id)

        # Check if known contact
        is_known = db.is_known_contact(request.tenant_id, request.username)
        if is_known:
            return ClassifyLeadResponse(
                success=True,
                username=request.username,
                classification="PESSOAL",
                score=0,
                reasoning="Known contact in whitelist"
            )

        # Use Gemini for classification
        import google.generativeai as genai

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not configured")

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")

        persona_context = ""
        if persona:
            persona_context = f"""
Contexto do ICP:
- Dores: {persona.get('icp_pain_points', '')}
- Perfil ideal: {persona.get('icp_profile', '')}
"""

        prompt = f"""Você é um classificador de leads para marketing no Instagram.

Analise esta mensagem recebida de @{request.username}:
"{request.message}"

{persona_context}

Classifique esta mensagem em UMA das categorias:
- LEAD_HOT: Interesse claro em comprar/contratar (ex: "quanto custa?", "quero saber mais")
- LEAD_WARM: Interesse moderado, engajamento positivo (ex: "legal seu conteúdo", "me conta mais")
- LEAD_COLD: Primeira interação, sem interesse claro ainda
- PESSOAL: Mensagem pessoal, não é lead (amigo, família, parceiro)
- SPAM: Propaganda, bot, mensagem irrelevante

Também dê uma pontuação de 0 a 100 para o potencial deste lead.

Responda APENAS em JSON:
{{
    "classification": "LEAD_HOT|LEAD_WARM|LEAD_COLD|PESSOAL|SPAM",
    "score": 0-100,
    "reasoning": "explicação curta",
    "suggested_response": "sugestão de resposta ou null"
}}
"""

        response = model.generate_content(prompt)
        response_text = response.text.strip()

        # Parse JSON
        if response_text.startswith("```"):
            import re
            response_text = re.sub(r'^```json?\n?', '', response_text)
            response_text = re.sub(r'\n?```$', '', response_text)

        result = json.loads(response_text)

        # Save to database
        db.save_classified_lead({
            "tenant_id": request.tenant_id,
            "persona_id": request.persona_id,
            "username": request.username,
            "original_message": request.message,
            "classification": result["classification"],
            "score": result["score"],
            "ai_reasoning": result["reasoning"],
            "suggested_response": result.get("suggested_response"),
            "classified_at": datetime.now().isoformat()
        })

        return ClassifyLeadResponse(
            success=True,
            username=request.username,
            classification=result["classification"],
            score=result["score"],
            reasoning=result["reasoning"],
            suggested_response=result.get("suggested_response")
        )

    except Exception as e:
        logger.error(f"Error classifying lead: {e}")
        return ClassifyLeadResponse(
            success=False,
            username=request.username,
            classification="LEAD_COLD",
            score=50,
            reasoning=f"Classification failed: {str(e)}"
        )


@app.post("/webhook/enrich-lead")
async def enrich_lead(request: EnrichLeadRequest):
    """
    Enrich a lead with profile data.
    Combines scraping + classification.
    """
    logger.info(f"Enriching lead: @{request.username}")

    # First, scrape profile
    profile_response = await scrape_profile(ScrapeProfileRequest(
        username=request.username,
        tenant_id=request.tenant_id,
        save_to_db=True
    ))

    if not profile_response.success:
        return {
            "success": False,
            "username": request.username,
            "error": profile_response.error
        }

    # Calculate lead score based on profile
    score = 50  # Base score

    if profile_response.followers_count > 10000:
        score += 10
    if profile_response.followers_count > 100000:
        score += 10

    if not profile_response.is_private:
        score += 5

    if profile_response.is_verified:
        score += 10

    if profile_response.bio:
        # Keywords that indicate business
        business_keywords = ["ceo", "founder", "empreendedor", "empresa", "negócio", "digital", "marketing"]
        bio_lower = profile_response.bio.lower()
        for keyword in business_keywords:
            if keyword in bio_lower:
                score += 5
                break

    return {
        "success": True,
        "username": request.username,
        "profile": {
            "full_name": profile_response.full_name,
            "bio": profile_response.bio,
            "followers": profile_response.followers_count,
            "following": profile_response.following_count,
            "posts": profile_response.posts_count,
            "is_verified": profile_response.is_verified,
            "is_private": profile_response.is_private,
            "category": profile_response.category
        },
        "lead_score": min(score, 100),
        "enriched_at": datetime.now().isoformat()
    }


# ============================================
# INBOX ENDPOINTS
# ============================================

@app.post("/webhook/check-inbox")
async def check_inbox(request: CheckInboxRequest):
    """
    Check Instagram inbox for new messages.
    Returns unread conversations.
    """
    logger.info("Checking inbox for new messages")

    try:
        browser_manager = await BrowserManager.get_instance()
        if not browser_manager.is_initialized:
            await browser_manager.initialize(headless=True)

        page = browser_manager.page

        # Navigate to inbox
        await page.goto('https://www.instagram.com/direct/inbox/', wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(3)

        # Extract conversations
        conversations = await page.evaluate('''() => {
            const convs = [];
            const items = document.querySelectorAll('div[role="listitem"], div[class*="conversation"]');

            items.forEach((item, index) => {
                if (index >= 20) return;  // Limit

                const usernameEl = item.querySelector('span[dir="auto"]');
                const previewEl = item.querySelectorAll('span[dir="auto"]')[1];
                const unreadEl = item.querySelector('div[class*="unread"], span[class*="badge"]');

                if (usernameEl) {
                    convs.push({
                        username: usernameEl.textContent?.trim(),
                        preview: previewEl?.textContent?.trim() || '',
                        has_unread: !!unreadEl
                    });
                }
            });

            return convs;
        }''')

        # Filter only unread
        unread = [c for c in conversations if c.get('has_unread')]

        return {
            "success": True,
            "total_conversations": len(conversations),
            "unread_count": len(unread),
            "unread_conversations": unread,
            "checked_at": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error checking inbox: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# ============================================
# WEBHOOK FROM EXTERNAL SERVICES
# ============================================

@app.post("/webhook/n8n")
async def n8n_webhook(payload: WebhookPayload, background_tasks: BackgroundTasks):
    """
    Generic webhook endpoint for n8n.
    Routes to appropriate handler based on event type.
    """
    logger.info(f"Received n8n webhook: {payload.event}")

    event_handlers = {
        "new_message": handle_new_message,
        "new_follower": handle_new_follower,
        "post_liked": handle_post_liked,
        "scheduled_dm": handle_scheduled_dm
    }

    handler = event_handlers.get(payload.event)
    if handler:
        background_tasks.add_task(handler, payload.data, payload.tenant_id)
        return {"status": "processing", "event": payload.event}

    return {"status": "unknown_event", "event": payload.event}


async def handle_new_message(data: Dict, tenant_id: str):
    """Handle new message event from n8n"""
    username = data.get("from_username")
    message = data.get("message_text")

    if username and message:
        # Classify and potentially auto-respond
        result = await classify_lead(ClassifyLeadRequest(
            username=username,
            message=message,
            tenant_id=tenant_id
        ))

        logger.info(f"Classified @{username}: {result.classification} (score: {result.score})")


async def handle_new_follower(data: Dict, tenant_id: str):
    """Handle new follower event"""
    username = data.get("username")
    if username:
        # Enrich the new follower
        await enrich_lead(EnrichLeadRequest(
            username=username,
            tenant_id=tenant_id
        ))


async def handle_post_liked(data: Dict, tenant_id: str):
    """Handle post like event"""
    username = data.get("username")
    post_url = data.get("post_url")

    if username:
        db.save_lead({
            "username": username,
            "source": "post_like",
            "source_url": post_url,
            "tenant_id": tenant_id
        })


async def handle_scheduled_dm(data: Dict, tenant_id: str):
    """Handle scheduled DM send"""
    username = data.get("username")
    message = data.get("message")

    if username and message:
        await send_dm(SendDMRequest(
            username=username,
            message=message,
            tenant_id=tenant_id,
            log_to_db=True
        ))


# ============================================
# LEADS API
# ============================================

@app.get("/api/leads")
async def get_leads(
    source: Optional[str] = None,
    tenant_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """Get leads from database with filters"""
    try:
        params = {
            "limit": limit,
            "offset": offset,
            "order": "created_at.desc"
        }

        if source:
            params["source"] = f"eq.{source}"
        if tenant_id:
            params["tenant_id"] = f"eq.{tenant_id}"

        response = requests.get(
            f"{db.base_url}/agentic_instagram_leads",
            headers=db.headers,
            params=params
        )

        return {
            "success": True,
            "leads": response.json(),
            "count": len(response.json())
        }

    except Exception as e:
        logger.error(f"Error fetching leads: {e}")
        return {"success": False, "error": str(e)}


@app.get("/api/classified-leads")
async def get_classified_leads(
    classification: Optional[str] = None,
    tenant_id: Optional[str] = None,
    min_score: int = 0,
    limit: int = 50
):
    """Get classified leads with filters"""
    try:
        params = {
            "limit": limit,
            "order": "score.desc",
            "score": f"gte.{min_score}"
        }

        if classification:
            params["classification"] = f"eq.{classification}"
        if tenant_id:
            params["tenant_id"] = f"eq.{tenant_id}"

        response = requests.get(
            f"{db.base_url}/classified_leads",
            headers=db.headers,
            params=params
        )

        return {
            "success": True,
            "leads": response.json(),
            "count": len(response.json())
        }

    except Exception as e:
        logger.error(f"Error fetching classified leads: {e}")
        return {"success": False, "error": str(e)}


# ============================================
# STATS ENDPOINTS
# ============================================

@app.get("/api/stats")
async def get_stats(tenant_id: Optional[str] = None):
    """Get overall statistics"""
    try:
        # Count leads by source
        leads_response = requests.get(
            f"{db.base_url}/agentic_instagram_leads",
            headers=db.headers,
            params={"select": "source"}
        )
        leads = leads_response.json()

        sources = {}
        for lead in leads:
            source = lead.get("source", "unknown")
            sources[source] = sources.get(source, 0) + 1

        # Count DMs sent today
        today = datetime.now().strftime("%Y-%m-%d")
        dms_response = requests.get(
            f"{db.base_url}/agentic_instagram_dm_sent",
            headers=db.headers,
            params={"sent_at": f"gte.{today}"}
        )

        return {
            "success": True,
            "total_leads": len(leads),
            "leads_by_source": sources,
            "dms_sent_today": len(dms_response.json()),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        return {"success": False, "error": str(e)}


# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Socialfy API Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind')
    parser.add_argument('--port', type=int, default=None, help='Port to bind')
    parser.add_argument('--reload', action='store_true', help='Enable auto-reload')
    args = parser.parse_args()

    # Use PORT from environment (Railway) or default to 8000
    port = args.port or int(os.getenv('PORT', 8000))

    logger.info(f"Starting Socialfy API on {args.host}:{port}")

    uvicorn.run(
        "api_server:app",
        host=args.host,
        port=port,
        reload=args.reload,
        log_level="info"
    )
