#!/usr/bin/env python3
"""Evaluate a generated people dossier for structural quality."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
URL_RE = re.compile(r"https?://|(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?86[- ]?)?(?:1[3-9]\d{9}|400[- ]?\d{3,4}[- ]?\d{3,4}|0\d{2,3}[- ]?\d{7,8})")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_path", type=Path, help="Path to structured_report.json")
    parser.add_argument("--output", type=Path, required=True, help="Path to evaluation.json")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def optional_ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 1.0


def evaluate(payload: dict[str, Any]) -> dict[str, Any]:
    claims = payload.get("claims", [])
    relationships = payload.get("relationship_notes", [])
    timeline = payload.get("timeline", [])
    backlog = payload.get("research_backlog", [])
    outreach = payload.get("outreach_channels", [])
    risks = payload.get("risk_ledger", [])
    sources = payload.get("source_register", [])

    traceable_claims = sum(
        1 for claim in claims if claim.get("sources") and any(source != claim.get("section") for source in claim.get("sources", []))
    )
    valid_labels = sum(1 for claim in claims if claim.get("label") in {"fact", "inference", "unverified"})
    relationship_noise = sum(
        1
        for row in relationships
        if row.get("entity") == "unknown"
        or row.get("entity", "").count("/") >= 2
        or len(row.get("entity", "")) > 24
    )
    clean_timeline = sum(
        1 for row in timeline if row.get("date") != "unknown" and not any(keyword in row.get("event", "") for keyword in ["来源", "营业收入", "净利润"])
    )
    useful_backlog = sum(
        1 for row in backlog if not any(keyword in row.get("question", "") for keyword in ["已确认", "已获取", "已发现", "已厘清", "已查实"])
    )
    valid_outreach = sum(
        1
        for row in outreach
        if EMAIL_RE.search(row.get("value", ""))
        or PHONE_RE.search(row.get("value", ""))
        or URL_RE.search(row.get("value", ""))
        or row.get("channel") == "social"
    )
    traceable_risks = sum(1 for row in risks if row.get("sources"))
    strong_sources = sum(1 for row in sources if row.get("tier") in {"tier1", "tier2"})

    metrics = {
        "claim_traceability_ratio": safe_ratio(traceable_claims, len(claims)),
        "claim_label_valid_ratio": safe_ratio(valid_labels, len(claims)),
        "relationship_noise_ratio": safe_ratio(relationship_noise, len(relationships)),
        "timeline_cleanliness_ratio": optional_ratio(clean_timeline, len(timeline)),
        "backlog_usefulness_ratio": safe_ratio(useful_backlog, len(backlog)),
        "outreach_valid_ratio": optional_ratio(valid_outreach, len(outreach)),
        "risk_traceability_ratio": optional_ratio(traceable_risks, len(risks)),
        "source_quality_ratio": safe_ratio(strong_sources, len(sources)),
        "counts": {
            "claims": len(claims),
            "relationships": len(relationships),
            "timeline": len(timeline),
            "backlog": len(backlog),
            "outreach": len(outreach),
            "risks": len(risks),
            "sources": len(sources),
        },
    }
    metrics["gates"] = {
        "traceable_claims": metrics["claim_traceability_ratio"] >= 0.6,
        "valid_labels": metrics["claim_label_valid_ratio"] >= 0.95,
        "low_relationship_noise": metrics["relationship_noise_ratio"] <= 0.2,
        "clean_timeline": metrics["timeline_cleanliness_ratio"] >= 0.8,
        "useful_backlog": metrics["backlog_usefulness_ratio"] >= 0.8,
        "traceable_risks": metrics["risk_traceability_ratio"] >= 0.8,
        "strong_source_mix": metrics["source_quality_ratio"] >= 0.7,
    }
    return metrics


def main() -> int:
    args = parse_args()
    payload = load_json(args.input_path)
    result = evaluate(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
