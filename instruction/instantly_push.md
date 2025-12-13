# Instantly.ai Integration

This document covers the Instantly.ai API integration for pushing leads from Google Sheets to Instantly campaigns.

## API Configuration

- **Base URL:** `https://api.instantly.ai/api/v2`
- **Authentication:** Bearer Token in Authorization header
- **API Key Location:** `.env` file as `INSTANTLY_API_KEY`

## Key Endpoints

### 1. Add Lead to Campaign
- **Endpoint:** `POST /api/v2/leads`
- **Method:** POST
- **Headers:**
  - `Authorization: Bearer <API_KEY>`
  - `Content-Type: application/json`
- **Body (Single Lead):**
```json
{
  "campaign": "uuid-of-campaign",
  "email": "lead@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "company_name": "Acme Corp",
  "website": "https://acme.com",
  "phone": "(555) 123-4567",
  "skip_if_in_campaign": true,
  "skip_if_in_workspace": false,
  "custom_variables": {
    "City": "Austin",
    "Source": "Agentic OS"
  }
}
```
- **CRITICAL:** Use `"campaign"` NOT `"campaign_id"`. The API documentation is misleading.
- **Important:** Bulk upload via `leads: [...]` array does NOT work. Must send leads one-by-one.

### 2. List Leads
- **Endpoint:** `POST /api/v2/leads/list`
- **Method:** POST (not GET)
- **Body:**
```json
{
  "campaign_id": "uuid-of-campaign",
  "limit": 50
}
```
- **Response:** Returns `items` array with leads and `next_starting_after` for pagination.

### 3. List Campaigns
- **Endpoint:** `GET /api/v2/campaigns`
- **Response:** Returns `items` array with campaign objects containing `id`, `name`, `status`.

### 5. Create Campaign
- **Endpoint:** `POST /api/v2/campaigns`
- **Body:**
```json
{
  "name": "Campaign Name",
  "email_list": ["sender@example.com"],
  "campaign_schedule": { ... }
}
```

### 6. Update Campaign Sequence
- **Endpoint:** `PATCH /api/v2/campaigns/{campaign_id}`
- **Body:**
```json
{
  "sequences": [
    {
      "steps": [
        {
          "type": "email",
          "delay": 0,
          "variants": [
            {
              "subject": "Subject Line",
              "body": "<p>Email Body</p>",
              "v_disabled": false
            }
          ]
        }
      ]
    }
  ]
}
```

## Workflow Usage

### Create Campaign & Add Sequence
```bash
./venv/bin/python3 implementation/instantly_create_campaign.py \
  --name "Dentists Florida" \
  --sheet "dentists florida"
```

### Push Leads from Google Sheet to Instantly
```bash
./venv/bin/python3 implementation/instantly_push.py \
  --sheet "mens health NY" \
  --campaign_id "adb1f3f6-0035-4edd-9252-1073138787df"
```

### Arguments
- `--sheet`: Name of the Google Sheet tab to read from.
- `--campaign_id`: UUID of the Instantly Campaign.

## Data Mapping

| Google Sheet Column | Instantly Field |
|---------------------|-----------------|
| Emails (first line) | email |
| Business Name | company_name |
| Website | website |
| Phone | phone |
| Address | custom_variables.Address |
| (Extracted) | custom_variables.City |
| LinkedIn | custom_variables.LinkedIn |
| (Static) | custom_variables.Source = "Agentic OS Scraper" |

## Email Template Variables

In your Instantly campaign sequence, use these variables:
- `{{email}}` - Lead's email
- `{{firstName}}` - First name (may be empty)
- `{{companyName}}` - Company name
- `{{website}}` - Website URL
- `{{phone}}` - Phone number
- `{{City}}` - Custom variable for city
- `{{LinkedIn}}` - Custom variable for LinkedIn URL

## Known Limitations

1. **Bulk Upload Broken:** The `leads: []` array format returns "Email is required" error. Must upload one lead at a time.
2. **Lead Status:** Leads are added to workspace, may need manual association with campaign in UI.
3. **City Extraction:** Currently uses simple heuristic (second-to-last comma-separated part). May be inaccurate for some addresses.
4. **Invalid Emails:** HTML-encoded emails (e.g., `&#105;&#110;&#102;&#111;`) will fail validation.

## Campaign Information

### Current Campaigns
- **Doctor Clinic Campaign 1**
  - ID: `adb1f3f6-0035-4edd-9252-1073138787df`
  - Used for: Mens Health Clinics outreach

### Connected Email Accounts
1. kevin@kevscales.com (Status: 2)
2. adrian@provazenpathdyno.org (Status: 1)
3. gabriel@provazenpathdyno.org (Status: 1)
4. tyler@provazenpathdyno.org (Status: 1)
5. jason@provazenpathdyno.org (Status: 1)
6. lawrence@provazenpathdyno.org (Status: 1)

