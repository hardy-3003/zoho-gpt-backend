# Agent Edit Protocol (L4 – Autonomous, Closed-Loop Evolution)

This document defines the mandatory rules for all logic modules (.py) and integrations in the Zoho GPT Backend.  
Every logic must adhere to **L4 — Autonomous, Closed-Loop Evolution** standards.

---

## 1. Self-Learning
- Each logic must **improve over time** from:
  - New inputs
  - User corrections
  - Usage patterns
- Include **hooks/placeholders** for:
  - GPT-based evaluations
  - Pattern extraction
  - Confidence scoring
  - Retry logic
- Self-learning code should use `/helpers/learning_hooks.py` functions and store variations in the local strategy registry inside the logic file.

---

## 2. History-Aware
- Persist **changelogs** for:
  - Invoices
  - Bills
  - Purchase Orders (POs)
  - Salaries
  - Items
  - Taxes
- Track:
  - Price changes
  - Periodic deltas
  - Vendor and cross-organization deviations
- Enable **anomaly flags** for manipulation detection and inconsistent trends.
- All history logs must be stored via `/helpers/history_store.py`.

---

## 3. Reverse-Learning from Custom Inputs
- When encountering **unfamiliar report formats** (e.g., new MIS PDFs):
  1. Auto-extract fields using `/helpers/pdf_extractor.py`.
  2. Map each figure to its Zoho origin using nomenclature maps in `/helpers/schema_registry.py`.
  3. Learn and **store** the format in `/docs/learned_formats/`.
  4. Generate it **autonomously next time**.
- Log every new format learned in `/docs/CHANGELOG.md`.

---

## 4. Expandable in the Same File
- Each logic must grow inside **its own `.py` file** in `/logics/`.
- Use **internal subtrees/strategies** for expansion.
- Create new files only for **shared utilities** in `/helpers/`.

---

## 5. Smart Accounting Validation
- Automatically check for accounting rule violations, including:
  - Unbalanced reversals
  - Mismatched categories
  - Missing journals
  - Date anomalies
- Use `/helpers/rules_engine.py` for these validations.
- Suggest fixes where possible and append recommendations to output.

---

## 6. No Rewrites
- All improvements are **additive** — no starting from scratch.
- Migrations/adapters must **preserve old behavior** while extending capabilities.
- Store migration notes in `/docs/CHANGELOG.md`.

---

## 7. Many-to-One Orchestration
- Orchestrator modules in `/orchestrators/` can **combine 2 → ∞ logics** for composite outputs.
- Support:
  - Configurable pipelines
  - Partial retries
  - Graceful degradation

---

## 8. Auto-Expansion
- From repeated requests/patterns:
  - Auto-create/extend **logic stubs** in `/logics/`.
  - Register them in `/helpers/schema_registry.py`.
  - Add automated tests in `/tests/unit/logic_xxx/` named `test_logic_xxx.py`.
  - Add guardrails via `/helpers/rules_engine.py`.

---

## 9. Logic Category Awareness

When the agent is performing edits or enhancements, it must use the **Logic Category Annotations** from `MASTER_SCOPE_OF_WORK.md` to decide the correct approach.

- **Static**:  
  - Focus on performance improvements, code clarity, and bug fixes.  
  - Avoid introducing functional changes unless approved.  
  - Do not auto-expand unless specifically instructed.

- **Dynamic (Regulation)**:  
  - Monitor relevant rule JSON files in `/config/regulations/` (GST, ITD, TDS).  
  - Update logic immediately when regulations change.  
  - Implement **effective-date versioning** by storing prior logic variations in `/helpers/history_store.py` and applying only when the transaction date falls in the effective range.

- **Dynamic (Patterns)**:  
  - Continuously refine anomaly heuristics and thresholds using `/helpers/history_store.py`.  
  - Add new detection strategies without breaking existing ones.

- **Dynamic (Growth)**:  
  - Expand feature coverage as business operations grow.  
  - Integrate new metrics, data sources, and modules when available.

- **Dynamic (Behavior)**:  
  - Learn from user inputs and reverse-learning pipeline.  
  - Support new formats, report types, and interaction patterns.

**Agent Edit Protocol Override:**  
If a Dynamic logic receives repeated related requests, the agent must:
1. Generate/extend the corresponding logic file in `/logics/`.  
2. Add/update schemas in `/helpers/schema_registry.py`, tests in `/tests/unit/logic_xxx/`, and registry entries.  
3. Log changes in `/docs/CHANGELOG.md` with category tag.

---

### Implementation Notes
- All logic modules must register in `/helpers/schema_registry.py`.
- Must pass **unit tests + validation tests** before deployment.
- Agent edits should always:
  1. Check this protocol.
  2. Implement changes in compliance with L4 rules.
  3. Log changes in `/docs/CHANGELOG.md`.

---

### ID Collision Policy (One ID → One File)
- Effective 2025-08-09, the ID range L-126…L-145 is authoritative for Inventory/Production/Fleet deep-spec logics.
- Older audit/AI/risk modules previously occupying L-126…L-145 have been moved to L-181…L-200 with file renames and updated `LOGIC_META["id"]`.
- Total logics: target 200+. New additions should avoid existing IDs and update docs accordingly.

---

**Author:** Hardy  
**Last Updated:** 2025-08-09
