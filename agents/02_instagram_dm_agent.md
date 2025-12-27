# SUBAGENTE 2: Instagram DM Agent

## Objetivo
Criar o agente de automação de DMs do Instagram usando Playwright, seguindo o framework "ii" (Information + Implementation).

## Contexto
Você é um subagente especializado em automação de browser com Playwright. Sua tarefa é criar um agente autônomo que envia DMs personalizados no Instagram.

## Dependências
- SUBAGENTE 1 deve ter completado (Playwright instalado, .env configurado)

---

## TAREFAS A EXECUTAR

### 1. Criar instruction/instagram_dm_agent.md (O Cérebro)

Este é o arquivo `information.md` do framework "ii":

```markdown
# Instagram DM Agent - Information

## GOAL
Enviar mensagens diretas personalizadas para leads qualificados no Instagram de forma autônoma, respeitando os limites da plataforma para evitar banimento.

## CONTEXT
Este agente opera como parte do AgenticOS para automatizar outreach no Instagram. Os leads são pessoas que engajaram com nossos posts (likes, comments, shares) ou foram scrapeados de outras fontes.

## WORKFLOW
1. Carregar sessão salva do Instagram (ou fazer login se não existir)
2. Ler lista de leads do banco de dados ou CSV
3. Para cada lead:
   a. Verificar se já foi contactado
   b. Navegar até o perfil
   c. Abrir conversa de DM
   d. Enviar mensagem personalizada
   e. Registrar no banco de dados
   f. Aguardar delay aleatório (30-60s)
4. Respeitar limites: 10 DMs/hora, 200 DMs/dia
5. Salvar sessão ao finalizar

## CONSTRAINTS (Learned from previous runs)
- NEVER send more than 10 DMs per hour
- NEVER send more than 200 DMs per day
- ALWAYS wait 30-60 seconds between DMs
- ALWAYS save session after successful login
- IF login fails with 2FA, wait for manual intervention
- IF rate limited, stop immediately and log error
- NEVER send DM to private accounts (can't DM without follow)
- ALWAYS check if DM was already sent to avoid duplicates

## MESSAGE TEMPLATES
### Template 1: Initial Outreach
```
Hey {first_name}! 👋

Noticed you engaged with our content - thanks for that!

We built something that might interest you: an AI system that automates Instagram outreach at scale.

Would love to show you how it works. Interested?
```

### Template 2: Value-First
```
{first_name}, quick question...

Do you spend hours manually DMing prospects on Instagram?

We automated this entire process and now send 200+ personalized DMs daily on autopilot.

Want me to show you how?
```

## ERROR HANDLING
- Screenshot on error → Send to Anthropic API for analysis
- Update this file with new constraints learned
- Retry failed actions up to 3 times with exponential backoff

## METRICS TO TRACK
- DMs sent today
- DMs sent this hour
- Success rate
- Response rate (if trackable)
- Errors encountered
```

### 2. Criar implementation/instagram_dm_agent.py (O Executor)

```python
"""
Instagram DM Agent - Implementation
Framework: ii (Information + Implementation)
"""

import os
import sys
import json
import random
import logging
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass

from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Setup logging
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / "instagram_dm.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("InstagramDMAgent")

# Configuration
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD")
SESSION_PATH = Path(__file__).parent.parent / "sessions" / "instagram_session.json"
DATA_PATH = Path(__file__).parent.parent / "data"

# Rate Limits
MAX_DMS_PER_HOUR = 10
MAX_DMS_PER_DAY = 200
MIN_DELAY_SECONDS = 30
MAX_DELAY_SECONDS = 60


@dataclass
class Lead:
    username: str
    full_name: Optional[str] = None
    bio: Optional[str] = None
    source: Optional[str] = None

    @property
    def first_name(self) -> str:
        if self.full_name:
            return self.full_name.split()[0]
        return self.username


@dataclass
class DMResult:
    lead: Lead
    success: bool
    message_sent: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class InstagramDMAgent:
    """
    Autonomous Instagram DM Agent using Playwright
    """

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.dms_sent_today = 0
        self.dms_sent_this_hour = 0
        self.hour_start = datetime.now()
        self.results: List[DMResult] = []

    async def start(self):
        """Initialize browser and load session"""
        logger.info("Starting Instagram DM Agent...")

        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=['--disable-blink-features=AutomationControlled']
        )

        # Try to load existing session
        if SESSION_PATH.exists():
            logger.info("Loading existing session...")
            storage_state = json.loads(SESSION_PATH.read_text())
            self.context = await self.browser.new_context(
                storage_state=storage_state,
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
        else:
            logger.info("No session found, will need to login...")
            self.context = await self.browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )

        self.page = await self.context.new_page()

    async def login(self) -> bool:
        """Login to Instagram and save session"""
        logger.info("Logging into Instagram...")

        try:
            await self.page.goto('https://www.instagram.com/accounts/login/')
            await self.page.wait_for_timeout(3000)

            # Check if already logged in
            if 'login' not in self.page.url:
                logger.info("Already logged in!")
                return True

            # Fill login form
            await self.page.fill('input[name="username"]', INSTAGRAM_USERNAME)
            await self.page.fill('input[name="password"]', INSTAGRAM_PASSWORD)
            await self.page.click('button[type="submit"]')

            # Wait for navigation
            await self.page.wait_for_timeout(5000)

            # Check for 2FA
            if 'challenge' in self.page.url or 'two_factor' in self.page.url:
                logger.warning("2FA required! Please complete manually...")
                # Wait for manual 2FA completion
                await self.page.wait_for_url('**/instagram.com/**', timeout=120000)

            # Handle "Save Login Info" popup
            try:
                save_button = await self.page.wait_for_selector(
                    'button:has-text("Save Info")', timeout=5000
                )
                if save_button:
                    await save_button.click()
            except:
                pass

            # Handle "Turn on Notifications" popup
            try:
                not_now = await self.page.wait_for_selector(
                    'button:has-text("Not Now")', timeout=5000
                )
                if not_now:
                    await not_now.click()
            except:
                pass

            # Save session
            await self.save_session()
            logger.info("Login successful!")
            return True

        except Exception as e:
            logger.error(f"Login failed: {e}")
            await self.take_screenshot("login_error")
            return False

    async def save_session(self):
        """Save browser session for reuse"""
        logger.info("Saving session...")
        SESSION_PATH.parent.mkdir(exist_ok=True)
        storage = await self.context.storage_state()
        SESSION_PATH.write_text(json.dumps(storage, indent=2))
        logger.info(f"Session saved to {SESSION_PATH}")

    async def take_screenshot(self, name: str) -> Path:
        """Take screenshot for debugging"""
        screenshot_path = LOG_DIR / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        await self.page.screenshot(path=str(screenshot_path))
        logger.info(f"Screenshot saved: {screenshot_path}")
        return screenshot_path

    def check_rate_limits(self) -> bool:
        """Check if we can send more DMs"""
        # Reset hourly counter if hour passed
        if datetime.now() - self.hour_start > timedelta(hours=1):
            self.dms_sent_this_hour = 0
            self.hour_start = datetime.now()

        if self.dms_sent_this_hour >= MAX_DMS_PER_HOUR:
            logger.warning(f"Hourly limit reached ({MAX_DMS_PER_HOUR} DMs)")
            return False

        if self.dms_sent_today >= MAX_DMS_PER_DAY:
            logger.warning(f"Daily limit reached ({MAX_DMS_PER_DAY} DMs)")
            return False

        return True

    def get_personalized_message(self, lead: Lead, template: int = 1) -> str:
        """Generate personalized message for lead"""
        templates = {
            1: f"""Hey {lead.first_name}! 👋

Noticed you engaged with our content - thanks for that!

We built something that might interest you: an AI system that automates Instagram outreach at scale.

Would love to show you how it works. Interested?""",

            2: f"""{lead.first_name}, quick question...

Do you spend hours manually DMing prospects on Instagram?

We automated this entire process and now send 200+ personalized DMs daily on autopilot.

Want me to show you how?"""
        }

        return templates.get(template, templates[1])

    async def send_dm(self, lead: Lead, message: str) -> DMResult:
        """Send DM to a single lead"""
        logger.info(f"Sending DM to @{lead.username}...")

        try:
            # Navigate to DM page
            await self.page.goto(f'https://www.instagram.com/direct/t/{lead.username}/')
            await self.page.wait_for_timeout(3000)

            # Alternative: Go to profile and click Message button
            if 'direct' not in self.page.url:
                await self.page.goto(f'https://www.instagram.com/{lead.username}/')
                await self.page.wait_for_timeout(2000)

                # Check if account is private
                private_indicator = await self.page.query_selector('text="This Account is Private"')
                if private_indicator:
                    logger.warning(f"@{lead.username} is private, skipping...")
                    return DMResult(lead=lead, success=False, error="Account is private")

                # Click Message button
                message_btn = await self.page.query_selector('div[role="button"]:has-text("Message")')
                if message_btn:
                    await message_btn.click()
                    await self.page.wait_for_timeout(2000)
                else:
                    logger.error(f"Message button not found for @{lead.username}")
                    return DMResult(lead=lead, success=False, error="Message button not found")

            # Find message input
            message_input = await self.page.query_selector('textarea[placeholder*="Message"]')
            if not message_input:
                message_input = await self.page.query_selector('div[role="textbox"]')

            if not message_input:
                await self.take_screenshot(f"no_input_{lead.username}")
                return DMResult(lead=lead, success=False, error="Message input not found")

            # Type message
            await message_input.fill(message)
            await self.page.wait_for_timeout(500)

            # Send message
            send_btn = await self.page.query_selector('button:has-text("Send")')
            if send_btn:
                await send_btn.click()
            else:
                # Try pressing Enter
                await message_input.press('Enter')

            await self.page.wait_for_timeout(2000)

            # Update counters
            self.dms_sent_today += 1
            self.dms_sent_this_hour += 1

            logger.info(f"DM sent successfully to @{lead.username}")
            return DMResult(lead=lead, success=True, message_sent=message)

        except Exception as e:
            logger.error(f"Failed to send DM to @{lead.username}: {e}")
            await self.take_screenshot(f"error_{lead.username}")
            return DMResult(lead=lead, success=False, error=str(e))

    async def run_campaign(self, leads: List[Lead], template: int = 1):
        """Run DM campaign for list of leads"""
        logger.info(f"Starting campaign with {len(leads)} leads...")

        # Ensure logged in
        await self.page.goto('https://www.instagram.com/')
        await self.page.wait_for_timeout(2000)

        if 'login' in self.page.url:
            success = await self.login()
            if not success:
                logger.error("Failed to login, aborting campaign")
                return

        for i, lead in enumerate(leads):
            # Check rate limits
            if not self.check_rate_limits():
                logger.info("Rate limit reached, pausing campaign...")
                break

            # Send DM
            message = self.get_personalized_message(lead, template)
            result = await self.send_dm(lead, message)
            self.results.append(result)

            # Log progress
            logger.info(f"Progress: {i+1}/{len(leads)} | Success: {result.success}")

            # Random delay
            if i < len(leads) - 1:
                delay = random.randint(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
                logger.info(f"Waiting {delay} seconds before next DM...")
                await asyncio.sleep(delay)

        # Save session after campaign
        await self.save_session()

        # Log summary
        successful = sum(1 for r in self.results if r.success)
        logger.info(f"Campaign complete! Sent: {successful}/{len(self.results)}")

    async def stop(self):
        """Cleanup and close browser"""
        if self.context:
            await self.save_session()
            await self.context.close()
        if self.browser:
            await self.browser.close()
        logger.info("Agent stopped")


def load_leads_from_csv(filepath: Path) -> List[Lead]:
    """Load leads from CSV file"""
    import csv
    leads = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            leads.append(Lead(
                username=row.get('username', ''),
                full_name=row.get('full_name', row.get('name', '')),
                bio=row.get('bio', ''),
                source=row.get('source', 'csv')
            ))
    return leads


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Instagram DM Agent')
    parser.add_argument('--leads', type=str, help='Path to leads CSV file')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--login-only', action='store_true', help='Only perform login and save session')
    parser.add_argument('--template', type=int, default=1, help='Message template to use (1 or 2)')
    args = parser.parse_args()

    agent = InstagramDMAgent(headless=args.headless)

    try:
        await agent.start()

        if args.login_only:
            await agent.login()
            logger.info("Login complete. Session saved.")
        else:
            # Load leads
            leads_file = Path(args.leads) if args.leads else DATA_PATH / "instagram_leads.csv"

            if not leads_file.exists():
                logger.error(f"Leads file not found: {leads_file}")
                logger.info("Creating sample leads file...")

                # Create sample leads file
                sample_leads = [
                    {"username": "test_user_1", "full_name": "Test User", "source": "sample"},
                    {"username": "test_user_2", "full_name": "Another User", "source": "sample"},
                ]

                leads_file.parent.mkdir(exist_ok=True)
                import csv
                with open(leads_file, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=['username', 'full_name', 'source'])
                    writer.writeheader()
                    writer.writerows(sample_leads)

                logger.info(f"Sample leads file created: {leads_file}")
                return

            leads = load_leads_from_csv(leads_file)
            await agent.run_campaign(leads, template=args.template)

    finally:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
```

### 3. Criar data/instagram_leads.csv (Sample Data)

```csv
username,full_name,bio,source
entrepreneur_daily,John Smith,Building businesses 🚀,sample
marketing_tips,Sarah Johnson,Digital Marketing Expert,sample
startup_founder,Mike Chen,Founder @TechStartup,sample
growth_hacker,Lisa Wang,Growth at Scale,sample
business_coach,David Brown,Helping entrepreneurs succeed,sample
```

### 4. Criar tests/test_instagram_login.py

```python
"""
Test Instagram login functionality
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from implementation.instagram_dm_agent import InstagramDMAgent


async def test_login():
    """Test that we can login to Instagram"""
    agent = InstagramDMAgent(headless=False)  # Use headed mode for testing

    try:
        await agent.start()
        success = await agent.login()

        if success:
            print("✅ Login successful!")
            print(f"Session saved to: {agent.SESSION_PATH}")
        else:
            print("❌ Login failed!")

    finally:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(test_login())
```

---

## VALIDAÇÃO

Após completar, executar:

```bash
# Verificar arquivos criados
ls -la instruction/instagram_dm_agent.md
ls -la implementation/instagram_dm_agent.py
ls -la data/instagram_leads.csv
ls -la tests/test_instagram_login.py

# Testar import
python -c "from implementation.instagram_dm_agent import InstagramDMAgent; print('Import OK')"

# Rodar teste de login (requer credenciais em .env)
# python tests/test_instagram_login.py
```

---

## OUTPUT ESPERADO

```
STATUS: SUCCESS / FAILURE

ARQUIVOS CRIADOS:
- instruction/instagram_dm_agent.md: OK
- implementation/instagram_dm_agent.py: OK
- data/instagram_leads.csv: OK
- tests/test_instagram_login.py: OK

FUNCIONALIDADES:
- Login com sessão persistente: IMPLEMENTADO
- Envio de DMs: IMPLEMENTADO
- Rate limiting: IMPLEMENTADO
- Logging: IMPLEMENTADO
- Templates de mensagem: IMPLEMENTADO

PRÓXIMOS PASSOS:
1. Configurar INSTAGRAM_USERNAME e INSTAGRAM_PASSWORD no .env
2. Executar: python tests/test_instagram_login.py
3. Completar 2FA manualmente (se necessário)
4. Executar: python implementation/instagram_dm_agent.py --leads data/instagram_leads.csv
```
