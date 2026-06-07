# Record Draft Contract

Use `add-record` or `update-record` with a JSON object containing only semantic
record data.

Required fields:

- `key`: stable lowercase identity matching `^[a-z0-9][a-z0-9_-]{0,79}$`.
- `type`
- `title`
- `summary`
- `confidence`
- `verification_status`
- `payload`

Optional fields:

- `status`, default `active`
- `scope`, default project scope
- `tags`, default `[]`
- `evidence`, default `[]`
- `relations`, default `[]`
- `extensions`

Do not provide `id`, `created_at`, `updated_at`, `generated_by`, or
`content_hash`. KirokuForge generates them.

Evidence may omit `observed_at`; `add-record` then uses the acquisition time.
Every evidence source must be listed in the active run's `inputs`.

Example:

```json
{
  "key": "canonical_memory",
  "type": "decision",
  "title": "Canonical project memory",
  "summary": "Structured JSON is the source of truth.",
  "confidence": "confirmed",
  "verification_status": "verified",
  "evidence": [
    {
      "source_id": "src_user_request",
      "relation": "supports",
      "method": "user_statement",
      "target": "/payload/decision",
      "locator": {
        "kind": "message",
        "message_id": "message-1"
      }
    }
  ],
  "payload": {
    "decision": "Use structured JSON as canonical memory.",
    "context": "Generated views must not become competing sources.",
    "implications": [
      "Generate user views from canonical records."
    ]
  }
}
```

Add it from a file:

```bash
python <skill-dir>/scripts/kiroku.py add-record \
  --dir ./kiroku \
  --run-id run_update_example \
  --file ./record-draft.json
```

For direct agent output, use `--stdin`.

The same key and semantic content is idempotent. The same key with changed
content is rejected and must later be handled by `update-record`. Equivalent
content under another key is also deduplicated.

Update a record using the hash read from canonical memory:

```bash
python <skill-dir>/scripts/kiroku.py update-record \
  --dir ./kiroku \
  --run-id run_update_example \
  --key canonical_memory \
  --expect-hash sha256:... \
  --file ./record-draft.json
```

An update is a complete semantic replacement, not a partial merge. The draft
must retain the same `key` and `type`. KirokuForge preserves `id`, `created_at`,
and timestamps of unchanged evidence, then refreshes `updated_at`,
`generated_by`, and `content_hash`.

`--expect-hash` is mandatory optimistic concurrency control. A stale hash
rejects the operation without changing canonical memory.
