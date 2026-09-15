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

Extraction ran as Claude Code subagents (`claude-sonnet-5`); see `.claude/skills/fde-extract/SKILL.md`.
Tests: `uv run pytest`.
