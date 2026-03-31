#!/usr/bin/env python3
"""Run retrieval, synthesis, build, and render for a people dossier."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import build_dossier
import render_report
import retrieve_sources


IDENTITY_KEYWORDS = ["法定代表人", "高管", "股东", "人物", "简介", "person", "履历", "背景"]
CAREER_KEYWORDS = ["曾任", "加入", "毕业", "履历", "董事长", "创立", "career"]
COMPANY_KEYWORDS = ["融资", "估值", "营收", "注册资本", "量产", "交付", "股东", "官网", "产品", "公司"]
RELATION_KEYWORDS = ["联合创始人", "合作伙伴", "妻子", "股东", "合资", "关联", "法定代表人"]
RISK_KEYWORDS = ["风险", "经营异常", "诉讼", "司法", "立案", "担保", "违法", "*ST"]
DIGITAL_KINDS = {"social", "video", "code"}
RISK_FALSE_POSITIVES = ["风险等级", "风控合规", "贷前尽调", "贷后风控", "采购风控", "营销拓客", "免费试用", "数据API"]
CONTACT_BLOCKLIST = {
    "sohu.com",
    "www.sohu.com",
    "qixin.com",
    "www.qixin.com",
    "aiqicha.baidu.com",
    "www.aiqicha.com",
    "zhihu.com",
    "zhuanlan.zhihu.com",
}
MATCH_PRIORITY = {"strong": 0, "likely": 1, "weak": 2, "ambiguous": 3}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--company", default="")
    parser.add_argument("--role", default="")
    parser.add_argument("--aliases", default="")
    parser.add_argument("--research-goal", default="")
    parser.add_argument("--must-answer", action="append", default=[])
    parser.add_argument("--seed-url", action="append", default=[])
    parser.add_argument("--seed-file", type=Path, default=None)
    parser.add_argument("--company-domain", action="append", default=[])
    parser.add_argument("--reuse-normalized", type=Path, default=None)
    parser.add_argument("--language", default="zh-CN")
    parser.add_argument("--max-results-per-query", type=int, default=5)
    parser.add_argument("--max-pages", type=int, default=10)
    parser.add_argument("--outdir", type=Path, required=True)
    return parser.parse_args()


def summarize_text(text: str, limit: int = 260) -> str:
    cleaned = " ".join(text.split()).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def source_tag(row: dict[str, Any]) -> str:
    return f"[{row['source_name']}|{row['tier']}|{row['domain']}]"


def is_noise_fragment(text: str) -> bool:
    return any(
        keyword in text
        for keyword in ["最新文章", "查看TA的文章", "返回搜狐", "免费试用", "数据API", "登录用户", "启信宝企业版", "阅读全文"]
    )


def source_text(row: dict[str, Any], target_terms: list[str] | None = None) -> str:
    target_terms = target_terms or []
    fetch = row.get("fetch", {})
    title = row.get("title", "")
    if title.startswith("http"):
        title = fetch.get("title", "") or row.get("source_name", "") or title
    parts = [title, row.get("snippet", ""), fetch.get("meta_description", "")]
    excerpt = fetch.get("text_excerpt", "")
    sentences = re.split(r"(?<=[。！？.!?])\s+", excerpt)
    for sentence in sentences:
        cleaned = " ".join(sentence.split()).strip()
        if len(cleaned) < 16 or is_noise_fragment(cleaned):
            continue
        if any(term and term in cleaned for term in target_terms) or any(
            keyword in cleaned for keyword in ["法定代表人", "股东", "董事长", "CEO", "量产", "融资", "乔迁", "成立", "产值", "交付"]
        ):
            parts.append(cleaned)
        if len(parts) >= 4:
            break
    deduped = list(dict.fromkeys(part for part in parts if part and not is_noise_fragment(part)))
    return summarize_text(" ".join(deduped), limit=360)


def match_keywords(row: dict[str, Any], keywords: list[str]) -> bool:
    corpus = " ".join(
        [
            row.get("title", ""),
            row.get("snippet", ""),
            row.get("fetch", {}).get("title", ""),
            row.get("fetch", {}).get("meta_description", ""),
            row.get("fetch", {}).get("text_excerpt", ""),
        ]
    ).lower()
    return any(keyword.lower() in corpus for keyword in keywords)


def keep_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    usable = [row for row in rows if row.get("entity_match") in {"strong", "likely"}]
    if not usable:
        usable = [row for row in rows if row.get("entity_match") != "ambiguous"]
    return sorted(
        usable or rows,
        key=lambda row: (
            MATCH_PRIORITY.get(row.get("entity_match", "weak"), 9),
            row.get("best_rank", 999),
            row.get("tier", "tier9"),
            -row.get("match_score", 0),
        ),
    )


def has_specific_risk_signal(row: dict[str, Any]) -> bool:
    corpus = " ".join(
        [
            row.get("title", ""),
            row.get("snippet", ""),
            row.get("fetch", {}).get("meta_description", ""),
            row.get("fetch", {}).get("text_excerpt", ""),
        ]
    )
    if any(keyword in corpus for keyword in RISK_FALSE_POSITIVES):
        return False
    return any(keyword in corpus for keyword in RISK_KEYWORDS)


def select_sources(rows: list[dict[str, Any]], predicate, limit: int) -> list[dict[str, Any]]:
    selected = []
    for row in rows:
        if predicate(row):
            selected.append(row)
        if len(selected) >= limit:
            break
    return selected


def build_outreach_channels(rows: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    seen = set()
    for row in rows:
        fetch = row.get("fetch", {})
        for email in fetch.get("emails", []):
            domain = email.lower().split("@")[-1]
            if domain in CONTACT_BLOCKLIST:
                continue
            key = ("email", email)
            if key not in seen:
                seen.add(key)
                lines.append(f"- {source_tag(row)} Public email: {email}")
        for phone in fetch.get("phones", []):
            if row.get("kind") not in {"official"}:
                continue
            key = ("phone", phone)
            if key not in seen:
                seen.add(key)
                lines.append(f"- {source_tag(row)} Public phone: {phone}")
        if row["kind"] == "official" and row["domain"] not in CONTACT_BLOCKLIST:
            key = ("site", row["domain"])
            if key not in seen:
                seen.add(key)
                lines.append(f"- {source_tag(row)} Public website: {row['url']}")
    return lines[:18]


def build_follow_up(rows: list[dict[str, Any]], must_answer: list[str]) -> list[str]:
    items: list[str] = []
    tiers = {row["tier"] for row in rows}
    joined = " ".join(source_text(row) for row in rows).lower()

    if "tier1" not in tiers:
        items.append("补查 Tier 1 硬源：至少补齐工商/公告/官网或政府页中的一种直接来源。")
    if not any(row["kind"] == "registry" for row in rows):
        items.append("补查工商或股权数据库，确认法定代表人、股东、控制权和关联实体。")
    if not any(row["kind"] in {"filing", "risk"} for row in rows):
        items.append("补查监管、公告、司法或经营异常线索，避免风险模块只依赖媒体叙事。")
    if not any(row["kind"] in DIGITAL_KINDS for row in rows):
        items.append("补查数字足迹，包括微博、LinkedIn、GitHub、视频平台或社区。")

    for question in must_answer:
        if question.lower() not in joined:
            items.append(f"继续核实必答问题：{question}")
    return [f"{idx}. {item}" for idx, item in enumerate(items[:12], start=1)]


def build_gap_notes(rows: list[dict[str, Any]]) -> list[str]:
    notes: list[str] = []
    for row in rows:
        if row.get("entity_match") != "ambiguous":
            continue
        notes.append(
            f"- {source_tag(row)} 存在同名异人或正文不一致风险：{row['title']}。请优先人工复核后再纳入结论。"
        )
    if not notes:
        notes.append("- 当前检索结果未发现明显同名异人冲突，但仍需持续复核弱匹配来源。")
    return notes[:6]


def synthesize_research_notes(args: argparse.Namespace, rows: list[dict[str, Any]], must_answer: list[str]) -> str:
    target_terms = [args.name, args.company, args.role]
    all_rows = rows
    rows = keep_rows(rows)
    overview = select_sources(rows, lambda row: row["tier"] in {"tier1", "tier2"}, 8)
    identity = select_sources(rows, lambda row: match_keywords(row, IDENTITY_KEYWORDS), 8)
    career = select_sources(rows, lambda row: match_keywords(row, CAREER_KEYWORDS), 8)
    company = select_sources(rows, lambda row: match_keywords(row, COMPANY_KEYWORDS), 10)
    digital = select_sources(rows, lambda row: row["kind"] in DIGITAL_KINDS or match_keywords(row, ["微博", "LinkedIn", "GitHub"]), 8)
    relation = select_sources(
        rows,
        lambda row: match_keywords(row, RELATION_KEYWORDS) and row.get("kind") not in {"registry"},
        8,
    )
    risk = select_sources(rows, has_specific_risk_signal, 10)
    timeline = select_sources(rows, lambda row: bool(re.search(r"(?:19|20)\\d{2}", source_text(row, target_terms))), 8)

    lines = [
        f"# {args.name} 人物尽调研究笔记",
        "",
        "一、概要",
    ]
    for row in overview:
        lines.append(f"- {source_tag(row)} {source_text(row, target_terms)}")

    lines.extend(["", "二、身份与背景"])
    for row in identity:
        lines.append(f"- {source_tag(row)} {source_text(row, target_terms)}")

    lines.extend(["", "三、职业履历"])
    for row in career:
        lines.append(f"- {source_tag(row)} {source_text(row, target_terms)}")

    lines.extend(["", "四、当前角色与公司"])
    for row in company:
        lines.append(f"- {source_tag(row)} {source_text(row, target_terms)}")

    lines.extend(["", "七、数字足迹"])
    for row in digital:
        lines.append(f"- {source_tag(row)} {source_text(row, target_terms)}")

    lines.extend(["", "九、关系网络"])
    for row in relation:
        lines.append(f"- {source_tag(row)} {source_text(row, target_terms)}")

    lines.extend(["", "十、时间线"])
    for row in timeline:
        lines.append(f"- {source_tag(row)} {source_text(row, target_terms)}")

    lines.extend(["", "十一、信息缺口与矛盾点"])
    lines.extend(build_gap_notes(all_rows))

    lines.extend(["", "十七、风险信号"])
    for row in risk:
        lines.append(f"- {source_tag(row)} {source_text(row, target_terms)}")

    lines.extend(["", "十八、证据来源"])
    for row in rows[:20]:
        lines.append(f"- {source_tag(row)} {row['title']} | {row['url']}")

    lines.extend(["", "十九、联系与触达"])
    outreach_lines = build_outreach_channels(rows)
    lines.extend(outreach_lines or ["- 未从公开抓取结果中提取到明确联系方式。"])

    lines.extend(["", "二十、后续研究方向"])
    lines.extend(build_follow_up(rows, must_answer) or ["1. 继续补充更高质量的 Tier 1 来源和数字足迹。"])

    return "\n".join(lines) + "\n"


def normalized_to_source_register(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    register = []
    for row in rows:
        used_for = ", ".join(sorted(row.get("query_buckets", [])))
        register.append(
            {
                "tier": row["tier"],
                "name": row["source_name"],
                "kind": row["kind"],
                "url": row["url"],
                "information_value": summarize_text(
                    " ".join(part for part in [row.get("title", ""), row.get("snippet", ""), row.get("entity_match", "")] if part),
                    180,
                ),
                "used_for": used_for or row.get("entity_match", "search result"),
            }
        )
    return register


def main() -> int:
    args = parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    retrieval_args = SimpleNamespace(
        name=args.name,
        company=args.company,
        role=args.role,
        aliases=args.aliases,
        research_goal=args.research_goal,
        must_answer=args.must_answer,
        seed_url=args.seed_url,
        seed_file=args.seed_file,
        company_domain=args.company_domain,
        reuse_normalized=args.reuse_normalized,
        max_results_per_query=args.max_results_per_query,
        max_pages=args.max_pages,
        outdir=args.outdir,
    )
    raw_sources, normalized_sources, search_log = retrieve_sources.retrieve(retrieval_args)
    retrieve_sources.write_json(args.outdir / "raw_sources.json", raw_sources)
    retrieve_sources.write_json(args.outdir / "normalized_sources.json", normalized_sources)
    retrieve_sources.write_json(args.outdir / "search_log.json", search_log)

    effective_target = search_log.get("target", {})
    effective_must_answer = effective_target.get("must_answer", args.must_answer)
    effective_seed_urls = effective_target.get("seed_urls", args.seed_url)
    effective_company_domains = effective_target.get("company_domains", args.company_domain)
    usable_sources = keep_rows(normalized_sources)
    research_notes = synthesize_research_notes(args, normalized_sources, effective_must_answer)
    notes_path = args.outdir / "research_notes.md"
    notes_path.write_text(research_notes, encoding="utf-8")

    build_args = SimpleNamespace(
        input_path=notes_path,
        name=args.name,
        company=args.company,
        role=args.role,
        language=args.language,
    )
    payload = build_dossier.build_payload(build_args, research_notes)
    payload["meta"]["research_goal"] = args.research_goal
    payload["meta"]["must_answer"] = effective_must_answer
    payload["meta"]["seed_urls"] = effective_seed_urls
    payload["meta"]["seed_file"] = str(args.seed_file) if args.seed_file else ""
    payload["meta"]["company_domains"] = effective_company_domains
    payload["meta"]["reuse_normalized"] = str(args.reuse_normalized) if args.reuse_normalized else ""
    payload["meta"]["usable_source_count"] = len(usable_sources)
    payload["source_register"] = normalized_to_source_register(usable_sources[:20])

    build_dossier.write_json(args.outdir / "structured_report.json", payload)
    build_dossier.write_json(args.outdir / "run_log.json", build_dossier.build_run_log(payload))
    report = render_report.render_report(payload)
    (args.outdir / "report.md").write_text(report, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
