# new_tasks.md — Forward-Only, One-Pass Plan (V4 Compliance)

## 0. Front Matter
- Document Purpose: Replace prior plan with a complete, dependency-safe, forward-only execution plan that brings this repo to full compliance with MASTER_SCOPE_OF_WORK.md (V4) in one pass of Phases 1–5.
- Version: 2025-08-15 (Asia/Kolkata)
- Owner: Hardy
- Change Log:
  - 2025-08-15: Full rewrite to align with MASTER_SCOPE_OF_WORK.md V4 and current repo audit; reorganized into five forward-only phases; added traceability and dependency audit.

---

## 1. Plan Overview

- Scope Summary: Build an MCP-ready and MCP-independent backend for autonomous, evidence-backed accounting and compliance. Deterministic-first logic modules (200 existing + 30 regulatory/evidence intelligence to add), Evidence OS (WORM ledger and content-addressed artifacts), Regulatory OS (rule packs + DSL + effective dates), orchestrators, consent-bound connectors, robust observability and SLOs, security/privacy controls, and surfaces (/mcp/*, /api/execute, optional GraphQL/CLI). The repo already has 200 logic modules, MCP endpoints, orchestrators, and many helpers; gaps include Evidence OS, full Regulatory OS, connectors, consent enforcement, /api/execute, observability scaffolding, and 201–230 logic set.
- Phase Map (1–5):
  - Phase 1: Foundations & zero-dependency enablers (scaffolds, contracts, offline tests, minimal surfaces).
  - Phase 2: Core functional logic upgrades (determinism enforcement, rule-pack routing, orchestrator compliance, caching, flags).
  - Phase 3: Intelligence & learning (reverse-learning upgrades, DSL compiler, anomaly engines, evidence coverage scorer) — offline fixtures only.
  - Phase 4: UX, integrations, and hardening (connectors, consent enforcement, security, watchers, GraphQL, dashboards hardening).
  - Phase 5: Launch & Run (E2E tests, performance/security gates, final readiness, rollback playbooks).
- No-Dependency Declaration: No task in this plan depends on a later phase. All enabling scaffolds required by later work are introduced in Phase 1. Each subphase is independently executable to Definition of Done.

---

## 2. Global Conventions

- Task ID Scheme: `P{phase}.{subphase}.{index}` (e.g., `P1.2.3`).
- Uniform Task Fields:
  - Title
  - Why (Outcome/Rationale)
  - Inputs/Prereqs (must already exist in same/earlier phase)
  - Steps (One-Pass)
  - Artifacts/Deliverables (with repo path)
  - Definition of Done (DoD)
  - Acceptance Criteria (Testable)
  - Owner/Role
  - Duration (estimate)
  - Risk & Mitigation
  - Assumptions/Decisions Logged
  - Traceability (Scope IDs from MASTER)

---

## 3. Dependency Guardrails

- Enabler Rule: If a task needs a missing logic/config/integration, the enabler is pulled into Phase 1.
- Backward-Only: Every dependency points backward (≤ current phase) or within the same subphase.
- Offline-First: Phases 1–3 do not require external network/APIs; fixtures and stubs only.

Dependency Audit Table (summary):
- Phase 1 subphases (1.1–1.8) have zero external deps; only file system and Python runtime.
- Phase 2 relies only on Phase 1 scaffolds (Evidence OS, Regulatory OS base, surfaces contracts, schema registry completeness, feature flags, cache helper).
- Phase 3 relies on Phase 1–2 artifacts; uses only local fixtures for learning, DSL compilation, and anomaly tests.
- Phase 4 brings external connectors and watchers; depends on Phase 1–3 scaffolds and tests, no forward references.
- Phase 5 depends on completed artifacts from Phases 1–4; no new feature build.

---

## 4. Phases (1–5)

### Phase 1 — Foundations & Zero-Dependency Enablers
- Create scaffolds: Evidence OS, Regulatory OS base, surfaces contracts (/api/execute), observability skeleton, cache & feature flags helpers, consent schema, CI minimally.
- Align `core.logic_loader` and MCP routes; ensure loaders/registry exports and dynamic year/token handling are correct.
- Developer runbooks and a non-prod “Hello, Production” local smoke.

### Phase 2 — Core Functional Logic
- Enforce deterministic-first logic contract across 1–200.
- Route regulatory logics through `run_rule_pack()`. 
- Orchestrator compliance: applied_rule_set merge, completeness scores.
- Deterministic caching, feature flags, schema registry completeness.

### Phase 3 — Intelligence, Self-Learning, and Anomaly Detection
- Upgrade reverse-learning to MASTER flow; add evidence coverage scorer; expand anomaly engines using offline fixtures; implement DSL compiler end-to-end (no external services needed).

### Phase 4 — UX, Integrations, and Hardening
- Implement consent-bound connectors (GSTN, IRP, E-Way Bill, TRACES, API Setu, AA, MCA).
- Security/privacy, PII redaction, data residency, SBOM, CI security gates.
- Regulatory Watchers (CBIC/CBDT/GSTN/E-Way/API Setu) and GraphQL surface.
- Dashboards hardening and SLO alerting.

### Phase 5 — Launch & Run
- E2E, performance, security validations; cross-phase compatibility tests; final readiness checklist and rollback.

---

## 5. Phase Catalog (Detailed Tasks)

### Phase 1 — Foundations & Zero-Dependency Enablers

#### P1.1.1 — Evidence OS: Package Scaffolding
- Why: Provide WORM ledger and content-addressed artifact store required by MASTER (5) without external deps.
- Inputs/Prereqs: Python runtime; repo write access.
- Steps:
  1) Create `evidence/__init__.py`, `evidence/ledger.py`, `evidence/blob_store.py`, `evidence/signer.py`.
  2) Implement local hash-chained ledger with Merkle roots; local filesystem blob store (SHA256); signer no-op with pluggable hook.
  3) Add unit tests under `tests/unit/evidence/` with fixtures.
- Artifacts/Deliverables: `evidence/*`, `tests/unit/evidence/*`.
- DoD: All new tests pass locally; simple write/read/merkle-root verified with fixture.
- Acceptance: `pytest -q tests/unit/evidence | cat` green; functions imported in a sample logic without runtime error.
- Owner/Role: Backend Engineer.
- Duration: 0.5–1 day.
- Risk: Incorrect persistence paths; Mitigation: tmpdirs + config.
- Assumptions: Local FS acceptable in dev.
- Traceability: MASTER 5, 10, 16.

#### P1.1.2 — Evidence Contract Wiring Helpers
- Why: Simplify attaching evidence from logics/orchestrators.
- Inputs: P1.1.1.
- Steps: Add `evidence/helpers.py` with `attach_evidence(payload, sources)` thin wrapper; validate schema.
- Artifacts: `evidence/helpers.py`.
- DoD: Wrapper imported by a sample logic and returns deterministic handles.
- Acceptance: Unit test proves stable handle scheme.
- Owner: Backend Engineer.
- Duration: 0.5 day.
- Risk: Handle collisions; Mitigation: include content-hash + source keys.
- Traceability: MASTER 5.

#### P1.2.1 — Regulatory OS: Base Layout & Runner Stub
- Why: Enable phase-2 routing of regulatory logics through rule packs, offline-only.
- Inputs: None.
- Steps:
  1) Create `regulatory_os/__init__.py`, `regulatory_os/rule_engine.py` with `run_rule_pack(reg, inputs, context)` stub returning deterministic fixture outputs.
  2) Create `regulatory_os/fixtures/*` and sample packs `rule_packs/gst@2025-08.json`, `itd@2025-08.json`.
  3) Add golden tests scaffolds under `regulatory_os/golden_tests/` (fixtures only; compilation later in Phase 3).
- Artifacts: `regulatory_os/*`.
- DoD: Golden tests skeletons run and skip if no compiler (marked xfail), runner stub returns fixture outputs.
- Acceptance: `pytest -q regulatory_os/golden_tests | cat` collects; skip marks visible.
- Owner: Backend Engineer.
- Duration: 1 day.
- Risk: Overcoupling to future DSL; Mitigation: thin runner API.
- Traceability: MASTER 6, 10, 15.

#### P1.3.1 — Surfaces: /api/execute Contract & Router
- Why: MCP-independent surface parity per MASTER 11.
- Inputs: main FastAPI app.
- Steps: Implement `/api/execute` in `main.py` mirroring MCP contracts (single logic or orchestrated execution) using loaded handlers; no external calls required.
- Artifacts: `main.py` (route), optional `surfaces/contracts.py` for schemas.
- DoD: Local request returns the same contract keys as MCP path.
- Acceptance: New `tests/integration/test_api_execute.py` passes.
- Owner: Backend Engineer.
- Duration: 0.5 day.
- Risk: Divergence with MCP; Mitigation: shared contract schema.
- Traceability: MASTER 11.

#### P1.3.2 — OpenAPI Seed
- Why: Document surfaces.
- Inputs: P1.3.1.
- Steps: Add minimal `surfaces/openapi.yaml` reflecting `/api/execute` request/response.
- Artifacts: `surfaces/openapi.yaml`.
- DoD: File parsable by Swagger editor.
- Acceptance: CI lint for YAML (basic schema) passes.
- Owner: Backend Engineer.
- Duration: 0.25 day.
- Risk: Spec drift; Mitigation: shared types.
- Traceability: MASTER 11.

#### P1.4.1 — Observability Skeleton & Budgets
- Why: SLO governance per MASTER 9 & 14.
- Inputs: None.
- Steps: Create `observability/` with `budgets.yaml`, `prometheus/rules.yaml`, and link existing dashboards (`dashboards/*.json`) or copy baselines into `observability/dashboards/`.
- Artifacts: `observability/*`.
- DoD: Budgets define p95/p99 per critical logics; rules file includes MWMBR and latency alerts.
- Acceptance: `tools/slo_scan.py` reads budgets; sample alert rule passes linter.
- Owner: SRE/Backend.
- Duration: 0.5 day.
- Risk: Duplicate dashboard locations; Mitigation: symlink or reference.
- Traceability: MASTER 9, 14.

#### P1.5.1 — Core Enablers: Feature Flags & Cache
- Why: Needed by orchestrators and deterministic performance (MASTER 13, 14).
- Inputs: None.
- Steps: Add `helpers/feature_flags.py` (env/file backed) and `helpers/cache.py` (memory TTL + key hashing by inputs/pack/version).
- Artifacts: `helpers/feature_flags.py`, `helpers/cache.py`.
- DoD: Unit tests cover enable/disable and cache set/get/ttl.
- Acceptance: `pytest -q tests/unit/helpers | cat` green.
- Owner: Backend Engineer.
- Duration: 0.5 day.
- Risk: Cache key errors; Mitigation: typed helpers + tests.
- Traceability: MASTER 13, 14.

#### P1.5.2 — Consent Object Schema
- Why: Prepare consent enforcement without external deps.
- Inputs: None.
- Steps: Add `helpers/consent.py` with schema validation and test fixtures.
- Artifacts: `helpers/consent.py`, `tests/unit/helpers/test_consent.py`.
- DoD: Valid/invalid consent objects validated deterministically.
- Acceptance: Unit tests pass.
- Owner: Backend Engineer.
- Duration: 0.5 day.
- Risk: Schema churn; Mitigation: anchor to MASTER sample.
- Traceability: MASTER 7, 8.

#### P1.6.1 — Loader & MCP Alignment (Planner/Registry)
- Why: Ensure planning/execution paths are stable.
- Inputs: `core/logic_loader.py`, `main.py`.
- Steps: Verify `load_all_logics`, `plan_from_query`, `LOGIC_REGISTRY` exports; `_REGISTRY` import in `main.py` occurs once; dynamic year detection and form-encoded token refresh in place; add unit tests.
- Artifacts: `tests/unit/core/test_logic_loader.py`, `tests/unit/test_main_contracts.py`.
- DoD: Tests cover planner and token refresh behavior.
- Acceptance: All tests pass.
- Owner: Backend Engineer.
- Duration: 0.5 day.
- Risk: Flaky discovery; Mitigation: deterministic mocks.
- Traceability: MASTER 11, 13.

#### P1.7.1 — CI Seed & Pre-commit
- Why: Keep changes safe.
- Inputs: None.
- Steps: Add basic CI config (lint + unit) and pre-commit hooks (black/ruff/mypy/bandit minimal).
- Artifacts: `.github/workflows/ci.yml`, `.pre-commit-config.yaml`.
- DoD: CI runs lint + unit tests.
- Acceptance: CI green on branch.
- Owner: SRE/Backend.
- Duration: 0.5 day.
- Risk: Env drift; Mitigation: pin tool versions.
- Traceability: MASTER 13, 10.

#### P1.8.1 — Dev Runbook & Local Smoke
- Why: One-pass validation of scaffolds.
- Inputs: All P1 tasks.
- Steps: Add `docs/runbooks/dev_smoke.md`; create `scripts/mcp_smoke.py` usage + `/api/execute` smoke.
- Artifacts: `docs/runbooks/dev_smoke.md`.
- DoD: Local smoke returns contract-consistent outputs.
- Acceptance: Maintainer runs smoke successfully.
- Owner: Backend.
- Duration: 0.25 day.
- Risk: OS differences; Mitigation: document macOS/Linux notes.
- Traceability: MASTER 11, 13.

---

### Phase 2 — Core Functional Logic

#### P2.1.1 — Logic Contract Compliance Audit (L-001…L-200)
- Why: Enforce deterministic-first, evidence-ready contract.
- Inputs: P1.1–P1.6.
- Steps: For each logic 1–200, verify contract keys, schema validation via `helpers/schema_registry.py`, add confidence scoring via `helpers/learning_hooks.py` where missing, and ensure alert structure. Add minimal evidence attach using P1.1.2.
- Artifacts: Per-logic edits; test augmentations under `tests/unit/logic_*/`.
- DoD: 100% of 1–200 validated; tests green.
- Acceptance: `tools/verify_contract_compliance.py` (existing) passes for all.
- Owner: Backend Engineer(s).
- Duration: 2–3 days (parallelizable).
- Risk: Breakage in edge logics; Mitigation: incremental commits + tests.
- Traceability: MASTER 2, 3, 10, 16.

#### P2.2.1 — Regulatory Pack Routing (Targeted IDs)
- Why: Route regulatory logics through `run_rule_pack()` per MASTER Migration.
- Inputs: P1.2.1.
- Steps: Update logics: 16, 17, 39–41, 84, 85, 195 to call `run_rule_pack()`; attach `applied_rule_set`.
- Artifacts: Edits to those logic files; golden fixtures referenced (local).
- DoD: Unit/integration tests for these IDs pass.
- Acceptance: `tests/integration/test_orchestrators.py` validates merged applied_rule_set.
- Owner: Backend Engineer.
- Duration: 1–2 days.
- Risk: Behavior drift; Mitigation: fixture-backed expected outputs.
- Traceability: MASTER 6, 15.

#### P2.3.1 — Orchestrator Compliance
- Why: Many-to-one with completeness and applied packs.
- Inputs: P1.5.1, P2.2.1.
- Steps: Ensure `orchestrators/mis_orchestrator.py` and `generic_report_orchestrator.py` merge alerts, compute completeness, and merge `applied_rule_set` from child logics; add feature-flag gating per logic.
- Artifacts: Orchestrator edits; tests under `tests/integration/`.
- DoD: MIS run returns required fields; feature flags respected.
- Acceptance: Existing MIS tests + new assertions pass.
- Owner: Backend Engineer.
- Duration: 1 day.
- Risk: Ordering effects; Mitigation: deterministic LOGIC_ORDER + tags.
- Traceability: MASTER 3, 7, 9.

#### P2.4.1 — Deterministic Cache Adoption
- Why: Cost & latency guardrails.
- Inputs: P1.5.1.
- Steps: Introduce deterministic keys `(logic_id, org_id, period, pack_versions)` to selected high-traffic logics (top 10), then expand.
- Artifacts: Edits in logics; unit timers + cache hit tests.
- DoD: Cache hit rates measurable in tests.
- Acceptance: Performance test budget for those logics met.
- Owner: Backend.
- Duration: 1 day.
- Risk: Stale cache; Mitigation: invalidate on pack version change.
- Traceability: MASTER 14.

#### P2.5.1 — Schema Registry Completeness
- Why: Ensure every logic ID registered with default schemas.
- Inputs: helpers/schema_registry.py.
- Steps: Call `ensure_all_logic_defaults()` (already in loader) and add missing schema stubs for uncovered IDs.
- Artifacts: `helpers/schema_registry.py` updates; `data/format_schemas.json` align.
- DoD: No missing schema warnings at load.
- Acceptance: Loader test validates coverage.
- Owner: Backend.
- Duration: 0.5 day.
- Risk: Schema drift; Mitigation: version templates.
- Traceability: MASTER 2, 10.

#### P2.6.1 — /api/execute Integration Tests
- Why: Guarantee surface parity.
- Inputs: P1.3.1.
- Steps: Add integration tests executing both MCP and `/api/execute` and asserting contract parity for a sample plan and logic.
- Artifacts: `tests/integration/test_surface_parity.py`.
- DoD: Tests pass locally.
- Acceptance: CI green.
- Owner: QA/Backend.
- Duration: 0.5 day.
- Risk: Minor diffs; Mitigation: shared serializer.
- Traceability: MASTER 11, 10.

---

### Phase 3 — Intelligence, Self-Learning, and Anomaly Detection

#### P3.1.1 — Reverse-Learning Pipeline Upgrade
- Why: Align to MASTER steps (extract → map → provenance → schema → verify → auto-enable).
- Inputs: Existing `helpers/pdf_extractor.py`, `docs/learned_formats/`, `generic_report_orchestrator.py`.
- Steps: Extend pipeline to persist provenance mapping and auto-register learned schema in `schema_registry`; add verification steps with subtotal reconciliation.
- Artifacts: `helpers/schema_registry.py` updates; orchestrator enhancements; tests `tests/integration/test_reverse_learning_minimal.py` expanded.
- DoD: New learned format re-generates deterministically.
- Acceptance: Test proves end-to-end learned reproduction.
- Owner: Backend.
- Duration: 1 day.
- Risk: Noisy PDFs; Mitigation: fixture-based tests.
- Traceability: MASTER 4.

#### P3.2.1 — DSL Compiler (Offline)
- Why: Compile rule packs to deterministic code paths without external calls.
- Inputs: P1.2.1.
- Steps: Implement `regulatory_os/dsl/{grammar.py,compiler.py}` and unit tests; update `rule_engine.py` to use compiler.
- Artifacts: `regulatory_os/dsl/*`, tests.
- DoD: Golden tests for gst@2025-08 and itd@2025-08 pass with fixtures.
- Acceptance: `pytest -q regulatory_os/golden_tests | cat` green.
- Owner: Backend.
- Duration: 1–2 days.
- Risk: Grammar complexity; Mitigation: MVP grammar + fixtures.
- Traceability: MASTER 6, 15.

#### P3.3.1 — Evidence Coverage Scorer (Logic 215)
- Why: Track ≥90% coverage target.
- Inputs: P1.1–P1.2.
- Steps: Implement `logics/logic_215_evidence_coverage_scorer.py`; add orchestrator hook to compute coverage.
- Artifacts: new logic file; tests.
- DoD: Coverage computed for MIS sections.
- Acceptance: Integration test asserts ≥90% on fixtures.
- Owner: Backend.
- Duration: 0.5 day.
- Risk: Counting method; Mitigation: clear contract.
- Traceability: MASTER 5, 9, 16 (IDs 215 explicitly).

#### P3.4.1 — Anomaly/Pattern Engines Upgrade
- Why: Enhance pattern-based detections per MASTER categories.
- Inputs: `helpers/anomaly_detector.py`, `helpers/pattern_detector.py`.
- Steps: Add offline fixtures and strengthen thresholds (p95/p99) with configurable budgets; wire alerts taxonomy.
- Artifacts: tests under `tests/unit/helpers/` and selected logic updates (75–94, 196).
- DoD: Pattern logics emit structured alerts deterministically.
- Acceptance: Unit tests cover edge scenarios without network.
- Owner: Backend.
- Duration: 1 day.
- Risk: Flaky thresholds; Mitigation: seeded fixtures.
- Traceability: MASTER 9, 12, 14; Logic IDs 75–94, 196.

---

### Phase 4 — UX, Integrations, and Hardening

#### P4.1.1 — Connectors (Consent-Bound)
- Why: MCP-independent data acquisition with lawful basis and consent.
- Inputs: P1.5.2.
- Steps: Create `/connectors/` clients: `gsp_gst_client.py`, `irp_einvoice_client.py`, `ewaybill_client.py`, `itd_traces_client.py`, `apisetu_client.py`, `aa_client.py`, `mca_client.py`; add consent validation at entry; implement retries, backoff, and rate limits; redact PII from logs.
- Artifacts: `connectors/*`, tests `tests/contract/test_connectors.py`.
- DoD: Contract tests pass with mocked HTTP.
- Acceptance: No network in tests; all mocks verified.
- Owner: Backend.
- Duration: 3–4 days (parallelizable).
- Risk: API changes; Mitigation: adapters + versioned contracts.
- Traceability: MASTER 7, 8, 10.

#### P4.1.2 — Consent Compliance Auditor (Logic 216)
- Why: Enforce consent scope/expiry across pipelines.
- Inputs: P1.5.2.
- Steps: Implement `logics/logic_216_consent_compliance_auditor.py`; add hooks in connectors/orchestrators.
- Artifacts: logic + tests.
- DoD: Violations produce alerts; passes valid scenarios.
- Acceptance: Contract tests cover edge cases.
- Owner: Backend.
- Duration: 0.5 day.
- Risk: Overblocking; Mitigation: clear severities.
- Traceability: MASTER 7 (ID 216 explicitly).

#### P4.2.1 — Security/Privacy & Data Residency
- Why: Zero-trust & compliance.
- Inputs: Observability skeleton, connectors.
- Steps: Add `helpers/pii_redaction.py`, `helpers/security.py`; integrate encryption-at-rest options for evidence/blob store; region pinning configs; SBOM generation script.
- Artifacts: helpers + configs + `scripts/sbom_generator.py`.
- DoD: PII never logged; SBOM generated; encryption toggles documented.
- Acceptance: Security tests pass; bandit and license checks green.
- Owner: Security/Backend.
- Duration: 1–2 days.
- Risk: Perf hit; Mitigation: feature flags.
- Traceability: MASTER 8, 10.

#### P4.3.1 — Regulatory Watchers
- Why: Auto-detect rule changes and open PRs.
- Inputs: P3.2.1 DSL/compiler; packs directory.
- Steps: Implement watchers under `regulatory_os/watchers/` for CBIC/CBDT/GSTN/E-Way/API Setu; mock feeds for tests; PR summaries as JSON files in CI artifacts.
- Artifacts: watchers + tests.
- DoD: On fixture change, watcher opens a diff artifact and updates pack file.
- Acceptance: Integration test simulates change and asserts artifact.
- Owner: Backend.
- Duration: 2 days.
- Risk: Source variability; Mitigation: adapters + optional feeds.
- Traceability: MASTER 6.

#### P4.4.1 — GraphQL Surface (Optional but First-Class per MASTER)
- Why: Alternate surface with contract parity.
- Inputs: P1.3.1.
- Steps: Add `surfaces/graphql/{schema.py,resolvers.py}`; mirror `/api/execute` behavior.
- Artifacts: GraphQL server files + tests.
- DoD: Query executes plan and returns contract-compliant output.
- Acceptance: Test parity with REST.
- Owner: Backend.
- Duration: 1 day.
- Risk: Divergent types; Mitigation: shared models.
- Traceability: MASTER 11.

#### P4.5.1 — Dashboards & Alerts Hardening
- Why: Production SLOs and runbooks.
- Inputs: P1.4.1.
- Steps: Finalize dashboards under `observability/dashboards/`; add runbooks for latency, dependency health, evidence coverage; wire alert policies.
- Artifacts: dashboards + runbooks.
- DoD: Dashboards render and alerts can be simulated.
- Acceptance: Dry-run tooling validates rules.
- Owner: SRE.
- Duration: 0.5–1 day.
- Risk: Noise; Mitigation: tuned thresholds.
- Traceability: MASTER 9.

---

### Phase 5 — Launch & Run

#### P5.1.1 — E2E & Compatibility
- Why: Validate cross-phase compatibility without backtracking.
- Inputs: All prior phases complete.
- Steps: E2E tests covering MIS, regulatory packs, evidence coverage, consent, and surfaces parity.
- Artifacts: `tests/e2e/test_full_workflow.py`.
- DoD: All E2E tests green locally and in CI.
- Acceptance: CI green with required stages.
- Owner: QA/Backend.
- Duration: 1 day.
- Risk: Flaky tests; Mitigation: deterministic fixtures.
- Traceability: MASTER 10, 16.

#### P5.1.2 — Performance & Security Gates
- Why: Enforce budgets and security posture.
- Inputs: Observability budgets, SBOM, security checks.
- Steps: Run load tests, finalize budgets, enable CI gates for latency and security.
- Artifacts: `tests/performance/*`, CI configs.
- DoD: p95/p99 within budgets; zero high/critical vulns.
- Acceptance: Pipelines enforce gates.
- Owner: SRE/Sec/Backend.
- Duration: 1 day.
- Risk: Budget misses; Mitigation: tune caches/flags.
- Traceability: MASTER 9, 14, 10.

#### P5.1.3 — Final Readiness & Rollback
- Why: Safe launch.
- Inputs: All artifacts.
- Steps: Complete final checklist; document rollback; tag release; update CHANGELOG.
- Artifacts: `docs/runbooks/launch_checklist.md`, CHANGELOG update.
- DoD: Checklist complete; release cut.
- Acceptance: Sign-off by owner.
- Owner: Owner/Lead.
- Duration: 0.5 day.
- Risk: Unknowns; Mitigation: canary plan.
- Traceability: MASTER 13, 16.

---

## 6. Traceability Matrix

Note: IDs map to grouped tasks where logically identical upgrades apply across ranges; targeted IDs called out explicitly. All groups are fully covered by Phase ≤ group’s tasks.

| MASTER Scope ID(s) | Scope Title/Excerpt | Task IDs | Phase | Notes |
|---|---|---|---|---|
| 5 | Evidence OS | P1.1.1, P1.1.2, P3.3.1 | 1,3 | Ledger, blob, signer, coverage scorer |
| 6 | Regulatory OS (packs/DSL) | P1.2.1, P2.2.1, P3.2.1, P4.3.1 | 1–4 | Base → routing → compiler → watchers |
| 7,8 | Connectors/Consent/Compliance | P1.5.2, P4.1.1, P4.1.2 | 1,4 | Schema → clients → auditor (216) |
| 9,14 | Observability & Budgets | P1.4.1, P4.5.1, P5.1.2 | 1,4,5 | Budgets, dashboards, gates |
| 10 | Testing & Governance | P1.7.1, P2.6.1, P5.1.1 | 1,2,5 | CI seed → parity → E2E |
| 11 | Surfaces (MCP, /api/execute, GraphQL) | P1.3.1, P1.3.2, P4.4.1 | 1,4 | REST, spec, GraphQL |
| 1–4 | Ground Rules (Deterministic-first, Evidence) | P2.1.1, P2.2.1, P3.1.1 | 2–3 | Contract & routing |
| 12 | ID/Category Policy | P2.1.1 | 2 | Audit ensures no collisions |
| 13 | DevEx & CI/CD | P1.5.1, P1.7.1 | 1 | Flags, cache, CI |
| 15–16 | Migration & Acceptance | P2.2.1, P3.2.1, P5.1.1–P5.1.3 | 2–5 | Golden, E2E, readiness |
| 1–200 | Logic modules existing | P2.1.1–P2.5.1 | 2 | Contract/evidence/cache/schema |
| 201–230 | Regulatory OS & Evidence Intelligence | P3.3.1 (215), P4.3.1 (watchers), P4.1.2 (216) + create missing files (see P2.7.1 below) | 3–4 | See P2.7.1 for file creation |

Additional Explicit Map for Regulatory IDs:
- 16, 17, 39–41, 84, 85, 195 → `P2.2.1` (routing through packs)
- 215 → `P3.3.1` (coverage scorer)
- 216 → `P4.1.2` (consent auditor)

---

## 7. Dependency Audit

- All P1 tasks require only local filesystem and Python; no network.
- P2 depends solely on P1 scaffolds; does not require external data (uses fixtures and existing logic data access paths guarded by flags/caches).
- P3 uses only fixtures and local compilers; no external data.
- P4 introduces external connectors/watchers but depends only on earlier scaffolds (P1–P3); no forward references.
- P5 executes tests and checks over built artifacts; no new feature dependencies.

---

## 8. Quality Gates Per Phase

- Phase 1: Unit tests for evidence, regulatory base, helpers, and `/api/execute` passing; CI seed green; local smoke OK.
- Phase 2: All logic contract checks pass; orchestrator integration tests pass; parity tests green.
- Phase 3: Golden DSL tests pass with fixtures; reverse-learning E2E passes; anomaly tests deterministic.
- Phase 4: Contract tests for connectors/consent/security pass with mocks; dashboards alert rules validated.
- Phase 5: E2E, performance within budgets, zero high/critical vulns, final checklist approved.

---

## 9. Launch Readiness Checklist

- Evidence OS operational with ≥90% coverage on MIS/P&L fixtures.
- Regulatory OS compiler and packs passing golden tests; orchestrators attach `applied_rule_set`.
- MCP + `/api/execute` + GraphQL surfaces contract parity verified.
- Connectors consent-bound with mocked contract tests; PII redaction enforced; residency toggles documented.
- Observability budgets and dashboards live; MWMBR and latency alerts configured; runbooks in repo.
- CI gates for lint, unit, integration, golden, contract, security, and performance enabled; SBOM published.
- Rollback recipe documented; closed-period replay tests pass on fixtures.

---

## Sanity Checks
- [ ] Repo fully audited against MASTER.
- [ ] No missing or partial features left out.
- [ ] No forward dependencies.
- [ ] Phases compatible with each other.
- [ ] One-pass execution.

---

## Appendix — Added/Clarified Tasks

#### P2.7.1 — Create Missing Logic Files (201–230)
- Why: Complete Master Logic Index.
- Inputs: P1 scaffolds.
- Steps: Add files for 201–230 per MASTER names with minimal deterministic skeletons returning contract-compliant stubs and evidence hooks; mark external data paths behind feature flags until P4 connectors are available.
- Artifacts: `logics/logic_201_*` … `logic_230_*` with tests under `tests/unit/logic_201..230/`.
- DoD: All import and return contract-compliant responses under fixtures.
- Acceptance: Unit tests pass without network.
- Owner: Backend.
- Duration: 2–3 days (parallelizable).
- Risk: Naming collisions; Mitigation: naming_enforcer.
- Traceability: MASTER 201–230.

#### Compliance Verification (Targeted Edits Already Present)
- Dynamic year detection in `main.py` (verified).
- Token refresh to form-encoded in `main.py` (verified).
- `_REGISTRY` import present and only once in `main.py` (verified).
- Logic loader exports `load_all_logics`, `plan_from_query`, and registry `LOGIC_REGISTRY` (verified).
- Compile and contract checks included via tests (P1.6.1, P2.6.1).

# Zoho GPT Backend - Master Scope of Work Implementation Tasks

**Version:** 2025-01-27  
**Status:** Implementation Plan  
**Compliance:** 100% with MASTER_SCOPE_OF_WORK.md and AGENT_EDIT_PROTOCOL.md  

---

## **CURRENT STATE ANALYSIS**

### **Existing Infrastructure**
- ✅ 200 logic files (logic_001 to logic_200) - **MISSING: logic_201-230 (30 Regulatory OS & Evidence Intelligence)**
- ✅ MCP endpoints (/mcp/manifest, /mcp/search, /mcp/fetch, /mcp/stream)
- ✅ Basic orchestrators (mis_orchestrator.py, generic_report_orchestrator.py)
- ✅ Core helpers (zoho_client.py, schema_registry.py, etc.)
- ✅ Dynamic year detection in main.py
- ✅ Token refresh as form-encoded
- ✅ LOGIC_REGISTRY and logic_loader exports

### **Missing Critical Components**
- ❌ Evidence OS (/evidence/ directory with ledger.py, blob_store.py, signer.py)
- ❌ Regulatory OS (/regulatory_os/ with rule_packs, DSL, watchers)
- ❌ /api/execute endpoint (non-MCP surface)
- ❌ /observability/ structure (prometheus/, dashboards/, runbooks/, budgets.yaml)
- ❌ Consent enforcement at connector/orchestrator boundaries
- ❌ Evidence coverage validation (≥90% requirement)
- ❌ 30 missing logic files (logic_201-230)
- ❌ Connectors (gsp_gst_client.py, irp_einvoice_client.py, etc.)

---

## **PHASE 0: EVIDENCE & CONTRACT FOUNDATION**

### **Week 1: Evidence OS Scaffolding**

#### **Task 0.1: Create Evidence OS Directory Structure**
```bash
mkdir -p evidence
mkdir -p evidence/tests
mkdir -p evidence/fixtures
```

**Files to Create:**
- `evidence/__init__.py` - Package initialization
- `evidence/ledger.py` - WORM hash-chained ledger (minimal implementation)
- `evidence/blob_store.py` - Content-addressed storage (local file-based)
- `evidence/signer.py` - Optional signing (no-op initially)
- `evidence/evidence_graph.py` - Evidence node management
- `evidence/tests/test_ledger.py` - Unit tests for ledger
- `evidence/tests/test_blob_store.py` - Unit tests for blob store
- `evidence/fixtures/sample_evidence.json` - Test fixtures

**Implementation Details:**
- `ledger.py`: Implement hash-chained WORM ledger with Merkle roots
- `blob_store.py`: Local file-based content-addressed storage with SHA256 hashing
- `signer.py`: No-op implementation with org key signing capability
- All evidence nodes must have format: `evidence://source/type/period/node_id`

#### **Task 0.2: Create Observability Structure**
```bash
mkdir -p observability/prometheus
mkdir -p observability/dashboards
mkdir -p observability/runbooks
```

**Files to Create:**
- `observability/budgets.yaml` - p95/p99 budgets per logic
- `observability/prometheus/rules.yaml` - SLO alerts and metrics
- `observability/prometheus/metrics.py` - Custom metrics collection
- `observability/dashboards/slo_overview.json` - Evidence coverage metrics
- `observability/dashboards/dependency_health.json` - Regulatory pack status
- `observability/runbooks/slo_latency.md` - SLO breach runbook
- `observability/runbooks/evidence_coverage.md` - Evidence coverage runbook

#### **Task 0.3: Create Regulatory OS Foundation**
```bash
mkdir -p regulatory_os/rule_packs
mkdir -p regulatory_os/golden_tests
mkdir -p regulatory_os/fixtures
```

**Files to Create:**
- `regulatory_os/__init__.py` - Package initialization
- `regulatory_os/rule_engine.py` - Thin run_rule_pack() implementation
- `regulatory_os/rule_packs/gst@2025-08.json` - Initial GST rule pack
- `regulatory_os/rule_packs/itd@2025-08.json` - Initial ITD rule pack
- `regulatory_os/golden_tests/test_gst_pack_2025_08.py` - Golden test for GST
- `regulatory_os/golden_tests/test_itd_pack_2025_08.py` - Golden test for ITD
- `regulatory_os/fixtures/gst_2025_08_inputs.json` - Test inputs
- `regulatory_os/fixtures/gst_2025_08_expected.json` - Expected outputs

#### **Task 0.4: Create API Execute Surface**
```bash
mkdir -p surfaces
```

**Files to Create:**
- `surfaces/__init__.py` - Package initialization
- `surfaces/api_execute.py` - /api/execute endpoint implementation
- `surfaces/openapi.yaml` - OpenAPI specification
- `surfaces/contracts.py` - Shared output contracts
- `surfaces/validation.py` - Input/output validation

**Implementation Details:**
- Mirror MCP outputs exactly
- Support both single logic and orchestrated execution
- Include evidence handles in all responses
- Validate against shared contracts

### **Week 2: Evidence Integration**

#### **Task 0.5: Update Core Helpers**
**Files to Modify:**
- `helpers/schema_registry.py` - Add evidence schema validation
- `helpers/learning_hooks.py` - Add confidence scoring
- `helpers/history_store.py` - Add event writing with evidence
- `helpers/rules_engine.py` - Add validate_accounting()
- `helpers/cache.py` - Add deterministic caching by inputs + pack versions

**Implementation Details:**
- `schema_registry.py`: Add evidence node schema validation
- `learning_hooks.py`: Implement confidence scoring heuristics
- `history_store.py`: Add evidence attachment to events
- `rules_engine.py`: Add accounting validation rules
- `cache.py`: Cache by deterministic keys (inputs + rule pack versions)

#### **Task 0.6: Wire Evidence to Top 10 Logics**
**Files to Modify (Add evidence handles with no behavior change):**
1. `logics/logic_001_profit_and_loss_summary.py`
2. `logics/logic_016_gstr_filing_status.py`
3. `logics/logic_017_tds_filing_status.py`
4. `logics/logic_039_tax_summary_report.py`
5. `logics/logic_040_gst_reconciliation_status.py`
6. `logics/logic_041_tds_deducted_vs_paid.py`
7. `logics/logic_084_input_tax_credit_reconciliation.py`
8. `logics/logic_085_late_filing_penalty_tracker.py`
9. `logics/logic_195_reverse_charge_monitor_gst.py`
10. `logics/logic_230_regulatory_delta_explainer.py` (if exists)

**Implementation Details:**
- Add `attach_evidence()` calls to each logic
- Return evidence handles in output contract
- Maintain backward compatibility
- Add explicit "missing" alerts for stubbed evidence

#### **Task 0.7: Update Main.py with /api/execute**
**Files to Modify:**
- `main.py` - Add /api/execute route

**Implementation Details:**
- Add `/api/execute` POST endpoint
- Mirror MCP contract exactly
- Support both single logic and orchestrated execution
- Include evidence handles in responses

#### **Task 0.8: Update Orchestrators**
**Files to Modify:**
- `orchestrators/mis_orchestrator.py` - Add applied_rule_set merging
- `orchestrators/generic_report_orchestrator.py` - Add evidence merging

**Implementation Details:**
- Merge applied_rule_set from all logics
- Combine evidence handles from all sections
- Add completeness scoring
- Maintain backward compatibility

### **Week 3: Testing & Validation**

#### **Task 0.9: Create Evidence Tests**
**Files to Create:**
- `tests/integration/test_evidence_contract.py` - Verify evidence coverage
- `tests/integration/test_api_execute.py` - Test /api/execute endpoint
- `tests/unit/evidence/test_ledger.py` - Test evidence ledger
- `tests/unit/evidence/test_blob_store.py` - Test blob store
- `tests/golden/test_evidence_coverage.py` - Golden tests for evidence

#### **Task 0.10: Update Configuration**
**Files to Create/Modify:**
- `config/evidence/schemas.yaml` - Evidence node schemas
- `config/regulations/rule_packs.yaml` - Registry of available packs
- `config/regulations/gst.json` - Update with effective dates

---

## **PHASE 1: DETERMINISM & REGULATORY PACKS**

### **Week 4: Regulatory Pack Implementation**

#### **Task 1.1: Implement Rule Engine**
**Files to Create/Modify:**
- `regulatory_os/rule_engine.py` - Complete run_rule_pack() implementation
- `regulatory_os/pack_loader.py` - Load and validate rule packs
- `regulatory_os/effective_date.py` - Effective date logic

**Implementation Details:**
- Load JSON rule packs by effective date
- Validate pack syntax and fixtures
- Run golden tests before enabling packs
- Support multiple pack versions per regulation

#### **Task 1.2: Route Regulatory Logics Through Rule Packs**
**Files to Modify:**
- `logics/logic_016_gstr_filing_status.py` - Route through GST pack
- `logics/logic_017_tds_filing_status.py` - Route through ITD pack
- `logics/logic_039_tax_summary_report.py` - Route through tax packs
- `logics/logic_040_gst_reconciliation_status.py` - Route through GST pack
- `logics/logic_041_tds_deducted_vs_paid.py` - Route through ITD pack
- `logics/logic_084_input_tax_credit_reconciliation.py` - Route through GST pack
- `logics/logic_085_late_filing_penalty_tracker.py` - Route through penalty packs
- `logics/logic_195_reverse_charge_monitor_gst.py` - Route through GST pack

**Implementation Details:**
- Call `run_rule_pack()` in each regulatory logic
- Attach applied_rule_set to outputs
- Validate against golden tests
- Maintain backward compatibility

#### **Task 1.3: Create Golden Test Framework**
**Files to Create:**
- `regulatory_os/golden_tests/__init__.py`
- `regulatory_os/golden_tests/framework.py` - Golden test framework
- `regulatory_os/golden_tests/test_gst_pack_2025_08.py` - GST golden tests
- `regulatory_os/golden_tests/test_itd_pack_2025_08.py` - ITD golden tests
- `regulatory_os/fixtures/gst_2025_08_inputs.json` - Historical inputs
- `regulatory_os/fixtures/gst_2025_08_expected.json` - Expected outputs

**Implementation Details:**
- Reproduce byte-identical outputs from historical data
- Validate rule pack changes don't break existing outputs
- Support multiple pack versions
- Automated testing in CI

### **Week 5: SLOs & Observability**

#### **Task 1.4: Implement SLO Monitoring**
**Files to Create/Modify:**
- `observability/prometheus/metrics.py` - Custom metrics collection
- `observability/prometheus/rules.yaml` - SLO alert rules
- `observability/dashboards/slo_overview.json` - SLO dashboard
- `observability/dashboards/dependency_health.json` - Dependency health

**Implementation Details:**
- Track p95/p99 latencies per logic
- Monitor evidence coverage (≥90% target)
- Alert on SLO breaches
- Track regulatory pack freshness

#### **Task 1.5: Add Runtime Metrics**
**Files to Modify:**
- All logic files - Add metrics collection
- `helpers/metrics.py` - Centralized metrics
- `main.py` - Add metrics middleware

**Implementation Details:**
- Track execution time per logic
- Monitor cache hit rates
- Track error rates and types
- Monitor evidence coverage

### **Week 6: Connectors & Consent**

#### **Task 1.6: Create Connectors**
**Files to Create:**
- `connectors/__init__.py`
- `connectors/gsp_gst_client.py` - GSTN API client
- `connectors/irp_einvoice_client.py` - E-invoice client
- `connectors/itd_traces_client.py` - TDS/26AS client
- `connectors/aa_client.py` - Account aggregator client
- `connectors/apisetu_client.py` - API Setu client
- `connectors/mca_client.py` - MCA client

**Implementation Details:**
- Implement official API clients only
- Add consent validation at connector boundary
- Support rate limiting and backoff
- Add PII redaction

#### **Task 1.7: Implement Consent Enforcement**
**Files to Create/Modify:**
- `helpers/consent.py` - Consent validation
- `logics/logic_216_consent_compliance_auditor.py` - Consent auditor
- All connectors - Add consent validation
- All orchestrators - Add consent validation

**Implementation Details:**
- Validate consent objects at connector boundary
- Audit consent compliance in logic_216
- Enforce scope and expiry
- Track consent usage

---

## **PHASE 2: COVERAGE & ORCHESTRATION**

### **Week 7: Missing Logic Files**

#### **Task 2.1: Create Missing Logic Files (logic_201-230)**
**Files to Create:**
- `logics/logic_201_regulatory_watcher_cbic_circulars_gst.py`
- `logics/logic_202_regulatory_watcher_cbdt_circulars_itd.py`
- `logics/logic_203_regulatory_watcher_gstn_irp_schema_changes.py`
- `logics/logic_204_regulatory_watcher_eway_bill_api_changes.py`
- `logics/logic_205_api_setu_subscription_manager_pan_kyc.py`
- `logics/logic_206_gstr1_books_reconciliation_line_level.py`
- `logics/logic_207_gstr2b_itc_books_aging_eligibility.py`
- `logics/logic_208_einvoice_sales_register_consistency.py`
- `logics/logic_209_eway_bill_delivery_inventory_movement_match.py`
- `logics/logic_210_26as_books_tds_map_payer_payee_sections.py`
- `logics/logic_211_ais_tis_mapper_to_ledgers_with_confidence.py`
- `logics/logic_212_cross_company_related_party_detector_mca_books.py`
- `logics/logic_213_aa_bank_statement_books_reconciliation.py`
- `logics/logic_214_effective_date_rule_evaluator_multi_period_recompute.py`
- `logics/logic_215_evidence_coverage_scorer.py`
- `logics/logic_216_consent_compliance_auditor_scope_expiry.py`
- `logics/logic_217_filing_calendar_synthesizer_auto_updated_from_circulars.py`
- `logics/logic_218_regulatory_impact_simulator_what_if.py`
- `logics/logic_219_audit_bundle_generator_rules_evidence_outputs.py`
- `logics/logic_220_enforcement_guard_fail_closed_on_invalid_pack.py`
- `logics/logic_221_supplier_risk_heatmap_gstr_performance_disputes.py`
- `logics/logic_222_itc_eligibility_classifier_rule_based_evidence.py`
- `logics/logic_223_tds_section_classifier_deterministic_with_proofs.py`
- `logics/logic_224_inventory_to_eway_reconciliation_gaps.py`
- `logics/logic_225_einvoice_cancellation_amendment_auditor.py`
- `logics/logic_226_bank_to_revenue_corroboration_aa_invoices.py`
- `logics/logic_227_gstin_pan_consistency_checker_api_setu.py`
- `logics/logic_228_ledger_drift_detector_books_vs_filings.py`
- `logics/logic_229_evidence_freshness_monitor.py`
- `logics/logic_230_regulatory_delta_explainer.py`

**Implementation Details:**
- Follow logic contract template exactly
- Include evidence handles from day 1
- Add appropriate tags and categories
- Implement deterministic core with learning hooks

#### **Task 2.2: Create Tests for New Logics**
**Files to Create:**
- `tests/unit/logic_201/test_logic_201.py` through `tests/unit/logic_230/test_logic_230.py`
- `tests/integration/test_regulatory_intelligence.py` - Integration tests
- `tests/performance/test_evidence_performance.py` - Performance tests

### **Week 8: Enhanced Orchestration**

#### **Task 2.3: Enhance Orchestrators**
**Files to Modify:**
- `orchestrators/mis_orchestrator.py` - Add completeness scoring
- `orchestrators/generic_report_orchestrator.py` - Add evidence merging
- `orchestrators/regulatory_orchestrator.py` - New regulatory compliance orchestrator

**Implementation Details:**
- Add completeness scoring (0.0-1.0)
- Merge evidence handles from all sections
- Combine applied_rule_set from all logics
- Support partial failures with graceful degradation

#### **Task 2.4: Implement Evidence Coverage Validation**
**Files to Create/Modify:**
- `helpers/evidence_coverage.py` - Coverage validation
- `logics/logic_215_evidence_coverage_scorer.py` - Coverage scoring
- All orchestrators - Add coverage validation

**Implementation Details:**
- Validate ≥90% evidence coverage for MIS/P&L sections
- Score coverage per logic and orchestrator
- Alert on insufficient coverage
- Track coverage trends over time

### **Week 9: Byte-Identical Replay**

#### **Task 2.5: Implement Replay System**
**Files to Create:**
- `evidence/replay.py` - Replay system
- `evidence/fixtures/closed_periods/` - Closed period data
- `tests/golden/test_replay_consistency.py` - Replay tests

**Implementation Details:**
- Recompute closed periods using frozen inputs + rule packs
- Verify byte-identical outputs
- Support multiple closed periods
- Track replay performance

#### **Task 2.6: Add Deterministic Caching**
**Files to Modify:**
- `helpers/cache.py` - Add deterministic caching
- All logic files - Use deterministic cache keys

**Implementation Details:**
- Cache by inputs + rule pack versions + period
- Support cache invalidation by rule pack changes
- Track cache hit rates
- Monitor cache performance

---

## **PHASE 3: WATCHERS & IMPACT SIMULATION**

### **Week 10: Regulatory Watchers**

#### **Task 3.1: Implement Watchers**
**Files to Create:**
- `regulatory_os/watchers/__init__.py`
- `regulatory_os/watchers/gst_watcher.py` - Monitor CBIC/GSTN changes
- `regulatory_os/watchers/itd_watcher.py` - Monitor CBDT changes
- `regulatory_os/watchers/eway_watcher.py` - Monitor E-Way Bill changes
- `regulatory_os/watchers/api_setu_watcher.py` - Monitor API Setu changes

**Implementation Details:**
- Monitor official regulatory sources
- Auto-open PRs with diff summaries
- Update rule packs automatically
- Notify on breaking changes

#### **Task 3.2: Implement DSL Compiler**
**Files to Create:**
- `regulatory_os/dsl/__init__.py`
- `regulatory_os/dsl/grammar.py` - DSL grammar
- `regulatory_os/dsl/compiler.py` - Compile to deterministic code
- `regulatory_os/dsl/tests/test_compiler.py` - DSL tests

**Implementation Details:**
- Define DSL grammar for rule packs
- Compile DSL to deterministic Python code
- Support effective date logic
- Validate compiled rules

### **Week 11: Impact Simulation**

#### **Task 3.3: Implement Impact Simulator**
**Files to Create/Modify:**
- `logics/logic_218_regulatory_impact_simulator_what_if.py` - Impact simulator
- `regulatory_os/impact_simulator.py` - Core simulation engine
- `regulatory_os/fixtures/impact_scenarios/` - Test scenarios

**Implementation Details:**
- Simulate regulatory changes before effective dates
- Compare outputs with current rules
- Generate impact reports
- Support what-if scenarios

#### **Task 3.4: Add GraphQL Surface**
**Files to Create:**
- `surfaces/graphql/__init__.py`
- `surfaces/graphql/schema.py` - GraphQL schema
- `surfaces/graphql/resolvers.py` - GraphQL resolvers
- `surfaces/graphql/tests/test_graphql.py` - GraphQL tests

**Implementation Details:**
- Define GraphQL schema
- Implement resolvers for logic execution
- Support evidence queries
- Maintain contract parity with MCP and /api/execute

---

## **PHASE 4: PRODUCTION READINESS**

### **Week 12: Security & Compliance**

#### **Task 4.1: Implement Security Measures**
**Files to Create/Modify:**
- `helpers/security.py` - Security utilities
- `helpers/pii_redaction.py` - PII redaction
- All connectors - Add PII redaction
- All logics - Add PII redaction

**Implementation Details:**
- Implement PII redaction in logs
- Add encryption at rest
- Support region pinning
- Add supply chain security (SBOM, vulnerability scanning)

#### **Task 4.2: Add CI/CD Gates**
**Files to Create/Modify:**
- `.github/workflows/ci.yml` - CI pipeline
- `.github/workflows/security.yml` - Security scanning
- `scripts/sbom_generator.py` - SBOM generation
- `scripts/license_checker.py` - License compliance

**Implementation Details:**
- Add linting (black, ruff, mypy)
- Add security scanning (bandit)
- Add license compliance
- Add SBOM generation
- Add golden test gates

### **Week 13: Performance & Monitoring**

#### **Task 4.3: Performance Optimization**
**Files to Create/Modify:**
- `tests/performance/test_load_performance.py` - Load tests
- `tests/performance/test_evidence_performance.py` - Evidence performance
- `observability/runbooks/performance_tuning.md` - Performance runbook

**Implementation Details:**
- Optimize evidence storage and retrieval
- Optimize rule pack compilation
- Add performance budgets
- Monitor resource usage

#### **Task 4.4: Final Validation**
**Files to Create/Modify:**
- `tests/e2e/test_full_workflow.py` - End-to-end tests
- `tests/contract/test_surface_parity.py` - Surface parity tests
- `scripts/validation_runner.py` - Validation script

**Implementation Details:**
- Test full workflow from MCP to evidence
- Verify surface parity (MCP, /api/execute, GraphQL)
- Validate evidence coverage ≥90%
- Test byte-identical replay

---

## **ACCEPTANCE CRITERIA VALIDATION**

### **Evidence Coverage ≥ 90%**
- [ ] All MIS/P&L sections have evidence handles
- [ ] Evidence coverage metrics implemented
- [ ] Coverage alerts configured
- [ ] Coverage dashboard operational

### **Deterministic Replay**
- [ ] Closed month replay implemented
- [ ] Byte-identical outputs verified
- [ ] Replay performance optimized
- [ ] Replay tests passing

### **Zero Untested Rule Merges**
- [ ] Golden tests for all rule packs
- [ ] CI gates for golden tests
- [ ] Rule pack validation implemented
- [ ] Breaking change detection

### **Connector Freshness SLOs**
- [ ] GSTR-2B ≤ 24h freshness
- [ ] 26AS on user trigger
- [ ] Freshness monitoring implemented
- [ ] Freshness alerts configured

### **Narratives on Demand**
- [ ] Variance explanation linked to rules
- [ ] Evidence links in explanations
- [ ] Narrative generation implemented
- [ ] Narrative quality scoring

### **Security Compliance**
- [ ] No PII in logs
- [ ] Consent enforced
- [ ] SBOM published
- [ ] High/critical vulns blocked

### **Observability**
- [ ] SLO dashboards live
- [ ] MWMBR alerts firing
- [ ] Runbooks complete
- [ ] Metrics collection operational

### **Surface Parity**
- [ ] MCP endpoints working
- [ ] /api/execute working
- [ ] GraphQL working
- [ ] Contract parity verified

---

## **ROLLBACK PLAN**

### **Phase 0 Rollback**
- Revert evidence handles from top 10 logics
- Remove /evidence/ directory
- Remove /api/execute endpoint
- Restore original main.py

### **Phase 1 Rollback**
- Disable rule pack routing
- Revert regulatory logic changes
- Remove regulatory_os directory
- Restore original logic behavior

### **Phase 2 Rollback**
- Remove logic_201-230 files
- Revert orchestrator enhancements
- Remove evidence coverage validation
- Restore original orchestration

### **Phase 3 Rollback**
- Disable watchers
- Remove DSL compiler
- Remove impact simulator
- Restore original regulatory handling

### **Phase 4 Rollback**
- Revert security changes
- Remove CI/CD gates
- Restore original performance
- Remove validation scripts

---

## **SUCCESS METRICS**

### **Technical Metrics**
- Evidence coverage: ≥90% for MIS/P&L sections
- Deterministic replay: 100% byte-identical for closed periods
- Rule pack testing: 100% golden test coverage
- Surface parity: 100% contract compliance
- Security: 0 high/critical vulnerabilities

### **Operational Metrics**
- SLO compliance: ≥99.9% availability
- Latency: p95 ≤ budgeted ms, p99 ≤ 2x p95
- Freshness: GSTR-2B ≤ 24h, 26AS on trigger
- Coverage: ≥90% evidence coverage maintained

### **Business Metrics**
- Regulatory compliance: 100% rule pack coverage
- Audit readiness: Complete evidence bundles
- Cost efficiency: Optimized caching and storage
- User satisfaction: Reliable and fast responses

---

**Author:** Hardy  
**Last Updated:** 2025-01-27  
**Status:** Ready for Implementation
