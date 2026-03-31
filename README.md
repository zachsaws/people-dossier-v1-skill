# People Dossier V1

> 一个面向 Codex 的公开来源人物尽调 Skill。  
> 用更稳的 `source pack + normalized cache + evaluation` 路线，把人物研究从“临时搜资料”变成“可复用、可回归、可交付”的 dossier 工作流。

[![GitHub Repo stars](https://img.shields.io/github/stars/zachsaws/people-dossier-v1-skill?style=flat-square)](https://github.com/zachsaws/people-dossier-v1-skill/stargazers)
[![GitHub license](https://img.shields.io/github/license/zachsaws/people-dossier-v1-skill?style=flat-square)](https://github.com/zachsaws/people-dossier-v1-skill/blob/main/LICENSE)
[![Codex Skill](https://img.shields.io/badge/Codex-Skill-0ea5e9?style=flat-square)](./SKILL.md)

## 中文介绍

`people-dossier-v1` 是一个专门给 Codex 用的人物研究 Skill，目标不是做“产品壳”，而是先把研究能力本身做稳。

它适合这些场景：

- 创始人 / 高管 / 操盘手的公开背景研究
- 会前人物 briefing
- BD / 投资 / 尽调前的 stakeholder mapping
- 从零散公开来源里整理出结构化 dossier

它解决的核心问题是：

- 不再只靠一次性搜索结果拼长文
- 把来源、结论、风险、缺口、后续问题拆成结构化对象
- 支持 `live retrieval`、`seeded retrieval`、`offline-stable regression`
- 能稳定输出 `JSON + Markdown`，并自带评测与 golden set

一句话理解：

> 这不是一个“帮你写人物报告的 Prompt”，而是一套“人物研究流水线 Skill”。

## 核心能力

- `retrieval`
  - 支持 live search、seed URL、official domain、source pack、normalized cache
- `entity resolution`
  - 对人名、公司名、别名、官方域名做匹配打分
- `structured output`
  - 输出 `structured_report.json`、`report.md`、`search_log.json`、`run_log.json`
- `quality evaluation`
  - 输出 `evaluation.json`
  - 跟踪 claim traceability、relationship noise、source quality 等指标
- `golden set regression`
  - 自带样例目标、source pack、cache 和汇总脚本

## 仓库结构

- `SKILL.md`
  - Skill 入口和工作流说明
- `scripts/`
  - 检索、构建、渲染、评测、回归脚本
- `references/`
  - report schema、source playbook、quality bar、section template
- `assets/source-packs/`
  - 可复用输入包
- `assets/cache/`
  - 离线稳定回归用的 normalized source cache

## 安装

直接克隆到 Codex 技能目录：

```bash
git clone https://github.com/zachsaws/people-dossier-v1-skill.git ~/.codex/skills/people-dossier-v1
```

如果你已经 clone 到别处，也可以直接把整个目录复制到 `~/.codex/skills/people-dossier-v1`。

## 使用方式

在 Codex 里可以直接说：

- `Use $people-dossier-v1 to research a person from public sources`
- `Generate a people dossier for <name>`

## 快速开始

### 1. 最稳的用法：source pack + normalized cache

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

### 2. 次稳的用法：official domain + seed URL

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

### 3. 评测输出质量

```bash
python3 scripts/evaluate_dossier.py \
  runs/guan-demo/structured_report.json \
  --output runs/guan-demo/evaluation.json
```

### 4. 跑自带 golden set

```bash
python3 scripts/run_golden_set.py \
  --targets assets/golden-set-targets.json \
  --outdir runs/golden-set
```

## 输出内容

每次运行会产出：

- `raw_sources.json`
- `normalized_sources.json`
- `search_log.json`
- `research_notes.md`
- `structured_report.json`
- `report.md`
- `run_log.json`
- 可选 `evaluation.json`

## 新建一个目标包

可以直接从 [`assets/source-packs/template.json`](assets/source-packs/template.json) 开始改。

## 适用边界

- 仅限公开来源
- 不碰私有或受保护数据
- 不适合作为法律、合规、雇佣决策的唯一依据

## 注意

- 最可靠的路径是 `source pack + normalized cache`
- 纯 live search 依赖公开搜索引擎，天然不稳定
- 当前脚本只依赖 Python 标准库
- 当前仓库提供的是 `skill-first` 方案，不是完整对外产品

## English

`people-dossier-v1` is a Codex skill for public-source people intelligence. It turns ad-hoc person research into a repeatable pipeline with retrieval, entity scoring, structured dossier output, evaluation, and golden-set regression.

## License

MIT
