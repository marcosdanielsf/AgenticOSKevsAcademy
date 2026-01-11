#!/usr/bin/env python3
"""
🚀 ENRIQUECIMENTO DE LEADS V2
============================
Pipeline completo para extrair dados de contato:
1. Extrai WhatsApp de links wa.me
2. Scrape Linktrees para email/telefone
3. Scrape sites dos médicos

Uso:
    python enrich_leads_v2.py --limit 10
    python enrich_leads_v2.py --all
"""

import os
import re
import json
import time
import requests
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv
from supabase import create_client
from bs4 import BeautifulSoup
import logging

load_dotenv()

# Config
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://bfumywvwubvernvhjehk.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LeadEnricher:
    """Pipeline de enriquecimento de leads"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
        })

    def extract_whatsapp_from_url(self, url: str) -> Optional[str]:
        """Extrai número do WhatsApp de URLs wa.me"""
        if not url:
            return None

        # Padrões de WhatsApp
        patterns = [
            r'wa\.me/(\d+)',
            r'wa\.me/message/(\w+)',  # Links encurtados
            r'api\.whatsapp\.com/send\?phone=(\d+)',
            r'whatsapp\.com/send\?phone=(\d+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def scrape_linktree(self, url: str) -> Dict:
        """Scrape Linktree para extrair links e contatos"""
        result = {
            'emails': [],
            'phones': [],
            'whatsapp': None,
            'linkedin': None,
            'website': None,
            'links': []
        }

        if not url or 'linktr.ee' not in url.lower():
            return result

        try:
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                return result

            soup = BeautifulSoup(response.text, 'html.parser')

            # Buscar todos os links
            links = soup.find_all('a', href=True)

            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True).lower()

                # WhatsApp
                if 'wa.me' in href or 'whatsapp' in href.lower():
                    phone = self.extract_whatsapp_from_url(href)
                    if phone:
                        result['whatsapp'] = phone
                    result['links'].append({'type': 'whatsapp', 'url': href})

                # LinkedIn
                elif 'linkedin.com' in href.lower():
                    result['linkedin'] = href
                    result['links'].append({'type': 'linkedin', 'url': href})

                # Email (mailto)
                elif href.startswith('mailto:'):
                    email = href.replace('mailto:', '').split('?')[0]
                    result['emails'].append(email)
                    result['links'].append({'type': 'email', 'url': email})

                # Telefone (tel)
                elif href.startswith('tel:'):
                    phone = href.replace('tel:', '').replace('+', '')
                    result['phones'].append(phone)
                    result['links'].append({'type': 'phone', 'url': phone})

                # Site próprio
                elif 'http' in href and 'linktr.ee' not in href and 'instagram' not in href.lower():
                    if not result['website']:
                        result['website'] = href
                    result['links'].append({'type': 'website', 'url': href})

            # Buscar emails no texto da página
            page_text = soup.get_text()
            emails_in_text = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', page_text)
            for email in emails_in_text:
                if email not in result['emails']:
                    result['emails'].append(email)

            # Buscar telefones no texto
            phones_in_text = re.findall(r'\(?\d{2}\)?[\s.-]?\d{4,5}[\s.-]?\d{4}', page_text)
            for phone in phones_in_text:
                clean_phone = re.sub(r'[^\d]', '', phone)
                if clean_phone not in result['phones'] and len(clean_phone) >= 10:
                    result['phones'].append(clean_phone)

        except Exception as e:
            logger.warning(f"Erro ao scrape Linktree {url}: {e}")

        return result

    def scrape_website(self, url: str) -> Dict:
        """Scrape site para extrair contatos"""
        result = {
            'emails': [],
            'phones': [],
            'whatsapp': None,
            'linkedin': None,
        }

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
            result['emails'] = list(set(emails))[:3]  # Max 3

            # Telefones
            phones = re.findall(r'\(?\d{2}\)?[\s.-]?\d{4,5}[\s.-]?\d{4}', page_text)
            result['phones'] = list(set([re.sub(r'[^\d]', '', p) for p in phones]))[:3]

            # WhatsApp em links
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if 'wa.me' in href or 'whatsapp' in href.lower():
                    phone = self.extract_whatsapp_from_url(href)
                    if phone:
                        result['whatsapp'] = phone
                        break

            # LinkedIn
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if 'linkedin.com' in href.lower():
                    result['linkedin'] = href
                    break

        except Exception as e:
            logger.warning(f"Erro ao scrape {url}: {e}")

        return result

    def enrich_lead(self, lead: Dict) -> Dict:
        """Enriquece um lead com dados de contato"""
        enrichment = {
            'email': None,
            'phone': None,
            'whatsapp': None,
            'linkedin_url': None,
            'enrichment_source': [],
        }

        handle = lead.get('instagram_handle', '').replace('@', '')

        # URL pode estar em custom_fields.website ou instagram_url
        custom_fields = lead.get('custom_fields') or {}
        external_url = custom_fields.get('website') or lead.get('instagram_url') or ''
        bio = lead.get('instagram_bio') or ''

        logger.info(f"🔍 Enriquecendo @{handle}")

        # 1. Verificar se external_url é WhatsApp direto
        if external_url:
            whatsapp = self.extract_whatsapp_from_url(external_url)
            if whatsapp:
                enrichment['whatsapp'] = whatsapp
                enrichment['phone'] = whatsapp
                enrichment['enrichment_source'].append('wa.me_direct')
                logger.info(f"   ✅ WhatsApp: {whatsapp}")

        # 2. Se for Linktree, fazer scrape
        if external_url and 'linktr.ee' in external_url.lower():
            linktree_data = self.scrape_linktree(external_url)

            if linktree_data['whatsapp'] and not enrichment['whatsapp']:
                enrichment['whatsapp'] = linktree_data['whatsapp']
                enrichment['phone'] = linktree_data['whatsapp']
                enrichment['enrichment_source'].append('linktree')

            if linktree_data['emails'] and not enrichment['email']:
                enrichment['email'] = linktree_data['emails'][0]
                enrichment['enrichment_source'].append('linktree')

            if linktree_data['linkedin'] and not enrichment['linkedin_url']:
                enrichment['linkedin_url'] = linktree_data['linkedin']
                enrichment['enrichment_source'].append('linktree')

            if linktree_data['phones'] and not enrichment['phone']:
                enrichment['phone'] = linktree_data['phones'][0]
                enrichment['enrichment_source'].append('linktree')

            # Se encontrou website no linktree, fazer scrape dele também
            if linktree_data['website']:
                time.sleep(1)  # Rate limit
                website_data = self.scrape_website(linktree_data['website'])

                if website_data['emails'] and not enrichment['email']:
                    enrichment['email'] = website_data['emails'][0]
                    enrichment['enrichment_source'].append('website')

                if website_data['phones'] and not enrichment['phone']:
                    enrichment['phone'] = website_data['phones'][0]
                    enrichment['enrichment_source'].append('website')

                if website_data['whatsapp'] and not enrichment['whatsapp']:
                    enrichment['whatsapp'] = website_data['whatsapp']
                    enrichment['enrichment_source'].append('website')

        # 3. Se for site direto (não linktree), fazer scrape
        elif external_url and 'http' in external_url and 'instagram' not in external_url.lower():
            website_data = self.scrape_website(external_url)

            if website_data['emails'] and not enrichment['email']:
                enrichment['email'] = website_data['emails'][0]
                enrichment['enrichment_source'].append('website')

            if website_data['phones'] and not enrichment['phone']:
                enrichment['phone'] = website_data['phones'][0]
                enrichment['enrichment_source'].append('website')

            if website_data['whatsapp'] and not enrichment['whatsapp']:
                enrichment['whatsapp'] = website_data['whatsapp']
                enrichment['enrichment_source'].append('website')

            if website_data['linkedin'] and not enrichment['linkedin_url']:
                enrichment['linkedin_url'] = website_data['linkedin']
                enrichment['enrichment_source'].append('website')

        # 4. Extrair da bio se ainda não tem dados
        if bio:
            # Email da bio
            if not enrichment['email']:
                emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', bio)
                if emails:
                    enrichment['email'] = emails[0]
                    enrichment['enrichment_source'].append('bio')

            # Telefone da bio
            if not enrichment['phone']:
                phones = re.findall(r'\(?\d{2}\)?[\s.-]?\d{4,5}[\s.-]?\d{4}', bio)
                if phones:
                    enrichment['phone'] = re.sub(r'[^\d]', '', phones[0])
                    enrichment['enrichment_source'].append('bio')

        # Log do resultado
        if enrichment['email'] or enrichment['phone'] or enrichment['whatsapp'] or enrichment['linkedin_url']:
            logger.info(f"   📧 Email: {enrichment['email']}")
            logger.info(f"   📱 Phone: {enrichment['phone']}")
            logger.info(f"   💬 WhatsApp: {enrichment['whatsapp']}")
            logger.info(f"   💼 LinkedIn: {enrichment['linkedin_url']}")
            logger.info(f"   📍 Source: {enrichment['enrichment_source']}")
        else:
            logger.info(f"   ❌ Nenhum dado encontrado")

        return enrichment


def update_lead_supabase(lead_id: str, enrichment: Dict) -> bool:
    """Atualiza lead no Supabase"""
    update_data = {
        'updated_at': datetime.now().isoformat()
    }

    if enrichment.get('email'):
        update_data['email'] = enrichment['email']
    if enrichment.get('phone'):
        update_data['phone'] = enrichment['phone']
    if enrichment.get('whatsapp'):
        update_data['whatsapp'] = enrichment['whatsapp']
    if enrichment.get('linkedin_url'):
        update_data['linkedin_url'] = enrichment['linkedin_url']
    if enrichment.get('enrichment_source'):
        # Salvar em custom_fields
        update_data['custom_fields'] = {'enrichment_source': enrichment['enrichment_source']}

    if len(update_data) > 1:
        try:
            supabase.table('socialfy_leads').update(update_data).eq('id', lead_id).execute()
            return True
        except Exception as e:
            logger.error(f"Erro ao atualizar lead {lead_id}: {e}")
            return False
    return False


def get_leads_to_enrich(limit: int = 50) -> List[Dict]:
    """Busca leads que precisam de enriquecimento"""
    result = supabase.table('socialfy_leads').select(
        'id, instagram_handle, name, instagram_bio, instagram_url, email, phone, whatsapp, linkedin_url, instagram_followers, custom_fields'
    ).or_('email.is.null,phone.is.null,whatsapp.is.null').not_.is_(
        'scraped_at', 'null'
    ).order('instagram_followers', desc=True).limit(limit).execute()

    return result.data


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Enriquecer leads com dados de contato')
    parser.add_argument('--limit', type=int, default=10, help='Número de leads')
    parser.add_argument('--all', action='store_true', help='Processar todos')
    args = parser.parse_args()

    print("="*60)
    print("🚀 ENRIQUECIMENTO DE LEADS V2")
    print("="*60)

    limit = 1000 if args.all else args.limit
    leads = get_leads_to_enrich(limit)

    print(f"\n📊 {len(leads)} leads para enriquecer")

    if not leads:
        print("✅ Todos os leads já estão enriquecidos!")
        return

    enricher = LeadEnricher()
    enriched_count = 0

    for i, lead in enumerate(leads, 1):
        handle = lead.get('instagram_handle', '').replace('@', '')
        print(f"\n[{i}/{len(leads)}] @{handle}")

        # Verificar se já tem dados completos
        if lead.get('email') and lead.get('phone') and lead.get('whatsapp'):
            print("   ⏭️ Já tem dados completos, pulando...")
            continue

        enrichment = enricher.enrich_lead(lead)

        # Só atualizar se encontrou algo novo
        has_new_data = (
            (enrichment['email'] and not lead.get('email')) or
            (enrichment['phone'] and not lead.get('phone')) or
            (enrichment['whatsapp'] and not lead.get('whatsapp')) or
            (enrichment['linkedin_url'] and not lead.get('linkedin_url'))
        )

        if has_new_data:
            if update_lead_supabase(lead['id'], enrichment):
                enriched_count += 1
                print("   ✅ Salvo no Supabase")

        # Rate limit
        time.sleep(2)

    print("\n" + "="*60)
    print(f"✅ FINALIZADO")
    print(f"   Total processados: {len(leads)}")
    print(f"   Enriquecidos: {enriched_count}")
    print("="*60)


if __name__ == "__main__":
    main()
