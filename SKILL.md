---
name: people-dossier-v1
description: Research a founder, executive, operator, or public business figure from public sources and produce a structured people dossier with facts, risks, sources, timeline, relationship notes, outreach paths, and follow-up questions. Use when Codex needs to do people intelligence, founder diligence, executive background research, stakeholder mapping, or a source-backed dossier from the open web.
---

# People Dossier V1

## Overview

This skill produces a source-backed people dossier from public sources. It is intentionally scoped to deliver most of the useful research effect of a Ventify-style report: structured sections, source registry, risk ledger, outreach paths, and research backlog, while stopping short of the vendor's full polished PDF product.

## Workflow

1. If you want a direct end-to-end run from target input, use `scripts/run_dossier.py`.
   - This is the main path once the skill is in normal use.
   - It writes:
     - `raw_sources.json`
     - `normalized_sources.json`
     - `search_log.json`
     - `research_notes.md`
     - `structured_report.json`
     - `report.md`
  - Command:

```bash
python3 scripts/run_dossier.py \
  --name "Target Name" \
  --company "Company Name" \
  --role "CEO" \
  --research-goal "What matters here" \
  --seed-file assets/source-packs/target.json \
  --seed-url "https://official-or-registry-source" \
  --company-domain "company.com" \
  --reuse-normalized /path/to/previous/normalized_sources.json \
  --outdir /path/to/run
```

   - `--seed-file` is optional.
   - Use it for reusable source packs that bundle:
     - aliases
     - official company domains
     - must-answer questions
     - stable seed URLs
   - `--seed-url` is optional and repeatable.
   - Use it when you already know one or more high-confidence URLs such as:
     - official company site
     - registry page
     - a strong media article
   - `--company-domain` is optional and repeatable.
   - Use it to bias retrieval toward official-site matches and upgrade official-domain rows into tier-1 official sources.
   - `--reuse-normalized` is optional.
   - Use it to bootstrap a new run from a previous `normalized_sources.json` or a curated cache when public search is unstable.

2. If you already have research notes, raw text, or an extracted PDF text artifact, build the dossier automatically.
   - Use `scripts/build_dossier.py`.
   - Command:

```bash
python3 scripts/build_dossier.py \
  /path/to/research_notes.txt \
  --name "Target Name" \
  --company "Company Name" \
  --role "CEO" \
  --outdir /path/to/run
```

3. If no research artifact exists yet, create a run folder first.
   - Use `scripts/scaffold_dossier.py` to initialize the output folder and a JSON skeleton.
   - Command:

```bash
python3 scripts/scaffold_dossier.py \
  --name "Target Name" \
  --company "Company Name" \
  --role "CEO" \
  --outdir /path/to/run
```

4. Research in this order.
   - Start with target resolution and company binding.
   - Pull hard sources first.
   - Expand into media, social, code, patent, hiring, and community only after the entity is stable.
   - Record unresolved questions instead of smoothing them over.

5. Fill or review `structured_report.json`.
   - Use `references/report-schema.md` for field definitions.
   - Use `references/source-playbook.md` for source tiers and search order.
   - Use `references/quality-bar.md` for fact vs inference rules.

6. Render the Markdown report.
   - Run:

```bash
python3 scripts/render_report.py \
  /path/to/run/structured_report.json \
  --output /path/to/run/report.md
```

7. Review before delivering.
   - Every important claim must be traceable to a source.
   - `fact`, `inference`, and `unverified` must remain separate.
   - Do not present private or protected data.
   - If a key fact is missing, keep it as a backlog item.

## Output Shape

- `structured_report.json`
- `report.md`
- `run_log.json`
- `raw_sources.json`
- `normalized_sources.json`
- `search_log.json`
- Optional research notes gathered during collection

The richer report should center on these modules:

- `Executive Summary`
- `Identity & Background`
- `Career History`
- `Current Company & Role`
- `Digital Footprint`
- `Signal Narrative`
- `Timeline`
- `Relationship Notes`
- `Behavior Patterns`
- `Gaps & Contradictions`
- `Comprehensive Assessment`
- `Risk Ledger`
- `Source Register`
- `Outreach & Research Backlog`

Read `references/template-sections.md` if you need the exact section intent.

## Research Rules

- Public-source only by default.
- Prefer high-confidence sources first:
  - Tier 1: registry, filings, official sites, government sites
  - Tier 2: mainstream media, industry media, GitHub, patents, hiring
  - Tier 3: social, video, forums, community, investor commentary
- Never collapse unsupported narrative into fact.
- Do not infer private contact data.
- Keep a visible research backlog when questions remain open.

## References

- `references/report-schema.md`
  - Read when filling or validating `structured_report.json`.
- `references/source-playbook.md`
  - Read when deciding where to search and how to tier sources.
- `references/quality-bar.md`
  - Read before finalizing claims and risk language.
- `references/template-sections.md`
  - Read when you need the exact meaning of each report module.

## Scripts

- `scripts/scaffold_dossier.py`
  - Initializes a dossier run folder and writes a JSON skeleton.
- `scripts/retrieve_sources.py`
  - Queries public search results, accepts optional source packs, seed URLs, company domains, and cached normalized sources.
- `scripts/run_dossier.py`
  - End-to-end orchestration from target input to dossier output, with optional seeded retrieval and cache reuse.
- `scripts/build_dossier.py`
  - Parses a research artifact into a populated `structured_report.json` plus a first-pass `run_log.json`.
- `scripts/render_report.py`
  - Renders a consistent Markdown dossier from `structured_report.json`.
- `scripts/evaluate_dossier.py`
  - Computes structural quality metrics on a generated dossier.
- `scripts/run_golden_set.py`
  - Runs the dossier pipeline across the golden target set.

## Evaluation

- Golden targets live at `assets/golden-set-targets.json`.
- Reusable source packs live at `assets/source-packs/`.
- Offline-stable normalized caches live at `assets/cache/`.
- The evaluation pass should track:
  - claim traceability
  - label validity
  - relationship noise
  - timeline cleanliness
  - backlog usefulness
  - outreach validity
  - risk traceability
  - source quality mix

## When This Skill Is Enough

- Founder or executive due diligence
- Public-source background research
- Stakeholder mapping
- Partner or customer intelligence
- Rapid pre-meeting research dossiers

## When This Skill Is Not Enough

- OCR-heavy or screenshot-only inputs
- Private investigation or protected data requests
- Legal, compliance, or employment decisions that require formal verification beyond public-source research
