"""Human-facing Markdown projections."""

from __future__ import annotations

from collections import Counter
from typing import Any


VIEW_TYPES = {
    "overview.md": {"fact", "constraint", "implementation_detail"},
    "decisions.md": {"decision", "assumption"},
    "actions.md": {"task", "roadmap_item"},
    "risks-and-questions.md": {"risk", "question", "conflict"},
    "preferences.md": {"preference"},
    "history.md": {"idea", "rejected_idea", "event"},
}


def _record_header(record: dict[str, Any]) -> str:
    return (
        f"<!-- record:{record['id']} -->\n"
        f"## {record['title']}\n\n"
        f"**ID:** `{record['id']}`  \n"
        f"**Type:** `{record['type']}` | **Status:** `{record['status']}` | "
        f"**Verification:** `{record['verification_status']}`  \n\n"
        f"{record['summary']}\n\n"
    )


def _payload(record: dict[str, Any]) -> str:
    lines: list[str] = []
    for key, value in record["payload"].items():
        label = key.replace("_", " ").title()
        if isinstance(value, list):
            lines.append(f"**{label}:**")
            if value:
                for item in value:
                    if isinstance(item, dict):
                        rendered = "; ".join(
                            f"{k.replace('_', ' ')}: {v}" for k, v in item.items()
                        )
                        lines.append(f"- {rendered}")
                    else:
                        lines.append(f"- {item}")
            else:
                lines.append("- None")
            lines.append("")
        elif value is not None:
            lines.append(f"**{label}:** {value}  ")
    return "\n".join(lines).rstrip() + "\n\n"


def _evidence(record: dict[str, Any]) -> str:
    if not record["evidence"]:
        return "**Evidence:** none\n\n"
    lines = ["**Evidence:**"]
    for item in record["evidence"]:
        lines.append(
            f"- `{item['source_id']}`: {item['relation']} via {item['method']}"
        )
    return "\n".join(lines) + "\n\n"


def render_record(record: dict[str, Any]) -> str:
    return _record_header(record) + _payload(record) + _evidence(record)


def render_views(memory: dict[str, Any]) -> dict[str, str]:
    project = memory["project"]
    records = memory["records"]
    counts = Counter(record["type"] for record in records)

    views: dict[str, str] = {}
    for filename, types in VIEW_TYPES.items():
        title = filename.removesuffix(".md").replace("-", " ").title()
        selected = [record for record in records if record["type"] in types]
        content = [f"# {title}\n\n"]
        if selected:
            for record in selected:
                content.append(render_record(record))
        else:
            content.append("_No records._\n")
        views[filename] = "".join(content)

    source_lines = ["# Sources\n\n"]
    for source in memory["sources"]:
        source_lines.extend(
            [
                f"## {source['title']}\n\n",
                f"**ID:** `{source['id']}`  \n",
                f"**Kind:** `{source['kind']}`  \n",
                f"**URI:** `{source['uri']}`  \n",
                f"**Revision:** `{source.get('revision') or 'unknown'}`  \n",
                f"**Integrity:** `{source['integrity']}`\n\n",
            ]
        )
    if not memory["sources"]:
        source_lines.append("_No sources._\n")
    views["sources.md"] = "".join(source_lines)

    index = [
        "# Kiroku Memory\n\n",
        f"**Project:** {project['name']}  \n",
        f"**Domain:** {project['domain']}  \n",
        f"**Status:** {project['status']}  \n",
        f"**Goal:** {project['goal']}  \n\n",
        "## Views\n\n",
    ]
    descriptions = {
        "overview.md": "Facts, constraints, and implementation context",
        "decisions.md": "Decisions and assumptions",
        "actions.md": "Tasks and roadmap",
        "risks-and-questions.md": "Risks, questions, and conflicts",
        "preferences.md": "Durable user and project preferences",
        "history.md": "Ideas, rejected alternatives, and events",
        "sources.md": "Evidence source index",
    }
    for filename in [*VIEW_TYPES, "sources.md"]:
        index.append(f"- [{filename}]({filename}): {descriptions[filename]}\n")
    index.extend(["\n## Statistics\n\n", "| Type | Count |\n", "|---|---:|\n"])
    for record_type in sorted(counts):
        index.append(f"| `{record_type}` | {counts[record_type]} |\n")
    index.append(f"| **Total** | **{len(records)}** |\n")
    views["INDEX.md"] = "".join(index)
    return views
