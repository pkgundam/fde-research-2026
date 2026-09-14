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
