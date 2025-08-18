from fastapi import FastAPI, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import requests, os, json, datetime, calendar, re

from core.operate_base import OperateInput
from core.registry import route

from core.registry import _REGISTRY  # add near other imports at the top if not present
from typing import Any, Dict
from orchestrators.generic_report_orchestrator import (
    learn_from_pdf,
    generate_from_learned,
)
import json, os
from core.logic_loader import load_all_logics, plan_from_query
from orchestrators.mis_orchestrator import NodeSpec, run_dag

# Import API routers
from app.api.execute import router as execute_router
from app.api.sse import router as sse_router
from app.api.webhooks import router as webhooks_router
from app.api.metrics import router as metrics_router

# Import modules for side-effects so they self-register in the registry
# (do not remove even if they look unused)
import operate.salary_operate  # noqa: F401
import operate.pnl_operate  # noqa: F401
import operate.withdrawals_operate  # noqa: F401

app = FastAPI()

# === CORS Middleware ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Include API Routers ===
app.include_router(execute_router)
app.include_router(sse_router)
app.include_router(webhooks_router)
app.include_router(metrics_router)

# === Constants ===
CREDENTIALS_FILE = "zoho_credentials.json"
ORG_IDS = {
    "formation": "60020606976",
    "active services": "60020679007",
    "shree sai": "60020561855",
    "shree sai engineering": "60020561855",
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
        "grant_type": "refresh_token",
    }
    res = requests.post(url, data=params)
    if res.status_code != 200:
        raise Exception(f"Failed to refresh Zoho access token: {res.text}")
    token_data = res.json()
    api_domain = creds.get("api_domain", "https://www.zohoapis.in")
    if api_domain and not api_domain.startswith("http"):
        api_domain = f"https://{api_domain}"
    return token_data["access_token"], api_domain


# === Health Check ===
@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/")
async def root():
    return {"message": "Zoho GPT Connector is running"}


# === Save Credentials ===
@app.post("/save_credentials")
async def save_credentials(request: Request, authorization: str = Header(None)):
    if authorization != f"Bearer {MCP_SECRET}":
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    data = await request.json()
    required = ["client_id", "client_secret", "refresh_token", "api_domain"]
    for field in required:
        if field not in data:
            return JSONResponse(
                status_code=400, content={"error": f"Missing field: {field}"}
            )
    with open(CREDENTIALS_FILE, "w") as f:
        json.dump(data, f)
    return {"status": "Credentials saved successfully"}


# === Debug: List registered ops ===
@app.get("/debug/ops")
async def debug_ops():
    return {"registered": len(_REGISTRY)}


# === MCP Manifest ===
@app.api_route("/mcp/manifest", methods=["GET", "POST", "HEAD"])
async def mcp_manifest():
    return {
        "name": "Zoho GPT Connector",
        "description": "Query your Zoho Books data using ChatGPT.",
        "version": "1.0",
        "tools": [{"type": "search"}, {"type": "fetch"}, {"type": "stream"}],
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
    # ensure logics are loaded for planning
    load_all_logics()
    plan = plan_from_query(query)
    last_query["plan"] = plan
    return {"results": [{"id": "result-001", "name": "Plan", "description": plan}]}


# === Fetch ===
@app.post("/mcp/fetch")
async def mcp_fetch(request: Request, authorization: str = Header(None)):
    if authorization != f"Bearer {MCP_SECRET}":
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    try:
        body = await request.json()
        # Direct logic execution override: accept {logic_id, payload}
        if isinstance(body, dict) and body.get("logic_id"):
            logic_id = body.get("logic_id")
            # Resolve by numeric ID prefix to avoid conflicts with title/name changes.
            # Expected file: logics/logic_###_*.py -> module path "logics.logic_###_...".
            # Accept either "L-014" or "014" etc.
            num = logic_id.replace("L-", "").replace("l-", "")
            num = num if len(num) == 3 else num.zfill(3)
            # Search for a module that starts with logic_{num}_*
            import pkgutil
            import logics as _logics_pkg

            candidate = None
            for _, modname, _ in pkgutil.iter_modules(_logics_pkg.__path__):
                if modname.startswith(f"logic_{num}_"):
                    candidate = f"logics.{modname}"
                    break
            if not candidate:
                return JSONResponse(
                    status_code=404,
                    content={"error": f"No logic module found for ID L-{num}"},
                )
            import importlib

            mod = importlib.import_module(candidate)
            payload = body.get("payload") or {}
            try:
                out = mod.handle(payload)
                # Return contract directly for smoke tests
                return out
            except Exception as e:
                return JSONResponse(status_code=500, content={"error": str(e)})

        query = last_query.get("text", "").lower()
        if not query:
            return {"error": "Missing query"}

        # Org selection by fuzzy match
        org_key = next((k for k in ORG_IDS if k in query), "formation")
        org_id = ORG_IDS[org_key]

        # Date parsing (simple month/year)
        month_map = {
            "january": "01",
            "february": "02",
            "march": "03",
            "april": "04",
            "may": "05",
            "june": "06",
            "july": "07",
            "august": "08",
            "september": "09",
            "october": "10",
            "november": "11",
            "december": "12",
        }
        # --- dynamic year detection ---
        year_match = re.search(r"\b(20\d{2})\b", query)
        year = year_match.group(1) if year_match else str(datetime.datetime.now().year)

        # two-digit year support (e.g., '24 -> 2024) with a simple cutoff
        if not year_match:
            short = re.search(r"\b(\d{2})\b", query)
            if short:
                yy = int(short.group(1))
                base = 2000 if yy < 70 else 1900
                year = str(base + yy)
        # --- end dynamic year detection ---
        month = next((m for m in month_map if m in query), None)
        if month:
            month_num = month_map[month]
            start_date = f"{year}-{month_num}-01"
            end_day = calendar.monthrange(int(year), int(month_num))[1]
            end_date = f"{year}-{month_num}-{end_day}"
        else:
            now = datetime.datetime.now()
            start_date = now.replace(day=1).strftime("%Y-%m-%d")
            last_day = calendar.monthrange(now.year, now.month)[1]
            end_date = now.replace(day=last_day).strftime("%Y-%m-%d")

        # Try to get real token; fallback to dry-run for local testing
        try:
            access_token, api_domain = get_access_token()
        except Exception:
            access_token, api_domain = ("dry-run", "https://www.zohoapis.in")
        headers = {"Authorization": f"Zoho-oauthtoken {access_token}"}

        plan = last_query.get("plan")
        op_in = OperateInput(
            org_id=org_id,
            start_date=start_date,
            end_date=end_date,
            headers=headers,
            api_domain=api_domain,
            query=query,
        )

        # Orchestrator plan
        if plan and plan.get("type") == "orchestrator" and plan.get("name") == "mis":
            from orchestrators.mis_orchestrator import run_mis

            out = run_mis(op_in, plan.get("sections", []))
            return {
                "records": [
                    {"id": "result-001", "content": out.content, "meta": out.meta}
                ]
            }

        # Logic plan: execute L-### handlers
        if plan and plan.get("type") == "logic" and plan.get("logic_ids"):
            from core.logic_loader import LOGIC_REGISTRY

            payload = {
                "org_id": org_id,
                "start_date": start_date,
                "end_date": end_date,
                "headers": headers,
                "api_domain": api_domain,
                "query": query,
            }
            results = {}
            for lid in plan.get("logic_ids", []):
                entry = LOGIC_REGISTRY.get(lid)
                if not entry:
                    results[lid] = {"error": "logic not found"}
                    continue
                handler, meta = entry
                try:
                    results[lid] = handler(payload)
                except Exception as e:
                    results[lid] = {"error": str(e)}
            return {
                "records": [
                    {
                        "id": "result-001",
                        "content": results,
                        "meta": {
                            "operator": "logic_runner",
                            "logic_ids": plan.get("logic_ids", []),
                        },
                    }
                ]
            }

        # Fallback: legacy keyword router (operate/*)
        op = route(query)
        if op is not None:
            out = op(op_in)
            return {
                "records": [
                    {"id": "result-001", "content": out.content, "meta": out.meta}
                ]
            }

        return {
            "records": [{"id": "result-001", "content": "No matching logic or plan."}]
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": {"type": "internal_error", "message": str(e)}},
        )


@app.post("/mcp/stream")
async def mcp_stream(request: Request, authorization: str = Header(None)):
    if authorization != f"Bearer {MCP_SECRET}":
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    try:
        body = await request.json()
        nodes = [NodeSpec(**n) for n in body.get("nodes", [])]
        edges = [tuple(e) for e in body.get("edges", [])]
        pl = body.get("payload", {})

        async def event_generator():
            queue: list[dict[str, Any]] = []

            def cb(evt: dict[str, Any]):
                queue.append(evt)

            results = run_dag(nodes, edges, pl, progress_cb=cb)
            for evt in queue:
                yield (json.dumps(evt) + "\n")
            yield (json.dumps({"stage": "complete"}) + "\n")
            yield (json.dumps({"results": list(results.keys())}) + "\n")

        return StreamingResponse(event_generator(), media_type="text/event-stream")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# === Reverse-Learning minimal endpoints ===
@app.post("/rl/learn")
async def rl_learn(payload: Dict[str, Any]):
    """
    Learn a PDF format and persist mapping to /docs/learned_formats/*.json
    """
    return learn_from_pdf(payload["pdf_path"], payload.get("name", "mis_fixture_v1"))


@app.post("/rl/generate")
async def rl_generate(payload: Dict[str, Any]):
    """
    Use a learned mapping to produce a contract-compliant output.
    payload: {"learned_path":"docs/learned_formats/mis_fixture_v1.json","source_fields":{...}, "period":"2025-06"}
    """
    with open(payload["learned_path"], "r", encoding="utf-8") as f:
        mapping = json.load(f).get("mapping", {})
    return generate_from_learned(payload, mapping)
