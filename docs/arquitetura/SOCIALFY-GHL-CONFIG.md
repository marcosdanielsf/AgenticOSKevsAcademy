# Socialfy - Configuração GoHighLevel White Label

## Domínio White Label

| Item | Valor |
|------|-------|
| **Domínio** | `app.socialfy.me` |
| **URL Base** | `https://app.socialfy.me` |
| **Location ID** | `sNwLyynZWP6jEtBy1ubf` |

> **IMPORTANTE:** Sempre usar `app.socialfy.me` em vez de `app.gohighlevel.com` para manter o branding Socialfy.

---

## URLs do Dashboard

### Contatos
```
https://app.socialfy.me/v2/location/sNwLyynZWP6jEtBy1ubf/contacts/smart_list/All
```

### Dashboard Principal
```
https://app.socialfy.me/v2/location/sNwLyynZWP6jEtBy1ubf/dashboard
```

### Oportunidades (Pipeline)
```
https://app.socialfy.me/v2/location/sNwLyynZWP6jEtBy1ubf/opportunities
```

### Automações/Workflows
```
https://app.socialfy.me/v2/location/sNwLyynZWP6jEtBy1ubf/automation
```

### Conversas
```
https://app.socialfy.me/v2/location/sNwLyynZWP6jEtBy1ubf/conversations
```

### Calendário
```
https://app.socialfy.me/v2/location/sNwLyynZWP6jEtBy1ubf/calendars
```

### Configurações
```
https://app.socialfy.me/v2/location/sNwLyynZWP6jEtBy1ubf/settings
```

---

## API Configuration

```bash
# Location ID
GHL_LOCATION_ID="sNwLyynZWP6jEtBy1ubf"

# API Base URL (não muda com white label)
GHL_API_URL="https://services.leadconnectorhq.com"

# API Version
GHL_API_VERSION="2021-07-28"
```

---

## Scripts de Sincronização

### Sincronizar Leads para GHL
```bash
python ~/Projects/scripts/instagram/sync-ghl.py --limit 50
```

### Scraper de Instagram
```bash
python ~/Projects/scripts/instagram/scraper-leads.py --file perfis.txt --vertical medico
```

---

## Leads Sincronizados

Para ver leads sincronizados no Supabase:
```sql
SELECT name, instagram_handle, ghl_contact_id
FROM socialfy_leads
WHERE ghl_contact_id IS NOT NULL;
```

---

*Última atualização: Janeiro 2026*
