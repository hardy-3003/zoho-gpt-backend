from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json

app = Flask(__name__)
CORS(app)

CREDENTIALS_FILE = "zoho_credentials.json"

@app.route("/health")
def health():
    return {"status": "ok"}

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

def load_credentials():
    if not os.path.exists(CREDENTIALS_FILE):
        raise Exception("Credentials not found. Please save them using /save_credentials")
    with open(CREDENTIALS_FILE) as f:
        return json.load(f)

# MCP Manifest
@app.route("/mcp/manifest", methods=["GET"])
def manifest():
    return jsonify({
        "name": "Zoho GPT Connector",
        "description": "Query your Zoho Books data using ChatGPT.",
        "version": "1.0",
        "tools": [{"type": "search"}, {"type": "fetch"}]
    })

# MCP Search (Mocked)
@app.route("/mcp/search", methods=["POST"])
def mcp_search():
    query = request.json.get("query", "")
    return jsonify({
        "results": [{
            "id": "result-001",
            "name": f"Zoho Query: {query}",
            "description": f"Query for: {query}"
        }]
    })

# MCP Fetch (Mocked)
@app.route("/mcp/fetch", methods=["POST"])
def mcp_fetch():
    ids = request.json.get("ids", [])
    return jsonify({
        "records": [{
            "id": id_,
            "content": f"Detailed Zoho data for {id_}"
        } for id_ in ids]
    })

if __name__ == "__main__":
    app.run(debug=True)
