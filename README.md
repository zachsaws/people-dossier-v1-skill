# People Dossier V1

Public-source people dossier skill for Codex.

This repository packages a reusable skill that can:

- research a founder, executive, operator, or public business figure
- bootstrap from live search, seed URLs, source packs, or cached normalized sources
- produce a structured dossier in `JSON + Markdown`
- evaluate output quality with repeatable golden-set regression

The skill is designed for `skill-first` usage, not full productization.

## What You Get

- `SKILL.md`
  - the skill entry and workflow
- `scripts/`
  - retrieval, build, render, evaluate, and regression scripts
- `references/`
  - report schema, source playbook, quality bar, section intent
- `assets/source-packs/`
  - reusable input packs for stable runs
- `assets/cache/`
  - normalized source caches for offline-stable regression

## Install

Clone this repository directly into your Codex skills directory:

```bash
git clone https://github.com/<your-account>/people-dossier-v1-skill.git ~/.codex/skills/people-dossier-v1
```

If you already cloned it elsewhere, copy the folder into `~/.codex/skills/people-dossier-v1`.

## Trigger

In Codex, ask for:

- `Use $people-dossier-v1 to research a person from public sources`
- `Generate a people dossier for <name>`

## Quick Start

### 1. Stable mode: source pack + normalized cache

```bash
python3 scripts/run_dossier.py \
  --name "管明尧" \
  --company "智身科技" \
  --role "CEO" \
  --research-goal "Validate public-source identity binding and company control signals." \
  --seed-file assets/source-packs/sparse-signal-operator.json \
  --reuse-normalized assets/cache/sparse-signal-operator.normalized.json \
  --outdir runs/guan-demo \
  --max-results-per-query 0 \
  --max-pages 0
```

### 2. Seeded live mode

```bash
python3 scripts/run_dossier.py \
  --name "Target Name" \
  --company "Company Name" \
  --role "CEO" \
  --research-goal "Generate a public-source dossier." \
  --company-domain "company.com" \
  --seed-url "https://company.com/" \
  --seed-url "https://registry-or-media-page" \
  --outdir runs/target-live
```

### 3. Evaluate a run

```bash
python3 scripts/evaluate_dossier.py \
  runs/guan-demo/structured_report.json \
  --output runs/guan-demo/evaluation.json
```

### 4. Run the bundled golden set

```bash
python3 scripts/run_golden_set.py \
  --targets assets/golden-set-targets.json \
  --outdir runs/golden-set
```

## Outputs

Each run writes:

- `raw_sources.json`
- `normalized_sources.json`
- `search_log.json`
- `research_notes.md`
- `structured_report.json`
- `report.md`
- `run_log.json`
- optional `evaluation.json`

## Create a New Target Pack

Use [`assets/source-packs/template.json`](assets/source-packs/template.json) as the starting point for a new person.

## Safety / Scope

- public-source only
- no private or protected data
- no employment, legal, or compliance decisions without independent formal verification

## Notes

- The most reliable path is `source pack + normalized cache`.
- Pure live search depends on public search engines and is inherently less stable.
- The skill uses only the Python standard library.

## License

MIT
