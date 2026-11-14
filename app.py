"""Flask application entry point for Prompt Injection Security Gateway."""

import os
import time
import uuid
import tempfile
from flask import Flask, request, jsonify, render_template

from config import Config
from gateway import (
    Detector,
    FileExtractor,
    PolicyEngine,
    AuditLogger,
    LLMClient,
)
from gateway.policy import Decision


def create_app(config_class=Config, test_mode=False) -> Flask:
    """Application factory pattern."""
    app = Flask(
        __name__,
        template_folder='templates',
        static_folder='static'
    )
    app.config.from_object(config_class)
    app.config["MAX_CONTENT_LENGTH"] = config_class.MAX_CONTENT_LENGTH

    @app.errorhandler(413)
    def request_too_large(_error):
        return jsonify({
            "decision": "BLOCK",
            "risk_score": 100,
            "severity": "CRITICAL",
            "findings": [],
            "forwarded_to_llm": False,
            "message": "Request exceeds the configured size limit.",
        }), 413

    # Initialize components
    detector = Detector(source="user_prompt")
    document_detector = Detector(source="uploaded_document")
    file_extractor = FileExtractor(max_size_bytes=app.config["MAX_CONTENT_LENGTH"])
    policy_engine = PolicyEngine(
        allow_threshold=app.config.get("ALLOW_THRESHOLD", 29),
        flag_threshold=app.config.get("FLAG_THRESHOLD", 69),
        flag_requires_confirmation=app.config.get("FLAG_REQUIRES_CONFIRMATION", True),
    )
    audit_logger = AuditLogger(config_class())
    llm_client = LLMClient(config_class())

    # Store components in app context for reuse
    app.detector = detector
    app.document_detector = document_detector
    app.file_extractor = file_extractor
    app.policy_engine = policy_engine
    app.audit_logger = audit_logger
    app.llm_client = llm_client

    @app.route("/")
    def index():
        """Render the main UI page."""
        return render_template("index.html")

    @app.route("/health")
    def health():
        """Health check endpoint."""
        return jsonify({
            "status": "healthy",
            "llm_configured": llm_client.is_configured,
            "provider": llm_client.provider_name,
            "model": llm_client.model_name if llm_client.is_configured else None,
        })

    @app.route("/api/scan", methods=["POST"])
    def scan_text():
        """Scan a text prompt for prompt injection indicators."""
        start_time = time.time()
        scan_id = str(uuid.uuid4())[:8]

        data = request.get_json(silent=True) or {}
        text = data.get("text", "")

        if not text or not text.strip():
            return jsonify({
                "scan_id": scan_id,
                "decision": "BLOCK",
                "risk_score": 100,
                "severity": "CRITICAL",
                "findings": [],
                "forwarded_to_llm": False,
                "message": "Empty or missing text prompt."
            }), 400

        # Detect
        detection_result = detector.detect(text)
        findings = detection_result.findings

        # Risk score
        scores = policy_engine.scorer.calculate_score(findings)
        contributing_codes = policy_engine.scorer.get_contributing_codes(findings)

        # Policy decision
        policy_result = policy_engine.decide(findings)

        # Log
        duration_ms = (time.time() - start_time) * 1000
        app.audit_logger.log(
            scan_id=scan_id,
            input_type="text",
            decision=policy_result.decision.value,
            risk_score=scores,
            finding_codes=[f.code.value for f in findings],
            duration_ms=duration_ms,
            llm_invoked=False,
        )

        response = {
            "scan_id": scan_id,
            "decision": policy_result.decision.value,
            "risk_score": scores,
            "severity": _get_severity(scores),
            "findings": [f.to_dict() for f in findings],
            "forwarded_to_llm": False,
            "message": policy_result.message,
        }

        return jsonify(response)

    @app.route("/api/scan-file", methods=["POST"])
    def scan_file():
        """Extract and scan an uploaded document."""
        start_time = time.time()
        scan_id = str(uuid.uuid4())[:8]

        if "file" not in request.files:
            return jsonify({
                "scan_id": scan_id,
                "decision": "BLOCK",
                "risk_score": 100,
                "severity": "CRITICAL",
                "findings": [],
                "forwarded_to_llm": False,
                "message": "No file provided."
            }), 400

        file = request.files["file"]
        filename = file.filename or "unknown"

        # Validate
        is_valid, error = file_extractor.validate_file(filename, 0)
        if not is_valid:
            return jsonify({
                "scan_id": scan_id,
                "decision": "BLOCK",
                "risk_score": 100,
                "severity": "CRITICAL",
                "findings": [],
                "forwarded_to_llm": False,
                "message": error,
            }), 400

        # Use a generated path; never include the untrusted upload filename.
        temp_fd, temp_path = tempfile.mkstemp(prefix="gateway_upload_")
        os.close(temp_fd)

        try:
            file.save(temp_path)

            # Extract
            extraction_result = file_extractor.extract(temp_path, filename)

            if not extraction_result.success:
                return jsonify({
                    "scan_id": scan_id,
                    "decision": "BLOCK",
                    "risk_score": 100,
                    "severity": "CRITICAL",
                    "findings": [],
                    "forwarded_to_llm": False,
                    "message": extraction_result.error or "Extraction failed.",
                    "file_type": extraction_result.file_type,
                }), 400

            # Detect in document text
            detection_result = document_detector.detect(extraction_result.text)
            findings = detection_result.findings

            # Risk score
            scores = policy_engine.scorer.calculate_score(findings)
            contributing_codes = policy_engine.scorer.get_contributing_codes(findings)

            # Policy decision
            policy_result = policy_engine.decide(findings)

            # Log
            duration_ms = (time.time() - start_time) * 1000
            app.audit_logger.log(
                scan_id=scan_id,
                input_type="file",
                decision=policy_result.decision.value,
                risk_score=scores,
                finding_codes=[f.code.value for f in findings],
                duration_ms=duration_ms,
                llm_invoked=False,
                file_extension=os.path.splitext(filename)[1].lower(),
            )

            response = {
                "scan_id": scan_id,
                "decision": policy_result.decision.value,
                "risk_score": scores,
                "severity": _get_severity(scores),
                "findings": [f.to_dict() for f in findings],
                "forwarded_to_llm": False,
                "message": policy_result.message,
                "extracted_text_length": len(extraction_result.text),
                "page_count": extraction_result.page_count,
            }

            return jsonify(response)

        finally:
            # Cleanup temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)

    @app.route("/api/ask", methods=["POST"])
    def ask_llm():
        """Scan and optionally forward to LLM."""
        start_time = time.time()
        scan_id = str(uuid.uuid4())[:8]

        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            data = {}
        text = data.get("text", "")
        document_text = data.get("document_text", "")
        flag_confirmed = data.get("flag_confirmation") is True

        if not isinstance(text, str) or not text.strip():
            return jsonify({
                "scan_id": scan_id,
                "decision": "BLOCK",
                "risk_score": 100,
                "severity": "CRITICAL",
                "findings": [],
                "forwarded_to_llm": False,
                "message": "Empty or missing text prompt."
            }), 400
        if not isinstance(document_text, str):
            return jsonify({
                "scan_id": scan_id,
                "decision": "BLOCK",
                "risk_score": 100,
                "severity": "CRITICAL",
                "findings": [],
                "forwarded_to_llm": False,
                "message": "Document text must be a string.",
            }), 400

        # Detect in user text
        detection_result = detector.detect(text)
        findings = detection_result.findings

        # Add document findings if present
        if document_text:
            doc_detection = document_detector.detect(document_text)
            findings.extend(doc_detection.findings)

        # Risk score
        scores = policy_engine.scorer.calculate_score(findings)
        contributing_codes = policy_engine.scorer.get_contributing_codes(findings)

        # Policy decision
        policy_result = policy_engine.decide(findings)

        # Determine if we can forward
        can_forward = policy_engine.is_forward_allowed(policy_result, flag_confirmed)

        llm_invoked = False
        answer = None
        llm_error = None

        if can_forward:
            if app.llm_client.is_configured:
                llm_invoked = True
                llm_response = app.llm_client.generate(
                    text, document_text if document_text else None
                )
                if llm_response.success and llm_response.content:
                    answer = llm_response.content
                else:
                    llm_error = llm_response.error or "LLM returned an empty response."
            else:
                llm_error = "LLM provider is not configured. Set its API key to generate answers."
        elif policy_result.decision == Decision.BLOCK:
            llm_error = "Request blocked by security policy. Content not forwarded to LLM."
        elif policy_result.decision == Decision.FLAG and not flag_confirmed:
            llm_error = "Request flagged for review. Confirm with flag_confirmation=true to allow forwarding."

        # Log
        duration_ms = (time.time() - start_time) * 1000
        app.audit_logger.log(
            scan_id=scan_id,
            input_type="text",
            decision=policy_result.decision.value,
            risk_score=scores,
            finding_codes=[f.code.value for f in findings],
            duration_ms=duration_ms,
            llm_invoked=llm_invoked,
        )

        response = {
            "scan_id": scan_id,
            "decision": policy_result.decision.value,
            "risk_score": scores,
            "severity": _get_severity(scores),
            "findings": [f.to_dict() for f in findings],
            "forwarded_to_llm": llm_invoked,
            "answer": answer,
            "message": policy_result.message,
            "requires_confirmation": policy_result.requires_confirmation,
        }

        if llm_error:
            response["error"] = llm_error

        return jsonify(response)

    @app.route("/api/logs", methods=["GET"])
    def get_logs():
        """Get recent scan logs."""
        limit = request.args.get("limit", 100, type=int)
        limit = min(limit, 1000)  # Cap the limit

        logs = app.audit_logger.get_recent_scans(limit)
        return jsonify({"logs": logs, "count": len(logs)})

    return app


def _get_severity(score: int) -> str:
    """Convert risk score to severity label."""
    if score <= 29:
        return "LOW"
    elif score <= 69:
        return "MEDIUM"
    else:
        return "HIGH"


# Create app instance for direct execution
app = create_app()

if __name__ == "__main__":
    # Get port from environment or default to 5000
    port = int(os.environ.get("PORT", 5000))
    # Debug mode should be controlled by FLASK_ENV
    debug = os.environ.get("FLASK_ENV") == "development"

    app.run(host="0.0.0.0", port=port, debug=debug)