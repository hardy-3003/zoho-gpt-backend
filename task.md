### Tasks to reach full MASTER_SCOPE_OF_WORK compliance

Only Partial (⚠️) and Pending (⏳) items are listed. Sections correspond to `MASTER_SCOPE_OF_WORK.md`.

- **0.1 Self‑Learning hooks (per logic)** — ⚠️ Partial
  - **Desc**: Standardize `score_confidence`, `record_feedback`, and per‑logic strategy registry usage across all 200 logics.
  - **Priority**: High
  - **Dependencies**: `helpers/learning_hooks.py` enhancements

- **0.2 History‑Aware deltas + anomaly flags** — ⚠️ Partial
  - **Desc**: Ensure every logic writes history events and optionally computes deltas and anomalies using `analyzers/`.
  - **Priority**: High
  - **Dependencies**: `helpers/history_store.py`, `analyzers/delta_compare.py`, `analyzers/anomaly_engine.py`

- **0.3 Reverse‑Learning pipeline (PDF → generator)** — ⏳ Pending
  - **Desc**: Implement end‑to‑end: PDF field extraction, provenance learning, schema capture to `/docs/learned_formats/`, verification, and auto‑enable orchestration.
  - **Priority**: High
  - **Dependencies**: `helpers/pdf_extractor.py`, `helpers/schema_registry.py`, `orchestrators/generic_report_orchestrator.py`, `docs/CHANGELOG.md`

- **0.5 Smart Accounting Validation coverage** — ⚠️ Partial
  - **Desc**: Integrate `helpers/rules_engine.validate_accounting` (and related checks) in all applicable logics.
  - **Priority**: Medium
  - **Dependencies**: `helpers/rules_engine.py`

- **0.7 Orchestration: Graph‑based DAG + partial retries** — ⚠️ Partial
  - **Desc**: Upgrade `orchestrators/mis_orchestrator.py` to DAG execution, per‑node retries, and graceful degradation annotations.
  - **Priority**: Medium
  - **Dependencies**: `core.logic_loader`, `core.registry`, `orchestrators/mis_orchestrator.py`

- **0.8 Auto‑Expansion of logic stubs** — ⏳ Pending
  - **Desc**: When patterns/requests repeat, auto‑create/extend logic stubs and register schemas/tests automatically.
  - **Priority**: Medium
  - **Dependencies**: `core/logic_loader.py`, `helpers/schema_registry.py`, test scaffolder

- **1.KT Observability (structured logs + metrics)** — ⏳ Pending
  - **Desc**: Add per‑logic and per‑pipeline telemetry (runtime, cache hits, error taxonomy, anomaly counts).
  - **Priority**: Medium
  - **Dependencies**: logging/metering utility

- **2.1 Logic Module Contract docstring & schema refs** — ⚠️ Partial
  - **Desc**: Ensure each logic includes the contract docstring (Title, ID, Tags, Inputs, Outputs, Assumptions, Evolution Notes) and uses schema refs.
  - **Priority**: Medium
  - **Dependencies**: `helpers/schema_registry.py`

- **2.2 Provenance mapping per field** — ⚠️ Partial
  - **Desc**: Enforce consistent provenance maps across results; ensure sources/paths recorded per figure.
  - **Priority**: High
  - **Dependencies**: shared provenance helpers

- **2.3 Per‑logic strategy registry (self‑learning state)** — ⏳ Pending
  - **Desc**: Lightweight strategy/state registry embedded per logic to evolve heuristics safely.
  - **Priority**: Medium
  - **Dependencies**: `helpers/learning_hooks.py`

- **3.1 Orchestrator Auto‑discovery by tags/rules** — ⚠️ Partial
  - **Desc**: Expand auto‑discovery in orchestrators for dynamic inclusion of matching logics.
  - **Priority**: Low
  - **Dependencies**: `core.logic_loader`

- **4.x Reverse‑Learning verification & auto‑enable** — ⏳ Pending
  - **Desc**: Reconciliation pass vs totals/subtotals; upon success, auto‑enable as orchestrated report.
  - **Priority**: High
  - **Dependencies**: reverse‑learning pipeline (0.3)

- **5.x History, Deltas & Anomaly integration across logics** — ⚠️ Partial
  - **Desc**: Systematically wire `history_store`, `delta_compare`, `anomaly_engine` in logic outputs with alerts.
  - **Priority**: Medium
  - **Dependencies**: analyzers

- **6.1 Tests: unit per logic; integration for orchestrators** — ⚠️ Partial
  - **Desc**: Add missing unit tests for remaining logics and strengthen orchestrator integration tests.
  - **Priority**: High
  - **Dependencies**: pytest scaffolds under `tests/unit/logic_xxx/`

- **6.2 Telemetry: metrics export** — ⏳ Pending
  - **Desc**: Add counters/histograms and structured logs for each logic and orchestrator run.
  - **Priority**: Medium
  - **Dependencies**: observability utility

- **6.3 Upgrades: adapters/migrations for learned schemas** — ⚠️ Partial
  - **Desc**: Create adapters and migration notes/scripts when learned schemas change.
  - **Priority**: Low
  - **Dependencies**: `docs/CHANGELOG.md`, schema versioning

- **7.1 /mcp/search planning depth** — ⚠️ Partial
  - **Desc**: Improve token→logic planner to handle richer NL intents, synonyms, and constraints.
  - **Priority**: Low
  - **Dependencies**: `core/logic_loader.py`

- **7.2 Streaming progress (SSE) integration** — ⚠️ Partial
  - **Desc**: Tie `/mcp/stream` progress to real execution stages; optionally inline SSE for `/mcp/fetch`.
  - **Priority**: Low
  - **Dependencies**: orchestrators, execution hooks


### Running updates
- Will move items here to Completed as implementations land and tests go green.


