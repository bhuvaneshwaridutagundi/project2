"""Policy decision engine."""

from enum import Enum
from dataclasses import dataclass
from typing import Optional

from .risk import RiskScorer, RiskResult
from .detector import Finding, FindingCode, CRITICAL_OVERRIDE_CODES


class Decision(Enum):
    """Policy decision outcomes."""
    ALLOW = "ALLOW"
    FLAG = "FLAG"
    BLOCK = "BLOCK"


@dataclass
class PolicyResult:
    """Result of policy decision."""
    decision: Decision
    score: int
    message: str
    requires_confirmation: bool

    def to_dict(self) -> dict:
        return {
            "decision": self.decision.value,
            "risk_score": self.score,
            "message": self.message,
            "requires_confirmation": self.requires_confirmation,
        }


class PolicyEngine:
    """
    Centralized policy engine for ALLOW/FLAG/BLOCK decisions.

    Thresholds (configurable):
    - 0-29: ALLOW
    - 30-69: FLAG
    - 70-100: BLOCK

    Critical override: SECRET_REVEAL and other critical patterns force BLOCK.
    """

    def __init__(
        self,
        allow_threshold: int = 29,
        flag_threshold: int = 69,
        flag_requires_confirmation: bool = True,
    ):
        self.allow_threshold = allow_threshold
        self.flag_threshold = flag_threshold
        self.flag_requires_confirmation = flag_requires_confirmation
        self.scorer = RiskScorer()

    def decide(self, findings: list[Finding]) -> PolicyResult:
        """
        Make a policy decision based on detection findings.

        Returns a PolicyResult with the decision, score, and explanation.
        """
        scores = self.scorer.calculate_score(findings)
        contributing_codes = self.scorer.get_contributing_codes(findings)

        # Check for critical override (BLOCK)
        if self._has_critical_override(findings):
            return PolicyResult(
                decision=Decision.BLOCK,
                score=scores,
                message="Critical threat detected requiring immediate block.",
                requires_confirmation=False,
            )

        # Apply thresholds
        if scores <= self.allow_threshold:
            if not findings:
                return PolicyResult(
                    decision=Decision.ALLOW,
                    score=0,
                    message="No suspicious indicators were detected.",
                    requires_confirmation=False,
                )
            return PolicyResult(
                decision=Decision.ALLOW,
                score=scores,
                message="Content passed risk assessment with low risk score.",
                requires_confirmation=False,
            )
        elif scores <= self.flag_threshold:
            return PolicyResult(
                decision=Decision.FLAG,
                score=scores,
                message=f"Content requires review (risk score: {scores}). Suspicious patterns detected.",
                requires_confirmation=self.flag_requires_confirmation,
            )
        else:
            return PolicyResult(
                decision=Decision.BLOCK,
                score=scores,
                message=f"Content blocked due to high risk score ({scores}). Potential prompt injection detected.",
                requires_confirmation=False,
            )

    def _has_critical_override(self, findings: list[Finding]) -> bool:
        """Check if any finding triggers critical override."""
        for finding in findings:
            if finding.code in CRITICAL_OVERRIDE_CODES:
                return True
        return False

    def is_forward_allowed(self, result: PolicyResult, flag_confirmed: bool = False) -> bool:
        """
        Check if content should be forwarded to LLM.

        ALLOW: always forward
        FLAG: only if confirmed
        BLOCK: never forward
        """
        if result.decision == Decision.ALLOW:
            return True
        if result.decision == Decision.FLAG:
            return flag_confirmed
        return False