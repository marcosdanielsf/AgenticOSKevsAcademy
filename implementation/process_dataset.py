import os
import argparse
from dotenv import load_dotenv
from apify_client import ApifyClient
import gspread
from google.oauth2.service_account import Credentials

# Load environment variables
load_dotenv()
APIFY_API_KEY = os.getenv('APIFY_API_KEY')
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
SERVICE_ACCOUNT_FILE = 'service_account.json'

if not APIFY_API_KEY or not SPREADSHEET_ID:
    raise ValueError("Missing API Keys in .env")

apify_client = ApifyClient(APIFY_API_KEY)

def get_sheet(sheet_name):
    scopes = ['https://www.googleapis.com/auth/spreadsheets']
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID).worksheet(sheet_name)

def process_dataset(dataset_id):
    print(f"--- Processing Dataset: {dataset_id} ---")
    
    # Map results by Original Start URL
    contact_map = {}
    
    # Iterate through the dataset
    # Note: We use clean=True to hide hidden fields if needed, but here we need originalStartUrl
    for item in apify_client.dataset(dataset_id).iterate_items():
        # Use originalStartUrl to group pages back to the business
        # Fallback to 'url' if originalStartUrl is missing (though it shouldn't be for the start page)
        start_url = item.get("originalStartUrl") or item.get("url")
        
        if not start_url:
            continue
            
        if start_url not in contact_map:
            contact_map[start_url] = {
                "emails": set(),
                "linkedin": set(),
                "twitter": set(),
                "facebook": set(),
                "instagram": set(),
                "youtube": set(),
                "tiktok": set()
            }
            
        # Aggregate Emails
        for email in item.get("emails", []):
            contact_map[start_url]["emails"].add(email)
            
        # Aggregate Socials (using plural keys from dataset)
        for link in item.get("linkedins", []): contact_map[start_url]["linkedin"].add(link)
        for link in item.get("twitters", []): contact_map[start_url]["twitter"].add(link)
        for link in item.get("facebooks", []): contact_map[start_url]["facebook"].add(link)
        for link in item.get("instagrams", []): contact_map[start_url]["instagram"].add(link)
        for link in item.get("youtubes", []): contact_map[start_url]["youtube"].add(link)
        for link in item.get("tiktoks", []): contact_map[start_url]["tiktok"].add(link)

    # Convert sets to strings
    final_map = {}
    for url, data in contact_map.items():
        final_map[url] = {
            "emails": "\n".join(sorted(list(data["emails"]))),
            "linkedin": "\n".join(sorted(list(data["linkedin"]))),
            "twitter": "\n".join(sorted(list(data["twitter"]))),
            "facebook": "\n".join(sorted(list(data["facebook"]))),
            "instagram": "\n".join(sorted(list(data["instagram"]))),
            "youtube": "\n".join(sorted(list(data["youtube"]))),
            "tiktok": "\n".join(sorted(list(data["tiktok"])))
        }
    
    print(f"Processed {len(final_map)} unique businesses from dataset.")
    return final_map

def update_sheet(contact_map, sheet_name):
    print(f"--- Updating Google Sheet: {sheet_name} ---")
    sheet = get_sheet(sheet_name)
    
    # Update Headers
    headers = ["Business Name", "Address", "Website", "Phone", "Rating", "Emails", "LinkedIn", "Twitter", "Facebook", "Instagram", "YouTube", "TikTok"]
    sheet.update(range_name="A1", values=[headers])
    
    # Get all data (list of lists)
    all_values = sheet.get_all_values()
    
    # Find the index of the "Website" column (usually index 2, but let's be safe if we just overwrote headers)
    try:
        website_idx = headers.index("Website")
    except ValueError:
        website_idx = 2 # Default fallback

    updates = []
    # Skip header row (index 0), start from row 2 (index 1 in 0-based list, but row 2 in sheet)
    for i, row in enumerate(all_values[1:], start=2):
        if len(row) <= website_idx:
            continue
            
        website = row[website_idx]
        if not website:
            continue
            
        # Direct lookup using the website URL from the sheet
        info = contact_map.get(website)
        
        # If no direct match, try stripping trailing slash
        if not info:
             info = contact_map.get(website.rstrip('/'))
        if not info:
             info = contact_map.get(website + '/')

        if info:
            row_num = i # i is already the 1-based row number because we started enumerate at 2
            
            # Update columns F, G, H, I, J, K, L
            updates.append({"range": f"F{row_num}", "values": [[info['emails']]]})
            updates.append({"range": f"G{row_num}", "values": [[info['linkedin']]]})
            updates.append({"range": f"H{row_num}", "values": [[info['twitter']]]})
            updates.append({"range": f"I{row_num}", "values": [[info['facebook']]]})
            updates.append({"range": f"J{row_num}", "values": [[info['instagram']]]})
            updates.append({"range": f"K{row_num}", "values": [[info['youtube']]]})
            updates.append({"range": f"L{row_num}", "values": [[info['tiktok']]]})
            
    if updates:
        print(f"Pushing {len(updates)} cell updates...")
        sheet.batch_update(updates)
        print("Success.")
    else:
        print("No matching rows found to update.")

def main():
    parser = argparse.ArgumentParser(description="Process Apify Dataset to Sheet")
    parser.add_argument("--dataset", required=True, help="Apify Dataset ID")
    parser.add_argument("--sheet", required=True, help="Google Sheet Name")
    
    args = parser.parse_args()
    
    try:
        contact_map = process_dataset(args.dataset)
        update_sheet(contact_map, args.sheet)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
