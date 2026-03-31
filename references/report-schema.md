# People Dossier JSON Schema

Use this file when filling `structured_report.json`.

## Top-level shape

```json
{
  "meta": {},
  "executive_summary": [],
  "identity_background": {},
  "career_history": {},
  "current_company_role": {},
  "digital_footprint": {},
  "signal_narrative": {},
  "relationship_notes": [],
  "behavior_patterns": [],
  "timeline": [],
  "gaps_contradictions": [],
  "comprehensive_assessment": {},
  "risk_ledger": [],
  "source_register": [],
  "outreach_channels": [],
  "research_backlog": [],
  "claims": []
}
```

## Fields

### `meta`

- `name`
- `company`
- `role`
- `language`
- `scope`
- `generated_at`
- `input_path`

### `executive_summary[]`

- Short bullets for the most decision-relevant findings

### `identity_background`

- `summary`
- `basic_facts[]`
- `aliases[]`
- `locations[]`
- `education[]`
- `identity_notes[]`

### `career_history`

- `summary`
- `highlights[]`

### `current_company_role`

- `company_summary`
- `role_summary`
- `ownership_notes[]`
- `company_metrics[]`
- `key_entities[]`

### `digital_footprint`

- `summary`
- `channels[]`
- `observations[]`

### `signal_narrative`

- `summary`
- `strengths[]`
- `concerns[]`

### `relationship_notes[]`

- `entity`
- `relationship`
- `detail`
- `confidence`
- `sources`

### `behavior_patterns[]`

- `pattern`
- `confidence`
- `sources`

### `timeline[]`

- `date`
- `event`
- `label`
  - `fact`
  - `inference`
  - `unverified`
- `confidence`
  - `high`
  - `medium`
  - `low`
- `sources`

### `gaps_contradictions[]`

- `item`
- `kind`
  - `gap`
  - `contradiction`
- `confidence`
- `sources`

### `comprehensive_assessment`

- `summary`
- `proven_points[]`
- `inferred_points[]`

### `risk_ledger[]`

- `category`
  - `legal_regulatory`
  - `governance`
  - `finance`
  - `dependency`
  - `execution_risk`
  - `narrative_gap`
- `severity`
  - `high`
  - `medium`
  - `low`
- `label`
- `detail`
- `confidence`
- `sources`

### `source_register[]`

- `tier`
  - `tier1`
  - `tier2`
  - `tier3`
- `name`
- `kind`
- `url`
- `information_value`
- `used_for`

### `outreach_channels[]`

- `channel`
- `value`
- `visibility`
  - `public`
- `effectiveness`
  - `high`
  - `medium`
  - `low`
- `notes`
- `source`

### `research_backlog[]`

- `question`
- `why_it_matters`
- `priority`
  - `high`
  - `medium`
  - `low`
- `next_search`

### `claims[]`

- `section`
- `statement`
- `label`
  - `fact`
  - `inference`
  - `unverified`
- `kind`
  - `general`
  - `timeline`
  - `relationship`
  - `risk`
- `confidence`
- `sources`
