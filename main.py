from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

# Load env variables
ZOHO_REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")
ZOHO_CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
ZOHO_CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")

# Health check
@app.route("/health")
def health():
    return {"status": "ok"}

# Endpoint to fetch invoices
@app.route("/get_invoices", methods=["GET"])
def get_invoices():
    org_id = request.args.get("organization_id")
    month = request.args.get("month")  # Format: YYYY-MM

    if not org_id or not month:
        return jsonify({"error": "Missing parameters"}), 400

    # Refresh access token
    auth_url = "https://accounts.zoho.in/oauth/v2/token"
    params = {
        "refresh_token": ZOHO_REFRESH_TOKEN,
        "client_id": ZOHO_CLIENT_ID,
        "client_secret": ZOHO_CLIENT_SECRET,
        "grant_type": "refresh_token"
    }
    auth_response = requests.post(auth_url, params=params)
    access_token = auth_response.json().get("access_token")

    # Fetch invoices
    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
    api_url = "https://www.zohoapis.in/books/v3/invoices"
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

# MIS Generator (placeholder)
@app.route("/generate_mis", methods=["GET"])
def generate_mis():
    org_name = request.args.get("org_name")
    month = request.args.get("month")
    year = request.args.get("year")

    if not org_name or not month or not year:
        return jsonify({"error": "Missing required query parameters"}), 400

    # Just a test response – replace with real logic
    return jsonify({
        "org": org_name,
        "month": month,
        "year": year,
        "status": "MIS generated (mock)"
    })

# MCP manifest
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

# MCP search endpoint
@app.route("/mcp/search", methods=["POST"])
def mcp_search():
    query = request.json.get("query", "")
    return jsonify({
        "results": [
            {
                "id": "result-001",
                "name": f"Zoho Query: {query}",
                "description": f"Query for: {query}"
            }
        ]
    })

# MCP fetch endpoint
@app.route("/mcp/fetch", methods=["POST"])
def mcp_fetch():
    ids = request.json.get("ids", [])
    return jsonify({
        "records": [
            {
                "id": id_,
                "content": f"Detailed Zoho data for {id_}"
            } for id_ in ids
        ]
    })

# Start app
if __name__ == "__main__":
    app.run(debug=True)
