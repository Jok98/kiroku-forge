# Provenance And Evidence

## Contents

1. Evidence purpose
2. Evidence structure
3. Observation methods
4. Verification rules
5. Source locator guidance
6. Examples

## Evidence Purpose

Evidence explains why a record exists. It must allow a future agent or user to
find the original input and distinguish observation from inference.

## Evidence Structure

```json
{
  "source_id": "src_security_configuration",
  "relation": "supports",
  "method": "direct_observation",
  "target": "/payload/decision",
  "locator": {
    "kind": "lines",
    "start_line": 20,
    "end_line": 24
  },
  "observed_at": "2026-06-07T10:00:00Z",
  "note": "The security chain permits all matching requests."
}
```

Evidence relations:

- `supports`
- `refutes`
- `context`
- `supersedes`

Observation methods:

- `user_statement`
- `direct_observation`
- `test_result`
- `inference`

## Verification Rules

- `verified`: at least one supporting evidence item using `user_statement`,
  `direct_observation`, or `test_result`.
- `partially_verified`: at least one evidence item, but the complete claim is not
  covered.
- `unverified`: evidence may be absent or inferential only.
- `contradicted`: at least one refuting evidence item.
- `confidence: confirmed`: allowed only with `verification_status: verified`.

An inference can support an assumption, risk, or question but does not by itself
make a record verified.

## Source Locator Guidance

Use the locator kind that best matches the source:

- `lines`: `start_line`, `end_line`
- `message`: `message_id`
- `section`: `section`
- `selector`: `selector`
- `command`: `command`
- `url_fragment`: `fragment`

Use `target` as a JSON Pointer when evidence applies to one field rather than the
whole record.

Do not store large source excerpts in memory. Use `note` for a concise
explanation and the source URI for retrieval.

## Examples

### Explicit user decision

Use:

```json
{
  "relation": "supports",
  "method": "user_statement"
}
```

The source should identify the conversation and message.

### Repository observation

Use `repository_file`, include its revision when available, and locate exact
lines.

### Command result

Create a `command_output` or `test_result` source. Include command, exit status,
environment, and captured content hash in source metadata.

### Inferred risk

Use `method: inference`, mark the record `unverified` or `partially_verified`,
and explain the inference in `note`.
