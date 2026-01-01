"""
Instagram Profile Scraper (Vision Mode)
========================================
Extrai dados de perfis do Instagram usando screenshot + AI Vision.
Muito mais robusto que seletores CSS - o Instagram pode mudar HTML, mas não a UI.
"""

import asyncio
import base64
import json
import os
import re
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
from playwright.async_api import Page

# Tentar importar Anthropic para visão
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


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
    extraction_method: str = "vision"

    def __post_init__(self):
        if self.recent_posts is None:
            self.recent_posts = []
        if self.scraped_at is None:
            self.scraped_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return asdict(self)


class InstagramProfileScraperVision:
    """
    Extrai dados de perfis do Instagram usando Screenshot + AI Vision.
    Usa Claude para analisar a imagem e extrair informações.
    """

    def __init__(self, page: Page, anthropic_api_key: Optional[str] = None):
        self.page = page
        self.api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = None

        if ANTHROPIC_AVAILABLE and self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)

    async def scrape_profile(self, username: str) -> InstagramProfile:
        """
        Extrai dados do perfil usando screenshot + visão AI.
        """
        profile = InstagramProfile(username=username)

        try:
            # 1. Navegar para o perfil
            url = f"https://www.instagram.com/{username}/"
            await self.page.goto(url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(3)

            # 2. Verificar se perfil existe
            page_content = await self.page.content()
            if "Sorry, this page isn't available" in page_content:
                profile.scrape_success = False
                profile.error_message = "Perfil não encontrado"
                return profile

            # 3. Tirar screenshot
            screenshot_bytes = await self.page.screenshot(type='png')

            # 4. Extrair dados via AI Vision
            if self.client:
                extracted_data = await self._extract_with_vision(screenshot_bytes, username)
                if extracted_data:
                    profile.full_name = extracted_data.get('full_name')
                    profile.bio = extracted_data.get('bio')
                    profile.followers_count = extracted_data.get('followers_count', 0)
                    profile.following_count = extracted_data.get('following_count', 0)
                    profile.posts_count = extracted_data.get('posts_count', 0)
                    profile.is_verified = extracted_data.get('is_verified', False)
                    profile.is_private = extracted_data.get('is_private', False)
                    profile.category = extracted_data.get('category')
                    profile.extraction_method = "vision_ai"
            else:
                # Fallback: extrair via meta tags
                profile = await self._fallback_extraction(profile)
                profile.extraction_method = "meta_tags"

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

    async def _extract_with_vision(self, screenshot_bytes: bytes, username: str) -> Optional[Dict]:
        """
        Usa Claude Vision para extrair dados do screenshot.
        """
        try:
            # Converter para base64
            image_base64 = base64.standard_b64encode(screenshot_bytes).decode("utf-8")

            # Prompt para extração
            prompt = f"""Analyze this Instagram profile screenshot for @{username} and extract the following information.
Return ONLY a valid JSON object with these exact keys (use null for missing values):

{{
    "full_name": "The display name shown on the profile",
    "bio": "The complete bio text",
    "followers_count": 12345,
    "following_count": 678,
    "posts_count": 90,
    "is_verified": true/false,
    "is_private": true/false,
    "category": "Business category if shown (e.g. 'Digital Creator', 'Entrepreneur')"
}}

Important:
- For follower/following/posts counts, convert "1.2K" to 1200, "5M" to 5000000
- Return raw numbers, not strings
- If the profile is private, still extract what you can see
- If you can't find a value, use null
- Return ONLY the JSON, no other text"""

            # Chamar Claude Vision
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": image_base64
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )

            # Extrair JSON da resposta
            response_text = response.content[0].text.strip()

            # Tentar fazer parse do JSON
            # Remover possíveis markdown code blocks
            if response_text.startswith("```"):
                response_text = re.sub(r'^```json?\n?', '', response_text)
                response_text = re.sub(r'\n?```$', '', response_text)

            data = json.loads(response_text)
            return data

        except Exception as e:
            print(f"Vision extraction failed: {e}")
            return None

    async def _fallback_extraction(self, profile: InstagramProfile) -> InstagramProfile:
        """
        Fallback: extrai via meta tags se Vision não estiver disponível.
        """
        try:
            # Extrair de meta description
            meta = await self.page.query_selector('meta[name="description"]')
            if meta:
                desc = await meta.get_attribute('content')
                if desc:
                    # Parse: "1,234 Followers, 567 Following, 89 Posts"
                    followers_match = re.search(r'([\d,\.KMkm]+)\s*Followers', desc, re.I)
                    following_match = re.search(r'([\d,\.KMkm]+)\s*Following', desc, re.I)
                    posts_match = re.search(r'([\d,\.KMkm]+)\s*Posts', desc, re.I)

                    if followers_match:
                        profile.followers_count = self._parse_count(followers_match.group(1))
                    if following_match:
                        profile.following_count = self._parse_count(following_match.group(1))
                    if posts_match:
                        profile.posts_count = self._parse_count(posts_match.group(1))

                    # Extrair bio
                    bio_match = re.search(r'Posts[^-]*-\s*(.+)', desc)
                    if bio_match:
                        bio = bio_match.group(1).strip()
                        bio = re.sub(r'\s*See Instagram photos.*$', '', bio)
                        if len(bio) > 5:
                            profile.bio = bio

            # Extrair nome do título
            title = await self.page.title()
            name_match = re.match(r'^([^(]+)\s*\(@', title)
            if name_match:
                profile.full_name = name_match.group(1).strip()

        except Exception as e:
            print(f"Fallback extraction failed: {e}")

        return profile

    def _parse_count(self, text: str) -> int:
        """Converte texto de contagem para número."""
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


# Alias para compatibilidade
InstagramProfileScraper = InstagramProfileScraperVision


# Função auxiliar
async def scrape_profile_standalone(username: str, page: Page) -> InstagramProfile:
    """Função auxiliar para scraping de perfil."""
    scraper = InstagramProfileScraperVision(page)
    return await scraper.scrape_profile(username)
