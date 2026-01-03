#!/usr/bin/env python3
"""
🔍 INSTAGRAM API SCRAPER (Método Bruno Fraga)
=============================================
Extrai dados ocultos do Instagram usando Session ID + API interna.

Dados extraídos:
- User ID (estático, nunca muda)
- FB ID (conexão com Facebook)
- Bio completa
- Seguidores/Seguindo
- Pista de email (ofuscado)
- Pista de telefone (ofuscado)
- WhatsApp vinculado
- Data de criação
- Se é conta business
- Categoria da conta
- Links externos
- E muito mais...

Uso:
    from instagram_api_scraper import InstagramAPIScraper

    scraper = InstagramAPIScraper(session_id="seu_session_id")
    profile = scraper.get_profile("username")
    print(profile)
"""

import os
import json
import requests
import logging
from datetime import datetime
from typing import Dict, Optional, List
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class InstagramAPIScraper:
    """
    Scraper do Instagram usando API interna + Session ID.
    Método baseado nas técnicas do Bruno Fraga.
    """

    # Endpoints da API interna do Instagram
    BASE_URL = "https://i.instagram.com/api/v1"
    GRAPH_URL = "https://www.instagram.com/api/v1"
    WEB_URL = "https://www.instagram.com"

    def __init__(self, session_id: str = None):
        """
        Inicializa o scraper.

        Args:
            session_id: O sessionid do cookie do Instagram (obrigatório)
        """
        self.session_id = session_id or os.getenv("INSTAGRAM_SESSION_ID")

        if not self.session_id:
            # Tentar carregar do arquivo de sessão
            session_path = Path(__file__).parent.parent / "sessions" / "instagram_session.json"
            if session_path.exists():
                try:
                    session_data = json.loads(session_path.read_text())
                    cookies = session_data.get("cookies", [])
                    for cookie in cookies:
                        if cookie.get("name") == "sessionid":
                            self.session_id = cookie.get("value")
                            break
                except Exception as e:
                    logger.warning(f"Erro ao carregar sessão: {e}")

        if not self.session_id:
            raise ValueError(
                "Session ID não encontrado. Configure INSTAGRAM_SESSION_ID no .env "
                "ou passe como parâmetro."
            )

        # Headers que imitam o app do Instagram
        self.headers = {
            "User-Agent": "Instagram 275.0.0.27.98 Android (33/13; 420dpi; 1080x2400; samsung; SM-G991B; o1s; exynos2100; en_US; 458229258)",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "X-IG-App-ID": "936619743392459",
            "X-IG-Device-ID": "android-1234567890",
            "X-IG-Connection-Type": "WIFI",
            "X-IG-Capabilities": "3brTvx0=",
            "X-IG-App-Locale": "en_US",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded",
            "Cookie": f"sessionid={self.session_id}",
        }

        # Headers para requisições web
        self.web_headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Cookie": f"sessionid={self.session_id}",
            "X-IG-App-ID": "936619743392459",
            "X-Requested-With": "XMLHttpRequest",
        }

        self.session = requests.Session()
        logger.info("InstagramAPIScraper inicializado")

    def get_user_id(self, username: str) -> Optional[str]:
        """
        Obtém o User ID a partir do username.
        O User ID é estático e nunca muda, mesmo se o username mudar.
        """
        try:
            # Método 1: Via web profile
            url = f"{self.WEB_URL}/api/v1/users/web_profile_info/?username={username}"
            response = self.session.get(url, headers=self.web_headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                user_data = data.get("data", {}).get("user", {})
                return user_data.get("id")

            # Método 2: Via search
            url = f"{self.WEB_URL}/web/search/topsearch/?query={username}"
            response = self.session.get(url, headers=self.web_headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                users = data.get("users", [])
                for user in users:
                    if user.get("user", {}).get("username", "").lower() == username.lower():
                        return user.get("user", {}).get("pk")

            return None

        except Exception as e:
            logger.error(f"Erro ao obter User ID para {username}: {e}")
            return None

    def get_profile(self, username: str) -> Dict:
        """
        Extrai dados completos do perfil via API.

        Retorna dados ocultos que não aparecem na interface visual:
        - user_id (estático)
        - fb_id (Facebook ID)
        - email_hint (pista do email)
        - phone_hint (pista do telefone)
        - whatsapp_number
        - account_created
        - is_business
        - category
        - E muito mais...
        """
        result = {
            "success": False,
            "username": username,
            "scraped_at": datetime.now().isoformat(),
            "method": "api",
            "error": None
        }

        try:
            # Método 1: API Mobile (i.instagram.com) - mais confiável
            url = f"{self.BASE_URL}/users/web_profile_info/?username={username}"
            response = self.session.get(url, headers=self.headers, timeout=15)

            if response.status_code == 200:
                data = response.json()
                user = data.get("data", {}).get("user", {})

                if user:
                    result.update(self._parse_web_profile(user))
                    result["success"] = True
                    result["method"] = "mobile_api"

                    # Tentar obter dados adicionais via API mobile
                    user_id = result.get("user_id")
                    if user_id:
                        extra_data = self._get_mobile_profile(user_id)
                        if extra_data:
                            result.update(extra_data)

                    return result

            # Método 2: Web Profile Info (fallback)
            url = f"{self.WEB_URL}/api/v1/users/web_profile_info/?username={username}"
            response = self.session.get(url, headers=self.web_headers, timeout=15)

            if response.status_code == 200:
                data = response.json()
                user = data.get("data", {}).get("user", {})

                if user:
                    result.update(self._parse_web_profile(user))
                    result["success"] = True
                    result["method"] = "web_profile_info"
                    return result

            # Método 3: GraphQL (fallback)
            profile_data = self._get_graphql_profile(username)
            if profile_data:
                result.update(profile_data)
                result["success"] = True
                result["method"] = "graphql"
                return result

            # Método 4: Página pública (último recurso)
            public_data = self._get_public_profile(username)
            if public_data:
                result.update(public_data)
                result["success"] = True
                result["method"] = "public_page"
                return result

            result["error"] = "Não foi possível obter dados do perfil"
            return result

        except Exception as e:
            logger.error(f"Erro ao obter perfil de {username}: {e}")
            result["error"] = str(e)
            return result

    def _parse_web_profile(self, user: Dict) -> Dict:
        """Parse dados do web_profile_info"""

        # Extrair informações de contato
        bio_links = user.get("bio_links", [])
        external_urls = [link.get("url") for link in bio_links if link.get("url")]

        # Dados básicos
        data = {
            "user_id": user.get("id"),
            "username": user.get("username"),
            "full_name": user.get("full_name"),
            "bio": user.get("biography"),
            "bio_with_entities": user.get("biography_with_entities"),
            "external_url": user.get("external_url"),
            "external_urls": external_urls,

            # Métricas
            "followers_count": user.get("edge_followed_by", {}).get("count", 0),
            "following_count": user.get("edge_follow", {}).get("count", 0),
            "posts_count": user.get("edge_owner_to_timeline_media", {}).get("count", 0),

            # Status da conta
            "is_private": user.get("is_private", False),
            "is_verified": user.get("is_verified", False),
            "is_business": user.get("is_business_account", False),
            "is_professional": user.get("is_professional_account", False),
            "is_creator": user.get("is_creator_account", False),

            # Categoria
            "category": user.get("category_name"),
            "category_id": user.get("category_id"),
            "business_category": user.get("business_category_name"),

            # Fotos
            "profile_pic_url": user.get("profile_pic_url"),
            "profile_pic_url_hd": user.get("profile_pic_url_hd"),

            # IDs importantes
            "fb_id": user.get("fbid"),
            "fb_profile_biolink": user.get("fb_profile_biolink"),

            # Configurações
            "has_ar_effects": user.get("has_ar_effects"),
            "has_clips": user.get("has_clips"),
            "has_guides": user.get("has_guides"),
            "has_channel": user.get("has_channel"),
            "hide_like_and_view_counts": user.get("hide_like_and_view_counts"),

            # Conexões
            "connected_fb_page": user.get("connected_fb_page"),
            "is_joined_recently": user.get("is_joined_recently"),
        }

        # Tentar extrair mais dados se disponíveis
        if user.get("edge_felix_video_timeline"):
            data["reels_count"] = user["edge_felix_video_timeline"].get("count", 0)

        if user.get("edge_mutual_followed_by"):
            data["mutual_followers_count"] = user["edge_mutual_followed_by"].get("count", 0)

        return data

    def _get_mobile_profile(self, user_id: str) -> Optional[Dict]:
        """Obtém dados adicionais via API mobile"""
        try:
            url = f"{self.BASE_URL}/users/{user_id}/info/"
            response = self.session.get(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                user = data.get("user", {})

                extra = {}

                # Pistas de contato (dados ofuscados)
                if user.get("public_email"):
                    extra["email"] = user["public_email"]
                if user.get("obfuscated_email"):
                    extra["email_hint"] = user["obfuscated_email"]
                if user.get("public_phone_number"):
                    extra["phone"] = user["public_phone_number"]
                if user.get("obfuscated_phone"):
                    extra["phone_hint"] = user["obfuscated_phone"]
                if user.get("public_phone_country_code"):
                    extra["phone_country_code"] = user["public_phone_country_code"]

                # WhatsApp
                if user.get("is_whatsapp_linked"):
                    extra["whatsapp_linked"] = True
                    if user.get("whatsapp_number"):
                        extra["whatsapp_number"] = user["whatsapp_number"]

                # Mais dados
                extra.update({
                    "has_anonymous_profile_picture": user.get("has_anonymous_profile_picture"),
                    "account_type": user.get("account_type"),
                    "is_call_to_action_enabled": user.get("is_call_to_action_enabled"),
                    "contact_phone_number": user.get("contact_phone_number"),
                    "city_name": user.get("city_name"),
                    "address_street": user.get("address_street"),
                    "direct_messaging": user.get("direct_messaging"),
                    "latitude": user.get("latitude"),
                    "longitude": user.get("longitude"),
                })

                # Limpar None values
                extra = {k: v for k, v in extra.items() if v is not None}

                return extra if extra else None

        except Exception as e:
            logger.debug(f"Erro ao obter dados mobile: {e}")
            return None

    def _get_graphql_profile(self, username: str) -> Optional[Dict]:
        """Obtém perfil via GraphQL"""
        try:
            url = f"{self.WEB_URL}/{username}/?__a=1&__d=dis"
            response = self.session.get(url, headers=self.web_headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                user = data.get("graphql", {}).get("user", {})

                if user:
                    return self._parse_web_profile(user)

            return None

        except Exception as e:
            logger.debug(f"Erro GraphQL: {e}")
            return None

    def _get_public_profile(self, username: str) -> Optional[Dict]:
        """Obtém dados da página pública"""
        try:
            url = f"{self.WEB_URL}/{username}/"
            response = self.session.get(url, headers=self.web_headers, timeout=10)

            if response.status_code == 200:
                # Procurar JSON embutido na página
                import re

                # Procurar dados do usuário no HTML
                patterns = [
                    r'"user":\s*({[^}]+})',
                    r'window\._sharedData\s*=\s*({.+?});</script>',
                ]

                for pattern in patterns:
                    match = re.search(pattern, response.text)
                    if match:
                        try:
                            data = json.loads(match.group(1))
                            if "username" in data:
                                return {
                                    "user_id": data.get("id"),
                                    "username": data.get("username"),
                                    "full_name": data.get("full_name"),
                                    "bio": data.get("biography"),
                                    "is_private": data.get("is_private"),
                                    "is_verified": data.get("is_verified"),
                                }
                        except:
                            continue

            return None

        except Exception as e:
            logger.debug(f"Erro página pública: {e}")
            return None

    def get_profile_by_id(self, user_id: str) -> Dict:
        """
        Obtém perfil pelo User ID (útil quando o username muda).
        """
        result = {
            "success": False,
            "user_id": user_id,
            "scraped_at": datetime.now().isoformat(),
            "method": "api_by_id",
            "error": None
        }

        try:
            url = f"{self.BASE_URL}/users/{user_id}/info/"
            response = self.session.get(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                user = data.get("user", {})

                if user:
                    result.update({
                        "success": True,
                        "username": user.get("username"),
                        "full_name": user.get("full_name"),
                        "bio": user.get("biography"),
                        "followers_count": user.get("follower_count"),
                        "following_count": user.get("following_count"),
                        "posts_count": user.get("media_count"),
                        "is_private": user.get("is_private"),
                        "is_verified": user.get("is_verified"),
                        "is_business": user.get("is_business"),
                        "category": user.get("category"),
                        "profile_pic_url": user.get("profile_pic_url"),
                        "profile_pic_url_hd": user.get("hd_profile_pic_url_info", {}).get("url"),
                        "email_hint": user.get("obfuscated_email"),
                        "phone_hint": user.get("obfuscated_phone"),
                        "whatsapp_linked": user.get("is_whatsapp_linked"),
                    })
            else:
                result["error"] = f"Status {response.status_code}"

        except Exception as e:
            result["error"] = str(e)

        return result

    def get_contact_hints(self, username: str) -> Dict:
        """
        Obtém pistas de contato (email/telefone ofuscados).
        Útil para triagem de suspeitos.
        """
        try:
            # Usar o endpoint de "esqueci minha senha"
            url = f"{self.WEB_URL}/accounts/account_recovery_send_ajax/"

            data = {
                "email_or_username": username,
            }

            response = self.session.post(
                url,
                headers=self.web_headers,
                data=data,
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "email_hint": result.get("email"),  # ex: u***@gmail.com
                    "phone_hint": result.get("phone_number"),  # ex: +55 ** ****-**68
                }

            return {"success": False, "error": "Não foi possível obter hints"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def calculate_lead_score(self, profile: Dict) -> Dict:
        """
        Calcula score do lead baseado nos dados do perfil.

        Retorna:
            score: 0-100
            classification: LEAD_HOT, LEAD_WARM, LEAD_COLD
            signals: Lista de sinais detectados
        """
        score = 0
        signals = []

        # Score por seguidores
        followers = profile.get("followers_count", 0)
        if followers >= 100000:
            score += 25
            signals.append("influencer_100k+")
        elif followers >= 10000:
            score += 20
            signals.append("influencer_10k+")
        elif followers >= 1000:
            score += 10
            signals.append("engaged_1k+")
        elif followers >= 500:
            score += 5
            signals.append("followers_500+")

        # Score por bio keywords
        bio = (profile.get("bio") or "").lower()
        business_keywords = [
            "ceo", "founder", "empreendedor", "empresa", "negócio",
            "marketing", "mentor", "coach", "consultor", "agência",
            "gestor", "diretor", "investidor", "startup", "digital",
            "vendas", "growth", "tech", "founder", "co-founder"
        ]

        keyword_count = 0
        for kw in business_keywords:
            if kw in bio:
                keyword_count += 1
                signals.append(f"keyword:{kw}")
                if keyword_count >= 3:
                    break

        score += min(30, keyword_count * 10)

        # Score por tipo de conta
        if profile.get("is_business"):
            score += 15
            signals.append("business_account")
        elif profile.get("is_professional"):
            score += 12
            signals.append("professional_account")
        elif profile.get("is_creator"):
            score += 10
            signals.append("creator_account")

        # Score por categoria
        if profile.get("category"):
            score += 5
            signals.append(f"category:{profile['category']}")

        # Score por verificação
        if profile.get("is_verified"):
            score += 10
            signals.append("verified")

        # Score por contato disponível
        if profile.get("email") or profile.get("email_hint"):
            score += 5
            signals.append("has_email")
        if profile.get("phone") or profile.get("phone_hint"):
            score += 5
            signals.append("has_phone")
        if profile.get("whatsapp_linked"):
            score += 5
            signals.append("has_whatsapp")

        # Penalidade por conta privada
        if profile.get("is_private"):
            score -= 10
            signals.append("private_account")

        # Penalidade por poucos posts
        posts = profile.get("posts_count", 0)
        if posts < 10:
            score -= 5
            signals.append("low_activity")
        elif posts >= 100:
            score += 5
            signals.append("active_poster")

        # Normalizar score
        score = max(0, min(100, score))

        # Classificação
        if score >= 70:
            classification = "LEAD_HOT"
        elif score >= 40:
            classification = "LEAD_WARM"
        else:
            classification = "LEAD_COLD"

        return {
            "score": score,
            "classification": classification,
            "signals": signals
        }


# ============================================
# FUNÇÕES DE CONVENIÊNCIA
# ============================================

def scrape_profile(username: str, session_id: str = None) -> Dict:
    """
    Função de conveniência para scrape rápido de um perfil.

    Uso:
        from instagram_api_scraper import scrape_profile

        profile = scrape_profile("username")
        print(profile)
    """
    scraper = InstagramAPIScraper(session_id=session_id)
    profile = scraper.get_profile(username)

    if profile.get("success"):
        score_data = scraper.calculate_lead_score(profile)
        profile.update(score_data)

    return profile


def scrape_multiple(usernames: List[str], session_id: str = None, delay: float = 2.0) -> List[Dict]:
    """
    Scrape múltiplos perfis com delay entre requisições.
    """
    import time

    scraper = InstagramAPIScraper(session_id=session_id)
    results = []

    for i, username in enumerate(usernames):
        print(f"[{i+1}/{len(usernames)}] Scraping @{username}...")

        profile = scraper.get_profile(username)

        if profile.get("success"):
            score_data = scraper.calculate_lead_score(profile)
            profile.update(score_data)

        results.append(profile)

        if i < len(usernames) - 1:
            time.sleep(delay)

    return results


# ============================================
# CLI
# ============================================

def main():
    """CLI para testar o scraper"""
    import argparse

    parser = argparse.ArgumentParser(description="Instagram API Scraper (Método Bruno Fraga)")
    parser.add_argument("username", help="Username do Instagram para scrape")
    parser.add_argument("--session-id", help="Session ID do Instagram")
    parser.add_argument("--output", "-o", help="Arquivo de saída (JSON)")
    parser.add_argument("--hints", action="store_true", help="Obter apenas hints de contato")

    args = parser.parse_args()

    print("\n" + "="*60)
    print("  INSTAGRAM API SCRAPER (Método Bruno Fraga)")
    print("="*60 + "\n")

    try:
        scraper = InstagramAPIScraper(session_id=args.session_id)

        if args.hints:
            print(f"🔍 Obtendo hints de contato para @{args.username}...")
            result = scraper.get_contact_hints(args.username)
        else:
            print(f"🔍 Extraindo dados de @{args.username}...")
            result = scraper.get_profile(args.username)

            if result.get("success"):
                score_data = scraper.calculate_lead_score(result)
                result.update(score_data)

        # Mostrar resultado
        print("\n📊 RESULTADO:\n")

        if result.get("success"):
            print(f"✅ Sucesso! Método: {result.get('method', 'N/A')}\n")

            # Dados básicos
            print(f"👤 Username: @{result.get('username')}")
            print(f"📛 Nome: {result.get('full_name', 'N/A')}")
            print(f"🆔 User ID: {result.get('user_id', 'N/A')}")
            print(f"🔗 FB ID: {result.get('fb_id', 'N/A')}")

            # Bio
            bio = result.get('bio', '')
            if bio:
                print(f"📝 Bio: {bio[:100]}{'...' if len(bio) > 100 else ''}")

            # Métricas
            print(f"\n📊 Métricas:")
            print(f"   Seguidores: {result.get('followers_count', 0):,}")
            print(f"   Seguindo: {result.get('following_count', 0):,}")
            print(f"   Posts: {result.get('posts_count', 0):,}")

            # Status
            print(f"\n🔐 Status:")
            print(f"   Privado: {'Sim' if result.get('is_private') else 'Não'}")
            print(f"   Verificado: {'Sim' if result.get('is_verified') else 'Não'}")
            print(f"   Business: {'Sim' if result.get('is_business') else 'Não'}")
            print(f"   Categoria: {result.get('category', 'N/A')}")

            # Contato
            print(f"\n📧 Contato:")
            print(f"   Email: {result.get('email', result.get('email_hint', 'N/A'))}")
            print(f"   Telefone: {result.get('phone', result.get('phone_hint', 'N/A'))}")
            print(f"   WhatsApp: {'Sim' if result.get('whatsapp_linked') else 'Não'}")

            # Score
            if "score" in result:
                print(f"\n🎯 QUALIFICAÇÃO:")
                print(f"   Score: {result['score']}/100")
                print(f"   Classificação: {result['classification']}")
                print(f"   Sinais: {', '.join(result.get('signals', []))}")

        else:
            print(f"❌ Erro: {result.get('error', 'Desconhecido')}")

        # Salvar output
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\n💾 Salvo em: {args.output}")

        print("\n" + "="*60 + "\n")

    except Exception as e:
        print(f"❌ Erro: {e}")
        raise


if __name__ == "__main__":
    main()
