---
name: fde-extract
description: Run the FDE posting skill-extraction step in-session — dispatch subagents over pending prompt files, then validate. Use after `python main.py prepare` and whenever `prompts/manifest.json` has pending ids.
---

# fde-extract

Extraction is the one pipeline step without an API key. It is done by subagents reading rendered prompt files and writing JSON files. Everything else is deterministic Python.

## Preconditions
- `uv run python main.py prepare [--limit N]` has been run; `data/processed/prompts/manifest.json` exists.
- `taxonomy.yaml` has been approved by the user.
- Prompts contain no code fences; extraction files must be raw JSON. A stray ```json fence is tolerated by the validator but should not be produced.

## Procedure
1. Read `data/processed/prompts/manifest.json`. If `pending` is empty, stop.
2. Split `pending` into batches of 15 ids.
3. For every batch, dispatch ONE subagent (Agent tool, `subagent_type: "general-purpose"`, `model: "sonnet"`) — dispatch all batches in a single message so they run in parallel. Prompt, verbatim, with the id list substituted:

   > You are performing structured data extraction. For EACH id in this list: {ids}
   > 1. Read `data/processed/prompts/{id}.md` in full.
   > 2. Follow its instructions exactly and produce the JSON object it asks for.
   > 3. Write that JSON (and nothing else — no markdown fences, no commentary) to `data/processed/extractions/{id}.json`.
   > Use only `canonical` names that appear in the prompt's taxonomy. Do not skip ids. Do not read any other files. When finished, reply with the list of ids written and nothing else.

4. When all subagents return, run `uv run python main.py validate`.
5. If `pending` is still non-empty (invalid or missing files), repeat steps 2–4 for those ids only. After two retries, show the user the remaining ids.
6. Show the user the validate summary and the top-25 rejects. Rejects that recur ≥ 3 times are candidates for new aliases or nodes in `taxonomy.yaml`; after editing the taxonomy, re-run `prepare` (prompts embed the taxonomy) and re-extract only postings whose rejects were affected (`grep -l` the canonical in `rejects.log`), then `validate` again.

## Notes
- Model name for Methodology: `claude-sonnet-5` (set in `aggregate/build_report_data.py` META_MODEL).
- Never edit an extraction JSON by hand; fix the prompt/taxonomy and re-run instead.
