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
