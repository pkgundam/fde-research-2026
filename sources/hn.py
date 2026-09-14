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
    r"(Senior |Staff |Lead |Principal |Founding )?(Forward[\s-]Deployed (AI |Software )?Engineer|\bFDE|Deployment Engineer|"
    r"Applied AI Engineer|Solutions Engineer \(?AI\)?|AI Solutions Engineer|Field Engineer|Implementation Engineer)\b", re.I)


def list_threads(*, months: int = 8, refresh: bool = False) -> list[dict]:
    url = f"{API}?query={quote(THREAD_QUERY)}&tags=story,author_whoishiring&hitsPerPage={months * 4}"
    status, body = base.cached_get(url, f"{NAME}/threads_{months}", refresh=refresh)
    hits = json.loads(body)["hits"] if status == 200 else []
    return [h for h in hits if h["title"].startswith("Ask HN: Who is hiring?")][:months]


def parse_comment(hit: dict) -> Posting | None:
    if hit.get("parent_id") != hit.get("story_id"):
        return None  # only top-level comments are job posts
    text = base.strip_html(hit.get("comment_text") or "")
    first, _, rest = text.partition("\n")
    if "|" not in first:
        return None  # HN convention is "Company | Location | ..."
    fields = [f.strip() for f in first.split("|")]
    company = fields[0] if fields else ""
    if not company or len(company) > 60:
        return None
    m = _TITLE_IN_TEXT.search(text)
    if not m or re.match(r"(s|ing)\b", text[m.end():], re.I):
        return None  # trailing \b already blocks plurals/compounds; belt-and-suspenders guard
    if not base.matches_title(m.group(0)):
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


def fetch(*, months: int = 8, refresh: bool = False) -> tuple[int, list[Posting]]:
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
