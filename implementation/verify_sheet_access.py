import gspread
from google.oauth2.service_account import Credentials

# Configuration
SERVICE_ACCOUNT_FILE = 'service_account.json'
SPREADSHEET_ID = '1UyR1jnEDSeHRCslIcA5YF3M5oNnR6LBi3sgfpcekaIE'

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def verify_access():
    try:
        print("Authenticating...")
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        client = gspread.authorize(creds)

        print(f"Opening spreadsheet ID: {SPREADSHEET_ID}...")
        sh = client.open_by_key(SPREADSHEET_ID)
        
        print(f"Successfully opened: '{sh.title}'")
        
        # Try writing a test value
        worksheet = sh.sheet1
        print("Attempting to write test value...")
        worksheet.update_acell('A1', 'Agentic OS Connection Verified')
        worksheet.update_acell('A2', 'Write Access Confirmed')
        worksheet.update_acell('B1', 'Test Column')
        worksheet.update_acell('B2', 'Hello from Agentic OS!')
        print("Successfully wrote to cells A1, A2, B1, B2.")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    verify_access()
