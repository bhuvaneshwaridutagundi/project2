# MASTER PROMPT: Develop Prompt Injection Security Gateway MVP

Act as a Senior Python Developer, Cybersecurity Engineer, AI/ML Engineer, and Software Architect.

I am developing a 5th-semester Computer Science Engineering mini project titled:

**Prompt Injection Security Gateway for AI Applications**

I have provided the following eight project documentation files:

1. README.md
2. PRD.md
3. ARCHITECTURE.md
4. AGENTS.md
5. TASKS.md
6. CONTEXT.md
7. CHANGELOG.md
8. TESTING.md

## 1. First: Understand the project documentation

Before writing any code:

- Read all eight Markdown files completely.
- Understand the project requirements, architecture, technology stack, development tasks, security requirements, and testing strategy.
- Treat these documents as the primary source of truth.
- Identify missing information or conflicts between documents.
- Do not ignore or unnecessarily change the documented requirements.
- Follow AGENTS.md throughout development.

## 2. Project objective

Build a reusable Prompt Injection Security Gateway that acts as an intermediate security layer between a user/application and an LLM.

The gateway must inspect both direct user prompts and indirect malicious instructions embedded in uploaded documents.

The expected workflow is:

USER → GATEWAY → SECURITY ANALYSIS → RISK SCORING → DECISION ENGINE → AI MODEL (if allowed).

The gateway must:

1. Accept user text prompts.
2. Accept PDF, DOCX, and TXT file uploads.
3. Extract readable text from uploaded documents.
4. Detect malicious prompt-injection instructions.
5. Identify suspicious behaviour and its source.
6. Calculate a risk score between 0 and 100.
7. Apply ALLOW, FLAG, or BLOCK decisions.
8. Prevent blocked content from reaching the AI model.
9. Forward approved requests to an actual configured LLM.
10. Display the AI-generated answer for approved requests.
11. Maintain security logs using SQLite.

## 3. Required technology stack

Use the following technologies:

- Python 3.11 or 3.12
- Flask for backend development.
- HTML, CSS, JavaScript and Bootstrap for frontend.
- PyMuPDF for PDF extraction.
- python-docx for Word document extraction.
- Python Regex for rule-based threat detection.
- Hugging Face Transformers for optional ML-based prompt-injection detection.
- Python for risk scoring and decision-making.
- SQLite for security logs.
- OpenAI API or Gemini API for LLM integration.
- pytest for automated testing.

Do not introduce unnecessary technologies or change the stack without explaining why.

## 4. Required project architecture

Create a modular and maintainable project structure based on ARCHITECTURE.md.

Separate the application into:

- Flask API and routes.
- Input validation.
- File extraction.
- Rule-based threat detection.
- Optional ML-based detection.
- Risk scoring.
- Security decision engine.
- LLM integration.
- Security audit logging.
- Frontend interface.
- Automated tests.

Do not put the entire project implementation inside app.py.

## 5. Core security functionality

### A. Text scanning

When a user enters a prompt:

- Analyze the input.
- Detect instruction overrides.
- Detect attempts to reveal hidden system prompts or secrets.
- Detect role manipulation and safety bypass attempts.
- Identify suspicious instructions based on context.
- Return structured findings.

### B. File scanning

When a user uploads a document:

- Validate file type and size.
- Extract readable text.
- Scan the extracted content.
- Identify whether a threat originated from the user prompt or uploaded document.
- Display detected suspicious instructions and their locations where possible.
- Do not forward blocked document content to the LLM.

### C. Risk scoring

Implement an explainable scoring system from 0 to 100.

Use the thresholds defined in PRD.md:

- 0–29: ALLOW
- 30–69: FLAG
- 70–100: BLOCK

Avoid duplicate scoring for repeated matches. Add a critical-threat override where appropriate.

### D. Decision engine

ALLOW:
Forward the approved user request to the configured LLM.

FLAG:
Hold the request and require explicit user review or confirmation. Never forward automatically.

BLOCK:
Reject the request, show a security warning, and do not call the LLM.

### E. AI integration

Create a provider-neutral LLM integration module.

- Configure the provider using environment variables.
- Keep API keys secret.
- Separate trusted system instructions from untrusted user and document content.
- Clearly label document content as untrusted data.
- Handle API errors and timeouts.
- Ensure blocked requests never reach the LLM.

The scanner must also work when no LLM API key is configured.

## 6. Frontend requirements

Create a clean, professional cybersecurity dashboard.

Include:

1. Dashboard with total scans, threats detected and blocked requests.
2. Text scanning section.
3. File upload section.
4. Risk score display.
5. ALLOW, FLAG and BLOCK result indicators.
6. Detected threat explanations.
7. AI response section for allowed requests.
8. Security logs and scan history.

Use a modern cybersecurity design with a professional dark-blue theme, clear typography, responsive layout, and intuitive navigation.

Do not create decorative buttons that have no functionality.

## 7. Development methodology

Develop the project according to TASKS.md in the following order:

Phase 1: Project setup and environment configuration.

Phase 2: Rule-based text scanning.

Phase 3: Risk scoring and decision engine.

Phase 4: PDF, DOCX and TXT file scanning.

Phase 5: Flask REST API and frontend integration.

Phase 6: SQLite security logging.

Phase 7: Actual LLM integration.

Phase 8: Optional Hugging Face classifier integration.

Phase 9: Automated testing and final validation.

Complete and test one phase before moving to the next.

## 8. Testing requirements

Follow TESTING.md.

Test:

- Normal educational prompts.
- Direct prompt injection.
- Indirect prompt injection inside uploaded documents.
- Hidden or suspicious document instructions where extractable.
- Unsupported files.
- Empty files.
- Oversized files.
- False positives.
- False negatives.
- Risk score boundaries.
- LLM API failures.
- Block decisions without LLM calls.
- Flag decisions without confirmation.

Use mocked LLM calls for automated tests.

## 9. Coding instructions

For every development phase:

1. Explain what the module does.
2. Show the exact folder and file to create.
3. Provide complete working code.
4. Explain where each code section belongs.
5. Provide the terminal commands to install dependencies and run it.
6. Explain how to test the feature.
7. Show expected output.
8. Fix errors before proceeding to the next phase.

Do not provide incomplete code, unexplained code snippets, or placeholder implementations presented as finished features.

If a feature requires an API key, explain how to configure it safely.

Never hardcode secrets.

## 10. Important restrictions

- Follow all eight documentation files.
- Do not skip development phases.
- Do not replace Flask with another framework.
- Do not use Streamlit.
- Do not train a large ML model from scratch.
- Do not claim 100% prompt-injection detection.
- Do not forward blocked inputs to the LLM.
- Do not silently remove suspicious text and treat the remainder as trusted.
- Keep the project suitable for a 5th-semester CSE mini-project.
- Prioritize a working, testable MVP over unnecessary advanced features.

## 11. Final expected deliverable

At completion, provide:

- Complete working source code.
- Organized project folder structure.
- requirements.txt.
- .env.example.
- All eight documentation files updated if implementation decisions change.
- Functional web interface.
- REST API endpoints.
- Text and file scanning.
- Risk scoring and Allow/Flag/Block decisions.
- LLM integration.
- SQLite security logs.
- Automated test suite.
- Setup and execution instructions.
- Sample malicious and benign test files.
- Final testing report.

## 12. Start now

First, inspect all eight Markdown documentation files.

Then provide:

1. Your understanding of the project.
2. The final proposed folder structure.
3. Any missing dependencies.
4. A phase-by-phase implementation plan.

After that, begin Phase 1.

Do not attempt to build the entire application in one response. Work incrementally, verify each phase, and maintain the existing project structure.