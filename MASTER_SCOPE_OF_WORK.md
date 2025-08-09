# Accounting Auto‑Auditable Backend (MCP‑Ready) — **MASTER SCOPE OF WORK**
**Version:** 2025-08-08 • **Owner:** Hardik • **Status:** Living document (authoritative)

> This file is the single source of truth for scope, principles, and structure. 
> Keep and re‑share this file if anything ever resets.


---

## 0) Ground Rules (L4 — Autonomous, Closed‑Loop Evolution)
**Applies to every logic module (.py) and every integration.**
1. **Self‑Learning:** Each logic improves over time from new inputs, user corrections, and usage patterns. Include hooks/placeholders for GPT‑based evaluations, pattern extraction, confidence scoring, and retry logic.
2. **History‑Aware:** Persist changelogs for invoices, bills, POs, salaries, items, taxes, etc. Track price changes, deltas by period, vendor and cross‑org deviation. Enable anomaly flags for manipulation and inconsistent trends.
3. **Reverse‑Learning from Custom Inputs:** On an unfamiliar report (e.g., new MIS PDF), auto‑extract fields, map each figure to its Zoho origin, learn the format, and generate it next time without help. Log every new format learned.
4. **Expandable in the Same File:** Logic must grow inside its own .py (internal subtrees/strategies). Create new files only for base helpers/shared utilities.
5. **Smart Accounting Validation:** Autonomously check for accounting rule violations (unbalanced reversals, mismatched categories, missing journals, date anomalies) and suggest fixes.
6. **No Rewrites:** Everything is upgradable; no “start from scratch.” Migrations and adapters preserve behavior while extending capability.
7. **Many‑to‑One Orchestration:** Reports (e.g., MIS) are composed by mediator/orchestrator modules that can call **2 → ∞** logics. Configurable pipelines, partial retries, graceful degradation.
8. **Auto‑Expansion:** From repeated requests/patterns, auto‑create/extend logic stubs (e.g., inferred `client_trend_analysis`) and register them safely with tests and guardrails.

---

## 1) Architecture & Folder Layout
```
repo/
  main.py                      # FastAPI app, MCP endpoints, tool router
  /logics/                     # 200+ operate files (one per logic, L4-compliant)
    logic_001_profit_loss.py
    ...
    logic_200_vendor_side_carbon_emissions_estimator.py
  /orchestrators/              # Mediators for multi-logic reports (e.g., MIS)
    mis_orchestrator.py
    generic_report_orchestrator.py
  /helpers/                    # Shared utilities (no business logic)
    zoho_client.py             # Auth, rate limiting, retries, caching
    pdf_extractor.py           # OCR/parse, table/field detection
    schema_registry.py         # JSONSchemas for inputs/outputs
    rules_engine.py            # Validations & guardrails
    history_store.py           # Append-only event log (queries, deltas, versions)
    learning_hooks.py          # Self-learning interfaces & scoring
  /analyzers/                  # Anomaly detectors, trend engines
    anomaly_engine.py
    delta_compare.py
  /prompts/                    # Few-shot prompts & guidance (if/when LLM used)
  /tests/                      # Unit, integration, contract tests
  /docs/                       # ADRs, SOPs, how-tos
```

**Key tenets**
- **MCP‑ready**: `/mcp/manifest`, `/mcp/search`, `/mcp/fetch` with POST support; SSE where applicable.
- **Front‑end agnostic**: No hard dependency on ChatGPT UI; callable from any client.
- **Observability**: Structured logs + metrics per logic and per orchestrated pipeline.
- **Security**: AuthN/Z for sensitive endpoints (`/generate_mis`, `/save_credentials`), rate limiting, input schemas.

---

## 2) Logic Module Contract (Template)
Each logic file **must implement**:
```python
# logic_xxx_example.py
\"\"\"
Title: <Human-friendly name>
ID: L-XXX
Tags: ["mis","pnl","compliance"]
Parent Logic: <optional>
Required Inputs: <typed schema or JSONSchema ref>
Outputs: <typed schema>
Assumptions: <explicit>
Evolution Notes: <how it self-learns; registries used>
\"\"\"

from typing import Any, Dict
from helpers.learning_hooks import record_feedback, score_confidence
from helpers.history_store import write_event
from helpers.rules_engine import validate_accounting

def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    # 1) Validate & parse inputs (schema_registry)
    # 2) Fetch source data (zoho_client)
    # 3) Compute result (deterministic core)
    # 4) Run accounting validations
    # 5) Log history + deltas
    # 6) Self-learning hooks (update strategy weights, add patterns)
    # 7) Return outputs with confidence & provenance map
    return {
      "result": ...,
      "provenance": {...},  # zoho endpoints/ids that produced each figure
      "confidence": score_confidence(...),
      "alerts": [...],      # anomalies / rule violations
    }
```

**Self‑learning inside the file**
- Keep a small **strategy registry** (JSON or lightweight state) per logic to add variants/heuristics over time.
- Always record **provenance** (which Zoho entity/endpoint produced each figure).

---

## 3) Orchestration (2 → ∞ logics)
- **Graph‑based execution**: orchestrators define DAGs of logic calls with declared inputs/outputs.
- **Partial failure tolerance**: continue with available results; annotate missing pieces.
- **Auto‑discovery**: orchestrator can discover and include new logics matching tags/rules.
- **Mediator examples**:
  - `mis_orchestrator.py` (configurable sections using 10–300+ logics)
  - `generic_report_orchestrator.py` (learned formats from PDFs/templates)

---

## 4) Reverse‑Learning Pipeline (New MIS PDFs → Working Generators)
1. **Ingest** PDF → `pdf_extractor.py` parses tables/labels/values.
2. **Field candidate mapping** to Zoho via heuristics + nomenclature maps.
3. **Provenance learning**: persist a mapping (field → Zoho endpoint/filter/path).
4. **Schema capture**: register new report schema; version it.
5. **Verification pass**: reconcile against totals/subtotals; highlight mismatches.
6. **Auto‑enable generation** next time; expose as an orchestrated report.

---

## 5) History, Deltas & Anomaly Detection
- **history_store**: append-only events: inputs, outputs, data snapshots, diffs.
- **delta_compare**: period‑to‑period (YoY, MoM), cross‑org, vendor‑wise.
- **anomaly_engine**: rules + heuristics (e.g., backdated entry spikes, round‑off abuse, category drift).

---

## 6) Testing, Observability, and Upgrades
- **Tests**: unit per logic; integration for orchestrators; contract tests for Zoho APIs.
- **Telemetry**: per logic runtime, cache hit rate, error taxonomy, anomaly counts.
- **Upgrades**: adapters for signature changes; migration scripts for learned schemas; never rewrite from zero.

---

## 7) MCP Endpoints (Behavioral Spec)
- `/mcp/manifest`: declares tools/inputs/outputs; versioned.
- `/mcp/search` (POST): understands natural language to logic selection/plan.
- `/mcp/fetch` (POST): executes logic or orchestrated plans; streams progress if SSE enabled.
- **Security**: token‑scoped per org; redaction for exports; rate limiters.

---

## 8) **Master Logic Index (200 modules, live)**
The following list is authoritative and will continue to grow.  
**Implementation rule:** one file per logic in `/logics/` named `logic_###_snake_case.py`.

# 🧠 MASTER LOGIC FILE LIST

## ✅ 1–102 Original Business Logic Modules

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
16. GSTR Filing Status
17. TDS Filing Status
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
39. Tax Summary Report
40. GST Reconciliation Status
41. TDS Deducted vs Paid
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
75. Error Detection Engine
76. Anomaly Detection Report
77. Vendor Duplication Check
78. Client Duplication Check
79. Data Entry Consistency
80. Duplicate Invoice Detection
81. Outlier Expenses Detection
82. Salary vs Market Benchmark
83. Tax Liability Estimator
84. Input Tax Credit Reconciliation
85. Late Filing Penalty Tracker
86. Missed Payment Tracker
87. Recurring Expenses Monitor
88. Profit Leakage Detector
89. Unbilled Revenue Tracker
90. Advance Received Adjustment
91. Advance Paid Adjustment
92. Suspense Account Monitor
93. Accounting Hygiene Score
94. Business Health Score
95. Scenario Simulation Engine
96. Expense Optimization Engine
97. Credit Rating Estimator
98. Business Valuation Estimator
99. Dividend Recommendation Engine
100. Risk Assessment Matrix
101. Cash Reserve Advisor
102. Strategic Suggestion Engine

---

## ➕ New Logics for Advanced Auditing + AI Intelligence

103. Auto Reconciliation Suggestion
104. Fabrication vs Billing Variance
105. BOQ vs Actual Cost
106. Material Rate Change Monitor
107. Inter-Branch Transfer Log
108. Employee Reimbursement Check
109. Pending Approvals Summary
110. Backdated Entry Detector
111. Late Vendor Payment Penalty Alert
112. Margin Pressure Tracker (Cost ↑ vs Price ↔)
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
125. Inventory Shrinkage Alert
## L-126–L-145 Inventory/Production/Fleet (Deep Spec)
126. Inventory Turnover Ratio
127. Stockout Frequency Alert
128. Excess Inventory Analysis
129. Demand Forecast Accuracy (MAPE)
130. Order Fulfillment Cycle Time
131. Supplier Lead Time Variability
132. Production Capacity Utilization
133. Production Downtime Analysis
134. Scrap Rate Monitor
135. Machine Efficiency Tracker (OEE)
136. Batch Yield Analysis
137. Quality Defect Rate
138. Return Rate Analysis
139. Warranty Claims Monitor
140. Customer Order Accuracy
141. On-time Delivery Rate
142. Transportation Cost Analysis
143. Fleet Utilization Rate
144. Fuel Consumption Tracker
145. Route Optimization Alerts
146. Zone-wise Carbon Score
147. Green Vendor Scorecard
148. Data Redundancy Detector
149. Audit Flag Generator (AI Marked High Risk Areas)
150. CA Review Ready Index

## 💡 Expandable Future Logics (for SaaS-level maturity)

151. Audit Automation Wizard (Step-by-step walkthrough)
152. Auto-Fill for Common Journal Entries (AI trained on history)
153. Period Lock & Unlock Tracker
154. Custom Rule Builder (for clients using SaaS version)
155. CFO Dashboard Generator
156. Financial KPI Designer
157. Self-learning Prediction Engine (for revenue/expense)
158. Multi-company Consolidation Reports
159. Alerts via Telegram/Slack/Email/WhatsApp
160. Custom User Access Logs and Abuse Detection
161. File Upload to Entry Mapper (e.g., Invoice PDF → JE)
162. Voice-to-Entry (convert spoken input to journal)
163. Advanced Filing Calendar Sync (GST, ROC, TDS)
164. API-based Third Party Integration Framework
165. Bank Feed Intelligence Layer
166. Year-end Closure Guide
167. Investment vs Working Capital Allocator
168. Performance Linked Pay Analyzer
169. Cross-company Loan Tracker
170. Government Scheme Utilization Tracker
171. Legal Case Cost Monitor
172. Automation of Monthly Compliance Summary
173. DSCR and ICR Calculators for Banking
174. Auto CA Remarks Based on Reports
175. User Behavior Based Module Suggestions
176. Scoring System for Business Maturity Level
177. CA Review Collaboration Toolkit
178. AI-Powered Explanation Tool (Explain balance sheet in plain Hindi)
179. Journal Trace Visualizer (graph view of entry relationships)
180. Interlinked Report Mapper

## L-181–L-200 Advanced Auditing + AI (Moved from 126–145)
181. Transaction Volume Spike Alert (moved from 126)
182. Overdue TDS Deduction Cases (moved from 127)
183. Related Party Transaction Tracker (moved from 128)
184. Vendor Contract Expiry Alert (moved from 129)
185. Unverified GSTIN Alert (moved from 130)
186. HSN-SAC Mapping Auditor (moved from 131)
187. AI Error Suggestion Engine (moved from 132)
188. Report Consistency Verifier (across months) (moved from 133)
189. Audit-Ready Report Generator (moved from 134)
190. Internal Control Weakness Identifier (moved from 135)
191. Monthly Report Completeness Checker (moved from 136)
192. Suggested Journal Entry Fixes (moved from 137)
193. Pending JE Approvals (moved from 138)
194. Partial Payments Tracker (moved from 139)
195. Reverse Charge Monitor (GST) (moved from 140)
196. P&L Ratio Anomaly Finder (moved from 141)
197. Mismatch in Payment vs Invoice Timeline (moved from 142)
198. Free Resource Usage Estimator (Power, Tools, etc.) (moved from 143)
199. Industry Benchmark Comparison Report (moved from 144)
200. Vendor-side Carbon Emissions Estimator (moved from 145)

---

## 💡 Expandable Future Logics (for SaaS-level maturity)

151. Audit Automation Wizard (Step-by-step walkthrough)
152. Auto-Fill for Common Journal Entries (AI trained on history)
153. Period Lock & Unlock Tracker
154. Custom Rule Builder (for clients using SaaS version)
155. CFO Dashboard Generator
156. Financial KPI Designer
157. Self-learning Prediction Engine (for revenue/expense)
158. Multi-company Consolidation Reports
159. Alerts via Telegram/Slack/Email/WhatsApp
160. Custom User Access Logs and Abuse Detection
161. File Upload to Entry Mapper (e.g., Invoice PDF → JE)
162. Voice-to-Entry (convert spoken input to journal)
163. Advanced Filing Calendar Sync (GST, ROC, TDS)
164. API-based Third Party Integration Framework
165. Bank Feed Intelligence Layer
166. Year-end Closure Guide
167. Investment vs Working Capital Allocator
168. Performance Linked Pay Analyzer
169. Cross-company Loan Tracker
170. Government Scheme Utilization Tracker
171. Legal Case Cost Monitor
172. Automation of Monthly Compliance Summary
173. DSCR and ICR Calculators for Banking
174. Auto CA Remarks Based on Reports
175. User Behavior Based Module Suggestions
176. Scoring System for Business Maturity Level
177. CA Review Collaboration Toolkit
178. AI-Powered Explanation Tool (Explain balance sheet in plain Hindi)
179. Journal Trace Visualizer (graph view of entry relationships)
180. Interlinked Report Mapper

---

✅ Total Logics So Far: **200 and expanding**

This list is modular, meaning you can:
- Create `logics/logic_001_profit_loss.py` → `logic_200_vendor_side_carbon_emissions_estimator.py`
- Each file contains 1 `handle(query)` or similar
- All are auto-registered via your loader in `main.py` for `/mcp/fetch` or API

---

### 📑 Logic Category Annotations (Static vs Dynamic)

**Purpose:** This table classifies each logic in the Master Logic Index according to its nature and how it should evolve.

- **Static** = Core accounting/reporting functions. Logic rarely changes unless optimized or improved for performance/readability.
- **Dynamic (Regulation)** = Changes automatically when laws or compliance rules change (e.g., ITD/GST/TDS).
- **Dynamic (Patterns)** = Evolves based on anomaly detection, historical data drift, or detected irregularities.
- **Dynamic (Growth)** = Expands with business growth, new operational features, or SaaS-level enhancements.
- **Dynamic (Behavior)** = Learns from user requests, usage patterns, and reverse-learning of new formats.

| #   | Logic Name | Category | Rationale |
|-----|------------|----------|-----------|
| 1   | Profit and Loss Summary | Static | Canonical accounting statement |
| 2   | Balance Sheet | Static | Standard financial statement |
| 3   | Trial Balance | Static | Core ledger validation report |
| 4   | Capital Account Summary | Static | Standard capital tracking |
| 5   | Partner Withdrawals | Static | Deterministic calculation |
| 6   | Zone-wise Expenses | Static | Simple aggregation |
| 16  | GSTR Filing Status | Dynamic (Regulation) | Bound to GST compliance rules |
| 17  | TDS Filing Status | Dynamic (Regulation) | Bound to TDS law changes |
| 39  | Tax Summary Report | Dynamic (Regulation) | Updates when tax rates change |
| 40  | GST Reconciliation Status | Dynamic (Regulation) | Follows GSTN format changes |
| 41  | TDS Deducted vs Paid | Dynamic (Regulation) | Updates with TDS thresholds |
| 75  | Error Detection Engine | Dynamic (Patterns) | Evolves with anomaly heuristics |
| 76  | Anomaly Detection Report | Dynamic (Patterns) | Learns from history_store |
| 83  | Tax Liability Estimator | Dynamic (Regulation) | Adapts to ITD circulars |
| 85  | Late Filing Penalty Tracker | Dynamic (Regulation) | Follows compliance timelines |
| 88  | Profit Leakage Detector | Dynamic (Patterns) | Learns from repeated leaks |
| 92  | Suspense Account Monitor | Dynamic (Patterns) | Flags unusual journal entries |
| 93  | Accounting Hygiene Score | Dynamic (Patterns) | Scoring changes with usage |
| 95  | Scenario Simulation Engine | Dynamic (Growth) | Expands with new scenario types |
| 97  | Credit Rating Estimator | Dynamic (Growth) | Grows with more parameters |
| 151 | Audit Automation Wizard | Dynamic (Behavior) | Learns new audit steps |
| 161 | File Upload to Entry Mapper | Dynamic (Behavior) | Adapts to new file formats |
| 174 | Auto CA Remarks Based on Reports | Dynamic (Behavior) | Expands commentary with use |
| 178 | AI-Powered Explanation Tool | Dynamic (Behavior) | Learns to explain new terms |
| 179 | Journal Trace Visualizer | Dynamic (Behavior) | Expands with new trace types |
| 180 | Interlinked Report Mapper | Dynamic (Behavior) | Grows with linked report types |

_Note:_ All Dynamic logics follow L4 rules: they can self-learn, update rulesets, or spawn new stubs when triggered by relevant events.

---

## 9) Acceptance & Next Step (single step at a time)
**Step‑1 for approval:** Confirm the **module contract** (Section 2) and the **naming scheme** (`logic_###_name.py`).  
