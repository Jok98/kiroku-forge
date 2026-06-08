"""Pure construction of KirokuForge CaptureBundle artifacts."""

from __future__ import annotations

import copy
import hashlib
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .findings import Finding, ValidationResult
from .hashing import sha256_hash
from .schema import validate_capture_bundle_schema


@dataclass(frozen=True)
class CaptureSourceInput:
    """One selected source for CAPTURE."""

    id: str
    kind: str
    title: str
    uri: str
    revision: str | None = None
    media_type: str | None = None
    metadata: Mapping[str, Any] | None = None
    content: str | bytes | None = None
    reference_uri: str | None = None
    content_hash: str | None = None
    unavailable_reason: str | None = None


@dataclass(frozen=True)
class CaptureResult:
    """Result of a CAPTURE attempt."""

    bundle: dict[str, Any] | None = None
    findings: tuple[Finding, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "findings",
            ValidationResult.from_findings(self.findings).findings,
        )

    @property
    def ok(self) -> bool:
        """Return whether CAPTURE produced a valid CaptureBundle."""

        return self.bundle is not None and not self.errors

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
            "findings": [finding.to_dict() for finding in self.findings],
        }


def source_content_hash(content: str | bytes) -> str:
    """Hash captured raw source content as UTF-8 or supplied bytes."""

    payload = content.encode("utf-8") if isinstance(content, str) else content
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def capture_bundle_hash(capture_bundle: dict[str, Any]) -> str:
    """Hash a CaptureBundle, excluding its stored artifact hash."""

    return sha256_hash(
        {
            key: value
            for key, value in capture_bundle.items()
            if key != "artifact_hash"
        }
    )


def _finding_result(result: ValidationResult) -> CaptureResult:
    return CaptureResult(bundle=None, findings=result.findings)


def _as_input(source: CaptureSourceInput | Mapping[str, Any]) -> CaptureSourceInput:
    if isinstance(source, CaptureSourceInput):
        return source
    return CaptureSourceInput(**dict(source))


def _same_revision(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return left.get("revision") == right.get("revision")


def _find_unchanged_source(
    source: Mapping[str, Any],
    existing_sources: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    for existing in sorted(existing_sources, key=lambda item: item["id"]):
        if (
            source["uri"] == existing["uri"]
            and _same_revision(source, existing)
            and source.get("content_hash") == existing.get("content_hash")
        ):
            return existing
    return None


def _find_previous_source(
    source: Mapping[str, Any],
    existing_sources: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    candidates = [
        existing
        for existing in existing_sources
        if existing["uri"] == source["uri"]
    ]
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda item: (item.get("captured_at", ""), item["id"]),
    )[-1]


def _material_and_hash(source: CaptureSourceInput) -> tuple[dict[str, Any], str | None]:
    if source.unavailable_reason is not None:
        return {"mode": "unavailable", "reason": source.unavailable_reason}, None

    if source.content is not None:
        content = (
            source.content.decode("utf-8")
            if isinstance(source.content, bytes)
            else source.content
        )
        return {"mode": "inline", "content": content}, source_content_hash(source.content)

    if source.reference_uri is not None:
        return {"mode": "reference", "uri": source.reference_uri}, source.content_hash

    return {"mode": "unavailable", "reason": "Source material was not supplied."}, None


def _captured_source(
    source_input: CaptureSourceInput,
    *,
    captured_at: str,
    existing_sources: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    material, content_hash = _material_and_hash(source_input)
    result: dict[str, Any] = {
        "id": source_input.id,
        "kind": source_input.kind,
        "title": source_input.title,
        "uri": source_input.uri,
        "status": "unavailable" if content_hash is None else "new",
        "captured_at": captured_at,
        "material": material,
    }
    if source_input.revision is not None:
        result["revision"] = source_input.revision
    if source_input.media_type is not None:
        result["media_type"] = source_input.media_type
    if source_input.metadata is not None:
        result["metadata"] = copy.deepcopy(dict(source_input.metadata))
    if content_hash is None:
        return result

    result["content_hash"] = content_hash
    unchanged = _find_unchanged_source(result, existing_sources)
    if unchanged is not None:
        result["status"] = "unchanged"
        result["matched_source_id"] = unchanged["id"]
        return result

    previous = _find_previous_source(result, existing_sources)
    if previous is not None:
        result["status"] = "changed"
        result["previous_source_id"] = previous["id"]
    return result


def capture_sources(
    *,
    capture_bundle_id: str,
    generated_at: str,
    actor: Mapping[str, Any],
    selection_scope: Mapping[str, Any],
    sources: Sequence[CaptureSourceInput | Mapping[str, Any]],
    existing_sources: Sequence[Mapping[str, Any]] = (),
) -> CaptureResult:
    """Build one CaptureBundle without mutating inputs or canonical memory."""

    captured_sources = [
        _captured_source(
            _as_input(source),
            captured_at=generated_at,
            existing_sources=existing_sources,
        )
        for source in sources
    ]
    bundle = {
        "artifact_type": "capture_bundle",
        "schema_version": "1.0.0",
        "capture_bundle_id": capture_bundle_id,
        "artifact_hash": "sha256:" + "0" * 64,
        "generated_at": generated_at,
        "actor": copy.deepcopy(dict(actor)),
        "selection_scope": copy.deepcopy(dict(selection_scope)),
        "sources": captured_sources,
    }
    bundle["artifact_hash"] = capture_bundle_hash(bundle)

    validation = validate_capture_bundle_schema(bundle)
    if not validation.ok:
        return _finding_result(validation)
    return CaptureResult(bundle=bundle)
