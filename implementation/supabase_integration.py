#!/usr/bin/env python3
"""
Supabase Integration for Socialfy Agents
=========================================
Connects our 23 Python agents to the existing Socialfy Platform Supabase tables.

Tables Mapping:
- crm_leads: Lead data from Instagram/LinkedIn scraping
- socialfy_messages: Messages sent/received
- growth_leads: Lead intelligence data (migrated from socialfy_leads)
- agent_conversations: AI agent conversation tracking
- llm_costs: AI/LLM cost tracking
- socialfy_analytics_daily: Daily aggregated metrics
"""

import os
import logging
import requests
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class SupabaseClient:
    """REST API client for Supabase - connects to Socialfy Platform"""

    def __init__(self):
        self.url = os.getenv('SUPABASE_URL')
        self.service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        self.anon_key = os.getenv('SUPABASE_ANON_KEY')

        if not self.url or not self.service_key:
            raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")

        self.headers = {
            'apikey': self.service_key,
            'Authorization': f'Bearer {self.service_key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }

        logger.info(f"SupabaseClient initialized: {self.url}")

    def _request(self, method: str, table: str, params: Dict = None, data: Any = None) -> Dict:
        """Make a request to Supabase REST API"""
        url = f"{self.url}/rest/v1/{table}"

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=data,
                timeout=30
            )

            if response.status_code >= 400:
                logger.error(f"Supabase error {response.status_code}: {response.text}")
                return {"error": response.text, "status": response.status_code}

            return response.json() if response.text else {}

        except Exception as e:
            logger.error(f"Supabase request failed: {e}")
            return {"error": str(e)}

    # ===========================================
    # CRM LEADS (Lead Discovery Agent)
    # ===========================================

    def insert_lead(self, lead_data: Dict) -> Dict:
        """Insert a new lead into crm_leads"""
        return self._request('POST', 'crm_leads', data=lead_data)

    def upsert_lead(self, lead_data: Dict) -> Dict:
        """Upsert a lead (update if exists)"""
        headers = {**self.headers, 'Prefer': 'resolution=merge-duplicates,return=representation'}
        return self._request('POST', 'crm_leads', data=lead_data)

    def get_lead_by_email(self, email: str) -> Optional[Dict]:
        """Get a lead by email"""
        result = self._request('GET', 'crm_leads', params={
            'email': f'eq.{email}',
            'limit': 1
        })
        return result[0] if isinstance(result, list) and result else None

    def get_lead_by_name(self, name: str) -> Optional[Dict]:
        """Get a lead by name (partial match)"""
        result = self._request('GET', 'crm_leads', params={
            'name': f'ilike.%{name}%',
            'limit': 5
        })
        return result if isinstance(result, list) else []

    def update_lead(self, lead_id: str, updates: Dict) -> Dict:
        """Update a lead by ID"""
        return self._request('PATCH', f'crm_leads?id=eq.{lead_id}', data=updates)

    # ===========================================
    # GROWTH LEADS (Profile Analyzer Agent)
    # ===========================================

    def upsert_growth_lead(self, lead_data: Dict) -> Dict:
        """Insert/update lead intelligence data in growth_leads"""
        return self._request('POST', 'growth_leads', data=lead_data)

    # Alias for backwards compatibility
    def upsert_socialfy_lead(self, lead_data: Dict) -> Dict:
        """Deprecated: Use upsert_growth_lead instead"""
        return self.upsert_growth_lead(lead_data)

    def update_icp_score(self, lead_id: str, icp_score: int, icp_analysis: Dict) -> Dict:
        """Update ICP score for a lead in growth_leads"""
        return self._request('PATCH', f'growth_leads?id=eq.{lead_id}', data={
            'icp_score': icp_score,
            'custom_fields': icp_analysis,  # icp_analysis goes into custom_fields
            'updated_at': datetime.now(timezone.utc).isoformat()
        })

    # ===========================================
    # SOCIALFY MESSAGES (Message Composer/Outreach Agent)
    # ===========================================

    def insert_message(self, message_data: Dict) -> Dict:
        """Insert a message record"""
        return self._request('POST', 'socialfy_messages', data={
            **message_data,
            'created_at': datetime.now(timezone.utc).isoformat()
        })

    def update_message_status(self, message_id: str, status: str, sent_at: str = None) -> Dict:
        """Update message status (sent, delivered, read, replied)"""
        data = {'status': status, 'updated_at': datetime.now(timezone.utc).isoformat()}
        if sent_at:
            data['sent_at'] = sent_at
        return self._request('PATCH', f'socialfy_messages?id=eq.{message_id}', data=data)

    def get_pending_messages(self, limit: int = 10) -> List[Dict]:
        """Get messages pending to send"""
        result = self._request('GET', 'socialfy_messages', params={
            'status': 'eq.pending',
            'order': 'created_at.asc',
            'limit': limit
        })
        return result if isinstance(result, list) else []

    # ===========================================
    # AGENT CONVERSATIONS (Lead Classifier Agent)
    # ===========================================

    def insert_conversation(self, conversation_data: Dict) -> Dict:
        """Insert a new agent conversation"""
        return self._request('POST', 'agent_conversations', data={
            **conversation_data,
            'started_at': datetime.now(timezone.utc).isoformat()
        })

    def update_conversation(self, conversation_id: str, updates: Dict) -> Dict:
        """Update conversation (agendou_consulta, ended_at, etc.)"""
        return self._request('PATCH', f'agent_conversations?id=eq.{conversation_id}', data=updates)

    def mark_lead_scheduled(self, conversation_id: str, consulta_id: str = None) -> Dict:
        """Mark a conversation as having scheduled a meeting"""
        return self._request('PATCH', f'agent_conversations?id=eq.{conversation_id}', data={
            'agendou_consulta': True,
            'consulta_id': consulta_id,
            'updated_at': datetime.now(timezone.utc).isoformat()
        })

    # ===========================================
    # LLM COSTS (Analytics Agent)
    # ===========================================

    def log_llm_cost(self, cost_data: Dict) -> Dict:
        """Log AI/LLM usage cost"""
        return self._request('POST', 'llm_costs', data={
            **cost_data,
            'created_at': datetime.now(timezone.utc).isoformat()
        })

    def get_total_llm_cost(self, location_id: str = None, days: int = 30) -> float:
        """Get total LLM cost for a location"""
        params = {'select': 'custo_usd'}
        if location_id:
            params['location_id'] = f'eq.{location_id}'

        result = self._request('GET', 'llm_costs', params=params)
        if isinstance(result, list):
            return sum(r.get('custo_usd', 0) for r in result)
        return 0.0

    # ===========================================
    # ANALYTICS (Daily Metrics)
    # ===========================================

    def upsert_daily_analytics(self, analytics_data: Dict) -> Dict:
        """Upsert daily analytics"""
        return self._request('POST', 'socialfy_analytics_daily', data=analytics_data)

    def get_analytics(self, organization_id: str, days: int = 30) -> List[Dict]:
        """Get analytics for an organization"""
        result = self._request('GET', 'socialfy_analytics_daily', params={
            'organization_id': f'eq.{organization_id}',
            'order': 'date.desc',
            'limit': days
        })
        return result if isinstance(result, list) else []

    # ===========================================
    # PIPELINE DEALS
    # ===========================================

    def insert_deal(self, deal_data: Dict) -> Dict:
        """Insert a pipeline deal"""
        return self._request('POST', 'socialfy_pipeline_deals', data=deal_data)

    def update_deal_stage(self, deal_id: str, stage: str, metadata: Dict = None) -> Dict:
        """Update deal stage"""
        data = {'stage': stage, 'updated_at': datetime.now(timezone.utc).isoformat()}
        if metadata:
            data.update(metadata)
        return self._request('PATCH', f'socialfy_pipeline_deals?id=eq.{deal_id}', data=data)

    def mark_deal_won(self, deal_id: str, value: float = None) -> Dict:
        """Mark a deal as won"""
        data = {
            'stage': 'won',
            'won_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        if value:
            data['value'] = value
        return self._request('PATCH', f'socialfy_pipeline_deals?id=eq.{deal_id}', data=data)


# ===========================================
# AGENT INTEGRATION HELPERS
# ===========================================

class SocialfyAgentIntegration:
    """
    Helper class to integrate our 23 agents with Socialfy Platform.

    Usage:
        integration = SocialfyAgentIntegration()

        # When LeadDiscovery finds a new lead:
        integration.save_discovered_lead(lead_data)

        # When ProfileAnalyzer scores a lead:
        integration.save_profile_analysis(lead_id, analysis)

        # When MessageComposer creates a message:
        integration.save_composed_message(lead_id, message)

        # When OutreachExecutor sends a DM:
        integration.mark_message_sent(message_id)
    """

    def __init__(self):
        self.db = SupabaseClient()
        logger.info("SocialfyAgentIntegration initialized")

    # LeadDiscovery Agent
    def save_discovered_lead(self, name: str, email: str, source: str, profile_data: Dict = None) -> Dict:
        """
        Save a newly discovered lead to crm_leads table.

        Real crm_leads columns: id, proposal_id, name, email, phone, company,
        score, status, last_activity, total_time_seconds, visit_count, created_at,
        ghl_contact_id, ghl_location_id, company_id, vertical, source_channel, current_agent

        Source channel examples:
        - instagram_dm, instagram_like, instagram_comment, instagram_follower
        - linkedin, website, referral, etc.
        """
        profile_data = profile_data or {}

        # Calculate status from score (valid: pending, viewed, engaged, hot, won, lost)
        score = profile_data.get('score', 0)
        if score >= 70:
            status = 'hot'
        elif score >= 40:
            status = 'engaged'
        else:
            status = 'pending'

        lead_data = {
            'name': name,
            'email': email,
            'phone': profile_data.get('phone'),
            'company': profile_data.get('company'),
            'source_channel': source,  # instagram_dm, instagram_like, instagram_comment, etc.
            'status': status,
            'score': score,
            'vertical': profile_data.get('vertical'),
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        # Remove None values
        lead_data = {k: v for k, v in lead_data.items() if v is not None}
        return self.db.insert_lead(lead_data)

    def save_instagram_lead(self, instagram_data: Dict) -> Dict:
        """
        Save Instagram lead data to crm_leads table.

        Maps Instagram profile data to crm_leads columns with proper score-to-status mapping.

        Args:
            instagram_data: Dict containing Instagram profile data with fields:
                - name (required)
                - email (optional)
                - phone (optional)
                - company (optional)
                - score (optional, defaults to 0)
                - username (optional)
                - bio (optional)
                - followers (optional)
                - following (optional)

        Returns:
            Dict with Supabase response

        Score to Status mapping:
            - score >= 70 → "hot"
            - score >= 40 → "engaged"
            - score < 40 → "pending"
        """
        # Calculate status from score
        score = instagram_data.get('score', 0)
        if score >= 70:
            status = 'hot'
        elif score >= 40:
            status = 'engaged'
        else:
            status = 'pending'

        # Determine specific source channel
        # Options: instagram_dm, instagram_like, instagram_comment, instagram_follower
        source_type = instagram_data.get('source_type', 'dm')
        source_channel = f"instagram_{source_type}"

        lead_data = {
            'name': instagram_data.get('name'),
            'email': instagram_data.get('email'),
            'phone': instagram_data.get('phone'),
            'company': instagram_data.get('company'),
            'source_channel': source_channel,
            'status': status,
            'score': score,
            'vertical': instagram_data.get('vertical'),
            'created_at': datetime.now(timezone.utc).isoformat()
        }

        # Remove None values
        lead_data = {k: v for k, v in lead_data.items() if v is not None}

        # Ensure we have at least a name
        if not lead_data.get('name'):
            raise ValueError("Instagram lead must have a name")

        logger.info(f"Saving Instagram lead: {lead_data.get('name')} with status={status}, score={score}")
        return self.db.insert_lead(lead_data)

    def update_lead_from_scrape(self, lead_id: str, scraped_data: Dict) -> Dict:
        """
        Update an existing lead with newly scraped data.

        Merges new scraped data with existing lead, updating score/status if provided.

        Args:
            lead_id: The UUID of the existing lead
            scraped_data: Dict containing updated fields:
                - email (optional)
                - phone (optional)
                - company (optional)
                - score (optional, will recalculate status)
                - Any other crm_leads fields

        Returns:
            Dict with Supabase response
        """
        updates = {}

        # Add basic fields if provided
        if scraped_data.get('email'):
            updates['email'] = scraped_data['email']
        if scraped_data.get('phone'):
            updates['phone'] = scraped_data['phone']
        if scraped_data.get('company'):
            updates['company'] = scraped_data['company']
        if scraped_data.get('vertical'):
            updates['vertical'] = scraped_data['vertical']

        # Handle score and status mapping
        if 'score' in scraped_data:
            score = scraped_data['score']
            updates['score'] = score

            # Recalculate status based on new score
            if score >= 70:
                updates['status'] = 'hot'
            elif score >= 40:
                updates['status'] = 'engaged'
            else:
                updates['status'] = 'pending'

        # Add last_activity timestamp
        updates['last_activity'] = datetime.now(timezone.utc).isoformat()

        if not updates:
            logger.warning(f"No updates provided for lead {lead_id}")
            return {"error": "No updates provided"}

        logger.info(f"Updating lead {lead_id} with scraped data: {list(updates.keys())}")
        return self.db.update_lead(lead_id, updates)

    # ProfileAnalyzer Agent
    def save_profile_analysis(self, lead_id: str, analysis: Dict) -> Dict:
        """Save profile analysis with ICP score"""
        return self.db.update_icp_score(
            lead_id=lead_id,
            icp_score=analysis.get('score', 0),
            icp_analysis={
                'reasoning': analysis.get('reasoning'),
                'keywords_found': analysis.get('keywords_found', []),
                'pain_points': analysis.get('pain_points', []),
                'buying_signals': analysis.get('buying_signals', []),
                'analyzed_at': datetime.now(timezone.utc).isoformat()
            }
        )

    # MessageComposer Agent
    def save_composed_message(self, lead_id: str, message: str, template_id: str = None) -> Dict:
        """Save a composed message ready to send"""
        return self.db.insert_message({
            'lead_id': lead_id,
            'channel': 'instagram',
            'direction': 'outbound',
            'content': message,
            'template_id': template_id,
            'status': 'pending'
        })

    # OutreachExecutor Agent
    def mark_message_sent(self, message_id: str) -> Dict:
        """Mark a message as sent"""
        return self.db.update_message_status(
            message_id=message_id,
            status='sent',
            sent_at=datetime.now(timezone.utc).isoformat()
        )

    # InboxMonitor Agent
    def save_received_message(self, lead_id: str, message: str) -> Dict:
        """Save a received message"""
        return self.db.insert_message({
            'lead_id': lead_id,
            'channel': 'instagram',
            'direction': 'inbound',
            'content': message,
            'status': 'received'
        })

    # LeadClassifier Agent
    def save_classification(self, lead_id: str, classification: str, analysis: Dict) -> Dict:
        """Save lead classification (HOT, WARM, COLD, SPAM)"""
        return self.db.update_lead(lead_id, {
            'classification': classification,
            'ai_reasoning': analysis.get('reasoning'),
            'suggested_response': analysis.get('suggested_response'),
            'updated_at': datetime.now(timezone.utc).isoformat()
        })

    # Analytics Agent
    def log_ai_usage(self, model: str, tokens_in: int, tokens_out: int, cost_usd: float) -> Dict:
        """Log AI model usage"""
        return self.db.log_llm_cost({
            'modelo_ia': model,
            'tokens_input': tokens_in,
            'tokens_output': tokens_out,
            'custo_usd': cost_usd
        })

    # Pipeline tracking
    def create_deal(self, lead_id: str, stage: str = 'prospect') -> Dict:
        """Create a pipeline deal from a lead"""
        return self.db.insert_deal({
            'lead_id': lead_id,
            'stage': stage,
            'created_at': datetime.now(timezone.utc).isoformat()
        })


# ===========================================
# TEST CONNECTION
# ===========================================

def test_connection():
    """Test Supabase connection"""
    try:
        client = SupabaseClient()
        print(f"✅ Connected to: {client.url}")

        # Try a simple query
        result = client._request('GET', 'crm_leads', params={'limit': 1})

        if 'error' in result:
            print(f"❌ Query failed: {result['error']}")
        else:
            print(f"✅ crm_leads accessible")
            if result:
                lead = result[0]
                print(f"   Sample lead: {lead.get('name', 'N/A')} ({lead.get('email', 'N/A')})")

        return True

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    test_connection()
