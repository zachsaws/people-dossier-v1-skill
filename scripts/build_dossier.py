#!/usr/bin/env python3
"""Build a structured people dossier from raw research text."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HEADING_PATTERNS = [
    re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$"),
    re.compile(r"^\s*(chapter|appendix)\b.*$", re.IGNORECASE),
    re.compile(r"^\s*第[一二三四五六七八九十百千万0-9]+章.*$"),
    re.compile(r"^\s*[一二三四五六七八九十]+、.+$"),
]

URL_RE = re.compile(r"https?://[^\s)\]>]+")
DOMAIN_RE = re.compile(r"\b(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}\b")
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"(?:\+?86[- ]?)?(?:1[3-9]\d{9}|400[- ]?\d{3,4}[- ]?\d{3,4}|0\d{2,3}[- ]?\d{7,8})")
HANDLE_RE = re.compile(r"(?<![\w.])@[A-Za-z0-9_][A-Za-z0-9_.-]{1,31}")
DATE_RE = re.compile(
    r"\b(?:19|20)\d{2}(?:[-/.](?:0?[1-9]|1[0-2])(?:[-/.](?:0?[1-9]|[12]\d|3[01]))?)?\b"
)

MODULE_RULES = {
    "overview": ["概要", "summary", "概览"],
    "identity_background": ["身份", "背景", "basic", "profile"],
    "career_history": ["职业履历", "履历", "career", "经历"],
    "current_company_role": ["当前角色", "公司", "current role", "company"],
    "digital_footprint": ["数字足迹", "digital footprint"],
    "signal_narrative": ["信号", "叙事", "内容与思维", "motivation", "情景"],
    "relationship_notes": ["关系网络", "relationship", "network"],
    "behavior_patterns": ["行为模式", "行事风格", "生活与性格"],
    "timeline": ["时间线", "timeline"],
    "gaps_contradictions": ["信息缺口", "矛盾", "gap", "contradiction"],
    "comprehensive_assessment": ["综合评估", "assessment"],
    "risks": ["风险", "risk"],
    "evidence_sources": ["证据来源", "sources"],
    "outreach": ["联系与触达", "触达", "contact"],
    "follow_up": ["后续研究方向", "后续", "next research", "follow-up"],
}

SOURCE_PATTERNS = [
    ("tier1", "registry", "天眼查"),
    ("tier1", "registry", "企查查"),
    ("tier1", "registry", "爱企查"),
    ("tier1", "registry", "水滴信用"),
    ("tier1", "filing", "港交所"),
    ("tier1", "filing", "HKEXnews"),
    ("tier1", "filing", "新三板"),
    ("tier1", "filing", "上市公司公告"),
    ("tier1", "official", "政府官网"),
    ("tier1", "official", "官网"),
    ("tier2", "media", "36氪"),
    ("tier2", "media", "搜狐"),
    ("tier2", "media", "新浪"),
    ("tier2", "media", "腾讯"),
    ("tier2", "media", "网易"),
    ("tier2", "media", "EqualOcean"),
    ("tier2", "media", "OFweek"),
    ("tier2", "code", "GitHub"),
    ("tier2", "patent", "Google Patents"),
    ("tier2", "patent", "专利"),
    ("tier2", "hiring", "BOSS直聘"),
    ("tier3", "social", "微博"),
    ("tier3", "social", "LinkedIn"),
    ("tier3", "social", "Instagram"),
    ("tier3", "social", "Telegram"),
    ("tier3", "video", "Bilibili"),
    ("tier3", "video", "YouTube"),
    ("tier3", "community", "知乎"),
    ("tier3", "community", "雪球"),
    ("tier3", "community", "东方财富"),
]

RELATION_KEYWORDS = ["联合创始人", "妻子", "家族公司", "股东", "合伙人", "关联", "控股", "合作伙伴"]
INFERENCE_KEYWORDS = ["评估", "推测", "可能", "意味着", "说明", "暗示", "大概率", "更接近"]
LOW_CONFIDENCE_KEYWORDS = ["未证实", "待确认", "不确定", "尚待", "存疑"]
RISK_KEYWORDS = ["风险", "立案调查", "经营异常", "担保", "追偿", "质疑", "司法", "冲突", "*st"]
HIGH_SEVERITY_KEYWORDS = ["立案调查", "经营异常", "追偿", "违法违规", "高关注度", "*st"]
MEDIUM_SEVERITY_KEYWORDS = ["担保", "司法", "质疑", "冲突", "矛盾", "风险升级"]
SOURCE_PREFIX_RE = re.compile(r"^[\[\【]([^\]\】]{2,180})[\]\】]\s*(.+)$")
CLAIM_MODULES = {
    "overview",
    "identity_background",
    "career_history",
    "current_company_role",
    "digital_footprint",
    "signal_narrative",
    "relationship_notes",
    "behavior_patterns",
    "timeline",
    "gaps_contradictions",
    "comprehensive_assessment",
    "risks",
}
STOP_ENTITY_TOKENS = {
    "联合创始人",
    "董事长兼",
    "董事长",
    "有限公司",
    "法定代表",
    "高管",
    "股东",
    "信息显示",
    "该公司现",
    "关系网络",
    "示例公司",
    "公司",
    "法定代表人",
    "创始人",
    "核心团队",
    "北京",
    "苏州",
    "上海",
    "成都",
    "公告提及",
    "科技股份",
    "人形机器",
    "人第二弹",
    "华为离职",
    "天才少年",
}
HANDLE_BLOCKLIST = {"@context", "@type", "@id"}
OUTREACH_BLOCKED_DOMAINS = {
    "aiqicha.baidu.com",
    "www.aiqicha.com",
    "qixin.com",
    "www.qixin.com",
    "qcc.com",
    "www.qcc.com",
    "tianyancha.com",
    "www.tianyancha.com",
    "sohu.com",
    "www.sohu.com",
    "zhihu.com",
    "www.zhihu.com",
    "zhuanlan.zhihu.com",
    "duckduckgo.com",
}
OUTREACH_BLOCKED_LOCALPARTS = {"kefu", "service", "support", "admin", "noreply", "no-reply"}
NOISE_SENTENCE_KEYWORDS = {
    "最新文章",
    "查看ta的文章",
    "返回搜狐",
    "微信好友",
    "朋友圈",
    "扫码下载",
    "app下载",
    "上一篇",
    "下一篇",
    "版权归原作者所有",
    "it频道最新文章",
    "新闻 体育 汽车 房产",
    "联系我们",
}
STOP_ENTITY_SUBSTRINGS = {"页面介绍", "公开资料", "数据集", "发布会", "计划", "人物之一", "身份"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_path", type=Path, help="Raw research text or Markdown")
    parser.add_argument("--name", default="")
    parser.add_argument("--company", default="")
    parser.add_argument("--role", default="")
    parser.add_argument("--language", default="zh-CN")
    parser.add_argument("--outdir", type=Path, required=True)
    return parser.parse_args()


def normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\f", "\n\n").strip()


def summarize_text(text: str, limit: int = 220) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def is_noise_sentence(text: str) -> bool:
    lowered = text.lower()
    if len(text.strip()) < 12:
        return True
    if any(keyword in lowered for keyword in NOISE_SENTENCE_KEYWORDS):
        return True
    if text.count("http") >= 2:
        return True
    if text.count("|") >= 4:
        return True
    return False


def is_heading(line: str) -> bool:
    if len(line.strip()) > 120:
        return False
    return any(pattern.match(line) for pattern in HEADING_PATTERNS)


def clean_heading(line: str) -> str:
    return re.sub(r"^\s*#{1,6}\s*", "", line).strip()


def split_sections(text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    sections: list[dict[str, Any]] = []
    current_title = "Document"
    current_lines: list[str] = []
    index = 1

    for line in lines:
        if is_heading(line):
            if current_lines:
                body = "\n".join(current_lines).strip()
                if body:
                    sections.append({"index": index, "title": current_title, "body": body})
                    index += 1
            current_title = clean_heading(line)
            current_lines = []
            continue
        current_lines.append(line)

    body = "\n".join(current_lines).strip()
    if body:
        sections.append({"index": index, "title": current_title, "body": body})

    if not sections:
        sections.append({"index": 1, "title": "Document", "body": text})
    return sections


def classify_module(title: str) -> str:
    lowered = title.lower()
    for module, keywords in MODULE_RULES.items():
        if any(keyword.lower() in lowered for keyword in keywords):
            return module
    return "other"


def split_sentences(text: str) -> list[str]:
    merged_lines: list[str] = []
    buffer = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        is_new_item = bool(re.match(r"^(?:\d+|[一二三四五六七八九十]+)[.、]", line) or line.startswith(("•", "-", "*")))
        if is_new_item and buffer:
            merged_lines.append(buffer)
            buffer = re.sub(r"^(?:\d+|[一二三四五六七八九十]+)[.、]\s*", "", line).lstrip("•*- ").strip()
        else:
            buffer += line
        if line.endswith(("。", "！", "？", ".", "!", "?")):
            merged_lines.append(buffer)
            buffer = ""
    if buffer:
        merged_lines.append(buffer)

    raw_parts = re.split(r"(?<=[。！？.!?])\s+", "\n".join(merged_lines))
    sentences = [re.sub(r"\s+", " ", part).strip(" -\t•") for part in raw_parts if part.strip()]
    return [sentence for sentence in sentences if 16 <= len(sentence) <= 500 and not is_noise_sentence(sentence)]


def extract_numbered_items(text: str) -> list[str]:
    items: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r"^(?:\d+|[一二三四五六七八九十]+)[.、]", stripped):
            if current:
                items.append("".join(current).strip())
            current = [re.sub(r"^(?:\d+|[一二三四五六七八九十]+)[.、]\s*", "", stripped)]
        else:
            if current:
                current.append(stripped)
    if current:
        items.append("".join(current).strip())
    return [item for item in items if len(item) >= 12]


def extract_public_handles(text: str) -> list[str]:
    handles = []
    for handle in sorted(set(HANDLE_RE.findall(text))):
        lowered = handle.lower()
        if any(lowered.endswith(suffix) for suffix in [".com", ".cn", ".ai", ".net", ".org"]):
            continue
        if lowered in HANDLE_BLOCKLIST:
            continue
        handles.append(handle)
    return handles


def parse_source_prefix(sentence: str) -> tuple[list[str], str]:
    match = SOURCE_PREFIX_RE.match(sentence.strip())
    if not match:
        return [], sentence.strip()
    raw_parts = [part.strip() for part in match.group(1).split("|") if part.strip()]
    sources: list[str] = []
    for part in raw_parts:
        if part not in sources:
            sources.append(part)
    return sources[:3], match.group(2).strip()


def infer_confidence(text: str) -> str:
    lowered = text.lower()
    if any(keyword in lowered for keyword in LOW_CONFIDENCE_KEYWORDS):
        return "low"
    if any(keyword in lowered for keyword in INFERENCE_KEYWORDS):
        return "medium"
    return "high" if any(keyword in lowered for keyword in ["确认", "明确", "显示", "已获取", "已查实"]) else "unknown"


def infer_label(sentence: str, module: str) -> tuple[str, str]:
    lowered = sentence.lower()
    if module in {"gaps_contradictions", "follow_up"}:
        return "unverified", "general"
    if module in {"risks"} or any(keyword in lowered for keyword in RISK_KEYWORDS):
        return "inference" if any(keyword in lowered for keyword in INFERENCE_KEYWORDS) else "fact", "risk"
    if module in {"relationship_notes"} or any(keyword in lowered for keyword in RELATION_KEYWORDS):
        return "fact" if infer_confidence(sentence) in {"high", "unknown"} else "inference", "relationship"
    if module in {"timeline"} or DATE_RE.search(sentence):
        return ("inference" if infer_confidence(sentence) == "medium" else "fact"), "timeline"
    if any(keyword in lowered for keyword in LOW_CONFIDENCE_KEYWORDS):
        return "unverified", "general"
    if any(keyword in lowered for keyword in INFERENCE_KEYWORDS) or module in {
        "signal_narrative",
        "behavior_patterns",
        "comprehensive_assessment",
    }:
        return "inference", "general"
    return "fact", "general"


def collect_claims(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    seen = set()
    for section in sections:
        module = classify_module(section["title"])
        if module not in CLAIM_MODULES:
            continue
        kept = 0
        line_candidates = [line.strip().lstrip("-* ").strip() for line in section["body"].splitlines() if line.strip()]
        if not line_candidates:
            line_candidates = [section["body"]]
        for line in line_candidates:
            inherited_sources, line_body = parse_source_prefix(line)
            sentences = split_sentences(line_body) or [line_body]
            for sentence in sentences:
                source_prefix, cleaned_sentence = parse_source_prefix(sentence)
                claim_sources = source_prefix or inherited_sources or [section["title"]]
                if is_noise_sentence(cleaned_sentence):
                    continue
                label, kind = infer_label(cleaned_sentence, module)
                if len(cleaned_sentence) < 24 and kind == "general":
                    continue
                if cleaned_sentence.startswith("Public "):
                    continue
                dedupe_key = (section["title"], cleaned_sentence)
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                claims.append(
                    {
                        "section": section["title"],
                        "statement": cleaned_sentence,
                        "label": label,
                        "kind": kind,
                        "confidence": infer_confidence(cleaned_sentence),
                        "sources": claim_sources[:3],
                    }
                )
                kept += 1
                if kept >= 12:
                    break
            if kept >= 12:
                break
    return claims


def section_map(sections: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    mapped: dict[str, list[dict[str, Any]]] = {}
    for section in sections:
        mapped.setdefault(classify_module(section["title"]), []).append(section)
    return mapped


def summarize_sections(sections: list[dict[str, Any]]) -> str:
    if not sections:
        return ""
    bullets = bulletize_sentences(sections, limit=3)
    if bullets:
        return summarize_text(" ".join(bullets), limit=320)
    return summarize_text(" ".join(section["body"] for section in sections), limit=320)


def bulletize_sentences(sections: list[dict[str, Any]], limit: int = 6) -> list[str]:
    bullets: list[str] = []
    seen = set()
    for section in sections:
        for sentence in split_sentences(section["body"]):
            _, cleaned_sentence = parse_source_prefix(sentence)
            if is_noise_sentence(cleaned_sentence):
                continue
            if cleaned_sentence in seen:
                continue
            seen.add(cleaned_sentence)
            bullets.append(cleaned_sentence)
            if len(bullets) >= limit:
                return bullets
    return bullets


def extract_locations(text: str) -> list[str]:
    matches = []
    for pattern in [r"现居地[:：]\s*([^\n。；;]+)", r"籍贯[:：]\s*([^\n。；;]+)", r"注册地[:：]\s*([^\n。；;]+)"]:
        for match in re.finditer(pattern, text):
            value = match.group(1).strip()
            if value and value not in matches:
                matches.append(value)
    return matches[:8]


def extract_education(text: str) -> list[str]:
    rows = []
    for pattern in [r"学校[:：]\s*([^\n。；;]+)", r"专业[:：]\s*([^\n。；;]+)", r"学历[:：]\s*([^\n。；;]+)"]:
        for match in re.finditer(pattern, text):
            value = match.group(1).strip()
            if value and value not in rows:
                rows.append(value)
    return rows[:8]


def extract_company_metrics(sections: list[dict[str, Any]]) -> list[str]:
    rows = []
    for sentence in bulletize_sentences(sections, limit=20):
        if re.search(r"(估值|融资|营收|员工|团队|注册资本|量产|交付|订单|产值|市占率)", sentence):
            rows.append(sentence)
        if len(rows) >= 8:
            break
    return rows


def extract_timeline_from_sections(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    seen = set()
    for section in sections:
        items = extract_numbered_items(section["body"]) or split_sentences(section["body"])
        for item in items:
            _, cleaned = parse_source_prefix(item)
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            if len(cleaned) < 12 or not DATE_RE.search(cleaned) or is_noise_sentence(cleaned):
                continue
            if any(keyword in cleaned for keyword in ["时间", "事件", "来源", "年度", "营业收入", "净利润", "发布日期", "发布于"]):
                continue
            key = summarize_text(cleaned, limit=140)
            if key in seen:
                continue
            seen.add(key)
            match = DATE_RE.search(cleaned)
            rows.append(
                {
                    "date": match.group(0) if match else "unknown",
                    "event": cleaned,
                    "label": "fact",
                    "confidence": infer_confidence(cleaned),
                    "sources": [section["title"]],
                }
            )
            if len(rows) >= 20:
                return rows
    return rows[:20]


def extract_relationships(claims: list[dict[str, Any]], target_name: str = "", target_company: str = "") -> list[dict[str, Any]]:
    rows = []
    seen = set()
    for claim in claims:
        if claim["kind"] != "relationship":
            continue
        if not any(keyword in claim["statement"] for keyword in ["股东", "关联", "合作", "联合创始人", "副总经理", "董事长", "合伙人"]):
            continue
        if any(marker in claim["statement"] for marker in ["法定代表人/高管/股东", "信用信息查询-启信宝", "爱企查"]):
            continue
        statement = claim["statement"]
        if " - " in statement:
            statement = statement.split(" - ", 1)[-1]
        orgs = re.findall(
            r"[\u4e00-\u9fffA-Za-z0-9（）()]{2,40}(?:股份有限公司|有限责任公司|有限公司|公司|集团|大学|研究院|实验室)",
            statement,
        )
        people: list[str] = []
        for pattern in [
            r"(?:副总经理|联合创始人|董事长|合伙人|书记)[:： ]?([\u4e00-\u9fff]{2,4})(?:[,，、与和及 ]|$)",
            r"(?:与|和|及|、)([\u4e00-\u9fff]{2,4})(?:合作|联合|共同|出席|表示|担任|为)",
        ]:
            people.extend(re.findall(pattern, statement))
        filtered: list[str] = []
        for entity in orgs + people:
            entity = entity.strip("（）() ")
            if len(entity) < 2 or entity in STOP_ENTITY_TOKENS:
                continue
            if entity.endswith("的") or any(token in entity for token in STOP_ENTITY_SUBSTRINGS):
                continue
            if entity == target_name or entity == target_company:
                continue
            if target_company and target_company in entity:
                continue
            filtered.append(entity)
        unique_entities = list(dict.fromkeys(filtered))
        if not unique_entities:
            continue
        entity = " / ".join(unique_entities[:3])
        dedupe_key = (entity, claim["statement"])
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        rows.append(
            {
                "entity": entity or "unknown",
                "relationship": "linked",
                "detail": claim["statement"],
                "confidence": claim["confidence"],
                "sources": claim["sources"],
            }
        )
    return rows[:18]


def extract_behavior_patterns(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for sentence in bulletize_sentences(sections, limit=12):
        rows.append(
            {
                "pattern": sentence,
                "confidence": infer_confidence(sentence),
                "sources": ["behavior"],
            }
        )
    return rows


def extract_gaps_and_backlog(gap_sections: list[dict[str, Any]], follow_sections: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    gaps: list[dict[str, Any]] = []
    backlog: list[dict[str, Any]] = []
    for section in gap_sections:
        items = extract_numbered_items(section["body"]) or split_sentences(section["body"])
        for sentence in items:
            if len(sentence) < 18:
                continue
            gaps.append(
                {
                    "item": sentence,
                    "kind": "contradiction" if any(keyword in sentence for keyword in ["矛盾", "落差", "冲突"]) else "gap",
                    "confidence": infer_confidence(sentence),
                    "sources": [section["title"]],
                }
            )
            if len(gaps) >= 12:
                break
    for section in follow_sections + gap_sections:
        follow_text = section["body"]
        if "高价值深挖方向" in follow_text:
            follow_text = follow_text.split("高价值深挖方向", 1)[1]
        items = extract_numbered_items(follow_text) or split_sentences(follow_text)
        for sentence in items:
            if len(sentence) < 18:
                continue
            if section not in follow_sections and not any(keyword in sentence for keyword in ["需", "跟踪", "查询", "确认", "获取", "搜索", "仍", "待", "后续"]):
                continue
            backlog.append(
                {
                    "question": sentence,
                    "why_it_matters": "Improves confidence on unresolved research questions.",
                    "priority": "high" if any(keyword in sentence for keyword in ["控制权", "司法", "风险", "持股", "确认"]) else "medium",
                    "next_search": "Search stronger tier-1 or tier-2 sources for direct confirmation.",
                }
            )
            if len(backlog) >= 12:
                break
    return gaps[:12], backlog[:12]


def infer_risk_category(text: str) -> str:
    if any(keyword in text for keyword in ["立案调查", "司法", "违法", "经营异常", "公告"]):
        return "legal_regulatory"
    if any(keyword in text for keyword in ["持股", "控制权", "法定代表人", "股东"]):
        return "governance"
    if any(keyword in text for keyword in ["营收", "亏损", "融资", "回款"]):
        return "finance"
    if any(keyword in text for keyword in ["依赖", "核心团队", "单点"]):
        return "dependency"
    if any(keyword in text for keyword in ["目标", "签约", "转化", "执行"]):
        return "execution_risk"
    return "narrative_gap"


def infer_severity(text: str) -> str:
    lowered = text.lower()
    if any(keyword in lowered for keyword in HIGH_SEVERITY_KEYWORDS):
        return "high"
    if any(keyword in lowered for keyword in MEDIUM_SEVERITY_KEYWORDS):
        return "medium"
    return "low"


def extract_risks(risk_sections: list[dict[str, Any]], claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    seen = set()
    candidates: list[tuple[str, list[str]]] = []
    for sentence in bulletize_sentences(risk_sections, limit=20):
        if any(keyword in sentence for keyword in RISK_KEYWORDS):
            candidates.append((sentence, ["风险信号"]))
    for claim in claims:
        if claim["kind"] == "risk":
            candidates.append((claim["statement"], claim.get("sources", ["风险信号"])))
    for sentence, sources in candidates:
        if is_noise_sentence(sentence):
            continue
        if not any(keyword in sentence for keyword in RISK_KEYWORDS):
            continue
        key = summarize_text(sentence, limit=120)
        if key in seen or not sentence.strip():
            continue
        seen.add(key)
        rows.append(
            {
                "category": infer_risk_category(sentence),
                "severity": infer_severity(sentence),
                "label": key,
                "detail": sentence,
                "confidence": infer_confidence(sentence),
                "sources": sources[:3],
            }
        )
        if len(rows) >= 18:
            break
    return rows


def extract_sources(raw_text: str, mapped: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows = []
    seen = set()
    evidence_text = "\n".join(section["body"] for section in mapped.get("evidence_sources", []))
    combined = evidence_text or raw_text
    lowered = combined.lower()
    for tier, kind, name in SOURCE_PATTERNS:
        if name.lower() in lowered:
            key = (tier, name)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "tier": tier,
                    "name": name,
                    "kind": kind,
                    "url": "",
                    "information_value": "Mentioned in research materials",
                    "used_for": "Evidence and corroboration",
                }
            )
    for url in sorted(set(URL_RE.findall(combined)))[:20]:
        key = ("tier2", url)
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "tier": "tier2",
                "name": url.split("/")[2],
                "kind": "web",
                "url": url,
                "information_value": "Direct URL in research artifact",
                "used_for": "Evidence and follow-up",
            }
        )
    return rows


def extract_outreach(raw_text: str, outreach_sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    text = "\n".join(section["body"] for section in outreach_sections) or raw_text
    rows = []
    seen = set()

    def add_row(channel: str, value: str, effectiveness: str, notes: str) -> None:
        key = (channel, value)
        if not value or key in seen:
            return
        if channel == "email":
            local, _, domain = value.lower().partition("@")
            if domain in OUTREACH_BLOCKED_DOMAINS or local in OUTREACH_BLOCKED_LOCALPARTS:
                return
        if channel == "website":
            parsed_domain = value.lower().replace("https://", "").replace("http://", "").split("/", 1)[0]
            if parsed_domain in OUTREACH_BLOCKED_DOMAINS:
                return
        seen.add(key)
        rows.append(
            {
                "channel": channel,
                "value": value,
                "visibility": "public",
                "effectiveness": effectiveness,
                "notes": notes,
                "source": "联系与触达",
            }
        )

    for email in sorted(set(EMAIL_RE.findall(text))):
        add_row("email", email, "high", "Public email discovered in research material.")
    for phone in sorted(set(PHONE_RE.findall(text))):
        add_row("phone", phone.strip(), "medium", "Public phone discovered in research material.")
    for url in sorted(set(URL_RE.findall(text))):
        if url.endswith("/u/"):
            continue
        add_row("website", url, "medium", "Public web channel discovered in research material.")
    for domain in sorted(set(DOMAIN_RE.findall(text))):
        if domain.lower() in {"com", "cn", "ai", "net", "org"}:
            continue
        if domain.lower() in OUTREACH_BLOCKED_DOMAINS:
            continue
        if "." in domain and not any(domain in row["value"] for row in rows):
            add_row("website", domain, "medium", "Public domain discovered in research material.")
    for handle in extract_public_handles(text):
        add_row("social", handle, "low", "Public handle discovered in research material.")
    return rows[:18]


def build_payload(args: argparse.Namespace, raw_text: str) -> dict[str, Any]:
    normalized = normalize_text(raw_text)
    sections = split_sections(normalized)
    mapped = section_map(sections)
    claims = collect_claims(sections)
    overview_sections = mapped.get("overview", [])
    identity_sections = mapped.get("identity_background", [])
    career_sections = mapped.get("career_history", [])
    company_sections = mapped.get("current_company_role", [])
    digital_sections = mapped.get("digital_footprint", [])
    signal_sections = mapped.get("signal_narrative", [])
    behavior_sections = mapped.get("behavior_patterns", [])
    assessment_sections = mapped.get("comprehensive_assessment", [])
    gap_sections = mapped.get("gaps_contradictions", [])
    follow_sections = mapped.get("follow_up", [])
    risk_sections = mapped.get("risks", [])

    gaps, backlog = extract_gaps_and_backlog(gap_sections, follow_sections)
    payload = {
        "meta": {
            "name": args.name,
            "company": args.company,
            "role": args.role,
            "language": args.language,
            "scope": "public-source",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "input_path": str(args.input_path),
        },
        "executive_summary": bulletize_sentences(overview_sections or assessment_sections or company_sections, limit=8),
        "identity_background": {
            "summary": summarize_sections(identity_sections or overview_sections),
            "basic_facts": bulletize_sentences(identity_sections, limit=6),
            "aliases": extract_public_handles(raw_text)[:8],
            "locations": extract_locations(raw_text),
            "education": extract_education(raw_text),
            "identity_notes": bulletize_sentences(identity_sections, limit=6),
        },
        "career_history": {
            "summary": summarize_sections(career_sections),
            "highlights": bulletize_sentences(career_sections, limit=10),
        },
        "current_company_role": {
            "company_summary": summarize_sections(company_sections),
            "role_summary": summarize_sections(overview_sections[:1] + company_sections[:1]),
            "ownership_notes": [claim["statement"] for claim in claims if any(keyword in claim["statement"] for keyword in ["持股", "股东", "控制权", "法人"])][:8],
            "company_metrics": extract_company_metrics(company_sections or overview_sections),
            "key_entities": [row["entity"] for row in extract_relationships(claims, args.name, args.company)[:8]],
        },
        "digital_footprint": {
            "summary": summarize_sections(digital_sections),
            "channels": [row["name"] for row in extract_sources(raw_text, mapped) if row["kind"] in {"social", "video", "code"}][:12],
            "observations": bulletize_sentences(digital_sections, limit=8),
        },
        "signal_narrative": {
            "summary": summarize_sections(signal_sections or overview_sections),
            "strengths": [sentence for sentence in bulletize_sentences(signal_sections or overview_sections, limit=10) if not any(keyword in sentence for keyword in RISK_KEYWORDS)][:6],
            "concerns": [sentence for sentence in bulletize_sentences(signal_sections + risk_sections, limit=12) if any(keyword in sentence for keyword in RISK_KEYWORDS)][:6],
        },
        "relationship_notes": extract_relationships(claims, args.name, args.company),
        "behavior_patterns": extract_behavior_patterns(behavior_sections),
        "timeline": extract_timeline_from_sections(mapped.get("timeline", []) + career_sections + company_sections),
        "gaps_contradictions": gaps,
        "comprehensive_assessment": {
            "summary": summarize_sections(assessment_sections or overview_sections),
            "proven_points": [claim["statement"] for claim in claims if claim["label"] == "fact"][:8],
            "inferred_points": [claim["statement"] for claim in claims if claim["label"] == "inference"][:8],
        },
        "risk_ledger": extract_risks(risk_sections, claims),
        "source_register": extract_sources(raw_text, mapped),
        "outreach_channels": extract_outreach(raw_text, mapped.get("outreach", [])),
        "research_backlog": backlog,
        "claims": claims,
    }
    return payload


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_run_log(payload: dict[str, Any]) -> dict[str, Any]:
    claim_counter = Counter(claim["label"] for claim in payload["claims"])
    return {
        "status": "built",
        "generated_at": payload["meta"]["generated_at"],
        "target": {
            "name": payload["meta"].get("name", ""),
            "company": payload["meta"].get("company", ""),
            "role": payload["meta"].get("role", ""),
        },
        "language": payload["meta"].get("language", ""),
        "claim_count": len(payload["claims"]),
        "timeline_count": len(payload["timeline"]),
        "risk_count": len(payload["risk_ledger"]),
        "source_count": len(payload["source_register"]),
        "outreach_count": len(payload["outreach_channels"]),
        "backlog_count": len(payload["research_backlog"]),
        "claim_labels": dict(claim_counter),
    }


def main() -> int:
    args = parse_args()
    raw_text = args.input_path.read_text(encoding="utf-8")
    args.outdir.mkdir(parents=True, exist_ok=True)
    payload = build_payload(args, raw_text)
    write_json(args.outdir / "structured_report.json", payload)
    write_json(args.outdir / "run_log.json", build_run_log(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
