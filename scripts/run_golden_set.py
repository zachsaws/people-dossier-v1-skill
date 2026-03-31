#!/usr/bin/env python3
"""Run the people dossier pipeline against a golden target set."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


METRIC_KEYS = [
    "claim_traceability_ratio",
    "claim_label_valid_ratio",
    "relationship_noise_ratio",
    "timeline_cleanliness_ratio",
    "backlog_usefulness_ratio",
    "outreach_valid_ratio",
    "risk_traceability_ratio",
    "source_quality_ratio",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets", type=Path, required=True, help="Path to golden-set targets.json")
    parser.add_argument("--outdir", type=Path, required=True, help="Directory for run outputs")
    parser.add_argument("--max-results-per-query", type=int, default=4)
    parser.add_argument("--max-pages", type=int, default=6)
    return parser.parse_args()


def extend_repeated_flag(cmd: list[str], flag: str, values: list[str]) -> None:
    for value in values:
        if value:
            cmd.extend([flag, value])


def resolve_optional_path(base_dir: Path, value: str | None) -> Path | None:
    if not value:
        return None
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    return (base_dir / candidate).resolve()


def average_metrics(results: list[dict[str, Any]]) -> dict[str, float]:
    if not results:
        return {key: 0.0 for key in METRIC_KEYS}
    return {
        key: round(sum(float(result.get(key, 0.0)) for result in results) / len(results), 4)
        for key in METRIC_KEYS
    }


def render_summary(summary: dict[str, Any]) -> str:
    lines = [
        "# People Dossier Golden Set Summary",
        "",
        f"- Generated at: {summary['generated_at']}",
        f"- Target count: {summary['target_count']}",
        f"- Success count: {summary['success_count']}",
        f"- Failure count: {summary['failure_count']}",
        "",
        "## Average Metrics",
    ]
    for key, value in summary["average_metrics"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Per Target"])
    for target in summary["targets"]:
        label = f"{target['id']} ({target['status']})"
        lines.append(f"- {label}")
        if target.get("error"):
            lines.append(f"  error: {target['error']}")
            continue
        lines.append(f"  evaluation: {target['evaluation_path']}")
        metrics = ", ".join(f"{key}={target.get(key, 0.0)}" for key in METRIC_KEYS)
        lines.append(f"  metrics: {metrics}")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    targets = json.loads(args.targets.read_text(encoding="utf-8"))
    args.outdir.mkdir(parents=True, exist_ok=True)

    run_script = Path(__file__).with_name("run_dossier.py")
    eval_script = Path(__file__).with_name("evaluate_dossier.py")
    base_dir = args.targets.parent

    summary_targets: list[dict[str, Any]] = []
    successful_metrics: list[dict[str, Any]] = []

    for target in targets:
        target_dir = args.outdir / target["id"]
        target_dir.mkdir(parents=True, exist_ok=True)

        run_cmd = [
            sys.executable,
            str(run_script),
            "--name",
            target["name"],
            "--company",
            target.get("company", ""),
            "--role",
            target.get("role", ""),
            "--research-goal",
            target.get("research_goal", ""),
            "--outdir",
            str(target_dir),
            "--max-results-per-query",
            str(target.get("max_results_per_query", args.max_results_per_query)),
            "--max-pages",
            str(target.get("max_pages", args.max_pages)),
        ]
        if target.get("aliases"):
            aliases = target["aliases"]
            if isinstance(aliases, list):
                aliases = ",".join(str(value) for value in aliases)
            run_cmd.extend(["--aliases", str(aliases)])
        extend_repeated_flag(run_cmd, "--must-answer", list(target.get("must_answer", [])))
        extend_repeated_flag(run_cmd, "--seed-url", list(target.get("seed_urls", [])))
        extend_repeated_flag(run_cmd, "--company-domain", list(target.get("company_domains", [])))

        seed_file = resolve_optional_path(base_dir, target.get("seed_file"))
        if seed_file:
            run_cmd.extend(["--seed-file", str(seed_file)])
        reuse_normalized = resolve_optional_path(base_dir, target.get("reuse_normalized"))
        if reuse_normalized:
            run_cmd.extend(["--reuse-normalized", str(reuse_normalized)])

        target_summary: dict[str, Any] = {
            "id": target["id"],
            "name": target["name"],
            "category": target.get("category", ""),
            "run_dir": str(target_dir),
        }

        try:
            subprocess.run(run_cmd, check=True)
            subprocess.run(
                [
                    sys.executable,
                    str(eval_script),
                    str(target_dir / "structured_report.json"),
                    "--output",
                    str(target_dir / "evaluation.json"),
                ],
                check=True,
            )
            evaluation = json.loads((target_dir / "evaluation.json").read_text(encoding="utf-8"))
            target_summary.update(
                {
                    "status": "ok",
                    "evaluation_path": str(target_dir / "evaluation.json"),
                    **{key: evaluation.get(key, 0.0) for key in METRIC_KEYS},
                    "gates": evaluation.get("gates", {}),
                }
            )
            successful_metrics.append(evaluation)
        except subprocess.CalledProcessError as exc:
            target_summary.update({"status": "error", "error": f"command failed: {exc}"})

        summary_targets.append(target_summary)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target_count": len(targets),
        "success_count": sum(1 for row in summary_targets if row["status"] == "ok"),
        "failure_count": sum(1 for row in summary_targets if row["status"] != "ok"),
        "average_metrics": average_metrics(successful_metrics),
        "targets": summary_targets,
    }
    (args.outdir / "golden_set_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.outdir / "golden_set_summary.md").write_text(render_summary(summary), encoding="utf-8")
    return 0 if summary["success_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
