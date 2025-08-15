# Agent Edit Protocol (L4 – Autonomous, Closed-Loop Evolution) — V3

This document defines **mandatory rules** for all logic modules (`.py`) and integrations in the Zoho GPT Backend.  
Every logic must comply with **L4 — Autonomous, Closed-Loop Evolution** standards, ensuring the system becomes progressively more intelligent, self-auditing, and adaptable — capable of outperforming human Chartered Accountants in accounting accuracy, compliance, and data-driven insight generation.

---

## 1. Self-Learning (Continuous Improvement Loop)
- Each logic must **continuously improve** from:
  - New inputs and datasets
  - User corrections or overrides
  - Detected usage patterns
- Include **learning hooks** for:
  - GPT-based evaluations
  - Pattern extraction
  - Confidence scoring
  - Retry and fallback strategies
- Implement hooks via `/helpers/learning_hooks.py` and store learned variations in a **local strategy registry** within the logic file.
- Self-learning must adapt rules for:
  - Accounting standards (IFRS, GAAP, local regulations)
  - Taxation logic (GST, Income Tax, TDS, future rules)
  - Audit heuristics

---

## 2. History-Aware (Change Intelligence)
- Persist **detailed changelogs** for:
  - Invoices
  - Bills
  - Purchase Orders (POs)
  - Salaries
  - Items
  - Taxes
  - Regulatory data (GST filings, ITD notices, TDS)
- Track:
  - Price changes over time
  - Vendor and client deviations
  - Cross-organization differences
  - Period-over-period deltas
- **Anomaly flags** must be triggered for:
  - Potential fraud
  - Data manipulation
  - Inconsistent trends
- All history logs must be stored in `/helpers/history_store.py` and be queryable by other modules.

---

## 3. Reverse-Learning from Custom Inputs
- On encountering **unfamiliar formats** (e.g., new MIS PDFs, GST JSON, ITD XML):
  1. Extract fields via `/helpers/pdf_extractor.py` or equivalent data parser.
  2. Map each field to its Zoho origin using `/helpers/schema_registry.py`.
  3. Store the learned format in `/docs/learned_formats/`.
  4. Autonomously reproduce the format next time.
- Every learned format must be logged in `/docs/CHANGELOG.md` with an identifier.

---

## 4. Expandable in the Same File
- Each logic must evolve **within its own `.py` file** inside `/logics/`.
- Internal expansions should use **sub-strategies** or nested classes.
- New files should be created **only for shared utilities** in `/helpers/`.

---

## 5. Smart Accounting Validation
- Automatically check for:
  - Unbalanced reversals
  - Category mismatches
  - Missing journals
  - Date anomalies
  - Cross-checks with **Income Tax**, **GST**, **TDS** rules
- Use `/helpers/rules_engine.py` for enforcement.
- Append actionable **fix suggestions** to output.

---

## 6. No Rewrites (Evolution > Replacement)
- All improvements must be **additive** — never discard functional history.
- If a migration is necessary:
  - Preserve old behavior via adapters.
  - Document changes in `/docs/CHANGELOG.md`.

---

## 7. Many-to-One Orchestration
- Orchestrator modules in `/orchestrators/` may **combine 2 → ∞ logics** for:
  - Composite reports
  - Multi-source validation
  - Cross-checking audits
- Must support:
  - Configurable pipelines
  - Partial retries
  - Graceful degradation on failures

---

## 8. Auto-Expansion
- Repeated patterns/requests must:
  - Auto-create/extend logic stubs in `/logics/`
  - Register in `/helpers/schema_registry.py`
  - Add tests in `/tests/unit/logic_xxx/` (`test_logic_xxx.py`)
  - Guardrail with `/helpers/rules_engine.py`

---

## 9. Logic Category Awareness (From MASTER_SCOPE_OF_WORK.md)
- **Static**: Improve performance/clarity without changing functionality.
- **Dynamic (Regulation)**:
  - Watch `/config/regulations/` for GST/ITD/TDS updates.
  - Version rules by **effective date**.
- **Dynamic (Patterns)**:
  - Refine anomaly heuristics over time.
- **Dynamic (Growth)**:
  - Expand coverage with new metrics/data sources.
- **Dynamic (Behavior)**:
  - Learn new formats and interaction styles.

---

## 10. External Data Integration for Autonomous Auditing
- Logic must be able to:
  - Fetch data from Income Tax Department APIs/portals
  - Fetch GST filing data from GSTN
  - Integrate bank feeds, payment gateways, POS data
  - Cross-check compliance automatically
- Must operate in both:
  - **MCP Mode** (direct GPT integration)
  - **Non-MCP Mode** (standalone backend, APIs, CLI tools)

---

## 11. Self-Observation & Full Data Retention
- Monitor **every transaction, metric, and anomaly**.
- Keep **historical baselines** for all data types.
- Compare **past vs present** to:
  - Predict risks
  - Detect inefficiencies
  - Suggest optimization actions

---

## 12. ID Collision Policy (Critical for Scaling)
- Effective 2025-08-09:
  - L-126…L-145: Reserved for Inventory/Production/Fleet deep-spec logics.
  - Audit/AI/Risk modules in L-181…L-200.
- New logics must not conflict with existing IDs.

---

### Implementation Notes
- All logic modules must be in `/helpers/schema_registry.py`.
- Must pass **unit + validation tests** pre-deploy.
- Agent edits must:
  1. Check this protocol.
  2. Follow L4 rules strictly.
  3. Log changes in `/docs/CHANGELOG.md`.

---

**Author:** Hardy  
**Last Updated:** 2025-08-15