#!/usr/bin/env python3
"""
INBOUND SQUAD
=============
Agents for handling incoming leads (lead nos aborda).

Agents:
1. InboxMonitorAgent - Monitor Instagram inbox for new messages
2. LeadClassifierAgent - Classify incoming leads with AI
3. AutoResponderAgent - Generate and send contextual responses
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

    def is_known_contact(self, tenant_id: str, username: str) -> bool:
        """Check if username is in whitelist"""
        try:
            response = requests.get(
                f"{self.base_url}/tenant_known_contacts",
                headers=self.headers,
                params={
                    "tenant_id": f"eq.{tenant_id}",
                    "username": f"eq.{username}"
                }
            )
            return len(response.json()) > 0
        except:
            return False

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
        except:
            return None

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
        except:
            return False


# ============================================
# INBOX MONITOR AGENT
# ============================================

class InboxMonitorAgent(BaseAgent):
    """
    Monitors Instagram inbox for new messages.

    Features:
    - Periodic inbox polling
    - New message detection
    - Dispatch to classifier
    - Multi-account support
    """

    def __init__(self, config: Dict = None):
        super().__init__(
            name="InboxMonitor",
            description="Monitors Instagram inbox for new messages"
        )

        self.config = config or {}
        self.poll_interval = self.config.get("poll_interval", 60)  # seconds
        self._last_check_time: Dict[str, datetime] = {}  # per account
        self._seen_messages: set = set()

        self.register_capability(AgentCapability(
            name="inbox_monitoring",
            description="Monitor Instagram inbox",
            task_types=[
                "check_inbox",
                "get_new_messages",
                "start_monitoring",
                "stop_monitoring"
            ],
            requires_browser=True
        ))

        self._monitoring = False
        self._monitor_task = None

    async def _on_initialize(self):
        self.logger.info(f"InboxMonitor: Poll interval {self.poll_interval}s")

    async def execute_task(self, task: Task) -> Any:
        task_type = task.task_type
        payload = task.payload

        if task_type == "check_inbox":
            return await self._check_inbox(
                account_username=payload.get("account_username")
            )

        elif task_type == "get_new_messages":
            return await self._get_new_messages(
                account_username=payload.get("account_username")
            )

        elif task_type == "start_monitoring":
            return await self._start_monitoring(
                accounts=payload.get("accounts", [])
            )

        elif task_type == "stop_monitoring":
            return await self._stop_monitoring()

        raise ValueError(f"Unknown task type: {task_type}")

    async def _check_inbox(self, account_username: str = None) -> Dict:
        """Check inbox for messages"""
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

            # Navigate to inbox
            await page.goto(
                'https://www.instagram.com/direct/inbox/',
                wait_until='domcontentloaded',
                timeout=30000
            )
            await asyncio.sleep(3)

            # Extract conversations
            conversations = await page.evaluate('''() => {
                const convs = [];
                const items = document.querySelectorAll('div[role="listitem"]');

                items.forEach((item, index) => {
                    if (index >= 30) return;

                    const spans = item.querySelectorAll('span');
                    let username = '';
                    let preview = '';

                    spans.forEach((span, i) => {
                        const text = span.textContent?.trim();
                        if (i === 0 && text) username = text;
                        if (i === 1 && text) preview = text;
                    });

                    // Check for unread indicator
                    const hasUnread = item.querySelector('[class*="unread"], [class*="badge"]') !== null;

                    // Get timestamp if visible
                    const timeEl = item.querySelector('time');
                    const timestamp = timeEl ? timeEl.getAttribute('datetime') : null;

                    if (username) {
                        convs.push({
                            username,
                            preview: preview.substring(0, 100),
                            has_unread: hasUnread,
                            timestamp
                        });
                    }
                });

                return convs;
            }''')

            await browser.close()
            await playwright.stop()

            # Filter new messages
            new_messages = []
            for conv in conversations:
                msg_id = f"{conv['username']}:{conv['preview'][:20]}"
                if msg_id not in self._seen_messages:
                    self._seen_messages.add(msg_id)
                    new_messages.append(conv)

            self._last_check_time[account_username or "default"] = datetime.now()

            return {
                "success": True,
                "total_conversations": len(conversations),
                "new_messages": new_messages,
                "unread_count": len([c for c in conversations if c.get("has_unread")]),
                "checked_at": datetime.now().isoformat()
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _get_new_messages(self, account_username: str = None) -> Dict:
        """Get only new messages since last check"""
        result = await self._check_inbox(account_username)

        if result.get("success"):
            return {
                "success": True,
                "messages": result.get("new_messages", []),
                "count": len(result.get("new_messages", []))
            }

        return result

    async def _start_monitoring(self, accounts: List[str] = None) -> Dict:
        """Start continuous inbox monitoring"""
        if self._monitoring:
            return {"success": False, "error": "Already monitoring"}

        self._monitoring = True
        accounts = accounts or ["default"]

        async def monitor_loop():
            while self._monitoring:
                for account in accounts:
                    try:
                        result = await self._check_inbox(account)
                        new_msgs = result.get("new_messages", [])

                        if new_msgs:
                            self.logger.info(f"Found {len(new_msgs)} new messages")
                            # Dispatch to classifier (via callback or queue)
                            # This would typically call the orchestrator

                    except Exception as e:
                        self.logger.error(f"Monitor error for {account}: {e}")

                await asyncio.sleep(self.poll_interval)

        self._monitor_task = asyncio.create_task(monitor_loop())

        return {
            "success": True,
            "message": f"Monitoring started for {len(accounts)} accounts",
            "poll_interval": self.poll_interval
        }

    async def _stop_monitoring(self) -> Dict:
        """Stop inbox monitoring"""
        self._monitoring = False

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        return {"success": True, "message": "Monitoring stopped"}


# ============================================
# LEAD CLASSIFIER AGENT
# ============================================

class LeadClassifierAgent(BaseAgent):
    """
    Classifies incoming leads using AI.

    Classifications:
    - LEAD_HOT: High buying intent
    - LEAD_WARM: Moderate interest
    - LEAD_COLD: First contact, unclear intent
    - PESSOAL: Personal contact (friend, family)
    - SPAM: Spam or bot messages
    """

    def __init__(self, config: Dict = None):
        super().__init__(
            name="LeadClassifier",
            description="Classifies incoming leads with AI"
        )

        self.config = config or {}
        self.db = SupabaseClient()

        self.register_capability(AgentCapability(
            name="lead_classification",
            description="Classify leads with AI",
            task_types=[
                "classify_lead",
                "check_whitelist",
                "batch_classify"
            ],
            requires_api_key="GEMINI_API_KEY"
        ))

    async def _on_initialize(self):
        self.logger.info("LeadClassifier: Ready with Gemini AI")

    async def execute_task(self, task: Task) -> Any:
        task_type = task.task_type
        payload = task.payload

        if task_type == "classify_lead":
            return await self._classify_lead(
                username=payload.get("username"),
                message=payload.get("message"),
                tenant_id=payload.get("tenant_id"),
                persona_id=payload.get("persona_id")
            )

        elif task_type == "check_whitelist":
            return self._check_whitelist(
                tenant_id=payload.get("tenant_id"),
                username=payload.get("username")
            )

        raise ValueError(f"Unknown task type: {task_type}")

    def _check_whitelist(self, tenant_id: str, username: str) -> Dict:
        """Check if user is in whitelist"""
        is_known = self.db.is_known_contact(tenant_id, username)

        return {
            "username": username,
            "is_known_contact": is_known,
            "skip_classification": is_known
        }

    async def _classify_lead(
        self,
        username: str,
        message: str,
        tenant_id: str,
        persona_id: str = None
    ) -> Dict:
        """Classify a lead using AI"""

        # First check whitelist
        whitelist_check = self._check_whitelist(tenant_id, username)
        if whitelist_check.get("is_known_contact"):
            return {
                "success": True,
                "username": username,
                "classification": "PESSOAL",
                "score": 0,
                "reasoning": "Known contact in whitelist",
                "needs_profile": False
            }

        # Get persona context
        persona = None
        if tenant_id:
            persona = self.db.get_active_persona(tenant_id)

        # Classify with AI
        try:
            import google.generativeai as genai

            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not configured")

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.5-flash")

            persona_context = ""
            if persona:
                persona_context = f"""
Contexto do ICP do negócio:
- Dores do cliente ideal: {persona.get('icp_pain_points', 'N/A')}
- Perfil ideal: {persona.get('icp_profile', 'N/A')}
- Tom de voz: {persona.get('tone_of_voice', 'profissional')}
"""

            prompt = f"""Você é um classificador de leads para marketing no Instagram.

Analise esta mensagem recebida de @{username}:
"{message}"

{persona_context}

Classifique esta mensagem em UMA das categorias:
- LEAD_HOT: Interesse claro em comprar/contratar (ex: "quanto custa?", "quero saber mais sobre o serviço", "como funciona o pagamento?")
- LEAD_WARM: Interesse moderado, engajamento positivo (ex: "legal seu conteúdo", "me conta mais", "vi seu post")
- LEAD_COLD: Primeira interação, sem interesse claro ainda (ex: "oi", "opa", saudação genérica)
- PESSOAL: Mensagem pessoal, não é lead (amigo, família, parceiro conhecido)
- SPAM: Propaganda, bot, mensagem irrelevante, proposta de parceria não solicitada

Também:
1. Dê uma pontuação de 0 a 100 para o potencial deste lead
2. Sugira uma resposta apropriada para esta mensagem
3. Indique se precisamos buscar o perfil deste usuário (needs_profile)

Responda APENAS em JSON:
{{
    "classification": "LEAD_HOT|LEAD_WARM|LEAD_COLD|PESSOAL|SPAM",
    "score": 0-100,
    "reasoning": "explicação curta",
    "suggested_response": "sugestão de resposta personalizada",
    "needs_profile": true|false
}}
"""

            response = model.generate_content(prompt)
            response_text = response.text.strip()

            # Parse JSON
            import re
            if response_text.startswith("```"):
                response_text = re.sub(r'^```json?\n?', '', response_text)
                response_text = re.sub(r'\n?```$', '', response_text)

            result = json.loads(response_text)

            # Save to database
            self.db.save_classified_lead({
                "tenant_id": tenant_id,
                "persona_id": persona_id,
                "username": username,
                "original_message": message,
                "classification": result["classification"],
                "score": result["score"],
                "ai_reasoning": result["reasoning"],
                "suggested_response": result.get("suggested_response"),
                "needs_profile_fetch": result.get("needs_profile", False),
                "classified_at": datetime.now().isoformat()
            })

            return {
                "success": True,
                "username": username,
                "classification": result["classification"],
                "score": result["score"],
                "reasoning": result["reasoning"],
                "suggested_response": result.get("suggested_response"),
                "needs_profile": result.get("needs_profile", False)
            }

        except Exception as e:
            self.logger.error(f"Classification error: {e}")
            return {
                "success": False,
                "username": username,
                "classification": "LEAD_COLD",
                "score": 50,
                "reasoning": f"Classification failed: {str(e)}",
                "needs_profile": True
            }


# ============================================
# AUTO RESPONDER AGENT
# ============================================

class AutoResponderAgent(BaseAgent):
    """
    Generates and sends contextual responses to leads.

    Features:
    - Context-aware responses
    - Persona tone adaptation
    - Qualifying questions
    - Smart follow-ups
    """

    def __init__(self, config: Dict = None):
        super().__init__(
            name="AutoResponder",
            description="Generates contextual responses to leads"
        )

        self.config = config or {}
        self.db = SupabaseClient()

        # Default response templates by classification
        self.templates = self.config.get("templates", {
            "LEAD_HOT": "Que legal seu interesse, {first_name}! {response} Posso te mandar mais detalhes?",
            "LEAD_WARM": "Oi {first_name}! {response} Quer que eu te explique melhor como funciona?",
            "LEAD_COLD": "Oi {first_name}! Que bom te ver por aqui! {response}",
            "PESSOAL": None,  # Don't auto-respond to personal
            "SPAM": None  # Don't respond to spam
        })

        self.register_capability(AgentCapability(
            name="auto_response",
            description="Generate and send contextual responses",
            task_types=[
                "generate_response",
                "send_response",
                "generate_qualifying_question"
            ],
            requires_api_key="GEMINI_API_KEY",
            requires_browser=True
        ))

    async def _on_initialize(self):
        self.logger.info("AutoResponder: Ready")

    async def execute_task(self, task: Task) -> Any:
        task_type = task.task_type
        payload = task.payload

        if task_type == "generate_response":
            return await self._generate_response(
                username=payload.get("username"),
                original_message=payload.get("original_message"),
                classification=payload.get("classification", {}),
                profile=payload.get("profile"),
                tenant_id=payload.get("tenant_id")
            )

        elif task_type == "send_response":
            return await self._send_response(
                username=payload.get("username"),
                message=payload.get("message")
            )

        elif task_type == "generate_qualifying_question":
            return await self._generate_qualifying_question(
                username=payload.get("username"),
                classification=payload.get("classification"),
                profile=payload.get("profile")
            )

        raise ValueError(f"Unknown task type: {task_type}")

    async def _generate_response(
        self,
        username: str,
        original_message: str,
        classification: Dict,
        profile: Dict = None,
        tenant_id: str = None
    ) -> Dict:
        """Generate a contextual response"""

        class_type = classification.get("classification", "LEAD_COLD")

        # Don't respond to spam or personal
        if class_type in ["SPAM", "PESSOAL"]:
            return {
                "success": True,
                "username": username,
                "should_respond": False,
                "reason": f"No auto-response for {class_type}"
            }

        # Get persona
        persona = None
        if tenant_id:
            persona = self.db.get_active_persona(tenant_id)

        # Generate response with AI
        try:
            import google.generativeai as genai

            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                # Use suggested response from classifier
                return {
                    "success": True,
                    "username": username,
                    "response": classification.get("suggested_response", "Oi! Como posso te ajudar?"),
                    "should_respond": True,
                    "method": "classifier_fallback"
                }

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.5-flash")

            # Build context
            profile_context = ""
            if profile:
                profile_context = f"""
Perfil do lead:
- Nome: {profile.get('full_name', username)}
- Bio: {profile.get('bio', 'N/A')}
- Seguidores: {profile.get('followers_count', 'N/A')}
"""

            persona_context = ""
            if persona:
                persona_context = f"""
Tom de voz da marca: {persona.get('tone_of_voice', 'amigável e profissional')}
Ofertas/serviços: {persona.get('main_offers', 'N/A')}
"""

            prompt = f"""Você é um assistente de vendas no Instagram. Gere uma resposta para esta mensagem.

Mensagem recebida de @{username}:
"{original_message}"

Classificação: {class_type} (score: {classification.get('score', 50)})

{profile_context}
{persona_context}

Regras:
- Seja natural e amigável, como uma pessoa real
- Máximo 2-3 frases
- Se for LEAD_HOT, seja mais direto sobre próximos passos
- Se for LEAD_WARM, gere curiosidade e engajamento
- Se for LEAD_COLD, seja acolhedor e faça uma pergunta
- NÃO use emojis demais (máximo 1-2)
- Use o primeiro nome se disponível

Responda APENAS com a mensagem de resposta, sem formatação."""

            response = model.generate_content(prompt)
            response_text = response.text.strip()

            # Get first name
            first_name = username
            if profile and profile.get("full_name"):
                first_name = profile["full_name"].split()[0]

            return {
                "success": True,
                "username": username,
                "response": response_text,
                "should_respond": True,
                "classification": class_type,
                "method": "gemini"
            }

        except Exception as e:
            self.logger.error(f"Response generation error: {e}")

            # Fallback to suggested response
            return {
                "success": True,
                "username": username,
                "response": classification.get("suggested_response", "Oi! Como posso te ajudar?"),
                "should_respond": True,
                "method": "fallback"
            }

    async def _send_response(self, username: str, message: str) -> Dict:
        """Send a response via DM"""
        try:
            from playwright.async_api import async_playwright
            import random

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

            # Navigate to conversation
            await page.goto(
                f'https://www.instagram.com/direct/t/{username}/',
                wait_until='domcontentloaded',
                timeout=30000
            )
            await asyncio.sleep(2)

            # Find and fill message input
            message_input = await page.wait_for_selector(
                'textarea[placeholder*="Message"], div[contenteditable="true"]',
                timeout=10000
            )

            if message_input:
                # Human-like typing
                for char in message:
                    await message_input.type(char, delay=random.randint(30, 70))

                await asyncio.sleep(0.5)
                await page.keyboard.press('Enter')
                await asyncio.sleep(1)

                await browser.close()
                await playwright.stop()

                return {
                    "success": True,
                    "username": username,
                    "message_sent": message,
                    "sent_at": datetime.now().isoformat()
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

    async def _generate_qualifying_question(
        self,
        username: str,
        classification: Dict,
        profile: Dict = None
    ) -> Dict:
        """Generate a qualifying question to better understand the lead"""

        questions = {
            "LEAD_HOT": [
                "Você já tem alguma solução em uso atualmente?",
                "Qual é o principal desafio que você está enfrentando?",
                "Quando você pretende tomar uma decisão?"
            ],
            "LEAD_WARM": [
                "O que mais te chamou atenção no meu conteúdo?",
                "Você trabalha com o que exatamente?",
                "Já tentou resolver esse problema antes?"
            ],
            "LEAD_COLD": [
                "Como posso te ajudar?",
                "O que te trouxe aqui?",
                "Tá curtindo o conteúdo?"
            ]
        }

        class_type = classification.get("classification", "LEAD_COLD")
        available_questions = questions.get(class_type, questions["LEAD_COLD"])

        import random
        question = random.choice(available_questions)

        return {
            "success": True,
            "username": username,
            "qualifying_question": question,
            "classification": class_type
        }


# ============================================
# FACTORY FUNCTION
# ============================================

def create_inbound_squad(config: Dict = None) -> Dict[str, BaseAgent]:
    """Create all inbound squad agents"""
    config = config or {}

    return {
        "InboxMonitor": InboxMonitorAgent(config.get("monitor")),
        "LeadClassifier": LeadClassifierAgent(config.get("classifier")),
        "AutoResponder": AutoResponderAgent(config.get("responder"))
    }
