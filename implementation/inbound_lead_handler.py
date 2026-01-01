#!/usr/bin/env python3
"""
🎯 INBOUND LEAD HANDLER
========================
Processes leads when they send a DM to Instagram.

Flow:
1. Lead sends DM → System detects username
2. Scrape profile via Instagram API
3. Calculate qualification score (0-100)
4. Save to Supabase crm_leads with proper status
5. Return profile + qualification for AI SDR (Heloise) to respond

Usage:
    from inbound_lead_handler import InboundLeadHandler

    handler = InboundLeadHandler()
    result = handler.process_inbound_dm("username")

    # Use result for AI SDR response
    if result['qualification']['status'] == 'hot':
        # Use aggressive sales approach
    elif result['qualification']['status'] == 'engaged':
        # Use nurturing approach
    else:
        # Use qualification approach

CLI:
    python3 inbound_lead_handler.py @username
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Optional
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from instagram_api_scraper import InstagramAPIScraper
from supabase_integration import SocialfyAgentIntegration

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class InboundLeadHandler:
    """
    Handles inbound DM leads from Instagram.

    Scrapes profile, qualifies the lead, saves to Supabase,
    and returns data for AI SDR to craft appropriate response.
    """

    def __init__(self, session_id: str = None):
        """
        Initialize the handler.

        Args:
            session_id: Instagram session ID (optional, will use env var if not provided)
        """
        self.scraper = InstagramAPIScraper(session_id=session_id)
        self.integration = SocialfyAgentIntegration()
        logger.info("InboundLeadHandler initialized")

    def process_inbound_dm(self, username: str) -> Dict:
        """
        Process an inbound DM from a lead.

        Args:
            username: Instagram username of the person who sent the DM

        Returns:
            Dict with:
                - profile: Full Instagram profile data
                - qualification: Score, status, classification, signals
                - crm_record: Supabase crm_leads record
                - ai_context: Context for AI SDR to use
        """
        # Remove @ if present
        username = username.lstrip('@')

        logger.info(f"Processing inbound DM from @{username}")

        result = {
            "success": False,
            "username": username,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "error": None
        }

        try:
            # Step 1: Scrape Instagram profile
            logger.info(f"📸 Scraping profile @{username}...")
            profile = self.scraper.get_profile(username)

            if not profile.get("success"):
                result["error"] = f"Failed to scrape profile: {profile.get('error', 'Unknown error')}"
                logger.error(result["error"])
                return result

            # Step 2: Calculate lead score
            logger.info(f"🎯 Calculating lead score...")
            score_data = self.scraper.calculate_lead_score(profile)

            score = score_data['score']
            signals = score_data['signals']

            # Step 3: Map score to status
            status = self._map_score_to_status(score)

            qualification = {
                "score": score,
                "status": status,
                "classification": score_data['classification'],
                "signals": signals,
                "qualified_at": datetime.now(timezone.utc).isoformat()
            }

            logger.info(f"✅ Qualification: {score}/100 → {status} ({score_data['classification']})")

            # Step 4: Prepare data for Supabase
            lead_name = profile.get('full_name') or username
            lead_email = profile.get('email') or f"{username}@instagram.placeholder"

            # Extract additional profile data
            profile_data = {
                'phone': profile.get('phone') or profile.get('phone_hint'),
                'company': profile.get('category') or profile.get('business_category'),
                'score': score,
                'status': status,
                'vertical': self._extract_vertical(profile),
                'instagram_user_id': profile.get('user_id'),
                'instagram_username': username,
                'instagram_bio': profile.get('bio'),
                'instagram_followers': profile.get('followers_count'),
                'instagram_verified': profile.get('is_verified'),
                'instagram_business': profile.get('is_business'),
                'instagram_category': profile.get('category'),
                'full_profile': profile,  # For notes generation (URL + bio)
                'qualification': qualification
            }

            # Step 5: Save to Supabase
            logger.info(f"💾 Saving to Supabase crm_leads...")
            crm_record = self.integration.save_discovered_lead(
                name=lead_name,
                email=lead_email,
                source='instagram_dm',  # Específico: veio de DM
                profile_data=profile_data
            )

            if isinstance(crm_record, dict) and 'error' in crm_record:
                logger.warning(f"⚠️ Error saving to Supabase: {crm_record['error']}")
                # Continue anyway - we still return the data for AI SDR
            else:
                # Supabase returns a list on successful insert
                if isinstance(crm_record, list) and crm_record:
                    crm_id = crm_record[0].get('id', 'unknown ID')
                elif isinstance(crm_record, dict):
                    crm_id = crm_record.get('id', 'unknown ID')
                else:
                    crm_id = 'unknown ID'
                logger.info(f"✅ Saved to CRM: {crm_id}")

            # Step 6: Build AI context for SDR
            ai_context = self._build_ai_context(profile, qualification)

            # Success result
            result.update({
                "success": True,
                "profile": profile,
                "qualification": qualification,
                "crm_record": crm_record,
                "ai_context": ai_context
            })

            logger.info(f"🎉 Successfully processed inbound lead @{username}")
            return result

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"❌ Error processing inbound DM: {e}", exc_info=True)
            return result

    def _map_score_to_status(self, score: int) -> str:
        """
        Map qualification score to CRM status.

        Args:
            score: 0-100 qualification score

        Returns:
            Status string: "hot", "engaged", or "pending"
        """
        if score >= 70:
            return "hot"
        elif score >= 40:
            return "engaged"
        else:
            return "pending"

    def _extract_vertical(self, profile: Dict) -> Optional[str]:
        """
        Extract business vertical from profile data.

        Args:
            profile: Instagram profile data

        Returns:
            Vertical string or None
        """
        # Check category
        category = profile.get('category') or profile.get('business_category')
        if category:
            return category

        # Check bio for keywords
        bio = (profile.get('bio') or '').lower()

        verticals = {
            'saas': ['saas', 'software', 'tech', 'startup'],
            'ecommerce': ['ecommerce', 'e-commerce', 'loja', 'shop'],
            'agency': ['agência', 'agency', 'marketing', 'publicidade'],
            'coaching': ['coach', 'mentoria', 'consultor', 'consultoria'],
            'creator': ['creator', 'influencer', 'criador', 'conteúdo']
        }

        for vertical, keywords in verticals.items():
            if any(kw in bio for kw in keywords):
                return vertical

        return None

    def _build_ai_context(self, profile: Dict, qualification: Dict) -> Dict:
        """
        Build context for AI SDR to craft appropriate response.

        Args:
            profile: Full Instagram profile
            qualification: Qualification data

        Returns:
            AI context dict with response guidance
        """
        score = qualification['score']
        status = qualification['status']
        signals = qualification['signals']

        # Determine response strategy
        if status == 'hot':
            strategy = "AGGRESSIVE_SALES"
            tone = "confident, direct, value-focused"
            goal = "Book a call immediately"
            approach = "They're highly qualified. Skip the nurturing - go straight for the meeting."
        elif status == 'engaged':
            strategy = "NURTURE_AND_QUALIFY"
            tone = "friendly, curious, helpful"
            goal = "Qualify further and build rapport"
            approach = "They show potential. Ask questions to understand their needs better."
        else:
            strategy = "QUALIFY_OR_DISQUALIFY"
            tone = "professional, exploratory"
            goal = "Determine if they're worth pursuing"
            approach = "Low score. Be polite but probe quickly to see if there's opportunity."

        # Extract key profile highlights
        highlights = []

        if profile.get('is_verified'):
            highlights.append("✓ Verified account")

        if profile.get('is_business'):
            highlights.append(f"✓ Business account ({profile.get('category', 'Unknown')})")

        followers = profile.get('followers_count', 0)
        if followers >= 10000:
            highlights.append(f"✓ {followers:,} followers")

        if profile.get('email') or profile.get('email_hint'):
            highlights.append("✓ Email available")

        # Check for business signals in bio
        bio = profile.get('bio', '')
        business_terms = ['ceo', 'founder', 'empreendedor', 'marketing', 'agência', 'consultor']
        found_terms = [term for term in business_terms if term in bio.lower()]
        if found_terms:
            highlights.append(f"✓ Bio mentions: {', '.join(found_terms)}")

        return {
            "score": score,
            "status": status,
            "strategy": strategy,
            "tone": tone,
            "goal": goal,
            "approach": approach,
            "highlights": highlights,
            "signals": signals,
            "profile_summary": {
                "name": profile.get('full_name'),
                "username": profile.get('username'),
                "bio": bio[:200] if bio else None,
                "followers": followers,
                "is_business": profile.get('is_business'),
                "category": profile.get('category')
            }
        }


# ===========================================
# CONVENIENCE FUNCTION
# ===========================================

def process_dm(username: str, session_id: str = None) -> Dict:
    """
    Convenience function to process a single inbound DM.

    Args:
        username: Instagram username
        session_id: Optional Instagram session ID

    Returns:
        Processing result dict
    """
    handler = InboundLeadHandler(session_id=session_id)
    return handler.process_inbound_dm(username)


# ===========================================
# CLI
# ===========================================

def main():
    """CLI for testing the inbound lead handler"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Inbound Lead Handler - Process Instagram DM leads"
    )
    parser.add_argument(
        "username",
        help="Instagram username of the person who sent DM (with or without @)"
    )
    parser.add_argument(
        "--session-id",
        help="Instagram session ID (optional, will use env var)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Save full result to JSON file"
    )
    parser.add_argument(
        "--ai-context-only",
        action="store_true",
        help="Show only AI context for SDR response"
    )

    args = parser.parse_args()

    print("\n" + "="*70)
    print("  🎯 INBOUND LEAD HANDLER")
    print("="*70 + "\n")

    try:
        # Process the DM
        result = process_dm(args.username, session_id=args.session_id)

        if not result['success']:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
            sys.exit(1)

        # Display results
        profile = result['profile']
        qualification = result['qualification']
        ai_context = result['ai_context']

        if args.ai_context_only:
            # Show only AI context
            print("🤖 AI SDR CONTEXT:\n")
            print(f"Strategy: {ai_context['strategy']}")
            print(f"Tone: {ai_context['tone']}")
            print(f"Goal: {ai_context['goal']}")
            print(f"Approach: {ai_context['approach']}")
            print(f"\nProfile Highlights:")
            for highlight in ai_context['highlights']:
                print(f"  {highlight}")
            print(f"\nKey Signals: {', '.join(ai_context['signals'][:5])}")
        else:
            # Full display
            print("✅ LEAD PROCESSED SUCCESSFULLY\n")

            # Profile summary
            print("👤 PROFILE:")
            print(f"   Username: @{profile.get('username')}")
            print(f"   Name: {profile.get('full_name', 'N/A')}")
            print(f"   User ID: {profile.get('user_id', 'N/A')}")
            print(f"   Followers: {profile.get('followers_count', 0):,}")
            print(f"   Following: {profile.get('following_count', 0):,}")
            print(f"   Posts: {profile.get('posts_count', 0):,}")

            bio = profile.get('bio', '')
            if bio:
                print(f"   Bio: {bio[:100]}{'...' if len(bio) > 100 else ''}")

            print(f"\n📊 STATUS:")
            print(f"   Business: {'Yes' if profile.get('is_business') else 'No'}")
            print(f"   Verified: {'Yes' if profile.get('is_verified') else 'No'}")
            print(f"   Private: {'Yes' if profile.get('is_private') else 'No'}")
            if profile.get('category'):
                print(f"   Category: {profile.get('category')}")

            # Qualification
            print(f"\n🎯 QUALIFICATION:")
            print(f"   Score: {qualification['score']}/100")
            print(f"   Status: {qualification['status'].upper()}")
            print(f"   Classification: {qualification['classification']}")
            print(f"   Signals: {', '.join(qualification['signals'][:5])}")
            if len(qualification['signals']) > 5:
                print(f"            + {len(qualification['signals']) - 5} more signals")

            # AI Context
            print(f"\n🤖 AI SDR GUIDANCE:")
            print(f"   Strategy: {ai_context['strategy']}")
            print(f"   Approach: {ai_context['approach']}")

            # CRM Record
            crm = result.get('crm_record', {})
            if crm and 'error' not in crm:
                crm_id = crm[0].get('id') if isinstance(crm, list) else crm.get('id')
                print(f"\n💾 CRM RECORD:")
                print(f"   Saved to Supabase: {crm_id or 'Success'}")
            elif crm and 'error' in crm:
                print(f"\n⚠️  CRM WARNING:")
                print(f"   {crm['error']}")

        # Save to file if requested
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\n💾 Full result saved to: {args.output}")

        print("\n" + "="*70 + "\n")

        # Exit with appropriate code
        sys.exit(0)

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        logger.error("Fatal error", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
