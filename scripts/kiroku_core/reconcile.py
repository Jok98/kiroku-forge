"""Pure deterministic reconciliation into KirokuForge ChangeSets."""

from __future__ import annotations

import copy
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .capture import capture_bundle_hash
from .change_set import validate_change_set
from .findings import Finding, ValidationResult
from .hashing import sha256_hash
from .schema import (
    validate_candidate_bundle_schema,
    validate_capture_bundle_schema,
)


ARTIFACT_HASH_MISMATCH = "ARTIFACT_HASH_MISMATCH"
RECONCILIATION_NEEDS_REVIEW = "RECONCILIATION_NEEDS_REVIEW"


@dataclass(frozen=True)
class ReconcileResult:
    """Result of a pure reconciliation attempt."""

    change_set: dict[str, Any] | None = None
    findings: tuple[Finding, ...] = field(default_factory=tuple)
    source_resolutions: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    candidate_resolutions: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    reconciliation_findings: tuple[dict[str, Any], ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "findings",
            ValidationResult.from_findings(self.findings).findings,
        )

    @property
    def ok(self) -> bool:
        """Return whether reconciliation completed without blocking errors."""

        return not self.errors

    @property
    def no_change(self) -> bool:
        """Return whether reconciliation produced no compilable ChangeSet."""

        return self.ok and self.change_set is None

    @property
    def errors(self) -> tuple[Finding, ...]:
        """Return blocking findings."""

        return tuple(
            finding
            for finding in self.findings
            if finding.severity == "error"
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible diagnostic representation."""

        return {
            "ok": self.ok,
            "no_change": self.no_change,
            "findings": [finding.to_dict() for finding in self.findings],
        }


def candidate_bundle_hash(candidate_bundle: dict[str, Any]) -> str:
    """Hash a CandidateBundle, excluding its stored artifact hash."""

    return sha256_hash(
        {
            key: value
            for key, value in candidate_bundle.items()
            if key != "artifact_hash"
        }
    )


def change_set_hash(change_set: dict[str, Any]) -> str:
    """Hash a ChangeSet, excluding its stored artifact hash."""

    return sha256_hash(
        {
            key: value
            for key, value in change_set.items()
            if key != "artifact_hash"
        }
    )


def _finding(
    code: str,
    path: str,
    message: str,
    *entity_ids: str,
) -> Finding:
    return Finding(
        code=code,
        severity="error",
        path=path,
        message=f"{path}: {message}",
        entity_ids=tuple(entity_ids),
    )


def _validate_inputs(
    capture_bundle: Any,
    candidate_bundle: Any,
) -> ValidationResult:
    capture_result = validate_capture_bundle_schema(capture_bundle)
    candidate_result = validate_candidate_bundle_schema(candidate_bundle)
    findings = [*capture_result.findings, *candidate_result.findings]
    if not capture_result.ok or not candidate_result.ok:
        return ValidationResult.from_findings(findings)

    if capture_bundle["artifact_hash"] != capture_bundle_hash(capture_bundle):
        findings.append(
            _finding(
                ARTIFACT_HASH_MISMATCH,
                "$.capture_bundle.artifact_hash",
                "stored hash differs from canonical CaptureBundle content",
                capture_bundle["capture_bundle_id"],
            )
        )
    if candidate_bundle["artifact_hash"] != candidate_bundle_hash(candidate_bundle):
        findings.append(
            _finding(
                ARTIFACT_HASH_MISMATCH,
                "$.candidate_bundle.artifact_hash",
                "stored hash differs from canonical CandidateBundle content",
                candidate_bundle["candidate_bundle_id"],
            )
        )

    expected_capture = candidate_bundle["capture_bundle"]
    if (
        expected_capture["artifact_id"] != capture_bundle["capture_bundle_id"]
        or expected_capture["artifact_hash"] != capture_bundle["artifact_hash"]
    ):
        findings.append(
            _finding(
                ARTIFACT_HASH_MISMATCH,
                "$.candidate_bundle.capture_bundle",
                "CandidateBundle does not reference the supplied CaptureBundle",
                candidate_bundle["candidate_bundle_id"],
                capture_bundle["capture_bundle_id"],
            )
        )
    return ValidationResult.from_findings(findings)


def _suffix(value: str, prefix: str) -> str:
    return value[len(prefix) :] if value.startswith(prefix) else value


def _entity_suffix(value: str) -> str:
    return value.split("_", 1)[1] if "_" in value else value


def _source_id(
    captured_source_id: str,
    source_id_map: Mapping[str, str],
) -> str:
    return source_id_map.get(
        captured_source_id,
        f"src_{_suffix(captured_source_id, 'csrc_')}",
    )


def _record_id(
    candidate_id: str,
    record_id_map: Mapping[str, str],
) -> str:
    return record_id_map.get(
        candidate_id,
        f"rec_{_suffix(candidate_id, 'can_')}",
    )


def _op_id(kind: str, entity_id: str) -> str:
    return f"op_{kind}_{_entity_suffix(entity_id)}"


def _finding_id(candidate_id: str) -> str:
    return f"fnd_{_suffix(candidate_id, 'can_')}_needs_review"


def _current_records(memory: dict[str, Any] | None) -> list[dict[str, Any]]:
    if memory is None:
        return []
    historical = {
        relation["target_id"]
        for record in memory["records"]
        for relation in record["relations"]
        if relation["type"] == "supersedes"
    }
    return [record for record in memory["records"] if record["id"] not in historical]


def _matching_record(
    candidate: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    for record in records:
        if (
            record["key"] == candidate["proposed_key"]
            and record["kind"] == candidate["kind"]
            and record["state"] == candidate["proposed_state"]
            and record["content"] == candidate["content"]
        ):
            return record
    return None


def _same_key_records(
    candidate: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    return [
        record
        for record in records
        if record["key"] == candidate["proposed_key"]
    ]


def _source_draft(
    captured_source: Mapping[str, Any],
    canonical_source_id: str,
) -> dict[str, Any]:
    draft: dict[str, Any] = {
        "id": canonical_source_id,
        "kind": captured_source["kind"],
        "title": captured_source["title"],
        "uri": captured_source["uri"],
        "integrity": "verified",
        "content_hash": captured_source["content_hash"],
        "captured_at": captured_source["captured_at"],
    }
    for key in ("revision", "media_type", "metadata"):
        if key in captured_source:
            draft[key] = copy.deepcopy(captured_source[key])
    return draft


def _canonical_evidence(
    evidence: Mapping[str, Any],
    source_id_by_captured_id: Mapping[str, str],
) -> dict[str, Any]:
    result = {
        "source_id": source_id_by_captured_id[evidence["captured_source_id"]],
        "relation": evidence["relation"],
        "method": evidence["method"],
        "locator": copy.deepcopy(evidence["locator"]),
        "observed_at": evidence["observed_at"],
    }
    for key in ("excerpt", "note"):
        if key in evidence:
            result[key] = copy.deepcopy(evidence[key])
    return result


def _record_draft(
    candidate: Mapping[str, Any],
    record_id: str,
    source_id_by_captured_id: Mapping[str, str],
) -> dict[str, Any]:
    return {
        "id": record_id,
        "key": candidate["proposed_key"],
        "kind": candidate["kind"],
        "state": candidate["proposed_state"],
        "title": candidate["title"],
        "summary": candidate["summary"],
        "scope": copy.deepcopy(candidate["scope"]),
        "tags": copy.deepcopy(candidate["tags"]),
        "verification": {"status": "unverified"},
        "evidence": [
            _canonical_evidence(evidence, source_id_by_captured_id)
            for evidence in candidate["evidence"]
        ],
        "relations": [],
        "content": copy.deepcopy(candidate["content"]),
    }


def _input_bundles(
    capture_bundle: Mapping[str, Any],
    candidate_bundle: Mapping[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "artifact_type": "capture_bundle",
            "artifact_id": capture_bundle["capture_bundle_id"],
            "artifact_hash": capture_bundle["artifact_hash"],
        },
        {
            "artifact_type": "candidate_bundle",
            "artifact_id": candidate_bundle["candidate_bundle_id"],
            "artifact_hash": candidate_bundle["artifact_hash"],
        },
    ]


def _reconciliation_finding(
    candidate: Mapping[str, Any],
    *,
    record_ids: Sequence[str] = (),
    message: str,
    recommended_action: str,
) -> dict[str, Any]:
    return {
        "id": _finding_id(candidate["id"]),
        "severity": "warning",
        "code": RECONCILIATION_NEEDS_REVIEW,
        "message": message,
        "candidate_ids": [candidate["id"]],
        "record_ids": list(record_ids),
        "recommended_action": recommended_action,
    }


def _needs_review_plan(
    candidate: Mapping[str, Any],
    finding: dict[str, Any],
    record_ids: Sequence[str] = (),
) -> dict[str, Any]:
    return {
        "candidate": candidate,
        "resolution": "needs_review",
        "rationale": "Automatic reconciliation would be unsafe.",
        "record_ids": list(record_ids),
        "operation_id": None,
        "finding_id": finding["id"],
    }


def _candidate_resolution(plan: Mapping[str, Any]) -> dict[str, Any]:
    operation_id = plan.get("operation_id")
    finding_id = plan.get("finding_id")
    return {
        "candidate_id": plan["candidate"]["id"],
        "resolution": plan["resolution"],
        "rationale": plan["rationale"],
        "record_ids": list(plan["record_ids"]),
        "operation_ids": [operation_id] if operation_id is not None else [],
        "finding_ids": [finding_id] if finding_id is not None else [],
    }


def reconcile_candidates(
    *,
    change_set_id: str,
    generated_at: str,
    capture_bundle: dict[str, Any],
    candidate_bundle: dict[str, Any],
    memory: dict[str, Any] | None,
    actor: Mapping[str, Any] | None = None,
    memory_id: str | None = None,
    project: Mapping[str, Any] | None = None,
    source_id_map: Mapping[str, str] | None = None,
    record_id_map: Mapping[str, str] | None = None,
    summary: str = "Reconcile candidates into canonical memory.",
) -> ReconcileResult:
    """Reconcile candidates into a validated ChangeSet, or report no change."""

    input_result = _validate_inputs(capture_bundle, candidate_bundle)
    if not input_result.ok:
        return ReconcileResult(findings=input_result.findings)

    source_ids = source_id_map or {}
    record_ids = record_id_map or {}
    captured_sources = {source["id"]: source for source in capture_bundle["sources"]}
    current_records = _current_records(memory)
    duplicate_candidate_keys = {
        key
        for key, count in Counter(
            candidate["proposed_key"]
            for candidate in candidate_bundle["candidates"]
        ).items()
        if count > 1
    }

    plans: list[dict[str, Any]] = []
    needed_captured_source_ids: set[str] = set()
    reconciliation_findings: list[dict[str, Any]] = []

    for candidate in candidate_bundle["candidates"]:
        matching = _matching_record(candidate, current_records)
        if matching is not None:
            plans.append(
                {
                    "candidate": candidate,
                    "resolution": "ignore",
                    "rationale": "Candidate is already represented by a current canonical record.",
                    "record_ids": [matching["id"]],
                    "operation_id": None,
                    "finding_id": None,
                }
            )
            continue

        same_key = _same_key_records(candidate, current_records)
        if same_key or candidate["proposed_key"] in duplicate_candidate_keys:
            affected_record_ids = [record["id"] for record in same_key]
            finding = _reconciliation_finding(
                candidate,
                record_ids=affected_record_ids,
                message="Candidate requires semantic review before canonical mutation.",
                recommended_action="Review whether to merge, supersede, ignore, or create with a different key.",
            )
            reconciliation_findings.append(finding)
            plans.append(_needs_review_plan(candidate, finding, affected_record_ids))
            continue

        missing_sources = [
            evidence["captured_source_id"]
            for evidence in candidate["evidence"]
            if evidence["captured_source_id"] not in captured_sources
        ]
        unavailable_sources = [
            evidence["captured_source_id"]
            for evidence in candidate["evidence"]
            if evidence["captured_source_id"] in captured_sources
            and captured_sources[evidence["captured_source_id"]]["status"] == "unavailable"
        ]
        if missing_sources or unavailable_sources:
            finding = _reconciliation_finding(
                candidate,
                message="Candidate references captured source material that cannot become canonical evidence.",
                recommended_action="Recapture the source or remove unsupported evidence before reconciliation.",
            )
            reconciliation_findings.append(finding)
            plans.append(_needs_review_plan(candidate, finding))
            continue

        for evidence in candidate["evidence"]:
            needed_captured_source_ids.add(evidence["captured_source_id"])
        plans.append(
            {
                "candidate": candidate,
                "resolution": "create",
                "rationale": "No compatible current canonical record exists.",
                "record_ids": [],
                "operation_id": None,
                "finding_id": None,
            }
        )

    source_resolutions: list[dict[str, Any]] = []
    source_id_by_captured_id: dict[str, str] = {}
    source_operations: list[dict[str, Any]] = []

    for captured_source in capture_bundle["sources"]:
        captured_source_id = captured_source["id"]
        status = captured_source["status"]
        needed = captured_source_id in needed_captured_source_ids
        if status == "unchanged":
            canonical_source_id = captured_source["matched_source_id"]
            source_id_by_captured_id[captured_source_id] = canonical_source_id
            source_resolutions.append(
                {
                    "captured_source_id": captured_source_id,
                    "resolution": "reuse",
                    "canonical_source_id": canonical_source_id,
                }
            )
        elif status in {"new", "changed"} and needed:
            canonical_source_id = _source_id(captured_source_id, source_ids)
            operation_id = _op_id("add_source", canonical_source_id)
            source_id_by_captured_id[captured_source_id] = canonical_source_id
            source_resolutions.append(
                {
                    "captured_source_id": captured_source_id,
                    "resolution": "add",
                    "canonical_source_id": canonical_source_id,
                    "operation_id": operation_id,
                }
            )
            source_operations.append(
                {
                    "operation_id": operation_id,
                    "operation_type": "add_source",
                    "source": _source_draft(captured_source, canonical_source_id),
                }
            )
        else:
            reason = (
                "Source material was unavailable."
                if status == "unavailable"
                else "No canonical operation references this captured source."
            )
            source_resolutions.append(
                {
                    "captured_source_id": captured_source_id,
                    "resolution": "ignore",
                    "reason": reason,
                }
            )

    record_operations: list[dict[str, Any]] = []
    for plan in plans:
        if plan["resolution"] != "create":
            continue
        candidate = plan["candidate"]
        record_id = _record_id(candidate["id"], record_ids)
        operation_id = _op_id("create_record", record_id)
        plan["record_ids"] = [record_id]
        plan["operation_id"] = operation_id
        record_operations.append(
            {
                "operation_id": operation_id,
                "operation_type": "create_record",
                "record": _record_draft(candidate, record_id, source_id_by_captured_id),
            }
        )

    candidate_resolutions = [_candidate_resolution(plan) for plan in plans]
    operations: list[dict[str, Any]] = []
    if memory is None and (source_operations or record_operations):
        if memory_id is None or project is None:
            raise ValueError("initial reconciliation requires memory_id and project")
        operations.append(
            {
                "operation_id": "op_initialize",
                "operation_type": "initialize_memory",
                "memory_id": memory_id,
                "project": copy.deepcopy(dict(project)),
            }
        )
    operations.extend(source_operations)
    operations.extend(record_operations)

    if not operations:
        return ReconcileResult(
            change_set=None,
            source_resolutions=tuple(source_resolutions),
            candidate_resolutions=tuple(candidate_resolutions),
            reconciliation_findings=tuple(reconciliation_findings),
        )

    active_actor = copy.deepcopy(dict(actor or candidate_bundle["actor"]))
    change_set = {
        "artifact_type": "change_set",
        "schema_version": "1.0.0",
        "change_set_id": change_set_id,
        "artifact_hash": "sha256:" + "0" * 64,
        "generated_at": generated_at,
        "actor": active_actor,
        "target_memory_id": None if memory is None else memory["memory_id"],
        "base_revision": None if memory is None else memory["revision"],
        "base_state_hash": None if memory is None else memory["state_hash"],
        "input_bundles": _input_bundles(capture_bundle, candidate_bundle),
        "summary": summary,
        "source_resolutions": source_resolutions,
        "candidate_resolutions": candidate_resolutions,
        "operations": operations,
        "findings": reconciliation_findings,
    }
    change_set["artifact_hash"] = change_set_hash(change_set)

    validation = validate_change_set(change_set, memory)
    if not validation.ok:
        return ReconcileResult(
            findings=validation.findings,
            source_resolutions=tuple(source_resolutions),
            candidate_resolutions=tuple(candidate_resolutions),
            reconciliation_findings=tuple(reconciliation_findings),
        )
    return ReconcileResult(
        change_set=change_set,
        source_resolutions=tuple(source_resolutions),
        candidate_resolutions=tuple(candidate_resolutions),
        reconciliation_findings=tuple(reconciliation_findings),
    )
