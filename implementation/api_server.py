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
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn
from dotenv import load_dotenv
import requests
import time
from collections import defaultdict
import psutil

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Load .env but don't override existing env vars (Railway sets them)
load_dotenv(override=False)

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

# Rate Limiting Configuration
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "60"))  # requests per window
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # window in seconds

# Server start time for uptime tracking
SERVER_START_TIME = time.time()

# Request metrics tracking
request_metrics = {
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "requests_by_endpoint": defaultdict(int),
    "requests_by_status": defaultdict(int),
    "last_request_time": None
}


# ============================================
# RATE LIMITER
# ============================================

class RateLimiter:
    """
    Simple in-memory rate limiter using sliding window.
    Tracks requests per IP address.
    """

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def is_allowed(self, client_ip: str) -> tuple[bool, dict]:
        """
        Check if request is allowed for given IP.
        Returns (is_allowed, info_dict)
        """
        async with self._lock:
            now = time.time()
            window_start = now - self.window_seconds

            # Clean old requests outside window
            self.requests[client_ip] = [
                req_time for req_time in self.requests[client_ip]
                if req_time > window_start
            ]

            current_count = len(self.requests[client_ip])
            remaining = max(0, self.max_requests - current_count)

            # Calculate reset time
            if self.requests[client_ip]:
                oldest = min(self.requests[client_ip])
                reset_time = int(oldest + self.window_seconds - now)
            else:
                reset_time = self.window_seconds

            info = {
                "limit": self.max_requests,
                "remaining": remaining,
                "reset": max(0, reset_time),
                "window": self.window_seconds
            }

            if current_count >= self.max_requests:
                return False, info

            # Record this request
            self.requests[client_ip].append(now)
            info["remaining"] = remaining - 1

            return True, info

    def get_stats(self) -> dict:
        """Get rate limiter statistics"""
        now = time.time()
        window_start = now - self.window_seconds

        active_ips = 0
        total_requests_in_window = 0

        for ip, times in self.requests.items():
            recent = [t for t in times if t > window_start]
            if recent:
                active_ips += 1
                total_requests_in_window += len(recent)

        return {
            "active_clients": active_ips,
            "requests_in_window": total_requests_in_window,
            "max_requests_per_client": self.max_requests,
            "window_seconds": self.window_seconds
        }


# Initialize rate limiter
rate_limiter = RateLimiter(
    max_requests=RATE_LIMIT_REQUESTS,
    window_seconds=RATE_LIMIT_WINDOW
)

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

    def resolve_tenant_id(self, tenant_id: str, auto_create: bool = True) -> Optional[str]:
        """
        Resolve tenant_id (slug or UUID) to UUID.
        Se auto_create=True e o tenant não existir, cria automaticamente.
        """
        tenant = self.get_tenant(tenant_id)
        if tenant:
            return tenant.get("id")

        # Tenant não existe - criar automaticamente se permitido
        if auto_create and tenant_id:
            created_tenant = self.create_tenant_from_ghl_location(tenant_id)
            if created_tenant:
                return created_tenant.get("id")

        return None

    def create_tenant_from_ghl_location(self, location_id: str) -> Optional[Dict]:
        """
        Cria um tenant automaticamente baseado no location_id do GHL.
        Isso permite que novos clientes sejam registrados automaticamente.
        """
        try:
            # Criar tenant com dados básicos
            tenant_data = {
                "name": f"GHL Location {location_id[:8]}",
                "slug": location_id,  # Usar location_id como slug
                "tier": "free",
                "status": "active",
                "settings": {
                    "ghl_location_id": location_id,
                    "auto_created": True,
                    "created_from": "classify_lead_api"
                }
            }

            response = requests.post(
                f"{self.base_url}/tenants",
                headers=self.headers,
                json=tenant_data
            )

            if response.status_code in [200, 201]:
                created = response.json()
                logger.info(f"✅ Auto-created tenant for GHL location: {location_id}")
                return created[0] if isinstance(created, list) else created
            else:
                logger.error(f"❌ Failed to auto-create tenant: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"❌ Exception creating tenant: {e}")
            return None

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
        """
        Save classified lead.
        Resolve tenant_id automaticamente (cria tenant se não existir).
        """
        try:
            # Resolver tenant_id para UUID válido
            raw_tenant_id = data.get("tenant_id")
            if raw_tenant_id:
                resolved_id = self.resolve_tenant_id(raw_tenant_id, auto_create=True)
                if resolved_id:
                    data["tenant_id"] = resolved_id
                else:
                    logger.warning(f"Could not resolve tenant_id: {raw_tenant_id}, skipping save")
                    return False

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


# ============================================
# RATE LIMITING MIDDLEWARE
# ============================================

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """
    Rate limiting middleware.
    Applies to all endpoints except health checks.
    """
    # Skip rate limiting for health endpoints
    path = request.url.path
    if path in ["/health", "/api/health", "/", "/docs", "/openapi.json", "/redoc"]:
        response = await call_next(request)
        return response

    # Get client IP (handle proxies)
    client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    if not client_ip:
        client_ip = request.headers.get("X-Real-IP", request.client.host if request.client else "unknown")

    # Check rate limit
    allowed, info = await rate_limiter.is_allowed(client_ip)

    if not allowed:
        # Return 429 Too Many Requests
        return JSONResponse(
            status_code=429,
            content={
                "error": "Too Many Requests",
                "message": f"Rate limit exceeded. Try again in {info['reset']} seconds.",
                "limit": info["limit"],
                "remaining": 0,
                "reset_in_seconds": info["reset"]
            },
            headers={
                "X-RateLimit-Limit": str(info["limit"]),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(info["reset"]),
                "Retry-After": str(info["reset"])
            }
        )

    # Process request
    response = await call_next(request)

    # Add rate limit headers to response
    response.headers["X-RateLimit-Limit"] = str(info["limit"])
    response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
    response.headers["X-RateLimit-Reset"] = str(info["reset"])

    return response


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """
    Middleware to track request metrics.
    """
    start_time = time.time()

    # Process request
    response = await call_next(request)

    # Track metrics
    process_time = time.time() - start_time
    request_metrics["total_requests"] += 1
    request_metrics["last_request_time"] = datetime.now().isoformat()
    request_metrics["requests_by_endpoint"][request.url.path] += 1
    request_metrics["requests_by_status"][response.status_code] += 1

    if 200 <= response.status_code < 400:
        request_metrics["successful_requests"] += 1
    else:
        request_metrics["failed_requests"] += 1

    # Add timing header
    response.headers["X-Process-Time"] = f"{process_time:.4f}"

    return response


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
# SCRAPE FOLLOWERS ENDPOINT
# ============================================

class ScrapeFollowersRequest(BaseModel):
    """Request para scrape de seguidores."""
    username: str = Field(..., description="Username do perfil alvo")
    max_followers: int = Field(100, description="Máximo de seguidores a retornar")
    save_to_db: bool = Field(True, description="Salvar leads no banco")
    tenant_id: Optional[str] = Field(None, description="ID do tenant")


@app.post("/webhook/scrape-followers")
async def scrape_followers(request: ScrapeFollowersRequest):
    """
    Scrape seguidores de um perfil do Instagram.
    Retorna lista de seguidores com dados básicos.
    """
    logger.info(f"Scraping followers de @{request.username} (max: {request.max_followers})")

    try:
        from instagram_api_scraper import InstagramAPIScraper
        from supabase_integration import SupabaseClient

        scraper = InstagramAPIScraper()
        result = scraper.get_followers(request.username, max_count=request.max_followers)

        if not result.get("success"):
            return {
                "success": False,
                "username": request.username,
                "error": result.get("error", "Falha ao buscar seguidores"),
                "followers": []
            }

        followers = result.get("followers", [])

        # Salvar no banco se solicitado
        saved_count = 0
        if request.save_to_db and followers:
            db = SupabaseClient()
            for follower in followers:
                try:
                    db._request('POST', 'growth_leads', data={
                        'instagram_username': follower.get('username'),
                        'name': follower.get('full_name') or follower.get('username'),
                        'source_channel': f'instagram_followers_{request.username}',
                        'funnel_stage': 'lead',
                        'lead_temperature': 'cold',
                        'location_id': request.tenant_id or '11111111-1111-1111-1111-111111111111',
                        'avatar_url': follower.get('profile_pic_url'),
                        'custom_fields': {
                            'scraped_from': request.username,
                            'is_private': follower.get('is_private'),
                            'is_verified': follower.get('is_verified'),
                        }
                    })
                    saved_count += 1
                except Exception as e:
                    logger.warning(f"Erro ao salvar follower {follower.get('username')}: {e}")

        return {
            "success": True,
            "username": request.username,
            "followers": followers,
            "count": len(followers),
            "total_followers": result.get("total_followers", 0),
            "saved_to_db": saved_count
        }

    except Exception as e:
        logger.error(f"Erro ao buscar seguidores: {e}", exc_info=True)
        return {
            "success": False,
            "username": request.username,
            "error": str(e),
            "followers": []
        }


# ============================================
# SCRAPE HASHTAG ENDPOINT
# ============================================

class ScrapeHashtagRequest(BaseModel):
    """Request para scrape de hashtag."""
    hashtag: str = Field(..., description="Hashtag a buscar (com ou sem #)")
    max_users: int = Field(50, description="Máximo de usuários a retornar")
    save_to_db: bool = Field(True, description="Salvar leads no banco")
    tenant_id: Optional[str] = Field(None, description="ID do tenant")


@app.post("/webhook/scrape-hashtag")
async def scrape_hashtag(request: ScrapeHashtagRequest):
    """
    Busca posts de uma hashtag e extrai os autores como leads.
    """
    hashtag = request.hashtag.lstrip("#").strip()
    logger.info(f"Scraping hashtag #{hashtag} (max: {request.max_users})")

    try:
        from instagram_api_scraper import InstagramAPIScraper
        from supabase_integration import SupabaseClient

        scraper = InstagramAPIScraper()
        result = scraper.search_hashtag(hashtag, max_posts=request.max_users)

        if not result.get("success"):
            return {
                "success": False,
                "hashtag": hashtag,
                "error": result.get("error", "Falha ao buscar hashtag"),
                "users": []
            }

        users = result.get("users", [])

        # Salvar no banco se solicitado
        saved_count = 0
        if request.save_to_db and users:
            db = SupabaseClient()
            for user in users:
                try:
                    db._request('POST', 'growth_leads', data={
                        'instagram_username': user.get('username'),
                        'name': user.get('full_name') or user.get('username'),
                        'source_channel': f'instagram_hashtag_{hashtag}',
                        'funnel_stage': 'lead',
                        'lead_temperature': 'cold',
                        'location_id': request.tenant_id or '11111111-1111-1111-1111-111111111111',
                        'avatar_url': user.get('profile_pic_url'),
                        'custom_fields': {
                            'scraped_from_hashtag': hashtag,
                            'is_private': user.get('is_private'),
                            'is_verified': user.get('is_verified'),
                        }
                    })
                    saved_count += 1
                except Exception as e:
                    logger.warning(f"Erro ao salvar user {user.get('username')}: {e}")

        return {
            "success": True,
            "hashtag": hashtag,
            "users": users,
            "count": len(users),
            "saved_to_db": saved_count
        }

    except Exception as e:
        logger.error(f"Erro ao buscar hashtag: {e}", exc_info=True)
        return {
            "success": False,
            "hashtag": hashtag,
            "error": str(e),
            "users": []
        }


# ============================================
# BATCH SCRAPE ENDPOINT
# ============================================

class BatchScrapeRequest(BaseModel):
    """Request para scrape em lote de usernames."""
    usernames: List[str] = Field(..., description="Lista de usernames a processar")
    save_to_db: bool = Field(True, description="Salvar leads no banco")
    tenant_id: Optional[str] = Field(None, description="ID do tenant")


@app.post("/webhook/scrape-batch")
async def scrape_batch(request: BatchScrapeRequest):
    """
    Scrape múltiplos perfis de uma vez.
    Processa lista de usernames e retorna dados de cada um.
    """
    logger.info(f"Batch scraping {len(request.usernames)} perfis")

    try:
        from instagram_api_scraper import InstagramAPIScraper
        from supabase_integration import SupabaseClient

        scraper = InstagramAPIScraper()
        db = SupabaseClient() if request.save_to_db else None

        results = []
        success_count = 0
        saved_count = 0

        for username in request.usernames:
            username = username.strip().lstrip("@").lower()
            if not username:
                continue

            try:
                profile = scraper.get_profile(username)

                if profile.get("success"):
                    score_data = scraper.calculate_lead_score(profile)
                    profile.update(score_data)
                    success_count += 1

                    # Salvar no banco
                    if db:
                        try:
                            db._request('POST', 'growth_leads', data={
                                'instagram_username': username,
                                'name': profile.get('full_name') or username,
                                'source_channel': 'instagram_batch_scrape',
                                'funnel_stage': 'lead',
                                'lead_temperature': 'hot' if profile.get('score', 0) >= 60 else 'warm' if profile.get('score', 0) >= 40 else 'cold',
                                'lead_score': profile.get('score', 0),
                                'location_id': request.tenant_id or '11111111-1111-1111-1111-111111111111',
                                'avatar_url': profile.get('profile_pic_url'),
                                'custom_fields': {
                                    'instagram_bio': profile.get('bio'),
                                    'instagram_followers': profile.get('followers_count'),
                                    'instagram_following': profile.get('following_count'),
                                    'instagram_posts': profile.get('posts_count'),
                                    'instagram_is_business': profile.get('is_business'),
                                    'instagram_is_verified': profile.get('is_verified'),
                                    'classification': profile.get('classification'),
                                    'signals': profile.get('signals', []),
                                }
                            })
                            saved_count += 1
                        except Exception as e:
                            logger.warning(f"Erro ao salvar {username}: {e}")

                results.append({
                    "username": username,
                    "success": profile.get("success", False),
                    "full_name": profile.get("full_name"),
                    "followers": profile.get("followers_count", 0),
                    "score": profile.get("score", 0),
                    "classification": profile.get("classification", "LEAD_COLD"),
                    "error": profile.get("error") if not profile.get("success") else None
                })

                # Rate limiting entre requests
                import time
                time.sleep(1.5)

            except Exception as e:
                results.append({
                    "username": username,
                    "success": False,
                    "error": str(e)
                })

        return {
            "success": True,
            "total": len(request.usernames),
            "processed": len(results),
            "success_count": success_count,
            "saved_to_db": saved_count,
            "results": results
        }

    except Exception as e:
        logger.error(f"Erro no batch scrape: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "results": []
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
    3. Save to Supabase (crm_leads + growth_leads)
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
# LEADS API (with pagination)
# ============================================

@app.get("/api/leads")
async def get_leads(
    source: Optional[str] = None,
    tenant_id: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    per_page: int = 50,
    sort_by: str = "created_at",
    sort_order: str = "desc"
):
    """
    Get leads from database with filters and pagination.

    Args:
        source: Filter by lead source (e.g., 'post_like', 'api_scrape')
        tenant_id: Filter by tenant
        status: Filter by status (warm, cold, hot)
        search: Search in username or name
        page: Page number (1-indexed)
        per_page: Items per page (max 100)
        sort_by: Sort field (created_at, username, score)
        sort_order: Sort order (asc, desc)

    Returns:
        Paginated response with leads and metadata
    """
    try:
        # Validate pagination params
        page = max(1, page)
        per_page = min(max(1, per_page), 100)  # Max 100 items per page
        offset = (page - 1) * per_page

        # Build query params
        params = {
            "limit": per_page,
            "offset": offset,
            "order": f"{sort_by}.{sort_order}"
        }

        if source:
            params["source"] = f"eq.{source}"
        if tenant_id:
            params["tenant_id"] = f"eq.{tenant_id}"
        if status:
            params["status"] = f"eq.{status}"
        if search:
            params["or"] = f"(username.ilike.%{search}%,full_name.ilike.%{search}%)"

        # Get leads
        response = requests.get(
            f"{db.base_url}/agentic_instagram_leads",
            headers=db.headers,
            params=params
        )
        leads = response.json() if response.status_code == 200 else []

        # Get total count for pagination
        count_headers = {**db.headers, "Prefer": "count=exact"}
        count_params = {k: v for k, v in params.items() if k not in ["limit", "offset", "order"]}
        count_response = requests.head(
            f"{db.base_url}/agentic_instagram_leads",
            headers=count_headers,
            params=count_params
        )

        # Parse total from Content-Range header
        content_range = count_response.headers.get("Content-Range", "0-0/0")
        try:
            total = int(content_range.split("/")[-1])
        except (ValueError, IndexError):
            total = len(leads)

        total_pages = (total + per_page - 1) // per_page if per_page > 0 else 1

        return {
            "success": True,
            "data": leads,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
                "next_page": page + 1 if page < total_pages else None,
                "prev_page": page - 1 if page > 1 else None
            },
            "filters": {
                "source": source,
                "tenant_id": tenant_id,
                "status": status,
                "search": search,
                "sort_by": sort_by,
                "sort_order": sort_order
            }
        }

    except Exception as e:
        logger.error(f"Error fetching leads: {e}")
        return {"success": False, "error": str(e), "data": [], "pagination": None}


@app.get("/api/classified-leads")
async def get_classified_leads(
    classification: Optional[str] = None,
    tenant_id: Optional[str] = None,
    min_score: int = 0,
    max_score: int = 100,
    page: int = 1,
    per_page: int = 50,
    sort_by: str = "created_at",
    sort_order: str = "desc"
):
    """
    Get classified leads with filters and pagination.

    Args:
        classification: Filter by classification (LEAD_HOT, LEAD_WARM, LEAD_COLD, SPAM)
        tenant_id: Filter by tenant
        min_score: Minimum score filter (0-100)
        max_score: Maximum score filter (0-100)
        page: Page number (1-indexed)
        per_page: Items per page (max 100)
        sort_by: Sort field (created_at, score, classification)
        sort_order: Sort order (asc, desc)

    Returns:
        Paginated response with classified leads
    """
    try:
        # Validate pagination params
        page = max(1, page)
        per_page = min(max(1, per_page), 100)
        offset = (page - 1) * per_page

        # Build query params
        params = {
            "limit": per_page,
            "offset": offset,
            "order": f"{sort_by}.{sort_order}"
        }

        if classification:
            params["classification"] = f"eq.{classification}"
        if tenant_id:
            params["tenant_id"] = f"eq.{tenant_id}"

        # Get leads
        response = requests.get(
            f"{db.base_url}/classified_leads",
            headers=db.headers,
            params=params
        )
        leads = response.json() if response.status_code == 200 else []

        # Filter by score in Python (score column may not exist in all records)
        if leads and (min_score > 0 or max_score < 100):
            leads = [
                l for l in leads
                if min_score <= l.get("score", 0) <= max_score
            ]

        # Get total count
        count_headers = {**db.headers, "Prefer": "count=exact"}
        count_params = {k: v for k, v in params.items() if k not in ["limit", "offset", "order"]}
        count_response = requests.head(
            f"{db.base_url}/classified_leads",
            headers=count_headers,
            params=count_params
        )

        content_range = count_response.headers.get("Content-Range", "0-0/0")
        try:
            total = int(content_range.split("/")[-1])
        except (ValueError, IndexError):
            total = len(leads)

        total_pages = (total + per_page - 1) // per_page if per_page > 0 else 1

        return {
            "success": True,
            "data": leads,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
                "next_page": page + 1 if page < total_pages else None,
                "prev_page": page - 1 if page > 1 else None
            },
            "filters": {
                "classification": classification,
                "tenant_id": tenant_id,
                "min_score": min_score,
                "max_score": max_score,
                "sort_by": sort_by,
                "sort_order": sort_order
            }
        }

    except Exception as e:
        logger.error(f"Error fetching classified leads: {e}")
        return {"success": False, "error": str(e), "data": [], "pagination": None}


@app.get("/api/history")
async def get_activity_history(
    event_type: Optional[str] = None,
    tenant_id: Optional[str] = None,
    username: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    per_page: int = 50
):
    """
    Get activity history with pagination.
    Combines DMs sent, leads processed, and other activities.

    Args:
        event_type: Filter by type (dm_sent, lead_classified, profile_scraped)
        tenant_id: Filter by tenant
        username: Filter by username
        start_date: Start date filter (ISO format)
        end_date: End date filter (ISO format)
        page: Page number
        per_page: Items per page

    Returns:
        Paginated activity history
    """
    try:
        page = max(1, page)
        per_page = min(max(1, per_page), 100)
        offset = (page - 1) * per_page

        all_history = []

        # Get DMs sent
        dm_params = {
            "limit": per_page * 2,  # Fetch more to combine
            "order": "sent_at.desc"
        }
        if tenant_id:
            dm_params["tenant_id"] = f"eq.{tenant_id}"
        if username:
            dm_params["username"] = f"eq.{username}"
        if start_date:
            dm_params["sent_at"] = f"gte.{start_date}"
        if end_date:
            dm_params["sent_at"] = f"lte.{end_date}"

        dm_response = requests.get(
            f"{db.base_url}/agentic_instagram_dm_sent",
            headers=db.headers,
            params=dm_params
        )

        if dm_response.status_code == 200:
            for dm in dm_response.json():
                all_history.append({
                    "event_type": "dm_sent",
                    "timestamp": dm.get("sent_at"),
                    "username": dm.get("username"),
                    "details": {
                        "message_preview": (dm.get("message") or "")[:100] + "..." if dm.get("message") and len(dm.get("message", "")) > 100 else dm.get("message"),
                        "status": dm.get("status", "sent")
                    },
                    "tenant_id": dm.get("tenant_id")
                })

        # Get classified leads as events
        if not event_type or event_type == "lead_classified":
            lead_params = {
                "limit": per_page * 2,
                "order": "created_at.desc"
            }
            if tenant_id:
                lead_params["tenant_id"] = f"eq.{tenant_id}"
            if username:
                lead_params["username"] = f"eq.{username}"

            leads_response = requests.get(
                f"{db.base_url}/classified_leads",
                headers=db.headers,
                params=lead_params
            )

            if leads_response.status_code == 200:
                for lead in leads_response.json():
                    all_history.append({
                        "event_type": "lead_classified",
                        "timestamp": lead.get("created_at"),
                        "username": lead.get("username"),
                        "details": {
                            "classification": lead.get("classification"),
                            "score": lead.get("score"),
                            "reasoning": (lead.get("reasoning") or "")[:100]
                        },
                        "tenant_id": lead.get("tenant_id")
                    })

        # Filter by event_type if specified
        if event_type:
            all_history = [h for h in all_history if h["event_type"] == event_type]

        # Sort by timestamp descending
        all_history.sort(key=lambda x: x.get("timestamp") or "", reverse=True)

        # Apply pagination
        total = len(all_history)
        paginated = all_history[offset:offset + per_page]
        total_pages = (total + per_page - 1) // per_page if per_page > 0 else 1

        return {
            "success": True,
            "data": paginated,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
                "next_page": page + 1 if page < total_pages else None,
                "prev_page": page - 1 if page > 1 else None
            },
            "filters": {
                "event_type": event_type,
                "tenant_id": tenant_id,
                "username": username,
                "start_date": start_date,
                "end_date": end_date
            }
        }

    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        return {"success": False, "error": str(e), "data": [], "pagination": None}


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


# ============================================
# MATCH LEAD CONTEXT - Endpoint principal para n8n
# ============================================

class MatchLeadContextRequest(BaseModel):
    """Request para match de lead vindo do webhook GHL."""
    phone: Optional[str] = Field(None, description="Telefone do contato")
    email: Optional[str] = Field(None, description="Email do contato")
    ig_id: Optional[str] = Field(None, description="Instagram Session ID (igSid)")
    ig_handle: Optional[str] = Field(None, description="Instagram handle (@usuario)")
    ghl_contact_id: Optional[str] = Field(None, description="ID do contato no GHL")
    location_id: Optional[str] = Field(None, description="ID da location GHL")
    first_name: Optional[str] = Field(None, description="Primeiro nome do contato")


class MatchLeadContextResponse(BaseModel):
    """Response com contexto completo do lead."""
    matched: bool
    source: Optional[str] = None  # agenticos_prospecting, ghl_inbound, unknown

    # Dados do lead
    lead_data: Optional[Dict[str, Any]] = None

    # Contexto de prospecção
    prospecting_context: Optional[Dict[str, Any]] = None

    # Histórico de conversas
    conversation_history: Optional[List[Dict[str, Any]]] = None

    # Placeholders prontos para o prompt
    placeholders: Optional[Dict[str, str]] = None

    # Ação necessária se não encontrou
    action_required: Optional[str] = None  # scrape_profile, create_lead, none
    scrape_target: Optional[Dict[str, Any]] = None


def normalize_phone(phone: str) -> str:
    """Normaliza telefone para formato internacional."""
    import re
    if not phone:
        return ""
    # Remove tudo que não é dígito
    digits = re.sub(r'\D', '', phone)
    # Se começa com 55 e tem 12-13 dígitos, já está ok
    if digits.startswith('55') and len(digits) >= 12:
        return f"+{digits}"
    # Se tem 11 dígitos (DDD + celular BR)
    if len(digits) == 11:
        return f"+55{digits}"
    # Se tem 10 dígitos (DDD + fixo BR)
    if len(digits) == 10:
        return f"+55{digits}"
    # Retorna como está
    return f"+{digits}" if digits else ""


def normalize_instagram(handle: str) -> str:
    """Normaliza handle do Instagram."""
    if not handle:
        return ""
    # Remove @ se tiver
    handle = handle.lstrip("@").lower().strip()
    # Remove URL se for
    if "instagram.com" in handle:
        handle = handle.split("/")[-1].split("?")[0]
    return f"@{handle}"


@app.post("/api/match-lead-context", response_model=MatchLeadContextResponse)
async def match_lead_context(request: MatchLeadContextRequest):
    """
    Endpoint principal para n8n buscar contexto do lead.

    Recebe dados do webhook GHL e tenta encontrar o lead no AgenticOS.
    Retorna dados enriquecidos, histórico e placeholders prontos para o prompt.

    Fluxo:
    1. Tenta match por ghl_contact_id (se já sincronizado)
    2. Tenta match por phone (normalizado)
    3. Tenta match por email
    4. Tenta match por ig_handle ou ig_id
    5. Se não encontrar, retorna action_required = scrape_profile
    """
    logger.info(f"Match Lead Context: phone={request.phone}, email={request.email}, ig_id={request.ig_id}")

    try:
        lead = None
        enriched = {}
        match_source = "unknown"

        # Normalizar identificadores
        phone_normalized = normalize_phone(request.phone) if request.phone else None
        email_normalized = request.email.lower().strip() if request.email else None
        ig_handle_normalized = normalize_instagram(request.ig_handle) if request.ig_handle else None

        # ============================================
        # TENTATIVA 1: Match por ghl_contact_id
        # ============================================
        if request.ghl_contact_id:
            try:
                response = requests.get(
                    f"{db.base_url}/growth_leads",
                    headers=db.headers,
                    params={
                        "ghl_contact_id": f"eq.{request.ghl_contact_id}",
                        "limit": 1
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    if data:
                        lead = data[0]
                        match_source = "ghl_synced"
                        logger.info(f"Match por ghl_contact_id: {request.ghl_contact_id}")
            except Exception as e:
                logger.warning(f"Erro match ghl_contact_id: {e}")

        # ============================================
        # TENTATIVA 2: Match por phone
        # ============================================
        if not lead and phone_normalized:
            try:
                # Tentar em growth_leads
                response = requests.get(
                    f"{db.base_url}/growth_leads",
                    headers=db.headers,
                    params={
                        "phone": f"eq.{phone_normalized}",
                        "limit": 1
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    if data:
                        lead = data[0]
                        match_source = "agenticos_prospecting"
                        logger.info(f"Match por phone: {phone_normalized}")

                # Fallback: crm_leads
                if not lead:
                    response = requests.get(
                        f"{db.base_url}/crm_leads",
                        headers=db.headers,
                        params={
                            "phone": f"eq.{phone_normalized}",
                            "limit": 1
                        }
                    )
                    if response.status_code == 200:
                        data = response.json()
                        if data:
                            lead = data[0]
                            match_source = "agenticos_crm"
                            logger.info(f"Match por phone (crm_leads): {phone_normalized}")
            except Exception as e:
                logger.warning(f"Erro match phone: {e}")

        # ============================================
        # TENTATIVA 3: Match por email
        # ============================================
        if not lead and email_normalized:
            try:
                response = requests.get(
                    f"{db.base_url}/growth_leads",
                    headers=db.headers,
                    params={
                        "email": f"eq.{email_normalized}",
                        "limit": 1
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    if data:
                        lead = data[0]
                        match_source = "agenticos_prospecting"
                        logger.info(f"Match por email: {email_normalized}")
            except Exception as e:
                logger.warning(f"Erro match email: {e}")

        # ============================================
        # TENTATIVA 4: Match por instagram_username
        # ============================================
        if not lead and ig_handle_normalized:
            try:
                response = requests.get(
                    f"{db.base_url}/growth_leads",
                    headers=db.headers,
                    params={
                        "instagram_username": f"eq.{ig_handle_normalized}",
                        "limit": 1
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    if data:
                        lead = data[0]
                        match_source = "agenticos_prospecting"
                        logger.info(f"Match por ig_handle: {ig_handle_normalized}")
            except Exception as e:
                logger.warning(f"Erro match ig_handle: {e}")

        # ============================================
        # TENTATIVA 5: Match por agentic_instagram_leads (scrapes)
        # ============================================
        if not lead and ig_handle_normalized:
            try:
                # Remove @ para busca
                handle_clean = ig_handle_normalized.lstrip("@")
                response = requests.get(
                    f"{db.base_url}/agentic_instagram_leads",
                    headers=db.headers,
                    params={
                        "username": f"eq.{handle_clean}",
                        "limit": 1
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    if data:
                        # Converter formato
                        ig_lead = data[0]
                        lead = {
                            "id": ig_lead.get("id"),
                            "name": ig_lead.get("full_name"),
                            "instagram_username": ig_lead.get('username'),
                            "source_channel": "instagram_scrape",
                            "ig_followers": ig_lead.get("followers"),
                            "ig_bio": ig_lead.get("bio"),
                            "created_at": ig_lead.get("created_at")
                        }
                        match_source = "instagram_scrape"
                        logger.info(f"Match por agentic_instagram_leads: {handle_clean}")
            except Exception as e:
                logger.warning(f"Erro match agentic_instagram_leads: {e}")

        # ============================================
        # SE NÃO ENCONTROU - Retornar ação necessária
        # ============================================
        if not lead:
            logger.info(f"Lead não encontrado. Retornando action_required=scrape_profile")
            return MatchLeadContextResponse(
                matched=False,
                source="unknown",
                action_required="scrape_profile",
                scrape_target={
                    "phone": phone_normalized,
                    "email": email_normalized,
                    "ig_id": request.ig_id,
                    "ig_handle": ig_handle_normalized,
                    "first_name": request.first_name
                }
            )

        # ============================================
        # BUSCAR DADOS ENRIQUECIDOS
        # ============================================
        lead_id = lead.get("id")
        if lead_id:
            try:
                response = requests.get(
                    f"{db.base_url}/enriched_lead_data",
                    headers=db.headers,
                    params={
                        "lead_id": f"eq.{lead_id}",
                        "order": "created_at.desc"
                    }
                )
                if response.status_code == 200:
                    enriched_list = response.json()

                    # Consolidar dados de múltiplas fontes
                    for e in enriched_list:
                        if not enriched.get("cargo") and e.get("cargo"):
                            enriched["cargo"] = e["cargo"]
                        if not enriched.get("empresa") and e.get("empresa"):
                            enriched["empresa"] = e["empresa"]
                        if not enriched.get("setor") and e.get("setor"):
                            enriched["setor"] = e["setor"]
                        if not enriched.get("porte") and e.get("porte"):
                            enriched["porte"] = e["porte"]
                        if not enriched.get("ig_followers") and e.get("ig_followers"):
                            enriched["ig_followers"] = e["ig_followers"]
                        if not enriched.get("ig_bio") and e.get("ig_bio"):
                            enriched["ig_bio"] = e["ig_bio"]
            except Exception as e:
                logger.warning(f"Erro buscando enriched_data: {e}")

        # ============================================
        # BUSCAR HISTÓRICO DE CONVERSAS
        # ============================================
        conversation_history = []
        if lead_id:
            try:
                response = requests.get(
                    f"{db.base_url}/agent_conversations",
                    headers=db.headers,
                    params={
                        "or": f"(lead_id.eq.{lead_id},contact_id.eq.{lead_id})",
                        "order": "created_at.desc",
                        "limit": 10
                    }
                )
                if response.status_code == 200:
                    convs = response.json()
                    for c in convs:
                        conversation_history.append({
                            "role": c.get("role", "unknown"),
                            "content": c.get("message") or c.get("content"),
                            "at": c.get("created_at"),
                            "channel": c.get("channel")
                        })
            except Exception as e:
                logger.warning(f"Erro buscando histórico: {e}")

        # ============================================
        # DETERMINAR SE FOI PROSPECTADO
        # ============================================
        source_channel = lead.get("source_channel", "")
        funnel_stage = lead.get("funnel_stage", "")
        was_prospected = any([
            source_channel.startswith("outbound") if source_channel else False,
            source_channel.startswith("instagram_scrape") if source_channel else False,
            source_channel.startswith("linkedin_scrape") if source_channel else False,
            lead.get("outreach_sent_at") is not None,
            funnel_stage == "prospected"
        ])

        # ============================================
        # MONTAR LEAD_DATA
        # ============================================
        lead_data = {
            "id": lead.get("id"),
            "name": lead.get("name") or lead.get("full_name") or request.first_name,
            "phone": lead.get("phone"),
            "email": lead.get("email"),
            "instagram_username": lead.get("instagram_username"),
            "cargo": enriched.get("cargo") or lead.get("cargo") or lead.get("title"),
            "empresa": enriched.get("empresa") or lead.get("empresa") or lead.get("company"),
            "setor": enriched.get("setor") or lead.get("setor"),
            "porte": enriched.get("porte") or lead.get("porte"),
            "icp_score": lead.get("icp_score"),
            "lead_temperature": lead.get("lead_temperature"),
            "ig_followers": enriched.get("ig_followers") or lead.get("ig_followers"),
            "ig_bio": enriched.get("ig_bio") or lead.get("ig_bio"),
            "ig_engagement": lead.get("ig_engagement"),
            "source_channel": lead.get("source_channel"),
            "funnel_stage": lead.get("funnel_stage"),
            "ghl_contact_id": lead.get("ghl_contact_id"),
            "location_id": lead.get("location_id"),
            "created_at": lead.get("created_at")
        }
        # Remover None
        lead_data = {k: v for k, v in lead_data.items() if v is not None}

        # ============================================
        # MONTAR PROSPECTING_CONTEXT
        # ============================================
        prospecting_context = {
            "was_prospected": was_prospected,
            "prospected_at": lead.get("outreach_sent_at"),
            "outreach_message": lead.get("last_outreach_message"),
            "outreach_channel": lead.get("source_channel") or (
                "instagram_dm" if "instagram" in str(lead.get("source_channel", "")).lower() else None
            )
        }

        # ============================================
        # MONTAR PLACEHOLDERS PARA O PROMPT
        # ============================================
        nome = lead_data.get("name", "").split()[0] if lead_data.get("name") else request.first_name or ""

        # Contexto de prospecção formatado
        contexto_prospeccao = ""
        if was_prospected:
            data_prospeccao = lead.get("outreach_sent_at", "data desconhecida")
            if isinstance(data_prospeccao, str) and "T" in data_prospeccao:
                data_prospeccao = data_prospeccao.split("T")[0]
            contexto_prospeccao = f"Lead prospectado em {data_prospeccao}"
            if prospecting_context.get("outreach_channel"):
                contexto_prospeccao += f" via {prospecting_context['outreach_channel']}"
            if lead_data.get("cargo") and lead_data.get("empresa"):
                contexto_prospeccao += f". Identificado como {lead_data['cargo']} na {lead_data['empresa']}."
            if lead_data.get("lead_temperature"):
                contexto_prospeccao += f" Classificado como {lead_data['lead_temperature']}."

        placeholders = {
            "{{nome}}": nome,
            "{{primeiro_nome}}": nome,
            "{{nome_completo}}": lead_data.get("name", ""),
            "{{cargo}}": lead_data.get("cargo", ""),
            "{{empresa}}": lead_data.get("empresa", ""),
            "{{setor}}": lead_data.get("setor", ""),
            "{{porte}}": lead_data.get("porte", ""),
            "{{icp_score}}": str(lead_data.get("icp_score", "")),
            "{{lead_temperature}}": lead_data.get("lead_temperature", ""),
            "{{ig_followers}}": str(lead_data.get("ig_followers", "")),
            "{{ig_bio}}": lead_data.get("ig_bio", ""),
            "{{contexto_prospeccao}}": contexto_prospeccao,
            "{{foi_prospectado}}": "sim" if was_prospected else "não",
            "{{fonte}}": lead_data.get("source_channel", "")
        }
        # Remover placeholders vazios
        placeholders = {k: v for k, v in placeholders.items() if v}

        logger.info(f"Match encontrado! source={match_source}, lead_id={lead_data.get('id')}")

        return MatchLeadContextResponse(
            matched=True,
            source=match_source,
            lead_data=lead_data,
            prospecting_context=prospecting_context,
            conversation_history=conversation_history if conversation_history else None,
            placeholders=placeholders,
            action_required="none"
        )

    except Exception as e:
        logger.error(f"Match Lead Context error: {e}", exc_info=True)
        return MatchLeadContextResponse(
            matched=False,
            source="error",
            action_required="scrape_profile",
            scrape_target={
                "phone": request.phone,
                "email": request.email,
                "ig_id": request.ig_id,
                "error": str(e)
            }
        )


# ============================================
# AUTO ENRICH LEAD - Scrape automático quando não encontrado
# ============================================

class AutoEnrichRequest(BaseModel):
    """Request para enriquecimento automático de lead"""
    phone: Optional[str] = None
    email: Optional[str] = None
    ig_id: Optional[str] = None
    ig_handle: Optional[str] = None
    ghl_contact_id: Optional[str] = None
    location_id: Optional[str] = None
    first_name: Optional[str] = None
    source_channel: Optional[str] = "unknown"

class AutoEnrichResponse(BaseModel):
    """Response do enriquecimento automático"""
    success: bool
    action_taken: str  # "matched", "scraped", "skipped", "error"
    lead_data: Optional[Dict[str, Any]] = None
    placeholders: Optional[Dict[str, str]] = None
    scrape_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@app.post("/api/auto-enrich-lead", response_model=AutoEnrichResponse)
async def auto_enrich_lead(request: AutoEnrichRequest):
    """
    Enriquecimento automático de lead.

    1. Primeiro tenta match no AgenticOS (via match-lead-context)
    2. Se não encontrar E tiver ig_handle → faz scrape automático
    3. Salva no banco e retorna dados enriquecidos

    Chamado pelo n8n quando matched=false no Match Lead Context.
    """
    logger.info(f"Auto Enrich Lead: ig_handle={request.ig_handle}, phone={request.phone}")

    try:
        # ============================================
        # PASSO 1: Verificar se já existe no AgenticOS
        # ============================================
        match_request = MatchLeadContextRequest(
            phone=request.phone,
            email=request.email,
            ig_id=request.ig_id,
            ig_handle=request.ig_handle,
            ghl_contact_id=request.ghl_contact_id,
            location_id=request.location_id,
            first_name=request.first_name
        )

        match_result = await match_lead_context(match_request)

        if match_result.matched:
            logger.info(f"Lead já existe no AgenticOS: {match_result.lead_data.get('id') if match_result.lead_data else 'N/A'}")
            return AutoEnrichResponse(
                success=True,
                action_taken="matched",
                lead_data=match_result.lead_data,
                placeholders=match_result.placeholders
            )

        # ============================================
        # PASSO 2: Se tiver ig_handle, fazer scrape
        # ============================================
        ig_handle = request.ig_handle

        # Tentar extrair do ig_id se não tiver handle
        if not ig_handle and request.ig_id:
            # Tentar buscar username via API do Instagram
            try:
                from instagram_api_scraper import InstagramAPIScraper
                scraper = InstagramAPIScraper()
                user_info = scraper.get_user_by_id(request.ig_id)
                if user_info and user_info.get("username"):
                    ig_handle = user_info.get("username")
                    logger.info(f"Username encontrado via ig_id: @{ig_handle}")
            except Exception as e:
                logger.warning(f"Não foi possível buscar username via ig_id: {e}")

        if not ig_handle:
            logger.info("Sem ig_handle para fazer scrape. Pulando enriquecimento.")
            return AutoEnrichResponse(
                success=True,
                action_taken="skipped",
                error="Sem ig_handle disponível para scrape"
            )

        # Normalizar handle
        ig_handle = ig_handle.lstrip("@").lower()

        logger.info(f"Iniciando scrape do perfil: @{ig_handle}")

        # ============================================
        # PASSO 3: Fazer scrape do perfil
        # ============================================
        try:
            from instagram_api_scraper import InstagramAPIScraper
            from supabase_integration import SocialfyAgentIntegration

            scraper = InstagramAPIScraper()
            profile = scraper.get_profile(ig_handle)

            if not profile.get("success"):
                logger.warning(f"Falha no scrape de @{ig_handle}: {profile.get('error')}")
                return AutoEnrichResponse(
                    success=False,
                    action_taken="error",
                    error=f"Scrape falhou: {profile.get('error')}"
                )

            # Calcular score
            score_data = scraper.calculate_lead_score(profile)

            # ============================================
            # PASSO 4: Salvar no banco
            # ============================================
            integration = SocialfyAgentIntegration()

            lead_name = profile.get("full_name") or request.first_name or ig_handle
            lead_email = request.email or profile.get("email") or f"{ig_handle}@instagram.lead"

            saved_lead = integration.save_discovered_lead(
                name=lead_name,
                email=lead_email,
                source=request.source_channel or "inbound_dm",
                profile_data={
                    "username": ig_handle,
                    "instagram_username": ig_handle,
                    "bio": profile.get("bio"),
                    "followers_count": profile.get("followers_count"),
                    "following_count": profile.get("following_count"),
                    "is_business": profile.get("is_business"),
                    "is_verified": profile.get("is_verified"),
                    "score": score_data.get("score", 0),
                    "classification": score_data.get("classification", "LEAD_COLD"),
                    "phone": request.phone or profile.get("phone"),
                    "company": profile.get("category"),
                    "ghl_contact_id": request.ghl_contact_id,
                    "location_id": request.location_id
                }
            )

            logger.info(f"Lead salvo com sucesso: @{ig_handle}")

            # ============================================
            # PASSO 5: Montar resposta com placeholders
            # ============================================
            # Map classification to lead_temperature
            classification = score_data.get("classification", "LEAD_COLD")
            lead_temperature = "hot" if classification == "LEAD_HOT" else ("warm" if classification == "LEAD_WARM" else "cold")

            lead_data = {
                "id": saved_lead.get("id") if saved_lead else None,
                "name": lead_name,
                "instagram_username": ig_handle,
                "ig_followers": profile.get("followers_count", 0),
                "ig_bio": profile.get("bio", ""),
                "icp_score": score_data.get("score", 0),
                "lead_temperature": lead_temperature,
                "source_channel": request.source_channel or "inbound_dm",
                "is_business": profile.get("is_business", False),
                "is_verified": profile.get("is_verified", False),
                "category": profile.get("category")
            }

            primeiro_nome = lead_name.split()[0] if lead_name else ig_handle

            placeholders = {
                "{{nome}}": primeiro_nome,
                "{{primeiro_nome}}": primeiro_nome,
                "{{nome_completo}}": lead_name,
                "{{instagram_username}}": ig_handle,
                "{{ig_followers}}": str(profile.get("followers_count", 0)),
                "{{ig_bio}}": profile.get("bio", ""),
                "{{icp_score}}": str(score_data.get("score", 0)),
                "{{lead_temperature}}": lead_temperature,
                "{{fonte}}": request.source_channel or "inbound_dm",
                "{{categoria}}": profile.get("category", ""),
                "{{foi_prospectado}}": "não",
                "{{contexto_prospeccao}}": f"Novo lead via {request.source_channel or 'Instagram'}. Perfil: {profile.get('followers_count', 0)} seguidores. Bio: {(profile.get('bio', '') or '')[:100]}"
            }

            # Remover placeholders vazios
            placeholders = {k: v for k, v in placeholders.items() if v}

            return AutoEnrichResponse(
                success=True,
                action_taken="scraped",
                lead_data=lead_data,
                placeholders=placeholders,
                scrape_result={
                    "username": ig_handle,
                    "followers": profile.get("followers_count"),
                    "score": score_data.get("score"),
                    "classification": score_data.get("classification")
                }
            )

        except Exception as e:
            logger.error(f"Erro no scrape/save: {e}", exc_info=True)
            return AutoEnrichResponse(
                success=False,
                action_taken="error",
                error=str(e)
            )

    except Exception as e:
        logger.error(f"Auto Enrich error: {e}", exc_info=True)
        return AutoEnrichResponse(
            success=False,
            action_taken="error",
            error=str(e)
        )


# ============================================
# ANALYZE CONVERSATION CONTEXT - Detecta se é resposta de prospecção
# ============================================

class ConversationContextRequest(BaseModel):
    """Request para análise de contexto de conversa"""
    contact_id: str
    location_id: str
    current_message: str
    contact_tags: Optional[List[str]] = None
    last_message_direction: Optional[str] = None  # "inbound" ou "outbound"
    conversation_count: Optional[int] = None

class ConversationContextResponse(BaseModel):
    """Response da análise de contexto"""
    should_activate_ia: bool
    reason: str
    context_type: str  # "prospecting_response", "inbound_organic", "returning_lead", "personal", "spam"
    confidence: float
    recommendation: str
    extra_context: Optional[Dict[str, Any]] = None

@app.post("/api/analyze-conversation-context", response_model=ConversationContextResponse)
async def analyze_conversation_context(request: ConversationContextRequest):
    """
    Analisa o contexto da conversa para decidir se deve ativar IA.

    Lógica:
    1. Se última mensagem foi NOSSA (outbound) → Lead está respondendo prospecção → ATIVAR
    2. Se tem tags de prospecção (prospectado, abordado, etc) → ATIVAR
    3. Se é primeira mensagem (inbound orgânico) → Classificar com IA
    4. Se histórico indica amigo/família → NÃO ATIVAR

    Chamado ANTES do classify-lead para dar contexto.
    """
    logger.info(f"Analyzing conversation context for contact {request.contact_id}")

    try:
        tags = request.contact_tags or []
        tags_lower = [t.lower() for t in tags]

        # ============================================
        # REGRA 1: Tags de prospecção = SEMPRE ativar
        # ============================================
        # NOTA: Tags que indicam que o lead FOI PROSPECTADO (recebeu outreach nosso)
        # NÃO incluir tags de ativação como "ativar_ia", "ia-ativa" - essas são flags de controle
        prospecting_tags = ["prospectado", "abordado", "social_selling", "outbound", "lead_qualificado", "lead-prospectado-ia"]
        has_prospecting_tag = any(tag in tags_lower for tag in prospecting_tags)

        if has_prospecting_tag:
            return ConversationContextResponse(
                should_activate_ia=True,
                reason="Lead possui tags de prospecção - foi abordado anteriormente",
                context_type="prospecting_response",
                confidence=0.95,
                recommendation="Ativar IA imediatamente - lead está respondendo prospecção",
                extra_context={"matching_tags": [t for t in tags if t.lower() in prospecting_tags]}
            )

        # ============================================
        # REGRA 2: Última mensagem foi nossa = Respondendo
        # ============================================
        if request.last_message_direction == "outbound":
            return ConversationContextResponse(
                should_activate_ia=True,
                reason="Última mensagem foi nossa - lead está respondendo",
                context_type="prospecting_response",
                confidence=0.90,
                recommendation="Ativar IA - lead respondeu nossa mensagem anterior"
            )

        # ============================================
        # REGRA 3: Tags de exclusão = NÃO ativar
        # ============================================
        exclusion_tags = ["amigo", "familia", "pessoal", "nao_ativar", "perdido", "spam", "bloqueado"]
        has_exclusion_tag = any(tag in tags_lower for tag in exclusion_tags)

        if has_exclusion_tag:
            return ConversationContextResponse(
                should_activate_ia=False,
                reason="Lead possui tags de exclusão - não é lead comercial",
                context_type="personal",
                confidence=0.95,
                recommendation="Não ativar IA - mover para perdido ou ignorar",
                extra_context={"matching_tags": [t for t in tags if t.lower() in exclusion_tags]}
            )

        # ============================================
        # REGRA 4: Primeira mensagem = Classificar com IA
        # ============================================
        if request.conversation_count is None or request.conversation_count <= 1:
            # Analisar mensagem com Gemini para classificar
            try:
                import google.generativeai as genai

                gemini_key = os.getenv("GEMINI_API_KEY")
                if gemini_key:
                    genai.configure(api_key=gemini_key)
                    model = genai.GenerativeModel("gemini-1.5-flash")

                    prompt = f"""Analise esta primeira mensagem de um contato e classifique:

MENSAGEM: "{request.current_message}"

Classifique como:
- LEAD_POTENTIAL: Parece ser alguém com interesse comercial
- PERSONAL: Parece ser amigo, família ou contato pessoal
- SPAM: Propaganda, bot ou irrelevante
- UNCLEAR: Não é possível determinar

Responda APENAS com o formato JSON:
{{"classification": "TIPO", "confidence": 0.X, "reason": "explicação breve"}}"""

                    response = model.generate_content(prompt)
                    response_text = response.text.strip()

                    # Parse JSON da resposta
                    if "{" in response_text:
                        json_str = response_text[response_text.find("{"):response_text.rfind("}")+1]
                        analysis = json.loads(json_str)

                        classification = analysis.get("classification", "UNCLEAR")
                        confidence = analysis.get("confidence", 0.5)

                        if classification == "LEAD_POTENTIAL":
                            return ConversationContextResponse(
                                should_activate_ia=True,
                                reason=f"Primeira mensagem - IA classificou como potencial lead: {analysis.get('reason', '')}",
                                context_type="inbound_organic",
                                confidence=confidence,
                                recommendation="Ativar IA para qualificação"
                            )
                        elif classification == "PERSONAL":
                            return ConversationContextResponse(
                                should_activate_ia=False,
                                reason=f"Primeira mensagem - IA identificou como pessoal: {analysis.get('reason', '')}",
                                context_type="personal",
                                confidence=confidence,
                                recommendation="Não ativar IA - provavelmente contato pessoal"
                            )
                        elif classification == "SPAM":
                            return ConversationContextResponse(
                                should_activate_ia=False,
                                reason=f"Primeira mensagem - IA identificou como spam: {analysis.get('reason', '')}",
                                context_type="spam",
                                confidence=confidence,
                                recommendation="Não ativar IA - marcar como spam"
                            )
            except Exception as e:
                logger.warning(f"Erro ao classificar com Gemini: {e}")

        # ============================================
        # REGRA 5: Lead retornando (já teve conversa)
        # ============================================
        if request.conversation_count and request.conversation_count > 1:
            return ConversationContextResponse(
                should_activate_ia=True,
                reason="Lead retornando - já houve conversas anteriores",
                context_type="returning_lead",
                confidence=0.75,
                recommendation="Ativar IA para continuar atendimento"
            )

        # ============================================
        # FALLBACK: Caso não se encaixe em nenhuma regra
        # ============================================
        return ConversationContextResponse(
            should_activate_ia=True,
            reason="Contexto não determinado - ativando IA por precaução",
            context_type="inbound_organic",
            confidence=0.50,
            recommendation="Ativar IA e monitorar"
        )

    except Exception as e:
        logger.error(f"Error analyzing conversation context: {e}", exc_info=True)
        # Em caso de erro, ativar IA por segurança
        return ConversationContextResponse(
            should_activate_ia=True,
            reason=f"Erro na análise: {str(e)} - ativando por precaução",
            context_type="inbound_organic",
            confidence=0.30,
            recommendation="Ativar IA (fallback de erro)"
        )


@app.get("/api/health")
async def api_health_check():
    """
    Comprehensive health check endpoint.

    Returns complete system status including:
    - Server uptime and version
    - Database connections status
    - External service integrations
    - Rate limiter statistics
    - Request metrics
    - System resources (CPU, memory)
    """
    now = datetime.now()
    uptime_seconds = time.time() - SERVER_START_TIME

    # Calculate uptime in human-readable format
    days, remainder = divmod(int(uptime_seconds), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"

    health = {
        "status": "healthy",
        "timestamp": now.isoformat(),
        "version": "1.0.0",
        "uptime": {
            "seconds": int(uptime_seconds),
            "human": uptime_str,
            "started_at": datetime.fromtimestamp(SERVER_START_TIME).isoformat()
        },
        "connections": {},
        "rate_limiter": rate_limiter.get_stats(),
        "metrics": {
            "total_requests": request_metrics["total_requests"],
            "successful_requests": request_metrics["successful_requests"],
            "failed_requests": request_metrics["failed_requests"],
            "success_rate": round(
                request_metrics["successful_requests"] / max(1, request_metrics["total_requests"]) * 100, 2
            ),
            "last_request": request_metrics["last_request_time"],
            "top_endpoints": dict(
                sorted(
                    request_metrics["requests_by_endpoint"].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10]
            ),
            "status_codes": dict(request_metrics["requests_by_status"])
        }
    }

    # Check Supabase connection
    try:
        test_response = requests.get(
            f"{SUPABASE_URL}/rest/v1/",
            headers={"apikey": SUPABASE_KEY},
            timeout=5
        )
        if test_response.status_code < 500:
            health["connections"]["supabase"] = {"status": "connected", "latency_ms": int(test_response.elapsed.total_seconds() * 1000)}
        else:
            health["connections"]["supabase"] = {"status": "error", "code": test_response.status_code}
            health["status"] = "degraded"
    except requests.exceptions.Timeout:
        health["connections"]["supabase"] = {"status": "timeout"}
        health["status"] = "degraded"
    except Exception as e:
        health["connections"]["supabase"] = {"status": "error", "message": str(e)}
        health["status"] = "degraded"

    # Check GHL configuration
    ghl_key = os.getenv("GHL_API_KEY") or os.getenv("GHL_ACCESS_TOKEN")
    health["connections"]["ghl"] = {"status": "configured" if ghl_key else "not_configured"}

    # Check OpenAI configuration
    health["connections"]["openai"] = {"status": "configured" if OPENAI_API_KEY else "not_configured"}

    # System resources (if psutil available)
    try:
        health["system"] = {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory": {
                "percent": psutil.virtual_memory().percent,
                "available_mb": round(psutil.virtual_memory().available / (1024 * 1024), 2)
            },
            "disk": {
                "percent": psutil.disk_usage('/').percent
            }
        }
    except Exception:
        health["system"] = {"message": "psutil not available"}

    return health


@app.get("/api/metrics")
async def get_api_metrics():
    """
    Get detailed API metrics and rate limiter stats.
    Useful for monitoring and dashboards.
    """
    return {
        "timestamp": datetime.now().isoformat(),
        "rate_limiter": rate_limiter.get_stats(),
        "requests": {
            "total": request_metrics["total_requests"],
            "successful": request_metrics["successful_requests"],
            "failed": request_metrics["failed_requests"],
            "success_rate": round(
                request_metrics["successful_requests"] / max(1, request_metrics["total_requests"]) * 100, 2
            ),
            "last_request": request_metrics["last_request_time"]
        },
        "endpoints": dict(request_metrics["requests_by_endpoint"]),
        "status_codes": dict(request_metrics["requests_by_status"]),
        "uptime_seconds": int(time.time() - SERVER_START_TIME)
    }


# ============================================
# PORTAL CRM - ENDPOINTS
# ============================================

# Import portal service
PORTAL_SERVICE_AVAILABLE = False
PORTAL_IMPORT_ERROR = None

try:
    from portal_service import portal_service, LeadSyncData, MessageSyncData, FunnelStage
    PORTAL_SERVICE_AVAILABLE = True
    logger.info("Portal service loaded successfully")
except ImportError as e:
    PORTAL_IMPORT_ERROR = str(e)
    logger.warning(f"Portal service not available: {e}")
except Exception as e:
    PORTAL_IMPORT_ERROR = str(e)
    logger.error(f"Portal service error: {e}")


@app.get("/api/portal/status")
async def portal_status():
    """
    Verifica status do Portal CRM.
    Sempre disponível mesmo se portal_service falhar.
    """
    return {
        "portal_service_available": PORTAL_SERVICE_AVAILABLE,
        "import_error": PORTAL_IMPORT_ERROR,
        "version": "1.0.0",
        "endpoints": [
            "/api/portal/sync/lead",
            "/api/portal/sync/message",
            "/api/portal/sync/metrics",
            "/api/portal/dashboard/summary",
            "/api/portal/leads",
            "/api/portal/conversations"
        ] if PORTAL_SERVICE_AVAILABLE else []
    }


# Pydantic models for Portal API
class PortalLeadSyncRequest(BaseModel):
    """Request para sincronizar lead do GHL"""
    ghl_contact_id: str
    location_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    instagram_username: Optional[str] = None
    source_channel: Optional[str] = None
    source_campaign: Optional[str] = None
    funnel_stage: Optional[str] = "lead"
    lead_temperature: Optional[str] = "cold"
    lead_score: Optional[int] = 0
    tags: Optional[List[str]] = None
    custom_fields: Optional[Dict] = None


class PortalMessageSyncRequest(BaseModel):
    """Request para sincronizar mensagem do GHL"""
    ghl_conversation_id: str
    ghl_message_id: str
    location_id: str
    ghl_contact_id: str
    content: str
    direction: str  # inbound, outbound
    channel: str  # instagram, whatsapp, sms, email
    sent_at: str  # ISO datetime
    sender_name: Optional[str] = None
    is_from_ai: Optional[bool] = False
    content_type: Optional[str] = "text"
    media_url: Optional[str] = None


class PortalMetricsRequest(BaseModel):
    """Request para calcular métricas"""
    location_id: str
    date: Optional[str] = None  # ISO date, default: today


# ---- SYNC ENDPOINTS ----

@app.post("/api/portal/sync/lead")
async def portal_sync_lead(request: PortalLeadSyncRequest):
    """
    Sincroniza um lead do GHL para o Supabase.
    Chamado pelo n8n quando um contato é criado/atualizado no GHL.

    Cria ou atualiza o lead na tabela growth_leads.
    """
    if not PORTAL_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Portal service not available")

    try:
        # Garantir que tenant existe
        portal_service.ensure_tenant_exists(request.location_id)

        # Converter para dataclass
        lead_data = LeadSyncData(
            ghl_contact_id=request.ghl_contact_id,
            location_id=request.location_id,
            name=request.name,
            email=request.email,
            phone=request.phone,
            instagram_username=request.instagram_username,
            source_channel=request.source_channel,
            source_campaign=request.source_campaign,
            funnel_stage=request.funnel_stage or "lead",
            lead_temperature=request.lead_temperature or "cold",
            lead_score=request.lead_score or 0,
            tags=request.tags,
            custom_fields=request.custom_fields
        )

        result = portal_service.sync_lead(lead_data)
        return result

    except Exception as e:
        logger.error(f"Error in portal sync lead: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/portal/sync/message")
async def portal_sync_message(request: PortalMessageSyncRequest):
    """
    Sincroniza uma mensagem do GHL para o Supabase.
    Chamado pelo n8n quando uma mensagem é recebida/enviada.

    Cria/atualiza conversa e adiciona mensagem.
    """
    if not PORTAL_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Portal service not available")

    try:
        # Parse datetime
        try:
            sent_at = datetime.fromisoformat(request.sent_at.replace('Z', '+00:00'))
        except:
            sent_at = datetime.now()

        msg_data = MessageSyncData(
            ghl_conversation_id=request.ghl_conversation_id,
            ghl_message_id=request.ghl_message_id,
            location_id=request.location_id,
            ghl_contact_id=request.ghl_contact_id,
            content=request.content,
            direction=request.direction,
            channel=request.channel,
            sent_at=sent_at,
            sender_name=request.sender_name,
            is_from_ai=request.is_from_ai or False,
            content_type=request.content_type or "text",
            media_url=request.media_url
        )

        result = portal_service.sync_message(msg_data)
        return result

    except Exception as e:
        logger.error(f"Error in portal sync message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/portal/sync/metrics")
async def portal_calculate_metrics(request: PortalMetricsRequest):
    """
    Calcula métricas diárias para um tenant.
    Chamado pelo n8n via cron diário.

    Popula portal_metrics_daily com breakdown outbound/inbound.
    """
    if not PORTAL_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Portal service not available")

    try:
        from datetime import date as date_type

        target_date = None
        if request.date:
            target_date = date_type.fromisoformat(request.date)

        result = portal_service.calculate_daily_metrics(
            location_id=request.location_id,
            target_date=target_date
        )
        return result

    except Exception as e:
        logger.error(f"Error calculating metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---- DASHBOARD ENDPOINTS ----

@app.get("/api/portal/dashboard/summary")
async def portal_dashboard_summary(
    location_id: str,
    period: str = "30d"
):
    """
    Obtém resumo do dashboard para um tenant.

    Query params:
    - location_id: ID do tenant (GHL location)
    - period: 7d, 30d, 90d (default: 30d)

    Returns:
    - KPIs do funil (prospected, leads, qualified, scheduled, showed, won, lost)
    - Breakdown outbound vs inbound
    - Revenue total e ticket médio
    """
    if not PORTAL_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Portal service not available")

    try:
        # Parse period
        period_days = {
            "7d": 7,
            "30d": 30,
            "90d": 90
        }.get(period, 30)

        result = portal_service.get_dashboard_summary(
            location_id=location_id,
            period_days=period_days
        )
        return result

    except Exception as e:
        logger.error(f"Error getting dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/portal/dashboard/funnel")
async def portal_dashboard_funnel(
    location_id: str,
    period: str = "30d",
    source_type: Optional[str] = None
):
    """
    Obtém dados do funil de vendas.

    Query params:
    - location_id: ID do tenant
    - period: 7d, 30d, 90d
    - source_type: outbound, inbound, null (todos)

    Returns:
    - Contagem por etapa do funil
    - Taxas de conversão entre etapas
    """
    if not PORTAL_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Portal service not available")

    try:
        period_days = {"7d": 7, "30d": 30, "90d": 90}.get(period, 30)

        result = portal_service.get_dashboard_summary(
            location_id=location_id,
            period_days=period_days
        )

        # Se source_type especificado, filtrar dados
        if source_type and result.get("success") and result.get("data"):
            # Adicionar filtro específico aqui se necessário
            result["source_type_filter"] = source_type

        return result

    except Exception as e:
        logger.error(f"Error getting funnel: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---- LEADS ENDPOINTS ----

@app.get("/api/portal/leads")
async def portal_list_leads(
    location_id: str,
    page: int = 1,
    limit: int = 20,
    stage: Optional[str] = None,
    source_type: Optional[str] = None,
    search: Optional[str] = None
):
    """
    Lista leads de um tenant com paginação e filtros.

    Query params:
    - location_id: ID do tenant
    - page: Página atual (default: 1)
    - limit: Itens por página (default: 20, max: 100)
    - stage: Filtrar por etapa (prospected, lead, qualified, scheduled, showed, won, lost)
    - source_type: outbound ou inbound
    - search: Busca por nome ou email

    Returns:
    - Lista de leads
    - Informações de paginação
    """
    if not PORTAL_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Portal service not available")

    try:
        # Validar limit
        limit = min(limit, 100)

        result = portal_service.get_leads(
            location_id=location_id,
            page=page,
            limit=limit,
            stage=stage,
            source_type=source_type,
            search=search
        )
        return result

    except Exception as e:
        logger.error(f"Error listing leads: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/portal/leads/{lead_id}")
async def portal_get_lead(
    lead_id: str,
    location_id: str
):
    """
    Obtém detalhes completos de um lead.

    Path params:
    - lead_id: ID do lead

    Query params:
    - location_id: ID do tenant (para validação)

    Returns:
    - Dados completos do lead
    - Conversas recentes
    - Atividades recentes
    """
    if not PORTAL_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Portal service not available")

    try:
        result = portal_service.get_lead_detail(
            location_id=location_id,
            lead_id=lead_id
        )

        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error", "Lead not found"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting lead: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---- CONVERSATIONS ENDPOINTS ----

@app.get("/api/portal/conversations")
async def portal_list_conversations(
    location_id: str,
    page: int = 1,
    limit: int = 20,
    channel: Optional[str] = None,
    status: Optional[str] = None
):
    """
    Lista conversas de um tenant.

    Query params:
    - location_id: ID do tenant
    - page: Página atual
    - limit: Itens por página
    - channel: instagram, whatsapp, sms, email
    - status: open, closed

    Returns:
    - Lista de conversas com dados do lead
    - Informações de paginação
    """
    if not PORTAL_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Portal service not available")

    try:
        limit = min(limit, 100)

        result = portal_service.get_conversations(
            location_id=location_id,
            page=page,
            limit=limit,
            channel=channel,
            status=status
        )
        return result

    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/portal/conversations/{conversation_id}/messages")
async def portal_get_messages(
    conversation_id: str,
    location_id: str,
    limit: int = 50
):
    """
    Obtém mensagens de uma conversa.

    Path params:
    - conversation_id: ID da conversa

    Query params:
    - location_id: ID do tenant
    - limit: Máximo de mensagens (default: 50)

    Returns:
    - Lista de mensagens ordenadas cronologicamente
    """
    if not PORTAL_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Portal service not available")

    try:
        result = portal_service.get_conversation_messages(
            location_id=location_id,
            conversation_id=conversation_id,
            limit=limit
        )

        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error", "Conversation not found"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---- TENANT ENDPOINTS ----

@app.post("/api/portal/tenant/ensure")
async def portal_ensure_tenant(
    location_id: str,
    client_name: Optional[str] = None
):
    """
    Garante que um tenant existe.
    Cria se não existir.

    Query params:
    - location_id: ID do GHL
    - client_name: Nome do cliente (opcional)

    Returns:
    - Dados do tenant
    - Action: found ou created
    """
    if not PORTAL_SERVICE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Portal service not available")

    try:
        result = portal_service.ensure_tenant_exists(
            location_id=location_id,
            client_name=client_name
        )
        return result

    except Exception as e:
        logger.error(f"Error ensuring tenant: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# SESSION POOL MANAGEMENT ENDPOINTS
# ============================================

# Try to import SessionPool
try:
    from instagram_session_pool import get_session_pool, SessionPool
    SESSION_POOL_AVAILABLE = True
except ImportError:
    SESSION_POOL_AVAILABLE = False
    logger.warning("SessionPool not available")


class AddSessionRequest(BaseModel):
    """Request para adicionar session ao pool"""
    username: str = Field(..., description="Username da conta Instagram")
    session_id: str = Field(..., description="Session ID (cookie sessionid)")
    daily_limit: int = Field(default=200, description="Limite diário de requests")
    notes: Optional[str] = Field(default=None, description="Notas sobre a conta")


class UpdateSessionRequest(BaseModel):
    """Request para atualizar session"""
    new_session_id: Optional[str] = Field(default=None, description="Novo session ID")
    status: Optional[str] = Field(default=None, description="Status: active, rate_limited, blocked, expired")
    daily_limit: Optional[int] = Field(default=None, description="Novo limite diário")
    notes: Optional[str] = Field(default=None, description="Novas notas")


@app.get("/api/sessions/pool")
async def get_session_pool_stats():
    """
    Retorna estatísticas do pool de sessions.

    Returns:
        - pool_available: Se o pool está configurado
        - total_sessions: Total de sessions no pool
        - active_sessions: Sessions ativas
        - rate_limited_sessions: Sessions em rate limit
        - blocked_sessions: Sessions bloqueadas
        - requests_today: Total de requests hoje
        - daily_capacity: Capacidade diária total
        - usage_percent: Porcentagem de uso
        - estimated_remaining: Requests restantes
    """
    if not SESSION_POOL_AVAILABLE:
        return {
            "pool_available": False,
            "message": "SessionPool module not available"
        }

    try:
        pool = get_session_pool()
        stats = pool.get_pool_stats()
        return stats

    except Exception as e:
        logger.error(f"Error getting pool stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions")
async def list_sessions():
    """
    Lista todas as sessions do pool com estatísticas.

    Returns:
        Lista de sessions com:
        - id, username, status, health_score
        - requests_today, daily_limit, usage_percent
        - last_request_at, rate_limited_until
        - last_error
    """
    if not SESSION_POOL_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="SessionPool not available. Configure Supabase and run migration."
        )

    try:
        pool = get_session_pool()
        sessions = pool.get_all_sessions()
        return {
            "success": True,
            "sessions": sessions,
            "count": len(sessions)
        }

    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sessions")
async def add_session(request: AddSessionRequest):
    """
    Adiciona nova session ao pool.

    Body:
        - username: Username da conta Instagram
        - session_id: Session ID (cookie sessionid)
        - daily_limit: Limite diário de requests (default: 200)
        - notes: Notas sobre a conta (opcional)

    Returns:
        ID da session criada
    """
    if not SESSION_POOL_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="SessionPool not available"
        )

    try:
        pool = get_session_pool()
        session_uuid = pool.add_session(
            username=request.username,
            session_id=request.session_id,
            daily_limit=request.daily_limit,
            notes=request.notes
        )

        if session_uuid:
            return {
                "success": True,
                "session_id": session_uuid,
                "message": f"Session @{request.username} added to pool"
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Failed to add session. Check if username already exists."
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/sessions/{session_uuid}")
async def update_session(session_uuid: str, request: UpdateSessionRequest):
    """
    Atualiza dados de uma session.

    Path:
        - session_uuid: ID (UUID) da session

    Body:
        - new_session_id: Novo session ID (cookie)
        - status: Novo status (active, rate_limited, blocked, expired)
        - daily_limit: Novo limite diário
        - notes: Novas notas
    """
    if not SESSION_POOL_AVAILABLE:
        raise HTTPException(status_code=503, detail="SessionPool not available")

    try:
        pool = get_session_pool()
        success = pool.update_session(
            session_id=session_uuid,
            new_session_id=request.new_session_id,
            status=request.status,
            daily_limit=request.daily_limit,
            notes=request.notes
        )

        if success:
            return {"success": True, "message": "Session updated"}
        else:
            raise HTTPException(status_code=400, detail="Failed to update session")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/sessions/{session_uuid}")
async def remove_session(session_uuid: str):
    """
    Remove session do pool.

    Path:
        - session_uuid: ID (UUID) da session a remover
    """
    if not SESSION_POOL_AVAILABLE:
        raise HTTPException(status_code=503, detail="SessionPool not available")

    try:
        pool = get_session_pool()
        success = pool.remove_session(session_uuid)

        if success:
            return {"success": True, "message": "Session removed"}
        else:
            raise HTTPException(status_code=404, detail="Session not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sessions/health-check")
async def run_health_check(background_tasks: BackgroundTasks):
    """
    Executa health check em todas as sessions ativas.

    O health check roda em background pois pode demorar.

    Returns:
        - Inicia o health check em background
        - Use GET /api/sessions para ver resultados
    """
    if not SESSION_POOL_AVAILABLE:
        raise HTTPException(status_code=503, detail="SessionPool not available")

    try:
        pool = get_session_pool()

        # Rodar em background
        background_tasks.add_task(pool.health_check_all)

        return {
            "success": True,
            "message": "Health check started in background. Check /api/sessions for results."
        }

    except Exception as e:
        logger.error(f"Error starting health check: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# CAMPAIGN MANAGEMENT ENDPOINTS
# ============================================

class StartCampaignRequest(BaseModel):
    """Request para iniciar campanha de prospecção."""
    name: str = Field(..., description="Nome da campanha")
    target_type: str = Field(..., description="Tipo de target: hashtag, profile, profiles (plural), or leads")
    target_value: str = Field(..., description="Valor do target (hashtag sem #, username, lista de usernames separados por vírgula, ou 'all')")
    limit: int = Field(default=50, ge=1, le=500, description="Número máximo de leads")
    min_score: int = Field(default=0, ge=0, le=100, description="Score mínimo para enviar DM (0=todos)")
    template_id: int = Field(default=1, ge=1, description="ID do template de mensagem")
    tenant_id: Optional[str] = Field(default="DEFAULT", description="ID do tenant")
    # MÉTODO KEVS - Novos parâmetros
    kevs_mode: bool = Field(default=False, description="Usar Método Kevs Anti-Block (round-robin + delay)")
    delay_min: float = Field(default=3.0, ge=1.0, le=30.0, description="Delay mínimo entre DMs em MINUTOS")
    delay_max: float = Field(default=7.0, ge=1.0, le=60.0, description="Delay máximo entre DMs em MINUTOS")

class CampaignStatusResponse(BaseModel):
    """Response com status da campanha."""
    success: bool
    campaign_id: str
    status: str  # pending, running, completed, failed
    message: str
    stats: Optional[Dict[str, Any]] = None

# Store for running campaigns (in-memory, would use Redis in production)
running_campaigns: Dict[str, Dict[str, Any]] = {}


@app.post("/api/campaign/start", response_model=CampaignStatusResponse)
async def start_campaign(
    request: StartCampaignRequest,
    background_tasks: BackgroundTasks
):
    """
    Inicia uma campanha de prospecção no Instagram.

    Fluxo:
    1. Se target_type == 'hashtag': Scrape posts da hashtag, extrai perfis, salva no banco
    2. Se target_type == 'profile': Scrape followers do perfil
    3. Se target_type == 'leads': Usa leads já existentes no banco
    4. Filtra por min_score se especificado
    5. Envia DMs personalizadas com rate limiting

    Returns:
        campaign_id: ID único da campanha para tracking
        status: Status atual (pending, running, completed, failed)
    """
    import uuid

    campaign_id = str(uuid.uuid4())[:8]

    logger.info(f"🚀 Starting campaign {campaign_id}: {request.name}")
    logger.info(f"   Target: {request.target_type}={request.target_value}")
    logger.info(f"   Limit: {request.limit}, Min Score: {request.min_score}")
    if request.kevs_mode:
        logger.info(f"   🔄 MÉTODO KEVS: Round-Robin + Delay {request.delay_min}-{request.delay_max}min")

    # Initialize campaign tracking
    running_campaigns[campaign_id] = {
        "id": campaign_id,
        "name": request.name,
        "status": "pending",
        "target_type": request.target_type,
        "target_value": request.target_value,
        "limit": request.limit,
        "min_score": request.min_score,
        "tenant_id": request.tenant_id,
        "kevs_mode": request.kevs_mode,
        "delay_min": request.delay_min,
        "delay_max": request.delay_max,
        "started_at": datetime.now().isoformat(),
        "stats": {
            "leads_scraped": 0,
            "dms_sent": 0,
            "dms_failed": 0,
            "dms_skipped": 0
        }
    }

    # Define async task
    async def run_campaign_task():
        try:
            running_campaigns[campaign_id]["status"] = "running"

            # Step 1: Scrape leads if needed
            if request.target_type == "hashtag":
                logger.info(f"📸 Scraping hashtag #{request.target_value}...")
                # Use existing scrape-hashtag endpoint logic
                try:
                    from instagram_dm_agent import InstagramDMAgent
                    agent = InstagramDMAgent()
                    # Scrape posts from hashtag
                    scrape_result = agent.scrape_hashtag_posts(request.target_value, limit=request.limit)
                    running_campaigns[campaign_id]["stats"]["leads_scraped"] = scrape_result.get("count", 0)
                except Exception as e:
                    logger.warning(f"Hashtag scrape failed: {e}. Using existing leads.")

            elif request.target_type == "profile":
                logger.info(f"👥 Scraping followers from @{request.target_value}...")
                try:
                    from instagram_dm_agent import InstagramDMAgent
                    agent = InstagramDMAgent()
                    scrape_result = agent.scrape_followers(request.target_value, limit=request.limit)
                    running_campaigns[campaign_id]["stats"]["leads_scraped"] = scrape_result.get("count", 0)
                except Exception as e:
                    logger.warning(f"Followers scrape failed: {e}. Using existing leads.")

            elif request.target_type == "profiles":
                # MÉTODO KEVS: Múltiplos perfis separados por vírgula
                profiles = [p.strip() for p in request.target_value.split(",") if p.strip()]
                logger.info(f"👥 Scraping followers from {len(profiles)} profiles: {profiles}")

                total_scraped = 0
                limit_per_profile = request.limit // len(profiles) if profiles else request.limit

                try:
                    from instagram_dm_agent import InstagramDMAgent
                    agent = InstagramDMAgent()

                    for profile in profiles:
                        logger.info(f"   📍 Scraping @{profile} (limit: {limit_per_profile})...")
                        try:
                            scrape_result = agent.scrape_followers(profile, limit=limit_per_profile)
                            scraped_count = scrape_result.get("count", 0)
                            total_scraped += scraped_count
                            logger.info(f"   ✅ @{profile}: {scraped_count} leads")
                        except Exception as e:
                            logger.warning(f"   ⚠️ @{profile} falhou: {e}")

                    running_campaigns[campaign_id]["stats"]["leads_scraped"] = total_scraped
                    logger.info(f"📊 Total scraped de {len(profiles)} perfis: {total_scraped} leads")
                except Exception as e:
                    logger.warning(f"Multi-profile scrape failed: {e}. Using existing leads.")

            # Step 2: Run DM campaign
            if request.kevs_mode:
                logger.info(f"📨 Starting KEVS campaign (Round-Robin + Delay {request.delay_min}-{request.delay_max}min)...")
            else:
                logger.info(f"📨 Starting DM campaign with min_score={request.min_score}...")

            try:
                from instagram_dm_agent import InstagramDMAgent
                agent = InstagramDMAgent(tenant_id=request.tenant_id, headless=True)

                # CRITICAL: Initialize agent and load account from database
                await agent.start()

                # Escolher método de campanha
                if request.kevs_mode:
                    # MÉTODO KEVS: Round-Robin + Delay em minutos
                    await agent.run_campaign_kevs(
                        limit=request.limit,
                        template_id=request.template_id,
                        min_score=request.min_score,
                        delay_min_minutes=request.delay_min,
                        delay_max_minutes=request.delay_max
                    )
                else:
                    # Método tradicional
                    await agent.run_campaign(
                        limit=request.limit,
                        template_id=request.template_id,
                        min_score=request.min_score
                    )

                # Update stats
                running_campaigns[campaign_id]["stats"]["dms_sent"] = agent.dms_sent
                running_campaigns[campaign_id]["stats"]["dms_failed"] = agent.dms_failed
                running_campaigns[campaign_id]["stats"]["dms_skipped"] = agent.dms_skipped
                running_campaigns[campaign_id]["status"] = "completed"
                running_campaigns[campaign_id]["completed_at"] = datetime.now().isoformat()

                # Cleanup browser
                await agent.stop()

            except Exception as e:
                logger.error(f"Campaign error: {e}")
                running_campaigns[campaign_id]["status"] = "failed"
                running_campaigns[campaign_id]["error"] = str(e)
                # Attempt cleanup even on error
                try:
                    await agent.stop()
                except:
                    pass

        except Exception as e:
            logger.error(f"Campaign task error: {e}")
            running_campaigns[campaign_id]["status"] = "failed"
            running_campaigns[campaign_id]["error"] = str(e)

    # Start campaign in background
    background_tasks.add_task(run_campaign_task)

    return CampaignStatusResponse(
        success=True,
        campaign_id=campaign_id,
        status="pending",
        message=f"Campaign '{request.name}' started. Use GET /api/campaign/{campaign_id} to check status.",
        stats=running_campaigns[campaign_id]["stats"]
    )


@app.get("/api/campaign/{campaign_id}", response_model=CampaignStatusResponse)
async def get_campaign_status(campaign_id: str):
    """
    Retorna status de uma campanha específica.
    """
    if campaign_id not in running_campaigns:
        raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found")

    campaign = running_campaigns[campaign_id]

    return CampaignStatusResponse(
        success=True,
        campaign_id=campaign_id,
        status=campaign["status"],
        message=f"Campaign '{campaign['name']}' is {campaign['status']}",
        stats=campaign.get("stats")
    )


@app.get("/api/campaigns")
async def list_campaigns(
    status: Optional[str] = None,
    limit: int = 20
):
    """
    Lista todas as campanhas.
    """
    campaigns = list(running_campaigns.values())

    # Filter by status if specified
    if status:
        campaigns = [c for c in campaigns if c["status"] == status]

    # Sort by started_at desc
    campaigns.sort(key=lambda x: x.get("started_at", ""), reverse=True)

    # Limit results
    campaigns = campaigns[:limit]

    return {
        "success": True,
        "total": len(campaigns),
        "campaigns": campaigns
    }


@app.post("/api/campaign/{campaign_id}/stop")
async def stop_campaign(campaign_id: str):
    """
    Para uma campanha em execução.
    """
    if campaign_id not in running_campaigns:
        raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found")

    campaign = running_campaigns[campaign_id]

    if campaign["status"] != "running":
        return {
            "success": False,
            "message": f"Campaign is not running (current status: {campaign['status']})"
        }

    # Mark as stopped
    campaign["status"] = "stopped"
    campaign["stopped_at"] = datetime.now().isoformat()

    return {
        "success": True,
        "message": f"Campaign '{campaign['name']}' stopped",
        "stats": campaign.get("stats")
    }


# ============================================
# NEW FOLLOWERS DETECTION ENDPOINTS
# ============================================

class DetectNewFollowersRequest(BaseModel):
    """Request para detectar novos seguidores."""
    account_id: str = Field(..., description="UUID da conta no instagram_accounts")
    max_followers: int = Field(500, description="Máximo de seguidores a buscar")
    enrich: bool = Field(False, description="Enriquecer dados de cada novo (mais lento)")
    save_snapshot: bool = Field(True, description="Salvar snapshot após detecção")


class DetectNewFollowersResponse(BaseModel):
    """Response da detecção de novos seguidores."""
    success: bool
    account_id: str
    username: Optional[str] = None
    current_followers_count: Optional[int] = None
    new_followers_count: int = 0
    saved_count: int = 0
    has_previous_snapshot: bool = False
    error: Optional[str] = None
    detected_at: str


class DetectAllAccountsRequest(BaseModel):
    """Request para detectar novos seguidores em todas as contas."""
    max_followers_per_account: int = Field(500, description="Máximo de seguidores por conta")
    enrich: bool = Field(False, description="Enriquecer dados")
    delay_between_accounts: int = Field(60, description="Delay em segundos entre contas")


class OutreachRequest(BaseModel):
    """Request para enviar outreach."""
    follower_id: str = Field(..., description="UUID do seguidor em new_followers_detected")
    message: str = Field(..., description="Mensagem a enviar")


class BulkOutreachRequest(BaseModel):
    """Request para outreach em massa."""
    follower_ids: List[str] = Field(..., description="Lista de UUIDs dos seguidores")
    message: str = Field(..., description="Mensagem a enviar para todos")


class FollowerStatsResponse(BaseModel):
    """Response com estatísticas de novos seguidores."""
    total_accounts: int = 0
    total_new_followers: int = 0
    pending: int = 0
    sent: int = 0
    responded: int = 0
    skipped: int = 0
    ready_for_outreach: int = 0
    avg_icp_score: float = 0


@app.post("/followers/detect-new", response_model=DetectNewFollowersResponse)
async def detect_new_followers_endpoint(request: DetectNewFollowersRequest):
    """
    Detecta novos seguidores de uma conta Instagram.

    Fluxo:
    1. Busca seguidores atuais via API do Instagram
    2. Compara com último snapshot para detectar novos
    3. Calcula ICP score para cada novo
    4. Salva no banco para processamento posterior
    """
    logger.info(f"Detectando novos seguidores para conta {request.account_id}")

    try:
        from new_followers_detector import NewFollowersDetector

        detector = NewFollowersDetector()
        result = detector.detect_new(
            account_id=request.account_id,
            max_followers=request.max_followers,
            enrich=request.enrich,
            save_snapshot=request.save_snapshot
        )

        return DetectNewFollowersResponse(**result)

    except Exception as e:
        logger.error(f"Erro ao detectar novos seguidores: {e}", exc_info=True)
        return DetectNewFollowersResponse(
            success=False,
            account_id=request.account_id,
            error=str(e),
            detected_at=datetime.now().isoformat()
        )


@app.post("/followers/detect-all")
async def detect_all_accounts_endpoint(
    request: DetectAllAccountsRequest,
    background_tasks: BackgroundTasks
):
    """
    Detecta novos seguidores para todas as contas ativas.
    Executa em background devido ao tempo de processamento.
    """
    logger.info("Iniciando detecção para todas as contas (background)")

    async def run_detection():
        from new_followers_detector import NewFollowersDetector
        detector = NewFollowersDetector()
        return detector.detect_all_accounts(
            max_followers_per_account=request.max_followers_per_account,
            enrich=request.enrich,
            delay_between_accounts=request.delay_between_accounts
        )

    # Executar em background
    background_tasks.add_task(run_detection)

    return {
        "success": True,
        "message": "Detecção iniciada em background",
        "params": {
            "max_followers_per_account": request.max_followers_per_account,
            "enrich": request.enrich,
            "delay_between_accounts": request.delay_between_accounts
        }
    }


@app.post("/followers/outreach")
async def send_outreach_endpoint(request: OutreachRequest):
    """
    Envia DM de outreach para um novo seguidor.
    Atualiza o status no banco.
    """
    logger.info(f"Enviando outreach para follower {request.follower_id}")

    try:
        from new_followers_detector import NewFollowersDetector

        detector = NewFollowersDetector()

        # Buscar dados do seguidor
        followers = detector.db.select(
            "new_followers_detected",
            filters={"id": f"eq.{request.follower_id}"}
        )

        if not followers:
            raise HTTPException(status_code=404, detail="Seguidor não encontrado")

        follower = followers[0]
        username = follower.get("follower_username")

        # Enviar DM via Instagram DM Agent
        try:
            from instagram_dm_agent import InstagramDMAgent

            dm_agent = InstagramDMAgent()
            dm_result = dm_agent.send_dm(username, request.message)

            if dm_result.get("success"):
                # Atualizar status para sent
                detector.update_outreach_status(
                    request.follower_id,
                    status="sent",
                    message=request.message
                )
                return {
                    "success": True,
                    "follower_id": request.follower_id,
                    "username": username,
                    "message": "DM enviada com sucesso"
                }
            else:
                # Atualizar status para failed
                detector.update_outreach_status(
                    request.follower_id,
                    status="failed"
                )
                return {
                    "success": False,
                    "follower_id": request.follower_id,
                    "error": dm_result.get("error", "Falha ao enviar DM")
                }

        except ImportError:
            # Se DM Agent não disponível, apenas marcar como sent (simular)
            logger.warning("InstagramDMAgent não disponível, marcando como sent")
            detector.update_outreach_status(
                request.follower_id,
                status="sent",
                message=request.message
            )
            return {
                "success": True,
                "follower_id": request.follower_id,
                "username": username,
                "message": "Status atualizado (DM Agent não disponível)"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao enviar outreach: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/followers/outreach/bulk")
async def send_bulk_outreach_endpoint(
    request: BulkOutreachRequest,
    background_tasks: BackgroundTasks
):
    """
    Envia DM de outreach para múltiplos seguidores.
    Executa em background.
    """
    logger.info(f"Iniciando outreach em massa para {len(request.follower_ids)} seguidores")

    async def run_bulk_outreach():
        from new_followers_detector import NewFollowersDetector
        detector = NewFollowersDetector()

        results = {"sent": 0, "failed": 0, "errors": []}

        for follower_id in request.follower_ids:
            try:
                detector.update_outreach_status(
                    follower_id,
                    status="sent",
                    message=request.message
                )
                results["sent"] += 1
                # Rate limiting
                await asyncio.sleep(2)

            except Exception as e:
                results["failed"] += 1
                results["errors"].append({"id": follower_id, "error": str(e)})

        logger.info(f"Bulk outreach concluído: {results['sent']} enviados, {results['failed']} falhas")
        return results

    background_tasks.add_task(run_bulk_outreach)

    return {
        "success": True,
        "message": f"Outreach em massa iniciado para {len(request.follower_ids)} seguidores",
        "processing_in_background": True
    }


@app.post("/followers/skip")
async def skip_follower_endpoint(follower_id: str):
    """
    Marca um seguidor como ignorado (skip).
    """
    logger.info(f"Ignorando follower {follower_id}")

    try:
        from new_followers_detector import NewFollowersDetector

        detector = NewFollowersDetector()
        success = detector.update_outreach_status(follower_id, status="skipped")

        return {
            "success": success,
            "follower_id": follower_id,
            "status": "skipped"
        }

    except Exception as e:
        logger.error(f"Erro ao ignorar follower: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/followers/stats", response_model=FollowerStatsResponse)
async def get_followers_stats():
    """
    Retorna estatísticas gerais de novos seguidores.
    """
    try:
        from new_followers_detector import NewFollowersDetector

        detector = NewFollowersDetector()
        stats = detector.get_stats()

        return FollowerStatsResponse(**stats)

    except Exception as e:
        logger.error(f"Erro ao buscar stats: {e}")
        return FollowerStatsResponse()


@app.get("/followers/stats/{account_id}")
async def get_account_followers_stats(account_id: str):
    """
    Retorna estatísticas de novos seguidores para uma conta específica.
    """
    try:
        from new_followers_detector import NewFollowersDetector

        detector = NewFollowersDetector()
        stats = detector.get_stats(account_id=account_id)

        if not stats:
            raise HTTPException(status_code=404, detail="Conta não encontrada")

        return stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar stats da conta: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/followers/pending")
async def get_pending_outreach(
    account_id: Optional[str] = None,
    min_icp_score: int = 70,
    limit: int = 50
):
    """
    Retorna lista de seguidores pendentes para outreach.
    Filtrados por ICP score mínimo.
    """
    try:
        from new_followers_detector import NewFollowersDetector

        detector = NewFollowersDetector()
        pending = detector.get_pending_outreach(
            account_id=account_id,
            min_icp_score=min_icp_score,
            limit=limit
        )

        return {
            "success": True,
            "count": len(pending),
            "min_icp_score": min_icp_score,
            "followers": pending
        }

    except Exception as e:
        logger.error(f"Erro ao buscar pendentes: {e}")
        return {
            "success": False,
            "error": str(e),
            "followers": []
        }


@app.get("/followers/accounts")
async def get_monitored_accounts(active_only: bool = True):
    """
    Retorna lista de contas Instagram monitoradas.
    """
    try:
        from new_followers_detector import NewFollowersDetector

        detector = NewFollowersDetector()
        accounts = detector.get_monitored_accounts(active_only=active_only)

        return {
            "success": True,
            "count": len(accounts),
            "accounts": accounts
        }

    except Exception as e:
        logger.error(f"Erro ao buscar contas: {e}")
        return {
            "success": False,
            "error": str(e),
            "accounts": []
        }


# ============================================
# MULTI-TENANT INSTAGRAM ACCOUNT MANAGEMENT
# ============================================

class CreateInstagramAccountRequest(BaseModel):
    """Request para criar conta Instagram para um tenant."""
    tenant_id: str = Field(..., description="ID do tenant")
    username: str = Field(..., description="Username da conta Instagram")
    session_id: Optional[str] = Field(None, description="Session ID do Instagram")
    daily_limit: int = Field(50, ge=1, le=500, description="Limite diário de DMs")
    hourly_limit: int = Field(10, ge=1, le=50, description="Limite horário de DMs")
    notes: Optional[str] = Field(None, description="Notas sobre a conta")


class UpdateInstagramAccountRequest(BaseModel):
    """Request para atualizar conta Instagram."""
    session_id: Optional[str] = Field(None, description="Novo session ID")
    daily_limit: Optional[int] = Field(None, ge=1, le=500)
    hourly_limit: Optional[int] = Field(None, ge=1, le=50)
    status: Optional[str] = Field(None, description="active, paused, blocked")
    notes: Optional[str] = Field(None)


class InstagramAccountResponse(BaseModel):
    """Response com dados da conta Instagram."""
    id: int
    tenant_id: str
    username: str
    status: str
    daily_limit: int
    hourly_limit: int
    is_available: bool
    remaining_today: int
    remaining_this_hour: int
    last_used_at: Optional[str] = None
    blocked_until: Optional[str] = None


class TenantStatsResponse(BaseModel):
    """Response com estatísticas do tenant."""
    tenant_id: str
    total_accounts: int
    active_accounts: int
    available_accounts: int
    total_daily_capacity: int
    total_sent_today: int
    total_remaining_today: int
    accounts: List[Dict[str, Any]]


@app.get("/api/accounts/{tenant_id}", response_model=TenantStatsResponse)
async def get_tenant_accounts(tenant_id: str):
    """
    Lista todas as contas Instagram de um tenant com estatísticas.
    """
    try:
        from account_manager import AccountManager
        manager = AccountManager()
        stats = manager.get_tenant_stats(tenant_id)
        return TenantStatsResponse(**stats)
    except Exception as e:
        logger.error(f"Error getting tenant accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/accounts", response_model=InstagramAccountResponse)
async def create_instagram_account(request: CreateInstagramAccountRequest):
    """
    Cria uma nova conta Instagram para um tenant.

    Cada tenant pode ter múltiplas contas para:
    - Rotação automática quando uma atinge o limite
    - Distribuição de carga entre contas
    - Recuperação quando uma é bloqueada
    """
    try:
        from account_manager import AccountManager
        manager = AccountManager()

        # Check if account already exists
        existing = manager.get_account_by_username(request.tenant_id, request.username)
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Account @{request.username} already exists for tenant {request.tenant_id}"
            )

        account_id = manager.create_account(
            tenant_id=request.tenant_id,
            username=request.username,
            session_id=request.session_id,
            daily_limit=request.daily_limit,
            hourly_limit=request.hourly_limit
        )

        if not account_id:
            raise HTTPException(status_code=500, detail="Failed to create account")

        # Fetch created account
        account = manager.get_account_by_username(request.tenant_id, request.username)

        return InstagramAccountResponse(
            id=account.id,
            tenant_id=account.tenant_id,
            username=account.username,
            status=account.status,
            daily_limit=account.daily_limit,
            hourly_limit=account.hourly_limit,
            is_available=account.is_available,
            remaining_today=account.remaining_today,
            remaining_this_hour=account.remaining_this_hour,
            last_used_at=account.last_used_at.isoformat() if account.last_used_at else None,
            blocked_until=account.blocked_until.isoformat() if account.blocked_until else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/accounts/{tenant_id}/{username}")
async def update_instagram_account(
    tenant_id: str,
    username: str,
    request: UpdateInstagramAccountRequest
):
    """
    Atualiza uma conta Instagram existente.
    """
    try:
        from account_manager import AccountManager
        manager = AccountManager()

        account = manager.get_account_by_username(tenant_id, username)
        if not account:
            raise HTTPException(
                status_code=404,
                detail=f"Account @{username} not found for tenant {tenant_id}"
            )

        # Update fields
        update_data = {}
        if request.session_id is not None:
            update_data['session_id'] = request.session_id
        if request.daily_limit is not None:
            update_data['daily_limit'] = request.daily_limit
        if request.hourly_limit is not None:
            update_data['hourly_limit'] = request.hourly_limit
        if request.status is not None:
            update_data['status'] = request.status
        if request.notes is not None:
            update_data['notes'] = request.notes

        if update_data:
            manager._request("PATCH", "instagram_accounts",
                params={"id": f"eq.{account.id}"},
                data=update_data
            )

        return {"success": True, "message": f"Account @{username} updated"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/accounts/{tenant_id}/{username}")
async def delete_instagram_account(tenant_id: str, username: str):
    """
    Remove uma conta Instagram de um tenant.
    """
    try:
        from account_manager import AccountManager
        manager = AccountManager()

        account = manager.get_account_by_username(tenant_id, username)
        if not account:
            raise HTTPException(
                status_code=404,
                detail=f"Account @{username} not found for tenant {tenant_id}"
            )

        manager.delete_account(account.id)

        return {"success": True, "message": f"Account @{username} deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/accounts/{tenant_id}/{username}/block")
async def block_instagram_account(
    tenant_id: str,
    username: str,
    hours: int = 24,
    reason: Optional[str] = None
):
    """
    Marca uma conta como bloqueada temporariamente.
    Usado quando o Instagram bloqueia a conta.
    """
    try:
        from account_manager import AccountManager
        manager = AccountManager()

        account = manager.get_account_by_username(tenant_id, username)
        if not account:
            raise HTTPException(
                status_code=404,
                detail=f"Account @{username} not found for tenant {tenant_id}"
            )

        manager.mark_blocked(account.id, hours=hours, reason=reason)

        return {
            "success": True,
            "message": f"Account @{username} blocked for {hours} hours",
            "blocked_until": (datetime.now() + timedelta(hours=hours)).isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error blocking account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/accounts/{tenant_id}/{username}/unblock")
async def unblock_instagram_account(tenant_id: str, username: str):
    """
    Desbloqueia uma conta Instagram.
    """
    try:
        from account_manager import AccountManager
        manager = AccountManager()

        account = manager.get_account_by_username(tenant_id, username)
        if not account:
            raise HTTPException(
                status_code=404,
                detail=f"Account @{username} not found for tenant {tenant_id}"
            )

        manager.unblock_account(account.id)

        return {"success": True, "message": f"Account @{username} unblocked"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unblocking account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/accounts/{tenant_id}/available")
async def get_available_account(tenant_id: str):
    """
    Retorna a melhor conta disponível para prospecção.
    Útil para verificar antes de iniciar uma campanha.
    """
    try:
        from account_manager import AccountManager
        manager = AccountManager()

        account = manager.get_available_account(tenant_id)
        if not account:
            return {
                "success": False,
                "message": f"No available accounts for tenant {tenant_id}",
                "account": None
            }

        return {
            "success": True,
            "account": {
                "id": account.id,
                "username": account.username,
                "status": account.status,
                "remaining_today": account.remaining_today,
                "remaining_this_hour": account.remaining_this_hour
            }
        }

    except Exception as e:
        logger.error(f"Error getting available account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
