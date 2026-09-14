import json
from sources import collect
from sources.base import Posting


def P(i, company, title, text="x" * 10, source="a"):
    return Posting(id=i, title=title, company=company, url="u", full_text=text, source=source)


def test_run_dedupes_and_writes_stats(monkeypatch, tmp_path):
    monkeypatch.setattr(collect, "PROCESSED_DIR", tmp_path)
    monkeypatch.setattr(collect, "SOURCE_RUNNERS", {
        "a": lambda refresh: (10, [P("1", "Acme", "Forward Deployed Engineer"), P("2", "Acme", "Senior Forward Deployed Engineer", "longer text")]),
        "b": lambda refresh: (5, [P("3", "Beta", "FDE", source="b")]),
    })
    posts, stats = collect.run()
    assert [p.id for p in posts] == ["2", "3"]
    assert stats == [{"name": "a", "fetched": 10, "matched": 2, "kept": 1}, {"name": "b", "fetched": 5, "matched": 1, "kept": 1}]
    lines = (tmp_path / "postings.jsonl").read_text().splitlines()
    assert len(lines) == 2 and json.loads(lines[0])["id"] == "2"
    assert json.loads((tmp_path / "collect_stats.json").read_text()) == stats
    assert [p.id for p in collect.load_postings()] == ["2", "3"]
