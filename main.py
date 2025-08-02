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
from flask import request, jsonify
from zoho_api import fetch_invoices

@app.route("/generate_mis", methods=["GET"])
def generate_mis():
    org_name = request.args.get("org_name")
    month = request.args.get("month")
    year = request.args.get("year")

    if not org_name or not month or not year:
        return jsonify({"error": "Missing required query parameters"}), 400

    try:
        result = generate_mis_report(org_name, month, year)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

from flask import Flask, jsonify, request

app = Flask(__name__)

# MCP Manifest Endpoint
@app.route("/mcp/manifest", methods=["GET"])
def manifest():
    return jsonify({
        "name": "Zoho GPT Connector",
        "description": "Query your Zoho Books data using ChatGPT.",
        "version": "1.0",
        "tools": [
            {"type": "search"},
            {"type": "fetch"}
        ]
    })

# MCP Search Endpoint
@app.route("/mcp/search", methods=["POST"])
def mcp_search():
    query = request.json.get("query", "")
    return jsonify({
        "results": [
            {
                "id": "test-id-001",
                "name": f"Dummy Result for '{query}'",
                "description": "This is a test result. Replace this with live search logic."
            }
        ]
    })

# MCP Fetch Endpoint
@app.route("/mcp/fetch", methods=["POST"])
def mcp_fetch():
    ids = request.json.get("ids", [])
    return jsonify([
        {
            "id": i,
            "content": f"This is mocked content for ID: {i}"
        } for i in ids
    ])

if __name__ == '__main__':
    app.run(debug=True)
