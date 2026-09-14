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
