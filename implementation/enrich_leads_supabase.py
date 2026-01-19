#!/usr/bin/env python3
"""
Enriquecimento de Leads com Apify
- Busca leads do Supabase
- Usa Contact Info Scraper para extrair email/phone/LinkedIn
- Atualiza Supabase com dados enriquecidos
"""

import os
import re
import time
import json
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
from apify_client import ApifyClient

load_dotenv()

# Config - Variáveis de ambiente obrigatórias
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
APIFY_TOKEN = os.getenv('APIFY_API_TOKEN')

if not all([SUPABASE_URL, SUPABASE_KEY, APIFY_TOKEN]):
    raise ValueError("Variáveis de ambiente obrigatórias: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, APIFY_API_TOKEN")

# Apify Actors
CONTACT_SCRAPER_ACTOR = "vdrmota/contact-info-scraper"  # Email, phone, social from websites
LINKEDIN_FINDER_ACTOR = "anchor/linkedin-people-finder"  # Find LinkedIn by name
INSTAGRAM_SCRAPER_ACTOR = "apify/instagram-profile-scraper"  # Get more Instagram data

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
apify = ApifyClient(APIFY_TOKEN)


def get_leads_to_enrich(limit=50):
    """Busca leads que precisam de enriquecimento (sem email/phone)"""
    result = supabase.table('socialfy_leads').select(
        'id, instagram_handle, name, instagram_bio, instagram_url, email, phone, linkedin_url'
    ).is_('email', 'null').not_.is_('scraped_at', 'null').order(
        'instagram_followers', desc=True
    ).limit(limit).execute()

    return result.data


def extract_website_from_bio(bio):
    """Extrai URLs de websites da bio do Instagram"""
    if not bio:
        return None

    # Padrões de URL
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    urls = re.findall(url_pattern, bio)

    # Filtrar URLs de redes sociais (queremos sites próprios)
    social_domains = ['instagram.com', 'facebook.com', 'twitter.com', 'tiktok.com', 'youtube.com', 'wa.me', 'whatsapp.com']

    for url in urls:
        is_social = any(domain in url.lower() for domain in social_domains)
        if not is_social:
            return url

    # Procurar também por linktr.ee, bio.link etc
    linktree_pattern = r'linktr\.ee/\w+'
    linktree = re.findall(linktree_pattern, bio, re.IGNORECASE)
    if linktree:
        return f"https://{linktree[0]}"

    return None


def extract_whatsapp_from_bio(bio):
    """Extrai número de WhatsApp da bio"""
    if not bio:
        return None

    # Padrões de WhatsApp
    patterns = [
        r'wa\.me/(\d+)',
        r'api\.whatsapp\.com/send\?phone=(\d+)',
        r'whatsapp[:\s]*[\+]?(\d{10,15})',
        r'zap[:\s]*[\+]?(\d{10,15})',
        r'\(?\d{2}\)?[\s.-]?\d{4,5}[\s.-]?\d{4}',  # Formato brasileiro
    ]

    for pattern in patterns:
        match = re.search(pattern, bio, re.IGNORECASE)
        if match:
            return match.group(1) if match.groups() else match.group(0)

    return None


def extract_email_from_bio(bio):
    """Extrai email da bio"""
    if not bio:
        return None

    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, bio)

    return emails[0] if emails else None


def enrich_with_contact_scraper(websites):
    """Usa Contact Info Scraper do Apify para extrair dados de websites"""
    if not websites:
        return {}

    print(f"🔍 Scraping {len(websites)} websites com Apify...")

    start_urls = [{"url": url} for url in websites if url]

    run_input = {
        "startUrls": start_urls,
        "maxCrawlingDepth": 1,  # Ir 1 nível de profundidade
        "proxyConfiguration": {"useApifyProxy": True},
        "maxRequestsPerCrawl": len(websites) * 3,
    }

    try:
        run = apify.actor(CONTACT_SCRAPER_ACTOR).call(run_input=run_input, timeout_secs=300)
        print(f"✅ Scraper finalizado. Dataset: {run['defaultDatasetId']}")

        results = {}
        for item in apify.dataset(run['defaultDatasetId']).iterate_items():
            url = item.get("url", "")
            results[url] = {
                "emails": item.get("emails", []),
                "phones": item.get("phones", []),
                "linkedin": item.get("linkedIns", []),
                "facebook": item.get("facebooks", []),
                "twitter": item.get("twitters", []),
            }

        return results
    except Exception as e:
        print(f"❌ Erro no scraper: {e}")
        return {}


def enrich_with_linkedin_finder(leads):
    """Busca perfis LinkedIn pelo nome da pessoa"""
    if not leads:
        return {}

    print(f"🔍 Buscando LinkedIn para {len(leads)} pessoas...")

    searches = []
    for lead in leads:
        name = lead.get('name', '')
        # Adiciona contexto de médico/Brasil para melhorar a busca
        bio = lead.get('instagram_bio', '')

        # Extrair especialidade da bio
        especialidades = ['cirurgião', 'dermatologista', 'cardiologista', 'pediatra', 'oftalmologista',
                         'ortopedista', 'ginecologista', 'urologista', 'psiquiatra', 'neurologista']
        especialidade = ''
        for esp in especialidades:
            if esp in bio.lower():
                especialidade = esp
                break

        search_query = f"{name} {especialidade} médico Brasil".strip()
        searches.append({"searchQuery": search_query})

    run_input = {
        "searches": searches,
        "maxResults": 1,  # Só o primeiro resultado
        "proxyConfiguration": {"useApifyProxy": True},
    }

    try:
        run = apify.actor(LINKEDIN_FINDER_ACTOR).call(run_input=run_input, timeout_secs=300)
        print(f"✅ LinkedIn finder finalizado. Dataset: {run['defaultDatasetId']}")

        results = {}
        for item in apify.dataset(run['defaultDatasetId']).iterate_items():
            query = item.get("searchQuery", "")
            profile_url = item.get("linkedInProfileUrl", "")
            if profile_url:
                # Mapear de volta pelo nome
                for lead in leads:
                    if lead['name'] in query:
                        results[lead['id']] = profile_url
                        break

        return results
    except Exception as e:
        print(f"❌ Erro no LinkedIn finder: {e}")
        return {}


def update_lead_supabase(lead_id, data):
    """Atualiza lead no Supabase com dados enriquecidos"""
    update_data = {
        "updated_at": datetime.now().isoformat()
    }

    if data.get('email'):
        update_data['email'] = data['email']
    if data.get('phone'):
        update_data['phone'] = data['phone']
    if data.get('whatsapp'):
        update_data['whatsapp'] = data['whatsapp']
    if data.get('linkedin_url'):
        update_data['linkedin_url'] = data['linkedin_url']

    if len(update_data) > 1:  # Tem algo além do updated_at
        supabase.table('socialfy_leads').update(update_data).eq('id', lead_id).execute()
        return True
    return False


def enrich_leads(limit=10, use_apify=True):
    """Pipeline principal de enriquecimento"""
    print("="*60)
    print("🚀 INICIANDO ENRIQUECIMENTO DE LEADS")
    print("="*60)

    # 1. Buscar leads que precisam enriquecimento
    leads = get_leads_to_enrich(limit)
    print(f"\n📊 {len(leads)} leads precisam de enriquecimento")

    if not leads:
        print("✅ Todos os leads já estão enriquecidos!")
        return

    enriched_count = 0
    websites_to_scrape = []
    leads_for_linkedin = []

    # 2. Primeira passada: extrair dados da bio
    print("\n📝 Extraindo dados das bios...")
    for lead in leads:
        bio = lead.get('instagram_bio', '')
        lead_id = lead['id']
        handle = lead.get('instagram_handle', '')

        # Tentar extrair da bio primeiro
        email = extract_email_from_bio(bio)
        whatsapp = extract_whatsapp_from_bio(bio)
        website = extract_website_from_bio(bio)

        enrichment_data = {}

        if email:
            enrichment_data['email'] = email
            print(f"  ✅ @{handle}: email encontrado na bio")

        if whatsapp:
            enrichment_data['whatsapp'] = whatsapp
            print(f"  ✅ @{handle}: WhatsApp encontrado na bio")

        if enrichment_data:
            update_lead_supabase(lead_id, enrichment_data)
            enriched_count += 1

        # Coletar websites e leads para Apify
        if website and not email:
            websites_to_scrape.append({"lead_id": lead_id, "url": website, "handle": handle})

        if not lead.get('linkedin_url'):
            leads_for_linkedin.append(lead)

    # 3. Segunda passada: usar Apify para websites
    if use_apify and websites_to_scrape:
        print(f"\n🌐 Scraping {len(websites_to_scrape)} websites...")
        urls = [w['url'] for w in websites_to_scrape]
        contact_data = enrich_with_contact_scraper(urls)

        for website in websites_to_scrape:
            url = website['url']
            if url in contact_data:
                data = contact_data[url]
                enrichment = {}

                if data.get('emails'):
                    enrichment['email'] = data['emails'][0]
                if data.get('phones'):
                    enrichment['phone'] = data['phones'][0]
                if data.get('linkedin'):
                    enrichment['linkedin_url'] = data['linkedin'][0]

                if enrichment:
                    update_lead_supabase(website['lead_id'], enrichment)
                    print(f"  ✅ @{website['handle']}: dados do website")
                    enriched_count += 1

    # 4. Terceira passada: buscar LinkedIn pelo nome
    if use_apify and leads_for_linkedin:
        print(f"\n🔍 Buscando LinkedIn para {len(leads_for_linkedin)} leads...")
        linkedin_data = enrich_with_linkedin_finder(leads_for_linkedin[:20])  # Limitar a 20

        for lead_id, linkedin_url in linkedin_data.items():
            update_lead_supabase(lead_id, {'linkedin_url': linkedin_url})
            print(f"  ✅ LinkedIn encontrado")
            enriched_count += 1

    print("\n" + "="*60)
    print(f"✅ ENRIQUECIMENTO FINALIZADO")
    print(f"   Total processados: {len(leads)}")
    print(f"   Enriquecidos: {enriched_count}")
    print("="*60)


def quick_enrich_from_bio(limit=100):
    """Enriquecimento rápido apenas extraindo dados da bio (sem Apify)"""
    print("="*60)
    print("⚡ ENRIQUECIMENTO RÁPIDO (só bio)")
    print("="*60)

    # Buscar TODOS os leads com bio
    result = supabase.table('socialfy_leads').select(
        'id, instagram_handle, name, instagram_bio, email, phone, whatsapp'
    ).not_.is_('instagram_bio', 'null').limit(limit).execute()

    leads = result.data
    print(f"\n📊 {len(leads)} leads com bio")

    enriched_count = 0

    for lead in leads:
        bio = lead.get('instagram_bio', '')
        lead_id = lead['id']
        handle = lead.get('instagram_handle', '')

        # Só enriquecer se não tiver os dados
        enrichment_data = {}

        if not lead.get('email'):
            email = extract_email_from_bio(bio)
            if email:
                enrichment_data['email'] = email

        if not lead.get('whatsapp') and not lead.get('phone'):
            whatsapp = extract_whatsapp_from_bio(bio)
            if whatsapp:
                enrichment_data['whatsapp'] = whatsapp
                enrichment_data['phone'] = whatsapp

        if enrichment_data:
            update_lead_supabase(lead_id, enrichment_data)
            print(f"  ✅ @{handle}: {list(enrichment_data.keys())}")
            enriched_count += 1

    print(f"\n✅ {enriched_count} leads enriquecidos da bio")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Enriquecer leads com dados de contato")
    parser.add_argument("--limit", type=int, default=10, help="Número de leads para processar")
    parser.add_argument("--quick", action="store_true", help="Modo rápido (só extrai da bio)")
    parser.add_argument("--no-apify", action="store_true", help="Não usar Apify")

    args = parser.parse_args()

    if args.quick:
        quick_enrich_from_bio(args.limit)
    else:
        enrich_leads(args.limit, use_apify=not args.no_apify)
