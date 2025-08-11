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
  - Added standardized provenance helper `helpers/provenance.py` and enhanced history wrapper in `helpers/history_store.py`.
  - Extended `helpers/learning_hooks.py` with strategy helpers and a flexible `score_confidence` supporting new signature.
  - Added output contract validator in `helpers/schema_registry.py`.
  - Augmented `logics/logic_001_profit_and_loss_summary.py` and `logics/logic_006_zone_wise_expenses.py` to add per-figure provenance, history logging, and confidence refinement.
  - Added developer template `docs/dev_templates/logic_with_learning.md`.
