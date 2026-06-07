"""Read-only local HTTP server for canonical Kiroku memory."""

from __future__ import annotations

import json
import mimetypes
from collections import Counter
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

from .io import load_json, memory_hash
from .query import (
    QUERY_SORT_DIRECTIONS,
    QUERY_SORT_FIELDS,
    VALID_CONFIDENCE_LEVELS,
    VALID_RECORD_STATUSES,
    VALID_RECORD_TYPES,
    VALID_RELATION_TYPES,
    VALID_VERIFICATION_STATUSES,
    RecordQuery,
    build_memory_index,
    compact_record,
    query_records,
)
from .validation import validate_memory


API_VERSION = "1"
DEFAULT_PAGE_LIMIT = 50
MAX_PAGE_LIMIT = 200
LOOPBACK_HOST = "127.0.0.1"

RECORD_QUERY_PARAMETERS = {
    "key",
    "type",
    "status",
    "scope",
    "tag",
    "confidence",
    "verification_status",
    "relation_target",
    "relation_type",
    "search",
    "sort",
    "sort_dir",
    "offset",
    "limit",
}

BROWSER_ROUTES = {"/", "/records", "/sources", "/runs"}
BROWSER_ROUTE_PREFIXES = ("/records/", "/sources/", "/runs/")


class InvalidMemoryError(ValueError):
    """Canonical memory cannot be exposed by the viewer."""

    def __init__(self, details: list[str]):
        super().__init__("canonical memory is invalid")
        self.details = details


@dataclass(frozen=True)
class ViewerSnapshot:
    memory: dict[str, Any]
    digest: str
    warnings: list[str]


@dataclass(frozen=True)
class ViewerResponse:
    status: int
    body: bytes
    content_type: str
    headers: tuple[tuple[str, str], ...] = ()


class ViewerApplication:
    """Transport-neutral request handling for the local viewer."""

    def __init__(
        self,
        memory_dir: Path,
        schema_path: Path,
        assets_dir: Path,
    ) -> None:
        self.memory_dir = memory_dir.resolve()
        self.memory_path = self.memory_dir / "memory.json"
        self.schema_path = schema_path.resolve()
        self.assets_dir = assets_dir.resolve()

    def load_snapshot(self) -> ViewerSnapshot:
        try:
            memory = load_json(self.memory_path)
        except json.JSONDecodeError as exc:
            raise InvalidMemoryError(
                [
                    "memory.json contains invalid JSON at "
                    f"line {exc.lineno}, column {exc.colno}"
                ]
            ) from exc
        except OSError as exc:
            raise InvalidMemoryError(["memory.json could not be read"]) from exc
        except ValueError as exc:
            raise InvalidMemoryError(
                ["memory.json must contain a JSON object"]
            ) from exc

        result = validate_memory(memory, self.schema_path)
        if not result.ok:
            raise InvalidMemoryError(result.errors)
        return ViewerSnapshot(
            memory=memory,
            digest=memory_hash(memory),
            warnings=result.warnings,
        )

    def handle(self, method: str, target: str) -> ViewerResponse:
        if method not in {"GET", "HEAD"}:
            return _error_response(
                HTTPStatus.METHOD_NOT_ALLOWED,
                "read_only",
                "the local viewer is read-only",
                headers=(("Allow", "GET, HEAD"),),
            )

        parsed = urlsplit(target)
        try:
            path = unquote(parsed.path, errors="strict")
        except UnicodeDecodeError:
            return _error_response(
                HTTPStatus.BAD_REQUEST,
                "invalid_query",
                "request path is not valid UTF-8",
            )

        try:
            if path == "/api/v1" or path.startswith("/api/v1/"):
                return self._handle_api(path, parsed.query)
            if path == "/assets" or path.startswith("/assets/"):
                return self._handle_asset(path)
            if path in BROWSER_ROUTES or path.startswith(BROWSER_ROUTE_PREFIXES):
                return self._asset_response("index.html")
            return _error_response(
                HTTPStatus.NOT_FOUND,
                "not_found",
                "requested resource does not exist",
            )
        except Exception:
            return _error_response(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "viewer_error",
                "unexpected local viewer failure",
            )

    def _handle_api(self, path: str, raw_query: str) -> ViewerResponse:
        try:
            snapshot = self.load_snapshot()
        except InvalidMemoryError as exc:
            return _error_response(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                "invalid_memory",
                "canonical memory failed validation",
                exc.details,
            )

        try:
            params = parse_qs(
                raw_query,
                keep_blank_values=True,
                strict_parsing=True,
                max_num_fields=32,
            )
        except ValueError as exc:
            return _error_response(
                HTTPStatus.BAD_REQUEST,
                "invalid_query",
                f"malformed query string: {exc}",
            )

        route = path.rstrip("/") or "/"
        try:
            if route == "/api/v1/meta":
                self._reject_query_parameters(params, set())
                return _data_response(snapshot, self._meta(snapshot))
            if route == "/api/v1/records":
                return self._records_response(snapshot, params)
            if route.startswith("/api/v1/records/"):
                self._reject_query_parameters(params, set())
                return self._record_response(
                    snapshot,
                    route.removeprefix("/api/v1/records/"),
                )
            if route == "/api/v1/sources":
                return self._sources_response(snapshot, params)
            if route.startswith("/api/v1/sources/"):
                self._reject_query_parameters(params, set())
                return self._source_response(
                    snapshot,
                    route.removeprefix("/api/v1/sources/"),
                )
            if route == "/api/v1/runs":
                return self._runs_response(snapshot, params)
            if route.startswith("/api/v1/runs/"):
                self._reject_query_parameters(params, set())
                return self._run_response(
                    snapshot,
                    route.removeprefix("/api/v1/runs/"),
                )
        except ValueError as exc:
            return _error_response(
                HTTPStatus.BAD_REQUEST,
                "invalid_query",
                str(exc),
            )

        return _error_response(
            HTTPStatus.NOT_FOUND,
            "not_found",
            "requested API resource does not exist",
        )

    def _records_response(
        self,
        snapshot: ViewerSnapshot,
        params: dict[str, list[str]],
    ) -> ViewerResponse:
        self._reject_query_parameters(params, RECORD_QUERY_PARAMETERS)
        values = self._single_values(params)
        offset, limit = self._pagination(values)
        query = RecordQuery(
            key=values.get("key"),
            record_type=values.get("type"),
            status=values.get("status"),
            scope=values.get("scope"),
            tag=values.get("tag"),
            confidence=values.get("confidence"),
            verification_status=values.get("verification_status"),
            relation_target=values.get("relation_target"),
            relation_type=values.get("relation_type"),
            search=values.get("search"),
            sort=values.get("sort", "title"),
            sort_direction=values.get("sort_dir", "asc"),
        )
        records = query_records(snapshot.memory, query)
        page = records[offset : offset + limit]
        return _data_response(
            snapshot,
            [compact_record(record) for record in page],
            page={
                "offset": offset,
                "limit": limit,
                "returned": len(page),
                "total": len(records),
            },
        )

    def _record_response(
        self,
        snapshot: ViewerSnapshot,
        record_id: str,
    ) -> ViewerResponse:
        if not record_id or "/" in record_id:
            return _not_found("record")
        index = build_memory_index(snapshot.memory)
        record = index.records_by_id.get(record_id)
        if record is None:
            return _not_found("record")
        source_ids = {
            evidence["source_id"] for evidence in record["evidence"]
        }
        return _data_response(
            snapshot,
            {
                "record": record,
                "incoming_relations": index.incoming_relations.get(record_id, []),
                "evidence_sources": [
                    source
                    for source in snapshot.memory["sources"]
                    if source["id"] in source_ids
                ],
            },
        )

    def _sources_response(
        self,
        snapshot: ViewerSnapshot,
        params: dict[str, list[str]],
    ) -> ViewerResponse:
        values = self._collection_values(params)
        offset, limit = self._pagination(values)
        sources = sorted(
            snapshot.memory["sources"],
            key=lambda source: (source["title"].casefold(), source["id"]),
        )
        page = sources[offset : offset + limit]
        return _data_response(
            snapshot,
            page,
            page={
                "offset": offset,
                "limit": limit,
                "returned": len(page),
                "total": len(sources),
            },
        )

    def _source_response(
        self,
        snapshot: ViewerSnapshot,
        source_id: str,
    ) -> ViewerResponse:
        if not source_id or "/" in source_id:
            return _not_found("source")
        index = build_memory_index(snapshot.memory)
        source = index.sources_by_id.get(source_id)
        if source is None:
            return _not_found("source")
        return _data_response(
            snapshot,
            {
                "source": source,
                "record_ids": index.record_ids_by_source.get(source_id, []),
            },
        )

    def _runs_response(
        self,
        snapshot: ViewerSnapshot,
        params: dict[str, list[str]],
    ) -> ViewerResponse:
        values = self._collection_values(params)
        offset, limit = self._pagination(values)
        runs = sorted(
            snapshot.memory["runs"],
            key=lambda run: (run["started_at"], run["id"]),
            reverse=True,
        )
        page = runs[offset : offset + limit]
        return _data_response(
            snapshot,
            page,
            page={
                "offset": offset,
                "limit": limit,
                "returned": len(page),
                "total": len(runs),
            },
        )

    def _run_response(
        self,
        snapshot: ViewerSnapshot,
        run_id: str,
    ) -> ViewerResponse:
        if not run_id or "/" in run_id:
            return _not_found("run")
        index = build_memory_index(snapshot.memory)
        run = index.runs_by_id.get(run_id)
        if run is None:
            return _not_found("run")
        return _data_response(
            snapshot,
            {
                "run": run,
                "record_ids": index.record_ids_by_run.get(run_id, []),
            },
        )

    def _meta(self, snapshot: ViewerSnapshot) -> dict[str, Any]:
        memory = snapshot.memory
        return {
            "project": memory["project"],
            "memory_id": memory["memory_id"],
            "counts": {
                "records": len(memory["records"]),
                "sources": len(memory["sources"]),
                "runs": len(memory["runs"]),
                "by_type": _count(memory["records"], "type"),
                "by_status": _count(memory["records"], "status"),
                "by_verification_status": _count(
                    memory["records"],
                    "verification_status",
                ),
            },
            "supported_filters": {
                "types": VALID_RECORD_TYPES,
                "statuses": VALID_RECORD_STATUSES,
                "confidence": VALID_CONFIDENCE_LEVELS,
                "verification_statuses": VALID_VERIFICATION_STATUSES,
                "relation_types": VALID_RELATION_TYPES,
                "sort_fields": QUERY_SORT_FIELDS,
                "sort_directions": QUERY_SORT_DIRECTIONS,
            },
            "validation_warnings": snapshot.warnings,
            "page_limits": {
                "default": DEFAULT_PAGE_LIMIT,
                "maximum": MAX_PAGE_LIMIT,
            },
        }

    def _collection_values(
        self,
        params: dict[str, list[str]],
    ) -> dict[str, str]:
        self._reject_query_parameters(params, {"offset", "limit"})
        return self._single_values(params)

    @staticmethod
    def _reject_query_parameters(
        params: dict[str, list[str]],
        allowed: set[str],
    ) -> None:
        unknown = sorted(set(params) - allowed)
        if unknown:
            raise ValueError(
                f"unknown query parameter(s): {', '.join(unknown)}"
            )

    @staticmethod
    def _single_values(
        params: dict[str, list[str]],
    ) -> dict[str, str]:
        duplicate = sorted(key for key, values in params.items() if len(values) != 1)
        if duplicate:
            raise ValueError(
                f"query parameter(s) must appear once: {', '.join(duplicate)}"
            )
        return {key: values[0] for key, values in params.items()}

    @staticmethod
    def _pagination(values: dict[str, str]) -> tuple[int, int]:
        offset = _integer_parameter(values.get("offset", "0"), "offset")
        limit = _integer_parameter(
            values.get("limit", str(DEFAULT_PAGE_LIMIT)),
            "limit",
        )
        if offset < 0:
            raise ValueError("offset must be >= 0")
        if limit < 1 or limit > MAX_PAGE_LIMIT:
            raise ValueError(f"limit must be between 1 and {MAX_PAGE_LIMIT}")
        return offset, limit

    def _handle_asset(self, path: str) -> ViewerResponse:
        if path in {"/assets", "/assets/"}:
            return _not_found("asset")
        return self._asset_response(path.removeprefix("/assets/"))

    def _asset_response(self, relative_path: str) -> ViewerResponse:
        candidate = (self.assets_dir / relative_path).resolve()
        try:
            candidate.relative_to(self.assets_dir)
        except ValueError:
            return _not_found("asset")
        if not candidate.is_file():
            return _not_found("asset")
        try:
            content = candidate.read_bytes()
        except OSError:
            return _error_response(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "viewer_error",
                "viewer asset could not be read",
            )
        content_type = mimetypes.guess_type(candidate.name)[0]
        return ViewerResponse(
            status=HTTPStatus.OK,
            body=content,
            content_type=content_type or "application/octet-stream",
        )


class ViewerHTTPServer(ThreadingHTTPServer):
    """Threaded loopback server carrying one viewer application."""

    def __init__(
        self,
        server_address: tuple[str, int],
        application: ViewerApplication,
    ) -> None:
        self.application = application
        super().__init__(server_address, ViewerRequestHandler)


class ViewerRequestHandler(BaseHTTPRequestHandler):
    """HTTP adapter for ViewerApplication."""

    server: ViewerHTTPServer
    server_version = "KirokuViewer/1"
    sys_version = ""

    def __getattr__(self, name: str):
        if name.startswith("do_"):
            return lambda: self._dispatch(name.removeprefix("do_"))
        raise AttributeError(name)

    def version_string(self) -> str:
        return self.server_version

    def do_GET(self) -> None:
        self._dispatch("GET")

    def do_HEAD(self) -> None:
        self._dispatch("HEAD")

    def do_POST(self) -> None:
        self._dispatch("POST")

    def do_PUT(self) -> None:
        self._dispatch("PUT")

    def do_PATCH(self) -> None:
        self._dispatch("PATCH")

    def do_DELETE(self) -> None:
        self._dispatch("DELETE")

    def do_OPTIONS(self) -> None:
        self._dispatch("OPTIONS")

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _dispatch(self, method: str) -> None:
        response = self.server.application.handle(method, self.path)
        self.send_response(response.status)
        self.send_header("Content-Type", response.content_type)
        self.send_header("Content-Length", str(len(response.body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        if response.content_type.startswith("text/html"):
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; style-src 'self'; "
                "object-src 'none'; base-uri 'none'; "
                "frame-ancestors 'none'",
            )
        for name, value in response.headers:
            self.send_header(name, value)
        self.end_headers()
        if method != "HEAD":
            self.wfile.write(response.body)


def create_viewer_server(
    memory_dir: Path,
    schema_path: Path,
    assets_dir: Path,
    *,
    port: int = 8765,
) -> ViewerHTTPServer:
    if port < 0 or port > 65535:
        raise ValueError("port must be between 0 and 65535")
    application = ViewerApplication(memory_dir, schema_path, assets_dir)
    application.load_snapshot()
    return ViewerHTTPServer((LOOPBACK_HOST, port), application)


def _data_response(
    snapshot: ViewerSnapshot,
    data: Any,
    *,
    page: dict[str, int] | None = None,
) -> ViewerResponse:
    payload = {
        "api_version": API_VERSION,
        "schema_version": snapshot.memory["schema_version"],
        "memory_hash": snapshot.digest,
        "data": data,
    }
    if page is not None:
        payload["page"] = page
    return _json_response(HTTPStatus.OK, payload)


def _error_response(
    status: int,
    code: str,
    message: str,
    details: list[str] | None = None,
    *,
    headers: tuple[tuple[str, str], ...] = (),
) -> ViewerResponse:
    return _json_response(
        status,
        {
            "error": {
                "code": code,
                "message": message,
                "details": details or [],
            }
        },
        headers=headers,
    )


def _json_response(
    status: int,
    payload: dict[str, Any],
    *,
    headers: tuple[tuple[str, str], ...] = (),
) -> ViewerResponse:
    body = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode(
        "utf-8"
    )
    return ViewerResponse(
        status=status,
        body=body,
        content_type="application/json; charset=utf-8",
        headers=headers,
    )


def _not_found(resource: str) -> ViewerResponse:
    return _error_response(
        HTTPStatus.NOT_FOUND,
        "not_found",
        f"requested {resource} does not exist",
    )


def _integer_parameter(value: str, name: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def _count(items: list[dict[str, Any]], field: str) -> dict[str, int]:
    return dict(sorted(Counter(item[field] for item in items).items()))
