#!/usr/bin/env python3
"""
🔍 SCRAPE POST LIKERS → SUPABASE
================================
Scrape likers de um post do Instagram e salva no crm_leads.

Uso:
    python3 scrape_post_likers.py https://www.instagram.com/p/DQm5K-qEZEZ/
"""

import os
import sys
import json
import asyncio
import random
import argparse
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

# Adicionar path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from implementation.supabase_integration import SupabaseClient
from implementation.instagram_api_scraper import InstagramAPIScraper


# ============================================
# CONFIGURAÇÕES
# ============================================

INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD")
SESSION_PATH = Path(__file__).parent / "sessions" / "instagram_session.json"

# Rate limits (segurança)
MAX_LIKERS = 50  # Máximo de likers para scrape por execução
DELAY_BETWEEN_PROFILES = (2, 5)  # Segundos entre cada perfil
DELAY_SCROLL = (1, 3)  # Segundos entre scrolls


# ============================================
# FUNÇÕES AUXILIARES
# ============================================

def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def random_delay(min_sec, max_sec):
    """Delay humanizado"""
    delay = random.uniform(min_sec, max_sec)
    return delay


# ============================================
# SCRAPER
# ============================================

async def login_instagram(page):
    """Login no Instagram se necessário"""
    print("🔐 Verificando login...")

    await page.goto("https://www.instagram.com/", wait_until="domcontentloaded")
    await asyncio.sleep(3)

    # Verificar se já está logado
    current_url = page.url

    # Tentar encontrar elemento de usuário logado
    try:
        profile_link = await page.wait_for_selector(
            'svg[aria-label="Settings"], a[href*="/direct/"], svg[aria-label="Home"]',
            timeout=5000
        )
        if profile_link:
            print("✅ Já está logado!")
            return True
    except:
        pass

    # Precisa fazer login
    print("📝 Fazendo login...")

    if not INSTAGRAM_USERNAME or not INSTAGRAM_PASSWORD:
        print("❌ INSTAGRAM_USERNAME e INSTAGRAM_PASSWORD não configurados no .env")
        return False

    try:
        # Preencher username
        username_input = await page.wait_for_selector('input[name="username"]', timeout=10000)
        await username_input.fill(INSTAGRAM_USERNAME)
        await asyncio.sleep(random_delay(0.5, 1))

        # Preencher password
        password_input = await page.wait_for_selector('input[name="password"]')
        await password_input.fill(INSTAGRAM_PASSWORD)
        await asyncio.sleep(random_delay(0.5, 1))

        # Clicar em Login
        login_button = await page.wait_for_selector('button[type="submit"]')
        await login_button.click()

        # Aguardar login
        await asyncio.sleep(5)

        # Verificar se logou
        try:
            await page.wait_for_selector('svg[aria-label="Home"]', timeout=15000)
            print("✅ Login realizado com sucesso!")

            # Salvar sessão
            SESSION_PATH.parent.mkdir(exist_ok=True)
            storage_state = await page.context.storage_state()
            SESSION_PATH.write_text(json.dumps(storage_state))
            print(f"💾 Sessão salva em: {SESSION_PATH}")

            return True
        except:
            print("❌ Falha no login. Verifique usuário/senha.")
            return False

    except Exception as e:
        print(f"❌ Erro no login: {e}")
        return False


async def scrape_likers(page, post_url: str, max_likers: int = MAX_LIKERS):
    """Scrape likers de um post"""
    print(f"\n📸 Acessando post: {post_url}")

    await page.goto(post_url, wait_until="domcontentloaded")
    await asyncio.sleep(3)

    # Clicar em "likes" para abrir modal
    print("🔍 Procurando botão de likes...")

    try:
        # Tentar encontrar o link de likes (vários seletores possíveis)
        likes_selectors = [
            'a[href*="/liked_by/"]',
            'span:has-text("likes")',
            'button:has-text("others")',
            'a:has-text("likes")',
            'section a[href*="liked_by"]'
        ]

        likes_button = None
        for selector in likes_selectors:
            try:
                likes_button = await page.wait_for_selector(selector, timeout=3000)
                if likes_button:
                    break
            except:
                continue

        if not likes_button:
            # Tentar clicar no número de likes diretamente
            likes_button = await page.query_selector('section span:has-text("like")')

        if likes_button:
            await likes_button.click()
            print("✅ Modal de likes aberto")
            await asyncio.sleep(2)
        else:
            print("⚠️ Não encontrou botão de likes, tentando URL direta...")
            # Tentar acessar URL de likes diretamente
            post_id = post_url.split("/p/")[1].rstrip("/")
            await page.goto(f"https://www.instagram.com/p/{post_id}/liked_by/", wait_until="domcontentloaded")
            await asyncio.sleep(3)

    except Exception as e:
        print(f"⚠️ Erro ao abrir likes: {e}")

    # Coletar usernames dos likers
    likers = []
    seen_usernames = set()
    scroll_count = 0
    max_scrolls = 20

    print(f"📋 Coletando até {max_likers} likers...")

    while len(likers) < max_likers and scroll_count < max_scrolls:
        # Extrair usernames visíveis
        usernames = await page.evaluate('''() => {
            const users = [];
            // Procurar links de perfil no modal
            const links = document.querySelectorAll('a[href^="/"][role="link"]');
            links.forEach(link => {
                const href = link.getAttribute("href");
                if (href && href.match(/^\/[a-zA-Z0-9_.]+\/?$/) && !href.includes("/p/")) {
                    const username = href.replace(/\//g, "");
                    if (username && username.length > 0 && username !== "explore") {
                        users.push(username);
                    }
                }
            });
            return [...new Set(users)];
        }''')

        # Adicionar novos usernames
        for username in usernames:
            if username not in seen_usernames and len(likers) < max_likers:
                seen_usernames.add(username)
                likers.append({
                    "username": username,
                    "source": "post_likers",
                    "post_url": post_url,
                    "scraped_at": datetime.now().isoformat()
                })
                print(f"   [{len(likers)}/{max_likers}] @{username}")

        # Scroll no modal
        await page.evaluate('''() => {
            const modal = document.querySelector('div[role="dialog"] div[style*="overflow"]');
            if (modal) modal.scrollTop = modal.scrollHeight;
        }''')

        await asyncio.sleep(random_delay(*DELAY_SCROLL))
        scroll_count += 1

        # Verificar se chegou ao fim
        if len(usernames) == 0:
            break

    print(f"\n✅ Total de likers coletados: {len(likers)}")
    return likers


def enrich_profile(scraper: InstagramAPIScraper, username: str):
    """Buscar informações completas do perfil usando API scraper"""
    try:
        print(f"   🔍 Enriquecendo @{username} via API...")

        # Usar API scraper para obter dados completos
        profile_data = scraper.get_profile(username)

        if profile_data.get("success"):
            # Calcular score usando o método do scraper
            score_data = scraper.calculate_lead_score(profile_data)
            profile_data.update(score_data)

            # Adicionar delay para evitar rate limit
            import time
            time.sleep(random_delay(*DELAY_BETWEEN_PROFILES))

            return profile_data
        else:
            print(f"   ⚠️ Erro ao buscar @{username}: {profile_data.get('error', 'unknown')}")
            return None

    except Exception as e:
        print(f"   ⚠️ Erro ao buscar @{username}: {e}")
        return None


async def save_to_supabase(likers: list, enrich: bool = False, page=None):
    """Salvar likers no Supabase"""
    print_header("SALVANDO NO SUPABASE")

    client = SupabaseClient()
    saved_count = 0

    # Inicializar API scraper para enriquecimento
    scraper = None
    if enrich:
        try:
            scraper = InstagramAPIScraper()
            print("✅ Instagram API Scraper inicializado")
        except Exception as e:
            print(f"⚠️ Erro ao inicializar API scraper: {e}")
            print("   Continuando sem enriquecimento...")
            enrich = False

    for i, liker in enumerate(likers, 1):
        username = liker["username"]

        # Enriquecer perfil se solicitado
        profile_data = {}
        score = 30  # Score padrão
        status = "pending"  # Status padrão

        if enrich and scraper:
            print(f"   [{i}/{len(likers)}] Enriquecendo @{username}...")
            profile_data = enrich_profile(scraper, username) or {}

            if profile_data:
                # Obter score calculado pelo API scraper
                score = profile_data.get("score", 30)

                # Mapear status baseado no score
                # Valid status values: pending, viewed, engaged, hot, won, lost
                if score >= 70:
                    status = "hot"
                elif score >= 40:
                    status = "engaged"
                else:
                    status = "pending"

        # Preparar dados para salvar
        lead_data = {
            "name": profile_data.get("full_name") or username,
            "source_channel": "instagram_like",  # Específico: veio de curtida
            "status": status,
            "score": score,
            "created_at": datetime.now().isoformat()
        }

        # Adicionar email (pegar do perfil ou usar placeholder)
        if profile_data.get("email"):
            lead_data["email"] = profile_data["email"]
        elif profile_data.get("email_hint"):
            # Email hint está ofuscado, mas é melhor que nada
            lead_data["email"] = f"{username}@instagram.placeholder"
            # Adicionar hint como nota
        else:
            lead_data["email"] = f"{username}@instagram.placeholder"

        # Adicionar telefone se disponível
        if profile_data.get("phone"):
            lead_data["phone"] = profile_data["phone"]
        elif profile_data.get("phone_hint"):
            lead_data["phone"] = profile_data["phone_hint"]

        # Adicionar WhatsApp se disponível
        if profile_data.get("whatsapp_number"):
            # Adicionar ao campo phone ou criar campo customizado
            if not lead_data.get("phone"):
                lead_data["phone"] = profile_data["whatsapp_number"]

        # Adicionar company se tiver categoria
        if profile_data.get("category") or profile_data.get("business_category"):
            lead_data["company"] = profile_data.get("category") or profile_data.get("business_category")

        # Remover None values
        lead_data = {k: v for k, v in lead_data.items() if v is not None}

        # Salvar
        result = client.insert_lead(lead_data)

        if isinstance(result, list) and result:
            saved_count += 1
            lead_id = result[0].get("id", "?")

            # Construir mensagem de log com dados enriquecidos
            log_parts = [f"@{username}", f"Score: {score}", f"Status: {status}"]

            if profile_data.get("email") or profile_data.get("email_hint"):
                email_display = profile_data.get("email") or profile_data.get("email_hint")
                log_parts.append(f"Email: {email_display}")

            if profile_data.get("phone") or profile_data.get("phone_hint"):
                phone_display = profile_data.get("phone") or profile_data.get("phone_hint")
                log_parts.append(f"Phone: {phone_display}")

            if profile_data.get("whatsapp_linked"):
                log_parts.append("WhatsApp: ✓")

            if profile_data.get("user_id"):
                log_parts.append(f"UID: {profile_data['user_id']}")

            if profile_data.get("fb_id"):
                log_parts.append(f"FBID: {profile_data['fb_id']}")

            print(f"   ✅ {' | '.join(log_parts)} | ID: {lead_id[:8]}...")

        elif "error" in str(result):
            print(f"   ⚠️ @{username} → Erro: {result.get('error', 'unknown')[:50]}")
        else:
            saved_count += 1
            print(f"   ✅ @{username} → Score: {score} | Status: {status}")

    print(f"\n📊 Total salvo: {saved_count}/{len(likers)}")
    return saved_count


# ============================================
# MAIN
# ============================================

async def main(post_url: str, max_likers: int = MAX_LIKERS, enrich: bool = False):
    """Função principal"""
    print_header("SCRAPE POST LIKERS → SUPABASE")
    print(f"📸 Post: {post_url}")
    print(f"🎯 Max likers: {max_likers}")
    print(f"🔍 Enriquecer perfis: {'Sim' if enrich else 'Não'}")

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("❌ Playwright não instalado. Rode: pip install playwright && playwright install chromium")
        return

    playwright = await async_playwright().start()

    # Configurar browser
    browser_args = {
        "headless": False,  # False para debug, True para produção
        "args": ["--disable-blink-features=AutomationControlled"]
    }

    browser = await playwright.chromium.launch(**browser_args)

    # Carregar sessão se existir
    context_options = {
        "viewport": {"width": 1280, "height": 800},
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    if SESSION_PATH.exists():
        print(f"📂 Carregando sessão de: {SESSION_PATH}")
        storage_state = json.loads(SESSION_PATH.read_text())
        context_options["storage_state"] = storage_state

    context = await browser.new_context(**context_options)
    page = await context.new_page()

    try:
        # Verificar/fazer login
        if not await login_instagram(page):
            print("❌ Não foi possível fazer login")
            return

        # Scrape likers
        likers = await scrape_likers(page, post_url, max_likers)

        if not likers:
            print("⚠️ Nenhum liker encontrado")
            return

        # Salvar no Supabase
        saved = await save_to_supabase(likers, enrich=enrich, page=page if enrich else None)

        print_header("CONCLUÍDO")
        print(f"✅ {saved} leads salvos no crm_leads!")

    finally:
        # Salvar sessão atualizada
        storage_state = await context.storage_state()
        SESSION_PATH.parent.mkdir(exist_ok=True)
        SESSION_PATH.write_text(json.dumps(storage_state))

        await browser.close()
        await playwright.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Instagram post likers")
    parser.add_argument("post_url", help="URL do post do Instagram")
    parser.add_argument("--max", type=int, default=MAX_LIKERS, help=f"Máximo de likers (default: {MAX_LIKERS})")
    parser.add_argument("--enrich", action="store_true", help="Enriquecer perfis (mais lento)")

    args = parser.parse_args()

    asyncio.run(main(args.post_url, args.max, args.enrich))
