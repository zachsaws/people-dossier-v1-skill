# People Dossier V1

> 一个面向 Codex 的公开来源人物尽调 Skill。  
> 把“临时搜网页”升级成“可复用、可回归、可交付”的 `people dossier` 工作流。

[![GitHub Repo stars](https://img.shields.io/github/stars/zachsaws/people-dossier-v1-skill?style=flat-square)](https://github.com/zachsaws/people-dossier-v1-skill/stargazers)
[![GitHub license](https://img.shields.io/github/license/zachsaws/people-dossier-v1-skill?style=flat-square)](https://github.com/zachsaws/people-dossier-v1-skill/blob/main/LICENSE)
[![Codex Skill](https://img.shields.io/badge/Codex-Skill-0ea5e9?style=flat-square)](./SKILL.md)

如果你经常需要：

- 快速了解一个创始人 / 高管 / 操盘手
- 在会前做人物 briefing
- 给 BD / 投资 / 尽调准备一份结构化人物档案
- 把零散公开信息整理成可以复盘、可以继续追踪的 dossier

那这个 Skill 就是为这个问题做的。

## 它到底是什么

`people-dossier-v1` 不是一个“帮你写人物报告的 Prompt”。

它更接近一条稳定的研究流水线：

`target input -> retrieval -> entity resolution -> claims -> report -> evaluation`

相比一次性 prompt，它更适合长期使用，因为它：

- 有明确输入
  - `name / company / role / source pack / cache`
- 有结构化输出
  - `structured_report.json + report.md + evaluation.json`
- 有可评测质量
  - claim traceability、relationship noise、source quality
- 有可回归基准
  - golden set、source pack、normalized cache

## 为什么值得 star

这个仓库最有价值的地方，不是“会写一篇人物报告”，而是把人物研究拆成了可复用组件：

- `source pack`
  - 让同一类目标可以稳定复跑
- `normalized cache`
  - 避免每次都受搜索引擎状态影响
- `evaluation`
  - 不是只看“像不像”，而是看“能不能追溯”
- `golden set regression`
  - 改了 heuristics 以后还能知道质量有没有退

一句话说：

> 这是一个适合长期积累的人物研究 Skill，而不是一个一次性演示脚本。

## Example Output

运行后你会拿到的不是一篇散文，而是一组可复用研究产物：

```json
{
  "meta": {
    "name": "示例负责人C",
    "company": "示例智能硬件公司",
    "role": "CEO"
  },
  "executive_summary": [
    "官网将公司定位为具身智能全产业链技术服务商。",
    "公开来源显示目标与公司存在强绑定关系。"
  ],
  "source_register": [
    {
      "tier": "tier1",
      "name": "爱企查",
      "kind": "registry"
    },
    {
      "tier": "tier1",
      "name": "industry-example.ai",
      "kind": "official"
    }
  ],
  "research_backlog": [
    {
      "question": "继续核实公开履历、控制权与风险信号"
    }
  ]
}
```

同时还会生成：

- `raw_sources.json`
- `normalized_sources.json`
- `search_log.json`
- `research_notes.md`
- `structured_report.json`
- `report.md`
- `run_log.json`
- 可选 `evaluation.json`

## 30 秒安装

```bash
git clone https://github.com/zachsaws/people-dossier-v1-skill.git ~/.codex/skills/people-dossier-v1
```

如果你已经 clone 到别处，也可以直接把整个目录复制到 `~/.codex/skills/people-dossier-v1`。

## 最推荐的使用方式

### 1. 稳定模式：source pack + normalized cache

这是最推荐的路径，也是最接近“可复用 skill”的方式。

```bash
python3 scripts/run_dossier.py \
  --name "示例负责人C" \
  --company "示例智能硬件公司" \
  --role "CEO" \
  --research-goal "Validate public-source identity binding and company control signals." \
  --seed-file assets/source-packs/sparse-signal-operator.json \
  --reuse-normalized assets/cache/sparse-signal-operator.normalized.json \
  --outdir runs/example-demo \
  --max-results-per-query 0 \
  --max-pages 0
```

### 2. Live 模式：official domain + seed URL

当你没有现成 cache 时，可以这样跑：

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

### 3. 评测结果质量

```bash
python3 scripts/evaluate_dossier.py \
  runs/example-demo/structured_report.json \
  --output runs/example-demo/evaluation.json
```

### 4. 跑自带 golden set

```bash
python3 scripts/run_golden_set.py \
  --targets assets/golden-set-targets.json \
  --outdir runs/golden-set
```

## 适合谁

- 经常要做人物背景研究的人
- 想把“搜网页 + 写结论”变成结构化流程的人
- 想给 Codex 加一个稳定研究 Skill 的人
- 想积累 source pack / cache / evaluation 资产的人

## 不适合谁

- 想直接要一个完整 SaaS 产品的人
- 只想要一个单轮 prompt 的人
- 需要私有数据、受保护数据、或合规敏感调查的人

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

## 新建一个目标包

可以直接从 [`assets/source-packs/template.json`](assets/source-packs/template.json) 开始改。

## 边界说明

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
