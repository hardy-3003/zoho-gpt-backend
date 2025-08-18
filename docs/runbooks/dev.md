# Development Runbook

**Task P1.1.2 — One-Command Dev**  
**Version:** 1.0  
**Last Updated:** 2025-01-27  

## Overview

This runbook describes how to set up and use the one-command development environment for the Zoho GPT Backend. The setup provides a complete development experience with hot reload, test watching, and local dashboards.

## Phase-1 Exit (Foundations) — 2025-08-18

- All hard gates green locally: lint, type, unit, integration, contract, golden, id_policy, master_index_check, repo_inventory_check, l4_readiness_gate, replay (stub), perf baseline (stub).
- Deterministic artifacts refreshed and committed: `artifacts/master_index.json`, `artifacts/repo_logics.json`, `artifacts/master_vs_repo_report.json`, `artifacts/l4_readiness_report.json`, `artifacts/contract_snapshots.json`.
- Non-MCP contracts live (`/api/execute`, `/sse`, `/webhooks`, CLI); Evidence & Regulatory bases live; discovery count = 231.

### Phase-1 Exit — How to re-run locally

```bash
python -m venv .venv && source .venv/bin/activate
export PYTHONHASHSEED=0 LC_ALL=C LANG=C.UTF-8
pip install -r requirements.txt -r requirements-dev.txt

# Deterministic artifacts (only if intentional changes)
just contract-snapshots
just golden-rebuild CASE=
just replay-freeze CASE=
just master-index
just repo-inventory
just l4-readiness

# Hard gates
just lint
just type
just test
just contract-test
just golden-test
just replay-test
just id-lint
just master-index
just repo-inventory
just coverage-audit
just l4-readiness
just evidence-test
just regulatory-test
just obs-test

# Soft gates (non-blocking)
just parity-smoke || true
just traceability || true
just dep-audit || true
just perf-baseline || true
```

Checklist
- Contracts live (REST `/api/execute`, SSE `/sse`, CLI) — deterministic
- Evidence OS + Regulatory OS — tests green
- 231/231 present and indexed; ID policy/inventories clean
- L-231 and ratio helpers/configs exist
- L4 base present; readiness report ready==231
- Golden & Replay gates pass
- Observability: structured logs + `/metrics.json` working
- CI jobs green for: `lint`, `type`, `unit`, `contract`, `golden`, `id_policy`, `master_index_check`, `repo_inventory_check`, `logic_coverage_gate`, `l4_readiness_gate`, `traceability`, `dependency_audit`, `parity_smoke`, `replay_golden`, `perf_baseline`

## Prerequisites

### Required Software
- **Python 3.11+** - Core runtime
- **pip** - Package manager
- **just** - Command runner (install with `just install-just`)

### Optional Software
- **Git** - Version control
- **VS Code** - Recommended IDE with Python extension

## Quick Start

### 1. Clone the Repository
```bash
git clone <repository-url>
cd zoho-gpt-backend
```

### 2. Install just (if not already installed)
```bash
just install-just
```

### 3. Start Development Environment
```bash
just dev
```

This single command will:
- Install all dependencies
- Start the FastAPI server with hot reload on port 8000
- Start test watcher that runs tests automatically on file changes
- Start local dashboards (when implemented)
- Display success banner with URLs and ports

## Available Commands

### Main Development Commands

| Command | Description | Exit Code |
|---------|-------------|-----------|
| `just dev` | Start full development environment | 0 on success, non-zero on failure |
| `just test` | Run all tests with coverage | 0 on success, non-zero on failure |
| `just lint` | Run linting checks (ruff) | 0 on success, non-zero on failure |
| `just id-lint` | Run ID policy linting (logic file naming & coverage) | 0 on success, non-zero on failure |
| `just type` | Run type checking (mypy) | 0 on success, non-zero on failure |
| `just fmt` | Format code (black + ruff) | 0 on success, non-zero on failure |
| `just contract-snapshots` | Generate contract hash snapshots | 0 on success, non-zero on failure |
| `just contract-test` | Run contract shape tests | 0 on success, non-zero on failure |
| `just ci-local` | Run all CI checks locally | 0 on success, non-zero on failure |
| `just sbom` | Generate Software Bill of Materials | 0 on success, non-zero on failure |
| `just execute-contract-test` | Run execute endpoint contract tests | 0 on success, non-zero on failure |
| `just webhooks-contract-test` | Run webhooks contract tests | 0 on success, non-zero on failure |
| `just evidence-test` | Run evidence OS tests | 0 on success, non-zero on failure |
| `just replay-test` | Run evidence replay tests | 0 on success, non-zero on failure |
| `just replay-run CASE=<name>` | Run a single replay case | 0 on success, non-zero on failure |
| `just replay-freeze CASE=<name>` | Freeze expected hash for a case | 0 on success, non-zero on failure |

### API Endpoints

The development server exposes several API endpoints:

| Endpoint | Method | Description | Status |
|----------|--------|-------------|--------|
| `/` | GET | Root endpoint | ✅ Available |
| `/health` | GET | Health check | ✅ Available |
| `/metrics.json` | GET | JSON metrics snapshot | ✅ Available |
| `/docs` | GET | OpenAPI documentation | ✅ Available |
| `/api/execute` | POST | Execute logic modules (contract phase) | ✅ Available |
| `/sse` | GET | Server-Sent Events stream (contract phase) | ✅ Available |
| `/webhooks/{source}` | POST | Webhook ingress with HMAC verification (contract phase) | ✅ Available |
| `/mcp/search` | POST | MCP search endpoint | ✅ Available |
| `/mcp/fetch` | POST | MCP fetch endpoint | ✅ Available |
| `/mcp/stream` | POST | MCP streaming endpoint | ✅ Available |

#### Testing the Execute Endpoint

```bash
# Test the execute endpoint with contract tests
just execute-contract-test

# Manual test with curl
curl -X POST "http://localhost:8000/api/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "logic_id": "logic_001_profit_loss",
    "org_id": "60020606976",
    "period": "2025-01"
  }'
```

#### Testing the SSE Endpoint

```bash

#### Testing the CLI Interface

The CLI provides a contract-only interface for testing logic execution:

```bash
# Test CLI help
python -m cli --help
python -m cli execute --help

# Execute with flags
python -m cli execute --logic-id logic_001_profit_loss --org-id 60020606976 --period 2025-01

# Execute with plan file
echo '{"logic_id": "logic_001_profit_loss", "org_id": "60020606976", "period": "2025-01"}' > plan.json
python -m cli execute --plan plan.json

# Execute with inputs and context
python -m cli execute --logic-id logic_001_profit_loss --inputs '{"include_details": true}' --context '{"source": "cli"}'

# Run CLI contract tests
just cli-contract-test
```

**CLI Features:**
- **Contract-only**: No business logic execution, deterministic stubbed responses
- **JSON I/O**: Accepts ExecuteRequest JSON files, outputs ExecuteResponse JSON
- **Flag-based**: Supports individual parameters for quick testing
- **Error handling**: Proper exit codes and error messages
- **Deterministic**: Same input always produces same output

**CLI Commands:**
- `zgpt execute --plan <path.json>` - Execute from JSON plan file
- `zgpt execute --logic-id <id> [--org-id <id>] [--period <period>]` - Execute with flags
- `zgpt execute --logic-id <id> --inputs <json> --context <json>` - Execute with custom inputs/context
# Test the SSE endpoint with contract tests
just sse-contract-test

# Manual test with curl (stream events)
curl -N "http://localhost:8000/sse"
```

#### Testing the Webhooks Endpoint

```bash
# Test the webhooks endpoint with contract tests
just webhooks-contract-test

# Manual test with curl (example)
curl -X POST "http://localhost:8000/webhooks/test-source" \
  -H "Content-Type: application/json" \
  -H "X-Signature: <hmac-signature>" \
  -H "X-Id: <unique-message-id>" \
  -H "X-Timestamp: <unix-timestamp>" \
  -d '{"event": "test", "data": "value"}'
```

##### How to Send a Webhook

The webhooks endpoint requires three security headers:

1. **X-Signature**: HMAC-SHA256 signature of the request body
   ```bash
   # Generate signature (example)
   echo -n '{"event":"test"}' | openssl dgst -sha256 -hmac "webhook-secret-key-change-in-production"
   ```

2. **X-Id**: Unique message identifier (prevents replay attacks)
   ```bash
   # Use UUID or timestamp-based ID
   X-Id: "msg-$(date +%s)-$(uuidgen | cut -d'-' -f1)"
   ```

3. **X-Timestamp**: Unix timestamp of when the message was created
   ```bash
   # Current timestamp
   X-Timestamp: "$(date +%s)"
   ```

**Security Notes:**
- Change the webhook secret in production
- Messages older than 5 minutes are rejected
- Duplicate message IDs are rejected (replay protection)
- Invalid signatures return 401 Unauthorized

# Test with cursor parameter for resumability
curl -N "http://localhost:8000/sse?cursor=test_cursor_123"

# Test with JavaScript EventSource (browser)
const eventSource = new EventSource('http://localhost:8000/sse');
eventSource.onmessage = function(event) {
    console.log('Received:', event.data);
};
eventSource.addEventListener('progress', function(event) {
    console.log('Progress:', JSON.parse(event.data));
});
eventSource.addEventListener('section', function(event) {
    console.log('Section:', JSON.parse(event.data));
});
eventSource.addEventListener('done', function(event) {
    console.log('Done:', JSON.parse(event.data));
    eventSource.close();
});
```

### Utility Commands

| Command | Description |
|---------|-------------|
| `just setup` | Install dependencies |
| `just clean` | Clean development artifacts |
| `just install-just` | Install just command runner |
| `just help` | Show help information |

## Development Workflow

### 1. Daily Development
```bash
# Start development environment
just dev

# In another terminal, make changes to code
# Tests will run automatically on file changes
# API will reload automatically on file changes
```

### 2. Before Committing
```bash
# Run all CI checks locally
just ci-local

# Format code
just fmt

# Run tests
just test
```

### 3. Troubleshooting
```bash
# Clean up and start fresh
just clean
just setup
just dev
```

## Service URLs

## Scaffold missing logics (P1.5.3)

This task ensures complete coverage of 231/231 logic modules by creating minimal, deterministic contract-only stubs for any missing files listed in `artifacts/master_vs_repo_report.json`.

- When to run: after building MASTER index and running repo inventory.
- What it creates: `logics/logic_{id:03d}_{slug}.py` files with a contract-only `execute(inputs) -> dict` no-op stub.
- Guarantees: deterministic content, no timestamps, newline-at-EOF, UTF-8, and never overwrites existing files (idempotent).
- Idempotency: running the scaffolder multiple times makes no changes after first creation; a second run is a no-op.

Commands:

```bash
# Preview planned creations (no writes)
python3 tools/scaffold_missing_logics.py --dry-run

# Create stubs non-interactively
just scaffold-missing

# Audit coverage counters and verify idempotency
just coverage-audit
just coverage-check
```

When the development environment is running:

| Service | URL | Description |
|---------|-----|-------------|
| API Server | http://localhost:8000 | Main FastAPI application |
| Health Check | http://localhost:8000/health | Service health endpoint |
| API Documentation | http://localhost:8000/docs | Interactive API docs |
| Test Coverage | htmlcov/index.html | Coverage report (after tests) |

## Configuration

### Environment Variables
Create a `.env` file in the project root for local configuration:

```bash
# Zoho API Configuration
ZOHO_CLIENT_ID=your_client_id
ZOHO_CLIENT_SECRET=your_client_secret
ZOHO_REFRESH_TOKEN=your_refresh_token
ZOHO_API_DOMAIN=www.zohoapis.in

# MCP Configuration
MCP_SECRET=your_mcp_secret

# Development Configuration
DEBUG=true
LOG_LEVEL=info
```

### Credentials File
Ensure `zoho_credentials.json` exists in the project root:

```json
{
  "client_id": "your_client_id",
  "client_secret": "your_client_secret", 
  "refresh_token": "your_refresh_token",
  "api_domain": "www.zohoapis.in"
}
```

## Testing

### Test Structure
- `tests/unit/` - Unit tests for individual components
- `tests/integration/` - Integration tests
- `tests/performance/` - Performance tests
- `tests/contract/` - Contract shape tests (enforces schema hash snapshots)
- `tests/evidence/` - Evidence OS tests (blob store, ledger, signer)
- `tests/golden/` - Golden tests (when implemented)

### Golden Tests

Golden tests enforce deterministic outputs of the contract surface. Each case lives under `tests/golden/fixtures/<case>/` with `input.json` and `expected.json`.

Commands:

```bash
# Run all golden tests
just golden-test

# Rebuild expected.json for a single case
just golden-rebuild CASE=logic_001_basic

# Rebuild all goldens
just golden-rebuild
```

On failure, a unified diff is written to `tests/golden/diffs/<case>.diff` with hints to intentionally update goldens. CI uploads diffs as artifacts.

### Running Tests
```bash
# Run all tests
just test

# Run specific test categories
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/performance/ -v
pytest tests/contract/ -v
pytest tests/evidence/ -v

# Run with coverage
pytest tests/ --cov=logics --cov=helpers --cov=orchestrators --cov-report=html
```

### Contract Snapshots

The project uses contract snapshots to enforce cross-phase compatibility. Contract snapshots are deterministic hashes of all dataclass structures in `surfaces/contracts.py`.

#### Working with Contract Snapshots

```bash
# Generate contract snapshots
just contract-snapshots

# Run contract shape tests
just contract-test

# Both commands together (recommended)
just contract-snapshots && just contract-test
```

#### When Contract Snapshots Change

1. **New Contracts**: When adding new dataclasses to `surfaces/contracts.py`
2. **Modified Contracts**: When changing field names, types, or structure
3. **Removed Contracts**: When removing dataclasses

The CI pipeline will automatically:
- Generate new snapshots
- Run contract tests
- Commit updated snapshots if changes are detected

#### Contract Snapshot Files

- **Generated**: `artifacts/contract_snapshots.json`
- **Tool**: `tools/gen_contract_snapshots.py`
- **Tests**: `tests/contract/test_contract_shapes.py`

#### Troubleshooting Contract Issues

```bash
# If contract tests fail, regenerate snapshots
just contract-snapshots

# If you need to reset snapshots (use with caution)
rm artifacts/contract_snapshots.json
just contract-snapshots
```

## Evidence OS

The Evidence OS provides deterministic, content-addressed storage and verification for audit compliance. It consists of three core components:

### Components

1. **Blob Store** (`evidence/blob_store.py`)
   - Content-addressed storage for artifacts (PDFs, JSON, CSV, images)
   - SHA256 hashing with deterministic outputs
   - Pure Python local backend with clear interfaces for later swap

2. **Ledger** (`evidence/ledger.py`)
   - Append-only WORM (Write Once, Read Many) ledger
   - Hash-chained records with Merkle-rooted bundles
   - Tamper-evident integrity verification

3. **Signer** (`evidence/signer.py`)
   - Deterministic signing and verification
   - SHA256 + HMAC wrapper with pluggable signers
   - Support for both production and testing modes

### Usage

#### Blob Store
```python
from evidence.blob_store import BlobStore

# Initialize blob store
blob_store = BlobStore("data/evidence/blobs")

# Store data
blob_ref = blob_store.write("test data", content_type="text/plain")
print(f"Stored with hash: {blob_ref.hash}")

# Retrieve data
data = blob_store.read(blob_ref.hash)
print(f"Retrieved: {data.decode('utf-8')}")
```

#### Ledger
```python
from evidence.ledger import EvidenceLedger

# Initialize ledger
ledger = EvidenceLedger("data/evidence/ledger")

# Write record
record = ledger.write("key1", "test data")
print(f"Record ID: {record.record_id}")

# Read data
data = ledger.read("key1")
print(f"Data: {data.decode('utf-8')}")

# Verify integrity
assert ledger.verify_integrity("key1") is True
```

#### Signer
```python
from evidence.signer import EvidenceSigner

# Initialize signer
signer = EvidenceSigner()

# Sign data
signature_result = signer.sign("test data", "key1")
print(f"Signature: {signature_result.signature}")

# Verify signature
assert signer.verify("test data", signature_result) is True
```

### Testing

```bash
# Run evidence tests
just evidence-test

# Run specific evidence component tests
pytest tests/evidence/test_blob_store.py -v
pytest tests/evidence/test_ledger.py -v
pytest tests/evidence/test_signer.py -v
```

### Key Features

- **Deterministic**: Same inputs always produce same outputs
- **Tamper-Evident**: Any modification is detected through hash verification
- **Content-Addressed**: Data is referenced by its content hash
- **Append-Only**: Ledger maintains WORM guarantees
- **Pluggable**: Clear interfaces allow backend swapping
- **Pure Python**: No external dependencies for core functionality

### Storage Structure

```
data/evidence/
├── blobs/
│   ├── blobs/          # Actual blob data files
│   └── metadata/       # Blob metadata JSON files
└── ledger/
    ├── blobs/          # Ledger's blob store
    ├── records/        # Individual record files
    ├── bundles/        # Bundle metadata files
    └── index/          # Key-based index files
```

## Consent & Redaction

Consent governs access to external connectors and sensitive operations. We define a canonical JSON Schema and deterministic redaction utilities.

### Schema

- Path: `consent/schema/consent.schema.json`
- Required fields: `subject`, `scope[]`, `purpose`, `created_at`, `expires_at`, `retention_days`
- Optional: `consent_id`, `subject_type`, `lawful_basis`, `revoked_at`, `metadata`

Validate with `jsonschema`:
```python
import json, jsonschema
from pathlib import Path

schema = json.loads(Path('consent/schema/consent.schema.json').read_text())
payload = {
  "subject": "ORG:60020606976",
  "scope": ["gst.gstr2b.read"],
  "purpose": "compliance_reconciliation",
  "created_at": "2025-08-18T00:00:00Z",
  "expires_at": "2026-03-31T23:59:59Z",
  "retention_days": 365
}
jsonschema.validate(instance=payload, schema=schema)
```

### Redaction Utilities

- Module: `consent/redactor.py`
- Functions:
  - `redact_consent(consent, null_fields=[...], hash_fields=[...])` — pure and deterministic
  - `redact_consent_default(consent)` — hashes `subject`/`consent_id`, nulls `metadata`

Hashing is deterministic using a stable salt and canonical JSON; outputs prefixed with `sha256:`.

### Evidence Ledger Integration

Redacted consent objects can be written to the Evidence Ledger to generate stable, content-addressed records.

```python
from evidence.ledger import EvidenceLedger
from consent.redactor import redact_consent_default

ledger = EvidenceLedger('data/evidence/ledger')
redacted = redact_consent_default(payload)
record = ledger.write('consent:ORG:60020606976', redacted)
assert ledger.verify_integrity('consent:ORG:60020606976')
```

### Tests and Commands

- Unit tests under `tests/consent/` cover schema validation, redaction determinism, and ledger stability.

Run consent tests:
```bash
just consent-test
```

## Evidence Replay (Golden Runner)

Deterministic replay verifies that a previously stored ExecuteRequest produces a byte-identical canonical response under the current codebase (contract-only stub, no external I/O).

- Fixtures live under `tests/replay/fixtures/<case>/` and contain:
  - `manifest.json` — metadata including `input_path`
  - `input.json` — canonical ExecuteRequest
  - `expected_hash.txt` — frozen sha256 of canonical ExecuteResponse

Commands:

```bash
# Run all replay cases
just replay-test

# Run a specific case
just replay-run CASE=logic_001_basic

# Freeze/update the expected hash (intentional)
just replay-freeze CASE=logic_001_basic
```

On mismatch, diffs are written to `tests/replay/diffs/<case>/` with `observed.json`, `observed.hash`, `expected.hash`, and a `HINT.txt` for actions.

## Code Quality

### Linting
The project uses `ruff` for linting and formatting:

```bash
# Check code style
just lint

# Format code
just fmt
```

### ID Policy Linting
The project enforces strict ID policy for logic files:

```bash
# Check ID policy compliance
just id-lint
```

The ID linter validates:
- All logic files follow the `logic_XXX_name.py` naming pattern
- IDs are sequential from 001 to 231 with no gaps
- No duplicate IDs or filenames exist
- All expected logic files are present

This ensures the complete coverage of all 231 logic modules as defined in the project scope.

### Type Checking
The project uses `mypy` for static type checking:

```bash
# Run type checking
just type
```

### Security Scanning
```bash
# Run security checks
bandit -r logics/ helpers/ orchestrators/ core/ main.py
safety check
```

## Troubleshooting

### Common Issues

#### 1. Port Already in Use
```bash
# Check what's using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>
```

#### 2. Dependencies Issues
```bash
# Clean and reinstall
just clean
just setup
```

#### 3. Test Failures
```bash
# Run tests with verbose output
pytest tests/ -v -s

# Run specific failing test
pytest tests/unit/test_specific.py -v -s
```

#### 4. Type Checking Errors
```bash
# Run mypy with more details
mypy logics/ helpers/ orchestrators/ core/ main.py --show-error-codes
```

### Performance Issues

#### 1. Slow Test Execution
- Tests run in watch mode by default
- Use `just test` for single run
- Consider using `pytest-xdist` for parallel execution

#### 2. Memory Issues
```bash
# Monitor memory usage
ps aux | grep python

# Clean up caches
just clean
```

## CI/CD Integration

The local commands mirror the CI pipeline:

| Local Command | CI Job | Purpose |
|---------------|--------|---------|
| `just lint` | `lint` | Code style and quality |
| `just type` | `type` | Type checking |
| `just test` | `test` | Unit and integration tests |
| `just ci-local` | All jobs | Full CI pipeline locally |
| `just master-index` | `master_index_check` | Build MASTER index and fail on diffs |
| `just repo-inventory` | `repo_inventory_check` | Scan repo inventory and compare with MASTER |
| `just repo-inventory-check` | `repo_inventory_check` | Run repo inventory tests only |
| `just scaffold-missing` | `logic_coverage_gate` | Create contract-only stubs for any missing logics |
| `just coverage-audit` | `logic_coverage_gate` | Print coverage counters from diff report |
| `just coverage-check` | `logic_coverage_gate` | Run scaffold idempotency test |
| `just l4-readiness` | `l4_readiness_gate` | Audit L4 coverage/readiness and update artifact |
| `just l4-readiness-check` | `l4_readiness_gate` | Run L4 readiness tests |

### MASTER index (authoritative 231)

The MASTER index is a canonical list of 231 logic items derived from `MASTER_SCOPE_OF_WORK.md` and cross-checked against the `logics/` folder. It is generated deterministically into `artifacts/master_index.json`.

- Command to (re)generate:
```bash
just master-index
```

- Command to run checks only:
```bash
just master-index-check
```

CI Gate `master_index_check` enforces that:
- The extractor runs and produces `artifacts/master_index.json` deterministically.
- Any diff vs committed file fails the build (`git diff --exit-code artifacts/master_index.json`).
- Tests in `tests/master/test_master_index.py` pass (length==231, IDs contiguous 1..231, slugs/path patterns, determinism).


### Repo inventory

The repo inventory enumerates all logic modules physically present under `logics/` matching `logic_{id}_{slug}.py` and compares them with the authoritative MASTER index.

- Scanner: `tools/scan_repo_logics.py`
- Artifacts:
  - `artifacts/repo_logics.json` — canonical repo inventory (sorted by id, then slug)
  - `artifacts/master_vs_repo_report.json` — deterministic diff report vs MASTER
- Exit codes:
  - 0: inventories match (no diffs)
  - 3: mismatches detected (any non-empty list)
  - 2: parsing/determinism errors

Commands:

```bash
# Build inventory and summary
just repo-inventory

# Run inventory-only tests
just repo-inventory-check
```

Report fields in `master_vs_repo_report.json`:
- `missing_in_repo`: Present in MASTER, absent in repo
- `extra_in_repo`: Present in repo, not in MASTER
- `slug_mismatches`: Same id, slug differs
- `path_mismatches`: Same id, path differs
- `duplicate_ids`: Same id appears in multiple repo files

How to fix:
- For missing files or mismatches, use the next task P1.5.3 to scaffold or rename logic files to align with MASTER. Do not edit MASTER here.

CI Gate `repo_inventory_check` enforces that:
- The scanner runs and exits 0 when inventories match, or 3 when diffs exist.
- Any uncommitted changes to artifacts cause failure: `git diff --exit-code artifacts/repo_logics.json artifacts/master_vs_repo_report.json`.
- Tests in `tests/master/test_repo_inventory.py` validate determinism and structure.

## Future Enhancements

### Planned Features
- [ ] Local dashboards (Grafana, Prometheus)
- [ ] Database setup and migrations
- [ ] Docker development environment
- [ ] Performance profiling tools
- [ ] Automated dependency updates

### Observability baseline (P1.4.2)
- Structured logs: one JSON per line with fields `ts`, `level`, `evt`, `trace_id`, `evidence_id`, `attrs`.
- Sample log entry:
```json
{"ts":"2025-01-01T00:00:00.000000Z","level":"INFO","evt":"execute_ok","trace_id":"trace-abc","attrs":{"status_code":200,"logic_id":"logic_001_profit_loss"}}
```
- Metrics endpoint: `GET /metrics.json` returns a JSON snapshot, e.g.:
```json
{
  "requests_total": {"surface=rest": 12, "surface=sse": 3},
  "errors_total": {"surface=rest": 0},
  "exec_calls_total": {"logic=logic_001_profit_loss": 12}
}
```
- How to run: `just obs-test` to execute observability tests.

## Support

### Getting Help
1. Check this runbook first
2. Review the project documentation
3. Check the CI logs for similar issues
4. Create an issue with detailed error information

### Contributing
1. Follow the development workflow
2. Ensure all tests pass
3. Run `just ci-local` before submitting PRs
4. Update documentation as needed

---

**Note:** This runbook is part of Task P1.1.2 and follows the AGENT_EDIT_PROTOCOL.md guidelines for forward-only changes and comprehensive documentation.

## Regulatory OS — Packs & Effective Dates

### Pack Layout

```
regulatory/
  loader.py                          # validate_pack, load_active, list_packs
  schema/
    rule_pack.schema.json            # JSON Schema for packs
  rule_packs/
    in/
      gst.json                       # GST pack (multiple versions)
      # eway.json (optional example)
```

### Rule Pack Schema (minimal)
- versions[]: list of version objects
  - effective_from: YYYY-MM-DD (required)
  - effective_to: YYYY-MM-DD or null (optional, open-ended)
  - data: arbitrary object with rules/config for that version

### Effective-Date Selection Rules
- Windows must not overlap. Adjacency allowed (e.g., 2024-12-31 → 2025-01-01).
- Selection is deterministic: given a date, the single active version is chosen.
- If multiple versions are active due to overlap, validation fails (fail-closed).
- If no version is active for the date, loading fails with a clear error.

### Developer Commands
- Validate and load in code:

```python
from regulatory.loader import validate_pack, load_active

validate_pack("regulatory/rule_packs/in/gst.json")
active = load_active("regulatory/rule_packs", "in", "2025-01-15")
```

- Run tests:

```bash
just regulatory-test
```

## L4 contract base (P1.5.4)

The L4 contract defines deterministic no-op hooks that all logics can implement or subclass during Phase 1.

- Module: `logics/common/l4_base.py`
- Default singleton: `logics/common/l4_default.py` exporting `L4_DEFAULT`
- Determinism: All hooks return stable, JSON-serializable dicts; no timestamps, randomness, or I/O.

Hooks (signatures simplified for flexibility):

- `history_read(context: dict) -> dict` — returns `{ "snapshot": {}, "status": "empty" }`
- `history_write(context: dict, payload: dict) -> dict` — returns `{ "ack": true, "written": false }`
- `learn(context: dict, facts: list[dict]) -> dict` — returns `{ "accepted": 0, "rejected": len(facts) }`
- `detect_anomalies(context: dict, series: list[dict]) -> dict` — returns `{ "anomalies": [], "count": 0 }`
- `self_optimize(context: dict, state: dict) -> dict` — returns `{ "actions": [], "state": {} }`
- `explain(context: dict, result: dict) -> dict` — returns `{ "explanation": "no-op" }`
- `confidence(context: dict, result: dict) -> dict` — returns `{ "score": 1.0 }`

Command:

```bash
just l4-test
```

This runs `tests/l4/test_l4_base.py`, which asserts byte-identical outputs via canonical JSON.

## Coverage & L4 readiness gates (P1.5.5)

This gate enforces two invariants:

- Coverage: Exactly 231 logic modules exist with filenames `logic_{id:03d}_{slug}.py` for IDs 1..231.
- L4 readiness: Each module satisfies at least one of the acceptance rules:
  1) Contains `from logics.common.l4_default import L4`
  2) Contains `from logics.common.l4_base import L4Base` (and may instantiate `L4Base()` or expose `L4`)
  3) Defines a top-level symbol `L4 = ...`

Bonus (non-fatal) note: the auditor reports modules missing a top-level `execute(...)` stub.

Auditor: `tools/audit_l4_readiness.py` writes a deterministic report to `artifacts/l4_readiness_report.json` with sorted keys and `"timestamp": null` for byte-identical reruns.

Commands:

```bash
just l4-readiness           # run auditor and pretty-print report
just l4-readiness-check     # run tests for the L4 readiness gate
```

CI Gate `l4_readiness_gate` runs the auditor, fails if exit code != 0, asserts the committed artifact is up-to-date using `git diff --exit-code artifacts/l4_readiness_report.json`, and executes the readiness tests.

How to fix failures:
- Coverage: create missing files or correct filenames to match `logic_{id:03d}_{slug}.py`.
- Readiness: ensure one of the acceptance rules is met (import default `L4`, import `L4Base`, or define top-level `L4`).
- Optional: add a top-level `execute(...)` stub if absent to satisfy contract expectations.
