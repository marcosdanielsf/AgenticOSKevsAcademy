#!/usr/bin/env python3
"""
Instagram Post Likers Scraper
=============================
Captura usuários que curtiram um post específico e salva no Supabase.
Leads super qualificados - já demonstraram interesse no seu conteúdo!

Uso:
    python instagram_post_likers_scraper.py --url "https://instagram.com/p/XXXXX"
    python instagram_post_likers_scraper.py --url "https://instagram.com/p/XXXXX" --limit 100
"""

import os
import sys
import json
import asyncio
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Set

from playwright.async_api import async_playwright, Page, BrowserContext
from dotenv import load_dotenv
import requests

load_dotenv()

# ============================================
# CONFIGURATION
# ============================================

BASE_DIR = Path(__file__).parent.parent
SESSIONS_DIR = BASE_DIR / "sessions"
LOGS_DIR = BASE_DIR / "logs"
SESSIONS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SESSION_PATH = SESSIONS_DIR / "instagram_session.json"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / "post_likers_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("PostLikersScraper")


class SupabaseClient:
    """Cliente simples para Supabase REST API"""

    def __init__(self):
        self.base_url = f"{SUPABASE_URL}/rest/v1"
        self.headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

    def insert_leads(self, leads: List[Dict]) -> int:
        """Insere leads no Supabase, ignorando duplicatas"""
        inserted = 0
        for lead in leads:
            try:
                # Verificar se já existe
                check = requests.get(
                    f"{self.base_url}/agentic_instagram_leads",
                    headers=self.headers,
                    params={"username": f"eq.{lead['username']}"}
                )

                if check.json():
                    logger.debug(f"   Lead @{lead['username']} já existe, pulando...")
                    continue

                # Inserir
                response = requests.post(
                    f"{self.base_url}/agentic_instagram_leads",
                    headers=self.headers,
                    json=lead
                )
                response.raise_for_status()
                inserted += 1

            except Exception as e:
                logger.error(f"   Erro ao inserir @{lead['username']}: {e}")

        return inserted


class PostLikersScraper:
    """
    Captura usuários que curtiram um post específico do Instagram.
    """

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.db = SupabaseClient()

    async def start(self):
        """Inicializa o browser"""
        logger.info("🚀 Iniciando scraper de curtidas...")

        playwright = await async_playwright().start()

        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=['--disable-blink-features=AutomationControlled']
        )

        context_options = {
            'viewport': {'width': 1280, 'height': 800},
            'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

        # Carregar sessão existente
        if SESSION_PATH.exists():
            logger.info("📂 Carregando sessão existente...")
            try:
                storage_state = json.loads(SESSION_PATH.read_text())
                context_options['storage_state'] = storage_state
            except Exception as e:
                logger.warning(f"Não foi possível carregar sessão: {e}")

        self.context = await self.browser.new_context(**context_options)
        self.page = await self.context.new_page()

    async def verify_login(self) -> bool:
        """Verifica se está logado"""
        await self.page.goto('https://www.instagram.com/', wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(3)

        # Verificar múltiplos indicadores de login
        login_indicators = [
            'svg[aria-label="Home"]',
            'svg[aria-label="Página inicial"]',
            'svg[aria-label="Inicio"]',
            'a[href="/direct/inbox/"]',
            'span:has-text("Pesquisa")',
            'span:has-text("Search")',
        ]

        for selector in login_indicators:
            try:
                await self.page.wait_for_selector(selector, timeout=2000)
                logger.info("✅ Logado no Instagram")
                return True
            except:
                continue

        # Verificar se NÃO está na página de login
        current_url = self.page.url
        if 'login' not in current_url and 'accounts' not in current_url:
            logger.info("✅ Logado no Instagram (verificação por URL)")
            return True

        logger.error("❌ Não está logado! Execute primeiro: python instagram_dm_agent.py --login-only")
        return False

    async def scrape_likers(self, post_url: str, limit: int = 200) -> List[Dict]:
        """
        Captura usuários que curtiram um post.

        Args:
            post_url: URL do post (ex: https://instagram.com/p/XXXXX)
            limit: Número máximo de curtidas para capturar

        Returns:
            Lista de dicts com dados dos usuários
        """
        likers = []
        seen_usernames: Set[str] = set()

        logger.info(f"🔍 Acessando post: {post_url}")

        try:
            # Navegar para o post
            await self.page.goto(post_url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)

            # Verificar se post existe
            content = await self.page.content()
            if "Sorry, this page isn't available" in content:
                logger.error("❌ Post não encontrado!")
                return []

            # Clicar em "likes" para abrir modal
            # Pode ser "X likes", "X others", ou "Liked by X and Y others"
            likes_selectors = [
                'a[href*="/liked_by/"]',
                'span:has-text("likes")',
                'button:has-text("others")',
                'section span:has-text("like")'
            ]

            clicked = False
            for selector in likes_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=3000)
                    if element:
                        await element.click()
                        clicked = True
                        logger.info("✅ Modal de curtidas aberto")
                        break
                except:
                    continue

            if not clicked:
                # Tentar acessar diretamente a página de likes
                if '/p/' in post_url:
                    likes_url = post_url.rstrip('/') + '/liked_by/'
                    await self.page.goto(likes_url, wait_until='domcontentloaded', timeout=30000)
                    await asyncio.sleep(2)

            await asyncio.sleep(2)

            # Esperar modal/lista carregar
            scroll_container = None
            container_selectors = [
                'div[role="dialog"] div[style*="overflow"]',
                'div[role="dialog"]',
                'main'
            ]

            for selector in container_selectors:
                try:
                    scroll_container = await self.page.wait_for_selector(selector, timeout=3000)
                    if scroll_container:
                        break
                except:
                    continue

            # Scroll e captura
            last_count = 0
            no_new_count = 0

            while len(likers) < limit and no_new_count < 5:
                # Capturar usernames visíveis
                usernames = await self.page.evaluate(r'''() => {
                    const links = document.querySelectorAll('a[href^="/"]');
                    const usernames = [];
                    links.forEach(link => {
                        const href = link.getAttribute('href');
                        // Filtrar apenas perfis (não posts, não explore, etc)
                        if (href && href.match(/^\/[a-zA-Z0-9._]+\/?$/) &&
                            !href.includes('/p/') &&
                            !href.includes('/explore/') &&
                            !href.includes('/direct/') &&
                            !href.includes('/stories/') &&
                            href !== '/') {
                            const username = href.replace(/\//g, '');
                            if (username && username.length > 0) {
                                usernames.push(username);
                            }
                        }
                    });
                    return [...new Set(usernames)];
                }''')

                # Adicionar novos usernames
                for username in usernames:
                    if username not in seen_usernames and len(likers) < limit:
                        seen_usernames.add(username)
                        likers.append({
                            'username': username,
                            'source': 'post_like',
                            'source_url': post_url,
                            'captured_at': datetime.now().isoformat()
                        })

                # Verificar se encontramos novos
                if len(likers) == last_count:
                    no_new_count += 1
                else:
                    no_new_count = 0
                    last_count = len(likers)

                logger.info(f"   📊 Capturados: {len(likers)}/{limit}")

                # Scroll para carregar mais
                if scroll_container:
                    await scroll_container.evaluate('el => el.scrollTop = el.scrollHeight')
                else:
                    await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')

                await asyncio.sleep(1.5)

            logger.info(f"✅ Total capturado: {len(likers)} usuários")

        except Exception as e:
            logger.error(f"❌ Erro ao capturar curtidas: {e}")

        return likers

    async def save_to_supabase(self, likers: List[Dict]) -> int:
        """Salva os leads no Supabase"""
        if not likers:
            return 0

        logger.info(f"💾 Salvando {len(likers)} leads no Supabase...")

        leads_to_insert = []
        for liker in likers:
            # Filtrar usernames inválidos
            username = liker['username']
            if username in ['reels', 'explore', 'direct', 'stories', 'marcosdanielsf']:
                continue
            leads_to_insert.append({
                'username': username,
                'source': liker['source'],
                'full_name': username  # Será atualizado pelo Smart Mode depois
            })

        inserted = self.db.insert_leads(leads_to_insert)
        logger.info(f"✅ {inserted} novos leads inseridos")

        return inserted

    async def stop(self):
        """Fecha o browser"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        logger.info("👋 Scraper finalizado")


async def main():
    parser = argparse.ArgumentParser(description='Captura usuários que curtiram um post')
    parser.add_argument('--url', required=True, help='URL do post do Instagram')
    parser.add_argument('--limit', type=int, default=200, help='Máximo de curtidas (default: 200)')
    parser.add_argument('--headless', action='store_true', help='Rodar sem interface gráfica')
    parser.add_argument('--no-save', action='store_true', help='Não salvar no Supabase (apenas exibir)')
    args = parser.parse_args()

    scraper = PostLikersScraper(headless=args.headless)

    try:
        await scraper.start()

        if not await scraper.verify_login():
            return

        # Capturar curtidas
        likers = await scraper.scrape_likers(args.url, limit=args.limit)

        if likers:
            # Exibir resultados
            print("\n" + "="*60)
            print(f"👥 USUÁRIOS QUE CURTIRAM ({len(likers)})")
            print("="*60)
            for i, liker in enumerate(likers[:20], 1):
                print(f"   {i}. @{liker['username']}")
            if len(likers) > 20:
                print(f"   ... e mais {len(likers) - 20} usuários")
            print("="*60)

            # Salvar no Supabase
            if not args.no_save:
                inserted = await scraper.save_to_supabase(likers)
                print(f"\n✅ {inserted} novos leads prontos para abordagem!")
                print(f"   Execute: python instagram_dm_agent.py --limit {inserted}")
        else:
            print("\n⚠️  Nenhuma curtida encontrada")

    finally:
        await scraper.stop()


if __name__ == "__main__":
    asyncio.run(main())
