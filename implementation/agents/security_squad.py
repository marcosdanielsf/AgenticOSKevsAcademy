#!/usr/bin/env python3
"""
SECURITY SQUAD
==============
Agents for security, compliance, and protection.

Agents:
1. RateLimitGuardAgent - Protect against rate limiting
2. SessionSecurityAgent - Session validation and refresh
3. AntiDetectionAgent - Avoid bot detection
4. ComplianceAgent - GDPR, privacy compliance
"""

import os
import sys
import asyncio
import random
import hashlib
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field

sys.path.insert(0, str(Path(__file__).parent.parent))

from .base_agent import BaseAgent, Task, AgentCapability


# ============================================
# RATE LIMIT GUARD AGENT
# ============================================

@dataclass
class RateLimitBucket:
    """Token bucket for rate limiting"""
    name: str
    max_tokens: int
    refill_rate: float  # tokens per second
    tokens: float = field(default=0)
    last_refill: datetime = field(default_factory=datetime.now)

    def consume(self, amount: int = 1) -> bool:
        """Try to consume tokens, return True if successful"""
        self._refill()
        if self.tokens >= amount:
            self.tokens -= amount
            return True
        return False

    def _refill(self):
        """Refill tokens based on time elapsed"""
        now = datetime.now()
        elapsed = (now - self.last_refill).total_seconds()
        self.tokens = min(self.max_tokens, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

    def wait_time(self, amount: int = 1) -> float:
        """Calculate wait time needed for tokens"""
        self._refill()
        if self.tokens >= amount:
            return 0
        needed = amount - self.tokens
        return needed / self.refill_rate


class RateLimitGuardAgent(BaseAgent):
    """
    Protects against Instagram rate limiting.

    Features:
    - Token bucket algorithm for smooth rate limiting
    - Per-action rate limits (DM, follow, like, etc.)
    - Automatic backoff on warnings
    - Daily/hourly limit tracking
    """

    def __init__(self, config: Dict = None):
        super().__init__(
            name="RateLimitGuard",
            description="Protects against rate limiting"
        )

        self.config = config or {}

        # Rate limit buckets per action type
        self.buckets: Dict[str, RateLimitBucket] = {
            "dm": RateLimitBucket(
                name="dm",
                max_tokens=10,  # Max burst
                refill_rate=10/3600  # 10 per hour
            ),
            "follow": RateLimitBucket(
                name="follow",
                max_tokens=20,
                refill_rate=50/3600  # 50 per hour
            ),
            "like": RateLimitBucket(
                name="like",
                max_tokens=50,
                refill_rate=200/3600  # 200 per hour
            ),
            "profile_view": RateLimitBucket(
                name="profile_view",
                max_tokens=100,
                refill_rate=500/3600  # 500 per hour
            ),
            "scrape": RateLimitBucket(
                name="scrape",
                max_tokens=30,
                refill_rate=100/3600  # 100 per hour
            )
        }

        # Daily limits
        self.daily_limits = {
            "dm": 50,
            "follow": 200,
            "like": 500,
            "profile_view": 1000,
            "scrape": 500
        }

        self.daily_usage: Dict[str, int] = {}
        self.last_reset_date = datetime.now().date()

        # Warning state
        self.warning_level = 0  # 0-3, increases on rate limit warnings
        self.last_warning_time: Optional[datetime] = None

        self.register_capability(AgentCapability(
            name="rate_limit_guard",
            description="Rate limiting protection",
            task_types=[
                "check_can_perform",
                "consume_quota",
                "get_wait_time",
                "report_warning",
                "get_status"
            ]
        ))

    async def _on_initialize(self):
        self.logger.info("RateLimitGuard: Initialized with adaptive limits")

    async def execute_task(self, task: Task) -> Any:
        task_type = task.task_type
        payload = task.payload

        if task_type == "check_can_perform":
            return self._check_can_perform(
                action_type=payload.get("action_type"),
                amount=payload.get("amount", 1)
            )

        elif task_type == "consume_quota":
            return self._consume_quota(
                action_type=payload.get("action_type"),
                amount=payload.get("amount", 1)
            )

        elif task_type == "get_wait_time":
            return self._get_wait_time(
                action_type=payload.get("action_type")
            )

        elif task_type == "report_warning":
            return self._report_warning(
                warning_type=payload.get("warning_type"),
                details=payload.get("details")
            )

        elif task_type == "get_status":
            return self._get_status()

        raise ValueError(f"Unknown task type: {task_type}")

    def _reset_daily_if_needed(self):
        """Reset daily counters if it's a new day"""
        today = datetime.now().date()
        if today != self.last_reset_date:
            self.daily_usage = {}
            self.last_reset_date = today
            self.warning_level = max(0, self.warning_level - 1)  # Reduce warning level
            self.logger.info("Daily limits reset")

    def _check_can_perform(self, action_type: str, amount: int = 1) -> Dict:
        """Check if action can be performed within limits"""
        self._reset_daily_if_needed()

        bucket = self.buckets.get(action_type)
        if not bucket:
            return {"can_perform": True, "reason": "Unknown action type, allowing"}

        # Check daily limit
        daily_used = self.daily_usage.get(action_type, 0)
        daily_limit = self.daily_limits.get(action_type, 1000)

        # Reduce limits based on warning level
        effective_limit = int(daily_limit * (1 - self.warning_level * 0.25))

        if daily_used + amount > effective_limit:
            return {
                "can_perform": False,
                "reason": "daily_limit_reached",
                "daily_used": daily_used,
                "daily_limit": effective_limit,
                "wait_until": "tomorrow"
            }

        # Check token bucket
        if not bucket.consume(amount):
            wait_time = bucket.wait_time(amount)
            return {
                "can_perform": False,
                "reason": "rate_limit",
                "wait_seconds": wait_time,
                "tokens_available": bucket.tokens
            }

        # Refund tokens (we only checked, didn't consume yet)
        bucket.tokens += amount

        return {
            "can_perform": True,
            "daily_remaining": effective_limit - daily_used,
            "warning_level": self.warning_level
        }

    def _consume_quota(self, action_type: str, amount: int = 1) -> Dict:
        """Consume quota for an action"""
        self._reset_daily_if_needed()

        bucket = self.buckets.get(action_type)
        if bucket:
            bucket.consume(amount)

        self.daily_usage[action_type] = self.daily_usage.get(action_type, 0) + amount

        return {
            "consumed": amount,
            "action_type": action_type,
            "daily_used": self.daily_usage[action_type]
        }

    def _get_wait_time(self, action_type: str) -> Dict:
        """Get recommended wait time before next action"""
        bucket = self.buckets.get(action_type)
        if not bucket:
            return {"wait_seconds": 0}

        base_wait = bucket.wait_time(1)

        # Add random jitter (human-like behavior)
        jitter = random.uniform(0.5, 2.0)

        # Increase wait based on warning level
        warning_multiplier = 1 + (self.warning_level * 0.5)

        total_wait = (base_wait + random.uniform(1, 3)) * jitter * warning_multiplier

        return {
            "wait_seconds": total_wait,
            "base_wait": base_wait,
            "warning_multiplier": warning_multiplier
        }

    def _report_warning(self, warning_type: str, details: str = None) -> Dict:
        """Report a rate limit warning"""
        self.warning_level = min(3, self.warning_level + 1)
        self.last_warning_time = datetime.now()

        self.logger.warning(f"Rate limit warning: {warning_type} - {details}")

        # Calculate cooldown period
        cooldown_minutes = 15 * (2 ** self.warning_level)  # 30, 60, 120, 240 minutes

        return {
            "warning_level": self.warning_level,
            "cooldown_minutes": cooldown_minutes,
            "resume_at": (datetime.now() + timedelta(minutes=cooldown_minutes)).isoformat()
        }

    def _get_status(self) -> Dict:
        """Get current rate limit status"""
        self._reset_daily_if_needed()

        return {
            "warning_level": self.warning_level,
            "daily_usage": self.daily_usage.copy(),
            "daily_limits": self.daily_limits.copy(),
            "buckets": {
                name: {
                    "tokens": bucket.tokens,
                    "max_tokens": bucket.max_tokens
                }
                for name, bucket in self.buckets.items()
            },
            "last_warning": self.last_warning_time.isoformat() if self.last_warning_time else None
        }


# ============================================
# SESSION SECURITY AGENT
# ============================================

class SessionSecurityAgent(BaseAgent):
    """
    Manages session security and validation.

    Features:
    - Session validation before actions
    - Automatic session refresh
    - Cookie rotation
    - Login state monitoring
    """

    def __init__(self, config: Dict = None):
        super().__init__(
            name="SessionSecurity",
            description="Session validation and security"
        )

        self.config = config or {}
        self._session_valid = False
        self._last_validation: Optional[datetime] = None
        self._validation_interval = timedelta(minutes=30)

        self.register_capability(AgentCapability(
            name="session_security",
            description="Session validation and refresh",
            task_types=[
                "validate_session",
                "refresh_session",
                "check_login_state",
                "rotate_cookies"
            ],
            requires_browser=True
        ))

    async def _on_initialize(self):
        self.logger.info("SessionSecurity: Initialized")

    async def execute_task(self, task: Task) -> Any:
        task_type = task.task_type
        payload = task.payload

        if task_type == "validate_session":
            return await self._validate_session()

        elif task_type == "check_login_state":
            return await self._check_login_state(
                page=payload.get("page")
            )

        raise ValueError(f"Unknown task type: {task_type}")

    async def _validate_session(self) -> Dict:
        """Validate current session is still active"""
        # Check if we need to revalidate
        if (self._last_validation and
            datetime.now() - self._last_validation < self._validation_interval and
            self._session_valid):
            return {"valid": True, "cached": True}

        try:
            from playwright.async_api import async_playwright
            import json

            sessions_dir = Path(__file__).parent.parent.parent / "sessions"
            session_file = sessions_dir / "instagram_session.json"

            if not session_file.exists():
                return {"valid": False, "error": "No session file"}

            # Quick validation - check if cookies exist and aren't expired
            session_data = json.loads(session_file.read_text())
            cookies = session_data.get("cookies", [])

            if not cookies:
                return {"valid": False, "error": "No cookies in session"}

            # Check for essential Instagram cookies
            essential_cookies = ["sessionid", "ds_user_id"]
            found_cookies = {c["name"] for c in cookies}
            missing = set(essential_cookies) - found_cookies

            if missing:
                return {"valid": False, "error": f"Missing cookies: {missing}"}

            # Check expiry
            now = datetime.now().timestamp()
            for cookie in cookies:
                if cookie["name"] == "sessionid":
                    expires = cookie.get("expires", 0)
                    if expires > 0 and expires < now:
                        return {"valid": False, "error": "Session expired"}

            self._session_valid = True
            self._last_validation = datetime.now()

            return {
                "valid": True,
                "cookies_count": len(cookies),
                "validated_at": self._last_validation.isoformat()
            }

        except Exception as e:
            self._session_valid = False
            return {"valid": False, "error": str(e)}

    async def _check_login_state(self, page=None) -> Dict:
        """Check if currently logged in on page"""
        if not page:
            return {"logged_in": False, "error": "No page provided"}

        try:
            # Multiple selectors for different languages
            login_indicators = [
                'svg[aria-label="Home"]',
                'svg[aria-label="Página inicial"]',
                'svg[aria-label="Inicio"]',
                'a[href="/direct/inbox/"]',
            ]

            for selector in login_indicators:
                element = await page.query_selector(selector)
                if element:
                    return {"logged_in": True, "indicator": selector}

            # Check URL
            url = page.url
            if "/login" in url or "/accounts/login" in url:
                return {"logged_in": False, "reason": "On login page"}

            return {"logged_in": False, "reason": "No login indicators found"}

        except Exception as e:
            return {"logged_in": False, "error": str(e)}


# ============================================
# ANTI DETECTION AGENT
# ============================================

class AntiDetectionAgent(BaseAgent):
    """
    Avoids bot detection by Instagram.

    Features:
    - Human-like behavior patterns
    - Random delays and pauses
    - Mouse movement simulation
    - Browser fingerprint randomization
    """

    def __init__(self, config: Dict = None):
        super().__init__(
            name="AntiDetection",
            description="Avoid bot detection"
        )

        self.config = config or {}

        # Behavior profiles
        self.profiles = {
            "casual": {
                "min_delay": 2,
                "max_delay": 8,
                "typing_speed": (50, 150),
                "scroll_probability": 0.3,
                "pause_probability": 0.2
            },
            "active": {
                "min_delay": 1,
                "max_delay": 4,
                "typing_speed": (30, 80),
                "scroll_probability": 0.2,
                "pause_probability": 0.1
            },
            "cautious": {
                "min_delay": 5,
                "max_delay": 15,
                "typing_speed": (80, 200),
                "scroll_probability": 0.4,
                "pause_probability": 0.3
            }
        }

        self.current_profile = "casual"

        self.register_capability(AgentCapability(
            name="anti_detection",
            description="Bot detection avoidance",
            task_types=[
                "get_random_delay",
                "simulate_human_typing",
                "simulate_scroll",
                "randomize_fingerprint",
                "set_profile"
            ]
        ))

    async def _on_initialize(self):
        self.logger.info("AntiDetection: Using 'casual' behavior profile")

    async def execute_task(self, task: Task) -> Any:
        task_type = task.task_type
        payload = task.payload

        if task_type == "get_random_delay":
            return self._get_random_delay()

        elif task_type == "simulate_human_typing":
            return await self._simulate_human_typing(
                page=payload.get("page"),
                element=payload.get("element"),
                text=payload.get("text")
            )

        elif task_type == "set_profile":
            return self._set_profile(payload.get("profile"))

        raise ValueError(f"Unknown task type: {task_type}")

    def _get_random_delay(self) -> Dict:
        """Get a random delay based on current profile"""
        profile = self.profiles[self.current_profile]

        base_delay = random.uniform(profile["min_delay"], profile["max_delay"])

        # Add occasional longer pauses (human behavior)
        if random.random() < profile["pause_probability"]:
            base_delay += random.uniform(3, 10)

        return {
            "delay_seconds": base_delay,
            "profile": self.current_profile
        }

    async def _simulate_human_typing(self, page, element, text: str) -> Dict:
        """Type text with human-like speed and errors"""
        if not page or not element or not text:
            return {"success": False, "error": "Missing parameters"}

        profile = self.profiles[self.current_profile]
        min_speed, max_speed = profile["typing_speed"]

        chars_typed = 0
        for i, char in enumerate(text):
            # Occasional typo and backspace
            if random.random() < 0.02 and i > 0:
                wrong_char = random.choice("qwertyuiopasdfghjklzxcvbnm")
                await element.type(wrong_char, delay=random.randint(min_speed, max_speed))
                await asyncio.sleep(random.uniform(0.2, 0.5))
                await page.keyboard.press("Backspace")
                await asyncio.sleep(random.uniform(0.1, 0.3))

            await element.type(char, delay=random.randint(min_speed, max_speed))
            chars_typed += 1

            # Occasional pause (thinking)
            if random.random() < 0.05:
                await asyncio.sleep(random.uniform(0.3, 1.0))

        return {"success": True, "chars_typed": chars_typed}

    def _set_profile(self, profile: str) -> Dict:
        """Set behavior profile"""
        if profile in self.profiles:
            self.current_profile = profile
            return {"success": True, "profile": profile}
        return {"success": False, "error": f"Unknown profile: {profile}"}


# ============================================
# COMPLIANCE AGENT
# ============================================

class ComplianceAgent(BaseAgent):
    """
    Ensures compliance with privacy regulations.

    Features:
    - GDPR/LGPD compliance checks
    - Consent tracking
    - Data retention policies
    - Opt-out handling
    """

    def __init__(self, config: Dict = None):
        super().__init__(
            name="Compliance",
            description="Privacy and compliance management"
        )

        self.config = config or {}

        # Opt-out list (usernames who requested to be removed)
        self._opt_outs: set = set()

        # Data retention (days)
        self.retention_days = self.config.get("retention_days", 90)

        self.register_capability(AgentCapability(
            name="compliance",
            description="Privacy compliance",
            task_types=[
                "check_can_contact",
                "record_opt_out",
                "check_data_retention",
                "anonymize_data"
            ]
        ))

    async def _on_initialize(self):
        self.logger.info(f"Compliance: Data retention = {self.retention_days} days")

    async def execute_task(self, task: Task) -> Any:
        task_type = task.task_type
        payload = task.payload

        if task_type == "check_can_contact":
            return self._check_can_contact(
                username=payload.get("username"),
                tenant_id=payload.get("tenant_id")
            )

        elif task_type == "record_opt_out":
            return self._record_opt_out(
                username=payload.get("username"),
                reason=payload.get("reason")
            )

        raise ValueError(f"Unknown task type: {task_type}")

    def _check_can_contact(self, username: str, tenant_id: str = None) -> Dict:
        """Check if user can be contacted"""
        # Check opt-out list
        if username in self._opt_outs:
            return {
                "can_contact": False,
                "reason": "User opted out"
            }

        # Additional checks could include:
        # - Frequency caps (don't contact same user too often)
        # - Minor protection (if age data available)
        # - Jurisdiction restrictions

        return {"can_contact": True}

    def _record_opt_out(self, username: str, reason: str = None) -> Dict:
        """Record user opt-out request"""
        self._opt_outs.add(username)
        self.logger.info(f"Opt-out recorded: {username} - {reason}")

        return {
            "success": True,
            "username": username,
            "opted_out_at": datetime.now().isoformat()
        }


# ============================================
# FACTORY FUNCTION
# ============================================

def create_security_squad(config: Dict = None) -> Dict[str, BaseAgent]:
    """Create all security squad agents"""
    config = config or {}

    return {
        "RateLimitGuard": RateLimitGuardAgent(config.get("rate_limit")),
        "SessionSecurity": SessionSecurityAgent(config.get("session")),
        "AntiDetection": AntiDetectionAgent(config.get("anti_detection")),
        "Compliance": ComplianceAgent(config.get("compliance"))
    }
