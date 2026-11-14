# Changelog

All notable project changes should be recorded here. Use dates in `YYYY-MM-DD` format. This file starts with the documentation baseline; implementation releases should be added as the MVP is developed.

## [Unreleased]

### Fixed
- Restored browser scan results by correcting JavaScript parsing and severity rendering.
- Completed TXT, PDF, and DOCX extraction with upload validation and controlled failures.
- Kept in-memory audit databases available across connections so API scans can complete.
- Detected requests to reveal "your system prompt" as critical secret-disclosure findings.

### Added
- Integrated Gemini through the official `google-genai` SDK with server-side key configuration, timeouts, safe error responses, and rate-limit handling.
- Added a browser action to ask Gemini only after scanning; flagged prompts require explicit confirmation and blocked content is never forwarded.

### Planned
- Optional classifier adapter.

## [1.0.0] - 2026-11-13

### Added
- Initial MVP documentation baseline.
- Defined direct and indirect prompt-injection threat scope.
- Defined REST API direction and local development stack.
- Defined security and privacy constraints.

### Core Modules (Phase 1-7 Complete)
- **gateway/detector.py**: Rule-based prompt injection detection with 5 detection categories:
  - INSTRUCTION_OVERRIDE: Detect attempts to ignore/disable previous instructions
  - ROLE_OVERRIDE: Detect attempts to change AI role/persona (unrestricted, developer, admin, etc.)
  - SECRET_REVEAL: Detect requests for system prompts, API keys, credentials, passwords
  - SAFETY_BYPASS: Detect attempts to bypass safeguards/restrictions
  - DATA_EXFILTRATION: Detect attempts to exfiltrate data externally

- **gateway/risk.py**: Risk scoring engine (0-100) with severity weights:
  - LOW: 10, MEDIUM: 20, HIGH: 35, CRITICAL: 50
  - Critical override for SECRET_REVEAL findings

- **gateway/policy.py**: Centralized policy engine:
  - ALLOW: score 0-29
  - FLAG: score 30-69 (requires confirmation)
  - BLOCK: score 70-100 or critical override

- **gateway/file_extractor.py**: Multi-format document extraction:
  - TXT: UTF-8 and latin-1 encoding support
  - PDF: PyMuPDF text extraction
  - DOCX: python-docx paragraph and table extraction
  - File size limits, extension validation
  - Safe temporary file handling with cleanup

- **gateway/llm_client.py**: Provider-neutral LLM adapter:
  - OpenAI and Gemini API support
  - Environment variable configuration
  - Timeout and error handling
  - Clear separation of trusted system prompts from untrusted user content

- **gateway/audit.py**: SQLite-based audit logging:
  - Scan metadata (ID, timestamp, decision, score, duration)
  - No full prompt/document content stored by default
  - Configurable database path

- **app.py**: Flask REST API with routes:
  - POST /api/scan: Scan text prompts
  - POST /api/scan-file: Extract and scan documents
  - POST /api/ask: Scan and forward to LLM (policy-gated)
  - GET /api/logs: Retrieve scan history
  - GET /health: Health check endpoint

- **templates/index.html**: Web UI with Bootstrap:
  - Text prompt scanner
  - File upload component
  - Results panel with decision/score/findings
  - Recent logs display

- **tests/**: Automated test suite (67 tests):
  - Unit tests for detector, policy, risk scoring
  - Integration tests for file extraction
  - Security tests for Block/FLAG enforcement
  - API tests for all endpoints

### Added
- Initial MVP documentation baseline.
- Defined direct and indirect prompt-injection threat scope.
- Defined REST API direction and local development stack.
- Defined security and privacy constraints.
