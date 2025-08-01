import os
import requests

def fetch_invoices(organization_id, start_date, end_date):
    headers = {
        "Authorization": f"Zoho-oauthtoken {os.getenv('ZOHO_ACCESS_TOKEN')}"
    }

    url = f"https://books.zoho.in/api/v3/invoices"
    params = {
        "organization_id": organization_id,
        "date_start": start_date,
        "date_end": end_date,
        "status": "all"
    }

    response = requests.get(url, headers=headers, params=params)
    return response.json()
