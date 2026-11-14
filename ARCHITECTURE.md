# Architecture
## Prompt Injection Security Gateway for AI Applications

## 1. Architectural style

A modular Flask application exposing REST endpoints. The gateway is a security boundary between an AI application and an LLM provider.

```text
User / Client Application
        |
        v
Frontend (HTML/CSS/JavaScript) or REST Client
        |
        v
Flask API Layer
        |
        v
Input Validation + File Extraction
        |
        v
Detection Orchestrator
   |          |            |
   v          v            v
Rule Engine  ML Classifier  Source/Context Analysis
   |          |            |
   +----------+------------+
              |
              v
       Risk Scoring Engine
              |
              v
        Policy Decision
       /      |       \\
   ALLOW     FLAG     BLOCK
     |        |         |
     v        v         v
 LLM Adapter Hold for   Security
     |       review      response
     v
 LLM Provider
     |
     v
Response returned to client

All decisions ---> Audit Logger ---> SQLite
```

## 2. Trust boundaries

- System/developer instructions are trusted configuration owned by the application.
- User prompts are untrusted.
- Uploaded files and extracted document text are untrusted.
- Retrieved webpages, emails, and external tool output are untrusted.
- Detector output is a risk signal, not an authorization decision.
- LLM output is also untrusted and must not be allowed to authorize privileged actions.

Never concatenate untrusted content into the system-instruction string. Keep instructions and data in separate message fields where the provider supports roles. Clearly delimit untrusted document text and tell the model to treat it as data to analyze, not instructions to follow. Enforce access control and tool permissions in application code, not through prompt wording alone.

## 3. Components

### 3.1 Flask API / routes
Responsibilities:
- Validate request shape and content type.
- Enforce upload size limits.
- Call extraction and scanning services.
- Apply policy.
- Invoke the LLM adapter only when permitted.
- Return consistent JSON responses.

### 3.2 File extractor
Supported MVP formats:
- `.txt`: decode UTF-8; handle decode errors safely.
- `.pdf`: extract text with PyMuPDF; report when no selectable text is present.
- `.docx`: extract paragraphs and table text with python-docx.

Do not trust the filename or browser MIME type alone. Check extension and content where practical. Do not execute macros or embedded content. Scanned PDF OCR is outside MVP scope and should return an informative message.

### 3.3 Detection orchestrator
Runs independent detectors over labelled sources:
- `user_prompt`
- `uploaded_document`
- Future: `retrieved_content`

Each finding should include:
- stable finding code,
- human-readable explanation,
- severity,
- source,
- matched evidence span or safe excerpt where appropriate,
- detector name/version.

Avoid returning sensitive full content in logs or UI.

### 3.4 Rule detector
Initial rule categories:
- instruction override: “ignore/disregard previous instructions”
- role/persona override: “you are now…”, “act as…”
- hidden prompt/secret extraction: requests for system prompts, credentials, keys, or confidential data
- safety bypass: requests to bypass safeguards or restrictions
- data exfiltration / unauthorized disclosure instructions
- suspicious instruction embedded in quoted or document content

Rules must be tested against benign contexts. A phrase can be discussed academically without being an attack; source, intent, and surrounding context matter.

### 3.5 Optional ML detector
Provide an adapter interface such as `classify(text) -> findings`. Use a compatible, documented prompt-injection classifier from Hugging Face only after checking its model card, license, input format, limitations, and hardware requirements. Keep it optional so the application works without model downloads or GPU.

Do not treat the classifier's output as ground truth. Combine it with rules and evaluate false positives/negatives.

### 3.6 Risk scoring engine
Convert findings into a bounded score from 0 to 100. Suggested initial approach:
- each finding contributes points based on severity and confidence;
- repeated duplicate matches should not inflate score without limit;
- cap the total at 100;
- record the contributing finding codes;
- apply a critical-signal override for high-confidence severe behaviour.

Illustrative starting weights (tune with test data):
- low: 10
- medium: 20
- high: 35
- critical: 50

Do not describe this score as a probability.

### 3.7 Policy engine
Centralized policy:
- `ALLOW`: score 0–29 and no critical override.
- `FLAG`: score 30–69; hold request and require explicit review/confirmation.
- `BLOCK`: score 70–100 or critical override.

Default safe behaviour: if detector fails, file extraction is incomplete, or policy cannot decide, do not forward the content automatically. Return a controlled error or Flag decision.

### 3.8 LLM adapter
A provider-neutral interface:
- `generate(user_task, untrusted_context) -> answer`
- provider and model configured via environment variables.
- no API key hardcoded in source.
- timeout and error handling.
- do not call for Block.
- do not call for Flag unless the user explicitly confirms and policy permits it.

For document Q&A, the model receives the user's task separately from document content. Document content must be labelled untrusted. Do not allow the document to change system instructions or authorize tools.

### 3.9 Audit logger
Store minimal metadata:
- scan ID, timestamp, input type, file extension (if any), score, decision, finding codes, detector versions, processing duration, LLM invoked (yes/no).
Do not store complete prompt/file text by default. If full-content logging is ever added, require explicit consent, access control, retention limits, and redaction.

## 4. API contracts

### POST `/api/scan`
Request:
```json
{
  "text": "Explain what a firewall is."
}
```

Response:
```json
{
  "scan_id": "generated-id",
  "decision": "ALLOW",
  "risk_score": 0,
  "severity": "LOW",
  "findings": [],
  "forwarded_to_llm": false,
  "message": "No suspicious indicators were detected."
}
```

### POST `/api/scan-file`
Multipart form data:
- `file`: one PDF, DOCX, or TXT file
- optional `task`: what the user wants the AI to do with the file

Response uses the same scan-result structure and includes `source: "uploaded_document"` in findings.

### POST `/api/ask`
Request:
```json
{
  "text": "Summarize the attached document.",
  "document_text": "Extracted content supplied by the trusted application layer.",
  "flag_confirmation": false
}
```

The public API should normally accept a file or a server-generated document reference rather than trusting arbitrary client-supplied `document_text`. This example shows the internal service shape only.

Response on Block:
```json
{
  "scan_id": "generated-id",
  "decision": "BLOCK",
  "risk_score": 90,
  "findings": [
    {
      "code": "INSTRUCTION_OVERRIDE",
      "source": "uploaded_document",
      "severity": "HIGH",
      "message": "The document contains an instruction attempting to override the AI's task."
    }
  ],
  "forwarded_to_llm": false,
  "answer": null
}
```

Response on Allow with configured LLM:
```json
{
  "scan_id": "generated-id",
  "decision": "ALLOW",
  "risk_score": 0,
  "findings": [],
  "forwarded_to_llm": true,
  "answer": "A firewall monitors and controls network traffic..."
}
```

### GET `/api/logs`
Returns recent metadata records. Add pagination and authentication before exposing logs beyond local development.

### GET `/health`
Returns service status and whether optional components are configured. Never expose secrets.

## 5. Suggested code structure

```text
app.py
config.py
gateway/
  routes.py
  file_extractor.py
  detector.py
  classifier.py
  risk.py
  policy.py
  llm_client.py
  audit.py
templates/index.html
static/css/style.css
static/js/app.js
tests/
```

## 6. Data flow and sequence

1. Client submits text or a file.
2. API validates size, extension, and request fields.
3. Extractor obtains text; extraction status is retained.
4. Orchestrator scans prompt and document as separate sources.
5. Risk engine calculates score and records reasons.
6. Policy engine returns Allow, Flag, or Block.
7. Block: do not invoke LLM.
8. Flag: hold; require explicit confirmation and apply a documented policy.
9. Allow: construct a provider request with trusted instructions separate from untrusted user/document data.
10. Audit metadata is written and response returned.

## 7. Security controls for MVP

- Maximum upload size (initial default: 10 MB).
- Extension/content validation and safe temporary-file handling.
- No execution of uploaded files, macros, scripts, or extracted instructions.
- Secrets only in environment variables.
- No full-content logging by default.
- LLM call gated by policy in one centralized function.
- Provider timeouts and exception handling.
- Fail closed for blocked/uncertain inputs.
- Tests assert that blocked inputs never reach the LLM adapter.

## 8. Deployment boundary

MVP target is local development on a student laptop. Flask debug mode is development-only. Before any public deployment, add authentication, HTTPS, rate limiting, CSRF protection for browser forms, secure file storage, retention controls, monitoring, and a production WSGI server.
