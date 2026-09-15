"""Run every source, dedupe, persist postings.jsonl + per-source stats."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sources import arbeitnow, ashby, base, discover, greenhouse, hn, lever, remotive
from sources.base import Posting

PROCESSED_DIR = base.PROCESSED_DIR


def _ats_runner(module):
    def run(refresh: bool):
        slugs = discover.load_companies().get("resolved", {}).get(module.NAME, {})
        fetched, out = 0, []
        for slug, name in slugs.items():
            n, posts = module.fetch(slug, name=name, refresh=refresh)
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
    hn_threads_meta = None
    for name, runner in SOURCE_RUNNERS.items():
        fetched, posts = runner(refresh)
        stats.append({"name": name, "fetched": fetched, "matched": len(posts), "kept": 0})
        all_posts.extend(posts)
        if name == "hn":
            # cached (no network cost beyond what hn.fetch() already paid): re-derive the thread
            # window covered by this run's HN "Who is hiring" threads for collect_meta.json.
            threads = hn.list_threads(months=hn.DEFAULT_MONTHS, refresh=refresh)
            first, last = hn.thread_window(threads)
            hn_threads_meta = {"months": hn.DEFAULT_MONTHS, "first": first, "last": last}
    deduped = base.dedupe(all_posts)
    kept_by_source = {}
    for p in deduped:
        kept_by_source[p.source] = kept_by_source.get(p.source, 0) + 1
    for s in stats:
        s["kept"] = kept_by_source.get(s["name"], 0)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    (PROCESSED_DIR / "postings.jsonl").write_text("\n".join(p.model_dump_json() for p in deduped) + "\n")
    (PROCESSED_DIR / "collect_stats.json").write_text(json.dumps(stats, indent=2))
    collected_at = base.latest_fetched_at([s["name"] for s in stats]) or datetime.now(timezone.utc).isoformat()
    collect_meta = {"collected_at": collected_at, "hn_threads": hn_threads_meta}
    (PROCESSED_DIR / "collect_meta.json").write_text(json.dumps(collect_meta, indent=2))
    for s in stats:
        print(f"{s['name']:10s} fetched={s['fetched']:6d} matched={s['matched']:4d} kept={s['kept']:4d}")
    print(f"TOTAL kept={len(deduped)} companies={len({base.normalize_company(p.company) for p in deduped})}")
    return deduped, stats


def load_postings() -> list[Posting]:
    path = PROCESSED_DIR / "postings.jsonl"
    return [Posting.model_validate_json(ln) for ln in path.read_text().splitlines() if ln.strip()]
