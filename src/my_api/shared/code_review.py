"""Code review findings and compliance scoring.

This module provides data models for code review findings and
compliance score calculation for architecture audits.

**Feature: api-code-review**
**Validates: Requirements All**
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Severity(str, Enum):
    """Finding severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingStatus(str, Enum):
    """Finding status values."""

    PASS = "pass"
    FAIL = "fail"
    PARTIAL = "partial"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True, slots=True)
class ReviewFinding:
    """Represents a single code review finding.

    Attributes:
        id: Unique identifier for the finding.
        requirement_id: Reference to the requirement being checked.
        severity: Severity level of the finding.
        title: Short title describing the finding.
        description: Detailed description of the finding.
        file_path: Path to the file where finding was identified.
        line_number: Line number in the file (if applicable).
        recommendation: Suggested action to address the finding.
        status: Current status of the finding.
    """

    id: str
    requirement_id: str
    severity: Severity
    title: str
    description: str
    recommendation: str
    status: FindingStatus
    file_path: str | None = None
    line_number: int | None = None


@dataclass
class ReviewReport:
    """Complete code review report.

    Attributes:
        project_name: Name of the project being reviewed.
        review_date: Date when the review was conducted.
        findings: List of all review findings.
        summary: Count of findings by severity.
        compliance_score: Overall compliance percentage (0-100).
    """

    project_name: str
    review_date: datetime
    findings: list[ReviewFinding] = field(default_factory=list)

    @property
    def summary(self) -> dict[str, int]:
        """Get count of findings by severity.

        Returns:
            Dictionary mapping severity to count.
        """
        counts: dict[str, int] = {s.value: 0 for s in Severity}
        for finding in self.findings:
            counts[finding.severity.value] += 1
        return counts

    @property
    def compliance_score(self) -> float:
        """Calculate overall compliance score.

        Score is calculated as:
        (Passed Criteria / Total Applicable Criteria) × 100

        Findings with status NOT_APPLICABLE are excluded from calculation.

        Returns:
            Compliance percentage between 0 and 100.
        """
        return calculate_compliance_score(self.findings)

    @property
    def rating(self) -> str:
        """Get compliance rating based on score.

        Returns:
            Rating string (Excellent, Good, Acceptable, Needs Work, Critical).
        """
        score = self.compliance_score
        if score >= 90:
            return "Excellent"
        if score >= 80:
            return "Good"
        if score >= 70:
            return "Acceptable"
        if score >= 60:
            return "Needs Work"
        return "Critical"


def calculate_compliance_score(findings: list[ReviewFinding]) -> float:
    """Calculate compliance score from a list of findings.

    The score is calculated as the percentage of passed criteria
    out of all applicable criteria. Findings with NOT_APPLICABLE
    status are excluded from the calculation.

    **Feature: api-code-review, Property: Score Calculation Consistency**
    **Validates: Design compliance scoring**

    Args:
        findings: List of review findings.

    Returns:
        Compliance score between 0.0 and 100.0.
        Returns 100.0 if there are no applicable findings.
    """
    if not findings:
        return 100.0

    applicable = [
        f for f in findings if f.status != FindingStatus.NOT_APPLICABLE
    ]

    if not applicable:
        return 100.0

    passed = sum(
        1 for f in applicable if f.status == FindingStatus.PASS
    )
    partial = sum(
        1 for f in applicable if f.status == FindingStatus.PARTIAL
    )

    # Partial findings count as 0.5
    score = (passed + (partial * 0.5)) / len(applicable) * 100

    # Ensure score is within bounds
    return max(0.0, min(100.0, score))


def classify_finding_severity(
    finding: ReviewFinding,
) -> Severity:
    """Classify finding severity based on requirement category.

    Security-related findings (requirement IDs starting with "2.")
    are elevated to critical/high severity.

    Args:
        finding: The finding to classify.

    Returns:
        Appropriate severity level.
    """
    req_id = finding.requirement_id

    # OWASP Security requirements (2.x)
    if req_id.startswith("2."):
        if "injection" in finding.title.lower():
            return Severity.CRITICAL
        return Severity.HIGH

    # Architecture requirements (1.x)
    if req_id.startswith("1."):
        return Severity.MEDIUM

    # Code quality requirements (7.x)
    if req_id.startswith("7."):
        return Severity.LOW

    return Severity.INFO
