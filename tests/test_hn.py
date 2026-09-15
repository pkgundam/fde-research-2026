import json
from pathlib import Path
from sources import hn

HIT = {"objectID": "1", "story_id": 9, "parent_id": 9, "created_at": "2026-09-11T10:39:33Z",
       "comment_text": "Cider Consulting | NY, USA | REMOTE (US-based only)<p>We are hiring a Forward Deployed Engineer to own engagements end-to-end. Travel 20%."}


def test_parse_comment_top_level():
    p = hn.parse_comment(HIT)
    assert p.company == "Cider Consulting" and p.location == "NY, USA"
    assert p.remote_flag and p.travel_mentioned and p.source == "hn"
    assert p.title == "Forward Deployed Engineer"
    assert p.posted_date == "2026-09-11" and p.company_size_hint == "startup"
    assert p.url == "https://news.ycombinator.com/item?id=1"


def test_parse_comment_skips_replies_and_non_matching():
    assert hn.parse_comment({**HIT, "parent_id": 5}) is None
    assert hn.parse_comment({**HIT, "comment_text": "Acme | SF | Hiring a Data Scientist"}) is None


def test_parse_fixture():
    d = json.loads(Path("tests/fixtures/hn_comments_sample.json").read_text())
    posts = [p for p in map(hn.parse_comment, d["hits"]) if p]
    assert len(posts) >= 1


def test_parse_comment_rejects_prose_and_missing_pipe():
    # "field engineers" / prose mention should not count as a title match
    assert hn.parse_comment({
        **HIT,
        "comment_text": "Acme | SF | We are hiring Backend Engineers to support our field engineers",
    }) is None
    # no "|" separators at all -> reject, doesn't fit "Company | Location | ..." convention
    assert hn.parse_comment({
        **HIT,
        "comment_text": "We are hiring a Forward Deployed Engineer, no pipes here",
    }) is None


def test_list_threads_filters_non_hiring_threads_and_paginates(monkeypatch):
    hits = [
        {"objectID": "1", "title": "Ask HN: Who is hiring? (September 2026)"},
        {"objectID": "2", "title": "Ask HN: Who wants to be hired? (September 2026)"},
        {"objectID": "3", "title": "Ask HN: Freelancer? Seeking freelancer? (September 2026)"},
        {"objectID": "4", "title": "Ask HN: Who is hiring? (August 2026)"},
        {"objectID": "5", "title": "Ask HN: Who wants to be hired? (August 2026)"},
        {"objectID": "6", "title": "Ask HN: Freelancer? Seeking freelancer? (August 2026)"},
        {"objectID": "7", "title": "Ask HN: Who is hiring? (July 2026)"},
        {"objectID": "8", "title": "Ask HN: Who wants to be hired? (July 2026)"},
    ]
    captured = {}

    def fake(url, cache_key, *, refresh=False, params=None):
        captured["url"] = url
        return 200, json.dumps({"hits": hits})

    monkeypatch.setattr(hn.base, "cached_get", fake)
    threads = hn.list_threads(months=4)
    assert [t["objectID"] for t in threads] == ["1", "4", "7"]
    assert "hitsPerPage=16" in captured["url"]


def test_thread_window_parses_month_year_and_sorts_oldest_first():
    threads = [
        {"objectID": "1", "title": "Ask HN: Who is hiring? (September 2026)"},
        {"objectID": "2", "title": "Ask HN: Who is hiring? (February 2026)"},
        {"objectID": "3", "title": "Ask HN: Who is hiring? (June 2026)"},
    ]
    assert hn.thread_window(threads) == ("2026-02", "2026-09")


def test_thread_window_empty_returns_none_none():
    assert hn.thread_window([]) == (None, None)


def test_fetch_dedupes_across_queries_and_counts_fetched(monkeypatch):
    thread = {"objectID": "49522897", "title": "Ask HN: Who is hiring? (September 2026)"}
    valid_hit = {"objectID": "100", "parent_id": 49522897, "story_id": 49522897,
                 "created_at": "2026-09-11T10:39:33Z",
                 "comment_text": "Acme | SF | REMOTE<p>Hiring a Forward Deployed Engineer to lead delivery."}
    reply_hit = {"objectID": "101", "parent_id": 100, "story_id": 49522897,
                 "created_at": "2026-09-11T10:40:00Z",
                 "comment_text": "Interested, will apply."}

    def fake(url, cache_key, *, refresh=False, params=None):
        if "tags=story" in url:
            return 200, json.dumps({"hits": [thread]})
        return 200, json.dumps({"hits": [valid_hit, reply_hit]})

    monkeypatch.setattr(hn.base, "cached_get", fake)
    fetched, postings = hn.fetch(months=1)
    assert len(postings) == 1
    assert postings[0].company == "Acme"
    assert fetched == 2 * len(hn.QUERIES)
