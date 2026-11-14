# AGENTS.md — Development Instructions

This file gives coding agents and human contributors the rules for changing this repository.

## Product objective

Build a reusable Flask REST security gateway that inspects untrusted user prompts and uploaded documents before an application forwards them to an LLM. It must return explainable `ALLOW`, `FLAG`, or `BLOCK` decisions and must never send blocked content to the LLM.

## Required engineering principles

1. Keep modules small and single-purpose.
2. Keep detection, risk scoring, policy, extraction, LLM calls, and audit logging separate.
3. Put policy thresholds in one configuration/module; do not duplicate them in routes.
4. Use type hints for public service functions where practical.
5. Return structured findings with stable codes; avoid relying only on free-form messages.
6. Treat all user prompts, uploaded files, extracted text, and retrieved content as untrusted.
7. Never merge document text into trusted system instructions.
8. Never execute content from a prompt or uploaded file.
9. Never call the LLM for a Block decision. Flag must not be forwarded without explicit confirmation.
10. Do not log full prompts, file contents, API keys, or other secrets by default.
11. Keep provider API keys in environment variables; never commit `.env`.
12. Prefer fail-closed behaviour if scanning or extraction fails.
13. Do not claim that a scan proves content is safe.
14. Add or update tests for every behaviour change.

## Coding conventions

- Python: follow PEP 8; use descriptive names.
- Flask: routes should validate and orchestrate, not contain detector logic.
- File handling: use safe temporary paths, size limits, and cleanup.
- API: return consistent JSON and appropriate HTTP status codes.
- Errors: do not expose stack traces, secrets, or internal paths to clients.
- Dependencies: add only necessary packages and pin compatible versions before release.
- Frontend: show the decision, risk score, source, and reason in accessible plain language.

## Required checks before marking a task complete

1. Run the relevant pytest tests.
2. Run the full test suite when practical.
3. Verify Block does not invoke the LLM adapter using a mock/spy.
4. Verify Flag is held pending confirmation.
5. Verify a benign prompt is not automatically blocked by a broad keyword rule.
6. Verify malformed and oversized files return controlled errors.
7. Update `CHANGELOG.md` and `TASKS.md` if scope/status changes.
8. Update `README.md` if setup, configuration, or API behaviour changes.

## Do not

- Add a frontend framework or database server without a clear MVP need.
- Train a large model from scratch.
- make a network call during unit tests.
- hardcode API keys, passwords, or local machine paths.
- silently strip suspicious text and forward the rest as trusted content.
- treat a model-generated “safe” label as authorization.
- add unreviewed file formats or execute embedded content.
- use Flask debug mode in production.

## Definition of done

A feature is done only when its implementation, tests, user-facing behaviour, documentation, and security implications are addressed. If a security limitation remains, document it explicitly rather than describing the feature as complete.
