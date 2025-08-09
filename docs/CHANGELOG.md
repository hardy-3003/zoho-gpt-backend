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
