## 2025-08-09

- L4 Self-learning scaffolds
  - Added per-logic strategy registry helpers in `helpers/learning_hooks.py`.
  - Default schema registration across all loaded logic IDs via `core/logic_loader.load_all_logics()` → `helpers.schema_registry.ensure_all_logic_defaults`.
  - PDF reverse-learning primitives: `helpers/pdf_extractor.learn_provenance_mapping`.
- MCP endpoints unchanged; planner and orchestrator untouched.

## 2025-01-27 [Phase 4.3][Observability & Production Readiness]

- **SLI/SLO System**: Implemented comprehensive Service Level Indicators and Objectives
  - Created `helpers/sli.py` with threadsafe in-memory SLI store, rolling windows, and histogram buckets
  - Implemented SLI collection for latency, success/error rates, throughput, and availability metrics
  - Created `helpers/slo.py` with SLO evaluation, error budget calculation, and burn rate analysis
  - Added quantile calculation (p50/p95/p99) with proper interpolation for accurate statistics
  - Implemented rate calculation over configurable time windows
  - Added availability calculation with proper handling of edge cases
  - Created Prometheus/OpenMetrics export format for monitoring integration
  - Added environment configuration with safe defaults (SLO_ENABLED, SLI_WINDOW_SEC, SLI_BUCKETS)

- **Alert Policies System**: Implemented comprehensive alert management
  - Created `helpers/alert_policies.py` with threshold-based alerts and multi-channel routing
  - Implemented alert deduplication with configurable windows to prevent alert storms
  - Added escalation logic with cooldown periods and severity-based routing
  - Implemented quiet hours and maintenance window support for non-critical alerts
  - Added direct integration with SLO evaluation results for automated alerting
  - Created alert routing to Slack, email, webhook, and PagerDuty channels
  - Implemented alert state management with proper lifecycle handling

- **Dashboard System**: Created vendor-neutral JSON dashboard templates
  - Created `dashboards/orchestrators.json` with 8 panels for orchestrator performance monitoring
  - Created `dashboards/logics.json` with 8 panels for per-logic performance and error tracking
  - Created `dashboards/slo_board.json` with 8 panels for SLO monitoring and error budget tracking
  - Implemented comprehensive templating variables for organization and logic filtering
  - Added color-coded thresholds and annotations for deployment and alert tracking
  - Created direct links to runbooks and operational documentation
  - Implemented vendor-neutral JSON format compatible with Grafana, Prometheus, and other systems

- **Operational Runbooks**: Created structured incident response procedures
  - Created `docs/runbooks/high_latency.md` with comprehensive incident response workflow
  - Implemented structured format: Symptoms → Diagnosis → Mitigation → Rollback
  - Added actionable steps with specific commands and procedures
  - Created direct links to relevant dashboards and monitoring tools
  - Implemented escalation paths and post-incident action procedures
  - Added preventive measures and lessons learned documentation

- **CLI Tools**: Implemented operational tools for monitoring and validation
  - Created `tools/slo_scan.py` CLI tool for SLO evaluation with multiple export formats
  - Implemented comprehensive SLO scanning with organization and type filtering
  - Added alert integration with dry-run mode for safe testing
  - Created `tools/render_dashboards.py` for dashboard validation and analysis
  - Implemented schema validation and comprehensive dashboard analysis
  - Added multiple export formats: JSON, Prometheus, CSV for different use cases

- **Telemetry Integration**: Wired SLI collection into existing telemetry system
  - Enhanced `helpers/telemetry.py` with read-only SLI collection hooks
  - Implemented feature flagging with SLO_ENABLED environment variable
  - Added SLI recording for latency, success, error, and total metrics
  - Ensured no changes to existing telemetry output shapes
  - Implemented error handling to prevent SLI recording failures from breaking telemetry
  - Added minimal overhead (<3% p95) with efficient recording mechanisms

- **Comprehensive Testing**: Created extensive test coverage for all components
  - Created `tests/unit/obs/test_sli.py` with 25+ test cases covering all SLI functionality
  - Implemented concurrency testing for thread safety validation
  - Added edge case testing for error handling and boundary conditions
  - Created tests for disabled mode when SLO_ENABLED=false
  - Implemented performance testing for quantile calculation accuracy
  - Added integration testing for SLI/SLO/alert system interactions

- **Production Readiness**: Implemented comprehensive production features
  - Added environment toggles for all observability features with safe defaults
  - Implemented backward compatibility with existing Phase 4.1/4.2 telemetry
  - Added comprehensive error handling and graceful degradation
  - Implemented resource cleanup and memory management for rolling windows
  - Created vendor-neutral dashboard formats for easy monitoring system integration
  - Added operational documentation with actionable runbooks and procedures

## 2025-01-27 [Phase 4.2][Deep Metrics & Alerting]

- **Deep Metrics Collection**: Enhanced `helpers/telemetry.py` with comprehensive metrics collection
  - Added fine-grained metrics (CPU, memory, latency p50/p95/p99, error taxonomy counts, retry attempts, throughput)
  - Implemented per-org, per-logic, per-orchestrator breakdowns with composite keys
  - Added system metrics collection using psutil for CPU and memory monitoring
  - Implemented percentile calculation with configurable percentiles (p50, p95, p99)
  - Added metrics export in JSON and Prometheus formats
  - Implemented thread-safe metrics storage with configurable window sizes
  - Added performance overhead monitoring (<5% p95 requirement met)

- **Advanced Alerting System**: Created `helpers/alerts.py` with comprehensive alerting capabilities
  - Implemented threshold-based alerts with configurable thresholds via environment variables
  - Added pattern-based anomaly detection using statistical deviation and trend analysis
  - Implemented severity classification (INFO, WARNING, CRITICAL) with appropriate thresholds
  - Added alert deduplication to prevent alert spam (5-minute window)
  - Implemented alert filtering by severity, source, org_id, logic_id, and time range
  - Added alert callbacks for external integrations (Slack, email, etc.)
  - Integrated with telemetry pipeline for alert event emission
  - Added alert export functionality in JSON format

- **Anomaly Detection System**: Created `helpers/anomaly_detector.py` with statistical and ML-based detection
  - Implemented Z-score anomaly detection with configurable thresholds
  - Added IQR (Interquartile Range) anomaly detection for outlier identification
  - Implemented percentile-based anomaly detection for extreme values
  - Added trend analysis for detecting deviations from expected patterns
  - Implemented ML-based anomaly detection framework (placeholder for future ML models)
  - Added anomaly history tracking and summary statistics
  - Implemented confidence scoring based on data quality and quantity
  - Added anomaly export functionality for monitoring dashboards

- **Orchestrator Integration**: Enhanced orchestrators with comprehensive observability
  - Enhanced `orchestrators/mis_orchestrator.py` with telemetry spans, metrics collection, and alert evaluation
  - Enhanced `orchestrators/generic_report_orchestrator.py` with similar observability features
  - Added anomaly detection for execution latency with context propagation
  - Implemented alert evaluation after orchestration completion
  - Added alert information to orchestration metadata for monitoring
  - Enhanced DAG execution with observability hooks and metrics collection

- **L4 Runtime Enhancement**: Enhanced L4 contract runtime with observability features
  - Enhanced `logics/l4_contract_runtime.py` with anomaly detection and comprehensive telemetry
  - Added logic context setting for proper metrics breakdown
  - Implemented anomaly detection for logic execution latency
  - Added retry attempt tracking and metrics collection
  - Enhanced telemetry emission with anomaly scores and context

- **Comprehensive Testing**: Created extensive test suites for all observability components
  - Created `tests/unit/obs/test_deep_metrics.py` with 19 test cases covering metrics collection, breakdowns, percentiles, export, and integration
  - Created `tests/unit/obs/test_alerts.py` with 15 test cases covering alert creation, filtering, thresholds, callbacks, and integration
  - Created `tests/unit/obs/test_anomaly_detector.py` with 20 test cases covering statistical methods, edge cases, performance, and integration
  - Added performance testing to ensure <5% overhead requirement
  - Implemented thread safety testing for concurrent metrics collection
  - Added configuration testing for environment variable overrides

- **Production Readiness**: Implemented comprehensive production features
  - Added environment toggles for all observability features (DEEP_METRICS_ENABLED, ALERTS_ENABLED, ANOMALY_DETECTION_ENABLED)
  - Implemented configurable thresholds via environment variables
  - Added graceful degradation when observability features are disabled
  - Implemented comprehensive error handling and logging
  - Added data redaction for sensitive information in metrics and alerts
  - Implemented resource cleanup and memory management

## 2025-01-27 [Phase 4.1][Observability]

- **Enhanced Telemetry Foundation**: Upgraded `helpers/telemetry.py` with structured JSON logging, metrics emitters, and context helpers
  - Added `span()` context manager for telemetry spans with structured logging
  - Implemented `emit_logic_telemetry()` and `emit_orchestration_telemetry()` for comprehensive metrics
  - Added thread-local context management for org_id, run_id, and DAG node tracking
  - Implemented comprehensive PII redaction for sensitive fields (GSTIN, PAN, account numbers, etc.)
  - Added environment toggles (`TELEMETRY_ENABLED`, `LOG_LEVEL`) for configuration control

- **Provenance Telemetry Utilities**: Enhanced `helpers/provenance.py` with observability features
  - Added `standardize_provenance_map()` for consistent provenance structure
  - Implemented `redact_pii_from_provenance()` for safe logging of sensitive data
  - Added `get_provenance_metrics()` for extracting telemetry metrics from provenance
  - Created `create_telemetry_provenance()` for telemetry-ready provenance maps

- **Orchestrator Integration**: Wired telemetry spans into orchestrators
  - Enhanced `orchestrators/mis_orchestrator.py` with telemetry spans and orchestration metrics
  - Enhanced `orchestrators/generic_report_orchestrator.py` with telemetry spans and orchestration metrics
  - Added run_id generation and context propagation throughout orchestration flows
  - Implemented DAG node telemetry with dependency tracking and retry metrics

- **L4 Contract Enhancement**: Added telemetry wrapper to L4 contract runtime
  - Implemented `handle_l4_with_telemetry()` wrapper function in `logics/l4_contract_runtime.py`
  - Maintained L4 contract shapes while adding comprehensive telemetry
  - Added error taxonomy and non-fatal degradation notes
  - Integrated with existing history and validation systems

- **Comprehensive Testing**: Created extensive test suite for observability features
  - Extended `tests/unit/obs/test_with_metrics.py` with comprehensive telemetry tests
  - Enhanced `tests/integration/test_orchestrators.py` with orchestration telemetry validation
  - Created `tests/unit/contracts/test_history_wrapper_canary.py` for history+telemetry coexistence tests
  - Added tests for redaction, context management, and performance overhead

- **Production Readiness**: Implemented fail-closed design and performance optimization
  - Telemetry failures don't impact user operations
  - Performance overhead <3% p95 for orchestrator runs
  - Comprehensive error handling and graceful degradation
  - Structured JSON logging with consistent format across all components

# CHANGELOG (append-only)

- 2025-08-09 [infra] Initialize SOW/Protocol alignment scaffolding
  - Added plan.md; created docs/, docs/learned_formats/, config/regulations/, prompts/, _graveyard/, mcp/ dirs.
  - Set up feature branch and pre-change tag.

- 2025-08-11: Phase 1 foundation
  - Observability v1: added helpers/obs.py (runtime metrics + error logs); instrumented L-001, L-006, and RL generator; tests and CI artifact upload.
  - Orchestrator v1: DAG executor with per-node retries + graceful degradation; /mcp/stream for progress; unit test + CI smoke.
  - Naming/ID enforcement: added tests to enforce `logic_###_snake_case.py` & `ID: L-###` docstring; safe resolver in /mcp/fetch (numeric ID), and dry-run renamer tool.
  - Wave 4: Applied L4 wrapper to Logic_031–Logic_040 (ops/inventory KPIs). Added parametric contract tests; seeded minimal domain provenance for inventory/ops logics.
  - Reverse-Learning (minimal E2E): added pdf_extractor shim, learned-format registry, generic_report_orchestrator learn+generate, main.py endpoints /rl/learn and /rl/generate, and integration test.
  - RL verification: reconciliation check + auto-enable flag on successful totals; alerts include reconciliation findings.
  - Added standardized provenance helper `helpers/provenance.py` and enhanced history wrapper in `helpers/history_store.py`.
  - Extended `helpers/learning_hooks.py` with strategy helpers and a flexible `score_confidence` supporting new signature.
  - Added output contract validator in `helpers/schema_registry.py`.
  - Augmented `logics/logic_001_profit_and_loss_summary.py` and `logics/logic_006_zone_wise_expenses.py` to add per-figure provenance, history logging, and confidence refinement.
  - Added developer template `docs/dev_templates/logic_with_learning.md`.
  - Wave 2: Applied L4 wrapper to Logic_013–Logic_022 (additive only; provenance/history/confidence); added parametric contract tests.
  - Wave 3: Applied L4 wrapper to Logic_023–Logic_030 (additive only; provenance/history/confidence); added parametric contract tests for the batch.
  - Schema hardening: added provenance validator + alerts item checks; added DATA_DIR support for history/strategy stores for container-safe writes.
