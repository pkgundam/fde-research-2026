# FDE Skills Roadmap

Pipeline that turns live Forward Deployed Engineer postings into a skills report (`fde-roadmap.html`).

    uv sync
    uv run python main.py discover   # find ATS boards (cached)
    uv run python main.py collect    # fetch + dedupe -> data/processed/postings.jsonl
    uv run python main.py prepare    # render extraction prompts
    # extraction: run /fde-extract in Claude Code (see .claude/skills/fde-extract/SKILL.md)
    uv run python main.py validate
    uv run python main.py aggregate
    uv run python main.py render     # -> fde-roadmap.html  (--fixture for sample data)

Sources: Greenhouse, Lever, Ashby, HN Who Is Hiring, Remotive, Arbeitnow. Taxonomy: `taxonomy.yaml`.
Design: `docs/superpowers/specs/2026-09-14-fde-skills-roadmap-design.md`.

`collect` never re-fetches a cached key unless `--refresh` is passed explicitly; raw responses live under `data/raw/`.
Extraction ran as Claude Sonnet 5 via Claude Code's `sonnet` alias, dispatched as subagents rather than through the API; see `.claude/skills/fde-extract/SKILL.md`.
`data/processed/extractions/` and `data/processed/prompts/manifest.json` are tracked in git, so `aggregate` and `render` reproduce `fde-roadmap.html` from the repository without re-running extraction.
Tests: `uv run pytest`.
