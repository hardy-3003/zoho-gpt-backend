from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

# === HEALTH CHECK ===
@app.route("/health")
def health():
    return {"status": "ok"}

# === MCP MANIFEST ===
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

# === MCP SEARCH ===
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

# === MCP FETCH ===
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

if __name__ == "__main__":
    app.run()
