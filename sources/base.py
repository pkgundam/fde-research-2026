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
