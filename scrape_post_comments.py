#!/usr/bin/env python3
"""
💬 SCRAPE POST COMMENTS → SUPABASE
==================================
Scrape usuários que comentaram em um post do Instagram e salva no crm_leads.

Uso:
    python3 scrape_post_comments.py https://www.instagram.com/p/DQm5K-qEZEZ/
    python3 scrape_post_comments.py https://www.instagram.com/p/DQm5K-qEZEZ/ --max 30 --enrich
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
MAX_COMMENTERS = 50  # Máximo de commenters para scrape por execução
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


async def scrape_commenters(page, post_url: str, max_commenters: int = MAX_COMMENTERS):
    """Scrape usuários que comentaram em um post"""
    print(f"\n📸 Acessando post: {post_url}")

    await page.goto(post_url, wait_until="domcontentloaded")
    await asyncio.sleep(3)

    # Coletar usernames dos comentaristas
    commenters = []
    seen_usernames = set()
    scroll_count = 0
    max_scrolls = 20

    print(f"📋 Coletando até {max_commenters} comentaristas...")

    # Tentar expandir comentários se houver "View all X comments"
    try:
        view_all = await page.query_selector('span:has-text("View all"), span:has-text("Ver todos")')
        if view_all:
            await view_all.click()
            await asyncio.sleep(2)
    except:
        pass

    while len(commenters) < max_commenters and scroll_count < max_scrolls:
        # Extrair usernames dos comentários
        comment_data = await page.evaluate('''() => {
            const comments = [];
            // Procurar links de perfil em comentários
            const commentElements = document.querySelectorAll('ul ul li, div[role="button"] a[href^="/"]');

            commentElements.forEach(el => {
                // Procurar link do username dentro do comentário
                const userLink = el.querySelector('a[href^="/"][role="link"]') || el;
                if (userLink && userLink.href) {
                    const href = new URL(userLink.href).pathname;
                    if (href.match(/^\/[a-zA-Z0-9_.]+\/?$/) && !href.includes("/p/")) {
                        const username = href.replace(/\//g, "");
                        if (username && username.length > 0 && username !== "explore") {
                            // Tentar pegar o texto do comentário
                            const commentText = el.textContent || "";
                            comments.push({
                                username: username,
                                comment_preview: commentText.substring(0, 100)
                            });
                        }
                    }
                }
            });
            return comments;
        }''')

        # Adicionar novos usernames
        for data in comment_data:
            username = data.get('username')
            if username and username not in seen_usernames and len(commenters) < max_commenters:
                seen_usernames.add(username)
                commenters.append({
                    "username": username,
                    "comment_preview": data.get('comment_preview', ''),
                    "source": "post_comment",
                    "post_url": post_url,
                    "scraped_at": datetime.now().isoformat()
                })
                print(f"   [{len(commenters)}/{max_commenters}] @{username}")

        # Scroll para carregar mais comentários
        await page.evaluate('''() => {
            const comments = document.querySelector('ul[class*="Comment"]');
            if (comments) comments.scrollTop = comments.scrollHeight;
            // Também scrollar na página principal
            window.scrollBy(0, 300);
        }''')

        await asyncio.sleep(random_delay(*DELAY_SCROLL))
        scroll_count += 1

        # Verificar se chegou ao fim
        if len(comment_data) == 0 and scroll_count > 3:
            break

    print(f"\n✅ Total de comentaristas coletados: {len(commenters)}")
    return commenters


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


async def save_to_supabase(commenters: list, enrich: bool = False):
    """Salvar comentaristas no Supabase"""
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

    for i, commenter in enumerate(commenters, 1):
        username = commenter["username"]

        # Enriquecer perfil se solicitado
        profile_data = {}
        score = 35  # Score padrão para comentaristas (um pouco mais que likers)
        status = "pending"

        if enrich and scraper:
            print(f"   [{i}/{len(commenters)}] Enriquecendo @{username}...")
            profile_data = enrich_profile(scraper, username) or {}

            if profile_data:
                score = profile_data.get("score", 35)

                if score >= 70:
                    status = "hot"
                elif score >= 40:
                    status = "engaged"
                else:
                    status = "pending"

        # Preparar dados para salvar
        lead_data = {
            "name": profile_data.get("full_name") or username,
            "source_channel": "instagram_comment",  # Específico: veio de comentário
            "status": status,
            "score": score,
            "created_at": datetime.now().isoformat()
        }

        # Adicionar email se disponível
        if profile_data.get("email"):
            lead_data["email"] = profile_data["email"]
        else:
            lead_data["email"] = f"{username}@instagram.placeholder"

        # Adicionar telefone se disponível
        if profile_data.get("phone"):
            lead_data["phone"] = profile_data["phone"]
        elif profile_data.get("phone_hint"):
            lead_data["phone"] = profile_data["phone_hint"]

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
            print(f"   ✅ @{username} | Score: {score} | Status: {status} | ID: {lead_id[:8]}...")
        elif "error" in str(result):
            print(f"   ⚠️ @{username} → Erro: {result.get('error', 'unknown')[:50]}")
        else:
            saved_count += 1
            print(f"   ✅ @{username} → Score: {score} | Status: {status}")

    print(f"\n📊 Total salvo: {saved_count}/{len(commenters)}")
    return saved_count


# ============================================
# MAIN
# ============================================

async def main(post_url: str, max_commenters: int = MAX_COMMENTERS, enrich: bool = False):
    """Função principal"""
    print_header("SCRAPE POST COMMENTS → SUPABASE")
    print(f"📸 Post: {post_url}")
    print(f"🎯 Max comentaristas: {max_commenters}")
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

        # Scrape commenters
        commenters = await scrape_commenters(page, post_url, max_commenters)

        if not commenters:
            print("⚠️ Nenhum comentarista encontrado")
            return

        # Salvar no Supabase
        saved = await save_to_supabase(commenters, enrich=enrich)

        print_header("CONCLUÍDO")
        print(f"✅ {saved} leads salvos no crm_leads!")
        print(f"📊 source_channel: instagram_comment")

    finally:
        # Salvar sessão atualizada
        storage_state = await context.storage_state()
        SESSION_PATH.parent.mkdir(exist_ok=True)
        SESSION_PATH.write_text(json.dumps(storage_state))

        await browser.close()
        await playwright.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Instagram post commenters")
    parser.add_argument("post_url", help="URL do post do Instagram")
    parser.add_argument("--max", type=int, default=MAX_COMMENTERS, help=f"Máximo de comentaristas (default: {MAX_COMMENTERS})")
    parser.add_argument("--enrich", action="store_true", help="Enriquecer perfis (mais lento)")

    args = parser.parse_args()

    asyncio.run(main(args.post_url, args.max, args.enrich))
