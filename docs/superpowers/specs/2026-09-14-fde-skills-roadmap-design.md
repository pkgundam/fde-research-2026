# FDE Skills Roadmap — Design Spec

**Date:** 2026-09-14
**Source requirement:** `req.md`
**Status:** approved in brainstorming; ready for implementation planning

## 1. Goal

A data pipeline that collects current Forward Deployed Engineer (FDE) job
postings from permissively-licensed sources, extracts structured skill
requirements against a closed taxonomy, aggregates frequency / criticality /
co-occurrence, and renders a single self-contained `fde-roadmap.html` report
styled after OwlHub's design tokens. The report is intended for public
publication (LinkedIn), so the methodology must be transparent and reproducible.

## 2. Hard constraints (from req.md)

- Do not scrape LinkedIn, Indeed, or any site that blocks automated access.
  Sources are limited to: Greenhouse, Lever, Ashby board APIs; HN "Who Is
  Hiring" via Algolia; Remotive; Arbeitnow. **Adzuna is skipped** (requires
  registration; mostly re-lists ATS postings). Listed as "not used" in
  Methodology.
- Output is ONE self-contained HTML file: inline CSS/JS, no build step, no
  external assets except `<script>` tags from a CDN. No web-font downloads.
- Every raw fetch is cached to disk in `data/raw/`; a source is never re-hit
  during development unless `--refresh` is passed explicitly.
- Taxonomy is approved by the user before any extraction runs.
- A 10-posting extraction sample is approved by the user before the full run.
- HTML is built against fixture data first so rendering is never blocked on
  collection.
- Section 7 of the HTML has a clearly marked placeholder div for one user-written
  sentence; no promotional copy is authored by the assistant.

## 3. Decisions taken during brainstorming

| # | Decision | Choice | Why |
|---|---|---|---|
| 1 | Style guide | `owl-hub/src/app/owlhub-tokens.css` + `docs/features/design-system-migration.md` | Brand-guide `.md` files are not in the repo; tokens CSS is the concrete source of truth |
| 2 | LLM extraction backend | **In-session subagents** driven by a `SKILL.md` runbook; no API key | User has no API key; cost of API route (~$2–10) is small but not zero; pipeline stays reproducible via fixed prompt files + programmatic validation |
| 3 | Adzuna | Skip | Requires signup; low unique yield after dedupe |
| 4 | Repo location | This directory (`owl-hub-roadmaps/`), `git init`, uv + Python 3.12 | — |
| 5 | Inter-step data | JSONL / JSON files per step, Pydantic models at boundaries | Inspectable, re-runnable, matches cache-everything rule |
| 6 | HTML generation | Jinja2 template + inline JSON blob + Chart.js (+ annotation plugin) from cdnjs | Readable template, one data blob, fixture and real data share a shape |
| 7 | JD segmentation | Heuristic regex on section headers in Python; extraction prompt tags per mention and infers when headers are missing | One LLM pass per posting, not two |
| 8 | HN window | Last 4 monthly "Who Is Hiring" threads | ATS boards are live; HN needs a bound |
| 9 | Gap baseline | Hardcoded set from roadmap.sh "AI Engineer" roadmap + common LLM-bootcamp syllabi, cited in code | Spec asks for a hardcoded list |

## 4. Repository layout

```
owl-hub-roadmaps/
  pyproject.toml            # uv; Python 3.12; httpx, pydantic, pyyaml, jinja2, pytest
  main.py                   # CLI: discover | collect | prepare | validate | aggregate | render | all-offline
  taxonomy.yaml             # closed vocabulary (user-approved)
  sources/
    base.py                 # Posting model, cached fetch helper, title filter, normalizers
    companies.yaml          # candidate company names; resolved slugs written back under `resolved:`
    greenhouse.py lever.py ashby.py hn.py remotive.py arbeitnow.py
  extract/
    segment.py              # header-regex JD segmentation
    prompt.md               # Jinja-templated extraction prompt (single source of truth)
    prepare.py              # renders prompts/{id}.md + prompts/manifest.json
    schema.py               # Extraction Pydantic model + JSON schema export
    validate.py             # taxonomy validation, rejects.log, manifest update
  aggregate/
    frequency.py criticality.py cooccurrence.py market.py gap.py
    build_report_data.py    # assembles report_data.json
  render/
    template.html.j2
    render.py
    content.yaml            # roadmap tracks, proof projects, insight prose (authored after real data)
    fixtures/report_data.fixture.json
  data/
    raw/{source}/{key}.json           # verbatim HTTP body + fetched_at
    processed/postings.jsonl
    processed/prompts/{id}.md
    processed/prompts/manifest.json   # ids still needing a valid extraction
    processed/extractions/{id}.json
    processed/rejects.log
    processed/report_data.json
  .claude/skills/fde-extract/SKILL.md # runbook for the in-session extraction step
  tests/
  docs/superpowers/specs/             # this file
  fde-roadmap.html                    # output
```

## 5. Data contracts

### Posting (`sources/base.py`)
`id` (sha1 of `source:source_id`), `title`, `company`, `company_size_hint`
(`startup|scaleup|enterprise|unknown`, from a hardcoded map), `location`,
`remote_flag: bool`, `travel_mentioned: bool` (regex over full text),
`seniority_raw` (as written in title), `url`, `posted_date` (ISO or null),
`full_text` (HTML stripped), `source`.

### Extraction (`extract/schema.py`)
```
posting_id: str
skills: [{canonical: str, section: responsibility|requirement|nice_to_have, evidence: str (<=12 words)}]
seniority: junior|mid|senior|staff_plus|unspecified
years_required: int | null
travel_expectation: none|occasional|frequent|unspecified
customer_facing_intensity: 1..5
responsibility_verbs: [str] (exactly 5)
segmentation_quality: header|inferred
```

### report_data.json
One object with keys `meta`, `skills`, `scatter`, `clusters`, `stacks`,
`market`, `gap`. The fixture file has the identical shape; `render` cannot
distinguish fixture from real data.

## 6. Step 1 — Collect

- `discover`: for every name in `companies.yaml` (≈70 AI-native companies
  including the ones named in req.md), try 2–3 slug variants against all three
  ATS APIs; write resolving slugs to `resolved:`; cache every probe; log
  unresolved without retry.
- Greenhouse (`content=true`), Lever (`mode=json`), Ashby: pull whole board per
  resolved company, then title-filter locally against the seven title patterns
  from req.md plus "FDE" / "Forward-Deployed" variants (case-insensitive).
- HN: Algolia `search_by_date` over comments in the last 4 "Who Is Hiring"
  threads matching any title pattern; parse the conventional first line
  `Company | Role | Location | …`; `company_size_hint = startup`.
- Remotive, Arbeitnow: keyword search endpoints, local title filter.
- Normalize: `normalized_company` = lowercase minus `inc|labs|ai|.com`;
  `normalized_title` = lowercase minus seniority words, parentheticals, req IDs.
- Dedupe on `(normalized_company, normalized_title)`; keep the row with the
  longest `full_text`.
- Emit per-source counts (fetched / matched / kept) for Methodology.
- If under 300 after dedupe: extend `companies.yaml` and re-run `discover`.

## 7. Step 2 — Extract

### taxonomy.yaml
Six clusters (`software_foundations`, `ai_application_engineering`,
`data_and_integrations`, `deployment_and_operations`, `customer_delivery`,
`product_thinking_and_communication`), each a list of
`{canonical, aliases[], definition}`. ~80–100 skills. Generic aliases (e.g.
"cloud") map to a generic node (`cloud_platforms`), not to a specific vendor.
**User approves before extraction.**

### prepare
`segment.py` splits `full_text` into `responsibilities / requirements /
nice_to_have / other` using header regexes; sets `segmentation_quality`.
`prompt.md` receives: full taxonomy (canonical + aliases + definitions),
segmented JD, JSON schema, and rules (only canonical names; tag by section;
infer when headers missing; ≤12-word evidence quote per skill; never invent).
Writes `prompts/{id}.md` and `prompts/manifest.json`.

### extraction (in-session)
`.claude/skills/fde-extract/SKILL.md`: read manifest; dispatch subagents
pinned to Sonnet in batches of 15 postings; each writes `extractions/{id}.json`
only; then run `validate`. Re-dispatch only ids still in the manifest.

### validate
Every `skills[].canonical` must exist in the taxonomy; unknowns go to
`rejects.log` (posting id, section, evidence). Schema failures put the id back
in the manifest. Output counts + rejects for joint review; frequent rejects
become aliases or new nodes, then only affected postings re-run.

### Checkpoints
1. taxonomy.yaml approved.
2. 10-posting sample: JSONs shown next to their JDs plus rejects → approved.
3. Full run.

## 8. Step 3 — Aggregate

Pure functions over `list[Extraction]`:

- **frequency**: per skill, postings mentioning it (once per posting) / N;
  per cluster, share of postings with ≥1 skill in the cluster.
- **criticality**: per skill, `responsibility` mentions / all mentions;
  `low_n` flag when < 5 mentions.
- **co-occurrence**: for skill pairs with both ≥ 5% frequency,
  `lift = P(A∧B)/(P(A)P(B))`; keep `lift > 1.2` and support ≥ 8 postings;
  greedy modularity clustering (no networkx), 3–4 communities, each named
  from top-3 members (names shown to user before render).
- **market**: seniority distribution, years histogram, travel expectation,
  customer-facing intensity distribution, top-15 responsibility verbs;
  startup-vs-enterprise deltas > 15 pt emitted as a list for prose only.
- **gap**: `STANDARD_ROADMAP_SKILLS` hardcoded set; output FDE skills with
  frequency ≥ 20% not in the set, sorted by frequency.
- **scatter outliers**: top-3 by frequency with criticality in bottom
  quartile; top-3 by criticality (n ≥ 8) with frequency in bottom half.
- **meta**: N, date range, per-source counts, segmentation split, reject count.

## 9. Step 4 — Render

Single Jinja2 template, eight `<section id>` blocks in req.md order, data
inlined as `<script id="data" type="application/json">`, one inline script
builds charts. External: `chart.js` and `chartjs-plugin-annotation` from
cdnjs, exact versions pinned.

Style (from `owlhub-tokens.css`): canvas `#fcfdfe`, text `#18324a`, secondary
`#71869a`, violet `#3f00ff`, readable teal `#137a6c` (bright teal `#32c6b0`
only on fills), 8px spacing rhythm, borders over shadows, 680px prose measure,
`prefers-reduced-motion` respected. `font-family: Inter, system-ui, …` with no
download. Six cluster colors (violet, teal, navy, blue, amber, slate), always
paired with a text label.

Sections:
1. Flow diagram: CSS flex row of 8 nodes with SVG arrows; wraps on mobile.
2. Top-30 horizontal bars, colored by cluster.
3. Scatter: `min-height: 70vh`; quadrant lines at medians; quadrant labels via
   annotation plugin; outlier callouts; `low_n` at 40% opacity; hover shows n
   and an evidence example.
4. Six cluster cards with coverage % and member chips.
5. Staged tracks as vertical steppers; Python track opens with a "Skip:" block.
6. Four small distributions + verb list + startup-vs-enterprise prose.
7. Four project cards + `<div id="author-note" class="placeholder">` with a
   visible "YOUR ONE SENTENCE HERE" marker.
8. Methodology from `meta`, including "Adzuna: not used" and stated limitations.

Roadmap tracks, proof-project specs and insight prose live in
`render/content.yaml`, authored after real aggregates exist and shown to the
user before final render.

## 10. Testing

- pytest per source module against recorded raw fixtures in `tests/fixtures/`.
- `segment` against 6 JD header shapes.
- `validate` against valid / schema-invalid / unknown-skill JSONs.
- Every aggregate function against a 6-posting synthetic set with
  hand-computed expected values.
- `render` smoke test: renders from fixture; all 8 section ids and the
  placeholder present; file < 1.5 MB.
- Manual: Chrome screenshots at 1280px and 390px before hand-off.

## 11. Order of work

1. Scaffold, `git init`, fixture, template + charts (fake report viewable day one)
2. `taxonomy.yaml` → user approval
3. Sources, `discover`, `collect` → per-source counts
4. `prepare`, `validate`, SKILL.md → 10-posting sample → user approval
5. Full extraction → rejects review → alias fixes → re-run affected
6. Aggregate on real data → stack names → shown to user
7. `content.yaml` → final render → mobile check
8. Methodology numbers, final file

## 12. Stated limitations (to appear in Methodology)

- Sample skews toward companies with public ATS boards and HN presence.
- HN postings have weaker structure; company size for them is assumed startup.
- Extraction is LLM-based; evidence quotes are provided but not human-verified
  for every posting.
- Startup-vs-enterprise comparisons are directional only.
