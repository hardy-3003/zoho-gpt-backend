# AGENT_EDIT_PROTOCOL.md — V7 (Execution-Ready)

Effective Date: 2025-08-18  
Owner: hardy-3003  

---

## 1) Core Execution Objective
- Complete every task in `task.md` exactly once in forward phase order (1 → 5).
- No backtracking: create missing dependencies in the same or earlier phase.
- By the end of Phase 5, all items in `MASTER_SCOPE_OF_WORK.md` must be complete, compliant, tested, and integrated, with MCP and other platforms ready for launch.

---

## 2) Scope Enforcement Rules
- Every `MASTER_SCOPE_OF_WORK.md` line item must map to one or more Task IDs in `task.md`.
- Missing or non-compliant items must become explicit tasks in the earliest feasible phase.
- Before editing `task.md`, perform a full repo audit and convert gaps into tasks placed in Phase ≤ first consumer. Record audit summary in `log.md`.
- Maintain a Traceability Matrix at the end of `task.md` mapping each MASTER scope item to Task IDs.
- All tasks in `task.md` must contain: Title, Why, Inputs/Prereqs, Steps, Deliverables, DoD, Acceptance Criteria, Owner/Role, Duration, Risks/Mitigation, Assumptions/Decisions, Traceability IDs.
- **Enforce full coverage of **231 logics**. Explicitly include **L-231 Ratio Impact Advisor**, `/helpers/ratios.py`, `/configs/bank_covenants.yaml`, and `/configs/ratio_targets.yaml`.

---

## 3) Task & Phase Rules
- Phases 1–5 only. Subphases must be independent.
- No forward dependencies. If found, pull enablers forward.
- Cross-phase linking tests must be added for interactions with earlier phases. Resolve issues before marking complete.
- Definition of Done: code compiles, tests added/updated and pass, contracts honored, docs updated, no TODO/FIXME left, surfaces parity verified.
- If JE-time checks are enabled, `transaction_posting_orchestrator.py` must be delivered in Phase 2 with deterministic ratio covenant enforcement.

---

## 4) L4 Autonomous Intelligence Standards
1. Self-Learning: use `/helpers/learning_hooks.py` for evaluations, pattern extraction, confidence scoring, retry/fallback; adapt to IFRS/GAAP/local rules.
2. History-Aware: maintain persistent logs via `/helpers/history_store.py`.
3. Reverse-Learning: map unknown formats via `/helpers/schema_registry.py`, store in `/docs/learned_formats/`, log in `docs/CHANGELOG.md`.
4. Expandable in Same File: evolve logic in `/logics/*.py`; new files only for shared utilities.
5. Smart Accounting Validation: enforce via `/helpers/rules_engine.py` with fix suggestions.
6. No Rewrites: preserve prior behavior via adapters; log in `docs/CHANGELOG.md`.
7. Many-to-One Orchestration: `/orchestrators/` can combine 2 → ∞ logics with retries and degradation handling.
8. Auto-Expansion: auto-create/extend logic stubs, register schemas, add tests, guard via rules engine.
9. Logic Category Awareness: Static, Dynamic–Regulation (watch `/config/regulations/`), Dynamic–Patterns, Dynamic–Growth, Dynamic–Behavior.
10. External Data Integration: support GSTN, ITD, banks, POS; operate in MCP and non-MCP modes.
11. Self-Observation & Data Retention: track metrics/anomalies, maintain baselines, propose optimizations.
12. ID Collision Policy: respect reserved ID ranges, ensure uniqueness.
13. Deterministic Ratio Guardrails** — All JE-time posting checks must simulate pre/post ratios, enforce covenant thresholds from configs, attach evidence nodes, and advise alternatives.

---

## 5) Logging & Change Tracking
- `log.md` is a single continuous, append-only, chronological file in repo root.
- Log Entry Structure (indented, no inner code fences):
    ## Task ID: P{phase}.{subphase}.{index}
    Task Title: <copied from task.md>
    Date: YYYY-MM-DD
    Commit Hash: <git commit>
    
    Summary of Changes
    - What changed and why.
    - Files/modules updated.
    
    After Snippet:
        # Minimal excerpt showing final state after change
    
    Reasoning
    - Why change was required.
    - Related tasks/dependencies validated.
- End-of-phase summary in `log.md`: completed tasks, pending tasks with reasons, risks/follow-ups, confirmation of cross-phase linking test success.
- Evidence nodes must include:  
  - Trial Balance hash before/after JE.  
  - Covenant profile hash (from `/configs/bank_covenants.yaml`).  
  - JE payload hash.  
  - Simulation outputs of breached ratios.

---

## 6) Task Completion Marking
- On completion, append to the task title in `task.md`: [COMPLETED — YYYY-MM-DD]
- If partial: [PARTIAL — awaiting <Task ID>]

---

## 7) Quality & Verification Rules
- Lint/style pass, no high-severity vulnerabilities.
- Unit & integration tests ≥ 95% pass rate.
- MCP vs non-MCP parity where relevant.
- Cross-module interactions require integration tests in the same phase.
- Add ratio-specific SLOs:  
  - `ratio_sim_latency_ms` (p95 ≤ budget).  
  - `ratio_breach_count` (must be monitored & alert if > threshold).  
  - `suggestion_accept_rate` tracked for advisory effectiveness.

---

## 8) Workflow Enforcement
1. Read `task.md`; select next pending task.
2. Verify prerequisites exist in current or earlier phase; add enabler if missing.
3. Implement change in one pass.
4. Commit with message: Task P{phase}.{subphase}.{index} — <Title>.
5. Append to `log.md` per Section 5.
6. Mark completion in `task.md` per Section 6.
7. Push to repo.

---

## 9) Dependency & Linking Guardrails
- Dependencies must point backward or within current phase.
- Create missing enablers immediately.

---

## 10) Change Reversal Support
- `log.md` + commit hash must allow reversal without agent.
- Git history must match log entries.

---

## 11) Sanity Checks Before Closing a Phase
- All MASTER scope items in phase are covered and marked.
- No forward dependencies.
- Cross-phase linking tests passed.
- L4 standards satisfied.
- Repo stable, docs updated, ready for next phase.
- Explicitly verify coverage is **231/231** (not 230), with L-231 Ratio Impact Advisor and ratio covenant configs/helpers present.

---

## 12) Prohibited Actions
- Editing `MASTER_SCOPE_OF_WORK.md` to fit plan.
- Skipping repo audit or traceability updates.
- Marking complete without tests, `log.md`, and `task.md` update.
- Introducing forward dependencies or leaving TODO/FIXME.
