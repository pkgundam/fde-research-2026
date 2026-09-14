# FDE Skills Roadmap — agent notes

Pipeline: `uv run python main.py discover | collect | prepare | validate | aggregate | render`.
Extraction between `prepare` and `validate` is done in-session: see `.claude/skills/fde-extract/SKILL.md`.
Never re-fetch sources without `--refresh`; raw responses are cached under `data/raw/`.
Spec: `docs/superpowers/specs/2026-09-14-fde-skills-roadmap-design.md`. Plan: `docs/superpowers/plans/2026-09-14-fde-skills-roadmap.md`.
