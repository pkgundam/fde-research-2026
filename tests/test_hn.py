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
