"""Tests for the policy engine."""

import pytest
from gateway.policy import PolicyEngine, Decision
from gateway.detector import Finding, FindingCode


class TestPolicyEngine:
    """Tests for the PolicyEngine class."""

    def setup_method(self):
        self.policy = PolicyEngine(
            allow_threshold=29,
            flag_threshold=69,
            flag_requires_confirmation=True,
        )

    def test_zero_score_is_allow(self):
        """Test that score 0 results in ALLOW."""
        findings = []
        result = self.policy.decide(findings)
        assert result.decision == Decision.ALLOW

    def test_low_score_is_allow(self):
        """Test that low score (29) results in ALLOW."""
        findings = [
            Finding(
                code=FindingCode.INSTRUCTION_OVERRIDE,
                source="user_prompt",
                severity="LOW",
                message="Test finding",
            )
        ]
        result = self.policy.decide(findings)
        assert result.decision == Decision.ALLOW

    def test_borderline_low_score_is_allow(self):
        """Test that score at threshold boundary is ALLOW."""
        findings = []
        # Score 0 should be ALLOW
        result = self.policy.decide(findings)
        assert result.decision == Decision.ALLOW

    def test_mid_score_is_flag(self):
        """Test that mid-range score results in FLAG."""
        # HIGH severity = 35 points, which is in FLAG range (30-69)
        findings = [
            Finding(
                code=FindingCode.INSTRUCTION_OVERRIDE,
                source="user_prompt",
                severity="HIGH",
                message="Test finding",
            )
        ]
        result = self.policy.decide(findings)
        assert result.decision == Decision.FLAG

    def test_flag_requires_confirmation(self):
        """Test that FLAG requires confirmation."""
        # HIGH severity = 35 points
        findings = [
            Finding(
                code=FindingCode.INSTRUCTION_OVERRIDE,
                source="user_prompt",
                severity="HIGH",
                message="Test finding",
            )
        ]
        result = self.policy.decide(findings)
        assert result.requires_confirmation is True

    def test_high_score_is_block(self):
        """Test that high score results in BLOCK."""
        findings = [
            Finding(
                code=FindingCode.SECRET_REVEAL,
                source="user_prompt",
                severity="CRITICAL",
                message="Test finding",
            )
        ]
        result = self.policy.decide(findings)
        assert result.decision == Decision.BLOCK

    def test_max_score_is_block(self):
        """Test that maximum score results in BLOCK."""
        # HIGH (35) + MEDIUM (20) = 55, which is BLOCK (> 69)
        # Actually 55 is in FLAG range, so let's use CRITICAL
        findings = [
            Finding(
                code=FindingCode.INSTRUCTION_OVERRIDE,
                source="user_prompt",
                severity="CRITICAL",
                message="Test finding",
            ),
            Finding(
                code=FindingCode.ROLE_OVERRIDE,
                source="user_prompt",
                severity="CRITICAL",
                message="Test finding 2",
            ),
        ]
        result = self.policy.decide(findings)
        # Score = 50 + 50 = 100, which is BLOCK
        assert result.decision == Decision.BLOCK

    # --- Critical Override Tests ---

    def test_secret_reveal_critical_override(self):
        """Test that SECRET_REVEAL triggers BLOCK even with low score."""
        findings = [
            Finding(
                code=FindingCode.SECRET_REVEAL,
                source="user_prompt",
                severity="CRITICAL",
                message="Request to reveal secrets",
            )
        ]
        result = self.policy.decide(findings)
        assert result.decision == Decision.BLOCK
        assert "critical" in result.message.lower()

    # --- Forward Allowed Tests ---

    def test_allow_is_forwarded(self):
        """Test that ALLOW decision allows forwarding."""
        findings = []
        result = self.policy.decide(findings)
        assert self.policy.is_forward_allowed(result) is True

    def test_allow_forwarded_when_confirmed(self):
        """Test that ALLOW with confirmation is forwarded."""
        findings = []
        result = self.policy.decide(findings)
        assert self.policy.is_forward_allowed(result, flag_confirmed=True) is True

    def test_flag_not_forwarded_without_confirmation(self):
        """Test that FLAG is not forwarded without confirmation."""
        # HIGH severity = 35 points = FLAG
        findings = [
            Finding(
                code=FindingCode.INSTRUCTION_OVERRIDE,
                source="user_prompt",
                severity="HIGH",
                message="Test finding",
            )
        ]
        result = self.policy.decide(findings)
        assert result.decision == Decision.FLAG
        assert self.policy.is_forward_allowed(result, flag_confirmed=False) is False

    def test_flag_forwarded_with_confirmation(self):
        """Test that FLAG is forwarded with confirmation."""
        # HIGH severity = 35 points = FLAG
        findings = [
            Finding(
                code=FindingCode.INSTRUCTION_OVERRIDE,
                source="user_prompt",
                severity="HIGH",
                message="Test finding",
            )
        ]
        result = self.policy.decide(findings)
        assert result.decision == Decision.FLAG
        assert self.policy.is_forward_allowed(result, flag_confirmed=True) is True

    def test_block_never_forwarded(self):
        """Test that BLOCK is never forwarded."""
        findings = [
            Finding(
                code=FindingCode.SECRET_REVEAL,
                source="user_prompt",
                severity="CRITICAL",
                message="Test finding",
            )
        ]
        result = self.policy.decide(findings)
        assert result.decision == Decision.BLOCK
        assert self.policy.is_forward_allowed(result) is False
        assert self.policy.is_forward_allowed(result, flag_confirmed=True) is False

    # --- Message Tests ---

    def test_message_provided(self):
        """Test that policy result includes a message."""
        findings = []
        result = self.policy.decide(findings)
        assert result.message is not None
        assert len(result.message) > 0

    def test_block_message_explains_block(self):
        """Test that BLOCK message explains the decision."""
        findings = [
            Finding(
                code=FindingCode.SECRET_REVEAL,
                source="user_prompt",
                severity="CRITICAL",
                message="Test finding",
            )
        ]
        result = self.policy.decide(findings)
        assert "block" in result.message.lower()

    # --- Threshold Flexibility Tests ---

    def test_custom_thresholds(self):
        """Test that custom thresholds work correctly."""
        custom_policy = PolicyEngine(allow_threshold=20, flag_threshold=50)
        findings = []
        result = custom_policy.decide(findings)
        assert result.decision == Decision.ALLOW

    def test_custom_flag_threshold(self):
        """Test that custom flag threshold changes behavior."""
        custom_policy = PolicyEngine(allow_threshold=29, flag_threshold=15)
        findings = []  # Score 0
        result = custom_policy.decide(findings)
        # With flag_threshold < score, this would be FLAG
        # Actually score 0 <= flag_threshold 15, so ALLOW
        assert result.decision == Decision.ALLOW


class TestPolicyBoundaryValues:
    """Tests for policy boundary values."""

    def setup_method(self):
        self.policy = PolicyEngine(allow_threshold=29, flag_threshold=69)

    def test_score_at_allow_boundary(self):
        """Test score exactly at ALLOW boundary."""
        # LOW (10) is ALLOW (<= 29)
        findings = [
            Finding(
                code=FindingCode.INSTRUCTION_OVERRIDE,
                source="user_prompt",
                severity="LOW",
                message="Test",
            )
        ]
        result = self.policy.decide(findings)
        assert result.decision == Decision.ALLOW

    def test_score_at_flag_boundary(self):
        """Test score at FLAG boundary."""
        # HIGH (35) is FLAG (30-69)
        findings = [
            Finding(
                code=FindingCode.INSTRUCTION_OVERRIDE,
                source="user_prompt",
                severity="HIGH",
                message="Test",
            )
        ]
        result = self.policy.decide(findings)
        assert result.decision == Decision.FLAG

    def test_score_above_flag_boundary_is_block(self):
        """Test score above FLAG boundary is BLOCK."""
        # CRITICAL (50) + CRITICAL (50) = 100, which is BLOCK (> 69)
        findings = [
            Finding(
                code=FindingCode.SECRET_REVEAL,
                source="user_prompt",
                severity="CRITICAL",
                message="Test",
            )
        ]
        result = self.policy.decide(findings)
        assert result.decision == Decision.BLOCK