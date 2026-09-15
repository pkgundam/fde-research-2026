"""Lever public postings API."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sources import base
from sources.base import Posting

NAME = "lever"


def _url(slug: str) -> str:
    return f"https://api.lever.co/v0/postings/{slug}?mode=json"


def parse(body: str, slug: str, name: str | None = None) -> tuple[int, list[Posting]]:
    try:
        jobs = json.loads(body)
    except json.JSONDecodeError:
        return 0, []
    if not isinstance(jobs, list) or not jobs:
        return 0, []
    company = name or slug.replace("-", " ").title()
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


def fetch(slug: str, *, name: str | None = None, refresh: bool = False) -> tuple[int, list[Posting]]:
    status, body = base.cached_get(_url(slug), f"{NAME}/{slug}", refresh=refresh)
    return parse(body, slug, name) if status == 200 else (0, [])
