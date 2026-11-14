"""Rule-based prompt injection detector."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import re


class FindingCode(str, Enum):
    """Stable codes for detection findings."""
    INSTRUCTION_OVERRIDE = "INSTRUCTION_OVERRIDE"
    ROLE_OVERRIDE = "ROLE_OVERRIDE"
    SECRET_REVEAL = "SECRET_REVEAL"
    SAFETY_BYPASS = "SAFETY_BYPASS"
    DATA_EXFILTRATION = "DATA_EXFILTRATION"


# Finding codes that trigger immediate BLOCK decision (critical override)
CRITICAL_OVERRIDE_CODES = {
    FindingCode.SECRET_REVEAL,
}


@dataclass
class Finding:
    """Structured detection finding."""
    code: FindingCode
    source: str
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    message: str
    confidence: str = "MEDIUM"  # "LOW", "MEDIUM", "HIGH"
    evidence: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "code": self.code.value,
            "source": self.source,
            "severity": self.severity,
            "message": self.message,
            "confidence": self.confidence,
        }


@dataclass
class DetectionResult:
    """Result of scanning text for prompt injection."""
    findings: list[Finding] = field(default_factory=list)
    scan_time_ms: float = 0.0

    @property
    def is_clean(self) -> bool:
        return len(self.findings) == 0


class Detector:
    """Rule-based detector for prompt injection patterns."""

    # Severity assignments
    SEVERITY_MAP = {
        FindingCode.INSTRUCTION_OVERRIDE: "HIGH",
        FindingCode.ROLE_OVERRIDE: "MEDIUM",
        FindingCode.SECRET_REVEAL: "CRITICAL",
        FindingCode.SAFETY_BYPASS: "HIGH",
        FindingCode.DATA_EXFILTRATION: "HIGH",
    }

    def __init__(self, source: str = "user_prompt"):
        self.source = source
        self._patterns = self._build_patterns()

    def _build_patterns(self) -> dict[FindingCode, list[re.Pattern]]:
        """Build regex patterns for each threat type."""
        patterns = {}

        # Instruction override patterns
        patterns[FindingCode.INSTRUCTION_OVERRIDE] = [
            re.compile(
                r"\b(?:ignore|disregard|ignore\s+all|disregard\s+all|"
                r"previous\s+instructions|prior\s+instructions|above\s+instructions)\b",
                re.IGNORECASE
            ),
            re.compile(r"\bforget\s+(?:all\s+)?previous\s+instructions?\b", re.IGNORECASE),
        ]

        # Role/persona override patterns
        patterns[FindingCode.ROLE_OVERRIDE] = [
            # "act as a developer" - requesting role change to a privileged role
            re.compile(r"\bact\s+as\s+a?\s+(?:unrestricted|jailbroken|developer|admin)\b", re.IGNORECASE),
            # "You are now an unrestricted assistant/AI" - persona override
            re.compile(r"\byou\s+(?:are|become|now\s+are)\s+(?:an?\s+)?(?:unrestricted|jailbroken)\s+(?:assistant|AI)\b", re.IGNORECASE),
            re.compile(r"\byou\s+(?:are|become|now\s+are)\s+(?:an?\s+)?(?:unrestricted|jailbroken|developer|admin)\b", re.IGNORECASE),
            re.compile(r"\b(?:ignore\s+all\s+above|disregard\s+all\s+above)\b.*\brole\b", re.IGNORECASE),
            # "act as an unrestricted assistant"
            re.compile(r"\bact\s+as\s+(?:an?\s+)?(?:unrestricted|jailbroken)\b.*\bassistant\b", re.IGNORECASE),
            re.compile(r"\bact\s+as\s+(?:an?\s+)?(?:unrestricted|jailbroken)\b.*\bAI\b", re.IGNORECASE),
            # "unrestricted assistant/AI" phrase
            re.compile(r"\ban?\s+unrestricted\s+assistant\b", re.IGNORECASE),
            re.compile(r"\ban?\s+unrestricted\s+AI\b", re.IGNORECASE),
        ]

        # Secret/system-prompt extraction patterns
        patterns[FindingCode.SECRET_REVEAL] = [
            # "reveal hidden system prompt"
            re.compile(r"\breveal\s+(?:(?:the|your)\s+)?(?:hidden\s+)?system\s*prompt\b", re.IGNORECASE),
            # "reveal confidential/secret information"
            re.compile(r"\breveal\s+(?:all\s+)?(?:confidential|secret|hidden|sensitive)\s+(?:information|data|instructions|credentials)\b", re.IGNORECASE),
            # "reveal secrets" - direct request for secrets
            re.compile(r"\breveal\s+(?:all\s+)?secrets?\b", re.IGNORECASE),
            # "provide me with the API keys" - requesting credentials
            re.compile(r"\b(?:provide|get\s+me|give\s+me)\s+(?:me\s+with\s+)?(?:the\s+)?API\s+keys?\b", re.IGNORECASE),
            # "show me system prompt" (requires context)
            re.compile(r"\b(?:show\s+me|tell\s+me|reveal)\s+(?:the\s+)?(?:hidden\s+)?(?:system\s+)?prompt\b", re.IGNORECASE),
            # "API key" request - must include "key"
            re.compile(r"\b(?:API\s+key|api\s+key|password|credential|secret\s+key)\b", re.IGNORECASE),
        ]

        # Safety bypass patterns
        patterns[FindingCode.SAFETY_BYPASS] = [
            re.compile(r"\b(?:bypass|skip|ignore|disable)\s+(?:all\s+)?(?:safeguards?|restrictions?|protections?|safety)\b", re.IGNORECASE),
            re.compile(r"\bdo\s+not\s+(?:mention|reference|acknowledge|warn)\b.*\bthese\s+instructions?\b", re.IGNORECASE),
        ]

        # Data exfiltration patterns
        patterns[FindingCode.DATA_EXFILTRATION] = [
            re.compile(r"\btransmit\b.*\b(?:to|an?\s+external\s+)?(?:recipient|address|server|endpoint)\b", re.IGNORECASE),
            re.compile(r"\bsend\s+(?:all\s+)?(?:my\s+)?(?:data|information|secrets?|credentials)\b", re.IGNORECASE),
        ]

        return patterns

    def detect(self, text: str) -> DetectionResult:
        """Scan text for prompt injection indicators."""
        findings = []

        if not text or not text.strip():
            return DetectionResult(findings=findings)

        for code, pattern_list in self._patterns.items():
            for pattern in pattern_list:
                match = pattern.search(text)
                if match:
                    finding = Finding(
                        code=code,
                        source=self.source,
                        severity=self.SEVERITY_MAP.get(code, "MEDIUM"),
                        message=self._get_message(code),
                        confidence="HIGH" if code in (FindingCode.SECRET_REVEAL, FindingCode.SAFETY_BYPASS) else "MEDIUM",
                        evidence=match.group(0)[:100],  # Truncate for safety
                    )
                    findings.append(finding)

        return DetectionResult(findings=findings)

    def _get_message(self, code: FindingCode) -> str:
        """Get human-readable message for a finding code."""
        messages = {
            FindingCode.INSTRUCTION_OVERRIDE: "Attempt detected to override or ignore system instructions.",
            FindingCode.ROLE_OVERRIDE: "Attempt detected to change the AI's role or behavior.",
            FindingCode.SECRET_REVEAL: "Request detected to reveal hidden system prompts or secrets.",
            FindingCode.SAFETY_BYPASS: "Attempt detected to bypass safety restrictions or safeguards.",
            FindingCode.DATA_EXFILTRATION: "Attempt detected to exfiltrate data to external recipients.",
        }
        return messages.get(code, "Suspicious instruction pattern detected.")


def scan_text(text: str, source: str = "user_prompt") -> DetectionResult:
    """Convenience function to scan text."""
    detector = Detector(source=source)
    return detector.detect(text)