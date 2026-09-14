from pathlib import Path
from sources import remotive, arbeitnow

F = Path("tests/fixtures")


def test_remotive_parse_filters_titles_locally():
    n, posts = remotive.parse((F / "remotive_sample.json").read_text())
    assert n == 3 and len(posts) == 1
    p = posts[0]
    assert p.source == "remotive" and p.remote_flag and p.company and "<" not in p.full_text
    assert p.posted_date and len(p.posted_date) == 10


def test_arbeitnow_parse():
    n, posts = arbeitnow.parse((F / "arbeitnow_sample.json").read_text())
    assert n == 3 and len(posts) == 1
    p = posts[0]
    assert p.source == "arbeitnow" and p.url.startswith("https://") and p.posted_date and p.posted_date[:2] == "20"
