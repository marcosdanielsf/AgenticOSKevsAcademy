#!/usr/bin/env python3
"""
INFRASTRUCTURE SQUAD
====================
Support agents for system management.

Agents:
1. AccountManagerAgent - Multi-account management, rotation, warmup
2. AnalyticsAgent - Metrics collection, reporting
3. ErrorHandlerAgent - Error recovery, alerting, retry logic
"""

import os
import sys
import json
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import random

sys.path.insert(0, str(Path(__file__).parent.parent))

from .base_agent import BaseAgent, Task, AgentCapability
import requests


# ============================================
# SUPABASE CLIENT
# ============================================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


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

    def insert(self, table: str, data: Dict) -> bool:
        try:
            response = requests.post(
                f"{self.base_url}/{table}",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
            return True
        except:
            return False

    def query(self, table: str, params: Dict = None) -> List[Dict]:
        try:
            response = requests.get(
                f"{self.base_url}/{table}",
                headers=self.headers,
                params=params or {}
            )
            return response.json()
        except:
            return []


# ============================================
# ACCOUNT MANAGER AGENT
# ============================================

class AccountManagerAgent(BaseAgent):
    """
    Manages Instagram accounts:
    - Session storage and retrieval
    - Account rotation for rate limiting
    - Account warmup scheduling
    - Health monitoring

    Supports multi-tenant with multiple accounts per tenant.
    """

    def __init__(self, config: Dict = None):
        super().__init__(
            name="AccountManager",
            description="Manages Instagram accounts and sessions"
        )

        self.config = config or {}
        self.db = SupabaseClient()

        # Account states
        self._accounts: Dict[str, Dict] = {}  # username -> account data
        self._sessions: Dict[str, Dict] = {}  # username -> session data
        self._current_account: str = None
        self._rotation_index = 0

        # Warmup config
        self.warmup_days = self.config.get("warmup_days", 7)
        self.warmup_schedule = self.config.get("warmup_schedule", {
            1: {"dms": 5, "follows": 10},
            2: {"dms": 10, "follows": 20},
            3: {"dms": 15, "follows": 30},
            4: {"dms": 20, "follows": 40},
            5: {"dms": 30, "follows": 50},
            6: {"dms": 40, "follows": 60},
            7: {"dms": 50, "follows": 70}
        })

        self.register_capability(AgentCapability(
            name="account_management",
            description="Manage Instagram accounts and sessions",
            task_types=[
                "load_session",
                "save_session",
                "rotate_account",
                "get_current_account",
                "check_account_health",
                "start_warmup",
                "get_daily_limits"
            ]
        ))

    async def _on_initialize(self):
        self.logger.info("AccountManager: Loading accounts...")
        await self._load_accounts_from_db()

    async def _load_accounts_from_db(self):
        """Load accounts from database"""
        # For now, load from sessions directory
        sessions_dir = Path(__file__).parent.parent.parent / "sessions"

        for session_file in sessions_dir.glob("*.json"):
            username = session_file.stem.replace("instagram_session_", "").replace("instagram_session", "default")

            try:
                session_data = json.loads(session_file.read_text())
                self._sessions[username] = session_data
                self._accounts[username] = {
                    "username": username,
                    "status": "active",
                    "session_file": str(session_file),
                    "loaded_at": datetime.now().isoformat(),
                    "daily_dms_sent": 0,
                    "daily_follows": 0,
                    "warmup_day": 7  # Assume warmed up
                }
                self.logger.info(f"  Loaded account: {username}")
            except Exception as e:
                self.logger.error(f"  Failed to load {session_file}: {e}")

        if self._accounts:
            self._current_account = list(self._accounts.keys())[0]

    async def execute_task(self, task: Task) -> Any:
        task_type = task.task_type
        payload = task.payload

        if task_type == "load_session":
            return await self._load_session(
                username=payload.get("username")
            )

        elif task_type == "save_session":
            return await self._save_session(
                username=payload.get("username"),
                session_data=payload.get("session_data")
            )

        elif task_type == "rotate_account":
            return await self._rotate_account()

        elif task_type == "get_current_account":
            return self._get_current_account()

        elif task_type == "check_account_health":
            return await self._check_account_health(
                username=payload.get("username")
            )

        elif task_type == "get_daily_limits":
            return self._get_daily_limits(
                username=payload.get("username")
            )

        raise ValueError(f"Unknown task type: {task_type}")

    async def _load_session(self, username: str = None) -> Dict:
        """Load session for an account"""
        username = username or self._current_account or "default"

        if username in self._sessions:
            return {
                "success": True,
                "username": username,
                "session": self._sessions[username]
            }

        # Try to load from file
        sessions_dir = Path(__file__).parent.parent.parent / "sessions"
        session_file = sessions_dir / f"instagram_session_{username}.json"

        if not session_file.exists():
            session_file = sessions_dir / "instagram_session.json"

        if session_file.exists():
            try:
                session_data = json.loads(session_file.read_text())
                self._sessions[username] = session_data
                return {
                    "success": True,
                    "username": username,
                    "session": session_data
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        return {"success": False, "error": "Session not found"}

    async def _save_session(self, username: str, session_data: Dict) -> Dict:
        """Save session for an account"""
        sessions_dir = Path(__file__).parent.parent.parent / "sessions"
        sessions_dir.mkdir(exist_ok=True)

        session_file = sessions_dir / f"instagram_session_{username}.json"

        try:
            session_file.write_text(json.dumps(session_data, indent=2))
            self._sessions[username] = session_data

            return {
                "success": True,
                "username": username,
                "saved_to": str(session_file)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _rotate_account(self) -> Dict:
        """Rotate to next available account"""
        if not self._accounts:
            return {"success": False, "error": "No accounts available"}

        # Filter active accounts
        active = [u for u, a in self._accounts.items() if a.get("status") == "active"]

        if not active:
            return {"success": False, "error": "No active accounts"}

        # Round-robin rotation
        self._rotation_index = (self._rotation_index + 1) % len(active)
        self._current_account = active[self._rotation_index]

        return {
            "success": True,
            "previous_account": active[(self._rotation_index - 1) % len(active)],
            "current_account": self._current_account,
            "total_accounts": len(active)
        }

    def _get_current_account(self) -> Dict:
        """Get current active account"""
        if not self._current_account:
            return {"success": False, "error": "No account selected"}

        account = self._accounts.get(self._current_account, {})

        return {
            "success": True,
            "username": self._current_account,
            "status": account.get("status"),
            "daily_dms_sent": account.get("daily_dms_sent", 0),
            "daily_follows": account.get("daily_follows", 0),
            "warmup_day": account.get("warmup_day", 7)
        }

    async def _check_account_health(self, username: str = None) -> Dict:
        """Check if account is healthy"""
        username = username or self._current_account

        if username not in self._accounts:
            return {"success": False, "error": "Account not found"}

        account = self._accounts[username]

        # Simple health check - try to load the page
        try:
            from playwright.async_api import async_playwright

            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(headless=True)

            context_options = {'viewport': {'width': 1280, 'height': 800}}

            if username in self._sessions:
                context_options['storage_state'] = self._sessions[username]

            context = await browser.new_context(**context_options)
            page = await context.new_page()

            await page.goto('https://www.instagram.com/', timeout=30000)
            await asyncio.sleep(2)

            # Check for login indicators
            content = await page.content()
            is_logged_in = 'svg[aria-label="Home"]' in content or '/direct/' in content

            await browser.close()
            await playwright.stop()

            status = "healthy" if is_logged_in else "needs_login"
            account["status"] = "active" if is_logged_in else "inactive"

            return {
                "success": True,
                "username": username,
                "is_logged_in": is_logged_in,
                "status": status,
                "checked_at": datetime.now().isoformat()
            }

        except Exception as e:
            account["status"] = "error"
            return {
                "success": False,
                "username": username,
                "error": str(e),
                "status": "error"
            }

    def _get_daily_limits(self, username: str = None) -> Dict:
        """Get daily limits for account based on warmup stage"""
        username = username or self._current_account

        if username not in self._accounts:
            return {"dms": 50, "follows": 70}  # Default limits

        account = self._accounts[username]
        warmup_day = min(account.get("warmup_day", 7), 7)

        limits = self.warmup_schedule.get(warmup_day, {"dms": 50, "follows": 70})

        return {
            "username": username,
            "warmup_day": warmup_day,
            "limits": limits,
            "current_usage": {
                "dms_sent": account.get("daily_dms_sent", 0),
                "follows": account.get("daily_follows", 0)
            },
            "remaining": {
                "dms": limits["dms"] - account.get("daily_dms_sent", 0),
                "follows": limits["follows"] - account.get("daily_follows", 0)
            }
        }


# ============================================
# ANALYTICS AGENT
# ============================================

class AnalyticsAgent(BaseAgent):
    """
    Collects and reports on system metrics:
    - Lead generation stats
    - DM performance
    - Conversion tracking
    - Agent performance
    """

    def __init__(self, config: Dict = None):
        super().__init__(
            name="Analytics",
            description="Collects and reports on system metrics"
        )

        self.config = config or {}
        self.db = SupabaseClient()

        self.register_capability(AgentCapability(
            name="analytics",
            description="Collect and report metrics",
            task_types=[
                "get_daily_stats",
                "get_lead_stats",
                "get_dm_stats",
                "get_conversion_stats",
                "save_enriched_lead",
                "track_event"
            ]
        ))

    async def _on_initialize(self):
        self.logger.info("Analytics: Ready")

    async def execute_task(self, task: Task) -> Any:
        task_type = task.task_type
        payload = task.payload

        if task_type == "get_daily_stats":
            return await self._get_daily_stats(
                tenant_id=payload.get("tenant_id"),
                date=payload.get("date")
            )

        elif task_type == "get_lead_stats":
            return await self._get_lead_stats(
                tenant_id=payload.get("tenant_id")
            )

        elif task_type == "get_dm_stats":
            return await self._get_dm_stats(
                tenant_id=payload.get("tenant_id")
            )

        elif task_type == "save_enriched_lead":
            return await self._save_enriched_lead(
                lead_data=payload
            )

        elif task_type == "track_event":
            return await self._track_event(
                event_type=payload.get("event_type"),
                event_data=payload.get("event_data")
            )

        raise ValueError(f"Unknown task type: {task_type}")

    async def _get_daily_stats(self, tenant_id: str = None, date: str = None) -> Dict:
        """Get daily statistics"""
        date = date or datetime.now().strftime("%Y-%m-%d")

        # Query leads
        leads = self.db.query("agentic_instagram_leads", {
            "created_at": f"gte.{date}"
        })

        # Query DMs
        dms = self.db.query("agentic_instagram_dm_sent", {
            "sent_at": f"gte.{date}"
        })

        # Query classified leads
        classified = self.db.query("classified_leads", {
            "classified_at": f"gte.{date}"
        })

        # Calculate stats
        total_leads = len(leads)
        total_dms = len(dms)
        total_classified = len(classified)

        hot_leads = len([c for c in classified if c.get("classification") == "LEAD_HOT"])
        warm_leads = len([c for c in classified if c.get("classification") == "LEAD_WARM"])

        # Lead sources
        sources = {}
        for lead in leads:
            source = lead.get("source", "unknown")
            sources[source] = sources.get(source, 0) + 1

        return {
            "success": True,
            "date": date,
            "leads": {
                "total": total_leads,
                "by_source": sources
            },
            "dms_sent": total_dms,
            "classified": {
                "total": total_classified,
                "hot": hot_leads,
                "warm": warm_leads,
                "cold": total_classified - hot_leads - warm_leads
            },
            "conversion_rate": (hot_leads + warm_leads) / max(1, total_classified)
        }

    async def _get_lead_stats(self, tenant_id: str = None) -> Dict:
        """Get lead statistics"""
        params = {}
        if tenant_id:
            params["tenant_id"] = f"eq.{tenant_id}"

        leads = self.db.query("agentic_instagram_leads", params)

        # Group by source
        by_source = {}
        for lead in leads:
            source = lead.get("source", "unknown")
            by_source[source] = by_source.get(source, 0) + 1

        # Recent leads (last 7 days)
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        recent = [l for l in leads if l.get("created_at", "") >= week_ago]

        return {
            "success": True,
            "total_leads": len(leads),
            "by_source": by_source,
            "last_7_days": len(recent),
            "avg_per_day": len(recent) / 7
        }

    async def _get_dm_stats(self, tenant_id: str = None) -> Dict:
        """Get DM statistics"""
        params = {"order": "sent_at.desc"}
        if tenant_id:
            params["tenant_id"] = f"eq.{tenant_id}"

        dms = self.db.query("agentic_instagram_dm_sent", params)

        # Group by day
        by_day = {}
        for dm in dms:
            day = dm.get("sent_at", "")[:10]
            by_day[day] = by_day.get(day, 0) + 1

        return {
            "success": True,
            "total_dms": len(dms),
            "by_day": by_day,
            "avg_per_day": len(dms) / max(1, len(by_day))
        }

    async def _save_enriched_lead(self, lead_data: Dict) -> Dict:
        """Save enriched lead to database"""
        success = self.db.insert("agentic_instagram_leads", lead_data)

        return {
            "success": success,
            "username": lead_data.get("username")
        }

    async def _track_event(self, event_type: str, event_data: Dict) -> Dict:
        """Track an analytics event"""
        event = {
            "event_type": event_type,
            "event_data": json.dumps(event_data),
            "timestamp": datetime.now().isoformat()
        }

        # For now, just log
        self.logger.info(f"Event: {event_type} - {event_data}")

        return {"success": True, "event": event_type}


# ============================================
# ERROR HANDLER AGENT
# ============================================

class ErrorHandlerAgent(BaseAgent):
    """
    Handles errors and recovery:
    - Retry with exponential backoff
    - Alert dispatching
    - Error pattern detection
    - Automatic recovery actions
    """

    def __init__(self, config: Dict = None):
        super().__init__(
            name="ErrorHandler",
            description="Handles errors and recovery"
        )

        self.config = config or {}

        # Error tracking
        self._error_history: List[Dict] = []
        self._error_counts: Dict[str, int] = {}

        # Alert thresholds
        self.alert_threshold = self.config.get("alert_threshold", 5)
        self.critical_errors = self.config.get("critical_errors", [
            "login_failed",
            "account_blocked",
            "rate_limited"
        ])

        self.register_capability(AgentCapability(
            name="error_handling",
            description="Handle errors and recovery",
            task_types=[
                "handle_error",
                "get_error_stats",
                "clear_errors",
                "check_alerts"
            ]
        ))

    async def _on_initialize(self):
        self.logger.info("ErrorHandler: Ready")

    async def execute_task(self, task: Task) -> Any:
        task_type = task.task_type
        payload = task.payload

        if task_type == "handle_error":
            return await self._handle_error(
                error_type=payload.get("error_type"),
                error_message=payload.get("error_message"),
                context=payload.get("context", {})
            )

        elif task_type == "get_error_stats":
            return self._get_error_stats()

        elif task_type == "clear_errors":
            return self._clear_errors()

        elif task_type == "check_alerts":
            return self._check_alerts()

        raise ValueError(f"Unknown task type: {task_type}")

    async def _handle_error(
        self,
        error_type: str,
        error_message: str,
        context: Dict
    ) -> Dict:
        """Handle an error and determine recovery action"""

        # Record error
        error = {
            "type": error_type,
            "message": error_message,
            "context": context,
            "timestamp": datetime.now().isoformat()
        }
        self._error_history.append(error)
        self._error_counts[error_type] = self._error_counts.get(error_type, 0) + 1

        self.logger.error(f"Error: {error_type} - {error_message}")

        # Determine recovery action
        recovery_action = None

        if "rate_limit" in error_type.lower() or "too many" in error_message.lower():
            recovery_action = {
                "action": "pause_and_retry",
                "delay_seconds": random.randint(300, 600),  # 5-10 min
                "reason": "Rate limit detected"
            }

        elif "login" in error_type.lower() or "session" in error_type.lower():
            recovery_action = {
                "action": "refresh_session",
                "reason": "Session expired or invalid"
            }

        elif "blocked" in error_type.lower():
            recovery_action = {
                "action": "rotate_account",
                "reason": "Account may be blocked"
            }

        elif "network" in error_type.lower() or "timeout" in error_type.lower():
            recovery_action = {
                "action": "retry_with_backoff",
                "delay_seconds": 30,
                "max_retries": 3
            }

        # Check if alert needed
        should_alert = (
            error_type in self.critical_errors or
            self._error_counts.get(error_type, 0) >= self.alert_threshold
        )

        return {
            "success": True,
            "error_recorded": True,
            "recovery_action": recovery_action,
            "should_alert": should_alert,
            "error_count": self._error_counts.get(error_type, 0)
        }

    def _get_error_stats(self) -> Dict:
        """Get error statistics"""
        recent_errors = [
            e for e in self._error_history
            if datetime.fromisoformat(e["timestamp"]) > datetime.now() - timedelta(hours=24)
        ]

        return {
            "success": True,
            "total_errors": len(self._error_history),
            "last_24h": len(recent_errors),
            "by_type": self._error_counts.copy(),
            "recent_errors": self._error_history[-10:]  # Last 10
        }

    def _clear_errors(self) -> Dict:
        """Clear error history"""
        count = len(self._error_history)
        self._error_history.clear()
        self._error_counts.clear()

        return {
            "success": True,
            "cleared": count
        }

    def _check_alerts(self) -> Dict:
        """Check if any alerts should be triggered"""
        alerts = []

        for error_type, count in self._error_counts.items():
            if count >= self.alert_threshold:
                alerts.append({
                    "type": error_type,
                    "count": count,
                    "severity": "critical" if error_type in self.critical_errors else "warning"
                })

        return {
            "success": True,
            "has_alerts": len(alerts) > 0,
            "alerts": alerts
        }


# ============================================
# FACTORY FUNCTION
# ============================================

def create_infrastructure_squad(config: Dict = None) -> Dict[str, BaseAgent]:
    """Create all infrastructure squad agents"""
    config = config or {}

    return {
        "AccountManager": AccountManagerAgent(config.get("account_manager")),
        "Analytics": AnalyticsAgent(config.get("analytics")),
        "ErrorHandler": ErrorHandlerAgent(config.get("error_handler"))
    }
