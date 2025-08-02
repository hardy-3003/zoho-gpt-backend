from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
import requests
from datetime import datetime

app = Flask(__name__)
CORS(app)

CREDENTIALS_FILE = "zoho_credentials.json"
ORG_IDS = {
    "formation": "60020606976",
    "shree sai engineering": "60020561855",
    "active services": "60020679007"
}

# -------------------- Utility Functions --------------------
def load_credentials():
    if not os.path.exists(CREDENTIALS_FILE):
        raise Exception("Credentials not found. Please save them using /save_credentials")
    with open(CREDENTIALS_FILE) as f:
        return json.load(f)

def get_access_token():
    creds = load_credentials()
    token_url = "https://accounts.zoho.in/oauth/v2/token"
    params = {
        "refresh_token": creds["refresh_token"],
        "client_id": creds["client_id"],
        "client_secret": creds["client_secret"],
        "grant_type": "refresh_token"
    }
    response = requests.post(token_url, params=params)
    return response.json().get("access_token")

# -------------------- Health --------------------
@app.route("/health")
def health():
    return {"status": "ok"}

# -------------------- Save Credentials --------------------
@app.route("/save_credentials", methods=["POST"])
def save_credentials():
    data = request.get_json()
    required_fields = ["client_id", "client_secret", "refresh_token", "api_domain"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400
    with open(CREDENTIALS_FILE, "w") as f:
        json.dump(data, f)
    return jsonify({"status": "Credentials saved successfully"})

# -------------------- MCP --------------------
@app.route("/mcp/manifest", methods=["GET"])
def manifest():
    return jsonify({
        "name": "Zoho GPT Connector",
        "description": "Query your Zoho Books data using ChatGPT.",
        "version": "1.0",
        "tools": [{"type": "search"}, {"type": "fetch"}]
    })

search_memory = {}  # Temporary in-memory search context

@app.route("/mcp/search", methods=["POST"])
def mcp_search():
    query = request.json.get("query", "").lower()
    matched_org = next((org for org in ORG_IDS if org in query), None)
    if not matched_org:
        return jsonify({"error": "No valid organization found in query."}), 400
    result_id = "result-001"
    search_memory[result_id] = {
        "query": query,
        "org_id": ORG_IDS[matched_org],
        "org_name": matched_org
    }
    return jsonify({
        "results": [{
            "id": result_id,
            "name": f"Zoho Query: {query}",
            "description": f"Query for: {query} | Org: {matched_org} | ID: {ORG_IDS[matched_org]}"
        }]
    })

@app.route("/mcp/fetch", methods=["POST"])
def mcp_fetch():
    ids = request.json.get("ids", [])
    if not ids:
        return jsonify({"error": "No result ID provided."}), 400
    result_id = ids[0]
    if result_id not in search_memory:
        return jsonify({"error": "Unknown result ID."}), 400

    context = search_memory[result_id]
    query = context["query"]
    org_id = context["org_id"]
    access_token = get_access_token()

    headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}

    # Extract date/month if mentioned
    if "june" in query and "2025" in query:
        date_start = "2025-06-01"
        date_end = "2025-06-30"
    else:
        today = datetime.today().strftime("%Y-%m-%d")
        date_start = date_end = today

    # Salary Fetch
    if "salary" in query:
        url = f"https://www.zohoapis.in/books/v3/journals?organization_id={org_id}&date_start={date_start}&date_end={date_end}&filter_by=JournalType.Salary"
        response = requests.get(url, headers=headers)
        data = response.json()
        return jsonify({
            "records": [{
                "id": result_id,
                "content": data
            }]
        })

    return jsonify({"records": [{"id": result_id, "content": "No handler for this query yet."}]}), 200

# -------------------- Run --------------------
if __name__ == "__main__":
    app.run(debug=True)
