#!/usr/bin/env python3
"""
🚀 PIPELINE COMPLETO DE ENRIQUECIMENTO DE LEADS
===============================================
1. Busca external_url via Instagram API
2. Faz scrape de Linktrees e sites
3. Extrai email, phone, WhatsApp, LinkedIn
4. Salva no Supabase

Uso:
    python enrich_pipeline.py --limit 10
    python enrich_pipeline.py --all
"""

import os
import re
import sys
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional

from dotenv import load_dotenv
from supabase import create_client
import requests
from bs4 import BeautifulSoup

# Adicionar path para imports locais
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from instagram_api_scraper import InstagramAPIScraper

load_dotenv()

# Config
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://bfumywvwubvernvhjehk.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EnrichmentPipeline:
    """Pipeline completo de enriquecimento"""

    def __init__(self):
        self.scraper = InstagramAPIScraper()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })
        self.stats = {
            'processed': 0,
            'urls_found': 0,
            'enriched': 0,
            'emails': 0,
            'phones': 0,
            'whatsapp': 0,
            'linkedin': 0,
            'errors': 0,
        }

    def get_leads_to_enrich(self, limit: int = 50) -> List[Dict]:
        """Busca leads que precisam de enriquecimento"""
        result = supabase.table('socialfy_leads').select(
            'id, instagram_handle, name, instagram_bio, email, phone, whatsapp, linkedin_url, instagram_followers, custom_fields'
        ).or_('email.is.null,phone.is.null,whatsapp.is.null').not_.is_(
            'scraped_at', 'null'
        ).order('instagram_followers', desc=True).limit(limit).execute()

        return result.data

    def fetch_external_url(self, handle: str) -> Optional[str]:
        """Busca external_url do perfil via Instagram API"""
        clean_handle = handle.replace('@', '').replace('@@', '')

        try:
            profile = self.scraper.get_profile(clean_handle)

            if profile.get('success'):
                external_url = profile.get('external_url', '')
                if external_url:
                    return external_url

        except Exception as e:
            logger.warning(f"Erro ao buscar external_url de @{clean_handle}: {e}")

        return None

    def extract_whatsapp_from_url(self, url: str) -> Optional[str]:
        """Extrai número do WhatsApp de URLs"""
        if not url:
            return None

        patterns = [
            r'wa\.me/(\d+)',
            r'api\.whatsapp\.com/send\?phone=(\d+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def scrape_linktree(self, url: str) -> Dict:
        """Scrape Linktree"""
        result = {'emails': [], 'phones': [], 'whatsapp': None, 'linkedin': None}

        if not url or 'linktr.ee' not in url.lower():
            return result

        try:
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                return result

            soup = BeautifulSoup(response.text, 'html.parser')

            for link in soup.find_all('a', href=True):
                href = link.get('href', '')

                # WhatsApp
                if 'wa.me' in href or 'whatsapp' in href.lower():
                    phone = self.extract_whatsapp_from_url(href)
                    if phone:
                        result['whatsapp'] = phone

                # LinkedIn
                elif 'linkedin.com' in href.lower():
                    result['linkedin'] = href

                # Email
                elif href.startswith('mailto:'):
                    email = href.replace('mailto:', '').split('?')[0]
                    if self._is_valid_email(email):
                        result['emails'].append(email)

                # Telefone
                elif href.startswith('tel:'):
                    phone = re.sub(r'[^\d]', '', href.replace('tel:', ''))
                    if len(phone) >= 10:
                        result['phones'].append(phone)

            # Buscar emails no texto
            page_text = soup.get_text()
            emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', page_text)
            for email in emails:
                if self._is_valid_email(email) and email not in result['emails']:
                    result['emails'].append(email)

        except Exception as e:
            logger.warning(f"Erro scraping Linktree {url}: {e}")

        return result

    def scrape_website(self, url: str) -> Dict:
        """Scrape site genérico"""
        result = {'emails': [], 'phones': [], 'whatsapp': None, 'linkedin': None}

        if not url:
            return result

        try:
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                return result

            soup = BeautifulSoup(response.text, 'html.parser')
            page_text = soup.get_text()

            # Emails
            emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', page_text)
            result['emails'] = [e for e in set(emails) if self._is_valid_email(e)][:3]

            # WhatsApp
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if 'wa.me' in href:
                    phone = self.extract_whatsapp_from_url(href)
                    if phone:
                        result['whatsapp'] = phone
                        break

            # LinkedIn
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if 'linkedin.com/in/' in href.lower():
                    result['linkedin'] = href
                    break

        except Exception as e:
            logger.warning(f"Erro scraping {url}: {e}")

        return result

    def _is_valid_email(self, email: str) -> bool:
        """Valida se email parece real"""
        if not email:
            return False

        # Filtrar emails inválidos
        invalid_patterns = [
            'example.com', 'test.com', 'email.com',
            'linktree', 'instagram', 'facebook',
            'sentry.io', 'wixpress', 'cloudflare',
        ]

        email_lower = email.lower()
        for pattern in invalid_patterns:
            if pattern in email_lower:
                return False

        # Verificar formato básico
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return False

        return True

    def enrich_lead(self, lead: Dict) -> Dict:
        """Enriquece um lead"""
        handle = lead.get('instagram_handle', '').replace('@', '').replace('@@', '')
        lead_id = lead['id']

        enrichment = {
            'email': None,
            'phone': None,
            'whatsapp': None,
            'linkedin_url': None,
            'external_url': None,
            'source': [],
        }

        # 1. Buscar external_url se não tiver
        custom_fields = lead.get('custom_fields') or {}
        external_url = custom_fields.get('website')

        if not external_url:
            logger.info(f"   📡 Buscando external_url via Instagram API...")
            external_url = self.fetch_external_url(handle)

            if external_url:
                enrichment['external_url'] = external_url
                self.stats['urls_found'] += 1
                logger.info(f"   🔗 URL: {external_url}")
                time.sleep(1)  # Rate limit Instagram
            else:
                logger.info(f"   ❌ Sem external_url")
                return enrichment

        # 2. Verificar se é WhatsApp direto
        if external_url:
            whatsapp = self.extract_whatsapp_from_url(external_url)
            if whatsapp and len(whatsapp) >= 10:
                enrichment['whatsapp'] = whatsapp
                enrichment['phone'] = whatsapp
                enrichment['source'].append('wa.me')
                logger.info(f"   💬 WhatsApp direto: {whatsapp}")

        # 3. Scrape Linktree
        if external_url and 'linktr.ee' in external_url.lower():
            logger.info(f"   🌳 Scraping Linktree...")
            linktree_data = self.scrape_linktree(external_url)

            if linktree_data['whatsapp'] and not enrichment['whatsapp']:
                enrichment['whatsapp'] = linktree_data['whatsapp']
                enrichment['phone'] = linktree_data['whatsapp']
                enrichment['source'].append('linktree')

            if linktree_data['emails'] and not enrichment['email']:
                enrichment['email'] = linktree_data['emails'][0]
                enrichment['source'].append('linktree')

            if linktree_data['linkedin'] and not enrichment['linkedin_url']:
                enrichment['linkedin_url'] = linktree_data['linkedin']
                enrichment['source'].append('linktree')

            if linktree_data['phones'] and not enrichment['phone']:
                enrichment['phone'] = linktree_data['phones'][0]
                enrichment['source'].append('linktree')

        # 4. Scrape site genérico
        elif external_url and 'http' in external_url:
            # Evitar scrape de redes sociais
            skip_domains = ['instagram.com', 'facebook.com', 'twitter.com', 'tiktok.com', 'youtube.com']
            should_scrape = not any(d in external_url.lower() for d in skip_domains)

            if should_scrape:
                logger.info(f"   🌐 Scraping website...")
                website_data = self.scrape_website(external_url)

                if website_data['emails'] and not enrichment['email']:
                    enrichment['email'] = website_data['emails'][0]
                    enrichment['source'].append('website')

                if website_data['whatsapp'] and not enrichment['whatsapp']:
                    enrichment['whatsapp'] = website_data['whatsapp']
                    enrichment['phone'] = website_data['whatsapp']
                    enrichment['source'].append('website')

                if website_data['linkedin'] and not enrichment['linkedin_url']:
                    enrichment['linkedin_url'] = website_data['linkedin']
                    enrichment['source'].append('website')

        return enrichment

    def update_lead(self, lead_id: str, handle: str, enrichment: Dict, current_lead: Dict) -> bool:
        """Atualiza lead no Supabase"""
        update_data = {'updated_at': datetime.now().isoformat()}

        # Só atualizar campos que não existem
        if enrichment.get('email') and not current_lead.get('email'):
            update_data['email'] = enrichment['email']
            self.stats['emails'] += 1

        if enrichment.get('phone') and not current_lead.get('phone'):
            update_data['phone'] = enrichment['phone']
            self.stats['phones'] += 1

        if enrichment.get('whatsapp') and not current_lead.get('whatsapp'):
            update_data['whatsapp'] = enrichment['whatsapp']
            self.stats['whatsapp'] += 1

        if enrichment.get('linkedin_url') and not current_lead.get('linkedin_url'):
            update_data['linkedin_url'] = enrichment['linkedin_url']
            self.stats['linkedin'] += 1

        # Atualizar custom_fields com website se encontrou
        if enrichment.get('external_url'):
            custom_fields = current_lead.get('custom_fields') or {}
            custom_fields['website'] = enrichment['external_url']
            if enrichment.get('source'):
                custom_fields['enrichment_source'] = enrichment['source']
            update_data['custom_fields'] = custom_fields

        if len(update_data) > 1:
            try:
                supabase.table('socialfy_leads').update(update_data).eq('id', lead_id).execute()
                self.stats['enriched'] += 1
                logger.info(f"   ✅ @{handle}: {list(update_data.keys())}")
                return True
            except Exception as e:
                logger.error(f"   ❌ Erro ao salvar @{handle}: {e}")
                self.stats['errors'] += 1

        return False

    def run(self, limit: int = 10):
        """Executa o pipeline"""
        print("="*70)
        print("🚀 PIPELINE DE ENRIQUECIMENTO DE LEADS")
        print("="*70)

        leads = self.get_leads_to_enrich(limit)
        total = len(leads)

        print(f"\n📊 {total} leads para processar\n")

        if not leads:
            print("✅ Todos os leads já estão enriquecidos!")
            return

        for i, lead in enumerate(leads, 1):
            handle = lead.get('instagram_handle', '').replace('@', '').replace('@@', '')
            self.stats['processed'] += 1

            print(f"\n[{i}/{total}] @{handle} ({lead.get('instagram_followers', 0):,} seg)")

            # Verificar se já tem dados completos
            if lead.get('email') and lead.get('phone') and lead.get('whatsapp'):
                print("   ⏭️ Já tem dados completos")
                continue

            enrichment = self.enrich_lead(lead)

            if any([enrichment.get('email'), enrichment.get('phone'),
                    enrichment.get('whatsapp'), enrichment.get('linkedin_url')]):
                self.update_lead(lead['id'], handle, enrichment, lead)
            else:
                print("   ❌ Nenhum dado encontrado")

            time.sleep(2)  # Rate limit geral

        # Estatísticas finais
        print("\n" + "="*70)
        print("📊 ESTATÍSTICAS")
        print("="*70)
        print(f"   Processados: {self.stats['processed']}")
        print(f"   URLs encontradas: {self.stats['urls_found']}")
        print(f"   Leads enriquecidos: {self.stats['enriched']}")
        print(f"   📧 Emails: {self.stats['emails']}")
        print(f"   📱 Phones: {self.stats['phones']}")
        print(f"   💬 WhatsApp: {self.stats['whatsapp']}")
        print(f"   💼 LinkedIn: {self.stats['linkedin']}")
        print(f"   ❌ Erros: {self.stats['errors']}")
        print("="*70)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Pipeline de enriquecimento de leads')
    parser.add_argument('--limit', type=int, default=10, help='Número de leads')
    parser.add_argument('--all', action='store_true', help='Processar todos')
    args = parser.parse_args()

    limit = 500 if args.all else args.limit

    pipeline = EnrichmentPipeline()
    pipeline.run(limit)


if __name__ == "__main__":
    main()
