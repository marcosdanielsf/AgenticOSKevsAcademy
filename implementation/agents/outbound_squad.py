#!/usr/bin/env python3
"""
OUTBOUND SQUAD
==============
Agents for active lead hunting (busca ativa).

Agents:
1. LeadDiscoveryAgent - Find leads from various sources
2. ProfileAnalyzerAgent - Analyze Instagram profiles
3. LeadQualifierAgent - Score and qualify leads
4. MessageComposerAgent - Create personalized messages
5. OutreachExecutorAgent - Send DMs
"""

import os
import sys
import json
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from .base_agent import BaseAgent, Task, AgentCapability


# ============================================
# LEAD DISCOVERY AGENT
# ============================================

class LeadDiscoveryAgent(BaseAgent):
    """
    Finds leads from multiple sources:
    - Post likers
    - Post commenters
    - Followers of accounts
    - Hashtag explorers
    - Competitor followers
    """

    def __init__(self):
        super().__init__(
            name="LeadDiscovery",
            description="Discovers leads from various Instagram sources"
        )

        self.register_capability(AgentCapability(
            name="lead_discovery",
            description="Find leads from Instagram",
            task_types=[
                "scrape_likers",
                "scrape_commenters",
                "scrape_followers",
                "scrape_hashtag",
                "scrape_competitors"
            ],
            requires_browser=True
        ))

    async def _on_initialize(self):
        self.logger.info("LeadDiscovery: Initializing scrapers...")

    async def execute_task(self, task: Task) -> Any:
        task_type = task.task_type
        payload = task.payload

        if task_type == "scrape_likers":
            return await self._scrape_likers(
                post_url=payload.get("post_url"),
                limit=payload.get("limit", 200)
            )

        elif task_type == "scrape_commenters":
            return await self._scrape_commenters(
                post_url=payload.get("post_url"),
                limit=payload.get("limit", 100)
            )

        elif task_type == "scrape_followers":
            return await self._scrape_followers(
                username=payload.get("username"),
                limit=payload.get("limit", 500)
            )

        raise ValueError(f"Unknown task type: {task_type}")

    async def _scrape_likers(self, post_url: str, limit: int) -> Dict:
        """Scrape users who liked a post"""
        try:
            from instagram_post_likers_scraper import PostLikersScraper

            scraper = PostLikersScraper(headless=True)
            await scraper.start()

            if not await scraper.verify_login():
                return {"success": False, "error": "Not logged in"}

            likers = await scraper.scrape_likers(post_url, limit=limit)
            inserted = await scraper.save_to_supabase(likers)

            await scraper.stop()

            return {
                "success": True,
                "source": "post_likers",
                "total_found": len(likers),
                "inserted": inserted,
                "post_url": post_url
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _scrape_commenters(self, post_url: str, limit: int) -> Dict:
        """Scrape users who commented on a post"""
        try:
            from instagram_post_commenters_scraper import PostCommentersScraper

            scraper = PostCommentersScraper(headless=True)
            await scraper.start()

            if not await scraper.verify_login():
                return {"success": False, "error": "Not logged in"}

            commenters = await scraper.scrape_commenters(post_url, limit=limit)
            inserted = await scraper.save_to_supabase(commenters)

            await scraper.stop()

            return {
                "success": True,
                "source": "post_commenters",
                "total_found": len(commenters),
                "inserted": inserted,
                "post_url": post_url
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _scrape_followers(self, username: str, limit: int) -> Dict:
        """Scrape followers of an account"""
        try:
            from instagram_followers_downloader import InstagramFollowersScraper

            scraper = InstagramFollowersScraper(headless=True)
            await scraper.start()

            if not await scraper.verify_login():
                return {"success": False, "error": "Not logged in"}

            followers = await scraper.scrape_followers(username, limit=limit)

            await scraper.stop()

            return {
                "success": True,
                "source": "followers",
                "total_found": len(followers),
                "target_account": username
            }

        except Exception as e:
            return {"success": False, "error": str(e)}


# ============================================
# PROFILE ANALYZER AGENT
# ============================================

class ProfileAnalyzerAgent(BaseAgent):
    """
    Analyzes Instagram profiles using:
    - Gemini Vision (screenshot + AI)
    - Meta tags fallback
    - Posts analysis
    """

    def __init__(self):
        super().__init__(
            name="ProfileAnalyzer",
            description="Analyzes Instagram profiles with AI"
        )

        self.register_capability(AgentCapability(
            name="profile_analysis",
            description="Analyze Instagram profiles",
            task_types=["scrape_profile", "analyze_posts"],
            requires_browser=True,
            requires_api_key="GEMINI_API_KEY"
        ))

        self._browser_manager = None

    async def _on_initialize(self):
        self.logger.info("ProfileAnalyzer: Ready with Gemini Vision")

    async def execute_task(self, task: Task) -> Any:
        task_type = task.task_type
        payload = task.payload

        if task_type == "scrape_profile":
            return await self._scrape_profile(
                username=payload.get("username")
            )

        raise ValueError(f"Unknown task type: {task_type}")

    async def _scrape_profile(self, username: str) -> Dict:
        """Scrape and analyze a profile"""
        try:
            from playwright.async_api import async_playwright

            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(headless=True)

            # Load session
            context_options = {'viewport': {'width': 1280, 'height': 800}}

            session_path = Path(__file__).parent.parent.parent / "sessions" / "instagram_session.json"
            if session_path.exists():
                storage_state = json.loads(session_path.read_text())
                context_options['storage_state'] = storage_state

            context = await browser.new_context(**context_options)
            page = await context.new_page()

            # Use Gemini scraper
            from instagram_profile_scraper_gemini import InstagramProfileScraperGemini

            scraper = InstagramProfileScraperGemini(page)
            profile = await scraper.scrape_profile(username)

            await browser.close()
            await playwright.stop()

            if profile.scrape_success:
                return {
                    "success": True,
                    "username": profile.username,
                    "full_name": profile.full_name,
                    "bio": profile.bio,
                    "followers_count": profile.followers_count,
                    "following_count": profile.following_count,
                    "posts_count": profile.posts_count,
                    "is_verified": profile.is_verified,
                    "is_private": profile.is_private,
                    "category": profile.category,
                    "extraction_method": profile.extraction_method
                }
            else:
                return {
                    "success": False,
                    "username": username,
                    "error": profile.error_message
                }

        except Exception as e:
            return {"success": False, "username": username, "error": str(e)}


# ============================================
# LEAD QUALIFIER AGENT
# ============================================

class LeadQualifierAgent(BaseAgent):
    """
    Qualifies leads based on:
    - ICP match (Ideal Customer Profile)
    - Profile signals (followers, bio keywords)
    - Engagement patterns
    - Priority routing (HOT/WARM/COLD)
    """

    def __init__(self, config: Dict = None):
        super().__init__(
            name="LeadQualifier",
            description="Scores and qualifies leads based on ICP"
        )

        self.config = config or {}

        # Default ICP scoring weights
        self.weights = self.config.get("weights", {
            "followers": 0.2,
            "bio_keywords": 0.3,
            "is_business": 0.2,
            "engagement": 0.15,
            "verified": 0.15
        })

        # Business keywords (can be customized per tenant)
        self.business_keywords = self.config.get("business_keywords", [
            "ceo", "founder", "empreendedor", "empresa", "negócio",
            "digital", "marketing", "mentor", "coach", "consultor",
            "agência", "gestor", "diretor", "expert"
        ])

        self.register_capability(AgentCapability(
            name="lead_qualification",
            description="Score and qualify leads",
            task_types=["qualify_lead", "batch_qualify", "update_icp"]
        ))

    async def _on_initialize(self):
        self.logger.info(f"LeadQualifier: Ready with {len(self.business_keywords)} keywords")

    async def execute_task(self, task: Task) -> Any:
        task_type = task.task_type
        payload = task.payload

        if task_type == "qualify_lead":
            return await self._qualify_lead(
                username=payload.get("username"),
                profile=payload.get("profile", {}),
                tenant_id=payload.get("tenant_id")
            )

        elif task_type == "batch_qualify":
            return await self._batch_qualify(
                leads=payload.get("leads", [])
            )

        raise ValueError(f"Unknown task type: {task_type}")

    async def _qualify_lead(
        self,
        username: str,
        profile: Dict,
        tenant_id: str = None
    ) -> Dict:
        """Qualify a single lead"""
        score = 0
        signals = []

        # Followers score (0-20 points)
        followers = profile.get("followers_count", 0)
        if followers >= 100000:
            score += 20
            signals.append("influencer_100k+")
        elif followers >= 10000:
            score += 15
            signals.append("influencer_10k+")
        elif followers >= 1000:
            score += 10
            signals.append("engaged_1k+")
        elif followers >= 500:
            score += 5

        # Bio keywords (0-30 points)
        bio = (profile.get("bio") or "").lower()
        keyword_matches = 0
        for keyword in self.business_keywords:
            if keyword in bio:
                keyword_matches += 1
                signals.append(f"keyword:{keyword}")

        score += min(30, keyword_matches * 10)

        # Is business/creator account (0-20 points)
        if profile.get("category"):
            score += 20
            signals.append(f"category:{profile['category']}")

        # Verified (0-15 points)
        if profile.get("is_verified"):
            score += 15
            signals.append("verified")

        # Not private (0-10 points)
        if not profile.get("is_private"):
            score += 10
        else:
            signals.append("private_account")

        # Posts activity (0-5 points)
        posts = profile.get("posts_count", 0)
        if posts >= 50:
            score += 5
            signals.append("active_poster")

        # Determine classification
        score = min(100, score)

        if score >= 70:
            classification = "LEAD_HOT"
            priority = 1
        elif score >= 40:
            classification = "LEAD_WARM"
            priority = 2
        else:
            classification = "LEAD_COLD"
            priority = 3

        return {
            "success": True,
            "username": username,
            "score": score,
            "classification": classification,
            "priority": priority,
            "signals": signals,
            "qualified_at": datetime.now().isoformat()
        }

    async def _batch_qualify(self, leads: List[Dict]) -> Dict:
        """Qualify multiple leads"""
        results = []
        for lead in leads:
            result = await self._qualify_lead(
                username=lead.get("username"),
                profile=lead
            )
            results.append(result)

        # Sort by score
        results.sort(key=lambda x: x.get("score", 0), reverse=True)

        return {
            "success": True,
            "total": len(results),
            "hot": len([r for r in results if r.get("classification") == "LEAD_HOT"]),
            "warm": len([r for r in results if r.get("classification") == "LEAD_WARM"]),
            "cold": len([r for r in results if r.get("classification") == "LEAD_COLD"]),
            "leads": results
        }


# ============================================
# MESSAGE COMPOSER AGENT
# ============================================

class MessageComposerAgent(BaseAgent):
    """
    Creates hyper-personalized messages using:
    - Profile data hooks (bio, name, category)
    - Persona tone adaptation
    - Template filling
    - AI generation (Gemini)
    """

    def __init__(self, config: Dict = None):
        super().__init__(
            name="MessageComposer",
            description="Creates personalized outreach messages"
        )

        self.config = config or {}

        # Default templates (can be overridden by persona)
        self.templates = self.config.get("templates", {
            "hot": "Oi {first_name}! Vi que você trabalha com {category}. {hook} Posso te mostrar algo que pode transformar seus resultados?",
            "warm": "Oi {first_name}! {hook} Tô desenvolvendo algo que pode te interessar. Posso te contar?",
            "cold": "Oi! Vi seu perfil e curti seu trabalho. {hook} Bora trocar uma ideia?"
        })

        self.register_capability(AgentCapability(
            name="message_composition",
            description="Create personalized messages",
            task_types=["compose_message", "generate_hook", "adapt_tone"],
            requires_api_key="GEMINI_API_KEY"
        ))

    async def _on_initialize(self):
        self.logger.info("MessageComposer: Ready with templates")

    async def execute_task(self, task: Task) -> Any:
        task_type = task.task_type
        payload = task.payload

        if task_type == "compose_message":
            return await self._compose_message(
                username=payload.get("username"),
                profile=payload.get("profile", {}),
                qualification=payload.get("qualification", {}),
                persona=payload.get("persona")
            )

        elif task_type == "generate_hook":
            return await self._generate_hook(
                profile=payload.get("profile", {})
            )

        raise ValueError(f"Unknown task type: {task_type}")

    async def _compose_message(
        self,
        username: str,
        profile: Dict,
        qualification: Dict,
        persona: Dict = None
    ) -> Dict:
        """Compose a personalized message"""

        # Extract first name
        full_name = profile.get("full_name", username)
        first_name = full_name.split()[0] if full_name else username

        # Get classification
        classification = qualification.get("classification", "LEAD_COLD")
        template_key = classification.replace("LEAD_", "").lower()

        # Generate hook from bio
        hook = await self._generate_hook(profile)

        # Get template (from persona or default)
        if persona and persona.get("dm_template"):
            template = persona.get("dm_template")
        else:
            template = self.templates.get(template_key, self.templates["cold"])

        # Fill template
        message = template.format(
            first_name=first_name,
            username=username,
            category=profile.get("category", "seu nicho"),
            hook=hook.get("hook", ""),
            bio=profile.get("bio", "")[:50]
        )

        return {
            "success": True,
            "username": username,
            "message": message,
            "template_used": template_key,
            "hooks_used": hook.get("hooks", []),
            "composed_at": datetime.now().isoformat()
        }

    async def _generate_hook(self, profile: Dict) -> Dict:
        """Generate personalization hook from profile"""
        bio = profile.get("bio", "")
        hooks = []

        if not bio:
            return {"hook": "", "hooks": []}

        # Try AI generation
        try:
            import google.generativeai as genai

            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-2.5-flash")

                prompt = f"""Analise esta bio do Instagram e crie UM gancho de personalização curto (máximo 15 palavras) para começar uma conversa de forma natural.

Bio: "{bio}"

Exemplo de gancho: "Vi que você manja de marketing digital"
Outro exemplo: "Curti seu foco em empreendedorismo"

Responda APENAS com o gancho, sem aspas, sem explicação."""

                response = model.generate_content(prompt)
                hook = response.text.strip().strip('"').strip("'")

                return {
                    "hook": hook,
                    "hooks": [hook],
                    "method": "gemini"
                }

        except Exception as e:
            self.logger.warning(f"Gemini hook generation failed: {e}")

        # Fallback: keyword extraction
        keywords = ["empreendedor", "marketing", "digital", "mentor", "coach", "negócio", "startup"]
        for kw in keywords:
            if kw in bio.lower():
                hooks.append(f"Vi que você é {kw}")
                break

        return {
            "hook": hooks[0] if hooks else "",
            "hooks": hooks,
            "method": "keyword_fallback"
        }


# ============================================
# OUTREACH EXECUTOR AGENT
# ============================================

class OutreachExecutorAgent(BaseAgent):
    """
    Executes outreach actions:
    - Send DMs with human-like behavior
    - Rate limiting
    - Session management
    - Error recovery
    """

    def __init__(self, config: Dict = None):
        super().__init__(
            name="OutreachExecutor",
            description="Sends DMs with human-like behavior"
        )

        self.config = config or {}

        # Rate limits
        self.daily_limit = self.config.get("daily_limit", 50)
        self.hourly_limit = self.config.get("hourly_limit", 10)
        self.min_delay_seconds = self.config.get("min_delay", 30)
        self.max_delay_seconds = self.config.get("max_delay", 120)

        # Counters
        self._daily_count = 0
        self._hourly_count = 0
        self._last_reset_hour = datetime.now().hour
        self._last_reset_day = datetime.now().date()

        self.register_capability(AgentCapability(
            name="outreach_execution",
            description="Send DMs and manage outreach",
            task_types=["send_dm", "check_limits", "reset_counters"],
            requires_browser=True,
            rate_limit_per_minute=2
        ))

    async def _on_initialize(self):
        self.logger.info(f"OutreachExecutor: Limits {self.hourly_limit}/hr, {self.daily_limit}/day")

    async def execute_task(self, task: Task) -> Any:
        task_type = task.task_type
        payload = task.payload

        if task_type == "send_dm":
            return await self._send_dm(
                username=payload.get("username"),
                message=payload.get("message"),
                tenant_id=payload.get("tenant_id")
            )

        elif task_type == "check_limits":
            return self._check_limits()

        raise ValueError(f"Unknown task type: {task_type}")

    def _check_limits(self) -> Dict:
        """Check current rate limits"""
        now = datetime.now()

        # Reset hourly counter
        if now.hour != self._last_reset_hour:
            self._hourly_count = 0
            self._last_reset_hour = now.hour

        # Reset daily counter
        if now.date() != self._last_reset_day:
            self._daily_count = 0
            self._last_reset_day = now.date()

        return {
            "hourly_remaining": self.hourly_limit - self._hourly_count,
            "daily_remaining": self.daily_limit - self._daily_count,
            "can_send": (self._hourly_count < self.hourly_limit and
                        self._daily_count < self.daily_limit)
        }

    async def _send_dm(
        self,
        username: str,
        message: str,
        tenant_id: str = None
    ) -> Dict:
        """Send a DM to a user"""

        # Check limits
        limits = self._check_limits()
        if not limits["can_send"]:
            return {
                "success": False,
                "username": username,
                "error": "Rate limit reached",
                "limits": limits
            }

        try:
            from playwright.async_api import async_playwright
            import random

            # Human-like delay
            delay = random.uniform(self.min_delay_seconds, self.max_delay_seconds)
            await asyncio.sleep(delay)

            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(headless=True)

            # Load session
            context_options = {'viewport': {'width': 1280, 'height': 800}}

            session_path = Path(__file__).parent.parent.parent / "sessions" / "instagram_session.json"
            if session_path.exists():
                storage_state = json.loads(session_path.read_text())
                context_options['storage_state'] = storage_state

            context = await browser.new_context(**context_options)
            page = await context.new_page()

            # Navigate to DM
            await page.goto(
                f'https://www.instagram.com/direct/t/{username}/',
                wait_until='domcontentloaded',
                timeout=30000
            )
            await asyncio.sleep(2)

            # Find message input
            message_input = await page.wait_for_selector(
                'textarea[placeholder*="Message"], div[contenteditable="true"]',
                timeout=10000
            )

            if message_input:
                # Type with human-like speed
                for char in message:
                    await message_input.type(char, delay=random.randint(30, 80))
                    if random.random() < 0.1:  # Occasional pause
                        await asyncio.sleep(random.uniform(0.2, 0.5))

                await asyncio.sleep(0.5)

                # Send
                await page.keyboard.press('Enter')
                await asyncio.sleep(1)

                # Update counters
                self._hourly_count += 1
                self._daily_count += 1

                await browser.close()
                await playwright.stop()

                return {
                    "success": True,
                    "username": username,
                    "message_sent": message,
                    "sent_at": datetime.now().isoformat(),
                    "limits_after": self._check_limits()
                }

            await browser.close()
            await playwright.stop()

            return {
                "success": False,
                "username": username,
                "error": "Could not find message input"
            }

        except Exception as e:
            return {
                "success": False,
                "username": username,
                "error": str(e)
            }


# ============================================
# FACTORY FUNCTION
# ============================================

def create_outbound_squad(config: Dict = None) -> Dict[str, BaseAgent]:
    """Create all outbound squad agents"""
    config = config or {}

    return {
        "LeadDiscovery": LeadDiscoveryAgent(),
        "ProfileAnalyzer": ProfileAnalyzerAgent(),
        "LeadQualifier": LeadQualifierAgent(config.get("qualifier")),
        "MessageComposer": MessageComposerAgent(config.get("composer")),
        "OutreachExecutor": OutreachExecutorAgent(config.get("executor"))
    }
