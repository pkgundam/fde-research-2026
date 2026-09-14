# FDE Skills Roadmap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python pipeline that collects 300+ Forward Deployed Engineer postings from permissive job APIs, extracts skills against a closed taxonomy (in-session LLM step), aggregates frequency/criticality/co-occurrence, and renders one self-contained `fde-roadmap.html`.

**Architecture:** Each pipeline step is a `main.py` subcommand that reads files from the previous step and writes files for the next (`data/raw/` → `postings.jsonl` → `prompts/*.md` → `extractions/*.json` → `report_data.json` → HTML). Pydantic models guard every boundary. The only non-Python step is extraction, run by subagents via `.claude/skills/fde-extract/SKILL.md` and verified by `validate`.

**Tech Stack:** Python 3.12, uv, httpx, pydantic v2, pyyaml, jinja2, pytest; Chart.js 4.4.1 + chartjs-plugin-annotation 3.0.1 from cdnjs.

**Spec:** `docs/superpowers/specs/2026-09-14-fde-skills-roadmap-design.md`

## Global Constraints

- Sources: Greenhouse, Lever, Ashby, HN Who Is Hiring (Algolia), Remotive, Arbeitnow only. Adzuna not used. Never LinkedIn/Indeed.
- Every HTTP GET goes through `sources.base.cached_get`; a cached file is never re-fetched unless `--refresh`.
- Output HTML: inline CSS/JS; external assets only `https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js` and `https://cdnjs.cloudflare.com/ajax/libs/chartjs-plugin-annotation/3.0.1/chartjs-plugin-annotation.min.js`. No web-font downloads.
- Style tokens: canvas `#fcfdfe`, text `#18324a`, secondary `#71869a`, violet `#3f00ff`, readable teal `#137a6c`, teal fill `#32c6b0`, border `#dbe7ee`, 8px spacing, `font-family: Inter, system-ui, -apple-system, "Segoe UI", sans-serif`, mono `"JetBrains Mono", SFMono-Regular, Consolas, monospace`.
- HTML section 7 must contain `<div id="author-note" class="placeholder">YOUR ONE SENTENCE HERE</div>`; no promotional copy anywhere.
- User checkpoints: (1) `taxonomy.yaml` approved before Task 12; (2) 10-posting sample approved before Task 20 full run.
- Run all Python via `uv run`. Commit after every task with a conventional-commit message ending in `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`.
- Verified API facts (2026-09-14): Greenhouse `content` is HTML-entity-escaped HTML; Lever returns a JSON list with `descriptionPlain`, `lists[].text/content`, `createdAt` in ms; Ashby returns `{jobs:[...]}` with `descriptionPlain`, `publishedAt`, `isRemote`; unknown slugs return HTTP 404 on all three. HN thread ids come from `search_by_date?query="Ask HN: Who is hiring?"&tags=story,author_whoishiring`; comments via `tags=comment,story_{id}`, top-level when `parent_id == story_id`. Remotive `?search=` is loose (returns unrelated jobs). Arbeitnow ignores `search`; 250 jobs/page, `created_at` is unix seconds.

---

## File Structure

| File | Responsibility |
|---|---|
| `pyproject.toml` | uv project, deps, pytest config |
| `main.py` | argparse CLI dispatching to step functions |
| `taxonomy.yaml` | closed skill vocabulary (user-approved) |
| `sources/base.py` | `Posting` model, `cached_get`, `matches_title`, `normalize_company`, `normalize_title`, `dedupe`, `strip_html`, `size_hint`, `travel_mentioned` |
| `sources/companies.yaml` | candidate names + `resolved:` slugs per ATS |
| `sources/greenhouse.py`, `lever.py`, `ashby.py` | `probe(slug)` + `fetch(slug) -> list[Posting]` |
| `sources/hn.py` | thread discovery + comment parsing |
| `sources/remotive.py`, `arbeitnow.py` | keyword/paginated fetch + local filter |
| `sources/discover.py` | slug discovery loop |
| `sources/collect.py` | run all sources, dedupe, write `postings.jsonl`, print counts |
| `extract/segment.py` | JD → sections |
| `extract/schema.py` | `Extraction` model, `SECTION`, JSON schema |
| `extract/prompt.md` | extraction prompt template |
| `extract/prepare.py` | write `prompts/{id}.md` + `manifest.json` |
| `extract/validate.py` | validate extractions, write `rejects.log`, update manifest |
| `aggregate/frequency.py` … `gap.py` | pure aggregate functions |
| `aggregate/build_report_data.py` | assemble `report_data.json` |
| `render/template.html.j2`, `render/render.py`, `render/content.yaml`, `render/fixtures/report_data.fixture.json` | HTML |
| `.claude/skills/fde-extract/SKILL.md` | extraction runbook |
| `tests/` | one test file per module, fixtures under `tests/fixtures/` |

---

### Task 1: Scaffold, Posting model, cached fetch

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `main.py`, `sources/__init__.py`, `sources/base.py`, `tests/__init__.py`, `tests/test_base.py`, `data/raw/.gitkeep`, `data/processed/.gitkeep`

**Interfaces:**
- Produces: `Posting` (pydantic), `cached_get(url: str, cache_key: str, *, refresh: bool=False, params: dict|None=None) -> tuple[int, str]` (status, body text), `RAW_DIR`, `PROCESSED_DIR`, `strip_html(s) -> str`.

- [ ] **Step 1: Create project files**

`pyproject.toml`:
```toml
[project]
name = "fde-roadmap"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["httpx>=0.27", "pydantic>=2.7", "pyyaml>=6", "jinja2>=3.1"]

[dependency-groups]
dev = ["pytest>=8"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

`.gitignore`:
```
.venv/
__pycache__/
.pytest_cache/
data/raw/**/*.json
data/processed/prompts/
data/processed/extractions/
*.pyc
```
(Keep `postings.jsonl`, `report_data.json`, `rejects.log` tracked — they are small and are the evidence trail.)

Run: `uv sync` — expect `.venv` created and `uv.lock` written.

- [ ] **Step 2: Write failing tests for cached_get and strip_html**

`tests/test_base.py`:
```python
import json
from pathlib import Path
import httpx
import pytest
from sources import base


def test_strip_html_unescapes_and_strips():
    s = "&lt;div&gt;&lt;h2&gt;About&lt;/h2&gt;&lt;p&gt;Hi &amp; bye&lt;/p&gt;&lt;/div&gt;"
    assert base.strip_html(s) == "About\nHi & bye"


def test_cached_get_writes_then_reads_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(base, "RAW_DIR", tmp_path)
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(200, text='{"ok": 1}')

    monkeypatch.setattr(base, "_client", httpx.Client(transport=httpx.MockTransport(handler)))
    status, body = base.cached_get("https://x.test/a", "src/key1")
    assert (status, body) == (200, '{"ok": 1}')
    cached = json.loads((tmp_path / "src" / "key1.json").read_text())
    assert cached["status"] == 200 and cached["body"] == '{"ok": 1}' and "fetched_at" in cached

    status2, body2 = base.cached_get("https://x.test/a", "src/key1")
    assert (status2, body2) == (200, '{"ok": 1}')
    assert len(calls) == 1  # second call served from disk


def test_cached_get_caches_404(tmp_path, monkeypatch):
    monkeypatch.setattr(base, "RAW_DIR", tmp_path)
    monkeypatch.setattr(base, "_client", httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(404, text="nf"))))
    assert base.cached_get("https://x.test/b", "src/key2") == (404, "nf")
    assert (tmp_path / "src" / "key2.json").exists()
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_base.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'sources'` or `AttributeError`.

- [ ] **Step 4: Implement sources/base.py (first half)**

```python
"""Shared posting model, disk-cached HTTP, and text helpers."""
from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import httpx
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

_client = httpx.Client(timeout=30, headers={"User-Agent": "fde-roadmap/0.1 (research; contact via repo)"}, follow_redirects=True)


class Posting(BaseModel):
    id: str
    title: str
    company: str
    company_size_hint: str = "unknown"  # startup | scaleup | enterprise | unknown
    location: str = ""
    remote_flag: bool = False
    travel_mentioned: bool = False
    seniority_raw: str = ""
    url: str
    posted_date: str | None = None  # ISO date
    full_text: str
    source: str


def make_id(source: str, source_id: str) -> str:
    return hashlib.sha1(f"{source}:{source_id}".encode()).hexdigest()[:16]


def cached_get(url: str, cache_key: str, *, refresh: bool = False, params: dict | None = None) -> tuple[int, str]:
    """GET url, caching status+body verbatim under data/raw/{cache_key}.json.

    Never re-hits the network if the cache file exists, unless refresh=True.
    """
    path = RAW_DIR / f"{cache_key}.json"
    if path.exists() and not refresh:
        d = json.loads(path.read_text())
        return d["status"], d["body"]
    resp = _client.get(url, params=params)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "url": str(resp.url), "status": resp.status_code, "body": resp.text,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }))
    return resp.status_code, resp.text


_TAG_RE = re.compile(r"<(br|p|/p|/div|/li|/h[1-6]|/tr)\s*/?>", re.I)
_ANY_TAG_RE = re.compile(r"<[^>]+>")


def strip_html(s: str) -> str:
    """Unescape entities (twice: Greenhouse double-escapes), turn block tags into newlines, drop tags."""
    s = html.unescape(html.unescape(s))
    s = _TAG_RE.sub("\n", s)
    s = _ANY_TAG_RE.sub("", s)
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in s.splitlines()]
    return "\n".join(ln for ln in lines if ln)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_base.py -v`
Expected: 3 PASS.

- [ ] **Step 6: Create main.py skeleton**

```python
"""FDE roadmap pipeline CLI."""
import argparse
import sys


def main(argv=None):
    p = argparse.ArgumentParser(prog="fde-roadmap")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("discover", "collect", "prepare", "validate", "aggregate", "render"):
        sp = sub.add_parser(name)
        sp.add_argument("--refresh", action="store_true", help="re-hit sources (never default)")
        sp.add_argument("--fixture", action="store_true", help="render: use fixture data")
        sp.add_argument("--limit", type=int, default=None, help="prepare: only first N postings")
    args = p.parse_args(argv)
    print(f"{args.cmd}: not implemented yet", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: scaffold project, Posting model, cached HTTP helper

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---
### Task 2: Fixture data, render.py, HTML template (viewable fake report)

**Files:**
- Create: `render/__init__.py`, `render/render.py`, `render/template.html.j2`, `render/content.yaml`, `render/fixtures/report_data.fixture.json`, `tests/test_render.py`
- Modify: `main.py` (wire `render`)

**Interfaces:**
- Consumes: nothing from code; defines the `report_data.json` contract below that Tasks 15–19 must produce.
- Produces: `render.render.render_html(data: dict, content: dict) -> str`, `render.render.load_content() -> dict`, CLI `uv run python main.py render [--fixture]` writing `fde-roadmap.html`.

**report_data.json contract (fixture must match exactly):**
```
meta:      {n_postings:int, n_companies:int, date_range:[iso,iso], generated_at:iso,
            sources:[{name, fetched, matched, kept}], segmentation:{header:int, inferred:int},
            rejects:int, adzuna_used:false, model:"claude-sonnet-5"}
skills:    [{canonical, label, cluster, n, frequency:0-1, criticality:0-1,
            mentions:{responsibility, requirement, nice_to_have}, low_n:bool, evidence:str}]
clusters:  [{key, label, coverage:0-1, skills:[canonical,...]}]   # six, spec order
scatter:   {median_frequency, median_criticality, outliers:[{canonical, note}]}
stacks:    [{name, skills:[canonical,...], support:int}]
market:    {seniority:{junior,mid,senior,staff_plus,unspecified},
            years:{"0-2","3-5","6-9","10+","unspecified"},
            travel:{none,occasional,frequent,unspecified},
            customer_facing:{"1","2","3","4","5"},
            verbs:[[verb,count],...] (15),
            segment_deltas:[{skill, startup:0-1, enterprise:0-1}]}
gap:       [{canonical, label, frequency}]
```
`content.yaml` (merged in at render time as `content`):
```
flow:      [{step, blurb}]  (8 steps in spec order)
roadmap:   [{track, skip:[str] (optional), stages:[{name, skills:[str], why}]}]
projects:  [{name, scope, proves, clusters:[key]}]
insights:  {segment_prose: str, limitations:[str]}
```

- [ ] **Step 1: Write the fixture**

`render/fixtures/report_data.fixture.json` — 12 skills across all six clusters, realistic numbers. Use exactly:
```json
{
  "meta": {"n_postings": 300, "n_companies": 80, "date_range": ["2026-05-01", "2026-09-14"],
           "generated_at": "2026-09-14T00:00:00Z", "model": "claude-sonnet-5",
           "sources": [{"name": "greenhouse", "fetched": 4000, "matched": 140, "kept": 120},
                       {"name": "lever", "fetched": 1500, "matched": 60, "kept": 50},
                       {"name": "ashby", "fetched": 3000, "matched": 90, "kept": 80},
                       {"name": "hn", "fetched": 900, "matched": 40, "kept": 35},
                       {"name": "remotive", "fetched": 200, "matched": 10, "kept": 8},
                       {"name": "arbeitnow", "fetched": 5000, "matched": 9, "kept": 7}],
           "segmentation": {"header": 240, "inferred": 60}, "rejects": 41, "adzuna_used": false},
  "skills": [
    {"canonical": "python", "label": "Python", "cluster": "software_foundations", "n": 270, "frequency": 0.9, "criticality": 0.28, "mentions": {"responsibility": 80, "requirement": 170, "nice_to_have": 20}, "low_n": false, "evidence": "Strong proficiency in Python"},
    {"canonical": "typescript", "label": "TypeScript", "cluster": "software_foundations", "n": 120, "frequency": 0.4, "criticality": 0.35, "mentions": {"responsibility": 42, "requirement": 60, "nice_to_have": 18}, "low_n": false, "evidence": "experience with TypeScript/React"},
    {"canonical": "llm_apis", "label": "LLM APIs", "cluster": "ai_application_engineering", "n": 240, "frequency": 0.8, "criticality": 0.55, "mentions": {"responsibility": 132, "requirement": 90, "nice_to_have": 18}, "low_n": false, "evidence": "build applications on top of LLM APIs"},
    {"canonical": "rag", "label": "RAG", "cluster": "ai_application_engineering", "n": 150, "frequency": 0.5, "criticality": 0.6, "mentions": {"responsibility": 90, "requirement": 50, "nice_to_have": 10}, "low_n": false, "evidence": "design retrieval-augmented pipelines"},
    {"canonical": "evals", "label": "Evals", "cluster": "ai_application_engineering", "n": 90, "frequency": 0.3, "criticality": 0.7, "mentions": {"responsibility": 63, "requirement": 22, "nice_to_have": 5}, "low_n": false, "evidence": "own evaluation frameworks for model quality"},
    {"canonical": "sql", "label": "SQL", "cluster": "data_and_integrations", "n": 180, "frequency": 0.6, "criticality": 0.3, "mentions": {"responsibility": 54, "requirement": 110, "nice_to_have": 16}, "low_n": false, "evidence": "comfortable writing SQL"},
    {"canonical": "rest_apis", "label": "REST / API integration", "cluster": "data_and_integrations", "n": 200, "frequency": 0.67, "criticality": 0.62, "mentions": {"responsibility": 124, "requirement": 66, "nice_to_have": 10}, "low_n": false, "evidence": "integrate with customer systems via APIs"},
    {"canonical": "aws", "label": "AWS", "cluster": "deployment_and_operations", "n": 160, "frequency": 0.53, "criticality": 0.4, "mentions": {"responsibility": 64, "requirement": 80, "nice_to_have": 16}, "low_n": false, "evidence": "deploy on AWS"},
    {"canonical": "kubernetes", "label": "Kubernetes", "cluster": "deployment_and_operations", "n": 75, "frequency": 0.25, "criticality": 0.45, "mentions": {"responsibility": 34, "requirement": 30, "nice_to_have": 11}, "low_n": false, "evidence": "experience with Kubernetes"},
    {"canonical": "stakeholder_communication", "label": "Stakeholder communication", "cluster": "customer_delivery", "n": 60, "frequency": 0.2, "criticality": 0.85, "mentions": {"responsibility": 51, "requirement": 8, "nice_to_have": 1}, "low_n": false, "evidence": "present outcomes to executive stakeholders"},
    {"canonical": "scoping", "label": "Scoping & discovery", "cluster": "customer_delivery", "n": 130, "frequency": 0.43, "criticality": 0.8, "mentions": {"responsibility": 104, "requirement": 22, "nice_to_have": 4}, "low_n": false, "evidence": "scope engagements with customers"},
    {"canonical": "product_sense", "label": "Product sense", "cluster": "product_thinking_and_communication", "n": 12, "frequency": 0.04, "criticality": 0.75, "mentions": {"responsibility": 9, "requirement": 3, "nice_to_have": 0}, "low_n": true, "evidence": "translate user needs into product feedback"}
  ],
  "clusters": [
    {"key": "software_foundations", "label": "Software foundations", "coverage": 0.97, "skills": ["python", "typescript"]},
    {"key": "ai_application_engineering", "label": "AI application engineering", "coverage": 0.9, "skills": ["llm_apis", "rag", "evals"]},
    {"key": "data_and_integrations", "label": "Data & integrations", "coverage": 0.8, "skills": ["sql", "rest_apis"]},
    {"key": "deployment_and_operations", "label": "Deployment & operations", "coverage": 0.65, "skills": ["aws", "kubernetes"]},
    {"key": "customer_delivery", "label": "Customer delivery", "coverage": 0.7, "skills": ["stakeholder_communication", "scoping"]},
    {"key": "product_thinking_and_communication", "label": "Product thinking & communication", "coverage": 0.3, "skills": ["product_sense"]}
  ],
  "scatter": {"median_frequency": 0.45, "median_criticality": 0.55,
              "outliers": [{"canonical": "python", "note": "Everyone asks, few make it the job"},
                           {"canonical": "stakeholder_communication", "note": "Rarely listed, always the job"}]},
  "stacks": [{"name": "LLM app core", "skills": ["python", "llm_apis", "rag", "evals"], "support": 80},
             {"name": "Enterprise plumbing", "skills": ["rest_apis", "sql", "aws"], "support": 60},
             {"name": "Field delivery", "skills": ["scoping", "stakeholder_communication"], "support": 45}],
  "market": {"seniority": {"junior": 5, "mid": 90, "senior": 150, "staff_plus": 25, "unspecified": 30},
             "years": {"0-2": 10, "3-5": 120, "6-9": 80, "10+": 20, "unspecified": 70},
             "travel": {"none": 60, "occasional": 120, "frequent": 50, "unspecified": 70},
             "customer_facing": {"1": 10, "2": 30, "3": 80, "4": 110, "5": 70},
             "verbs": [["build", 210], ["deploy", 180], ["integrate", 150], ["partner", 120], ["scope", 100], ["own", 95], ["prototype", 90], ["evaluate", 80], ["translate", 70], ["lead", 60], ["design", 55], ["debug", 50], ["present", 45], ["iterate", 40], ["document", 30]],
             "segment_deltas": [{"skill": "kubernetes", "startup": 0.15, "enterprise": 0.45}, {"skill": "typescript", "startup": 0.55, "enterprise": 0.3}]},
  "gap": [{"canonical": "scoping", "label": "Scoping & discovery", "frequency": 0.43},
          {"canonical": "rest_apis", "label": "REST / API integration", "frequency": 0.67},
          {"canonical": "stakeholder_communication", "label": "Stakeholder communication", "frequency": 0.2}]
}
```

- [ ] **Step 2: Write placeholder content.yaml**

`render/content.yaml` (placeholder text is fine here — replaced in Task 21; the structure is what matters):
```yaml
flow:
  - {step: Discover, blurb: "Sit with the customer; find the workflow that actually hurts."}
  - {step: Scope, blurb: "Turn the pain into a bounded, measurable first deliverable."}
  - {step: Prototype, blurb: "Ship something rough in days, on their data."}
  - {step: Integrate, blurb: "Wire it into the systems they already run."}
  - {step: Deploy, blurb: "Get it into their environment, under their constraints."}
  - {step: Evaluate, blurb: "Measure against the outcome you scoped, not vibes."}
  - {step: Improve, blurb: "Close the gaps the eval exposed."}
  - {step: "Feed back", blurb: "Bring what the field taught you to the product team."}
roadmap:
  - track: Python for FDE
    skip: ["Deep CPython internals", "Metaclasses", "Competitive-programming algorithms"]
    stages:
      - {name: "Stage 1", skills: ["python", "rest_apis"], why: "placeholder"}
  - track: AI application engineering
    stages:
      - {name: "Stage 1", skills: ["llm_apis", "rag", "evals"], why: "placeholder"}
projects:
  - {name: "Project A", scope: "placeholder", proves: "placeholder", clusters: ["ai_application_engineering", "customer_delivery"]}
  - {name: "Project B", scope: "placeholder", proves: "placeholder", clusters: ["data_and_integrations"]}
  - {name: "Project C", scope: "placeholder", proves: "placeholder", clusters: ["deployment_and_operations"]}
  - {name: "Project D", scope: "placeholder", proves: "placeholder", clusters: ["product_thinking_and_communication"]}
insights:
  segment_prose: "placeholder"
  limitations: ["placeholder"]
```

- [ ] **Step 3: Write failing render test**

`tests/test_render.py`:
```python
import json
from pathlib import Path
from render import render as r

FIX = Path("render/fixtures/report_data.fixture.json")
SECTION_IDS = ["what-fde-does", "top-technologies", "frequency-vs-criticality", "capability-clusters",
               "learning-roadmap", "market-insights", "proof-projects", "methodology"]


def test_render_from_fixture_has_all_sections_and_placeholder():
    data = json.loads(FIX.read_text())
    html = r.render_html(data, r.load_content())
    for sid in SECTION_IDS:
        assert f'id="{sid}"' in html, sid
    assert '<div id="author-note" class="placeholder">YOUR ONE SENTENCE HERE</div>' in html
    assert 'type="application/json"' in html
    assert "cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js" in html
    assert "chartjs-plugin-annotation/3.0.1" in html
    assert len(html.encode()) < 1_500_000
    # no other external assets
    assert "fonts.googleapis" not in html and "<link" not in html
```

- [ ] **Step 4: Run test to verify it fails**

Run: `uv run pytest tests/test_render.py -v`
Expected: FAIL `ModuleNotFoundError` / `AttributeError`.

- [ ] **Step 5: Implement render/render.py**

```python
"""Render report_data.json + content.yaml into one self-contained HTML file."""
from __future__ import annotations

import json
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "fde-roadmap.html"
FIXTURE = HERE / "fixtures" / "report_data.fixture.json"
REPORT_DATA = ROOT / "data" / "processed" / "report_data.json"

CLUSTER_COLORS = {  # from owlhub-tokens.css; always shown with a text label
    "software_foundations": "#3f00ff",
    "ai_application_engineering": "#137a6c",
    "data_and_integrations": "#18324a",
    "deployment_and_operations": "#2563eb",
    "customer_delivery": "#a85f00",
    "product_thinking_and_communication": "#71869a",
}


def load_content() -> dict:
    return yaml.safe_load((HERE / "content.yaml").read_text())


def render_html(data: dict, content: dict) -> str:
    env = Environment(loader=FileSystemLoader(HERE), autoescape=select_autoescape(["j2"]))
    tpl = env.get_template("template.html.j2")
    payload = {**data, "content": content, "cluster_colors": CLUSTER_COLORS}
    return tpl.render(data=payload, data_json=json.dumps(payload, ensure_ascii=False).replace("</", "<\\/"))


def run(fixture: bool = False) -> Path:
    src = FIXTURE if fixture or not REPORT_DATA.exists() else REPORT_DATA
    data = json.loads(src.read_text())
    OUT.write_text(render_html(data, load_content()))
    print(f"rendered {OUT} from {src.name} ({OUT.stat().st_size // 1024} KB)")
    return OUT
```

- [ ] **Step 6: Write render/template.html.j2**

Full template (all eight sections, inline CSS, Chart.js). Keep the section ids exactly as tested.

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FDE Skills Roadmap — what Forward Deployed Engineer postings actually ask for</title>
<style>
:root{--canvas:#fcfdfe;--surface:#fff;--text:#18324a;--muted:#71869a;--violet:#3f00ff;--violet-100:#ede8ff;
--teal:#137a6c;--teal-fill:#32c6b0;--teal-100:#dcf7f2;--line:#dbe7ee;--line-strong:#b9cbd7;--amber:#a85f00;--amber-100:#fff1d6;
--s1:4px;--s2:8px;--s3:12px;--s4:16px;--s5:24px;--s6:32px;--s7:48px;--s8:64px;--r:12px;--measure:680px;--max:1100px}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--canvas);color:var(--text);font:17px/1.6 Inter,system-ui,-apple-system,"Segoe UI",sans-serif;padding-block:0;padding-inline:clamp(16px,4vw,40px)}
code,.mono{font-family:"JetBrains Mono",SFMono-Regular,Consolas,monospace;font-size:.9em}
h1,h2,h3{font-weight:500;letter-spacing:-.02em;line-height:1.15;margin:0}
h1{font-size:clamp(2rem,5vw,3.25rem)}h2{font-size:clamp(1.5rem,3vw,2rem);margin-bottom:var(--s3)}h3{font-size:1.1rem}
p{max-width:var(--measure);margin:0 0 var(--s4)}
a{color:var(--violet)}
.wrap{max-width:var(--max);margin:0 auto}
header.hero{padding-block:var(--s8) var(--s6);border-bottom:1px solid var(--line)}
.eyebrow{display:inline-flex;align-items:center;gap:8px;font-size:.8rem;letter-spacing:.06em;text-transform:uppercase;color:var(--violet);background:var(--violet-100);border-radius:999px;padding:4px 12px;margin-bottom:var(--s4)}
.eyebrow::before{content:"";width:6px;height:6px;border-radius:50%;background:var(--violet)}
.lede{color:var(--muted);font-size:1.15rem;max-width:var(--measure)}
section{padding-block:var(--s7);border-bottom:1px solid var(--line)}
section:last-of-type{border-bottom:0}
.sub{color:var(--muted);max-width:var(--measure);margin-bottom:var(--s5)}
.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:var(--s5)}
.grid{display:grid;gap:var(--s4)}
.grid-2{grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}
.grid-3{grid-template-columns:repeat(auto-fit,minmax(260px,1fr))}
.chip{display:inline-block;font-size:.8rem;padding:2px 10px;border-radius:999px;border:1px solid var(--line-strong);margin:2px 4px 2px 0;background:var(--surface)}
.chip.low{opacity:.5}
.legend{display:flex;flex-wrap:wrap;gap:var(--s3);font-size:.85rem;color:var(--muted);margin:var(--s3) 0}
.legend span::before{content:"";display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px;background:var(--c);vertical-align:-1px}
/* flow */
.flow{display:flex;flex-wrap:wrap;gap:var(--s3);list-style:none;padding:0;margin:0;counter-reset:step}
.flow li{flex:1 1 160px;position:relative;background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:var(--s4);counter-increment:step}
.flow li b{display:block;font-weight:500}
.flow li b::before{content:counter(step);display:inline-grid;place-items:center;width:24px;height:24px;border-radius:50%;background:var(--violet);color:#fff;font-size:.75rem;margin-right:8px}
.flow li small{color:var(--muted);display:block;margin-top:var(--s1);line-height:1.4}
.flow li:not(:last-child)::after{content:"→";position:absolute;right:-13px;top:14px;color:var(--line-strong)}
@media (max-width:700px){.flow li:not(:last-child)::after{content:"↓";right:auto;left:16px;top:auto;bottom:-16px}.flow{gap:var(--s5)}}
/* charts */
.chart-box{position:relative;width:100%}
#bars-box{height:calc(30*22px + 40px)}
#scatter-box{min-height:70vh;height:70vh}
@media (max-width:700px){#scatter-box{height:80vh}}
.quadrant-key{display:grid;grid-template-columns:1fr 1fr;gap:var(--s2);font-size:.85rem;color:var(--muted);margin-top:var(--s3)}
/* clusters */
.cluster{border-left:4px solid var(--c)}
.cluster .pct{font-size:2rem;font-weight:500;color:var(--c)}
/* roadmap */
.track{margin-bottom:var(--s5)}
.stages{list-style:none;padding:0;margin:0;border-left:2px solid var(--line-strong)}
.stages li{position:relative;padding:0 0 var(--s4) var(--s5)}
.stages li::before{content:"";position:absolute;left:-7px;top:8px;width:12px;height:12px;border-radius:50%;background:var(--violet);border:2px solid var(--canvas)}
.skip{background:var(--amber-100);border:1px solid #e5c98f;border-radius:var(--r);padding:var(--s3) var(--s4);margin-bottom:var(--s4)}
.skip b{color:var(--amber)}
/* market */
.dist{display:grid;grid-template-columns:auto 1fr auto;gap:var(--s2) var(--s3);align-items:center;font-size:.9rem}
.dist .bar{height:10px;background:var(--line);border-radius:5px;overflow:hidden}.dist .bar i{display:block;height:100%;background:var(--teal-fill)}
.verbs{display:flex;flex-wrap:wrap;gap:var(--s2)}
/* projects */
.placeholder{border:2px dashed var(--violet);background:var(--violet-100);border-radius:var(--r);padding:var(--s4);font-style:italic;color:var(--violet);margin-bottom:var(--s5)}
table{border-collapse:collapse;width:100%;font-size:.9rem}td,th{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line)}th{color:var(--muted);font-weight:500}
.table-wrap{overflow-x:auto}
footer{color:var(--muted);font-size:.85rem;padding-block:var(--s6)}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
</style>
</head>
<body>
<div class="wrap">
<header class="hero">
  <span class="eyebrow">Research report</span>
  <h1>What Forward Deployed Engineer roles actually demand</h1>
  <p class="lede">A skills map built from {{ data.meta.n_postings }} live FDE job postings across {{ data.meta.n_companies }} companies, extracted against a fixed taxonomy and split by whether a skill is the <em>job</em> or merely a <em>requirement</em>.</p>
</header>

<section id="what-fde-does">
  <h2>1 · What an FDE does</h2>
  <p class="sub">The loop every posting describes, in one form or another.</p>
  <ol class="flow">{% for f in data.content.flow %}<li><b>{{ f.step }}</b><small>{{ f.blurb }}</small></li>{% endfor %}</ol>
</section>

<section id="top-technologies">
  <h2>2 · Most requested technologies</h2>
  <p class="sub">Share of postings mentioning each skill in any section. Colour = capability cluster.</p>
  <div class="legend" id="legend-bars"></div>
  <div class="chart-box" id="bars-box"><canvas id="bars"></canvas></div>
</section>

<section id="frequency-vs-criticality">
  <h2>3 · Frequency vs criticality</h2>
  <p class="sub"><b>Frequency</b> (x): how often a skill appears. <b>Criticality</b> (y): the share of its mentions that sit in a <em>responsibilities</em> section rather than requirements or nice-to-haves — i.e. how often the skill <em>is the job</em>. Faded points have fewer than 5 mentions.</p>
  <div class="chart-box" id="scatter-box"><canvas id="scatter"></canvas></div>
  <div class="quadrant-key">
    <span><b>Top-left — Hidden core:</b> rarely listed, but when listed it is the work.</span>
    <span><b>Top-right — The job:</b> common and central. Learn these first.</span>
    <span><b>Bottom-left — Peripheral:</b> occasional nice-to-haves.</span>
    <span><b>Bottom-right — Table stakes:</b> everyone asks; nobody hires for it alone.</span>
  </div>
</section>

<section id="capability-clusters">
  <h2>4 · Capability clusters</h2>
  <p class="sub">Coverage = share of postings mentioning at least one skill in the cluster.</p>
  <div class="grid grid-3">
  {% for c in data.clusters %}
    <div class="card cluster" style="--c:{{ data.cluster_colors[c.key] }}">
      <div class="pct">{{ (c.coverage*100)|round|int }}%</div>
      <h3>{{ c.label }}</h3>
      <div>{% for s in c.skills %}{% set sk = data.skills|selectattr('canonical','equalto',s)|first %}<span class="chip{% if sk and sk.low_n %} low{% endif %}">{{ sk.label if sk else s }}{% if sk %} · {{ (sk.frequency*100)|round|int }}%{% endif %}</span>{% endfor %}</div>
    </div>
  {% endfor %}
  </div>
</section>

<section id="learning-roadmap">
  <h2>5 · Learning roadmap</h2>
  <p class="sub">Staged tracks ordered by what the data says matters first.</p>
  {% for t in data.content.roadmap %}
  <div class="track card">
    <h3>{{ t.track }}</h3>
    {% if t.skip %}<div class="skip"><b>Skip (for now):</b> {{ t.skip|join(' · ') }}</div>{% endif %}
    <ol class="stages">{% for st in t.stages %}<li><b>{{ st.name }}</b> — {% for s in st.skills %}{% set sk = data.skills|selectattr('canonical','equalto',s)|first %}<span class="chip">{{ sk.label if sk else s }}</span>{% endfor %}<br><small style="color:var(--muted)">{{ st.why }}</small></li>{% endfor %}</ol>
  </div>
  {% endfor %}
</section>

<section id="market-insights">
  <h2>6 · Market insights</h2>
  <div class="grid grid-2">
    {% for key, title in [('seniority','Seniority'),('years','Years required'),('travel','Travel expectation'),('customer_facing','Customer-facing intensity (1–5)')] %}
    <div class="card"><h3>{{ title }}</h3>
      {% set d = data.market[key] %}{% set total = d.values()|sum %}
      <div class="dist">{% for k, v in d.items() %}<span>{{ k|replace('_',' ') }}</span><span class="bar"><i style="width:{{ (100*v/total)|round(1) if total else 0 }}%"></i></span><span class="mono">{{ (100*v/total)|round|int if total else 0 }}%</span>{% endfor %}</div>
    </div>
    {% endfor %}
  </div>
  <div class="card" style="margin-top:var(--s4)"><h3>Most common responsibility verbs</h3>
    <div class="verbs">{% for v, n in data.market.verbs %}<span class="chip">{{ v }} <span class="mono" style="color:var(--muted)">{{ n }}</span></span>{% endfor %}</div></div>
  <div class="card" style="margin-top:var(--s4)"><h3>Startup vs enterprise</h3><p>{{ data.content.insights.segment_prose }}</p></div>
  <div class="card" style="margin-top:var(--s4)"><h3>What FDE demands that standard AI-engineer roadmaps skip</h3>
    <div>{% for g in data.gap %}<span class="chip">{{ g.label }} · {{ (g.frequency*100)|round|int }}%</span>{% endfor %}</div></div>
</section>

<section id="proof-projects">
  <h2>7 · Proof projects</h2>
  <div id="author-note" class="placeholder">YOUR ONE SENTENCE HERE</div>
  <div class="grid grid-2">
  {% for p in data.content.projects %}
    <div class="card"><h3>{{ p.name }}</h3>
      <p><b>Scope.</b> {{ p.scope }}</p><p><b>Proves.</b> {{ p.proves }}</p>
      <div>{% for ck in p.clusters %}{% set c = data.clusters|selectattr('key','equalto',ck)|first %}<span class="chip" style="border-color:{{ data.cluster_colors[ck] }}">{{ c.label if c else ck }}</span>{% endfor %}</div>
    </div>
  {% endfor %}
  </div>
</section>

<section id="methodology">
  <h2>8 · Methodology</h2>
  <p><b>n = {{ data.meta.n_postings }}</b> unique postings from {{ data.meta.n_companies }} companies, posted {{ data.meta.date_range[0] }} to {{ data.meta.date_range[1] }}. Deduplicated on (normalised company, normalised title).</p>
  <div class="table-wrap"><table><tr><th>Source</th><th>Fetched</th><th>Title-matched</th><th>Kept after dedupe</th></tr>
  {% for s in data.meta.sources %}<tr><td>{{ s.name }}</td><td class="mono">{{ s.fetched }}</td><td class="mono">{{ s.matched }}</td><td class="mono">{{ s.kept }}</td></tr>{% endfor %}</table></div>
  <p style="margin-top:var(--s4)"><b>Extraction.</b> Each posting was segmented into responsibilities / requirements / nice-to-have sections ({{ data.meta.segmentation.header }} by explicit headers, {{ data.meta.segmentation.inferred }} inferred) and passed once, with the full closed taxonomy, to {{ data.meta.model }} using a fixed prompt. Every returned skill was validated against the taxonomy; {{ data.meta.rejects }} out-of-vocabulary mentions were logged and reviewed. Adzuna: {{ 'used' if data.meta.adzuna_used else 'not used' }}. LinkedIn and Indeed were not scraped.</p>
  <p><b>Limitations.</b></p><ul>{% for l in data.content.insights.limitations %}<li>{{ l }}</li>{% endfor %}</ul>
</section>
<footer>Generated {{ data.meta.generated_at[:10] }}. Pipeline and taxonomy are open; charts by Chart.js.</footer>
</div>

<script id="data" type="application/json">{{ data_json|safe }}</script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/chartjs-plugin-annotation/3.0.1/chartjs-plugin-annotation.min.js"></script>
<script>
(function(){
  const D = JSON.parse(document.getElementById('data').textContent);
  const C = D.cluster_colors, labelOf = Object.fromEntries(D.clusters.map(c=>[c.key,c.label]));
  const pct = v => Math.round(v*100)+'%';
  const mobile = matchMedia('(max-width:700px)').matches;
  Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
  Chart.defaults.color = '#71869a';
  if (window['chartjs-plugin-annotation']) Chart.register(window['chartjs-plugin-annotation']);

  // legend
  document.getElementById('legend-bars').innerHTML = D.clusters.map(c=>`<span style="--c:${C[c.key]}">${c.label}</span>`).join('');

  // 2. bars
  const top = [...D.skills].sort((a,b)=>b.frequency-a.frequency).slice(0,30);
  document.getElementById('bars-box').style.height = (top.length*22+40)+'px';
  new Chart(document.getElementById('bars'), {type:'bar', data:{labels:top.map(s=>s.label),
    datasets:[{data:top.map(s=>s.frequency), backgroundColor:top.map(s=>C[s.cluster]), borderRadius:3}]},
    options:{indexAxis:'y', responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false},
      tooltip:{callbacks:{label:c=>`${pct(c.raw)} of postings · ${labelOf[top[c.dataIndex].cluster]}`}}},
      scales:{x:{min:0,max:1,ticks:{callback:v=>pct(v)},grid:{color:'#dbe7ee'}}, y:{grid:{display:false}}}}});

  // 3. scatter
  const S = D.skills, mx = D.scatter.median_frequency, my = D.scatter.median_criticality;
  const notes = Object.fromEntries(D.scatter.outliers.map(o=>[o.canonical,o.note]));
  const ann = {
    vx:{type:'line', xMin:mx, xMax:mx, borderColor:'#b9cbd7', borderDash:[4,4]},
    hy:{type:'line', yMin:my, yMax:my, borderColor:'#b9cbd7', borderDash:[4,4]},
    q1:{type:'label', xValue:0.02, yValue:0.98, position:{x:'start',y:'start'}, content:['Hidden core'], color:'#71869a', font:{size:12}},
    q2:{type:'label', xValue:0.98, yValue:0.98, position:{x:'end',y:'start'}, content:['The job'], color:'#71869a', font:{size:12}},
    q3:{type:'label', xValue:0.02, yValue:0.02, position:{x:'start',y:'end'}, content:['Peripheral'], color:'#71869a', font:{size:12}},
    q4:{type:'label', xValue:0.98, yValue:0.02, position:{x:'end',y:'end'}, content:['Table stakes'], color:'#71869a', font:{size:12}},
  };
  S.forEach((s,i)=>{ if(notes[s.canonical]) ann['o'+i]={type:'label', xValue:s.frequency, yValue:s.criticality,
      content:[s.label, notes[s.canonical]], backgroundColor:'#fff', borderColor:C[s.cluster], borderWidth:1, borderRadius:6,
      padding:6, font:{size:11}, color:'#18324a', yAdjust:s.criticality>my?28:-28, xAdjust:s.frequency>mx?-40:40}; });
  new Chart(document.getElementById('scatter'), {type:'scatter',
    data:{datasets:D.clusters.map(c=>({label:c.label, data:S.filter(s=>s.cluster===c.key).map(s=>({x:s.frequency,y:s.criticality,s})),
      backgroundColor:S.filter(s=>s.cluster===c.key).map(s=>C[c.key]+(s.low_n?'66':'cc')), pointRadius:mobile?5:7, pointHoverRadius:9}))},
    options:{responsive:true, maintainAspectRatio:false,
      plugins:{legend:{position:'bottom'}, annotation:{annotations:ann},
        tooltip:{callbacks:{title:c=>c[0].raw.s.label, label:c=>{const s=c.raw.s;return [`frequency ${pct(s.frequency)} (n=${s.n})`,`criticality ${pct(s.criticality)}`,`e.g. "${s.evidence}"`];}}}},
      scales:{x:{min:0,max:1,title:{display:true,text:'Frequency — share of postings'},ticks:{callback:pct},grid:{color:'#eef3f7'}},
              y:{min:0,max:1,title:{display:true,text:'Criticality — share of mentions that are responsibilities'},ticks:{callback:pct},grid:{color:'#eef3f7'}}}}});
})();
</script>
</body>
</html>
```

- [ ] **Step 7: Wire main.py render and run the test**

In `main.py`, replace the `print(... not implemented ...)` body with:
```python
    if args.cmd == "render":
        from render import render as r
        r.run(fixture=args.fixture)
        return 0
    print(f"{args.cmd}: not implemented yet", file=sys.stderr)
    return 1
```
Run: `uv run pytest tests/test_render.py -v` → PASS. Then `uv run python main.py render --fixture` and open `fde-roadmap.html` in Chrome; check the bar chart, scatter with quadrant labels and two callouts, and that nothing scrolls horizontally at 390px width.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: HTML template, fixture data, render step

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---
### Task 3: taxonomy.yaml + loader (USER CHECKPOINT 1)

**Files:**
- Create: `taxonomy.yaml`, `extract/__init__.py`, `extract/taxonomy.py`, `tests/test_taxonomy.py`

**Interfaces:**
- Produces: `extract.taxonomy.load() -> Taxonomy` with `.clusters: dict[str, list[Skill]]`, `.by_canonical: dict[str, Skill]`, `.alias_index: dict[str, str]` (lowercased alias → canonical), `.canonical_names() -> set[str]`, `.cluster_of(canonical) -> str`, `.labels: dict[canonical, label]`. `Skill` = pydantic `{canonical, label, aliases: list[str], definition}`.

- [ ] **Step 1: Write failing tests**

`tests/test_taxonomy.py`:
```python
from extract import taxonomy as T

CLUSTERS = ["software_foundations", "ai_application_engineering", "data_and_integrations",
            "deployment_and_operations", "customer_delivery", "product_thinking_and_communication"]


def test_six_clusters_in_spec_order():
    tx = T.load()
    assert list(tx.clusters.keys()) == CLUSTERS


def test_canonicals_unique_snake_case_and_aliases_unique():
    tx = T.load()
    names = [s.canonical for c in tx.clusters.values() for s in c]
    assert len(names) == len(set(names))
    assert all(n == n.lower() and " " not in n for n in names)
    seen = {}
    for c in tx.clusters.values():
        for s in c:
            for a in s.aliases:
                assert a.lower() not in seen, f"alias {a!r} in both {seen.get(a.lower())} and {s.canonical}"
                seen[a.lower()] = s.canonical


def test_generic_cloud_maps_to_generic_node_not_aws():
    tx = T.load()
    assert tx.alias_index["cloud"] == "cloud_platforms"
    assert tx.alias_index["amazon web services"] == "aws"


def test_size():
    tx = T.load()
    assert 80 <= len(tx.by_canonical) <= 110
```

- [ ] **Step 2: Run to verify fail** — `uv run pytest tests/test_taxonomy.py -v` → FAIL (no module).

- [ ] **Step 3: Write extract/taxonomy.py**

```python
"""Closed skill vocabulary loaded from taxonomy.yaml."""
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel

PATH = Path(__file__).resolve().parent.parent / "taxonomy.yaml"


class Skill(BaseModel):
    canonical: str
    label: str
    aliases: list[str] = []
    definition: str


class Taxonomy(BaseModel):
    clusters: dict[str, list[Skill]]
    cluster_labels: dict[str, str]

    @property
    def by_canonical(self) -> dict[str, Skill]:
        return {s.canonical: s for c in self.clusters.values() for s in c}

    @property
    def alias_index(self) -> dict[str, str]:
        idx = {}
        for c in self.clusters.values():
            for s in c:
                idx[s.canonical] = s.canonical
                idx[s.label.lower()] = s.canonical
                for a in s.aliases:
                    idx[a.lower()] = s.canonical
        return idx

    @property
    def labels(self) -> dict[str, str]:
        return {k: v.label for k, v in self.by_canonical.items()}

    def canonical_names(self) -> set[str]:
        return set(self.by_canonical)

    def cluster_of(self, canonical: str) -> str:
        for key, skills in self.clusters.items():
            if any(s.canonical == canonical for s in skills):
                return key
        raise KeyError(canonical)


def load(path: Path = PATH) -> Taxonomy:
    raw = yaml.safe_load(path.read_text())
    return Taxonomy(
        clusters={k: [Skill(**s) for s in v["skills"]] for k, v in raw["clusters"].items()},
        cluster_labels={k: v["label"] for k, v in raw["clusters"].items()},
    )
```

- [ ] **Step 4: Write taxonomy.yaml**

Structure (write all six clusters; ~85–100 skills total; every alias lowercase; the list below is the required minimum per cluster — add peers in the same style):
```yaml
clusters:
  software_foundations:
    label: Software foundations
    skills:
      - {canonical: python, label: Python, aliases: [python3, py], definition: Writing production Python}
      - {canonical: typescript, label: TypeScript / JavaScript, aliases: [javascript, node, node.js, nodejs, js, ts], definition: Building in the JS/TS ecosystem}
      - {canonical: react, label: React / frontend, aliases: [next.js, nextjs, frontend development, front-end], definition: Building web UIs}
      - {canonical: java, label: Java / JVM, aliases: [kotlin, scala, jvm, spring, spring boot], definition: JVM-language backend work}
      - {canonical: go, label: Go, aliases: [golang], definition: Writing Go}
      - {canonical: rust, label: Rust, aliases: [], definition: Writing Rust}
      - {canonical: cpp, label: C / C++, aliases: [c++, "c/c++"], definition: Systems programming in C or C++}
      - {canonical: git, label: Git & code review, aliases: [github, version control, pull requests], definition: Collaborating through version control}
      - {canonical: testing, label: Testing, aliases: [unit tests, integration tests, tdd, test automation], definition: Writing automated tests}
      - {canonical: system_design, label: System design, aliases: [architecture, distributed systems, scalable systems, software architecture], definition: Designing services and their interactions}
      - {canonical: algorithms, label: Algorithms & data structures, aliases: [data structures, computer science fundamentals, cs fundamentals], definition: Classic CS fundamentals}
      - {canonical: debugging, label: Debugging & troubleshooting, aliases: [troubleshooting, root cause analysis, root-cause], definition: Diagnosing failures in unfamiliar systems}
      - {canonical: shell, label: Linux & shell, aliases: [bash, linux, unix, command line, cli], definition: Working on the command line}
      - {canonical: async_concurrency, label: Concurrency & async, aliases: [asyncio, multithreading, concurrency], definition: Concurrent or asynchronous programming}
  ai_application_engineering:
    label: AI application engineering
    skills:
      - {canonical: llm_apis, label: LLM APIs, aliases: [openai api, anthropic api, claude api, gpt, foundation models, large language models, llms, llm], definition: Building on hosted LLM APIs}
      - {canonical: prompt_engineering, label: Prompt engineering, aliases: [prompting, prompt design, system prompts], definition: Designing and iterating prompts}
      - {canonical: rag, label: RAG & retrieval, aliases: [retrieval augmented generation, retrieval-augmented generation, vector search, embeddings, semantic search], definition: Retrieval pipelines over private data}
      - {canonical: vector_databases, label: Vector databases, aliases: [pinecone, weaviate, pgvector, chroma, qdrant, milvus], definition: Operating a vector store}
      - {canonical: agents, label: Agents & tool use, aliases: [agentic, agentic workflows, tool calling, function calling, multi-agent, ai agents], definition: Building LLM agents that call tools}
      - {canonical: llm_frameworks, label: LLM frameworks, aliases: [langchain, langgraph, llamaindex, llama index, dspy, semantic kernel], definition: Using an LLM orchestration framework}
      - {canonical: evals, label: Evals & quality measurement, aliases: [evaluation, evaluations, llm evaluation, benchmarks, golden sets, eval frameworks], definition: Measuring model/application quality systematically}
      - {canonical: fine_tuning, label: Fine-tuning, aliases: [finetuning, lora, rlhf, sft, model training], definition: Adapting model weights}
      - {canonical: ml_fundamentals, label: ML fundamentals, aliases: [machine learning, deep learning, pytorch, tensorflow, neural networks, statistics], definition: Classical ML / DL background}
      - {canonical: nlp, label: NLP, aliases: [natural language processing, text processing], definition: Language-processing techniques}
      - {canonical: computer_vision, label: Computer vision, aliases: [cv, image models, ocr, document understanding, multimodal], definition: Vision or document-image models}
      - {canonical: speech, label: Speech / voice, aliases: [asr, tts, voice agents, speech recognition, text-to-speech], definition: Speech-based products}
      - {canonical: llm_observability, label: LLM observability & tracing, aliases: [tracing, langsmith, langfuse, braintrust, monitoring llm], definition: Observing LLM apps in production}
      - {canonical: guardrails_safety, label: Guardrails & safety, aliases: [guardrails, responsible ai, ai safety, hallucination mitigation, content moderation], definition: Constraining model behaviour}
      - {canonical: model_serving, label: Model serving & inference, aliases: [inference, vllm, model deployment, triton, gpu inference, latency optimization], definition: Serving models efficiently}
      - {canonical: cloud_platforms, label: Cloud platforms (generic), aliases: [cloud, cloud infrastructure, public cloud, cloud services], definition: Unspecified cloud provider experience}
  data_and_integrations:
    label: Data & integrations
    skills:
      - {canonical: sql, label: SQL & relational DBs, aliases: [postgres, postgresql, mysql, relational databases, databases], definition: Querying and modelling relational data}
      - {canonical: nosql, label: NoSQL stores, aliases: [mongodb, dynamodb, redis, cassandra, document databases], definition: Non-relational data stores}
      - {canonical: rest_apis, label: REST / API integration, aliases: [apis, rest, restful, api integration, api design, graphql, grpc, webhooks], definition: Integrating with or designing HTTP APIs}
      - {canonical: data_pipelines, label: Data pipelines & ETL, aliases: [etl, elt, airflow, dbt, data engineering, spark, pyspark, batch processing], definition: Moving and transforming data at scale}
      - {canonical: streaming, label: Streaming & messaging, aliases: [kafka, event streaming, pub/sub, pubsub, message queues, rabbitmq], definition: Event-driven data flow}
      - {canonical: data_warehouses, label: Data warehouses & lakehouses, aliases: [snowflake, bigquery, redshift, databricks, delta lake, lakehouse], definition: Analytical data platforms}
      - {canonical: enterprise_systems, label: Enterprise systems (ERP/CRM), aliases: [salesforce, sap, servicenow, workday, crm, erp, epic, legacy systems], definition: Integrating with enterprise line-of-business systems}
      - {canonical: data_modeling, label: Data modelling & schemas, aliases: [schema design, data modeling, ontology, knowledge graphs], definition: Designing data structures for a domain}
      - {canonical: unstructured_data, label: Unstructured data processing, aliases: [document parsing, pdf parsing, document processing, data extraction, web scraping], definition: Turning documents and text into structured data}
      - {canonical: data_quality, label: Data quality & cleaning, aliases: [data cleaning, data validation, data wrangling], definition: Making messy customer data usable}
      - {canonical: analytics, label: Analytics & dashboards, aliases: [pandas, data analysis, tableau, looker, bi, business intelligence, jupyter], definition: Analysing and presenting data}
      - {canonical: auth_identity, label: Auth & identity, aliases: [sso, oauth, saml, okta, authentication, authorization, iam], definition: Identity integration}
  deployment_and_operations:
    label: Deployment & operations
    skills:
      - {canonical: aws, label: AWS, aliases: [amazon web services, ec2, s3, lambda, eks, bedrock, sagemaker], definition: Building or deploying on AWS}
      - {canonical: gcp, label: Google Cloud, aliases: [google cloud platform, gke, vertex ai, vertex, bigquery ml], definition: Building or deploying on GCP}
      - {canonical: azure, label: Azure, aliases: [microsoft azure, azure openai, aks], definition: Building or deploying on Azure}
      - {canonical: docker, label: Docker & containers, aliases: [containers, containerization, containerisation], definition: Packaging software in containers}
      - {canonical: kubernetes, label: Kubernetes, aliases: [k8s, helm, container orchestration], definition: Operating workloads on Kubernetes}
      - {canonical: ci_cd, label: CI/CD, aliases: [github actions, continuous integration, continuous delivery, continuous deployment, jenkins, gitlab ci, build pipelines], definition: Automated build and deploy pipelines}
      - {canonical: iac, label: Infrastructure as code, aliases: [terraform, pulumi, cloudformation, ansible, infrastructure-as-code], definition: Declarative infrastructure}
      - {canonical: observability, label: Observability & monitoring, aliases: [monitoring, logging, metrics, datadog, grafana, prometheus, alerting, opentelemetry], definition: Seeing what production is doing}
      - {canonical: on_prem_airgapped, label: On-prem / air-gapped deployment, aliases: [on-premise, on premise, on-prem, air-gapped, airgapped, vpc deployment, customer environment, private cloud, self-hosted], definition: Deploying into customer-controlled environments}
      - {canonical: security_compliance, label: Security & compliance, aliases: [soc 2, soc2, hipaa, gdpr, fedramp, security best practices, compliance, data privacy, encryption], definition: Meeting security and regulatory requirements}
      - {canonical: networking, label: Networking, aliases: [vpc, dns, load balancing, firewalls, vpn, tcp/ip], definition: Network-level infrastructure}
      - {canonical: incident_response, label: Incident response & on-call, aliases: [on-call, oncall, incident management, sre, site reliability, reliability], definition: Keeping production up}
      - {canonical: gpu_infra, label: GPU infrastructure, aliases: [gpus, cuda, gpu clusters, nvidia], definition: Operating GPU compute}
      - {canonical: cost_performance, label: Performance & cost optimisation, aliases: [performance tuning, cost optimization, cost optimisation, scalability, optimization], definition: Making systems faster or cheaper}
      - {canonical: serverless, label: Serverless & managed services, aliases: [cloud functions, managed services, paas], definition: Function-as-a-service deployments}
  customer_delivery:
    label: Customer delivery
    skills:
      - {canonical: customer_facing, label: Customer-facing engineering, aliases: [client-facing, client facing, customer facing, working directly with customers, customer engagement], definition: Working directly with customers as an engineer}
      - {canonical: scoping, label: Scoping & discovery, aliases: [requirements gathering, discovery, needs assessment, use case identification, solution scoping, define requirements], definition: Turning a customer problem into a bounded deliverable}
      - {canonical: stakeholder_communication, label: Stakeholder communication, aliases: [executive communication, executive stakeholders, c-level, presenting to leadership, stakeholder management, communicate with stakeholders], definition: Communicating with senior customer stakeholders}
      - {canonical: prototyping, label: Rapid prototyping & POCs, aliases: [proof of concept, proofs of concept, poc, pocs, pilots, pilot, mvp, rapid prototyping, demos, demo], definition: Building quick proofs of value}
      - {canonical: implementation_onboarding, label: Implementation & onboarding, aliases: [onboarding, implementation, rollout, go-live, deployment to customers, customer deployment], definition: Getting the product live at a customer}
      - {canonical: project_management, label: Project & engagement management, aliases: [project management, engagement management, delivery management, timelines, milestones], definition: Running the engagement}
      - {canonical: technical_support, label: Technical support & escalation, aliases: [escalations, escalation, customer support, support engineering, tier 3, tier-3], definition: Handling customer technical issues}
      - {canonical: travel_onsite, label: Travel & on-site work, aliases: [travel, on-site, onsite, on site, embedded with customers, embed with customers], definition: Physically working at customer sites}
      - {canonical: training_enablement, label: Training & enablement, aliases: [enablement, training customers, workshops, documentation for customers, playbooks], definition: Teaching customers to use the product}
      - {canonical: consulting, label: Consulting & advisory, aliases: [advisory, trusted advisor, consulting experience, professional services], definition: Advising customers on approach}
      - {canonical: pre_sales, label: Pre-sales & solutions engineering, aliases: [pre-sales, presales, sales engineering, solutions engineering, technical sales, rfp], definition: Supporting deals technically}
      - {canonical: domain_expertise, label: Domain / industry expertise, aliases: [industry expertise, domain knowledge, healthcare, financial services, fintech, legal, government, defense, manufacturing, insurance], definition: Knowing a customer vertical}
      - {canonical: expectation_management, label: Expectation & risk management, aliases: [managing expectations, risk management, navigating ambiguity, ambiguity], definition: Keeping customers aligned under uncertainty}
  product_thinking_and_communication:
    label: Product thinking & communication
    skills:
      - {canonical: product_sense, label: Product sense, aliases: [product thinking, product mindset, product intuition, user needs, user empathy], definition: Judging what to build and why}
      - {canonical: product_feedback_loop, label: Feeding insight back to product, aliases: [product feedback, inform the roadmap, influence roadmap, voice of the customer, work with product team], definition: Turning field learning into product change}
      - {canonical: written_communication, label: Written communication, aliases: [writing, documentation, technical writing, write clearly, clear writing], definition: Writing that others act on}
      - {canonical: verbal_communication, label: Verbal communication & presenting, aliases: [communication skills, presentation, presenting, public speaking, verbal], definition: Explaining technical work aloud}
      - {canonical: cross_functional, label: Cross-functional collaboration, aliases: [collaboration, cross-functional, work with sales, work with engineering, work across teams, teamwork], definition: Working across internal functions}
      - {canonical: ownership_autonomy, label: Ownership & autonomy, aliases: [ownership, self-directed, autonomy, self-starter, bias for action, entrepreneurial, scrappy, startup mindset], definition: Operating without close direction}
      - {canonical: prioritization, label: Prioritisation & tradeoffs, aliases: [prioritization, prioritisation, tradeoffs, trade-offs, time management, juggle multiple], definition: Choosing what matters under constraint}
      - {canonical: mentoring_leadership, label: Mentoring & technical leadership, aliases: [mentoring, mentorship, technical leadership, lead engineers, team lead], definition: Raising others' bar}
      - {canonical: business_acumen, label: Business acumen & ROI, aliases: [business value, roi, business outcomes, commercial awareness, value realization], definition: Connecting work to customer value}
      - {canonical: learning_agility, label: Learning agility, aliases: [fast learner, quick learner, learn quickly, curiosity, curious, adaptability, adaptable], definition: Picking up new domains quickly}
      - {canonical: metrics_measurement, label: Success metrics & measurement, aliases: [kpis, success metrics, define metrics, measure impact, outcomes], definition: Defining and tracking outcome metrics}
```

- [ ] **Step 5: Run tests** — `uv run pytest tests/test_taxonomy.py -v` → PASS. (If the count assertion fails, add/remove peers until 80–110.)

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: closed skill taxonomy and loader

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 7: USER CHECKPOINT 1** — Show the user `taxonomy.yaml` (cluster counts + full skill list). Do not start Task 12 (`prepare`) until they approve. Tasks 4–11 may proceed in the meantime since they do not depend on the taxonomy.

---

### Task 4: Title filter, normalisers, dedupe, size hint

**Files:**
- Modify: `sources/base.py`
- Create: `sources/companies.yaml`, `tests/test_filters.py`

**Interfaces:**
- Produces: `matches_title(title) -> bool`, `normalize_company(s) -> str`, `normalize_title(s) -> str`, `dedupe(postings: list[Posting]) -> list[Posting]`, `size_hint(company) -> str`, `travel_mentioned(text) -> bool`, `seniority_raw(title) -> str`, `SIZE_MAP: dict[str,str]`.

- [ ] **Step 1: Write failing tests**

`tests/test_filters.py`:
```python
from sources import base
from sources.base import Posting


def P(**kw):
    d = dict(id="x", title="Forward Deployed Engineer", company="Acme", url="u", full_text="t", source="s")
    d.update(kw)
    return Posting(**d)


def test_matches_title_positive():
    for t in ["Forward Deployed Engineer", "Forward-Deployed AI Engineer, Enterprise", "Senior FDE",
              "Deployment Engineer", "Solutions Engineer (AI)", "Applied AI Engineer", "Field Engineer",
              "Implementation Engineer, AI", "Forward Deployed Software Engineer - London"]:
        assert base.matches_title(t), t


def test_matches_title_negative():
    for t in ["Software Engineer", "Solutions Engineer", "Account Executive", "Field Marketing Manager",
              "Deployment Strategist Intern"]:
        assert not base.matches_title(t), t


def test_normalize_company():
    assert base.normalize_company("Scale AI, Inc.") == "scale"
    assert base.normalize_company("Harvey.com") == "harvey"
    assert base.normalize_company("Anthropic") == "anthropic"


def test_normalize_title():
    assert base.normalize_title("Senior Forward Deployed Engineer (Remote - US) [Req 123]") == "forward deployed engineer"
    assert base.normalize_title("Forward-Deployed Engineer, Staff") == "forward deployed engineer"


def test_dedupe_keeps_longest_text():
    a = P(id="a", company="Scale AI", title="Forward Deployed Engineer", full_text="short")
    b = P(id="b", company="Scale, Inc", title="Senior Forward Deployed Engineer", full_text="much longer text")
    c = P(id="c", company="Other", title="Forward Deployed Engineer")
    out = base.dedupe([a, b, c])
    assert [p.id for p in out] == ["b", "c"]


def test_size_hint_and_travel():
    assert base.size_hint("Palantir Technologies") == "enterprise"
    assert base.size_hint("Decagon") == "startup"
    assert base.size_hint("Unknown Co") == "unknown"
    assert base.travel_mentioned("Expect up to 25% travel to customer sites")
    assert not base.travel_mentioned("Fully remote role")


def test_seniority_raw():
    assert base.seniority_raw("Senior Forward Deployed Engineer") == "senior"
    assert base.seniority_raw("Staff FDE") == "staff"
    assert base.seniority_raw("Forward Deployed Engineer") == ""
```

- [ ] **Step 2: Run to verify fail** — `uv run pytest tests/test_filters.py -v` → FAIL AttributeError.

- [ ] **Step 3: Append to sources/base.py**

```python
# ---------- title filtering ----------
TITLE_PATTERNS = [
    r"forward[\s-]*deployed",
    r"\bfde\b",
    r"\bdeployment engineer\b",
    r"solutions? engineer.*\b(ai|ml|llm|genai)\b",
    r"\b(ai|ml|llm|genai)\b.*solutions? engineer",
    r"applied ai engineer",
    r"\bfield engineer\b",
    r"implementation engineer.*\b(ai|ml|llm)\b",
    r"\b(ai|ml|llm)\b.*implementation engineer",
]
_TITLE_RES = [re.compile(p, re.I) for p in TITLE_PATTERNS]


def matches_title(title: str) -> bool:
    return any(r.search(title) for r in _TITLE_RES)


# ---------- normalisation ----------
_COMPANY_STRIP = re.compile(r"[,.]?\s*\b(inc|llc|ltd|labs|ai|technologies|technology|corp|corporation|co)\b\.?|\.com|\.ai", re.I)
_SENIORITY_WORDS = r"(senior|sr\.?|staff|principal|lead|junior|jr\.?|associate|intern|ii|iii|iv|entry[- ]level|mid[- ]level)"
_TITLE_STRIP = [re.compile(r"\(.*?\)|\[.*?\]"), re.compile(r"\s[-–—|]\s.*$|[,:|].*$"), re.compile(rf"\b{_SENIORITY_WORDS}\b", re.I)]


def normalize_company(s: str) -> str:
    s = _COMPANY_STRIP.sub("", s.lower())
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def normalize_title(s: str) -> str:
    for r in _TITLE_STRIP:
        s = r.sub("", s)
    s = s.replace("-", " ")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", s.lower())).strip()


def dedupe(postings: list[Posting]) -> list[Posting]:
    """Keep one posting per (normalized_company, normalized_title); prefer the longest full_text."""
    best: dict[tuple[str, str], Posting] = {}
    order: list[tuple[str, str]] = []
    for p in postings:
        key = (normalize_company(p.company), normalize_title(p.title))
        if key not in best:
            order.append(key)
            best[key] = p
        elif len(p.full_text) > len(best[key].full_text):
            best[key] = p
    return [best[k] for k in order]


SIZE_MAP = {  # normalized company -> hint; extend as discover resolves more boards
    "enterprise": ["palantir", "databricks", "snowflake", "salesforce", "microsoft", "google", "amazon", "oracle", "ibm", "nvidia", "servicenow", "c3", "uipath", "datadog"],
    "scaleup": ["openai", "anthropic", "scale", "cohere", "glean", "harvey", "sierra", "mistral", "perplexity", "writer", "cresta", "anyscale", "weights biases", "vercel", "together", "fireworks", "hebbia", "abridge", "hippocratic", "adept", "runway", "elevenlabs", "notion", "figma", "rippling", "ramp", "brex", "retool", "samsara", "verkada"],
    "startup": ["decagon", "modal", "replicate", "baseten", "langchain", "pinecone", "weaviate", "braintrust", "langfuse", "unstructured", "vellum", "humanloop", "lamini", "contextual", "reducto", "extend", "eve", "norm", "tennr", "rilla", "hex", "distyl", "distyl ai", "rox", "ema", "sana", "eleos", "assort", "parloa", "poly", "clay", "11x", "artisan"],
}


def size_hint(company: str) -> str:
    n = normalize_company(company)
    for hint, names in SIZE_MAP.items():
        if n in names:
            return hint
    return "unknown"


_TRAVEL_RE = re.compile(r"\btravel(ling)?\b|on[- ]site at (customer|client)|\d{1,2}\s?%\s*(of\s+)?(travel|time)", re.I)


def travel_mentioned(text: str) -> bool:
    return bool(_TRAVEL_RE.search(text))


_SENIORITY_RE = re.compile(rf"\b{_SENIORITY_WORDS}\b", re.I)


def seniority_raw(title: str) -> str:
    m = _SENIORITY_RE.search(title)
    if not m:
        return ""
    w = m.group(1).lower().rstrip(".")
    return {"sr": "senior", "jr": "junior"}.get(w, w)
```

- [ ] **Step 4: Run tests** — `uv run pytest tests/test_filters.py -v` → PASS. Adjust `SIZE_MAP` names if `normalize_company` produces a different form (test by printing).

- [ ] **Step 5: Write sources/companies.yaml**

```yaml
# Candidate company names. `discover` writes resolved slugs under `resolved:`.
# Slug variants tried: lowercase-no-spaces, lowercase-hyphenated, plus any listed in `slugs:`.
candidates:
  - {name: Anthropic}
  - {name: OpenAI, slugs: [openai]}
  - {name: Scale AI, slugs: [scaleai, scale]}
  - {name: Sierra, slugs: [sierra]}
  - {name: Cohere}
  - {name: Databricks}
  - {name: Palantir}
  - {name: Glean}
  - {name: Harvey, slugs: [harvey]}
  - {name: Decagon}
  - {name: Mistral AI, slugs: [mistral]}
  - {name: Perplexity, slugs: [perplexityai, perplexity]}
  - {name: Writer, slugs: [writer]}
  - {name: Cresta}
  - {name: Hebbia}
  - {name: Anyscale}
  - {name: Modal, slugs: [modal, modallabs]}
  - {name: Replicate}
  - {name: Baseten}
  - {name: Weights & Biases, slugs: [wandb]}
  - {name: Together AI, slugs: [togetherai, together]}
  - {name: Fireworks AI, slugs: [fireworksai, fireworks]}
  - {name: LangChain, slugs: [langchain]}
  - {name: Pinecone}
  - {name: Weaviate}
  - {name: Snowflake}
  - {name: C3 AI, slugs: [c3ai, c3]}
  - {name: Abridge}
  - {name: Hippocratic AI, slugs: [hippocraticai]}
  - {name: ElevenLabs, slugs: [elevenlabs]}
  - {name: Runway, slugs: [runwayml, runway]}
  - {name: Adept}
  - {name: Contextual AI, slugs: [contextualai]}
  - {name: Unstructured, slugs: [unstructured, unstructuredio]}
  - {name: Vellum, slugs: [vellum, vellumai]}
  - {name: Braintrust, slugs: [braintrust, braintrustdata]}
  - {name: Reducto}
  - {name: Distyl AI, slugs: [distyl, distylai]}
  - {name: Tennr}
  - {name: Rilla}
  - {name: Hex, slugs: [hex, hextechnologies]}
  - {name: Notion}
  - {name: Retool}
  - {name: Rippling}
  - {name: Ramp}
  - {name: Brex}
  - {name: Samsara}
  - {name: Verkada}
  - {name: Vercel}
  - {name: Datadog}
  - {name: UiPath}
  - {name: Ema, slugs: [ema, emaunlimited]}
  - {name: Sana, slugs: [sana, sanalabs]}
  - {name: Parloa}
  - {name: Eleos Health, slugs: [eleos, eleoshealth]}
  - {name: Assort Health, slugs: [assorthealth]}
  - {name: Clay}
  - {name: 11x, slugs: [11x]}
  - {name: Artisan, slugs: [artisan, artisanai]}
  - {name: Rox, slugs: [rox]}
  - {name: Norm AI, slugs: [normai, norm]}
  - {name: Eve, slugs: [eve, evelegal]}
  - {name: Extend, slugs: [extend]}
  - {name: Humanloop}
  - {name: Lamini}
  - {name: Cognition, slugs: [cognition, cognitionai]}
  - {name: Sourcegraph}
  - {name: Cursor, slugs: [anysphere, cursor]}
  - {name: Windsurf, slugs: [codeium, windsurf]}
  - {name: Poolside}
  - {name: Magic, slugs: [magic]}
  - {name: Applied Intuition, slugs: [appliedintuition]}
  - {name: Shield AI, slugs: [shieldai]}
  - {name: Anduril, slugs: [andurilindustries, anduril]}
  - {name: Vannevar Labs, slugs: [vannevarlabs]}
  - {name: Rebellion Defense, slugs: [rebelliondefense]}
resolved: {}
```

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: title filter, normalisers, dedupe, company candidates

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---
### Task 5: Greenhouse, Lever, Ashby source modules

**Files:**
- Create: `sources/greenhouse.py`, `sources/lever.py`, `sources/ashby.py`, `tests/test_ats_sources.py`, `tests/fixtures/greenhouse_sample.json`, `tests/fixtures/lever_sample.json`, `tests/fixtures/ashby_sample.json`

**Interfaces:**
- Consumes: `base.cached_get`, `base.Posting`, `base.make_id`, `base.strip_html`, `base.matches_title`, `base.size_hint`, `base.travel_mentioned`, `base.seniority_raw`.
- Produces: in each module `probe(slug: str, *, refresh=False) -> bool` (board exists) and `fetch(slug: str, *, refresh=False) -> tuple[int, list[Posting]]` (`(n_fetched_on_board, title_matched_postings)`); `parse(body: str, slug: str) -> tuple[int, list[Posting]]` (pure, for tests).

- [ ] **Step 1: Record fixtures**

Fetch one real board per ATS through `cached_get` (so the raw cache is populated and never re-hit), then copy a trimmed 3-job version into `tests/fixtures/`. Keep at least one FDE-titled job in each fixture; if the live board lacks one, edit one job title in the *test fixture only* to "Forward Deployed Engineer".

```bash
uv run python -c "
from sources.base import cached_get
import json
s,b = cached_get('https://boards-api.greenhouse.io/v1/boards/anthropic/jobs?content=true','greenhouse/anthropic'); d=json.loads(b); d['jobs']=d['jobs'][:3]; json.dump(d,open('tests/fixtures/greenhouse_sample.json','w'))
s,b = cached_get('https://api.lever.co/v0/postings/palantir?mode=json','lever/palantir'); d=json.loads(b)[:3]; json.dump(d,open('tests/fixtures/lever_sample.json','w'))
s,b = cached_get('https://api.ashbyhq.com/posting-api/job-board/openai','ashby/openai'); d=json.loads(b); d['jobs']=d['jobs'][:3]; json.dump(d,open('tests/fixtures/ashby_sample.json','w'))
"
```
Then set `jobs[0].title` (Greenhouse), `[0].text` (Lever), `jobs[0].title` (Ashby) to `"Forward Deployed Engineer"` in the three fixture files.

- [ ] **Step 2: Write failing tests**

`tests/test_ats_sources.py`:
```python
import json
from pathlib import Path
from sources import greenhouse, lever, ashby

F = Path("tests/fixtures")


def test_greenhouse_parse():
    n, posts = greenhouse.parse((F / "greenhouse_sample.json").read_text(), "anthropic")
    assert n == 3 and len(posts) == 1
    p = posts[0]
    assert p.source == "greenhouse" and p.title == "Forward Deployed Engineer" and p.company == "Anthropic"
    assert p.url.startswith("https://") and "<" not in p.full_text and len(p.full_text) > 200
    assert p.posted_date and len(p.posted_date) == 10


def test_lever_parse():
    n, posts = lever.parse((F / "lever_sample.json").read_text(), "palantir")
    assert n == 3 and len(posts) == 1
    p = posts[0]
    assert p.source == "lever" and p.company == "Palantir" and len(p.full_text) > 200
    assert p.posted_date and p.posted_date[:2] == "20"


def test_ashby_parse():
    n, posts = ashby.parse((F / "ashby_sample.json").read_text(), "openai")
    assert n == 3 and len(posts) == 1
    p = posts[0]
    assert p.source == "ashby" and p.company == "Openai" and p.location and len(p.full_text) > 200


def test_parse_404_returns_empty():
    assert greenhouse.parse('{"status":404,"error":"not found"}', "x") == (0, [])
    assert lever.parse("Not Found", "x") == (0, [])
    assert ashby.parse("Not Found", "x") == (0, [])
```

- [ ] **Step 3: Run to verify fail** — `uv run pytest tests/test_ats_sources.py -v` → FAIL.

- [ ] **Step 4: Implement the three modules**

`sources/greenhouse.py`:
```python
"""Greenhouse public board API."""
from __future__ import annotations

import json

from sources import base
from sources.base import Posting

NAME = "greenhouse"


def _url(slug: str) -> str:
    return f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"


def _company(slug: str, jobs: list[dict]) -> str:
    return (jobs[0].get("company_name") if jobs else None) or slug.replace("-", " ").title()


def parse(body: str, slug: str) -> tuple[int, list[Posting]]:
    try:
        d = json.loads(body)
    except json.JSONDecodeError:
        return 0, []
    jobs = d.get("jobs") if isinstance(d, dict) else None
    if not jobs:
        return 0, []
    company = _company(slug, jobs)
    out = []
    for j in jobs:
        if not base.matches_title(j["title"]):
            continue
        text = base.strip_html(j.get("content") or "")
        loc = (j.get("location") or {}).get("name", "")
        out.append(Posting(
            id=base.make_id(NAME, str(j["id"])), title=j["title"], company=company,
            company_size_hint=base.size_hint(company), location=loc,
            remote_flag="remote" in (loc + " " + j["title"]).lower(),
            travel_mentioned=base.travel_mentioned(text), seniority_raw=base.seniority_raw(j["title"]),
            url=j["absolute_url"], posted_date=(j.get("first_published") or j.get("updated_at") or "")[:10] or None,
            full_text=text, source=NAME,
        ))
    return len(jobs), out


def probe(slug: str, *, refresh: bool = False) -> bool:
    status, _ = base.cached_get(_url(slug), f"{NAME}/{slug}", refresh=refresh)
    return status == 200


def fetch(slug: str, *, refresh: bool = False) -> tuple[int, list[Posting]]:
    status, body = base.cached_get(_url(slug), f"{NAME}/{slug}", refresh=refresh)
    return parse(body, slug) if status == 200 else (0, [])
```

`sources/lever.py`:
```python
"""Lever public postings API."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sources import base
from sources.base import Posting

NAME = "lever"


def _url(slug: str) -> str:
    return f"https://api.lever.co/v0/postings/{slug}?mode=json"


def parse(body: str, slug: str) -> tuple[int, list[Posting]]:
    try:
        jobs = json.loads(body)
    except json.JSONDecodeError:
        return 0, []
    if not isinstance(jobs, list) or not jobs:
        return 0, []
    company = slug.replace("-", " ").title()
    out = []
    for j in jobs:
        title = j.get("text", "")
        if not base.matches_title(title):
            continue
        parts = [j.get("descriptionPlain", "")]
        for lst in j.get("lists", []):
            parts.append(lst.get("text", ""))
            parts.append(base.strip_html(lst.get("content", "")))
        parts.append(j.get("additionalPlain", ""))
        text = "\n".join(p for p in parts if p)
        cats = j.get("categories", {})
        loc = cats.get("location", "") or ", ".join(cats.get("allLocations", []))
        created = j.get("createdAt")
        posted = datetime.fromtimestamp(created / 1000, tz=timezone.utc).date().isoformat() if created else None
        out.append(Posting(
            id=base.make_id(NAME, j["id"]), title=title, company=company,
            company_size_hint=base.size_hint(company), location=loc,
            remote_flag=(j.get("workplaceType") == "remote") or "remote" in loc.lower(),
            travel_mentioned=base.travel_mentioned(text), seniority_raw=base.seniority_raw(title),
            url=j["hostedUrl"], posted_date=posted, full_text=text, source=NAME,
        ))
    return len(jobs), out


def probe(slug: str, *, refresh: bool = False) -> bool:
    status, _ = base.cached_get(_url(slug), f"{NAME}/{slug}", refresh=refresh)
    return status == 200


def fetch(slug: str, *, refresh: bool = False) -> tuple[int, list[Posting]]:
    status, body = base.cached_get(_url(slug), f"{NAME}/{slug}", refresh=refresh)
    return parse(body, slug) if status == 200 else (0, [])
```

`sources/ashby.py`:
```python
"""Ashby public job-board API."""
from __future__ import annotations

import json

from sources import base
from sources.base import Posting

NAME = "ashby"


def _url(slug: str) -> str:
    return f"https://api.ashbyhq.com/posting-api/job-board/{slug}"


def parse(body: str, slug: str) -> tuple[int, list[Posting]]:
    try:
        d = json.loads(body)
    except json.JSONDecodeError:
        return 0, []
    jobs = d.get("jobs") if isinstance(d, dict) else None
    if not jobs:
        return 0, []
    company = slug.replace("-", " ").title()
    out = []
    for j in jobs:
        if not j.get("isListed", True) or not base.matches_title(j["title"]):
            continue
        text = j.get("descriptionPlain") or base.strip_html(j.get("descriptionHtml", ""))
        loc = j.get("location", "") or ""
        out.append(Posting(
            id=base.make_id(NAME, j["id"]), title=j["title"], company=company,
            company_size_hint=base.size_hint(company), location=loc,
            remote_flag=bool(j.get("isRemote")) or "remote" in loc.lower(),
            travel_mentioned=base.travel_mentioned(text), seniority_raw=base.seniority_raw(j["title"]),
            url=j["jobUrl"], posted_date=(j.get("publishedAt") or "")[:10] or None,
            full_text=text, source=NAME,
        ))
    return len(jobs), out


def probe(slug: str, *, refresh: bool = False) -> bool:
    status, body = base.cached_get(_url(slug), f"{NAME}/{slug}", refresh=refresh)
    return status == 200 and '"jobs"' in body


def fetch(slug: str, *, refresh: bool = False) -> tuple[int, list[Posting]]:
    status, body = base.cached_get(_url(slug), f"{NAME}/{slug}", refresh=refresh)
    return parse(body, slug) if status == 200 else (0, [])
```

- [ ] **Step 5: Run tests** — `uv run pytest tests/test_ats_sources.py -v` → PASS.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: Greenhouse, Lever, Ashby source modules

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: HN Who Is Hiring source

**Files:**
- Create: `sources/hn.py`, `tests/test_hn.py`, `tests/fixtures/hn_comments_sample.json`

**Interfaces:**
- Produces: `hn.fetch(*, months=4, refresh=False) -> tuple[int, list[Posting]]`, `hn.parse_comment(hit: dict) -> Posting | None`, `hn.list_threads(*, months, refresh) -> list[dict]` (`objectID`, `title`, `created_at`).

- [ ] **Step 1: Record fixture**

```bash
uv run python -c "
from sources.base import cached_get; import json
s,b = cached_get('https://hn.algolia.com/api/v1/search_by_date?query=%22forward%20deployed%22&tags=comment,story_49522897&hitsPerPage=1000','hn/thread_49522897_q0')
d=json.loads(b); d['hits']=d['hits'][:3]; json.dump(d,open('tests/fixtures/hn_comments_sample.json','w'))"
```

- [ ] **Step 2: Write failing tests**

`tests/test_hn.py`:
```python
import json
from pathlib import Path
from sources import hn

HIT = {"objectID": "1", "story_id": 9, "parent_id": 9, "created_at": "2026-09-11T10:39:33Z",
       "comment_text": "Cider Consulting | NY, USA | REMOTE (US-based only)<p>We are hiring a Forward Deployed Engineer to own engagements end-to-end. Travel 20%."}


def test_parse_comment_top_level():
    p = hn.parse_comment(HIT)
    assert p.company == "Cider Consulting" and p.location == "NY, USA"
    assert p.remote_flag and p.travel_mentioned and p.source == "hn"
    assert p.title == "Forward Deployed Engineer"
    assert p.posted_date == "2026-09-11" and p.company_size_hint == "startup"
    assert p.url == "https://news.ycombinator.com/item?id=1"


def test_parse_comment_skips_replies_and_non_matching():
    assert hn.parse_comment({**HIT, "parent_id": 5}) is None
    assert hn.parse_comment({**HIT, "comment_text": "Acme | SF | Hiring a Data Scientist"}) is None


def test_parse_fixture():
    d = json.loads(Path("tests/fixtures/hn_comments_sample.json").read_text())
    posts = [p for p in map(hn.parse_comment, d["hits"]) if p]
    assert len(posts) >= 1
```

- [ ] **Step 3: Run to verify fail** — `uv run pytest tests/test_hn.py -v` → FAIL.

- [ ] **Step 4: Implement sources/hn.py**

```python
"""HN 'Who is hiring?' via Algolia search API."""
from __future__ import annotations

import json
import re
from urllib.parse import quote

from sources import base
from sources.base import Posting

NAME = "hn"
API = "https://hn.algolia.com/api/v1/search_by_date"
THREAD_QUERY = '"Ask HN: Who is hiring?"'
QUERIES = ['"forward deployed"', '"deployment engineer"', '"applied ai engineer"', '"solutions engineer"',
           '"field engineer"', '"implementation engineer"', '"fde"']
_TITLE_IN_TEXT = re.compile(
    r"(Senior |Staff |Lead |Principal |Founding )?(Forward[\s-]Deployed (AI |Software )?Engineer|FDE|Deployment Engineer|"
    r"Applied AI Engineer|Solutions Engineer \(?AI\)?|AI Solutions Engineer|Field Engineer|Implementation Engineer)", re.I)


def list_threads(*, months: int = 4, refresh: bool = False) -> list[dict]:
    url = f"{API}?query={quote(THREAD_QUERY)}&tags=story,author_whoishiring&hitsPerPage={months}"
    status, body = base.cached_get(url, f"{NAME}/threads_{months}", refresh=refresh)
    hits = json.loads(body)["hits"] if status == 200 else []
    return [h for h in hits if h["title"].startswith("Ask HN: Who is hiring?")][:months]


def parse_comment(hit: dict) -> Posting | None:
    if hit.get("parent_id") != hit.get("story_id"):
        return None  # only top-level comments are job posts
    text = base.strip_html(hit.get("comment_text") or "")
    first, _, rest = text.partition("\n")
    fields = [f.strip() for f in first.split("|")]
    company = fields[0] if fields else ""
    m = _TITLE_IN_TEXT.search(text)
    if not company or not m or not base.matches_title(m.group(0)):
        return None
    title = re.sub(r"\s+", " ", m.group(0)).strip()
    location = fields[1] if len(fields) > 1 else ""
    return Posting(
        id=base.make_id(NAME, str(hit["objectID"])), title=title, company=company,
        company_size_hint="startup", location=location,
        remote_flag="remote" in first.lower(), travel_mentioned=base.travel_mentioned(text),
        seniority_raw=base.seniority_raw(title), url=f"https://news.ycombinator.com/item?id={hit['objectID']}",
        posted_date=(hit.get("created_at") or "")[:10] or None, full_text=text, source=NAME,
    )


def fetch(*, months: int = 4, refresh: bool = False) -> tuple[int, list[Posting]]:
    seen, out, fetched = set(), [], 0
    for th in list_threads(months=months, refresh=refresh):
        for qi, q in enumerate(QUERIES):
            url = f"{API}?query={quote(q)}&tags=comment,story_{th['objectID']}&hitsPerPage=1000"
            status, body = base.cached_get(url, f"{NAME}/thread_{th['objectID']}_q{qi}", refresh=refresh)
            if status != 200:
                continue
            for hit in json.loads(body)["hits"]:
                fetched += 1
                if hit["objectID"] in seen:
                    continue
                seen.add(hit["objectID"])
                p = parse_comment(hit)
                if p:
                    out.append(p)
    return fetched, out
```

- [ ] **Step 5: Run tests** — `uv run pytest tests/test_hn.py -v` → PASS.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: HN Who Is Hiring source

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: Remotive and Arbeitnow sources

**Files:**
- Create: `sources/remotive.py`, `sources/arbeitnow.py`, `tests/test_boards.py`, `tests/fixtures/remotive_sample.json`, `tests/fixtures/arbeitnow_sample.json`

**Interfaces:**
- Produces: `remotive.fetch(*, refresh=False) -> tuple[int, list[Posting]]`, `arbeitnow.fetch(*, pages=20, refresh=False) -> tuple[int, list[Posting]]`, and `parse(body) -> tuple[int, list[Posting]]` in each.

- [ ] **Step 1: Record fixtures**

```bash
uv run python -c "
from sources.base import cached_get; import json
s,b = cached_get('https://remotive.com/api/remote-jobs?search=forward+deployed','remotive/search_forward_deployed'); d=json.loads(b); d['jobs']=d['jobs'][:3]; json.dump(d,open('tests/fixtures/remotive_sample.json','w'))
s,b = cached_get('https://www.arbeitnow.com/api/job-board-api?page=1','arbeitnow/page_1'); d=json.loads(b); d['data']=d['data'][:3]; json.dump(d,open('tests/fixtures/arbeitnow_sample.json','w'))"
```
Then set `jobs[0].title` / `data[0].title` in the fixtures to `"Forward Deployed Engineer"`.

- [ ] **Step 2: Write failing tests**

`tests/test_boards.py`:
```python
from pathlib import Path
from sources import remotive, arbeitnow

F = Path("tests/fixtures")


def test_remotive_parse_filters_titles_locally():
    n, posts = remotive.parse((F / "remotive_sample.json").read_text())
    assert n == 3 and len(posts) == 1
    p = posts[0]
    assert p.source == "remotive" and p.remote_flag and p.company and "<" not in p.full_text
    assert p.posted_date and len(p.posted_date) == 10


def test_arbeitnow_parse():
    n, posts = arbeitnow.parse((F / "arbeitnow_sample.json").read_text())
    assert n == 3 and len(posts) == 1
    p = posts[0]
    assert p.source == "arbeitnow" and p.url.startswith("https://") and p.posted_date and p.posted_date[:2] == "20"
```

- [ ] **Step 3: Run to verify fail** — `uv run pytest tests/test_boards.py -v` → FAIL.

- [ ] **Step 4: Implement**

`sources/remotive.py`:
```python
"""Remotive public API (search is loose; filter titles locally)."""
from __future__ import annotations

import json

from sources import base
from sources.base import Posting

NAME = "remotive"
SEARCHES = ["forward deployed", "deployment engineer", "applied ai", "solutions engineer ai", "field engineer", "implementation engineer"]


def parse(body: str) -> tuple[int, list[Posting]]:
    try:
        jobs = json.loads(body).get("jobs", [])
    except (json.JSONDecodeError, AttributeError):
        return 0, []
    out = []
    for j in jobs:
        if not base.matches_title(j.get("title", "")):
            continue
        text = base.strip_html(j.get("description", ""))
        company = j.get("company_name", "")
        out.append(Posting(
            id=base.make_id(NAME, str(j["id"])), title=j["title"], company=company,
            company_size_hint=base.size_hint(company), location=j.get("candidate_required_location", ""),
            remote_flag=True, travel_mentioned=base.travel_mentioned(text), seniority_raw=base.seniority_raw(j["title"]),
            url=j["url"], posted_date=(j.get("publication_date") or "")[:10] or None, full_text=text, source=NAME,
        ))
    return len(jobs), out


def fetch(*, refresh: bool = False) -> tuple[int, list[Posting]]:
    fetched, out, seen = 0, [], set()
    for s in SEARCHES:
        key = f"{NAME}/search_{s.replace(' ', '_')}"
        status, body = base.cached_get("https://remotive.com/api/remote-jobs", key, refresh=refresh, params={"search": s})
        if status != 200:
            continue
        n, posts = parse(body)
        fetched += n
        for p in posts:
            if p.id not in seen:
                seen.add(p.id)
                out.append(p)
    return fetched, out
```

`sources/arbeitnow.py`:
```python
"""Arbeitnow public job board API (no server-side search; paginate and filter locally)."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sources import base
from sources.base import Posting

NAME = "arbeitnow"


def parse(body: str) -> tuple[int, list[Posting]]:
    try:
        jobs = json.loads(body).get("data", [])
    except (json.JSONDecodeError, AttributeError):
        return 0, []
    out = []
    for j in jobs:
        if not base.matches_title(j.get("title", "")):
            continue
        text = base.strip_html(j.get("description", ""))
        company = j.get("company_name", "")
        ts = j.get("created_at")
        out.append(Posting(
            id=base.make_id(NAME, j["slug"]), title=j["title"], company=company,
            company_size_hint=base.size_hint(company), location=j.get("location", ""),
            remote_flag=bool(j.get("remote")), travel_mentioned=base.travel_mentioned(text),
            seniority_raw=base.seniority_raw(j["title"]), url=j["url"],
            posted_date=datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat() if ts else None,
            full_text=text, source=NAME,
        ))
    return len(jobs), out


def fetch(*, pages: int = 20, refresh: bool = False) -> tuple[int, list[Posting]]:
    fetched, out = 0, []
    for page in range(1, pages + 1):
        status, body = base.cached_get("https://www.arbeitnow.com/api/job-board-api", f"{NAME}/page_{page}", refresh=refresh, params={"page": page})
        if status != 200:
            break
        n, posts = parse(body)
        if n == 0:
            break
        fetched += n
        out.extend(posts)
    return fetched, out
```

- [ ] **Step 5: Run tests** — `uv run pytest tests/test_boards.py -v` → PASS.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: Remotive and Arbeitnow sources

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---
### Task 8: Slug discovery

**Files:**
- Create: `sources/discover.py`, `tests/test_discover.py`
- Modify: `main.py` (wire `discover`)

**Interfaces:**
- Consumes: `greenhouse.probe`, `lever.probe`, `ashby.probe`, `sources/companies.yaml`.
- Produces: `discover.slug_variants(name: str, extra: list[str]) -> list[str]`, `discover.run(*, refresh=False) -> dict[str, dict[str, str]]` (`{"greenhouse": {slug: name}, "lever": {...}, "ashby": {...}}`) written back to `companies.yaml` under `resolved:`; `discover.load_companies() -> dict`.

- [ ] **Step 1: Write failing tests**

`tests/test_discover.py`:
```python
from sources import discover


def test_slug_variants():
    assert discover.slug_variants("Scale AI", ["scaleai", "scale"]) == ["scaleai", "scale", "scale-ai"]
    assert discover.slug_variants("Anthropic", []) == ["anthropic"]
    assert discover.slug_variants("Weights & Biases", ["wandb"]) == ["wandb", "weightsbiases", "weights-biases"]


def test_run_records_resolved(monkeypatch, tmp_path):
    cfg = tmp_path / "companies.yaml"
    cfg.write_text("candidates:\n  - {name: Foo, slugs: [foo]}\n  - {name: Bar}\nresolved: {}\n")
    monkeypatch.setattr(discover, "PATH", cfg)
    monkeypatch.setattr(discover, "PROBES", {"greenhouse": lambda s, refresh=False: s == "foo",
                                             "lever": lambda s, refresh=False: False,
                                             "ashby": lambda s, refresh=False: s == "bar"})
    res = discover.run()
    assert res == {"greenhouse": {"foo": "Foo"}, "lever": {}, "ashby": {"bar": "Bar"}}
    assert "resolved:" in cfg.read_text() and "foo: Foo" in cfg.read_text()
```

- [ ] **Step 2: Run to verify fail** — `uv run pytest tests/test_discover.py -v` → FAIL.

- [ ] **Step 3: Implement sources/discover.py**

```python
"""Find which ATS hosts each candidate company's board."""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from sources import ashby, greenhouse, lever

PATH = Path(__file__).resolve().parent / "companies.yaml"
PROBES = {"greenhouse": greenhouse.probe, "lever": lever.probe, "ashby": ashby.probe}


def load_companies() -> dict:
    return yaml.safe_load(PATH.read_text())


def slug_variants(name: str, extra: list[str]) -> list[str]:
    base = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", "", name.lower())).strip()
    joined, hyphen = base.replace(" ", ""), base.replace(" ", "-")
    out = list(extra)
    for v in (joined, hyphen):
        if v not in out:
            out.append(v)
    return out


def run(*, refresh: bool = False) -> dict[str, dict[str, str]]:
    cfg = load_companies()
    resolved: dict[str, dict[str, str]] = {k: {} for k in PROBES}
    for cand in cfg["candidates"]:
        name, variants = cand["name"], slug_variants(cand["name"], cand.get("slugs", []))
        for ats, probe in PROBES.items():
            for slug in variants:
                if probe(slug, refresh=refresh):
                    resolved[ats][slug] = name
                    print(f"  {ats:10s} {slug:24s} <- {name}")
                    break
        if not any(name in r.values() for r in resolved.values()):
            print(f"  unresolved  {name}")
    cfg["resolved"] = resolved
    PATH.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True))
    return resolved
```

- [ ] **Step 4: Wire main.py**

Add before the render branch:
```python
    if args.cmd == "discover":
        from sources import discover
        res = discover.run(refresh=args.refresh)
        print({k: len(v) for k, v in res.items()})
        return 0
```

- [ ] **Step 5: Run tests, then run discovery for real** — `uv run pytest tests/test_discover.py -v` → PASS. Then `uv run python main.py discover` (one-time network; all probes cached). Expect ≥ 40 resolved boards. Commit the updated `companies.yaml`.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: ATS slug discovery

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: Collect step → postings.jsonl

**Files:**
- Create: `sources/collect.py`, `tests/test_collect.py`
- Modify: `main.py` (wire `collect`)

**Interfaces:**
- Consumes: all `fetch` functions, `base.dedupe`, `discover.load_companies`.
- Produces: `collect.run(*, refresh=False) -> tuple[list[Posting], list[dict]]`; writes `data/processed/postings.jsonl` (one `Posting.model_dump_json()` per line) and `data/processed/collect_stats.json` (`[{name, fetched, matched, kept}]`); `collect.load_postings() -> list[Posting]`.

- [ ] **Step 1: Write failing test**

`tests/test_collect.py`:
```python
import json
from sources import collect
from sources.base import Posting


def P(i, company, title, text="x" * 10, source="a"):
    return Posting(id=i, title=title, company=company, url="u", full_text=text, source=source)


def test_run_dedupes_and_writes_stats(monkeypatch, tmp_path):
    monkeypatch.setattr(collect, "PROCESSED_DIR", tmp_path)
    monkeypatch.setattr(collect, "SOURCE_RUNNERS", {
        "a": lambda refresh: (10, [P("1", "Acme", "Forward Deployed Engineer"), P("2", "Acme", "Senior Forward Deployed Engineer", "longer text")]),
        "b": lambda refresh: (5, [P("3", "Beta", "FDE", source="b")]),
    })
    posts, stats = collect.run()
    assert [p.id for p in posts] == ["2", "3"]
    assert stats == [{"name": "a", "fetched": 10, "matched": 2, "kept": 1}, {"name": "b", "fetched": 5, "matched": 1, "kept": 1}]
    lines = (tmp_path / "postings.jsonl").read_text().splitlines()
    assert len(lines) == 2 and json.loads(lines[0])["id"] == "2"
    assert json.loads((tmp_path / "collect_stats.json").read_text()) == stats
    assert [p.id for p in collect.load_postings()] == ["2", "3"]
```

- [ ] **Step 2: Run to verify fail** — `uv run pytest tests/test_collect.py -v` → FAIL.

- [ ] **Step 3: Implement sources/collect.py**

```python
"""Run every source, dedupe, persist postings.jsonl + per-source stats."""
from __future__ import annotations

import json

from sources import arbeitnow, ashby, base, discover, greenhouse, hn, lever, remotive
from sources.base import Posting

PROCESSED_DIR = base.PROCESSED_DIR


def _ats_runner(module):
    def run(refresh: bool):
        slugs = discover.load_companies().get("resolved", {}).get(module.NAME, {})
        fetched, out = 0, []
        for slug in slugs:
            n, posts = module.fetch(slug, refresh=refresh)
            fetched += n
            out.extend(posts)
        return fetched, out
    return run


SOURCE_RUNNERS = {
    "greenhouse": _ats_runner(greenhouse),
    "lever": _ats_runner(lever),
    "ashby": _ats_runner(ashby),
    "hn": lambda refresh: hn.fetch(refresh=refresh),
    "remotive": lambda refresh: remotive.fetch(refresh=refresh),
    "arbeitnow": lambda refresh: arbeitnow.fetch(refresh=refresh),
}


def run(*, refresh: bool = False) -> tuple[list[Posting], list[dict]]:
    all_posts, stats = [], []
    for name, runner in SOURCE_RUNNERS.items():
        fetched, posts = runner(refresh)
        stats.append({"name": name, "fetched": fetched, "matched": len(posts), "kept": 0})
        all_posts.extend(posts)
    deduped = base.dedupe(all_posts)
    kept_by_source = {}
    for p in deduped:
        kept_by_source[p.source] = kept_by_source.get(p.source, 0) + 1
    for s in stats:
        s["kept"] = kept_by_source.get(s["name"], 0)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    (PROCESSED_DIR / "postings.jsonl").write_text("\n".join(p.model_dump_json() for p in deduped) + "\n")
    (PROCESSED_DIR / "collect_stats.json").write_text(json.dumps(stats, indent=2))
    for s in stats:
        print(f"{s['name']:10s} fetched={s['fetched']:6d} matched={s['matched']:4d} kept={s['kept']:4d}")
    print(f"TOTAL kept={len(deduped)} companies={len({base.normalize_company(p.company) for p in deduped})}")
    return deduped, stats


def load_postings() -> list[Posting]:
    path = PROCESSED_DIR / "postings.jsonl"
    return [Posting.model_validate_json(ln) for ln in path.read_text().splitlines() if ln.strip()]
```

- [ ] **Step 4: Wire main.py**

```python
    if args.cmd == "collect":
        from sources import collect
        collect.run(refresh=args.refresh)
        return 0
```

- [ ] **Step 5: Run tests, then collect for real** — `uv run pytest -v` (all green) then `uv run python main.py collect`. Report the per-source table and TOTAL to the user. If TOTAL < 300: add candidates to `companies.yaml`, re-run `discover` then `collect` (only new slugs hit the network).

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: collect step with dedupe and per-source stats

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: JD segmentation

**Files:**
- Create: `extract/segment.py`, `tests/test_segment.py`

**Interfaces:**
- Produces: `segment.segment(text: str) -> Segments` where `Segments` is pydantic `{responsibilities: str, requirements: str, nice_to_have: str, other: str, quality: Literal["header","inferred"]}`.

- [ ] **Step 1: Write failing tests**

`tests/test_segment.py`:
```python
from extract.segment import segment

JD = """About us
We build things.
What you'll do
- Deploy models for customers
- Scope engagements
What we're looking for
- 5+ years Python
- AWS experience
Nice to have
- Kubernetes
Benefits
- Health insurance
"""


def test_segments_by_headers():
    s = segment(JD)
    assert s.quality == "header"
    assert "Deploy models" in s.responsibilities and "Scope" in s.responsibilities
    assert "5+ years Python" in s.requirements and "AWS" in s.requirements
    assert "Kubernetes" in s.nice_to_have and "Kubernetes" not in s.requirements
    assert "Health insurance" in s.other and "We build things" in s.other


def test_alternate_headers():
    s = segment("Responsibilities:\nShip\nRequirements:\nPython\nBonus points:\nRust\n")
    assert s.responsibilities.strip() == "Ship" and s.requirements.strip() == "Python" and s.nice_to_have.strip() == "Rust"
    s = segment("The Role\nShip\nQualifications\nPython\nPreferred qualifications\nRust\n")
    assert "Ship" in s.responsibilities and "Python" in s.requirements and "Rust" in s.nice_to_have


def test_no_headers_is_inferred():
    s = segment("We want an engineer who can deploy and knows Python.")
    assert s.quality == "inferred" and s.other.strip() and not s.responsibilities
```

- [ ] **Step 2: Run to verify fail** — `uv run pytest tests/test_segment.py -v` → FAIL.

- [ ] **Step 3: Implement extract/segment.py**

```python
"""Split a job description into responsibility / requirement / nice-to-have sections by header lines."""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel

HEADERS = {
    "responsibilities": [r"what you('|’)ll (do|be doing|work on)", r"what you will (do|be doing)", r"responsibilities", r"the role", r"your role", r"about the role", r"in this role", r"you will", r"what you('|’)ll own", r"day[- ]to[- ]day", r"key duties", r"duties", r"what you('|’)ll be doing", r"how you('|’)ll (contribute|make an impact)"],
    "requirements": [r"what we('|’)re looking for", r"what we are looking for", r"requirements", r"qualifications", r"minimum qualifications", r"basic qualifications", r"required (skills|experience|qualifications)", r"you (have|bring|are)", r"about you", r"who you are", r"what you('|’)ll bring", r"what you bring", r"must[- ]haves?", r"skills (and|&) experience", r"experience", r"what we (require|value|need)", r"you might be a fit if", r"you('|’)re a fit if", r"ideal candidate"],
    "nice_to_have": [r"nice[- ]to[- ]haves?", r"bonus( points)?", r"preferred( qualifications| skills| experience)?", r"plus(es)?", r"it('|’)s a plus", r"extra credit", r"great if you", r"additional qualifications", r"even better if"],
    "other": [r"about (us|the (company|team))", r"benefits", r"perks", r"compensation", r"salary", r"what we offer", r"why join", r"our (mission|values)", r"equal opportunity", r"how to apply", r"interview process", r"location", r"the team"],
}
_HEADER_RES = [(sec, re.compile(rf"^\W*(?:{p})\W*$", re.I)) for sec, pats in HEADERS.items() for p in pats]


class Segments(BaseModel):
    responsibilities: str = ""
    requirements: str = ""
    nice_to_have: str = ""
    other: str = ""
    quality: Literal["header", "inferred"] = "inferred"


def _classify(line: str) -> str | None:
    if len(line) > 60:
        return None
    for sec, r in _HEADER_RES:
        if r.match(line):
            return sec
    return None


def segment(text: str) -> Segments:
    buckets = {"responsibilities": [], "requirements": [], "nice_to_have": [], "other": []}
    current, hit = "other", False
    for line in text.splitlines():
        sec = _classify(line.strip())
        if sec:
            current = sec
            hit = hit or sec != "other"
            continue
        buckets[current].append(line)
    out = {k: "\n".join(v).strip() for k, v in buckets.items()}
    quality = "header" if hit and (out["responsibilities"] or out["requirements"]) else "inferred"
    if quality == "inferred":  # nothing reliable: put everything in other
        out = {"responsibilities": "", "requirements": "", "nice_to_have": "", "other": text.strip()}
    return Segments(**out, quality=quality)
```

- [ ] **Step 4: Run tests** — `uv run pytest tests/test_segment.py -v` → PASS.

- [ ] **Step 5: Measure on real data and report**

```bash
uv run python -c "
from sources.collect import load_postings; from extract.segment import segment; from collections import Counter
print(Counter(segment(p.full_text).quality for p in load_postings()))"
```
If `inferred` > 30%, print 10 inferred postings' first 40 lines, add the missing header phrasings to `HEADERS`, re-run tests.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: JD header segmentation

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---
### Task 11: Extraction schema, prompt template, prepare step

**Files:**
- Create: `extract/schema.py`, `extract/prompt.md`, `extract/prepare.py`, `tests/test_prepare.py`
- Modify: `main.py` (wire `prepare`)

**Interfaces:**
- Consumes: `taxonomy.load()`, `segment.segment`, `collect.load_postings`.
- Produces: `schema.Extraction` (pydantic), `schema.SkillMention`, `schema.json_schema() -> dict`; `prepare.render_prompt(posting, segments, taxonomy) -> str`; `prepare.run(limit: int|None=None) -> int` writing `data/processed/prompts/{id}.md` and `data/processed/prompts/manifest.json` (`{"pending": [ids], "done": [ids]}`); `PROMPTS_DIR`, `EXTRACTIONS_DIR`, `MANIFEST`.

- [ ] **Step 1: Write failing tests**

`tests/test_prepare.py`:
```python
import json
from pydantic import ValidationError
import pytest
from extract import schema, prepare, taxonomy
from extract.segment import segment
from sources.base import Posting

GOOD = {"posting_id": "abc", "skills": [{"canonical": "python", "section": "requirement", "evidence": "Strong Python"}],
        "seniority": "senior", "years_required": 5, "travel_expectation": "occasional",
        "customer_facing_intensity": 4, "responsibility_verbs": ["build", "deploy", "scope", "own", "present"],
        "segmentation_quality": "header"}


def test_schema_accepts_good_and_rejects_bad():
    schema.Extraction(**GOOD)
    with pytest.raises(ValidationError):
        schema.Extraction(**{**GOOD, "customer_facing_intensity": 6})
    with pytest.raises(ValidationError):
        schema.Extraction(**{**GOOD, "skills": [{"canonical": "python", "section": "bonus", "evidence": "x"}]})
    with pytest.raises(ValidationError):
        schema.Extraction(**{**GOOD, "responsibility_verbs": ["a", "b"]})


def test_render_prompt_contains_taxonomy_segments_and_schema():
    p = Posting(id="abc", title="FDE", company="Acme", url="u", source="t",
                full_text="What you'll do\nDeploy models\nRequirements\nPython\n")
    txt = prepare.render_prompt(p, segment(p.full_text), taxonomy.load())
    assert "stakeholder_communication" in txt and "amazon web services" in txt
    assert "## RESPONSIBILITIES" in txt and "Deploy models" in txt
    assert '"posting_id": "abc"' in txt and "customer_facing_intensity" in txt
    assert "segmentation_quality" in txt and '"header"' in txt


def test_run_writes_prompts_and_manifest(monkeypatch, tmp_path):
    monkeypatch.setattr(prepare, "PROMPTS_DIR", tmp_path / "prompts")
    monkeypatch.setattr(prepare, "EXTRACTIONS_DIR", tmp_path / "extractions")
    monkeypatch.setattr(prepare, "MANIFEST", tmp_path / "prompts" / "manifest.json")
    posts = [Posting(id=f"id{i}", title="FDE", company="Acme", url="u", source="t", full_text="Requirements\nPython") for i in range(3)]
    monkeypatch.setattr(prepare, "load_postings", lambda: posts)
    (tmp_path / "extractions").mkdir()
    (tmp_path / "extractions" / "id1.json").write_text(json.dumps({**GOOD, "posting_id": "id1"}))
    assert prepare.run(limit=2) == 2
    m = json.loads(prepare.MANIFEST.read_text())
    assert m["pending"] == ["id0"] and m["done"] == ["id1"]
    assert (tmp_path / "prompts" / "id0.md").exists()
```

- [ ] **Step 2: Run to verify fail** — `uv run pytest tests/test_prepare.py -v` → FAIL.

- [ ] **Step 3: Implement extract/schema.py**

```python
"""Strict output contract for one posting's extraction."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

SECTION = Literal["responsibility", "requirement", "nice_to_have"]
SENIORITY = Literal["junior", "mid", "senior", "staff_plus", "unspecified"]
TRAVEL = Literal["none", "occasional", "frequent", "unspecified"]


class SkillMention(BaseModel):
    canonical: str
    section: SECTION
    evidence: str = Field(max_length=120)


class Extraction(BaseModel):
    posting_id: str
    skills: list[SkillMention]
    seniority: SENIORITY
    years_required: int | None = None
    travel_expectation: TRAVEL
    customer_facing_intensity: int = Field(ge=1, le=5)
    responsibility_verbs: list[str] = Field(min_length=5, max_length=5)
    segmentation_quality: Literal["header", "inferred"]


def json_schema() -> dict:
    return Extraction.model_json_schema()
```

- [ ] **Step 4: Write extract/prompt.md** (Jinja template)

```markdown
# Skill extraction — posting {{ posting.id }}

You are extracting structured skill requirements from ONE job posting for a Forward Deployed Engineer-type role.
Return ONLY a JSON object matching the schema at the end. No prose, no markdown fences.

## Rules
1. Use ONLY `canonical` names from the taxonomy below. Match by meaning using the aliases and definitions. If a skill in the posting has no node, OMIT it (do not invent names).
2. Tag every skill mention with the section it appears in: `responsibility` (what you will do), `requirement` (must have), `nice_to_have` (bonus / preferred). A skill may appear in more than one section — emit one entry per section it appears in, never duplicates within a section.
3. If the posting has no explicit sections (segmentation_quality = "inferred"), decide the tag from phrasing: "you will / own / build / lead" → responsibility; "must / required / X+ years / strong" → requirement; "bonus / plus / preferred / ideally" → nice_to_have.
4. `evidence`: a quote of at most 12 words from the posting that justifies the tag.
5. `seniority`: junior | mid | senior | staff_plus | unspecified — from title and years.
6. `years_required`: the minimum years stated, else null.
7. `travel_expectation`: none | occasional (≤25% or "some") | frequent (>25%, "significant", "embedded on-site") | unspecified.
8. `customer_facing_intensity`: 1 = internal only … 5 = embedded with customers most of the time.
9. `responsibility_verbs`: exactly 5 lowercase verbs, most representative of the responsibilities section (e.g. "deploy", "scope").
10. `segmentation_quality`: copy the value given below.

## Taxonomy (closed vocabulary)
{% for ckey, skills in taxonomy.clusters.items() %}
### {{ taxonomy.cluster_labels[ckey] }} ({{ ckey }})
{% for s in skills %}- `{{ s.canonical }}` — {{ s.label }}. {{ s.definition }}.{% if s.aliases %} Aliases: {{ s.aliases|join(', ') }}{% endif %}
{% endfor %}{% endfor %}

## Posting
- title: {{ posting.title }}
- company: {{ posting.company }}
- location: {{ posting.location }}
- segmentation_quality: "{{ segments.quality }}"

## RESPONSIBILITIES
{{ segments.responsibilities or "(none found)" }}

## REQUIREMENTS
{{ segments.requirements or "(none found)" }}

## NICE_TO_HAVE
{{ segments.nice_to_have or "(none found)" }}

## OTHER (context only — extract from here ONLY if the three sections above are empty)
{{ segments.other or "(none)" }}

## Output schema
Return exactly this shape with "posting_id": "{{ posting.id }}":
```json
{{ schema_json }}
```
```

- [ ] **Step 5: Implement extract/prepare.py**

```python
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
        return schema.Extraction.model_validate_json(f.read_text()).posting_id == pid
    except Exception:
        return False


def run(limit: int | None = None) -> int:
    tx = taxonomy.load()
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    EXTRACTIONS_DIR.mkdir(parents=True, exist_ok=True)
    postings = load_postings()[: limit or None]
    pending, done = [], []
    for p in postings:
        (PROMPTS_DIR / f"{p.id}.md").write_text(render_prompt(p, segment(p.full_text), tx))
        (done if _valid_extraction(p.id) else pending).append(p.id)
    MANIFEST.write_text(json.dumps({"pending": pending, "done": done}, indent=2))
    print(f"prompts written: {len(postings)}  pending: {len(pending)}  done: {len(done)}")
    return len(postings)
```

- [ ] **Step 6: Wire main.py**

```python
    if args.cmd == "prepare":
        from extract import prepare
        prepare.run(limit=args.limit)
        return 0
```

- [ ] **Step 7: Run tests** — `uv run pytest tests/test_prepare.py -v` → PASS. Then `uv run python main.py prepare --limit 10` and read one generated prompt end-to-end for sanity (taxonomy renders, sections populated, schema example has the right id).

- [ ] **Step 8: Commit**

```bash
git add -A && git commit -m "feat: extraction schema, prompt template, prepare step

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 12: Validate step + rejects log

**Files:**
- Create: `extract/validate.py`, `tests/test_validate.py`
- Modify: `main.py` (wire `validate`)

**Interfaces:**
- Consumes: `schema.Extraction`, `taxonomy.load`, `prepare.MANIFEST/EXTRACTIONS_DIR`.
- Produces: `validate.validate_one(path: Path, tx) -> tuple[Extraction|None, list[dict]]` (cleaned extraction with unknown skills removed, list of rejects `{posting_id, canonical, section, evidence}`); `validate.run() -> dict` (`{"valid": n, "invalid": n, "rejects": n}`), writes `data/processed/rejects.log` (one JSON per line) and updates manifest; `validate.load_valid_extractions() -> list[Extraction]`.

- [ ] **Step 1: Write failing tests**

`tests/test_validate.py`:
```python
import json
from extract import validate, taxonomy, prepare

GOOD = {"posting_id": "a", "skills": [{"canonical": "python", "section": "requirement", "evidence": "x"},
                                      {"canonical": "quantum_computing", "section": "nice_to_have", "evidence": "q"},
                                      {"canonical": "Amazon Web Services", "section": "requirement", "evidence": "aws"}],
        "seniority": "mid", "years_required": None, "travel_expectation": "unspecified", "customer_facing_intensity": 3,
        "responsibility_verbs": ["a", "b", "c", "d", "e"], "segmentation_quality": "inferred"}


def test_validate_one_drops_unknown_and_resolves_alias(tmp_path):
    f = tmp_path / "a.json"
    f.write_text(json.dumps(GOOD))
    ex, rejects = validate.validate_one(f, taxonomy.load())
    assert [s.canonical for s in ex.skills] == ["python", "aws"]
    assert rejects == [{"posting_id": "a", "canonical": "quantum_computing", "section": "nice_to_have", "evidence": "q"}]


def test_validate_one_schema_failure_returns_none(tmp_path):
    f = tmp_path / "b.json"
    f.write_text('{"posting_id": "b"}')
    ex, rejects = validate.validate_one(f, taxonomy.load())
    assert ex is None and rejects == []


def test_run_updates_manifest_and_rejects(monkeypatch, tmp_path):
    ex_dir, pr_dir = tmp_path / "extractions", tmp_path / "prompts"
    ex_dir.mkdir(); pr_dir.mkdir()
    monkeypatch.setattr(validate, "EXTRACTIONS_DIR", ex_dir)
    monkeypatch.setattr(validate, "MANIFEST", pr_dir / "manifest.json")
    monkeypatch.setattr(validate, "REJECTS", tmp_path / "rejects.log")
    (pr_dir / "manifest.json").write_text(json.dumps({"pending": ["a", "b", "c"], "done": []}))
    (ex_dir / "a.json").write_text(json.dumps(GOOD))
    (ex_dir / "b.json").write_text("not json")
    res = validate.run()
    assert res == {"valid": 1, "invalid": 1, "missing": 1, "rejects": 1}
    m = json.loads((pr_dir / "manifest.json").read_text())
    assert m["done"] == ["a"] and sorted(m["pending"]) == ["b", "c"]
    assert json.loads((tmp_path / "rejects.log").read_text().splitlines()[0])["canonical"] == "quantum_computing"
    assert json.loads((ex_dir / "a.json").read_text())["skills"][1]["canonical"] == "aws"  # rewritten clean
```

- [ ] **Step 2: Run to verify fail** — `uv run pytest tests/test_validate.py -v` → FAIL.

- [ ] **Step 3: Implement extract/validate.py**

```python
"""Validate extraction JSON files against the schema and the closed taxonomy."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from pydantic import ValidationError

from extract import taxonomy
from extract.prepare import EXTRACTIONS_DIR, MANIFEST
from extract.schema import Extraction, SkillMention
from sources.base import PROCESSED_DIR

REJECTS = PROCESSED_DIR / "rejects.log"


def validate_one(path: Path, tx: taxonomy.Taxonomy) -> tuple[Extraction | None, list[dict]]:
    try:
        ex = Extraction.model_validate_json(path.read_text())
    except (ValidationError, ValueError):
        return None, []
    if ex.posting_id != path.stem:
        return None, []
    idx, kept, rejects, seen = tx.alias_index, [], [], set()
    for s in ex.skills:
        canon = idx.get(s.canonical.strip().lower())
        if canon is None:
            rejects.append({"posting_id": ex.posting_id, "canonical": s.canonical, "section": s.section, "evidence": s.evidence})
            continue
        if (canon, s.section) in seen:
            continue
        seen.add((canon, s.section))
        kept.append(SkillMention(canonical=canon, section=s.section, evidence=s.evidence))
    return ex.model_copy(update={"skills": kept}), rejects


def run() -> dict:
    tx = taxonomy.load()
    m = json.loads(MANIFEST.read_text())
    ids = list(dict.fromkeys(m["pending"] + m["done"]))
    done, pending, all_rejects, counts = [], [], [], Counter()
    for pid in ids:
        f = EXTRACTIONS_DIR / f"{pid}.json"
        if not f.exists():
            counts["missing"] += 1
            pending.append(pid)
            continue
        ex, rejects = validate_one(f, tx)
        if ex is None:
            counts["invalid"] += 1
            pending.append(pid)
            continue
        f.write_text(ex.model_dump_json(indent=2))  # persist the cleaned version
        all_rejects.extend(rejects)
        counts["valid"] += 1
        done.append(pid)
    MANIFEST.write_text(json.dumps({"pending": pending, "done": done}, indent=2))
    REJECTS.write_text("".join(json.dumps(r) + "\n" for r in all_rejects))
    res = {"valid": counts["valid"], "invalid": counts["invalid"], "missing": counts["missing"], "rejects": len(all_rejects)}
    print(res)
    top = Counter(r["canonical"].lower() for r in all_rejects).most_common(25)
    for name, n in top:
        print(f"  reject x{n:3d}  {name}")
    return res


def load_valid_extractions() -> list[Extraction]:
    m = json.loads(MANIFEST.read_text())
    return [Extraction.model_validate_json((EXTRACTIONS_DIR / f"{pid}.json").read_text()) for pid in m["done"]]
```

- [ ] **Step 4: Wire main.py**

```python
    if args.cmd == "validate":
        from extract import validate
        validate.run()
        return 0
```

- [ ] **Step 5: Run tests** — `uv run pytest tests/test_validate.py -v` → PASS.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: extraction validation and rejects log

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 13: Extraction runbook skill + 10-posting sample (USER CHECKPOINT 2)

**Files:**
- Create: `.claude/skills/fde-extract/SKILL.md`, `AGENTS.md`

**Interfaces:**
- Consumes: `prompts/manifest.json`, `prompts/{id}.md`; `validate.run()`.
- Produces: `extractions/{id}.json` for every pending id.

- [ ] **Step 1: Write `.claude/skills/fde-extract/SKILL.md`**

```markdown
---
name: fde-extract
description: Run the FDE posting skill-extraction step in-session — dispatch subagents over pending prompt files, then validate. Use after `python main.py prepare` and whenever `prompts/manifest.json` has pending ids.
---

# fde-extract

Extraction is the one pipeline step without an API key. It is done by subagents reading rendered prompt files and writing JSON files. Everything else is deterministic Python.

## Preconditions
- `uv run python main.py prepare [--limit N]` has been run; `data/processed/prompts/manifest.json` exists.
- `taxonomy.yaml` has been approved by the user.

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
```

- [ ] **Step 2: Write AGENTS.md** (so Codex/other agents find the runbook)

```markdown
# FDE Skills Roadmap — agent notes

Pipeline: `uv run python main.py discover | collect | prepare | validate | aggregate | render`.
Extraction between `prepare` and `validate` is done in-session: see `.claude/skills/fde-extract/SKILL.md`.
Never re-fetch sources without `--refresh`; raw responses are cached under `data/raw/`.
Spec: `docs/superpowers/specs/2026-09-14-fde-skills-roadmap-design.md`. Plan: `docs/superpowers/plans/2026-09-14-fde-skills-roadmap.md`.
```

- [ ] **Step 3: Run the 10-posting sample**

Precondition: USER CHECKPOINT 1 (taxonomy) approved.
```bash
uv run python main.py prepare --limit 10
```
Then follow the skill (one subagent, 10 ids), then `uv run python main.py validate`.

- [ ] **Step 4: USER CHECKPOINT 2 — present the sample**

For each of the 10 postings print: title, company, source, `segmentation_quality`, then the extraction JSON, then the first 30 lines of the REQUIREMENTS segment so the user can spot-check evidence quotes. Print the rejects list. **Wait for approval before Task 20.** If the user asks for prompt/taxonomy changes, apply them, re-run `prepare --limit 10`, re-extract, re-validate, re-present.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: fde-extract runbook skill, agent notes, 10-posting sample

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---
### Task 14: Frequency and criticality aggregates

**Files:**
- Create: `aggregate/__init__.py`, `aggregate/frequency.py`, `aggregate/criticality.py`, `tests/conftest.py`, `tests/test_frequency_criticality.py`

**Interfaces:**
- Consumes: `schema.Extraction`, `taxonomy.Taxonomy`.
- Produces: `frequency.skill_frequency(exs) -> dict[canonical, {"n": int, "frequency": float}]`, `frequency.cluster_coverage(exs, tx) -> dict[cluster_key, float]`, `criticality.skill_criticality(exs, low_n=5) -> dict[canonical, {"criticality": float, "mentions": {section: int}, "low_n": bool, "evidence": str}]`.

- [ ] **Step 1: Write the shared synthetic fixture**

`tests/conftest.py`:
```python
import pytest
from extract.schema import Extraction, SkillMention as M


def ex(pid, skills, seniority="senior", years=5, travel="occasional", cfi=4, verbs=None, quality="header"):
    return Extraction(posting_id=pid, skills=[M(canonical=c, section=s, evidence=f"{c} {s}") for c, s in skills],
                      seniority=seniority, years_required=years, travel_expectation=travel, customer_facing_intensity=cfi,
                      responsibility_verbs=verbs or ["build", "deploy", "scope", "own", "present"], segmentation_quality=quality)


@pytest.fixture
def six():
    """6 postings. python in 6 (1 responsibility, 5 requirement); aws in 3 (all requirement);
    scoping in 3 (3 responsibility); kubernetes in 2 (1 resp, 1 nice); evals in 1 (resp)."""
    return [
        ex("p1", [("python", "requirement"), ("aws", "requirement"), ("scoping", "responsibility"), ("kubernetes", "responsibility")], seniority="senior", years=5, travel="frequent", cfi=5),
        ex("p2", [("python", "responsibility"), ("aws", "requirement"), ("scoping", "responsibility")], seniority="mid", years=3, travel="occasional", cfi=4),
        ex("p3", [("python", "requirement"), ("aws", "requirement"), ("scoping", "responsibility"), ("evals", "responsibility")], seniority="senior", years=6, travel="none", cfi=3),
        ex("p4", [("python", "requirement"), ("kubernetes", "nice_to_have")], seniority="staff_plus", years=10, travel="unspecified", cfi=2, quality="inferred"),
        ex("p5", [("python", "requirement")], seniority="unspecified", years=None, travel="unspecified", cfi=1, verbs=["ship", "deploy", "scope", "own", "present"]),
        ex("p6", [("python", "requirement"), ("python", "responsibility")], seniority="junior", years=1, travel="occasional", cfi=4),
    ]
```

- [ ] **Step 2: Write failing tests**

`tests/test_frequency_criticality.py`:
```python
from aggregate import frequency, criticality
from extract import taxonomy


def test_skill_frequency_counts_once_per_posting(six):
    f = frequency.skill_frequency(six)
    assert f["python"] == {"n": 6, "frequency": 1.0}
    assert f["aws"] == {"n": 3, "frequency": 0.5}
    assert f["kubernetes"]["n"] == 2 and f["evals"]["n"] == 1


def test_cluster_coverage(six):
    cov = frequency.cluster_coverage(six, taxonomy.load())
    assert cov["software_foundations"] == 1.0
    assert cov["deployment_and_operations"] == 4 / 6  # aws or kubernetes: p1 p2 p3 p4
    assert cov["customer_delivery"] == 0.5
    assert cov["product_thinking_and_communication"] == 0.0


def test_skill_criticality(six):
    c = criticality.skill_criticality(six, low_n=3)
    assert c["python"]["mentions"] == {"responsibility": 2, "requirement": 6, "nice_to_have": 0}
    assert c["python"]["criticality"] == 2 / 8 and c["python"]["low_n"] is False
    assert c["scoping"]["criticality"] == 1.0
    assert c["aws"]["criticality"] == 0.0
    assert c["kubernetes"]["criticality"] == 0.5 and c["kubernetes"]["low_n"] is True
    assert c["evals"]["low_n"] is True and c["scoping"]["evidence"] == "scoping responsibility"
```

- [ ] **Step 3: Run to verify fail** — `uv run pytest tests/test_frequency_criticality.py -v` → FAIL.

- [ ] **Step 4: Implement**

`aggregate/frequency.py`:
```python
"""How often each skill / cluster appears across postings."""
from __future__ import annotations

from collections import Counter

from extract.schema import Extraction
from extract.taxonomy import Taxonomy


def skill_frequency(exs: list[Extraction]) -> dict[str, dict]:
    n = len(exs)
    counts = Counter(c for e in exs for c in {s.canonical for s in e.skills})
    return {c: {"n": k, "frequency": k / n if n else 0.0} for c, k in counts.items()}


def cluster_coverage(exs: list[Extraction], tx: Taxonomy) -> dict[str, float]:
    n = len(exs)
    out = {}
    for key, skills in tx.clusters.items():
        members = {s.canonical for s in skills}
        hit = sum(1 for e in exs if any(s.canonical in members for s in e.skills))
        out[key] = hit / n if n else 0.0
    return out
```

`aggregate/criticality.py`:
```python
"""Share of a skill's mentions that are responsibilities (vs requirement / nice-to-have)."""
from __future__ import annotations

from collections import defaultdict

from extract.schema import Extraction

SECTIONS = ("responsibility", "requirement", "nice_to_have")


def skill_criticality(exs: list[Extraction], low_n: int = 5) -> dict[str, dict]:
    mentions: dict[str, dict[str, int]] = defaultdict(lambda: {s: 0 for s in SECTIONS})
    evidence: dict[str, str] = {}
    for e in exs:
        for s in e.skills:
            mentions[s.canonical][s.section] += 1
            if s.section == "responsibility" or s.canonical not in evidence:
                evidence[s.canonical] = s.evidence  # prefer a responsibility quote
    out = {}
    for c, m in mentions.items():
        total = sum(m.values())
        out[c] = {"criticality": m["responsibility"] / total if total else 0.0, "mentions": dict(m),
                  "low_n": total < low_n, "evidence": evidence.get(c, "")}
    return out
```

- [ ] **Step 5: Run tests** — PASS.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: frequency and criticality aggregates

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 15: Co-occurrence lift and stack clustering

**Files:**
- Create: `aggregate/cooccurrence.py`, `tests/test_cooccurrence.py`

**Interfaces:**
- Produces: `cooccurrence.pair_lift(exs, *, min_freq=0.05, min_support=8, min_lift=1.2) -> list[{"a","b","lift","support"}]`, `cooccurrence.cluster_stacks(pairs, *, max_stacks=4, min_size=2) -> list[{"skills": [..], "support": int}]`.

- [ ] **Step 1: Write failing tests**

`tests/test_cooccurrence.py`:
```python
from aggregate import cooccurrence as co


def test_pair_lift_math(six):
    pairs = co.pair_lift(six, min_freq=0.1, min_support=2, min_lift=1.0)
    d = {(p["a"], p["b"]): p for p in pairs}
    # aws & scoping co-occur in p1,p2,p3: P(ab)=0.5, P(a)=0.5, P(b)=0.5 -> lift 2.0
    assert d[("aws", "scoping")]["lift"] == 2.0 and d[("aws", "scoping")]["support"] == 3
    # python & aws: P(ab)=0.5, P(python)=1 -> lift 1.0 (kept because min_lift=1.0)
    assert d[("aws", "python")]["lift"] == 1.0


def test_pair_lift_filters(six):
    pairs = co.pair_lift(six, min_freq=0.1, min_support=2, min_lift=1.2)
    keys = {(p["a"], p["b"]) for p in pairs}
    assert ("aws", "scoping") in keys and ("aws", "python") not in keys


def test_cluster_stacks_groups_connected_pairs():
    pairs = [{"a": "aws", "b": "scoping", "lift": 2.0, "support": 3}, {"a": "aws", "b": "kubernetes", "lift": 1.5, "support": 2},
             {"a": "rag", "b": "evals", "lift": 3.0, "support": 4}]
    stacks = co.cluster_stacks(pairs, max_stacks=4, min_size=2)
    groups = [set(s["skills"]) for s in stacks]
    assert {"aws", "scoping", "kubernetes"} in groups and {"rag", "evals"} in groups
    assert stacks[0]["support"] >= stacks[-1]["support"]
```

- [ ] **Step 2: Run to verify fail** — FAIL.

- [ ] **Step 3: Implement aggregate/cooccurrence.py**

```python
"""Skill-pair lift and greedy grouping into 'stacks that travel together'."""
from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations

from extract.schema import Extraction


def pair_lift(exs: list[Extraction], *, min_freq: float = 0.05, min_support: int = 8, min_lift: float = 1.2) -> list[dict]:
    n = len(exs)
    sets = [frozenset(s.canonical for s in e.skills) for e in exs]
    single = Counter(c for s in sets for c in s)
    eligible = {c for c, k in single.items() if k / n >= min_freq}
    pair = Counter()
    for s in sets:
        for a, b in combinations(sorted(s & eligible), 2):
            pair[(a, b)] += 1
    out = []
    for (a, b), k in pair.items():
        lift = (k / n) / ((single[a] / n) * (single[b] / n))
        if k >= min_support and lift >= min_lift:
            out.append({"a": a, "b": b, "lift": round(lift, 3), "support": k})
    return sorted(out, key=lambda p: (-p["lift"], -p["support"]))


def cluster_stacks(pairs: list[dict], *, max_stacks: int = 4, min_size: int = 2) -> list[dict]:
    """Greedy: take strongest edges first, merge into groups; split large groups by dropping weakest cross edges."""
    adj: dict[str, dict[str, float]] = defaultdict(dict)
    for p in pairs:
        adj[p["a"]][p["b"]] = adj[p["b"]][p["a"]] = p["lift"]
    group_of: dict[str, int] = {}
    groups: dict[int, set[str]] = {}
    nxt = 0
    for p in sorted(pairs, key=lambda p: -p["lift"]):
        ga, gb = group_of.get(p["a"]), group_of.get(p["b"])
        if ga is None and gb is None:
            groups[nxt] = {p["a"], p["b"]}; group_of[p["a"]] = group_of[p["b"]] = nxt; nxt += 1
        elif ga is None:
            groups[gb].add(p["a"]); group_of[p["a"]] = gb
        elif gb is None:
            groups[ga].add(p["b"]); group_of[p["b"]] = ga
        elif ga != gb and len(groups[ga]) + len(groups[gb]) <= 8:
            groups[ga] |= groups[gb]
            for s in groups[gb]:
                group_of[s] = ga
            del groups[gb]
    support = {(p["a"], p["b"]): p["support"] for p in pairs}
    out = []
    for g in groups.values():
        if len(g) < min_size:
            continue
        sup = max((support.get((a, b), support.get((b, a), 0)) for a, b in combinations(sorted(g), 2)), default=0)
        out.append({"skills": sorted(g, key=lambda s: -sum(adj[s].get(o, 0) for o in g)), "support": sup})
    return sorted(out, key=lambda s: -s["support"])[:max_stacks]
```

- [ ] **Step 4: Run tests** — PASS.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: co-occurrence lift and stack grouping

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 16: Market aggregates and gap analysis

**Files:**
- Create: `aggregate/market.py`, `aggregate/gap.py`, `tests/test_market_gap.py`

**Interfaces:**
- Consumes: `Extraction`, `Posting` (for `company_size_hint`), `frequency.skill_frequency`.
- Produces: `market.distributions(exs) -> dict` with keys `seniority`, `years`, `travel`, `customer_facing`, `verbs`; `market.segment_deltas(exs, postings, freq_threshold=0.15) -> list[{"skill","startup","enterprise"}]`; `gap.STANDARD_ROADMAP_SKILLS: set[str]`; `gap.gaps(freq: dict, *, min_frequency=0.2) -> list[{"canonical","frequency"}]`.

- [ ] **Step 1: Write failing tests**

`tests/test_market_gap.py`:
```python
from aggregate import market, gap
from sources.base import Posting


def test_distributions(six):
    d = market.distributions(six)
    assert d["seniority"] == {"junior": 1, "mid": 1, "senior": 2, "staff_plus": 1, "unspecified": 1}
    assert d["years"] == {"0-2": 1, "3-5": 2, "6-9": 1, "10+": 1, "unspecified": 1}
    assert d["travel"] == {"none": 1, "occasional": 2, "frequent": 1, "unspecified": 2}
    assert d["customer_facing"] == {"1": 1, "2": 1, "3": 1, "4": 2, "5": 1}
    assert d["verbs"][0] == ["deploy", 6] and len(d["verbs"]) <= 15


def test_segment_deltas(six):
    posts = [Posting(id=e.posting_id, title="t", company="c", url="u", full_text="x", source="s",
                     company_size_hint="startup" if e.posting_id in ("p1", "p2", "p3") else "enterprise") for e in six]
    deltas = market.segment_deltas(six, posts, freq_threshold=0.3)
    d = {x["skill"]: x for x in deltas}
    assert d["scoping"] == {"skill": "scoping", "startup": 1.0, "enterprise": 0.0}
    assert "python" not in d  # 1.0 vs 1.0, no delta


def test_gap():
    freq = {"python": {"frequency": 0.9}, "scoping": {"frequency": 0.4}, "rag": {"frequency": 0.5}, "travel_onsite": {"frequency": 0.1}}
    g = gap.gaps(freq, min_frequency=0.2)
    assert [x["canonical"] for x in g] == ["scoping"]
    assert "python" in gap.STANDARD_ROADMAP_SKILLS and "rag" in gap.STANDARD_ROADMAP_SKILLS
```

- [ ] **Step 2: Run to verify fail** — FAIL.

- [ ] **Step 3: Implement**

`aggregate/market.py`:
```python
"""Seniority / years / travel / customer-facing distributions, verbs, startup-vs-enterprise deltas."""
from __future__ import annotations

from collections import Counter

from extract.schema import Extraction
from sources.base import Posting

SENIORITY = ["junior", "mid", "senior", "staff_plus", "unspecified"]
YEARS = ["0-2", "3-5", "6-9", "10+", "unspecified"]
TRAVEL = ["none", "occasional", "frequent", "unspecified"]


def _years_bucket(y: int | None) -> str:
    if y is None:
        return "unspecified"
    return "0-2" if y <= 2 else "3-5" if y <= 5 else "6-9" if y <= 9 else "10+"


def distributions(exs: list[Extraction]) -> dict:
    sen = Counter(e.seniority for e in exs)
    yrs = Counter(_years_bucket(e.years_required) for e in exs)
    trv = Counter(e.travel_expectation for e in exs)
    cfi = Counter(str(e.customer_facing_intensity) for e in exs)
    verbs = Counter(v.lower().strip() for e in exs for v in e.responsibility_verbs)
    return {
        "seniority": {k: sen.get(k, 0) for k in SENIORITY},
        "years": {k: yrs.get(k, 0) for k in YEARS},
        "travel": {k: trv.get(k, 0) for k in TRAVEL},
        "customer_facing": {k: cfi.get(k, 0) for k in "12345"},
        "verbs": [[v, n] for v, n in verbs.most_common(15)],
    }


def segment_deltas(exs: list[Extraction], postings: list[Posting], freq_threshold: float = 0.15) -> list[dict]:
    hint = {p.id: p.company_size_hint for p in postings}
    groups = {"startup": [e for e in exs if hint.get(e.posting_id) == "startup"],
              "enterprise": [e for e in exs if hint.get(e.posting_id) == "enterprise"]}
    if not groups["startup"] or not groups["enterprise"]:
        return []
    def freq(group):
        c = Counter(s for e in group for s in {m.canonical for m in e.skills})
        return {k: v / len(group) for k, v in c.items()}
    fs, fe = freq(groups["startup"]), freq(groups["enterprise"])
    out = []
    for skill in set(fs) | set(fe):
        a, b = fs.get(skill, 0.0), fe.get(skill, 0.0)
        if abs(a - b) >= freq_threshold:
            out.append({"skill": skill, "startup": round(a, 3), "enterprise": round(b, 3)})
    return sorted(out, key=lambda d: -abs(d["startup"] - d["enterprise"]))
```

`aggregate/gap.py`:
```python
"""What FDE postings demand that standard AI-engineer roadmaps do not teach.

STANDARD_ROADMAP_SKILLS is the union of topics covered by roadmap.sh's "AI Engineer" roadmap
(https://roadmap.sh/ai-engineer, checked 2026-09) and the syllabus shared by common LLM
bootcamps (DeepLearning.AI short courses, Full Stack LLM Bootcamp): Python, LLM APIs, prompting,
RAG + vector DBs, agents/frameworks, embeddings, fine-tuning basics, evals, ML fundamentals,
model serving, cloud basics, Git, REST, Docker, observability, guardrails, multimodal.
Expressed in taxonomy canonical names.
"""
from __future__ import annotations

STANDARD_ROADMAP_SKILLS: set[str] = {
    "python", "git", "rest_apis", "docker", "cloud_platforms", "aws", "sql",
    "llm_apis", "prompt_engineering", "rag", "vector_databases", "agents", "llm_frameworks", "evals",
    "fine_tuning", "ml_fundamentals", "nlp", "computer_vision", "model_serving", "llm_observability",
    "guardrails_safety", "testing", "system_design",
}


def gaps(freq: dict[str, dict], *, min_frequency: float = 0.2) -> list[dict]:
    out = [{"canonical": c, "frequency": round(v["frequency"], 3)} for c, v in freq.items()
           if v["frequency"] >= min_frequency and c not in STANDARD_ROADMAP_SKILLS]
    return sorted(out, key=lambda d: -d["frequency"])
```

- [ ] **Step 4: Run tests** — PASS.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: market distributions, segment deltas, gap analysis

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 17: Build report_data.json

**Files:**
- Create: `aggregate/build_report_data.py`, `tests/test_build_report_data.py`
- Modify: `main.py` (wire `aggregate`)

**Interfaces:**
- Consumes: all aggregate modules, `validate.load_valid_extractions`, `collect.load_postings`, `collect_stats.json`, `rejects.log`, `taxonomy.load`.
- Produces: `build_report_data.build(exs, postings, stats, n_rejects, tx, *, generated_at) -> dict` (exact `report_data.json` contract from Task 2), `build_report_data.run() -> Path`.

- [ ] **Step 1: Write failing test**

`tests/test_build_report_data.py`:
```python
import json
from pathlib import Path
from aggregate import build_report_data as b
from extract import taxonomy
from sources.base import Posting

FIX_KEYS = json.loads(Path("render/fixtures/report_data.fixture.json").read_text())


def test_build_matches_fixture_shape(six):
    posts = [Posting(id=e.posting_id, title="FDE", company=f"C{i}", url="u", full_text="x", source="greenhouse",
                     posted_date=f"2026-0{i+3}-01", company_size_hint="startup" if i < 3 else "enterprise") for i, e in enumerate(six)]
    stats = [{"name": "greenhouse", "fetched": 10, "matched": 6, "kept": 6}]
    d = b.build(six, posts, stats, n_rejects=2, tx=taxonomy.load(), generated_at="2026-09-14T00:00:00Z")
    assert set(d) == set(FIX_KEYS)
    assert d["meta"]["n_postings"] == 6 and d["meta"]["n_companies"] == 6 and d["meta"]["date_range"] == ["2026-03-01", "2026-08-01"]
    assert d["meta"]["segmentation"] == {"header": 5, "inferred": 1} and d["meta"]["rejects"] == 2 and d["meta"]["adzuna_used"] is False
    py = next(s for s in d["skills"] if s["canonical"] == "python")
    assert set(py) == set(FIX_KEYS["skills"][0]) and py["label"] == "Python" and py["cluster"] == "software_foundations"
    assert [c["key"] for c in d["clusters"]] == [c["key"] for c in FIX_KEYS["clusters"]]
    assert set(d["scatter"]) == {"median_frequency", "median_criticality", "outliers"}
    assert set(d["market"]) == set(FIX_KEYS["market"])
    assert all(set(g) == {"canonical", "label", "frequency"} for g in d["gap"])
    assert all(set(s) == {"name", "skills", "support"} for s in d["stacks"])
```

- [ ] **Step 2: Run to verify fail** — FAIL.

- [ ] **Step 3: Implement aggregate/build_report_data.py**

```python
"""Assemble every aggregate into the single JSON object the HTML template consumes."""
from __future__ import annotations

import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

from aggregate import cooccurrence, criticality, frequency, gap, market
from extract import taxonomy
from extract.schema import Extraction
from sources.base import PROCESSED_DIR, Posting, normalize_company

META_MODEL = "claude-sonnet-5"
OUT = PROCESSED_DIR / "report_data.json"


def _outliers(skills: list[dict], mx: float, my: float) -> list[dict]:
    solid = [s for s in skills if not s["low_n"]]
    crit_q1 = statistics.quantiles([s["criticality"] for s in solid], n=4)[0] if len(solid) >= 4 else my
    hi_freq_lo_crit = sorted([s for s in solid if s["criticality"] <= crit_q1], key=lambda s: -s["frequency"])[:3]
    lo_freq_hi_crit = sorted([s for s in solid if s["frequency"] < mx and s["n"] >= 8], key=lambda s: -s["criticality"])[:3]
    out = [{"canonical": s["canonical"], "note": "Everyone asks; rarely the job itself"} for s in hi_freq_lo_crit]
    out += [{"canonical": s["canonical"], "note": "Rarely listed; when it is, it's the job"} for s in lo_freq_hi_crit]
    return out


def _stack_name(skills: list[str], tx: taxonomy.Taxonomy) -> str:
    return " + ".join(tx.labels.get(s, s) for s in skills[:3])


def build(exs: list[Extraction], postings: list[Posting], stats: list[dict], n_rejects: int,
          tx: taxonomy.Taxonomy, *, generated_at: str) -> dict:
    freq = frequency.skill_frequency(exs)
    crit = criticality.skill_criticality(exs)
    skills = []
    for c, f in freq.items():
        skills.append({"canonical": c, "label": tx.labels[c], "cluster": tx.cluster_of(c), "n": f["n"],
                       "frequency": round(f["frequency"], 4), "criticality": round(crit[c]["criticality"], 4),
                       "mentions": crit[c]["mentions"], "low_n": crit[c]["low_n"], "evidence": crit[c]["evidence"]})
    skills.sort(key=lambda s: -s["frequency"])
    cov = frequency.cluster_coverage(exs, tx)
    clusters = [{"key": k, "label": tx.cluster_labels[k], "coverage": round(cov[k], 4),
                 "skills": [s.canonical for s in v if s.canonical in freq]} for k, v in tx.clusters.items()]
    fx = [s["frequency"] for s in skills] or [0]
    fy = [s["criticality"] for s in skills if not s["low_n"]] or [0]
    mx, my = statistics.median(fx), statistics.median(fy)
    pairs = cooccurrence.pair_lift(exs)
    stacks = [{"name": _stack_name(s["skills"], tx), "skills": s["skills"], "support": s["support"]}
              for s in cooccurrence.cluster_stacks(pairs)]
    mkt = market.distributions(exs)
    mkt["segment_deltas"] = market.segment_deltas(exs, postings)
    dates = sorted(p.posted_date for p in postings if p.posted_date)
    return {
        "meta": {"n_postings": len(exs), "n_companies": len({normalize_company(p.company) for p in postings}),
                 "date_range": [dates[0], dates[-1]] if dates else ["", ""], "generated_at": generated_at, "model": META_MODEL,
                 "sources": stats, "segmentation": {"header": sum(e.segmentation_quality == "header" for e in exs),
                                                     "inferred": sum(e.segmentation_quality == "inferred" for e in exs)},
                 "rejects": n_rejects, "adzuna_used": False},
        "skills": skills,
        "clusters": clusters,
        "scatter": {"median_frequency": round(mx, 4), "median_criticality": round(my, 4), "outliers": _outliers(skills, mx, my)},
        "stacks": stacks,
        "market": mkt,
        "gap": [{"canonical": g["canonical"], "label": tx.labels[g["canonical"]], "frequency": g["frequency"]} for g in gap.gaps(freq)],
    }


def run() -> Path:
    from extract.validate import load_valid_extractions
    from sources.collect import load_postings
    exs = load_valid_extractions()
    done = {e.posting_id for e in exs}
    postings = [p for p in load_postings() if p.id in done]
    stats = json.loads((PROCESSED_DIR / "collect_stats.json").read_text())
    rejects_path = PROCESSED_DIR / "rejects.log"
    n_rejects = len(rejects_path.read_text().splitlines()) if rejects_path.exists() else 0
    data = build(exs, postings, stats, n_rejects, taxonomy.load(), generated_at=datetime.now(timezone.utc).isoformat())
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"report_data.json: n={data['meta']['n_postings']} skills={len(data['skills'])} stacks={len(data['stacks'])} gaps={len(data['gap'])}")
    for s in data["stacks"]:
        print(f"  stack support={s['support']:3d}  {s['name']}  <- {s['skills']}")
    return OUT
```

- [ ] **Step 4: Wire main.py**

```python
    if args.cmd == "aggregate":
        from aggregate import build_report_data
        build_report_data.run()
        return 0
```

- [ ] **Step 5: Run tests, then smoke the real pipeline on the 10-sample** — `uv run pytest -v` all green; `uv run python main.py aggregate && uv run python main.py render` and open the HTML: the charts now show the 10 real postings.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: assemble report_data.json; aggregate step wired

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---
### Task 18: Full extraction run and rejects review

**Files:**
- Modify: `taxonomy.yaml` (aliases/nodes from reject review), `data/processed/*` (generated)

**Interfaces:**
- Consumes: `.claude/skills/fde-extract/SKILL.md`, `prepare.run`, `validate.run`.
- Produces: a valid `extractions/{id}.json` for every posting in `postings.jsonl`; final `rejects.log`.

Precondition: USER CHECKPOINT 2 approved.

- [ ] **Step 1: Prepare all prompts** — `uv run python main.py prepare` (no limit). Note `pending` count.

- [ ] **Step 2: Extract** — follow `.claude/skills/fde-extract/SKILL.md` exactly (batches of 15, Sonnet, parallel dispatch). Then `uv run python main.py validate`.

- [ ] **Step 3: Retry loop** — while `pending` non-empty and retries < 2: re-dispatch pending ids, validate.

- [ ] **Step 4: Rejects review with the user** — show the top-25 rejects with counts and two evidence examples each. For each recurring reject (≥3) decide with the user: add as alias to an existing node, add a new node (rare — the taxonomy is closed on purpose), or leave rejected. Apply edits to `taxonomy.yaml`, run `uv run pytest tests/test_taxonomy.py`.

- [ ] **Step 5: Re-extract affected postings only**

```bash
uv run python -c "
import json; ids=sorted({json.loads(l)['posting_id'] for l in open('data/processed/rejects.log') if json.loads(l)['canonical'].lower() in {'<alias1>','<alias2>'}}); print(len(ids)); print(' '.join(ids))"
```
Delete those ids' `extractions/{id}.json`, run `uv run python main.py prepare` (re-embeds taxonomy, marks them pending), extract per skill, `validate`.

- [ ] **Step 6: Report** — print final `{valid, invalid, missing, rejects}` and `n_postings` to the user. Must be ≥ 300 valid.

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "data: full extraction run, taxonomy alias fixes from reject review

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 19: Aggregate on real data, stack names, content.yaml

**Files:**
- Modify: `render/content.yaml` (replace placeholders), `aggregate/build_report_data.py` (only if stack naming needs manual override)

**Interfaces:**
- Consumes: `report_data.json` from `uv run python main.py aggregate`.
- Produces: final `render/content.yaml`.

- [ ] **Step 1: Aggregate** — `uv run python main.py aggregate`. Print the stacks, the scatter outliers, the gap list, and `market.segment_deltas` to the user.

- [ ] **Step 2: Stack names** — propose one 2–4 word name per stack (e.g. "LLM app core", "Enterprise plumbing", "Field delivery"). Get the user's OK; if they prefer different names, add a `STACK_NAME_OVERRIDES: dict[frozenset, str]` at the top of `build_report_data.py` keyed by the stack's skill set and apply it in `_stack_name`.

- [ ] **Step 3: Author content.yaml from the numbers** — replace every placeholder. Rules:
  - `flow`: keep the 8 steps; one-sentence blurbs, no marketing.
  - `roadmap`: 4 tracks — "Python for FDE" (must start with `skip:` listing what the data says is NOT asked: derive from software_foundations skills with frequency < 10%, plus deep-internals topics), "AI application engineering", "Integration & deployment", "Customer delivery & communication". Each track 3 stages; each stage's `skills` are canonical names ordered by frequency × criticality descending; `why` cites the number ("in 61% of postings, 70% as a responsibility").
  - `projects`: 4 build specs. Each `scope` is 2–3 sentences of concrete deliverable, `proves` names the skills from the scatter's "The job" quadrant it evidences, `clusters` lists the cluster keys exercised. Together the four must cover all six clusters. No promotional language; no first-person.
  - `insights.segment_prose`: 3–5 sentences from `segment_deltas`, directional only ("more often", "roughly twice as likely"), explicitly noting sample sizes are thin. No percentages with decimals.
  - `insights.limitations`: the four from spec §12 plus anything observed (e.g. inferred-segmentation share).
- [ ] **Step 4: Show content.yaml to the user** and apply their edits.

- [ ] **Step 5: Render and check** — `uv run python main.py render`; `uv run pytest -v`. Open `fde-roadmap.html`; verify every canonical referenced in `content.yaml` resolves to a label (no raw snake_case visible).

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: real aggregates, stack names, roadmap and project content

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 20: Visual QA, methodology pass, final file

**Files:**
- Modify: `render/template.html.j2` (fixes only), `README.md` (create)

- [ ] **Step 1: Screenshots** — open `fde-roadmap.html` in Chrome at 1280px and 390px (use the browser tools; `file://` URL). Check: no horizontal scroll at 390px; scatter quadrant labels and callouts don't overlap points badly; bar chart labels readable; flow diagram wraps; every section heading present in order 1–8; placeholder div visible in section 7. Fix CSS/JS in the template only; re-run `uv run pytest tests/test_render.py`.

- [ ] **Step 2: Methodology proof-read** — confirm section 8 states: sources with counts, n, date range, dedupe rule, segmentation split, model name, reject count, "Adzuna: not used", "LinkedIn and Indeed were not scraped", limitations list. Numbers must match `report_data.json` (`jq .meta data/processed/report_data.json`).

- [ ] **Step 3: Self-contained check**

```bash
grep -oE 'https?://[^"'"'"' )]+' fde-roadmap.html | sort -u
```
Expected: only the two cdnjs URLs plus posting/HN URLs that appear in *text* (none should be loaded as assets). `grep -c '<link' fde-roadmap.html` → 0.

- [ ] **Step 4: README.md**

```markdown
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
```

- [ ] **Step 5: Final test run and commit**

```bash
uv run pytest -v
git add -A && git commit -m "feat: final report, README, visual QA fixes

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 6: Hand-off** — tell the user the path to `fde-roadmap.html`, the final n / companies / date range, where the placeholder div is, and how to re-run after edits.

---

## Self-review

**Spec coverage:** §2 constraints → Global Constraints + Tasks 1 (cache), 2 (single file, placeholder), 3/13 (checkpoints); §6 Collect → Tasks 4–9; §7 Extract → Tasks 3, 10–13, 18; §8 Aggregate → Tasks 14–17 (frequency, criticality, co-occurrence + stacks, market, gap, outliers, meta); §9 Render → Tasks 2, 19, 20 (all eight sections, style tokens, CDN pins, mobile); §10 Testing → each task has tests; smoke render + screenshots in Task 20; §11 Order → task order matches; §12 Limitations → Task 19 step 3.

**Placeholder scan:** `content.yaml` placeholders in Task 2 are intentional fixture text and are replaced in Task 19 step 3 with explicit authoring rules. Task 18 step 5 has `<alias1>` as a deliberate substitution slot in a shell one-liner.

**Type consistency:** `fetch` returns `tuple[int, list[Posting]]` in every source (Tasks 5–7) and `collect.SOURCE_RUNNERS` consumes that shape (Task 9). `prepare.MANIFEST`/`EXTRACTIONS_DIR` are imported by `validate` (Task 12) and monkeypatched in tests via `validate.*` names — `validate.py` binds them at module level via `from extract.prepare import EXTRACTIONS_DIR, MANIFEST`, so monkeypatching `validate.EXTRACTIONS_DIR` works. `report_data.json` keys in Task 17 match the Task 2 contract and the fixture; the test asserts it. `Taxonomy.labels`, `.cluster_of`, `.cluster_labels`, `.alias_index` used in Tasks 11, 12, 14, 17 are all defined in Task 3.
