"""Render one extraction prompt per posting and maintain the pending/done manifest."""
from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Template

from extract import schema, taxonomy
from extract.segment import Segments, segment
from sources.base import PROCESSED_DIR, Posting
from sources.collect import load_postings  # re-exported for monkeypatching in tests

PROMPTS_DIR = PROCESSED_DIR / "prompts"
EXTRACTIONS_DIR = PROCESSED_DIR / "extractions"
MANIFEST = PROMPTS_DIR / "manifest.json"
TEMPLATE = Path(__file__).resolve().parent / "prompt.md"


def render_prompt(posting: Posting, segments: Segments, tx: taxonomy.Taxonomy) -> str:
    example = {"posting_id": posting.id, "skills": [{"canonical": "python", "section": "requirement", "evidence": "Strong proficiency in Python"}],
               "seniority": "senior", "years_required": 5, "travel_expectation": "occasional", "customer_facing_intensity": 4,
               "responsibility_verbs": ["build", "deploy", "scope", "integrate", "present"], "segmentation_quality": segments.quality}
    return Template(TEMPLATE.read_text()).render(posting=posting, segments=segments, taxonomy=tx,
                                                 schema_json=json.dumps(example, indent=2))


def _valid_extraction(pid: str) -> bool:
    f = EXTRACTIONS_DIR / f"{pid}.json"
    if not f.exists():
        return False
    try:
        return schema.parse_extraction(f.read_text()).posting_id == pid
    except Exception:
        return False


def run(limit: int | None = None) -> int:
    tx = taxonomy.load()
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    EXTRACTIONS_DIR.mkdir(parents=True, exist_ok=True)
    postings = load_postings()
    if limit is not None:
        postings = postings[:limit]
    pending, done = [], []
    for p in postings:
        (PROMPTS_DIR / f"{p.id}.md").write_text(render_prompt(p, segment(p.full_text), tx))
        (done if _valid_extraction(p.id) else pending).append(p.id)
    MANIFEST.write_text(json.dumps({"pending": pending, "done": done}, indent=2))
    print(f"prompts written: {len(postings)}  pending: {len(pending)}  done: {len(done)}")
    return len(postings)
