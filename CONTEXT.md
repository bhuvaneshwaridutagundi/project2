# Project Context

## 1. Project identity

**Project name:** Prompt Injection Security Gateway for AI Applications

**Short description:** A reusable REST-based security service that sits between an AI application and an LLM. It scans untrusted prompts and uploaded documents for prompt-injection indicators, calculates a risk score, and applies Allow, Flag, or Block policies before content is forwarded.

## 2. Problem being solved

LLM applications may treat system instructions, user messages, and retrieved documents as if they have equal authority when content is combined carelessly. Direct prompt injection appears in a user's message. Indirect prompt injection may be embedded in a webpage, PDF, or email that the model later reads. Such content may attempt to override instructions, bypass safeguards, or obtain protected information.

Application developers need a pluggable layer that inspects inputs, applies consistent policy, and records security events.

## 3. Target MVP behaviour

- User submits a text prompt or uploads a PDF, DOCX, or TXT file.
- Gateway extracts document text if required.
- Prompt and document are scanned as separate untrusted sources.
- Detector produces findings with codes, severity, and explanation.
- Risk engine calculates a score from 0 to 100.
- Policy returns Allow, Flag, or Block.
- Blocked content is not forwarded to an LLM.
- Flagged content is held until explicit confirmation/review.
- Allowed requests can be sent to a configured LLM with document content clearly marked as untrusted.
- Scan metadata is recorded in SQLite.

## 4. Current development assumptions

- Team size: 4 students.
- Project level: 5th-semester CSE mini project.
- Primary language: Python.
- Backend: Flask.
- Frontend: HTML, CSS, JavaScript.
- Development environment: VS Code on Windows is the current working environment.
- Database: SQLite for local MVP.
- Initial detection: rule-based; optional ML classifier added after baseline works.
- AI provider: one provider selected and configured using an environment variable; scan-only mode must work without an API key.
- Deployment target: local laptop demonstration.

These are project assumptions and can be updated by the team.

## 5. Key terminology

- **LLM:** Large Language Model that generates responses from input.
- **Prompt injection:** Untrusted content attempting to alter the model's intended behaviour.
- **Direct injection:** Malicious instruction supplied directly by the user.
- **Indirect injection:** Malicious instruction embedded in external content the application retrieves or uploads.
- **Gateway:** Intermediate service that inspects and applies policy before forwarding input.
- **Finding:** A structured detection signal.
- **Risk score:** Heuristic score from 0–100; not a probability.
- **Allow:** Input may proceed to the LLM.
- **Flag:** Input is held for review/confirmation.
- **Block:** Input is rejected and not forwarded.
- **Untrusted content:** User or external data that must not be treated as system/developer instructions.

## 6. Design decisions

1. Flask is used because the team already started with it and it is suitable for a small REST MVP.
2. Rules are implemented first because they are transparent, quick to test, and do not require model downloads.
3. ML classification is optional and additive, not the sole security control.
4. PDF/DOCX/TXT are the initial supported formats.
5. SQLite is sufficient for a local student project.
6. LLM integration is isolated behind an adapter to avoid tying the gateway to one provider.
7. Full prompt/document contents are not stored in audit logs by default.
8. Flag does not silently pass content to the model.

## 7. Known limitations

- Pattern rules cannot understand every context and can miss novel attacks.
- ML classifiers can be wrong and may have language, length, and domain limitations.
- A document parser may not extract text from scanned PDFs or unusual layouts.
- Hidden content in images, OCR layers, metadata, or complex file structures is outside initial scope.
- A safe scan does not guarantee safe model behaviour.
- Provider-side safeguards and application authorization remain necessary.

## 8. Questions to resolve during implementation

- Which LLM provider will the team use for the demo?
- Which compatible classifier and model license are acceptable?
- What maximum upload size is appropriate for the team's laptops?
- Will Flag be shown as a manual review step or a confirmation checkbox?
- What labelled test prompts will be used to measure detection quality?
