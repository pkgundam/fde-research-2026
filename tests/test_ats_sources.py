import json
from pathlib import Path
from sources import greenhouse, lever, ashby

F = Path("tests/fixtures")


def test_greenhouse_parse():
    n, posts = greenhouse.parse((F / "greenhouse_sample.json").read_text(), "anthropic")
    assert n == 3 and len(posts) == 1
    p = posts[0]
    assert p.source == "greenhouse" and p.title == "Forward Deployed Engineer" and p.company == "Anthropic"
    assert p.url.startswith("https://") and "<" not in p.full_text and len(p.full_text) > 200
    assert p.posted_date and len(p.posted_date) == 10


def test_lever_parse():
    n, posts = lever.parse((F / "lever_sample.json").read_text(), "palantir")
    assert n == 3 and len(posts) == 1
    p = posts[0]
    assert p.source == "lever" and p.company == "Palantir" and len(p.full_text) > 200
    assert p.posted_date and p.posted_date[:2] == "20"


def test_ashby_parse():
    n, posts = ashby.parse((F / "ashby_sample.json").read_text(), "openai")
    assert n == 3 and len(posts) == 1
    p = posts[0]
    assert p.source == "ashby" and p.company == "Openai" and p.location and len(p.full_text) > 200


def test_parse_404_returns_empty():
    assert greenhouse.parse('{"status":404,"error":"not found"}', "x") == (0, [])
    assert lever.parse("Not Found", "x") == (0, [])
    assert ashby.parse("Not Found", "x") == (0, [])
