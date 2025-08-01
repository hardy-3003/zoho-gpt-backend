from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

ZOHO_REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")
ZOHO_CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
ZOHO_CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")

@app.route("/health")
def health():
    return {"status": "ok"}

@app.route("/get_invoices", methods=["GET"])
def get_invoices():
    org_id = request.args.get("organization_id")
    month = request.args.get("month")  # Format: YYYY-MM

    # Step 1: Get new access token using refresh token
    auth_url = "https://accounts.zoho.in/oauth/v2/token"
    params = {
        "refresh_token": ZOHO_REFRESH_TOKEN,
        "client_id": ZOHO_CLIENT_ID,
        "client_secret": ZOHO_CLIENT_SECRET,
        "grant_type": "refresh_token"
    }
    auth_response = requests.post(auth_url, params=params)
    access_token = auth_response.json().get("access_token")

    # Step 2: Fetch invoices from Zoho Books
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}"
    }
    api_url = f"https://www.zohoapis.in/books/v3/invoices"
    params = {
        "organization_id": org_id,
        "date_start": f"{month}-01",
        "date_end": f"{month}-30",
        "status": "All",
        "sort_column": "date",
        "sort_order": "A"
    }

    response = requests.get(api_url, headers=headers, params=params)
    return jsonify(response.json())

if __name__ == "__main__":
    app.run()
