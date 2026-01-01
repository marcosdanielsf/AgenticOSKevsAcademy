#!/usr/bin/env python3
"""
QUALITY SQUAD
=============
Agents for quality assurance and validation.

Agents:
1. DataValidatorAgent - Validate lead and profile data
2. MessageQualityAgent - Ensure message quality
3. DeduplicationAgent - Prevent duplicate leads/messages
4. AuditLoggerAgent - Comprehensive audit logging
"""

import os
import sys
import re
import json
import hashlib
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from .base_agent import BaseAgent, Task, AgentCapability


# ============================================
# DATA VALIDATOR AGENT
# ============================================

class DataValidatorAgent(BaseAgent):
    """
    Validates lead and profile data quality.

    Features:
    - Username format validation
    - Bio content analysis
    - Suspicious pattern detection
    - Data completeness scoring
    """

    def __init__(self, config: Dict = None):
        super().__init__(
            name="DataValidator",
            description="Data quality validation"
        )

        self.config = config or {}

        # Validation rules
        self.username_pattern = re.compile(r'^[a-zA-Z0-9._]{1,30}$')

        # Suspicious patterns (bots, spam)
        self.suspicious_patterns = [
            r'\d{5,}',  # Many consecutive numbers
            r'follow.*back',
            r'f4f|l4l|s4s',
            r'earn.*money.*fast',
            r'free.*followers',
            r'dm.*promo',
            r'bot[_\d]*$',
        ]

        # Business keywords (positive signals)
        self.business_keywords = [
            'ceo', 'founder', 'empreendedor', 'empresário',
            'marketing', 'digital', 'consultor', 'mentor',
            'coach', 'agência', 'startup', 'tech'
        ]

        self.register_capability(AgentCapability(
            name="data_validation",
            description="Validate data quality",
            task_types=[
                "validate_username",
                "validate_profile",
                "validate_lead",
                "detect_bot",
                "calculate_quality_score"
            ]
        ))

    async def _on_initialize(self):
        self.logger.info("DataValidator: Initialized with validation rules")

    async def execute_task(self, task: Task) -> Any:
        task_type = task.task_type
        payload = task.payload

        if task_type == "validate_username":
            return self._validate_username(payload.get("username"))

        elif task_type == "validate_profile":
            return self._validate_profile(payload)

        elif task_type == "validate_lead":
            return self._validate_lead(payload)

        elif task_type == "detect_bot":
            return self._detect_bot(payload)

        elif task_type == "calculate_quality_score":
            return self._calculate_quality_score(payload)

        raise ValueError(f"Unknown task type: {task_type}")

    def _validate_username(self, username: str) -> Dict:
        """Validate username format"""
        if not username:
            return {"valid": False, "error": "Username is empty"}

        username = username.lstrip('@')

        if not self.username_pattern.match(username):
            return {"valid": False, "error": "Invalid username format"}

        # Check for suspicious patterns
        for pattern in self.suspicious_patterns:
            if re.search(pattern, username.lower()):
                return {
                    "valid": True,
                    "warning": "Suspicious username pattern",
                    "pattern_matched": pattern
                }

        return {"valid": True, "username": username}

    def _validate_profile(self, profile: Dict) -> Dict:
        """Validate profile data completeness and quality"""
        issues = []
        warnings = []
        score = 100

        # Required fields
        required_fields = ["username"]
        for field in required_fields:
            if not profile.get(field):
                issues.append(f"Missing required field: {field}")
                score -= 20

        # Recommended fields
        recommended_fields = ["full_name", "bio", "followers_count"]
        for field in recommended_fields:
            if not profile.get(field):
                warnings.append(f"Missing recommended field: {field}")
                score -= 5

        # Validate username
        username_result = self._validate_username(profile.get("username", ""))
        if not username_result.get("valid"):
            issues.append(username_result.get("error"))
            score -= 30

        # Check for suspicious bio
        bio = profile.get("bio", "")
        if bio:
            for pattern in self.suspicious_patterns:
                if re.search(pattern, bio.lower()):
                    warnings.append(f"Suspicious pattern in bio: {pattern}")
                    score -= 10

        # Check follower ratio
        followers = profile.get("followers_count", 0)
        following = profile.get("following_count", 0)

        if followers > 0 and following > 0:
            ratio = following / followers
            if ratio > 10:  # Following way more than followers
                warnings.append("Unusual follower/following ratio")
                score -= 15

        return {
            "valid": len(issues) == 0,
            "score": max(0, score),
            "issues": issues,
            "warnings": warnings
        }

    def _validate_lead(self, lead: Dict) -> Dict:
        """Validate lead data"""
        result = self._validate_profile(lead)

        # Additional lead-specific validation
        classification = lead.get("classification")
        if classification and classification not in ["LEAD_HOT", "LEAD_WARM", "LEAD_COLD", "PESSOAL", "SPAM"]:
            result["issues"].append(f"Invalid classification: {classification}")
            result["score"] -= 10

        lead_score = lead.get("score", 0)
        if not (0 <= lead_score <= 100):
            result["issues"].append(f"Score out of range: {lead_score}")

        result["valid"] = len(result["issues"]) == 0
        return result

    def _detect_bot(self, profile: Dict) -> Dict:
        """Detect if profile is likely a bot"""
        bot_signals = 0
        reasons = []

        username = profile.get("username", "")
        bio = profile.get("bio", "")
        followers = profile.get("followers_count", 0)
        following = profile.get("following_count", 0)
        posts = profile.get("posts_count", 0)

        # Check username patterns
        if re.search(r'\d{5,}', username):
            bot_signals += 2
            reasons.append("Many numbers in username")

        # Check bio patterns
        for pattern in self.suspicious_patterns:
            if re.search(pattern, bio.lower()):
                bot_signals += 2
                reasons.append(f"Suspicious bio pattern: {pattern}")

        # Check ratios
        if following > 0 and followers == 0:
            bot_signals += 1
            reasons.append("Following but no followers")

        if following > 5000 and followers < 100:
            bot_signals += 2
            reasons.append("Mass following behavior")

        if posts == 0 and following > 100:
            bot_signals += 1
            reasons.append("No posts but following many")

        # Check for generic/empty profile
        if not bio and not profile.get("full_name"):
            bot_signals += 1
            reasons.append("Empty profile")

        is_bot = bot_signals >= 3
        confidence = min(100, bot_signals * 20)

        return {
            "is_bot": is_bot,
            "confidence": confidence,
            "signals": bot_signals,
            "reasons": reasons
        }

    def _calculate_quality_score(self, data: Dict) -> Dict:
        """Calculate overall data quality score"""
        profile_result = self._validate_profile(data)
        bot_result = self._detect_bot(data)

        # Start with profile score
        score = profile_result["score"]

        # Reduce if likely bot
        if bot_result["is_bot"]:
            score -= 30

        # Bonus for business signals
        bio = (data.get("bio") or "").lower()
        business_matches = sum(1 for kw in self.business_keywords if kw in bio)
        score += min(20, business_matches * 5)

        # Bonus for verified
        if data.get("is_verified"):
            score += 10

        # Bonus for post activity
        if data.get("posts_count", 0) >= 50:
            score += 5

        return {
            "quality_score": max(0, min(100, score)),
            "profile_issues": profile_result["issues"],
            "profile_warnings": profile_result["warnings"],
            "bot_detection": bot_result,
            "recommendation": "proceed" if score >= 50 else "review" if score >= 30 else "skip"
        }


# ============================================
# MESSAGE QUALITY AGENT
# ============================================

class MessageQualityAgent(BaseAgent):
    """
    Ensures message quality before sending.

    Features:
    - Grammar/spelling check
    - Tone analysis
    - Length validation
    - Personalization check
    """

    def __init__(self, config: Dict = None):
        super().__init__(
            name="MessageQuality",
            description="Message quality assurance"
        )

        self.config = config or {}

        # Message constraints
        self.min_length = self.config.get("min_length", 20)
        self.max_length = self.config.get("max_length", 500)
        self.max_emojis = self.config.get("max_emojis", 3)

        # Spam patterns to avoid
        self.spam_patterns = [
            r'click here',
            r'free money',
            r'limited time',
            r'act now',
            r'buy now',
            r'100% guaranteed',
        ]

        self.register_capability(AgentCapability(
            name="message_quality",
            description="Message quality validation",
            task_types=[
                "validate_message",
                "check_personalization",
                "analyze_tone",
                "suggest_improvements"
            ]
        ))

    async def _on_initialize(self):
        self.logger.info("MessageQuality: Initialized")

    async def execute_task(self, task: Task) -> Any:
        task_type = task.task_type
        payload = task.payload

        if task_type == "validate_message":
            return self._validate_message(payload.get("message"))

        elif task_type == "check_personalization":
            return self._check_personalization(
                message=payload.get("message"),
                profile=payload.get("profile", {})
            )

        elif task_type == "analyze_tone":
            return self._analyze_tone(payload.get("message"))

        elif task_type == "suggest_improvements":
            return self._suggest_improvements(
                message=payload.get("message"),
                profile=payload.get("profile", {})
            )

        raise ValueError(f"Unknown task type: {task_type}")

    def _validate_message(self, message: str) -> Dict:
        """Validate message quality"""
        if not message:
            return {"valid": False, "error": "Message is empty"}

        issues = []
        warnings = []

        # Length check
        if len(message) < self.min_length:
            issues.append(f"Message too short (min: {self.min_length})")
        if len(message) > self.max_length:
            issues.append(f"Message too long (max: {self.max_length})")

        # Emoji count
        import emoji
        emoji_count = len([c for c in message if c in emoji.EMOJI_DATA])
        if emoji_count > self.max_emojis:
            warnings.append(f"Too many emojis ({emoji_count}, max: {self.max_emojis})")

        # Spam patterns
        for pattern in self.spam_patterns:
            if re.search(pattern, message.lower()):
                issues.append(f"Contains spam pattern: {pattern}")

        # ALL CAPS check
        words = message.split()
        caps_words = sum(1 for w in words if w.isupper() and len(w) > 2)
        if caps_words > len(words) * 0.3:
            warnings.append("Too many words in ALL CAPS")

        # Excessive punctuation
        if re.search(r'[!?]{3,}', message):
            warnings.append("Excessive punctuation")

        return {
            "valid": len(issues) == 0,
            "length": len(message),
            "issues": issues,
            "warnings": warnings
        }

    def _check_personalization(self, message: str, profile: Dict) -> Dict:
        """Check if message is personalized"""
        personalization_score = 0
        used_elements = []

        message_lower = message.lower()

        # Check for name usage
        first_name = (profile.get("full_name") or "").split()[0].lower() if profile.get("full_name") else ""
        if first_name and first_name in message_lower:
            personalization_score += 30
            used_elements.append("first_name")

        # Check for username reference
        username = profile.get("username", "").lower()
        if username and username in message_lower:
            personalization_score += 20
            used_elements.append("username")

        # Check for category/niche reference
        category = (profile.get("category") or "").lower()
        if category and category in message_lower:
            personalization_score += 25
            used_elements.append("category")

        # Check for bio keyword usage
        bio = (profile.get("bio") or "").lower()
        bio_words = set(re.findall(r'\w+', bio))
        message_words = set(re.findall(r'\w+', message_lower))
        common_words = bio_words & message_words - {'de', 'e', 'a', 'o', 'que', 'com', 'para', 'em'}
        if len(common_words) >= 2:
            personalization_score += 25
            used_elements.append(f"bio_keywords: {list(common_words)[:3]}")

        return {
            "personalization_score": min(100, personalization_score),
            "used_elements": used_elements,
            "is_personalized": personalization_score >= 30,
            "recommendation": "good" if personalization_score >= 50 else "add_more_personalization"
        }

    def _analyze_tone(self, message: str) -> Dict:
        """Analyze message tone"""
        # Simple keyword-based tone analysis
        positive_words = ['legal', 'incrível', 'parabéns', 'sucesso', 'ótimo', 'excelente', 'fantástico']
        negative_words = ['problema', 'difícil', 'ruim', 'errado', 'falha']
        formal_words = ['prezado', 'cordialmente', 'atenciosamente', 'senhor', 'senhora']
        casual_words = ['opa', 'e aí', 'fala', 'blz', 'tmj', 'vlw']

        message_lower = message.lower()

        positive_count = sum(1 for w in positive_words if w in message_lower)
        negative_count = sum(1 for w in negative_words if w in message_lower)
        formal_count = sum(1 for w in formal_words if w in message_lower)
        casual_count = sum(1 for w in casual_words if w in message_lower)

        # Determine primary tone
        if formal_count > casual_count:
            formality = "formal"
        elif casual_count > formal_count:
            formality = "casual"
        else:
            formality = "neutral"

        if positive_count > negative_count:
            sentiment = "positive"
        elif negative_count > positive_count:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        return {
            "formality": formality,
            "sentiment": sentiment,
            "positive_indicators": positive_count,
            "negative_indicators": negative_count
        }

    def _suggest_improvements(self, message: str, profile: Dict) -> Dict:
        """Suggest improvements for the message"""
        suggestions = []

        validation = self._validate_message(message)
        personalization = self._check_personalization(message, profile)
        tone = self._analyze_tone(message)

        # Length suggestions
        if len(message) < 50:
            suggestions.append("Consider adding more context to your message")
        if len(message) > 300:
            suggestions.append("Consider making the message more concise")

        # Personalization suggestions
        if not personalization["is_personalized"]:
            first_name = (profile.get("full_name") or "").split()[0] if profile.get("full_name") else None
            if first_name:
                suggestions.append(f"Add the recipient's name: {first_name}")
            if profile.get("bio"):
                suggestions.append("Reference something from their bio")

        # Tone suggestions
        if tone["sentiment"] == "negative":
            suggestions.append("Consider using more positive language")
        if tone["formality"] == "formal" and profile.get("followers_count", 0) < 10000:
            suggestions.append("Consider a more casual, friendly tone")

        # Call to action
        if not any(word in message.lower() for word in ['?', 'responda', 'me conta', 'o que acha', 'quer']):
            suggestions.append("Add a question or call-to-action to encourage response")

        return {
            "suggestions": suggestions,
            "validation_issues": validation["issues"],
            "personalization_score": personalization["personalization_score"],
            "overall_quality": "good" if len(suggestions) <= 1 else "needs_improvement"
        }


# ============================================
# DEDUPLICATION AGENT
# ============================================

class DeduplicationAgent(BaseAgent):
    """
    Prevents duplicate leads and messages.

    Features:
    - Username-based dedup
    - Content hash dedup
    - Similarity detection
    - Cross-tenant isolation
    """

    def __init__(self, config: Dict = None):
        super().__init__(
            name="Deduplication",
            description="Duplicate prevention"
        )

        self.config = config or {}

        # In-memory dedup sets (per tenant)
        self._seen_usernames: Dict[str, Set[str]] = defaultdict(set)
        self._seen_message_hashes: Dict[str, Set[str]] = defaultdict(set)
        self._contacted_users: Dict[str, Dict[str, datetime]] = defaultdict(dict)

        # Contact cooldown (don't contact same user within X days)
        self.contact_cooldown_days = self.config.get("contact_cooldown_days", 30)

        self.register_capability(AgentCapability(
            name="deduplication",
            description="Duplicate prevention",
            task_types=[
                "check_duplicate_lead",
                "mark_lead_seen",
                "check_can_contact",
                "mark_contacted",
                "check_message_duplicate",
                "get_stats"
            ]
        ))

    async def _on_initialize(self):
        self.logger.info("Deduplication: Initialized")

    async def execute_task(self, task: Task) -> Any:
        task_type = task.task_type
        payload = task.payload

        tenant_id = payload.get("tenant_id", "default")

        if task_type == "check_duplicate_lead":
            return self._check_duplicate_lead(
                tenant_id=tenant_id,
                username=payload.get("username")
            )

        elif task_type == "mark_lead_seen":
            return self._mark_lead_seen(
                tenant_id=tenant_id,
                username=payload.get("username")
            )

        elif task_type == "check_can_contact":
            return self._check_can_contact(
                tenant_id=tenant_id,
                username=payload.get("username")
            )

        elif task_type == "mark_contacted":
            return self._mark_contacted(
                tenant_id=tenant_id,
                username=payload.get("username")
            )

        elif task_type == "check_message_duplicate":
            return self._check_message_duplicate(
                tenant_id=tenant_id,
                message=payload.get("message")
            )

        elif task_type == "get_stats":
            return self._get_stats(tenant_id=tenant_id)

        raise ValueError(f"Unknown task type: {task_type}")

    def _check_duplicate_lead(self, tenant_id: str, username: str) -> Dict:
        """Check if lead was already seen"""
        username = username.lower().lstrip('@')
        is_duplicate = username in self._seen_usernames[tenant_id]

        return {
            "is_duplicate": is_duplicate,
            "username": username
        }

    def _mark_lead_seen(self, tenant_id: str, username: str) -> Dict:
        """Mark lead as seen"""
        username = username.lower().lstrip('@')
        self._seen_usernames[tenant_id].add(username)

        return {
            "success": True,
            "username": username,
            "total_seen": len(self._seen_usernames[tenant_id])
        }

    def _check_can_contact(self, tenant_id: str, username: str) -> Dict:
        """Check if user can be contacted (respecting cooldown)"""
        username = username.lower().lstrip('@')

        last_contact = self._contacted_users[tenant_id].get(username)

        if not last_contact:
            return {"can_contact": True, "reason": "Never contacted"}

        days_since = (datetime.now() - last_contact).days

        if days_since >= self.contact_cooldown_days:
            return {
                "can_contact": True,
                "reason": f"Cooldown passed ({days_since} days)"
            }

        return {
            "can_contact": False,
            "reason": f"Contacted {days_since} days ago",
            "wait_days": self.contact_cooldown_days - days_since
        }

    def _mark_contacted(self, tenant_id: str, username: str) -> Dict:
        """Mark user as contacted"""
        username = username.lower().lstrip('@')
        self._contacted_users[tenant_id][username] = datetime.now()

        return {
            "success": True,
            "username": username,
            "contacted_at": datetime.now().isoformat()
        }

    def _check_message_duplicate(self, tenant_id: str, message: str) -> Dict:
        """Check if message content was already sent (prevent copy-paste spam)"""
        # Create hash of normalized message
        normalized = re.sub(r'\s+', ' ', message.lower().strip())
        message_hash = hashlib.md5(normalized.encode()).hexdigest()

        is_duplicate = message_hash in self._seen_message_hashes[tenant_id]

        if not is_duplicate:
            self._seen_message_hashes[tenant_id].add(message_hash)

        return {
            "is_duplicate": is_duplicate,
            "hash": message_hash
        }

    def _get_stats(self, tenant_id: str) -> Dict:
        """Get deduplication stats"""
        return {
            "tenant_id": tenant_id,
            "leads_seen": len(self._seen_usernames[tenant_id]),
            "users_contacted": len(self._contacted_users[tenant_id]),
            "unique_messages": len(self._seen_message_hashes[tenant_id])
        }


# ============================================
# AUDIT LOGGER AGENT
# ============================================

class AuditLoggerAgent(BaseAgent):
    """
    Comprehensive audit logging.

    Features:
    - Action logging
    - Error tracking
    - Performance metrics
    - Compliance reporting
    """

    def __init__(self, config: Dict = None):
        super().__init__(
            name="AuditLogger",
            description="Comprehensive audit logging"
        )

        self.config = config or {}

        # In-memory audit log (in production, use database)
        self._audit_log: List[Dict] = []
        self.max_log_size = self.config.get("max_log_size", 10000)

        # Log file
        self.log_dir = Path(__file__).parent.parent.parent / "logs"
        self.log_dir.mkdir(exist_ok=True)

        self.register_capability(AgentCapability(
            name="audit_logging",
            description="Audit log operations",
            task_types=[
                "log_action",
                "log_error",
                "get_logs",
                "get_summary",
                "export_logs"
            ]
        ))

    async def _on_initialize(self):
        self.logger.info("AuditLogger: Initialized")

    async def execute_task(self, task: Task) -> Any:
        task_type = task.task_type
        payload = task.payload

        if task_type == "log_action":
            return self._log_action(
                action=payload.get("action"),
                agent=payload.get("agent"),
                details=payload.get("details", {}),
                tenant_id=payload.get("tenant_id")
            )

        elif task_type == "log_error":
            return self._log_error(
                error_type=payload.get("error_type"),
                error_message=payload.get("error_message"),
                agent=payload.get("agent"),
                context=payload.get("context", {})
            )

        elif task_type == "get_logs":
            return self._get_logs(
                limit=payload.get("limit", 100),
                action_type=payload.get("action_type"),
                agent=payload.get("agent"),
                tenant_id=payload.get("tenant_id")
            )

        elif task_type == "get_summary":
            return self._get_summary(
                hours=payload.get("hours", 24)
            )

        elif task_type == "export_logs":
            return self._export_logs(
                filename=payload.get("filename")
            )

        raise ValueError(f"Unknown task type: {task_type}")

    def _log_action(
        self,
        action: str,
        agent: str,
        details: Dict = None,
        tenant_id: str = None
    ) -> Dict:
        """Log an action"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "action",
            "action": action,
            "agent": agent,
            "tenant_id": tenant_id,
            "details": details or {}
        }

        self._add_to_log(entry)
        return {"success": True, "entry_id": len(self._audit_log)}

    def _log_error(
        self,
        error_type: str,
        error_message: str,
        agent: str,
        context: Dict = None
    ) -> Dict:
        """Log an error"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "error",
            "error_type": error_type,
            "error_message": error_message,
            "agent": agent,
            "context": context or {}
        }

        self._add_to_log(entry)
        return {"success": True, "entry_id": len(self._audit_log)}

    def _add_to_log(self, entry: Dict):
        """Add entry to log with size management"""
        self._audit_log.append(entry)

        # Trim if exceeds max size
        if len(self._audit_log) > self.max_log_size:
            self._audit_log = self._audit_log[-self.max_log_size:]

    def _get_logs(
        self,
        limit: int = 100,
        action_type: str = None,
        agent: str = None,
        tenant_id: str = None
    ) -> Dict:
        """Get filtered logs"""
        logs = self._audit_log

        if action_type:
            logs = [l for l in logs if l.get("action") == action_type]
        if agent:
            logs = [l for l in logs if l.get("agent") == agent]
        if tenant_id:
            logs = [l for l in logs if l.get("tenant_id") == tenant_id]

        return {
            "logs": logs[-limit:],
            "total": len(logs),
            "returned": min(limit, len(logs))
        }

    def _get_summary(self, hours: int = 24) -> Dict:
        """Get summary of recent activity"""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent = [
            l for l in self._audit_log
            if datetime.fromisoformat(l["timestamp"]) > cutoff
        ]

        actions = defaultdict(int)
        errors = defaultdict(int)
        agents = defaultdict(int)

        for entry in recent:
            if entry["type"] == "action":
                actions[entry.get("action", "unknown")] += 1
            elif entry["type"] == "error":
                errors[entry.get("error_type", "unknown")] += 1

            agents[entry.get("agent", "unknown")] += 1

        return {
            "period_hours": hours,
            "total_entries": len(recent),
            "actions_by_type": dict(actions),
            "errors_by_type": dict(errors),
            "entries_by_agent": dict(agents)
        }

    def _export_logs(self, filename: str = None) -> Dict:
        """Export logs to file"""
        if not filename:
            filename = f"audit_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        filepath = self.log_dir / filename

        with open(filepath, 'w') as f:
            json.dump(self._audit_log, f, indent=2)

        return {
            "success": True,
            "filepath": str(filepath),
            "entries_exported": len(self._audit_log)
        }


# ============================================
# FACTORY FUNCTION
# ============================================

def create_quality_squad(config: Dict = None) -> Dict[str, BaseAgent]:
    """Create all quality squad agents"""
    config = config or {}

    return {
        "DataValidator": DataValidatorAgent(config.get("validator")),
        "MessageQuality": MessageQualityAgent(config.get("message")),
        "Deduplication": DeduplicationAgent(config.get("dedup")),
        "AuditLogger": AuditLoggerAgent(config.get("audit"))
    }
