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


_FETCHED_AT_RE = re.compile(r'"fetched_at":\s*"([^"]*)"')


def latest_fetched_at(source_names: list[str]) -> str | None:
    """Max `fetched_at` across the raw cache entries under data/raw/{name}/ for each given source
    name (cache keys are namespaced f"{source}/..."). Used to report when a run's data was
    actually collected, since cached_get never re-fetches an existing key."""
    latest = None
    for name in source_names:
        d = RAW_DIR / name
        if not d.exists():
            continue
        for f in d.rglob("*.json"):
            try:
                text = f.read_text()
            except OSError:
                continue
            m = _FETCHED_AT_RE.search(text)
            if m and m.group(1) and (latest is None or m.group(1) > latest):
                latest = m.group(1)
    return latest


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

# roles that share FDE-ish vocabulary but aren't the IC engineering role we're after
_TITLE_EXCLUDE_RE = re.compile(
    r"\b(product manager|program manager|project manager|engineering manager|manager|director|"
    r"head of|vp|rvp|vice president|chief|cto|recruiter|recruiting|sales|account executive|designer|"
    r"intern|internship|marketing|analyst|strategist|creative|finance|investor|banker|gtm|"
    r"operations specialist|hardware|electrical|network deployment|robot|physical design)\b",
    re.I,
)


def matches_title(title: str) -> bool:
    if not any(r.search(title) for r in _TITLE_RES):
        return False
    return not _TITLE_EXCLUDE_RE.search(title)


# ---------- normalisation ----------
_COMPANY_STRIP = re.compile(r"[,.]?\s*\b(inc|llc|ltd|labs|ai|technologies|technology|corp|corporation|co)\b\.?|\.com|\.ai", re.I)
_SENIORITY_WORDS = r"(senior|sr\.?|staff|principal|lead|junior|jr\.?|associate|intern|ii|iii|iv|entry[- ]level|mid[- ]level)"
_TITLE_PAREN_RE = re.compile(r"\(.*?\)|\[.*?\]")
_TITLE_SEP_RE = re.compile(r"\s[-–—|]\s|[,:|]")
_TITLE_SENIORITY_RE = re.compile(rf"\b{_SENIORITY_WORDS}\b", re.I)

# HN "Company | Location | ..." field is free text and often carries markdown links, bare URLs,
# or trailing "(https://...)(YCS21)"-style parentheticals that would otherwise be counted as part
# of the company name.
_COMPANY_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_COMPANY_PAREN_RE = re.compile(r"\([^)]*\)")
_COMPANY_URL_RE = re.compile(r"https?://\S+")


def normalize_company(s: str) -> str:
    s = _COMPANY_MD_LINK_RE.sub(r"\1", s)
    s = _COMPANY_PAREN_RE.sub(" ", s)
    s = _COMPANY_URL_RE.sub(" ", s)
    s = _COMPANY_STRIP.sub("", s.lower())
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def normalize_title(s: str) -> str:
    s = _TITLE_PAREN_RE.sub("", s)
    m = _TITLE_SEP_RE.search(s)
    if m and matches_title(s[: m.start()]):
        s = s[: m.start()]
    s = _TITLE_SENIORITY_RE.sub("", s)
    s = s.replace("-", " ")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", s.lower())).strip()


DEDUPE_SIMILARITY = 0.8
# JD texts shorter than this many words carry no reliable similarity signal (a handful of words
# produces noisy/coincidental shingle overlap either way), so comparisons involving one fall back
# to the old title-only behaviour: same (company, title) key always merges, longest text wins.
_DEDUPE_MIN_WORDS = 30


def _shingles(text: str, k: int = 6) -> set[str]:
    words = re.sub(r"[^a-z ]+", " ", text.lower()).split()
    if not words:
        return set()
    if len(words) < k:
        return {" ".join(words)}
    return {" ".join(words[i : i + k]) for i in range(len(words) - k + 1)}


def _word_count(text: str) -> int:
    return len(re.sub(r"[^a-z ]+", " ", text.lower()).split())


def _containment(a: set[str], b: set[str]) -> float:
    """Containment = |A∩B| / min(|A|, |B|): how much of the smaller shingle set is covered by
    the other. Unlike Jaccard, this stays high when one JD is the other plus extra boilerplate,
    since it isn't diluted by the union growing with the longer text."""
    if not a and not b:
        return 1.0  # two empty-shingle texts count as identical
    m = min(len(a), len(b))
    if m == 0:
        return 0.0  # one side has no shingles at all: nothing in common to contain
    return len(a & b) / m


def _is_near_duplicate(p: Posting, rep: Posting) -> bool:
    if _word_count(p.full_text) < _DEDUPE_MIN_WORDS or _word_count(rep.full_text) < _DEDUPE_MIN_WORDS:
        return True  # short text: fall back to old title-only merge behaviour
    return _containment(_shingles(p.full_text), _shingles(rep.full_text)) >= DEDUPE_SIMILARITY


def _pick_representative(p: Posting, rep: Posting) -> Posting:
    if p.source == "hn" and rep.source == "hn":
        # HN "Who is hiring" ads are rewritten every month, so containment between reposts sits
        # at 0.4-0.6 (below DEDUPE_SIMILARITY) even though they're the same ad; keep the newest
        # by posted_date, falling back to "first seen" (i.e. keep rep) when undated.
        return p if (p.posted_date or "") > (rep.posted_date or "") else rep
    return p if len(p.full_text) > len(rep.full_text) else rep


def dedupe(postings: list[Posting]) -> list[Posting]:
    """Keep one posting per (normalized_company, normalized_title) group, but within a group only
    merge postings whose JD text is a near-duplicate (containment >= DEDUPE_SIMILARITY over 6-word
    shingles); dissimilar JDs under the same key are kept as separate representatives. When two
    postings merge, the one with the longer full_text is kept. HN postings are the exception: they
    always merge on the (company, title) key alone (no similarity check), keeping the newest by
    posted_date, because monthly reposts are rewritten and have no reliable similarity signal.
    Groups (and each group's surviving representatives) are returned in first-seen order."""
    groups: dict[tuple[str, str], list[Posting]] = {}
    order: list[tuple[str, str]] = []
    for p in postings:
        key = (normalize_company(p.company), normalize_title(p.title))
        if key not in groups:
            order.append(key)
            groups[key] = []
        reps = groups[key]
        for i, rep in enumerate(reps):
            same_hn = p.source == "hn" and rep.source == "hn"
            if same_hn or _is_near_duplicate(p, rep):
                reps[i] = _pick_representative(p, rep)
                break
        else:
            reps.append(p)
    out: list[Posting] = []
    for key in order:
        out.extend(groups[key])
    return out


SIZE_MAP = {  # normalized company -> hint; extend as discover resolves more boards
    "enterprise": ["palantir", "databricks", "snowflake", "c3", "uipath", "datadog", "mongodb", "confluent", "hashicorp", "gitlab", "cloudflare", "stripe", "twilio", "okta", "figma", "dropbox", "box", "zendesk", "elastic", "nutanix", "rubrik", "pure storage", "deloitte", "accenture song", "thoughtworks", "epam", "globant", "liveperson"],
    "scaleup": ["openai", "anthropic", "scale", "cohere", "glean", "harvey", "sierra", "mistral", "perplexity", "writer", "cresta", "anyscale", "weights biases", "vercel", "together", "fireworks", "hebbia", "abridge", "hippocratic", "adept", "runway", "elevenlabs", "notion", "rippling", "ramp", "brex", "retool", "samsara", "verkada", "cognition", "cursor", "shield", "sourcegraph", "windsurf", "vannevar", "applied intuition", "hugging face", "groq", "cerebras", "coreweave", "lambda", "replit", "gong", "clari", "vanta", "wiz", "snyk", "dataiku", "datarobot", "fivetran", "dbt", "airtable", "asana", "zapier", "intercom", "sprinklr", "xai", "deepgram", "assemblyai", "synthesia", "jasper", "moveworks", "abnormal security",
                "neon", "planetscale", "temporal", "sendbird", "typeface", "nightfall", "persona", "alloy", "sardine", "unit21", "monte carlo", "yellow", "level", "people", "aisera", "zilliz", "n8n", "stackblitz", "supabase", "hasura", "tines", "torq", "cyera", "honeycomb"],
    "startup": ["decagon", "modal", "replicate", "baseten", "langchain", "pinecone", "weaviate", "braintrust", "unstructured", "vellum", "humanloop", "lamini", "contextual", "reducto", "extend", "eve", "norm", "tennr", "rilla", "hex", "distyl", "rox", "ema", "sana", "parloa", "clay", "11x", "artisan", "eleos health", "assort health", "anduril", "magic", "poolside", "rebellion defense",
                "centml", "fal", "voiceflow", "assembled", "copy", "anyword", "whylabs", "elicit", "you", "middesk", "hightouch", "census", "merge", "metaplane", "bigeye", "anomalo", "deepnote", "llamaindex", "portkey", "langfuse", "helicone", "martian", "gumloop", "e2b", "browserbase", "firecrawl", "tavily", "composio", "crewai", "convex", "workos", "stytch", "cortex", "rasa", "clerk"],
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
