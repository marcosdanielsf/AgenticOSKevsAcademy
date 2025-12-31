"""
Instagram Profile Scraper (v2)
==============================
Extrai dados de perfis do Instagram usando Playwright.
Usa seletores robustos que funcionam mesmo quando o Instagram muda classes.
"""

import asyncio
import json
import re
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime
from playwright.async_api import Page


@dataclass
class InstagramProfile:
    """Dados extraídos de um perfil do Instagram"""
    username: str
    full_name: Optional[str] = None
    bio: Optional[str] = None
    followers_count: int = 0
    following_count: int = 0
    posts_count: int = 0
    is_verified: bool = False
    is_private: bool = False
    is_business: bool = False
    category: Optional[str] = None
    external_url: Optional[str] = None
    profile_pic_url: Optional[str] = None
    recent_posts: List[Dict] = None

    # Métricas calculadas
    engagement_rate: float = 0.0
    avg_likes: float = 0.0
    avg_comments: float = 0.0
    posting_frequency: Optional[str] = None

    # Metadata
    scraped_at: str = None
    scrape_success: bool = True
    error_message: Optional[str] = None

    def __post_init__(self):
        if self.recent_posts is None:
            self.recent_posts = []
        if self.scraped_at is None:
            self.scraped_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return asdict(self)


class InstagramProfileScraper:
    """
    Extrai dados de perfis do Instagram usando Playwright.
    Usa JavaScript injection para extrair dados de forma mais confiável.
    """

    def __init__(self, page: Page):
        self.page = page

    async def scrape_profile(self, username: str) -> InstagramProfile:
        """
        Extrai todos os dados de um perfil do Instagram.
        """
        profile = InstagramProfile(username=username)

        try:
            # Navegar para o perfil
            url = f"https://www.instagram.com/{username}/"
            await self.page.goto(url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(3)  # Esperar mais tempo para carregar

            # Verificar se perfil existe
            page_content = await self.page.content()
            if "Sorry, this page isn't available" in page_content:
                profile.scrape_success = False
                profile.error_message = "Perfil não encontrado"
                return profile

            # Verificar se é privado
            if "This account is private" in page_content or "This Account is Private" in page_content:
                profile.is_private = True

            # Extrair dados usando JavaScript (mais confiável)
            data = await self._extract_via_javascript()

            if data:
                profile.full_name = data.get('full_name')
                profile.bio = data.get('bio')
                profile.followers_count = data.get('followers', 0)
                profile.following_count = data.get('following', 0)
                profile.posts_count = data.get('posts', 0)
                profile.is_verified = data.get('is_verified', False)
                profile.external_url = data.get('external_url')
            else:
                # Fallback: extrair via DOM
                profile.full_name = await self._get_full_name()
                profile.bio = await self._get_bio()
                counts = await self._get_counts()
                profile.posts_count = counts.get('posts', 0)
                profile.followers_count = counts.get('followers', 0)
                profile.following_count = counts.get('following', 0)
                profile.is_verified = await self._check_verified()

            # Determinar frequência de postagem
            if profile.posts_count >= 100:
                profile.posting_frequency = "muito ativo"
            elif profile.posts_count >= 50:
                profile.posting_frequency = "ativo"
            elif profile.posts_count >= 20:
                profile.posting_frequency = "moderado"
            else:
                profile.posting_frequency = "pouco ativo"

            profile.scrape_success = True

        except Exception as e:
            profile.scrape_success = False
            profile.error_message = str(e)

        return profile

    async def _extract_via_javascript(self) -> Optional[Dict]:
        """
        Extrai dados do perfil via JavaScript.
        O Instagram armazena dados em window._sharedData ou em meta tags.
        """
        try:
            # Método 1: Tentar extrair de meta tags (mais confiável)
            data = await self.page.evaluate('''() => {
                const result = {};

                // Extrair de meta tags
                const descMeta = document.querySelector('meta[name="description"]');
                if (descMeta) {
                    const desc = descMeta.getAttribute('content') || '';

                    // Parse: "1,234 Followers, 567 Following, 89 Posts - See Instagram photos..."
                    const followersMatch = desc.match(/([\d,\.KMkm]+)\s*Followers/i);
                    const followingMatch = desc.match(/([\d,\.KMkm]+)\s*Following/i);
                    const postsMatch = desc.match(/([\d,\.KMkm]+)\s*Posts/i);

                    if (followersMatch) {
                        result.followers = parseCount(followersMatch[1]);
                    }
                    if (followingMatch) {
                        result.following = parseCount(followingMatch[1]);
                    }
                    if (postsMatch) {
                        result.posts = parseCount(postsMatch[1]);
                    }

                    // Extrair bio da description
                    const bioMatch = desc.match(/Posts[^-]*-\s*(.+)/);
                    if (bioMatch) {
                        result.bio = bioMatch[1].trim();
                    }
                }

                // Extrair nome do título
                const titleMeta = document.querySelector('meta[property="og:title"]');
                if (titleMeta) {
                    const title = titleMeta.getAttribute('content') || '';
                    // Format: "Name (@username) • Instagram photos and videos"
                    const nameMatch = title.match(/^([^(]+)\s*\(@/);
                    if (nameMatch) {
                        result.full_name = nameMatch[1].trim();
                    }
                }

                // Verificar se é verificado
                result.is_verified = !!document.querySelector('svg[aria-label="Verified"]');

                // Extrair URL externa
                const externalLink = document.querySelector('a[href*="l.instagram.com"]');
                if (externalLink) {
                    result.external_url = externalLink.getAttribute('href');
                }

                function parseCount(str) {
                    if (!str) return 0;
                    str = str.replace(/,/g, '');
                    const num = parseFloat(str);
                    if (str.toLowerCase().includes('k')) return Math.round(num * 1000);
                    if (str.toLowerCase().includes('m')) return Math.round(num * 1000000);
                    return Math.round(num) || 0;
                }

                return Object.keys(result).length > 0 ? result : null;
            }''')

            return data

        except Exception as e:
            print(f"JavaScript extraction failed: {e}")
            return None

    async def _get_full_name(self) -> Optional[str]:
        """Extrai o nome completo do perfil via DOM"""
        try:
            # Tentar via título da página
            title = await self.page.title()
            # Format: "Name (@username) • Instagram photos and videos"
            match = re.match(r'^([^(]+)\s*\(@', title)
            if match:
                return match.group(1).strip()

            # Tentar via header
            header = await self.page.query_selector('header')
            if header:
                spans = await header.query_selector_all('span')
                for span in spans:
                    text = await span.inner_text()
                    # Nome geralmente é um span sem @ no início
                    if text and not text.startswith('@') and len(text) > 2:
                        return text.strip()
        except:
            pass
        return None

    async def _get_bio(self) -> Optional[str]:
        """Extrai a bio do perfil via DOM"""
        try:
            # Tentar via meta description
            meta = await self.page.query_selector('meta[name="description"]')
            if meta:
                desc = await meta.get_attribute('content')
                if desc:
                    # Extract bio part after "Posts - "
                    match = re.search(r'Posts[^-]*-\s*(.+)', desc)
                    if match:
                        bio = match.group(1).strip()
                        # Remove "See Instagram photos and videos" suffix
                        bio = re.sub(r'\s*See Instagram photos.*$', '', bio)
                        if len(bio) > 5:
                            return bio
        except:
            pass
        return None

    async def _check_verified(self) -> bool:
        """Verifica se o perfil é verificado"""
        try:
            verified = await self.page.query_selector('svg[aria-label="Verified"]')
            return verified is not None
        except:
            return False

    async def _get_counts(self) -> Dict[str, int]:
        """Extrai contagens de posts, seguidores e seguindo"""
        counts = {'posts': 0, 'followers': 0, 'following': 0}

        try:
            # Tentar via meta description
            meta = await self.page.query_selector('meta[name="description"]')
            if meta:
                desc = await meta.get_attribute('content')
                if desc:
                    # Parse: "1,234 Followers, 567 Following, 89 Posts"
                    followers_match = re.search(r'([\d,\.KMkm]+)\s*Followers', desc, re.I)
                    following_match = re.search(r'([\d,\.KMkm]+)\s*Following', desc, re.I)
                    posts_match = re.search(r'([\d,\.KMkm]+)\s*Posts', desc, re.I)

                    if followers_match:
                        counts['followers'] = self._parse_count(followers_match.group(1))
                    if following_match:
                        counts['following'] = self._parse_count(following_match.group(1))
                    if posts_match:
                        counts['posts'] = self._parse_count(posts_match.group(1))
        except:
            pass

        return counts

    def _parse_count(self, text: str) -> int:
        """Converte texto de contagem para número"""
        try:
            text = text.replace(',', '').replace(' ', '').upper()
            num = float(re.sub(r'[KMB]', '', text))

            if 'K' in text:
                return int(num * 1000)
            elif 'M' in text:
                return int(num * 1000000)
            elif 'B' in text:
                return int(num * 1000000000)

            return int(num)
        except:
            return 0


# Função auxiliar para uso standalone
async def scrape_profile_standalone(username: str, page: Page) -> InstagramProfile:
    """Função auxiliar para scraping de perfil"""
    scraper = InstagramProfileScraper(page)
    return await scraper.scrape_profile(username)
