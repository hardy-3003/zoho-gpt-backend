# new# new_tasks.md — Forward-Only, One-Pass Plan (V9, Cross-Phase Linked & Repo-Aligned)

**Repo:** hardy-3003/zoho-gpt-backend (`main`)  
**Owner:** @hardy-3003  
**Version (IST):** 2025-08-18  
**Purpose:** Deliver a **single forward pass** (Phases **1–5**, no Phase 0) that makes this repo **fully compliant** with **MASTER_SCOPE_OF_WORK.md** (all **231** logics, L4-ready) and **AGENT_EDIT_PROTOCOL.md**, and **launchable** immediately after Phase 5 **without** revisiting earlier steps.

> **Non-negotiables**
> - Phases are **1–5** only. Every sub-phase (e.g., **1.1, 1.2**) is **independently shippable** to DoD.
> - **No forward dependencies**: if Phase N needs X, X exists in **Phase ≤ N** as an **enabler** (contract/stub).
> - **One-pass**: once a task is done, we never return to it.
> - **Machine-enforced**: CI gates & scripts **fail builds** if anything is missing/misaligned.

---

## 0) Change Log
- **V9:** Extended V8 with **MASTER V4 alignment** by:
  - Raising logic coverage to **231 (not 230)** by adding **L-231 Ratio Impact Advisor**.
  - Adding `/helpers/ratios.py` and `/configs/bank_covenants.yaml`, `/configs/ratio_targets.yaml`.
  - Adding **transaction_posting_orchestrator** (optional) to support JE-time ratio checks powered by L-231.
  - Extending **replay fixtures**, **evidence nodes**, **observability metrics** (`ratio_sim_latency_ms`, `ratio_breach_count`, `suggestion_accept_rate`), and **release gates** for ratio covenant parity and performance.
  - Updating **traceability** and **discovery** targets to enforce **231/231** coverage end-to-end.
- **V8:** Rebuilt with explicit **cross-phase compatibility** tasks, integrated **byte-identical replay**, **performance gates**, and an **explicit catalog of logic_201…230** (borrowed clarity from V4), while preserving V7’s forward-only backbone and machine-enforced guarantees.

---

## 1) Plan Overview

### Scope Summary
Backend that executes **231** L4-capable logic modules with evidence-first design; robust MCP and non-MCP surfaces; Regulatory OS (rule packs + DSL + watchers); reverse-learning & anomaly; reproducible evidence & replay; production-grade ops (security, observability, SLOs). **All contracts are anchored in Phase 1**; later phases must comply.

### Phase Map (1–5)
1. **Foundations & Enablers** — CI/CD, **surfaces contracts** (REST/**SSE**/**webhooks**/**CLI**), Evidence & Regulatory base, **231/231 scaffolds** with L4 contracts, ID-policy, golden tests, generators/auditors, one-command dev, **contract hash snapshots**.
2. **Core Logic & Orchestration** — Implement/normalize behavior; **DAG** + **Auto-Discovery** (reports); REST↔MCP parity smoke; **Auto-Expansion contracts**; **deterministic caching**; **replay system (closed-period) groundwork**; **perf baselines**.
3. **Intelligence** — Reverse-learning pipeline, anomaly engines, **Auto-Expansion live** (guard-railed); **cross-phase E2E compat suites** ensuring P3 does not break P1/P2; **L4 activation**.
4. **Integrations & Regulatory OS** — Connectors; **Regulatory adapters** (GSTR-2B, 26AS, AIS, e-invoice, e-way, AA); watchers→auto-PRs; security/residency hardening; (GraphQL **required only if MASTER mandates**, otherwise optional).
5. **Launch & Run** — E2E rehearsal; **MCP POST/SSE** & surfaces parity release gates; **byte-identical replay gate**; SLOs; rollback; Go/No-Go.

### No-Dependency Declaration
All Inputs/Prereqs reference **same or earlier** sub-phases. Missing prerequisites are introduced as **Phase-1 enablers**.

---

## 2) Global Conventions

**Task ID:** `P{phase}.{subphase}.{index}` (e.g., `P1.2.3`)  
**Uniform Fields (every task):** Title · Why · Inputs/Prereqs · Steps (one-pass) · Artifacts (repo paths) · DoD · Acceptance Criteria · Owner · Duration (est) · Risks/Mitigation · Assumptions · Traceability (MASTER IDs)  
**Quality Bars (implicit):** ruff + mypy + bandit + safety + SBOM, unit + contract + golden + parity + E2E tests, docs/runbooks updated.

---

## 3) Dependency Guardrails & Cross-Phase Linking (NEW IN V8)

- **Contract Anchors (Phase-1):** shared dataclasses & **schema hash snapshots** for all surfaces. Any schema drift later → CI fails.  
- **Parity Smokes (Phase-2):** MCP vs REST `/api/execute` + discovery=**231** → ensures P2 complies with P1.  
- **Compat E2E (Phase-3):** learning/anomaly/auto-expansion **must** pass end-to-end against P1/P2 contracts.  
- **Adapter Parity (Phase-4):** regulatory adapters normalize to **Phase-1 internal schema** (golden parity).  
- **Final Release Gates (Phase-5):** MCP POST/SSE & surfaces parity + **byte-identical replay** + E2E all green.

---

## 4) Phases, Sub-phases & Tasks (repo-aligned)

> Paths below match current repo patterns. Keep Task IDs stable even if files move.

### **Phase 1 — Foundations & Zero-Dependency Enablers [COMPLETED — 2025-08-18]**

#### **Subphase 1.1 — CI/CD, One-Command Dev, ID Policy**
- **P1.1.1 CI workflow upgrade & SBOM [COMPLETED — 2025-01-27]**
  - **Why:** Make completeness *mechanically enforced*.  
  - **Steps:** Extend `.github/workflows/ci.yml` with jobs: `lint`, `type`, `unit`, `contract`, **golden**, **id_policy**, **master_index_check**, **repo_inventory_check**, **logic_coverage_gate**, **l4_readiness_gate**, **traceability**, **dependency_audit**, **parity_smoke**, **replay_golden** (stub), **perf_baseline** (stub). Produce SBOM via `cyclonedx`.  
  - **Artifacts:** `.github/workflows/ci.yml`, `sbom.json`, `pyproject.toml`.  
  - **DoD:** CI runs all jobs on PR; SBOM generated.  
  - **Acceptance:** Any missing gate → CI fail.

- **P1.1.2 One-command dev [COMPLETED — 2025-01-27]**
  - **Artifacts:** `justfile` or `Makefile`; `docs/runbooks/dev.md`.  
  - **DoD:** `just dev` runs API + tests watch from clean clone.

- **P1.1.3 ID-range/collision linter [COMPLETED — 2025-01-27]**
  - **Why:** Enforce machine-readable ID policy for 231/231 logic coverage.
  - **Artifacts:** `scripts/id_linter.py`; CI `id_policy` job; `just id-lint` target; updated `docs/runbooks/dev.md`.
  - **DoD:** IDs 001–231 unique & within range; linter fails on any violation; CI integration complete.

#### **Subphase 1.2 — Contract Anchors & Non-MCP Surfaces (Contracts Only)**
- **P1.2.1 Contract dataclasses & schema hash snapshots [COMPLETED — 2025-08-18]**
  - **Why:** **Cross-phase anchors.**  
  - **Artifacts:** `surfaces/contracts.py`, `tests/contract/test_contract_shapes.py` (snapshot hashes).  
  - **DoD:** Any schema change triggers snapshot diff → CI fail.

- **P1.2.2 REST `/api/execute` (contract) [COMPLETED — 2025-01-27]**
  - **Artifacts:** `app/api/execute.py`, import in `main.py`; `tests/contract/test_execute.py`; OpenAPI update.  
  - **DoD:** Contract tests green.

- **P1.2.3 Non-MCP `/sse` (contract) [COMPLETED — 2025-01-27]** → `app/api/sse.py`, `tests/contract/test_sse.py` (ordered events, resume).  
- **P1.2.4 `/webhooks` ingress (contract) [COMPLETED — 2025-01-27]** → HMAC, replay protection, tests.  
- **P1.2.5 `/cli` runner (contract) [COMPLETED — 2025-01-27]** → `cli/__main__.py`, tests.

#### **Subphase 1.3 — Evidence & Regulatory OS Base + Golden Gate**
- **P1.3.1 Evidence OS base [COMPLETED — 2025-01-27]** → `evidence/ledger.py`, `evidence/blob_store.py`, `evidence/signer.py`, tests.  
- **P1.3.2 Regulatory OS loader + effective-date [COMPLETED — 2025-08-18]**  
  - **Steps:** move `gst.json`→`regulatory/rule_packs/in/gst.json`; create `regulatory/loader.py` (schema validate + date selection).  
  - **Artifacts:** loader + golden tests.  
- **P1.3.3 Golden-test gate [COMPLETED — 2025-08-18]** → `tests/golden/**` (include MIS fixtures).
 - **P1.3.4 Evidence Replay “Golden” Runner [COMPLETED — 2025-08-18]**  
   - **Why:** Replay prior runs deterministically from stored manifests to enforce evidence-first governance.  
   - **Artifacts:** `tools/hash_utils.py`, `tools/replay_runner.py`, `tests/replay/**` (fixtures + tests), `just` targets (`replay-test`, `replay-run`, `replay-freeze`), CI `replay_golden` job.  
   - **DoD:** At least two fixtures (logic_001, logic_231) with frozen hashes; tests assert equality; diffs uploaded on CI failure.  

#### **Subphase 1.4 — Consent & Observability Skeleton**
- **P1.4.1 Consent schema & redaction [COMPLETED — 2025-08-18]** → `consent/schema/consent.schema.json`, `consent/redactor.py`, tests.  
- **P1.4.2 — Observability baseline [COMPLETED — 2025-08-18]** → structured logger, in-proc metrics, `/metrics.json`, tests, docs.

#### **Subphase 1.5 — Master Logic Coverage 231/231 (Contracts + L4 Template)**
> Repo has ~202 logic modules. **Create the missing ~29 now** (V9 adds L-231), and enforce L4 hooks for **all 231**.

- **P1.5.1 Extract MASTER index (authoritative 231) [COMPLETED — 2025-08-18]**  
  - **Why:** Lock authoritative list length to MASTER.  
  - **Artifacts:** `tools/extract_master_index.py` → `artifacts/master_index.json`; CI `master_index_check`.  
  - **DoD:** Exactly **231** logic items extracted from MASTER.

- **P1.5.2 Scan repo inventory [COMPLETED — 2025-08-18]**  
  - **Artifacts:** `tools/scan_repo_logics.py` → `artifacts/repo_logics.json`; CI `repo_inventory_check`.  
  - **DoD:** Inventory enumerates all `logics/logic_###_*.py`.

- **P1.5.3 Scaffold **all missing** logics (contract stubs) [COMPLETED — 2025-08-18]**  
  - **Steps:** Create each `logics/logic_###_<slug>.py` (see **Appendix A** names) with `LOGIC_META`, `handle()`, **subclass `l4_base`**, and contract tests.  
  - **Include:** `logic_231_ratio_impact_advisor.py` (NEW in V9).  
  - **Also add (NEW):** `/helpers/ratios.py`, `/configs/bank_covenants.yaml`, `/configs/ratio_targets.yaml` (deterministic ratio formulas and covenant profiles).  
  - **Artifacts:** `tools/gen_missing_logics.py` + generated files + `tests/contract/logics/*`.  
  - **DoD:** Exactly **231** logic modules; ratio helpers/configs present; contracts green; discovery lists all.

- **P1.5.4 L4 contract base (no-op hooks) [COMPLETED — 2025-08-18]**  
  - **Artifacts:** `logics/common/l4_base.py` with: `history_read/write`, `learn`, `reverse_learn`, `detect_anomalies`, `self_optimize`, `explain`, `confidence` (flags OFF).  
  - **DoD:** All logics subclass or implement L4 hooks.

- **P1.5.5 Coverage & L4 readiness gates [COMPLETED — 2025-08-18]**  
  - **Artifacts:** `tools/audit_l4_readiness.py`; CI gates must pass.  
  - **DoD:** CI `logic_coverage_gate` and `l4_readiness_gate` PASS for **231/231**.

> **Phase-1 Exit (hard gates):** CI green for `lint/type/unit/contract/golden/id_policy/master_index_check/repo_inventory_check/logic_coverage_gate/l4_readiness_gate/traceability/dependency_audit/parity_smoke(restricted)/replay_golden(stub)/perf_baseline(stub)`.  
> Non-MCP contracts live; Evidence & Regulatory base live; **231/231** discoverable; L4 hooks present; ratio helpers/configs in place.  
> [COMPLETED — 2025-08-18]

---

### **Phase 2 — Core Functional Logic & Orchestration (no forward deps)**

#### **Subphase 2.1 — Orchestrator v2: DAG + Auto-Discovery**
- **P2.1.1 DAG scheduler conformance** → tests for parallelism, retry, idempotency, cycle detection.  
- **P2.1.2 Discovery report & health** → `core/logic_loader.py: discovery_report()` must list **231**; CI fails if not.  
- **P2.1.3 Orchestrator integration smoke** → sample DAGs deterministic.

#### **Subphase 2.2 — Implementations & Normalization**
- **P2.2.1 Implement core ops for newly scaffolded ~29**  
  - **Why:** Deliver working behavior for the new logic set added in Phase-1.  
  - **DoD (explicit in V9):** Implement `logic_231_ratio_impact_advisor.py` deterministically (JE-time simulation using `/helpers/ratios.py`, thresholds from `/configs/bank_covenants.yaml`, suggestions with `validate_accounting()` guard, evidence nodes for TB before/after, JE payload, and covenant profile hash).

- **P2.2.2 Normalize existing ~202 to IO contracts** (if needed).  
  - **DoD:** IO shapes match Phase-1 contracts; parity smoke green.

- **P2.2.3 REST↔MCP parity smoke** → `tests/parity/test_rest_vs_mcp.py` (first cross-phase link).

- **P2.2.4 Implement **transaction_posting_orchestrator** (optional but recommended) (NEW)**  
  - **Why:** Run JE-time ratio checks (L-231) *before commit*; block/warn per policy.  
  - **Artifacts:** `orchestrators/transaction_posting_orchestrator.py`, unit/integration tests.  
  - **DoD:** Deterministic policy gate with SSE-friendly progress; configurable “warn” vs “block”.

#### **Subphase 2.3 — Auto-Expansion (Contracts Only)**
- **P2.3.1 Stub-gen contracts & registry hookup** → `auto_expansion/contracts.py`, tests (no write).

#### **Subphase 2.4 — Deterministic Caching & Perf Baselines (NEW)**
- **P2.4.1 Cache keys & perf budgets** → `helpers/cache.py`, `tests/performance/test_load_performance.py`; budgets from `config/budgets.yaml`.  
- **DoD:** Top N logics meet p95/p99 thresholds; CI `perf_baseline` passes.

#### **Subphase 2.5 — Evidence Replay (Closed-Period, Byte-Identical) — groundwork**
- **P2.5.1 Replay framework (offline)** → `evidence/replay.py`, `tests/golden/test_replay_consistency.py`, `evidence/fixtures/closed_periods/**`.  
- **DoD (extend in V9):** Fixtures include JE simulations & covenant profiles so that L-231 “before/after” replays are **byte-identical**.

> **Phase-2 Exit:** DAG/discovery conformance; **all 231** have core behavior; parity smoke green; Auto-Expansion contracts in place; **replay groundwork** & **perf baselines** green; (optional) transaction orchestrator passing tests.

---

### **Phase 3 — Intelligence & Cross-Phase Compatibility (forward-only)**

#### **Subphase 3.1 — Reverse-Learning Pipeline**
- **P3.1.1 Ingest PDFs/JSON/XML → learned profiles** → `learning/reverse_pipeline.py`, tests using MIS fixture; deterministic improvement w/ changelog.

#### **Subphase 3.2 — Anomaly & Budgets**
- **P3.2.1 Deterministic anomaly detectors per logic** → `analyzers/anomaly.py`, extend `config/budgets.yaml`, tests.

#### **Subphase 3.3 — Auto-Expansion Live (Guard-railed)**
- **P3.3.1 Enable engine** → `auto_expansion/engine.py`, E2E tests; **never** overwrites curated code.

#### **Subphase 3.4 — L4 Activation Across All Logics**
- **P3.4.1 History/Reverse-learning ON**, **P3.4.2 Budgets active**, **P3.4.3 Self-optimize (conservative)**, **P3.4.4 Mediator for multi-logic compositions** → composite (≥3) plans must pass evidence & parity checks.  
- **P3.4.5 Ratio learning/advisory loop (NEW in V9)**  
  - **Why:** L-231 suggestions should adapt to org/facility decisions while remaining non-authoritative.  
  - **Artifacts:** Extend `helpers/learning_hooks.py` + L-231 to record accept/reject + context; metrics `suggestion_accept_rate`.  
  - **DoD:** Learning signals recorded, surfaced in observability; no drift from deterministic truths.

#### **Subphase 3.5 — Cross-Phase Compat E2E Suites (NEW)**
- **P3.5.1 Learning/Anomaly Compat E2E** → `tests/e2e/test_learning_parity.py` runs learned formats through **Phase-1 contracts** and **Phase-2 orchestrators**.  
- **P3.5.2 Auto-Expansion Guardrail E2E** → `tests/e2e/test_autoexp_guardrails.py` ensures generated stubs compile to P1 contracts and pass P2 discovery.  
- **DoD:** Both suites green; violations fail CI.

> **Phase-3 Exit:** Intelligence active; cross-phase E2E compat proven; mediator OK; ratio learning loop active; no backtracking required.

---

### **Phase 4 — Integrations, Regulatory OS & Hardening**

#### **Subphase 4.1 — Connectors (Consent-Bound)**
- **P4.1.1 Clients** → `connectors/{gsp_gst_client, irp_einvoice_client, ewaybill_client, itd_traces_client, apisetu_client, aa_client, mca_client}.py`, mocked contract tests.  
- **P4.1.2 Consent Compliance Auditor (Logic 216)** → `logics/logic_216_consent_compliance_auditor.py`.

#### **Subphase 4.2 — Regulatory Adapters (First-Class)**
- **P4.2.1–P4.2.6** → `regulatory/adapters/{gstr2b,26as,ais,einvoice,eway,aa}.py` + goldens under `tests/golden/regulatory/adapters/**`.  
- **DoD:** Adapters normalize to **Phase-1 internal schema**.

#### **Subphase 4.3 — Watchers & Auto-PRs**
- **P4.3.1 Watchers** → `regulatory_os/watchers/{gst, itd, eway, apisetu}.py` (mock feeds); diffs → auto-PR artifact & updated packs.

#### **Subphase 4.4 — Security/Residency & (Optional) GraphQL**
- **P4.4.1 Security/Privacy & Data Residency** → `helpers/pii_redaction.py`, `helpers/security.py`, encryption at rest, region pinning; SBOM in CI.  
- **P4.4.2 GraphQL Surface** (enable **only** if MASTER mandates) → `surfaces/graphql/{schema.py,resolvers.py}`, tests; parity with REST/MCP.

> **Phase-4 Exit:** Adapters contract-green; connectors pass consent/redaction; watchers generate diffs; security/residency green; GraphQL parity (if required) green.

---

### **Phase 5 — Launch & Run**

#### **Subphase 5.1 — E2E & SLOs**
- **P5.1.1 Rehearsal, canaries, rollback drills** → runbook execution; rollback verified; SLOs green.

#### **Subphase 5.2 — Final Cross-Phase Release Gates (HARD)**
- **P5.2.1 MCP method/stream contracts** → `/mcp/search` **POST**, `/mcp/fetch` **POST**, `/mcp/stream` SSE pass.  
- **P5.2.2 Surfaces parity** → `/api/execute`, **/sse**, **/webhooks**, **/cli** parity vs MCP for sampled plans.  
- **P5.2.3 Byte-Identical Replay Gate (NEW)** → `tests/golden/test_replay_consistency.py` must pass for closed periods.  
- **P5.2.4 Release gates job** depends on `parity`, `e2e`, `replay`, `perf_baseline`. **Any red → no release.**  
- **P5.2.5 Ratio covenant parity & perf gates (NEW in V9)**  
  - **Why:** Ensure **MCP vs REST** parity for ratio simulations; enforce p95 latency budgets for JE-time checks; track breach & near-breach counts.  
  - **Artifacts:** CI assertions for `ratio_sim_latency_ms`, `ratio_breach_count`, `near_breach_count`, parity snapshot tests.  
  - **DoD:** CI fails on perf regression or parity drift.

#### **Subphase 5.3 — Go/No-Go**
- **P5.3.1 Final checklist** → zero high/critical vulns; evidence coverage ≥90%; sign-off recorded.

---

## 5) Phase Catalog (illustrative entries; apply template to all)

- **P1.2.1 Contract dataclasses & schema hash snapshots**
  - **Why:** Lock contracts for all phases.  
  - **Inputs:** None.  
  - **Steps:** Implement `surfaces/contracts.py`; add `tests/contract/test_contract_shapes.py` snapshot suite.  
  - **Artifacts:** `surfaces/contracts.py`, `tests/contract/test_contract_shapes.py`.  
  - **DoD:** Snapshot diffs fail CI.  
  - **Acceptance:** Contract hashes stable across runs.  
  - **Traceability:** MASTER Surfaces/Protocol; Golden Rules 2–3.

- **P2.5.1 Evidence Replay (Closed-Period Byte-Identical) [COMPLETED — 2025-08-18]**
  - **Why:** Deterministic governance for real audits.  
  - **Inputs:** Evidence OS base; Regulatory loader.  
  - **Steps:** Implement `evidence/replay.py`; add fixtures; make golden E2E.  
  - **Artifacts:** `tools/hash_utils.py`, `tools/replay_runner.py`, `tests/replay/**` (fixtures + tests), CI workflow job `replay_golden`.  
  - **DoD:** Frozen inputs + packs → **byte-identical** outputs.  
  - **Acceptance:** `replay_golden` CI stage green.  
  - **Traceability:** MASTER Evidence/Replay.

- **P2.2.1 (L-231) Ratio Impact Advisor — Deterministic Implementation (NEW in V9)**
  - **Why:** JE-time covenant protection with deterministic simulation and advisory suggestions.  
  - **Inputs:** `/helpers/ratios.py`, `/configs/bank_covenants.yaml`, `/configs/ratio_targets.yaml`, TB fetch functions.  
  - **Steps:** Implement before/after ratio computation, covenant mapping, breach/near-breach detection, advisory generator under accounting validations, evidence attachments (TB hashes, JE hash, covenant profile hash).  
  - **Artifacts:** `logics/logic_231_ratio_impact_advisor.py`, tests (`unit`, `contract`, `performance`).  
  - **DoD:** All tests pass; metrics emitted; parity smoke includes L-231; CI perf budget respected.

---

## 6) Traceability Matrix (Machine-Generated)
> **Run:** `python tools/gen_traceability.py > docs/traceability_matrix.md` (CI job `traceability`)  
> CI fails if coverage < 100% of MASTER or any item maps to no Task ID.

| MASTER ID | Title/Excerpt | Task IDs | Phase | Repo Status (DONE/STUB/MISSING) | Notes |
|---|---|---|---|---|---|
| Surfaces | Non-MCP (REST/SSE/webhooks/CLI) + anchors | P1.2.1–P1.2.5, P5.2.2 | 1,5 | MISSING→DONE | Hash snapshots enforce parity |
| Orchestration | DAG + Discovery | P2.1.1–P2.1.3 | 2 | PARTIAL→DONE | discovery==**231** |
| Auto-Expansion | Contracts→Live | P2.3.1, P3.3.1 | 2–3 | NEW→DONE | Guard-railed |
| Regulatory OS | Loader+DSL+Adapters+Watchers | P1.3.2, P3.2.1, P4.2.*, P4.3.1 | 1,3–4 | MISSING→DONE | Goldens |
| Evidence | Ledger/Blob/Signer + Replay | P1.3.1, P2.5.1, P5.2.3 | 1,2,5 | NEW→DONE | Byte-identical gate incl. JE sims |
| Intelligence | Reverse+Anomaly+Mediator | P3.1.*, P3.2.*, P3.4.* | 3 | NEW→DONE | Cross-phase E2E |
| Perf/SLO | Cache+Budgets+Perf gates | P2.4.1, P5.1.1, **P5.2.5** | 2,5 | NEW→DONE | CI perf for ratios |
| 001–231 | Logic coverage | P1.5.*, P2.2.1–2, **P2.2.4** | 1–2 | PARTIAL→DONE | **231/231** + JE orchestrator (opt.)

---

## 7) Dependency Audit (Machine-Generated)
> **Run:** `python tools/gen_dependency_audit.py > docs/dependency_audit.md` (CI job `dependency_audit`)  
> CI fails if any task references a **later** task.

| Task ID | Inputs/Prereqs | Audit |
|---|---|---|
| P1.5.3 | P1.5.1, P1.5.2, P1.2.1 | ✅ same/earlier |
| P2.2.1 | P1.5.3, P2.1.1 | ✅ same/earlier |
| P2.2.4 | P1.5.3, P2.1.*, P2.2.1 | ✅ same/earlier |
| P3.4.5 | P1.2.*, P2.2.*, P2.1.* | ✅ same/earlier |
| P5.2.5 | P2.5.1, P2.2.1, P2.2.4 | ✅ same/earlier |

---

## 8) Quality Gates Per Phase
- **P1:** lint/type/unit/**contract/golden** + `id_policy` + `master_index_check` (==**231**) + `repo_inventory_check` + `logic_coverage_gate` (**231/231**) + `l4_readiness_gate` + `traceability` + `dependency_audit` + **parity_smoke(restricted)** + **replay_golden(stub)** + **perf_baseline(stub)**.  
- **P2:** DAG/discovery tests (**231**), **parity_smoke**, **replay_golden**, **perf_baseline**; L-231 implementation tests; (opt.) transaction orchestrator tests.  
- **P3:** learning/anomaly determinism + **compat E2E** + auto-exp live (guard-railed) + **ratio learning loop** active.  
- **P4:** adapter goldens + connector contracts + security/residency.  
- **P5:** MCP **POST/SSE** & surfaces parity + **byte-identical replay gate** + E2E rehearsal + rollback + **ratio parity/perf gates**.

---

## 9) Launch Readiness Checklist (must be **true**)
- [ ] Phases **1→5** completed **once**; no TODOs.  
- [ ] **231/231** logic modules present & discoverable; contract-green; L4 hooks present.  
- [ ] L-231 Ratio Advisor implemented with covenant configs & helpers; evidence nodes present (TB before/after, JE hash, covenant hash).  
- [ ] (Optional) Transaction posting orchestrator tested with policy gate.  
- [ ] MCP `/mcp/search` **POST**, `/mcp/fetch` **POST`, `/mcp/stream` SSE pass; **parity** across REST/**SSE**/**webhooks**/**CLI** including L-231 flows.  
- [ ] **Byte-identical replay** for closed periods includes JE delta scenarios; evidence coverage ≥90%.  
- [ ] SLO dashboards green; **zero high/critical** vulns; rollback drill passed; ratio perf budgets respected.

---

## 10) Scripts To Add (turns plan into guarantees)
- `tools/extract_master_index.py` — parse MASTER → `artifacts/master_index.json` (**exactly 231**).  
- `tools/scan_repo_logics.py` — enumerate `logics/logic_###_*.py` → `artifacts/repo_logics.json`.  
- `tools/gen_missing_logics.py` — create **all missing** stubs/tests (uses `logics/common/l4_base.py`).  
- `tools/audit_l4_readiness.py` — verify L4 hooks across all logics.  
- `tools/gen_traceability.py` — emit exhaustive matrix 1…231 with Task IDs + repo status.  
- `tools/gen_dependency_audit.py` — build task graph from this file; fail on forward edges.  
- `tools/lint_id_policy.py` — enforce ID range/uniqueness & slug hygiene.  
- `tools/slo_scan.py` — validate budgets/alerts exist.  
- (Optional) `scripts/sbom_generator.py`, `scripts/license_checker.py`.  
- `tools/ratios_testgen.py` — generate fixtures for JE-time ratio simulations & covenant profiles.

---

## 11) Sanity Checks (gates for merging THIS file)
- [ ] Non-MCP surfaces present from **Phase 1**; MCP already in `main.py`.  
- [ ] **231/231** logic modules guaranteed in **Phase 1** (no “add later”).  
- [ ] Cross-phase anchors, parity smokes, compat E2E, replay & perf baselines are defined and **gated**.  
- [ ] No forward dependencies; dependency audit clean.  
- [ ] One-pass execution guaranteed by CI.

---

## Appendix A — Explicit Catalog for **logic_201…231** (from MASTER, for reviewer clarity)
> **Note:** Creation of these files happens in **P1.5.3** (Phase-1), not later. Names retained from prior plan for clarity.  
> (V9 adds the final entry for L-231 to complete **231/231** coverage.)

- `logic_201_regulatory_watcher_cbic_circulars_gst.py`  
- `logic_202_regulatory_watcher_cbdt_circulars_itd.py`  
- `logic_203_regulatory_watcher_gstn_irp_schema_changes.py`  
- `logic_204_regulatory_watcher_eway_bill_api_changes.py`  
- `logic_205_api_setu_subscription_manager_pan_kyc.py`  
- `logic_206_gstr1_books_reconciliation_line_level.py`  
- `logic_207_gstr2b_itc_books_aging_eligibility.py`  
- `logic_208_einvoice_sales_register_consistency.py`  
- `logic_209_eway_bill_delivery_inventory_movement_match.py`  
- `logic_210_26as_books_tds_map_payer_payee_sections.py`  
- `logic_211_ais_tis_mapper_to_ledgers_with_confidence.py`  
- `logic_212_cross_company_related_party_detector_mca_books.py`  
- `logic_213_aa_bank_statement_books_reconciliation.py`  
- `logic_214_effective_date_rule_evaluator_multi_period_recompute.py`  
- `logic_215_evidence_coverage_scorer.py`  
- `logic_216_consent_compliance_auditor_scope_expiry.py`  
- `logic_217_filing_calendar_synthesizer_auto_updated_from_circulars.py`  
- `logic_218_regulatory_impact_simulator_what_if.py`  
- `logic_219_audit_bundle_generator_rules_evidence_outputs.py`  
- `logic_220_enforcement_guard_fail_closed_on_invalid_pack.py`  
- `logic_221_supplier_risk_heatmap_gstr_performance_disputes.py`  
- `logic_222_itc_eligibility_classifier_rule_based_evidence.py`  
- `logic_223_tds_section_classifier_deterministic_with_proofs.py`  
- `logic_224_inventory_to_eway_reconciliation_gaps.py`  
- `logic_225_einvoice_cancellation_amendment_auditor.py`  
- `logic_226_bank_to_revenue_corroboration_aa_invoices.py`  
- `logic_227_gstin_pan_consistency_checker_api_setu.py`  
- `logic_228_ledger_drift_detector_books_vs_filings.py`  
- `logic_229_evidence_freshness_monitor.py`  
- `logic_230_regulatory_delta_explainer.py`  
- `logic_231_ratio_impact_advisor.py`


> Each follows the **Phase-1 L4 contract** and has a dedicated contract/unit test.

---

**End of `new_tasks.md` (V9)**
