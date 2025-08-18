import os
import requests


def fetch_invoices(api_domain, access_token, organization_id, start_date, end_date):
    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}

    url = f"{api_domain}/books/v3/invoices"
    params = {
        "organization_id": organization_id,
        "date_start": start_date,
        "date_end": end_date,
        "status": "all",
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch invoices: {response.text}")
    return response.json()
