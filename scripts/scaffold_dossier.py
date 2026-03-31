#!/usr/bin/env python3
"""Initialize a richer people dossier run folder."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--company", default="")
    parser.add_argument("--role", default="")
    parser.add_argument("--language", default="zh-CN")
    parser.add_argument("--outdir", type=Path, required=True)
    return parser.parse_args()


def build_payload(args: argparse.Namespace) -> dict:
    return {
        "meta": {
            "name": args.name,
            "company": args.company,
            "role": args.role,
            "language": args.language,
            "scope": "public-source",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "input_path": "",
        },
        "executive_summary": [],
        "identity_background": {
            "summary": "",
            "basic_facts": [],
            "aliases": [],
            "locations": [],
            "education": [],
            "identity_notes": [],
        },
        "career_history": {"summary": "", "highlights": []},
        "current_company_role": {
            "company_summary": "",
            "role_summary": "",
            "ownership_notes": [],
            "company_metrics": [],
            "key_entities": [],
        },
        "digital_footprint": {
            "summary": "",
            "channels": [],
            "observations": [],
        },
        "signal_narrative": {
            "summary": "",
            "strengths": [],
            "concerns": [],
        },
        "relationship_notes": [],
        "behavior_patterns": [],
        "timeline": [],
        "gaps_contradictions": [],
        "comprehensive_assessment": {
            "summary": "",
            "proven_points": [],
            "inferred_points": [],
        },
        "risk_ledger": [],
        "source_register": [],
        "outreach_channels": [],
        "research_backlog": [],
        "claims": [],
    }


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_run_log(path: Path) -> None:
    payload = {
        "status": "initialized",
        "notes": [],
        "artifacts": ["structured_report.json", "report.md"],
    }
    write_json(path, payload)


def write_report_stub(path: Path, payload: dict) -> None:
    meta = payload["meta"]
    body = f"""# People Dossier

## Meta

- Name: {meta["name"]}
- Company: {meta["company"] or "unknown"}
- Role: {meta["role"] or "unknown"}
- Language: {meta["language"]}
- Scope: {meta["scope"]}

## Executive Summary

- Pending research.

## Identity & Background

## Career History

## Current Company & Role

## Digital Footprint

## Signal Narrative

## Relationship Notes

## Behavior Patterns

## Timeline

## Gaps & Contradictions

## Comprehensive Assessment

## Risk Ledger

## Source Register

## Outreach & Research Backlog
"""
    path.write_text(body, encoding="utf-8")


def main() -> int:
    args = parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    payload = build_payload(args)
    write_json(args.outdir / "structured_report.json", payload)
    write_run_log(args.outdir / "run_log.json")
    write_report_stub(args.outdir / "report.md", payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
