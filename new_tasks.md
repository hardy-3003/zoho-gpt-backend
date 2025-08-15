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
