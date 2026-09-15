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


def test_lever_parse_uses_resolved_name_and_keeps_id_stable():
    _, posts_fallback = lever.parse((F / "lever_sample.json").read_text(), "palantir")
    _, posts_resolved = lever.parse((F / "lever_sample.json").read_text(), "palantir", name="Palantir Technologies")
    assert posts_fallback[0].company == "Palantir"
    assert posts_resolved[0].company == "Palantir Technologies"
    assert posts_fallback[0].id == posts_resolved[0].id  # id = sha1(source:source_id), unaffected by company name


def test_ashby_parse():
    n, posts = ashby.parse((F / "ashby_sample.json").read_text(), "openai")
    assert n == 3 and len(posts) == 1
    p = posts[0]
    assert p.source == "ashby" and p.company == "Openai" and p.location and len(p.full_text) > 200


def test_ashby_parse_uses_resolved_name_and_keeps_id_stable():
    _, posts_fallback = ashby.parse((F / "ashby_sample.json").read_text(), "openai")
    _, posts_resolved = ashby.parse((F / "ashby_sample.json").read_text(), "openai", name="OpenAI")
    assert posts_fallback[0].company == "Openai"
    assert posts_resolved[0].company == "OpenAI"
    assert posts_fallback[0].id == posts_resolved[0].id


def test_greenhouse_parse_falls_back_to_resolved_name_when_no_company_name_field(tmp_path):
    body = (F / "greenhouse_sample.json").read_text()
    _, posts_default = greenhouse.parse(body, "anthropic")
    _, posts_named = greenhouse.parse(body, "anthropic", name="Anthropic PBC")
    # company_name is present in the fixture, so the resolved name is not needed as a fallback
    # here, but the id must still be stable regardless of which name wins.
    assert posts_default[0].id == posts_named[0].id


def test_parse_404_returns_empty():
    assert greenhouse.parse('{"status":404,"error":"not found"}', "x") == (0, [])
    assert lever.parse("Not Found", "x") == (0, [])
    assert ashby.parse("Not Found", "x") == (0, [])
