V4 — Accounting Auto-Auditable Backend (Deterministic-First, Evidence OS, MCP-Ready & MCP-Independent) — MASTER SCOPE OF WORK
Version: 2025-08-15 • Owner: Hardik • Status: Living document (authoritative)

> Single source of truth for scope, principles, structure, governance, and acceptance criteria.  
> Keep and re-share this file if anything ever resets. Supersedes prior versions (V1/V2) with stronger determinism, evidence guarantees, regulatory automation, and production SLOs.

──────────────────────────────────────────────────────────────────────────────

0) Ground Rules — L4+ (Autonomous, Closed-Loop Evolution, Deterministic-First)

Applies to every logic module (.py), connector, orchestrator, rule-pack, and surface.

1. Deterministic-First, Generative-Second  
   • Accounting/compliance conclusions MUST be produced by deterministic rules (rules_engine + Regulatory OS DSL).  
   • LLMs may propose mappings, narratives, remediations, and prioritizations WITH confidence scores; these are advisory.

2. Evidence or It Didn’t Happen  
   • Every figure/statement must carry provenance into a WORM, content-addressed Evidence Graph (hash-chained).  
   • Closed periods are replayable (byte-identical) from frozen inputs + rule-pack versions.

3. Self-Learning (Within Guardrails)  
   • Each logic maintains in-file strategy registry and feedback loops.  
   • Learning can never overwrite deterministic truth; it only proposes better strategies or mappings.

4. History-Aware  
   • Persist changelogs for invoices, bills, POs, salaries, items, taxes, etc. Track deltas (MoM, YoY), vendor and cross-org deviation.

5. Reverse-Learning for New Formats  
   • On unfamiliar reports (e.g., MIS PDF), auto-extract → map → verify → register schema → regenerate next time with provenance.

6. Expandable in the Same File  
   • Each logic evolves in its own `.py` via internal strategies/subtrees. New files only for shared helpers/utilities.

7. Many-to-One Orchestration  
   • Orchestrators compose **2 → ∞** logics with DAG execution, partial retries, graceful degradation, and applied_rule_set attachment.

8. Auto-Expansion  
   • Repeated unmet requests auto-spawn logic stubs with tests and safe registration.

9. Zero-Trust by Default  
   • Inputs validated against schemas; PII redaction; least privilege; no portal automation without explicit consent.

10. Cost-&-SLO-Aware  
   • Deterministic caches, rate limits, concurrency budgets; measurable SLOs (availability, p95/p99 latencies).

──────────────────────────────────────────────────────────────────────────────

1) Architecture & Folder Layout

repo/
  main.py                                # FastAPI app; MCP + non-MCP surfaces; tool router; SSE
  /logics/                               # 200+ operate files (L4-compliant, deterministic core)
    logic_001_profit_loss.py
    ...
    logic_230_regulatory_delta_explainer.py
  /orchestrators/
    mis_orchestrator.py
    generic_report_orchestrator.py
  /helpers/
    zoho_client.py                       # Auth, backoff, retries, caching
    pdf_extractor.py                     # OCR/parse; table/field detection
    schema_registry.py                   # JSONSchemas for inputs/outputs
    rules_engine.py                      # Deterministic rules + guardrails + DSL hooks
    history_store.py                     # Append-only event/event-diff store
    learning_hooks.py                    # Self-learning interfaces & scoring
    cache.py                             # Layered cache (memory/redis/ttl)
    feature_flags.py                     # Launch-darkly-style toggles (local impl)
  /regulatory_os/                        # Rule packs + watchers + DSL + adapters
    rule_packs/                          # e.g., gst@2025-08/, itd@2025-08/
    watchers/                            # CBIC/CBDT/GSTN/IRP/E-Way Bill/API Setu diffs
    dsl/                                 # Rules DSL grammar + compiler/transpiler
    adapters/                            # Normalizers: GSTR-2B, 26AS, AIS, e-invoice, AA
  /connectors/                           # Consent-based, MCP-independent sources
    apisetu_client.py
    gsp_gst_client.py
    irp_einvoice_client.py
    ewaybill_client.py
    itd_traces_client.py
    aa_client.py
    mca_client.py
  /evidence/                             # Evidence OS
    ledger.py                            # WORM (hash-chained, Merkle-rooted)
    blob_store.py                        # Content-addressed artifacts
    signer.py                            # Optional signing for legal defensibility
  /observability/
    prometheus/                          # Rules, alerts (SLOs)
    dashboards/                          # Grafana JSON
    runbooks/                            # Incident runbooks (SLO, latency, deps)
  /surfaces/
    openapi.yaml                         # OpenAPI for /api/execute etc.
    graphql/                             # GraphQL schema & resolvers
    cli/                                 # Minimal CLI wrapper
  /prompts/                              # Few-shot prompts for narratives (non-authoritative)
  /tests/                                # Unit, integration, golden, contract, DSL, security, load
  /docs/                                 # ADRs, SOPs, CHANGELOG, learned formats

Tenets
• MCP-ready: /mcp/manifest, /mcp/search (POST), /mcp/fetch (POST + SSE).  
• MCP-independent: /api/execute, /graphql, /webhooks, /sse, /cli.  
• Observability: Structured logs/metrics + SLOs per logic/orchestrator.  
• Security: AuthN/Z, rate limits, schema validation, consent objects, PII redaction.  
• Data Residency: Configurable storage backends with encryption at rest + region pinning.

──────────────────────────────────────────────────────────────────────────────

2) Logic Module Contract (Template, Deterministic-First)

"""
Title: <Human-friendly name>
ID: L-XXX
Tags: ["mis","pnl","compliance"]
Category: <Static | Dynamic(Regulation) | Dynamic(Patterns) | Dynamic(Growth) | Dynamic(Behavior)>
Required Inputs: <typed schema or JSONSchema ref>
Outputs: <typed schema>
Assumptions: <explicit>
Evidence: <which sources will be attached>
Evolution Notes: <self-learning pathways; strategies; data>
"""

from typing import Any, Dict
from helpers.schema_registry import validate_payload
from helpers.learning_hooks import record_feedback, score_confidence
from helpers.history_store import write_event
from helpers.rules_engine import validate_accounting, run_rule_pack
from evidence.ledger import attach_evidence

def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    # 1) Validate inputs
    validate_payload("L-XXX", payload)

    # 2) Fetch source data (zoho_client / connectors / cache)
    #    data = ...

    # 3) Deterministic core: rules_engine + (optional) regulatory_os DSL
    #    result, applied_rule_set = run_rule_pack("gst", data, context=payload)

    # 4) Accounting validations
    #    alerts += validate_accounting(result)

    # 5) Evidence: attach_evidence(...) → returns graph handles per figure
    #    provenance = attach_evidence(result, sources=data)

    # 6) History: write_event(...)
    #    write_event(logic="L-XXX", inputs=payload, outputs=result, provenance=provenance)

    # 7) Self-learning (advisory only)
    #    record_feedback("L-XXX", context=payload, outputs=result)

    # 8) Optional LLM narratives/remediations (non-authoritative)
    #    explanation = ...

    return {
      "result": ...,                                 # deterministic object/array/number
      "provenance": {...},                           # evidence://node-id handles
      "confidence": score_confidence(...),           # deterministic heuristic
      "alerts": [...],                                # rule violations with severities
      "applied_rule_set": {...},                     # pack versions + effective dates
      "explanation": "optional narrative (advisory)"
    }

Output Contract (Every Logic)
{
  "result": <object/array/number>,
  "provenance": { "<figure_key>": ["evidence://<node-id>", "..."] },
  "confidence": <0.0-1.0>,
  "alerts": [
    { "code": "RULE_<...>", "severity": "info|warn|error", "message": "...", "evidence": ["evidence://..."] }
  ],
  "applied_rule_set": {
    "packs": { "gst": "gst@2025-08", "itd": "itd@2025-08" },
    "effective_date_window": { "from": "YYYY-MM-DD", "to": "YYYY-MM-DD" }
  }
}

Hard Rules
• No PII in messages/logs; IDs only.  
• Confidence is computed by deterministic heuristics; LLM confidence is advisory only.  
• Missing data is explicit (null + alert), never silently omitted.

──────────────────────────────────────────────────────────────────────────────

3) Orchestration (2 → ∞)

• Graph-based execution: DAG with declared inputs/outputs and data contracts.  
• Partial failure tolerance: Continue with available results; annotate gaps with completeness score.  
• Auto-discovery: Orchestrators discover and include new logics matching tags/rules.  
• Regulatory lens: Attach applied_rule_set (+ versions) for each section.  
• Feature flags: Orchestrator can toggle experimental logics per org/environment.

Orchestrator Output MUST include:
{
  "sections": { "<logic_id_or_name>": <logic_output>, ... },
  "alerts": [ ... merged and deduped ... ],
  "completeness": 0.0-1.0,
  "applied_rule_set": { ... merged pack versions ... }
}

──────────────────────────────────────────────────────────────────────────────

4) Reverse-Learning Pipeline (New MIS PDFs → Working Generators)

1. Ingest PDF → pdf_extractor parses tables/labels/values.  
2. Field mapping → canonical schemas via nomenclature maps.  
3. Provenance learning → persist mapping (field → endpoint/path/filter).  
4. Schema capture → register versioned report schema.  
5. Verification → reconcile totals/subtotals; flag mismatches.  
6. Auto-enable generation → expose as orchestrated report next time (with evidence).

──────────────────────────────────────────────────────────────────────────────

5) Evidence OS (WORM Graph + Artifacts)

• ledger.py: Hash-chained WORM ledger with Merkle roots per bundle.  
• blob_store.py: Content-addressed storage for artifacts (PDFs, JSON, CSV, images).  
• signer.py: Optional signing (org key) for legal defensibility.  
• Replay: Recompute closed periods using frozen inputs + rule-packs → byte-identical outputs.  
• Coverage: ≥90% evidence nodes mapped to outputs for MIS/P&L sections.

Example Evidence Node
{
  "id": "evidence://gstn/2b/2025-07/line/84523",
  "hash": "sha256:...",
  "source": "gstn:gstr2b",
  "meta": { "gstin": "...", "period": "2025-07", "line_no": 84523 }
}

──────────────────────────────────────────────────────────────────────────────

6) Regulatory OS (Rule Packs, Watchers, DSL)

• Rule Packs (JSON/YAML): effective_from/to, fixtures, acceptance tests; packs: GST, ITD (TDS/AIS/26AS), MCA.  
• Watchers: Monitor CBIC/CBDT/GSTN/IRP/E-Way Bill/API Setu changes; open PRs with diff summaries.  
• Adapters: Normalize payloads (GSTR-2B, 26AS, AIS, e-invoice, e-way bill, AA statements) to canonical schemas.  
• DSL Compilation: Packs compile to deterministic code paths; orchestrators refuse packs that fail golden tests.  
• Regulatory Impact Simulator: What-if deltas before effective dates.

Sample Rule Pack (YAML)
pack: gst@2025-09
effective_from: 2025-09-01
effective_to: null
rules:
  - id: GST_ITC_ELIGIBILITY
    when: "invoice.date in_period && invoice.has_einvoice"
    then: "itc.eligible = true"
fixtures:
  inputs: fixtures/gst_2025_09_inputs.json
  expected: fixtures/gst_2025_09_expected.json
tests:
  - assert: "totals.itc_eligible == 123456.78"

──────────────────────────────────────────────────────────────────────────────

7) Connectors, Consent & Compliance (MCP-Independent)

• Connectors live in /connectors/: gsp_gst_client.py, irp_einvoice_client.py, ewaybill_client.py, itd_traces_client.py, aa_client.py, mca_client.py, apisetu_client.py.  
• Consent Objects: scope, purpose, expiry, retention, lawful basis; enforced at runtime.  
• Allowed paths: Official APIs or user-in-the-loop uploads (no scraping of restricted portals).  
• PII Rules: Redact in logs; encrypt at rest; rotate credentials; region pinning.

Consent Object (JSON)
{
  "subject": "ORG:60020606976",
  "scope": ["gst.gstr2b.read", "einvoice.irp.read"],
  "purpose": "compliance_reconciliation",
  "expires_at": "2026-03-31T23:59:59Z",
  "retention_days": 365
}

──────────────────────────────────────────────────────────────────────────────

8) Security, Privacy & Data Residency

• Authentication: Org-scoped tokens; per-org rate limits; mTLS optional.  
• Authorization: RBAC with least privilege; per-logic & per-connector scopes.  
• Secrets: KMS-backed; rotation policy; no secrets in code or logs.  
• Privacy: PII redaction; selective disclosure; export redaction pipelines.  
• Residency: Storage backends MUST support region selection and encryption at rest.  
• Supply-Chain: Pin dependencies; SBOM generation; vulnerability scanning on CI.  
• Chaos & Fault Tolerance: Backoffs, circuit breakers, bulkheads; dependency health in dashboards.

──────────────────────────────────────────────────────────────────────────────

9) Observability & SLOs

• Metrics per logic: runtime, cache hit rate, error taxonomy, anomaly counts.  
• Global SLOs: Availability ≥ 99.9%; p95 latency per logic ≤ budgeted ms; p99 ≤ double p95.  
• Dashboards: SLO Overview, Dependency Lens (Zoho, GSTN, IRP, TRACES, AA).  
• Alerts: MWMBR (Minutes With Missed Budget Ratio), burn-rate SLO alerts.  
• Runbooks: Checked into /observability/runbooks/.

Example Prometheus Record/Alert (pseudo-YAML)
groups:
- name: slo
  rules:
  - record: logic_latency_p95
    expr: histogram_quantile(0.95, sum(rate(logic_latency_ms_bucket[5m])) by (le, logic))
  - alert: LogicP95BudgetBreach
    expr: logic_latency_p95 > on(logic) budget_ms{tier="critical"}
    for: 10m
    labels: { severity: "page" }
    annotations: { runbook: "slo_latency.md" }

──────────────────────────────────────────────────────────────────────────────

10) Testing, Governance & Change Control

Testing Matrix
• Unit: Each logic; edge cases; schema validation.  
• Integration: Orchestrators with ≥3 logics; completeness score assertions.  
• Golden (Regulatory): Rule-packs MUST reproduce known historic outputs (byte-identical).  
• Contract: Connector req/resp schemas; rate limit/backoff behavior.  
• Security: PII redaction tests; consent scope enforcement.  
• Load/Resilience: Soak tests; chaos/load profiles; cache efficacy.

Commit & PR Template

commit
[<Category>] <Logic/Pack/Connector>: <Short summary>
- Deterministic changes: ...
- DSL/Rule pack: ...
- Evidence: <% coverage>, nodes added: N, merkle_root: <hash>
- Tests: unit/integration/golden/contract passed
- Observability: metrics/alerts added
- Rollback: <one-liner>

PR
• What changed / why now  
• Evidence samples (IDs, hashes, merkle root)  
• Screenshots (dashboards/runbooks)  
• Risks & rollback  
• Tags: category:regulation|patterns|growth|behavior|static

Definition of Done (per change)
• Deterministic implementation + tests pass (incl. goldens).  
• Evidence coverage ≥ 90% for affected outputs.  
• Observability in place; SLOs not regressing.  
• Docs updated (CHANGELOG + ADR if regulation).  
• Feature-flagged & both MCP + non-MCP surfaces working.

Rollback Recipe
• Revert rule-pack/version or logic file changes.  
• Disable feature flag.  
• Replay closed months with prior pack → verify byte-identity.

──────────────────────────────────────────────────────────────────────────────

11) Surfaces & Protocols

MCP:  
• /mcp/manifest — tools/inputs/outputs; versioned.  
• /mcp/search (POST) — NL → logic selection/plan.  
• /mcp/fetch (POST/SSE) — execute plan; stream progress.

Non-MCP (first-class):  
• /api/execute (JSON), /graphql, /webhooks, /sse, /cli.  
• Same output contract & evidence guarantees.

Minimal OpenAPI Snippet (/api/execute)
paths:
  /api/execute:
    post:
      summary: Execute a logic or orchestrated plan
      requestBody: { content: { application/json: { schema: { $ref: "#/components/schemas/ExecuteRequest" }}}}
      responses:
        "200": { description: OK, content: { application/json: { schema: { $ref: "#/components/schemas/ExecuteResponse" }}}}

GraphQL Sketch
type Query {
  execute(plan: ExecutePlanInput!): ExecuteResult!
}

──────────────────────────────────────────────────────────────────────────────

12) Master Logic Index (Authoritative, Growing)

Implementation rule: One file per logic in /logics/ named logic_###_snake_case.py.  
Categories: Static • Dynamic(Regulation) • Dynamic(Patterns) • Dynamic(Growth) • Dynamic(Behavior).  
Note: Same 1–200 set as V2, plus 201–230 “Regulatory OS & Evidence Intelligence”. IDs and names are unchanged to preserve backward compatibility.

✅ 1–102 Original Business Logic Modules (unchanged IDs)
1. Profit and Loss Summary
2. Balance Sheet
3. Trial Balance
4. Capital Account Summary
5. Partner Withdrawals
6. Zone-wise Expenses
7. Material Purchase Summary
8. Salary Summary
9. Vendor Payment Summary
10. Receivables Summary
11. Payables Summary
12. Debtor Ageing Buckets
13. Creditor Ageing Buckets
14. Invoice Status
15. Bill Status
16. GSTR Filing Status (Regulation)
17. TDS Filing Status (Regulation)
18. Highest Selling Items
19. Highest Revenue Clients
20. Client-wise Profitability
21. PO-wise Profitability
22. Item-wise Sales Summary
23. Item-wise Profitability
24. Employee Cost Trends
25. Purchase Returns Summary
26. Sales Returns Summary
27. Dead Stock Report
28. Stock Movement Report
29. Cash Flow Statement
30. Bank Reconciliation Status
31. Expense Category Trends
32. Monthly Revenue Trend
33. Monthly Expense Trend
34. Budget vs Actual Report
35. Year-on-Year Growth
36. Month-on-Month Comparison
37. Project-wise Profitability
38. Vendor-wise Spend
39. Tax Summary Report (Regulation)
40. GST Reconciliation Status (Regulation)
41. TDS Deducted vs Paid (Regulation)
42. Credit Utilization Percentage
43. Sales Conversion Ratio
44. Revenue Forecast
45. Expense Forecast
46. Upcoming Invoice Dues
47. Upcoming Bill Payments
48. Receivable Alerts
49. Payable Alerts
50. Loan Outstanding Summary
51. Interest Paid Summary
52. Capital Invested Timeline
53. Shareholder Equity Movement
54. Depreciation Calculation
55. Fixed Asset Register
56. Inventory Valuation
57. Raw Material Usage
58. Bill of Materials Breakdown
59. Overhead Cost Allocation
60. Manufacturing Cost Sheet
61. Production Efficiency Report
62. Sales Team Performance
63. Employee Productivity Analysis
64. Client Acquisition Cost
65. Lead to Client Ratio
66. Marketing Spend Efficiency
67. Campaign ROI Summary
68. Departmental P&L
69. Business Vertical Summary
70. Inter-company Transactions
71. Fund Transfer Logs
72. Internal Audit Checklist
73. Compliance Tracker
74. Audit Trail Summary
75. Error Detection Engine (Patterns)
76. Anomaly Detection Report (Patterns)
77. Vendor Duplication Check
78. Client Duplication Check
79. Data Entry Consistency
80. Duplicate Invoice Detection
81. Outlier Expenses Detection
82. Salary vs Market Benchmark
83. Tax Liability Estimator (Regulation)
84. Input Tax Credit Reconciliation (Regulation)
85. Late Filing Penalty Tracker (Regulation)
86. Missed Payment Tracker
87. Recurring Expenses Monitor
88. Profit Leakage Detector (Patterns)
89. Unbilled Revenue Tracker
90. Advance Received Adjustment
91. Advance Paid Adjustment
92. Suspense Account Monitor (Patterns)
93. Accounting Hygiene Score (Patterns)
94. Business Health Score (Patterns)
95. Scenario Simulation Engine (Growth)
96. Expense Optimization Engine (Patterns/Growth)
97. Credit Rating Estimator (Growth)
98. Business Valuation Estimator (Growth)
99. Dividend Recommendation Engine (Growth)
100. Risk Assessment Matrix (Growth)
101. Cash Reserve Advisor (Growth)
102. Strategic Suggestion Engine (Behavior)

➕ 103–150 Advanced Intelligence & Ops (unchanged IDs)
103. Auto Reconciliation Suggestion
104. Fabrication vs Billing Variance
105. BOQ vs Actual Cost
106. Material Rate Change Monitor
107. Inter-Branch Transfer Log
108. Employee Reimbursement Check
109. Pending Approvals Summary
110. Backdated Entry Detector
111. Late Vendor Payment Penalty Alert
112. Margin Pressure Tracker (Cost↑ vs Price↔)
113. Contract Breach Detection
114. Client Risk Profiling
115. Invoice Bounce Predictor
116. High Risk Vendor Pattern
117. Multi-GSTIN Entity Aggregator
118. Real-Time Working Capital Snapshot
119. Invoice Duplication Prevention on Entry
120. Cross-Period Adjustment Tracker
121. Manual Journal Suspicion Detector
122. Round-off Abuse Detector
123. Loan Covenant Breach Alert
124. Expense Inflation Flag (Employee-wise)
125. Inventory Turnover Ratio
126. Stockout Frequency Alert
127. Excess Inventory Analysis
128. Demand Forecast Accuracy (MAPE)
129. Order Fulfillment Cycle Time
130. Supplier Lead Time Variability
131. Production Capacity Utilization
132. Production Downtime Analysis
133. Scrap Rate Monitor
134. Machine Efficiency Tracker (OEE)
135. Batch Yield Analysis
136. Quality Defect Rate
137. Return Rate Analysis
138. Warranty Claims Monitor
139. Customer Order Accuracy
140. On-time Delivery Rate
141. Transportation Cost Analysis
142. Fleet Utilization Rate
143. Fuel Consumption Tracker
144. Route Optimization Alerts
145. Zone-wise Carbon Score
146. Green Vendor Scorecard
147. Data Redundancy Detector
148. Audit Flag Generator (AI High-Risk Areas)
149. CA Review Ready Index
150. Industry Benchmark Comparison Report

💡 151–180 SaaS-Level Maturity & UX (unchanged IDs)
151. Audit Automation Wizard
152. Auto-Fill for Common JEs
153. Period Lock & Unlock Tracker
154. Custom Rule Builder
155. CFO Dashboard Generator
156. Financial KPI Designer
157. Self-learning Prediction Engine (Rev/Exp)
158. Multi-company Consolidation Reports
159. Alerts via Telegram/Slack/Email/WhatsApp
160. User Access Logs & Abuse Detection
161. File Upload → Entry Mapper (Invoice PDF → JE)
162. Voice-to-Entry
163. Advanced Filing Calendar Sync (GST, ROC, TDS)
164. API-based Third-Party Integration Framework
165. Bank Feed Intelligence Layer
166. Year-end Closure Guide
167. Investment vs Working Capital Allocator
168. Performance Linked Pay Analyzer
169. Cross-company Loan Tracker
170. Government Scheme Utilization Tracker
171. Legal Case Cost Monitor
172. Automated Monthly Compliance Summary
173. DSCR and ICR Calculators
174. Auto CA Remarks on Reports
175. User-Behavior-Based Module Suggestions
176. Business Maturity Scoring
177. CA Collaboration Toolkit
178. AI-Powered Explanation (Multilingual)
179. Journal Trace Visualizer (graph)
180. Interlinked Report Mapper

🧭 181–200 Advanced Auditing & Control (unchanged IDs)
181. Transaction Volume Spike Alert
182. Overdue TDS Deduction Cases
183. Related Party Transaction Tracker
184. Vendor Contract Expiry Alert
185. Unverified GSTIN Alert
186. HSN-SAC Mapping Auditor
187. AI Error Suggestion Engine
188. Report Consistency Verifier (across months)
189. Audit-Ready Report Bundle
190. Internal Control Weakness Identifier
191. Monthly Report Completeness Checker
192. Suggested Journal Entry Fixes
193. Pending JE Approvals
194. Partial Payments Tracker
195. Reverse Charge Monitor (GST)
196. P&L Ratio Anomaly Finder
197. Payment vs Invoice Timeline Mismatch
198. Free Resource Usage Estimator
199. Industry Benchmark Comparator
200. Vendor-side Carbon Emissions Estimator

🚀 201–230 Regulatory OS & Evidence Intelligence (unchanged IDs)
201. Regulatory Watcher — CBIC Circulars (GST)
202. Regulatory Watcher — CBDT Circulars/Notifications (ITD)
203. Regulatory Watcher — GSTN/IRP Schema Changes
204. Regulatory Watcher — E-Way Bill API Changes
205. API Setu Subscription Manager (PAN/KYC)
206. GSTR-1 ↔ Books Reconciliation (line-level)
207. GSTR-2B ITC ↔ Books (aging/eligibility)
208. E-Invoice ↔ Sales Register Consistency
209. E-Way Bill ↔ Delivery/Inventory Movement Match
210. 26AS ↔ Books TDS Map (payer/payee/sections)
211. AIS/TIS Mapper (to ledgers, with confidence)
212. Cross-Company Related-Party Detector (MCA + Books)
213. AA Bank Statement ↔ Books Reconciliation
214. Effective-Date Rule Evaluator (multi-period recompute)
215. Evidence Coverage Scorer
216. Consent Compliance Auditor (scope/expiry)
217. Filing Calendar Synthesizer (auto-updated from circulars)
218. Regulatory Impact Simulator (what-if)
219. Audit Bundle Generator (rules + evidence + outputs)
220. Enforcement Guard (fail-closed on invalid pack)
221. Supplier Risk Heatmap (GSTR + performance + disputes)
222. ITC Eligibility Classifier (rule-based + evidence)
223. TDS Section Classifier (deterministic with proofs)
224. Inventory to E-Way Reconciliation Gaps
225. E-Invoice Cancellation/Amendment Auditor
226. Bank-to-Revenue Corroboration (AA + invoices)
227. GSTIN-PAN Consistency Checker (API Setu)
228. Ledger Drift Detector (books vs filings)
229. Evidence Freshness Monitor
230. Regulatory Delta Explainer

Logic Category Annotations
• Static — Core accounting/reporting. Rare functional changes; improvements focus on performance/clarity.  
• Dynamic (Regulation) — Changes with laws; governed by Rule Packs + effective-date logic.  
• Dynamic (Patterns) — Evolves with anomalies/history; thresholds adapt via statistics (p95/p99).  
• Dynamic (Growth) — Expands features/integrations; backward-compatible outputs.  
• Dynamic (Behavior) — Learns formats and reproduces them with provenance.

──────────────────────────────────────────────────────────────────────────────

13) DevEx & CI/CD

• One-Command Dev: `just dev` (or Make) spins API + hot reload + test watch + local dashboards.  
• Pre-Commit: Format (black/ruff), type (mypy), security (bandit), licenses (pip-licenses), SBOM (syft).  
• CI Stages: lint → unit → integration → golden → contract → security → build → e2e smoke → canary.  
• Feature Flags: /helpers/feature_flags.py; flags are required for risk-bearing changes.  
• Versioning: SemVer per logic and per rule-pack; CHANGELOG enforced by CI.

──────────────────────────────────────────────────────────────────────────────

14) Cost & Performance Guardrails

• Deterministic caches (keyed by inputs + pack versions + period).  
• Budget files per logic (`/observability/budgets.yaml`) define p95/p99 & CPU/mem caps.  
• “Fail-open advisory, fail-closed authoritative”: When dependencies wobble, advisory narratives may continue; authoritative numbers pause with clear alerts.

──────────────────────────────────────────────────────────────────────────────

15) Migration Map (V1/V2 → V4)

Phase 0 (No Breaking Changes)
0. Keep existing logic IDs/names; add evidence handles to outputs (no behavior change).  
1. Introduce /evidence/, wire `attach_evidence()` in top 10 logics (P&L, ITC, TDS, GST recos).  
2. Add /regulatory_os/ with initial `gst@2025-08` + golden tests (reproduce last closed month).

Phase 1 (Determinism & Packs)
3. Route regulatory logics (16,17,39–41,84,85,195) through `run_rule_pack()`.  
4. Add `/observability/` dashboards + SLO alerts; wire runtime/error metrics for top logics.  
5. Implement /api/execute (non-MCP) mirroring MCP outputs.

Phase 2 (Coverage & Orchestration)
6. MIS orchestrator attaches `applied_rule_set` and completeness scores.  
7. Evidence coverage ≥90% on MIS sections; byte-identical recompute for last closed month.

Phase 3 (Watchers & Impact)
8. Enable watchers for CBIC/CBDT/GSTN → automated PRs with pack deltas.  
9. Regulatory Impact Simulator for “what-if” before enforcement.

Exit Criteria  
• All above green; CI/CD gates (goldens, SBOM, security) enforced; feature flags removed for stabilized paths.

──────────────────────────────────────────────────────────────────────────────

16) Acceptance Criteria (Definition of “Won”)

• Evidence Coverage ≥ 90% for MIS/P&L sections (each figure has provenance).  
• Determinism: Recompute closed month → byte-identical outputs.  
• Zero untested rule merges: Rule-pack PRs require passing historical goldens.  
• Connector Freshness SLOs: e.g., GSTR-2B ≤ 24h; 26AS on user trigger.  
• Narratives on demand: “Explain this variance” linked to rules + evidence.  
• Security: No PII in logs; consent enforced; SBOM published; high/critical vulns = block.  
• Observability: SLO dashboards live; MWMBR alerts firing correctly; runbooks complete.  
• Surfaces: MCP + /api/execute + /graphql parity on contracts/evidence.

──────────────────────────────────────────────────────────────────────────────

Appendix A — Minimal Logic Skeleton (copy-paste)

# file: logics/logic_001_profit_loss.py
"""
Title: Profit and Loss Summary
ID: L-001
Tags: ["mis","pnl"]
Category: Static
Required Inputs: {"period": "YYYY-MM", "org_id": "string"}
Outputs: {"totals": {...}, "sections": {...}}
Assumptions: Period is closed for authoritative mode.
Evidence: invoices, bills, journals, adjustments
Evolution Notes: Add client/segment breakdown strategies; caching by period+org
"""
from typing import Any, Dict
from helpers.schema_registry import validate_payload
from helpers.history_store import write_event
from helpers.rules_engine import validate_accounting
from helpers.learning_hooks import record_feedback, score_confidence
from evidence.ledger import attach_evidence
from helpers.cache import cache_get, cache_set
from helpers.zoho_client import fetch_pnl_primitives

def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    validate_payload("L-001", payload)
    cache_key = ("L-001", payload["org_id"], payload["period"])
    if cached := cache_get(cache_key):
        return cached

    data = fetch_pnl_primitives(org_id=payload["org_id"], period=payload["period"])
    # Deterministic core (example aggregation)
    totals = {
        "revenue": sum(i["amount"] for i in data["sales"]),
        "cogs": sum(i["amount"] for i in data["cogs"]),
    }
    totals["gross_profit"] = totals["revenue"] - totals["cogs"]
    totals["opex"] = sum(i["amount"] for i in data["opex"])
    totals["ebit"] = totals["gross_profit"] - totals["opex"]

    alerts = validate_accounting({"totals": totals})
    provenance = attach_evidence({"totals": totals}, sources=data)

    out = {
        "result": {"totals": totals, "sections": {}},
        "provenance": provenance,
        "confidence": score_confidence({"totals": totals}, alerts=alerts),
        "alerts": alerts,
        "applied_rule_set": {"packs": {}, "effective_date_window": None}
    }
    write_event(logic="L-001", inputs=payload, outputs=out["result"], provenance=provenance)
    cache_set(cache_key, out, ttl_seconds=6*3600)
    record_feedback("L-001", context=payload, outputs=out["result"])
    return out

──────────────────────────────────────────────────────────────────────────────

Appendix B — MIS Orchestrator Skeleton

# file: orchestrators/mis_orchestrator.py
from typing import Dict, Any, List
from helpers.feature_flags import is_enabled
from helpers.history_store import write_event

LOGIC_ORDER = [
  "logic_001_profit_loss",
  "logic_084_input_tax_credit_reconciliation",
  "logic_040_gst_reconciliation_status",
  # ... add 2→∞ logics
]

def execute(payload: Dict[str, Any]) -> Dict[str, Any]:
    sections, alerts, packs = {}, [], {}
    completeness = 0.0
    ran = 0

    for logic in LOGIC_ORDER:
        if not is_enabled(logic, org_id=payload["org_id"]): continue
        try:
            mod = __import__(f"logics.{logic}", fromlist=["handle"])
            out = mod.handle(payload)
            sections[logic] = out
            alerts.extend(out.get("alerts", []))
            for k,v in out.get("applied_rule_set", {}).get("packs", {}).items():
                packs[k] = v
            ran += 1
        except Exception as e:
            alerts.append({"code":"ORCH_EXEC_FAIL","severity":"warn","message":str(e),"evidence":[]})

    completeness = ran / max(1, len(LOGIC_ORDER))
    result = {
      "sections": sections,
      "alerts": alerts,
      "completeness": round(completeness, 3),
      "applied_rule_set": {"packs": packs}
    }
    write_event(logic="ORCH_MIS", inputs=payload, outputs=result, provenance={})
    return result

──────────────────────────────────────────────────────────────────────────────

Appendix C — /mcp/* Contracts (sketch)

POST /mcp/search
Request: { "query": "mis for 2025-07 formation", "org_id":"...", "period":"2025-07" }
Response: { "plan": [{"logic":"mis_orchestrator","inputs":{"org_id":"...","period":"2025-07"}}] }

POST /mcp/fetch (SSE if stream=true)
Request: { "plan":[...], "stream": true }
Event Stream: progress %, section results, final JSON identical to /api/execute

──────────────────────────────────────────────────────────────────────────────

Appendix D — Golden Test Pattern (Regulatory)

# tests/golden/test_gst_pack_2025_08.py
def test_gst_pack_reproduces_closed_month():
    inputs = load("fixtures/gst_2025_08_inputs.json")
    expected = load("fixtures/gst_2025_08_expected.json")  # from historic filing
    result, packs = run_rule_pack("gst@2025-08", inputs)
    assert result == expected
    assert packs["gst"] == "gst@2025-08"

──────────────────────────────────────────────────────────────────────────────

Appendix E — PR Checklist (copy-paste into PR body)

- [ ] Category set: static | regulation | patterns | growth | behavior  
- [ ] Deterministic core updated; DSL/Rule-pack if regulation  
- [ ] Evidence coverage ≥ 90% (attach merkle root/hash)  
- [ ] Unit + Integration + Golden + Contract tests PASS  
- [ ] Metrics & alerts updated; runbooks unchanged or updated  
- [ ] Feature flag path documented; rollback recipe included  
- [ ] Data residency/PII considerations documented

──────────────────────────────────────────────────────────────────────────────

Next Step (Single-Step Approval Gate)

Step-1: Approve the module contract & naming scheme (`logic_###_snake_case.py`) and the Evidence OS requirement.  
Once approved, proceed to Migration Phase 0 (Appendix “Migration Map”) without changing behavior: add evidence handles to the top 10 logics.

Author: Hardy • Last Updated: 2025-08-15
