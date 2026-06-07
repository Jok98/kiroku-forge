# Local Viewer Contract

This document defines the boundary between canonical Kiroku memory and the
local human-facing viewer. It is the implementation contract for P2.

## Ownership And Location

- The viewer implementation belongs to the KirokuForge skill.
- Project memory remains in the project-specific `kiroku/` directory.
- The viewer receives that directory explicitly and reads
  `<selected-dir>/memory.json`.
- The viewer never requires a copy of its assets inside the selected memory.
- The selected memory may be outside the skill and outside a source project.

The planned entry point is:

```bash
python <skill-dir>/scripts/kiroku.py serve --dir /path/to/project/kiroku
```

## Canonical Boundary

`memory.json` is the only data source for the viewer. The viewer must not read
`agent-bootstrap.json` or `views/*.md` as canonical input.

Before returning memory data, the server validates it against
`schemas/memory-v2.schema.json` and the semantic validator. Invalid memory must
produce diagnostics and must not be partially rendered as valid knowledge.

P2 is read-only:

- only HTTP `GET` and `HEAD` are allowed;
- no endpoint writes, repairs, normalizes, hashes, or rebuilds memory;
- browser interaction must leave every file in the selected directory
  unchanged;
- future mutations must reuse the controlled CLI mutation pipeline rather than
  implementing a second writer.

## Network Boundary

- Bind to `127.0.0.1` by default.
- Do not expose a remote interface without an explicit future option.
- Treat all strings from memory as untrusted display content and escape them.
- Do not make local source paths or arbitrary URIs executable or clickable by
  default.
- Do not fetch source URIs or external assets.

## Shared Query Semantics

The CLI and viewer use `kiroku_core.query.RecordQuery` and `query_records`.
Filters compose with logical AND:

- `key`
- `type`
- `status`
- `scope`
- `tag`
- `confidence`
- `verification_status`
- `relation_target`
- `relation_type`
- `search`

`relation_target` and `relation_type` must match the same outgoing relation.
`search` is case-insensitive and covers key, title, summary, scope, tags, and
the type-specific payload. Evidence text is excluded from generic search.

Supported sort fields are `title`, `type`, `status`, `created_at`, and
`updated_at`, in ascending or descending direction.

The derived `MemoryIndex` provides:

- record lookup by ID and key;
- source and run lookup by ID;
- incoming relations for a record;
- records backed by a source;
- records whose current version was generated or changed by a run.

Indexes are derived in memory and are never persisted beside `memory.json`.

## HTTP API V1

All JSON endpoints use the `/api/v1` prefix. P2.1 may add fields, but removing
or changing the meaning of a field requires a new API version.

Planned resources:

| Method and path | Result |
| --- | --- |
| `GET /api/v1/meta` | API version, schema version, memory hash, project summary, counts, supported filter values |
| `GET /api/v1/records` | Filtered, sorted record collection |
| `GET /api/v1/records/{record_id}` | Full record, incoming relations, resolved evidence sources |
| `GET /api/v1/sources` | Source collection |
| `GET /api/v1/sources/{source_id}` | Full source and IDs of records using it |
| `GET /api/v1/runs` | Run collection |
| `GET /api/v1/runs/{run_id}` | Full run and IDs of records whose current version was generated or changed by it |

`GET /api/v1/records` accepts the shared filter names as query parameters,
using `type` for `RecordQuery.record_type`, plus:

- `sort`, default `title`;
- `sort_dir`, default `asc`;
- `offset`, default `0`;
- `limit`, default `50`, maximum `200`.

Filtering and sorting happen before pagination. A collection response has this
shape:

```json
{
  "api_version": "1",
  "schema_version": "2.0.0",
  "memory_hash": "sha256:...",
  "data": [],
  "page": {
    "offset": 0,
    "limit": 50,
    "returned": 0,
    "total": 0
  }
}
```

Single-resource responses omit `page` and place the resource in `data`.
Record collections use compact records; record details return the full record.
Source and run collections accept only `offset` and `limit`.

## Errors

Errors use one stable envelope:

```json
{
  "error": {
    "code": "invalid_query",
    "message": "unknown record type: example",
    "details": []
  }
}
```

Required error codes:

| HTTP status | Code | Meaning |
| --- | --- | --- |
| `400` | `invalid_query` | Unsupported or malformed query parameter |
| `404` | `not_found` | Requested record, source, or run does not exist |
| `405` | `read_only` | A mutating HTTP method was attempted |
| `422` | `invalid_memory` | Canonical memory failed structural or semantic validation |
| `500` | `viewer_error` | Unexpected local viewer failure |

Validation diagnostics are returned in `error.details`. They must not include
file contents or unrelated local paths.

## Browser Routes

Human-facing routes are stable deep links:

- `/` for the project dashboard;
- `/records` for the record explorer;
- `/records/{record_id}` for record detail;
- `/sources` and `/sources/{source_id}`;
- `/runs` and `/runs/{run_id}`.

Explorer filters remain in the URL query string so a view can be bookmarked.
The browser routes are client-side navigation and do not change API semantics.

## P2.1 Implementation

P2.1 provides:

- `serve --dir <memory-dir> [--port <port>]`;
- loopback-only binding on `127.0.0.1`;
- a threaded stdlib HTTP server;
- validation at startup and before each API response;
- the API V1 resources defined above;
- bounded pagination and strict query parameter validation;
- derived reverse relation, source, and run lookups;
- a confined skill-owned asset directory;
- explicit `405 read_only` responses for mutating methods;
- `Cache-Control: no-store`, content type protection, and a restrictive
  content security policy for HTML.

Port `0` asks the operating system to select an available local port. The
server reloads canonical memory for each API request, so valid external changes
are visible without rebuilding or restarting the viewer.

## P2.2 Implementation

P2.2 provides a dependency-free browser interface over API V1:

- a project dashboard with record, source, and run distributions;
- a record explorer exposing every shared query filter and supported sort;
- bookmarkable filter, sort, and pagination state in the URL;
- record details with payload, evidence locators, provenance, and relations;
- source and run indexes with stable detail deep links;
- safe DOM construction without rendering memory strings as HTML;
- skill-owned static assets compatible with the restrictive CSP;
- browser-level tests for explorer queries and record, source, and run routes.

The interface remains a projection over `memory.json`. It does not add a
browser-side writer or another persistence format.

## P2.0 Acceptance Criteria

- Query behavior is independent of argparse and reusable by the future server.
- Existing CLI query behavior remains compatible.
- Viewer-only filters use the same query implementation as the CLI.
- Reverse relation, source, and run lookups are derived without changing
  canonical memory.
- The read-only, validation, API, error, and deep-link contracts are explicit.
- No HTTP server or browser UI is introduced in P2.0.
