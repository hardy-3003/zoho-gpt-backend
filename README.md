Zoho GPT Backend
=================

MCP-ready backend for the Zoho GPT accounting assistant. This repository contains:

- Deterministic logic modules under `logics/` (231 total including `logic_231_ratio_impact_advisor.py`).
- Orchestrators under `orchestrators/`.
- Observability utilities under `obs/` (structured logs and in-process metrics).
- FastAPI surfaces under `app/api/` and a CLI under `cli/`.

Install (editable):

```bash
pip install -e .[dev]
```


