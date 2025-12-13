"""
Instantly Create Campaign - Automate campaign creation, sequence setup, and lead pushing.

This script:
1. Creates a new campaign in Instantly.ai
2. Configures the schedule (Mon-Fri, 9-5 CST)
3. Adds all active email accounts to the campaign
4. Sets up the "Doctor OS" email sequence
5. (Optional) Pushes leads from a Google Sheet to the new campaign

Usage:
    ./venv/bin/python3 implementation/instantly_create_campaign.py \
        --name "Dentists Florida" \
        --sheet "dentists florida"
"""

import os
import argparse
import json
import requests
from dotenv import load_dotenv
# Import push_leads from the existing script to reuse logic
from instantly_push import push_leads

# Load environment variables
load_dotenv()

INSTANTLY_API_KEY = os.getenv('INSTANTLY_API_KEY')
BASE_URL = "https://api.instantly.ai/api/v2"

if not INSTANTLY_API_KEY:
    raise ValueError("Missing INSTANTLY_API_KEY in .env")

# Default Schedule (Mon-Fri, 9-5 CST)
DEFAULT_SCHEDULE = {
    "schedules": [
        {
            "name": "Default",
            "timing": {
                "from": "09:00",
                "to": "17:00"
            },
            "days": {
                "0": False, # Sunday
                "1": True,  # Monday
                "2": True,
                "3": True,
                "4": True,
                "5": True,  # Friday
                "6": False  # Saturday
            },
            "timezone": "America/Chicago"
        }
    ]
}

# Doctor OS Sequence Template
DOCTOR_OS_SEQUENCE = [
    {
        "steps": [
            {
                "type": "email",
                "delay": 0,
                "variants": [
                    {
                        "subject": "Scaling {{companyName}}",
                        "body": """<p>Hi {{firstName | there}},</p>
<p>I came across <strong>{{companyName}}</strong> while researching top clinics in <strong>{{City}}</strong>.</p>
<p>I'm building <strong>"Doctor OS"</strong> – an agentic operating system designed specifically to scale practices like yours.</p>
<p>It automates your entire marketing pipeline end-to-end:</p>
<ul>
<li><strong>LinkedIn Growth:</strong> Networking with potential partners and patients on autopilot.</li>
<li><strong>Video Content:</strong> Creating viral shorts to widen your reach (without you editing a thing).</li>
<li><strong>Appointments:</strong> Booking consults directly onto your calendar.</li>
</ul>
<p>It's like having a full-stack marketing team, but it runs entirely on AI.</p>
<p>Are you open to seeing how it works?</p>
<p>Best,<br>Adrian</p>""",
                        "v_disabled": False
                    }
                ]
            }
        ]
    }
]

def get_active_accounts():
    """Fetch all active email accounts (status=1 or 2) from Instantly."""
    url = f"{BASE_URL}/accounts"
    headers = {"Authorization": f"Bearer {INSTANTLY_API_KEY}"}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # Handle potential wrapping
        accounts = data.get('accounts', data.get('items', data))
        
        # Filter for active accounts (Status 1=Active, 2=Warmup Only?)
        # Let's use all accounts that are not disabled/error
        active_emails = [
            acc['email'] for acc in accounts 
            if acc.get('status') in [1, 2]
        ]
        return active_emails
        
    except Exception as e:
        print(f"Error fetching accounts: {e}")
        return []

def create_campaign(name, email_list):
    """Create a new campaign with schedule and email accounts."""
    url = f"{BASE_URL}/campaigns"
    headers = {
        "Authorization": f"Bearer {INSTANTLY_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "name": name,
        "email_list": email_list,
        "campaign_schedule": DEFAULT_SCHEDULE
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error creating campaign: {e}")
        if 'response' in locals():
            print(f"Response: {response.text}")
        return None

def add_sequence(campaign_id):
    """Add the Doctor OS sequence to the campaign."""
    url = f"{BASE_URL}/campaigns/{campaign_id}"
    headers = {
        "Authorization": f"Bearer {INSTANTLY_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "sequences": DOCTOR_OS_SEQUENCE
    }
    
    try:
        response = requests.patch(url, headers=headers, json=payload)
        response.raise_for_status()
        print("Sequence added successfully.")
        return True
    except Exception as e:
        print(f"Error adding sequence: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Create Instantly Campaign & Push Leads")
    parser.add_argument("--name", required=True, help="Name of the new campaign")
    parser.add_argument("--sheet", help="Google Sheet name to push leads from (optional)")
    
    args = parser.parse_args()
    
    print(f"--- Starting Campaign Creation: {args.name} ---")
    
    # 1. Get Accounts
    accounts = get_active_accounts()
    if not accounts:
        print("No active email accounts found. Aborting.")
        return
    print(f"Found {len(accounts)} active email accounts.")
    
    # 2. Create Campaign
    campaign = create_campaign(args.name, accounts)
    if not campaign:
        return
        
    campaign_id = campaign['id']
    print(f"Campaign Created! ID: {campaign_id}")
    
    # 3. Add Sequence
    if add_sequence(campaign_id):
        print("Doctor OS Sequence configured.")
        
    # 4. Push Leads (Optional)
    if args.sheet:
        print(f"\n--- Pushing Leads from Sheet: {args.sheet} ---")
        push_leads(args.sheet, campaign_id)
        
    print(f"\nDone! Campaign '{args.name}' is ready.")
    print(f"View it here: https://app.instantly.ai/app/campaigns/{campaign_id}")

if __name__ == "__main__":
    main()
