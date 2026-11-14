# Prompt Injection Security Gateway for AI Applications

A lightweight, reusable security layer that sits between an application and a Large Language Model (LLM). It inspects user prompts and uploaded documents for prompt-injection attempts, assigns a risk score, and applies an `ALLOW`, `FLAG`, or `BLOCK` decision before content is sent to an LLM.

## MVP goals

- Accept plain-text prompts and supported document uploads.
- Extract text from PDF, DOCX, and TXT files.
- Detect suspicious instruction patterns using deterministic rules.
- Optionally run a prompt-injection classifier (for example, a compatible Hugging Face model) as a second signal.
- Calculate and explain a risk score.
- Apply configurable `ALLOW`, `FLAG`, and `BLOCK` policies.
- Forward approved requests to a configured LLM provider.
- Store scan metadata and security decisions in SQLite.
- Expose the scanner as reusable Flask REST endpoints.

> **Security limitation:** A scan result is a risk assessment, not proof that content is safe. Detection can produce false positives and false negatives. Keep retrieved/uploaded content untrusted even after a scan, and enforce authorization and tool permissions outside the LLM.

## MVP scope

### Included
- Flask application and REST API.
- Simple browser interface for text scanning and file uploads.
- PDF, DOCX, and TXT text extraction.
- Rule-based detection for common injection behaviours: instruction override, role/persona manipulation, requests to reveal hidden prompts/secrets, and attempts to bypass safeguards.
- Optional classifier adapter, disabled by default until configured and evaluated.
- Explainable score, policy decision, and scan history.
- LLM adapter with provider configuration via environment variables.

### Not included in the first MVP
- Guaranteed detection of every attack or hidden steganographic content.
- Image OCR, audio/video analysis, archive extraction, or arbitrary web crawling.
- Autonomous agents or execution of tools requested by uploaded content.
- Multi-tenant enterprise authentication, billing, distributed deployment, or high-availability infrastructure.
- Automatic deletion of suspicious sentences and forwarding of the remaining document as trusted content.

## User flow

1. User enters a prompt and optionally uploads one document.
2. The API validates the request and extracts document text.
3. The gateway scans the user prompt and extracted document content as **untrusted data**.
4. The detection layer returns findings and a risk score.
5. The policy engine chooses `ALLOW`, `FLAG`, or `BLOCK`.
6. `BLOCK`: return a warning; do not call the LLM.
7. `FLAG`: in the MVP, require explicit user confirmation or block by default. Never silently pass flagged content.
8. `ALLOW`: forward the original task plus document content in a clearly delimited untrusted-data section to the LLM adapter.
9. Store scan metadata and decision in SQLite; avoid storing full sensitive content by default.

## Suggested technology stack

| Area | Technology |
|---|---|
| Language | Python 3.11 or 3.12 |
| Backend/API | Flask |
| Frontend | HTML, CSS, JavaScript, Bootstrap (optional) |
| PDF extraction | PyMuPDF |
| DOCX extraction | python-docx |
| TXT extraction | Python standard library |
| Detection v1 | Python rules/regular expressions |
| Optional ML detection | Hugging Face Transformers model adapter |
| LLM | Provider adapter for OpenAI or Gemini; configure one provider |
| Database | SQLite |
| Testing | pytest, Flask test client |
| API manual testing | Postman or curl |
| Version control | Git and GitHub |

Use a supported Python version rather than an unreleased interpreter version. Pin dependency versions in `requirements.txt` after confirming compatibility.

## Quick start

```bash
# 1. Create and activate a virtual environment
python -m venv .venv

# Windows PowerShell
.venv\\Scripts\\Activate.ps1

# macOS/Linux
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create local configuration
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux

# 4. Start the app
python app.py
```

Open `http://127.0.0.1:5000`.

The initial implementation should support scanning even when no LLM API key is configured. LLM answering should return a clear configuration error until a provider and key are set.

## Proposed repository structure

```text
prompt-injection-gateway/
├── app.py
├── config.py
├── requirements.txt
├── .env.example
├── README.md
├── PRD.md
├── ARCHITECTURE.md
├── AGENTS.md
├── TASKS.md
├── CONTEXT.md
├── CHANGELOG.md
├── TESTING.md
├── gateway/
│   ├── __init__.py
│   ├── routes.py
│   ├── file_extractor.py
│   ├── detector.py
│   ├── risk.py
│   ├── policy.py
│   ├── llm_client.py
│   └── audit.py
├── templates/
│   └── index.html
├── static/
│   ├── css/style.css
│   └── js/app.js
├── instance/
│   └── gateway.db
└── tests/
    ├── test_detector.py
    ├── test_policy.py
    ├── test_files.py
    └── test_api.py
```

## Configuration

Keep secrets out of source control. Example environment variables:

```dotenv
FLASK_ENV=development
SECRET_KEY=change-this-for-local-development
DATABASE_PATH=instance/gateway.db
MAX_CONTENT_LENGTH_MB=10
FLAG_REQUIRES_CONFIRMATION=true
LLM_PROVIDER=gemini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.5-flash-lite
```

Copy `.env.example` to `.env`, add a Gemini API key from Google AI Studio, and restart Flask. The app reads the key on the server only; never put it in JavaScript or return it from an endpoint. `.env` is ignored by Git.

The browser's **Scan Prompt** action only scans. **Scan & Ask Gemini** sends an approved prompt to Gemini; flagged prompts are held until the user explicitly confirms, and blocked prompts are never sent. The Document Scanner remains scan-only. The `/api/ask` endpoint can also scan and accept extracted `document_text` as untrusted input.

Gemini free-tier model access and quotas can change. Review Google's [current pricing and free-tier terms](https://ai.google.dev/gemini-api/docs/pricing) before use; free-tier requests may be used to improve Google products, so do not send sensitive content.

## API overview

See `ARCHITECTURE.md` for request and response examples. Initial endpoints:

- `POST /api/scan` — scan a text prompt.
- `POST /api/scan-file` — extract and scan a supported file.
- `POST /api/ask` — scan and, only when policy allows, send the request to the configured LLM.
- `GET /api/logs` — list recent scan metadata.

File uploads are limited by `MAX_CONTENT_LENGTH_MB`; unsupported, empty, corrupted, or text-free documents return a controlled error instead of an `ALLOW` result. Scanned PDFs require OCR, which is not supported in this MVP.

## Development order

Follow `TASKS.md`. Build and test text scanning first, then file extraction, risk/policy decisions, logging, and finally LLM integration.

## Responsible use

Use only files and prompts you are authorized to inspect. Treat every uploaded or retrieved document as untrusted. Do not place secrets in prompts or test fixtures. For production use, add authentication, rate limiting, malware scanning, stronger file isolation, retention controls, and security review.
