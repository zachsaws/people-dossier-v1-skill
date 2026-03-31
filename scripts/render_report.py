#!/usr/bin/env python3
"""Render a richer Markdown people dossier from structured_report.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_path", type=Path, help="Path to structured_report.json")
    parser.add_argument("--output", type=Path, required=True, help="Path to report.md")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def render_list(rows: list[str], fallback: str = "- None.") -> list[str]:
    if not rows:
        return [fallback]
    return [f"- {row}" for row in rows]


def render_sources(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["- None."]
    lines = [
        "| Tier | Name | Kind | Information Value | Used For |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row.get('tier', '')} | {row.get('name', '')} | {row.get('kind', '')} | {row.get('information_value', '')} | {row.get('used_for', '')} |"
        )
    return lines


def render_claim_rows(rows: list[dict[str, Any]], key: str, fallback: str) -> list[str]:
    if not rows:
        return [fallback]
    return [f"- {row.get(key, '')}" for row in rows]


def render_report(payload: dict[str, Any]) -> str:
    meta = payload.get("meta", {})
    identity = payload.get("identity_background", {})
    career = payload.get("career_history", {})
    current = payload.get("current_company_role", {})
    digital = payload.get("digital_footprint", {})
    signal = payload.get("signal_narrative", {})
    assessment = payload.get("comprehensive_assessment", {})

    lines = [
        "# People Dossier",
        "",
        "## Meta",
        f"- Name: {meta.get('name', 'unknown')}",
        f"- Company: {meta.get('company', 'unknown')}",
        f"- Role: {meta.get('role', 'unknown')}",
        f"- Language: {meta.get('language', 'unknown')}",
        f"- Scope: {meta.get('scope', 'unknown')}",
        "",
        "## Executive Summary",
    ]
    lines.extend(render_list(payload.get("executive_summary", [])))

    lines.extend(
        [
            "",
            "## Identity & Background",
            f"- Summary: {identity.get('summary') or 'unknown'}",
        ]
    )
    lines.extend(render_list(identity.get("basic_facts", []), fallback="- No basic facts recorded."))
    lines.extend(render_list([f"Alias: {alias}" for alias in identity.get("aliases", [])], fallback="- No aliases recorded."))
    lines.extend(render_list([f"Location: {item}" for item in identity.get("locations", [])], fallback="- No public locations recorded."))
    lines.extend(render_list([f"Education: {item}" for item in identity.get("education", [])], fallback="- No education details recorded."))

    lines.extend(
        [
            "",
            "## Career History",
            f"- Summary: {career.get('summary') or 'unknown'}",
        ]
    )
    lines.extend(render_list(career.get("highlights", []), fallback="- No career highlights recorded."))

    lines.extend(
        [
            "",
            "## Current Company & Role",
            f"- Company summary: {current.get('company_summary') or 'unknown'}",
            f"- Role summary: {current.get('role_summary') or 'unknown'}",
        ]
    )
    lines.extend(render_list([f"Ownership note: {item}" for item in current.get("ownership_notes", [])], fallback="- No ownership notes recorded."))
    lines.extend(render_list([f"Metric: {item}" for item in current.get("company_metrics", [])], fallback="- No company metrics recorded."))

    lines.extend(
        [
            "",
            "## Digital Footprint",
            f"- Summary: {digital.get('summary') or 'unknown'}",
        ]
    )
    lines.extend(render_list([f"Channel: {item}" for item in digital.get("channels", [])], fallback="- No digital channels recorded."))
    lines.extend(render_list(digital.get("observations", []), fallback="- No digital observations recorded."))

    lines.extend(
        [
            "",
            "## Signal Narrative",
            f"- Summary: {signal.get('summary') or 'unknown'}",
            "",
            "### Strengths",
        ]
    )
    lines.extend(render_list(signal.get("strengths", []), fallback="- No strengths recorded."))
    lines.extend(["", "### Concerns"])
    lines.extend(render_list(signal.get("concerns", []), fallback="- No concerns recorded."))

    lines.extend(["", "## Relationship Notes"])
    relationship_rows = []
    for row in payload.get("relationship_notes", []):
        relationship_rows.append(
            f"{row.get('entity', 'unknown')}: {row.get('detail', '')} [{row.get('confidence', 'unknown')}]"
        )
    lines.extend(render_list(relationship_rows, fallback="- No relationship notes recorded."))

    lines.extend(["", "## Behavior Patterns"])
    behavior_rows = []
    for row in payload.get("behavior_patterns", []):
        behavior_rows.append(f"{row.get('pattern', '')} [{row.get('confidence', 'unknown')}]")
    lines.extend(render_list(behavior_rows, fallback="- No behavior patterns recorded."))

    lines.extend(["", "## Timeline"])
    timeline_rows = []
    for row in payload.get("timeline", []):
        timeline_rows.append(
            f"{row.get('date', 'unknown')} | {row.get('label', 'unknown')} | {row.get('event', '')}"
        )
    lines.extend(render_list(timeline_rows, fallback="- No timeline events recorded."))

    lines.extend(["", "## Gaps & Contradictions"])
    gap_rows = []
    for row in payload.get("gaps_contradictions", []):
        gap_rows.append(f"{row.get('kind', 'gap')}: {row.get('item', '')}")
    lines.extend(render_list(gap_rows, fallback="- No gaps or contradictions recorded."))

    lines.extend(
        [
            "",
            "## Comprehensive Assessment",
            f"- Summary: {assessment.get('summary') or 'unknown'}",
            "",
            "### Proven Points",
        ]
    )
    lines.extend(render_list(assessment.get("proven_points", []), fallback="- No proven points recorded."))
    lines.extend(["", "### Inferred Points"])
    lines.extend(render_list(assessment.get("inferred_points", []), fallback="- No inferred points recorded."))

    lines.extend(["", "## Risk Ledger"])
    risk_rows = []
    for row in payload.get("risk_ledger", []):
        risk_rows.append(
            f"[{row.get('severity', 'unknown')}] {row.get('category', 'unknown')}: {row.get('label', '')} - {row.get('detail', '')}"
        )
    lines.extend(render_list(risk_rows, fallback="- No risks recorded."))

    lines.extend(["", "## Source Register"])
    lines.extend(render_sources(payload.get("source_register", [])))

    lines.extend(["", "## Outreach & Research Backlog", "", "### Outreach Channels"])
    outreach_rows = []
    for row in payload.get("outreach_channels", []):
        outreach_rows.append(
            f"{row.get('channel', 'unknown')}: {row.get('value', '')} ({row.get('effectiveness', 'unknown')})"
        )
    lines.extend(render_list(outreach_rows, fallback="- No public outreach channels recorded."))

    backlog_rows = []
    for row in payload.get("research_backlog", []):
        backlog_rows.append(
            f"{row.get('priority', 'unknown')} priority: {row.get('question', '')} - {row.get('why_it_matters', '')}"
        )
    lines.extend(["", "### Research Backlog"])
    lines.extend(render_list(backlog_rows, fallback="- No backlog items recorded."))

    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    payload = load_json(args.input_path)
    report = render_report(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
