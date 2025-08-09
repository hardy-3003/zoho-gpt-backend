# SOW + Protocol Alignment Plan (Living)

Owner: Agent • Branch: `feature/sow-protocol-alignment` • Tag: `pre_sow_protocol_alignment`

## Rule Books (single source of truth)
- `MASTER_SCOPE_OF_WORK.md` v2025-08-08
- `AGENT_EDIT_PROTOCOL.md` (L4 — Autonomous, Closed-Loop Evolution)

## Mandatory Requirements Extract (concise)
- Architecture folders: `logics/`, `orchestrators/`, `helpers/`, `analyzers/`, `tests/`, `docs/`, `prompts/`, `config/regulations/`.
- Logic Module Contract: every `logics/logic_###_*.py` must expose `LOGIC_META` and `handle(payload)` returning `{result, provenance, confidence, alerts, meta}` and include: input validation (via `helpers/schema_registry.py`), deterministic compute, `rules_engine` validations, `history_store` writes, `learning_hooks` usage, and internal strategy registry + provenance.
- Orchestration: auto-discovery and 2→∞ logic composition; tolerant to partial failures.
- MCP endpoints: `/mcp/manifest`, `/mcp/search` (NL→plan), `/mcp/fetch` (exec plan), optional `/mcp/stream` for SSE.
- Security: Auth on sensitive routes (`/mcp/*`, `/save_credentials`, `/generate_mis`), redaction, rate limits, typed errors.
- Tests: unit per logic (≥3 positive + 1 negative), orchestrator integration, Zoho contract tests, perf guards.
- Dynamic categories: Regulation reads `config/regulations/*.json` with effective-date versioning; Patterns leverage `history_store` + `analyzers`; Growth and Behavior expand safely with CHANGELOG entries and learned formats (`docs/learned_formats/`).

## Initial Gap Snapshot
- Missing dirs: `docs/`, `docs/CHANGELOG.md`, `docs/learned_formats/`, `prompts/`, `config/regulations/`.
- MCP manifest file exists as `mcp_manifest.json`, but no `/mcp/` folder. Endpoint behavior present in `main.py` (OK) but needs typed errors and auth confirmed. `save_credentials` already gated by `MCP_SECRET` (OK).
- `helpers/schema_registry.py` minimal; needs per-logic schemas and registration.
- Many logic files exist (1–200 present). Need contract conformance pass and annotations where required.
- Tests: only `tests/test_manifest.py`. Need unit test suites per logic and integration tests.

## Execution Plan by Phases
1. Safety
   - Branch + tag created. Use `_graveyard/` for any removals and append to `docs/CHANGELOG.md`.
2. Ingest + Plan
   - This plan.md committed; will keep updated per batch.
3. Repo Scan + Gap Report
   - Create missing dirs/files; generate `gap_report.md` listing non-compliances (structure, schemas, contracts, endpoints, tests).
4. Enforce Logic Contract (Batching 20 files/run)
   - Ensure each logic returns required keys, has provenance list, calls history/learning/validation hooks, and defines `LOGIC_META` with tags.
   - For Regulation logics (e.g., L-016, L-017, L-039–041, L-083, L-085), wire `config/regulations/` loader and effective-date selection.
5. Orchestrators
   - Enhance auto-discovery based on `core/logic_loader.LOGIC_REGISTRY` and tag filters.
6. MCP + Security
   - Tighten `/mcp/*` typed error shapes, ensure auth on all sensitive endpoints, add redaction and rate-limit placeholders.
7. Tests & CI
   - Add per-logic unit tests (stubs with 3+1 cases), orchestrator integration tests, contract tests for Zoho client, and perf guards.
   - Add GitHub Actions workflow.
8. Auto-Expansion & Reverse-Learning
   - Implement stub creators when unmet intents appear; reverse-learning flow writing to `docs/learned_formats/`.
9. Regulation Watchers
   - Create versioned JSON loaders and watcher placeholders in `config/regulations/`.
10. Observability + Changelog
   - Structured logs; append-only updates to `docs/CHANGELOG.md` per batch.

## Conflicts/Notes
- Naming in repo largely matches Master Index; retain existing names but ensure `LOGIC_META.id` uses `L-###` format (already does).
- Keep static logics minimal (no feature drift); only refactor for clarity/contract.

## Next Steps (Batch-1)
- Create missing dirs/files; seed `docs/CHANGELOG.md`.
- Generate `gap_report.md` with current findings.
- Tighten `/mcp/*` error typing and ensure form-encoded token refresh already in place.
- Run tests; add initial unit test skeletons for a few logics to establish pattern.


