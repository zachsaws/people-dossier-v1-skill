#!/usr/bin/env python3
"""Retrieve public web search results and normalize them for a people dossier."""

from __future__ import annotations

import argparse
import html
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urljoin, urlparse
from urllib.request import Request, urlopen


SEARCH_ENDPOINT = "https://html.duckduckgo.com/html/?q={query}"
SOGOU_SEARCH_ENDPOINT = "https://www.sogou.com/web?query={query}"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36"
RESULT_RE = re.compile(
    r'<a[^>]*class="result__a"[^>]*href="(?P<href>[^"]+)"[^>]*>(?P<title>.*?)</a>.*?'
    r'(?:<a class="result__snippet"[^>]*>(?P<snippet>.*?)</a>)?',
    re.S,
)
SOGOU_TITLE_RE = re.compile(
    r'<h3 class="vr-title[^"]*"[^>]*>.*?<a[^>]*href="(?P<href>[^"]+)"[^>]*>(?P<title>.*?)</a>.*?</h3>',
    re.S,
)
SOGOU_SUMMARY_RE = re.compile(
    r'(?:(?:id="cacheresult_summary_[^"]+")|(?:class="fz-mid[^"]*"))[^>]*>(?P<snippet>.*?)</div>',
    re.S,
)
SOGOU_DATA_URL_RE = re.compile(r'data-url="(?P<url>https?://[^"]+)"')
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
META_DESC_RE = re.compile(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_STYLE_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.I | re.S)
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
HREF_RE = re.compile(r'href=["\']([^"\']+)["\']', re.I)
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"(?:\+?86[- ]?)?(?:1[3-9]\d{9}|400[- ]?\d{3,4}[- ]?\d{3,4}|0\d{2,3}[- ]?\d{7,8})")

DOMAIN_RULES = [
    ("aiqicha.baidu.com", "tier1", "registry", "爱企查"),
    ("aiqicha.com", "tier1", "registry", "爱企查"),
    ("qcc.com", "tier1", "registry", "企查查"),
    ("tianyancha.com", "tier1", "registry", "天眼查"),
    ("qixin.com", "tier1", "registry", "启信宝"),
    ("xiniudata.com", "tier2", "company_data", "烯牛数据"),
    ("hkexnews.hk", "tier1", "filing", "HKEXnews"),
    ("neeq.com.cn", "tier1", "filing", "新三板"),
    ("cninfo.com.cn", "tier1", "filing", "巨潮资讯"),
    ("gov.cn", "tier1", "official", "政府官网"),
    ("36kr.com", "tier2", "media", "36氪"),
    ("sohu.com", "tier2", "media", "搜狐"),
    ("sina.com", "tier2", "media", "新浪"),
    ("qq.com", "tier2", "media", "腾讯"),
    ("163.com", "tier2", "media", "网易"),
    ("equalocean.com", "tier2", "media", "EqualOcean"),
    ("ofweek.com", "tier2", "media", "OFweek"),
    ("github.com", "tier2", "code", "GitHub"),
    ("patents.google.com", "tier2", "patent", "Google Patents"),
    ("weibo.com", "tier3", "social", "微博"),
    ("linkedin.com", "tier3", "social", "LinkedIn"),
    ("instagram.com", "tier3", "social", "Instagram"),
    ("t.me", "tier3", "social", "Telegram"),
    ("space.bilibili.com", "tier3", "video", "Bilibili"),
    ("bilibili.com", "tier3", "video", "Bilibili"),
    ("youtube.com", "tier3", "video", "YouTube"),
    ("zhihu.com", "tier3", "community", "知乎"),
    ("xueqiu.com", "tier3", "community", "雪球"),
    ("eastmoney.com", "tier3", "community", "东方财富"),
    ("zhipin.com", "tier2", "hiring", "BOSS直聘"),
]
REGISTRY_LIKE_KINDS = {"registry", "company_data"}


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
    parser.add_argument("--max-results-per-query", type=int, default=5)
    parser.add_argument("--max-pages", type=int, default=10)
    parser.add_argument("--outdir", type=Path, required=True)
    return parser.parse_args()


def summarize_text(text: str, limit: int = 320) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def strip_html(value: str) -> str:
    value = SCRIPT_STYLE_RE.sub(" ", value)
    value = COMMENT_RE.sub(" ", value)
    value = TAG_RE.sub(" ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def dedupe_preserve_order(values: list[str]) -> list[str]:
    seen = set()
    output = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        output.append(value)
    return output


def normalize_domain(domain: str) -> str:
    cleaned = domain.strip().lower()
    cleaned = cleaned.replace("https://", "").replace("http://", "").strip("/")
    return cleaned


def load_seed_payload(path: Path | None) -> dict[str, Any]:
    if not path or not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def company_domain_urls(domains: list[str]) -> list[str]:
    urls: list[str] = []
    common_paths = ["", "/", "/about", "/about-us", "/contact", "/news", "/company", "/team"]
    for domain in domains:
        normalized = normalize_domain(domain)
        if not normalized:
            continue
        for path in common_paths:
            urls.append(f"https://{normalized}{path}")
    return dedupe_preserve_order(urls)


def build_queries(
    name: str,
    company: str,
    role: str,
    aliases: list[str],
    research_goal: str,
    must_answer: list[str],
    company_domains: list[str],
) -> list[dict[str, str]]:
    subject = " ".join(part for part in [name, company] if part).strip()
    descriptor = " ".join(part for part in [name, company, role] if part).strip()
    queries: list[dict[str, str]] = []

    def add(bucket: str, query: str) -> None:
        query = " ".join(query.split()).strip()
        if query and query not in {row["query"] for row in queries}:
            queries.append({"bucket": bucket, "query": query})

    add("overview", f'"{name}" "{company}"')
    add("identity", f'"{name}" "{company}"')
    if role:
        add("identity", f'"{name}" "{company}" "{role}"')
    add("company", f'site:aiqicha.baidu.com "{name}" "{company}"')
    add("company", f'site:qixin.com "{name}" "{company}"')
    add("company", f'site:tianyancha.com "{name}" "{company}"')
    add("company", f'"{name}" "{company}" 法定代表人 股东')
    add("company", f'"{company}" 官网 联系方式')
    for domain in company_domains[:2]:
        normalized_domain = normalize_domain(domain)
        if not normalized_domain:
            continue
        add("company", f'site:{normalized_domain} "{company}"')
        add("company", f'site:{normalized_domain} "{name}" "{company}"')
        if role:
            add("company", f'site:{normalized_domain} "{name}" "{role}"')
    add("company", f'"{name}" "{company}" 融资 公告')
    add("media", f'site:sohu.com "{name}" "{company}"')
    add("media", f'site:mp.weixin.qq.com "{name}" "{company}"')
    add("risk", f'"{name}" "{company}" 风险 司法')
    add("risk", f'"{company}" 经营异常 诉讼')
    add("digital", f'site:weibo.com "{name}" "{company}"')
    add("digital", f'site:github.com "{name}" "{company}"')
    add("digital", f'site:linkedin.com/in "{name}" "{company}"')
    add("patent", f'"{name}" 专利')
    for alias in aliases:
        add("identity", f'"{alias}" "{company}"')
    if research_goal:
        add("goal", f"{descriptor or subject} {research_goal}")
    for question in must_answer:
        add("must_answer", f"{descriptor or subject} {question}")
    return queries


def combined_text(row: dict[str, Any]) -> str:
    fetch = row.get("fetch", {})
    return " ".join(
        part
        for part in [
            row.get("title", ""),
            row.get("snippet", ""),
            fetch.get("title", ""),
            fetch.get("meta_description", ""),
            fetch.get("text_excerpt", ""),
        ]
        if part
    )


def assess_entity_match(
    row: dict[str, Any],
    name: str,
    company: str,
    role: str,
    aliases: list[str],
    company_domains: list[str],
) -> dict[str, Any]:
    combined = combined_text(row)
    title_meta = " ".join(
        part
        for part in [
            row.get("title", ""),
            row.get("snippet", ""),
            row.get("fetch", {}).get("title", ""),
            row.get("fetch", {}).get("meta_description", ""),
        ]
        if part
    )
    fetch_text = " ".join(
        part
        for part in [
            row.get("fetch", {}).get("meta_description", ""),
            row.get("fetch", {}).get("text_excerpt", ""),
        ]
        if part
    )

    name_match = bool(name and name in combined)
    name_in_title = bool(name and name in title_meta)
    company_in_title = bool(company and company in title_meta)
    company_in_fetch = bool(company and company in fetch_text)
    role_match = bool(role and role in combined)
    alias_match = any(alias in combined for alias in aliases if alias)
    official_domain_match = normalize_domain(row.get("domain", "")) in {normalize_domain(domain) for domain in company_domains}
    notes: list[str] = []
    score = 0

    if name_match:
        score += 2
    else:
        notes.append("name_missing")
    if company_in_title:
        score += 2
    if company_in_fetch:
        score += 3
    elif company and company_in_title and row.get("fetch", {}).get("status") == "ok":
        notes.append("company_missing_in_fetch")
    elif company:
        notes.append("company_missing")
    if role_match:
        score += 1
    if alias_match:
        score += 1
    if official_domain_match:
        score += 2

    status = "weak"
    if "company_missing_in_fetch" in notes and row.get("kind") in REGISTRY_LIKE_KINDS:
        status = "ambiguous"
    elif score >= 6:
        status = "strong"
    elif score >= 4:
        status = "likely"
    elif score >= 2:
        status = "weak"
    if status in {"strong", "likely"} and not any([name_in_title, company_in_title]):
        status = "weak"
    if status == "likely" and not name_match and row.get("kind") not in {"official", "registry"}:
        status = "weak"
    if official_domain_match and company and company_in_fetch:
        status = "strong" if score >= 5 else "likely"
    if company and not company_in_title and not company_in_fetch and row.get("kind") in REGISTRY_LIKE_KINDS:
        status = "ambiguous"

    return {
        "entity_match": status,
        "match_score": score,
        "match_signals": {
            "name_match": name_match,
            "name_in_title": name_in_title,
            "company_in_title": company_in_title,
            "company_in_fetch": company_in_fetch,
            "role_match": role_match,
            "alias_match": alias_match,
            "official_domain_match": official_domain_match,
        },
        "match_notes": notes,
    }


def search_duckduckgo(query: str, max_results: int) -> list[dict[str, Any]]:
    encoded = quote(query)
    url = SEARCH_ENDPOINT.format(query=encoded)
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        html_text = urlopen(req, timeout=20).read().decode("utf-8", errors="ignore")
    except Exception:  # pragma: no cover - external engine variability
        return []
    results = []
    for rank, match in enumerate(RESULT_RE.finditer(html_text), start=1):
        href = match.group("href")
        title = strip_html(match.group("title"))
        snippet = strip_html(match.group("snippet") or "")
        resolved_url = resolve_result_url(href)
        if not resolved_url:
            continue
        results.append(
            {
                "rank": rank,
                "title": title,
                "snippet": snippet,
                "url": resolved_url,
                "redirect_url": href,
            }
        )
        if len(results) >= max_results:
            break
    return results


def search_sogou(query: str, max_results: int) -> list[dict[str, Any]]:
    encoded = quote(query)
    url = SOGOU_SEARCH_ENDPOINT.format(query=encoded)
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        html_text = urlopen(req, timeout=20).read().decode("utf-8", errors="ignore")
    except Exception:  # pragma: no cover - external engine variability
        return []
    matches = list(SOGOU_TITLE_RE.finditer(html_text))
    results: list[dict[str, Any]] = []
    for rank, match in enumerate(matches, start=1):
        next_start = matches[rank].start() if rank < len(matches) else len(html_text)
        block = html_text[match.end() : next_start]
        href = html.unescape(match.group("href"))
        title = strip_html(match.group("title"))
        snippet_match = SOGOU_SUMMARY_RE.search(block)
        data_url_match = SOGOU_DATA_URL_RE.search(block)
        snippet = strip_html(snippet_match.group("snippet")) if snippet_match else ""
        resolved_url = data_url_match.group("url") if data_url_match else resolve_result_url(href)
        if not resolved_url:
            continue
        results.append(
            {
                "rank": rank,
                "title": title,
                "snippet": snippet,
                "url": resolved_url,
                "redirect_url": href,
                "engine": "sogou",
            }
        )
        if len(results) >= max_results:
            break
    return results


def resolve_result_url(href: str) -> str:
    if href.startswith("//"):
        href = "https:" + href
    if href.startswith("/link?url="):
        return "https://www.sogou.com" + href
    parsed = urlparse(href)
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        qs = parse_qs(parsed.query)
        uddg = qs.get("uddg", [""])[0]
        return unquote(uddg) if uddg else ""
    return href


def infer_source_class(url: str, query_bucket: str) -> tuple[str, str, str]:
    domain = urlparse(url).netloc.lower()
    for needle, tier, kind, display_name in DOMAIN_RULES:
        if needle in domain:
            return tier, kind, display_name
    if query_bucket in {"digital"}:
        return "tier3", "social", domain or "web"
    if query_bucket in {"risk"}:
        return "tier2", "risk", domain or "web"
    if query_bucket in {"patent"}:
        return "tier2", "patent", domain or "web"
    if query_bucket in {"seed"}:
        return "tier2", "web", domain or "web"
    return "tier2", "web", domain or "web"


def fetch_page(url: str) -> dict[str, Any]:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=15) as response:
            final_url = response.geturl()
            body = response.read(200_000)
            content_type = response.headers.get("Content-Type", "")
        text = body.decode("utf-8", errors="ignore")
        discovered_links = []
        for href in HREF_RE.findall(text):
            href = html.unescape(href).strip()
            if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
                continue
            absolute = urljoin(final_url, href)
            parsed = urlparse(absolute)
            if parsed.scheme not in {"http", "https"}:
                continue
            discovered_links.append(absolute)
        title_match = TITLE_RE.search(text)
        meta_match = META_DESC_RE.search(text)
        stripped = strip_html(text)
        return {
            "status": "ok",
            "final_url": final_url,
            "content_type": content_type,
            "title": strip_html(title_match.group(1)) if title_match else "",
            "meta_description": strip_html(meta_match.group(1)) if meta_match else "",
            "text_excerpt": summarize_text(stripped, limit=800),
            "emails": sorted(set(EMAIL_RE.findall(stripped)))[:6],
            "phones": sorted(set(PHONE_RE.findall(stripped)))[:6],
            "links": dedupe_preserve_order(discovered_links)[:40],
        }
    except Exception as exc:  # pragma: no cover - network variability
        return {
            "status": "error",
            "final_url": url,
            "error": str(exc),
            "content_type": "",
            "title": "",
            "meta_description": "",
            "text_excerpt": "",
            "emails": [],
            "phones": [],
            "links": [],
        }


def direct_seed_rows(seed_urls: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for url in dedupe_preserve_order(seed_urls):
        domain = urlparse(url).netloc.lower()
        tier, kind, display_name = infer_source_class(url, "seed")
        rows.append(
            {
                "query": "__seed__",
                "query_bucket": "seed",
                "rank": 0,
                "title": url,
                "snippet": "",
                "url": url,
                "redirect_url": url,
                "engine": "seed",
                "tier_hint": tier,
                "kind_hint": kind,
                "source_name_hint": display_name,
                "domain": domain,
            }
        )
    return rows


def load_reused_normalized(path: Path | None) -> list[dict[str, Any]]:
    if not path or not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    rows: list[dict[str, Any]] = []
    for row in data:
        if not isinstance(row, dict) or not row.get("url"):
            continue
        rows.append(
            {
                "query": "__reused__",
                "query_bucket": "seed",
                "rank": row.get("best_rank", 0),
                "title": row.get("title", row["url"]),
                "snippet": row.get("snippet", ""),
                "url": row["url"],
                "redirect_url": row["url"],
                "engine": "reused",
                "tier_hint": row.get("tier", "tier2"),
                "kind_hint": row.get("kind", "web"),
                "source_name_hint": row.get("source_name", urlparse(row["url"]).netloc.lower()),
                "domain": row.get("domain", urlparse(row["url"]).netloc.lower()),
                "fetch": row.get("fetch", {}) if isinstance(row.get("fetch"), dict) else {},
            }
        )
    return rows


def candidate_links_from_page(row: dict[str, Any]) -> list[str]:
    fetch = row.get("fetch", {})
    source_domain = urlparse(row.get("url", "")).netloc.lower()
    candidates = []
    for link in fetch.get("links", []):
        parsed = urlparse(link)
        if parsed.netloc.lower() != source_domain:
            continue
        lowered = link.lower()
        if any(token in lowered for token in ["/about", "about-us", "/contact", "contact-us", "/news", "/company", "/team"]):
            candidates.append(link)
    return dedupe_preserve_order(candidates)[:6]


def retrieve(args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    seed_payload = load_seed_payload(args.seed_file)
    aliases = dedupe_preserve_order(
        [item.strip() for item in args.aliases.split(",") if item.strip()] + list(seed_payload.get("aliases", []))
    )
    company_domains = dedupe_preserve_order(list(args.company_domain) + list(seed_payload.get("company_domains", [])))
    normalized_company_domains = {normalize_domain(domain) for domain in company_domains if normalize_domain(domain)}
    seed_urls = dedupe_preserve_order(list(args.seed_url) + list(seed_payload.get("seed_urls", [])))
    if company_domains and (args.max_pages > 0 or not args.reuse_normalized):
        seed_urls = dedupe_preserve_order(seed_urls + company_domain_urls(company_domains))
    must_answer = dedupe_preserve_order(list(args.must_answer) + list(seed_payload.get("must_answer", [])))
    queries = build_queries(args.name, args.company, args.role, aliases, args.research_goal, must_answer, company_domains)
    started = time.time()
    raw_sources: list[dict[str, Any]] = []
    raw_sources.extend(direct_seed_rows(seed_urls))
    raw_sources.extend(load_reused_normalized(args.reuse_normalized))

    if args.max_results_per_query > 0:
        for query_row in queries:
            results = search_duckduckgo(query_row["query"], args.max_results_per_query)
            if not results:
                results = search_sogou(query_row["query"], args.max_results_per_query)
            for result in results:
                tier, kind, display_name = infer_source_class(result["url"], query_row["bucket"])
                raw_sources.append(
                    {
                        "query": query_row["query"],
                        "query_bucket": query_row["bucket"],
                        "rank": result["rank"],
                        "title": result["title"],
                        "snippet": result["snippet"],
                        "url": result["url"],
                        "redirect_url": result["redirect_url"],
                        "engine": result.get("engine", "ddg"),
                        "tier_hint": tier,
                        "kind_hint": kind,
                        "source_name_hint": display_name,
                        "domain": urlparse(result["url"]).netloc.lower(),
                    }
                )

    normalized: dict[str, dict[str, Any]] = {}
    for row in raw_sources:
        key = row["url"]
        if row["kind_hint"] in REGISTRY_LIKE_KINDS:
            key = f"{row['source_name_hint']}|{row['title']}"
        existing = normalized.get(key)
        if not existing:
            normalized[key] = {
                "url": row["url"],
                "domain": row["domain"],
                "title": row["title"],
                "snippet": row["snippet"],
                "tier": row["tier_hint"],
                "kind": row["kind_hint"],
                "source_name": row["source_name_hint"],
                "best_rank": row["rank"],
                "queries": [row["query"]],
                "query_buckets": [row["query_bucket"]],
                "search_hits": 1,
                "fetch": row.get("fetch", {}) if isinstance(row.get("fetch"), dict) else {},
            }
            continue
        existing["best_rank"] = min(existing["best_rank"], row["rank"])
        if row["query"] not in existing["queries"]:
            existing["queries"].append(row["query"])
        if row["query_bucket"] not in existing["query_buckets"]:
            existing["query_buckets"].append(row["query_bucket"])
        existing["search_hits"] += 1
        if len(row["snippet"]) > len(existing["snippet"]):
            existing["snippet"] = row["snippet"]
        if len(row["title"]) > len(existing["title"]):
            existing["title"] = row["title"]
        if not existing.get("fetch") and row.get("fetch"):
            existing["fetch"] = row["fetch"]

    normalized_sources = sorted(normalized.values(), key=lambda row: (row["best_rank"], row["tier"], row["domain"]))
    for row in normalized_sources[: args.max_pages]:
        prefetched = row.get("fetch", {})
        if prefetched.get("status") in {"ok", "cached", "manual"}:
            row["fetch"] = prefetched
        else:
            row["fetch"] = fetch_page(row["url"])
        final_url = row["fetch"].get("final_url", row["url"])
        if final_url and final_url != row["url"]:
            row["url"] = final_url
            row["domain"] = urlparse(final_url).netloc.lower()
            tier, kind, display_name = infer_source_class(final_url, row["query_buckets"][0])
            row["tier"] = tier
            row["kind"] = kind
            row["source_name"] = display_name
        fetch_title = row["fetch"].get("title", "").strip()
        if fetch_title and (row["title"].startswith("http") or len(fetch_title) > len(row["title"])):
            row["title"] = fetch_title
        fetch_meta = row["fetch"].get("meta_description", "").strip()
        if fetch_meta and not row.get("snippet"):
            row["snippet"] = fetch_meta
        if normalize_domain(row["domain"]) in normalized_company_domains:
            row["tier"] = "tier1"
            row["kind"] = "official"
            if not row.get("source_name") or row["source_name"] == row["domain"]:
                row["source_name"] = row["domain"]
    for row in normalized_sources[args.max_pages :]:
        prefetched = row.get("fetch", {})
        if prefetched.get("status") in {"ok", "cached", "manual"}:
            row["fetch"] = prefetched
        else:
            row["fetch"] = {
                "status": "skipped",
                "final_url": row["url"],
                "content_type": "",
                "title": "",
                "meta_description": "",
                "text_excerpt": "",
                "emails": [],
                "phones": [],
                "links": [],
            }
        if normalize_domain(row["domain"]) in normalized_company_domains:
            row["tier"] = "tier1"
            row["kind"] = "official"
            if not row.get("source_name") or row["source_name"] == row["domain"]:
                row["source_name"] = row["domain"]

    expanded_seed_rows = []
    for row in normalized_sources[: args.max_pages]:
        if row.get("query_buckets") and "seed" not in row["query_buckets"]:
            continue
        for link in candidate_links_from_page(row):
            tier, kind, display_name = infer_source_class(link, "seed")
            expanded_seed_rows.append(
                {
                    "url": link,
                    "domain": urlparse(link).netloc.lower(),
                    "title": link,
                    "snippet": "",
                    "tier": tier,
                    "kind": kind,
                    "source_name": display_name,
                    "best_rank": 0,
                    "queries": ["__seed_expansion__"],
                    "query_buckets": ["seed"],
                    "search_hits": 1,
                }
            )
    for row in expanded_seed_rows:
        if any(existing["url"] == row["url"] for existing in normalized_sources):
            continue
        row["fetch"] = fetch_page(row["url"])
        if normalize_domain(row["domain"]) in normalized_company_domains:
            row["tier"] = "tier1"
            row["kind"] = "official"
            row["source_name"] = row["domain"]
        normalized_sources.append(row)

    for row in normalized_sources:
        row.update(assess_entity_match(row, args.name, args.company, args.role, aliases, company_domains))

    finished = time.time()
    entity_match_counts: dict[str, int] = {}
    for row in normalized_sources:
        entity_match_counts[row["entity_match"]] = entity_match_counts.get(row["entity_match"], 0) + 1
    search_log = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target": {
            "name": args.name,
            "company": args.company,
            "role": args.role,
            "aliases": aliases,
            "research_goal": args.research_goal,
            "must_answer": must_answer,
            "seed_urls": seed_urls,
            "seed_file": str(args.seed_file) if args.seed_file else "",
            "company_domains": company_domains,
            "reuse_normalized": str(args.reuse_normalized) if args.reuse_normalized else "",
        },
        "query_count": len(queries),
        "queries": queries,
        "raw_source_count": len(raw_sources),
        "normalized_source_count": len(normalized_sources),
        "fetched_page_count": min(len(normalized_sources), args.max_pages),
        "entity_match_counts": entity_match_counts,
        "duration_seconds": round(finished - started, 3),
    }
    return raw_sources, normalized_sources, search_log


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    raw_sources, normalized_sources, search_log = retrieve(args)
    write_json(args.outdir / "raw_sources.json", raw_sources)
    write_json(args.outdir / "normalized_sources.json", normalized_sources)
    write_json(args.outdir / "search_log.json", search_log)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
