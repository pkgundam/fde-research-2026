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
