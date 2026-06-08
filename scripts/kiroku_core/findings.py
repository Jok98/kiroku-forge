"""Shared deterministic validation findings."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable


_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")
_SEVERITY_ORDER = {
    "error": 0,
    "warning": 1,
    "info": 2,
}


@dataclass(frozen=True)
class Finding:
    """One machine-readable validation problem."""

    code: str
    severity: str
    path: str
    message: str
    entity_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.severity not in _SEVERITY_ORDER:
            raise ValueError(f"unsupported finding severity: {self.severity!r}")
        if not _CODE_PATTERN.fullmatch(self.code):
            raise ValueError(f"invalid finding code: {self.code!r}")
        if not self.path.startswith("$"):
            raise ValueError("finding path must be a JSONPath rooted at '$'")
        if not self.message:
            raise ValueError("finding message must not be empty")
        if not all(isinstance(entity_id, str) for entity_id in self.entity_ids):
            raise ValueError("finding entity IDs must be strings")
        object.__setattr__(
            self,
            "entity_ids",
            tuple(sorted(set(self.entity_ids))),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""

        return {
            "code": self.code,
            "severity": self.severity,
            "path": self.path,
            "message": self.message,
            "entity_ids": list(self.entity_ids),
        }


def finding_sort_key(finding: Finding) -> tuple[Any, ...]:
    """Return the normative deterministic order for findings."""

    return (
        _SEVERITY_ORDER[finding.severity],
        finding.path,
        finding.code,
        finding.entity_ids,
        finding.message,
    )


@dataclass(frozen=True)
class ValidationResult:
    """An immutable, deterministically ordered validation result."""

    findings: tuple[Finding, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "findings",
            tuple(sorted(self.findings, key=finding_sort_key)),
        )

    @classmethod
    def from_findings(cls, findings: Iterable[Finding]) -> ValidationResult:
        """Build a result from any finding iterable."""

        return cls(tuple(findings))

    @property
    def ok(self) -> bool:
        """Return whether the result contains no blocking errors."""

        return not any(
            finding.severity == "error" for finding in self.findings
        )

    @property
    def errors(self) -> tuple[Finding, ...]:
        """Return blocking findings."""

        return tuple(
            finding
            for finding in self.findings
            if finding.severity == "error"
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""

        return {
            "ok": self.ok,
            "findings": [
                finding.to_dict() for finding in self.findings
            ],
        }
