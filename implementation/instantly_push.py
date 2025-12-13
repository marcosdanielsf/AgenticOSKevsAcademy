"""
Instantly Push - Push leads from Google Sheets to Instantly.ai campaigns.

This script reads leads from a specified Google Sheet and pushes them
to an Instantly campaign one-by-one via the API v2.

Usage:
    ./venv/bin/python3 implementation/instantly_push.py \
        --sheet "mens health NY" \
        --campaign_id "adb1f3f6-0035-4edd-9252-1073138787df"

API Reference:
    - Endpoint: POST /api/v2/leads
    - Auth: Bearer token in Authorization header
    - Bulk upload via 'leads' array does NOT work; must send individually
"""

import os
import argparse
import json
import requests
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

INSTANTLY_API_KEY = os.getenv('INSTANTLY_API_KEY')
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
SERVICE_ACCOUNT_FILE = 'service_account.json'
BASE_URL = "https://api.instantly.ai/api/v2"

if not INSTANTLY_API_KEY or not SPREADSHEET_ID:
    raise ValueError("Missing INSTANTLY_API_KEY or SPREADSHEET_ID in .env")


def get_sheet(sheet_name):
    """Connect to Google Sheets and return the specified worksheet."""
    scopes = ['https://www.googleapis.com/auth/spreadsheets']
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID).worksheet(sheet_name)


def extract_city(address):
    """
    Extract city from address string.
    Uses simple heuristic: city is usually the second-to-last comma-separated part.
    Example: "123 Main St, Austin, TX 78701" -> "Austin"
    """
    if not address:
        return ""
    parts = address.split(',')
    if len(parts) >= 2:
        # Take the second to last part, then first word (to avoid state/zip)
        return parts[-2].strip().split(' ')[0]
    return ""


def push_leads(sheet_name, campaign_id):
    """
    Read leads from Google Sheet and push to Instantly campaign.
    
    Args:
        sheet_name: Name of the Google Sheet tab
        campaign_id: UUID of the Instantly campaign
    """
    print(f"--- Reading Sheet: {sheet_name} ---")
    sheet = get_sheet(sheet_name)
    data = sheet.get_all_records()
    
    # Build leads list from sheet data
    leads = []
    for row in data:
        emails_raw = row.get("Emails", "")
        if not emails_raw:
            continue
            
        # Take the first email found (split by newline)
        email = emails_raw.split('\n')[0].strip()
        if not email:
            continue
            
        company_name = row.get("Business Name", "")
        website = row.get("Website", "")
        phone = row.get("Phone", "")
        address = row.get("Address", "")
        city = extract_city(address)
        
        # Build lead object matching Instantly's expected format
        lead = {
            "email": email,
            "company_name": company_name,
            "website": website,
            "phone": phone,
            "custom_variables": {
                "City": city,
                "Address": address,
                "LinkedIn": row.get("LinkedIn", "").split('\n')[0],
                "Source": "Agentic OS Scraper"
            }
        }
        leads.append(lead)
        
    print(f"Found {len(leads)} valid leads.")
    
    if not leads:
        print("No leads to push.")
        return

    # API setup
    url = f"{BASE_URL}/leads"
    headers = {
        "Authorization": f"Bearer {INSTANTLY_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Preview first email
    first_lead = leads[0]
    print("\n--- Email Preview (with template variables) ---")
    print(f"To: {first_lead['email']}")
    print(f"Subject: Scaling {{{{companyName}}}}")
    print("Body Preview:")
    print(f"  Company: {first_lead['company_name']}")
    print(f"  City: {first_lead['custom_variables']['City']}")
    print("---------------------------------------------\n")

    # Push leads one by one (bulk upload via 'leads' array is broken in API v2)
    success_count = 0
    fail_count = 0
    
    print(f"Pushing {len(leads)} leads to Campaign {campaign_id}...")
    
    for lead in leads:
        # Build payload - flatten lead into root of payload
        # NOTE: The key is "campaign" NOT "campaign_id"
        payload = {
            "campaign": campaign_id,
            "skip_if_in_campaign": True,
            "skip_if_in_workspace": False,
            **lead  # Unpack email, company_name, website, phone, custom_variables
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                success_count += 1
                print(f"✓ {lead['email']}")
            else:
                fail_count += 1
                error_msg = response.json().get('message', response.text)
                print(f"✗ {lead['email']} - {error_msg}")
                
        except Exception as e:
            fail_count += 1
            print(f"✗ {lead['email']} - Exception: {e}")
            
    print(f"\n--- Finished ---")
    print(f"Success: {success_count}")
    print(f"Failed: {fail_count}")


def main():
    parser = argparse.ArgumentParser(
        description="Push leads from Google Sheet to Instantly campaign"
    )
    parser.add_argument(
        "--sheet", 
        required=True, 
        help="Name of the Google Sheet tab to read from"
    )
    parser.add_argument(
        "--campaign_id", 
        required=True, 
        help="UUID of the Instantly Campaign"
    )
    
    args = parser.parse_args()
    push_leads(args.sheet, args.campaign_id)


if __name__ == "__main__":
    main()
