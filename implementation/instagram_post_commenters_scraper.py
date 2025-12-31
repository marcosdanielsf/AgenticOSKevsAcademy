#!/usr/bin/env python3
"""
Instagram Post Commenters Scraper
=================================
Captura usuários que comentaram em um post específico.
Leads ULTRA qualificados - engajamento ativo > curtida passiva!

Uso:
    python instagram_post_commenters_scraper.py --url "https://instagram.com/p/XXXXX"
    python instagram_post_commenters_scraper.py --url "https://instagram.com/p/XXXXX" --limit 50
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
        logging.FileHandler(LOGS_DIR / "post_commenters_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("PostCommentersScraper")


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


class PostCommentersScraper:
    """
    Captura usuários que comentaram em um post específico do Instagram.
    Também captura o conteúdo do comentário para personalização!
    """

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.db = SupabaseClient()

    async def start(self):
        """Inicializa o browser"""
        logger.info("🚀 Iniciando scraper de comentários...")

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
        await asyncio.sleep(2)

        try:
            await self.page.wait_for_selector('svg[aria-label="Home"]', timeout=5000)
            logger.info("✅ Logado no Instagram")
            return True
        except:
            logger.error("❌ Não está logado! Execute primeiro: python instagram_dm_agent.py --login-only")
            return False

    async def scrape_commenters(self, post_url: str, limit: int = 100) -> List[Dict]:
        """
        Captura usuários que comentaram em um post.

        Args:
            post_url: URL do post (ex: https://instagram.com/p/XXXXX)
            limit: Número máximo de comentadores para capturar

        Returns:
            Lista de dicts com dados dos usuários e seus comentários
        """
        commenters = []
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

            # Clicar em "View all X comments" se existir
            try:
                view_all = await self.page.wait_for_selector(
                    'span:has-text("View all"), button:has-text("View all")',
                    timeout=3000
                )
                if view_all:
                    await view_all.click()
                    await asyncio.sleep(2)
            except:
                pass

            # Carregar mais comentários (scroll)
            last_count = 0
            no_new_count = 0

            while len(commenters) < limit and no_new_count < 5:
                # Capturar comentários visíveis
                comments_data = await self.page.evaluate('''() => {
                    const comments = [];

                    // Procurar estrutura de comentários
                    const commentElements = document.querySelectorAll('ul ul li, div[role="button"] + ul li');

                    commentElements.forEach(li => {
                        // Encontrar link do username
                        const usernameLink = li.querySelector('a[href^="/"]');
                        if (!usernameLink) return;

                        const href = usernameLink.getAttribute('href');
                        if (!href || !href.match(/^\/[a-zA-Z0-9._]+\/?$/)) return;

                        const username = href.replace(/\//g, '');
                        if (!username) return;

                        // Tentar capturar o texto do comentário
                        let commentText = '';
                        const spans = li.querySelectorAll('span');
                        spans.forEach(span => {
                            const text = span.textContent?.trim();
                            if (text && text.length > 3 && text !== username && !text.includes('Reply') && !text.includes('like')) {
                                commentText = text;
                            }
                        });

                        comments.push({
                            username: username,
                            comment: commentText.substring(0, 200)  // Limitar tamanho
                        });
                    });

                    // Também buscar de forma alternativa
                    const allLinks = document.querySelectorAll('a[role="link"][href^="/"]');
                    allLinks.forEach(link => {
                        const href = link.getAttribute('href');
                        if (href && href.match(/^\/[a-zA-Z0-9._]+\/?$/) &&
                            !href.includes('/p/') && !href.includes('/explore/')) {
                            const username = href.replace(/\//g, '');
                            if (username && !comments.find(c => c.username === username)) {
                                // Tentar pegar texto próximo
                                const parent = link.closest('li') || link.parentElement;
                                const text = parent?.textContent?.replace(username, '').trim() || '';
                                comments.push({
                                    username: username,
                                    comment: text.substring(0, 200)
                                });
                            }
                        }
                    });

                    return comments;
                }''')

                # Adicionar novos comentadores
                for data in comments_data:
                    username = data.get('username', '')
                    if username and username not in seen_usernames and len(commenters) < limit:
                        seen_usernames.add(username)
                        commenters.append({
                            'username': username,
                            'comment': data.get('comment', ''),
                            'source': 'post_comment',
                            'source_url': post_url,
                            'captured_at': datetime.now().isoformat()
                        })

                # Verificar se encontramos novos
                if len(commenters) == last_count:
                    no_new_count += 1
                else:
                    no_new_count = 0
                    last_count = len(commenters)

                logger.info(f"   📊 Capturados: {len(commenters)}/{limit}")

                # Tentar carregar mais comentários
                try:
                    # Clicar em "Load more comments" ou similar
                    load_more = await self.page.query_selector(
                        'button:has-text("Load more"), svg[aria-label="Load more comments"]'
                    )
                    if load_more:
                        await load_more.click()
                        await asyncio.sleep(1.5)
                except:
                    pass

                # Scroll
                await self.page.evaluate('window.scrollBy(0, 500)')
                await asyncio.sleep(1)

            logger.info(f"✅ Total capturado: {len(commenters)} comentadores")

        except Exception as e:
            logger.error(f"❌ Erro ao capturar comentários: {e}")

        return commenters

    async def save_to_supabase(self, commenters: List[Dict]) -> int:
        """Salva os leads no Supabase"""
        if not commenters:
            return 0

        logger.info(f"💾 Salvando {len(commenters)} leads no Supabase...")

        leads_to_insert = []
        for commenter in commenters:
            comment_preview = commenter.get('comment', '')[:100]
            leads_to_insert.append({
                'username': commenter['username'],
                'source': commenter['source'],
                'notes': f"Comentou: \"{comment_preview}...\" no post: {commenter.get('source_url', 'N/A')}"
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
    parser = argparse.ArgumentParser(description='Captura usuários que comentaram em um post')
    parser.add_argument('--url', required=True, help='URL do post do Instagram')
    parser.add_argument('--limit', type=int, default=100, help='Máximo de comentadores (default: 100)')
    parser.add_argument('--headless', action='store_true', help='Rodar sem interface gráfica')
    parser.add_argument('--no-save', action='store_true', help='Não salvar no Supabase (apenas exibir)')
    args = parser.parse_args()

    scraper = PostCommentersScraper(headless=args.headless)

    try:
        await scraper.start()

        if not await scraper.verify_login():
            return

        # Capturar comentadores
        commenters = await scraper.scrape_commenters(args.url, limit=args.limit)

        if commenters:
            # Exibir resultados
            print("\n" + "="*60)
            print(f"💬 USUÁRIOS QUE COMENTARAM ({len(commenters)})")
            print("="*60)
            for i, c in enumerate(commenters[:15], 1):
                comment = c.get('comment', '')[:50]
                print(f"   {i}. @{c['username']}")
                if comment:
                    print(f"      \"{comment}...\"")
            if len(commenters) > 15:
                print(f"   ... e mais {len(commenters) - 15} comentadores")
            print("="*60)

            # Salvar no Supabase
            if not args.no_save:
                inserted = await scraper.save_to_supabase(commenters)
                print(f"\n✅ {inserted} novos leads prontos para abordagem!")
                print(f"   Execute: python instagram_dm_agent.py --limit {inserted}")
                print(f"\n💡 Dica: Use o comentário para personalizar a DM!")
                print(f"   Ex: \"Vi que você comentou sobre X no meu post...\"")
        else:
            print("\n⚠️  Nenhum comentário encontrado")

    finally:
        await scraper.stop()


if __name__ == "__main__":
    asyncio.run(main())
