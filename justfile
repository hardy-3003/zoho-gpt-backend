# One-Command Dev Setup for Zoho GPT Backend
# Task P1.1.2 — One-Command Dev

# Default target
default:
    @just --list

# Main development command - boots API with hot reload, runs tests in watch mode
dev:
    @echo "🚀 Starting Zoho GPT Backend Development Environment"
    @echo "📋 Prerequisites: Python 3.11+, pip, just"
    @echo ""
    @echo "🔧 Setting up environment..."
    @just setup
    @echo ""
    @echo "🌐 Starting API server with hot reload..."
    @echo "   API: http://localhost:8000"
    @echo "   Health: http://localhost:8000/health"
    @echo "   Docs: http://localhost:8000/docs"
    @echo ""
    @echo "🧪 Starting test watcher..."
    @echo "   Tests will run automatically on file changes"
    @echo ""
    @echo "📊 Starting local dashboards (if available)..."
    @just start-dashboards
    @echo ""
    @echo "✅ Development environment ready!"
    @echo "   Press Ctrl+C to stop all services"
    @echo ""
    # Start API server with hot reload and test watcher in parallel
    @just start-api & just start-test-watch & wait

# Setup development environment
setup:
    @echo "📦 Installing dependencies..."
    python3 -m pip install -U pip
    pip3 install -r requirements-dev.txt
    @echo "✅ Dependencies installed"

# Start FastAPI server with hot reload
start-api:
    @echo "🌐 Starting FastAPI server..."
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload --log-level info

# Start test watcher
start-test-watch:
    @echo "🧪 Starting test watcher..."
    pytest tests/ --watch --watch-delay 2 -v

# Start local dashboards (stub for now)
start-dashboards:
    @echo "📊 Local dashboards: Not implemented yet"
    @echo "   Future: Grafana, Prometheus, etc."

# Run all tests
test:
    @echo "🧪 Running all tests..."
    pytest tests/ -v --cov=logics --cov=helpers --cov=orchestrators --cov-report=term-missing
    @echo "✅ Tests completed"

# Run linting checks
lint:
    @echo "🔍 Running linting checks..."
    ruff check .
    @echo "✅ Linting completed"

# Run ID policy linting
id-lint:
    @echo "🔍 Running ID policy linting..."
    python3 scripts/id_linter.py
    @echo "✅ ID policy linting completed"

# Run type checking
type:
    @echo "🔍 Running type checking..."
    mypy logics/ helpers/ orchestrators/ core/ main.py
    @echo "✅ Type checking completed"

# Run code formatting
fmt:
    @echo "🎨 Running code formatting..."
    black .
    ruff format .
    @echo "✅ Formatting completed"

# Run contract snapshot generation
contract-snapshots:
    @echo "📋 Generating contract snapshots..."
    python3 tools/gen_contract_snapshots.py
    @echo "✅ Contract snapshots generated"

# Run contract tests
contract-test:
    @echo "🧪 Running contract tests..."
    pytest tests/contract/ -v
    @echo "✅ Contract tests completed"

# Run execute endpoint contract tests
execute-contract-test:
    @echo "🧪 Running execute endpoint contract tests..."
    pytest tests/contract/test_execute.py -v
    @echo "✅ Execute contract tests completed"

# Run SSE endpoint contract tests
sse-contract-test:
    @echo "🧪 Running SSE endpoint contract tests..."
    pytest tests/contract/test_sse.py -v
    @echo "✅ SSE contract tests completed"

# Run webhooks contract tests
webhooks-contract-test:
    @echo "🧪 Running webhooks contract tests..."
    pytest tests/contract/test_webhooks.py -v
    @echo "✅ Webhooks contract tests completed"

# Run CLI contract tests
cli-contract-test:
    @echo "🧪 Running CLI contract tests..."
    pytest tests/contract/test_cli.py -v
    @echo "✅ CLI contract tests completed"

# Run evidence tests
evidence-test:
    @echo "🧪 Running evidence OS tests..."
    pytest tests/evidence/ -v --cov=evidence --cov-report=term-missing
    @echo "✅ Evidence tests completed"

# Run consent tests
consent-test:
    @echo "🧪 Running consent tests..."
    pytest tests/consent/ -v
    @echo "✅ Consent tests completed"

# Run all CI checks locally
ci-local:
    @echo "🔧 Running CI checks locally..."
    @echo "1/7: Linting..."
    @just lint
    @echo "2/7: Type checking..."
    @just type
    @echo "3/7: Unit tests..."
    pytest tests/unit/ -v --cov=logics --cov=helpers --cov=orchestrators --cov-report=xml
    @echo "4/7: Integration tests..."
    pytest tests/integration/ -v
    @echo "5/7: Performance tests..."
    pytest tests/performance/ -v
    @echo "6/7: Contract tests..."
    @just contract-test
    @echo "7/7: Security checks..."
    bandit -r logics/ helpers/ orchestrators/ core/ main.py
    safety check
    @echo "✅ All CI checks passed locally!"

# Generate SBOM
sbom:
    @echo "📋 Generating Software Bill of Materials..."
    # Note: This is a placeholder until cyclonedx-python-lib is properly configured
    @echo "SBOM generation: Not fully implemented yet"
    @echo "   Future: cyclonedx-python-lib integration"
    @echo "✅ SBOM placeholder completed"

# Clean up development artifacts
clean:
    @echo "🧹 Cleaning up development artifacts..."
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name ".coverage" -delete 2>/dev/null || true
    @echo "✅ Cleanup completed"

# Install just if not available
install-just:
    @echo "📦 Installing just command runner..."
    @echo "Please install just manually if not already installed:"
    @echo "  macOS: brew install just"
    @echo "  Linux: cargo install just"
    @echo "  Windows: cargo install just"
    @echo "  Or visit: https://just.systems/man/en/"

# Show help
help:
    @echo "Zoho GPT Backend - Development Commands"
    @echo ""
    @echo "Main commands:"
    @echo "  just dev              - Start full development environment (API + tests + dashboards)"
    @echo "  just test             - Run all tests"
    @echo "  just lint             - Run linting checks"
    @echo "  just type             - Run type checking"
    @echo "  just fmt              - Format code"
    @echo "  just ci-local         - Run all CI checks locally"
    @echo "  just contract-snapshots - Generate contract snapshots"
    @echo "  just contract-test    - Run contract shape tests"
    @echo "  just execute-contract-test - Run execute endpoint contract tests"
    @echo "  just sse-contract-test - Run SSE endpoint contract tests"
    @echo "  just webhooks-contract-test - Run webhooks contract tests"
    @echo "  just cli-contract-test - Run CLI contract tests"
    @echo "  just evidence-test    - Run evidence OS tests"
    @echo "  just sbom             - Generate Software Bill of Materials"
    @echo "  just master-index     - Build canonical MASTER index (231)"
    @echo "  just master-index-check - Run MASTER index tests"
    @echo "  just l4-readiness     - Audit L4 readiness & pretty-print report"
    @echo "  just l4-readiness-check - Run L4 readiness tests"
    @echo ""
    @echo "Utility commands:"
    @echo "  just setup            - Install dependencies"
    @echo "  just clean            - Clean development artifacts"
    @echo "  just install-just     - Install just command runner"
    @echo "  just help             - Show this help"
    @echo ""
    @echo "Prerequisites:"
    @echo "  - Python 3.11+"
    @echo "  - pip"
    @echo "  - just (install with: just install-just)"

# Repo inventory scanner
repo-inventory:
    @echo "🔎 Scanning repo inventory (logics/) and comparing with MASTER..."
    python3 tools/scan_repo_logics.py --summary
    @echo "📄 artifacts/repo_logics.json"
    @echo "📄 artifacts/master_vs_repo_report.json"

repo-inventory-check:
    @echo "🧪 Running repo inventory tests..."
    pytest -q tests/master/test_repo_inventory.py

# L4 base tests (P1.5.4)
l4-test:
    @echo "🧪 Running L4 base tests..."
    pytest -q tests/l4

# Scaffold missing logic stubs (P1.5.3)
scaffold-missing:
    @echo "🧱 Scaffolding missing logics from artifacts/master_vs_repo_report.json..."
    python3 tools/scaffold_missing_logics.py --yes

# Coverage audit: scan and pretty-print counts
coverage-audit:
    @echo "📊 Running coverage audit (MASTER vs repo)..."
    python3 tools/scan_repo_logics.py --summary
    @echo ""
    @echo "Counts:"
    python3 - <<'PY'
import json, pathlib
p = pathlib.Path('artifacts/master_vs_repo_report.json')
obj = json.loads(p.read_text(encoding='utf-8'))
print(json.dumps({k: len(obj.get(k, [])) for k in ['missing_in_repo','extra_in_repo','slug_mismatches','path_mismatches','duplicate_ids']}, sort_keys=True))
PY

# Coverage check: run scaffold test
coverage-check:
    @echo "🧪 Running scaffold missing coverage test..."
    pytest -q tests/master/test_scaffold_missing.py

# Observability tests
obs-test:
    @echo "🩺 Running observability tests..."
    pytest -q tests/obs

# Run regulatory loader tests
regulatory-test:
    @echo "🧪 Running regulatory loader tests..."
    pytest tests/regulatory/ -v

# Golden tests
golden-test:
    @echo "🟡 Running golden tests..."
    pytest tests/golden/ -v

golden-rebuild CASE="":
    @echo "🛠️  Rebuilding golden expected.json files..."
    if [ "${CASE}" = "" ]; then \
        python3 tools/gen_golden.py; \
    else \
        python3 tools/gen_golden.py --case "${CASE}"; \
    fi

# Replay (Evidence) golden runner
replay-test:
    @echo "🔁 Running replay tests..."
    pytest tests/replay/ -v
    @echo "✅ Replay tests completed"

replay-run CASE="":
    @echo "🔁 Running replay for case: ${CASE}"
    if [ "${CASE}" = "" ]; then \
        python3 -m tools.replay_runner run-all; \
    else \
        python3 -m tools.replay_runner run --case "${CASE}"; \
    fi

replay-freeze CASE="":
    @echo "🧊 Freezing expected hash for case: ${CASE}"
    if [ "${CASE}" = "" ]; then \
        echo "ERROR: Provide CASE=<name>"; \
        exit 2; \
    fi
    python3 -m tools.replay_runner freeze --case "${CASE}"

# Master index (authoritative 231)
master-index:
    @echo "📚 Extracting MASTER index → artifacts/master_index.json"
    python3 tools/extract_master_index.py --summary
    @echo "✅ Done"

master-index-check:
    @echo "🔎 Running MASTER index tests..."
    pytest -q tests/master/test_master_index.py
    @echo "✅ MASTER index checks passed"

# L4 readiness auditor (P1.5.5)
l4-readiness:
    @echo "🧪 Auditing L4 readiness (231/231 coverage & adapters)..."
    python3 tools/audit_l4_readiness.py && jq . artifacts/l4_readiness_report.json || true

l4-readiness-check:
    @echo "🧪 Running L4 readiness tests..."
    pytest -q tests/master/test_l4_readiness.py

# Soft gates added for Phase-1 Exit
traceability:
    python3 tools/traceability_check.py

dep-audit:
    python3 tools/dep_audit.py

parity-smoke:
    pytest -q tests/parity/test_parity_smoke.py

perf-baseline:
    pytest -q tests/perf/test_perf_baseline.py
