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
