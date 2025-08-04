from flask import Flask, request, jsonify
from flask_cors import CORS
import os, json, requests
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ========== Configuration ==========
CREDENTIALS_FILE = "zoho_credentials.json"
ORG_IDS = {
    "formation": "60020606976",
    "shree sai engineering": "60018074998",
    "third company": "YOUR_THIRD_COMPANY_ID"
}

# ========== Helper Functions ==========
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

# ========== Basic Routes ==========
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

# ========== MCP Endpoints ==========
@app.route("/mcp/manifest", methods=["GET"])
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
    org_id = None
    matched_org = "Unknown"

    for name in ORG_IDS:
        if name in query:
            org_id = ORG_IDS[name]
            matched_org = name
            break

    return jsonify({
        "results": [{
            "id": "result-001",
            "name": f"Zoho Query: {query}",
            "description": f"Query for: {query} | Org: {matched_org} | ID: {org_id or 'Not Found'}"
        }]
    })

@app.route("/mcp/fetch", methods=["POST"])
def mcp_fetch():
    try:
        ids = request.json.get("ids", [])
        if not ids or ids[0] != "result-001":
            return jsonify({"error": "Invalid or missing ID"}), 400

        query = "salary of employees in formation for june 2025"
        access_token, api_domain = get_access_token()
        headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}
        org_id = ORG_IDS.get("formation")

        # ===================== EXPENSES =====================
        expense_url = f"{api_domain}/books/v3/expenses"
        exp_params = {
            "organization_id": org_id,
            "date_start": "2025-06-01",
            "date_end": "2025-06-30",
            "filter_by": "Category.All"
        }
        exp_res = requests.get(expense_url, headers=headers, params=exp_params).json()

        expenses = [
            {
                "source": "Expense",
                "employee": e.get("vendor_name"),
                "amount": e.get("total"),
                "date": e.get("date"),
                "description": e.get("description")
            }
            for e in exp_res.get("expenses", [])
            if "salary" in e.get("description", "").lower() or "salary" in e.get("category_name", "").lower()
        ]

        # ===================== VENDOR BILLS =====================
        bill_url = f"{api_domain}/books/v3/vendorbills"
        bill_params = {
            "organization_id": org_id,
            "date_start": "2025-06-01",
            "date_end": "2025-06-30"
        }
        bill_res = requests.get(bill_url, headers=headers, params=bill_params).json()

        vendor_bills = [
            {
                "source": "Vendor Bill",
                "employee": b.get("vendor_name"),
                "amount": b.get("total"),
                "date": b.get("date"),
                "description": b.get("line_items", [{}])[0].get("name")
            }
            for b in bill_res.get("bills", [])
            if "salary" in b.get("line_items", [{}])[0].get("name", "").lower()
        ]

        combined = expenses + vendor_bills
        combined = combined or [{"message": "No salary data found in June 2025 for Formation."}]

        return jsonify({
            "records": [{
                "id": "result-001",
                "title": "Salary Data - Formation - June 2025",
                "text": json.dumps(combined, indent=2),
                "url": "https://books.zoho.in",
                "metadata": {"source": "Zoho Books"}
            }]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
        @app.post("/mcp/fetch")
async def mcp_fetch(request: Request):
    # your implementation here
    return {...}

@app.post("/mcp/search")
async def mcp_search(request: Request):
    # your implementation here
    return {...}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
