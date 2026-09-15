# FDE Skills Roadmap

What Forward Deployed Engineer roles actually ask for — a skills report built from 276 FDE job postings (first published in the 12 months before collection) across 151 companies.

**Report:** open [`fde-roadmap.html`](fde-roadmap.html) in a browser. It is a single self-contained file (inline CSS/JS; Chart.js loaded from cdnjs).

## What it shows

1. The FDE lifecycle every posting describes (discover → scope → prototype → integrate → deploy → evaluate → improve → feed back)
2. Most requested skills, coloured by capability cluster
3. Frequency vs criticality — how often a skill is asked for vs how often it *is the job* — as a quadrant panel and a scatter
4. Coverage of six capability clusters
5. A staged learning roadmap (Python for FDE, AI application engineering, integration & deployment, customer delivery & communication)
6. Market insights: seniority, years, travel, customer-facing intensity, skill stacks that travel together, startup vs enterprise, and what FDE demands that AI-engineer roadmaps do not teach
7. Four proof projects that exercise all six clusters
8. Methodology and limitations

## How it was built

Postings were collected from public job-board APIs only (Greenhouse, Lever, Ashby, Hacker News "Who is hiring?" via Algolia, Remotive, Arbeitnow — no LinkedIn or Indeed), de-duplicated, segmented into responsibilities / requirements / nice-to-have, and passed once each to Claude Sonnet 5 with a fixed prompt and a closed 81-skill taxonomy (`taxonomy.yaml`). Because extraction was restricted to that taxonomy, a separate open-vocabulary pass on a 30-posting sample estimates what it misses (88% of freely named skills map to a node; the main gap is AI coding assistants). Aggregation and rendering are deterministic Python. The full method, numbers and limitations are in section 8 of the report.

Extraction ran inside Claude Code as subagents (Claude Sonnet 5 via the `sonnet` alias) rather than through the API; the runbook is `.claude/skills/fde-extract/SKILL.md`.

## Reproducing

    uv sync
    uv run python main.py discover   # resolve company ATS boards (cached)
    uv run python main.py collect    # fetch + dedupe -> data/processed/postings.jsonl
    uv run python main.py prepare    # render one extraction prompt per posting
    # extraction: run /fde-extract in Claude Code (see .claude/skills/fde-extract/SKILL.md)
    uv run python main.py validate
    uv run python main.py aggregate  # -> data/processed/report_data.json
    uv run python main.py render     # -> fde-roadmap.html   (--fixture renders sample data)

Every HTTP GET is cached under `data/raw/` and is never re-fetched unless you pass `--refresh`.

Tests: `uv run pytest`

## What is and is not in this repository

- Tracked: the pipeline, the taxonomy, the authored prose (`render/content.yaml`), the per-posting skill extractions with short evidence quotes (`data/processed/extractions/`), the aggregated `report_data.json`, and the rendered report. `render` reproduces the report from `report_data.json` without any network access.
- Not tracked: raw API responses (`data/raw/`) and the collected posting texts (`data/processed/postings.jsonl`). Job descriptions belong to the employers that wrote them; run `collect` to rebuild the file locally (a few minutes, no credentials needed). `aggregate` needs it.

Design notes and the implementation plan are under `docs/superpowers/`.
