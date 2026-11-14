"""Risk scoring engine."""

from typing import Dict, List, Set
from .detector import Finding, FindingCode


# Severity weights for risk scoring
SEVERITY_WEIGHTS: Dict[str, int] = {
    "LOW": 10,
    "MEDIUM": 20,
    "HIGH": 35,
    "CRITICAL": 50,
}

# Critical override codes that bypass normal threshold
CRITICAL_OVERRIDE_CODES: Set[FindingCode] = {
    FindingCode.SECRET_REVEAL,
}


class RiskScorer:
    """Calculate risk scores from detection findings."""

    def __init__(self, max_score: int = 100):
        self.max_score = max_score

    def calculate_score(self, findings: List[Finding]) -> int:
        """
        Calculate a risk score from 0 to 100 based on findings.

        Rules:
        - Each finding contributes points based on severity
        - Duplicate matches of same code don't inflate score
        - Total is capped at 100
        - Critical findings trigger immediate high score
        """
        if not findings:
            return 0

        # Check for critical override
        for finding in findings:
            if finding.code in CRITICAL_OVERRIDE_CODES:
                return self.max_score

        # Calculate weighted score, deduplicating by code
        seen_codes: Set[FindingCode] = set()
        total_score = 0

        for finding in findings:
            if finding.code not in seen_codes:
                weight = SEVERITY_WEIGHTS.get(finding.severity, 10)
                total_score += weight
                seen_codes.add(finding.code)

        return min(total_score, self.max_score)

    def get_contributing_codes(self, findings: List[Finding]) -> List[str]:
        """Get unique finding codes that contributed to the score."""
        return list({f.code.value for f in findings})


class RiskResult:
    """Result of risk scoring."""

    def __init__(self, score: int, contributing_codes: List[str]):
        self._score = score
        self._codes = contributing_codes

    @property
    def score(self) -> int:
        return self._score

    @property
    def contributing_codes(self) -> List[str]:
        return self._codes

    def to_dict(self) -> dict:
        return {
            "risk_score": self._score,
            "contributing_codes": self._codes,
        }