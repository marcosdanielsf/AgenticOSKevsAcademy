"""
Instagram Profile Scraper
==========================
Extrai dados completos de perfis do Instagram usando Playwright.
Parte do sistema de Score Semântico para qualificação de leads.
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
    Usa a página do Instagram diretamente (não API).
    """

    def __init__(self, page: Page):
        self.page = page

    async def scrape_profile(self, username: str) -> InstagramProfile:
        """
        Extrai todos os dados de um perfil do Instagram.

        Args:
            username: Nome de usuário (sem @)

        Returns:
            InstagramProfile com todos os dados extraídos
        """
        profile = InstagramProfile(username=username)

        try:
            # Navegar para o perfil
            url = f"https://www.instagram.com/{username}/"
            await self.page.goto(url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(2)

            # Verificar se perfil existe
            if await self._check_profile_not_found():
                profile.scrape_success = False
                profile.error_message = "Perfil não encontrado"
                return profile

            # Extrair dados básicos
            profile.full_name = await self._get_full_name()
            profile.bio = await self._get_bio()
            profile.is_verified = await self._check_verified()
            profile.is_private = await self._check_private()
            profile.external_url = await self._get_external_url()
            profile.category = await self._get_category()

            # Extrair contagens
            counts = await self._get_counts()
            profile.posts_count = counts.get('posts', 0)
            profile.followers_count = counts.get('followers', 0)
            profile.following_count = counts.get('following', 0)

            # Se não for privado, extrair posts recentes
            if not profile.is_private:
                profile.recent_posts = await self._get_recent_posts(limit=6)

                # Calcular métricas de engajamento
                if profile.recent_posts and profile.followers_count > 0:
                    profile = self._calculate_engagement_metrics(profile)

            profile.scrape_success = True

        except Exception as e:
            profile.scrape_success = False
            profile.error_message = str(e)

        return profile

    async def _check_profile_not_found(self) -> bool:
        """Verifica se o perfil não existe"""
        try:
            not_found = await self.page.query_selector('text="Sorry, this page isn\'t available."')
            return not_found is not None
        except:
            return False

    async def _get_full_name(self) -> Optional[str]:
        """Extrai o nome completo do perfil"""
        try:
            # Tentar diferentes seletores
            selectors = [
                'header section span[class*="x1lliihq"]',
                'header h2',
                'header section > div > span'
            ]
            for selector in selectors:
                element = await self.page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    if text and text.strip():
                        return text.strip()
        except:
            pass
        return None

    async def _get_bio(self) -> Optional[str]:
        """Extrai a bio do perfil"""
        try:
            # Bio geralmente está em um h1 ou span dentro da seção do header
            bio_element = await self.page.query_selector('header section h1')
            if bio_element:
                return (await bio_element.inner_text()).strip()

            # Tentar seletor alternativo
            bio_element = await self.page.query_selector('header section > div > span:not([class*="username"])')
            if bio_element:
                text = await bio_element.inner_text()
                if text and len(text) > 5:  # Bio geralmente tem mais de 5 chars
                    return text.strip()
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

    async def _check_private(self) -> bool:
        """Verifica se o perfil é privado"""
        try:
            private = await self.page.query_selector('text="This account is private"')
            return private is not None
        except:
            return False

    async def _get_external_url(self) -> Optional[str]:
        """Extrai URL externa do perfil"""
        try:
            link = await self.page.query_selector('header section a[href*="l.instagram.com"]')
            if link:
                return await link.get_attribute('href')
        except:
            pass
        return None

    async def _get_category(self) -> Optional[str]:
        """Extrai categoria do perfil (se for business)"""
        try:
            # Categoria aparece como texto pequeno abaixo do nome
            category_element = await self.page.query_selector('header section div[class*="category"]')
            if category_element:
                return (await category_element.inner_text()).strip()
        except:
            pass
        return None

    async def _get_counts(self) -> Dict[str, int]:
        """Extrai contagens de posts, seguidores e seguindo"""
        counts = {'posts': 0, 'followers': 0, 'following': 0}

        try:
            # Pegar todos os elementos de contagem
            count_elements = await self.page.query_selector_all('header section ul li')

            for element in count_elements:
                text = await element.inner_text()
                text_lower = text.lower()

                # Extrair número
                number = self._parse_count(text)

                if 'post' in text_lower:
                    counts['posts'] = number
                elif 'follower' in text_lower or 'seguidore' in text_lower:
                    counts['followers'] = number
                elif 'following' in text_lower or 'seguindo' in text_lower:
                    counts['following'] = number
        except:
            pass

        return counts

    def _parse_count(self, text: str) -> int:
        """Converte texto de contagem para número (ex: '1.2M' -> 1200000)"""
        try:
            # Remover texto não numérico exceto K, M, B e pontos/vírgulas
            text = text.upper().strip()

            # Encontrar padrão numérico
            match = re.search(r'([\d,.]+)\s*([KMB])?', text)
            if not match:
                return 0

            number_str = match.group(1).replace(',', '.').replace(' ', '')
            multiplier_char = match.group(2)

            number = float(number_str)

            multipliers = {'K': 1000, 'M': 1000000, 'B': 1000000000}
            if multiplier_char and multiplier_char in multipliers:
                number *= multipliers[multiplier_char]

            return int(number)
        except:
            return 0

    async def _get_recent_posts(self, limit: int = 6) -> List[Dict]:
        """Extrai dados dos posts mais recentes"""
        posts = []

        try:
            # Pegar elementos de post
            post_elements = await self.page.query_selector_all('article a[href*="/p/"]')

            for i, element in enumerate(post_elements[:limit]):
                try:
                    post_data = {
                        'index': i,
                        'url': await element.get_attribute('href'),
                        'likes': 0,
                        'comments': 0
                    }

                    # Tentar extrair likes/comments do hover ou atributos
                    img = await element.query_selector('img')
                    if img:
                        alt = await img.get_attribute('alt')
                        if alt:
                            post_data['alt_text'] = alt
                            # Extrair números do alt text se disponível
                            likes_match = re.search(r'(\d+)\s*like', alt.lower())
                            if likes_match:
                                post_data['likes'] = int(likes_match.group(1))

                    posts.append(post_data)
                except:
                    continue

        except:
            pass

        return posts

    def _calculate_engagement_metrics(self, profile: InstagramProfile) -> InstagramProfile:
        """Calcula métricas de engajamento baseado nos posts"""
        if not profile.recent_posts or profile.followers_count == 0:
            return profile

        total_likes = sum(p.get('likes', 0) for p in profile.recent_posts)
        total_comments = sum(p.get('comments', 0) for p in profile.recent_posts)
        num_posts = len(profile.recent_posts)

        if num_posts > 0:
            profile.avg_likes = total_likes / num_posts
            profile.avg_comments = total_comments / num_posts

            # Engagement rate = (likes + comments) / followers * 100
            total_engagement = total_likes + total_comments
            profile.engagement_rate = (total_engagement / num_posts / profile.followers_count) * 100

        # Determinar frequência de postagem (simplificado)
        if profile.posts_count >= 100:
            profile.posting_frequency = "muito ativo"
        elif profile.posts_count >= 50:
            profile.posting_frequency = "ativo"
        elif profile.posts_count >= 20:
            profile.posting_frequency = "moderado"
        else:
            profile.posting_frequency = "pouco ativo"

        return profile


# Função auxiliar para uso standalone
async def scrape_profile_standalone(username: str, page: Page) -> InstagramProfile:
    """Função auxiliar para scraping de perfil"""
    scraper = InstagramProfileScraper(page)
    return await scraper.scrape_profile(username)
