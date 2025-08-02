from flask import Flask, request, jsonify
from flask_cors import CORS
import os, json, requests
from datetime import datetime

app = Flask(__name__)
CORS(app)

CREDENTIALS_FILE = "zoho_credentials.json"
ORG_IDS = {
    "formation": "60020606976",
    "shree sai engineering": "60018074998",
    "third company": "YOUR_THIRD_COMPANY_ID"
}

# ========== AUTH HELPERS ==========
def load_credentials():
    if not os.path.exists(CREDENTIALS_FILE):
        raise Exception("Credentials not found. Please save them using /save_credentials")
    with open(CREDENTIALS_FILE) as f:
        return json.load(f)

def get_access_token():
    creds = load_credentials()
    url = "https://accounts.zoho.in/oauth/v2/token"
    params = {
        "refresh_token": creds["refresh_token"],
        "client_id": creds["client_id"],
        "client_secret": creds["client_secret"],
        "grant_type": "refresh_token"
    }
    res = requests.post(url, params=params).json()
    return res["access_token"], creds["api_domain"]

# ========== BASIC ROUTES ==========
@app.route("/health")
def health():
    return {"status": "ok"}

@app.route("/save_credentials", methods=["POST"])
def save_credentials():
    data = request.get_json()
    required = ["client_id", "client_secret", "refresh_token", "api_domain"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400
    with open(CREDENTIALS_FILE, "w") as f:
        json.dump(data, f)
    return jsonify({"status": "Credentials saved successfully"})

# ========== MCP ==========
@app.route("/mcp/manifest")
def manifest():
    return jsonify({
        "name": "Zoho GPT Connector",
        "description": "Query your Zoho Books data using ChatGPT.",
        "version": "1.0",
        "tools": [{"type": "search"}, {"type": "fetch"}]
    })

@app.route("/mcp/search", methods=["POST"])
def mcp_search():
    query = request.json.get("query", "").lower()
    org_name = "formation"
    for name in ORG_IDS:
        if name in query:
            org_name = name
            break
    return jsonify({
        "results": [{
            "id": "result-001",
            "name": f"Zoho Query: {query}",
            "description": f"Query for: {query} | Org: {org_name} | ID: {ORG_IDS.get(org_name)}"
        }]
    })

@app.route("/mcp/fetch", methods=["POST"])
def mcp_fetch():
    try:
        access_token, api_domain = get_access_token()
        ids = request.json.get("ids", [])
        if not ids:
            return jsonify({"error": "Missing query ID"}), 400

        query = "salary of employees in formation for june 2025"  # Hardcoded for now
        org_id = ORG_IDS["formation"]
        headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}

        # === Logic 1: Salary
        if "salary" in query:
            url = f"{api_domain}/books/v3/expenses"
            params = {
                "organization_id": org_id,
                "date_start": "2025-06-01",
                "date_end": "2025-06-30",
                "filter_by": "Category.All"
            }
            res = requests.get(url, headers=headers, params=params).json()
            salary_exp = [
                {
                    "employee": e.get("vendor_name"),
                    "amount": e.get("total"),
                    "date": e.get("date"),
                    "description": e.get("description")
                }
                for e in res.get("expenses", [])
                if "salary" in e.get("description", "").lower()
                or "salary" in e.get("category_name", "").lower()
            ]
            return jsonify({"records": [{
                "id": "result-001",
                "content": salary_exp or "No salary data found."
            }]})

        # === Logic 2: Partner Withdrawals
        elif "partner withdrawal" in query or "withdrawals" in query:
            url = f"{api_domain}/books/v3/journals"
            params = {
                "organization_id": org_id,
                "date_start": "2025-04-01",
                "date_end": "2025-07-31"
            }
            res = requests.get(url, headers=headers, params=params).json()
            withdrawals = [
                {
                    "partner": j.get("reference_number"),
                    "amount": j.get("amount"),
                    "date": j.get("date"),
                    "description": j.get("description")
                }
                for j in res.get("journals", [])
                if "withdrawal" in j.get("description", "").lower()
            ]
            return jsonify({"records": [{
                "id": "result-001",
                "content": withdrawals or "No partner withdrawals found."
            }]})

        # === Logic 3: Vendor Outstanding (basic)
        elif "vendor outstanding" in query:
            url = f"{api_domain}/books/v3/purchases"
            params = {
                "organization_id": org_id,
                "status": "open"
            }
            res = requests.get(url, headers=headers, params=params).json()
            outstanding = [
                {
                    "vendor": p.get("vendor_name"),
                    "amount": p.get("balance"),
                    "invoice": p.get("purchaseorder_number")
                }
                for p in res.get("purchaseorders", [])
            ]
            return jsonify({"records": [{
                "id": "result-001",
                "content": outstanding or "No vendor outstanding found."
            }]})

        # === Logic 4: Monthly P&L Placeholder
        elif "profit" in query or "p&l" in query:
            return jsonify({"records": [{
                "id": "result-001",
                "content": "Profit and Loss logic is being added next..."
            }]})

        # === Default Fallback
        else:
            return jsonify({"records": [{
                "id": "result-001",
                "content": f"No matching logic found for query: {query}"
            }]})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
