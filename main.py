from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import requests, os, json
from datetime import datetime

app = FastAPI()

# CORS for ChatGPT MCP
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Configuration ===
CREDENTIALS_FILE = "zoho_credentials.json"
ORG_IDS = {
    "formation": "60020606976",
    "shree sai engineering": "60018074998",
    "third company": "YOUR_THIRD_COMPANY_ID"
}

# === Helpers ===
def load_credentials():
    if not os.path.exists(CREDENTIALS_FILE):
        raise Exception("Missing zoho_credentials.json")
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

# === Save Credentials (optional helper) ===
@app.post("/save_credentials")
async def save_credentials(request: Request):
    data = await request.json()
    with open(CREDENTIALS_FILE, "w") as f:
        json.dump(data, f)
    return {"status": "Credentials saved"}

# === MCP manifest ===
@app.post("/mcp/manifest")
async def mcp_manifest():
    return {
        "name": "Zoho GPT Connector",
        "description": "Query your Zoho Books data using ChatGPT.",
        "version": "1.0",
        "tools": [{"type": "search"}, {"type": "fetch"}]
    }

# === MCP search ===
last_query = {}

@app.post("/mcp/search")
async def mcp_search(request: Request):
    body = await request.json()
    query = body.get("query", "").lower()
    last_query["text"] = query
    return {
        "results": [{
            "id": "result-001",
            "name": f"Zoho Query: {query}",
            "description": f"Query for: {query}"
        }]
    }

# === MCP fetch ===
@app.post("/mcp/fetch")
async def mcp_fetch(request: Request):
    try:
        query = last_query.get("text", "").lower()
        if not query:
            return {"error": "Missing query"}

        # Extract company/org
        org_key = next((k for k in ORG_IDS if k in query), "formation")
        org_id = ORG_IDS[org_key]

        # Extract date
        month_map = {
            "january": "01", "february": "02", "march": "03", "april": "04",
            "may": "05", "june": "06", "july": "07", "august": "08",
            "september": "09", "october": "10", "november": "11", "december": "12"
        }
        year = "2025"
        month = next((m for m in month_map if m in query), "06")
        month_num = month_map.get(month, "06")
        start_date = f"{year}-{month_num}-01"
        end_date = f"{year}-{month_num}-30"

        # Auth
        access_token, api_domain = get_access_token()
        headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}

        # ==== Salary Query ====
        if "salary" in query or "wages" in query:
            expenses_url = f"{api_domain}/books/v3/expenses"
            bills_url = f"{api_domain}/books/v3/vendorbills"
            params = {
                "organization_id": org_id,
                "date_start": start_date,
                "date_end": end_date,
                "filter_by": "Category.All"
            }

            exp = requests.get(expenses_url, headers=headers, params=params).json().get("expenses", [])
            bills = requests.get(bills_url, headers=headers, params=params).json().get("bills", [])
            salary_data = []

            for e in exp:
                if "salary" in e.get("description", "").lower() or "salary" in e.get("category_name", "").lower():
                    salary_data.append({
                        "source": "Expense",
                        "employee": e.get("vendor_name"),
                        "amount": e.get("total"),
                        "date": e.get("date"),
                        "desc": e.get("description")
                    })

            for b in bills:
                for line in b.get("line_items", []):
                    if "salary" in line.get("description", "").lower():
                        salary_data.append({
                            "source": "Vendor Bill",
                            "employee": b.get("vendor_name"),
                            "amount": line.get("item_total"),
                            "date": b.get("date"),
                            "desc": line.get("description")
                        })

            return {
                "records": [{
                    "id": "result-001",
                    "content": salary_data or "No salary data found."
                }]
            }

        # ==== P&L Query ====
        if "p&l" in query or "profit and loss" in query or "income" in query:
            url = f"{api_domain}/books/v3/reports/ProfitAndLoss"
            params = {
                "organization_id": org_id,
                "start_date": start_date,
                "end_date": end_date
            }
            report = requests.get(url, headers=headers, params=params).json()
            summary = report.get("report", {}).get("summary", {})
            return {
                "records": [{
                    "id": "result-001",
                    "content": {
                        "Revenue": summary.get("total_income", {}).get("value", 0),
                        "Expenses": summary.get("total_expense", {}).get("value", 0),
                        "Profit": summary.get("net_profit", {}).get("value", 0)
                    }
                }]
            }

        # Future logic will go here...

        return {
            "records": [{
                "id": "result-001",
                "content": "Query received but no logic found yet."
            }]
        }

    except Exception as e:
        return {"error": str(e)}
