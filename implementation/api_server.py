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
- /webhook/rag-ingest - Ingest knowledge into RAG system (Segundo Cérebro)
- /webhook/rag-search - Semantic search in knowledge base
- /webhook/rag-categories - List knowledge categories

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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

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
    event: Optional[str] = "generic"
    data: Optional[Dict[str, Any]] = {}
    tenant_id: Optional[str] = None
    timestamp: Optional[str] = None
    action: Optional[str] = None  # Alias for event (compatibility)

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
# RAG MODELS (Segundo Cérebro)
# ============================================

class RAGIngestRequest(BaseModel):
    """Request to ingest knowledge into the RAG system"""
    category: str = Field(..., description="Category: schema, pattern, rule, decision, error_fix, workflow, api")
    title: str = Field(..., description="Title of the knowledge")
    content: str = Field(..., description="Full content/explanation")
    project_key: Optional[str] = Field(None, description="Project identifier: ai-factory, socialfy, etc")
    tags: List[str] = Field(default=[], description="Tags for filtering")
    source: Optional[str] = Field(None, description="Source of the knowledge")

class RAGIngestResponse(BaseModel):
    success: bool
    knowledge_id: Optional[str] = None
    message: str
    error: Optional[str] = None

class RAGSearchRequest(BaseModel):
    """Request to search knowledge in the RAG system"""
    query: str = Field(..., description="Search query")
    category: Optional[str] = Field(None, description="Filter by category")
    project_key: Optional[str] = Field(None, description="Filter by project")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    threshold: float = Field(0.7, description="Minimum similarity threshold (0-1)")
    limit: int = Field(5, description="Maximum results to return")

class RAGSearchResult(BaseModel):
    id: str
    category: str
    project_key: Optional[str]
    title: str
    content: str
    tags: List[str]
    similarity: float
    usage_count: int

class RAGSearchResponse(BaseModel):
    success: bool
    results: List[RAGSearchResult] = []
    count: int = 0
    error: Optional[str] = None

class RAGCategoriesResponse(BaseModel):
    success: bool
    categories: List[Dict[str, Any]] = []
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

@app.get("/debug/env")
async def debug_env():
    """Debug endpoint to check environment variables (masked)"""
    return {
        "SUPABASE_URL": SUPABASE_URL[:30] + "..." if SUPABASE_URL else None,
        "SUPABASE_KEY": "***" + SUPABASE_KEY[-10:] if SUPABASE_KEY else None,
        "OPENAI_API_KEY": "***" + OPENAI_API_KEY[-10:] if OPENAI_API_KEY else None,
        "openai_configured": bool(OPENAI_API_KEY),
        "supabase_configured": bool(SUPABASE_URL and SUPABASE_KEY),
    }


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
            "source": "dm_received"
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

    if not profile_response.get("success"):
        return {
            "success": False,
            "username": request.username,
            "error": profile_response.get("error")
        }

    # Calculate lead score based on profile
    score = 50  # Base score

    followers_count = profile_response.get("followers_count", 0)
    if followers_count > 10000:
        score += 10
    if followers_count > 100000:
        score += 10

    if not profile_response.get("is_private"):
        score += 5

    if profile_response.get("is_verified"):
        score += 10

    bio = profile_response.get("bio", "")
    if bio:
        # Keywords that indicate business
        business_keywords = ["ceo", "founder", "empreendedor", "empresa", "negócio", "digital", "marketing"]
        bio_lower = bio.lower()
        for keyword in business_keywords:
            if keyword in bio_lower:
                score += 5
                break

    return {
        "success": True,
        "username": request.username,
        "profile": {
            "full_name": profile_response.get("full_name"),
            "bio": profile_response.get("bio"),
            "followers": profile_response.get("followers_count"),
            "following": profile_response.get("following_count"),
            "posts": profile_response.get("posts_count"),
            "is_verified": profile_response.get("is_verified"),
            "is_private": profile_response.get("is_private"),
            "category": profile_response.get("category")
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
    # Use action as fallback for event (compatibility)
    event = payload.event or payload.action or "generic"
    data = payload.data or {}

    logger.info(f"Received n8n webhook: {event}")

    event_handlers = {
        "new_message": handle_new_message,
        "new_follower": handle_new_follower,
        "post_liked": handle_post_liked,
        "scheduled_dm": handle_scheduled_dm
    }

    handler = event_handlers.get(event)
    if handler:
        background_tasks.add_task(handler, data, payload.tenant_id)
        return {"status": "processing", "event": event}

    # For generic/test events, just acknowledge
    return {"status": "received", "event": event, "data": data}


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
            "order": "created_at.desc"  # Use created_at (score column may not exist)
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

        leads = response.json()

        # Filter by min_score in Python (in case column doesn't exist in DB)
        if min_score > 0 and leads:
            leads = [l for l in leads if l.get("score", 0) >= min_score]

        return {
            "success": True,
            "leads": leads,
            "count": len(leads)
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
# RAG ENDPOINTS (Segundo Cérebro)
# ============================================

def get_openai_embedding(text: str) -> Optional[List[float]]:
    """Get embedding from OpenAI API"""
    try:
        import openai

        if not OPENAI_API_KEY:
            logger.error("OPENAI_API_KEY not configured")
            return None

        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error getting OpenAI embedding: {e}")
        return None


@app.post("/webhook/rag-ingest", response_model=RAGIngestResponse)
async def rag_ingest(request: RAGIngestRequest):
    """
    Ingest knowledge into the RAG system (Segundo Cérebro).
    Generates embedding and saves to rag_knowledge table.

    Categories:
    - schema: Database structures, tables
    - pattern: Code patterns, architecture
    - rule: Business rules, conventions
    - decision: Technical decisions made
    - error_fix: Errors and their fixes
    - workflow: n8n workflows, automations
    - api: Endpoints, integrations
    """
    logger.info(f"RAG Ingest: {request.title} ({request.category})")

    try:
        # 1. Generate embedding
        embedding = get_openai_embedding(f"{request.title}\n\n{request.content}")

        if not embedding:
            return RAGIngestResponse(
                success=False,
                message="Failed to generate embedding",
                error="OpenAI API error or not configured"
            )

        # 2. Check if knowledge with same title exists
        check_response = requests.get(
            f"{db.base_url}/rag_knowledge",
            headers=db.headers,
            params={
                "title": f"eq.{request.title}",
                "select": "id"
            }
        )

        existing = check_response.json() if check_response.status_code == 200 else []

        # 3. Prepare data
        knowledge_data = {
            "category": request.category,
            "title": request.title,
            "content": request.content,
            "embedding": embedding,
            "project_key": request.project_key,
            "tags": request.tags,
            "source": request.source or f"api-{datetime.now().strftime('%Y-%m-%d')}",
            "updated_at": datetime.now().isoformat()
        }

        # 4. Upsert (update if exists, insert if not)
        if existing:
            # Update existing
            knowledge_id = existing[0]["id"]
            response = requests.patch(
                f"{db.base_url}/rag_knowledge",
                headers=db.headers,
                params={"id": f"eq.{knowledge_id}"},
                json=knowledge_data
            )
        else:
            # Insert new
            knowledge_data["created_at"] = datetime.now().isoformat()
            knowledge_data["created_by"] = "api-server"
            response = requests.post(
                f"{db.base_url}/rag_knowledge",
                headers=db.headers,
                json=knowledge_data
            )

        if response.status_code in [200, 201]:
            result = response.json()
            knowledge_id = result[0]["id"] if result else existing[0]["id"] if existing else None

            logger.info(f"RAG Ingest success: {knowledge_id}")
            return RAGIngestResponse(
                success=True,
                knowledge_id=knowledge_id,
                message=f"Knowledge {'updated' if existing else 'created'} successfully"
            )
        else:
            logger.error(f"RAG Ingest failed: {response.text}")
            return RAGIngestResponse(
                success=False,
                message="Failed to save knowledge",
                error=response.text
            )

    except Exception as e:
        logger.error(f"RAG Ingest error: {e}", exc_info=True)
        return RAGIngestResponse(
            success=False,
            message="Error processing request",
            error=str(e)
        )


@app.post("/webhook/rag-search", response_model=RAGSearchResponse)
async def rag_search(request: RAGSearchRequest):
    """
    Semantic search in the knowledge base.
    Uses pgvector for cosine similarity search.
    """
    logger.info(f"RAG Search: {request.query[:50]}...")

    try:
        # 1. Generate embedding for query
        query_embedding = get_openai_embedding(request.query)

        if not query_embedding:
            return RAGSearchResponse(
                success=False,
                error="Failed to generate query embedding"
            )

        # 2. Call search function via RPC
        # Using Supabase RPC to call the search_knowledge function
        rpc_payload = {
            "query_embedding": query_embedding,
            "match_threshold": request.threshold,
            "match_count": request.limit
        }

        if request.category:
            rpc_payload["filter_category"] = request.category
        if request.project_key:
            rpc_payload["filter_project"] = request.project_key
        if request.tags:
            rpc_payload["filter_tags"] = request.tags

        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/rpc/search_rag_knowledge",
            headers=db.headers,
            json=rpc_payload
        )

        if response.status_code == 200:
            results = response.json()

            # Convert to response model
            search_results = [
                RAGSearchResult(
                    id=str(r["id"]),
                    category=r["category"],
                    project_key=r.get("project_key"),
                    title=r["title"],
                    content=r["content"],
                    tags=r.get("tags", []),
                    similarity=r["similarity"],
                    usage_count=r.get("usage_count", 0)
                )
                for r in results
            ]

            # Increment usage count for returned results
            for r in results:
                try:
                    requests.post(
                        f"{SUPABASE_URL}/rest/v1/rpc/increment_rag_usage",
                        headers=db.headers,
                        json={"knowledge_id": r["id"]}
                    )
                except:
                    pass  # Non-critical, don't fail search

            logger.info(f"RAG Search found {len(search_results)} results")
            return RAGSearchResponse(
                success=True,
                results=search_results,
                count=len(search_results)
            )
        else:
            logger.error(f"RAG Search failed: {response.text}")
            return RAGSearchResponse(
                success=False,
                error=f"Search failed: {response.text}"
            )

    except Exception as e:
        logger.error(f"RAG Search error: {e}", exc_info=True)
        return RAGSearchResponse(
            success=False,
            error=str(e)
        )


@app.get("/webhook/rag-categories", response_model=RAGCategoriesResponse)
async def rag_categories():
    """
    List all knowledge categories with counts.
    """
    logger.info("RAG Categories: listing")

    try:
        # Query distinct categories with counts
        response = requests.get(
            f"{db.base_url}/rag_knowledge",
            headers=db.headers,
            params={"select": "category"}
        )

        if response.status_code == 200:
            data = response.json()

            # Count by category
            category_counts = {}
            for item in data:
                cat = item.get("category", "unknown")
                category_counts[cat] = category_counts.get(cat, 0) + 1

            categories = [
                {"category": cat, "count": count}
                for cat, count in sorted(category_counts.items(), key=lambda x: -x[1])
            ]

            return RAGCategoriesResponse(
                success=True,
                categories=categories
            )
        else:
            return RAGCategoriesResponse(
                success=False,
                error=response.text
            )

    except Exception as e:
        logger.error(f"RAG Categories error: {e}")
        return RAGCategoriesResponse(
            success=False,
            error=str(e)
        )


@app.get("/webhook/rag-stats")
async def rag_stats():
    """
    Get RAG system statistics.
    """
    try:
        # Count total knowledge
        response = requests.get(
            f"{db.base_url}/rag_knowledge",
            headers=db.headers,
            params={"select": "id,category,project_key,usage_count,created_at"}
        )

        if response.status_code == 200:
            data = response.json()

            # Calculate stats
            total = len(data)
            by_category = {}
            by_project = {}
            total_usage = 0

            for item in data:
                cat = item.get("category", "unknown")
                proj = item.get("project_key", "none")
                by_category[cat] = by_category.get(cat, 0) + 1
                by_project[proj] = by_project.get(proj, 0) + 1
                total_usage += item.get("usage_count", 0)

            return {
                "success": True,
                "total_knowledge": total,
                "total_usage": total_usage,
                "by_category": by_category,
                "by_project": by_project,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {"success": False, "error": response.text}

    except Exception as e:
        logger.error(f"RAG Stats error: {e}")
        return {"success": False, "error": str(e)}


# ============================================
# FASE 0 - INTEGRATION ENDPOINTS
# Endpoints para integracao AgenticOS <-> AI Factory
# ============================================

class LeadContextRequest(BaseModel):
    """Request para buscar contexto do lead."""
    channel: str = Field(..., description="Canal: instagram, whatsapp, email")
    identifier: str = Field(..., description="Identificador: @handle, +5511999, email")


class LeadContextResponse(BaseModel):
    """Response com contexto do lead para AI Agent."""
    found: bool
    lead_id: Optional[str] = None
    cargo: Optional[str] = None
    empresa: Optional[str] = None
    setor: Optional[str] = None
    porte: Optional[str] = None
    icp_score: Optional[int] = None
    icp_tier: Optional[str] = None
    ig_followers: Optional[int] = None
    ig_engagement: Optional[float] = None
    was_prospected: bool = False
    prospected_at: Optional[str] = None
    context_string: Optional[str] = None


class SyncLeadRequest(BaseModel):
    """Request para sincronizar lead entre sistemas."""
    lead_id: str
    source: str = Field(..., description="Sistema origem: agenticos, ai_factory")
    target: str = Field(..., description="Sistema destino: agenticos, ai_factory, ghl")


class UpdateGHLRequest(BaseModel):
    """Request para atualizar contato no GHL."""
    contact_id: str
    location_id: str
    custom_fields: Dict[str, Any]


@app.post("/api/get-lead-context", response_model=LeadContextResponse)
async def get_lead_context(request: LeadContextRequest):
    """
    Busca contexto do lead para o AI Factory.
    Chamado pelo 05-Execution antes de gerar resposta.

    Args:
        channel: Canal de origem (instagram, whatsapp, email)
        identifier: Identificador no canal (@handle, telefone, email)

    Returns:
        Contexto do lead com dados enriquecidos para hiperpersonalizacao
    """
    try:
        # Importar skill
        from skills.get_lead_by_channel import get_lead_by_channel, get_lead_context_for_ai

        # Buscar contexto formatado
        result = await get_lead_context_for_ai(
            channel=request.channel,
            identifier=request.identifier
        )

        if not result.get("success"):
            return LeadContextResponse(found=False)

        data = result.get("data", {})

        if not data.get("found"):
            return LeadContextResponse(found=False)

        lead = data.get("lead_data", {})

        return LeadContextResponse(
            found=True,
            lead_id=lead.get("id"),
            cargo=lead.get("cargo"),
            empresa=lead.get("empresa"),
            setor=lead.get("setor"),
            porte=lead.get("porte"),
            icp_score=lead.get("icp_score"),
            icp_tier=lead.get("icp_tier"),
            ig_followers=lead.get("ig_followers"),
            ig_engagement=lead.get("ig_engagement"),
            was_prospected=data.get("was_prospected", False),
            prospected_at=data.get("prospected_at"),
            context_string=data.get("context_string")
        )

    except Exception as e:
        logger.error(f"Get lead context error: {e}")
        return LeadContextResponse(found=False)


@app.post("/api/sync-lead")
async def sync_lead_endpoint(request: SyncLeadRequest):
    """
    Sincroniza lead entre sistemas.

    Args:
        lead_id: ID do lead
        source: Sistema origem (agenticos, ai_factory)
        target: Sistema destino (agenticos, ai_factory, ghl)

    Returns:
        Status da sincronizacao
    """
    try:
        from skills.sync_lead import sync_lead

        result = await sync_lead(
            lead_id=request.lead_id,
            source=request.source,
            target=request.target
        )

        return result

    except Exception as e:
        logger.error(f"Sync lead error: {e}")
        return {"success": False, "error": str(e)}


@app.post("/api/update-ghl-contact")
async def update_ghl_contact_endpoint(request: UpdateGHLRequest):
    """
    Atualiza custom fields de contato no GHL.

    Args:
        contact_id: ID do contato no GHL
        location_id: ID da location
        custom_fields: Dict com field_key -> value

    Returns:
        Status da atualizacao
    """
    try:
        from skills.update_ghl_contact import update_ghl_contact

        result = await update_ghl_contact(
            contact_id=request.contact_id,
            location_id=request.location_id,
            custom_fields=request.custom_fields
        )

        return result

    except Exception as e:
        logger.error(f"Update GHL contact error: {e}")
        return {"success": False, "error": str(e)}


@app.post("/api/ensure-ghl-fields/{location_id}")
async def ensure_ghl_fields_endpoint(location_id: str):
    """
    Garante que custom fields necessarios existem no GHL.

    Args:
        location_id: ID da location no GHL

    Returns:
        Lista de campos existentes, criados e falhos
    """
    try:
        from skills.update_ghl_contact import ensure_custom_fields_exist

        result = await ensure_custom_fields_exist(location_id=location_id)

        return result

    except Exception as e:
        logger.error(f"Ensure GHL fields error: {e}")
        return {"success": False, "error": str(e)}


@app.get("/api/skills")
async def list_skills():
    """
    Lista todos os skills disponiveis.

    Returns:
        Lista de skills com nome e descricao
    """
    try:
        from skills import SkillRegistry

        skills = SkillRegistry.list_all()

        return {
            "success": True,
            "skills": skills,
            "total": len(skills)
        }

    except Exception as e:
        logger.error(f"List skills error: {e}")
        return {"success": False, "error": str(e)}


@app.get("/api/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        Status do servidor e conexoes
    """
    health = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "fase-0",
        "connections": {}
    }

    # Check Supabase
    try:
        from supabase_integration import SupabaseClient
        sb = SupabaseClient()
        health["connections"]["supabase"] = "connected"
    except Exception as e:
        health["connections"]["supabase"] = f"error: {str(e)}"

    # Check GHL
    ghl_key = os.getenv("GHL_API_KEY") or os.getenv("GHL_ACCESS_TOKEN")
    health["connections"]["ghl"] = "configured" if ghl_key else "not configured"

    return health


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
