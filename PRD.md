# Product Requirements Document (PRD)
## Prompt Injection Security Gateway for AI Applications

- **Document status:** MVP baseline
- **Version:** 1.0
- **Product type:** Reusable REST-based security middleware
- **Primary users:** Developers integrating LLMs; end users submitting prompts/documents

## 1. Problem statement

Many LLM applications combine trusted system instructions with untrusted user messages and retrieved content. If these trust boundaries are not preserved, an attacker can place instructions in a user prompt or inside a document, webpage, or email that the application later supplies to the model. These direct and indirect prompt-injection attempts may try to override intended instructions, reveal protected information, or manipulate model behaviour.

LLM providers may offer built-in safeguards, but application developers still need an application-level, pluggable layer that inspects inputs, records security decisions, and applies consistent policies before content reaches an LLM.

## 2. Product vision

Provide a small, reusable gateway between an AI application and an LLM. The gateway accepts text and supported files, analyzes untrusted content, produces explainable findings and a risk score, and applies `ALLOW`, `FLAG`, or `BLOCK` policies. Approved requests can be forwarded to a configured LLM provider. Security metadata is logged for monitoring and evaluation.

## 3. Goals

1. Inspect direct user prompts before forwarding them to an LLM.
2. Extract and inspect text from PDF, DOCX, and TXT files.
3. Identify common prompt-injection behaviours using explainable rules.
4. Support an optional ML classifier as an additional signal.
5. Produce a risk score from 0 to 100 with reasons.
6. Enforce configurable Allow/Flag/Block decisions.
7. Prevent blocked inputs from reaching the LLM.
8. Provide a reusable REST API and a simple demonstration UI.
9. Maintain privacy-conscious audit logs.
10. Measure detection quality with a repeatable test set.

## 4. Non-goals for MVP

- Perfect or guaranteed prompt-injection prevention.
- Full semantic understanding of every language or encoding.
- OCR for scanned images, image/video/audio input, or web crawling.
- LLM agent tool execution or authorization.
- Enterprise identity management, multi-tenancy, cloud deployment, and high availability.
- Replacing provider-side safety systems or secure application design.

## 5. Personas and primary use cases

### Persona A — AI application developer
Wants a common API to scan prompts and documents before sending them to an LLM.

### Persona B — End user
Wants to ask a question or upload a document and receive an answer when the content passes the gateway's policy.

### Persona C — Project evaluator/security reviewer
Wants to see why a prompt was allowed, flagged, or blocked and inspect test evidence.

### Use cases
- UC-01: Submit normal text and receive an LLM answer after an Allow decision.
- UC-02: Submit a direct injection prompt and receive a Block warning.
- UC-03: Upload a document containing suspicious instructions and receive a finding identifying the source.
- UC-04: Submit borderline content and receive a Flag decision requiring confirmation/review.
- UC-05: Review recent scan decisions in the security log.
- UC-06: Integrate another application using the REST API.

## 6. Functional requirements

| ID | Requirement | Priority |
|---|---|---|
| FR-01 | Accept plain-text prompt input through the UI and API. | Must |
| FR-02 | Accept PDF, DOCX, and TXT files within a configurable size limit. | Must |
| FR-03 | Extract readable text from supported documents and report extraction errors. | Must |
| FR-04 | Scan prompt and document text separately, preserving their source labels. | Must |
| FR-05 | Detect common injection patterns with explainable rules. | Must |
| FR-06 | Return risk score, severity, matched signals, and decision. | Must |
| FR-07 | Apply Allow, Flag, and Block policies using configurable thresholds. | Must |
| FR-08 | Ensure Block decisions never invoke the LLM adapter. | Must |
| FR-09 | Require explicit confirmation for Flag decisions; default to no forwarding. | Must |
| FR-10 | Forward allowed requests to a configured LLM provider. | Must for complete demo |
| FR-11 | Clearly delimit document content as untrusted data in the LLM request. | Must |
| FR-12 | Store timestamp, source type, score, decision, and finding codes in SQLite. | Must |
| FR-13 | Expose REST endpoints for scanning, asking, and retrieving logs. | Must |
| FR-14 | Provide a simple browser UI showing findings and decision. | Must |
| FR-15 | Allow an optional ML classifier to add a detection signal. | Should |
| FR-16 | Provide a health/status endpoint and useful error messages. | Should |

## 7. Decision policy

Initial thresholds for development only; tune them against the project's labelled test set.

| Score | Decision | Behaviour |
|---:|---|---|
| 0–29 | ALLOW | Forward to LLM if configured |
| 30–69 | FLAG | Do not forward until explicit review/confirmation |
| 70–100 | BLOCK | Do not forward; return a warning |

The score is a heuristic risk indicator, not a calibrated probability. A high-confidence critical signal may trigger Block even if the weighted score is lower. Policy configuration must be centralized rather than duplicated across routes.

## 8. Non-functional requirements

- **Security:** Validate file type and size; generate safe server-side filenames; never execute uploaded content; keep API keys in environment variables.
- **Privacy:** Do not log full prompts or document text by default. Store minimal metadata and finding codes.
- **Reliability:** Invalid files and provider failures must return controlled errors without crashing the app.
- **Usability:** Explain the decision in plain language and identify which source was flagged.
- **Performance:** Target a local scan response under 3 seconds for ordinary text under 10 KB when optional ML inference is disabled; measure actual results.
- **Maintainability:** Separate routes, extraction, detection, scoring, policy, LLM, and audit modules.
- **Portability:** Run locally on a student laptop with documented setup steps.
- **Extensibility:** Allow detector and LLM provider implementations to be replaced without rewriting API routes.

## 9. User interface requirements

- Text input area and Scan button.
- File upload control showing allowed formats and size limit.
- Result panel with decision, score, severity, detected source, and reasons.
- For Allow, display the AI response when an LLM is configured.
- For Flag, explain that the content is held for review and is not sent automatically.
- For Block, explain that the request was not forwarded.
- Recent scan history with sensitive content omitted.

## 10. Acceptance criteria

The MVP is acceptable when:
1. A normal educational prompt is scanned and receives Allow in the baseline test set.
2. A known direct injection example is detected and blocked.
3. A supported file is extracted and scanned.
4. A malicious instruction in a test document is identified as document-originated.
5. A Flag result is not forwarded without confirmation.
6. Automated tests prove that Block never calls the LLM adapter.
7. A safe request reaches a mocked LLM adapter and returns its response.
8. Every scan decision creates a metadata log entry.
9. Invalid, oversized, and unsupported files return safe error responses.
10. Setup instructions allow another team member to run the application.

## 11. Risks and mitigations

| Risk | Mitigation |
|---|---|
| False negatives | Layer rules, classifier, secure prompt construction, and least-privilege tool permissions. |
| False positives | Flag/review path, labelled test data, threshold tuning. |
| Malicious file/parser payload | Limit file size, allowlist formats, update parsers, isolate processing. |
| Sensitive data in logs | Store metadata only; configure retention and access controls. |
| LLM provider unavailable | Return controlled error; keep scan-only functionality available. |
| Model treats document instructions as trusted | Delimit untrusted content and keep system instructions separate. |

## 12. MVP success metrics

Report measured values on a documented test set:
- Attack recall = detected malicious test cases / all malicious test cases.
- Benign false-positive rate = benign cases incorrectly flagged or blocked / all benign cases.
- Block enforcement = blocked cases that did not call the LLM / all blocked cases.
- File extraction success rate on supported test files.
- Median scan latency, with hardware and classifier settings recorded.

Do not claim production-grade protection based only on a small demonstration dataset.
