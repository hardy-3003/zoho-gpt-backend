from fastapi import FastAPI, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import requests, os, json, datetime

app = FastAPI()

# === CORS Middleware ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Constants ===
CREDENTIALS_FILE = "zoho_credentials.json"
ORG_IDS = {
    "formation": "60020606976",
    "shree sai engineering": "60018074998",
    "active services": "60019742072"
}
MCP_SECRET = os.getenv("MCP_SECRET", "default-secret")

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
    res = requests.post(url, params=params)
    if res.status_code != 200:
        raise Exception("Failed to refresh Zoho access token")
    token_data = res.json()
    return token_data["access_token"], creds["api_domain"]

# === Health Check ===
@app.get("/health")
async def health_check():
    return {"status": "ok"}

# === Save Credentials ===
@app.post("/save_credentials")
async def save_credentials(request: Request):
    data = await request.json()
    required = ["client_id", "client_secret", "refresh_token", "api_domain"]
    for field in required:
        if field not in data:
            return JSONResponse(status_code=400, content={"error": f"Missing field: {field}"})
    with open(CREDENTIALS_FILE, "w") as f:
        json.dump(data, f)
    return {"status": "Credentials saved successfully"}

# === MCP Manifest ===
@app.api_route("/mcp/manifest", methods=["GET", "POST", "HEAD"])
async def mcp_manifest():
    return {
        "name": "Zoho GPT Connector",
        "description": "Query your Zoho Books data using ChatGPT.",
        "version": "1.0",
        "tools": [
            {"type": "search"},
            {"type": "fetch"}
        ]
    }

# === Search ===
last_query = {}

@app.post("/mcp/search")
async def mcp_search(request: Request, authorization: str = Header(None)):
    if authorization != f"Bearer {MCP_SECRET}":
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
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

# === Fetch ===
@app.post("/mcp/fetch")
async def mcp_fetch(request: Request, authorization: str = Header(None)):
    if authorization != f"Bearer {MCP_SECRET}":
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    try:
        query = last_query.get("text", "").lower()
        if not query:
            return {"error": "Missing query"}

        org_key = next((k for k in ORG_IDS if k in query), "formation")
        org_id = ORG_IDS[org_key]

        # Date Parsing
        month_map = {
            "january": "01", "february": "02", "march": "03", "april": "04",
            "may": "05", "june": "06", "july": "07", "august": "08",
            "september": "09", "october": "10", "november": "11", "december": "12"
        }
        year = "2025"
        month = next((m for m in month_map if m in query), None)
        if month:
            month_num = month_map[month]
            start_date = f"{year}-{month_num}-01"
            end_date = f"{year}-{month_num}-30"
        else:
            now = datetime.datetime.now()
            start_date = now.replace(day=1).strftime("%Y-%m-%d")
            end_date = now.replace(day=28).strftime("%Y-%m-%d")

        access_token, api_domain = get_access_token()
        headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}

        # Salary
        if "salary" in query or "wages" in query:
            expenses_url = f"{api_domain}/books/v3/expenses"
            bills_url = f"{api_domain}/books/v3/vendorbills"
            params = {
                "organization_id": org_id,
                "date_start": start_date,
                "date_end": end_date,
                "filter_by": "Category.All"
            }

            expenses = requests.get(expenses_url, headers=headers, params=params).json().get("expenses", [])
            bills = requests.get(bills_url, headers=headers, params=params).json().get("bills", [])
            salary_data = []

            for e in expenses:
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

            return {"records": [{"id": "result-001", "content": salary_data or "No salary data found."}]}

        # Profit & Loss
        if "p&l" in query or "profit and loss" in query or "income" in query:
            url = f"{api_domain}/books/v3/reports/ProfitAndLoss"
            params = {"organization_id": org_id, "start_date": start_date, "end_date": end_date}
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

        return {"records": [{"id": "result-001", "content": "Query received but no matching logic found yet."}]}

    except Exception as e:
        return {"error": str(e)}
