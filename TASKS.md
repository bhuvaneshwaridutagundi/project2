# MVP Tasks and Delivery Plan

Status key: `[ ]` not started · `[x]` completed · `[-]` in progress

## Milestone 0 — Repository and environment
- [ ] Create the project folder and proposed package structure.
- [ ] Select a supported Python version (recommend 3.11 or 3.12).
- [ ] Create and activate a virtual environment.
- [ ] Add `requirements.txt` and `.env.example`.
- [ ] Add `.gitignore` for `.venv/`, `.env`, `__pycache__/`, database files, uploads, and test artifacts.
- [ ] Confirm the Flask home page runs locally.

**Exit criteria:** another teammate can install dependencies and start the app using README instructions.

## Milestone 1 — Text scanning foundation
- [ ] Define a `Finding` data structure: code, source, severity, message, confidence/evidence metadata.
- [ ] Implement rule-based detector for instruction override.
- [ ] Add rules for role override, secret/system-prompt extraction, and safety bypass.
- [ ] Label findings with source `user_prompt`.
- [ ] Add benign examples that mention attacks for educational purposes.
- [ ] Unit-test each rule and benign edge cases.

**Exit criteria:** text scan returns structured findings and does not rely only on a single keyword.

## Milestone 2 — Risk scoring and policy
- [ ] Implement bounded risk score 0–100.
- [ ] Add severity weights and duplicate-match handling.
- [ ] Add critical-signal override.
- [ ] Implement centralized Allow/Flag/Block policy.
- [ ] Ensure Flag requires explicit confirmation and defaults to hold.
- [ ] Add tests for thresholds and boundary values.

**Exit criteria:** same findings produce the same score and policy decision; policy is tested independently.

## Milestone 3 — Document support
- [x] Add TXT extraction.
- [x] Add PDF extraction using PyMuPDF.
- [x] Add DOCX extraction using python-docx.
- [x] Validate extension, file size, and empty/unreadable files.
- [x] Scan document text separately from the user's task.
- [x] Identify the source of each finding.
- [x] Return a clear message for scanned PDFs with no extractable text (OCR is not MVP).

**Exit criteria:** test files with normal and malicious text produce source-labelled results.

## Milestone 4 — Flask REST API and UI
- [x] Implement `POST /api/scan`.
- [x] Implement `POST /api/scan-file`.
- [x] Implement `GET /api/logs`.
- [x] Implement `GET /health`.
- [x] Add consistent JSON response schemas and HTTP error codes.
- [x] Add text scan form and file upload UI.
- [x] Display decision, score, severity, and findings.
- [x] Add safe handling for loading and error states.
- [x] Add responsive dashboard metrics, audit-backed analytics, and searchable scan history.

**Exit criteria:** all scan operations work from the browser and Postman/curl.

## Milestone 5 — Audit logging
- [ ] Create SQLite schema for scan metadata and findings.
- [ ] Log scan ID, timestamp, source type, score, decision, finding codes, duration, and LLM-called flag.
- [ ] Do not store full content by default.
- [ ] Add pagination or a reasonable result limit to logs.
- [ ] Test that failed requests do not create misleading success records.

**Exit criteria:** every completed scan has a traceable metadata record.

## Milestone 6 — LLM integration
- [x] Define provider-neutral LLM adapter interface.
- [x] Configure Gemini through environment variables and the official Google GenAI SDK.
- [x] Add request timeout and controlled provider error handling, including rate-limit responses.
- [x] Keep system instructions separate from user and document content.
- [x] Clearly label uploaded/retrieved content as untrusted data.
- [x] Gate every LLM call through the policy decision.
- [x] Add tests with a mocked LLM adapter.
- [x] Verify Block never calls the adapter and Flag needs confirmation.

**Exit criteria:** an allowed request produces an AI answer; blocked requests never reach the provider.

Live Gemini requests still require a user-owned API key and are not made by automated tests.

## Milestone 7 — Optional ML classifier
- [ ] Select a compatible prompt-injection classifier after reviewing its model card and license.
- [ ] Implement classifier adapter behind a feature flag.
- [ ] Handle unavailable model, download failure, and inference timeout.
- [ ] Combine ML output with rule findings without treating it as ground truth.
- [ ] Evaluate against the same labelled test set.
- [ ] Compare false-positive and false-negative rates with rules-only baseline.

**Exit criteria:** ML can be enabled/disabled without changing API contracts; measured results are documented.

## Milestone 8 — Final validation and demo
- [ ] Complete all cases in `TESTING.md`.
- [ ] Run full test suite.
- [ ] Measure scan latency on the team's laptop.
- [ ] Review privacy and secret-handling settings.
- [ ] Prepare demo prompts and harmless sample documents.
- [ ] Update README, architecture, changelog, and project screenshots.
- [ ] Prepare known limitations and future enhancements for evaluation.

**Exit criteria:** reproducible demo, test evidence, and honest statement of limitations.

## Suggested team split (4 members)

| Member | Main ownership | Shared review |
|---|---|---|
| 1 | Flask API, integration, configuration | API and integration tests |
| 2 | Rule detector, risk scoring, policy | Detection evaluation |
| 3 | File extraction and upload validation | Malicious/benign document tests |
| 4 | Frontend, SQLite logs, demo documentation | End-to-end testing |

All members should understand the end-to-end data flow and security boundary. Avoid having only one member understand the LLM integration or policy logic.
