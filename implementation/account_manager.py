"""
Instagram Account Manager - Multi-Tenant Support
=================================================
Manages Instagram accounts per tenant for scalable prospecting.

Each tenant can have multiple Instagram accounts with:
- Individual session management
- Rate limiting per account
- Automatic rotation when blocked
- Usage tracking and analytics
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("AccountManager")

# Supabase config
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


@dataclass
class InstagramAccount:
    """Represents an Instagram account for a tenant"""
    id: int
    tenant_id: str
    username: str
    session_id: Optional[str]
    session_data: Optional[Dict]
    status: str
    daily_limit: int
    hourly_limit: int
    last_used_at: Optional[datetime]
    blocked_until: Optional[datetime]
    dms_sent_today: int = 0
    dms_sent_last_hour: int = 0

    @property
    def is_available(self) -> bool:
        """Check if account is available for use"""
        if self.status != 'active':
            return False
        if self.blocked_until and self.blocked_until > datetime.now():
            return False
        if self.dms_sent_today >= self.daily_limit:
            return False
        if self.dms_sent_last_hour >= self.hourly_limit:
            return False
        return True

    @property
    def remaining_today(self) -> int:
        return max(0, self.daily_limit - self.dms_sent_today)

    @property
    def remaining_this_hour(self) -> int:
        return max(0, self.hourly_limit - self.dms_sent_last_hour)


class AccountManager:
    """
    Manages Instagram accounts for multi-tenant prospecting.

    Usage:
        manager = AccountManager()

        # Get available account for tenant
        account = manager.get_available_account("mottivme")

        # Use account credentials
        session_id = account.session_id

        # Update usage after sending DM
        manager.record_usage(account.id)

        # Mark account as blocked if Instagram blocks it
        manager.mark_blocked(account.id, hours=24)
    """

    def __init__(self):
        self.base_url = f"{SUPABASE_URL}/rest/v1"
        self.headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

    def _request(self, method: str, endpoint: str, params: dict = None, data: dict = None) -> Any:
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

    def get_tenant_accounts(self, tenant_id: str) -> List[InstagramAccount]:
        """Get all Instagram accounts for a tenant"""
        try:
            data = self._request("GET", "instagram_accounts", params={
                "tenant_id": f"eq.{tenant_id}",
                "select": "*"
            })

            accounts = []
            for row in data:
                # Get usage stats
                stats = self._get_account_stats(row['username'])

                accounts.append(InstagramAccount(
                    id=row['id'],
                    tenant_id=row['tenant_id'],
                    username=row['username'],
                    session_id=row.get('session_id'),
                    session_data=row.get('session_data'),
                    status=row['status'],
                    daily_limit=row.get('daily_limit', 50),
                    hourly_limit=row.get('hourly_limit', 10),
                    last_used_at=datetime.fromisoformat(row['last_used_at']) if row.get('last_used_at') else None,
                    blocked_until=datetime.fromisoformat(row['blocked_until']) if row.get('blocked_until') else None,
                    dms_sent_today=stats.get('today', 0),
                    dms_sent_last_hour=stats.get('last_hour', 0)
                ))

            return accounts
        except Exception as e:
            logger.error(f"Error fetching tenant accounts: {e}")
            return []

    def get_available_account(self, tenant_id: str) -> Optional[InstagramAccount]:
        """
        Get the best available account for a tenant.
        Prioritizes accounts with:
        1. More remaining daily quota
        2. Least recently used
        """
        accounts = self.get_tenant_accounts(tenant_id)

        # Filter available accounts
        available = [a for a in accounts if a.is_available]

        if not available:
            logger.warning(f"No available accounts for tenant {tenant_id}")
            return None

        # Sort by remaining quota (desc) then by last_used (asc)
        available.sort(key=lambda a: (-a.remaining_today, a.last_used_at or datetime.min))

        best_account = available[0]
        logger.info(f"Selected account @{best_account.username} for tenant {tenant_id} "
                   f"(remaining: {best_account.remaining_today} today, {best_account.remaining_this_hour} this hour)")

        return best_account

    def get_account_by_username(self, tenant_id: str, username: str) -> Optional[InstagramAccount]:
        """Get specific account by username"""
        try:
            data = self._request("GET", "instagram_accounts", params={
                "tenant_id": f"eq.{tenant_id}",
                "username": f"eq.{username}",
                "select": "*"
            })

            if not data:
                return None

            row = data[0]
            stats = self._get_account_stats(row['username'])

            return InstagramAccount(
                id=row['id'],
                tenant_id=row['tenant_id'],
                username=row['username'],
                session_id=row.get('session_id'),
                session_data=row.get('session_data'),
                status=row['status'],
                daily_limit=row.get('daily_limit', 50),
                hourly_limit=row.get('hourly_limit', 10),
                last_used_at=datetime.fromisoformat(row['last_used_at']) if row.get('last_used_at') else None,
                blocked_until=datetime.fromisoformat(row['blocked_until']) if row.get('blocked_until') else None,
                dms_sent_today=stats.get('today', 0),
                dms_sent_last_hour=stats.get('last_hour', 0)
            )
        except Exception as e:
            logger.error(f"Error fetching account: {e}")
            return None

    def _get_account_stats(self, username: str) -> Dict[str, int]:
        """Get DM stats for an account"""
        try:
            # Today's count
            today = datetime.now().date().isoformat()
            today_response = requests.get(
                f"{self.base_url}/agentic_instagram_dm_sent",
                headers={**self.headers, "Prefer": "count=exact"},
                params={
                    "select": "*",
                    "account_used": f"eq.{username}",
                    "sent_at": f"gte.{today}T00:00:00"
                },
                timeout=10
            )
            today_count = int(today_response.headers.get('content-range', '*/0').split('/')[-1])

            # Last hour count
            one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
            hour_response = requests.get(
                f"{self.base_url}/agentic_instagram_dm_sent",
                headers={**self.headers, "Prefer": "count=exact"},
                params={
                    "select": "*",
                    "account_used": f"eq.{username}",
                    "sent_at": f"gte.{one_hour_ago}"
                },
                timeout=10
            )
            hour_count = int(hour_response.headers.get('content-range', '*/0').split('/')[-1])

            return {'today': today_count, 'last_hour': hour_count}
        except Exception as e:
            logger.error(f"Error getting account stats: {e}")
            return {'today': 0, 'last_hour': 0}

    def record_usage(self, account_id: int):
        """Record that account was used"""
        try:
            self._request("PATCH", "instagram_accounts",
                params={"id": f"eq.{account_id}"},
                data={"last_used_at": datetime.now().isoformat()}
            )
        except Exception as e:
            logger.error(f"Error recording usage: {e}")

    def mark_blocked(self, account_id: int, hours: int = 24, reason: str = None):
        """Mark account as temporarily blocked"""
        try:
            blocked_until = datetime.now() + timedelta(hours=hours)
            self._request("PATCH", "instagram_accounts",
                params={"id": f"eq.{account_id}"},
                data={
                    "status": "blocked",
                    "blocked_until": blocked_until.isoformat(),
                    "notes": f"Blocked: {reason}" if reason else None
                }
            )
            logger.warning(f"Account {account_id} blocked until {blocked_until}")
        except Exception as e:
            logger.error(f"Error marking account blocked: {e}")

    def unblock_account(self, account_id: int):
        """Unblock an account"""
        try:
            self._request("PATCH", "instagram_accounts",
                params={"id": f"eq.{account_id}"},
                data={
                    "status": "active",
                    "blocked_until": None
                }
            )
            logger.info(f"Account {account_id} unblocked")
        except Exception as e:
            logger.error(f"Error unblocking account: {e}")

    def update_session(self, account_id: int, session_id: str, session_data: dict = None):
        """Update account session credentials"""
        try:
            data = {"session_id": session_id}
            if session_data:
                data["session_data"] = session_data

            self._request("PATCH", "instagram_accounts",
                params={"id": f"eq.{account_id}"},
                data=data
            )
            logger.info(f"Session updated for account {account_id}")
        except Exception as e:
            logger.error(f"Error updating session: {e}")

    def create_account(self, tenant_id: str, username: str, session_id: str = None,
                      daily_limit: int = 50, hourly_limit: int = 10) -> Optional[int]:
        """Create a new Instagram account for a tenant"""
        try:
            result = self._request("POST", "instagram_accounts", data={
                "tenant_id": tenant_id,
                "username": username,
                "session_id": session_id,
                "status": "active",
                "daily_limit": daily_limit,
                "hourly_limit": hourly_limit
            })

            if result:
                logger.info(f"Created account @{username} for tenant {tenant_id}")
                return result[0]['id']
            return None
        except Exception as e:
            logger.error(f"Error creating account: {e}")
            return None

    def delete_account(self, account_id: int):
        """Delete an Instagram account"""
        try:
            self._request("DELETE", "instagram_accounts",
                params={"id": f"eq.{account_id}"}
            )
            logger.info(f"Deleted account {account_id}")
        except Exception as e:
            logger.error(f"Error deleting account: {e}")

    def get_tenant_stats(self, tenant_id: str) -> Dict[str, Any]:
        """Get aggregated stats for a tenant"""
        accounts = self.get_tenant_accounts(tenant_id)

        total_accounts = len(accounts)
        active_accounts = len([a for a in accounts if a.status == 'active'])
        available_accounts = len([a for a in accounts if a.is_available])

        total_daily_capacity = sum(a.daily_limit for a in accounts if a.status == 'active')
        total_sent_today = sum(a.dms_sent_today for a in accounts)
        total_remaining_today = sum(a.remaining_today for a in accounts if a.is_available)

        return {
            "tenant_id": tenant_id,
            "total_accounts": total_accounts,
            "active_accounts": active_accounts,
            "available_accounts": available_accounts,
            "total_daily_capacity": total_daily_capacity,
            "total_sent_today": total_sent_today,
            "total_remaining_today": total_remaining_today,
            "accounts": [
                {
                    "username": a.username,
                    "status": a.status,
                    "is_available": a.is_available,
                    "remaining_today": a.remaining_today,
                    "remaining_this_hour": a.remaining_this_hour
                }
                for a in accounts
            ]
        }


# Fallback for backward compatibility
def get_default_account() -> Optional[InstagramAccount]:
    """
    Get default account from environment variables.
    Used when tenant doesn't have accounts configured.
    """
    username = os.getenv("INSTAGRAM_USERNAME")
    session_id = os.getenv("INSTAGRAM_SESSION_ID")

    if not username:
        logger.warning("No INSTAGRAM_USERNAME configured and no tenant account found")
        return None

    return InstagramAccount(
        id=0,
        tenant_id="default",
        username=username,
        session_id=session_id,
        session_data=None,
        status="active",
        daily_limit=int(os.getenv("INSTAGRAM_DM_PER_DAY", 200)),
        hourly_limit=int(os.getenv("INSTAGRAM_DM_PER_HOUR", 10)),
        last_used_at=None,
        blocked_until=None
    )
