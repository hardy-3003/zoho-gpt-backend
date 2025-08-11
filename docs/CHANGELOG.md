## 2025-08-09

- L4 Self-learning scaffolds
  - Added per-logic strategy registry helpers in `helpers/learning_hooks.py`.
  - Default schema registration across all loaded logic IDs via `core/logic_loader.load_all_logics()` → `helpers.schema_registry.ensure_all_logic_defaults`.
  - PDF reverse-learning primitives: `helpers/pdf_extractor.learn_provenance_mapping`.
- MCP endpoints unchanged; planner and orchestrator untouched.

# CHANGELOG (append-only)

- 2025-08-09 [infra] Initialize SOW/Protocol alignment scaffolding
  - Added plan.md; created docs/, docs/learned_formats/, config/regulations/, prompts/, _graveyard/, mcp/ dirs.
  - Set up feature branch and pre-change tag.

- 2025-08-11: Phase 1 foundation
  - Observability v1: added helpers/obs.py (runtime metrics + error logs); instrumented L-001, L-006, and RL generator; tests and CI artifact upload.
  - Orchestrator v1: DAG executor with per-node retries + graceful degradation; /mcp/stream for progress; unit test + CI smoke.
  - Wave 4: Applied L4 wrapper to Logic_031–Logic_040 (ops/inventory KPIs). Added parametric contract tests; seeded minimal domain provenance for inventory/ops logics.
  - Reverse-Learning (minimal E2E): added pdf_extractor shim, learned-format registry, generic_report_orchestrator learn+generate, main.py endpoints /rl/learn and /rl/generate, and integration test.
  - RL verification: reconciliation check + auto-enable flag on successful totals; alerts include reconciliation findings.
  - Added standardized provenance helper `helpers/provenance.py` and enhanced history wrapper in `helpers/history_store.py`.
  - Extended `helpers/learning_hooks.py` with strategy helpers and a flexible `score_confidence` supporting new signature.
  - Added output contract validator in `helpers/schema_registry.py`.
  - Augmented `logics/logic_001_profit_and_loss_summary.py` and `logics/logic_006_zone_wise_expenses.py` to add per-figure provenance, history logging, and confidence refinement.
  - Added developer template `docs/dev_templates/logic_with_learning.md`.
  - Wave 2: Applied L4 wrapper to Logic_013–Logic_022 (additive only; provenance/history/confidence); added parametric contract tests.
  - Wave 3: Applied L4 wrapper to Logic_023–Logic_030 (additive only; provenance/history/confidence); added parametric contract tests for the batch.
  - Schema hardening: added provenance validator + alerts item checks; added DATA_DIR support for history/strategy stores for container-safe writes.
