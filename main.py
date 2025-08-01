from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

ZOHO_REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")
ZOHO_CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
ZOHO_CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
ZOHO_API_DOMAIN = os.getenv("ZOHO_API_DOMAIN")

def get_access_token():
    url = f"https://accounts.zoho.in/oauth/v2/token"
    params = {
        "refresh_token": ZOHO_REFRESH_TOKEN,
        "client_id": ZOHO_CLIENT_ID,
        "client_secret": ZOHO_CLIENT_SECRET,
        "grant_type": "refresh_token"
    }
    response = requests.post(url, params=params)
    return response.json().get("access_token")

@app.route("/")
def home():
    return "Zoho GPT Backend is running!"

@app.route("/invoices")
def get_invoices():
    org_id = request.args.get("org_id")
    date_start = request.args.get("date_start")
    date_end = request.args.get("date_end")

    token = get_access_token()
    if not token:
        return jsonify({"error": "Unable to get access token"}), 500

    headers = {
        "Authorization": f"Zoho-oauthtoken {token}"
    }

    params = {
        "organization_id": org_id,
        "date_start": date_start,
        "date_end": date_end,
        "per_page": 200
    }

    api_url = f"{ZOHO_API_DOMAIN}/books/v3/invoices"
    response = requests.get(api_url, headers=headers, params=params)
    return jsonify(response.json())

if __name__ == "__main__":
    app.run(debug=True, port=8080)
    @app.route("/health")
def health():
    return {"status": "ok"}
